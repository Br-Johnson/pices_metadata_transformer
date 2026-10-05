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


class Transport:
    """Source-supported modern subset; no claim of deployed API compatibility."""
    def __init__(self, fixture):
        self.fixture = fixture
        self.inner = fixture.transport
        self.calls = []
        self.published = False
        self.included = False
        self.fail_before = self.fail_after = None
        self.change = lambda index, response: response
        self.doi = '10.5281/zenodo.19000001'
        self.request_id = 'opaque-safe-request-1'

    def request_record(self):
        return {'id': self.request_id, 'type': 'community-inclusion', 'status': 'submitted', 'is_open': True,
                'topic': {'record': self.inner.identifier}, 'receiver': {'community': COMMUNITY},
                'created_by': {'user': '123'}}

    def request(self, method, path, body, *, timeout, accept=draft.MIME):
        index = len(self.calls)
        self.calls.append((method, path, body, accept))
        assert 0 < timeout <= draft.TIMEOUT
        if index == self.fail_before:
            raise TimeoutError(fixtures.TOKEN)
        base = '/api/records/' + self.inner.identifier
        media = accept
        if path.startswith('/api/requests/'):
            assert accept == 'application/json' and self.included and path == '/api/requests/' + self.request_id
            response = 200, media, encode(self.request_record())
        elif path == base + '/communities':
            assert self.published and method == 'POST' and accept == 'application/json'
            assert parse(body) == {'communities': [{'id': COMMUNITY, 'require_review': True}]}
            self.included = True
            response = 200, media, encode({'processed': [{'community_id': COMMUNITY,
                         'request_id': self.request_id, 'request': self.request_record()}]})
        else:
            publish = path.endswith('/actions/publish')
            if publish:
                assert body is None and method == 'POST'
                self.published = True
                translated = self.inner.base
            else:
                translated = path if '/draft' in path else path.replace(base, self.inner.base, 1)
                if '/draft' not in path:
                    assert self.published
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
                elif 'metadata' in value and self.published:
                    value.update(is_published=True, status='published', created=NOW.isoformat(), revision_id=1,
                                 pids={'doi': {'provider': 'datacite', 'identifier': self.doi},
                                       'oai': {'provider': 'oai', 'identifier': 'oai:zenodo.org:' + self.inner.identifier}})
                    value['parent']['pids'] = {'doi': {'provider': 'datacite', 'identifier': '10.5281/zenodo.19000000'}}
                    value['links'] = {k: v.replace('/draft', '') for k, v in value['links'].items()}
                raw = encode(value)
            response = 202 if publish else status, mime, raw
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
            value.update(exclusive_writer=True, community={'id': COMMUNITY, 'slug': 'pices',
                         'evidence_sha256': 'd' * 64, 'reviewed_by': 'Dummy parent',
                         'open_submissions': True, 'owner_authorized': True})
        self.grant_path.write_bytes(encode(value))

    def runner(self, action='publish', documents=None):
        f = self.fixture
        return publication.Runner(f.json_file, f.paths, self.packet, f.grant_path, f.proof_path,
                                  self.grant_path, fixtures.TOKEN, action=action, transport=self.transport,
                                  now=lambda: NOW, **(documents or {}))

    def ready(self):
        self.grant('capture')
        result = self.runner('capture').run()
        snapshot_path = Path(result['snapshot_path'])
        snapshot = parse(snapshot_path.read_bytes())
        duplicate = raw_duplicates(self.prepared, bridge=self.bound, snapshot=snapshot, now=NOW)
        from scripts.modern_publication_qa import pending_manifest
        manifest = approve(pending_manifest(self.prepared, self.bound, snapshot, duplicate,
                           source_revision='a' * 40, now=NOW), now=NOW)
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
        self.assertFalse(first['community_membership_verified'])
        self.assertFalse(first['doi_registration_verified'])
        self.assertEqual(first['counts'], {'get': 16, 'publish': 1, 'inclusion': 1})
        result = self.runner(documents=docs).run(read_only=True)
        self.assertEqual(result['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual(len([r for r in self.transport.calls if r[0] == 'POST']), 2)
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run(read_only=True)
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()

    def test_lost_publish_response_recovers_read_only_without_inclusion(self):
        docs = self.ready()
        self.transport.fail_after = 5
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.transport.fail_after = None
        result = self.runner(documents=docs).run(read_only=True)
        self.assertTrue(result['published_verified'])
        self.assertFalse(result['community_submission_verified'])
        self.assertEqual(result['counts'], {'get': 10, 'publish': 1, 'inclusion': 0})
        self.assertEqual(len([r for r in self.transport.calls if r[0] == 'POST']), 1)

    def test_lost_inclusion_response_does_not_repeat_or_search(self):
        docs = self.ready()
        self.transport.fail_after = 11
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.transport.fail_after = None
        result = self.runner(documents=docs).run(read_only=True)
        self.assertTrue(result['published_verified'])
        self.assertFalse(result['community_submission_verified'])
        self.assertEqual(len([r for r in self.transport.calls if r[0] == 'POST']), 2)
        self.assertFalse(any('/api/requests/' in r[1] for r in self.transport.calls))

    def test_prepublication_changed_revision_prevents_post(self):
        docs = self.ready()
        self.mutate_response(4, lambda data: data.update(revision_id=3))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertTrue(all(r[0] == 'GET' for r in self.transport.calls))

    def test_published_changed_identity_held(self):
        docs = self.ready()
        self.mutate_response(5, lambda data: data.update(id='19000002'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertEqual(len(self.transport.calls), 6)

    def test_published_file_object_swap_held(self):
        docs = self.ready()
        self.mutate_response(8, lambda data: data.update(file_id='00000000-0000-4000-8000-000000000099'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.transport.included)

    def test_doi_changed_on_readback_held(self):
        docs = self.ready()
        self.mutate_response(6, lambda data: data['pids']['doi'].update(identifier='10.5281/zenodo.99999999'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.transport.included)

    def test_legacy_doi_collision_blocks_confirmation(self):
        docs = self.ready()
        Path(self.fixture.paths.uploads_registry_path).write_bytes(encode({'FGDC-4': {'deposition_id': 98765,
                                  'doi': self.transport.doi}}))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.transport.included)

    def test_legacy_cannot_adopt_modern_doi(self):
        docs = self.ready()
        self.runner(documents=docs).run()
        with self.assertRaises(ValueError):
            reject_modern_attempt(self.fixture.paths, 'FGDC-4', 98765, self.transport.doi.upper())

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
                           source_revision='a' * 40, now=NOW), now=NOW)
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
        packet = parse(self.packet.read_bytes())
        packet['evidence']['runtime_sha256'] = publication.PR34_RUNTIME
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
        self.assertEqual(bound['original_runtime_sha256'], publication.PR34_RUNTIME)
        self.assertEqual(current, self.prepared)
        self.assertEqual(original, path.read_bytes())

    def test_failed_response_preserves_untrusted_doi_against_later_adoption(self):
        docs = self.ready()
        self.mutate_response(5, lambda data: data['metadata'].update(title='Wrong provider title'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        row = parse(Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json').read_bytes())['targets']['FGDC-141']
        self.assertIn(self.transport.doi, row['doi_claims'])
        self.assertNotIn('published_baseline', row)
        with self.assertRaises(ValueError):
            reject_modern_attempt(self.fixture.paths, 'FGDC-4', 98765, self.transport.doi)

    def test_foreign_oai_identifier_held(self):
        docs = self.ready()
        self.mutate_response(5, lambda data: data['pids']['oai'].update(identifier='oai:zenodo.org:98765'))
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        self.assertFalse(self.transport.included)

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
        for request_id in ('../records/98765', '?token=unsafe', ''):
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
            if index == 5:
                value = parse(self.grant_path.read_bytes())
                value['approved'] = False
                self.grant_path.write_bytes(encode(value))
            return response
        self.transport.change = revoke
        with self.assertRaises(ValueError):
            self.runner(documents=docs).run()
        row = parse(Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json').read_bytes())['targets']['FGDC-141']
        self.assertIn(self.transport.doi, row['doi_claims'])
        self.assertEqual(row['counts']['publish'], 1)
        self.assertNotIn('published_baseline', row)
        self.assertEqual(len(self.transport.calls), 6)

    def test_grant_expiry_during_publish_retains_doi_evidence_but_stops(self):
        docs = self.ready()
        runner = self.runner(documents=docs)
        clock = [NOW]
        runner.now = lambda: clock[0]
        def expire(index, response):
            if index == 5:
                clock[0] += timedelta(seconds=600)
            return response
        self.transport.change = expire
        with self.assertRaises(ValueError):
            runner.run()
        row = parse(Path(self.fixture.paths.uploads_registry_path + '.modern-publication-v1.json').read_bytes())['targets']['FGDC-141']
        self.assertIn(self.transport.doi, row['doi_claims'])
        self.assertEqual(row['counts']['publish'], 1)
        self.assertNotIn('published_baseline', row)
        self.assertEqual(len(self.transport.calls), 6)


if __name__ == '__main__':
    unittest.main()
