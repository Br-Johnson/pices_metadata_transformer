"""Real finite pairs retain two originals, both policies and their semantic holds."""

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import content_class_targets as classes
from scripts.artifact_contract import fingerprint, prepare_artifact, validate_files
from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, prepare_metadata, read_json

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-04'
SUPPORTED = ('FGDC-2953', 'FGDC-3181')
HELD = ('FGDC-2837', 'FGDC-3065')


def current_profiles():
    older, previous = REPO / 'docs/readiness/2026-10-02', REPO / 'docs/readiness/2026-10-03'
    return {
        'authority_manifest': older / 'rehosting_authority.json',
        'access_interpretation_manifest': older / 'contact_source_interpretation.json',
        'creator_interpretation_manifest': older / 'exxon_citation_interpretation.json',
        'contributor_access_interpretation_manifest': older / 'contributor_source_interpretation.json',
        'collective_creator_interpretation_manifest': previous / 'dfo_staff_citation_interpretation.json',
        'institution_creator_interpretation_manifest': DOCS / 'source_citation_credits_415.json',
        'source_link_interpretation_manifest': previous / 'historical_dataset_linkage_21.json',
        'source_title_interpretation_manifest': DOCS / 'source_display_titles_36.json',
        'source_scope_attestation_manifest': previous / 'source_scope_reconciliation_904.json',
        'dataset_access_interpretation_manifest': DOCS / 'finite_source_resource_access_607.json',
    }


class ContentClassTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='pices-class-source-')
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.reviewed_at = datetime.now(timezone.utc).isoformat()
        source = Path(cls.fixture.name) / 'sources'
        source.mkdir()
        for sid in (*SUPPORTED, *HELD):
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        cls.prepared = Path(cls.fixture.name) / 'prepared'
        cls.report = classify_collection(source, cls.prepared, cls.reviewed_at, **current_profiles())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='pices-class-target-')
        self.addCleanup(self.tmp.cleanup)
        prepared = Path(self.tmp.name) / 'prepared'
        shutil.copytree(self.prepared, prepared)
        self.paths = OutputPaths(str(prepared), 'sandbox')
        self.identities = classes.load_representation()['classes']
        self.supported_id = next(row['record_target_id'] for row in self.identities
                                 if row['source_ids'] == list(SUPPORTED))
        self.held_id = next(row['record_target_id'] for row in self.identities
                            if row['source_ids'] == list(HELD))

    def target(self, identifier=None):
        return classes.prepare_class_target(identifier or self.supported_id, self.paths,
                                            reviewed_at=self.reviewed_at)

    def payload_path(self, sid):
        return Path(self.paths.zenodo_json_dir) / (sid + '.json')

    def test_exact_finite_scope_and_live_authority_pins(self):
        mapping = read_json(classes.MAP_PATH)
        self.assertEqual(len(self.identities), 228)
        self.assertEqual(len({sid for row in self.identities for sid in row['source_ids']}), 456)
        self.assertEqual({row['record_target_id'] for row in self.identities},
                         {row['canonical_content_id'] for row in mapping['groups']})
        for row in self.identities:
            self.assertEqual(row['record_target_id'], 'sha256:' + row['source_sha256'])
            self.assertIsNone(row['canonical_source_id'])
            self.assertIsNone(row['canonical_provider_record_id'])
        for attr in ('REPRESENTATION_PATH', 'MAP_PATH', 'AUTHORITY_PATH'):
            path = Path(self.tmp.name) / (attr + '.json')
            path.write_bytes(getattr(classes, attr).read_bytes() + b' ')
            with self.subTest(evidence=attr), patch.object(classes, attr, path):
                with self.assertRaises(ValueError):
                    self.target()
                with self.assertRaises(ValueError):
                    classes.require_singleton_operation(source_id='unrelated')
            path.unlink()
            with patch.object(classes, attr, path), self.assertRaises(ValueError):
                self.target()

    def test_supported_pair_preserves_both_originals_metadata_and_v1_contracts(self):
        before = {sid: self.payload_path(sid).read_bytes() for sid in SUPPORTED}
        target = self.target()
        self.assertEqual(target, self.target())
        self.assertEqual(target, classes.validate_class_target(target, self.paths))
        self.assertEqual(target['source_semantic_status'], 'supported')
        self.assertEqual(target['source_ids'], list(SUPPORTED))
        self.assertFalse(target['upload_eligible'])
        self.assertEqual(target['production_reconciliation_status'], 'pending')
        self.assertIsNone(target['canonical_source_id'])
        self.assertEqual(target['artifact_contract']['schema_version'], 2)
        self.assertEqual(len(target['artifact_contract']['files']), 2)
        for member in target['members']:
            sid = member['source_id']
            payload = json.loads(before[sid])
            original = Path(self.paths.original_fgdc_dir) / (sid + '.xml')
            self.assertEqual(original.read_bytes(), (REPO / 'FGDC' / original.name).read_bytes())
            self.assertEqual(self.payload_path(sid).read_bytes(), before[sid])
            artifact = prepare_artifact(payload, original)
            self.assertEqual(artifact['schema_version'], 1)
            self.assertEqual(member['artifact_v1_sha256'], artifact['sha256'])
            self.assertEqual(member['payload_sha256'], hashlib.sha256(before[sid]).hexdigest())
            self.assertEqual(target['common_source_metadata_sha256'], fingerprint(payload['metadata']))
            prepared = prepare_metadata(str(self.payload_path(sid)), self.paths)[0]
            self.assertEqual({k: v for k, v in target['metadata'].items() if k != 'notes'},
                             {k: v for k, v in prepared.items() if k != 'notes'})
            old_suffix = ('\n\nDeposited object: original FGDC XML metadata artifact; '
                          'underlying research data are not included. Artifact contract SHA-256: '
                          + artifact['sha256'])
            self.assertTrue(prepared['notes'].endswith(old_suffix))
            self.assertEqual(prepared['notes'][:-len(old_suffix)],
                             target['metadata']['notes'].rsplit('\n\nOriginal XML content class: ', 1)[0])
            self.assertTrue(target['metadata']['notes'].startswith(payload['metadata']['notes']))
            self.assertIn(sid + '.xml', target['metadata']['notes'])
            self.assertNotIn(artifact['sha256'], target['metadata']['notes'])
        self.assertEqual(target['metadata']['access_right'], 'restricted')
        self.assertEqual(target['metadata']['license'], '')
        self.assertEqual(target['metadata']['upload_type'], 'other')

    def test_exact_two_file_inventory_requires_both_names_despite_identical_bytes(self):
        contract = self.target()['artifact_contract']
        files = [{'filename': row['name'], 'filesize': row['size'], 'checksum': 'md5:' + row['md5']}
                 for row in contract['files']]
        self.assertEqual(files[0]['checksum'], files[1]['checksum'])
        self.assertEqual(validate_files(files, contract), set())
        self.assertEqual(validate_files(files[:1], contract, allow_missing=True), {files[1]['filename']})
        for altered in (files[:1], files + [files[0]],
                        [dict(files[0], filename='renamed.xml'), files[1]],
                        [dict(files[0], filesize=0), files[1]],
                        [files[0], dict(files[1], checksum='md5:' + '0' * 32)]):
            with self.subTest(files=altered), self.assertRaises(ValueError):
                validate_files(altered, contract)

    def test_both_member_semantics_and_changed_partner_policy_hold_the_whole_target(self):
        held = self.target(self.held_id)
        self.assertEqual(held['source_semantic_status'], 'held')
        self.assertTrue(all(row['hold_reasons'] for row in held['member_assessments']))
        before = self.target()
        path = self.payload_path(SUPPORTED[1])
        payload = read_json(path)
        payload['artifact_policy']['rights_scope'] = 'unproven-underlying-data'
        atomic_json(path, payload)
        after = self.target()
        self.assertEqual([row['source_semantic_status'] for row in after['member_assessments']],
                         ['supported', 'held'])
        self.assertEqual(after['source_semantic_status'], 'held')
        self.assertNotEqual(after['member_set_sha256'], before['member_set_sha256'])
        with self.assertRaises(ValueError):
            classes.validate_class_target(before, self.paths)

    def test_missing_changed_or_disagreeing_member_cannot_fabricate_a_complete_artifact(self):
        source = Path(self.paths.original_fgdc_dir) / (SUPPORTED[1] + '.xml')
        raw = source.read_bytes()
        source.unlink()
        with self.assertRaises(OSError):
            self.target()
        output = Path(self.tmp.name) / 'missing-member-targets'
        report = classes.build_target_view(self.paths, DOCS / 'residual_evidence15_integrated_source_status.json',
                                           output, reviewed_at=self.reviewed_at, limit=1)
        row = report['class_targets'][0]
        self.assertEqual(row['source_semantic_status'], 'held')
        self.assertIsNone(row['artifact_contract_sha256'])
        self.assertFalse(read_json(output / row['payload_path'])['upload_eligible'])
        source.write_bytes(raw + b' ')
        with self.assertRaises(ValueError):
            self.target()
        source.write_bytes(raw)
        path = self.payload_path(SUPPORTED[1])
        payload = read_json(path)
        payload['metadata']['description'] += ' Invented interpretation.'
        atomic_json(path, payload)
        with self.assertRaisesRegex(ValueError, 'complete member metadata'):
            self.target()

    def test_target_rebuild_rejects_self_rehashed_edits_and_is_outside_upload_inputs(self):
        original = self.target()
        for key, value in (('upload_eligible', True), ('source_ids', [SUPPORTED[0]]),
                           ('canonical_source_id', SUPPORTED[0]), ('member_set_sha256', '0' * 64)):
            altered = copy.deepcopy(original)
            altered[key] = value
            altered['metadata_sha256'] = fingerprint(altered['metadata'])
            with self.subTest(key=key), self.assertRaises(ValueError):
                classes.validate_class_target(altered, self.paths)
        output = Path(self.tmp.name) / 'targets'
        report = classes.build_target_view(self.paths, DOCS / 'residual_evidence15_integrated_source_status.json',
                                           output, reviewed_at=self.reviewed_at, limit=1)
        self.assertEqual(report['summary']['class_targets'], 1)
        self.assertEqual(report['summary']['represented_source_files'], 2)
        self.assertFalse(report['summary']['complete_target_population'])
        self.assertNotIn('singleton_targets', report)
        self.assertEqual(len(list((output / 'originals').glob('*.xml'))), 2)
        self.assertFalse(list(Path(self.paths.zenodo_json_dir).glob('XMLCLASS-*.json')))
        with self.assertRaises(ValueError):
            classes.build_target_view(self.paths, DOCS / 'residual_evidence15_integrated_source_status.json',
                                      output, reviewed_at=self.reviewed_at, limit=1)
        with self.assertRaises(ValueError):
            classes.build_target_view(self.paths, DOCS / 'residual_evidence15_integrated_source_status.json',
                                      Path(self.paths.zenodo_json_dir) / 'classes',
                                      reviewed_at=self.reviewed_at, limit=1)


if __name__ == '__main__':
    unittest.main()
