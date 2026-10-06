"""Exact PICES26 wire projection; originals and name-only legacy credits persist."""

import copy
import html
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_singleton as mapping
from scripts.agent_qa import assess_source
from scripts.production_mutations import PROTECTED
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_exxon_coverage as exxon_tests
from tests import test_modern_organizational_coverage as organizational_tests
from tests.test_modern_upload_compatibility import CompatibilityTransport

MAPPING_SHA = '15d5f40fe829919a0ff9d9b81bcfc6205b2cd4042a3891e4dc9e4b3595204670'
REVIEW_SHA = '7e4b0ea88d239855852383878f9bfcdcb4c4ba232c451ddfcae6910e7682a711'
NAME = 'North Pacific Marine Science Organization (PICES)'
MODERN = [{'person_or_org': {'name': NAME, 'type': 'organizational'}}]
OLD_SOURCES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839')


class ModernPicesCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.PICES_MAPPING.read_bytes())
        cls.ids = [row['source_id'] for row in cls.manifest['members']]
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=cls.ids + list(OLD_SOURCES))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def fixture(self, sid='FGDC-1319'):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        return fixtures.Fixture(directory.name, self.prepared_root, source_id=sid)

    def test_all26_exact_source_origin_legacy_profile_plan_and_independent_review(self):
        self.assertEqual(mapping.sha(mapping.PICES_MAPPING.read_bytes()), MAPPING_SHA)
        self.assertEqual(mapping.PICES_MAPPING_SHA, MAPPING_SHA)
        raw = (mapping.PICES_MAPPING.parent / 'modern_pices26_source_review.json').read_bytes()
        self.assertEqual(mapping.sha(raw), REVIEW_SHA)
        review = mapping.parse(raw)
        self.assertEqual(self.manifest['review_sha256'], REVIEW_SHA)
        self.assertEqual(self.manifest['members'], review['members'])
        self.assertEqual(self.manifest['modern_creators'], MODERN)
        self.assertEqual(self.manifest['creators'], [{'name': NAME}])
        self.assertEqual(self.manifest['source_plan_sha256'], mapping.PLAN_SHA)
        self.assertEqual(self.manifest['creator_profile_sha256'], mapping.PROFILE_SHA)
        cohort = next(row for row in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']
                      if row['profile'] == 'pices_literal_26')
        self.assertEqual(self.manifest['members'], cohort['members'])
        self.assertEqual(self.manifest['creators'], cohort['creators'])
        targets = {row['record_target_id']: row for row in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        self.assertEqual(len(set(self.ids)), 26)
        self.assertFalse(set(self.ids) & set(PROTECTED))
        for member in self.manifest['members']:
            sid = member['source_id']
            with self.subTest(source=sid):
                raw = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
                self.assertEqual(mapping.sha(raw), member['source_sha256'])
                nodes = ET.fromstring(raw).findall('./idinfo/citation/citeinfo/origin')
                self.assertEqual(len(nodes), 1)
                self.assertEqual((nodes[0].text, nodes[0].attrib, list(nodes[0])), (NAME, {}, []))
                target = targets[sid]
                self.assertEqual(target['source_ids'], [sid])
                self.assertEqual(target['source_sha256'], member['source_sha256'])
                self.assertEqual(target['source_semantic_status'], 'supported')
                self.assertIsNone(target['identity_decision']['production_record_id'])
                self.assertIsNone(target['identity_decision']['production_doi'])

    def test_all26_fresh_repeat_keeps_complete_legacy_metadata_dates_rights_and_xml(self):
        for sid in self.ids:
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                prepared = fixture.prepared
                before = fixture.json_file.read_bytes()
                metadata, source_sha, artifact, _ = assess_source(fixture.json_file, fixture.paths)
                self.assertEqual(metadata['creators'], [{'name': NAME}])
                wire = mapping.parse(prepared.body)
                self.assertEqual(wire['metadata']['creators'], MODERN)
                text = wire['metadata']['additional_descriptions'][0]['description']
                self.assertEqual(mapping.parse(html.unescape(text.split('<pre>', 1)[1][:-6])), metadata)
                for field in ('title', 'description', 'publication_date'):
                    self.assertEqual(wire['metadata'][field], metadata[field])
                self.assertEqual(wire['metadata']['subjects'], [{'subject': k} for k in metadata.get('keywords', [])])
                self.assertEqual(wire['access'], {'record': 'public', 'files': 'restricted'})
                self.assertNotIn('rights', wire['metadata'])
                self.assertNotIn('license', wire['metadata'])
                self.assertEqual(prepared.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(prepared.evidence['source_sha256'], source_sha)
                self.assertEqual(prepared.evidence['schema_version'], 5)
                self.assertEqual(prepared.evidence['policy'], mapping.PICES_POLICY)
                self.assertEqual(prepared.evidence['creator_profile_sha256'], mapping.PROFILE_SHA)
                self.assertEqual(prepared.evidence['mapping_manifest_sha256'], MAPPING_SHA)
                self.assertEqual(mapping.prepare(fixture.json_file, fixture.paths), prepared)
                self.assertEqual(fixture.json_file.read_bytes(), before)

    def test_rehashed_manifest_cannot_change_members_origin_legacy_or_wire_credits(self):
        fixture = self.fixture()
        changes = [lambda d: d['members'].pop(),
                   lambda d: d['members'][0].update(source_sha256='0' * 64),
                   lambda d: d['creators'][0].update(type='Organization'),
                   lambda d: d.update(raw_origin='PICES'),
                   lambda d: d['modern_creators'][0]['person_or_org'].update(name='PICES'),
                   lambda d: d['modern_creators'][0]['person_or_org'].update(type='personal'),
                   lambda d: d['modern_creators'][0].update(affiliations=[{'name': NAME}]),
                   lambda d: d['modern_creators'].append({'person_or_org': {'name': 'Editor', 'type': 'organizational'}})]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                value = copy.deepcopy(self.manifest)
                change(value)
                path = self.root / 'changed.json'
                path.write_bytes(mapping.encode(value))
                with patch.object(mapping, 'PICES_MAPPING', path), \
                        patch.object(mapping, 'PICES_MAPPING_SHA', mapping.sha(path.read_bytes())), \
                        self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])

    def test_withdrawal_and_untyped_other_sources_hold_without_changing_prior_policies(self):
        fixture = self.fixture()
        with patch.object(mapping, 'PICES_MAPPING', self.root / 'missing.json'):
            with self.assertRaises(OSError):
                fixture.runner().run()
            for sid, version in zip(OLD_SOURCES, range(1, 5), strict=True):
                self.assertEqual(self.fixture(sid).prepared.evidence['schema_version'], version)
        self.assertEqual(fixture.transport.calls, [])
        profile = mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)
        # SOA now has a finite citation policy; MSO Anchorage remains untyped.
        outside = next(row['members'][0]['source_id'] for row in profile['cohorts']
                       if row['profile'] == 'plain_institution_program_37_FGDC-2232')
        self.assertEqual(outside, 'FGDC-2232')
        for sid in (outside, *PROTECTED):
            with self.subTest(source=sid), self.assertRaises(ValueError):
                mapping.pices_source_policy(sid)

    def test_legacy_input_cannot_gain_type_or_editor_even_when_modern_shape_is_valid(self):
        fixture = self.fixture()
        before = fixture.json_file.read_bytes()
        for creators in ([{'name': NAME, 'type': 'Organization'}], [{'name': 'Vera Alexander'}]):
            with self.subTest(creators=creators):
                payload = mapping.parse(before)
                payload['metadata']['creators'] = creators
                fixture.json_file.write_bytes(mapping.encode(payload))
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])

    def test_completed_upload_community_release_and_readonly_retry_use_same_source(self):
        fixture = self.fixture()
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
        harness = organizational_tests.PublicationFixture(fixture)
        self.assertEqual([method for method, _, _ in fixture.transport.calls if method != 'GET'],
                         ['POST', 'POST', 'PUT'])
        documents = harness.ready()
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['release_complete'])
        self.assertTrue(result['community_membership_verified'])
        retry = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(retry['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual([call[0] for call in harness.transport.calls if call[0] != 'GET'], ['PUT', 'POST'])

    def test_pr40_old_policies_bridge_completed_upload_without_rewriting_history(self):
        for sid in OLD_SOURCES:
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
                harness = organizational_tests.PublicationFixture(fixture)
                retained = exxon_tests.save_historical_runtime(harness, publication.PR40_RUNTIME)
                original_calls = list(fixture.transport.calls)
                _, bound = harness.bridge()
                self.assertEqual(bound['original_runtime_sha256'], publication.PR40_RUNTIME)
                self.assertEqual(fixture.transport.calls, original_calls)
                self.assertEqual({path: path.read_bytes() for path in retained}, retained)

    def test_new_policy_cannot_claim_old_runtime_or_repeat_uncertain_create(self):
        harness = organizational_tests.PublicationFixture(self.fixture())
        exxon_tests.save_historical_runtime(harness, publication.PR40_RUNTIME)
        with self.assertRaises(ValueError):
            harness.bridge()
        fixture = self.fixture()
        fixture.transport.fail_index = 0
        fixture.transport.effect_before_fail = True
        runner = fixture.runner()
        with self.assertRaises(ValueError):
            runner.run()
        intent = runner.intent_path.read_bytes()
        runner.journal_path.unlink()
        with self.assertRaises(ValueError):
            fixture.runner().run()
        self.assertEqual(len(fixture.transport.calls), 1)
        self.assertEqual(runner.intent_path.read_bytes(), intent)
