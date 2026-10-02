"""Offline delegated agent QA: evidence supports approval, not upload counts."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.agent_qa import build_manifest
from scripts.artifact_contract import prepare_artifact
from scripts.matching.evidence import snapshot_inventory
from scripts.path_config import OutputPaths
from scripts.qa_manifest import (approved_population_hash, validate_approval, validate_program_review)
from scripts.upload_service import atomic_json, metadata_hash, prepare_metadata


class AgentQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.paths = OutputPaths(self.tmp.name, 'production')
        self.source = Path(self.paths.original_fgdc_dir, 'sample.xml')
        self.raw = (b'<metadata><idinfo><citation><citeinfo><title>Metadata catalogue</title>'
                    b'<origin>Example Marine Institute</origin><pubdate>19770101</pubdate></citeinfo></citation>'
                    b'<descript><abstract>Original descriptive metadata.</abstract></descript><useconst>CC0</useconst>'
                    b'</idinfo><metainfo><metd>20020430</metd>'
                    b'<metuc>CC BY 4.0</metuc></metainfo></metadata>')
        self.source.write_bytes(self.raw)
        self.file = Path(self.paths.zenodo_json_dir, 'sample.json')
        self.payload = {'metadata': {'title': 'Metadata catalogue', 'description': 'Original descriptive metadata.',
                                    'publication_date': '2002-04-30', 'upload_type': 'other',
                                    'creators': [{'name': 'Example Marine Institute', 'type': 'Organization'}],
                                    'license': 'cc-by-4.0', 'access_right': 'open', 'notes': ''},
                        'artifact_policy': {'schema_version': 1, 'object_kind': 'original_fgdc_xml',
                                            'resource_type': 'other', 'date_semantics': 'source_metadata_date',
                                            'source_sha256': hashlib.sha256(self.raw).hexdigest(),
                                            'reviewer': 'Fixture record assessor', 'reviewed_at': '2026-01-01',
                                            'rationale': 'Fixture', 'rights_evidence': 'Explicit source XML grant',
                                            'date_evidence': 'Source metainfo.metd', 'rights_scope': 'original_fgdc_xml',
                                            'rights_source_xpath': './metainfo/metuc', 'license': 'cc-by-4.0'},
                        'content_classification': {'inventory_complete': True, 'reviewer': 'Fixture assessor',
                                                   'reviewed_at': '2026-01-01', 'rationale': 'Inspected fixture',
                                                   'files': [{'name': 'sample.xml', 'role': 'descriptive_metadata',
                                                              'evidence': 'Inspected descriptive XML'}]}}
        self.remote_path, self.duplicate_path = Path(self.tmp.name, 'remote.json'), Path(self.tmp.name, 'duplicates.json')
        self.inputs = {'sample': {'remote_snapshot': str(self.remote_path), 'duplicate_snapshot': str(self.duplicate_path)}}
        self.sync()

    def sync(self):
        now = datetime.now(timezone.utc).isoformat()
        self.file.write_text(json.dumps(self.payload))
        metadata, _, source_hash = prepare_metadata(str(self.file), self.paths)
        contract = prepare_artifact(self.payload, self.source)
        self.entry = {'environment': 'production', 'deposition_id': 123, 'upload_status': 'success',
                      'zenodo_url': 'https://zenodo.org/deposit/123', 'json_file': str(self.file),
                      'source_sha256': source_hash, 'metadata_sha256': metadata_hash(metadata), 'artifact_contract': contract}
        atomic_json(self.paths.uploads_registry_path, {'sample': self.entry})
        file = contract['files'][0]
        self.remote = {'endpoint': 'https://zenodo.org/api/deposit/depositions/123', 'http_status': 200,
                       'retrieved_at': now, 'body': {'id': 123, 'state': 'inprogress',
                       'submitted': False, 'metadata': metadata,
                       'files': [{'filename': file['name'], 'filesize': file['size'], 'checksum': 'sha256:' + file['sha256']}]}}
        atomic_json(self.remote_path, self.remote)
        snapshot = {'repository': 'fixture repository', 'endpoint': 'https://example.invalid/dois',
                    'retrieved_at': now, 'query': 'Metadata catalogue',
                    'scope': 'Explicit fixture title search only; not real global repository absence',
                    'http_status': 200, 'format': 'datacite', 'scope_complete': True,
                    'body': {'data': [], 'links': {}, 'meta': {'total': 0}}}
        parsed = snapshot_inventory(snapshot)
        self.duplicates = {'schema_version': 1, 'status': 'checked_no_match', 'inventory_complete': True,
                           'environment': 'production', 'fgdc_id': 'sample', 'source_sha256': source_hash,
                           'metadata_sha256': metadata_hash(metadata), 'candidates': [], 'scope': 'Fixture title search',
                           'checked_at': now,
                           'valid_until': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                           'evidence': [{'status': 'checked_no_match', 'inventory_complete': True,
                                         'endpoint': snapshot['endpoint'], 'scope': snapshot['scope'],
                                         'response_sha256': parsed['response_sha256'], 'snapshot': snapshot}]}
        atomic_json(self.duplicate_path, self.duplicates)

    def build(self):
        with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
            return build_manifest(self.paths, self.inputs, 'Codex fixture agent', 'fixture-run', revision='fixture-revision')

    def test_supported_source_metadata_date_org_xml_grant_approved_with_honest_provenance(self):
        manifest = self.build()
        record = manifest['records'][0]
        self.assertTrue(record['qa']['approved'], record.get('hold_reasons'))
        self.assertEqual(record['qa']['reviewer_type'], 'agent')
        self.assertEqual(record['qa']['run_id'], 'fixture-run')
        validate_approval(manifest, 'sample', self.entry, self.paths)
        with self.assertRaisesRegex(ValueError, 'Program'):
            validate_program_review(manifest)

    def test_unknown_rights_hold_even_restricted_and_underlying_grant_does_not_relicense_xml(self):
        for change in ('scope', 'restricted', 'underlying'):
            with self.subTest(change=change):
                original = copy.deepcopy(self.payload)
                if change == 'scope':
                    self.payload['artifact_policy'].pop('rights_scope')
                elif change == 'restricted':
                    self.payload['metadata'].update(access_right='restricted', license='')
                    self.payload['artifact_policy']['license'] = ''
                else:
                    self.source.write_bytes(self.raw.replace(b'<metuc>CC BY 4.0', b'<metuc>Unknown'))
                    self.payload['artifact_policy']['source_sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
                self.sync()
                self.assertFalse(self.build()['records'][0]['qa']['approved'])
                self.payload = original
                self.source.write_bytes(self.raw)

    def test_unknown_date_and_creator_ambiguity_held(self):
        for old, new in [(b'20020430', b'122003'), (b'Example Marine Institute', b'Alice and Bob')]:
            with self.subTest(new=new):
                self.source.write_bytes(self.raw.replace(old, new))
                self.payload['artifact_policy']['source_sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
                self.sync()
                self.assertFalse(self.build()['records'][0]['qa']['approved'])
                self.source.write_bytes(self.raw)

    def test_changed_source_payload_files_and_saved_response_block_stale_approval(self):
        manifest = self.build()
        for mutation in ('source', 'payload', 'files', 'id'):
            with self.subTest(mutation=mutation):
                if mutation == 'source':
                    self.source.write_bytes(self.raw + b'\n')
                elif mutation == 'payload':
                    changed = copy.deepcopy(self.payload); changed['metadata']['license'] = 'cc-zero'
                    self.file.write_text(json.dumps(changed))
                else:
                    changed = copy.deepcopy(self.remote)
                    if mutation == 'files': changed['body']['files'][0]['checksum'] = 'md5:wrong'
                    else: changed['body']['id'] = 456
                    atomic_json(self.remote_path, changed)
                with self.assertRaises((ValueError, OSError)):
                    validate_approval(manifest, 'sample', self.entry, self.paths)
                self.source.write_bytes(self.raw); self.file.write_text(json.dumps(self.payload)); atomic_json(self.remote_path, self.remote)

    def test_malformed_or_incomplete_remote_and_duplicate_evidence_held(self):
        for mutation in ('files_missing', 'wrong_id', 'partial', 'html', 'forged_empty', 'expired'):
            with self.subTest(mutation=mutation):
                self.sync()
                if mutation in ('files_missing', 'wrong_id'):
                    if mutation == 'files_missing': self.remote['body'].pop('files')
                    else: self.remote['body']['id'] = 456
                    atomic_json(self.remote_path, self.remote)
                else:
                    proof = self.duplicates['evidence'][0]
                    if mutation == 'partial': proof['snapshot']['body']['links']['next'] = 'https://example.invalid/page2'
                    elif mutation == 'html': proof['snapshot']['body'] = '<html>app</html>'
                    elif mutation == 'forged_empty': proof.pop('snapshot')
                    else: self.duplicates['valid_until'] = '2000-01-01T00:00:00Z'
                    atomic_json(self.duplicate_path, self.duplicates)
                self.assertFalse(self.build()['records'][0]['qa']['approved'])

    def test_program_review_is_bound_to_population_and_honest_sample(self):
        manifest = self.build()
        digest = approved_population_hash(manifest)
        for key in manifest['program_review']:
            manifest['program_review'][key] = {'status': 'reviewed', 'reviewer_type': 'agent',
                'reviewer': 'Independent fixture assessor', 'reviewed_at': '2026-01-01', 'rationale': 'Fixture only',
                'population_sha256': digest, 'evidence': [{'scope': 'Fixture program process', 'reference': 'fixture-log'}],
                'sampled_ids': ['sample'], 'risk_strata': ['explicit XML license and institutional author']}
        validate_program_review(manifest)
        manifest['records'][0]['metadata_sha256'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'stale'):
            validate_program_review(manifest)

    def test_schema1_cannot_impersonate_human_with_agent_review(self):
        manifest = self.build(); manifest['schema_version'] = 1
        with self.assertRaisesRegex(ValueError, 'human'):
            validate_approval(manifest, 'sample', self.entry, self.paths)

    def test_live_metadata_files_validation_does_not_rehash_publication_state(self):
        manifest = self.build()
        done = copy.deepcopy(self.remote['body']); done.update(state='done', submitted=True)
        validate_approval(manifest, 'sample', self.entry, self.paths, done['metadata'], done['files'])

    def test_malformed_snapshot_objects_and_timestamps_are_held(self):
        for target, value in [(self.remote_path, []), (self.duplicate_path, None)]:
            self.sync(); atomic_json(target, value)
            self.assertFalse(self.build()['records'][0]['qa']['approved'])
        self.sync(); self.remote['retrieved_at'] = 123; atomic_json(self.remote_path, self.remote)
        self.assertFalse(self.build()['records'][0]['qa']['approved'])

    def test_source_backed_artifact_suffix_supported_technical_test_label_held(self):
        self.payload['metadata']['title'] += ' - FGDC XML metadata artifact'
        self.sync(); self.assertTrue(self.build()['records'][0]['qa']['approved'])
        self.payload['metadata']['title'] += ' [SANDBOX TECHNICAL TEST ONLY]'
        self.sync(); self.assertFalse(self.build()['records'][0]['qa']['approved'])

    def test_metadata_access_constraints_cannot_be_overridden_by_a_license_label(self):
        for text, approved in [('Restricted metadata; permission required for access', False),
                               ('No restrictions', True), ('None', True)]:
            self.source.write_bytes(self.raw.replace(b'<metainfo>', ('<metainfo><metac>' + text + '</metac>').encode()))
            self.payload['artifact_policy']['source_sha256'] = hashlib.sha256(self.source.read_bytes()).hexdigest()
            self.sync()
            self.assertEqual(self.build()['records'][0]['qa']['approved'], approved)

    def test_raw_snapshot_freshness_cannot_be_extended_by_outer_expiry(self):
        for target in ('remote', 'duplicate'):
            self.sync()
            old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            if target == 'remote':
                self.remote['retrieved_at'] = old; atomic_json(self.remote_path, self.remote)
            else:
                self.duplicates['evidence'][0]['snapshot']['retrieved_at'] = old
                atomic_json(self.duplicate_path, self.duplicates)
            self.assertFalse(self.build()['records'][0]['qa']['approved'])

    def test_inverse_title_query_and_local_identical_source_alias_are_held(self):
        self.duplicates['evidence'][0]['snapshot']['query'] = 'NOT Metadata catalogue'
        atomic_json(self.duplicate_path, self.duplicates)
        self.assertFalse(self.build()['records'][0]['qa']['approved'])
        self.sync()
        atomic_json(self.paths.uploads_registry_path, {'sample': self.entry,
                    'alias': dict(self.entry, deposition_id=456, zenodo_url='https://zenodo.org/deposit/456')})
        manifest = self.build()
        self.assertFalse(any(record['qa']['approved'] for record in manifest['records']))

    def test_legacy_source_access_constraints_also_hold_even_with_explicit_grant(self):
        self.source.write_bytes(self.raw.replace(b'<useconst>', b'<accconst>Restricted</accconst><useconst>'))
        self.payload.pop('artifact_policy'); self.payload.pop('content_classification')
        self.payload['metadata'].update(license='cc-zero', publication_date='1977-01-01')
        self.file.write_text(json.dumps(self.payload))
        metadata, _, digest = prepare_metadata(str(self.file), self.paths)
        self.entry.update(source_sha256=digest, metadata_sha256=metadata_hash(metadata), artifact_contract=None)
        atomic_json(self.paths.uploads_registry_path, {'sample': self.entry})
        self.assertFalse(self.build()['records'][0]['qa']['approved'])

    def test_bad_source_produces_per_record_hold_without_hiding_supported_record(self):
        sample = copy.deepcopy(self.entry)
        sample_source = self.source
        self.source = Path(self.paths.original_fgdc_dir, 'other.xml')
        self.file = Path(self.paths.zenodo_json_dir, 'other.json')
        self.raw += b'\n'
        self.source.write_bytes(self.raw)
        self.payload['artifact_policy']['source_sha256'] = hashlib.sha256(self.raw).hexdigest()
        self.payload['content_classification']['files'][0]['name'] = 'other.xml'
        self.remote_path = Path(self.tmp.name, 'other-remote.json')
        self.duplicate_path = Path(self.tmp.name, 'other-duplicates.json')
        self.sync()
        other = dict(self.entry, deposition_id=456, zenodo_url='https://zenodo.org/deposit/456')
        self.remote['endpoint'] = 'https://zenodo.org/api/deposit/depositions/456'
        self.remote['body']['id'] = 456
        atomic_json(self.remote_path, self.remote)
        self.duplicates['fgdc_id'] = 'other'; atomic_json(self.duplicate_path, self.duplicates)
        atomic_json(self.paths.uploads_registry_path, {'sample': sample, 'other': other})
        sample_source.write_bytes(b'<malformed>')
        self.inputs['other'] = {'remote_snapshot': str(self.remote_path), 'duplicate_snapshot': str(self.duplicate_path)}
        rows = {row['fgdc_id']: row for row in self.build()['records']}
        self.assertTrue(rows['other']['qa']['approved'], rows['other'].get('hold_reasons'))
        self.assertFalse(rows['sample']['qa']['approved'])
        self.assertTrue(rows['sample']['hold_reasons'])

    def test_shared_remote_identity_blocks_entire_assessment_population(self):
        atomic_json(self.paths.uploads_registry_path, {'sample': self.entry, 'other': dict(self.entry)})
        self.assertFalse(any(row['qa']['approved'] for row in self.build()['records']))


if __name__ == '__main__':
    unittest.main()
