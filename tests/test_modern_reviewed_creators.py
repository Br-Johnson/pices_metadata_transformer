"""Finite194 creator authority, original preservation and offline execution.

All members are checked against retained source/review objects and original XML.
Only ten new sources and seven prior-policy representatives are freshly prepared.
All execution uses synthetic transports; no fixture confers provider authority.
"""

import copy
import html
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_publication_qa as qa
from scripts import modern_singleton as mapping
from scripts import modern_singleton_executor as draft
from scripts.agent_qa import assess_source
from scripts.citation_creator_interpretation import source_element
from scripts.path_config import OutputPaths
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_exxon_coverage as exxon_tests
from tests.test_modern_organizational_coverage import PublicationFixture
from tests.test_modern_publication import NOW as PUBLICATION_NOW
from tests.test_modern_publication_qa import raw_duplicates
from tests.test_modern_upload_compatibility import CompatibilityTransport

MAPPING_SHA = 'c7d0b522bf7e9a9c990b6cbdf93797280ff1e57979e6bd133186905c4deec6c3'
SOURCE_SHA = '1dbb3af3945a0993e705e56a94b307cb02ca444451a98ef8e36ade366eddaad1'
REVIEW_SHA = '20c585d143cc0a295bdbbce54b2e3fa5bace5846802534b2f7bf40bb3f04b271'
NEW_SOURCES = ('FGDC-1', 'FGDC-10', 'FGDC-1314', 'FGDC-540', 'FGDC-907',
               'FGDC-2602', 'FGDC-3593', 'FGDC-2664', 'FGDC-4078', 'FGDC-4084')
OLD_SOURCES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839',
               'FGDC-1319', 'FGDC-59', 'FGDC-3875')
# Exact obsolete vectors from the historical payloads identified in the source
# packet. CI uses these literals; it never reads the historical workspace paths.
STALE_CREATORS = {
    'FGDC-10': [{'name': '83 Havelock St.'}],
    'FGDC-1314': [{'name': 'Journal Ontogenesis Vol 28, No 1, 1997, Russian Journal of Developmental Biology'}],
}


class ModernReviewedCreatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.REVIEWED_CREATORS_MAPPING.read_bytes())
        cls.source = mapping.parse(mapping.REVIEWED_CREATORS_SOURCE.read_bytes())
        cls.review = mapping.parse(mapping.REVIEWED_CREATORS_REVIEW.read_bytes())
        cls.rows = {row['source_id']: row for row in cls.manifest['rows']}
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=list(NEW_SOURCES))
        cls.old_sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.old_sources.cleanup)
        cls.old_prepared = fixtures.prepare_sources(cls.old_sources.name, ids=list(OLD_SOURCES))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        no_wire = patch.object(draft, 'Transport', side_effect=AssertionError('Real transport forbidden'))
        no_wire.start()
        self.addCleanup(no_wire.stop)

    def fixture(self, sid='FGDC-1'):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        prepared_root = self.old_prepared if sid in OLD_SOURCES else self.prepared_root
        return fixtures.Fixture(directory.name, prepared_root, source_id=sid)

    def test_all194_original_roots_complete_vectors_authorities_and_plan_match_independent_review(self):
        for path, actual, expected in (
                (mapping.REVIEWED_CREATORS_MAPPING, mapping.REVIEWED_CREATORS_MAPPING_SHA, MAPPING_SHA),
                (mapping.REVIEWED_CREATORS_SOURCE, mapping.REVIEWED_CREATORS_SOURCE_SHA, SOURCE_SHA),
                (mapping.REVIEWED_CREATORS_REVIEW, mapping.REVIEWED_CREATORS_REVIEW_SHA, REVIEW_SHA)):
            self.assertEqual(actual, expected)
            self.assertEqual(mapping.sha(path.read_bytes()), expected)
        rows = self.manifest['rows']
        self.assertEqual(len(rows), 194)
        self.assertEqual(len(self.rows), 194)
        self.assertEqual(Counter(row['creator_authority_kind'] for row in rows),
                         {'creator426': 82, 'direct': 42, 'dfo70': 70})
        self.assertEqual(self.manifest['authority_counts'], {'creator426': 82, 'direct': 42, 'dfo70': 70})
        self.assertEqual(self.manifest['source_packet_sha256'], SOURCE_SHA)
        self.assertEqual(self.manifest['independent_review_sha256'], REVIEW_SHA)
        self.assertEqual(self.manifest['source_plan_sha256'], mapping.PLAN_SHA)
        self.assertEqual(self.review['verdict'], 'APPROVE_EXACT194_COMPOSITION_RETAIN29_HOLDS_SOURCE_ONLY')
        members = [{'source_id': row['source_id'], 'source_sha256': row['source_sha256']} for row in rows]
        self.assertEqual(members, self.source['members'])
        self.assertEqual(members, self.review['approved_members'])
        self.assertEqual(mapping.sha(mapping.encode(members)), self.review['approved_membership_sha256'])
        self.assertEqual(mapping.sha(mapping.encode(self.source['source_rows'])),
                         self.review['approved_source_rows_sha256'])
        sources = {row['source_id']: row for row in self.source['source_rows']}
        self.assertEqual(len(sources), 194)
        self.assertEqual(set(sources), set(self.rows))
        targets = {row['record_target_id']: row for row in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        profiles = {row['profile']: row for row in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']}
        dfo = mapping.pinned(mapping.DFO_PROFILE, mapping.DFO_PROFILE_SHA)
        for row in rows:
            sid = row['source_id']
            with self.subTest(source=sid):
                source = sources[sid]
                original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
                root = ET.fromstring(original)
                self.assertEqual(len(original), source['source_bytes'])
                self.assertEqual(mapping.sha(original), row['source_sha256'])
                self.assertEqual(mapping.sha(mapping.encode(source_element(root))), row['source_root_sha256'])
                self.assertEqual(row['source_root_sha256'], source['source_root_sha256'])
                self.assertEqual([source_element(node) for node in root.findall('./idinfo/citation/citeinfo/origin')],
                                 row['primary_origins'])
                self.assertEqual(row['primary_origins'], source['original_primary_origin_elements'])
                for xpath, digest in source['raw_source_constraint_and_date_element_sha256'].items():
                    self.assertEqual(mapping.sha(mapping.encode([source_element(node) for node in root.findall(xpath)])),
                                     digest, xpath)
                self.assertEqual(row['creators'], source['complete_legacy_creators'])
                self.assertEqual(mapping.sha(mapping.encode(row['creators'])), source['complete_legacy_creators_sha256'])
                self.assertEqual(row['modern_creators'], source['proposed_modern_creators'])
                self.assertEqual(mapping.sha(mapping.encode(row['modern_creators'])), source['proposed_modern_creators_sha256'])
                self.assertEqual(row['approval_partition'], source['approval_partition'])
                target = targets[sid]
                self.assertEqual(mapping.sha(mapping.encode(target)), row['source_plan_target_sha256'])
                self.assertEqual(row['source_plan_target_sha256'], source['current_source_plan_target']['object_sha256'])
                self.assertEqual(target['source_ids'], [sid])
                self.assertEqual(target['source_semantic_status'], 'supported')
                self.assertEqual(target['source_sha256'], row['source_sha256'])
                self.assertIsNone(target['identity_decision']['production_record_id'])
                self.assertIsNone(target['identity_decision']['production_doi'])
                self.assertNotIn(sid, mapping.PROTECTED)
                authority = source['current_creator_authority']
                if row['creator_authority_kind'] == 'direct':
                    self.assertEqual(authority['kind'],
                                     'existing_default_primary_citation_legacy_route_no_creator426_or_dfo_profile')
                    self.assertIsNone(row['creator_cohort'])
                    self.assertIsNone(row['creator_authority_object_sha256'])
                else:
                    expected_kind = ('existing_creator426_cohort' if row['creator_authority_kind'] == 'creator426'
                                     else 'existing_dfo_literal_collective_profile')
                    self.assertEqual(authority['kind'], expected_kind)
                    profile = profiles[row['creator_cohort']] if row['creator_authority_kind'] == 'creator426' else dfo
                    self.assertEqual(profile['creators'], row['creators'])
                    self.assertEqual(profile['profile'], row['creator_cohort'])
                    self.assertIn({'source_id': sid, 'source_sha256': row['source_sha256']}, profile['members'])
                    self.assertEqual(mapping.sha(mapping.encode(profile)), row['creator_authority_object_sha256'])
                    self.assertEqual(authority['reference']['object_sha256'], row['creator_authority_object_sha256'])

    def test_reviewed_cardinality_changes_and_affiliations_are_preserved_without_universal_name_rules(self):
        direct = [row for row in self.rows.values() if row['creator_authority_kind'] == 'direct']
        cardinality = {row['source_id'] for row in direct if len(row['creators']) != len(row['modern_creators'])}
        affiliated = {row['source_id'] for row in direct if any(c.get('affiliations') for c in row['modern_creators'])}
        self.assertEqual(len(cardinality), 15)
        self.assertEqual(cardinality, set(self.review['direct42_cardinality_change_sources']))
        self.assertEqual(len(affiliated), 22)
        self.assertEqual(affiliated, set(self.review['direct42_affiliation_sources']))
        self.assertEqual(Counter(c['person_or_org']['type'] for row in self.rows.values() for c in row['modern_creators']),
                         {'organizational': 109, 'personal': 250})
        self.assertEqual(len(self.rows['FGDC-540']['creators']), 1)
        self.assertEqual(self.rows['FGDC-540']['modern_creators'], [
            {'person_or_org': {'name': 'Alaska Native Science Commission', 'type': 'organizational'}},
            {'person_or_org': {'name': 'UAA: Institute for Social & Economic Research', 'type': 'organizational'}}])
        vector = self.rows['FGDC-2602']['modern_creators']
        self.assertEqual(len(vector), 3)
        self.assertEqual(vector[0]['affiliations'], [{'name': 'University Research Institute, Reykjavik'}])
        self.assertNotIn('affiliations', vector[1])
        self.assertNotIn('affiliations', vector[2])
        for row in self.rows.values():
            if row['creator_authority_kind'] == 'dfo70':
                self.assertEqual(row['creators'], [{'name': 'DFO Staff'}])
                self.assertEqual(row['modern_creators'], [
                    {'person_or_org': {'name': 'DFO Staff', 'type': 'organizational'}}])

    def test_ten_fresh_preparations_repeat_exactly_and_preserve_metadata_xml_rights_dates_and_authority(self):
        paths = OutputPaths(str(self.prepared_root), 'production')
        authority = {'creator426': mapping.PROFILE_SHA, 'direct': MAPPING_SHA, 'dfo70': mapping.DFO_PROFILE_SHA}
        self.assertEqual(len(NEW_SOURCES), 10)
        for sid in NEW_SOURCES:
            with self.subTest(source=sid):
                path = Path(paths.zenodo_json_dir) / (sid + '.json')
                original_input = path.read_bytes()
                prepared = mapping.prepare(path, paths)
                self.assertEqual(prepared, mapping.prepare(path, paths))
                metadata, source_sha, artifact, _ = assess_source(path, paths)
                row = self.rows[sid]
                expected_authority = authority[row['creator_authority_kind']]
                self.assertEqual(metadata['creators'], row['creators'])
                self.assertEqual(prepared.evidence['creator_profile_sha256'], expected_authority)
                self.assertEqual(prepared.evidence['creator_authority_kind'], row['creator_authority_kind'])
                self.assertEqual(prepared.evidence['creator_cohort'], row['creator_cohort'])
                self.assertEqual(prepared.evidence['schema_version'], 8)
                self.assertEqual(prepared.evidence['policy'], mapping.REVIEWED_CREATORS_POLICY)
                self.assertEqual(prepared.evidence['mapping_manifest_sha256'], MAPPING_SHA)
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(prepared.evidence['source_sha256'], source_sha)
                self.assertEqual(prepared.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                wire = mapping.parse(prepared.body)
                self.assertEqual(wire['metadata']['creators'], row['modern_creators'])
                block = wire['metadata']['additional_descriptions'][0]['description']
                self.assertTrue(block.startswith('<p>' + mapping.PRESERVATION_LABEL + '</p><pre>'))
                self.assertEqual(mapping.parse(html.unescape(block.split('<pre>', 1)[1][:-6]).encode()), metadata)
                for field in ('title', 'publication_date', 'description'):
                    self.assertEqual(wire['metadata'][field], metadata[field])
                self.assertEqual(wire['metadata']['subjects'], [{'subject': item} for item in metadata.get('keywords', [])])
                self.assertEqual(wire['access'], {'record': 'public', 'files': 'restricted'})
                self.assertEqual((metadata['access_right'], metadata['license']), ('restricted', ''))
                self.assertNotIn('rights', wire['metadata'])
                self.assertNotIn('license', wire['metadata'])
                self.assertEqual(prepared.evidence['legacy_metadata_sha256'], mapping.sha(mapping.encode(metadata)))
                self.assertEqual(prepared.evidence['prepared_input_sha256'], mapping.sha(original_input))
                self.assertEqual(prepared.evidence['wire_sha256'], mapping.sha(prepared.body))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))
                policy = mapping.parse(original_input)['artifact_policy']
                if row['creator_authority_kind'] == 'direct':
                    self.assertNotIn('creator_interpretation', policy)
                else:
                    self.assertEqual(policy['creator_interpretation']['manifest_sha256'], expected_authority)
                self.assertEqual(path.read_bytes(), original_input)

    def test_withdrawn194_mapping_source_or_review_holds_new_sources_and_keeps_all_seven_prior_policies(self):
        fixture = self.fixture()
        old = {sid: mapping.source_policy(sid) for sid in OLD_SOURCES}
        for attribute in ('REVIEWED_CREATORS_MAPPING', 'REVIEWED_CREATORS_SOURCE', 'REVIEWED_CREATORS_REVIEW'):
            with self.subTest(authority=attribute), patch.object(mapping, attribute, self.root / 'missing.json'):
                with self.assertRaises((ValueError, OSError)):
                    mapping.prepare(fixture.json_file, fixture.paths)
                with self.assertRaises((ValueError, OSError)):
                    fixture.runner().run()
                for sid, version in zip(OLD_SOURCES, range(1, 8), strict=True):
                    self.assertEqual(mapping.source_policy(sid), old[sid])
                    self.assertEqual(old[sid][1]['schema_version'], version)
            self.assertEqual(fixture.transport.calls, [])
            self.assertFalse((draft.state_root(fixture.paths) / 'FGDC-1.modern-create-v1.intent.json').exists())

    def test_personal29_holds_pairs_protected_and_other_policies_never_enter194(self):
        held = self.review['preserved_held_members']
        self.assertEqual(len(held), 29)
        self.assertEqual(mapping.sha(mapping.encode(held)), self.review['preserved_held_membership_sha256'])
        held_ids = {row['source_id'] for row in held}
        self.assertTrue(held_ids.isdisjoint(self.rows))
        excluded = held_ids | {'FGDC-2953', 'FGDC-3181', *OLD_SOURCES, *mapping.PROTECTED}
        for sid in sorted(excluded):
            with self.subTest(source=sid), self.assertRaises(ValueError):
                mapping.reviewed_creator_source_policy(sid)

    def test_self_rehashed_manifest_cannot_change_membership_authority_roots_or_reviewed_vectors(self):
        fixture = self.fixture()
        for label, mutate in (
                ('missing member', lambda m: m['rows'].pop()),
                ('different source', lambda m: m['rows'][0].update(source_id='FGDC-542')),
                ('source hash', lambda m: m['rows'][0].update(source_sha256='0' * 64)),
                ('whole XML root', lambda m: m['rows'][0].update(source_root_sha256='0' * 64)),
                ('primary origin', lambda m: m['rows'][0]['primary_origins'][0].update(text='Invented')),
                ('source target', lambda m: m['rows'][0].update(source_plan_target_sha256='0' * 64)),
                ('authority kind', lambda m: m['rows'][0].update(creator_authority_kind='direct')),
                ('creator cohort', lambda m: m['rows'][0].update(creator_cohort='pices_literal_26')),
                ('creator authority', lambda m: m['rows'][0].update(creator_authority_object_sha256='0' * 64)),
                ('full legacy array', lambda m: m['rows'][0]['creators'].reverse()),
                ('modern order', lambda m: m['rows'][0]['modern_creators'].reverse()),
                ('personal initials', lambda m: m['rows'][0]['modern_creators'][0]['person_or_org'].update(given_name='S.')),
                ('invented affiliation', lambda m: m['rows'][0]['modern_creators'][0].update(affiliations=[{'name': 'Invented'}]))):
            with self.subTest(change=label):
                value = copy.deepcopy(self.manifest)
                mutate(value)
                changed = self.root / 'changed194.json'
                changed.write_bytes(mapping.encode(value))
                with patch.object(mapping, 'REVIEWED_CREATORS_MAPPING', changed), \
                        patch.object(mapping, 'REVIEWED_CREATORS_MAPPING_SHA', mapping.sha(changed.read_bytes())):
                    with self.assertRaises(ValueError):
                        mapping.prepare(fixture.json_file, fixture.paths)
                    with self.assertRaises(ValueError):
                        fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])

    def test_stale_historical_creator_vectors_cannot_replace_current_fgdc10_or1314_credits(self):
        for sid, stale in STALE_CREATORS.items():
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                original = mapping.parse(fixture.json_file.read_bytes())
                self.assertEqual(original['metadata']['creators'], self.rows[sid]['creators'])
                self.assertNotEqual(original['metadata']['creators'], stale)
                changed = copy.deepcopy(original)
                changed['metadata']['creators'] = stale
                # Keep the currently pinned creator reference: rejection must
                # still compare the full current source-derived creator array.
                self.assertEqual(changed['artifact_policy'], original['artifact_policy'])
                fixture.json_file.write_bytes(mapping.encode(changed))
                with self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])
                self.assertFalse((draft.state_root(fixture.paths) / (sid + '.modern-create-v1.intent.json')).exists())

    def test_source_authority_references_cannot_cross_categories_or_appear_on_direct_sources(self):
        for sid in ('FGDC-1', 'FGDC-540', 'FGDC-4078'):
            fixture = self.fixture(sid)
            original = mapping.parse(fixture.json_file.read_bytes())
            kind = self.rows[sid]['creator_authority_kind']
            wrong = {'manifest_path': 'docs/readiness/2026-10-04/source_citation_credits_426.json',
                     'manifest_sha256': mapping.PROFILE_SHA if kind != 'creator426' else mapping.DFO_PROFILE_SHA}
            for reference in (None, wrong):
                with self.subTest(source=sid, reference=reference):
                    changed = copy.deepcopy(original)
                    changed['artifact_policy']['creator_interpretation'] = reference
                    fixture.json_file.write_bytes(mapping.encode(changed))
                    with self.assertRaises(ValueError):
                        mapping.prepare(fixture.json_file, fixture.paths)
                    with self.assertRaises(ValueError):
                        fixture.runner().run()
                    self.assertEqual(fixture.transport.calls, [])

    def test_direct_affiliation_and_cardinality_flow_passes_community_qa_release_readback_and_retry(self):
        fixture = self.fixture('FGDC-2602')
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
        harness = PublicationFixture(fixture)
        draft_journal = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
        draft_before = draft_journal.read_bytes()
        row = mapping.parse(draft_before)['targets']['FGDC-2602']
        self.assertEqual(row['counts'], {'get': 5, 'create': 1, 'init': 1, 'content': 1, 'commit': 0})
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        duplicate = mapping.parse(documents['duplicate'].read_bytes())
        evidence = qa.assess(harness.prepared, harness.bound, snapshot, duplicate, now=PUBLICATION_NOW,
                             community=harness.community_authority)
        self.assertEqual(evidence['prepared_evidence'], harness.prepared.evidence)
        self.assertEqual(harness.prepared.evidence['creator_profile_sha256'], MAPPING_SHA)
        first = harness.runner(documents=documents).run()
        self.assertTrue(first['release_complete'])
        self.assertTrue(first['community_membership_verified'])
        self.assertEqual(first['counts'], {'get': 16, 'review': 1, 'submit': 1})
        draft_calls = list(fixture.transport.calls)
        draft_writes = [call for call in draft_calls if call[0] != 'GET']
        publication_writes = [call for call in harness.transport.calls if call[0] != 'GET']
        retry = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(retry['counts'], publication.PUBLISH_LIMITS)
        self.assertTrue(retry['release_complete'])
        # The publication fake forwards its five record/file GETs to the inner
        # transport; the sixth request GET is handled by the publication fake.
        self.assertEqual(len(fixture.transport.calls) - len(draft_calls), 5)
        self.assertTrue(all(call[0] == 'GET' for call in fixture.transport.calls[len(draft_calls):]))
        self.assertEqual([call for call in fixture.transport.calls if call[0] != 'GET'], draft_writes)
        self.assertEqual([call for call in harness.transport.calls if call[0] != 'GET'], publication_writes)
        self.assertEqual(draft_journal.read_bytes(), draft_before)
        self.assertEqual([call[0] for call in draft_writes], ['POST', 'POST', 'PUT'])
        self.assertEqual([call[0] for call in publication_writes], ['PUT', 'POST'])

    def test_fully_rebound_qa_cannot_swap_authority_category_cohort_or_mapping_for_any_category(self):
        for sid in ('FGDC-1', 'FGDC-540', 'FGDC-4078'):
            harness = PublicationFixture(self.fixture(sid))
            documents = harness.ready()
            snapshot = mapping.parse(documents['snapshot'].read_bytes())
            duplicate = mapping.parse(documents['duplicate'].read_bytes())
            baseline = qa.assess(harness.prepared, harness.bound, snapshot, duplicate,
                                 now=PUBLICATION_NOW, community=harness.community_authority)
            self.assertEqual(baseline['prepared_evidence'], harness.prepared.evidence)
            original = harness.prepared.evidence
            wrong_kind = 'direct' if original['creator_authority_kind'] != 'direct' else 'creator426'
            wrong_authority = mapping.PROFILE_SHA if original['creator_profile_sha256'] != mapping.PROFILE_SHA else mapping.DFO_PROFILE_SHA
            for key, value in (('creator_authority_kind', wrong_kind), ('creator_profile_sha256', wrong_authority),
                               ('creator_cohort', 'pices_literal_26'), ('mapping_manifest_sha256', mapping.CITATION_ORG_MAPPING_SHA),
                               ('schema_version', 7), ('policy', mapping.CITATION_ORG_POLICY)):
                with self.subTest(source=sid, field=key):
                    evidence = copy.deepcopy(original)
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

    def test_historical_runtimes_bridge_then_existing_policies_without_state_or_dispatch_changes(self):
        cases = [(sid, version, publication.PR46_RUNTIME)
                 for sid, version in zip(OLD_SOURCES, range(1, 8), strict=True)]
        cases.append(('FGDC-1', 8, publication.REVIEWED194_RUNTIME))
        for sid, version, historical_runtime in cases:
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
                harness = PublicationFixture(fixture)
                self.assertEqual(harness.prepared.evidence['schema_version'], version)
                previous_grant_sha = mapping.sha(fixture.grant_path.read_bytes())
                exxon_tests.save_historical_runtime(harness, historical_runtime)
                # Finish generating the synthetic historical graph before any
                # preservation snapshot. Keep every original diagnostic and
                # bind a new exclusive sidecar to the rebound historical grant.
                journal_path = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
                journal = mapping.parse(journal_path.read_bytes())
                row = journal['targets'][sid]
                grant_sha = mapping.sha(fixture.grant_path.read_bytes())
                self.assertNotEqual(grant_sha, previous_grant_sha)
                old_sidecars = {}
                for index, receipt in enumerate(row['requests']):
                    self.assertIn('response_evidence', receipt)
                    pointer = receipt['response_evidence']
                    old_path = journal_path.parent / pointer['filename']
                    old_raw = old_path.read_bytes()
                    self.assertEqual(mapping.sha(old_raw), pointer['sha256'])
                    diagnostic = mapping.parse(old_raw)
                    request = {key: value for key, value in receipt.items() if key != 'response_evidence'}
                    self.assertEqual(diagnostic['grant_sha256'], previous_grant_sha)
                    self.assertEqual(diagnostic['source_id'], sid)
                    self.assertEqual(diagnostic['request_index'], index)
                    self.assertEqual(diagnostic['request'], request)
                    old_sidecars[old_path] = old_raw
                    diagnostic['grant_sha256'] = grant_sha
                    name = f'{journal_path.name}.{sid}.{grant_sha}.{index}.response.json'
                    self.assertNotEqual(name, pointer['filename'])
                    draft.permanent_intent(journal_path.parent / name, diagnostic)
                    receipt['response_evidence'] = {'filename': name, 'sha256': mapping.sha(mapping.encode(diagnostic))}
                journal_path.write_bytes(mapping.encode(journal))
                harness.bound['draft_row_sha256'] = mapping.sha(mapping.encode(row))
                harness.bound['binding'] = mapping.sha(mapping.encode(
                    {key: value for key, value in harness.bound.items() if key != 'binding'}))
                self.assertEqual(len(old_sidecars), len(row['requests']))
                self.assertEqual({path: path.read_bytes() for path in old_sidecars}, old_sidecars)
                for index, receipt in enumerate(row['requests']):
                    pointer = receipt['response_evidence']
                    self.assertEqual(pointer['filename'],
                                     f'{journal_path.name}.{sid}.{grant_sha}.{index}.response.json')
                    raw = (journal_path.parent / pointer['filename']).read_bytes()
                    self.assertEqual(mapping.sha(raw), pointer['sha256'])
                    diagnostic = mapping.parse(raw)
                    old_name = f'{journal_path.name}.{sid}.{previous_grant_sha}.{index}.response.json'
                    expected = mapping.parse(old_sidecars[journal_path.parent / old_name])
                    self.assertEqual(diagnostic, dict(expected, grant_sha256=grant_sha))
                    self.assertEqual(diagnostic['grant_sha256'], row['grant_sha256'])
                    self.assertEqual(diagnostic['source_id'], sid)
                    self.assertEqual(diagnostic['request_index'], index)
                    self.assertEqual(diagnostic['request'],
                                     {key: value for key, value in receipt.items() if key != 'response_evidence'})
                packet = mapping.parse(harness.packet.read_bytes())
                self.assertEqual(packet['evidence'], dict(harness.prepared.evidence, runtime_sha256=historical_runtime))
                retained = {path: path.read_bytes() for path in fixture.root.rglob('*') if path.is_file()}
                calls = list(fixture.transport.calls)
                prepared, bound = harness.bridge()
                self.assertEqual(prepared, harness.prepared)
                self.assertEqual(bound, harness.bound)
                self.assertEqual(bound['original_runtime_sha256'], historical_runtime)
                self.assertEqual(bound['runtime_sha256'], prepared.evidence['runtime_sha256'])
                self.assertNotEqual(bound['runtime_sha256'], historical_runtime)
                self.assertEqual(fixture.transport.calls, calls)
                self.assertEqual({path: path.read_bytes() for path in retained}, retained)
                row = mapping.parse(Path(fixture.paths.uploads_registry_path + '.modern-v1.json').read_bytes())['targets'][sid]
                self.assertEqual(row['counts'], {'get': 5, 'create': 1, 'init': 1, 'content': 1, 'commit': 0})


if __name__ == '__main__':
    unittest.main()
