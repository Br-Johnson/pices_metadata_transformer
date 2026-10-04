"""Offline only: real Session/adapter/pool, synthetic sockets, no DNS or network."""
import copy
from contextlib import nullcontext
import errno
import io
import json
import os
from pathlib import Path
import socket
import sys
import threading
import tempfile
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, '/workspace/pices_metadata_transformer')
import requests
from urllib3.connection import HTTPSConnection
from urllib3.connectionpool import HTTPSConnectionPool
from scripts import modern_synthetic_canary as modern
import write_observer as observer


BODY_VALUE = modern.modern_wire_payload(modern.load(modern.PACKET / 'metadata-put.json'))
BODY_VALUE['metadata']['publisher'] = 'Zenodo'
BODY = requests.Request('PUT', observer.URL, json=BODY_VALUE).prepare().body
TOKEN = 'offline-observer-dummy-token'
PROXY_USER = 'offline-proxy-user'
PROXY_PASS = 'offline-proxy-password'


class FakeSocket:
    def __init__(self, code=None, partial=0, location='body', tunnel=False):
        self.code, self.partial, self.location = code, partial, location
        self.tunnel = tunnel
        self.calls, self.accepted, self.read_count = [], [], 0
    def sendall(self, data):
        raw = bytes(data)
        self.calls.append(raw)
        location = ('body' if raw == BODY else 'connect' if raw.startswith(b'CONNECT ') else 'headers')
        if self.code is not None and location == self.location:
            self.accepted.append(raw[:self.partial])
            raise OSError(self.code, 'PRIVATE exception ' + TOKEN + PROXY_PASS)
        self.accepted.append(raw)
    def makefile(self, *args, **kwargs):
        self.read_count += 1
        if self.tunnel and self.read_count == 1:
            return io.BytesIO(b'HTTP/1.1 200 Connection established\r\n\r\n')
        return io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Length: 15\r\n'
                          b'Content-Type: application/vnd.inveniordm.v1+json\r\n'
                          b'ETag: "8"\r\nConnection: close\r\n\r\n{"metadata":{}}')
    def close(self):
        pass
    def settimeout(self, value):
        pass


def deny(*args, **kwargs):
    raise AssertionError('Real network forbidden')


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.blocks = []
        for block in (patch.dict(os.environ, {}, clear=True),
                      patch('requests.sessions.get_netrc_auth', return_value=None),
                      patch.object(socket, 'socket', deny), patch.object(socket, 'getaddrinfo', deny),
                      patch.object(socket, 'create_connection', deny)):
            block.start()
            self.addCleanup(block.stop)

    def run_request(self, code=None, partial=0, location='body', proxy=False, persist=None,
                    alter_headers=None, unsupported=False, observed=True, current_wrappers=False,
                    capture_body=False):
        fake = FakeSocket(code, partial, location, proxy)
        connections, pools = [], []
        receipts = []
        captured = {}
        def connect(conn):
            connections.append(conn)
            # The observer must not wrap CONNECT's send/endheaders.
            self.assertNotIn('send', conn.__dict__)
            self.assertNotIn('endheaders', conn.__dict__)
            conn.sock = fake
            if conn._tunnel_host:
                conn._tunnel()
            conn.is_verified = True
            conn.proxy_is_verified = True
            conn._has_connected_to_proxy = proxy
        def saver(value):
            receipts.append(copy.deepcopy(value))
            if persist:
                persist(value)
        with requests.Session() as session:
            adapter = session.get_adapter(observer.URL)
            original_pool = adapter.get_connection_with_tls_context
            def pool(*args, **kwargs):
                found = original_pool(*args, **kwargs)
                pools.append(found)
                captured['verify'] = args[1]
                captured['proxies'] = copy.deepcopy(kwargs.get('proxies'))
                return found
            adapter.get_connection_with_tls_context = pool
            # Preexisting instance override must be restored exactly.
            session_before, adapter_before = dict(session.__dict__), dict(adapter.__dict__)
            if proxy:
                os.environ['https_proxy'] = 'http://' + PROXY_USER + ':' + PROXY_PASS + '@offline.invalid:8080'
            headers = {'Authorization': 'Bearer ' + TOKEN, 'Accept': observer.ACCEPT,
                       'Content-Type': 'application/json', 'If-Match': '7'}
            if alter_headers:
                headers.update(alter_headers)
            connection_patch = patch.object(HTTPSConnection, 'connect', connect)
            if unsupported:
                original_get = HTTPSConnectionPool._get_conn
                def bad_get(pool, *args, **kwargs):
                    conn = original_get(pool, *args, **kwargs)
                    conn.send = lambda *_: None
                    connections.append(conn)
                    return conn
                self.enterContext(patch.object(HTTPSConnectionPool, '_get_conn', bad_get))
            with connection_patch:
                try:
                    scope = observer.observe_one_put(session, BODY, '7', saver) if observed else nullcontext({})
                    with scope as result:
                        captured['result'] = result
                        def dispatch(transport=None):
                            if transport is None:
                                response = session.request('PUT', observer.URL, json=BODY_VALUE, headers=headers,
                                    allow_redirects=False, verify=True, timeout=2, stream=True)
                            else:
                                response = transport('PUT', observer.URL, BODY_VALUE, headers,
                                    allow_redirects=False, verify=True, timeout=2, stream=True)
                            with response:
                                captured['status'] = response.status_code
                                if capture_body:
                                    from response.response_capture import capture_response
                                    body_capture = capture_response(response, TOKEN)
                                    captured['capture_artifact'] = body_capture.artifact
                                    captured['body'] = body_capture.data
                                else:
                                    captured['body'] = response.content
                        if current_wrappers:
                            class FixtureController:
                                validate_stage = staticmethod(Path)
                                def __init__(self, stage, token, transport):
                                    self.transport = transport
                                    self.grant = modern.load(stage / 'approval.json')
                                    self.state = {'pending': {'kind': 'metadata'}}
                                def observe(self, *args, **kwargs):
                                    pass
                                def check_prepared(self, prepared):
                                    assert prepared.body == BODY
                                def request(self):
                                    dispatch(self.transport)
                                def run(self, retry):
                                    self.request()
                            with tempfile.TemporaryDirectory() as stage:
                                modern.atomic(Path(stage) / 'approval.json', {'valid_until':
                                    (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()})
                                with patch.object(modern.requests, 'Session', return_value=session):
                                    modern._execute_controller(stage, TOKEN, FixtureController)
                        else:
                            dispatch()
                except BaseException as error:
                    captured['exception'] = type(error).__name__
            # Existing modern wrapper restores methods as bound instance shadows;
            # the observer itself restores exact attribute presence.
            self.assertEqual(set(session.__dict__), set(session_before) | ({'prepare_request'} if current_wrappers else set()))
            self.assertEqual(set(adapter.__dict__), set(adapter_before) | ({'send'} if current_wrappers else set()))
            if current_wrappers:
                self.assertIs(session.prepare_request.__func__, requests.sessions.Session.prepare_request)
                self.assertIs(adapter.send.__func__, requests.adapters.HTTPAdapter.send)
            self.assertIs(adapter.get_connection_with_tls_context, pool)
            for conn in connections:
                self.assertNotIn('request', conn.__dict__)
                self.assertNotIn('endheaders', conn.__dict__)
                self.assertNotIn('putheader', conn.__dict__)
                if not unsupported:
                    self.assertNotIn('send', conn.__dict__)
            for selected in pools:
                self.assertNotIn('_get_conn', selected.__dict__)
            self.assertIs(adapter, session.get_adapter(observer.URL))
            if unsupported:
                self.assertEqual(pools[0].pool.qsize(), 10)
        serialized = json.dumps(receipts)
        for secret in (TOKEN, PROXY_USER, PROXY_PASS, 'offline.invalid', 'Authorization', 'PRIVATE exception'):
            self.assertNotIn(secret, serialized)
        captured.update(socket=fake, receipts=receipts, pools=pools)
        return captured

    def test_direct_success_actual_fixed_body_and_final_framing(self):
        found = self.run_request()
        self.assertEqual(found['status'], 200)
        self.assertEqual(found['socket'].calls[-1], BODY)
        self.assertEqual(found['socket'].accepted[-1], BODY)
        self.assertTrue(found['result']['local_body_send_completed'])
        self.assertFalse(found['result']['write_failure_observed'])
        self.assertFalse(found['result']['origin_receipt_proved'])
        self.assertIn(b'Content-Length: 517\r\n', found['socket'].calls[0])
        self.assertNotIn(b'Transfer-Encoding', found['socket'].calls[0])
        self.assertTrue(found['verify'])

    def test_observation_leaves_direct_and_proxy_wire_bytes_identical(self):
        for proxy in (False, True):
            with self.subTest(proxy=proxy):
                baseline = self.run_request(proxy=proxy, observed=False)
                instrumented = self.run_request(proxy=proxy)
                self.assertEqual(baseline['socket'].calls, instrumented['socket'].calls)
                self.assertEqual(baseline['proxies'], instrumented['proxies'])
                self.assertEqual(baseline['verify'], instrumented['verify'])
                self.assertEqual(baseline['status'], instrumented['status'])
                self.assertEqual(baseline['body'], instrumented['body'])

    def test_current_execute_wrappers_compose_with_observer(self):
        baseline = self.run_request()
        composed = self.run_request(current_wrappers=True)
        self.assertEqual(baseline['socket'].calls, composed['socket'].calls)
        self.assertTrue(composed['result']['local_body_send_completed'])
        self.assertEqual(composed['status'], 200)

    def test_baseline_etag_requires_exact_strong_revision7(self):
        self.assertEqual(observer.if_match_from_baseline('"7"', 7), '7')
        for etag, revision in [('7', 7), ('W/"7"', 7), ('"8"', 7), ('"7"', 8), ('"7"', '7')]:
            with self.subTest(etag=etag, revision=revision), self.assertRaises(observer.ObservationHeld):
                observer.if_match_from_baseline(etag, revision)

    def test_integrated_body_capture_reads_once_after_observed_write(self):
        found = self.run_request(capture_body=True, current_wrappers=True)
        self.assertTrue(found['result']['local_body_send_completed'])
        self.assertEqual(found['socket'].read_count, 1)
        self.assertTrue(found['capture_artifact']['snapshot_available'])
        self.assertEqual(found['capture_artifact']['snapshot'], {'metadata': {}})
        self.assertEqual(found['capture_artifact']['headers']['ETag'], '"8"')

    def test_proxy_selection_connect_auth_and_original_adapter_unchanged(self):
        found = self.run_request(proxy=True)
        self.assertEqual(found['status'], 200)
        self.assertTrue(found['socket'].calls[0].startswith(b'CONNECT '))
        self.assertIn(b'Proxy-Authorization:', found['socket'].calls[0])
        self.assertNotIn(b'Proxy-Authorization:', found['socket'].calls[1])
        self.assertEqual(found['socket'].calls[-1], BODY)
        self.assertTrue(found['result']['local_body_send_completed'])
        self.assertEqual(found['result']['body_send_calls'], 1)
        self.assertTrue(any(e.get('proxy_present') for e in found['result']['events']))
        self.assertIn('https', found['proxies'])

    def test_suppressed_errors_remain_observed_with_200(self):
        for code in (errno.EPIPE, errno.ECONNRESET, errno.EPROTOTYPE):
            with self.subTest(code=code):
                found = self.run_request(code=code)
                self.assertEqual(found['status'], 200)
                self.assertFalse(found['result']['local_body_send_completed'])
                self.assertTrue(found['result']['write_failure_observed'])
                events = [e for e in found['result']['events'] if e['event'] == 'body_send_exception']
                self.assertTrue(events[0]['accepted_bytes_unknown'])

    def test_partial_write_is_unknown_and_not_counted_as_completed(self):
        found = self.run_request(code=errno.EPIPE, partial=11)
        self.assertEqual(found['status'], 200)
        self.assertEqual(len(found['socket'].accepted[-1]), 11)
        self.assertFalse(found['result']['local_body_send_completed'])
        self.assertFalse(any(e.get('local_bytes_send_returned') for e in found['result']['events']))

    def test_header_error_before_body_is_retained(self):
        found = self.run_request(code=errno.EPIPE, location='headers')
        self.assertEqual(found['status'], 200)
        self.assertEqual(found['result']['body_send_calls'], 0)
        self.assertTrue(found['result']['write_failure_observed'])

    def test_nonsuppressed_error_preserves_connectionerror(self):
        found = self.run_request(code=errno.EIO)
        self.assertEqual(found['exception'], 'ConnectionError')
        self.assertTrue(found['result']['write_failure_observed'])

    def test_connect_failure_restores_hooks_without_body_claim(self):
        found = self.run_request(code=errno.ECONNRESET, location='connect', proxy=True)
        self.assertEqual(found['exception'], 'ProxyError')
        self.assertEqual(found['result']['connection_requests'], 0)
        self.assertFalse(found['result']['local_body_send_completed'])

    def test_transfer_encoding_rejected_before_connection(self):
        found = self.run_request(alter_headers={'Transfer-Encoding': 'chunked'})
        self.assertEqual(found['exception'], 'ObservationHeld')
        self.assertEqual(found['socket'].calls, [])

    def test_unsupported_connection_replenishes_pool(self):
        found = self.run_request(unsupported=True)
        self.assertEqual(found['exception'], 'ObservationHeld')
        self.assertEqual(found['socket'].calls, [])

    def test_receipt_failure_after_checkout_replenishes_pool(self):
        def fail(receipt):
            if receipt['events'][-1]['event'] == 'original_connection_observed':
                raise OSError(errno.EPIPE, 'fixture-only')
        found = self.run_request(persist=fail)
        self.assertEqual(found['exception'], 'ObservationHeld')
        self.assertEqual(found['socket'].calls, [])
        self.assertEqual(found['pools'][0].pool.qsize(), 10)

    def test_reentrant_and_foreign_thread_rejected_without_send(self):
        with requests.Session() as session:
            with observer.observe_one_put(session, BODY, '7', lambda _: None) as result:
                with self.assertRaises(observer.ObservationHeld):
                    with observer.observe_one_put(session, BODY, '7', lambda _: None):
                        pass
                errors = []
                prepared = requests.Request('PUT', observer.URL, data=BODY).prepare()
                def foreign():
                    try:
                        session.send(prepared)
                    except observer.ObservationHeld:
                        errors.append(True)
                worker = threading.Thread(target=foreign)
                worker.start()
                worker.join(2)
                self.assertEqual(errors, [True])
                self.assertEqual(result['session_send_calls'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
