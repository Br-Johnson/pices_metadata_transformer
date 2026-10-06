"""Finite institutional wire types preserve source credits and legacy objects."""

import copy
import html
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_publication_qa as qa
from scripts import modern_singleton as mapping
from scripts.agent_qa import assess_source
from scripts.citation_creator_interpretation import source_element
from scripts.path_config import OutputPaths
from scripts.production_mutations import PROTECTED
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_exxon_coverage as exxon_tests
from tests import test_modern_organizational_coverage as organizational_tests
from tests.test_modern_publication import NOW as PUBLICATION_NOW
from tests.test_modern_publication_qa import raw_duplicates
from tests.test_modern_upload_compatibility import CompatibilityTransport

MAPPING_SHA = '19dd282e701bb115e256c90cac0ebaba0cfa1b49baf748dc4bf55106cc22dfd1'
REVIEW_SHA = '8cc6bd3a75de1e63b28b18f325a04d17333a356647804221d256a25d91f5b662'
BINDING_REVIEW_SHA = '0cdf17201243f9bdaeaca90c4ae1f46b573d0be9429359942a8b7eb89a73d633'
OLD_SOURCES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839', 'FGDC-1319')


class ModernInstitutionCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.INSTITUTION_MAPPING.read_bytes())
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.ids = [g['members'][0]['source_id'] for g in cls.manifest['groups']]
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=cls.ids + list(OLD_SOURCES))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, sid='FGDC-59'):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        return fixtures.Fixture(directory.name, self.prepared_root, source_id=sid)

    def test_all91_exact_original_origin_plan_and_independent_source_review(self):
        self.assertEqual(mapping.sha(mapping.INSTITUTION_MAPPING.read_bytes()), MAPPING_SHA)
        self.assertEqual(mapping.INSTITUTION_MAPPING_SHA, MAPPING_SHA)
        directory = mapping.INSTITUTION_MAPPING.parent
        raw = (directory / 'modern_institution91_source_review.json').read_bytes()
        self.assertEqual(mapping.sha(raw), REVIEW_SHA)
        review = mapping.parse(raw)
        self.assertEqual(self.manifest['review_sha256'], REVIEW_SHA)
        raw = (directory / 'modern_institution91_source_bindings.json').read_bytes()
        self.assertEqual(mapping.sha(raw), BINDING_REVIEW_SHA)
        self.assertEqual(self.manifest['binding_review_sha256'], BINDING_REVIEW_SHA)
        self.assertEqual(mapping.parse(raw)['mismatches'], [])
        selected = [g for g in review['groups'] if g['verdict'] == 'approve']
        targets = {r['record_target_id']: r for r in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        actual = []
        for group in self.manifest['groups']:
            source = next(g for g in selected if g['full_existing_creator_objects'] == group['creators'])
            self.assertEqual(group['members'], source['members'])
            self.assertEqual(group['modern_creators'], source['proposed_modern_creators'])
            self.assertEqual(len(group['creators']), 1)
            self.assertEqual(set(group['creators'][0]), {'name'})
            for member in group['members']:
                sid = member['source_id']
                with self.subTest(source=sid):
                    xml = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
                    self.assertEqual(mapping.sha(xml), member['source_sha256'])
                    nodes = ET.fromstring(xml).findall('./idinfo/citation/citeinfo/origin')
                    self.assertIn([source_element(node) for node in nodes], group['primary_origin_variants'])
                    target = targets[sid]
                    self.assertEqual(target['source_ids'], [sid])
                    self.assertEqual(target['source_sha256'], member['source_sha256'])
                    self.assertEqual(target['source_semantic_status'], 'supported')
                    self.assertIsNone(target['identity_decision']['production_record_id'])
                    self.assertIsNone(target['identity_decision']['production_doi'])
                actual.append(member)
        self.assertEqual(len(actual), 91)
        self.assertEqual(len({r['source_id'] for r in actual}), 91)
        self.assertEqual(sorted(actual, key=lambda r: int(r['source_id'][5:])), review['recommendation']['members'])

    def test_nine_groups_fresh_repeat_preserve_complete_legacy_names_dates_rights_and_xml(self):
        paths = OutputPaths(str(self.prepared_root), 'production')
        for group in self.manifest['groups']:
            sid = group['members'][0]['source_id']
            with self.subTest(source=sid):
                path = Path(paths.zenodo_json_dir) / (sid + '.json')
                before = path.read_bytes()
                prepared = mapping.prepare(path, paths)
                metadata, source_sha, artifact, _ = assess_source(path, paths)
                self.assertEqual(metadata['creators'], group['creators'])
                self.assertNotIn('creator_interpretation', mapping.parse(before)['artifact_policy'])
                wire = mapping.parse(prepared.body)
                self.assertEqual(wire['metadata']['creators'], group['modern_creators'])
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
                self.assertEqual(prepared.evidence['schema_version'], 6)
                self.assertEqual(prepared.evidence['policy'], mapping.INSTITUTION_POLICY)
                self.assertEqual(prepared.evidence['creator_profile_sha256'], MAPPING_SHA)
                self.assertEqual(prepared.evidence['mapping_manifest_sha256'], MAPPING_SHA)
                self.assertEqual(mapping.prepare(path, paths), prepared)
                self.assertEqual(path.read_bytes(), before)

    def test_withdrawn_or_modified_manifest_holds_new_sources_without_affecting_prior_policies(self):
        fixture = self.fixture()
        changed = self.root / 'changed.json'
        changed.write_bytes(mapping.INSTITUTION_MAPPING.read_bytes() + b' ')
        for path in (changed, self.root / 'missing.json'):
            with self.subTest(path=path.name), patch.object(mapping, 'INSTITUTION_MAPPING', path):
                with self.assertRaises((ValueError, OSError)):
                    mapping.prepare(fixture.json_file, fixture.paths)
                with self.assertRaises((ValueError, OSError)):
                    fixture.runner().run()
                for sid, version in zip(OLD_SOURCES, range(1, 6), strict=True):
                    self.assertEqual(self.fixture(sid).prepared.evidence['schema_version'], version)
        self.assertEqual(fixture.transport.calls, [])

    def test_historical79_split_into_exact42_reviewed_and37_retained_holds(self):
        review = mapping.parse((mapping.INSTITUTION_MAPPING.parent / 'modern_institution91_source_review.json').read_bytes())
        ids = [r['source_id'] for r in review['held']['members']]
        self.assertEqual(len(ids), 79)
        reviewed = {r['source_id'] for r in mapping.parse(mapping.REVIEWED_CREATORS_MAPPING.read_bytes())['rows']
                    if r['creator_authority_kind'] == 'direct'}
        self.assertEqual(len(set(ids) & reviewed), 42)
        held = set(ids) - reviewed
        self.assertEqual(len(held), 37)
        for sid in set(ids) & reviewed:
            self.assertEqual(mapping.institution_source_policy(sid)[1]['policy'], mapping.REVIEWED_CREATORS_POLICY)
        for sid in (*sorted(held), 'FGDC-2232', 'FGDC-182', 'FGDC-2953', 'FGDC-3181', *PROTECTED):
            with self.subTest(source=sid), self.assertRaises(ValueError):
                mapping.institution_source_policy(sid)

    def test_rehashed_manifest_cannot_change_origin_legacy_wire_or_selected_source_hash(self):
        fixture = self.fixture()
        changes = [lambda d: d['groups'][0]['members'].pop(),
                   lambda d: d['groups'][0]['members'][0].update(source_sha256='0' * 64),
                   lambda d: d['groups'][0]['creators'][0].update(type='Organization'),
                   lambda d: d['groups'][0]['primary_origin_variants'][0][0].update(text='CSIRO'),
                   lambda d: d['groups'][0]['primary_origin_variants'][0][0].update(attributes={'role': 'author'}),
                   lambda d: d['groups'][0]['modern_creators'][0]['person_or_org'].update(name='CSIRO'),
                   lambda d: d['groups'][0]['modern_creators'][0]['person_or_org'].update(type='personal'),
                   lambda d: d['groups'][0]['modern_creators'][0].update(affiliations=[{'name': 'CSIRO'}])]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                value = copy.deepcopy(self.manifest)
                change(value)
                path = self.root / 'changed.json'
                path.write_bytes(mapping.encode(value))
                with patch.object(mapping, 'INSTITUTION_MAPPING', path), \
                        patch.object(mapping, 'INSTITUTION_MAPPING_SHA', mapping.sha(path.read_bytes())):
                    with self.assertRaises(ValueError):
                        mapping.prepare(fixture.json_file, fixture.paths)
                    with self.assertRaises(ValueError):
                        fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])

    def test_input_cannot_gain_legacy_type_or_add_citation_interpretation_authority(self):
        fixture = self.fixture()
        original = fixture.json_file.read_bytes()
        for changed in ('creator', 'authority'):
            with self.subTest(change=changed):
                payload = mapping.parse(original)
                if changed == 'creator':
                    payload['metadata']['creators'][0]['type'] = 'Organization'
                else:
                    payload['artifact_policy']['creator_interpretation'] = {'manifest_sha256': MAPPING_SHA}
                fixture.json_file.write_bytes(mapping.encode(payload))
                with self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])

    def test_completed_upload_community_release_and_readonly_retry_keep_literal_credit(self):
        fixture = self.fixture('FGDC-4089')
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
        harness = organizational_tests.PublicationFixture(fixture)
        self.assertEqual([c[0] for c in fixture.transport.calls if c[0] != 'GET'], ['POST', 'POST', 'PUT'])
        documents = harness.ready()
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['release_complete'])
        self.assertTrue(result['community_membership_verified'])
        retry = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(retry['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual([c[0] for c in harness.transport.calls if c[0] != 'GET'], ['PUT', 'POST'])

    def test_pr41_five_old_policies_bridge_completed_upload_without_rewriting_history(self):
        for sid in OLD_SOURCES:
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
                harness = organizational_tests.PublicationFixture(fixture)
                retained = exxon_tests.save_historical_runtime(harness, publication.PR41_RUNTIME)
                original_calls = list(fixture.transport.calls)
                _, bound = harness.bridge()
                self.assertEqual(bound['original_runtime_sha256'], publication.PR41_RUNTIME)
                self.assertEqual(fixture.transport.calls, original_calls)
                self.assertEqual({path: path.read_bytes() for path in retained}, retained)

    def test_new_policy_cannot_claim_the_prior_runtime(self):
        harness = organizational_tests.PublicationFixture(self.fixture())
        exxon_tests.save_historical_runtime(harness, publication.PR41_RUNTIME)
        with self.assertRaises(ValueError):
            harness.bridge()

    def test_rehashed_qa_cannot_substitute_prior_policy_cohort_or_creator_authority(self):
        harness = organizational_tests.PublicationFixture(self.fixture())
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        original_duplicate = mapping.parse(documents['duplicate'].read_bytes())
        accepted = qa.assess(harness.prepared, harness.bound, snapshot, original_duplicate,
                             now=PUBLICATION_NOW, community=harness.community_authority)
        self.assertEqual(accepted['prepared_evidence'], harness.prepared.evidence)
        for key, value in (('schema_version', 5), ('policy', mapping.PICES_POLICY),
                           ('mapping_manifest_sha256', mapping.DIRECT_SHA), ('creator_cohort', 'pices_literal_26'),
                           ('creator_profile_sha256', mapping.PROFILE_SHA)):
            with self.subTest(field=key):
                evidence = copy.deepcopy(harness.prepared.evidence)
                evidence[key] = value
                prepared = replace(harness.prepared, evidence=evidence, binding=mapping.sha(mapping.encode(evidence)))
                bound = copy.deepcopy(harness.bound)
                bound['preparation_binding'] = prepared.binding
                bound['binding'] = mapping.sha(mapping.encode({k: v for k, v in bound.items() if k != 'binding'}))
                saved = copy.deepcopy(snapshot)
                saved['bridge_binding'] = bound['binding']
                duplicate = raw_duplicates(prepared, bridge=bound, snapshot=saved, now=PUBLICATION_NOW)
                with self.assertRaises(ValueError):
                    qa.assess(prepared, bound, saved, duplicate, now=PUBLICATION_NOW,
                              community=harness.community_authority)
        self.assertEqual(harness.transport.calls, [])
