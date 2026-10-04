"""One-pass bounded response capture; no requests, token lookup, or persistence.

The caller owns private, atomic 0600 persistence of ``result.artifact`` only.
``result.data`` is original parsed data for the controller and MUST NOT be logged
or persisted as the sanitized artifact. This is a bounded credential/URL filter,
not a universal sanitizer or an assertion that metadata is public. Body hashes
describe bytes yielded by iter_content (normally decoded), not TLS/wire bytes.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import re

from scripts.modern_canary_errors import (
    _credential_variants,
    _normalized_error_text,
    _safe_trace_headers,
    body_credential_echoed,
)

MAX_BODY_BYTES = 65536
_JSON_MIMES = {"application/json", "application/vnd.inveniordm.v1+json"}
_CREDENTIAL_KEYS = {
    "authorization", "proxyauthorization", "accesstoken", "refreshtoken",
    "idtoken", "token", "apikey", "password", "passwd", "pwd", "secret",
    "clientsecret", "cookie", "setcookie", "sessionid", "sessiontoken",
    "credential", "credentials", "accesskey", "secretkey", "privatekey", "bearer",
    "auth", "authentication", "authtoken", "apitoken", "bearertoken", "xapikey", "xauthtoken",
    "cookies", "session", "secretaccesskey", "awsaccesskeyid", "awssecretaccesskey",
    "awssessiontoken", "currentpassword", "newpassword", "passwordconfirmation",
}
_HEADER_KEYS = {"headers", "requestheaders", "responseheaders"}
_ASSIGNMENT_FIELD = re.compile(r'''(?i)(?=\b([a-z][a-z0-9_ -]{0,63})["']?\s*[:=]\s*\S)''')
_AUTH_SCHEME = re.compile(r"(?i)\b(?:Bearer|Basic)\s+\S+")
_URL = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://|\bwww\.|\b(?:mailto|data|javascript):")


@dataclass(frozen=True)
class CaptureResult:
    data: object = field(repr=False)
    artifact: dict


class _Hold(Exception):
    pass


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Hold("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise _Hold("nonfinite_json_number")


def _normalized(value):
    result = _normalized_error_text(value).replace("\\/", "/")
    if result == "[REDACTED_UNRESOLVED_ENCODING]" or re.search(
        r"\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})", result
    ):
        raise _Hold("uncertain_string_encoding")
    return result


def _credential_assignment(value):
    return bool(_AUTH_SCHEME.search(value)) or any(
        re.sub(r"[^a-z0-9]", "", match.group(1).lower()) in _CREDENTIAL_KEYS
        for match in _ASSIGNMENT_FIELD.finditer(value)
    )


def _url_or_path(value):
    return bool(_URL.search(value) or value.startswith(("/", "./", "../", "\\\\"))
                or re.match(r"^[A-Za-z]:\\", value))


def _safe_headers(response, variants):
    """Preserve only these response headers, with bounded value grammars."""
    headers = {}
    suppressed = False
    allowed = ("Content-Type", "Content-Length", "ETag", "Date",
               "X-Revision-Id", "X-Revision", "Revision")
    for name in allowed:
        value = response.headers.get(name)
        if value is None:
            continue
        if not isinstance(value, str) or len(value) > 256:
            suppressed = True
            continue
        try:
            normalized = _normalized(value)
        except _Hold:
            suppressed = True
            continue
        if (any(secret in normalized for secret in variants)
                or _credential_assignment(normalized) or _url_or_path(normalized)):
            suppressed = True
            continue
        if name == "Content-Type":
            valid = bool(re.fullmatch(
                r"(?:application/json|application/vnd\.inveniordm\.v1\+json|"
                r"text/plain|text/html)(?:;\s*charset=(?:utf-8|UTF-8))?", value
            ))
        elif name == "ETag":
            valid = bool(re.fullmatch(r'(?:W/)?"[A-Za-z0-9._:-]{1,128}"', value))
        elif name == "Date":
            try:
                valid = bool(re.fullmatch(
                    r"[A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} GMT", value
                )) and parsedate_to_datetime(value).tzinfo is not None
            except (ValueError, TypeError, OverflowError):
                valid = False
        else:
            valid = bool(re.fullmatch(r"[0-9]{1,20}", value))
        if valid:
            headers[name] = value
        else:
            suppressed = True
    return headers, suppressed


def _sanitize(data, variants):
    state = {"credential_content_redacted": False, "urls_redacted": False,
             "headers_redacted": False}
    nodes = 0

    def string(value):
        normalized = _normalized(value)
        if any(secret in normalized for secret in variants) or _credential_assignment(normalized):
            state["credential_content_redacted"] = True
            return "[REDACTED_CREDENTIAL]"
        if _url_or_path(normalized):
            state["urls_redacted"] = True
            return "[REDACTED_URL]"
        return value

    def visit(value, depth):
        nonlocal nodes
        nodes += 1
        if nodes > 8192 or depth > 64:
            raise _Hold("json_structure_limit")
        if isinstance(value, str):
            return string(value)
        if isinstance(value, list):
            return [visit(item, depth + 1) for item in value]
        if isinstance(value, dict):
            result = {}
            for index, (key, item) in enumerate(value.items()):
                safe_key = string(key)
                if safe_key != key:
                    safe_key = f"[REDACTED_KEY_{index}]"
                if safe_key in result or (safe_key != key and safe_key in value):
                    raise _Hold("redacted_key_collision")
                normalized_key = re.sub(r"[^a-z0-9]", "", _normalized(key).lower())
                if normalized_key in _CREDENTIAL_KEYS:
                    result[safe_key] = "[REDACTED_CREDENTIAL]"
                    state["credential_content_redacted"] = True
                elif normalized_key in _HEADER_KEYS:
                    result[safe_key] = "[REDACTED_HEADERS]"
                    state["headers_redacted"] = True
                else:
                    result[safe_key] = visit(item, depth + 1)
            return result
        return value

    sanitized = visit(data, 0)
    encoded = json.dumps(sanitized, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    if body_credential_echoed(encoded, sanitized, variants[0]):
        raise _Hold("credential_remaining_after_redaction")
    if len(encoded) > MAX_BODY_BYTES:
        raise _Hold("sanitized_snapshot_limit")
    return sanitized, state


def capture_response(response, token, *, max_body_bytes=MAX_BODY_BYTES):
    """Consume iter_content once, returning original data plus a safe artifact.

    Does not call raise_for_status: 200 validation errors and 400/412 responses
    receive the same capture. On a stream failure/truncation, no partial JSON is
    returned. The caller must stop/reconcile on snapshot_available=False, and is
    responsible for closing the response, especially after the size cutoff.
    """
    if (not isinstance(token, str) or not token or not token.isascii()
            or any(not 33 <= ord(ch) <= 126 for ch in token)):
        raise ValueError("An explicit printable ASCII token is required")
    if type(max_body_bytes) is not int or not 1 <= max_body_bytes <= MAX_BODY_BYTES:
        raise ValueError("max_body_bytes must be between 1 and 65536")
    variants = _credential_variants(token)
    headers, suppressed = _safe_headers(response, variants)
    status = response.status_code
    artifact = {
        "schema_version": 1, "private_only": True,
        "sanitizer_scope": "known_credentials_conventional_keys_urls_header_blocks",
        "read_started_utc": _utc_now(), "read_finished_utc": None,
        "status": status if type(status) is int and 100 <= status <= 599 else None,
        "headers": headers, "allowlisted_header_suppressed": suppressed,
        "trace_identifiers": _safe_trace_headers(response, token),
        "max_body_bytes": max_body_bytes, "captured_bytes": 0,
        "iterator_exhausted": False, "body_complete": False, "body_sha256": None,
        "content_length_check": "not_evaluated", "content_encoding": "not_evaluated",
        "transfer_encoding": "not_evaluated",
        "body_hash_scope": "complete_iter_content_bytes_not_wire_bytes",
        "credential_echo_detected": False,
        "snapshot_available": False, "snapshot": None, "hold_reason": None,
    }
    buffer = bytearray()
    reason = None
    try:
        for chunk in response.iter_content(chunk_size=min(4096, max_body_bytes + 1)):
            if not isinstance(chunk, bytes):
                reason = "unsupported_stream_chunk"
                break
            remaining = max_body_bytes - len(buffer)
            buffer.extend(chunk[:remaining])
            if len(chunk) > remaining:
                reason = "body_size_limit"
                break
        else:
            artifact["iterator_exhausted"] = True
            artifact["body_complete"] = True
    except Exception:
        # Provider/transport exception text can contain credentials and URLs.
        reason = "body_read_error"
    artifact["read_finished_utc"] = _utc_now()
    raw = bytes(buffer)
    artifact["captured_bytes"] = len(raw)
    data = None
    artifact["credential_echo_detected"] = body_credential_echoed(raw, None, token)
    if reason is None and artifact["body_complete"]:
        # Evaluate original header shape even when its persistable value was
        # suppressed; an omitted malformed header must not silently skip checks.
        length = response.headers.get("Content-Length")
        length_valid = isinstance(length, str) and bool(re.fullmatch(r"[0-9]{1,20}", length))
        encoding = response.headers.get("Content-Encoding", "identity")
        encoding = encoding.strip().lower() if isinstance(encoding, str) else "unsupported"
        if encoding == "":
            encoding = "identity"
        supported_encoding = encoding in ("identity", "gzip", "deflate", "br", "zstd")
        artifact["content_encoding"] = encoding if supported_encoding else "unsupported"
        transfer = response.headers.get("Transfer-Encoding")
        transfer = transfer.strip().lower() if isinstance(transfer, str) else transfer
        artifact["transfer_encoding"] = ("absent" if transfer is None else
                                         "chunked" if transfer == "chunked" else "unsupported")
        if length is not None and not length_valid:
            artifact["content_length_check"] = "invalid"
            reason = "invalid_content_length"
        elif not supported_encoding:
            artifact["content_length_check"] = "unavailable_unsupported_encoding"
            reason = "unsupported_content_encoding"
        elif artifact["transfer_encoding"] == "unsupported":
            artifact["content_length_check"] = "unavailable_unsupported_framing"
            reason = "unsupported_transfer_encoding"
        elif transfer is not None and length is not None:
            artifact["content_length_check"] = "conflicting_framing"
            reason = "conflicting_response_framing"
        elif length is None:
            artifact["content_length_check"] = "unavailable_no_content_length"
        elif encoding != "identity":
            # iter_content yields decoded bytes, not the encoded length.
            artifact["content_length_check"] = "unavailable_decoded_encoding"
        elif int(length) != len(raw):
            artifact["content_length_check"] = "mismatch"
            reason = "content_length_mismatch"
        else:
            artifact["content_length_check"] = "verified"
        if reason is not None:
            artifact["body_complete"] = False
    if reason is None:
        mime = headers.get("Content-Type", "").split(";", 1)[0]
        if mime not in _JSON_MIMES:
            reason = "unsupported_content_type"
        else:
            try:
                data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                                  parse_constant=_reject_constant)
                artifact["credential_echo_detected"] |= body_credential_echoed(raw, data, token)
                if not isinstance(data, dict):
                    raise _Hold("unsupported_json_root")
                sanitized, redactions = _sanitize(data, variants)
                artifact.update(redactions)
                artifact["snapshot"] = sanitized
                artifact["snapshot_available"] = True
            except _Hold as exc:
                reason = str(exc)  # All _Hold values are fixed local enums.
            except (ValueError, UnicodeError, RecursionError):
                reason = "invalid_json"
    if (artifact["body_complete"] and not artifact["credential_echo_detected"]
            and not artifact.get("credential_content_redacted")
            and not artifact.get("headers_redacted") and reason is None):
        artifact["body_sha256"] = hashlib.sha256(raw).hexdigest()
    artifact["hold_reason"] = reason
    return CaptureResult(data=data, artifact=artifact)
