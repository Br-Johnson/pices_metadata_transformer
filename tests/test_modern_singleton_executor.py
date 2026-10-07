"""Independent offline faults for the modern four-mutation singleton workflow.

Only temporary source-derived fixtures and injected transports are exercised.
No test grants provider authority or treats a source assessment as publication QA.
"""

import contextlib
import copy
import getpass
import json
import os
import stat
import subprocess
import tempfile
import unittest
import warnings
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.modern_singleton import Held, encode, parse
from scripts.modern_singleton_executor import (
    LIMITS,
    MAX_BYTES,
    MIME,
    USER_AGENT,
    Runner,
    Transport,
    production_token,
)
from scripts.production_mutations import MutationJournal
from scripts.upload_service import atomic_json, ledger_lock, read_json
from tests import modern_singleton_fixtures as fixtures


class FaultTransport:
    """Wrap the realistic fixture without changing its successful effect model."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = []
        self.fail_before = None
        self.fail_after = None
        self.change = lambda index, response: response

    def request(self, method, path, body, *, timeout):
        index = len(self.calls)
        self.calls.append((method, path, body, timeout))
        if index == self.fail_before:
            raise TimeoutError('Dummy offline transport failure')
        response = self.inner.request(method, path, body, timeout=timeout)
        if index == self.fail_after:
            raise TimeoutError('Dummy offline response lost after effect')
        return self.change(index, response)


class ModernSingletonExecutorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=['FGDC-141'])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.index = 0

    def fixture(self):
        self.index += 1
        fixture = fixtures.Fixture(Path(self.temporary.name) / str(self.index), self.prepared_root)
        fixture.transport = FaultTransport(fixture.transport)
        return fixture

    @staticmethod
    def runner(fixture, now=None):
        return Runner(fixture.json_file, fixture.paths, fixture.grant_path, fixture.proof_path,
                      fixtures.TOKEN, fixture.transport, now=now or (lambda: fixtures.NOW))

    @staticmethod
    def row(fixture):
        return read_json(fixture.paths.uploads_registry_path + '.modern-v1.json')['targets'][
            fixture.prepared.source_id]

    @staticmethod
    def writes(fixture):
        return [call for call in fixture.transport.calls if call[0] != 'GET']

    @staticmethod
    def change_json(fixture, index, mutation):
        def change(current, response):
            status, mime, raw = response
            if current == index:
                data = parse(raw)
                mutation(data)
                raw = encode(data)
            return status, mime, raw
        fixture.transport.change = change

    def test_full_create_upload_bracketed_readback_and_retry_have_exact_budgets(self):
        fixture = self.fixture()
        runner = self.runner(fixture)
        self.assertEqual(fixture.transport.calls, [])
        first = runner.run()
        self.assertTrue(first['draft_verified'])
        self.assertFalse(first['publication_approved'])
        self.assertEqual(first['counts'], dict(LIMITS, get=5))
        self.assertEqual([call[0] for call in fixture.transport.calls],
                         ['POST', 'POST', 'PUT', 'POST'] + ['GET'] * 5)
        self.assertEqual(fixture.transport.calls[0][1:3], ('/api/records', fixture.prepared.body))
        self.assertEqual(fixture.transport.calls[2][2], fixture.prepared.xml)
        self.assertEqual(fixture.transport.calls[4][1], fixture.transport.calls[8][1])
        second = self.runner(fixture).run(read_only=True)
        self.assertTrue(second['read_only'])
        self.assertEqual(second['counts'], LIMITS)
        self.assertEqual(second['identity'], first['identity'])
        self.assertEqual(second['revision_id'], first['revision_id'])
        self.assertEqual(len(self.writes(fixture)), 4)
        self.assertTrue(all(0 < call[3] <= 20 for call in fixture.transport.calls))
        with self.assertRaises(ValueError):
            self.runner(fixture).run(read_only=True)
        self.assertEqual(len(fixture.transport.calls), 14)

    def test_grant_mismatches_never_dispatch(self):
        changes = ({'approved': False}, {'owner': 123}, {'origin': 'https://sandbox.zenodo.org'},
                   {'executor': 'unassigned-executor'}, {'binding': '0' * 64},
                   {'state_root': '/tmp/another-state-root'}, {'draft_only': False},
                   {'token_scope': 'deposit:actions'}, {'canary_receipt_sha256': ''},
                   {'reviewed_by': ''}, {'limits': dict(LIMITS, create=True)})
        for change in changes:
            with self.subTest(change=change):
                fixture = self.fixture()
                fixture.change_grant(**change)
                with self.assertRaises(ValueError):
                    self.runner(fixture)
                self.assertEqual(fixture.transport.calls, [])

    def test_incomplete_or_conflicting_duplicate_history_proof_never_dispatches(self):
        changes = ({'complete': False}, {'history_reconciled': False},
                   {'matched_record_ids': ['19000001']}, {'matched_dois': ['10.5281/zenodo.1']},
                   {'owner': '124'}, {'binding': '0' * 64}, {'reviewed_by': ''},
                   {'history_sha256': ''}, {'inventory_sha256': ''})
        for change in changes:
            with self.subTest(change=change):
                fixture = self.fixture()
                fixture.change_proof(**change)
                with self.assertRaises(ValueError):
                    self.runner(fixture)
                self.assertEqual(fixture.transport.calls, [])

    def test_time_and_evidence_changes_between_constructor_and_run_hold(self):
        for mode in ('grant', 'proof', 'payload', 'expiry'):
            with self.subTest(mode=mode):
                fixture = self.fixture()
                clock = [fixtures.NOW]
                runner = self.runner(fixture, now=lambda current=clock: current[0])
                if mode == 'grant':
                    fixture.change_grant(reviewed_by='Changed reviewer')
                elif mode == 'proof':
                    fixture.change_proof(reviewed_by='Changed independent reviewer')
                elif mode == 'payload':
                    raw = fixture.json_file.read_bytes()
                    fixture.json_file.write_bytes(raw + b'\n')
                else:
                    clock[0] += timedelta(seconds=601)
                with self.assertRaises(ValueError):
                    runner.run()
                self.assertEqual(fixture.transport.calls, [])

    def test_every_write_fault_is_spent_before_and_after_remote_effect(self):
        for index, action in enumerate(('create', 'init', 'content', 'commit')):
            for when in ('fail_before', 'fail_after'):
                with self.subTest(action=action, when=when):
                    fixture = self.fixture()
                    setattr(fixture.transport, when, index)
                    with self.assertRaises(ValueError):
                        self.runner(fixture).run()
                    self.assertEqual(self.row(fixture)['counts'][action], 1)
                    self.assertEqual(len(fixture.transport.calls), index + 1)
                    with self.assertRaises(ValueError):
                        self.runner(fixture).run()
                    self.assertEqual(len(fixture.transport.calls), index + 1)

    def test_lost_create_response_cannot_be_adopted_by_read_only_mode(self):
        fixture = self.fixture()
        fixture.transport.fail_after = 0
        with self.assertRaises(ValueError):
            self.runner(fixture).run()
        self.assertIsNone(self.row(fixture)['identity'])
        with self.assertRaises(ValueError):
            self.runner(fixture).run(read_only=True)
        self.assertEqual(len(fixture.transport.calls), 1)

    def test_lost_commit_response_recovers_only_by_complete_readback(self):
        fixture = self.fixture()
        fixture.transport.fail_after = 3
        with self.assertRaises(ValueError):
            self.runner(fixture).run()
        result = self.runner(fixture).run(read_only=True)
        self.assertTrue(result['draft_verified'])
        self.assertTrue(result['read_only'])
        self.assertEqual(result['counts'], dict(LIMITS, get=5))
        self.assertEqual(len(self.writes(fixture)), 4)

    def test_partial_upload_read_only_recovery_does_not_resume_unspent_writes(self):
        for index in (1, 2, 3):
            with self.subTest(index=index):
                fixture = self.fixture()
                fixture.transport.fail_before = index
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                before = len(self.writes(fixture))
                with self.assertRaises(ValueError):
                    self.runner(fixture).run(read_only=True)
                self.assertEqual(len(self.writes(fixture)), before)

    def test_independent_permanent_intent_survives_journal_loss_and_refreshed_grant(self):
        fixture = self.fixture()
        runner = self.runner(fixture)
        runner.run()
        intent = runner.intent_path.read_bytes()
        runner.journal_path.unlink()
        fixture.change_proof(reviewed_by='Fresh independent reviewer')
        fixture.change_grant(reviewed_by='Fresh grant reviewer')
        with self.assertRaises(ValueError):
            self.runner(fixture).run()
        self.assertEqual(runner.intent_path.read_bytes(), intent)
        self.assertEqual(len(self.writes(fixture)), 4)

    def test_existing_legacy_identity_or_attempt_prevents_modern_creation(self):
        for source in ('registry', 'journal'):
            with self.subTest(source=source):
                fixture = self.fixture()
                path = fixture.paths.uploads_registry_path
                value = {fixture.prepared.source_id: {'deposition_id': 19000001}}
                if source == 'journal':
                    path += '.mutations.json'
                    value = {'targets': value}
                atomic_json(path, value)
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(fixture.transport.calls, [])

    def test_returned_create_identity_cannot_alias_another_legacy_source(self):
        for source in ('registry', 'journal'):
            with self.subTest(source=source):
                fixture = self.fixture()
                path = fixture.paths.uploads_registry_path
                value = {'different-source': {'environment': 'production', 'deposition_id': 19000001}}
                if source == 'journal':
                    path += '.mutations.json'
                    value = {'targets': value}
                atomic_json(path, value)
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(len(fixture.transport.calls), 1)
                self.assertIsNone(self.row(fixture)['identity'])

    def test_modern_permanent_intent_blocks_legacy_creation_even_after_journal_loss(self):
        fixture = self.fixture()
        runner = self.runner(fixture)
        fixture.transport.fail_after = 0
        with self.assertRaises(ValueError):
            runner.run()
        runner.journal_path.unlink()
        evidence = fixture.prepared.evidence
        entry = {'environment': 'production', 'source_sha256': evidence['source_sha256'],
                 'metadata_sha256': evidence['legacy_metadata_sha256'],
                 'artifact_contract': evidence['artifact_contract']}
        with self.assertRaises(ValueError):
            MutationJournal(fixture.paths).begin(fixture.prepared.source_id, entry, 'create')
        self.assertEqual(len(fixture.transport.calls), 1)

    def test_other_sources_untrusted_candidate_blocks_new_identity_but_never_adopts(self):
        for candidate in ('19000001', '19000000'):
            with self.subTest(candidate=candidate):
                fixture = self.fixture()
                # A retained uncertain response is a collision barrier, even
                # though it is insufficient authority to adopt that record.
                counts = dict.fromkeys(LIMITS, 0)
                counts['create'] = 1
                history = {'schema_version': 1, 'kind': 'modern-production-draft-attempts',
                           'targets': {'FGDC-142': {
                               'binding': 'a' * 64, 'grant_sha256': 'b' * 64,
                               'intent_sha256': 'c' * 64, 'phase': 'started',
                               'identity': None, 'untrusted_candidate_id': candidate,
                               'counts': counts, 'requests': [{
                                   'kind': 'create', 'method': 'POST', 'path': '/api/records',
                                   'body_sha256': 'd' * 64, 'status': 'uncertain',
                                   'attempted_at': fixtures.NOW.isoformat()}]}}}
                atomic_json(fixture.paths.uploads_registry_path + '.modern-v1.json', history)
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(len(fixture.transport.calls), 1)
                self.assertIsNone(self.row(fixture)['identity'])
                with self.assertRaises(ValueError):
                    self.runner(fixture).run(read_only=True)
                self.assertEqual(len(fixture.transport.calls), 1)

    def test_legacy_returned_or_adopted_id_cannot_alias_any_modern_identity_or_candidate(self):
        for kind in ('record', 'parent', 'candidate'):
            with self.subTest(kind=kind):
                fixture = self.fixture()
                if kind == 'candidate':
                    self.change_json(fixture, 0, lambda d: d['parent']['access']['owned_by'].update(user='124'))
                    with self.assertRaises(ValueError):
                        self.runner(fixture).run()
                    self.assertIsNone(self.row(fixture)['identity'])
                    identifier = int(self.row(fixture)['untrusted_candidate_id'])
                else:
                    result = self.runner(fixture).run()
                    identifier = int(result['identity']['id' if kind == 'record' else 'parent_id'])
                evidence = fixture.prepared.evidence
                entry = {'environment': 'production', 'source_sha256': evidence['source_sha256'],
                         'metadata_sha256': evidence['legacy_metadata_sha256'],
                         'artifact_contract': evidence['artifact_contract'], 'deposition_id': identifier}
                journal = MutationJournal(fixture.paths)
                # A different source may retain its own uncertain create, but
                # neither a response nor offline adoption can steal an ID.
                journal.begin('different-source', dict(entry, deposition_id=None), 'create')
                with self.assertRaises(ValueError):
                    journal.confirm('different-source', entry, 'create', {'id': identifier})
                with self.assertRaises(ValueError):
                    journal.adopt('different-source', entry)
                with self.assertRaises(ValueError):
                    journal.begin('another-source', entry, 'metadata')
                retained = MutationJournal(fixture.paths).data['targets']['different-source']
                self.assertIsNone(retained['deposition_id'])
                self.assertEqual(retained['actions']['create']['status'], 'uncertain')

    def test_directory_fsync_failure_prevents_dispatch_and_preserves_barrier(self):
        for fail_at in (1, 2, 3):
            with self.subTest(directory_fsync=fail_at):
                fixture = self.fixture()
                runner = self.runner(fixture)
                original, directories = os.fsync, [0]

                def fail(fd, observed=directories, target=fail_at, fsync=original):
                    if stat.S_ISDIR(os.fstat(fd).st_mode):
                        observed[0] += 1
                        if observed[0] == target:
                            raise OSError('Fixture directory durability failure')
                    return fsync(fd)

                with patch('os.fsync', side_effect=fail), self.assertRaises(OSError):
                    runner.run()
                self.assertTrue(runner.intent_path.exists())
                self.assertEqual(fixture.transport.calls, [])
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(fixture.transport.calls, [])

    def test_expiry_after_durable_create_intent_prevents_transport(self):
        fixture = self.fixture()
        clock = [fixtures.NOW]
        runner = self.runner(fixture, now=lambda: clock[0])
        save = runner.save

        def expire_after_save():
            save()
            if runner.row['counts']['create']:
                clock[0] += timedelta(seconds=601)

        with patch.object(runner, 'save', side_effect=expire_after_save), self.assertRaises(ValueError):
            runner.run()
        self.assertEqual(self.row(fixture)['counts']['create'], 1)
        self.assertEqual(fixture.transport.calls, [])

    def test_ledger_lock_covers_remote_create_and_blocks_competing_runner(self):
        fixture = self.fixture()
        original = fixture.transport.change

        def check(index, response):
            with self.assertRaises(BlockingIOError), ledger_lock(fixture.paths):
                pass
            return original(index, response)

        fixture.transport.change = check
        self.assertTrue(self.runner(fixture).run()['draft_verified'])

    def test_create_identity_state_and_protected_ids_hold_before_init(self):
        mutations = (
            lambda d: d.update(id='17317855'),
            lambda d: d.update(id='10042430'),
            lambda d: d.update(id='15046283'),
            lambda d: d.update(id=19000001),
            lambda d: d.update(id='019000001'),
            lambda d: d.update(is_published=True),
            lambda d: d.update(status='published'),
            lambda d: d.update(versions={'index': 2}),
            lambda d: d.update(pids={'doi': {'identifier': '10.5281/zenodo.17317855'}}),
            lambda d: d['parent']['access']['owned_by'].update(user='124'),
            lambda d: d['links'].update(self='https://example.invalid/records/19000001/draft'),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(fault=index):
                fixture = self.fixture()
                self.change_json(fixture, 0, mutation)
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(len(fixture.transport.calls), 1)
                self.assertIsNone(self.row(fixture)['identity'])

    def test_create_metadata_access_and_validation_error_mismatch_hold_before_init(self):
        mutations = (
            lambda d: d['metadata'].update(title='Different source'),
            lambda d: d['metadata'].update(creators=[]),
            lambda d: d['metadata'].update(additional_descriptions=[]),
            lambda d: d['access'].update(files='public'),
            lambda d: d['files'].update(enabled=False),
            lambda d: d.update(errors=[{'field': 'publisher', 'messages': ['Missing publisher']}]),
            lambda d: d.update(errors=[{'field': 'files.enabled', 'messages': ['Permission denied']}]),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(fault=index):
                fixture = self.fixture()
                self.change_json(fixture, 0, mutation)
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(len(fixture.transport.calls), 1)

    def test_multipart_response_key_transfer_links_and_checksum_fail_closed(self):
        faults = (
            (1, lambda d: d['entries'][0].update(key='another.xml')),
            (1, lambda d: d['entries'].append(copy.deepcopy(d['entries'][0]))),
            (2, lambda d: d.update(transfer={'type': 'remote'})),
            (2, lambda d: d['links'].update(commit='https://example.invalid/commit')),
            (3, lambda d: d.update(status='pending')),
            (3, lambda d: d.update(checksum='md5:' + '0' * 32)),
            (3, lambda d: d.update(size=True)),
        )
        for index, mutation in faults:
            with self.subTest(response_index=index, mutation=repr(mutation)):
                fixture = self.fixture()
                self.change_json(fixture, index, mutation)
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(len(fixture.transport.calls), index + 1)

    def test_readback_brackets_reject_concurrent_metadata_and_revision_changes(self):
        for mutation in (lambda d: d.update(revision_id=d['revision_id'] + 1),
                         lambda d: d['metadata'].update(description='Concurrent change')):
            fixture = self.fixture()
            self.change_json(fixture, 8, mutation)
            with self.assertRaises(ValueError):
                self.runner(fixture).run()
            self.assertEqual(self.row(fixture)['phase'], 'started')
            self.assertEqual(len(fixture.transport.calls), 9)
            self.assertEqual(len(self.writes(fixture)), 4)

    def test_readback_rejects_extra_file_and_changed_downloaded_bytes(self):
        fixture = self.fixture()
        self.change_json(fixture, 5, lambda d: d['entries'].append(copy.deepcopy(d['entries'][0])))
        with self.assertRaises(ValueError):
            self.runner(fixture).run()
        self.assertEqual(len(fixture.transport.calls), 6)
        fixture = self.fixture()
        fixture.transport.change = lambda i, r: (r[0], r[1], r[2] + b'changed') if i == 7 else r
        with self.assertRaises(ValueError):
            self.runner(fixture).run()
        self.assertEqual(len(fixture.transport.calls), 8)
        self.assertEqual(self.row(fixture)['phase'], 'started')

    def test_verified_retry_rejects_revision_or_metadata_drift_without_writes(self):
        for mutation in (lambda d: d.update(revision_id=d['revision_id'] + 1),
                         lambda d: d['metadata'].update(title='Changed after completion')):
            fixture = self.fixture()
            self.runner(fixture).run()
            self.change_json(fixture, 9, mutation)
            with self.assertRaises(ValueError):
                self.runner(fixture).run(read_only=True)
            self.assertEqual(len(self.writes(fixture)), 4)
            self.assertEqual(len(fixture.transport.calls), 10)

    def test_redirect_rate_limit_and_server_errors_are_single_attempt_holds(self):
        for status in (301, 302, 307, 308, 429, 500, 503):
            with self.subTest(status=status):
                fixture = self.fixture()
                fixture.transport.change = lambda i, r, code=status: (code, r[1], r[2])
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(len(fixture.transport.calls), 1)
                self.assertEqual(self.row(fixture)['counts']['create'], 1)

    def test_nonmodern_mime_duplicate_json_keys_and_oversized_body_are_rejected(self):
        responses = ((201, 'text/html', b'{}'),
                     (201, MIME, b'{"id":"19000001","id":"19000002"}'),
                     (201, MIME, b'{' + b' ' * (1024 * 1024)),
                     (201, MIME, b'not json'))
        for response in responses:
            with self.subTest(mime=response[1], size=len(response[2])):
                fixture = self.fixture()
                fixture.transport.change = lambda i, r, changed=response: changed
                with self.assertRaises(ValueError):
                    self.runner(fixture).run()
                self.assertEqual(len(fixture.transport.calls), 1)

    def test_credential_echo_and_exception_text_never_enter_persisted_evidence(self):
        for mode in ('literal', 'escaped', 'exception'):
            with self.subTest(mode=mode):
                fixture = self.fixture()
                if mode == 'exception':
                    def leak(index, response):
                        raise RuntimeError('Authorization: Bearer ' + fixtures.TOKEN)
                    fixture.transport.change = leak
                else:
                    token = fixtures.TOKEN if mode == 'literal' else ''.join(
                        '\\u' + format(ord(c), '04x') for c in fixtures.TOKEN)
                    raw = ('{"error":"' + token + '"}').encode()
                    fixture.transport.change = lambda i, r, changed=raw: (400, MIME, changed)
                with self.assertRaises(ValueError) as caught:
                    self.runner(fixture).run()
                self.assertNotIn(fixtures.TOKEN, str(caught.exception))
                row = self.row(fixture)
                self.assertNotIn(fixtures.TOKEN, json.dumps(row))
                self.assertEqual(row['counts']['create'], 1)
                if mode != 'exception':
                    self.assertTrue(row['requests'][0]['credential_suppressed'])
                    self.assertIsNone(row['requests'][0]['response_sha256'])

    def test_illegal_mutation_routes_cannot_use_a_retained_runner(self):
        fixture = self.fixture()
        runner = self.runner(fixture)
        runner.run()
        for kind, method, path in (
                ('publish', 'POST', '/api/records/19000001/draft/actions/publish'),
                ('metadata', 'PUT', '/api/records/19000001/draft'),
                ('commit', 'DELETE', '/api/records/19000001/draft'),
                ('init', 'POST', '/api/records/19000002/draft/files')):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.call(kind, method, path, 200)
        self.assertEqual(len(fixture.transport.calls), 9)

    def test_corrupt_or_symlinked_journal_cannot_start_new_creation(self):
        for mode in ('corrupt', 'symlink'):
            fixture = self.fixture()
            runner = self.runner(fixture)
            if mode == 'corrupt':
                runner.journal_path.write_bytes(b'{incomplete')
            else:
                other = runner.journal_path.with_suffix('.other')
                other.write_bytes(b'{}')
                runner.journal_path.symlink_to(other)
            with self.assertRaises(ValueError):
                runner.run()
            self.assertEqual(fixture.transport.calls, [])


class ModernSingletonTransportTests(unittest.TestCase):
    def test_user_agent_identifies_the_client_with_a_valid_header_value(self):
        # zenodo.org's edge rejects requests without a User-Agent; the value must
        # name the project, a reachable URL and a contact, and be a legal header value.
        self.assertRegex(USER_AGENT, r'\Apices-metadata-transformer/\d+\.\d+ \(\+https://[^\s();]+; [^\s()@;]+@[^\s();]+\)\Z')
        self.assertTrue(USER_AGENT.isascii() and USER_AGENT.isprintable() and USER_AGENT == USER_AGENT.strip())

    def test_mac_wire_uses_fixed_host_exact_body_and_modern_headers_without_redirects(self):
        # Every request shape carries the identifying User-Agent: body-bearing
        # writes and the body-less GETs used by capture, readback and recovery.
        scenarios = (('POST', '/api/records', b'{"metadata":{}}', 'application/json', 301, MIME),
                     ('PUT', '/api/records/19000001/draft/files/FGDC-141.xml/content',
                      b'<metadata/>', 'application/octet-stream', 200, MIME),
                     ('GET', '/api/records/19000001/draft', None, None, 200, MIME),
                     ('GET', '/api/requests/0f2e5c1a-5d2e-4a5b-9c7d-1234567890ab', None, None, 200,
                      'application/json'))
        for method, path, body, content_type, status, accept in scenarios:
            with self.subTest(method=method, status=status, accept=accept):
                response = Mock(status=status)
                response.read1.side_effect = [b'{"fixture":true}', b'']
                response.getheader.return_value = accept
                connection = Mock()
                connection.getresponse.return_value = response
                context = Mock(keylog_filename='dummy-must-be-disabled')
                with (patch('scripts.modern_singleton_executor.platform.system', return_value='Darwin'),
                      patch('scripts.modern_singleton_executor.ssl.create_default_context', return_value=context),
                      patch('scripts.modern_singleton_executor.http.client.HTTPSConnection',
                            return_value=connection) as constructor,
                      patch('scripts.modern_singleton_executor.signal.signal'),
                      patch('scripts.modern_singleton_executor.signal.setitimer', return_value=(0, 0)),
                      patch('scripts.modern_singleton_executor.time.monotonic', return_value=10)):
                    result = Transport(fixtures.TOKEN).request(method, path, body, timeout=5, accept=accept)
                self.assertEqual((result.status, result.mime, result.body), (status, accept, b'{"fixture":true}'))
                self.assertTrue(result.complete)
                constructor.assert_called_once_with('zenodo.org', timeout=5, context=context)
                self.assertIsNone(context.keylog_filename)
                expected = {'Authorization': 'Bearer ' + fixtures.TOKEN, 'Accept': accept,
                            'Accept-Encoding': 'identity', 'Connection': 'close', 'User-Agent': USER_AGENT}
                if body is not None:
                    expected.update({'Content-Type': content_type, 'Content-Length': str(len(body))})
                connection.request.assert_called_once_with(method, path, body=body, headers=expected)
                self.assertEqual([call.args for call in response.getheader.call_args_list], [('Content-Type', ''), ('Location',)])
                connection.close.assert_called_once()
                self.assertTrue(all(0 < call.args[0] <= 5 for call in connection.sock.settimeout.call_args_list))

    def test_mac_transport_bounds_response_bytes_and_deadline_and_always_closes(self):
        for fault in ('oversize', 'deadline'):
            with self.subTest(fault=fault):
                response = Mock(status=200)
                if fault == 'oversize':
                    response.read1.side_effect = [b'x' * 8192] * (MAX_BYTES // 8192) + [b'x']
                else:
                    response.read1.return_value = b''
                connection = Mock()
                connection.getresponse.return_value = response
                with (patch('scripts.modern_singleton_executor.platform.system', return_value='Darwin'),
                      patch('scripts.modern_singleton_executor.ssl.create_default_context', return_value=Mock()),
                      patch('scripts.modern_singleton_executor.http.client.HTTPSConnection',
                            return_value=connection) as constructor,
                      patch('scripts.modern_singleton_executor.signal.signal'),
                      patch('scripts.modern_singleton_executor.signal.setitimer', return_value=(0, 0)),
                      patch('scripts.modern_singleton_executor.time.monotonic',
                            side_effect=[0, 1, 21] if fault == 'deadline' else None,
                            return_value=10)):
                    result = Transport(fixtures.TOKEN).request('GET', '/api/records/19000001/draft', None, timeout=20)
                    self.assertFalse(result.complete)
                    self.assertEqual(result.read_error, 'body_limit' if fault == 'oversize' else 'read_interrupted')
                constructor.assert_called_once()
                connection.request.assert_called_once()
                connection.close.assert_called_once()
                if fault == 'oversize':
                    self.assertEqual(response.read1.call_count, MAX_BYTES // 8192 + 1)
                    self.assertEqual(response.read1.call_args.args, (1,))
                else:
                    response.read1.assert_not_called()

    def test_cloud_constructor_and_invalid_timeout_refuse_before_connection(self):
        with (patch('scripts.modern_singleton_executor.platform.system', return_value='Linux'),
              patch('scripts.modern_singleton_executor.http.client.HTTPSConnection') as constructor,
              patch('scripts.modern_singleton_executor.ssl.create_default_context') as tls):
            with self.assertRaises(ValueError):
                Transport(fixtures.TOKEN)
            constructor.assert_not_called()
            tls.assert_not_called()
        with (patch('scripts.modern_singleton_executor.platform.system', return_value='Darwin'),
              patch('scripts.modern_singleton_executor.http.client.HTTPSConnection') as constructor,
              patch('scripts.modern_singleton_executor.ssl.create_default_context') as tls):
            transport = Transport(fixtures.TOKEN)
            for timeout in (0, -1, 21):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    transport.request('GET', '/api/records/19000001/draft', None, timeout=timeout)
            constructor.assert_not_called()
            tls.assert_not_called()


class ProductionTokenTests(unittest.TestCase):
    SERVICE = 'pices-zenodo-production'
    COMMAND = ['/usr/bin/security', 'find-generic-password', '-s', 'pices-zenodo-production', '-w']

    @contextlib.contextmanager
    def mac_terminal(self, *, tty=True, system='Darwin'):
        stdin = Mock()
        stdin.isatty.return_value = tty
        with (patch('scripts.modern_singleton_executor.platform.system', return_value=system),
              patch('scripts.modern_singleton_executor.sys.stdin', stdin)):
            yield

    def test_keychain_token_is_read_from_the_named_login_item_without_prompting(self):
        completed = Mock(returncode=0, stdout='keychain-token-value-0123456789\r\n', stderr='')
        with (self.mac_terminal(),
              patch('scripts.modern_singleton_executor.subprocess.run', return_value=completed) as run,
              patch('scripts.modern_singleton_executor.getpass.getpass', side_effect=AssertionError('no prompt'))):
            token = production_token('Production token: ', self.SERVICE, action='execute')
        self.assertEqual(token, 'keychain-token-value-0123456789')
        run.assert_called_once_with(self.COMMAND, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                    timeout=30, check=False)

    def test_keychain_failures_and_bad_service_names_hold_without_a_prompt(self):
        cases = ((self.SERVICE, Mock(returncode=44, stdout='', stderr='The specified item could not be found')),
                 (self.SERVICE, Mock(returncode=1, stdout='looks-like-a-token-0123456789\n', stderr='')),
                 (self.SERVICE, Mock(returncode=0, stdout='\n', stderr='')),
                 (self.SERVICE, Mock(returncode=0, stdout='two\nlines\n', stderr='')),
                 ('zenodo-production', None), ('bad service name', None), ('', None), ('../x', None),
                 ('-w', None), ('pices-' + 'x' * 121, None))
        for service, completed in cases:
            with self.subTest(service=service):
                with (self.mac_terminal(),
                      patch('scripts.modern_singleton_executor.subprocess.run', return_value=completed) as run,
                      patch('scripts.modern_singleton_executor.getpass.getpass',
                            side_effect=AssertionError('no prompt')),
                      self.assertRaises(Held)):
                    production_token('Production token: ', service, action='execute')
                if completed is None:
                    run.assert_not_called()

    def test_both_token_routes_require_a_mac_terminal_and_the_prompt_never_spawns_a_process(self):
        for system, tty in (('Linux', True), ('Darwin', False)):
            with self.subTest(system=system, tty=tty):
                with (self.mac_terminal(tty=tty, system=system),
                      patch('scripts.modern_singleton_executor.subprocess.run',
                            side_effect=AssertionError('no process')) as run,
                      patch('scripts.modern_singleton_executor.getpass.getpass',
                            side_effect=AssertionError('no prompt')) as prompt):
                    for keychain in (self.SERVICE, None):
                        with self.assertRaises(Held):
                            production_token('Production token: ', keychain, action='execute')
                    run.assert_not_called()
                    prompt.assert_not_called()
        with (self.mac_terminal(),
              patch('scripts.modern_singleton_executor.subprocess.run', side_effect=AssertionError('no process')),
              patch('scripts.modern_singleton_executor.getpass.getpass',
                    return_value='typed-token-0123456789') as prompt):
            self.assertEqual(production_token('Production token: ', action='execute'), 'typed-token-0123456789')
            prompt.assert_called_once_with('Production token: ')

    def test_keychain_route_is_refused_for_publish_before_any_lookup_and_bad_shapes_hold(self):
        with (self.mac_terminal(),
              patch('scripts.modern_singleton_executor.subprocess.run', side_effect=AssertionError('no process')) as run,
              patch('scripts.modern_singleton_executor.getpass.getpass', side_effect=AssertionError('no prompt')),
              self.assertRaises(Held)):
            production_token('Production token: ', self.SERVICE, action='publish')
        run.assert_not_called()
        with (self.mac_terminal(),
              patch('scripts.modern_singleton_executor.subprocess.run', side_effect=AssertionError('no process')),
              self.assertRaises(Held)):
            production_token('Production token: ', self.SERVICE, action='unlisted')
        for stdout in ('short\n', 'has space inside 0123456789\n', 'non-ascii-\u00e9-0123456789\n', 'x' * 4097 + '\n'):
            with self.subTest(stdout=stdout[:12]):
                with (self.mac_terminal(),
                      patch('scripts.modern_singleton_executor.subprocess.run',
                            return_value=Mock(returncode=0, stdout=stdout, stderr='')),
                      self.assertRaises(Held)):
                    production_token('Production token: ', self.SERVICE, action='execute')
        with (self.mac_terminal(),
              patch('scripts.modern_singleton_executor.getpass.getpass', return_value='short'),
              self.assertRaises(Held)):
            production_token('Production token: ', action='publish')

    def test_insecure_prompt_fallback_is_an_error_not_a_token(self):
        def echoing_prompt(prompt):
            warnings.warn('Password input may be echoed.', getpass.GetPassWarning, stacklevel=2)
            return 'echoed-token-0123456789'
        with (self.mac_terminal(),
              patch('scripts.modern_singleton_executor.getpass.getpass', side_effect=echoing_prompt),
              self.assertRaises(getpass.GetPassWarning)):
            production_token('Production token: ', action='execute')


if __name__ == '__main__':
    unittest.main()
