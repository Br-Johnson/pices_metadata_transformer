"""Finite primary-origin membership plus representative real-source execution.

Every selected XML/hash/origin binding is checked without reclassifying the
collection. Fresh mapping and provider fault contracts use a small source sample.
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
from scripts.production_mutations import PROTECTED
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_organizational_coverage as organizational_tests
from tests import test_modern_publication as publication_tests
from tests.test_modern_publication_qa import raw_duplicates

SOURCE_CENSUS_SHA = 'b04e7ec9f942d61677c4f047f3eb7f94d9b98ba906c346b9338fda53aeab4589'
DIRECT_SHA = '35512b48636ae563acfc26a77c547699bba2dfe767e414e995e83079e3f3eb13'
SELECTION_SHA = '6f359520df74f31f1b54bf24d5a0123fe099245cc80a410fed396aa390729d33'
ORIGIN_PATH = './idinfo/citation/citeinfo/origin'


def representative_sources(groups):
    """Deterministically exercise diversity present in the reviewed selection."""
    selected = []

    def add(group, member=None):
        sid = (member or group['members'][0])['source_id']
        if sid not in selected:
            selected.append(sid)

    for key in (lambda group: len(group['creators']), lambda group: len(group['primary_origin_variants']),
                lambda group: len(group['members'])):
        add(max(groups, key=key))
    largest_group, largest_member = max(
        ((group, member) for group in groups for member in group['members']),
        key=lambda pair: (mapping.ROOT / 'FGDC' / (pair[1]['source_id'] + '.xml')).stat().st_size)
    add(largest_group, largest_member)
    for index in (round(i * (len(groups) - 1) / 9) for i in range(10)):
        add(groups[index])
        if len(selected) == 10:
            break
    for group in groups:
        if len(selected) == 10:
            break
        add(group)
    return selected


class ModernPrimaryOrganizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(mapping.DIRECT_PROFILE.read_bytes())
        cls.groups = cls.manifest['groups']
        cls.samples = representative_sources(cls.groups)
        cls.representative = cls.samples[0]
        cls.source_tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.source_tmp.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.source_tmp.name, ids=cls.samples + ['FGDC-141', 'FGDC-696'])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def fixture(self, source_id=None):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        return fixtures.Fixture(directory.name, self.prepared_root, source_id=source_id or self.representative)

    def test_all_selected_source_group_origin_and_review_pins_without_reclassification(self):
        manifest = self.manifest
        self.assertEqual(mapping.sha(mapping.DIRECT_PROFILE.read_bytes()), DIRECT_SHA)
        self.assertEqual(mapping.DIRECT_SHA, DIRECT_SHA)
        self.assertEqual(manifest['schema_version'], 1)
        self.assertEqual(manifest['kind'], 'modern-direct-primary-organizations-v1')
        self.assertEqual(manifest['policy'], 'modern-xml-direct-organizations-v1')
        self.assertEqual(manifest['source_census_sha256'], SOURCE_CENSUS_SHA)
        self.assertEqual(manifest['source_plan_sha256'], mapping.PLAN_SHA)
        self.assertEqual(mapping.sha(mapping.PLAN.read_bytes()), mapping.PLAN_SHA)
        self.assertEqual(len(self.groups), manifest['group_count'])
        self.assertEqual(manifest['group_count'], 294)
        self.assertEqual(manifest['member_count'], 2628)
        self.assertEqual(len({group['profile'] for group in self.groups}), len(self.groups))
        self.assertTrue(manifest['review_sha256'])
        for path, digest in manifest['review_sha256'].items():
            self.assertTrue(path.startswith('docs/readiness/2026-10-06/'))
            self.assertEqual(mapping.sha((mapping.ROOT / path).read_bytes()), digest)
        plan = {row['record_target_id']: row for row in json.loads(mapping.PLAN.read_bytes())['targets']}
        old = {row['source_id'] for row in mapping.cohort()['members']}
        old.update(row['source_id'] for row in json.loads(mapping.EXTENSION.read_bytes())['members'])
        selected = set()
        for group in self.groups:
            self.assertEqual(set(group), {'profile', 'creators', 'primary_origin_variants', 'members'})
            self.assertRegex(group['profile'], r'^primary-origin-[0-9]+$')
            self.assertTrue(group['creators'])
            self.assertTrue(group['primary_origin_variants'])
            for creator in group['creators']:
                self.assertEqual(set(creator), {'name', 'type'})
                self.assertEqual(creator['type'], 'Organization')
                self.assertTrue(creator['name'].strip())
            used_variants = set()
            for member in group['members']:
                sid = member['source_id']
                with self.subTest(source=sid, group=group['profile']):
                    self.assertEqual(set(member), {'source_id', 'source_sha256'})
                    self.assertNotIn(sid, selected | old | set(PROTECTED))
                    selected.add(sid)
                    raw = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
                    self.assertEqual(mapping.sha(raw), member['source_sha256'])
                    origins = [source_element(node) for node in ET.fromstring(raw).findall(ORIGIN_PATH)]
                    self.assertIn(origins, group['primary_origin_variants'])
                    used_variants.add(mapping.sha(mapping.encode(origins)))
                    target = plan[sid]
                    self.assertEqual(target['source_ids'], [sid])
                    self.assertEqual(target['source_sha256'], member['source_sha256'])
                    self.assertEqual(target['source_semantic_status'], 'supported')
                    self.assertIsNone(target['identity_decision']['production_record_id'])
                    self.assertIsNone(target['identity_decision']['production_doi'])
            self.assertEqual(used_variants,
                             {mapping.sha(mapping.encode(variant)) for variant in group['primary_origin_variants']})
        self.assertEqual(len(selected), manifest['member_count'])
        self.assertEqual(len(self.samples), 10)
        self.assertTrue(set(self.samples).issubset(selected))

    def test_selection_equals_both_independent_reviewers_complete_approved_groups(self):
        selection_raw = mapping.DIRECT_PROFILE.with_name('modern_direct_primary_selection.json').read_bytes()
        self.assertEqual(mapping.sha(selection_raw), SELECTION_SHA)
        selection = mapping.parse(selection_raw)
        self.assertEqual(selection['review_sha256'], self.manifest['review_sha256'])
        reviewed = {}
        for path, digest in self.manifest['review_sha256'].items():
            raw = (mapping.ROOT / path).read_bytes()
            self.assertEqual(mapping.sha(raw), digest)
            review = mapping.parse(raw)
            self.assertEqual(review['census_sha256'], SOURCE_CENSUS_SHA)
            # The two independently authored receipts retain their own schemas.
            rows = review['groups'] if 'groups' in review else review['reviews']
            for row in rows:
                self.assertNotIn(row['group_id'], reviewed)
                self.assertIn(row['verdict'], ('approve', 'hold'))
                creators = row['creator_objects'] if 'creator_objects' in row else row['full_creator_objects']
                variants = [[source_element(ET.fromstring(element)) for element in variant['elements']]
                            for variant in row['primary_origin_element_variants']]
                reviewed[row['group_id']] = dict(verdict=row['verdict'], creators=creators,
                                                members=row['members'], variants=variants)
        self.assertEqual(len(reviewed), 357)
        approved = {profile: row for profile, row in reviewed.items() if row['verdict'] == 'approve'}
        held = {profile: row for profile, row in reviewed.items() if row['verdict'] == 'hold'}
        self.assertEqual(len(approved), 294)
        self.assertEqual(len(held), 63)
        self.assertEqual({group['profile'] for group in self.groups}, set(approved))
        for group in self.groups:
            with self.subTest(profile=group['profile']):
                row = approved[group['profile']]
                self.assertEqual(group['creators'], row['creators'])
                self.assertEqual(group['members'], row['members'])
                self.assertEqual({mapping.encode(variant) for variant in group['primary_origin_variants']},
                                 {mapping.encode(variant) for variant in row['variants']})
        selected_ids = {member['source_id'] for row in approved.values() for member in row['members']}
        held_ids = {member['source_id'] for row in held.values() for member in row['members']}
        self.assertEqual(len(selected_ids), 2628)
        self.assertEqual(len(held_ids), 69)
        self.assertFalse(selected_ids & held_ids)
        self.assertEqual(set(selection['selected_group_ids']), set(approved))
        self.assertEqual(set(selection['mapping_hold_group_ids']), set(held))
        self.assertEqual(set(selection['mapping_hold_source_ids']), held_ids)
        self.assertTrue({'FGDC-729', 'FGDC-768', 'FGDC-4050', 'FGDC-4051'}.issubset(held_ids))

    def test_diverse_real_sources_preserve_complete_metadata_order_dates_rights_and_originals(self):
        for sid in self.samples:
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                prepared = fixture.prepared
                group, policy = mapping.source_policy(sid)
                metadata, source_sha, artifact, _ = assess_source(fixture.json_file, fixture.paths)
                payload = mapping.parse(fixture.json_file.read_bytes())
                self.assertNotIn('creator_interpretation', payload['artifact_policy'])
                self.assertEqual(policy, {'schema_version': 3, 'policy': 'modern-xml-direct-organizations-v1',
                                         'mapping_manifest_sha256': mapping.DIRECT_SHA, 'creator_cohort': group['profile']})
                self.assertEqual(prepared.evidence['creator_profile_sha256'], mapping.DIRECT_SHA)
                for key, value in policy.items():
                    self.assertEqual(prepared.evidence[key], value)
                self.assertEqual(prepared.evidence['source_sha256'], source_sha)
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(prepared.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                self.assertEqual(mapping.sha(prepared.xml), source_sha)
                self.assertLessEqual(len(prepared.body), draft.MAX_BYTES)
                self.assertLessEqual(len(prepared.xml), draft.MAX_BYTES)
                meta = mapping.parse(prepared.body)['metadata']
                preserved = meta['additional_descriptions'][0]['description']
                self.assertTrue(preserved.startswith('<p>' + mapping.PRESERVATION_LABEL + '</p><pre>'))
                self.assertEqual(json.loads(html.unescape(preserved.split('<pre>', 1)[1][:-6])), metadata)
                self.assertEqual(metadata['creators'], group['creators'])
                self.assertEqual(meta['creators'], [{'person_or_org': {'name': creator['name'], 'type': 'organizational'}}
                                                    for creator in group['creators']])
                for key in ('title', 'publication_date', 'description'):
                    self.assertEqual(meta[key], metadata[key])
                self.assertEqual(meta['subjects'], [{'subject': value} for value in metadata.get('keywords', [])])
                self.assertEqual(meta['publisher'], 'Zenodo')
                self.assertNotIn('rights', meta)
                self.assertNotIn('license', meta)
                self.assertEqual(mapping.parse(prepared.body)['access'], {'record': 'public', 'files': 'restricted'})
                self.assertEqual(prepared.evidence['legacy_metadata_sha256'], mapping.sha(mapping.encode(metadata)))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))

    def test_previous105_policies_and_representative_preparations_ignore_missing_direct_manifest(self):
        old = [row['source_id'] for row in mapping.cohort()['members']]
        old += [row['source_id'] for row in json.loads(mapping.EXTENSION.read_bytes())['members']]
        before = {sid: mapping.source_policy(sid) for sid in old}
        self.assertEqual(len(before), 105)
        with patch.object(mapping, 'DIRECT_PROFILE', self.root / 'missing-direct.json'):
            for sid in old:
                self.assertEqual(mapping.source_policy(sid), before[sid])
            for sid, version in (('FGDC-141', 1), ('FGDC-696', 2)):
                with self.subTest(source=sid):
                    evidence = self.fixture(sid).prepared.evidence
                    self.assertEqual(evidence['schema_version'], version)
                    self.assertEqual(evidence['creator_profile_sha256'], mapping.PROFILE_SHA)

    def test_direct_member_requires_exact_manifest_hash_and_presence(self):
        fixture = self.fixture()
        changed = self.root / 'changed-direct.json'
        changed.write_bytes(mapping.DIRECT_PROFILE.read_bytes() + b' ')
        for path in (changed, self.root / 'missing-direct.json'):
            with self.subTest(path=path.name), patch.object(mapping, 'DIRECT_PROFILE', path):
                with self.assertRaises((ValueError, OSError)):
                    mapping.prepare(fixture.json_file, fixture.paths)
        with patch.object(mapping, 'DIRECT_SHA', '0' * 64), self.assertRaises(ValueError):
            mapping.prepare(fixture.json_file, fixture.paths)

    def test_exact_primary_element_member_hash_and_creator_type_cannot_be_self_reassigned(self):
        fixture = self.fixture()
        for change in ('origin_whitespace', 'origin_attribute', 'source_hash', 'creator_type', 'creator_name'):
            with self.subTest(change=change):
                manifest = copy.deepcopy(self.manifest)
                group = next(group for group in manifest['groups']
                             if any(member['source_id'] == self.representative for member in group['members']))
                if change.startswith('origin_'):
                    for variant in group['primary_origin_variants']:
                        if change == 'origin_whitespace':
                            variant[0]['text'] = (variant[0]['text'] or '') + ' '
                        else:
                            variant[0]['attributes']['invented'] = 'changed'
                elif change == 'source_hash':
                    next(member for member in group['members']
                         if member['source_id'] == self.representative)['source_sha256'] = '0' * 64
                elif change == 'creator_type':
                    group['creators'][0]['type'] = 'Person'
                else:
                    group['creators'][0]['name'] += ' invented'
                changed = self.root / 'rehashed-direct.json'
                changed.write_bytes(mapping.encode(manifest))
                with patch.object(mapping, 'DIRECT_PROFILE', changed), \
                        patch.object(mapping, 'DIRECT_SHA', mapping.sha(changed.read_bytes())), \
                        self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)

    def test_any_creator_interpretation_key_is_rejected_including_none_and_forged426(self):
        fixture = self.fixture()
        original = fixture.json_file.read_bytes()
        for value in (None, {}, {'manifest_path': str(mapping.PROFILE), 'manifest_sha256': mapping.PROFILE_SHA}):
            with self.subTest(reference=value):
                payload = mapping.parse(original)
                payload['artifact_policy']['creator_interpretation'] = value
                fixture.json_file.write_bytes(mapping.encode(payload))
                with self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])

    def test_unselected_person_reference_paired_protected_and_held_sources_stay_blocked(self):
        fixture = self.fixture()
        # MSO remains outside every finite policy; PICES26 and citation organizations have their own.
        for sid in ('FGDC-1', 'FGDC-2232', 'FGDC-710', 'FGDC-2953', 'FGDC-3181',
                    'FGDC-729', 'FGDC-768', 'FGDC-4050', 'FGDC-4051', *PROTECTED):
            with self.subTest(source=sid):
                path = fixture.json_file.with_name(sid + '.json')
                path.write_bytes(fixture.json_file.read_bytes())
                with self.assertRaises(ValueError):
                    mapping.source_policy(sid)
                with self.assertRaises(ValueError):
                    mapping.prepare(path, fixture.paths)

    def test_source_creator_order_date_rights_and_original_bytes_remain_freshly_checked(self):
        fixture = self.fixture()
        original = fixture.json_file.read_bytes()
        creators = mapping.parse(original)['metadata']['creators']
        changes = [('creators', [{'name': creator['name']} for creator in creators]),
                   ('publication_date', '2026-10-06'), ('license', 'cc-by-4.0'), ('access_right', 'open')]
        if len(creators) > 1:
            changes.append(('creators', list(reversed(creators))))
        for key, value in changes:
            with self.subTest(field=key, value=value):
                payload = mapping.parse(original)
                payload['metadata'][key] = value
                fixture.json_file.write_bytes(mapping.encode(payload))
                with self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)
        fixture.json_file.write_bytes(original)
        original_copy = Path(fixture.paths.original_fgdc_dir) / (self.representative + '.xml')
        original_copy.write_bytes(original_copy.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            mapping.prepare(fixture.json_file, fixture.paths)

    def test_direct_source_complete_offline_draft_publication_and_unchanged_retry(self):
        fixture = self.fixture()
        harness = organizational_tests.PublicationFixture(fixture)
        base = '/api/records/19000001/draft'
        file = base + '/files/' + self.representative + '.xml'
        self.assertEqual([call for call in fixture.transport.calls if call[0] != 'GET'], [
            ('POST', '/api/records', fixture.prepared.body),
            ('POST', base + '/files', mapping.encode([{'key': self.representative + '.xml'}])),
            ('PUT', file + '/content', fixture.prepared.xml), ('POST', file + '/commit', None),
        ])
        self.assertEqual(fixture.runner().run(read_only=True)['counts'], draft.LIMITS)
        harness.prepared, harness.bound = harness.bridge()
        documents = harness.ready()
        record = mapping.parse(documents['qa'].read_bytes())['records'][0]
        self.assertEqual(record['fgdc_id'], self.representative)
        self.assertEqual(record['agent_evidence']['prepared_evidence']['schema_version'], 3)
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['published_verified'])
        self.assertTrue(result['community_submission_verified'])
        result = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(result['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual([call[0] for call in harness.transport.calls if call[0] != 'GET'], ['PUT', 'POST'])
        self.assertTrue(result['community_membership_verified'])
        self.assertTrue(result['release_complete'])
        self.assertFalse(result['doi_registration_verified'])

    def test_direct_source_uncertain_create_intent_survives_journal_loss_and_fresh_grant(self):
        for effect in (False, True):
            with self.subTest(effect_before_response_loss=effect):
                fixture = self.fixture()
                fixture.transport.fail_index = 0
                fixture.transport.effect_before_fail = effect
                runner = fixture.runner()
                with self.assertRaises(ValueError):
                    runner.run()
                intent = runner.intent_path.read_bytes()
                row = mapping.parse(runner.journal_path.read_bytes())['targets'][self.representative]
                self.assertEqual(row['counts']['create'], 1)
                self.assertIsNone(row['identity'])
                for readonly in (False, True):
                    with self.assertRaises(ValueError):
                        fixture.runner().run(read_only=readonly)
                runner.journal_path.unlink()
                fixture.change_proof(reviewed_by='Fresh synthetic independent reviewer')
                fixture.change_grant(reviewed_by='Fresh synthetic parent reviewer')
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(runner.intent_path.read_bytes(), intent)
                self.assertEqual(len(fixture.transport.calls), 1)

    def test_qa_rejects_rehashed_schema_policy_cohort_and_false426_authority(self):
        harness = organizational_tests.PublicationFixture(self.fixture())
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        for key, value in (('schema_version', 2), ('policy', mapping.EXTENSION_POLICY),
                           ('mapping_manifest_sha256', mapping.EXTENSION_SHA), ('creator_cohort', mapping.COHORT),
                           ('creator_profile_sha256', mapping.PROFILE_SHA)):
            with self.subTest(field=key):
                evidence = copy.deepcopy(harness.prepared.evidence)
                evidence[key] = value
                forged = replace(harness.prepared, evidence=evidence, binding=mapping.sha(mapping.encode(evidence)))
                bound = copy.deepcopy(harness.bound)
                bound['preparation_binding'] = forged.binding
                bound['binding'] = mapping.sha(mapping.encode({k: v for k, v in bound.items() if k != 'binding'}))
                saved = copy.deepcopy(snapshot)
                saved['bridge_binding'] = bound['binding']
                duplicate = raw_duplicates(forged, bridge=bound, snapshot=saved, now=publication_tests.NOW)
                with self.assertRaises(ValueError):
                    qa.assess(forged, bound, saved, duplicate, now=publication_tests.NOW)
        self.assertEqual(harness.transport.calls, [])

    def test_original19_saved_pr36_draft_bridges_and_publishes_without_changing_creation_history(self):
        self.assert_pr36_publication_preserves_creation('FGDC-141', 1)

    def test_extension86_saved_pr36_draft_bridges_and_publishes_without_changing_creation_history(self):
        self.assert_pr36_publication_preserves_creation('FGDC-696', 2)

    def assert_pr36_publication_preserves_creation(self, sid, version):
        harness = organizational_tests.PublicationFixture(self.fixture(sid))
        fixture = harness.fixture
        current = harness.prepared
        packet = mapping.parse(harness.packet.read_bytes())
        packet['evidence']['runtime_sha256'] = publication.PR36_RUNTIME
        packet['binding'] = mapping.sha(mapping.encode(packet['evidence']))
        harness.packet.write_bytes(mapping.encode(packet))
        fixture.change_proof(binding=packet['binding'])
        fixture.change_grant(binding=packet['binding'])
        journal_path = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
        journal = mapping.parse(journal_path.read_bytes())
        row = journal['targets'][sid]
        initial_row = copy.deepcopy(row)
        row['binding'] = packet['binding']
        row['grant_sha256'] = mapping.sha(fixture.grant_path.read_bytes())
        intent_path = draft.state_root(fixture.paths) / (sid + '.modern-create-v1.intent.json')
        intent = mapping.parse(intent_path.read_bytes())
        intent.update(binding=packet['binding'], grant_sha256=row['grant_sha256'])
        intent_path.write_bytes(mapping.encode(intent))
        row['intent_sha256'] = mapping.sha(intent_path.read_bytes())
        journal_path.write_bytes(mapping.encode(journal))
        self.assertEqual({key: value for key, value in row.items()
                          if key not in {'binding', 'grant_sha256', 'intent_sha256'}},
                         {key: value for key, value in initial_row.items()
                          if key not in {'binding', 'grant_sha256', 'intent_sha256'}})
        history_paths = (harness.packet, fixture.grant_path, fixture.proof_path, journal_path, intent_path)
        retained = {path: path.read_bytes() for path in history_paths}
        initial_calls = list(fixture.transport.calls)

        harness.prepared, harness.bound = harness.bridge()
        self.assertEqual(harness.prepared, current)
        self.assertEqual(harness.prepared.evidence['schema_version'], version)
        self.assertEqual(harness.bound['identity'], initial_row['identity'])
        self.assertEqual(harness.bound['original_runtime_sha256'], publication.PR36_RUNTIME)
        self.assertEqual(harness.bound['original_preparation_binding'], packet['binding'])
        self.assertEqual(harness.bound['preparation_binding'], current.binding)
        self.assertEqual({key: value for key, value in packet['evidence'].items() if key != 'runtime_sha256'},
                         {key: value for key, value in current.evidence.items() if key != 'runtime_sha256'})
        documents = harness.ready()
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['published_verified'])
        self.assertTrue(result['community_submission_verified'])
        retry = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(retry['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual([call[0] for call in harness.transport.calls if call[0] != 'GET'], ['PUT', 'POST'])
        # Publication's fake delegates read response synthesis to the draft fake;
        # its appended reads must not be mistaken for renewed creation actions.
        self.assertEqual(fixture.transport.calls[:len(initial_calls)], initial_calls)
        self.assertTrue(all(call[0] == 'GET' for call in fixture.transport.calls[len(initial_calls):]))
        self.assertEqual([call for call in fixture.transport.calls if call[0] != 'GET'],
                         [call for call in initial_calls if call[0] != 'GET'])
        self.assertEqual({path: path.read_bytes() for path in history_paths}, retained)
        self.assertEqual(mapping.parse(journal_path.read_bytes())['targets'][sid]['counts'], initial_row['counts'])

    def test_all_historical_runtimes_hold_direct_policy_even_with_consistent_rebound_history(self):
        for runtime in (publication.PR34_RUNTIME, publication.PR35_RUNTIME, publication.PR36_RUNTIME):
            with self.subTest(runtime=runtime):
                harness = organizational_tests.PublicationFixture(self.fixture())
                fixture = harness.fixture
                packet = mapping.parse(harness.packet.read_bytes())
                packet['evidence']['runtime_sha256'] = runtime
                packet['binding'] = mapping.sha(mapping.encode(packet['evidence']))
                harness.packet.write_bytes(mapping.encode(packet))
                fixture.change_proof(binding=packet['binding'])
                fixture.change_grant(binding=packet['binding'])
                journal_path = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
                journal = mapping.parse(journal_path.read_bytes())
                row = journal['targets'][self.representative]
                row['binding'] = packet['binding']
                row['grant_sha256'] = mapping.sha(fixture.grant_path.read_bytes())
                intent_path = draft.state_root(fixture.paths) / (self.representative + '.modern-create-v1.intent.json')
                intent = mapping.parse(intent_path.read_bytes())
                intent.update(binding=packet['binding'], grant_sha256=row['grant_sha256'])
                intent_path.write_bytes(mapping.encode(intent))
                row['intent_sha256'] = mapping.sha(intent_path.read_bytes())
                journal_path.write_bytes(mapping.encode(journal))
                original_history = journal_path.read_bytes(), intent_path.read_bytes()
                with self.assertRaises(ValueError):
                    harness.bridge()
                # Match the complete hypothetical bridge so the capture refusal
                # cannot be explained by an unrelated stale grant binding.
                harness.bound.update(original_preparation_binding=packet['binding'],
                                     original_runtime_sha256=runtime,
                                     preparation_packet_sha256=mapping.sha(harness.packet.read_bytes()),
                                     draft_row_sha256=mapping.sha(mapping.encode(row)),
                                     create_intent_sha256=row['intent_sha256'],
                                     grant_sha256=row['grant_sha256'])
                harness.bound['binding'] = mapping.sha(mapping.encode(
                    {key: value for key, value in harness.bound.items() if key != 'binding'}))
                harness.grant('capture')
                with self.assertRaises(ValueError):
                    harness.runner('capture').run()
                self.assertEqual(harness.transport.calls, [])
                self.assertEqual((journal_path.read_bytes(), intent_path.read_bytes()), original_history)


if __name__ == '__main__':
    unittest.main()
