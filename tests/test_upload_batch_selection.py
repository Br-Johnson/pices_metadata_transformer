"""Compatibility uploader batches select pending records and report only their work."""
from datetime import datetime, timedelta, timezone
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.path_config import OutputPaths
from scripts.upload_service import DraftUploadService, atomic_json, metadata_hash, prepare_metadata, read_json
from scripts.upload_to_zenodo import ZenodoUploader
from scripts.zenodo_api import ZenodoAPIError


class UploadBatchSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = OutputPaths(self.tmp.name, 'sandbox')
        self.files = self.prepare_files(3)
        identifiers = itertools.count(101)
        self.client = Mock(base_url='https://sandbox.zenodo.org')
        self.client.create_deposition.side_effect = lambda: {'id': next(identifiers)}
        self.client.update_deposition_metadata.side_effect = lambda identifier, metadata, **kwargs: {'id': identifier, 'metadata': metadata}
        with patch('scripts.upload_to_zenodo.get_logger', return_value=Mock()):
            self.uploader = ZenodoUploader(output_dir=self.tmp.name)
        self.uploader.client = self.client
        self.service = DraftUploadService(self.paths, 'sandbox')

    def prepare_files(self, count):
        files, fingerprints = [], {}
        for number in range(count):
            name = f'synthetic-{number:02d}'
            source = Path(self.paths.original_fgdc_dir, name + '.xml')
            source.write_text('<metadata><title>' + name + '</title></metadata>')
            file = Path(self.paths.zenodo_json_dir, name + '.json')
            file.write_text(json.dumps({'metadata': {
                'title': name, 'description': 'Synthetic batch selection fixture only',
                'upload_type': 'dataset', 'publication_date': '2000-01-01',
                'creators': [{'name': 'Smith, Jane'}], 'access_right': 'open', 'license': 'cc-zero',
                'notes': '', 'communities': [{'identifier': 'synthetic-fixture-only'}]}}))
            files.append(str(file))
            fingerprints[file.name] = metadata_hash(prepare_metadata(str(file), self.paths)[0])
        atomic_json(self.paths.safe_to_upload_path, {
            'environment': 'sandbox', 'inventory_complete': True,
            'files': [Path(f).name for f in files], 'metadata_hashes': fingerprints,
            'valid_until': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
        return files

    def call(self, files, limit=None):
        with patch('scripts.upload_to_zenodo.tqdm', side_effect=lambda values, **kwargs: values):
            return self.uploader.upload_files(files, limit)

    def test_zero_limit_preserves_wrapper_unlimited_behavior(self):
        summary = self.call(self.files, limit=0)
        self.assertEqual(summary['total_files'], 3)
        self.assertEqual(summary['successful_uploads'], 3)
        self.assertEqual(summary['failed_uploads'], 0)
        self.assertEqual(self.client.create_deposition.call_count, 3)

    def test_completed_prefix_does_not_consume_limit(self):
        self.assertTrue(self.service.upload(self.files[0], self.client)['success'])
        self.client.reset_mock()
        summary = self.call(self.files, limit=1)
        self.assertEqual(self.client.create_deposition.call_count, 1)
        self.assertEqual(summary['total_files'], 1)
        self.assertEqual(summary['successful_uploads'], 1)
        self.assertEqual(summary['failed_uploads'], 0)
        self.assertEqual(summary['success_rate'], 100)
        ledger = read_json(self.paths.uploads_registry_path)
        self.assertEqual(ledger['synthetic-01']['upload_status'], 'success')
        self.assertNotIn('synthetic-02', ledger)
        self.assertEqual(self.uploader.stats['skipped_files'], 1)

    def test_each_invocation_statistics_and_histograms_describe_only_that_work(self):
        first = self.call([self.files[0]], limit=1)
        self.assertEqual(first['success_rate'], 100)
        self.client.update_deposition_metadata.side_effect = ZenodoAPIError('Synthetic current-call failure')
        failed = self.call([self.files[1]], limit=1)
        self.assertEqual((failed['total_files'], failed['successful_uploads'], failed['failed_uploads']), (1, 0, 1))
        self.assertEqual(failed['success_rate'], 0)
        self.assertEqual(failed['upload_types'], {})
        self.assertEqual(failed['communities'], {})
        self.assertEqual(failed['error_types'], {'Synthetic current-call failure': 1})
        before = self.client.create_deposition.call_count
        empty = self.call([self.files[0]], limit=1)
        self.assertEqual((empty['total_files'], empty['successful_uploads'], empty['failed_uploads']), (0, 0, 0))
        self.assertEqual(empty['success_rate'], 0)
        self.assertEqual(empty['upload_types'], {})
        self.assertEqual(empty['communities'], {})
        self.assertEqual(empty['error_types'], {})
        self.assertEqual(self.client.create_deposition.call_count, before)
        self.assertEqual(read_json(self.uploader.upload_log_path), [])
        self.assertEqual(read_json(self.uploader.upload_errors_path), [])
        ledger = read_json(self.paths.uploads_registry_path)
        self.assertEqual(ledger['synthetic-00']['upload_status'], 'success')
        self.assertEqual(ledger['synthetic-01']['upload_status'], 'failed')

    def test_limit_applies_to_caller_subset_order_after_pending_filter(self):
        summary = self.call([self.files[2], self.files[1]], limit=1)
        self.assertEqual(summary['successful_uploads'], 1)
        ledger = read_json(self.paths.uploads_registry_path)
        self.assertEqual(list(ledger), ['synthetic-02'])

    def test_synthetic_limit_ten_smoke_and_unchanged_rerun(self):
        files = self.prepare_files(12)
        self.assertTrue(self.service.upload(files[0], self.client)['success'])
        self.client.reset_mock()
        summary = self.call(files, limit=10)
        self.assertEqual((summary['total_files'], summary['successful_uploads'], summary['failed_uploads']), (10, 10, 0))
        self.assertEqual(summary['success_rate'], 100)
        self.assertEqual(self.client.create_deposition.call_count, 10)
        ledger = read_json(self.paths.uploads_registry_path)
        self.assertEqual(len(ledger), 11)
        self.assertNotIn('synthetic-11', ledger)
        completed = files[:11]
        before = self.client.create_deposition.call_count
        rerun = self.call(completed, limit=10)
        self.assertEqual((rerun['total_files'], rerun['successful_uploads'], rerun['failed_uploads']), (0, 0, 0))
        self.assertEqual(self.client.create_deposition.call_count, before)
        self.client.publish_deposition.assert_not_called()
        self.client.delete_deposition.assert_not_called()


if __name__ == '__main__':
    unittest.main()
