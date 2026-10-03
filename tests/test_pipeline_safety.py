"""Offline regression tests for draft isolation, rights and recovery boundaries."""

import json
from datetime import datetime, timedelta, timezone
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.path_config import OutputPaths
from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
from scripts.upload_service import DraftUploadService, atomic_json, metadata_hash, prepare_metadata, read_json
from scripts.zenodo_api import ZenodoAPIClient, ZenodoAPIError
from scripts.reconcile_draft import reconcile
from scripts.upload_audit import UploadAuditor


class RightsTests(unittest.TestCase):
    def setUp(self):
        with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
            self.transformer = FGDCToZenodoTransformer()

    def test_explicit_license_denials_are_not_grants(self):
        for text in ('This is not a MIT license', 'No MIT license is granted', 'Apache-2.0 is not applicable', 'MIT License does not apply', 'CC-BY-4.0 does not apply to these data', 'Not covered by the MIT License', 'Apache-2.01'):
            with self.subTest(text=text):
                self.assertIsNone(self.transformer._detect_license(text, 'fixture'))

    def test_gpl_family_does_not_consume_agpl_or_lgpl(self):
        for text in ('AGPL-3.0', 'LGPL-3.0', 'GNU Affero General Public License 3.0', 'GNU Lesser General Public License 3.0'):
            with self.subTest(text=text):
                self.assertIsNone(self.transformer._detect_license(text, 'fixture'))
        self.assertEqual(self.transformer._detect_license('GPL-3.0', 'fixture'), 'gpl-3.0')

    def test_specific_cc_variants_preserve_restrictions_and_version(self):
        for text, expected in [('CC-BY-SA 4.0', 'cc-by-sa-4.0'),
                               ('CC BY-NC 4.0', 'cc-by-nc-4.0'),
                               ('Creative Commons Attribution-ShareAlike 3.0', 'cc-by-sa-3.0'),
                               ('https://creativecommons.org/licenses/by-nc-nd/4.0/', 'cc-by-nc-nd-4.0'),
                               ('CC BY 4.0', 'cc-by-4.0'), ('CC0', 'cc-zero')]:
            with self.subTest(text=text):
                self.assertEqual(self.transformer._detect_license(text, 'fixture'), expected)

    def test_access_and_unknown_terms_do_not_grant_cc0(self):
        for terms in ['', 'None', 'open access', 'All rights reserved. Permission required.', 'CC BY-SA']:
            root = ET.fromstring(f'<metadata><useconst>{terms}</useconst></metadata>')
            metadata = {'license': '', 'access_right': 'open'}
            self.transformer._extract_access_constraints(metadata, root, 'fixture')
            self.assertEqual(metadata['license'], '')


class DraftRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.paths = OutputPaths(self.directory.name, 'sandbox')
        self.file = Path(self.paths.zenodo_json_dir) / 'sample.json'
        metadata = {'title': 'Example dataset', 'upload_type': 'dataset',
                    'publication_date': '2000-01-01', 'description': 'Sample description',
                    'creators': [{'name': 'Smith, Jane'}], 'access_right': 'open',
                    'license': 'cc-zero', 'notes': ''}
        self.file.write_text(json.dumps({'metadata': metadata}))
        (Path(self.paths.original_fgdc_dir) / 'sample.xml').write_text('<metadata><title>Example dataset</title></metadata>')
        self.digest = metadata_hash(prepare_metadata(str(self.file), self.paths)[0])
        atomic_json(self.paths.safe_to_upload_path,
                    {'environment': 'sandbox', 'inventory_complete': True,
                     'files': ['sample.json'], 'metadata_hashes': {'sample.json': self.digest},
                     'valid_until': (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()})
        self.client = Mock(base_url='https://sandbox.zenodo.org')
        self.client.create_deposition.return_value = {'id': 123}
        self.client.update_deposition_metadata.return_value = {'metadata': {}}
        self.service = DraftUploadService(self.paths, 'sandbox')

    def test_reconciliation_cannot_alias_another_source_draft(self):
        self.service.upload(str(self.file), self.client)
        other = Path(self.paths.zenodo_json_dir) / 'other.json'
        other.write_bytes(self.file.read_bytes())
        (Path(self.paths.original_fgdc_dir) / 'other.xml').write_bytes((Path(self.paths.original_fgdc_dir) / 'sample.xml').read_bytes())
        metadata, _, source_hash = prepare_metadata(str(other), self.paths)
        snapshot = {'http_status': 200, 'retrieved_at': '2026-01-01T00:00:00Z',
                    'endpoint': 'https://sandbox.zenodo.org/api/deposit/depositions/123',
                    'confirmed_fgdc_id': 'other', 'confirmed_metadata_sha256': metadata_hash(metadata),
                    'confirmed_source_sha256': source_hash,
                    'body': {'id': 123, 'state': 'unsubmitted', 'files': [], 'metadata': {}}}
        with self.assertRaisesRegex(ValueError, 'shared'):
            reconcile(self.paths, 'other', snapshot, 'Fixture reviewer', 'Source correlation fixture')
        self.assertNotIn('other', read_json(self.paths.uploads_registry_path))

    def test_created_draft_response_cannot_claim_another_source_id(self):
        atomic_json(self.paths.uploads_registry_path, {'other': {'environment': 'sandbox', 'deposition_id': 123}})
        result = self.service.upload(str(self.file), self.client)
        self.assertFalse(result['success'])
        self.assertTrue(result['needs_reconciliation'])
        self.assertNotIn('deposition_id', result)
        self.client.update_deposition_metadata.assert_not_called()

    def test_recovery_snapshot_requires_explicit_state_and_files(self):
        metadata, _, source_hash = prepare_metadata(str(self.file), self.paths)
        snapshot = {'http_status': 200, 'retrieved_at': '2026-01-01T00:00:00Z',
                    'endpoint': 'https://sandbox.zenodo.org/api/deposit/depositions/123',
                    'confirmed_fgdc_id': 'sample', 'confirmed_metadata_sha256': metadata_hash(metadata),
                    'confirmed_source_sha256': source_hash,
                    'body': {'id': 123, 'state': 'unsubmitted', 'files': [], 'metadata': {}}}
        for field in ('state', 'files'):
            incomplete = dict(snapshot, body=dict(snapshot['body']))
            incomplete['body'].pop(field)
            with self.subTest(field=field), self.assertRaises(ValueError):
                reconcile(self.paths, 'sample', incomplete, 'Fixture reviewer', 'Fixture correlation')

    def test_draft_id_survives_failed_update_and_resume_uses_same_id(self):
        self.client.update_deposition_metadata.side_effect = ZenodoAPIError('failed update')
        result = self.service.upload(str(self.file), self.client)
        self.assertFalse(result['success'])
        self.assertEqual(result['deposition_id'], 123)
        self.assertEqual(read_json(self.paths.uploads_registry_path)['sample']['deposition_id'], 123)
        self.client.update_deposition_metadata.side_effect = None
        result = self.service.upload(str(self.file), self.client)
        self.assertTrue(result['success'])
        self.assertEqual(self.client.create_deposition.call_count, 1)
        self.service.upload(str(self.file), self.client)
        self.assertEqual(self.client.update_deposition_metadata.call_count, 2)
        self.assertEqual(self.service.pending_files(), [])

    def test_uncertain_creation_blocks_retry(self):
        self.client.create_deposition.side_effect = ZenodoAPIError('lost response')
        result = self.service.upload(str(self.file), self.client)
        self.assertTrue(result['needs_reconciliation'])
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            self.service.upload(str(self.file), self.client)
        self.assertEqual(self.client.create_deposition.call_count, 1)

    def test_missing_stale_and_wrong_environment_inventory_block_creation(self):
        for envelope in [{}, {'environment': 'production', 'inventory_complete': True},
                         {'environment': 'sandbox', 'inventory_complete': True,
                          'files': ['sample.json'], 'metadata_hashes': {'sample.json': 'stale'}}]:
            atomic_json(self.paths.safe_to_upload_path, envelope)
            with self.assertRaises(ValueError):
                self.service.upload(str(self.file), self.client)
        self.client.create_deposition.assert_not_called()

    def test_environment_state_and_reports_are_isolated_without_legacy_migration(self):
        production = OutputPaths(self.directory.name, 'production')
        legacy = OutputPaths(self.directory.name)
        atomic_json(legacy.uploads_registry_path, {'sample': {'upload_status': 'success'}})
        self.assertNotEqual(self.paths.uploads_registry_path, production.uploads_registry_path)
        self.assertNotEqual(self.paths.upload_reports_dir, production.upload_reports_dir)
        self.assertFalse(Path(production.uploads_registry_path).exists())
        self.assertTrue(Path(legacy.uploads_registry_path).exists())

    def test_wrong_host_and_unknown_license_block_all_writes(self):
        with self.assertRaisesRegex(ValueError, 'host'):
            self.service.upload(str(self.file), Mock(base_url='https://zenodo.org'))
        payload = json.loads(self.file.read_text())
        payload['metadata']['license'] = ''
        self.file.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, '[Ll]icense'):
            self.service.upload(str(self.file), self.client)
        self.client.create_deposition.assert_not_called()

    def test_duplicate_inventory_failure_invalidates_old_authorization(self):
        checker = PreUploadDuplicateChecker.__new__(PreUploadDuplicateChecker)
        checker.paths = self.paths
        checker.sandbox = True
        checker.community_identifier = 'pices'
        checker.client = Mock()
        checker.client.get_records_by_query.side_effect = ZenodoAPIError('inventory unavailable')
        with self.assertRaises(ZenodoAPIError):
            checker.load_existing_zenodo_records()
        self.assertFalse(read_json(self.paths.safe_to_upload_path)['inventory_complete'])
        with self.assertRaises(ValueError):
            self.service.pending_files()

    def test_owned_drafts_are_in_duplicate_inventory(self):
        checker = PreUploadDuplicateChecker.__new__(PreUploadDuplicateChecker)
        checker.paths, checker.sandbox, checker.community_identifier = self.paths, True, 'pices'
        checker.client = Mock()
        checker.client.get_records_by_query.return_value = []
        checker.client.get_all_my_depositions.return_value = [{'id': 123, 'state': 'unsubmitted', 'metadata': {'title': 'Example dataset'}}]
        inventory = checker.load_existing_zenodo_records()
        self.assertIn('example dataset', inventory['titles'])
        self.assertFalse(checker.check_file_for_duplicates(str(self.file), inventory)['safe_to_upload'])

    def test_expired_inventory_blocks_new_creation(self):
        safe = read_json(self.paths.safe_to_upload_path)
        safe['valid_until'] = '2000-01-01T00:00:00+00:00'
        atomic_json(self.paths.safe_to_upload_path, safe)
        with self.assertRaisesRegex(ValueError, 'expired'):
            self.service.upload(str(self.file), self.client)
        self.client.create_deposition.assert_not_called()

    def test_human_reconciliation_resumes_uncertain_create_without_another_post(self):
        self.client.create_deposition.side_effect = ZenodoAPIError('lost response')
        self.service.upload(str(self.file), self.client)
        metadata, _, source_hash = prepare_metadata(str(self.file), self.paths)
        snapshot = {'endpoint': 'https://sandbox.zenodo.org/api/deposit/depositions/123',
                    'http_status': 200, 'retrieved_at': '2026-01-01T00:00:00Z',
                    'confirmed_fgdc_id': 'sample', 'confirmed_metadata_sha256': metadata_hash(metadata),
                    'confirmed_source_sha256': source_hash,
                    'body': {'id': 123, 'state': 'unsubmitted', 'files': [], 'metadata': {}}}
        reconcile(self.paths, 'sample', snapshot, 'Fixture reviewer', 'Offline source correlation test')
        self.client.create_deposition.side_effect = None
        self.assertTrue(self.service.upload(str(self.file), self.client)['success'])
        self.assertEqual(self.client.create_deposition.call_count, 1)

    def test_reconciliation_rejects_wrong_environment_or_conflicting_id(self):
        snapshot = {'endpoint': 'https://zenodo.org/api/deposit/depositions/123',
                    'http_status': 200, 'retrieved_at': '2026-01-01T00:00:00Z',
                    'confirmed_fgdc_id': 'sample', 'body': {'id': 123}}
        with self.assertRaises(ValueError):
            reconcile(self.paths, 'sample', snapshot, 'Fixture reviewer', 'Offline test')

    def test_audit_counts_unique_ledger_records_not_duplicate_report_entries(self):
        self.service.upload(str(self.file), self.client)
        atomic_json(self.paths.upload_log_path, [{'success': True}, {'success': True}])
        analysis = UploadAuditor(self.directory.name).analyze_upload_logs()
        self.assertEqual(analysis['summary']['total_files_processed'], 1)
        self.assertEqual(analysis['coverage_status'], 'local_ledger_only')


class RetryTests(unittest.TestCase):
    def test_post_transport_failure_is_not_replayed(self):
        client = ZenodoAPIClient.__new__(ZenodoAPIClient)
        client._rate_limit_check = Mock()
        client.api_url = 'https://example.invalid/api/'
        client.max_retries = 3
        client.session = Mock()
        client.session.request.side_effect = requests.exceptions.Timeout('lost response')
        with self.assertRaises(ZenodoAPIError):
            client.create_deposition()
        self.assertEqual(client.session.request.call_count, 1)

class InventoryResponseTests(unittest.TestCase):
    def test_malformed_and_truncated_inventory_block(self):
        client = ZenodoAPIClient.__new__(ZenodoAPIClient)
        for response in ({}, {'hits': {'hits': [], 'total': 1}}, {'hits': {'hits': [{'id': 1}], 'total': 2}}, {'hits': {'hits': [], 'total': {'value': 0, 'relation': 'gte'}}}):
            client.search_records = Mock(return_value=response)
            with self.subTest(response=response), self.assertRaises(ValueError):
                client.get_records_by_query(size=2)

    def test_complete_paginated_inventory(self):
        client = ZenodoAPIClient.__new__(ZenodoAPIClient)
        client.search_records = Mock(side_effect=[{'hits': {'hits': [{'id': 1}], 'total': 2}, 'links': {'next': 'next'}}, {'hits': {'hits': [{'id': 2}], 'total': 2}}])
        self.assertEqual([row['id'] for row in client.get_records_by_query(size=1)], [1, 2])

class InventoryStructureTests(unittest.TestCase):
    def test_owned_draft_inventory_requires_valid_unique_records(self):
        client = ZenodoAPIClient.__new__(ZenodoAPIClient)
        for payload in ({}, None, [{'id': True}], [{'id': 1}, {'id': 1}]):
            client._make_request = Mock(return_value=Mock(json=Mock(return_value=payload)))
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                client.get_all_my_depositions()
        client._make_request = Mock(side_effect=[Mock(json=Mock(return_value=[{'id': 1}])), Mock(json=Mock(return_value=[{'id': 1}]))])
        with self.assertRaises(ValueError):
            client.get_all_my_depositions(page_size=1)

    def test_published_inventory_repeated_ids_do_not_prove_completeness(self):
        client = ZenodoAPIClient.__new__(ZenodoAPIClient)
        client.search_records = Mock(side_effect=[{'hits': {'hits': [{'id': 1}], 'total': 2}, 'links': {'next': 'next'}}, {'hits': {'hits': [{'id': 1}], 'total': 2}}])
        with self.assertRaises(ValueError):
            client.get_records_by_query(size=1)
