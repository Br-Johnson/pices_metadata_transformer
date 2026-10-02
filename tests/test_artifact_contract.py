"""Offline original XML attachment, readback, recovery and QA regressions."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.artifact_contract import prepare_artifact, validate_files
from scripts.path_config import OutputPaths
from scripts.qa_manifest import prepare_manifest, validate_approval, QA_CHECKS
from scripts.reconcile_draft import reconcile
from scripts.upload_service import DraftUploadService, atomic_json, metadata_hash, prepare_metadata, read_json
from scripts.verify_uploads import ZenodoVerifier
from scripts.publish_records import RecordPublisher
from scripts.zenodo_api import ZenodoAPIClient, ZenodoAPIError


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.paths = OutputPaths(self.directory.name, 'sandbox')
        self.source = Path(self.paths.original_fgdc_dir) / 'sample.xml'
        self.raw = b'<metadata><title>Descriptive catalogue entry</title></metadata>'
        self.source.write_bytes(self.raw)
        self.json_file = Path(self.paths.zenodo_json_dir) / 'sample.json'
        self.payload = {
            'metadata': {'title': 'Original XML metadata artifact', 'upload_type': 'other',
                         'publication_date': '2000-01-01', 'description': 'Descriptive catalogue entry',
                         'creators': [{'name': 'Example Institute', 'type': 'Organization'}],
                         'access_right': 'open', 'license': 'cc-by-4.0', 'notes': ''},
            'artifact_policy': {'schema_version': 1, 'object_kind': 'original_fgdc_xml',
                                'resource_type': 'other', 'date_semantics': 'source_metadata_date',
                                'source_sha256': hashlib.sha256(self.raw).hexdigest(),
                                'reviewer': 'Fixture reviewer', 'reviewed_at': '2026-10-02',
                                'rationale': 'Fixture object decision only',
                                'rights_evidence': 'Synthetic fixture grant; not real source permission',
                                'date_evidence': 'Synthetic fixture date; not a real source date'},
            'content_classification': {'inventory_complete': True, 'reviewer': 'Fixture reviewer',
                                       'reviewed_at': '2026-10-02', 'rationale': 'XML contains descriptions',
                                       'files': [{'name': 'sample.xml', 'role': 'descriptive_metadata',
                                                  'evidence': 'Inspected synthetic XML'}]},
        }
        self.write_payload()
        self.metadata = prepare_metadata(str(self.json_file), self.paths)[0]
        atomic_json(self.paths.safe_to_upload_path,
                    {'environment': 'sandbox', 'inventory_complete': True,
                     'files': ['sample.json'], 'metadata_hashes': {'sample.json': metadata_hash(self.metadata)},
                     'valid_until': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
        self.remote = {'id': 123, 'state': 'inprogress', 'submitted': False, 'metadata': {}, 'files': []}
        self.client = Mock(base_url='https://sandbox.zenodo.org')
        self.client.create_deposition.return_value = {'id': 123}
        self.client.get_deposition.side_effect = lambda _: copy.deepcopy(self.remote)
        self.client.update_deposition_metadata.side_effect = self.update
        self.client.upload_file.side_effect = self.attach
        self.service = DraftUploadService(self.paths, 'sandbox')

    def write_payload(self):
        self.json_file.write_text(json.dumps(self.payload))

    def update(self, identifier, metadata):
        self.assertEqual(identifier, 123)
        self.remote['metadata'] = copy.deepcopy(metadata)
        return copy.deepcopy(self.remote)

    def attach(self, identifier, path, filename):
        self.assertEqual(identifier, 123)
        raw = Path(path).read_bytes()
        self.assertEqual(raw, self.raw)
        self.assertNotEqual(Path(path), self.source)
        self.remote['files'] = [{'filename': filename, 'filesize': len(raw),
                                'checksum': 'md5:' + hashlib.md5(raw, usedforsecurity=False).hexdigest()}]
        return copy.deepcopy(self.remote['files'][0])

    def upload(self):
        return self.service.upload(str(self.json_file), self.client)

    def approve(self, paths, entry):
        atomic_json(paths.uploads_registry_path, {'sample': entry})
        manifest = prepare_manifest(paths)
        row = manifest['records'][0]
        row['qa'] = {'approved': True, 'reviewer': 'Fixture reviewer', 'reviewed_at': '2026-10-02',
                     'rationale': 'Fixture approval only', 'checks': dict.fromkeys(QA_CHECKS, True)}
        row['duplicate_review'] = {'status': 'reviewed', 'classification': 'checked_no_match',
                                   'rationale': 'Synthetic inventory only', 'evidence': ['fixture']}
        return manifest

    def test_attachment_readback_and_idempotent_rerun(self):
        result = self.upload()
        self.assertTrue(result['success'], result.get('error'))
        self.assertEqual(result['artifact_contract']['files'][0]['sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertIn('pices-metadata-only', result['metadata']['keywords'])
        self.assertEqual(self.source.read_bytes(), self.raw)
        self.assertTrue(self.upload()['success'])
        self.client.create_deposition.assert_called_once()
        self.client.update_deposition_metadata.assert_called_once()
        self.client.upload_file.assert_called_once()
        self.client.publish_deposition.assert_not_called()
        self.assertEqual(self.service.pending_files(), [])
        verifier = ZenodoVerifier.__new__(ZenodoVerifier)
        verifier.paths, verifier.client, verifier.logger = self.paths, self.client, Mock()
        self.assertTrue(verifier._verify_single_record(result)['verification_successful'])

    def test_documented_synthetic_contract_example(self):
        example = json.loads((Path(__file__).resolve().parents[1] / 'contracts/examples/original_xml_artifact.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / example['source_filename']
            source.write_bytes(example['source_utf8'].encode())
            contract = prepare_artifact(example['transformed_payload'], source)
            self.assertEqual(contract['object_kind'], 'original_fgdc_xml')
            self.assertEqual(contract['files'][0]['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError, 'missing'):
                validate_files([], contract)

    def test_lost_attachment_response_resumes_without_new_create_or_put(self):
        def lost(*args, **kwargs):
            self.attach(*args, **kwargs)
            raise ZenodoAPIError('Lost attachment response')
        self.client.upload_file.side_effect = lost
        self.assertFalse(self.upload()['success'])
        self.assertEqual(read_json(self.paths.uploads_registry_path)['sample']['deposition_id'], 123)
        self.client.upload_file.side_effect = self.attach
        self.assertTrue(self.upload()['success'])
        self.client.create_deposition.assert_called_once()
        self.client.upload_file.assert_called_once()

    def test_missing_readback_does_not_claim_success(self):
        self.client.upload_file.side_effect = lambda *a, **k: {}
        result = self.upload()
        self.assertFalse(result['success'])
        self.assertIn('missing', result['error'])
        self.assertEqual(result['deposition_id'], 123)

    def test_unexpected_or_corrupt_file_blocks_without_overwrite(self):
        for filename, size, checksum in [('foreign.xml', 10, 'md5:bad'), ('sample.xml', len(self.raw), 'md5:bad')]:
            with self.subTest(filename=filename):
                self.remote['files'] = [{'filename': filename, 'filesize': size, 'checksum': checksum}]
                self.assertFalse(self.upload()['success'])
        self.client.upload_file.assert_not_called()
        self.client.update_deposition_metadata.assert_not_called()
        self.client.create_deposition.assert_called_once()

    def test_changed_source_invalidates_policy_before_any_write(self):
        self.source.write_bytes(self.raw + b'\n')
        with self.assertRaisesRegex(ValueError, 'source hash'):
            self.upload()
        self.client.create_deposition.assert_not_called()

    def test_changed_policy_and_remote_file_invalidate_existing_success(self):
        self.assertTrue(self.upload()['success'])
        self.remote['files'][0]['checksum'] = 'md5:wrong'
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.upload()
        self.payload['artifact_policy']['rights_evidence'] = 'Revised fixture decision'
        self.write_payload()
        with self.assertRaisesRegex(ValueError, 'policy changed'):
            self.upload()
        self.client.create_deposition.assert_called_once()
        self.client.upload_file.assert_called_once()

    def test_missing_policy_provenance_or_wrong_inventory_fail_closed(self):
        for mutation in ('rights', 'file', 'type'):
            payload = copy.deepcopy(self.payload)
            if mutation == 'rights':
                del payload['artifact_policy']['rights_evidence']
            elif mutation == 'file':
                payload['content_classification']['files'][0]['name'] = 'other.xml'
            else:
                payload['metadata']['upload_type'] = 'dataset'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                prepare_artifact(payload, self.source)

    def test_qa_binds_file_policy_and_live_checksum(self):
        entry = self.upload()
        manifest = self.approve(self.paths, entry)
        validate_approval(manifest, 'sample', entry, self.paths, self.remote['metadata'], self.remote['files'])
        bad_files = copy.deepcopy(self.remote['files'])
        bad_files[0]['checksum'] = 'md5:wrong'
        with self.assertRaisesRegex(ValueError, 'checksum'):
            validate_approval(manifest, 'sample', entry, self.paths, self.remote['metadata'], bad_files)
        manifest['records'][0]['artifact_contract']['files'][0]['sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'artifact approval'):
            validate_approval(manifest, 'sample', entry, self.paths)

    def test_production_mock_publication_verifies_approved_attachment(self):
        entry = self.upload()
        paths = OutputPaths(self.directory.name, 'production')
        target = Path(paths.zenodo_json_dir) / 'sample.json'
        target.write_bytes(self.json_file.read_bytes())
        # Both environments use the same immutable original source directory.
        entry = dict(entry, environment='production', json_file=str(target), zenodo_url='https://zenodo.org/deposit/123')
        manifest = self.approve(paths, entry)
        with patch('scripts.publish_records.create_zenodo_client', return_value=self.client), patch('scripts.publish_records.get_logger', return_value=Mock()):
            publisher = RecordPublisher(False, self.directory.name, manifest)
        def publish(_):
            self.remote.update(state='done', submitted=True)
            return copy.deepcopy(self.remote)
        self.client.publish_deposition.side_effect = publish
        self.remote['files'][0]['checksum'] = 'md5:wrong'
        self.assertFalse(publisher._publish_single_record(entry)['publish_successful'])
        self.client.publish_deposition.assert_not_called()
        self.remote['files'][0]['checksum'] = 'md5:' + hashlib.md5(self.raw, usedforsecurity=False).hexdigest()
        self.assertTrue(publisher._publish_single_record(entry)['publish_successful'])
        self.client.publish_deposition.assert_called_once()
        self.assertTrue(publisher._publish_single_record(entry)['already_published'])
        self.client.publish_deposition.assert_called_once()

    def test_final_publication_readback_metadata_drift_is_not_reported_successful(self):
        entry = self.upload()
        paths = OutputPaths(self.directory.name, 'production')
        target = Path(paths.zenodo_json_dir) / 'sample.json'
        target.write_bytes(self.json_file.read_bytes())
        entry = dict(entry, environment='production', json_file=str(target), zenodo_url='https://zenodo.org/deposit/123')
        manifest = self.approve(paths, entry)
        with patch('scripts.publish_records.create_zenodo_client', return_value=self.client), patch('scripts.publish_records.get_logger', return_value=Mock()):
            publisher = RecordPublisher(False, self.directory.name, manifest)
        def publish(_):
            self.remote.update(state='done', submitted=True)
            self.remote['metadata']['license'] = 'cc-zero'
            return copy.deepcopy(self.remote)
        self.client.publish_deposition.side_effect = publish
        result = publisher._publish_single_record(entry)
        self.assertFalse(result['publish_successful'])
        self.assertIn('QA-approved', result['error'])
        self.assertFalse(publisher._publish_single_record(entry)['publish_successful'])
        self.client.publish_deposition.assert_called_once()

    def test_nasa_organizational_origin_preserves_entire_name(self):
        import xml.etree.ElementTree as ET
        from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
        with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
            transformer = FGDCToZenodoTransformer()
        name = 'National Aeronautics and Space Administration (NASA)'
        root = ET.fromstring('<metadata><idinfo><citation><citeinfo><origin>' + name + '</origin></citeinfo></citation></idinfo></metadata>')
        self.assertEqual(transformer._extract_creators(root, 'fixture'), [{'name': name, 'type': 'Organization'}])

    def test_reconcile_matching_attachment_and_environment_gate(self):
        entry = self.upload()
        snapshot = {'http_status': 200, 'retrieved_at': '2026-10-02',
                    'endpoint': 'https://sandbox.zenodo.org/api/deposit/depositions/123',
                    'confirmed_fgdc_id': 'sample', 'confirmed_metadata_sha256': entry['metadata_sha256'],
                    'confirmed_source_sha256': entry['source_sha256'], 'body': copy.deepcopy(self.remote)}
        result = reconcile(self.paths, 'sample', snapshot, 'Fixture reviewer', 'Reviewed fixture identity')
        self.assertEqual(result['artifact_contract'], entry['artifact_contract'])
        snapshot['endpoint'] = 'https://zenodo.org/api/deposit/depositions/123'
        with self.assertRaisesRegex(ValueError, 'environment'):
            reconcile(self.paths, 'sample', snapshot, 'Fixture reviewer', 'Fixture')

    def test_bucket_host_redirect_and_timeout_boundaries(self):
        client = ZenodoAPIClient.__new__(ZenodoAPIClient)
        client.sandbox, client.access_token = True, 'synthetic-fixture-token'
        client.get_deposition = Mock()
        with patch('scripts.zenodo_api.requests.put') as put:
            for bucket in ('https://zenodo.org/api/files/example', 'https://sandbox.zenodo.org.evil.example/api/files/example',
                           'http://sandbox.zenodo.org/api/files/example', 'https://sandbox.zenodo.org/api/files/example?redirect=1'):
                client.get_deposition.return_value = {'id': 123, 'links': {'bucket': bucket}}
                with self.subTest(bucket=bucket), self.assertRaises(ZenodoAPIError):
                    client.upload_file(123, str(self.source))
            put.assert_not_called()
            for bucket in ('https://sandbox.zenodo.org/api/files/..', 'https://sandbox.zenodo.org/api/files/%2e%2e'):
                client.get_deposition.return_value = {'id': 123, 'links': {'bucket': bucket}}
                with self.subTest(bucket=bucket), self.assertRaises(ZenodoAPIError):
                    client.upload_file(123, str(self.source))
            client.get_deposition.return_value = {'id': 999, 'links': {'bucket': 'https://sandbox.zenodo.org/api/files/568377dd-daf8-4235-85e1-a56011ad454b'}}
            with self.assertRaisesRegex(ZenodoAPIError, 'requested deposition'):
                client.upload_file(123, str(self.source))
            put.assert_not_called()
            client.get_deposition.return_value = {'id': 123, 'links': {'bucket': 'https://sandbox.zenodo.org/api/files/568377dd-daf8-4235-85e1-a56011ad454b'}}
            put.return_value.status_code = 302
            with self.assertRaisesRegex(ZenodoAPIError, '302'):
                client.upload_file(123, str(self.source))
            self.assertFalse(put.call_args.kwargs['allow_redirects'])
            self.assertEqual(put.call_args.kwargs['timeout'], (10, 60))
            put.return_value.status_code = 201
            client.upload_file(123, str(self.source), filename='source space.xml')
            self.assertTrue(put.call_args.args[0].endswith('/source%20space.xml'))


if __name__ == '__main__':
    unittest.main()
