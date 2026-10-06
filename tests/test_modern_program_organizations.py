"""Exact20 organizational projections, original preservation and policy boundaries.

All20 retained source/review/XML vectors are checked without broad classification.
Ten varied sources use fresh preparation; one shared fake publication flow checks
the new policy. Synthetic grants never confer real provider authority.
"""

import copy
import html
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
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
from tests.test_modern_organizational_coverage import PublicationFixture
from tests.test_modern_publication import NOW as PUBLICATION_NOW
from tests.test_modern_publication_qa import raw_duplicates
from tests.test_modern_upload_compatibility import CompatibilityTransport

MANIFEST_SHA = '0485e9c5e24566df94ad59397b8bdf2ebde375e88504d9f419bc61b71a0b20e1'
SOURCE_SHA = '56f6e99cefe31bcba6802781e2746771947d448cd2c9ad4cde4c66d58c35653d'
REVIEW_SHA = 'f0cfcd9a0fe12cdac1d52cd399355c2da09033c0e42a2279140c555bb2bd983b'
REVIEWED194_RUNTIME = '6cc86a1740fcd93e65d42e21b1c199c160974c607be54db71f43d3e25466349e'
APPROVED = ('FGDC-355', 'FGDC-360', 'FGDC-669', 'FGDC-1291', 'FGDC-1765',
            'FGDC-1767', 'FGDC-1791', 'FGDC-1946', 'FGDC-2197', 'FGDC-2232',
            'FGDC-2302', 'FGDC-3776', 'FGDC-3777', 'FGDC-3788', 'FGDC-3926',
            'FGDC-3928', 'FGDC-4017', 'FGDC-4028', 'FGDC-4061', 'FGDC-4064')
SAMPLES = ('FGDC-355', 'FGDC-669', 'FGDC-1291', 'FGDC-1765', 'FGDC-2197',
           'FGDC-2232', 'FGDC-3788', 'FGDC-4028', 'FGDC-4061', 'FGDC-4064')
OLD_SAMPLES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839',
               'FGDC-1319', 'FGDC-59', 'FGDC-3875', 'FGDC-1')
HOLDS = ('FGDC-419', 'FGDC-545', 'FGDC-546', 'FGDC-547', 'FGDC-548', 'FGDC-549',
         'FGDC-550', 'FGDC-551', 'FGDC-552', 'FGDC-553', 'FGDC-554', 'FGDC-556',
         'FGDC-557', 'FGDC-558', 'FGDC-559', 'FGDC-560', 'FGDC-573', 'FGDC-574',
         'FGDC-575', 'FGDC-576', 'FGDC-578', 'FGDC-579', 'FGDC-580', 'FGDC-581',
         'FGDC-715', 'FGDC-859', 'FGDC-2296', 'FGDC-3873', 'FGDC-3970')


def source_packet_hash(value):
    """The frozen proposal uses UTF8, distinct from mapper/reviewer ASCII JSON."""
    return mapping.sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


class ModernProgramOrganizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.PROGRAM20.read_bytes())
        cls.source = mapping.parse(mapping.PROGRAM20_SOURCE.read_bytes())
        cls.review = mapping.parse(mapping.PROGRAM20_REVIEW.read_bytes())
        cls.rows = {row['source_id']: row for row in cls.manifest['rows']}
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=list(SAMPLES))

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        no_real_transport = patch.object(draft, 'Transport', side_effect=AssertionError('Real transport forbidden'))
        no_real_transport.start()
        self.addCleanup(no_real_transport.stop)

    def fixture(self, sid='FGDC-2232'):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        return fixtures.Fixture(directory.name, self.prepared_root, source_id=sid)

    def test_exact20_ordered29_organizations_match_original_roots_plan_creator426_and_independent_review(self):
        for path, declared, expected in (
                (mapping.PROGRAM20, mapping.PROGRAM20_SHA, MANIFEST_SHA),
                (mapping.PROGRAM20_SOURCE, mapping.PROGRAM20_SOURCE_SHA, SOURCE_SHA),
                (mapping.PROGRAM20_REVIEW, mapping.PROGRAM20_REVIEW_SHA, REVIEW_SHA)):
            self.assertEqual(declared, expected)
            self.assertEqual(mapping.sha(path.read_bytes()), expected)
        self.assertEqual(tuple(row['source_id'] for row in self.manifest['rows']), APPROVED)
        self.assertEqual(len(self.rows), 20)
        self.assertEqual(self.manifest['member_count'], 20)
        self.assertEqual(self.manifest['complete_array_group_count'], 17)
        self.assertEqual(self.manifest['modern_creator_object_count'], 29)
        self.assertEqual(len({mapping.encode(row['modern_creators']) for row in self.rows.values()}), 17)
        self.assertEqual(sum(len(row['modern_creators']) for row in self.rows.values()), 29)
        members = [{'source_id': row['source_id'], 'source_sha256': row['source_sha256']}
                   for row in self.manifest['rows']]
        self.assertEqual(members, self.manifest['members'])
        self.assertEqual(members, self.source['approved_members'])
        self.assertEqual(members, self.review['approved_members'])
        self.assertEqual(mapping.sha(mapping.encode(members)), self.manifest['membership_sha256'])
        self.assertEqual(self.review['decision'],
                         'APPROVE_EXACT20_COMPLETE_ORGANIZATIONAL_PROJECTIONS_RETAIN29_COMPLETE_ARRAY_HOLDS')
        sources = {row['source_id']: row for row in self.source['source_rows']}
        reviewed = {row['source_id']: row for row in self.review['source_rows']}
        profiles = {row['profile']: row for row in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']}
        targets = {row['record_target_id']: row for row in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        for sid, row in self.rows.items():
            with self.subTest(source=sid):
                source, review = sources[sid], reviewed[sid]
                original = (mapping.ROOT / row['source_path']).read_bytes()
                root = ET.fromstring(original)
                self.assertEqual(row['source_path'], 'FGDC/' + sid + '.xml')
                self.assertEqual(len(original), row['source_bytes'])
                self.assertEqual(mapping.sha(original), row['source_sha256'])
                self.assertEqual(source_element(root), source['source_root'])
                self.assertEqual(mapping.sha(mapping.encode(source_element(root))), row['source_root_sha256'])
                self.assertEqual([source_element(node) for node in root.findall('./idinfo/citation/citeinfo/origin')],
                                 row['primary_origins'])
                self.assertEqual(row['primary_origins'], review['exact_primary_origin_elements'])
                self.assertEqual(source_packet_hash(source), row['source_packet_row_sha256_utf8'])
                self.assertEqual(mapping.sha(mapping.encode(review)), row['independent_review_row_sha256_ascii'])
                self.assertEqual(review['proposal_row_sha256'], row['source_packet_row_sha256_utf8'])
                self.assertEqual(source['decision'], 'APPROVE_ORGANIZATIONAL_PROJECTION')
                self.assertEqual(review['decision'], 'APPROVE_FINITE_COMPLETE_ORGANIZATIONAL_ARRAY')
                self.assertEqual(row['creators'], source['complete_legacy_creators'])
                self.assertEqual(row['creators'], review['complete_legacy_creators'])
                self.assertEqual(mapping.sha(mapping.encode(row['creators'])), row['creators_sha256'])
                self.assertEqual(row['modern_creators'], source['proposed_complete_modern_creators'])
                self.assertEqual(row['modern_creators'], review['approved_complete_modern_creators'])
                self.assertEqual(mapping.sha(mapping.encode(row['modern_creators'])), row['modern_creators_sha256'])
                self.assertEqual(row['modern_creators'], [
                    {'person_or_org': {'name': creator['name'], 'type': 'organizational'}}
                    for creator in row['creators']])
                profile = profiles[row['creator_cohort']]
                self.assertEqual(row['creator_authority_kind'], 'creator426')
                self.assertEqual(profile, source['complete_current_creator_cohort'])
                self.assertEqual(profile, review['complete_current_creator_cohort'])
                self.assertEqual(profile['creators'], row['creators'])
                self.assertEqual(mapping.sha(mapping.encode(profile)), row['creator_authority_object_sha256'])
                self.assertIn({'source_id': sid, 'source_sha256': row['source_sha256']}, profile['members'])
                target = targets[sid]
                self.assertEqual(mapping.sha(mapping.encode(target)), row['source_plan_target_sha256'])
                self.assertEqual(target, review['source_plan_target'])
                self.assertEqual(target['source_ids'], [sid])
                self.assertEqual(target['source_semantic_status'], 'supported')
                self.assertIsNone(target['identity_decision']['production_record_id'])
                self.assertIsNone(target['identity_decision']['production_doi'])
                self.assertNotIn(sid, mapping.PROTECTED)
                for xpath, elements in source['source_dates'].items():
                    self.assertEqual([source_element(node) for node in root.findall(xpath)], elements)
                self.assertEqual(source['source_dates'], review['source_dates'])
                self.assertEqual(mapping.sha(mapping.encode(source['source_dates'])), row['source_dates_sha256_ascii'])
                self.assertEqual(source['raw_four_constraints'], review['raw_four_constraints'])
                self.assertEqual(mapping.sha(mapping.encode(source['raw_four_constraints'])),
                                 row['raw_four_constraints_sha256_ascii'])
                selected, fields = mapping.program_organization_source_policy(sid)
                self.assertEqual(selected['modern_creators'], row['modern_creators'])
                self.assertEqual(selected['creators'], row['creators'])
                self.assertEqual(fields, {'schema_version': 9, 'policy': mapping.PROGRAM_POLICY,
                                         'mapping_manifest_sha256': MANIFEST_SHA,
                                         'creator_authority_kind': 'creator426', 'creator_cohort': row['creator_cohort']})

    def test_ten_fresh_preparations_repeat_exactly_and_preserve_complete_metadata_source_copies_rights_dates(self):
        paths = OutputPaths(str(self.prepared_root), 'production')
        self.assertEqual(len(SAMPLES), 10)
        for sid in SAMPLES:
            with self.subTest(source=sid):
                path = Path(paths.zenodo_json_dir) / (sid + '.json')
                copied = Path(paths.original_fgdc_dir) / (sid + '.xml')
                original_input, original_copy = path.read_bytes(), copied.read_bytes()
                prepared = mapping.prepare(path, paths)
                self.assertEqual(prepared, mapping.prepare(path, paths))
                metadata, source_sha, artifact, _ = assess_source(path, paths)
                row = self.rows[sid]
                wire = mapping.parse(prepared.body)
                self.assertEqual(metadata['creators'], row['creators'])
                self.assertEqual(wire['metadata']['creators'], row['modern_creators'])
                block = wire['metadata']['additional_descriptions'][0]['description']
                self.assertTrue(block.startswith('<p>' + mapping.PRESERVATION_LABEL + '</p><pre>'))
                self.assertEqual(mapping.parse(html.unescape(block.split('<pre>', 1)[1][:-6]).encode()), metadata)
                for field in ('title', 'description', 'publication_date'):
                    self.assertEqual(wire['metadata'][field], metadata[field])
                self.assertEqual(wire['metadata']['subjects'], [{'subject': item} for item in metadata.get('keywords', [])])
                self.assertEqual((metadata['access_right'], metadata['license']), ('restricted', ''))
                self.assertEqual(wire['access'], {'record': 'public', 'files': 'restricted'})
                self.assertNotIn('rights', wire['metadata'])
                self.assertNotIn('license', wire['metadata'])
                self.assertEqual(prepared.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                self.assertEqual(prepared.xml, original_copy)
                self.assertEqual(prepared.evidence['source_sha256'], source_sha)
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(prepared.evidence['creator_profile_sha256'], mapping.PROFILE_SHA)
                self.assertEqual(prepared.evidence['creator_authority_kind'], 'creator426')
                self.assertEqual(prepared.evidence['legacy_metadata_sha256'], mapping.sha(mapping.encode(metadata)))
                self.assertEqual(prepared.evidence['prepared_input_sha256'], mapping.sha(original_input))
                self.assertEqual(prepared.evidence['wire_sha256'], mapping.sha(prepared.body))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))
                self.assertEqual(mapping.parse(original_input)['artifact_policy']['creator_interpretation']['manifest_sha256'],
                                 mapping.PROFILE_SHA)
                self.assertEqual(path.read_bytes(), original_input)
                self.assertEqual(copied.read_bytes(), original_copy)

    def test_missing_or_changed_evidence_closes_new_policy_and_preserves_all_eight_prior_policy_selections(self):
        fixture = self.fixture()
        old = {sid: mapping.source_policy(sid) for sid in OLD_SAMPLES}
        for attribute in ('PROGRAM20', 'PROGRAM20_SOURCE', 'PROGRAM20_REVIEW'):
            changed = self.root / (attribute + '-changed.json')
            changed.write_bytes(getattr(mapping, attribute).read_bytes() + b' ')
            for replacement in (self.root / 'missing.json', changed):
                with self.subTest(evidence=attribute, replacement=replacement.name), \
                        patch.object(mapping, attribute, replacement):
                    with self.assertRaises((ValueError, OSError)):
                        fixture.runner().run()
                    for version, sid in enumerate(OLD_SAMPLES, 1):
                        self.assertEqual(mapping.source_policy(sid), old[sid])
                        self.assertEqual(old[sid][1]['schema_version'], version)
            self.assertEqual(fixture.transport.calls, [])
        self.assertEqual(mapping.prepare(fixture.json_file, fixture.paths), fixture.prepared)
        self.assertFalse((draft.state_root(fixture.paths) / 'FGDC-2232.modern-create-v1.intent.json').exists())

    def test_all29_retained_program_and_unaami_holds_stay_outside_new_mapping(self):
        held = self.manifest['retained_held_members']
        self.assertEqual(tuple(row['source_id'] for row in held), HOLDS)
        self.assertEqual(len(held), self.manifest['retained_held_member_count'])
        self.assertEqual(held, self.source['held_members'])
        self.assertEqual(held, self.review['held_members'])
        self.assertEqual(mapping.sha(mapping.encode(held)), self.manifest['retained_held_membership_sha256'])
        self.assertTrue(set(HOLDS).isdisjoint(APPROVED))
        for sid in HOLDS:
            with self.subTest(source=sid):
                with self.assertRaises(ValueError):
                    mapping.program_organization_source_policy(sid)
                with self.assertRaises(ValueError):
                    mapping.source_policy(sid)

    def test_self_rehashed_manifest_cannot_change_scope_roots_live_authority_or_ordered_vectors(self):
        fixture = self.fixture('FGDC-4061')
        index = next(i for i, row in enumerate(self.manifest['rows']) if row['source_id'] == 'FGDC-4061')
        for label, mutate in (
                ('missing source', lambda m: m['rows'].pop()),
                ('held source', lambda m: m['rows'][index].update(source_id='FGDC-859')),
                ('source hash', lambda m: m['rows'][index].update(source_sha256='0' * 64)),
                ('root', lambda m: m['rows'][index].update(source_root_sha256='0' * 64)),
                ('origin', lambda m: m['rows'][index]['primary_origins'][0].update(text='Invented')),
                ('plan', lambda m: m['rows'][index].update(source_plan_target_sha256='0' * 64)),
                ('authority', lambda m: m['rows'][index].update(creator_authority_object_sha256='0' * 64)),
                ('cohort', lambda m: m['rows'][index].update(creator_cohort='plain_institution_program_37_FGDC-859')),
                ('legacy array', lambda m: m['rows'][index]['creators'].reverse()),
                ('modern order', lambda m: m['rows'][index]['modern_creators'].reverse()),
                ('creator count', lambda m: m['rows'][index]['modern_creators'].pop()),
                ('actor name', lambda m: m['rows'][index]['modern_creators'][0]['person_or_org'].update(name='Invented')),
                ('actor type', lambda m: m['rows'][index]['modern_creators'][0]['person_or_org'].update(type='personal')),
                ('role', lambda m: m['rows'][index]['modern_creators'][0].update(role={'id': 'datamanager'})),
                ('affiliation', lambda m: m['rows'][index]['modern_creators'][0].update(affiliations=[{'name': 'Invented'}])),
                ('identifier', lambda m: m['rows'][index]['modern_creators'][0]['person_or_org'].update(identifiers=[{'scheme': 'ror', 'identifier': 'invented'}]))):
            with self.subTest(change=label):
                changed = copy.deepcopy(self.manifest)
                mutate(changed)
                path = self.root / 'rehashed-program20.json'
                path.write_bytes(mapping.encode(changed))
                with patch.object(mapping, 'PROGRAM20', path), \
                        patch.object(mapping, 'PROGRAM20_SHA', mapping.sha(path.read_bytes())):
                    # Rejection must occur in preparation itself, not only in
                    # the old dummy grant's subsequently mismatched binding.
                    with self.assertRaises(ValueError):
                        mapping.prepare(fixture.json_file, fixture.paths)
                    with self.assertRaises(ValueError):
                        fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])
        self.assertEqual(mapping.prepare(fixture.json_file, fixture.paths), fixture.prepared)

    def test_changed_source_copy_reference_complete_creator_array_or_metadata_cannot_dispatch(self):
        fixture = self.fixture('FGDC-669')
        original = fixture.json_file.read_bytes()
        payload = mapping.parse(original)
        for field, value in (
                ('creators', list(reversed(payload['metadata']['creators']))),
                ('title', payload['metadata']['title'] + ' changed'),
                ('description', payload['metadata']['description'] + ' changed'),
                ('publication_date', '2026-10-06'),
                ('notes', payload['metadata'].get('notes', '') + ' Rights conditions satisfied.'),
                ('access_right', 'open'), ('license', 'cc-by-4.0')):
            with self.subTest(field=field):
                changed = copy.deepcopy(payload)
                changed['metadata'][field] = value
                fixture.json_file.write_bytes(mapping.encode(changed))
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])
        for reference in (None, {'manifest_path': 'docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json',
                                 'manifest_sha256': mapping.DFO_PROFILE_SHA}):
            changed = copy.deepcopy(payload)
            changed['artifact_policy']['creator_interpretation'] = reference
            fixture.json_file.write_bytes(mapping.encode(changed))
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                fixture.runner().run()
        fixture.json_file.write_bytes(original)
        copied = Path(fixture.paths.original_fgdc_dir) / 'FGDC-669.xml'
        before = copied.read_bytes()
        copied.write_bytes(before + b' ')
        with self.assertRaises(ValueError):
            fixture.runner().run()
        copied.write_bytes(before)
        self.assertEqual(mapping.prepare(fixture.json_file, fixture.paths), fixture.prepared)
        self.assertEqual(fixture.transport.calls, [])

    def test_shared_qa_requires_creator426_and_complete_community_flow_retries_read_only(self):
        fixture = self.fixture('FGDC-4061')
        self.assertEqual(fixture.transport.calls, [])
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
        harness = PublicationFixture(fixture)
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        duplicate = mapping.parse(documents['duplicate'].read_bytes())
        evidence = qa.assess(harness.prepared, harness.bound, snapshot, duplicate,
                             now=PUBLICATION_NOW, community=harness.community_authority)
        self.assertEqual(evidence['prepared_evidence'], harness.prepared.evidence)
        self.assertEqual(harness.prepared.evidence['creator_profile_sha256'], mapping.PROFILE_SHA)
        self.assertEqual(mapping.parse(harness.prepared.body)['metadata']['creators'], self.rows['FGDC-4061']['modern_creators'])
        for key, value in (('creator_profile_sha256', mapping.PROGRAM20_SHA),
                           ('creator_authority_kind', 'direct'),
                           ('creator_cohort', 'plain_institution_program_37_FGDC-859'),
                           ('schema_version', 8), ('policy', mapping.REVIEWED_CREATORS_POLICY)):
            with self.subTest(field=key):
                changed = copy.deepcopy(harness.prepared.evidence)
                changed[key] = value
                prepared = replace(harness.prepared, evidence=changed, binding=mapping.sha(mapping.encode(changed)))
                bound = copy.deepcopy(harness.bound)
                bound['preparation_binding'] = prepared.binding
                bound['binding'] = mapping.sha(mapping.encode({k: v for k, v in bound.items() if k != 'binding'}))
                saved = copy.deepcopy(snapshot)
                saved['bridge_binding'] = bound['binding']
                proof = raw_duplicates(prepared, bridge=bound, snapshot=saved, now=PUBLICATION_NOW)
                with self.assertRaises(ValueError):
                    qa.assess(prepared, bound, saved, proof, now=PUBLICATION_NOW, community=harness.community_authority)
        first = harness.runner(documents=documents).run()
        self.assertTrue(first['release_complete'])
        self.assertTrue(first['community_membership_verified'])
        self.assertEqual(first['counts'], {'get': 16, 'review': 1, 'submit': 1})
        writes = [call for call in harness.transport.calls if call[0] != 'GET']
        draft_writes = [call for call in fixture.transport.calls if call[0] != 'GET']
        journal = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
        before = journal.read_bytes()
        retried = harness.runner(documents=documents).run(read_only=True)
        self.assertTrue(retried['release_complete'])
        self.assertEqual(retried['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual([call for call in harness.transport.calls if call[0] != 'GET'], writes)
        self.assertEqual([call for call in fixture.transport.calls if call[0] != 'GET'], draft_writes)
        self.assertEqual([call[0] for call in writes], ['PUT', 'POST'])
        self.assertEqual([call[0] for call in draft_writes], ['POST', 'POST', 'PUT'])
        self.assertEqual(journal.read_bytes(), before)

    def test_schema9_rejects_every_prior_runtime_including_reviewed194_before_reading_historical_state(self):
        fixture = self.fixture()
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
        harness = PublicationFixture(fixture)
        self.assertEqual(harness.prepared.evidence['schema_version'], 9)
        self.assertEqual(publication.REVIEWED194_RUNTIME, REVIEWED194_RUNTIME)
        current, bound = harness.bridge()
        self.assertEqual(current, fixture.prepared)
        self.assertEqual(bound['original_runtime_sha256'], current.evidence['runtime_sha256'])
        packet = mapping.parse(harness.packet.read_bytes())
        originals = {path: path.read_bytes() for path in fixture.root.rglob('*') if path.is_file()}
        calls = list(fixture.transport.calls)
        runtimes = [getattr(publication, f'PR{number}_RUNTIME') for number in range(34, 47)] + [REVIEWED194_RUNTIME]
        for runtime in runtimes:
            with self.subTest(runtime=runtime):
                self.assertNotEqual(runtime, current.evidence['runtime_sha256'])
                backdated = copy.deepcopy(packet)
                backdated['evidence']['runtime_sha256'] = runtime
                backdated['binding'] = mapping.sha(mapping.encode(backdated['evidence']))
                self.assertEqual(backdated['evidence'], dict(current.evidence, runtime_sha256=runtime))
                forged = self.root / ('backdated-' + runtime + '.json')
                forged.write_bytes(mapping.encode(backdated))
                with patch.object(draft, 'read_document', wraps=draft.read_document) as reads:
                    with self.assertRaises(ValueError):
                        publication.bridge(fixture.json_file, fixture.paths, forged, fixture.grant_path, fixture.proof_path)
                self.assertEqual([call.args[0] for call in reads.call_args_list], [forged])
                self.assertEqual(fixture.transport.calls, calls)
                self.assertEqual({path: path.read_bytes() for path in originals}, originals)


if __name__ == '__main__':
    unittest.main()
