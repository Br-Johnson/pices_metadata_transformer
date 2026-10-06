"""Reviewed institutional wire types preserve current source-profile attribution."""

import copy
import html
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_publication_qa as qa
from scripts import modern_singleton as mapping
from scripts.agent_qa import assess_source
from scripts.path_config import OutputPaths
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_exxon_coverage as exxon_tests
from tests import test_modern_organizational_coverage as organizational_tests
from tests.test_modern_publication import NOW as PUBLICATION_NOW
from tests.test_modern_publication_qa import raw_duplicates
from tests.test_modern_upload_compatibility import CompatibilityTransport

OLD_SOURCES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839', 'FGDC-1319', 'FGDC-59')


class ModernCitationOrganizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.CITATION_ORG_MAPPING.read_bytes())
        cls.review = mapping.parse(mapping.CITATION_ORG_REVIEW.read_bytes())
        members = [m for g in cls.manifest['groups'] for m in g['members']]
        largest = max(members, key=lambda m: (mapping.ROOT / 'FGDC' / (m['source_id'] + '.xml')).stat().st_size)
        ids = list(dict.fromkeys(['FGDC-3875', 'FGDC-3951', 'FGDC-2552', 'FGDC-3781',
                                 'FGDC-3782', 'FGDC-3784', 'FGDC-4044', 'FGDC-706',
                                 'FGDC-743', largest['source_id']]))
        for group in sorted(cls.manifest['groups'], key=lambda g: -len(g['creators'])):
            if len(ids) == 10:
                break
            sid = group['members'][0]['source_id']
            if sid not in ids:
                ids.append(sid)
            if len(ids) == 10:
                break
        cls.ids = ids
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=ids)
        cls.old_sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.old_sources.cleanup)
        cls.old_prepared = fixtures.prepare_sources(cls.old_sources.name, ids=list(OLD_SOURCES))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, sid='FGDC-3875'):
        temporary = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(temporary.cleanup)
        return fixtures.Fixture(temporary.name, self.old_prepared if sid in OLD_SOURCES else self.prepared_root,
                                source_id=sid)

    def test_exact129_current_profile_originals_plan_and_independent_membership(self):
        self.assertEqual(len(self.ids), 10)
        self.assertEqual(mapping.sha(mapping.CITATION_ORG_MAPPING.read_bytes()), mapping.CITATION_ORG_MAPPING_SHA)
        self.assertEqual(mapping.sha(mapping.CITATION_ORG_REVIEW.read_bytes()), mapping.CITATION_ORG_REVIEW_SHA)
        source = mapping.pinned(mapping.CITATION_ORG_SOURCE, mapping.CITATION_ORG_SOURCE_SHA)
        self.assertEqual(source['members'], self.review['approved_members'])
        self.assertEqual(len(source['selected_historical_creator_mismatches']), 12)
        profiles = {r['profile']: r for r in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']}
        targets = {r['record_target_id']: r for r in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        selected = []
        for group in self.manifest['groups']:
            self.assertEqual(group['modern_creators'], [
                {'person_or_org': {'name': c['name'], 'type': 'organizational'}} for c in group['creators']])
            self.assertTrue(all(set(c) == {'name'} for c in group['creators']))
            for member in group['members']:
                sid = member['source_id']
                with self.subTest(source=sid):
                    original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
                    self.assertEqual(mapping.sha(original), member['source_sha256'])
                    profile = profiles[member['creator_cohort']]
                    self.assertEqual(mapping.sha(mapping.encode(profile)), member['cohort_object_sha256'])
                    self.assertEqual(profile['creators'], group['creators'])
                    policy_group, fields = mapping.citation_organization_source_policy(sid)
                    self.assertEqual(policy_group, group)
                    self.assertEqual(fields, {'schema_version': 7, 'policy': mapping.CITATION_ORG_POLICY,
                                             'mapping_manifest_sha256': mapping.CITATION_ORG_MAPPING_SHA,
                                             'creator_cohort': member['creator_cohort']})
                    target = targets[sid]
                    self.assertEqual(target['source_ids'], [sid])
                    self.assertEqual(target['source_semantic_status'], 'supported')
                    self.assertEqual(target['source_sha256'], member['source_sha256'])
                    self.assertIsNone(target['identity_decision']['production_record_id'])
                    self.assertIsNone(target['identity_decision']['production_doi'])
                selected.append({'source_id': sid, 'source_sha256': member['source_sha256']})
        self.assertEqual(len(self.manifest['groups']), 53)
        self.assertEqual(sorted(selected, key=lambda r: int(r['source_id'][5:])), self.review['approved_members'])
        self.assertEqual(len({r['source_id'] for r in selected}), 129)

    def test_ten_fresh_samples_preserve_complete_metadata_current_credits_rights_dates_and_xml(self):
        paths = OutputPaths(str(self.prepared_root), 'production')
        for sid in self.ids:
            with self.subTest(source=sid):
                path = Path(paths.zenodo_json_dir) / (sid + '.json')
                original = path.read_bytes()
                prepared = mapping.prepare(path, paths)
                self.assertEqual(prepared, mapping.prepare(path, paths))
                metadata, source_sha, artifact, _ = assess_source(path, paths)
                selected, _ = mapping.source_policy(sid)
                self.assertEqual(metadata['creators'], selected['creators'])
                self.assertEqual(prepared.evidence['creator_profile_sha256'], mapping.PROFILE_SHA)
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(prepared.evidence['source_sha256'], source_sha)
                self.assertEqual(prepared.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                wire = mapping.parse(prepared.body)
                self.assertEqual(wire['metadata']['creators'], selected['modern_creators'])
                if sid in ('FGDC-706', 'FGDC-743'):
                    self.assertEqual(metadata['creators'], [{'name': name} for name in
                                     ('Ecotrust', 'Pacific GIS', 'Conservation International')])
                    self.assertEqual(len(wire['metadata']['creators']), 3)
                block = wire['metadata']['additional_descriptions'][0]['description']
                self.assertEqual(mapping.parse(html.unescape(block.split('<pre>', 1)[1][:-6]).encode()), metadata)
                for field in ('title', 'publication_date', 'description'):
                    self.assertEqual(wire['metadata'][field], metadata[field])
                self.assertEqual(wire['metadata']['subjects'], [{'subject': k} for k in metadata['keywords']])
                self.assertEqual((metadata['access_right'], metadata['license']), ('restricted', ''))
                self.assertEqual(path.read_bytes(), original)

    def test_withdrawn_finite_manifest_or_reviews_leave_all_six_prior_policies_available(self):
        fixture = self.fixture()
        for attr in ('CITATION_ORG_MAPPING', 'CITATION_ORG_REVIEW', 'CITATION_ORG_SOURCE'):
            with self.subTest(authority=attr), patch.object(mapping, attr, self.root / 'missing.json'):
                with self.assertRaises((ValueError, OSError)):
                    mapping.prepare(fixture.json_file, fixture.paths)
                with self.assertRaises((ValueError, OSError)):
                    fixture.runner().run()
                for sid, version in zip(OLD_SOURCES, range(1, 7), strict=True):
                    self.assertEqual(self.fixture(sid).prepared.evidence['schema_version'], version)
            self.assertEqual(fixture.transport.calls, [])

    def test_historical160_split_into_reviewed82_program20_and58_retained_holds(self):
        outside = self.review['outside_scope_creator426_source_ids']
        self.assertEqual(len(outside), 160)
        reviewed = {r['source_id'] for r in mapping.parse(mapping.REVIEWED_CREATORS_MAPPING.read_bytes())['rows']
                    if r['creator_authority_kind'] == 'creator426'}
        self.assertEqual(len(set(outside) & reviewed), 82)
        program = {r['source_id'] for r in mapping.parse(mapping.PROGRAM20.read_bytes())['rows']}
        self.assertEqual(len(set(outside) & program), 20)
        self.assertFalse(reviewed & program)
        held = set(outside) - reviewed - program
        self.assertEqual(len(held), 58)
        for sid in [*sorted(set(outside) & reviewed), 'FGDC-4078']:
            self.assertEqual(mapping.citation_organization_source_policy(sid)[1]['policy'], mapping.REVIEWED_CREATORS_POLICY)
        for sid in sorted(program):
            self.assertEqual(mapping.citation_organization_source_policy(sid)[1]['policy'], mapping.PROGRAM_POLICY)
        for sid in [*sorted(held), 'FGDC-710', 'FGDC-859', 'FGDC-2953', 'FGDC-3181', *mapping.PROTECTED]:
            with self.subTest(source=sid), self.assertRaises(ValueError):
                mapping.citation_organization_source_policy(sid)

    def test_self_rehashed_mapping_cannot_change_finite_membership_credit_order_or_projection(self):
        fixture = self.fixture()
        for mutate in (
                lambda m: m['groups'].pop(),
                lambda m: m['groups'][0]['members'].pop(),
                lambda m: m['groups'][0]['members'][0].update(source_sha256='0' * 64),
                lambda m: m['groups'][0]['members'][0].update(source_id='FGDC-2232'),
                lambda m: m['groups'][0]['members'][0].update(creator_cohort='pices_literal_26'),
                lambda m: m['groups'][0]['members'][0].update(cohort_object_sha256='0' * 64),
                lambda m: m['groups'][0]['creators'][0].update(type='Organization'),
                lambda m: m['groups'][0]['modern_creators'][0]['person_or_org'].update(name='Invented'),
                lambda m: m['groups'][0]['modern_creators'][0]['person_or_org'].update(type='personal'),
                lambda m: m['groups'][0]['modern_creators'][0].update(affiliations=[{'name': 'Invented'}])):
            value = copy.deepcopy(self.manifest)
            mutate(value)
            changed = self.root / 'changed.json'
            changed.write_bytes(mapping.encode(value))
            with patch.object(mapping, 'CITATION_ORG_MAPPING', changed), \
                    patch.object(mapping, 'CITATION_ORG_MAPPING_SHA', mapping.sha(changed.read_bytes())):
                with self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)
                with self.assertRaises(ValueError):
                    fixture.runner().run()
            self.assertEqual(fixture.transport.calls, [])

    def test_stale_or_typed_legacy_payload_and_changed_profile_binding_hold(self):
        fixture = self.fixture('FGDC-3951')
        original = fixture.json_file.read_bytes()
        for mutate in (
                lambda p: p['metadata']['creators'][0].update(name='Contact-only person'),
                lambda p: p['metadata']['creators'][0].update(type='Organization'),
                lambda p: p['artifact_policy']['creator_interpretation'].update(manifest_sha256='0' * 64),
                lambda p: p['artifact_policy'].pop('creator_interpretation')):
            value = mapping.parse(original)
            mutate(value)
            fixture.json_file.write_bytes(mapping.encode(value))
            with self.assertRaises(ValueError):
                mapping.prepare(fixture.json_file, fixture.paths)
            with self.assertRaises(ValueError):
                fixture.runner().run()
        self.assertEqual(fixture.transport.calls, [])

    def test_completed_upload_community_qa_release_and_retry_keep_exact_multiple_credits(self):
        fixture = self.fixture('FGDC-4044')
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
        harness = organizational_tests.PublicationFixture(fixture)
        documents = harness.ready()
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['release_complete'])
        self.assertTrue(result['community_membership_verified'])
        retry = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(retry['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual([c[0] for c in fixture.transport.calls if c[0] != 'GET'], ['POST', 'POST', 'PUT'])
        self.assertEqual([c[0] for c in harness.transport.calls if c[0] != 'GET'], ['PUT', 'POST'])

    def test_pr45_old_six_policy_history_bridges_and_new_policy_cannot_backdate(self):
        for sid in OLD_SOURCES:
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
                harness = organizational_tests.PublicationFixture(fixture)
                retained = exxon_tests.save_historical_runtime(harness, publication.PR45_RUNTIME)
                calls = list(fixture.transport.calls)
                _, bound = harness.bridge()
                self.assertEqual(bound['original_runtime_sha256'], publication.PR45_RUNTIME)
                self.assertEqual(fixture.transport.calls, calls)
                self.assertEqual({p: p.read_bytes() for p in retained}, retained)
        harness = organizational_tests.PublicationFixture(self.fixture())
        exxon_tests.save_historical_runtime(harness, publication.PR45_RUNTIME)
        with self.assertRaises(ValueError):
            harness.bridge()

    def test_fully_rebound_qa_rejects_wrong_policy_cohort_mapping_and_creator_authority(self):
        harness = organizational_tests.PublicationFixture(self.fixture())
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        duplicate = mapping.parse(documents['duplicate'].read_bytes())
        self.assertEqual(qa.assess(harness.prepared, harness.bound, snapshot, duplicate,
                                  now=PUBLICATION_NOW, community=harness.community_authority)['prepared_evidence'],
                         harness.prepared.evidence)
        for key, value in (('schema_version', 6), ('policy', mapping.INSTITUTION_POLICY),
                           ('mapping_manifest_sha256', mapping.INSTITUTION_MAPPING_SHA),
                           ('creator_cohort', 'pices_literal_26'), ('creator_profile_sha256', mapping.EXXON_SHA)):
            with self.subTest(field=key):
                evidence = copy.deepcopy(harness.prepared.evidence)
                evidence[key] = value
                prepared = replace(harness.prepared, evidence=evidence, binding=mapping.sha(mapping.encode(evidence)))
                bound = copy.deepcopy(harness.bound)
                bound['preparation_binding'] = prepared.binding
                bound['binding'] = mapping.sha(mapping.encode({k: v for k, v in bound.items() if k != 'binding'}))
                saved = copy.deepcopy(snapshot)
                saved['bridge_binding'] = bound['binding']
                changed = raw_duplicates(prepared, bridge=bound, snapshot=saved, now=PUBLICATION_NOW)
                with self.assertRaises(ValueError):
                    qa.assess(prepared, bound, saved, changed, now=PUBLICATION_NOW,
                              community=harness.community_authority)


if __name__ == '__main__':
    unittest.main()
