"""Bounded diagnostic evidence, independent of response acceptance or authority.

No network or credential discovery. Only complete, credential-screened response
bodies can supply a bounded diagnostic prefix. Partial reads remain failures.
"""

import base64
import hashlib
import html
import json
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit, urlunsplit

MAX_RESPONSE_BYTES = 1024 * 1024
MAX_DIAGNOSTIC_BYTES = 64 * 1024


@dataclass(frozen=True)
class Response:
    status: int
    mime: str
    body: bytes
    location: str | None = None
    complete: bool = True
    read_error: str | None = None


def normalize_response(value):
    # The legacy three-field injected transport remains usable offline. The real
    # transport always reports completeness and the allowlisted response headers.
    if isinstance(value, tuple) and len(value) == 3:
        value = Response(*value)
    if (not isinstance(value, Response) or type(value.status) is not int
            or not 100 <= value.status <= 599 or not isinstance(value.body, bytes)
            or len(value.body) > MAX_RESPONSE_BYTES or type(value.complete) is not bool
            or value.read_error not in (None, 'body_limit', 'read_interrupted', 'incomplete_body')
            or value.complete != (value.read_error is None)):
        raise ValueError('Invalid bounded response evidence')
    return value


def sensitive(raw, token):
    """Suppress known credential encodings and explicit credential assignments.

Scan the entire received body before taking a prefix. Never retain a transformed
credential-bearing response or a hash of its secret-bearing bytes.
"""
    variants = {token, json.dumps(token)[1:-1]}
    for encoder in (base64.b64encode, base64.urlsafe_b64encode):
        encoded = encoder(token.encode()).decode()
        variants.update((encoded, encoded.rstrip('=')))
        # Interior blocks also catch the token inside a larger base64 container,
        # independent of the three possible byte alignments and trailing data.
        variants.update(encoder(b'x' * offset + token.encode()).decode()[4:-4] for offset in range(3))
    variants.update((token.encode().hex(), token.encode().hex().upper()))
    if any(token.encode(encoding) in raw for encoding in ('utf-8', 'utf-16le', 'utf-16be')):
        return True
    def contains(value):
        if any(variant in value for variant in variants):
            return True
        return bool(re.search(r'(?i)\b(?:authorization|proxy-authorization|set-cookie|cookie|'
                              r'access[_-]?token|refresh[_-]?token|token|api[_-]?key|password|client[_-]?secret|secret)'
                              r'[\s"\']*[:=]', value))

    def decode_once(value):
        changed = html.unescape(unquote(value))
        changed = re.sub(r'\\u00([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), changed)
        changed = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), changed)
        return changed.replace('\\/', '/')

    value = raw.decode('utf-8', errors='replace')
    for _ in range(5):
        if contains(value):
            return True
        changed = decode_once(value)
        if changed == value:
            return False
        value = changed
    # Residual encoded wrappers are omitted rather than treated as proof that a
    # deeply nested credential is safe to persist.
    return contains(value) or decode_once(value) != value


def safe_location(value):
    if value is None:
        return None, 'absent'
    if (not isinstance(value, str) or len(value) > 4096
            or any(ord(c) <= 32 or ord(c) >= 127 or c in ',\\' for c in value)):
        return None, 'omitted_invalid'
    try:
        parts = urlsplit(value)
        if (parts.username is not None or parts.password is not None
                or parts.scheme not in ('', 'http', 'https')
                or (parts.scheme and not parts.netloc)):
            return None, 'omitted_invalid'
        sanitized = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
    except ValueError:
        return None, 'omitted_invalid'
    return sanitized, 'query_fragment_removed' if parts.query or parts.fragment else 'retained'


def diagnostic(response, token):
    response = normalize_response(response)
    headers = [v for v in (response.mime, response.location) if isinstance(v, str)]
    suppressed = sensitive(response.body, token) or any(sensitive(v.encode(), token) for v in headers)
    # Incomplete prefixes may end inside a credential; omit them entirely.
    retained = response.body[:MAX_DIAGNOSTIC_BYTES] if response.complete and not suppressed else b''
    mime = response.mime
    if suppressed or not isinstance(mime, str) or len(mime) > 512 or any(not 32 <= ord(c) < 127 for c in mime):
        mime = None
    location, location_status = ((None, 'credential_suppressed') if suppressed else safe_location(response.location))
    full_sha = hashlib.sha256(response.body).hexdigest() if response.complete and not suppressed else None
    return {
        'schema_version': 1, 'kind': 'modern-response-diagnostic-v1',
        'http_status': response.status, 'content_type': mime, 'location': location,
        'location_status': location_status, 'response_complete': response.complete,
        'read_error': response.read_error, 'received_bytes': len(response.body),
        'received_bytes_scope': 'complete_body' if response.complete else 'captured_prefix_lower_bound',
        'credential_suppressed': suppressed, 'response_sha256': full_sha,
        'body_base64': base64.b64encode(retained).decode(), 'retained_bytes': len(retained),
        'retained_sha256': hashlib.sha256(retained).hexdigest() if retained else None,
        'body_status': ('credential_suppressed' if suppressed else 'incomplete_omitted'
                        if not response.complete else 'prefix' if len(retained) < len(response.body) else 'complete'),
        'diagnostic_only': True,
    }
