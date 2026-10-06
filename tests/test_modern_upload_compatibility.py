"""Synthetic offline contracts for optional upload commit and binary MIME lists.

These fixtures extend the existing source-derived fake effects. They are not
retained provider captures and make no live production compatibility claim.
"""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_singleton as mapping
from scripts import modern_singleton_executor as draft
from scripts.production_mutations import reject_modern_attempt
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_exxon_coverage as exxon_tests
from tests import test_modern_organizational_coverage as organizational_tests


class CompatibilityTransport(fixtures.FakeTransport):
    """Synthetic completed-on-content response, using the unchanged fake routes."""

    def __init__(self, fixture, *, complete_on_content=False):
        super().__init__(fixture)
        self.complete_on_content = complete_on_content
        self.binary_mime = 'application/octet-stream'
        self.json_mime = draft.MIME
        self.wire_change = lambda index, response: response
        self.change = exxon_tests.canonical_person_names

    def request(self, method, path, body, *, timeout):
        index = len(self.calls)
        if self.complete_on_content and method == 'PUT' and path == self.file + '/content':
            if self.fail_index != index or self.effect_before_fail:
                # Completion need not increment the record revision: the complete
                # five-GET snapshot must simply bracket one consistent revision.
                self.complete = True
        status, mime, raw = super().request(method, path, body, timeout=timeout)
        mime = self.binary_mime if method == 'GET' and path == self.file + '/content' else self.json_mime
        return self.wire_change(index, (status, mime, raw))


class ModernUploadCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=['FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839'])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def fixture(self, sid='FGDC-141', *, completed=False):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        fixture = fixtures.Fixture(directory.name, self.prepared_root, source_id=sid)
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=completed)
        return fixture

    @staticmethod
    def journal_path(fixture):
        return Path(fixture.paths.uploads_registry_path + '.modern-v1.json')

    def row(self, fixture):
        return mapping.parse(self.journal_path(fixture).read_bytes())['targets'][fixture.prepared.source_id]

    def assert_full_lifecycle(self, sid, completed):
        fixture = self.fixture(sid, completed=completed)
        fixture.transport.binary_mime = 'application/octet-stream, application/octet-stream'
        harness = organizational_tests.PublicationFixture(fixture)
        row = self.row(fixture)
        commit = int(not completed)
        self.assertEqual(row['counts'], dict(draft.LIMITS, get=5, commit=commit))
        expected_methods = ['POST', 'POST', 'PUT'] + ([] if completed else ['POST']) + ['GET'] * 5
        self.assertEqual([call[0] for call in fixture.transport.calls], expected_methods)
        self.assertEqual(fixture.transport.calls[0], ('POST', '/api/records', fixture.prepared.body))
        self.assertEqual(fixture.transport.calls[2], ('PUT', fixture.transport.file + '/content', fixture.prepared.xml))
        self.assertEqual(row['create_revision'], 1)
        self.assertEqual(row['verified_revision'], 1 if completed else 2)
        if completed:
            self.assertEqual(row['upload_completion'], {
                'schema_version': 1, 'kind': 'content-completed-v1', 'request_index': 2,
                'response_sha256': row['requests'][2]['response_sha256']})
        else:
            self.assertNotIn('upload_completion', row)
        first_writes = [call for call in fixture.transport.calls if call[0] != 'GET']
        retry = fixture.runner().run(read_only=True)
        self.assertEqual(retry['counts'], dict(draft.LIMITS, commit=commit))
        self.assertEqual(len(fixture.transport.calls), 13 if completed else 14)
        self.assertEqual([call for call in fixture.transport.calls if call[0] != 'GET'], first_writes)
        harness.prepared, harness.bound = harness.bridge()
        original_history = self.journal_path(fixture).read_bytes()
        # The existing publication fake parses its inner canonical MIME before
        # constructing a response. Inject duplicate headers after that conversion.
        fixture.transport.binary_mime = 'application/octet-stream'
        def duplicate_binary(index, response):
            status, media, raw = response
            if media == 'application/octet-stream':
                media += ', application/octet-stream'
            return status, media, raw
        harness.transport.change = duplicate_binary
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        self.assertEqual(len(snapshot['responses']), 5)
        self.assertEqual(snapshot['responses'][3]['media_type'], 'application/octet-stream')
        self.assertEqual(snapshot['revision_id'], 1 if completed else 2)
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['published_verified'])
        self.assertTrue(result['community_submission_verified'])
        retry = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(retry['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual(sum(call[0] == 'POST' for call in harness.transport.calls), 2)
        self.assertEqual(self.journal_path(fixture).read_bytes(), original_history)
        self.assertFalse(retry['community_membership_verified'])
        self.assertFalse(retry['doi_registration_verified'])

    def test_pending_content_keeps_commit_and_complete_publication_workflow(self):
        self.assert_full_lifecycle('FGDC-141', False)

    def test_completed_exxon_content_skips_commit_without_revision_increment_through_publication_retry(self):
        self.assert_full_lifecycle('FGDC-1839', True)

    def test_completed_content_corruptions_hold_before_commit_or_readback(self):
        changes = {
            'key': lambda value: value.update(key='different.xml'),
            'checksum': lambda value: value.update(checksum='md5:' + '0' * 32),
            'size': lambda value: value.update(size=True),
            'size_mismatch': lambda value: value.update(size=value['size'] + 1),
            'link': lambda value: value['links'].update(content='https://other.invalid/content'),
            'transfer': lambda value: value.update(transfer={'type': 'R'}),
            'status': lambda value: value.update(status='unknown'),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                fixture = self.fixture(completed=True)
                def mutate(index, status, value, change=change):
                    if index == 2:
                        change(value)
                    return status, value
                fixture.transport.change = mutate
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual([call[0] for call in fixture.transport.calls], ['POST', 'POST', 'PUT'])
                row = self.row(fixture)
                self.assertEqual(row['counts'], dict(get=0, create=1, init=1, content=1, commit=0))
                self.assertNotIn('upload_completion', row)

    def test_completed_snapshot_still_requires_exact_file_identity_and_bracketed_revision(self):
        for mode in ('identity', 'revision', 'descriptor', 'content'):
            with self.subTest(mode=mode):
                fixture = self.fixture(completed=True)
                def corrupt(index, response, mode=mode):
                    status, media, raw = response
                    if mode == 'content' and index == 6:
                        raw += b'\n'
                    elif (mode in ('identity', 'revision') and index == 7) or (mode == 'descriptor' and index == 5):
                        value = mapping.parse(raw)
                        if mode == 'identity':
                            value['parent']['id'] = '19000002'
                        elif mode == 'revision':
                            value['revision_id'] += 1
                        else:
                            value['checksum'] = 'md5:' + '0' * 32
                        raw = mapping.encode(value)
                    return status, media, raw
                fixture.transport.wire_change = corrupt
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(sum(call[0] != 'GET' for call in fixture.transport.calls), 3)
                self.assertEqual(self.row(fixture)['phase'], 'started')
                self.assertEqual(self.row(fixture)['counts']['commit'], 0)
                self.assertIn('upload_completion', self.row(fixture))

    def test_uncertain_content_has_no_replay_speculative_commit_new_grant_or_journal_reset(self):
        for effect in (False, True):
            with self.subTest(remote_effect=effect):
                fixture = self.fixture(completed=True)
                fixture.transport.fail_index, fixture.transport.effect_before_fail = 2, effect
                runner = fixture.runner()
                with self.assertRaises(ValueError):
                    runner.run()
                self.assertEqual(fixture.transport.complete, effect)
                row = self.row(fixture)
                self.assertEqual(row['counts'], dict(get=0, create=1, init=1, content=1, commit=0))
                self.assertNotIn('upload_completion', row)
                intent = runner.intent_path.read_bytes()
                for readonly in (False, True):
                    with self.assertRaises(ValueError):
                        fixture.runner().run(read_only=readonly)
                fixture.change_proof(reviewed_by='Renewed offline evidence reviewer')
                fixture.change_grant(reviewed_by='Renewed offline parent reviewer')
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                runner.journal_path.unlink()
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(runner.intent_path.read_bytes(), intent)
                self.assertEqual(len(fixture.transport.calls), 3)

    def test_branch_marker_must_be_durable_before_any_completed_readback(self):
        fixture = self.fixture(completed=True)
        atomic = draft.atomic_json
        def fail_marker(path, value):
            if any('upload_completion' in row for row in value.get('targets', {}).values()):
                raise OSError('Synthetic durability failure')
            return atomic(path, value)
        with patch.object(draft, 'atomic_json', side_effect=fail_marker), self.assertRaises(OSError):
            fixture.runner().run()
        self.assertTrue(fixture.transport.complete)
        self.assertNotIn('upload_completion', self.row(fixture))
        self.assertEqual(len(fixture.transport.calls), 3)
        for readonly in (False, True):
            with self.assertRaises(ValueError):
                fixture.runner().run(read_only=readonly)
        self.assertEqual(len(fixture.transport.calls), 3)

    def test_missing_malformed_or_unbound_completed_marker_prevents_readback_and_bridge(self):
        fixture = self.fixture(completed=True)
        harness = organizational_tests.PublicationFixture(fixture)
        path = self.journal_path(fixture)
        original = path.read_bytes()
        changes = {
            'missing': lambda row: row.pop('upload_completion'),
            'null': lambda row: row.update(upload_completion=None),
            'kind': lambda row: row['upload_completion'].update(kind='unreviewed'),
            'schema_type': lambda row: row['upload_completion'].update(schema_version=True),
            'index': lambda row: row['upload_completion'].update(request_index=1),
            'index_type': lambda row: row['upload_completion'].update(request_index=True),
            'hash': lambda row: row['upload_completion'].update(response_sha256='0' * 64),
            'extra': lambda row: row['upload_completion'].update(assumed=True),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                journal = mapping.parse(original)
                change(journal['targets'][fixture.prepared.source_id])
                path.write_bytes(mapping.encode(journal))
                with self.assertRaises(ValueError):
                    fixture.runner().run(read_only=True)
                with self.assertRaises(ValueError):
                    harness.bridge()
                self.assertEqual(len(fixture.transport.calls), 8)
        path.write_bytes(original)

    def test_completed_marker_cannot_coexist_with_any_commit_attempt(self):
        for completed in (False, True):
            with self.subTest(completed=completed):
                fixture = self.fixture(completed=completed)
                harness = organizational_tests.PublicationFixture(fixture)
                path = self.journal_path(fixture)
                journal = mapping.parse(path.read_bytes())
                row = journal['targets'][fixture.prepared.source_id]
                row['upload_completion'] = {'schema_version': 1, 'kind': 'content-completed-v1',
                                            'request_index': 2, 'response_sha256': row['requests'][2]['response_sha256']}
                if completed:
                    receipt = copy.deepcopy(row['requests'][2])
                    receipt.update(kind='commit', method='POST', path=fixture.transport.file + '/commit', body_sha256=None)
                    row['requests'].insert(3, receipt)
                    row['counts']['commit'] = 1
                path.write_bytes(mapping.encode(journal))
                before = len(fixture.transport.calls)
                with self.assertRaises(ValueError):
                    fixture.runner().run(read_only=True)
                with self.assertRaises(ValueError):
                    harness.bridge()
                self.assertEqual(len(fixture.transport.calls), before)

    def test_durable_completion_prohibits_commit_even_with_unspent_commit_budget(self):
        fixture = self.fixture(completed=True)
        fixture.runner().run()
        path = self.journal_path(fixture)
        journal = mapping.parse(path.read_bytes())
        journal['targets'][fixture.prepared.source_id]['phase'] = 'started'
        path.write_bytes(mapping.encode(journal))
        original = path.read_bytes()
        runner = fixture.runner()
        runner.load()
        with self.assertRaises(ValueError):
            runner.call('commit', 'POST', fixture.transport.file + '/commit', 200)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(fixture.transport.calls), 8)
        self.assertEqual(self.row(fixture)['counts']['commit'], 0)

    def test_completed_marker_is_not_authority_for_a_different_content_transcript(self):
        fixture = self.fixture(completed=True)
        harness = organizational_tests.PublicationFixture(fixture)
        path = self.journal_path(fixture)
        original = path.read_bytes()
        changes = {'method': 'POST', 'path': fixture.transport.file.replace('19000001', '19000002') + '/content',
                   'body_sha256': '0' * 64, 'http_status': 500, 'credential_suppressed': True}
        for key, value in changes.items():
            with self.subTest(field=key):
                journal = mapping.parse(original)
                journal['targets'][fixture.prepared.source_id]['requests'][2][key] = value
                path.write_bytes(mapping.encode(journal))
                with self.assertRaises(ValueError):
                    fixture.runner().run(read_only=True)
                with self.assertRaises(ValueError):
                    harness.bridge()
                self.assertEqual(len(fixture.transport.calls), 8)
        path.write_bytes(original)

    def test_historical_pr38_four_write_sources_bridge_without_rewriting_receipts(self):
        for sid in ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839'):
            with self.subTest(source=sid):
                harness = organizational_tests.PublicationFixture(self.fixture(sid))
                current = harness.prepared
                retained = exxon_tests.save_historical_runtime(harness, publication.PR38_RUNTIME)
                harness.prepared, harness.bound = harness.bridge()
                self.assertEqual(harness.prepared, current)
                self.assertEqual(harness.bound['original_runtime_sha256'], publication.PR38_RUNTIME)
                harness.grant('capture')
                self.assertTrue(harness.runner('capture').run()['capture_verified'])
                self.assertEqual({path: path.read_bytes() for path in retained}, retained)

    def test_three_write_completed_marker_cannot_be_backdated_to_pr38(self):
        harness = organizational_tests.PublicationFixture(self.fixture('FGDC-1839', completed=True))
        retained = exxon_tests.save_historical_runtime(harness, publication.PR38_RUNTIME)
        with self.assertRaises(ValueError):
            harness.bridge()
        harness.grant('capture')
        with self.assertRaises(ValueError):
            harness.runner('capture').run()
        self.assertEqual(harness.transport.calls, [])
        self.assertEqual({path: path.read_bytes() for path in retained}, retained)

    def test_binary_mime_normalization_accepts_only_single_or_identical_bare_lists(self):
        for media in ('application/octet-stream', 'application/xml', 'text/xml'):
            for raw in (media, media + '; charset=utf-8', media + ', ' + media,
                        ' ' + media.upper() + ' , ' + media + ' ', ', '.join([media] * 3)):
                with self.subTest(header=raw):
                    self.assertEqual(draft.response_media_type(raw, binary=True), media)
        self.assertEqual(draft.response_media_type(draft.MIME), draft.MIME)
        self.assertEqual(draft.response_media_type(draft.MIME + '; charset=utf-8'), draft.MIME)

    def test_binary_mime_lists_reject_mixed_empty_parameterized_malformed_and_control_values(self):
        values = [None, '', 'application/octet-stream,', ',application/octet-stream',
                  'application/octet-stream,,application/octet-stream', 'application/octet-stream, text/xml',
                  'application/octet-stream, application/octet-stream, text/html', 'image/png, image/png',
                  'application/octet-stream; charset=utf-8, application/octet-stream; charset=utf-8',
                  'application/octet-stream; charset=utf-8, application/octet-stream; charset=ascii',
                  'application/octet-stream; charset=utf-8, text/html', 'application/octet-stream garbage, application/octet-stream garbage',
                  'application/octet-stream\r\n', 'application/octet-stream\x00',
                  draft.MIME + ', ' + draft.MIME]
        for value in values:
            with self.subTest(header=value), self.assertRaises(ValueError):
                draft.response_media_type(value, binary=True)
        for value in (draft.MIME + ', ' + draft.MIME, draft.MIME + '; charset=utf-8, text/html',
                      draft.MIME + '\n', 'application/json, application/json'):
            with self.subTest(header=value), self.assertRaises(ValueError):
                draft.response_media_type(value)

    def test_mixed_binary_header_after_semicolon_stops_actual_readback(self):
        fixture = self.fixture(completed=True)
        fixture.transport.binary_mime = 'application/octet-stream; charset=utf-8, text/html'
        with self.assertRaises(ValueError):
            fixture.runner().run()
        self.assertEqual(self.row(fixture)['counts'], dict(get=4, create=1, init=1, content=1, commit=0))
        self.assertEqual(len(fixture.transport.calls), 7)

    def test_duplicate_json_header_is_refused_before_identity_or_next_write(self):
        fixture = self.fixture(completed=True)
        fixture.transport.json_mime = draft.MIME + ', ' + draft.MIME
        with self.assertRaises(ValueError):
            fixture.runner().run()
        self.assertEqual(len(fixture.transport.calls), 1)
        self.assertIsNone(self.row(fixture)['identity'])

    def test_saved_snapshot_cannot_hide_a_second_binary_media_type_after_parameters(self):
        harness = organizational_tests.PublicationFixture(self.fixture(completed=True))
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        snapshot['responses'][3]['media_type'] = 'application/octet-stream; charset=utf-8, text/html'
        with self.assertRaises(ValueError):
            publication.validate_snapshot(harness.prepared, harness.bound, snapshot)
        self.assertEqual(harness.transport.calls, [])

    def test_rejected_header_retains_observed_doi_only_as_cross_source_conflict_evidence(self):
        harness = organizational_tests.PublicationFixture(self.fixture(completed=True))
        documents = harness.ready()
        def corrupt_header(index, response):
            status, media, raw = response
            return (status, draft.MIME + ';\tcharset=utf-8', raw) if index == 5 else response
        harness.transport.change = corrupt_header
        with self.assertRaises(ValueError):
            harness.runner(documents=documents).run()
        path = Path(harness.fixture.paths.uploads_registry_path + '.modern-publication-v1.json')
        row = mapping.parse(path.read_bytes())['targets'][harness.prepared.source_id]
        self.assertIn(harness.transport.doi, row['doi_claims'])
        self.assertNotIn('published_baseline', row)
        self.assertNotIn('published_verified', row)
        self.assertEqual(row['counts']['publish'], 1)
        self.assertEqual(row['counts']['inclusion'], 0)
        self.assertEqual(len(harness.transport.calls), 6)
        with self.assertRaises(ValueError):
            reject_modern_attempt(harness.fixture.paths, 'FGDC-4', 98765, harness.transport.doi)
        reject_modern_attempt(harness.fixture.paths, 'FGDC-4', 98765, '10.5281/zenodo.98765')
        with self.assertRaises(ValueError):
            harness.runner(documents=documents).run()
        self.assertEqual(len(harness.transport.calls), 6)

    def test_completed_content_redirect_and_token_echo_never_commit_or_leak(self):
        for mode in ('redirect', 'token'):
            with self.subTest(mode=mode):
                fixture = self.fixture(completed=True)
                def change(index, response, mode=mode):
                    if index != 2:
                        return response
                    status, media, raw = response
                    return (301, media, raw) if mode == 'redirect' else (status, media, fixtures.TOKEN.encode())
                fixture.transport.wire_change = change
                with self.assertRaises(ValueError) as caught:
                    fixture.runner().run()
                raw = self.journal_path(fixture).read_bytes()
                self.assertNotIn(fixtures.TOKEN, str(caught.exception))
                self.assertNotIn(fixtures.TOKEN.encode(), raw)
                row = self.row(fixture)
                self.assertNotIn('upload_completion', row)
                self.assertEqual(len(fixture.transport.calls), 3)
                self.assertEqual(row['counts']['commit'], 0)
                if mode == 'token':
                    self.assertTrue(row['requests'][2]['credential_suppressed'])
                    self.assertIsNone(row['requests'][2]['response_sha256'])


if __name__ == '__main__':
    unittest.main()
