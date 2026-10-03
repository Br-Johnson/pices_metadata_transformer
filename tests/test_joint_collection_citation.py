"""Exact joint-citation corrections preserve source terms and independent holds."""
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
PREVIOUS = REPO / 'docs/readiness/2026-10-03/institution_program_citation_99.json'
MANIFEST = REPO / 'docs/readiness/2026-10-03/joint_collection_citation_190.json'


class JointCollectionCitationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(MANIFEST)
        self.cohorts = self.manifest['cohorts'][11:]
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

    def test_full_190_binding_preserves_prior_99_and_exact_reviewed_after_images(self):
        self.assertEqual(self.manifest['cohorts'][:11], read_json(PREVIOUS)['cohorts'])
        self.assertEqual([len(c['members']) for c in self.cohorts], [37, 31, 23])
        self.assertEqual(self.cohorts[0]['creators'],
            [{'name': 'Ecotrust'}, {'name': 'Pacific GIS'}, {'name': 'Conservation International'}])
        self.assertEqual(self.cohorts[1]['creators'],
            [{'name': 'USDA Forest Service', 'type': 'Organization'},
             {'name': 'Alaska Department of Natural Resources, Division of Support Services-Land Records Information Section',
              'type': 'Organization'}])
        self.assertEqual(self.cohorts[2]['creators'], [{'name': 'Unaami Arctic Data Collection'}])
        self.assertEqual(len({m['source_id'] for c in self.manifest['cohorts'] for m in c['members']}), 190)
        for cohort in self.manifest['cohorts']:
            for member in cohort['members']:
                raw = (REPO / 'FGDC' / (member['source_id'] + '.xml')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
                self.assertEqual(validate_creator_interpretation(self.reference, member['source_id'],
                    member['source_sha256'], ET.fromstring(raw)), cohort['creators'])

    def test_rehashed_membership_scope_and_full_creator_forgery_fail_closed(self):
        member = self.cohorts[0]['members'][0]
        root = ET.parse(REPO / 'FGDC' / (member['source_id'] + '.xml')).getroot()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'forged.json'
            for fault in ('member', 'name', 'type', 'affiliation', 'identifier', 'order', 'prior', 'scope'):
                candidate = copy.deepcopy(self.manifest)
                cohort = candidate['cohorts'][11]
                if fault == 'member':
                    cohort['members'][0]['source_sha256'] = '0' * 64
                elif fault in ('name', 'type', 'affiliation'):
                    cohort['creators'][0][fault] = 'Inferred'
                elif fault == 'identifier':
                    cohort['creators'][0]['orcid'] = 'inferred'
                elif fault == 'order':
                    cohort['creators'].reverse()
                elif fault == 'prior':
                    candidate['cohorts'][0]['creators'][0]['name'] = 'Changed prior credit'
                else:
                    candidate['scope'] = 'xml_authorship'
                p.write_text(json.dumps(candidate))
                reference = {'manifest_path': str(p), 'manifest_sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                with self.subTest(fault=fault), self.assertRaises(ValueError):
                    validate_creator_interpretation(reference, member['source_id'], member['source_sha256'], root)
        with self.assertRaises(ValueError):
            validate_creator_interpretation(self.reference, 'not-a-member', member['source_sha256'], root)

    def test_91_actual_source_decisions_change_only_68_creator_lists_and_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, PREVIOUS)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 91, 'failed': 0})
            payloads = {m['source_id']: read_json(Path(paths.zenodo_json_dir) / (m['source_id'] + '.json'))
                        for m in self.members}
            after, paths = self.prepared(tmp)
            self.assertEqual(after['summary']['source_status_counts'], {'supported': 1, 'held': 90, 'failed': 0})
            self.assertEqual([r['source_id'] for r in after['records'] if r['source_status'] == 'supported'], ['FGDC-619'])
            held = [r for r in after['records'] if r['source_status'] == 'held']
            self.assertTrue(all(any('access' in reason.casefold() for reason in r['hold_reasons']) for r in held))
            self.assertTrue(all(not any('Creator semantics' in reason for reason in r['hold_reasons']) for r in held))
            creator_changes = 0
            for cohort in self.cohorts:
                for member in cohort['members']:
                    sid = member['source_id']
                    payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                    expected = copy.deepcopy(payloads[sid])
                    changed_creators = expected['metadata']['creators'] != cohort['creators']
                    creator_changes += changed_creators
                    if changed_creators:
                        lines = [line for line in expected['metadata']['notes'].splitlines()
                                 if line.startswith('Curator decision: ')]
                        self.assertEqual(len(lines), 1)
                        decision = json.loads(lines[0].removeprefix('Curator decision: '))
                        self.assertEqual(decision['metadata']['creators'], expected['metadata']['creators'])
                        decision['metadata']['creators'] = cohort['creators']
                        expected['metadata']['notes'] = expected['metadata']['notes'].replace(
                            lines[0], 'Curator decision: ' + json.dumps(decision, sort_keys=True))
                        caveat = '\nSource dataset citation originators are preserved for attribution; '
                        self.assertEqual(expected['metadata']['notes'].count(caveat), 1)
                        expected['metadata']['notes'] = expected['metadata']['notes'].replace(
                            caveat, '\nOriginal primary citation origin: ' + cohort['raw_origin'] + caveat)
                    expected['metadata']['creators'] = cohort['creators']
                    expected['artifact_policy']['creator_interpretation'] = self.reference
                    self.assertEqual(payload, expected)
                    self.assertEqual(payload['metadata']['access_right'], 'restricted')
                    self.assertEqual(payload['metadata']['license'], '')
                    self.assertIn(cohort['raw_origin'], payload['metadata']['notes'])
                    self.assertIn('XML authorship is not independently established', payload['metadata']['notes'])
                    self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(),
                                     (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            self.assertEqual(creator_changes, 68)
            self.assertEqual(after['summary']['remote_verified'], 0)
            self.assertEqual(after['summary']['publication_approved'], 0)

    def test_unchanged_resume_and_missing_withdrawn_evidence_restore_original_creators(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, PREVIOUS)
            originals = {m['source_id']: read_json(Path(paths.zenodo_json_dir) / (m['source_id'] + '.json'))['metadata']
                         for m in self.members}
            after, paths = self.prepared(tmp)
            self.assertEqual(after, self.prepared(tmp)[0])
            p = Path(paths.zenodo_json_dir) / 'FGDC-619.json'
            payload = read_json(p)
            payload['metadata']['creators'][0]['affiliation'] = 'Inferred'
            atomic_json(p, payload)
            self.assertEqual(after, self.prepared(tmp)[0])
            for evidence in (PREVIOUS, Path(tmp) / 'missing.json', None):
                report, paths = self.prepared(tmp, evidence)
                self.assertEqual(report['summary']['source_status_counts'], before['summary']['source_status_counts'])
                for sid, metadata in originals.items():
                    self.assertEqual(read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))['metadata'], metadata)

    def test_agent_and_human_schemas_reject_unreviewed_creator_or_access_changes(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import prepare_manifest, validate_approval, QA_CHECKS
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, ids=['FGDC-619'])
            p = Path(paths.zenodo_json_dir) / 'FGDC-619.json'
            payload = read_json(p)
            assess_source(str(p), paths)
            metadata, source, digest = prepare_metadata(str(p), paths)
            entry = {'environment': 'sandbox', 'zenodo_url': 'https://sandbox.zenodo.org/deposit/123',
                     'deposition_id': 123, 'upload_status': 'success', 'publish_status': 'draft', 'success': True,
                     'json_file': str(p), 'source_sha256': digest, 'metadata_sha256': metadata_hash(metadata),
                     'artifact_contract': prepare_artifact(payload, source)}
            atomic_json(paths.uploads_registry_path, {'FGDC-619': entry})
            manifest = prepare_manifest(paths)
            record = manifest['records'][0]
            record['qa'].update(approved=True, reviewer_type='human', reviewer='Offline fixture, not release authority',
                reviewed_at=self.reviewed_at, rationale='Dummy test fixture', checks=dict.fromkeys(QA_CHECKS, True),
                run_id='fixture', review_revision=manifest['source_revision'], evidence=['fixture'])
            record['duplicate_review'].update(status='reviewed', classification='checked_no_match',
                                             rationale='fixture only', evidence=['fixture'])
            for schema in (1, 2):
                manifest['schema_version'] = schema
                self.assertTrue(validate_approval(manifest, 'FGDC-619', entry, paths, metadata)['qa']['approved'])
                for fault in ('type', 'affiliation', 'name', 'identifier', 'order', 'withdraw', 'license', 'date'):
                    changed = copy.deepcopy(payload)
                    if fault in ('type', 'affiliation', 'name'):
                        changed['metadata']['creators'][0][fault] = 'Inferred'
                    elif fault == 'identifier':
                        changed['metadata']['creators'][0]['orcid'] = 'inferred'
                    elif fault == 'order':
                        changed['metadata']['creators'].reverse()
                    elif fault == 'withdraw':
                        changed['artifact_policy'].pop('creator_interpretation')
                    elif fault == 'license':
                        changed['metadata']['license'] = 'cc-by-4.0'
                    else:
                        changed['metadata']['publication_date'] = '2000-01-01'
                    atomic_json(p, changed)
                    with self.subTest(schema=schema, fault=fault), self.assertRaises(ValueError):
                        assess_source(str(p), paths)
                    with self.subTest(schema=schema, fault=fault), self.assertRaises(ValueError):
                        validate_approval(manifest, 'FGDC-619', entry, paths, metadata)
                    atomic_json(p, payload)


if __name__ == '__main__':
    unittest.main()
