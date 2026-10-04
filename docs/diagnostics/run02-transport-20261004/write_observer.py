"""One fixed PUT's local write observations; no dispatch, credentials or routing setup.

For an exclusively owned existing Session, Requests 2.34.2 / urllib3 2.8.0.
All hooks delegate to the existing instances and are removed on every exit.
The caller must separately authorize/spend the action, capture the response,
and hold unless local_body_send_completed is true. This module issues no grant.
"""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import errno
import hashlib
import http.client
import threading
import time

import requests
import urllib3
from urllib3.connection import HTTPConnection

URL = 'https://sandbox.zenodo.org/api/records/612988/draft'
BODY_SHA = '71830ca80356953b8654dd0e589eeff15b1b46c08c313b98372936c85c09da7a'
BODY_LENGTH = 517
ACCEPT = 'application/vnd.inveniordm.v1+json'


class ObservationHeld(RuntimeError):
    """Fixed message only; never includes headers, credentials or exception text."""


def require(condition):
    if not condition:
        raise ObservationHeld('Offline-reviewed observer invariant failed')


def failure_code(error):
    if isinstance(error, OSError):
        return {errno.EPIPE: 'EPIPE', errno.ECONNRESET: 'ECONNRESET',
                errno.EPROTOTYPE: 'EPROTOTYPE'}.get(error.errno, 'other_os_error')
    if isinstance(error, ObservationHeld):
        return 'observer_hold'
    return 'other_exception'


def if_match_from_baseline(etag, revision_id):
    """Exact observed baseline only; public upstream parses If-Match as integer."""
    require(type(revision_id) is int and revision_id == 7 and etag == '"7"')
    return '7'


def replace(stack, instance, name, function):
    """Restore exact instance-attribute presence, not a new bound-method shadow."""
    prior = instance.__dict__.get(name)
    existed = name in instance.__dict__
    def restore():
        if existed:
            setattr(instance, name, prior)
        else:
            instance.__dict__.pop(name, None)
    stack.callback(restore)
    setattr(instance, name, function)


@contextmanager
def observe_one_put(session, expected_body, if_match, persist):
    """Yield safe observations; preserve proxies, auth, TLS, adapters and exceptions.

    `persist` accepts a detached closed receipt and must atomically retain it in
    the caller's fresh private diagnostic ledger. It must not send any request.
    `if_match` is the separately reviewed decimal revision header, not guessed.
    Only the fixed517-byte body is supported. No streams/iterables are wrapped.
    """
    require(requests.__version__ == '2.34.2' and urllib3.__version__ == '2.8.0')
    require(type(expected_body) is bytes and len(expected_body) == BODY_LENGTH
            and hashlib.sha256(expected_body).hexdigest() == BODY_SHA)
    require(if_match == '7')
    require(not getattr(session, '_fixed_write_observer', False))
    adapter = session.get_adapter(URL)
    require(adapter.max_retries.total == 0)
    thread = threading.get_ident()
    started = time.monotonic()
    result = {'schema_version': 1, 'requests_version': requests.__version__,
              'urllib3_version': urllib3.__version__, 'events': [],
              'prepared_body_sha256': BODY_SHA, 'prepared_body_bytes': BODY_LENGTH,
              'session_send_calls': 0, 'pool_selections': 0, 'connection_checkouts': 0,
              'connection_requests': 0, 'body_send_calls': 0,
              'local_body_send_completed': False, 'write_failure_observed': False,
              'origin_receipt_proved': False, 'response_returned': False}

    def emit(event, **facts):
        require(threading.get_ident() == thread)
        result['events'].append({'event': event,
            'utc': datetime.now(timezone.utc).isoformat(),
            'elapsed_seconds': round(time.monotonic() - started, 6), **facts})
        # Receipt contains only our fixed keys/labels, booleans, numbers and hashes.
        import copy
        try:
            persist(copy.deepcopy(result))
        except BaseException:
            raise ObservationHeld('Observer receipt persistence failed') from None

    def validate_headers(headers):
        require(headers.get('Content-Length') == str(BODY_LENGTH)
                and 'Transfer-Encoding' not in headers
                and headers.get('Content-Type') == 'application/json'
                and headers.get('Accept') == ACCEPT
                and headers.get('If-Match') == if_match)

    with ExitStack() as lifetime:
        replace(lifetime, session, '_fixed_write_observer', True)
        original_send = session.send
        original_pool_selection = adapter.get_connection_with_tls_context

        def send(prepared, **options):
            require(threading.get_ident() == thread and result['session_send_calls'] == 0)
            result['session_send_calls'] += 1
            require(prepared.method == 'PUT' and prepared.url == URL
                    and type(prepared.body) is bytes and prepared.body == expected_body
                    and options.get('allow_redirects') is False
                    and options.get('stream') is True
                    and options.get('verify') not in (None, False, ''))
            validate_headers(prepared.headers)
            emit('session_send_entered', content_length=BODY_LENGTH, transfer_encoding_absent=True)
            try:
                response = original_send(prepared, **options)
            except BaseException as error:
                emit('session_send_exception', exception=failure_code(error))
                raise
            result['response_returned'] = True
            try:
                emit('response_headers_returned', status=response.status_code
                     if type(response.status_code) is int and 100 <= response.status_code <= 599 else None)
            except BaseException:
                # Caller never received this streamed response; release it here.
                try:
                    response.close()
                except BaseException:
                    result['response_cleanup_failed'] = True
                raise
            return response

        def select_pool(*args, **kwargs):
            require(threading.get_ident() == thread and result['pool_selections'] == 0)
            result['pool_selections'] += 1
            pool = original_pool_selection(*args, **kwargs)
            emit('original_pool_selected', proxy_present=bool(getattr(pool, 'proxy', None)))
            original_checkout = pool._get_conn

            def checkout(*args, **kwargs):
                require(threading.get_ident() == thread and result['connection_checkouts'] == 0)
                result['connection_checkouts'] += 1
                conn = original_checkout(*args, **kwargs)
                hooks = ExitStack()
                try:
                    require(getattr(conn.request, '__func__', None) is HTTPConnection.request
                            and getattr(conn.send, '__func__', None) is http.client.HTTPConnection.send
                            and getattr(conn.endheaders, '__func__', None) is http.client.HTTPConnection.endheaders
                            and getattr(conn.putheader, '__func__', None) is HTTPConnection.putheader
                            and all(getattr(getattr(conn, name), '__self__', None) is conn
                                    for name in ('request', 'send', 'endheaders', 'putheader'))
                            and conn.debuglevel == 0)
                    original_request = conn.request

                    def request(method, url, body=None, headers=None, **options):
                        require(threading.get_ident() == thread and result['connection_requests'] == 0)
                        result['connection_requests'] += 1
                        require(method == 'PUT' and url == '/api/records/612988/draft'
                                and type(body) is bytes and body == expected_body
                                and options.get('chunked') is False)
                        validate_headers(headers)
                        emit('connection_request_entered')
                        phase = {'headers': False, 'ended': False, 'length_headers': 0}
                        original_endheaders, original_write, original_header = conn.endheaders, conn.send, conn.putheader

                        def header(name, *values):
                            lowered = name.lower() if isinstance(name, str) else name.decode('ascii').lower()
                            require(lowered != 'transfer-encoding')
                            if lowered == 'content-length':
                                require(values == (str(BODY_LENGTH),) and phase['length_headers'] == 0)
                                phase['length_headers'] += 1
                            return original_header(name, *values)

                        def endheaders(message_body=None, *, encode_chunked=False):
                            require(message_body is None and encode_chunked is False
                                    and not phase['ended'] and phase['length_headers'] == 1)
                            phase['headers'] = True
                            try:
                                value = original_endheaders(message_body, encode_chunked=encode_chunked)
                            finally:
                                phase['headers'] = False
                            phase['ended'] = True
                            emit('headers_send_returned', content_length=BODY_LENGTH,
                                 transfer_encoding_absent=True)
                            return value

                        def write(data):
                            require(threading.get_ident() == thread)
                            is_body = not phase['headers']
                            if is_body:
                                require(phase['ended'] and result['body_send_calls'] == 0
                                        and type(data) is bytes and data == expected_body)
                                result['body_send_calls'] += 1
                                emit('body_send_entered', bytes_requested=BODY_LENGTH)
                            try:
                                value = original_write(data)
                            except BaseException as error:
                                result['write_failure_observed'] = True
                                emit('body_send_exception' if is_body else 'header_send_exception',
                                     exception=failure_code(error), accepted_bytes_unknown=True)
                                raise
                            if is_body:
                                result['local_body_send_completed'] = True
                                emit('body_send_returned', local_bytes_send_returned=BODY_LENGTH)
                            return value

                        with ExitStack() as scoped:
                            replace(scoped, conn, 'putheader', header)
                            replace(scoped, conn, 'endheaders', endheaders)
                            replace(scoped, conn, 'send', write)
                            try:
                                value = original_request(method, url, body=body, headers=headers, **options)
                            except BaseException as error:
                                emit('connection_request_exception', exception=failure_code(error))
                                raise
                            emit('connection_request_returned')
                            return value

                    replace(hooks, conn, 'request', request)
                    emit('original_connection_observed')
                    lifetime.callback(hooks.close)
                    return conn
                except BaseException:
                    hooks.close()
                    try:
                        conn.close()
                    finally:
                        pool._put_conn(None)
                    raise

            replace(lifetime, pool, '_get_conn', checkout)
            return pool

        replace(lifetime, adapter, 'get_connection_with_tls_context', select_pool)
        replace(lifetime, session, 'send', send)
        emit('observer_ready')
        yield result
