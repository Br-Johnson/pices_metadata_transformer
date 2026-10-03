"""Finite dataset-acquisition evidence preserves metadata rights and held cohorts."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.dataset_access_interpretation import validate_dataset_access_interpretation

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-03'
MANIFEST = DOCS / 'finite_source_resource_access_264.json'


class ExplicitDatasetAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_bytes())
        self.reference = {'manifest_path': str(MANIFEST),
                          'manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
        self.member = next(m for m in self.manifest['members'] if m['source_id'] == 'FGDC-1094')
        self.root = ET.parse(REPO / 'FGDC/FGDC-1094.xml').getroot()
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def validate(self, root=None, reference=None, member=None):
        member = self.member if member is None else member
        return validate_dataset_access_interpretation(self.reference if reference is None else reference,
            member['source_id'], member['source_sha256'], self.root if root is None else root)

    def test_all_exact_bindings_preserve_legacy_cohort_and_grant_no_authority(self):
        old = json.loads((REPO / 'docs/readiness/2026-10-02/registration_access_interpretation.json').read_bytes())
        self.assertEqual(self.manifest['members'][:122], old['members'])
        self.assertEqual(self.manifest['source_contexts'], old['source_contexts'])
        self.assertEqual(len(self.manifest['members']), 264)
        self.assertEqual(len(self.manifest['acquisition_contexts']), 142)
        queue = json.loads((DOCS / 'remaining_source_credit_candidates_86.json').read_bytes())
        joint = json.loads((DOCS / 'joint_collection_source_decisions.json').read_bytes())
        protected = {m['source_id'] for m in queue['members']} | {
            m['source_id'] for g in joint['remaining_meaning_decisions'] for m in g['members']}
        self.assertFalse(protected & self.manifest['acquisition_contexts'].keys())
        for member in self.manifest['members']:
            root = ET.parse(REPO / 'FGDC' / (member['source_id'] + '.xml')).getroot()
            result = self.validate(member=member, root=root)
            expected_meaning = self.manifest['acquisition_contexts'].get(member['source_id'], {}).get('meaning', 'underlying_dataset_acquisition')
            self.assertEqual(result['meaning'], expected_meaning)
            self.assertFalse(result['grants_rehosting'])
            self.assertFalse(result['grants_new_license'])
            self.assertFalse(result['publication_approved'])

    def test_exact_context_constraints_membership_and_manifest_cannot_be_expanded(self):
        for xpath in tuple(self.manifest['acquisition_contexts']['FGDC-1094']['constraints']) + (
                './idinfo/citation/citeinfo/title', './idinfo/descript/abstract', './idinfo/descript/purpose'):
            for mutation in ('text', 'mixed', 'attribute', 'repeated', 'missing'):
                root = copy.deepcopy(self.root)
                node = root.find(xpath)
                parent = root.find(xpath.rsplit('/', 1)[0])
                if mutation == 'text':
                    node.text = 'Different scope or source context'
                elif mutation == 'mixed':
                    ET.SubElement(node, 'b').text = 'extra'
                elif mutation == 'attribute':
                    node.set('scope', 'different')
                elif mutation == 'repeated':
                    parent.append(copy.deepcopy(node))
                else:
                    parent.remove(node)
                with self.subTest(xpath=xpath, mutation=mutation), self.assertRaises(ValueError):
                    self.validate(root=root)
        for name in ('metsi', 'metextns'):
            root = copy.deepcopy(self.root)
            ET.SubElement(root.find('./metainfo'), name)
            with self.assertRaises(ValueError):
                self.validate(root=root)
        for key in ('source_id', 'source_sha256'):
            with self.assertRaises(ValueError):
                self.validate(member={**self.member, key: 'unsupported'})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'changed.json'
            for key, value in (('members', []), ('meaning', 'unrestricted_metadata'), ('grants_new_license', True)):
                path.write_text(json.dumps({**self.manifest, key: value}))
                ref = {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.validate(reference=ref)

    def prepared(self, tmp, enabled=True, authority=True, ids=('FGDC-1094',)):
        from scripts.collection_qa import classify_collection
        from scripts.path_config import OutputPaths
        old_docs = REPO / 'docs/readiness/2026-10-02'
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        for sid in ids:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        output = Path(tmp) / 'output'
        report = classify_collection(source, output, self.reviewed_at,
            authority_manifest=old_docs / 'rehosting_authority.json' if authority else None,
            dataset_access_interpretation_manifest=MANIFEST if enabled else old_docs / 'registration_access_interpretation.json',
            institution_creator_interpretation_manifest=DOCS / 'access_held_source_citations_396.json')
        return report, OutputPaths(str(output), 'sandbox')

    def test_opt_in_withdrawal_preserves_complete_metadata_and_protected_holds(self):
        from scripts.agent_qa import assess_source
        ids = tuple(self.manifest['acquisition_contexts']) + ('FGDC-3682', 'FGDC-2557', 'FGDC-2603',
                'FGDC-2691', 'FGDC-2694', 'FGDC-2695', 'FGDC-545', 'FGDC-696', 'FGDC-10')
        with tempfile.TemporaryDirectory() as tmp:
            baseline, paths = self.prepared(tmp, enabled=False, ids=ids)
            old = {sid: json.loads((Path(paths.zenodo_json_dir) / (sid + '.json')).read_bytes()) for sid in ids}
            after, paths = self.prepared(tmp, ids=ids)
            before_rows = {r['source_id']: r for r in baseline['records']}
            for row in after['records']:
                sid = row['source_id']
                path = Path(paths.zenodo_json_dir) / (sid + '.json')
                payload = json.loads(path.read_bytes())
                self.assertEqual(payload['metadata'], old[sid]['metadata'])
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(),
                                 (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
                if sid in self.manifest['acquisition_contexts']:
                    self.assertEqual(row['source_status'], 'supported')
                    self.assertEqual(row['dataset_access_interpretation'], 'SOURCE_BACKED')
                    assess_source(str(path), paths)
                else:
                    self.assertEqual(row['source_status'], before_rows[sid]['source_status'])
                    self.assertEqual(row['hold_reasons'], before_rows[sid]['hold_reasons'])
            withdrawn, _ = self.prepared(tmp, enabled=False, ids=ids)
            self.assertEqual(withdrawn['summary'], baseline['summary'])
            for row in withdrawn['records']:
                self.assertEqual(row['source_status'], before_rows[row['source_id']]['source_status'])

    def test_separate_authority_and_rights_stay_mandatory_in_shared_gate(self):
        from scripts.agent_qa import assess_source
        from scripts.dataset_access_interpretation import validate_dataset_access_policy
        with tempfile.TemporaryDirectory() as tmp:
            report, paths = self.prepared(tmp, authority=False)
            self.assertEqual(report['records'][0]['source_status'], 'held')
            report, paths = self.prepared(tmp)
            self.assertEqual(report['records'][0]['source_status'], 'supported')
            path = Path(paths.zenodo_json_dir) / 'FGDC-1094.json'
            original = json.loads(path.read_bytes())
            for mutation in ('conflict', 'missing_authority', 'policy_license', 'metadata_license', 'open_access', 'reference'):
                payload = copy.deepcopy(original)
                policy = payload['artifact_policy']
                if mutation == 'conflict':
                    policy['source_access_interpretation'] = self.reference
                elif mutation == 'missing_authority':
                    del policy['rehosting_authority']
                elif mutation == 'policy_license':
                    policy['license'] = 'cc-by-4.0'
                elif mutation == 'metadata_license':
                    payload['metadata']['license'] = 'cc-by-4.0'
                elif mutation == 'open_access':
                    payload['metadata']['access_right'] = 'open'
                else:
                    policy['dataset_access_interpretation']['manifest_sha256'] = '0' * 64
                path.write_text(json.dumps(payload))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    assess_source(str(path), paths)
                with self.subTest(shared=mutation), self.assertRaises(ValueError):
                    validate_dataset_access_policy(policy, 'FGDC-1094', self.member['source_sha256'], self.root, payload['metadata'])

    def test_both_human_schemas_recheck_external_profile_bytes(self):
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval
        from scripts.upload_service import metadata_hash, prepare_metadata
        for schema in (1, 2):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as tmp:
                _, paths = self.prepared(tmp)
                path = Path(paths.zenodo_json_dir) / 'FGDC-1094.json'
                evidence = Path(tmp) / 'access-evidence.json'
                shutil.copyfile(MANIFEST, evidence)
                payload = json.loads(path.read_bytes())
                payload['artifact_policy']['dataset_access_interpretation']['manifest_path'] = str(evidence)
                path.write_text(json.dumps(payload))
                metadata, source, digest = prepare_metadata(str(path), paths)
                artifact = prepare_artifact(payload, source)
                entry = {'environment': 'sandbox', 'deposition_id': 123, 'json_file': str(path),
                         'source_sha256': digest, 'metadata_sha256': metadata_hash(metadata),
                         'artifact_contract': artifact, 'zenodo_url': 'https://sandbox.zenodo.org/deposit/123'}
                record = {'fgdc_id': 'FGDC-1094', 'deposition_id': 123, 'source_sha256': digest,
                          'metadata_sha256': metadata_hash(metadata), 'artifact_contract': artifact,
                          'qa': {'approved': True, 'reviewer_type': 'human', 'reviewer': 'Offline fixture',
                                 'reviewed_at': self.reviewed_at, 'rationale': 'Fixture only',
                                 'checks': dict.fromkeys(QA_CHECKS, True), 'run_id': 'fixture',
                                 'review_revision': 'fixture', 'evidence': ['Fixture only']},
                          'duplicate_review': {'status': 'reviewed', 'classification': 'checked_no_match',
                                               'rationale': 'Fixture only', 'evidence': ['Fixture only']}}
                manifest = {'schema_version': schema, 'source_revision': 'fixture', 'environment': 'sandbox', 'records': [record]}
                validate_approval(manifest, 'FGDC-1094', entry, paths)
                evidence.write_bytes(evidence.read_bytes() + b'\n')
                with self.assertRaises(ValueError):
                    validate_approval(manifest, 'FGDC-1094', entry, paths)
