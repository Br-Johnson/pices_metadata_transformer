"""Registration access interpretation stays source-bound and rights-neutral."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.dataset_access_interpretation import validate_dataset_access_interpretation, MANIFEST_SHA256

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-02'
MANIFEST = DOCS / 'registration_access_interpretation.json'


class DatasetAccessInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_bytes())
        self.member = self.manifest['members'][0]
        self.reference = {'manifest_path': str(MANIFEST), 'manifest_sha256': MANIFEST_SHA256}
        self.root = ET.parse(REPO / 'FGDC' / (self.member['source_id'] + '.xml')).getroot()
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def validate(self, reference=None, member=None, root=None):
        member = self.member if member is None else member
        return validate_dataset_access_interpretation(self.reference if reference is None else reference,
            member['source_id'], member['source_sha256'], self.root if root is None else root)

    def test_exact_source_backed_interpretation_grants_no_authority(self):
        result = self.validate()
        self.assertEqual(result['status'], 'SOURCE_BACKED')
        self.assertFalse(result['grants_rehosting'])
        self.assertFalse(result['grants_new_license'])
        self.assertFalse(result['publication_approved'])

    def test_membership_id_and_hash_both_required(self):
        for key, value in [('source_id', 'unknown'), ('source_sha256', '0' * 64)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(member={**self.member, key: value})

    def test_plain_exact_constraints_and_context_are_required(self):
        for xpath in ('./metainfo/metac', './idinfo/accconst', './metainfo/metuc', './idinfo/useconst',
                      './idinfo/descript/abstract'):
            for mutation in ('text', 'mixed', 'attribute', 'repeated'):
                root = copy.deepcopy(self.root)
                node = root.find(xpath)
                if mutation == 'text':
                    node.text = 'Different meaning'
                elif mutation == 'mixed':
                    ET.SubElement(node, 'b').text = 'extra'
                elif mutation == 'attribute':
                    node.set('scope', 'different')
                else:
                    parent = root.find(xpath.rsplit('/', 1)[0])
                    parent.append(copy.deepcopy(node))
                with self.subTest(xpath=xpath, mutation=mutation), self.assertRaises(ValueError):
                    self.validate(root=root)

    def test_security_and_extension_fields_remain_held(self):
        for name in ('metsi', 'metextns'):
            root = copy.deepcopy(self.root)
            ET.SubElement(root.find('./metainfo'), name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.validate(root=root)

    def test_rehashed_manifest_cannot_expand_meaning_or_membership(self):
        for key, value in [('status', 'USER_ATTESTED'), ('members', []), ('grants_new_license', True),
                           ('meaning', 'unrestricted_metadata'), ('evidence', {})]:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'changed.json'
                path.write_text(json.dumps({**self.manifest, key: value}))
                ref = {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.subTest(key=key), self.assertRaises(ValueError):
                    self.validate(reference=ref)

    def test_missing_stale_and_malformed_reference_rejected(self):
        for ref in ({}, {**self.reference, 'manifest_path': '/missing'},
                    {**self.reference, 'manifest_sha256': '0' * 64}):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                self.validate(reference=ref)

    def prepared(self, tmp, enabled=True, authority=True, source_id='FGDC-3682'):
        from scripts.collection_qa import classify_collection
        from scripts.path_config import OutputPaths
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        shutil.copyfile(REPO / 'FGDC' / (source_id + '.xml'), source / (source_id + '.xml'))
        output = Path(tmp) / 'output'
        report = classify_collection(source, output, self.reviewed_at,
            DOCS / 'rehosting_authority.json' if authority else None,
            DOCS / 'contact_source_interpretation.json', DOCS / 'exxon_citation_interpretation.json',
            MANIFEST if enabled else None)
        paths = OutputPaths(str(output), 'sandbox')
        return report, paths, Path(paths.zenodo_json_dir) / (source_id + '.json')

    def test_opt_in_only_preserves_rights_dates_creators_and_source(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            baseline, _, path = self.prepared(tmp, False)
            self.assertEqual(baseline['summary']['source_status_counts']['held'], 1)
            old = json.loads(path.read_bytes())
            self.assertTrue(any('access constraints' in reason for reason in baseline['records'][0]['hold_reasons']))
            report, paths, path = self.prepared(tmp)
            self.assertEqual(report['summary']['source_status_counts']['supported'], 1)
            payload = json.loads(path.read_bytes())
            self.assertEqual(payload['metadata'], old['metadata'])
            self.assertEqual(payload['metadata']['license'], '')
            self.assertEqual(payload['metadata']['access_right'], 'restricted')
            self.assertEqual(report['records'][0]['dataset_access_interpretation'], 'SOURCE_BACKED')
            self.assertFalse(report['records'][0]['publication_approved'])
            self.assertEqual((Path(paths.original_fgdc_dir) / 'FGDC-3682.xml').read_bytes(),
                             (REPO / 'FGDC/FGDC-3682.xml').read_bytes())
            assess_source(str(path), paths)

    def test_separate_authority_required_and_unrelated_cohort_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            report, _, _ = self.prepared(tmp, authority=False)
            self.assertEqual(report['summary']['source_status_counts']['supported'], 0)
            self.assertTrue(any('separate rehosting authority' in r for r in report['records'][0]['hold_reasons']))
        with tempfile.TemporaryDirectory() as tmp:
            default, _, path = self.prepared(tmp, enabled=False, source_id='FGDC-1839')
            old = json.loads(path.read_bytes())
            report, _, path = self.prepared(tmp, enabled=True, source_id='FGDC-1839')
            self.assertEqual(report['summary'], default['summary'])
            self.assertEqual(json.loads(path.read_bytes()), old)

    def test_agent_rejects_conflicting_profiles_missing_authority_or_rights_changes(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            _, paths, path = self.prepared(tmp)
            original = json.loads(path.read_bytes())
            for mutation in ('conflict', 'missing_authority', 'policy_license', 'metadata_license', 'open_access', 'reference'):
                payload = copy.deepcopy(original)
                if mutation == 'conflict':
                    payload['artifact_policy']['source_access_interpretation'] = self.reference
                elif mutation == 'missing_authority':
                    del payload['artifact_policy']['rehosting_authority']
                elif mutation == 'policy_license':
                    payload['artifact_policy']['license'] = 'cc-by-4.0'
                elif mutation == 'metadata_license':
                    payload['metadata']['license'] = 'cc-by-4.0'
                elif mutation == 'open_access':
                    payload['metadata']['access_right'] = 'open'
                else:
                    payload['artifact_policy']['dataset_access_interpretation']['manifest_sha256'] = '0' * 64
                path.write_text(json.dumps(payload))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    assess_source(str(path), paths)

    def test_all_human_schemas_revalidate_external_evidence_and_policy(self):
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval
        from scripts.upload_service import metadata_hash, prepare_metadata
        for schema in (1, 2):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as tmp:
                _, paths, path = self.prepared(tmp)
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
                record = {'fgdc_id': 'FGDC-3682', 'deposition_id': 123, 'source_sha256': digest,
                          'metadata_sha256': metadata_hash(metadata), 'artifact_contract': artifact,
                          'qa': {'approved': True, 'reviewer_type': 'human', 'reviewer': 'Offline test fixture',
                                 'reviewed_at': self.reviewed_at, 'rationale': 'Fixture source review',
                                 'checks': dict.fromkeys(QA_CHECKS, True), 'run_id': 'fixture',
                                 'review_revision': 'fixture', 'evidence': ['Fixture evidence']},
                          'duplicate_review': {'status': 'reviewed', 'classification': 'checked_no_match',
                                               'rationale': 'Fixture only', 'evidence': ['Fixture only']}}
                manifest = {'schema_version': schema, 'source_revision': 'fixture', 'environment': 'sandbox',
                            'records': [record]}
                validate_approval(manifest, 'FGDC-3682', entry, paths)
                for mutation in ('changed_bytes', 'missing_file', 'reference', 'conflict', 'missing_authority'):
                    shutil.copyfile(MANIFEST, evidence)
                    candidate = copy.deepcopy(payload)
                    if mutation == 'changed_bytes':
                        evidence.write_bytes(evidence.read_bytes() + b'\n')
                    elif mutation == 'missing_file':
                        evidence.unlink()
                    elif mutation == 'reference':
                        candidate['artifact_policy']['dataset_access_interpretation']['manifest_sha256'] = '0' * 64
                    elif mutation == 'conflict':
                        candidate['artifact_policy']['source_access_interpretation'] = self.reference
                    else:
                        del candidate['artifact_policy']['rehosting_authority']
                    path.write_text(json.dumps(candidate))
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        validate_approval(manifest, 'FGDC-3682', entry, paths)

    def test_coherently_rehashed_cache_cannot_grant_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, path = self.prepared(tmp)
            payload = json.loads(path.read_bytes())
            payload['metadata']['license'] = 'cc-by-4.0'
            path.write_text(json.dumps(payload))
            report_path = Path(tmp) / 'output/classification.json'
            cached = json.loads(report_path.read_bytes())
            cached['records'][0]['prepared_payload_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            report_path.write_text(json.dumps(cached))
            report, _, _ = self.prepared(tmp)
            self.assertEqual(report['summary']['source_status_counts']['supported'], 0)
            self.assertEqual(report['summary']['source_status_counts']['held'], 1)

    def test_compiler_accepts_only_well_formed_bound_reference(self):
        from scripts.curation_batches import compile_batches
        from tests.test_curation_batches import CurationBatchTests
        fixture = CurationBatchTests(methodName='test_artifact_tokens_bind_each_source_and_validate')
        fixture.setUp()
        try:
            batch = copy.deepcopy(fixture.batch)
            batch['correction']['artifact_policy'] = {
                'schema_version': 1, 'object_kind': 'original_fgdc_xml', 'resource_type': 'other',
                'date_semantics': 'source_metadata_date', 'source_sha256': '$source_sha256',
                'reviewer': batch['reviewer'], 'reviewed_at': batch['reviewed_at'], 'rationale': batch['rationale'],
                'rights_evidence': 'Fixture source XML', 'date_evidence': 'Fixture metadata date',
                'dataset_access_interpretation': self.reference}
            batch['correction']['content_classification'] = {
                'inventory_complete': True, 'reviewer': batch['reviewer'],
                'reviewed_at': batch['reviewed_at'], 'rationale': batch['rationale'],
                'files': [{'name': '$source_filename', 'role': 'descriptive_metadata',
                           'evidence': 'Fixture original XML'}]}
            doc = {'schema_version': 1, 'batches': [batch]}
            decisions, _ = compile_batches([doc], fixture.sources)
            self.assertEqual(decisions['FGDC1']['artifact_policy']['dataset_access_interpretation'], self.reference)
            for bad in ({}, {**self.reference, 'manifest_sha256': 'invalid'}, {**self.reference, 'extra': True}):
                batch['correction']['artifact_policy']['dataset_access_interpretation'] = bad
                with self.subTest(reference=bad), self.assertRaises(ValueError):
                    compile_batches([doc], fixture.sources)
        finally:
            fixture.doCleanups()

    def test_stale_external_manifest_invalidates_agent_and_cached_classification(self):
        from scripts.agent_qa import assess_source
        from scripts.collection_qa import classify_collection
        with tempfile.TemporaryDirectory() as tmp:
            _, paths, path = self.prepared(tmp)
            evidence = Path(tmp) / 'evidence.json'
            shutil.copyfile(MANIFEST, evidence)
            payload = json.loads(path.read_bytes())
            payload['artifact_policy']['dataset_access_interpretation']['manifest_path'] = str(evidence)
            path.write_text(json.dumps(payload))
            assess_source(str(path), paths)
            evidence.write_bytes(evidence.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'differs from the reviewed profile'):
                assess_source(str(path), paths)
            report = classify_collection(Path(tmp) / 'sources', Path(tmp) / 'output', self.reviewed_at,
                DOCS / 'rehosting_authority.json', dataset_access_interpretation_manifest=evidence)
            self.assertEqual(report['summary']['source_status_counts']['supported'], 0)
            self.assertTrue(any('exact reviewed manifest' in r for r in report['records'][0]['hold_reasons']))
