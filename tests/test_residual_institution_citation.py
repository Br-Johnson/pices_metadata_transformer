"""The reviewed 27-source extension preserves attribution and independent holds."""
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
PREVIOUS = REPO / 'docs/readiness/2026-10-03/institution_citation_interpretation.json'
MANIFEST = REPO / 'docs/readiness/2026-10-03/institution_program_citation_99.json'


class ResidualInstitutionCitationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(MANIFEST)
        self.cohorts = self.manifest['cohorts'][4:]
        self.members = [member for cohort in self.cohorts for member in cohort['members']]
        self.reference = {'manifest_path': str(MANIFEST),
                          'manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def prepared(self, tmp, manifest=MANIFEST, source_ids=None):
        from scripts.collection_qa import classify_collection
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        for sid in source_ids or [member['source_id'] for member in self.members]:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        report = classify_collection(source, Path(tmp) / 'output', self.reviewed_at,
            authority_manifest=DOCS / 'rehosting_authority.json',
            access_interpretation_manifest=DOCS / 'contact_source_interpretation.json',
            creator_interpretation_manifest=DOCS / 'exxon_citation_interpretation.json',
            dataset_access_interpretation_manifest=DOCS / 'registration_access_interpretation.json',
            contributor_access_interpretation_manifest=DOCS / 'contributor_source_interpretation.json',
            collective_creator_interpretation_manifest=REPO / 'docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json',
            institution_creator_interpretation_manifest=manifest)
        return report, OutputPaths(str(Path(tmp) / 'output'), 'sandbox')

    def test_combined_99_preserves_72_and_validates_all_exact_source_objects(self):
        self.assertEqual(self.manifest['cohorts'][:4], read_json(PREVIOUS)['cohorts'])
        self.assertEqual([len(c['members']) for c in self.cohorts], [9, 4, 3, 4, 3, 2, 2])
        members = [m for c in self.manifest['cohorts'] for m in c['members']]
        self.assertEqual(len({m['source_id'] for m in members}), 99)
        for cohort in self.manifest['cohorts']:
            for member in cohort['members']:
                raw = (REPO / 'FGDC' / (member['source_id'] + '.xml')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
                self.assertEqual(validate_creator_interpretation(self.reference, member['source_id'],
                    member['source_sha256'], ET.fromstring(raw)), cohort['creators'])

    def test_extension_does_not_trust_rehashed_content_or_same_name_nonmember(self):
        cohort = self.cohorts[0]
        member = cohort['members'][0]
        root = ET.parse(REPO / 'FGDC' / (member['source_id'] + '.xml')).getroot()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'forged.json'
            for fault in ('member', 'name', 'type', 'affiliation', 'identifier', 'prior', 'scope'):
                manifest = copy.deepcopy(self.manifest)
                c = manifest['cohorts'][4]
                if fault == 'member':
                    c['members'][0]['source_sha256'] = '0' * 64
                elif fault in ('name', 'type', 'affiliation'):
                    c['creators'][0][fault] = 'Inferred'
                elif fault == 'identifier':
                    c['creators'][0]['orcid'] = 'inferred'
                elif fault == 'prior':
                    manifest['cohorts'][0]['creators'][0]['name'] = 'Changed older cohort'
                else:
                    manifest['scope'] = 'xml_authorship'
                p.write_text(json.dumps(manifest))
                ref = {'manifest_path': str(p), 'manifest_sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                with self.subTest(fault=fault), self.assertRaises(ValueError):
                    validate_creator_interpretation(ref, member['source_id'], member['source_sha256'], root)
        with self.assertRaises(ValueError):
            validate_creator_interpretation(self.reference, 'not-in-reviewed-cohort', member['source_sha256'], root)

    def test_all_27_retain_full_metadata_rights_dates_and_eleven_access_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, PREVIOUS)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 27, 'failed': 0})
            original = {member['source_id']: read_json(Path(paths.zenodo_json_dir) /
                        (member['source_id'] + '.json')) for member in self.members}
            after, paths = self.prepared(tmp)
            held = {row['source_id']: row['hold_reasons'] for row in after['records'] if row['source_status'] == 'held'}
            self.assertEqual(set(held), {'FGDC-220', 'FGDC-257', 'FGDC-258', 'FGDC-259', 'FGDC-260',
                                       'FGDC-228', 'FGDC-231', 'FGDC-232', 'FGDC-378', 'FGDC-500', 'FGDC-504'})
            self.assertTrue(all(any('access' in reason.casefold() for reason in reasons) for reasons in held.values()))
            for sid, before_payload in original.items():
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                self.assertEqual(payload['metadata'], before_payload['metadata'])
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertIn('XML authorship is not independently established', payload['metadata']['notes'])
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(),
                                 (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
                expected = copy.deepcopy(before_payload)
                expected['artifact_policy']['creator_interpretation'] = self.reference
                self.assertEqual(payload, expected)
            self.assertEqual(after['summary']['remote_verified'], 0)
            self.assertEqual(after['summary']['publication_approved'], 0)

    def test_resume_withdrawal_and_payload_mutation_rederive_conservative_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, paths = self.prepared(tmp)
            self.assertEqual(first, self.prepared(tmp)[0])
            p = Path(paths.zenodo_json_dir) / 'FGDC-3926.json'
            payload = read_json(p)
            self.assertNotIn('type', payload['metadata']['creators'][0])
            payload['metadata']['creators'][0]['type'] = 'Organization'
            atomic_json(p, payload)
            self.assertEqual(first, self.prepared(tmp)[0])
            self.assertEqual(self.prepared(tmp, PREVIOUS)[0]['summary']['source_status_counts']['held'], 27)
            self.assertEqual(self.prepared(tmp, Path(tmp) / 'missing.json')[0]['summary']['source_status_counts']['held'], 27)

    def test_agent_and_both_human_schemas_reject_unbound_full_object_changes(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import prepare_manifest, validate_approval, QA_CHECKS
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, source_ids=['FGDC-3926'])
            p = Path(paths.zenodo_json_dir) / 'FGDC-3926.json'
            payload = read_json(p)
            assess_source(str(p), paths)
            metadata, source, source_digest = prepare_metadata(str(p), paths)
            entry = {'environment': 'sandbox', 'zenodo_url': 'https://sandbox.zenodo.org/deposit/123',
                     'deposition_id': 123, 'upload_status': 'success', 'publish_status': 'draft', 'success': True,
                     'json_file': str(p), 'source_sha256': source_digest, 'metadata_sha256': metadata_hash(metadata),
                     'artifact_contract': prepare_artifact(payload, source)}
            atomic_json(paths.uploads_registry_path, {'FGDC-3926': entry})
            manifest = prepare_manifest(paths)
            record = manifest['records'][0]
            record['qa'].update(approved=True, reviewer_type='human', reviewer='Offline contract fixture only',
                reviewed_at=self.reviewed_at, rationale='Dummy fixture, not actual release approval',
                checks=dict.fromkeys(QA_CHECKS, True), run_id='fixture',
                review_revision=manifest['source_revision'], evidence=['fixture'])
            record['duplicate_review'].update(status='reviewed', classification='checked_no_match',
                                             rationale='fixture', evidence=['fixture'])
            for schema in (1, 2):
                manifest['schema_version'] = schema
                self.assertTrue(validate_approval(manifest, 'FGDC-3926', entry, paths, metadata)['qa']['approved'])
                for fault in ('type', 'affiliation', 'name', 'withdraw', 'license', 'date'):
                    changed = copy.deepcopy(payload)
                    if fault in ('type', 'affiliation', 'name'):
                        changed['metadata']['creators'][0][fault] = 'Inferred'
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
                        validate_approval(manifest, 'FGDC-3926', entry, paths, metadata)
                    atomic_json(p, payload)


if __name__ == '__main__':
    unittest.main()
