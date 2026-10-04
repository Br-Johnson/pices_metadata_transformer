"""Offline tests only: fake responses, no sessions, environment tokens or sockets."""
import base64
import hashlib
import html
import json
import unittest
from urllib.parse import quote

from response_capture import capture_response


TOKEN = 'offline-DUMMY-token-A+/&=42'


class FakeResponse:
    def __init__(self, raw, status=200, headers=None, chunks=None, failure=None):
        self.status_code = status
        self.headers = headers or {
            'Content-Type': 'application/vnd.inveniordm.v1+json',
            'Content-Length': str(len(raw)),
        }
        self.chunks = chunks if chunks is not None else [raw]
        self.failure = failure
        self.iter_calls = 0
        self.url = 'https://must-not-persist.example/private?token=' + TOKEN

    def iter_content(self, chunk_size):
        self.iter_calls += 1
        yield from self.chunks
        if self.failure:
            raise self.failure

    def json(self):
        raise AssertionError('Capture must not read via response.json()')


class CaptureTests(unittest.TestCase):
    def capture(self, payload, **kwargs):
        raw = json.dumps(payload, ensure_ascii=False).encode()
        response = FakeResponse(raw, **kwargs)
        return response, capture_response(response, TOKEN), raw

    def test_full_json_and_error_statuses_have_same_capture(self):
        payload = {'metadata': {'title': 'A fictional record', 'subjects': [{'subject': 'Ocean'}]},
                   'revision_id': 3, 'errors': [{'field': 'metadata.publisher',
                                              'messages': ['Missing data for required field.']}]}
        for status in [200, 400, 412]:
            with self.subTest(status=status):
                response, result, raw = self.capture(payload, status=status)
                self.assertEqual(response.iter_calls, 1)
                self.assertEqual(result.data, payload)
                self.assertEqual(result.artifact['snapshot'], payload)
                self.assertTrue(result.artifact['body_complete'])
                self.assertTrue(result.artifact['snapshot_available'])
                self.assertEqual(result.artifact['body_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(result.artifact['status'], status)
                self.assertTrue(result.artifact['read_started_utc'].endswith('Z'))
                self.assertLessEqual(result.artifact['read_started_utc'], result.artifact['read_finished_utc'])

    def test_headers_have_explicit_allowlist_and_value_validation(self):
        headers = {'Content-Type': 'application/json', 'Content-Length': '2',
                   'ETag': '"3"', 'Date': 'Sun, 04 Oct 2026 12:00:00 GMT',
                   'X-Revision-Id': '3', 'X-Revision': '3', 'Revision': '3',
                   'Set-Cookie': 'unknown-private-cookie', 'Location': 'https://private.example',
                   'X-Arbitrary': 'private', 'Authorization': TOKEN}
        result = capture_response(FakeResponse(b'{}', headers=headers), TOKEN)
        self.assertEqual(set(result.artifact['headers']),
                         {'Content-Type', 'Content-Length', 'ETag', 'Date',
                          'X-Revision-Id', 'X-Revision', 'Revision'})
        encoded = json.dumps(result.artifact)
        for sensitive in [TOKEN, 'unknown-private-cookie', 'https://private.example',
                          'must-not-persist', 'X-Arbitrary']:
            self.assertNotIn(sensitive, encoded)
        headers['ETag'] = '"' + TOKEN + '"'
        result = capture_response(FakeResponse(b'{}', headers=headers), TOKEN)
        self.assertNotIn('ETag', result.artifact['headers'])
        self.assertTrue(result.artifact['allowlisted_header_suppressed'])

    def test_conventional_credentials_and_urls_cannot_hide_in_etag(self):
        for etag in ['"password:OFFLINE_OTHER_SECRET"', '"mailto:private"',
                     '"client_secret:OFFLINE_OTHER_SECRET"', '"pwd:OTHER"']:
            with self.subTest(etag=etag):
                response = FakeResponse(b'{}', headers={'Content-Type': 'application/json',
                                                       'Content-Length': '2', 'ETag': etag})
                result = capture_response(response, TOKEN)
                self.assertNotIn('ETag', result.artifact['headers'])
                self.assertTrue(result.artifact['allowlisted_header_suppressed'])

    def test_existing_safe_trace_projection_available_for_success_and_errors(self):
        identifier = '0123456789abcdef0123456789abcdef'
        for status in [200, 400, 412]:
            response = FakeResponse(b'{}', status=status, headers={
                'Content-Type': 'application/json', 'Content-Length': '2',
                'x-request-id': identifier, 'x-correlation-id': TOKEN,
                'x-trace-id': 'https://private.example/trace',
            })
            result = capture_response(response, TOKEN)
            self.assertEqual(result.artifact['trace_identifiers'], {'x-request-id': identifier})
            self.assertNotIn(TOKEN, json.dumps(result.artifact))

    def test_textual_assignments_cover_conventional_keys(self):
        for key in ['client_secret', 'id_token', 'pwd', 'session_token', 'x-auth-token',
                    'api key', 'aws_secret_access_key', 'new-password']:
            with self.subTest(key=key):
                _, result, _ = self.capture({'message': f'Error: {key}=OFFLINE_OTHER_SECRET',
                                            'x-auth-token': 'OTHER_AUTH'})
                self.assertTrue(result.artifact['snapshot_available'])
                self.assertNotIn('OFFLINE_OTHER_SECRET', json.dumps(result.artifact))
                self.assertNotIn('OTHER_AUTH', json.dumps(result.artifact))
                self.assertIsNone(result.artifact['body_sha256'])

    def test_recursive_known_token_variants_and_original_data_separation(self):
        variants = [TOKEN, quote(TOKEN, safe=''), html.escape(TOKEN),
                    base64.b64encode(TOKEN.encode()).decode(),
                    base64.urlsafe_b64encode(TOKEN.encode()).decode().rstrip('=')]
        payload = {'nested': [{'message': v} for v in variants], TOKEN: 'key-value'}
        _, result, _ = self.capture(payload)
        self.assertEqual(result.data, payload)
        self.assertTrue(result.artifact['snapshot_available'])
        self.assertTrue(result.artifact['credential_echo_detected'])
        self.assertIsNone(result.artifact['body_sha256'])
        encoded = json.dumps(result.artifact)
        for variant in variants:
            self.assertNotIn(variant, encoded)
        self.assertNotIn(TOKEN, repr(result))

    def test_escaped_json_and_nested_percent_encoding(self):
        escaped = ''.join('\\u%04x' % ord(char) for char in TOKEN)
        raw = ('{"value":"' + escaped + '"}').encode()
        result = capture_response(FakeResponse(raw), TOKEN)
        self.assertTrue(result.artifact['credential_echo_detected'])
        self.assertEqual(result.artifact['snapshot']['value'], '[REDACTED_CREDENTIAL]')
        _, nested, _ = self.capture({'value': quote(quote(TOKEN, safe=''), safe='')})
        self.assertTrue(nested.artifact['snapshot_available'])
        self.assertEqual(nested.artifact['snapshot']['value'], '[REDACTED_CREDENTIAL]')
        self.assertIsNone(nested.artifact['body_sha256'])

    def test_unknown_credentials_urls_and_body_headers_are_redacted(self):
        payload = {'metadata': {'title': 'Keep this title'}, 'access_token': 'OTHER-SECRET',
                   'nested': {'api-key': 'UNKNOWN-API-KEY', 'password': 'UNKNOWN-PASS',
                              'x-api-key': 'UNKNOWN-X-KEY', 'auth_token': 'UNKNOWN-AUTH'},
                   'messages': ['Bearer ANOTHER-SECRET', 'password=HIDDEN',
                                'See https://private.example/path?key=UNKNOWN',
                                'mailto:private@example.test'],
                   'headers': {'X-Custom': 'UNKNOWN-HEADER'},
                   'links': {'self': 'https://private.example/record/42',
                             'draft': '/api/records/private-draft',
                             'escaped': 'https:\\/\\/private.example/escaped'}}
        _, result, _ = self.capture(payload)
        self.assertEqual(result.data, payload)
        self.assertTrue(result.artifact['snapshot_available'])
        self.assertEqual(result.artifact['snapshot']['metadata'], payload['metadata'])
        self.assertIsNone(result.artifact['body_sha256'])
        encoded = json.dumps(result.artifact)
        for hidden in ['OTHER-SECRET', 'UNKNOWN-API-KEY', 'UNKNOWN-PASS', 'ANOTHER-SECRET',
                       'HIDDEN', 'private.example', 'private@example.test', 'UNKNOWN-HEADER',
                       'UNKNOWN-X-KEY', 'UNKNOWN-AUTH', 'private-draft']:
            self.assertNotIn(hidden, encoded)

    def test_maximum_size_complete_versus_truncated(self):
        raw = b'{"x":"' + b'x' * (65536 - 8) + b'"}'
        self.assertEqual(len(raw), 65536)
        result = capture_response(FakeResponse(raw, chunks=[raw[:32000], raw[32000:]]), TOKEN)
        self.assertTrue(result.artifact['body_complete'])
        self.assertTrue(result.artifact['snapshot_available'])
        self.assertIsNone(result.artifact['hold_reason'])
        oversized = raw + b' '
        response = FakeResponse(oversized, chunks=[oversized])
        result = capture_response(response, TOKEN)
        self.assertEqual(response.iter_calls, 1)
        self.assertFalse(result.artifact['body_complete'])
        self.assertEqual(result.artifact['captured_bytes'], 65536)
        self.assertEqual(result.artifact['hold_reason'], 'body_size_limit')
        self.assertIsNone(result.data)
        self.assertIsNone(result.artifact['snapshot'])
        self.assertIsNone(result.artifact['body_sha256'])

    def test_redaction_expansion_cannot_exceed_snapshot_bound(self):
        raw = json.dumps({'x': ['password=a'] * 4600}, separators=(',', ':')).encode()
        self.assertLess(len(raw), 65536)
        result = capture_response(FakeResponse(raw), TOKEN)
        self.assertTrue(result.artifact['body_complete'])
        self.assertEqual(result.artifact['hold_reason'], 'sanitized_snapshot_limit')
        self.assertIsNone(result.artifact['snapshot'])
        self.assertIsNone(result.artifact['body_sha256'])

    def test_stream_failure_even_after_valid_prefix_withholds_snapshot(self):
        response = FakeResponse(b'{}', chunks=[b'{}'],
                                failure=RuntimeError('secret ' + TOKEN + ' https://private.example'))
        result = capture_response(response, TOKEN)
        self.assertEqual(response.iter_calls, 1)
        self.assertEqual(result.artifact['hold_reason'], 'body_read_error')
        self.assertFalse(result.artifact['body_complete'])
        self.assertIsNone(result.data)
        self.assertNotIn(TOKEN, json.dumps(result.artifact))
        self.assertNotIn('private.example', json.dumps(result.artifact))

    def test_unsupported_and_ambiguous_json_hold_full_snapshot(self):
        cases = [(b'<html>private</html>', 'text/html', 'unsupported_content_type'),
                 (b'{"x":', 'application/json', 'invalid_json'),
                 (b'[]', 'application/json', 'unsupported_json_root'),
                 (b'{"x":1,"x":2}', 'application/json', 'duplicate_json_key'),
                 (b'{"x":NaN}', 'application/json', 'nonfinite_json_number'),
                 (b'{"x":"\\\\u0041"}', 'application/json', 'uncertain_string_encoding')]
        for raw, mime, reason in cases:
            with self.subTest(reason=reason):
                response = FakeResponse(raw, headers={'Content-Type': mime, 'Content-Length': str(len(raw))})
                result = capture_response(response, TOKEN)
                self.assertTrue(result.artifact['body_complete'])
                self.assertFalse(result.artifact['snapshot_available'])
                self.assertIsNone(result.artifact['snapshot'])
                self.assertEqual(result.artifact['hold_reason'], reason)

    def test_uncertain_deep_encoding_and_redacted_key_collision_hold(self):
        value = TOKEN
        for _ in range(12):
            value = quote(value, safe='')
        _, result, _ = self.capture({'x': value})
        self.assertEqual(result.artifact['hold_reason'], 'uncertain_string_encoding')
        _, result, _ = self.capture({TOKEN: 'secret-key', '[REDACTED_KEY_0]': 'collision'})
        self.assertEqual(result.artifact['hold_reason'], 'redacted_key_collision')
        self.assertIsNone(result.artifact['snapshot'])

    def test_content_length_and_nonbytes_errors_hold(self):
        response = FakeResponse(b'{}', headers={'Content-Type': 'application/json', 'Content-Length': '4'})
        result = capture_response(response, TOKEN)
        self.assertEqual(result.artifact['hold_reason'], 'content_length_mismatch')
        self.assertFalse(result.artifact['body_complete'])
        response = FakeResponse(b'{}', chunks=['not bytes'])
        result = capture_response(response, TOKEN)
        self.assertEqual(result.artifact['hold_reason'], 'unsupported_stream_chunk')

    def test_malformed_length_unknown_encoding_and_conflicting_framing_hold(self):
        cases = [({'Content-Length': '4, 999'}, 'invalid_content_length'),
                 ({'Content-Length': '4', 'Content-Encoding': 'x-unsupported-private'},
                  'unsupported_content_encoding'),
                 ({'Content-Length': '2', 'Transfer-Encoding': 'chunked'},
                  'conflicting_response_framing'),
                 ({'Transfer-Encoding': 'private-coding'}, 'unsupported_transfer_encoding')]
        for extra, reason in cases:
            with self.subTest(reason=reason):
                response = FakeResponse(b'{}', headers={'Content-Type': 'application/json', **extra})
                result = capture_response(response, TOKEN)
                self.assertTrue(result.artifact['iterator_exhausted'])
                self.assertFalse(result.artifact['body_complete'])
                self.assertFalse(result.artifact['snapshot_available'])
                self.assertEqual(result.artifact['hold_reason'], reason)
                self.assertNotIn('private', json.dumps(result.artifact['headers']))

    def test_absent_length_is_explicitly_unverified(self):
        response = FakeResponse(b'{}', headers={'Content-Type': 'application/json',
                                               'Transfer-Encoding': 'chunked'})
        result = capture_response(response, TOKEN)
        self.assertTrue(result.artifact['body_complete'])
        self.assertTrue(result.artifact['iterator_exhausted'])
        self.assertEqual(result.artifact['transfer_encoding'], 'chunked')
        self.assertEqual(result.artifact['content_length_check'], 'unavailable_no_content_length')

    def test_identity_length_check_is_not_applied_to_decoded_gzip(self):
        response = FakeResponse(b'{}', headers={'Content-Type': 'application/json',
                                               'Content-Length': '22', 'Content-Encoding': 'gzip'})
        result = capture_response(response, TOKEN)
        self.assertTrue(result.artifact['snapshot_available'])
        self.assertEqual(result.artifact['captured_bytes'], 2)
        self.assertEqual(result.artifact['content_length_check'], 'unavailable_decoded_encoding')
        self.assertEqual(result.artifact['content_encoding'], 'gzip')

    def test_invalid_input_rejected_before_stream_consumption(self):
        response = FakeResponse(b'{}')
        for token in ['', 'has space', '\N{SNOWMAN}']:
            with self.assertRaises(ValueError):
                capture_response(response, token)
        for limit in [0, 65537, True]:
            with self.assertRaises(ValueError):
                capture_response(response, TOKEN, max_body_bytes=limit)
        self.assertEqual(response.iter_calls, 0)


if __name__ == '__main__':
    unittest.main()
