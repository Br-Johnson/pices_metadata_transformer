"""Offline interruption/restart contracts for production write attempts.

All remote effects are in-memory fixtures. These tests confer no production
authority and do not exercise the modern provider transport or class executor.
"""

import copy
import hashlib
import json
import os
import stat
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from scripts.path_config import OutputPaths
from scripts.production_mutations import PROTECTED, MutationJournal, preserve_identity
from scripts.publish_records import RecordPublisher
from scripts.reconcile_draft import reconcile
from scripts.release_manifest import prepare_release
from scripts.upload_service import DraftUploadService, atomic_json, read_json
from scripts.zenodo_api import ZenodoAPIClient, ZenodoAPIError
from tests import test_artifact_contract as artifact_fixtures


class ProductionMutationTests(unittest.TestCase):
    def setUp(self):
        # Composition deliberately avoids importing/inheriting another TestCase
        # into this module's discovery namespace.
        self.fixture = artifact_fixtures.ArtifactTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.paths = OutputPaths(self.fixture.directory.name, 'production')
        self.json_file = Path(self.paths.zenodo_json_dir) / 'sample.json'
        self.json_file.write_bytes(self.fixture.json_file.read_bytes())
        inventory = read_json(self.fixture.paths.safe_to_upload_path)
        inventory['environment'] = 'production'
        atomic_json(self.paths.safe_to_upload_path, inventory)
        self.client = self.fixture.client
        self.client.base_url = 'https://zenodo.org'
        self.remote = self.fixture.remote
        self.service = DraftUploadService(self.paths, 'production')

    def upload(self):
        return self.service.upload(str(self.json_file), self.client)

    def journal(self):
        return MutationJournal(self.paths).data['targets']['sample']

    def writes(self):
        return tuple(getattr(self.client, method).call_count for method in
                     ('create_deposition', 'update_deposition_metadata', 'upload_file',
                      'publish_deposition'))

    def snapshot(self, entry):
        return {'http_status': 200, 'retrieved_at': '2026-10-05T00:00:00+00:00',
                'endpoint': 'https://zenodo.org/api/deposit/depositions/123',
                'confirmed_fgdc_id': 'sample',
                'confirmed_metadata_sha256': entry['metadata_sha256'],
                'confirmed_source_sha256': entry['source_sha256'],
                'body': copy.deepcopy(self.remote)}

    def recover(self, entry):
        return reconcile(self.paths, 'sample', self.snapshot(entry),
                         'Offline fixture reviewer', 'Correlated synthetic source and record')

    def publisher(self, entry):
        self.remote['doi'] = '10.5281/zenodo.123'
        qa = self.fixture.approve(self.paths, entry)
        release = prepare_release(qa)
        release['release'].update(approved=True, authority='Fixture release authority',
                                  authorized_at='2026-10-05', rationale='Offline fixture only')
        publisher = RecordPublisher.__new__(RecordPublisher)
        publisher.paths, publisher.client = self.paths, self.client
        publisher.sandbox, publisher.logger = False, Mock()
        publisher.qa_manifest, publisher.release_manifest = qa, release
        return publisher

    def test_malformed_or_falsy_doi_never_confirms_published_identity(self):
        entry = self.upload()
        publisher = self.publisher(entry)
        self.remote.update(state='done', submitted=True)
        for invalid in ('not-a-doi', '10.5281/', '10.5281/with space', False, 0, [], {}):
            with self.subTest(doi=invalid):
                with self.assertRaisesRegex(ValueError, 'DOI'):
                    preserve_identity('sample', dict(entry, doi=invalid))
                self.remote['doi'] = invalid
                result = publisher._publish_single_record(entry)
                self.assertFalse(result['publish_successful'])
                self.assertIn('DOI', result['error'])
        self.client.publish_deposition.assert_not_called()
        self.assertNotIn('publish', self.journal()['actions'])

    def test_successful_restart_is_read_only(self):
        first = self.upload()
        self.assertTrue(first['success'], first.get('error'))
        self.assertTrue(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))
        self.assertEqual({key: value['status'] for key, value in self.journal()['actions'].items()},
                         {'create': 'verified', 'metadata': 'verified', 'artifact': 'verified'})
        self.assertEqual(self.fixture.source.read_bytes(), self.fixture.raw)

    def test_create_exception_spends_attempt_even_without_observed_effect(self):
        self.client.create_deposition.side_effect = TimeoutError('Fixture lost response')
        result = self.upload()
        self.assertFalse(result['success'])
        self.assertTrue(result['needs_reconciliation'])
        self.assertEqual(self.journal()['actions']['create']['status'], 'uncertain')
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            self.upload()
        self.assertEqual(self.writes(), (1, 0, 0, 0))

    def test_create_effect_with_lost_response_requires_explicit_identity_recovery(self):
        self.client.create_deposition.side_effect = TimeoutError('Fixture created, response lost')
        result = self.upload()
        self.assertFalse(result['success'])
        recovered = self.recover(result)
        self.assertEqual(recovered['deposition_id'], 123)
        self.assertEqual(self.journal()['actions']['create']['status'], 'uncertain')
        self.client.create_deposition.side_effect = None
        self.assertTrue(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))

    def test_metadata_exception_without_effect_never_repeats_put(self):
        self.client.update_deposition_metadata.side_effect = TimeoutError('Fixture PUT timeout')
        self.assertFalse(self.upload()['success'])
        self.client.update_deposition_metadata.side_effect = self.fixture.update
        second = self.upload()
        self.assertFalse(second['success'])
        self.assertIn('already attempted', second['error'])
        self.assertEqual(self.writes(), (1, 1, 0, 0))

    def test_metadata_effect_with_lost_response_advances_to_unspent_artifact(self):
        def update_then_interrupt(identifier, metadata):
            self.fixture.update(identifier, metadata)
            raise TimeoutError('Fixture metadata accepted, response lost')
        self.client.update_deposition_metadata.side_effect = update_then_interrupt
        self.assertFalse(self.upload()['success'])
        self.assertEqual(self.journal()['actions']['metadata']['status'], 'uncertain')
        self.assertTrue(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))
        self.assertEqual(self.journal()['actions']['metadata']['status'], 'verified')

    def test_artifact_exception_without_effect_never_repeats_upload(self):
        self.client.upload_file.side_effect = TimeoutError('Fixture file timeout')
        self.assertFalse(self.upload()['success'])
        self.client.upload_file.side_effect = self.fixture.attach
        self.assertFalse(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))
        self.assertEqual(self.journal()['actions']['artifact']['status'], 'uncertain')

    def test_artifact_effect_with_lost_response_is_verified_without_reupload(self):
        def attach_then_interrupt(*args, **kwargs):
            self.fixture.attach(*args, **kwargs)
            raise TimeoutError('Fixture upload accepted, response lost')
        self.client.upload_file.side_effect = attach_then_interrupt
        self.assertFalse(self.upload()['success'])
        self.assertTrue(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))
        self.assertEqual(self.journal()['actions']['artifact']['status'], 'verified')

    def test_registry_loss_and_refreshed_inventory_do_not_replenish_create(self):
        self.assertTrue(self.upload()['success'])
        before = Path(str(self.paths.uploads_registry_path) + '.mutations.json').read_bytes()
        Path(self.paths.uploads_registry_path).unlink()
        # A new complete inventory may approve the same source; it cannot erase
        # the independent durable record of the spent create.
        atomic_json(self.paths.safe_to_upload_path, read_json(self.paths.safe_to_upload_path))
        result = self.upload()
        self.assertFalse(result['success'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))
        self.assertEqual(Path(str(self.paths.uploads_registry_path) + '.mutations.json').read_bytes(), before)

    def test_payload_source_artifact_environment_identity_and_doi_conflicts_hold(self):
        entry = self.upload()
        entry['doi'] = '10.5281/zenodo.123'
        journal = MutationJournal(self.paths)
        journal.confirm('sample', entry, 'artifact', dict(self.remote, doi=entry['doi']))
        changes = [dict(source_sha256='a' * 64), dict(metadata_sha256='b' * 64),
                   dict(artifact_contract=None), dict(environment='sandbox'),
                   dict(deposition_id=124), dict(doi='10.5281/zenodo.124')]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                MutationJournal(self.paths).validate('sample', dict(entry, **change))
        self.assertEqual(self.writes(), (1, 1, 1, 0))

    def test_source_or_payload_edit_blocks_service_before_any_remote_read(self):
        entry = self.upload()
        reads = self.client.get_deposition.call_count
        payload = json.loads(self.json_file.read_text())
        payload['metadata']['description'] += ' Changed fixture interpretation.'
        self.json_file.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, 'Metadata changed'):
            self.upload()
        self.json_file.write_bytes(self.fixture.json_file.read_bytes())
        self.fixture.source.write_bytes(self.fixture.raw + b'\n')
        with self.assertRaises(ValueError):
            self.upload()
        self.assertEqual(self.client.get_deposition.call_count, reads)
        self.assertEqual(entry['deposition_id'], 123)
        self.assertEqual(self.writes(), (1, 1, 1, 0))

    def test_protected_associations_match_pinned_source_evidence(self):
        path = Path(__file__).resolve().parents[1] / 'docs/readiness/2026-10-04/alias228_production_reconciliation_input.json'
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         'a5b34f430a3b0b3a14776987e9828b4a1cf701ce2dc2172bd4cbb472759e37e5')
        rows = json.loads(raw)['protected_existing_imports']
        self.assertEqual(PROTECTED, {r['source_id']: (r['record_id'], r['source_sha256']) for r in rows})
        for row in rows:
            entry = dict(environment='production', deposition_id=row['record_id'],
                         source_sha256=row['source_sha256'])
            self.assertEqual(preserve_identity(row['source_id'], entry), row['doi'])
            for change in ({'deposition_id': None}, {'deposition_id': 123},
                           {'source_sha256': 'a' * 64}, {'doi': '10.5281/zenodo.123'}):
                with self.subTest(source=row['source_id'], change=change), self.assertRaises(ValueError):
                    preserve_identity(row['source_id'], dict(entry, **change))
            with self.assertRaises(ValueError):
                preserve_identity('sample', entry)
            with self.assertRaises(ValueError):
                preserve_identity('sample', dict(entry, deposition_id=123, doi=row['doi']))

    def test_created_protected_or_excluded_id_never_reaches_metadata_or_file(self):
        # Each scenario has its own registry/journal; none contacts a provider.
        for identifier in (17317855, 10042430, 15046283):
            with self.subTest(identifier=identifier):
                self.client.create_deposition.return_value = {'id': identifier}
                result = self.upload()
                self.assertFalse(result['success'])
                self.assertTrue(result['needs_reconciliation'])
                self.client.get_deposition.assert_not_called()
                self.client.update_deposition_metadata.assert_not_called()
                self.client.upload_file.assert_not_called()
                # Explicitly remove only these synthetic fixture files to give
                # the next scenario an independent target history.
                Path(self.paths.uploads_registry_path).unlink()
                Path(str(self.paths.uploads_registry_path) + '.mutations.json').unlink()

    def test_known_doi_survives_metadata_response_without_doi(self):
        self.client.create_deposition.return_value = {'id': 123, 'doi': '10.5281/zenodo.123'}
        first = self.upload()
        self.assertTrue(first['success'], first.get('error'))
        self.assertEqual(first['doi'], '10.5281/zenodo.123')
        self.assertEqual(self.upload()['doi'], first['doi'])
        self.assertEqual(self.journal()['doi'], first['doi'])

    def test_remote_id_or_doi_conflict_holds_before_further_writes(self):
        self.client.create_deposition.return_value = {'id': 123, 'doi': '10.5281/zenodo.123'}
        self.remote['metadata']['doi'] = '10.5281/zenodo.124'
        self.assertFalse(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 0, 0, 0))
        self.remote['metadata'].clear()
        self.remote['id'] = 124
        self.assertFalse(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 0, 0, 0))

    def test_newly_observed_doi_cannot_collide_with_registry_only_identity(self):
        atomic_json(self.paths.uploads_registry_path,
                    {'retained-other': {'environment': 'production', 'deposition_id': 124,
                                        'doi': '10.5281/ZENODO.124'}})
        self.remote['doi'] = '10.5281/zenodo.124'
        result = self.upload()
        self.assertFalse(result['success'])
        self.assertIn('Shared DOI', result['error'])
        self.assertEqual(self.writes(), (1, 0, 0, 0))

    def test_explicit_reconciliation_cannot_reset_spent_metadata_attempt(self):
        self.client.update_deposition_metadata.side_effect = TimeoutError('Fixture PUT timeout')
        entry = self.upload()
        before = copy.deepcopy(self.journal()['actions'])
        self.recover(entry)
        self.assertEqual(self.journal()['actions'], before)
        self.client.update_deposition_metadata.side_effect = self.fixture.update
        self.assertFalse(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 1, 0, 0))

    def test_legacy_incomplete_production_registry_requires_reconciliation(self):
        entry = self.upload()
        entry.update(upload_status='failed', success=False,
                     reconciliation={'reviewer': 'Old fixture reviewer', 'rationale': 'Stale decision'})
        atomic_json(self.paths.uploads_registry_path, {'sample': entry})
        Path(str(self.paths.uploads_registry_path) + '.mutations.json').unlink()
        reads = self.client.get_deposition.call_count
        with self.assertRaisesRegex(ValueError, 'Legacy incomplete'):
            self.upload()
        self.assertEqual(self.client.get_deposition.call_count, reads)
        self.assertEqual(self.writes(), (1, 1, 1, 0))

    def test_legacy_reconciliation_without_journal_does_not_grant_fresh_writes(self):
        entry = self.upload()
        Path(str(self.paths.uploads_registry_path) + '.mutations.json').unlink()
        self.remote['metadata'] = {}
        self.remote['files'] = []
        self.recover(entry)
        actions = self.journal()['actions']
        self.assertEqual(set(actions), {'create', 'metadata', 'artifact', 'publish'})
        self.assertTrue(all(row['status'] == 'uncertain' for row in actions.values()))
        self.assertFalse(self.upload()['success'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))

    def test_legacy_draft_without_journal_cannot_publish_but_done_readback_is_safe(self):
        entry = self.upload()
        publisher = self.publisher(entry)
        Path(str(self.paths.uploads_registry_path) + '.mutations.json').unlink()
        self.assertFalse(publisher._publish_single_record(entry)['publish_successful'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))
        self.remote.update(state='done', submitted=True)
        result = publisher._publish_single_record(entry)
        self.assertTrue(result['publish_successful'], result.get('error'))
        self.assertTrue(result['already_published'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))

    def test_doi_casefold_preserves_literal_and_prevents_cross_source_collision(self):
        original_doi = '10.5281/ZENODO.123'
        self.client.create_deposition.return_value = {'id': 123, 'doi': original_doi}
        self.remote['doi'] = original_doi.lower()
        entry = self.upload()
        self.assertTrue(entry['success'], entry.get('error'))
        self.assertEqual(entry['doi'], original_doi)
        other = dict(entry, deposition_id=124, doi=original_doi.lower())
        with self.assertRaises(ValueError):
            MutationJournal(self.paths).begin('another-source', other, 'metadata')
        other['doi'] = None
        journal = MutationJournal(self.paths)
        journal.begin('another-source', other, 'metadata')
        with self.assertRaises(ValueError):
            journal.confirm('another-source', other, 'metadata',
                            {'id': 124, 'doi': original_doi.lower()})
        self.assertEqual(self.writes(), (1, 1, 1, 0))

    def test_journal_directory_fsync_failure_prevents_create_dispatch(self):
        original = os.fsync
        directories = 0

        def fail_journal_directory(fd):
            nonlocal directories
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                directories += 1
                if directories == 2:  # Registry intent first, independent journal second.
                    raise OSError('Fixture directory fsync failure')
            return original(fd)

        with patch('scripts.upload_service.os.fsync', side_effect=fail_journal_directory):
            result = self.upload()
        self.assertFalse(result['success'])
        self.assertIn('fsync', result['error'])
        self.assertEqual(self.writes(), (0, 0, 0, 0))
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            self.upload()
        self.assertEqual(self.writes(), (0, 0, 0, 0))

    def test_corrupt_journal_fails_before_remote_reads_or_writes(self):
        path = Path(str(self.paths.uploads_registry_path) + '.mutations.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{incomplete')
        with self.assertRaises(ValueError):
            self.upload()
        self.client.get_deposition.assert_not_called()
        self.assertEqual(self.writes(), (0, 0, 0, 0))

    def test_publish_exception_without_effect_never_repeats_post(self):
        entry = self.upload()
        publisher = self.publisher(entry)
        self.client.publish_deposition.side_effect = TimeoutError('Fixture publish timeout')
        first = publisher._publish_single_record(entry)
        self.assertFalse(first['publish_successful'])
        self.assertEqual(self.journal()['actions']['publish']['status'], 'uncertain')
        self.assertFalse(publisher._publish_single_record(entry)['publish_successful'])
        self.assertEqual(self.writes(), (1, 1, 1, 1))

    def test_publish_effect_with_lost_response_becomes_read_only_verified(self):
        entry = self.upload()
        publisher = self.publisher(entry)

        def publish_then_interrupt(_):
            self.remote.update(state='done', submitted=True)
            raise TimeoutError('Fixture published, response lost')

        self.client.publish_deposition.side_effect = publish_then_interrupt
        self.assertFalse(publisher._publish_single_record(entry)['publish_successful'])
        result = publisher._publish_single_record(entry)
        self.assertTrue(result['publish_successful'], result.get('error'))
        self.assertTrue(result['already_published'])
        self.assertEqual(self.journal()['actions']['publish']['status'], 'verified')
        self.assertEqual(self.writes(), (1, 1, 1, 1))

    def test_publish_success_response_without_independent_readback_stays_uncertain(self):
        entry = self.upload()
        publisher = self.publisher(entry)

        def publish(_):
            self.remote.update(state='done', submitted=True)
            self.client.get_deposition.side_effect = TimeoutError('Fixture readback unavailable')
            return copy.deepcopy(self.remote)

        self.client.publish_deposition.side_effect = publish
        result = publisher._publish_single_record(entry)
        self.assertFalse(result['publish_successful'])
        self.assertIn('independent readback', result['error'])
        self.assertEqual(self.journal()['actions']['publish']['status'], 'uncertain')
        self.client.get_deposition.side_effect = lambda _: copy.deepcopy(self.remote)
        self.assertTrue(publisher._publish_single_record(entry)['already_published'])
        self.assertEqual(self.writes(), (1, 1, 1, 1))

    def test_published_readback_without_any_known_doi_is_not_reported_successful(self):
        entry = self.upload()
        publisher = self.publisher(entry)
        self.remote.pop('doi')

        def publish(_):
            self.remote.update(state='done', submitted=True)
            return copy.deepcopy(self.remote)

        self.client.publish_deposition.side_effect = publish
        first = publisher._publish_single_record(entry)
        self.assertFalse(first['publish_successful'])
        self.assertIn('DOI', first['error'])
        self.assertEqual(self.journal()['actions']['publish']['status'], 'uncertain')
        self.assertFalse(publisher._publish_single_record(entry)['publish_successful'])
        self.assertEqual(self.writes(), (1, 1, 1, 1))

    def test_missing_release_approval_prevents_publish_intent_and_post(self):
        entry = self.upload()
        publisher = self.publisher(entry)
        publisher.release_manifest['release']['approved'] = False
        reads = self.client.get_deposition.call_count
        self.assertFalse(publisher._publish_single_record(entry)['publish_successful'])
        self.assertEqual(self.client.get_deposition.call_count, reads)
        self.assertNotIn('publish', self.journal()['actions'])
        self.assertEqual(self.writes(), (1, 1, 1, 0))


class MutationTransportTests(unittest.TestCase):
    def client(self):
        client = ZenodoAPIClient.__new__(ZenodoAPIClient)
        client.api_url = 'https://zenodo.org/api/'
        client.max_retries, client.retry_delay, client.backoff_factor = 3, 1, 2
        client._rate_limit_check = Mock()
        client.api_logger, client.logger, client.session = Mock(), Mock(), Mock()
        return client

    def test_mutation_http_failure_or_timeout_dispatches_exactly_once(self):
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            for fault in (429, 500, requests.exceptions.ReadTimeout('Fixture timeout')):
                with self.subTest(method=method, fault=type(fault).__name__):
                    client = self.client()
                    if isinstance(fault, int):
                        client.session.request.return_value = Mock(status_code=fault,
                                                                   headers={'Retry-After': '60'})
                    else:
                        client.session.request.side_effect = fault
                    with patch('scripts.zenodo_api.time.sleep') as sleep:
                        with self.assertRaises(ZenodoAPIError):
                            client._make_request(method, 'deposit/depositions/123')
                    client.session.request.assert_called_once()
                    self.assertFalse(client.session.request.call_args.kwargs['allow_redirects'])
                    sleep.assert_not_called()

    def test_redirects_are_refused_even_if_caller_requests_following(self):
        for method in ('GET', 'PUT'):
            for status in (301, 302, 307, 308):
                with self.subTest(method=method, status=status):
                    client = self.client()
                    client.session.request.return_value = Mock(
                        status_code=status, headers={'Location': 'https://example.invalid/capture'})
                    with self.assertRaises(ZenodoAPIError) as caught:
                        client._make_request(method, 'deposit/depositions/123', allow_redirects=True)
                    self.assertEqual(caught.exception.diagnostics['status'], status)
                    client.session.request.assert_called_once()
                    self.assertFalse(client.session.request.call_args.kwargs['allow_redirects'])

    def test_provider_body_and_transport_exception_tokens_are_redacted(self):
        token = 'dummy-offline-secret-never-a-real-credential'
        for fault in (Mock(status_code=500, text=token, headers={}),
                      requests.exceptions.Timeout('Authorization: Bearer ' + token)):
            client = self.client()
            if isinstance(fault, Exception):
                client.session.request.side_effect = fault
            else:
                client.session.request.return_value = fault
            with self.assertRaises(ZenodoAPIError) as caught:
                client._make_request('PUT', 'deposit/depositions/123')
            emitted = (str(caught.exception) + repr(caught.exception.diagnostics)
                       + repr(client.logger.mock_calls) + repr(client.api_logger.mock_calls))
            self.assertNotIn(token, emitted)
            client.session.request.assert_called_once()


if __name__ == '__main__':
    unittest.main()
