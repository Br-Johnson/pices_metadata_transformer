"""Dummy-only tests for a Mac existing-draft continuation and spent retry budget."""

import io
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import mac_sandbox_canary as mac
from scripts import modern_draft_schema as schema
from scripts import modern_synthetic_canary as modern

TOKEN = 'dummy-mac-canary-token-0123456789'
NOW = datetime(2026, 10, 5, 3, 0, tzinfo=timezone.utc)


class FakeTransport:
    def __init__(self, fixture):
        self.fixture = fixture
        self.calls = []
        self.change = None
        self.updated = False
        self.complete = False

    def entry(self, complete=None):
        complete = self.complete if complete is None else complete
        data = {'key': mac.KEY, 'status': 'completed' if complete else 'pending',
                'transfer': {'type': 'L'}, 'links': {
                    'self': mac.ORIGIN + mac.FILE, 'content': mac.ORIGIN + mac.FILE + '/content',
                    'commit': mac.ORIGIN + mac.FILE + '/commit'}}
        if complete:
            data.update(size=439, checksum='md5:a34b1bdba8624abcb496bfc91fd98f8d')
        return data

    def record(self):
        base = self.fixture.checkpoint['baseline']
        expected = json.loads(mac.fixture()[0])
        return {'id': '612988', 'created': base['created'], 'revision_id': 15 if self.complete else 12 if self.updated else 11,
                'metadata': expected['metadata'] if self.updated else base['metadata'],
                'access': expected['access'] if self.updated else base['access'], 'status': 'draft',
                'is_published': False, 'pids': {}, 'versions': {'index': 1},
                'parent': {'id': base['parent_id'], 'access': {'owned_by': {'user': base['owner']}}},
                'links': {'self': mac.ORIGIN + mac.BASE, 'files': mac.ORIGIN + mac.BASE + '/files'},
                'files': {'enabled': True, 'entries': {mac.KEY: self.entry()} if self.complete else {},
                          'count': int(self.complete), 'total_bytes': 439 if self.complete else 0},
                'errors': [] if self.complete else [{'field': 'files.enabled', 'messages': ['Missing uploaded files.']}]}

    def request(self, method, path, body, revision, timeout=mac.TIMEOUT):
        assert 0 < timeout <= mac.TIMEOUT
        # Every adapter entry already has a durable per-action intent.
        phase = 'retry' if (self.fixture.stage / 'retry.intent.json').exists() else 'execute'
        index = sum(1 for call in self.calls if call[0] == phase)
        assert (self.fixture.stage / f'{phase}-{index:02d}.intent.json').is_file()
        self.calls.append((phase, method, path, body, revision))
        status = 200
        if method == 'PUT' and path == mac.BASE:
            self.updated = True
        if method == 'POST' and path.endswith('/commit'):
            self.complete = True
        if path == mac.BASE:
            data = self.record()
        elif method == 'GET' and path.endswith('/content'):
            data = mac.fixture()[1]
        elif path == mac.BASE + '/files':
            data = {'entries': [self.entry()]}
            if method == 'POST':
                status = 201
        else:
            data = self.entry()
        if self.change:
            status, data = self.change(len(self.calls) - 1, status, deepcopy(data))
        raw = data if isinstance(data, bytes) else json.dumps(data).encode()
        mime = 'application/octet-stream' if method == 'GET' and path.endswith('/content') else 'application/json'
        return status, mime, raw


class Fixture:
    def __init__(self, directory):
        self.root = Path(directory)
        self.stage = self.root / 'stage'
        self.result = b'{"dummy": "already sanitized successful Mac receipt"}'
        self.bundle = b'dummy ZIP bytes; real pinned ZIP is never accessed by tests'
        self.checkpoint = {'schema_version': 1, 'executor': mac.EXECUTOR, 'origin': mac.ORIGIN,
                           'marker_sha256': mac.MARKER_SHA, 'marker_bytes': 319,
                           'prior_methods': ['GET', 'PUT', 'GET'], 'prior_statuses': [200, 200, 200],
                           'before_revision': 10, 'result_sha256': mac.sha(self.result),
                           'history_manifest_sha256': 'a' * 64,
                           'prior_intents': {'mac_corrected_get': 2, 'mac_corrected_put': 1, 'historical_get': 215},
                           'historical_holds_preserved': True,
                           'baseline': {'id': '612988', 'parent_id': '612987', 'owner': '123',
                                        'created': '2026-10-03T01:02:03Z', 'revision_id': 11,
                                        'metadata': {'title': 'SYNTHETIC MAC MARKER', 'publisher': 'Zenodo'},
                                        'access': {'record': 'public', 'files': 'restricted'}}}
        for name, data in [('checkpoint.json', mac.encode(self.checkpoint)), ('result.json', self.result),
                           ('bundle.zip', self.bundle)]:
            mac.write_new(self.root / name, data)
        mac.prepare(self.stage, self.root / 'checkpoint.json', self.root / 'result.json', self.root / 'bundle.zip')
        self.grant = {'approved': True, 'executor': mac.EXECUTOR, 'binding': mac.preflight(self.stage),
                      'limits': mac.LIMITS.copy(), 'started_at': NOW.isoformat(),
                      'expires_at': (NOW + timedelta(seconds=600)).isoformat(),
                      'checkpoint_transfer_verified': True, 'mac_runtime_reviewed': True,
                      'existing_draft_only': True, 'no_create_pid_publish_delete': True,
                      'token_scope': 'deposit:write'}
        self.grant_path = self.root / 'grant.json'
        mac.write_new(self.grant_path, self.grant)
        self.transport = FakeTransport(self)

    def runner(self):
        return mac.Runner(self.stage, self.grant_path, TOKEN, self.transport, lambda: NOW)

    def change_grant(self, **changes):
        self.grant.update(changes)
        self.grant_path.write_bytes(mac.encode(self.grant))


class MacCanaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        result = b'{"dummy": "already sanitized successful Mac receipt"}'
        bundle = b'dummy ZIP bytes; real pinned ZIP is never accessed by tests'
        patches = [patch.object(mac, 'RESULT_SHA', mac.sha(result)), patch.object(mac, 'BUNDLE_SHA', mac.sha(bundle))]
        for context in patches:
            context.start()
            self.addCleanup(context.stop)
        self.fixture = Fixture(self.temp.name)

    def test_fixture_is_exact_prior_schema_validated_payload_and_original_xml(self):
        body, xml = mac.fixture()
        self.assertEqual(len(body), 517)
        self.assertEqual(len(xml), 439)
        self.assertEqual(json.loads(body), schema.synthetic_payload(modern.load(modern.PACKET / 'metadata-put.json')))
        self.assertTrue(schema.validate_payload(json.loads(body)))
        self.assertEqual(mac.sha(body), mac.PAYLOAD_SHA)
        self.assertEqual(mac.sha(xml), mac.XML_SHA)

    def test_prepare_and_preflight_are_offline_and_carry_exact_history(self):
        with patch.object(mac.Transport, 'request', side_effect=AssertionError('network')):
            bound = mac.preflight(self.fixture.stage)
        self.assertEqual(bound['inputs_sha256']['mac-result.json'], mac.sha(self.fixture.result))
        self.assertEqual(json.loads((self.fixture.stage / 'checkpoint.json').read_bytes()), self.fixture.checkpoint)
        self.assertEqual(list(self.fixture.stage.glob('*.intent.json')), [])

    def test_full_flow_and_separate_durable_retry_have_exact_action_ceiling(self):
        result = self.fixture.runner().run()
        self.assertEqual(result['counts'], {'get': 6, 'metadata': 1, 'init': 1, 'content': 1, 'commit': 1})
        result = self.fixture.runner().run(retry=True)
        self.assertEqual(result['counts'], mac.LIMITS)
        calls = self.fixture.transport.calls
        self.assertEqual([call[1] for call in calls], ['GET', 'PUT', 'GET', 'POST', 'PUT', 'POST'] + ['GET'] * 8)
        self.assertEqual(calls[1][3:], (mac.fixture()[0], 11))
        self.assertTrue(all(call[0] == 'retry' and call[1] == 'GET' for call in calls[10:]))
        self.assertEqual(result['provider_mutations_this_phase'], 0)
        self.assertEqual(len(calls), 14)

    def test_redirect_anywhere_holds_with_no_next_action_or_reentry(self):
        self.fixture.transport.change = lambda index, status, data: (301 if index == 1 else status, data)
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        count = len(self.fixture.transport.calls)
        with self.assertRaises(FileExistsError):
            self.fixture.runner().run()
        with self.assertRaises(FileNotFoundError):
            self.fixture.runner().run(retry=True)
        self.assertEqual(len(self.fixture.transport.calls), count)
        self.assertEqual(count, 2)

    def test_uncertain_metadata_write_is_permanently_spent(self):
        def timeout(index, status, data):
            if index == 1:
                raise TimeoutError(TOKEN)
            return status, data
        self.fixture.transport.change = timeout
        with self.assertRaises(TimeoutError):
            self.fixture.runner().run()
        self.assertTrue((self.fixture.stage / 'execute-01.intent.json').exists())
        self.assertFalse((self.fixture.stage / 'execute.result.json').exists())
        with self.assertRaises(FileExistsError):
            self.fixture.runner().run()
        self.assertEqual(len(self.fixture.transport.calls), 2)
        self.assertNotIn(TOKEN, ''.join(path.read_text() for path in self.fixture.stage.glob('*.json')))

    def test_wrong_revision_metadata_owner_parent_or_files_stop_before_put(self):
        for key, value in [('revision_id', 12), ('metadata', {}), ('pids', {'doi': {}}),
                           ('is_published', True), ('id', '612989')]:
            with self.subTest(key=key):
                data = self.fixture.transport.record()
                data[key] = value
                with self.assertRaises(mac.Held):
                    self.fixture.runner().record(data, 'baseline', 11)
        data = self.fixture.transport.record()
        data['parent']['access']['owned_by']['user'] = '456'
        with self.assertRaises(mac.Held):
            self.fixture.runner().record(data, 'baseline', 11)
        data = self.fixture.transport.record()
        data['files']['entries'] = {mac.KEY: {'key': mac.KEY}}
        with self.assertRaises(mac.Held):
            self.fixture.runner().record(data, 'baseline', 11)

    def test_success_status_with_missing_metadata_stops_before_file_init(self):
        self.fixture.transport.change = lambda i, s, d: (s, dict(d, metadata={}) if i == 1 else d)
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        self.assertEqual(len(self.fixture.transport.calls), 2)

    def test_only_exact_empty_file_warning_is_accepted(self):
        runner = self.fixture.runner()
        data = self.fixture.transport.record()
        runner.record(data, 'baseline', 11)
        data['errors'][0]['messages'] = ['Permission denied']
        with self.assertRaises(mac.Held):
            runner.record(data, 'baseline', 11)
        data['errors'] = [{'field': 'metadata.title', 'messages': ['Missing uploaded files.']}]
        with self.assertRaises(mac.Held):
            runner.record(data, 'baseline', 11)

    def test_malformed_errors_never_count_as_error_free(self):
        for errors in [None, {}, '', 0, False]:
            data = self.fixture.transport.record()
            data['errors'] = errors
            with self.subTest(errors=errors), self.assertRaises(mac.Held):
                self.fixture.runner().record(data, 'baseline', 11)

    def test_expiry_after_durable_intent_prevents_transport(self):
        runner = self.fixture.runner()
        original = mac.write_new
        def expire(path, value):
            original(path, value)
            if path.name == 'execute-00.intent.json':
                runner.now = lambda: NOW + timedelta(seconds=601)
        with patch.object(mac, 'write_new', side_effect=expire), self.assertRaises(mac.Held):
            runner.run()
        self.assertEqual(self.fixture.transport.calls, [])
        self.assertTrue((self.fixture.stage / 'execute-00.intent.json').exists())

    def test_grant_withdrawal_between_calls_stops_next_mutation(self):
        def revoke(index, status, data):
            if index == 0:
                self.fixture.change_grant(approved=False)
            return status, data
        self.fixture.transport.change = revoke
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        self.assertEqual(len(self.fixture.transport.calls), 1)
        self.assertFalse((self.fixture.stage / 'execute-01.intent.json').exists())

    def test_source_reviewed_empty_serialization_defaults_are_tolerated(self):
        self.fixture.transport.updated = True
        data = self.fixture.transport.record()
        data['metadata']['rights'] = []
        creator = data['metadata']['creators'][0]
        creator['affiliations'] = []
        creator['role'] = {}
        creator['person_or_org']['identifiers'] = []
        self.fixture.runner().record(data, 'updated', 12)
        creator['affiliations'] = [{'name': 'Unexpected affiliation'}]
        with self.assertRaises(mac.Held):
            self.fixture.runner().record(data, 'updated', 12)

    def test_partial_file_inventory_and_wrong_bytes_fail_readback(self):
        self.fixture.transport.change = lambda i, s, d: (s, {'entries': []} if i == 7 else d)
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        self.assertEqual(len(self.fixture.transport.calls), 8)
        self.assertFalse((self.fixture.stage / 'execute.result.json').exists())

    def test_same_length_wrong_xml_bytes_fail_before_completion(self):
        self.fixture.transport.change = lambda i, s, d: (s, b'x' * 439 if i == 9 else d)
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        self.assertFalse((self.fixture.stage / 'execute.result.json').exists())

    def test_file_link_escape_and_checksum_mismatch_hold(self):
        runner = self.fixture.runner()
        for change in ['foreign', 'wrongid', 'checksum']:
            data = self.fixture.transport.entry(True)
            if change == 'foreign':
                data['links']['content'] = 'https://example.invalid/content'
            elif change == 'wrongid':
                data['links']['commit'] = mac.ORIGIN + '/api/records/1/draft/files/key/commit'
            else:
                data['checksum'] = 'md5:' + '0' * 32
            with self.subTest(change=change), self.assertRaises(mac.Held):
                runner.file(data, True)

    def test_retry_cannot_change_revision_or_repeat_successful_phase(self):
        self.fixture.runner().run()
        self.fixture.transport.change = lambda i, s, d: (s, dict(d, revision_id=16) if i == 10 else d)
        with self.assertRaises(mac.Held):
            self.fixture.runner().run(retry=True)
        with self.assertRaises(FileExistsError):
            self.fixture.runner().run(retry=True)
        self.assertEqual(len(self.fixture.transport.calls), 11)

    def test_retry_rejects_tampered_prior_receipts_before_transport(self):
        self.fixture.runner().run()
        path = self.fixture.stage / 'execute-01.response.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(mac.Held):
            self.fixture.runner().run(retry=True)
        self.assertEqual(len(self.fixture.transport.calls), 10)

    def test_grants_require_transfer_and_runtime_review_and_fixed_limits(self):
        for name in ['approved', 'checkpoint_transfer_verified', 'mac_runtime_reviewed',
                     'existing_draft_only', 'no_create_pid_publish_delete']:
            self.fixture.change_grant(**{name: False})
            with self.subTest(name=name), self.assertRaises(mac.Held):
                self.fixture.runner()
            self.fixture.change_grant(**{name: True})
        self.fixture.change_grant(limits=dict(mac.LIMITS, create=1))
        with self.assertRaises(mac.Held):
            self.fixture.runner()
        self.assertEqual(self.fixture.transport.calls, [])

    def test_expired_and_overlong_grants_fail_before_intent(self):
        for expires in [NOW, NOW + timedelta(seconds=601)]:
            self.fixture.change_grant(expires_at=expires.isoformat())
            with self.assertRaises(mac.Held):
                self.fixture.runner()
        self.assertEqual(list(self.fixture.stage.glob('*.intent.json')), [])

    def test_runtime_fixture_and_checkpoint_tampering_rejected(self):
        path = self.fixture.stage / 'checkpoint.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises(mac.Held):
            self.fixture.runner()
        self.assertEqual(self.fixture.transport.calls, [])

    def test_unrecognized_routes_or_write_budget_never_enter_transport(self):
        runner = self.fixture.runner()
        runner.phase = 'execute'
        for kind, method, path in [('create', 'POST', '/api/records'), ('metadata', 'PUT', '/api/records/1/draft'),
                                   ('get', 'GET', mac.BASE + '?page=2'), ('get', 'GET', 'https://zenodo.org' + mac.BASE),
                                   ('commit', 'POST', mac.BASE + '/actions/publish')]:
            with self.subTest(path=path), self.assertRaises(mac.Held):
                runner.call(kind, method, path, 200)
        runner.counts['metadata'] = 1
        with self.assertRaises(mac.Held):
            runner.call('metadata', 'PUT', mac.BASE, 200, mac.fixture()[0], 11)
        self.assertEqual(self.fixture.transport.calls, [])

    def test_token_echo_is_suppressed_without_persisting_provider_text(self):
        self.fixture.transport.change = lambda i, s, d: (s, {'secret': TOKEN})
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        receipt = json.loads((self.fixture.stage / 'execute-00.response.json').read_bytes())
        self.assertTrue(receipt['credential_suppressed'])
        self.assertIsNone(receipt['sha256'])
        self.assertNotIn(TOKEN, ''.join(path.read_text() for path in self.fixture.stage.glob('*.json')))
        for raw in [json.dumps({'secret': TOKEN}).encode(), ''.join('\\u%04x' % ord(c) for c in TOKEN).join(['"', '"']).encode()]:
            self.assertTrue(mac.echoed(raw, TOKEN))

    def test_duplicate_key_cannot_hide_escaped_token_before_fingerprinting(self):
        escaped = ''.join('\\u%04x' % ord(char) for char in TOKEN)
        raw = ('{"same":"' + escaped + '","same":"safe"}').encode()
        self.assertTrue(mac.echoed(raw, TOKEN))
        self.fixture.transport.change = lambda i, status, data: (status, raw)
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        receipt = json.loads((self.fixture.stage / 'execute-00.response.json').read_bytes())
        self.assertTrue(receipt['credential_suppressed'])
        self.assertIsNone(receipt['sha256'])

    def test_tls_preparation_is_inside_wall_deadline(self):
        with patch.object(mac.platform, 'system', return_value='Darwin'), \
                patch.object(mac.http.client, 'HTTPSConnection') as connection, \
                patch.object(mac.ssl, 'create_default_context'), \
                patch.object(mac.signal, 'signal'), \
                patch.object(mac.signal, 'setitimer', return_value=(0.0, 0.0)), \
                patch.object(mac.time, 'monotonic', side_effect=[0, 21]):
            with self.assertRaises(mac.Held):
                mac.Transport(TOKEN).request('GET', mac.BASE, None, None)
            connection.assert_not_called()

    def test_oversize_or_malformed_response_holds(self):
        self.fixture.transport.change = lambda i, s, d: (s, b'x' * (mac.MAX_BYTES + 1))
        with self.assertRaises(mac.Held):
            self.fixture.runner().run()
        self.assertEqual(len(self.fixture.transport.calls), 1)
        with self.assertRaises(mac.Held):
            mac.parse(b'{"id":1,"id":2}')
        with self.assertRaises(mac.Held):
            mac.parse(b'{"value":NaN}')

    def test_symlink_and_nonprivate_stage_are_rejected(self):
        path = self.fixture.root / 'link'
        path.symlink_to(self.fixture.stage, target_is_directory=True)
        with self.assertRaises(mac.Held):
            mac.preflight(path)
        self.fixture.stage.chmod(0o755)
        with self.assertRaises(mac.Held):
            mac.preflight(self.fixture.stage)

    def test_cli_blocks_nonmac_before_token_and_emits_only_closed_failure(self):
        with patch.object(mac.platform, 'system', return_value='Linux'), patch.object(mac.sys, 'argv', [
                'canary', 'execute', '--stage', str(self.fixture.stage), '--grant', str(self.fixture.grant_path)]), \
                patch.object(mac.getpass, 'getpass', side_effect=AssertionError('must not prompt')), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(mac.main(), 1)
        self.assertEqual(json.loads(output.getvalue())['held'], True)

    def test_real_transport_has_verified_tls_explicit_bytes_no_redirect_and_total_timer(self):
        class Response:
            status = 301
            def getheader(self, name, default):
                return 'application/json'
            def read1(self, size):
                return b''
        with patch.object(mac.platform, 'system', return_value='Darwin'), \
                patch.object(mac.http.client, 'HTTPSConnection') as connection, \
                patch.object(mac.signal, 'signal') as handler, \
                patch.object(mac.signal, 'setitimer', return_value=(0.0, 0.0)) as timer:
            connection.return_value.getresponse.return_value = Response()
            status, _, _ = mac.Transport(TOKEN).request('PUT', mac.BASE, mac.fixture()[0], 11)
            args, kwargs = connection.call_args
            self.assertEqual(args, ('sandbox.zenodo.org',))
            self.assertTrue(kwargs['context'].check_hostname)
            call = connection.return_value.request.call_args
            self.assertEqual(call.kwargs['body'], mac.fixture()[0])
            self.assertEqual(call.kwargs['headers']['If-Match'], '11')
            self.assertEqual(call.kwargs['headers']['Content-Length'], '517')
            self.assertEqual(status, 301)
            self.assertEqual(connection.return_value.request.call_count, 1)
            self.assertEqual(timer.call_args_list[0].args, (mac.signal.ITIMER_REAL, 20))
            self.assertEqual(handler.call_count, 2)
            connection.return_value.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
