"""Independent adversarial tests for bounded response diagnostics.

Synthetic sources, grants and transports only. Complete safe bodies have bounded
sidecars; incomplete/credential-bearing bytes have no retained body or full hash.
Diagnostics never reopen spent creates, authorize identities, or follow redirects.
All fixtures run only under the repository offline guard.
"""

import base64
import dataclasses
import http.client
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import quote

from scripts import modern_response_evidence as evidence_contract
from scripts import modern_singleton_executor as draft
from scripts.modern_singleton import encode, parse, sha
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_publication as publication_tests

# This token intentionally makes URL/base64 variants distinct.
TOKEN = 'dummy-response-only+/?token-419!'


def encoded_echoes(token):
    raw = token.encode()
    standard = base64.b64encode(raw).decode()
    urlsafe = base64.urlsafe_b64encode(raw).decode()
    return {
        'literal': token,
        'url': quote(token, safe=''),
        'all_percent': ''.join('%' + format(byte, '02x') for byte in raw),
        'nested_percent': quote(''.join('%' + format(byte, '02x') for byte in raw), safe=''),
        'json_unicode': ''.join('\\u' + format(ord(char), '04x') for char in token),
        'base64': standard,
        'base64_unpadded': standard.rstrip('='),
        'urlsafe_base64': urlsafe,
        'urlsafe_base64_unpadded': urlsafe.rstrip('='),
        'html_entities': ''.join('&#' + str(ord(char)) + ';' for char in token),
        'html_hex_entities': ''.join('&#x' + format(ord(char), 'x') + ';' for char in token),
    }


class StaticTransport:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def request(self, method, path, body, *, timeout, **kwargs):
        self.calls.append((method, path, body, timeout, kwargs))
        if self.error is not None:
            raise self.error
        return self.response


class ModernResponseEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=['FGDC-141'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index = 0

    def make(self, response=None, error=None, token=TOKEN):
        self.index += 1
        fixture = fixtures.Fixture(Path(self.temp.name) / str(self.index), self.prepared_root)
        transport = StaticTransport(response, error)
        runner = draft.Runner(fixture.json_file, fixture.paths, fixture.grant_path,
                              fixture.proof_path, token, transport=transport, now=lambda: fixtures.NOW)
        return fixture, runner, transport

    def read(self, runner):
        row = parse(runner.journal_path.read_bytes())['targets']['FGDC-141']
        self.assertEqual(len(row['requests']), 1)
        self.assertEqual(row['counts'], dict.fromkeys(draft.LIMITS, 0) | {'create': 1})
        self.assertIsNone(row['identity'])
        self.assertEqual(row['phase'], 'started')
        self.assertTrue(runner.intent_path.is_file())
        return row, row['requests'][0]

    def assert_held(self, runner, transport):
        with self.assertRaises(ValueError):
            runner.run()
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0][:2], ('POST', '/api/records'))
        return self.read(runner)

    def evidence(self, runner, receipt):
        pointer = receipt['response_evidence']
        self.assertEqual(set(pointer), {'filename', 'sha256'})
        self.assertEqual(Path(pointer['filename']).name, pointer['filename'])
        path = runner.journal_path.parent / pointer['filename']
        self.assertFalse(path.is_symlink())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        raw = path.read_bytes()
        self.assertEqual(sha(raw), pointer['sha256'])
        evidence = parse(raw)
        self.assertEqual(evidence['source_id'], 'FGDC-141')
        self.assertEqual(evidence['grant_sha256'], runner.grant_sha)
        self.assertEqual(evidence['request'], {k: v for k, v in receipt.items() if k != 'response_evidence'})
        return evidence

    def assert_not_retained(self, runner, value):
        texts = [runner.journal_path.read_text()]
        texts.extend(path.read_text() for path in runner.journal_path.parent.glob('*.response.json'))
        self.assertNotIn(value, ''.join(texts))

    def assert_safe_payload(self, runner, receipt, raw, *, mime, location=None):
        evidence = self.evidence(runner, receipt)
        self.assertEqual(evidence['schema_version'], 1)
        self.assertEqual(evidence['content_type'], mime)
        self.assertEqual(evidence['location'], location)
        self.assertTrue(evidence['response_complete'])
        self.assertIsNone(evidence['read_error'])
        self.assertFalse(evidence['credential_suppressed'])
        retained = base64.b64decode(evidence['body_base64'], validate=True)
        self.assertEqual(retained, raw[:evidence_contract.MAX_DIAGNOSTIC_BYTES])
        self.assertEqual(evidence['retained_bytes'], len(retained))
        self.assertEqual(evidence['body_status'], 'prefix' if len(raw) > evidence_contract.MAX_DIAGNOSTIC_BYTES else 'complete')
        self.assertEqual(evidence['retained_sha256'], sha(retained))
        self.assertEqual(receipt['response_sha256'], sha(raw))
        # Assert persisted-on-disk evidence, not merely an in-memory result.
        self.assertEqual(self.evidence(runner, self.read(runner)[1]), evidence)

    def test_first_create403_html_preserved_before_status_and_mime_rejection(self):
        raw = b'<!doctype html><title>Forbidden</title><p>Diagnostic fixture A403.</p>'
        fixture, runner, transport = self.make(evidence_contract.Response(403, 'text/html; charset=utf-8', raw))
        _, receipt = self.assert_held(runner, transport)
        self.assertEqual(receipt['http_status'], 403)
        self.assert_safe_payload(runner, receipt, raw, mime='text/html; charset=utf-8')
        with self.assertRaises(ValueError):
            runner.run()
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(sha(fixture.prepared.xml), fixture.prepared.evidence['source_sha256'])

    def test_redirect_preserves_safe_location_and_never_follows_it(self):
        for status in (301, 302, 303, 307, 308):
            with self.subTest(status=status):
                location = 'https://example.invalid/diagnostic-only'
                raw = b'<html>Moved</html>'
                _, runner, transport = self.make(evidence_contract.Response(status, 'text/html', raw, location=location))
                _, receipt = self.assert_held(runner, transport)
                self.assertEqual(receipt['http_status'], status)
                self.assert_safe_payload(runner, receipt, raw, mime='text/html', location=location)
                self.assertEqual(len(transport.calls), 1)

    def test_safe_json_and_nonutf8_rejections_are_retained_exactly(self):
        cases = ((400, draft.MIME, b'{"message":"validation fixture","errors":[{"field":"title"}]}'),
                 (403, 'text/html', b'\xff\xfe\x00\x80forbidden-fixture'),
                 (201, draft.MIME, b'{"id":"1","id":"2"}'),
                 (201, draft.MIME, b'{broken-json'))
        for status, mime, raw in cases:
            with self.subTest(status=status, raw=raw):
                _, runner, transport = self.make(evidence_contract.Response(status, mime, raw))
                _, receipt = self.assert_held(runner, transport)
                self.assert_safe_payload(runner, receipt, raw, mime=mime)

    def test_diagnostic_prefix_has_own_hash_and_full_body_hash_is_distinct(self):
        raw = b'Fixture prefix.' + b'x' * evidence_contract.MAX_DIAGNOSTIC_BYTES + b'Full response suffix.'
        self.assertLess(len(raw), draft.MAX_BYTES)
        _, runner, transport = self.make(evidence_contract.Response(403, 'text/plain', raw))
        _, receipt = self.assert_held(runner, transport)
        self.assert_safe_payload(runner, receipt, raw, mime='text/plain')
        self.assertNotEqual(receipt['response_sha256'], self.evidence(runner, receipt)['retained_sha256'])

    def test_secret_after_diagnostic_cap_suppresses_whole_response_before_hash(self):
        raw = b'ordinary fixture' + b'x' * evidence_contract.MAX_DIAGNOSTIC_BYTES + TOKEN.encode()
        _, runner, transport = self.make(evidence_contract.Response(403, 'text/plain', raw))
        _, receipt = self.assert_held(runner, transport)
        self.assertTrue(receipt['credential_suppressed'])
        self.assertIsNone(receipt['response_sha256'])
        self.assertEqual(self.evidence(runner, receipt)['body_base64'], '')
        self.assertIsNone(self.evidence(runner, receipt)['retained_sha256'])
        self.assert_not_retained(runner, TOKEN)

    def test_token_spellings_in_body_are_not_persisted_or_hashed(self):
        for mode, value in encoded_echoes(TOKEN).items():
            with self.subTest(mode=mode):
                # json_unicode must stay escaped in the actual JSON body.
                raw = ('{"message":"' + value + '"}').encode()
                _, runner, transport = self.make(evidence_contract.Response(403, 'application/json', raw))
                with self.assertRaises(ValueError) as caught:
                    runner.run()
                _, receipt = self.read(runner)
                self.assertEqual(len(transport.calls), 1)
                self.assertTrue(receipt['credential_suppressed'])
                self.assertIsNone(receipt['response_sha256'])
                evidence = self.evidence(runner, receipt)
                self.assertTrue(evidence['credential_suppressed'])
                self.assertEqual(evidence['body_base64'], '')
                self.assertIsNone(evidence['retained_sha256'])
                stored = runner.journal_path.read_text() + str(caught.exception)
                self.assertNotIn(TOKEN, stored)
                self.assertNotIn(value, stored)
                self.assertNotIn(sha(raw), stored)
                self.assert_not_retained(runner, value)
                self.assert_not_retained(runner, sha(raw))

    def test_token_in_mime_or_location_is_suppressed_without_persisting_header(self):
        for field in ('mime', 'location'):
            for mode, value in encoded_echoes(TOKEN).items():
                with self.subTest(field=field, mode=mode):
                    values = dict(mime='text/html', location='https://example.invalid/diagnostic')
                    values[field] = value
                    _, runner, transport = self.make(evidence_contract.Response(403, values['mime'], b'Forbidden',
                                                                   location=values['location']))
                    _, receipt = self.assert_held(runner, transport)
                    self.assertTrue(receipt['credential_suppressed'])
                    self.assertIsNone(self.evidence(runner, receipt)['content_type' if field == 'mime' else field])
                    self.assert_not_retained(runner, value)

    def test_location_credential_surfaces_not_copied_to_evidence(self):
        unrelated = 'dummy-unrelated-secret-888'
        values = ('https://user:' + unrelated + '@example.invalid/path',
                  'https://example.invalid/path?access_token=' + unrelated,
                  'https://example.invalid/path#token=' + unrelated,
                  'https://example.invalid/path?X-Amz-Signature=' + unrelated)
        for location in values:
            with self.subTest(location=location):
                _, runner, transport = self.make(evidence_contract.Response(302, 'text/html', b'Moved', location=location))
                _, receipt = self.assert_held(runner, transport)
                self.assert_not_retained(runner, unrelated)
                stored = self.evidence(runner, receipt)['location']
                self.assertTrue(stored is None or stored == 'https://example.invalid/path')

    def test_header_control_characters_or_excess_length_never_enter_journal(self):
        values = ('text/html\r\nAuthorization: dummy-other-secret',
                  'text/html\x00unsafe', 'x' * (evidence_contract.MAX_DIAGNOSTIC_BYTES + 1))
        for value in values:
            with self.subTest(length=len(value)):
                _, runner, transport = self.make(evidence_contract.Response(403, value, b'Forbidden', location=value))
                _, receipt = self.assert_held(runner, transport)
                self.assertIsNone(self.evidence(runner, receipt)['content_type'])
                self.assertIsNone(self.evidence(runner, receipt)['location'])
                self.assert_not_retained(runner, value)

    def test_incomplete_even_valid_create_json_cannot_authorize_identity_or_init(self):
        fixture, runner, transport = self.make()
        raw = encode(fixture.transport.record())
        transport.response = evidence_contract.Response(201, draft.MIME, raw, complete=False, read_error='incomplete_body')
        _, receipt = self.assert_held(runner, transport)
        self.assertFalse(self.evidence(runner, receipt)['response_complete'])
        self.assertEqual(self.evidence(runner, receipt)['read_error'], 'incomplete_body')
        self.assertIsNone(receipt['response_sha256'])
        self.assertNotIn('untrusted_candidate_id', runner.row)

    def test_partial403_preserves_status_but_omits_partial_body_and_hash(self):
        raw = b'<html>truncated diagnostic fixture'
        _, runner, transport = self.make(evidence_contract.Response(403, 'text/html', raw,
                                                       complete=False, read_error='incomplete_body'))
        _, receipt = self.assert_held(runner, transport)
        evidence = self.evidence(runner, receipt)
        self.assertEqual(receipt['http_status'], 403)
        self.assertFalse(evidence['response_complete'])
        self.assertEqual(evidence['body_base64'], '')
        self.assertIsNone(evidence['retained_sha256'])
        self.assertEqual(evidence['body_status'], 'incomplete_omitted')
        self.assertIsNone(receipt['response_sha256'])

    def test_no_header_timeout_saves_spent_intent_without_exception_secret(self):
        _, runner, transport = self.make(error=TimeoutError('Bearer ' + TOKEN))
        self.assert_held(runner, transport)
        stored = runner.journal_path.read_text()
        self.assertNotIn(TOKEN, stored)
        self.assertNotIn('http_status', self.read(runner)[1])
        with self.assertRaises(ValueError):
            runner.run(read_only=True)
        self.assertEqual(len(transport.calls), 1)

    def test_failed_diagnostic_fsync_never_dispatches_a_second_request(self):
        _, runner, transport = self.make(evidence_contract.Response(403, 'text/html', b'Forbidden'))
        actual = runner.save
        def interrupted():
            if runner.row and runner.row.get('requests') and 'http_status' in runner.row['requests'][-1]:
                raise OSError('Dummy durable evidence failure')
            actual()
        with patch.object(runner, 'save', side_effect=interrupted), self.assertRaises(OSError):
            runner.run()
        self.assertEqual(len(transport.calls), 1)
        self.assertTrue(runner.intent_path.exists())
        row = parse(runner.journal_path.read_bytes())['targets']['FGDC-141']
        self.assertEqual(row['counts']['create'], 1)
        self.assertEqual(len(row['requests']), 1)

    def test_missing_journal_after403_still_cannot_create_again(self):
        fixture, runner, transport = self.make(evidence_contract.Response(403, 'text/html', b'Forbidden'))
        self.assert_held(runner, transport)
        runner.journal_path.unlink()
        replacement = draft.Runner(fixture.json_file, fixture.paths, fixture.grant_path, fixture.proof_path,
                                   TOKEN, transport=transport, now=lambda: fixtures.NOW)
        with self.assertRaises(ValueError):
            replacement.run()
        self.assertEqual(len(transport.calls), 1)

    def test_legacy_three_tuple_transport_retains_diagnostic_without_location(self):
        raw = b'<p>Legacy injected tuple403 fixture.</p>'
        _, runner, transport = self.make((403, 'text/html', raw))
        _, receipt = self.assert_held(runner, transport)
        self.assert_safe_payload(runner, receipt, raw, mime='text/html')

    def test_publication_capture_reuses_same_durable403_diagnostic_path(self):
        helper = publication_tests.ModernPublicationTests(methodName='runTest')
        helper.prepared_root = self.prepared_root
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        helper.grant('capture')
        raw = b'<p>Publication capture403 fixture.</p>'
        helper.transport.change = lambda index, response: evidence_contract.Response(403, 'text/html', raw)
        runner = helper.runner('capture')
        with self.assertRaises(ValueError):
            runner.run()
        row = parse(runner.journal_path.read_bytes())['targets']['FGDC-141']
        self.assertEqual(row['counts'], {'get': 1})
        self.assertEqual(len(helper.transport.calls), 1)
        receipt = row['requests'][0]
        self.assertEqual(receipt['http_status'], 403)
        self.assertEqual(base64.b64decode(self.evidence(runner, receipt)['body_base64']), raw)
        self.assertEqual(receipt['response_sha256'], sha(raw))
        self.assertNotIn('snapshot_path', row)


    def test_sidecar_failure_preserves_minimal_status_and_spent_create_on_reopen(self):
        fixture, runner, transport = self.make(evidence_contract.Response(403, 'text/html', b'Forbidden'))
        original = draft.permanent_intent
        def fail_sidecar(path, value):
            if str(path).endswith('.response.json'):
                raise OSError('Dummy sidecar fsync failure')
            return original(path, value)
        with patch.object(draft, 'permanent_intent', side_effect=fail_sidecar), self.assertRaises(OSError):
            runner.run()
        _, receipt = self.read(runner)
        self.assertEqual(receipt['http_status'], 403)
        self.assertEqual(receipt['response_sha256'], sha(b'Forbidden'))
        self.assertNotIn('response_evidence', receipt)
        reopened = draft.Runner(fixture.json_file, fixture.paths, fixture.grant_path, fixture.proof_path,
                                TOKEN, transport=transport, now=lambda: fixtures.NOW)
        with self.assertRaises(ValueError):
            reopened.run()
        self.assertEqual(len(transport.calls), 1)

    def test_existing_sidecar_is_never_overwritten_or_adopted(self):
        _, runner, transport = self.make(evidence_contract.Response(403, 'text/html', b'Forbidden'))
        name = runner.journal_path.name + '.FGDC-141.' + runner.grant_sha + '.0.response.json'
        sidecar = runner.journal_path.parent / name
        prior = b'{"preserve":"unrelated existing evidence"}'
        sidecar.write_bytes(prior)
        with self.assertRaises(FileExistsError):
            runner.run()
        self.assertEqual(sidecar.read_bytes(), prior)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(self.read(runner)[1]['http_status'], 403)
        self.assertNotIn('response_evidence', self.read(runner)[1])


class ModernDiagnosticProjectionTests(unittest.TestCase):
    def assert_suppressed(self, raw, token=TOKEN):
        value = evidence_contract.diagnostic(evidence_contract.Response(403, 'application/json', raw), token)
        self.assertTrue(value['credential_suppressed'])
        self.assertEqual(value['body_status'], 'credential_suppressed')
        self.assertEqual(value['body_base64'], '')
        self.assertIsNone(value['retained_sha256'])
        self.assertIsNone(value['response_sha256'])
        self.assertIsNone(value['content_type'])
        self.assertIsNone(value['location'])
        return value

    def test_unknown_credential_assignments_are_suppressed_even_without_own_token(self):
        for raw in (b'{"nested":{"access_token":"other-test-secret"}}',
                    b'{"AUTHORIZATION":"Bearer other-test-secret"}',
                    b'Set-Cookie: sid=other-test-secret',
                    b'Proxy-Authorization: Basic dXNlcjpwYXNz',
                    b'api-key=other-test-secret', b'Password: other-test-secret'):
            with self.subTest(raw=raw):
                self.assert_suppressed(raw)

    def test_duplicate_json_keys_do_not_hide_earlier_escaped_credential(self):
        escaped = encoded_echoes(TOKEN)['json_unicode']
        raw = ('{"message":"' + escaped + '","message":"ordinary replacement"}').encode()
        self.assert_suppressed(raw)

    def test_deep_percent_entity_and_utf16_encodings_are_not_retained(self):
        deeply_encoded = ''.join('%' + format(byte, '02x') for byte in TOKEN.encode())
        for _ in range(7):
            deeply_encoded = quote(deeply_encoded, safe='')
        forms = (deeply_encoded.encode(), TOKEN.encode('utf-16le'), TOKEN.encode('utf-16be'),
                 ('&amp;' + '#x' + format(ord(TOKEN[0]), 'x') + ';' + TOKEN[1:]).encode())
        for raw in forms:
            with self.subTest(raw=raw):
                self.assert_suppressed(raw)

    def test_final_normalization_and_unresolved_html_wrappers_are_suppressed(self):
        value = ''.join('%' + format(byte, '02x') for byte in TOKEN.encode())
        for _ in range(4):
            value = quote(value, safe='')
        self.assert_suppressed(value.encode())
        value = ''.join('&#' + str(ord(char)) + ';' for char in TOKEN)
        for _ in range(8):
            value = value.replace('&', '&amp;')
        self.assert_suppressed(value.encode())

    def test_duplicate_or_malformed_locations_are_omitted(self):
        for location in ('https://first.invalid/x, https://second.invalid/y',
                         '/path with spaces', r'/path\unsafe', 'https://user:pass@example.invalid/x'):
            with self.subTest(location=location):
                value = evidence_contract.diagnostic(
                    evidence_contract.Response(302, 'text/html', b'Moved', location=location), TOKEN)
                self.assertIsNone(value['location'])
                self.assertEqual(value['location_status'], 'omitted_invalid')

    def test_incomplete_body_cannot_persist_fragment_of_a_credential(self):
        raw = b'<html>Bearer ' + TOKEN[:9].encode()
        value = evidence_contract.diagnostic(
            evidence_contract.Response(403, 'text/html', raw, complete=False, read_error='incomplete_body'), TOKEN)
        self.assertFalse(value['response_complete'])
        self.assertEqual(value['body_base64'], '')
        self.assertIsNone(value['retained_sha256'])
        self.assertIsNone(value['response_sha256'])

    def test_malformed_envelopes_do_not_become_complete_legacy_responses(self):
        cases = ([200, draft.MIME, b'{}'], (200, draft.MIME, b'{}', 'location'),
                 evidence_contract.Response(True, draft.MIME, b'{}'),
                 evidence_contract.Response(700, draft.MIME, b'{}'),
                 evidence_contract.Response(200, draft.MIME, b'x' * (draft.MAX_BYTES + 1)),
                 evidence_contract.Response(200, draft.MIME, b'{}', complete=False),
                 evidence_contract.Response(200, draft.MIME, b'{}', read_error='incomplete_body'))
        for case in cases:
            with self.subTest(kind=type(case).__name__), self.assertRaises(ValueError):
                evidence_contract.normalize_response(case)


class ModernResponseTransportTests(unittest.TestCase):
    def wire(self, *, status=403, mime='text/html', location=None, chunks=None, length=0,
             extra=None, socket_timeout=False, chunked=False, chunk_left=None):
        headers = {'Content-Type': mime, 'Location': location, **(extra or {})}
        response = Mock(status=status, length=length, chunked=chunked, chunk_left=chunk_left)
        response.read1.side_effect = chunks if chunks is not None else [b'Forbidden', b'']
        response.getheader.side_effect = lambda name, default=None: headers.get(name, default)
        connection = Mock()
        connection.getresponse.return_value = response
        if socket_timeout:
            connection.getresponse.side_effect = TimeoutError('dummy response header timeout')
        context = Mock(keylog_filename='dummy-must-be-disabled')
        with (patch.object(draft.platform, 'system', return_value='Darwin'),
              patch.object(draft.ssl, 'create_default_context', return_value=context),
              patch.object(draft.http.client, 'HTTPSConnection', return_value=connection) as constructor,
              patch.object(draft.signal, 'signal'),
              patch.object(draft.signal, 'setitimer', return_value=(0, 0)),
              patch.object(draft.time, 'monotonic', return_value=10)):
            result = draft.Transport(TOKEN).request('POST', '/api/records', b'{}', timeout=5)
        constructor.assert_called_once_with('zenodo.org', timeout=5, context=context)
        self.assertIsNone(context.keylog_filename)
        connection.close.assert_called_once()
        connection.request.assert_called_once()
        self.assertEqual(connection.request.call_args.args[:2], ('POST', '/api/records'))
        self.assertTrue(all(0 < call.args[0] <= 5 for call in connection.sock.settimeout.call_args_list))
        return result, response, connection

    def test_frozen_response_preserves_status_mime_body_and_safe_location(self):
        result, _, _ = self.wire(location='https://example.invalid/diagnostic')
        self.assertEqual((result.status, result.mime, result.body), (403, 'text/html', b'Forbidden'))
        self.assertEqual(result.location, 'https://example.invalid/diagnostic')
        self.assertTrue(result.complete)
        with self.assertRaises((dataclasses.FrozenInstanceError, AttributeError)):
            result.status = 200

    def test_only_mime_and_location_headers_are_requested_or_retained(self):
        other = 'dummy-unrelated-credential-value'
        result, response, _ = self.wire(extra={
            'Set-Cookie': 'session=' + other, 'Authorization': 'Bearer ' + other,
            'Proxy-Authorization': 'Basic ' + other, 'X-Api-Key': other})
        requested = {call.args[0].lower() for call in response.getheader.call_args_list}
        self.assertEqual(requested, {'content-type', 'location'})
        response.getheaders.assert_not_called()
        self.assertNotIn(other, repr(result))
        self.assertFalse(hasattr(result, 'headers'))

    def test_301_returns_once_without_followup_connection_or_redirect(self):
        result, response, connection = self.wire(status=301, location='https://example.invalid/do-not-fetch')
        self.assertEqual(result.status, 301)
        self.assertEqual(result.location, 'https://example.invalid/do-not-fetch')
        self.assertEqual(connection.request.call_count, 1)
        self.assertEqual(response.read1.call_count, 2)

    def test_midbody_exception_returns_bounded_incomplete_evidence_not_exception_text(self):
        result, _, _ = self.wire(chunks=[b'partial fixture', TimeoutError('Bearer ' + TOKEN)], length=20)
        self.assertEqual(result.status, 403)
        self.assertEqual(result.mime, 'text/html')
        self.assertEqual(result.body, b'partial fixture')
        self.assertFalse(result.complete)
        self.assertIn(result.read_error, ('read_interrupted',))
        self.assertNotIn(TOKEN, repr(result))

    def test_eof_with_positive_remaining_content_length_is_incomplete(self):
        result, _, _ = self.wire(status=201, mime=draft.MIME, chunks=[b'{}', b''], length=15)
        self.assertEqual(result.body, b'{}')
        self.assertFalse(result.complete)
        self.assertEqual(result.read_error, 'incomplete_body')

    def test_chunked_eof_with_unfinished_chunk_cannot_be_complete(self):
        result, _, _ = self.wire(status=201, mime=draft.MIME, chunks=[b'{}', b''],
                                length=None, chunked=True, chunk_left=5)
        self.assertFalse(result.complete)
        self.assertEqual(result.read_error, 'incomplete_body')

    def test_chunked_read_interruption_returns_partial_without_promoting_json(self):
        result, _, _ = self.wire(status=201, mime=draft.MIME,
                                chunks=[b'{}', http.client.IncompleteRead(TOKEN.encode())], length=None)
        self.assertFalse(result.complete)
        self.assertEqual(result.read_error, 'read_interrupted')
        self.assertEqual(result.body, b'{}')
        self.assertNotIn(TOKEN, repr(result))

    def test_oversize_stops_at_first_extra_byte_and_marks_hash_scope_incomplete(self):
        chunks = [b'x' * 8192] * (draft.MAX_BYTES // 8192) + [b'x', b'never-read']
        result, response, _ = self.wire(chunks=chunks)
        self.assertFalse(result.complete)
        self.assertEqual(result.read_error, 'body_limit')
        self.assertLessEqual(len(result.body), draft.MAX_BYTES)
        self.assertEqual(response.read1.call_count, draft.MAX_BYTES // 8192 + 1)
        self.assertEqual(response.read1.call_args.args, (1,))


if __name__ == '__main__':
    unittest.main()
