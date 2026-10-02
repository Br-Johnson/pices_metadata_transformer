"""Source-wording adjudication clears access only, never rights or release gates."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.collection_qa import classify_collection
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.qa_manifest import QA_CHECKS, prepare_manifest, validate_approval
from tests import test_rehosting_authority as authority_fixtures


class SourceAccessInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.authority = authority_fixtures.RehostingAuthorityTests(
            methodName='test_restricted_blank_license_with_source_bound_permission_is_supported')
        self.authority.setUp()
        self.addCleanup(self.authority.doCleanups)
        self.authority.authority_payload()
        self.fixture = self.authority.fixture
        self.path = Path(self.fixture.tmp.name, 'access-interpretation.json')
        template = Path(__file__).resolve().parents[1] / 'docs/readiness/2026-10-02/contact_source_interpretation.json'
        self.manifest = json.loads(template.read_text())
        self.fixture.raw = self.fixture.raw.replace(
            b'<metainfo>', b'<metainfo><metac>Contact Source.</metac>').replace(
            b'</idinfo>', b'<accconst>Contact Source.</accconst></idinfo>').replace(
            b'<useconst>CC0</useconst>', b'<useconst>Contact Source.</useconst>').replace(
            b'<metuc>Reuse rights unresolved</metuc>', b'<metuc>Contact Source.</metuc>')
        self.bind_source()

    def write_interpretation(self):
        self.path.write_text(json.dumps(self.manifest))
        self.reference = {'manifest_path': str(self.path),
                          'manifest_sha256': hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def bind_source(self):
        self.fixture.source.write_bytes(self.fixture.raw)
        digest = hashlib.sha256(self.fixture.raw).hexdigest()
        self.authority.manifest['sources'] = {'sample': digest}
        self.authority.write_authority()
        self.manifest['sources'] = {'sample': digest}
        self.write_interpretation()
        self.fixture.payload['artifact_policy'].update(
            source_sha256=digest, rehosting_authority=copy.deepcopy(self.authority.reference),
            source_access_interpretation=copy.deepcopy(self.reference), reviewed_at='2026-10-02T18:30:00Z')
        self.fixture.sync()

    def human_manifest(self, schema):
        manifest = prepare_manifest(self.fixture.paths)
        manifest['schema_version'] = schema
        record = manifest['records'][0]
        record['qa'].update(approved=True, reviewer_type='human', reviewer='Fixture human assessor',
                            reviewed_at='2026-10-02T18:30:00Z', rationale='Explicit fixture source adjudication',
                            checks={name: True for name in QA_CHECKS}, run_id='fixture-human-review',
                            review_revision=manifest['source_revision'], evidence=['Offline fixture review'])
        record['duplicate_review'].update(status='reviewed', classification='checked_no_match',
                                           rationale='Explicit fixture title comparison',
                                           evidence=self.fixture.duplicates['evidence'])
        return manifest

    def approve(self, manifest, remote=False):
        args = [manifest, 'sample', self.fixture.entry, self.fixture.paths]
        if remote:
            args.extend((self.fixture.remote['body']['metadata'], self.fixture.remote['body']['files']))
        return validate_approval(*args)

    def test_exact_attested_access_scope_preserves_restricted_blank_license(self):
        original = self.fixture.source.read_bytes()
        metadata, digest, artifact, _ = self.authority.assess()
        self.assertEqual(metadata['license'], '')
        self.assertEqual(metadata['access_right'], 'restricted')
        self.assertIn('USER_ATTESTED', metadata['access_conditions'])
        self.assertEqual(digest, self.manifest['sources']['sample'])
        self.assertIsNotNone(artifact)
        self.assertEqual(self.fixture.source.read_bytes(), original)

    def test_audited_paired_use_wordings_are_preserved_without_new_license(self):
        raw = self.fixture.raw
        for wording in (b'Contact Source.', b'Check with Source.', b'None'):
            with self.subTest(wording=wording):
                self.fixture.raw = raw.replace(b'<useconst>Contact Source.</useconst>', b'<useconst>' + wording + b'</useconst>').replace(
                    b'<metuc>Contact Source.</metuc>', b'<metuc>' + wording + b'</metuc>')
                self.bind_source()
                metadata, _, _, _ = self.authority.assess()
                self.assertEqual(metadata['license'], '')
                self.assertEqual(metadata['access_right'], 'restricted')
                self.assertIn(b'<metuc>' + wording + b'</metuc>', self.fixture.source.read_bytes())

    def test_missing_stale_changed_or_out_of_scope_evidence_fails_closed(self):
        baseline = copy.deepcopy(self.fixture.payload)
        for mutation in ('missing', 'digest', 'source_membership'):
            with self.subTest(mutation=mutation):
                self.fixture.payload = copy.deepcopy(baseline)
                reference = self.fixture.payload['artifact_policy']['source_access_interpretation']
                if mutation == 'missing': reference['manifest_path'] += '.missing'
                elif mutation == 'digest': reference['manifest_sha256'] = '0' * 64
                else:
                    self.manifest['sources'] = {'other': self.manifest['sources']['sample']}
                    self.write_interpretation()
                    self.fixture.payload['artifact_policy']['source_access_interpretation'] = self.reference
                self.fixture.sync()
                with self.assertRaisesRegex(ValueError, 'interpretation|attested access'):
                    self.authority.assess()

    def test_modified_statement_provenance_and_permission_claims_are_rejected(self):
        baseline = copy.deepcopy(self.manifest)
        for key, value in (('statement', 'All metadata may be licensed CC0'), ('status', 'VERIFIED'),
                           ('grants_rehosting', True), ('grants_new_license', True),
                           ('publication_approved', True), ('independently_verified_agreement', True),
                           ('license', 'cc-zero'), ('attested_at', '2026-10-02T12:20:58Z'),
                           ('provenance', {})):
            with self.subTest(key=key):
                self.manifest = copy.deepcopy(baseline)
                self.manifest[key] = value
                self.write_interpretation()
                self.fixture.payload['artifact_policy']['source_access_interpretation'] = self.reference
                self.fixture.sync()
                with self.assertRaisesRegex(ValueError, 'exact USER_ATTESTED'):
                    self.authority.assess()

    def test_nonmatching_and_extra_metadata_constraints_remain_held(self):
        baseline = self.fixture.raw
        variants = (
            baseline.replace(b'<accconst>Contact Source.</accconst>', b'<accconst>Check with Source.</accconst>'),
            baseline.replace(b'<metac>Contact Source.</metac>', b'<metac>Check with Source.</metac>'),
            baseline.replace(b'<metac>Contact Source.</metac>', b'<metac>Contact Source. Do not disclose metadata.</metac>'),
            baseline.replace(b'</metainfo>', b'<metac>Do not disclose metadata.</metac></metainfo>'),
            baseline.replace(b'<metuc>Contact Source.</metuc>', b'<metuc>Check with Source.</metuc>'),
            baseline.replace(b'Contact Source.</useconst>', b'Do not repost metadata.</useconst>').replace(
                b'Contact Source.</metuc>', b'Do not repost metadata.</metuc>'),
            baseline.replace(b'</metainfo>', b'<metsi><metsc>Sensitive metadata</metsc></metsi></metainfo>'),
            baseline.replace(b'</metainfo>', b'<metextns><onlink>Separate terms</onlink></metextns></metainfo>'),
        )
        for index, raw in enumerate(variants):
            with self.subTest(case=index):
                self.fixture.raw = raw
                self.bind_source()  # Coherent fresh hashes do not erase separate constraints.
                with self.assertRaisesRegex(ValueError, 'interpretation|Separate metadata'):
                    self.authority.assess()

    def test_interpretation_needs_separate_authority_and_post_attestation_timestamp(self):
        baseline = copy.deepcopy(self.fixture.payload)
        for mutation in ('authority', 'backdated', 'naive'):
            with self.subTest(mutation=mutation):
                self.fixture.payload = copy.deepcopy(baseline)
                policy = self.fixture.payload['artifact_policy']
                if mutation == 'authority': policy.pop('rehosting_authority')
                else: policy['reviewed_at'] = '2026-10-02T12:20:58Z' if mutation == 'backdated' else '2026-10-02T18:30:00'
                self.fixture.sync()
                with self.assertRaises(ValueError): self.authority.assess()

    def test_creator_date_and_relation_holds_remain_and_human_adjudication_is_compatible(self):
        baseline_raw, baseline_payload = self.fixture.raw, copy.deepcopy(self.fixture.payload)
        self.fixture.raw = baseline_raw.replace(b'Example Marine Institute', b'Alice and Bob')
        self.fixture.payload['metadata']['creators'] = [{'name': 'Alice and Bob'}]
        self.bind_source()
        with self.assertRaisesRegex(ValueError, 'Creator semantics'):
            self.authority.assess()
        for schema in (1, 2):
            self.assertTrue(self.approve(self.human_manifest(schema), remote=True)['qa']['approved'])
        self.fixture.raw, self.fixture.payload = baseline_raw.replace(b'20020430', b'122003'), copy.deepcopy(baseline_payload)
        self.bind_source()
        with self.assertRaisesRegex(ValueError, 'Exact source-backed date'):
            self.authority.assess()
        self.fixture.raw, self.fixture.payload = baseline_raw, copy.deepcopy(baseline_payload)
        self.fixture.payload['metadata']['related_identifiers'] = [
            {'identifier': '10.1234/example', 'relation': 'isSupplementTo', 'scheme': 'doi'}]
        self.bind_source()
        with self.assertRaisesRegex(ValueError, 'Relations require'):
            self.authority.assess()

    def test_changed_interpretation_invalidates_agent_and_human_approval_and_readback(self):
        agent = self.fixture.build()
        self.assertTrue(agent['records'][0]['qa']['approved'])
        self.assertIn('source_access_interpretation.py', agent['records'][0]['agent_evidence']['rules_sha256'])
        manifests = [agent, self.human_manifest(1), self.human_manifest(2)]
        for manifest in manifests:
            self.assertTrue(self.approve(manifest, remote=True)['qa']['approved'])
        self.manifest['sources'] = {}
        self.write_interpretation()
        for manifest in manifests:
            for remote in (False, True):
                with self.subTest(reviewer=manifest['records'][0]['qa']['reviewer_type'], schema=manifest['schema_version'], remote=remote):
                    with self.assertRaisesRegex(ValueError, 'interpretation manifest digest is stale'):
                        self.approve(manifest, remote)

    def test_collection_resume_keeps_alias_holds_and_rechecks_interpretation(self):
        sources = Path(self.fixture.tmp.name, 'collection-sources'); sources.mkdir()
        (sources / 'sample.xml').write_bytes(self.fixture.raw)
        (sources / 'alias.xml').write_bytes(self.fixture.raw)
        digest = hashlib.sha256(self.fixture.raw).hexdigest()
        self.authority.manifest['sources']['alias'] = digest
        self.authority.write_authority()
        self.manifest['sources']['alias'] = digest
        self.write_interpretation()
        output = Path(self.fixture.tmp.name, 'collection-output')
        args = (sources, output, '2026-10-02T18:30:00Z', self.authority.path, self.path)
        before = classify_collection(*args)
        self.assertEqual(before['summary']['source_status_counts']['held'], 2)
        for row in before['records']:
            self.assertEqual(row['source_status_without_aliases'], 'supported')
            self.assertFalse(row['publication_approved']); self.assertFalse(row['remote_verified'])
        with patch.object(FGDCToZenodoTransformer, '_build_zenodo_metadata', side_effect=AssertionError('Unexpected reconstruction')):
            self.assertEqual(classify_collection(*args), before)
        self.manifest['sources'] = {}
        self.write_interpretation()
        after = classify_collection(*args)
        self.assertNotEqual(after['profile_sha256'], before['profile_sha256'])
        for row in after['records']:
            self.assertEqual(row['source_status_without_aliases'], 'held')
            self.assertEqual(row['source_access_interpretation'], 'not_established')
            self.assertFalse(row['publication_approved']); self.assertFalse(row['remote_verified'])
        missing = classify_collection(sources, output, args[2], self.authority.path, str(self.path) + '.missing')
        self.assertEqual(missing['summary']['source_status_counts']['held'], 2)
        for source in sources.glob('*.xml'):
            self.assertEqual(source.read_bytes(), self.fixture.raw)


if __name__ == '__main__':
    unittest.main()
