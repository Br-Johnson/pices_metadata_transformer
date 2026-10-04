"""Selected redacted error diagnostics copied from reviewed02ba0e0.

No raw provider body, request URL, private owner or arbitrary response header is
persisted. The mandatory token is redacted before truncation. This pure helper
performs no network or credential resolution.
"""
import base64
import hashlib
import html
import json
import re
import unicodedata
from html.parser import HTMLParser
from urllib.parse import quote, unquote

VALIDATION_ERROR_FIELDS = (
    'metadata', 'metadata.keywords', 'metadata.subjects', 'metadata.resource_type',
    'metadata.creators', 'metadata.title', 'metadata.publication_date',
    'metadata.publisher', 'metadata.description', 'access', 'access.files', 'files',
)


def validation_errors_projection(data, token):
    """Flags and bounded schema paths only; never messages or provider values.

    The caller checks whole-body credential echoes first. Paths are checked
    against credential variants before any length bound or truncation; unsafe
    names are suppressed, rather than normalized into a different field.
    """
    present = isinstance(data, dict) and 'errors' in data
    errors = data.get('errors') if present else None
    labels = {str: 'string', dict: 'object', list: 'array', int: 'integer',
              bool: 'boolean', type(None): 'null'}
    result = {'errors_present': present,
              'errors_type': labels.get(type(errors), 'other') if present else 'missing',
              'errors_count': len(errors) if isinstance(errors, list) else None,
              'errors_shape_supported': isinstance(errors, list), 'unknown_error_field_present': False,
              'error_fields': [], 'error_field_names_suppressed': False,
              'error_field_names_truncated': False}
    result.update({name.replace('.', '_') + '_error_present': False for name in VALIDATION_ERROR_FIELDS})
    if isinstance(errors, list):
        for item in errors:
            field = item.get('field') if isinstance(item, dict) else None
            if field in VALIDATION_ERROR_FIELDS:
                result[field.replace('.', '_') + '_error_present'] = True
            else:
                result['unknown_error_field_present'] = True
            if not isinstance(item, dict) or not isinstance(field, str):
                result['errors_shape_supported'] = False
            # Modern paths use named components and bounded array indices.
            # URLs, spaces, punctuation, controls and opaque strings cannot pass.
            safe = (isinstance(field, str) and isinstance(token, str) and token
                    and token.isascii() and len(field) <= 128
                    and not any(secret in _normalized_error_text(field)
                                for secret in _credential_variants(token)))
            if safe:
                safe = bool(re.fullmatch(
                    r'[a-z_][a-z0-9_]{0,47}(?:\.[a-z_][a-z0-9_]{0,47}|\.[0-9]{1,4}|\[[0-9]{1,4}\]){0,11}', field))
                safe = safe and not re.search(r'[A-Za-z0-9]{24,}', field)
            if not safe:
                result['error_field_names_suppressed'] = True
            elif field not in result['error_fields']:
                if len(result['error_fields']) < 16:
                    result['error_fields'].append(field)
                else:
                    result['error_field_names_truncated'] = True
        result['error_fields'].sort()
    return result


def credential_echoed(data, token):
    """Check decoded JSON too: quotes, backslashes and Unicode can be escaped."""
    pending = [data]
    while pending:
        value = pending.pop()
        if isinstance(value, str) and token in value:
            return True
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return False

ERROR_PHRASES = ('internal server error', 'bad request', 'service unavailable',
                 'unexpected error', 'validation error', 'unauthorized', 'forbidden',
                 'not found', 'too many requests', 'gateway timeout', 'bad gateway')

TRACE_HEADERS = ('x-request-id', 'x-correlation-id', 'x-trace-id', 'traceparent',
                 'sentry-trace', 'x-amzn-trace-id', 'cf-ray')

def _normalized_error_text(value):
    for _ in range(8):
        decoded = html.unescape(unquote(value))
        if decoded == value:
            return ''.join(ch for ch in value if not unicodedata.category(ch).startswith('C'))
        value = decoded
    # A bounded normalization must suppress unresolved encodings, not leak them.
    if html.unescape(unquote(value)) != value:
        return '[REDACTED_UNRESOLVED_ENCODING]'
    return ''.join(ch for ch in value if not unicodedata.category(ch).startswith('C'))

def _credential_variants(token):
    standard = base64.b64encode(token.encode('ascii')).decode('ascii')
    urlsafe = base64.urlsafe_b64encode(token.encode('ascii')).decode('ascii')
    return (token, quote(token, safe=''), html.escape(token), standard, urlsafe,
            standard.rstrip('='), urlsafe.rstrip('='))

class _HumanErrorText(HTMLParser):
    """Collect human heading/message text while excluding active markup content."""
    def __init__(self, heading_only=False):
        super().__init__(convert_charrefs=True)
        self.heading_only, self.heading, self.finished = heading_only, None, False
        self.blocked, self.parts = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.blocked.append(tag)
        elif not self.blocked and not self.finished and self.heading is None and tag in ('title', 'h1'):
            self.heading = tag

    def handle_endtag(self, tag):
        if self.blocked:
            if tag == self.blocked[-1]:
                self.blocked.pop()
        elif self.heading_only and tag == self.heading:
            self.finished = True

    def handle_data(self, value):
        if not self.blocked and not self.finished and (not self.heading_only or self.heading):
            self.parts.append(value)

def _safe_message(value, token):
    """Redact selected human error text before truncation, never a nested body."""
    original = value
    value = _normalized_error_text(value)
    parser = _HumanErrorText()
    parser.feed(value)
    value = ''.join(parser.parts)
    # Error messages occasionally append structured payloads or traceback data.
    # Keep their diagnostic prefix, never the appended private object/stack.
    value = re.split(r'(?i)(?:Traceback|Stack trace)', value, maxsplit=1)[0]
    value = re.sub(r'(?s)[\{\[].*', '[REDACTED_STRUCTURED_CONTENT]', value)
    for secret in _credential_variants(token):
        value = value.replace(secret, '[REDACTED_CREDENTIAL]')
    value = re.sub(r'(?i)\b(?:authorization|bearer|token|access_token|api[_ -]?key|password|secret|cookie|session|owner|account_id|user_id|email|name|path)\s*[:=]\s*[^;,]+', '[REDACTED_PRIVATE_FIELD]', value)
    value = re.sub(r'(?i)\bBearer\s+\S+', 'Bearer [REDACTED_CREDENTIAL]', value)
    value = re.sub(r'(?i)\b(?:https?://|www\.)\S+', '[REDACTED_URL]', value)
    value = re.sub(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w.-]+", '[REDACTED_EMAIL]', value)
    value = re.sub(r'(?<!\w)(?:/[\w./-]+|[A-Za-z]:\\[^;,]+|\\{1,2}[^;,]+)', '[REDACTED_PATH]', value)
    value = re.sub(r'\b[A-Za-z0-9_+/=-]{24,}\b', '[REDACTED_OPAQUE_VALUE]', value)
    value = re.sub(r'\b\d+\b', '[REDACTED_NUMBER]', value)
    value = re.sub(r'\s+', ' ', value).strip()
    # Markers are fixed text. A credential echo must never survive normalization.
    for secret in _credential_variants(token):
        value = value.replace(secret, '[REDACTED_CREDENTIAL]')
    return value[:512], value != original, len(value) > 512

def _safe_trace_headers(response, token):
    """Only request identifiers with recognized trace syntax, never arbitrary values."""
    result = {}
    generic = r'(?:[0-9a-f]{16,64}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})'
    formats = {'traceparent': r'00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}',
               'sentry-trace': r'[0-9a-f]{32}-[0-9a-f]{16}(?:-[01])?',
               'x-amzn-trace-id': r'Root=1-[0-9a-f]{8}-[0-9a-f]{24}(?:;Parent=[0-9a-f]{16})?(?:;Sampled=[01])?',
               'cf-ray': r'[0-9a-f]{16}(?:-[A-Z]{3})?'}
    for key in TRACE_HEADERS:
        value = response.headers.get(key)
        if (isinstance(value, str) and len(value) <= 128
                and not any(secret in _normalized_error_text(value) for secret in _credential_variants(token))
                and re.fullmatch(formats.get(key, generic), value, re.IGNORECASE)):
            if key == 'traceparent' and (value.split('-')[1] == '0' * 32 or value.split('-')[2] == '0' * 16):
                continue
            result[key] = value
    return result

def response_projection(raw, response, method, token):
    """Retain selected redacted diagnostics; no other body, keys, values or headers."""
    status = response.status_code
    mime = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
    result = {'method': method, 'status': status if type(status) is int and 100 <= status <= 599 else None,
              'content_type': mime if mime in ('application/json', 'text/html', 'text/plain', 'application/xml') else 'other',
              'observed_bytes': len(raw), 'body_sha256': hashlib.sha256(raw).hexdigest()}
    data = None
    try:
        data = json.loads(raw)
        result['body_format'] = 'json'
        result['known_error_fields'] = sorted(k for k in ('message', 'errors', 'error', 'status', 'code')
                                              if isinstance(data, dict) and k in data)
    except (ValueError, UnicodeError, RecursionError):
        result['body_format'] = 'html' if b'<' in raw[:256] else 'other'
    text = raw.decode('utf-8', errors='replace').lower()
    result['error_categories'] = [phrase for phrase in ERROR_PHRASES if phrase in text] if result['status'] and result['status'] >= 400 else []
    result['credential_echo_detected'] = token.encode('ascii') in raw or credential_echoed(data, token)
    if result['status'] and result['status'] >= 400:
        result['trace_identifiers'] = _safe_trace_headers(response, token)
        message, source = None, None
        if isinstance(data, dict):
            if isinstance(data.get('message'), str):
                message, source = data['message'], 'json.message'
            body_status = data.get('status')
            if type(body_status) is int and 100 <= body_status <= 599:
                result['error_status'] = body_status
        elif result['body_format'] == 'html':
            parser = _HumanErrorText(heading_only=True)
            parser.feed(_normalized_error_text(raw.decode('utf-8', errors='replace')))
            if parser.heading and parser.finished:
                message, source = ''.join(parser.parts), 'html.' + parser.heading
        if message is not None:
            safe, redacted, truncated = _safe_message(message, token)
            result.update(error_message=safe, error_message_source=source,
                          error_message_redacted=redacted, error_message_truncated=truncated)
    return result
