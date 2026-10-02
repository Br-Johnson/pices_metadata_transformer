"""Exact alternative access attestation retains independent source and release holds."""
import copy
import hashlib
from unittest.mock import patch
import json
from pathlib import Path
import unittest
from tests import test_source_access_interpretation as access_fixtures


class ContributorSourceInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.base = access_fixtures.SourceAccessInterpretationTests('test_exact_attested_access_scope_preserves_restricted_blank_license')
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.base.manifest = json.loads(Path('docs/readiness/2026-10-02/contributor_source_interpretation.json').read_text())
        # Shape fixtures deliberately pin their one synthetic member. Real cohort
        # tests below never patch either production binding constant.
        self.count_patch = patch('scripts.source_access_interpretation.CONTRIBUTOR_SOURCE_COUNT', 1)
        self.count_patch.start()
        self.addCleanup(self.count_patch.stop)
        self.digest_patch = None
        self.base.fixture.raw = self.base.fixture.raw.replace(b'Contact Source.', b'Check with Contributor or Source.')
        self.bind()

    def bind(self):
        self.base.bind_source()
        if self.digest_patch is not None:
            self.digest_patch.stop()
        digest = hashlib.sha256(json.dumps(self.base.manifest['sources'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.digest_patch = patch('scripts.source_access_interpretation.CONTRIBUTOR_SOURCES_SHA256', digest)
        self.digest_patch.start()
        self.addCleanup(self.digest_patch.stop)
        self.base.fixture.payload['artifact_policy']['reviewed_at'] = '2026-10-02T23:44:00Z'
        self.base.fixture.sync()

    def test_exact_attested_alternative_supported_without_license_or_xml_changes(self):
        original = self.base.fixture.source.read_bytes()
        metadata, _, artifact, _ = self.base.authority.assess()
        self.assertEqual(metadata['license'], '')
        self.assertEqual(metadata['access_right'], 'restricted')
        self.assertIsNotNone(artifact)
        self.assertEqual(original, self.base.fixture.source.read_bytes())

    def test_other_wording_extra_constraints_and_date_stay_held(self):
        raw = self.base.fixture.raw
        for before, after in ((b'Check with Contributor or Source.', b'Check with Contributor'),
                              (b'</metainfo>', b'<metsi><metsc>Restricted</metsc></metsi></metainfo>'),
                              (b'<metuc>Check with Contributor or Source.</metuc>', b'<metuc>Do not repost metadata.</metuc>'),
                              (b'20020430', b'122003'),
                              (b'Example Marine Institute', b'Alice and Bob')):
            with self.subTest(after=after):
                self.base.fixture.raw = raw.replace(before, after)
                self.bind()
                with self.assertRaises(ValueError): self.base.authority.assess()

    def test_evidence_tampering_and_missing_authority_fail_closed(self):
        for key, value in (('statement', 'permission granted'), ('provenance', {}), ('sources', {}), ('grants_new_license', True)):
            baseline = copy.deepcopy(self.base.manifest)
            with self.subTest(key=key):
                self.base.manifest[key] = value
                self.base.write_interpretation()
                self.base.fixture.payload['artifact_policy']['source_access_interpretation'] = self.base.reference
                self.base.fixture.sync()
                with self.assertRaises(ValueError): self.base.authority.assess()
            self.base.manifest = baseline
        self.bind()
        self.base.fixture.payload['artifact_policy'].pop('rehosting_authority')
        self.base.fixture.sync()
        with self.assertRaises(ValueError): self.base.authority.assess()

    def test_backdated_assessment_rejected(self):
        self.base.fixture.payload['artifact_policy']['reviewed_at'] = '2026-10-02T23:42:59Z'
        self.base.fixture.sync()
        with self.assertRaises(ValueError): self.base.authority.assess()

    def test_collection_selects_only_exact_profile_and_rechecks_resume(self):
        from scripts.collection_qa import classify_collection
        sources = Path(self.base.fixture.tmp.name, 'contributor-sources')
        sources.mkdir()
        (sources / 'sample.xml').write_bytes(self.base.fixture.raw)
        output = Path(self.base.fixture.tmp.name, 'contributor-output')
        kwargs = dict(authority_manifest=self.base.authority.path,
                      contributor_access_interpretation_manifest=self.base.path)
        args = (sources, output, '2026-10-02T23:44:00Z')
        before = classify_collection(*args, **kwargs)
        self.assertEqual(before['summary']['source_status_counts']['supported'], 1)
        self.assertFalse(before['records'][0]['publication_approved'])
        self.assertEqual(classify_collection(*args, **kwargs), before)
        self.base.manifest['sources'] = {}
        self.base.write_interpretation()
        after = classify_collection(*args, **kwargs)
        self.assertEqual(after['summary']['source_status_counts']['held'], 1)
        self.assertEqual(after['records'][0]['source_access_interpretation'], 'not_established')

    def test_stale_attestation_invalidates_agent_and_human_readback(self):
        agent = self.base.fixture.build()
        self.assertTrue(agent['records'][0]['qa']['approved'])
        manifests = [agent, self.base.human_manifest(1), self.base.human_manifest(2)]
        for manifest in manifests:
            self.assertTrue(self.base.approve(manifest, remote=True)['qa']['approved'])
        self.base.manifest['sources'] = {}
        self.base.write_interpretation()
        for manifest in manifests:
            for remote in (False, True):
                with self.subTest(schema=manifest['schema_version'], remote=remote):
                    with self.assertRaisesRegex(ValueError, 'interpretation manifest digest is stale'):
                        self.base.approve(manifest, remote)


class ContributorCohortBindingTests(unittest.TestCase):
    def test_real_canonical_cohort_and_rehashed_membership_changes(self):
        import hashlib
        import tempfile
        from lxml import etree
        from scripts.source_access_interpretation import validate_interpretation
        manifest = json.loads(Path('docs/readiness/2026-10-02/contributor_source_interpretation.json').read_text())
        sid = 'FGDC-1209'
        raw = Path('FGDC', sid + '.xml').read_bytes()
        source_hash = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'manifest.json')
            for mutation in ('canonical', 'add', 'remove', 'rebind', 'substitute'):
                changed = copy.deepcopy(manifest)
                other = next(key for key in changed['sources'] if key != sid)
                if mutation == 'add': changed['sources']['new'] = '0' * 64
                elif mutation == 'remove': changed['sources'].pop(other)
                elif mutation == 'rebind': changed['sources'][other] = '0' * 64
                elif mutation == 'substitute': changed['sources']['new'] = changed['sources'].pop(other)
                path.write_text(json.dumps(changed))
                reference = {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.subTest(mutation=mutation):
                    if mutation == 'canonical':
                        self.assertEqual(validate_interpretation(reference, sid, source_hash, etree.fromstring(raw), '2026-10-02T23:48:30Z')['status'], 'USER_ATTESTED')
                    else:
                        with self.assertRaisesRegex(ValueError, 'canonical'):
                            validate_interpretation(reference, sid, source_hash, etree.fromstring(raw), '2026-10-02T23:48:30Z')
