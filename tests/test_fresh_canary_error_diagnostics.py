"""Mocked diagnostic retention never creates another allowance or stores bodies."""
import json
import base64
import html
import unittest
from urllib.parse import quote

import requests
from scripts import synthetic_fresh_canary as f


class FreshErrorDiagnosticTests(unittest.TestCase):
    token = 'offline-secret-with-quotation-"-slash-\\'

    def project(self, body, status=500, headers=None):
        response = requests.Response()
        response.status_code = status
        response.headers.update(headers or {'Content-Type': 'application/json'})
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        return f.response_projection(raw, response, 'POST', self.token)

    def test_json_human_message_and_request_identifier_are_retained(self):
        response = requests.Response()
        response.status_code = 500
        response.headers['Content-Type'] = 'application/json'
        response.headers['X-Request-ID'] = 'a1b2c3d4-1234-4567-89ab-0123456789ab'
        raw = json.dumps({'message': 'The account email must be confirmed before uploading.', 'status': 500}).encode()
        result = f.response_projection(raw, response, 'POST', 'offline-diagnostic-token')
        self.assertEqual(result['error_message'], 'The account email must be confirmed before uploading.')
        self.assertEqual(result['error_status'], 500)
        self.assertEqual(result['trace_identifiers']['x-request-id'], response.headers['X-Request-ID'])

    def test_credentials_urls_personal_fields_and_appended_private_payloads_are_redacted(self):
        variants = (self.token, quote(self.token, safe=''), html.escape(self.token),
                    base64.b64encode(self.token.encode()).decode())
        for value in variants:
            with self.subTest(value=value):
                result = self.project({'message': 'Internal server error: ' + value + '; confirmation is required.',
                                       'owner': 987654321, 'secret': value,
                                       'errors': [{'private_record': 'UNRELATED-PRIVATE-PAYLOAD'}]},
                                      headers={'Set-Cookie': self.token, 'Authorization': 'Bearer ' + self.token,
                                               'X-Secret': self.token, 'Content-Type': 'application/json'})
                text = json.dumps(result)
                self.assertIn('Internal server error:', result['error_message'])
                self.assertIn('confirmation is required.', result['error_message'])
                self.assertTrue(result['error_message_redacted'])
                for secret in (self.token, value, '987654321', 'UNRELATED-PRIVATE-PAYLOAD', 'Set-Cookie', 'X-Secret'):
                    self.assertNotIn(secret, text)
        result = self.project({'message': 'Request failed for user@example.test at https://private.test/a?access_token=secret; owner=987654321; path=/private/run/token; name=Alice Smith; payload {"private": "data"}'})
        text = json.dumps(result)
        for secret in ('user@example.test', 'private.test', '987654321', '/private/run/token', 'Alice', 'Smith', '"data"'):
            self.assertNotIn(secret, text)

    def test_html_keeps_only_redacted_title_or_heading_and_messages_are_bounded(self):
        result = self.project(('<html><title>Permission required for ' + html.escape(self.token) + '</title>'
            '<body>PRIVATE-OWNER-BODY 987654321</body></html>').encode(),
            headers={'Content-Type': 'text/html'})
        self.assertEqual(result['error_message_source'], 'html.title')
        self.assertIn('Permission required', result['error_message'])
        for private in (self.token, 'PRIVATE-OWNER-BODY', '987654321'):
            self.assertNotIn(private, json.dumps(result))
        heading = self.project(b'<h1>Service unavailable</h1><p>PRIVATE-BODY</p>', headers={'Content-Type': 'text/html'})
        self.assertEqual(heading['error_message'], 'Service unavailable')
        self.assertNotIn('PRIVATE-BODY', json.dumps(heading))
        plain = self.project(b'PRIVATE-RAW-BODY', headers={'Content-Type': 'text/plain'})
        self.assertNotIn('error_message', plain)
        nested = self.project({'message': {'private': 'PRIVATE-NESTED-BODY'}, 'status': 987654321})
        self.assertNotIn('error_message', nested)
        self.assertNotIn('error_status', nested)
        result = self.project({'message': ('A short diagnostic sentence. ' * 80) + self.token})
        self.assertEqual(len(result['error_message']), 512)
        self.assertTrue(result['error_message_truncated'])
        self.assertNotIn(self.token, json.dumps(result))
        success = self.project({'message': 'PRIVATE-SUCCESS-MESSAGE'}, status=200,
                               headers={'X-Request-ID': '0' * 32})
        self.assertNotIn('error_message', success)
        self.assertNotIn('trace_identifiers', success)

    def test_trace_header_allowlist_formats_and_credential_echoes_are_enforced(self):
        valid = {'X-Request-ID': 'a' * 32, 'X-Correlation-ID': 'a1b2c3d4-1234-4567-89ab-0123456789ab',
                 'X-Trace-ID': 'b' * 16, 'Traceparent': '00-' + 'a' * 32 + '-' + 'b' * 16 + '-01',
                 'Sentry-Trace': 'a' * 32 + '-' + 'b' * 16 + '-1',
                 'X-Amzn-Trace-Id': 'Root=1-12345678-' + 'a' * 24 + ';Parent=' + 'b' * 16 + ';Sampled=1',
                 'CF-Ray': 'a' * 16 + '-AMS', 'Location': 'https://private.test/' + self.token,
                 'Set-Cookie': self.token, 'X-Other': 'PRIVATE-OTHER-HEADER'}
        result = self.project({'message': 'Server error'}, headers=valid)
        self.assertEqual(set(result['trace_identifiers']), set(f.TRACE_HEADERS))
        self.assertNotIn('private.test', json.dumps(result))
        self.assertNotIn('PRIVATE-OTHER-HEADER', json.dumps(result))
        for value in (self.token, quote(self.token, safe=''), 'user@example.test', 'https://private.test',
                      'a' * 129, 'a' * 32 + '\r\nPRIVATE-INJECTION'):
            result = self.project({'message': 'Server error'}, headers={'X-Request-ID': value})
            self.assertEqual(result['trace_identifiers'], {})
        token = 'a' * 32
        response = requests.Response(); response.status_code = 500; response.headers['X-Request-ID'] = token
        result = f.response_projection(b'{"message":"Error"}', response, 'POST', token)
        self.assertEqual(result['trace_identifiers'], {})

    def test_persisted_failed_transaction_keeps_diagnostics_without_any_retry(self):
        import test_synthetic_fresh_canary as fixture
        obj = fixture.FreshCanaryTests('test_complete_new_identity_exact_readback_unchanged_retry_and_cached_rerun')
        obj.setUp()
        try:
            original_transport = obj.transport
            def transport(session, request, **kwargs):
                if request.method != 'POST':
                    return original_transport(session, request, **kwargs)
                obj.mutation = 'json500'
                response = original_transport(session, request, **kwargs)
                response._content = json.dumps({'message': 'Account confirmation is required; token=' + fixture.TOKEN,
                    'status': 500, 'owner': 987654321, 'secret': fixture.TOKEN}).encode()
                response.headers['X-Request-ID'] = 'a1b2c3d4-1234-4567-89ab-0123456789ab'
                return response
            obj.transport = transport
            result = obj.execute()
            self.assertTrue(result['failed'])
            self.assertEqual(result['counts']['create'], 1)
            self.assertFalse(any(method == 'PUT' for method, _ in obj.calls))
            saved = fixture.read_json(obj.folder / f.EVIDENCE)
            last = saved['responses'][-1]
            self.assertIn('Account confirmation is required', last['error_message'])
            self.assertEqual(last['error_status'], 500)
            self.assertIn('x-request-id', last['trace_identifiers'])
            for private in (fixture.TOKEN, '987654321'):
                self.assertNotIn(private, json.dumps([result, saved]))
            before = {p: p.read_bytes() for p in obj.folder.iterdir() if p.is_file()}
            count = len(obj.calls)
            with self.assertRaises(f.c.ZenodoAPIError):
                obj.execute()
            self.assertEqual(len(obj.calls), count)
            self.assertEqual({p: p.read_bytes() for p in before}, before)
            self.assertEqual({p: p.read_bytes() for p in obj.old.iterdir()}, obj.old_bytes)
        finally:
            obj.doCleanups()

    def test_partial_error_body_still_retains_only_safe_available_evidence(self):
        import test_synthetic_fresh_canary as fixture
        obj = fixture.FreshCanaryTests('test_complete_new_identity_exact_readback_unchanged_retry_and_cached_rerun')
        obj.setUp()
        try:
            original_transport = obj.transport
            def transport(session, request, **kwargs):
                response = original_transport(session, request, **kwargs)
                if request.method == 'POST':
                    response.status_code = 500
                    response.headers['X-Request-ID'] = 'a' * 32
                    response.headers['Content-Type'] = 'text/html'
                    response._content = (b'<title>Service unavailable</title>' + b'x' * 70000)
                return response
            obj.transport = transport
            result = obj.execute()
            self.assertTrue(result['failed'])
            last = fixture.read_json(obj.folder / f.EVIDENCE)['responses'][-1]
            self.assertFalse(last['body_complete'])
            self.assertEqual(last['error_message'], 'Service unavailable')
            self.assertEqual(last['trace_identifiers'], {'x-request-id': 'a' * 32})
            self.assertEqual(result['counts']['create'], 1)
        finally:
            obj.doCleanups()
