"""Exact full-object citation support excludes same-name siblings and other holds."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.citation_creator_interpretation import validate_creator_interpretation
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, metadata_hash, prepare_metadata, read_json

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-02'
PREVIOUS = REPO / 'docs/readiness/2026-10-03/joint_collection_citation_190.json'
MANIFEST = REPO / 'docs/readiness/2026-10-03/literal_citation_extension_229.json'
EVIDENCE = REPO / 'docs/readiness/2026-10-03/residual_source_candidates.json'
SIBLINGS = ['FGDC-121', 'FGDC-1767', 'FGDC-336', 'FGDC-533', 'FGDC-535']


class LiteralCitationExtensionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(MANIFEST)
        self.cohorts = self.manifest['cohorts'][14:]
        self.members = [m for c in self.cohorts for m in c['members']]
        self.reference = {'manifest_path': str(MANIFEST),
                          'manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def prepared(self, tmp, manifest=MANIFEST, ids=None):
        from scripts.collection_qa import classify_collection
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        for sid in ids or [m['source_id'] for m in self.members]:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        output = Path(tmp) / 'output'
        report = classify_collection(source, output, self.reviewed_at,
            authority_manifest=DOCS / 'rehosting_authority.json',
            access_interpretation_manifest=DOCS / 'contact_source_interpretation.json',
            creator_interpretation_manifest=DOCS / 'exxon_citation_interpretation.json',
            dataset_access_interpretation_manifest=DOCS / 'registration_access_interpretation.json',
            contributor_access_interpretation_manifest=DOCS / 'contributor_source_interpretation.json',
            collective_creator_interpretation_manifest=REPO / 'docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json',
            institution_creator_interpretation_manifest=manifest)
        return report, OutputPaths(str(output), 'sandbox')

    def test_exact_229_preserves_prior_190_and_all_39_complete_after_images(self):
        self.assertEqual(self.manifest['cohorts'][:14], read_json(PREVIOUS)['cohorts'])
        self.assertEqual(self.manifest['prior_manifest_sha256'], hashlib.sha256(PREVIOUS.read_bytes()).hexdigest())
        self.assertEqual(self.manifest['decision_evidence_sha256'], hashlib.sha256(EVIDENCE.read_bytes()).hexdigest())
        self.assertEqual(self.manifest['ancestral_prior_manifest_sha256'], read_json(PREVIOUS)['prior_manifest_sha256'])
        self.assertEqual(self.manifest['ancestral_decision_evidence_sha256'], read_json(PREVIOUS)['decision_evidence_sha256'])
        evidence = [e for g in read_json(EVIDENCE)['recommended_literal_batches'] for e in g['source_evidence']]
        expected = {e['source_id']: e for e in evidence}
        self.assertEqual({m['source_id'] for m in self.members}, set(expected))
        self.assertEqual(len(self.members), 39)
        self.assertTrue(set(expected).isdisjoint(SIBLINGS))
        self.assertEqual(sum(c['creators'][0].get('type') == 'Organization' for c in self.cohorts), 15)
        self.assertEqual(sum('type' not in c['creators'][0] for c in self.cohorts), 24)
        self.assertEqual(len({m['source_id'] for c in self.manifest['cohorts'] for m in c['members']}), 229)
        for cohort in self.manifest['cohorts']:
            for member in cohort['members']:
                raw = (REPO / 'FGDC' / (member['source_id'] + '.xml')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
                self.assertEqual(validate_creator_interpretation(self.reference, member['source_id'],
                    member['source_sha256'], ET.fromstring(raw)), cohort['creators'])
                if member['source_id'] in expected:
                    item = expected[member['source_id']]
                    self.assertEqual(cohort['raw_origin'], item['raw_primary_origins'][0])
                    self.assertEqual(cohort['creators'], item['existing_full_creators'])

    def test_rehashed_membership_or_object_changes_and_same_origin_siblings_fail_closed(self):
        first = self.members[0]
        root = ET.parse(REPO / 'FGDC' / (first['source_id'] + '.xml')).getroot()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'forged.json'
            for fault in ('hash', 'sibling', 'name', 'type', 'affiliation', 'identifier', 'prior', 'scope'):
                changed = copy.deepcopy(self.manifest)
                cohort = changed['cohorts'][14]
                if fault == 'hash':
                    cohort['members'][0]['source_sha256'] = '0' * 64
                elif fault == 'sibling':
                    cohort['members'][0]['source_id'] = SIBLINGS[0]
                elif fault in ('name', 'type', 'affiliation'):
                    cohort['creators'][0][fault] = 'Inferred'
                elif fault == 'identifier':
                    cohort['creators'][0]['orcid'] = 'inferred'
                elif fault == 'prior':
                    changed['cohorts'][0]['creators'][0]['name'] = 'Changed prior'
                else:
                    changed['scope'] = 'xml_authorship'
                path.write_text(json.dumps(changed))
                ref = {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.subTest(fault=fault), self.assertRaises(ValueError):
                    validate_creator_interpretation(ref, first['source_id'], first['source_sha256'], root)
        for sid in SIBLINGS:
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                validate_creator_interpretation(self.reference, sid, hashlib.sha256(raw).hexdigest(), ET.fromstring(raw))

    def test_actual_39_decisions_preserve_complete_metadata_and_five_sibling_holds(self):
        ids = [m['source_id'] for m in self.members] + SIBLINGS
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, PREVIOUS, ids)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 44, 'failed': 0})
            old = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json')) for sid in ids}
            after, paths = self.prepared(tmp, ids=ids)
            self.assertEqual(after['summary']['source_status_counts'], {'supported': 39, 'held': 5, 'failed': 0})
            self.assertEqual({r['source_id'] for r in after['records'] if r['source_status'] == 'held'}, set(SIBLINGS))
            for sid in ids:
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                expected = copy.deepcopy(old[sid])
                if sid not in SIBLINGS:
                    expected['artifact_policy']['creator_interpretation'] = self.reference
                self.assertEqual(payload, expected)
                self.assertEqual(payload['metadata'], old[sid]['metadata'])
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertIn('XML authorship is not independently established', payload['metadata']['notes'])
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(),
                                 (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            self.assertEqual(after['summary']['remote_verified'], 0)
            self.assertEqual(after['summary']['publication_approved'], 0)

    def test_unchanged_resume_and_withdrawal_retain_metadata_and_restore_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, paths = self.prepared(tmp)
            self.assertEqual(first, self.prepared(tmp)[0])
            path = Path(paths.zenodo_json_dir) / 'FGDC-129.json'
            original = read_json(path)
            changed = copy.deepcopy(original)
            changed['metadata']['creators'][0]['type'] = 'Organization'
            atomic_json(path, changed)
            self.assertEqual(first, self.prepared(tmp)[0])
            self.assertEqual(read_json(path), original)
            for evidence in (PREVIOUS, Path(tmp) / 'missing.json', None):
                report, paths = self.prepared(tmp, evidence)
                self.assertEqual(report['summary']['source_status_counts'], {'supported': 0, 'held': 39, 'failed': 0})
                self.assertEqual(read_json(path)['metadata'], original['metadata'])

    def test_agent_and_both_human_schemas_reject_unbound_object_rights_or_date_changes(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import prepare_manifest, validate_approval, QA_CHECKS
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, ids=['FGDC-129'])
            path = Path(paths.zenodo_json_dir) / 'FGDC-129.json'
            payload = read_json(path)
            assess_source(str(path), paths)
            metadata, source, source_sha = prepare_metadata(str(path), paths)
            entry = {'environment': 'sandbox', 'zenodo_url': 'https://sandbox.zenodo.org/deposit/123',
                     'deposition_id': 123, 'upload_status': 'success', 'publish_status': 'draft', 'success': True,
                     'json_file': str(path), 'source_sha256': source_sha, 'metadata_sha256': metadata_hash(metadata),
                     'artifact_contract': prepare_artifact(payload, source)}
            atomic_json(paths.uploads_registry_path, {'FGDC-129': entry})
            manifest = prepare_manifest(paths)
            record = manifest['records'][0]
            record['qa'].update(approved=True, reviewer_type='human', reviewer='Offline fixture only',
                reviewed_at=self.reviewed_at, rationale='Dummy test fixture, not release authority',
                checks=dict.fromkeys(QA_CHECKS, True), run_id='fixture',
                review_revision=manifest['source_revision'], evidence=['fixture'])
            record['duplicate_review'].update(status='reviewed', classification='checked_no_match',
                                             rationale='fixture only', evidence=['fixture'])
            for schema in (1, 2):
                manifest['schema_version'] = schema
                self.assertTrue(validate_approval(manifest, 'FGDC-129', entry, paths, metadata)['qa']['approved'])
                for fault in ('type', 'affiliation', 'name', 'identifier', 'withdraw', 'license', 'date'):
                    changed = copy.deepcopy(payload)
                    if fault in ('type', 'affiliation', 'name'):
                        changed['metadata']['creators'][0][fault] = 'Inferred'
                    elif fault == 'identifier':
                        changed['metadata']['creators'][0]['orcid'] = 'inferred'
                    elif fault == 'withdraw':
                        changed['artifact_policy'].pop('creator_interpretation')
                    elif fault == 'license':
                        changed['metadata']['license'] = 'cc-by-4.0'
                    else:
                        changed['metadata']['publication_date'] = '2000-01-01'
                    atomic_json(path, changed)
                    with self.subTest(schema=schema, fault=fault), self.assertRaises(ValueError):
                        assess_source(str(path), paths)
                    with self.subTest(schema=schema, fault=fault), self.assertRaises(ValueError):
                        validate_approval(manifest, 'FGDC-129', entry, paths, metadata)
                    atomic_json(path, payload)


if __name__ == '__main__':
    unittest.main()
