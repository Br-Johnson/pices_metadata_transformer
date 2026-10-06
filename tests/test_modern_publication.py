"""Offline publication effects, interrupted requests and exact source history."""

import copy
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_singleton_executor as draft
from scripts.modern_singleton import encode, parse, sha
from scripts.production_mutations import reject_modern_attempt
from scripts.release_manifest import prepare_release
from tests import modern_singleton_fixtures as fixtures
from tests.test_modern_publication_qa import approve, raw_duplicates

NOW = fixtures.NOW + timedelta(hours=1)
COMMUNITY = '12345678-1234-4234-9234-123456789012'
OBJECT = {k: '00000000-0000-4000-8000-' + str(i).zfill(12)
          for i, k in enumerate(('file_id', 'version_id', 'bucket_id'), 1)}


def community(bound, *, now=NOW, include_directly=True):
    """Explicit synthetic authority, not evidence of actual PICES permissions."""
    value = {
        'schema_version': 1, 'kind': 'modern-pices-authority-v1', 'origin': draft.ORIGIN,
        'id': COMMUNITY, 'slug': 'pices', 'parent_id': None,
        'owner': bound['identity']['owner'], 'record_id': bound['identity']['id'],
        'visibility': 'public', 'submission_policy': 'open', 'review_policy': 'members',
        'permissions': dict(manage=True, read_draft=True, submit_record=True, include_directly=include_directly),
        'captured_by': 'Dummy Mac', 'checked_at': now.isoformat(),
        'expires_at': (now + timedelta(hours=1)).isoformat(),
        'evidence': [{'role': 'community', 'reference': 'offline-community-fixture', 'sha256': 'c' * 64},
                     {'role': 'permissions', 'reference': 'offline-permission-fixture', 'sha256': 'd' * 64}],
    }
    value.update(reviewed_by='Dummy parent', reviewed_at=now.isoformat(),
                 reviewed_projection_sha256=sha(encode(value)))
    return value


class Transport:
    """Synthetic community-first service; never personal-only publication."""
    def __init__(self, fixture):
        self.fixture = fixture
        self.inner = fixture.transport
        self.calls = []
        self.published = False
        self.included = False
        self.review_created = False
        self.submitted = False
        self.accept_on_submit = True
        self.request_status = None
        self.review_revision_delta = 0
        self.fail_before = self.fail_after = None
        self.change = lambda index, response: response
        self.doi = '10.5281/zenodo.19000001'
        self.request_id = 'opaque-safe-request-1'

    def accept(self):
        assert self.submitted
        self.request_status = 'accepted'
        self.published = self.included = True

    def request_record(self):
        return {'id': self.request_id, 'type': 'community-submission', 'status': self.request_status,
                'is_open': self.request_status == 'submitted', 'is_closed': self.request_status == 'accepted',
                'topic': {'record': self.inner.identifier}, 'receiver': {'community': COMMUNITY},
                'created_by': {'user': '123'}}

    def request(self, method, path, body, *, timeout, accept=draft.MIME):
        index = len(self.calls)
        self.calls.append((method, path, body, accept))
        assert 0 < timeout <= draft.TIMEOUT
        if index == self.fail_before:
            raise TimeoutError(fixtures.TOKEN)
        base = '/api/records/' + self.inner.identifier
        if path.startswith('/api/requests/'):
            assert method == 'GET' and body is None and accept == 'application/json'
            assert self.review_created and path == '/api/requests/' + self.request_id
            response = 200, accept, encode(self.request_record())
        elif path == base + '/draft/review':
            assert method == 'PUT' and accept == 'application/json'
            assert not self.review_created and not self.published
            assert parse(body) == {'type': 'community-submission', 'receiver': {'community': COMMUNITY}}
            self.review_created, self.request_status = True, 'created'
            self.inner.revision += self.review_revision_delta
            response = 200, accept, encode(self.request_record())
        elif path == base + '/draft/actions/submit-review':
            assert self.review_created and not self.submitted and not self.published
            assert method == 'POST' and accept == 'application/json' and parse(body) == {'require_review': False}
            self.submitted, self.request_status = True, 'submitted'
            if self.accept_on_submit:
                self.accept()
            response = 202, accept, encode(self.request_record())
        else:
            assert method == 'GET' and body is None
            translated = path if '/draft' in path else path.replace(base, self.inner.base, 1)
            if '/draft' not in path:
                assert self.published and self.included
            status, mime, raw = self.inner.request('GET', translated, None, timeout=timeout)
            if mime != 'application/octet-stream':
                value = parse(raw)
                def enhance(entry):
                    entry.update(OBJECT)
                    if self.published:
                        entry['links'] = {k: v.replace('/draft', '') for k, v in entry['links'].items() if k != 'commit'}
                if value.get('key'):
                    enhance(value)
                elif isinstance(value.get('entries'), list):
                    for entry in value['entries']:
                        enhance(entry)
                elif 'metadata' in value:
                    if self.published:
                        value.update(is_published=True, status='published', created=NOW.isoformat(), revision_id=1,
                                     pids={'doi': {'provider': 'datacite', 'identifier': self.doi},
                                           'oai': {'provider': 'oai', 'identifier': 'oai:zenodo.org:' + self.inner.identifier}})
                        value['parent']['pids'] = {'doi': {'provider': 'datacite', 'identifier': '10.5281/zenodo.19000000'}}
                        value['parent']['communities'] = {'ids': [COMMUNITY], 'default': COMMUNITY}
                        value['links'] = {k: v.replace('/draft', '') for k, v in value['links'].items()}
                    elif self.review_created:
                        value['status'] = 'draft_with_review'
                        value['parent']['review'] = {'id': self.request_id, 'type': 'community-submission',
                                                     'receiver': {'community': COMMUNITY}}
                raw = encode(value)
            response = status, mime, raw
        if index == self.fail_after:
            raise TimeoutError('Lost dummy response ' + fixtures.TOKEN)
        return self.change(index, response)


class ModernPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=['FGDC-141'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fixture = fixtures.Fixture(Path(self.temp.name), self.prepared_root)
        self.fixture.runner().run()
        self.packet = Path(self.temp.name) / 'preparation.json'
        self.packet.write_bytes(encode({'binding': self.fixture.prepared.binding,
                                       'evidence': self.fixture.prepared.evidence, 'provider_requests': 0}))
        self.prepared, self.bound = self.bridge()
        self.transport = Transport(self.fixture)
        self.grant_path = Path(self.temp.name) / 'new-grant.json'

    def bridge(self):
        f = self.fixture
        return publication.bridge(f.json_file, f.paths, self.packet, f.grant_path, f.proof_path)

    def grant(self, action, documents=None):
        value = {'schema_version': 1, 'kind': 'modern-singleton-' + action + '-grant-v1',
                 'approved': True, 'executor': draft.EXECUTOR, 'origin': draft.ORIGIN,
                 'binding': self.bound['binding'], 'state_root': str(draft.state_root(self.fixture.paths)),
                 'owner': '123', 'limits': publication.CAPTURE_LIMITS if action == 'capture' else publication.PUBLISH_LIMITS,
                 'started_at': NOW.isoformat(), 'expires_at': (NOW + timedelta(seconds=600)).isoformat(),
                 'reviewed_by': 'Dummy parent reviewer',
                 'token_scope': publication.CAPTURE_TOKEN_SCOPE if action == 'capture' else publication.PUBLICATION_TOKEN_SCOPE,
                 'documents': {k: sha(p.read_bytes()) for k, p in (documents or {}).items()}}
        if action == 'publish':
            value.update(schema_version=2, kind='modern-singleton-publish-grant-v2',
                         exclusive_writer=True, community=getattr(self, 'community_authority', community(self.bound)))
        self.grant_path.write_bytes(encode(value))

    def runner(self, action='publish', documents=None):
        f = self.fixture
        return publication.Runner(f.json_file, f.paths, self.packet, f.grant_path, f.proof_path,
                                  self.grant_path, fixtures.TOKEN, action=action, transport=self.transport,
                                  now=lambda: NOW, **(documents or {}))

    def ready(self, *, authority=None):
        self.community_authority = authority if authority is not None else community(self.bound)
        self.transport.accept_on_submit = self.community_authority['permissions']['include_directly']
        self.grant('capture')
        result = self.runner('capture').run()
        snapshot_path = Path(result['snapshot_path'])
        snapshot = parse(snapshot_path.read_bytes())
        duplicate = raw_duplicates(self.prepared, bridge=self.bound, snapshot=snapshot, now=NOW)
        from scripts.modern_publication_qa import pending_manifest
        manifest = approve(pending_manifest(self.prepared, self.bound, snapshot, duplicate,
                           source_revision='a' * 40, now=NOW, community=self.community_authority), now=NOW)
        release = prepare_release(manifest)
        release['release'].update(approved=True, authority='Dummy human', authority_type='human',
                                  authorized_at=NOW.isoformat(), rationale='Exact fixture release')
        documents = {'snapshot': snapshot_path}
        for key, value in (('qa', manifest), ('duplicate', duplicate), ('release', release)):
            documents[key] = Path(self.temp.name) / (key + '.json')
            documents[key].write_bytes(encode(value))
        self.grant('publish', documents)
        self.transport.calls.clear()
        return documents

    def publication_row(self):
        path = Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json')
        return parse(path.read_bytes())['targets'][self.prepared.source_id]

    def mutate_response(self, index, transform):
        def change(i, response):
            if i != index:
                return response
            status, media, raw = response
            value = parse(raw)
            transform(value)
            return status, media, encode(value)
        self.transport.change = change

    def test_capture_preserves_original_expired_creation_receipts(self):
        old = Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json').read_bytes()
        self.grant('capture')
        result = self.runner('capture').run()
        self.assertTrue(result['capture_verified'])
        self.assertEqual(result['counts'], {'get': 5})
        self.assertEqual(old, Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json').read_bytes())
        with self.assertRaises(ValueError):
            self.runner('capture').run()
        self.assertEqual(len(self.transport.calls), 5)

    def test_full_flow_and_unchanged_read_only_retry(self):
        docs = self.ready()
        first = self.runner(documents=docs).run()
        self.assertTrue(first['published_verified'])
        self.assertTrue(first['community_submission_verified'])
        self.assertTrue(first['community_membership_verified'])
        self.assertTrue(first['release_complete'])
        self.assertFalse(first['doi_registration_verified'])
        self.assertEqual(first['counts'], {'get': 16, 'review': 1, 'submit': 1})
        base = self.fixture.transport.base
        writes = [r for r in self.transport.calls if r[0] != 'GET']
        self.assertEqual(writes, [
            ('PUT', base + '/review', encode({'type': 'community-submission',
                                             'receiver': {'community': COMMUNITY}}), 'application/json'),
            ('POST', base + '/actions/submit-review', encode({'require_review': False}), 'application/json')])
        result = self.runner(documents=docs).run(read_only=True)
        self.assertEqual(result['counts'], publication.PUBLISH_LIMITS)
        self.assertTrue(result['release_complete'])
        self.assertEqual([r for r in self.transport.calls if r[0] != 'GET'], writes)
        self.assertFalse(any(r[1].endswith(('/actions/publish', '/communities')) for r in self.transport.calls))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run(read_only=True)
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()

    def test_lost_review_response_holds_without_recovery_dispatch(self):
        docs = self.ready()
        self.transport.fail_after = 5
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertTrue(self.transport.review_created)
        self.assertFalse(self.transport.published)
        self.transport.fail_after = None
        for read_only in (False, True):
            with self.assertRaises(ValueError):
                self.runner(documents=docs).run(read_only=read_only)
        self.assertEqual(len(self.transport.calls), 6)
        self.assertEqual([r[0] for r in self.transport.calls if r[0] != 'GET'], ['PUT'])

    def test_lost_submit_response_recovers_accepted_record_with_gets_only(self):
        docs = self.ready()
        self.transport.fail_after = 11
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.transport.fail_after = None
        result = self.runner(documents=docs).run(read_only=True)
        self.assertTrue(result['release_complete'])
        self.assertTrue(result['community_membership_verified'])
        self.assertEqual(result['counts'], {'get': 16, 'review': 1, 'submit': 1})
        self.assertEqual([r[0] for r in self.transport.calls[12:]], ['GET'] * 6)
        self.assertEqual(self.transport.calls[12][1], '/api/requests/' + self.transport.request_id)

    def test_pending_submission_is_incomplete_until_later_get_only_acceptance(self):
        docs = self.ready(authority=community(self.bound, include_directly=False))
        pending = self.runner(documents=docs).run()
        self.assertEqual(pending['request_status'], 'submitted')
        self.assertTrue(pending['community_submission_verified'])
        for flag in ('published_verified', 'community_membership_verified', 'release_complete'):
            self.assertFalse(pending[flag])
        self.assertFalse(self.transport.published)
        self.assertEqual(pending['counts'], {'get': 11, 'review': 1, 'submit': 1})
        self.assertEqual(len(self.transport.calls), 13)
        writes = [r for r in self.transport.calls if r[0] != 'GET']
        self.transport.accept()
        complete = self.runner(documents=docs).run(read_only=True)
        self.assertTrue(complete['release_complete'])
        self.assertEqual(complete['counts'], {'get': 17, 'review': 1, 'submit': 1})
        self.assertEqual([r for r in self.transport.calls[13:] if r[0] != 'GET'], [])
        self.assertEqual([r for r in self.transport.calls if r[0] != 'GET'], writes)

    def test_submit_failure_without_effect_cannot_be_replayed(self):
        docs = self.ready()
        self.transport.fail_before = 11
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.transport.fail_before = None
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run(read_only=True)
        self.assertFalse(self.transport.published)
        self.assertEqual([r[0] for r in self.transport.calls if r[0] != 'GET'], ['PUT', 'POST'])
        self.assertEqual(self.transport.calls[-1][1], '/api/requests/' + self.transport.request_id)

    def test_existing_draft_review_prevents_review_write(self):
        docs = self.ready()
        self.mutate_response(0, lambda value: value['parent'].update(review={
            'id': 'existing-review', 'type': 'community-submission', 'receiver': {'community': COMMUNITY}}))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertTrue(all(call[0] == 'GET' for call in self.transport.calls))
        self.assertFalse(self.transport.review_created)

    def test_top_level_review_on_either_initial_record_read_prevents_review_write(self):
        for case, index in enumerate((0, 4)):
            with self.subTest(response_index=index):
                if case:
                    self.setUp()
                docs = self.ready()
                self.mutate_response(index, lambda value: value.update(review={
                    'id': 'fallback-review', 'type': 'community-submission',
                    'receiver': {'community': COMMUNITY}}))
                with self.assertRaises(ValueError):
                    self.runner(documents=docs).run()
                self.assertEqual([call[0] for call in self.transport.calls], ['GET'] * 5)
                self.assertFalse(self.transport.review_created)
                self.assertFalse(self.transport.published)

    def test_postreview_requires_draft_with_review_at_both_record_boundaries(self):
        cases = [(index, status) for index in (6, 10) for status in ('draft', 'in_review')]
        for case, (index, status) in enumerate(cases):
            with self.subTest(response_index=index, status=status):
                if case:
                    self.setUp()
                docs = self.ready()
                self.mutate_response(index, lambda value, status=status: value.update(status=status))
                with self.assertRaises(ValueError):
                    self.runner(documents=docs).run()
                self.assertEqual([call[0] for call in self.transport.calls if call[0] != 'GET'], ['PUT'])
                self.assertEqual(len(self.transport.calls), 11)
                self.assertFalse(self.transport.submitted)
                self.assertFalse(self.transport.published)

    def test_top_level_review_on_either_postreview_record_prevents_submit(self):
        for case, index in enumerate((6, 10)):
            with self.subTest(response_index=index):
                if case:
                    self.setUp()
                docs = self.ready()
                self.mutate_response(index, lambda value: value.update(review={
                    'id': self.transport.request_id, 'type': 'community-submission',
                    'receiver': {'community': COMMUNITY}}))
                with self.assertRaises(ValueError):
                    self.runner(documents=docs).run()
                self.assertEqual([call[0] for call in self.transport.calls if call[0] != 'GET'], ['PUT'])
                self.assertEqual(len(self.transport.calls), 11)
                self.assertFalse(self.transport.submitted)
                self.assertFalse(self.transport.published)

    def test_top_level_review_on_either_published_record_prevents_completion(self):
        for case, index in enumerate((13, 17)):
            with self.subTest(response_index=index):
                if case:
                    self.setUp()
                docs = self.ready()
                self.mutate_response(index, lambda value: value.update(review={
                    'id': 'unexpected-published-review', 'type': 'community-submission',
                    'receiver': {'community': COMMUNITY}}))
                with self.assertRaises(ValueError):
                    self.runner(documents=docs).run()
                self.assertEqual([call[0] for call in self.transport.calls if call[0] != 'GET'], ['PUT', 'POST'])
                self.assertEqual(len(self.transport.calls), index + 1)
                self.assertFalse(self.publication_row().get('published_verified', False))

    def test_review_response_destination_conflict_prevents_submit(self):
        docs = self.ready()
        self.mutate_response(5, lambda value: value.update(receiver={'community': '00000000-0000-4000-8000-000000000001'}))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual(len(self.transport.calls), 6)
        self.assertFalse(self.transport.submitted)

    def test_postreview_metadata_change_prevents_submit(self):
        docs = self.ready()
        self.mutate_response(6, lambda value: value['metadata'].update(title='Changed after review creation'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual([r[0] for r in self.transport.calls if r[0] != 'GET'], ['PUT'])
        self.assertFalse(self.transport.published)

    def test_postreview_file_object_change_prevents_submit(self):
        docs = self.ready()
        self.mutate_response(8, lambda value: value.update(file_id='00000000-0000-4000-8000-000000000099'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual([r[0] for r in self.transport.calls if r[0] != 'GET'], ['PUT'])
        self.assertFalse(self.transport.published)

    def test_postreview_bracketed_revision_change_prevents_submit(self):
        docs = self.ready()
        self.mutate_response(10, lambda value: value.update(revision_id=value['revision_id'] + 1))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual([r[0] for r in self.transport.calls if r[0] != 'GET'], ['PUT'])
        self.assertFalse(self.transport.published)

    def test_postreview_destination_change_prevents_submit(self):
        docs = self.ready()
        self.mutate_response(10, lambda value: value['parent']['review'].update(receiver={
            'community': '00000000-0000-4000-8000-000000000001'}))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual([r[0] for r in self.transport.calls if r[0] != 'GET'], ['PUT'])
        self.assertFalse(self.transport.published)

    def test_review_can_advance_revision_before_a_stable_exact_snapshot(self):
        docs = self.ready()
        self.transport.review_revision_delta = 1
        self.assertTrue(self.runner(documents=docs).run()['release_complete'])
        self.assertEqual(self.transport.inner.revision, self.bound['verified_revision'] + 1)

    def test_accepted_request_requires_exact_membership_default_and_no_review(self):
        changes = {
            'missing': lambda parent: parent.update(communities={'ids': [], 'default': COMMUNITY}),
            'wrong': lambda parent: parent.update(communities={'ids': ['00000000-0000-4000-8000-000000000001'], 'default': COMMUNITY}),
            'extra': lambda parent: parent['communities']['ids'].append('00000000-0000-4000-8000-000000000001'),
            'default': lambda parent: parent['communities'].update(default=None),
            'review': lambda parent: parent.update(review={'id': 'still-open-review'}),
        }
        for index, (name, change) in enumerate(changes.items()):
            with self.subTest(change=name):
                if index:
                    self.setUp()
                docs = self.ready()
                self.mutate_response(13, lambda value, change=change: change(value['parent']))
                with self.assertRaises(ValueError):
                    self.runner(documents=docs).run()
                self.assertFalse(self.publication_row().get('published_verified', False))
                self.assertEqual(len(self.transport.calls), 14)

    def test_old_direct_publication_journal_cannot_migrate_into_community_first_execution(self):
        docs = self.ready()
        self.runner(documents=docs).run()
        path = Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json')
        original = parse(path.read_bytes())
        intent = draft.state_root(self.fixture.paths) / (self.prepared.source_id + '.modern-publish-v1.intent.json')
        intent_bytes = intent.read_bytes()
        self.transport.calls.clear()
        for historical_counts in (False, True):
            with self.subTest(historical_counts=historical_counts):
                old = copy.deepcopy(original)
                row = old['targets'][self.prepared.source_id]
                row.pop('protocol')
                if historical_counts:
                    row['counts'] = {'get': 16, 'publish': 1, 'inclusion': 1}
                    for receipt in row['requests']:
                        if receipt['kind'] == 'review':
                            receipt.update(kind='publish', method='POST',
                                           path=self.fixture.transport.base + '/actions/publish')
                        elif receipt['kind'] == 'submit':
                            receipt.update(kind='inclusion', method='POST',
                                           path='/api/records/' + self.bound['identity']['id'] + '/communities')
                raw = encode(old)
                path.write_bytes(raw)
                for read_only in (False, True):
                    with self.assertRaises(ValueError):
                        self.runner(documents=docs).run(read_only=read_only)
                self.assertEqual(self.transport.calls, [])
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(intent.read_bytes(), intent_bytes)

    def test_postreview_stable_revision_cannot_regress_before_qa(self):
        docs = self.ready()
        self.transport.review_revision_delta = -1
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual([r[0] for r in self.transport.calls if r[0] != 'GET'], ['PUT'])
        self.assertFalse(self.transport.published)

    def test_accepted_submission_cannot_regress_to_pending_on_request_readback(self):
        docs = self.ready()
        self.mutate_response(12, lambda value: value.update(status='submitted', is_open=True, is_closed=False))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual(len(self.transport.calls), 13)
        self.assertFalse(self.publication_row().get('published_verified', False))

    def test_submit_response_wrong_request_identity_prevents_public_record_reads(self):
        docs = self.ready()
        self.mutate_response(11, lambda value: value.update(id='another-safe-request'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual(len(self.transport.calls), 12)
        self.assertFalse(self.publication_row().get('published_verified', False))

    def test_prepublication_changed_revision_prevents_post(self):
        docs = self.ready()
        self.mutate_response(4, lambda data: data.update(revision_id=3))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertTrue(all(r[0] == 'GET' for r in self.transport.calls))

    def test_published_changed_identity_held(self):
        docs = self.ready()
        self.mutate_response(13, lambda data: data.update(id='19000002'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual(len(self.transport.calls), 14)

    def test_published_file_object_swap_held(self):
        docs = self.ready()
        self.mutate_response(15, lambda data: data.update(file_id='00000000-0000-4000-8000-000000000099'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.publication_row().get('published_verified', False))

    def test_doi_changed_on_readback_held(self):
        docs = self.ready()
        self.mutate_response(17, lambda data: data['pids']['doi'].update(identifier='10.5281/zenodo.99999999'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.publication_row().get('published_verified', False))

    def test_legacy_doi_collision_blocks_confirmation(self):
        docs = self.ready()
        Path(self.fixture.paths.uploads_registry_path).write_bytes(encode({'FGDC-4': {'deposition_id': 98765,
                                  'doi': self.transport.doi}}))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.publication_row().get('published_verified', False))

    def test_legacy_cannot_adopt_modern_doi(self):
        docs = self.ready()
        self.runner(documents=docs).run()
        with self.assertRaises(ValueError):
            reject_modern_attempt(self.fixture.paths, 'FGDC-4', 98765, self.transport.doi.upper())

    def test_old_publication_grant_cannot_dispatch_community_first_protocol(self):
        docs = self.ready()
        value = parse(self.grant_path.read_bytes())
        value.update(schema_version=1, kind='modern-singleton-publish-grant-v1')
        self.grant_path.write_bytes(encode(value))
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_precommunity_qa_and_release_cannot_authorize_publication(self):
        from scripts.modern_publication_qa import pending_manifest
        docs = self.ready()
        snapshot, duplicate = (parse(docs[k].read_bytes()) for k in ('snapshot', 'duplicate'))
        qa = approve(pending_manifest(self.prepared, self.bound, snapshot, duplicate,
                     source_revision='a' * 40, now=NOW), now=NOW)
        release = prepare_release(qa)
        release['release'].update(approved=True, authority='Dummy human', authority_type='human',
                                  authorized_at=NOW.isoformat(), rationale='Explicit old fixture release')
        docs['qa'].write_bytes(encode(qa))
        docs['release'].write_bytes(encode(release))
        self.grant('publish', docs)
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_freshly_reviewed_other_destination_does_not_reuse_qa_or_release(self):
        from scripts.modern_publication_qa import community_projection_hash
        docs = self.ready()
        value = parse(self.grant_path.read_bytes())
        value['community']['id'] = '00000000-0000-4000-8000-000000000001'
        value['community']['reviewed_projection_sha256'] = community_projection_hash(value['community'])
        self.grant_path.write_bytes(encode(value))
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_community_authority_must_cover_entire_publication_grant(self):
        from scripts.modern_publication_qa import community_projection_hash
        authority = community(self.bound)
        authority['expires_at'] = (NOW + timedelta(seconds=599)).isoformat()
        authority['reviewed_projection_sha256'] = community_projection_hash(authority)
        docs = self.ready(authority=authority)
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_expired_or_unapproved_new_grant_never_dispatches(self):
        docs = self.ready()
        value = parse(self.grant_path.read_bytes())
        value['approved'] = False
        self.grant_path.write_bytes(encode(value))
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_changed_release_never_dispatches(self):
        docs = self.ready()
        release = parse(docs['release'].read_bytes())
        release['release']['approved'] = False
        docs['release'].write_bytes(encode(release))
        self.grant('publish', docs)
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_write_only_token_attestation_cannot_authorize_publication(self):
        docs = self.ready()
        grant = parse(self.grant_path.read_bytes())
        grant['token_scope'] = publication.CAPTURE_TOKEN_SCOPE
        self.grant_path.write_bytes(encode(grant))
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_external_only_or_foreign_owner_proof_never_dispatches(self):
        docs = self.ready()
        original = parse(docs['duplicate'].read_bytes())
        for alteration in ('missing', 'foreign-owner', 'sandbox', 'history-unreconciled'):
            with self.subTest(alteration=alteration):
                duplicate = copy.deepcopy(original)
                if alteration == 'missing':
                    duplicate.pop('production')
                elif alteration == 'foreign-owner':
                    duplicate['production']['owner'] = '456'
                elif alteration == 'sandbox':
                    duplicate['production']['origin'] = 'https://sandbox.zenodo.org'
                else:
                    duplicate['production']['history_reconciled'] = False
                docs['duplicate'].write_bytes(encode(duplicate))
                self.grant('publish', docs)
                with self.assertRaises(ValueError):
                    self.runner(documents=docs)
                self.assertEqual(self.transport.calls, [])

    def test_production_proof_must_cover_entire_publication_grant(self):
        docs = self.ready()
        from scripts.modern_publication_qa import (
            pending_manifest,
            production_projection_hash,
        )
        duplicate = parse(docs['duplicate'].read_bytes())
        duplicate['production']['expires_at'] = (NOW + timedelta(seconds=599)).isoformat()
        duplicate['production']['reviewed_projection_sha256'] = production_projection_hash(duplicate['production'])
        snapshot = parse(docs['snapshot'].read_bytes())
        manifest = approve(pending_manifest(self.prepared, self.bound, snapshot, duplicate,
                           source_revision='a' * 40, now=NOW, community=community(self.bound)), now=NOW)
        release = prepare_release(manifest)
        release['release'].update(approved=True, authority='Dummy human', authority_type='human',
                                  authorized_at=NOW.isoformat(), rationale='Exact fixture release')
        for key, value in (('duplicate', duplicate), ('qa', manifest), ('release', release)):
            docs[key].write_bytes(encode(value))
        self.grant('publish', docs)
        with self.assertRaises(ValueError):
            self.runner(documents=docs)
        self.assertEqual(self.transport.calls, [])

    def test_redirect_is_spent_and_never_followed(self):
        docs = self.ready()
        self.transport.change = lambda i, r: (301, r[1], b'{}') if i == 5 else r
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual(len(self.transport.calls), 6)
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual(len(self.transport.calls), 6)

    def test_token_echo_never_persisted(self):
        docs = self.ready()
        self.transport.change = lambda i, r: (r[0], r[1], encode({'echo': fixtures.TOKEN})) if i == 5 else r
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        journal = Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json').read_bytes()
        self.assertNotIn(fixtures.TOKEN.encode(), journal)
        self.assertTrue(parse(journal)['targets']['FGDC-141']['requests'][-1]['credential_suppressed'])

    def test_fsync_failure_prevents_any_provider_call(self):
        docs = self.ready()
        with patch.object(publication, 'atomic_json', side_effect=OSError('Dummy durability failure')):
            with self.assertRaises(OSError):
                self.runner(documents=docs).run()
        self.assertEqual(self.transport.calls, [])
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()

    def test_wrong_community_request_owner_held(self):
        docs = self.ready()
        self.mutate_response(12, lambda data: data.update(created_by={'user': '456'}))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()

    def test_malformed_old_attempt_history_held(self):
        path = Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json')
        value = parse(path.read_bytes())
        value['targets']['FGDC-141']['requests'][0]['http_status'] = 500
        path.write_bytes(encode(value))
        with self.assertRaises(ValueError):
            self.bridge()
        self.assertEqual(self.transport.calls, [])

    def test_runtime_bridge_is_explicit_and_nonruntime_fields_exact(self):
        value = parse(self.packet.read_bytes())
        for key, replacement in (('runtime_sha256', 'f' * 64), ('wire_sha256', 'e' * 64)):
            with self.subTest(key=key):
                changed = copy.deepcopy(value)
                changed['evidence'][key] = replacement
                changed['binding'] = sha(encode(changed['evidence']))
                self.packet.write_bytes(encode(changed))
                with self.assertRaises(ValueError):
                    self.bridge()
        self.packet.write_bytes(encode(value))
        self.assertEqual(self.bridge()[1], self.bound)

    def test_realistic_create_time_follows_dispatch_and_precedes_init(self):
        path = Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json')
        value = parse(path.read_bytes())
        row = value['targets']['FGDC-141']
        row['identity']['created'] = (fixtures.NOW + timedelta(seconds=1)).isoformat()
        for index, receipt in enumerate(row['requests'][1:], 2):
            receipt['attempted_at'] = (fixtures.NOW + timedelta(seconds=index)).isoformat()
        path.write_bytes(encode(value))
        self.assertEqual(self.bridge()[1]['identity'], row['identity'])
        row['identity']['created'] = (fixtures.NOW + timedelta(seconds=3)).isoformat()
        path.write_bytes(encode(value))
        with self.assertRaises(ValueError):
            self.bridge()

    def test_named_pr34_runtime_bridges_without_rewriting_old_history(self):
        self.assert_historical_runtime_bridges(publication.PR34_RUNTIME)

    def test_named_pr35_runtime_bridges_without_rewriting_old_history(self):
        self.assert_historical_runtime_bridges(publication.PR35_RUNTIME)

    def assert_historical_runtime_bridges(self, runtime):
        packet = parse(self.packet.read_bytes())
        packet['evidence']['runtime_sha256'] = runtime
        packet['binding'] = sha(encode(packet['evidence']))
        self.packet.write_bytes(encode(packet))
        self.fixture.change_proof(binding=packet['binding'])
        self.fixture.change_grant(binding=packet['binding'])
        path = Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json')
        value = parse(path.read_bytes())
        row = value['targets']['FGDC-141']
        row['binding'] = packet['binding']
        row['grant_sha256'] = sha(self.fixture.grant_path.read_bytes())
        intent_path = draft.state_root(self.fixture.paths) / 'FGDC-141.modern-create-v1.intent.json'
        intent = parse(intent_path.read_bytes())
        intent.update(binding=packet['binding'], grant_sha256=row['grant_sha256'])
        intent_path.write_bytes(encode(intent))
        row['intent_sha256'] = sha(intent_path.read_bytes())
        path.write_bytes(encode(value))
        original = path.read_bytes()
        current, bound = self.bridge()
        self.assertEqual(bound['original_runtime_sha256'], runtime)
        self.assertEqual(current, self.prepared)
        self.assertEqual(original, path.read_bytes())

    def test_started_capture_is_not_migrated_or_regranted_for_another_runtime(self):
        self.assert_historical_runtime_bridges(publication.PR35_RUNTIME)
        self.prepared, self.bound = self.bridge()
        self.grant('capture')
        self.runner('capture').run()
        calls = len(self.transport.calls)
        with patch('scripts.modern_singleton.runtime_binding', return_value='a' * 64):
            self.prepared, self.bound = self.bridge()
            self.grant('capture')
            with self.assertRaises(ValueError):
                self.runner('capture').run(read_only=True)
        self.assertEqual(len(self.transport.calls), calls)

    def test_started_publication_is_not_migrated_for_another_runtime(self):
        self.assert_historical_runtime_bridges(publication.PR35_RUNTIME)
        self.prepared, self.bound = self.bridge()
        docs = self.ready()
        self.runner(documents=docs).run()
        calls = len(self.transport.calls)
        path = Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json')
        original = path.read_bytes()
        with patch('scripts.modern_singleton.runtime_binding', return_value='a' * 64):
            self.prepared, self.bound = self.bridge()
            self.grant('publish', docs)
            with self.assertRaises(ValueError):
                self.runner(documents=docs).run(read_only=True)
        self.assertEqual(len(self.transport.calls), calls)
        self.assertEqual(path.read_bytes(), original)

    def test_failed_response_preserves_untrusted_doi_against_later_adoption(self):
        docs = self.ready()
        self.mutate_response(13, lambda data: data['metadata'].update(title='Wrong provider title'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        row = parse(Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json').read_bytes())['targets']['FGDC-141']
        self.assertIn(self.transport.doi, row['doi_claims'])
        self.assertNotIn('published_baseline', row)
        with self.assertRaises(ValueError):
            reject_modern_attempt(self.fixture.paths, 'FGDC-4', 98765, self.transport.doi)

    def test_foreign_oai_identifier_held(self):
        docs = self.ready()
        self.mutate_response(13, lambda data: data['pids']['oai'].update(identifier='oai:zenodo.org:98765'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.publication_row().get('published_verified', False))

    def test_integer_request_open_flag_held(self):
        docs = self.ready()
        self.mutate_response(12, lambda data: data.update(is_open=1))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()

    def test_prepublication_file_object_changed_since_qa_prevents_post(self):
        docs = self.ready()
        def change(index, response):
            if index not in (1, 2):
                return response
            status, media, raw = response
            data = parse(raw)
            entry = data['entries'][0] if index == 1 else data
            entry['file_id'] = '00000000-0000-4000-8000-000000000099'
            return status, media, encode(data)
        self.transport.change = change
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertTrue(all(r[0] == 'GET' for r in self.transport.calls))

    def test_publication_identity_still_blocks_legacy_if_draft_journal_lost(self):
        docs = self.ready()
        self.runner(documents=docs).run()
        Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json').unlink()
        with self.assertRaises(ValueError):
            reject_modern_attempt(self.fixture.paths, 'FGDC-4', int(self.bound['identity']['parent_id']))

    def test_corrupted_saved_request_identity_cannot_dispatch_recovery_get(self):
        docs = self.ready()
        self.runner(documents=docs).run()
        path = Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json')
        original = parse(path.read_bytes())
        self.transport.calls.clear()
        for request_id in ('../records/98765', '?token=unsafe', '', 'different-safe-request'):
            with self.subTest(request_id=request_id):
                changed = copy.deepcopy(original)
                changed['targets']['FGDC-141']['request_id'] = request_id
                path.write_bytes(encode(changed))
                with self.assertRaises(ValueError):
                    self.runner(documents=docs).run(read_only=True)
                self.assertEqual(self.transport.calls, [])

    def test_grant_revocation_during_publish_retains_doi_evidence_but_stops(self):
        docs = self.ready()
        def revoke(index, response):
            if index == 13:
                value = parse(self.grant_path.read_bytes())
                value['approved'] = False
                self.grant_path.write_bytes(encode(value))
            return response
        self.transport.change = revoke
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        row = parse(Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json').read_bytes())['targets']['FGDC-141']
        self.assertIn(self.transport.doi, row['doi_claims'])
        self.assertEqual(row['counts']['submit'], 1)
        self.assertNotIn('published_baseline', row)
        self.assertEqual(len(self.transport.calls), 14)

    def test_grant_expiry_during_publish_retains_doi_evidence_but_stops(self):
        docs = self.ready()
        runner = self.runner(documents=docs)
        clock = [NOW]
        runner.now = lambda: clock[0]
        def expire(index, response):
            if index == 13:
                clock[0] += timedelta(seconds=600)
            return response
        self.transport.change = expire
        with self.assertRaises(ValueError):
            runner.run()
        row = parse(Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json').read_bytes())['targets']['FGDC-141']
        self.assertIn(self.transport.doi, row['doi_claims'])
        self.assertEqual(row['counts']['submit'], 1)
        self.assertNotIn('published_baseline', row)
        self.assertEqual(len(self.transport.calls), 14)


if __name__ == '__main__':
    unittest.main()
