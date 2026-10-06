"""Finite Exxon citation coverage and personal-creator execution contracts.

All member pins use original-file reads. Only ten new sources are freshly
classified; injected transports exercise canonical names and interrupted writes.
"""

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
from scripts import modern_singleton_executor as draft
from scripts.agent_qa import assess_source
from scripts.production_mutations import PROTECTED
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_organizational_coverage as organizational_tests
from tests import test_modern_publication as publication_tests
from tests.test_modern_publication_qa import raw_duplicates

EXXON_PROFILE_SHA = 'ee49147aec99d83cf54cb7fa4e59f7e50229967af0f08f5408e97144367e99e5'
EXXON_MAPPING_SHA = '5dbfeb098ee8b3bbad0e06d020c1c14c88e32363d45fab4e69a5cc961482a94f'
SOURCE_REVIEW_SHA = 'ad17c1efcb4014edcfc3e4fb8c08fb884ee4ea4928805fb7929277f1a6d155f3'
SERVICE_CONTRACT_SHA = 'e320207b7feda481d7466eaa28e021d64ce24ce7e25f442e0f33e164fe9d88ab'
MODERN_CREATORS = [
    {'person_or_org': {'type': 'organizational', 'name': 'Exxon Valdez Oil Spill Trustee Council'}},
    {'person_or_org': {'type': 'personal', 'family_name': 'Bodkin', 'given_name': 'James'},
     'affiliations': [{'name': 'U.S. Geological Survey, Anchorage, Alaska'}]},
    {'person_or_org': {'type': 'personal', 'family_name': 'Dean', 'given_name': 'Thomas A.'},
     'affiliations': [{'name': 'Coastal Resources Associates, Inc., Carlsbad, California'}]},
]


def canonical_person_names(index, status, value):
    """Emulate the retained service's personal-name enrichment on every record."""
    if isinstance(value, dict) and 'metadata' in value:
        for creator in value['metadata']['creators']:
            person = creator['person_or_org']
            if person['type'] == 'personal':
                person['name'] = person['family_name'] + ', ' + person['given_name']
    return status, value


def save_historical_runtime(harness, runtime):
    """Construct a consistent synthetic old receipt without resetting actions."""
    fixture = harness.fixture
    packet = mapping.parse(harness.packet.read_bytes())
    packet['evidence']['runtime_sha256'] = runtime
    packet['binding'] = mapping.sha(mapping.encode(packet['evidence']))
    harness.packet.write_bytes(mapping.encode(packet))
    fixture.change_proof(binding=packet['binding'])
    fixture.change_grant(binding=packet['binding'])
    journal_path = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
    journal = mapping.parse(journal_path.read_bytes())
    row = journal['targets'][fixture.prepared.source_id]
    row.update(binding=packet['binding'], grant_sha256=mapping.sha(fixture.grant_path.read_bytes()))
    intent_path = draft.state_root(fixture.paths) / (fixture.prepared.source_id + '.modern-create-v1.intent.json')
    intent = mapping.parse(intent_path.read_bytes())
    intent.update(binding=packet['binding'], grant_sha256=row['grant_sha256'])
    intent_path.write_bytes(mapping.encode(intent))
    row['intent_sha256'] = mapping.sha(intent_path.read_bytes())
    journal_path.write_bytes(mapping.encode(journal))
    harness.bound.update(original_preparation_binding=packet['binding'], original_runtime_sha256=runtime,
                         preparation_packet_sha256=mapping.sha(harness.packet.read_bytes()),
                         draft_row_sha256=mapping.sha(mapping.encode(row)), create_intent_sha256=row['intent_sha256'],
                         grant_sha256=row['grant_sha256'])
    harness.bound['binding'] = mapping.sha(mapping.encode(
        {key: value for key, value in harness.bound.items() if key != 'binding'}))
    paths = (harness.packet, fixture.grant_path, fixture.proof_path, journal_path, intent_path)
    return {path: path.read_bytes() for path in paths}


class ModernExxonCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.EXXON_MAPPING.read_bytes())
        cls.profile = mapping.parse(mapping.EXXON_PROFILE.read_bytes())
        members = cls.manifest['members']
        largest = max(members, key=lambda row: (mapping.ROOT / 'FGDC' / (row['source_id'] + '.xml')).stat().st_size)
        ids = [largest['source_id']]
        for index in (round(i * (len(members) - 1) / 9) for i in range(10)):
            sid = members[index]['source_id']
            if sid not in ids:
                ids.append(sid)
            if len(ids) == 10:
                break
        cls.samples, cls.representative = ids, ids[0]
        cls.source_tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.source_tmp.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.source_tmp.name, ids=ids + ['FGDC-141', 'FGDC-696', 'FGDC-95'])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def fixture(self, sid=None):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        return fixtures.Fixture(directory.name, self.prepared_root, source_id=sid or self.representative)

    def test_all412_original_profile_plan_and_exact_primary_origin_bindings(self):
        self.assertEqual(mapping.sha(mapping.EXXON_PROFILE.read_bytes()), EXXON_PROFILE_SHA)
        self.assertEqual(mapping.EXXON_SHA, EXXON_PROFILE_SHA)
        self.assertEqual(mapping.sha(mapping.EXXON_MAPPING.read_bytes()), EXXON_MAPPING_SHA)
        self.assertEqual(mapping.EXXON_MAPPING_SHA, EXXON_MAPPING_SHA)
        self.assertEqual(self.manifest['schema_version'], 1)
        self.assertEqual(self.manifest['kind'], 'modern-exxon-singletons-v1')
        self.assertEqual(self.manifest['policy'], 'modern-xml-exxon412-v1')
        self.assertEqual(self.manifest['profile'], self.profile['profile'])
        self.assertEqual(self.manifest['source_plan_sha256'], mapping.PLAN_SHA)
        self.assertEqual(self.manifest['creators'], self.profile['creators'])
        self.assertEqual(self.manifest['modern_creators'], MODERN_CREATORS)
        self.assertEqual(len(self.profile['members']), 821)
        self.assertEqual(len(self.manifest['members']), 412)
        self.assertEqual(len(self.samples), 10)
        plan = mapping.parse(mapping.PLAN.read_bytes())
        targets = {source: target for target in plan['targets'] for source in target['source_ids']}
        expected = [row for row in self.profile['members']
                    if targets[row['source_id']]['source_ids'] == [row['source_id']]
                    and targets[row['source_id']]['source_semantic_status'] == 'supported'
                    and targets[row['source_id']]['identity_decision']['production_record_id'] is None
                    and targets[row['source_id']]['identity_decision']['production_doi'] is None
                    and row['source_id'] not in PROTECTED]
        self.assertEqual(self.manifest['members'], expected)
        seen = set()
        for row in self.manifest['members']:
            sid = row['source_id']
            with self.subTest(source=sid):
                self.assertNotIn(sid, seen | set(PROTECTED))
                seen.add(sid)
                raw = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
                self.assertEqual(mapping.sha(raw), row['source_sha256'])
                self.assertEqual(targets[sid]['source_sha256'], row['source_sha256'])
                nodes = ET.fromstring(raw).findall(self.profile['source_xpath'])
                self.assertEqual(len(nodes), 1)
                self.assertEqual(nodes[0].text, self.profile['raw_origin'])
                self.assertEqual(nodes[0].attrib, {})
                self.assertEqual(list(nodes[0]), [])
        self.assertFalse(seen & {'FGDC-1994', 'FGDC-2043', 'FGDC-2057'})

    def test_selection_and_personal_projection_equal_independent_source_and_service_contracts(self):
        directory = mapping.EXXON_MAPPING.parent
        review_raw = (directory / 'modern_exxon_source_review.json').read_bytes()
        contract_raw = (directory / 'modern_exxon_creator_contract.json').read_bytes()
        self.assertEqual(mapping.sha(review_raw), SOURCE_REVIEW_SHA)
        self.assertEqual(mapping.sha(contract_raw), SERVICE_CONTRACT_SHA)
        self.assertEqual(self.manifest['review_sha256'], SOURCE_REVIEW_SHA)
        self.assertEqual(self.manifest['service_contract_sha256'], SERVICE_CONTRACT_SHA)
        review, contract = mapping.parse(review_raw), mapping.parse(contract_raw)
        self.assertEqual(len(review['coherent_groups']), 1)
        group = review['coherent_groups'][0]
        self.assertEqual(group['candidate_count'], 412)
        self.assertEqual(group['members'], self.manifest['members'])
        self.assertEqual(group['existing_full_creator_objects'], self.manifest['creators'])
        self.assertEqual(group['existing_full_creator_objects_sha256'], mapping.sha(mapping.encode(self.profile['creators'])))
        self.assertEqual(review['candidate_membership_sha256'], mapping.sha(mapping.encode(self.manifest['members'])))
        self.assertEqual(contract['source_profile_sha256'], EXXON_PROFILE_SHA)
        self.assertEqual(contract['source_review_sha256'], SOURCE_REVIEW_SHA)
        self.assertEqual(self.manifest['modern_creators'], MODERN_CREATORS)
        excluded = {row['source_id'] for row in review['exclusions']}
        selected = {row['source_id'] for row in self.manifest['members']}
        self.assertEqual(len(excluded), 409)
        self.assertFalse(selected & excluded)
        self.assertEqual(selected | excluded, {row['source_id'] for row in self.profile['members']})
        for modern, legacy in zip(MODERN_CREATORS, self.profile['creators'], strict=True):
            person = modern['person_or_org']
            if person['type'] == 'personal':
                self.assertNotIn('name', person)
                self.assertEqual(person['family_name'] + ', ' + person['given_name'], legacy['name'])
                self.assertEqual(modern['affiliations'], [{'name': legacy['affiliation']}])
            else:
                self.assertEqual(person['name'], legacy['name'])

    def test_ten_fresh_sources_preserve_entire_metadata_names_affiliations_order_dates_and_rights(self):
        for sid in self.samples:
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                prepared = fixture.prepared
                metadata, source_sha, artifact, _ = assess_source(fixture.json_file, fixture.paths)
                payload = mapping.parse(fixture.json_file.read_bytes())
                self.assertEqual(payload['artifact_policy']['creator_interpretation']['manifest_sha256'], EXXON_PROFILE_SHA)
                self.assertEqual(metadata['creators'], self.profile['creators'])
                self.assertEqual(prepared.evidence['schema_version'], 4)
                self.assertEqual(prepared.evidence['policy'], 'modern-xml-exxon412-v1')
                self.assertEqual(prepared.evidence['creator_profile_sha256'], EXXON_PROFILE_SHA)
                self.assertEqual(prepared.evidence['mapping_manifest_sha256'], mapping.EXXON_MAPPING_SHA)
                self.assertEqual(prepared.evidence['creator_cohort'], self.profile['profile'])
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(prepared.evidence['source_sha256'], source_sha)
                self.assertEqual(prepared.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                wire = mapping.parse(prepared.body)
                self.assertEqual(wire['metadata']['creators'], MODERN_CREATORS)
                preserved = wire['metadata']['additional_descriptions'][0]['description']
                self.assertEqual(mapping.parse(html.unescape(preserved.split('<pre>', 1)[1][:-6])), metadata)
                for field in ('title', 'publication_date', 'description'):
                    self.assertEqual(wire['metadata'][field], metadata[field])
                self.assertEqual(wire['metadata']['subjects'], [{'subject': value} for value in metadata.get('keywords', [])])
                self.assertEqual(wire['access'], {'record': 'public', 'files': 'restricted'})
                self.assertNotIn('rights', wire['metadata'])
                self.assertNotIn('license', wire['metadata'])
                self.assertEqual(prepared.evidence['legacy_metadata_sha256'], mapping.sha(mapping.encode(metadata)))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))
                self.assertLessEqual(len(prepared.body), draft.MAX_BYTES)
                self.assertLessEqual(len(prepared.xml), draft.MAX_BYTES)

    def test_withdrawn_or_changed_mapping_and_original_authority_hold_before_dispatch(self):
        fixture = self.fixture()
        for name in ('EXXON_MAPPING', 'EXXON_PROFILE'):
            path = getattr(mapping, name)
            changed = self.root / (name + '.json')
            changed.write_bytes(path.read_bytes() + b' ')
            for replacement in (changed, self.root / 'missing.json'):
                with self.subTest(pin=name, replacement=replacement.name), patch.object(mapping, name, replacement):
                    with self.assertRaises((ValueError, OSError)):
                        fixture.runner().run()
                    self.assertEqual(fixture.transport.calls, [])

    def test_rehashed_manifest_cannot_reassign_source_members_or_personal_fields(self):
        fixture = self.fixture()
        for change in ('member_hash', 'missing_member', 'legacy_creator', 'given_name',
                       'affiliation', 'creator_order', 'personal_type', 'extra_person_name'):
            with self.subTest(change=change):
                value = copy.deepcopy(self.manifest)
                if change == 'member_hash':
                    next(row for row in value['members'] if row['source_id'] == self.representative)['source_sha256'] = '0' * 64
                elif change == 'missing_member':
                    value['members'] = [row for row in value['members'] if row['source_id'] != self.representative]
                elif change == 'legacy_creator':
                    value['creators'][1]['name'] = 'Bodkin, Jim'
                elif change == 'given_name':
                    value['modern_creators'][1]['person_or_org']['given_name'] = 'Jim'
                elif change == 'affiliation':
                    value['modern_creators'][1]['affiliations'][0]['name'] = 'USGS'
                elif change == 'creator_order':
                    value['modern_creators'].reverse()
                elif change == 'personal_type':
                    value['modern_creators'][1]['person_or_org']['type'] = 'organizational'
                else:
                    value['modern_creators'][1]['person_or_org']['name'] = 'Bodkin, James'
                changed = self.root / 'rehashed-exxon.json'
                changed.write_bytes(mapping.encode(value))
                with patch.object(mapping, 'EXXON_MAPPING', changed), \
                        patch.object(mapping, 'EXXON_MAPPING_SHA', mapping.sha(changed.read_bytes())), \
                        self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)

    def test_changed_creator_order_affiliations_dates_rights_or_original_copy_hold(self):
        fixture = self.fixture()
        original = fixture.json_file.read_bytes()
        creators = mapping.parse(original)['metadata']['creators']
        altered_affiliation = copy.deepcopy(creators)
        altered_affiliation[1]['affiliation'] = 'USGS'
        for key, value in (('creators', list(reversed(creators))), ('creators', altered_affiliation),
                           ('publication_date', '2026-10-06'), ('license', 'cc-by-4.0'), ('access_right', 'open')):
            with self.subTest(field=key):
                payload = mapping.parse(original)
                payload['metadata'][key] = value
                fixture.json_file.write_bytes(mapping.encode(payload))
                with self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)
        fixture.json_file.write_bytes(original)
        path = Path(fixture.paths.original_fgdc_dir) / (self.representative + '.xml')
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            mapping.prepare(fixture.json_file, fixture.paths)

    def test_forged_citation426_direct_or_missing_creator_authority_is_never_adopted(self):
        fixture = self.fixture()
        original = fixture.json_file.read_bytes()
        references = [None, {}, {'manifest_path': str(mapping.PROFILE), 'manifest_sha256': mapping.PROFILE_SHA},
                      {'manifest_path': str(mapping.DIRECT_PROFILE), 'manifest_sha256': mapping.DIRECT_SHA}]
        for reference in references:
            with self.subTest(reference=reference):
                payload = mapping.parse(original)
                if reference is None:
                    payload['artifact_policy'].pop('creator_interpretation')
                else:
                    payload['artifact_policy']['creator_interpretation'] = reference
                fixture.json_file.write_bytes(mapping.encode(payload))
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(fixture.transport.calls, [])

    def test_protected_held_and_paired_profile_members_remain_outside_new_policy(self):
        fixture = self.fixture()
        targets = mapping.parse(mapping.PLAN.read_bytes())['targets']
        paired = {sid for target in targets if len(target['source_ids']) > 1 for sid in target['source_ids']}
        profile_ids = {row['source_id'] for row in self.profile['members']}
        selected = {row['source_id'] for row in self.manifest['members']}
        excluded_pairs = paired & profile_ids
        self.assertTrue(excluded_pairs)
        self.assertFalse(excluded_pairs & selected)
        for sid in ('FGDC-2043', 'FGDC-2057', 'FGDC-1994', *sorted(excluded_pairs)[:2]):
            with self.subTest(source=sid):
                path = fixture.json_file.with_name(sid + '.json')
                path.write_bytes(fixture.json_file.read_bytes())
                with self.assertRaises(ValueError):
                    mapping.source_policy(sid)
                with self.assertRaises(ValueError):
                    mapping.prepare(path, fixture.paths)

    def test_exact_and_canonical_readback_names_accept_only_empty_identifier_defaults(self):
        expected = mapping.parse(self.fixture().prepared.body)['metadata']
        mapping.compare_metadata(copy.deepcopy(expected), expected)
        value = {'metadata': copy.deepcopy(expected)}
        canonical_person_names(0, 200, value)
        for creator in value['metadata']['creators']:
            creator['person_or_org']['identifiers'] = []
            creator['role'] = {}
            for affiliation in creator.get('affiliations', []):
                affiliation['identifiers'] = []
        mapping.compare_metadata(value['metadata'], expected)
        self.assertEqual([row['person_or_org']['name'] for row in value['metadata']['creators'][1:]],
                         ['Bodkin, James', 'Dean, Thomas A.'])
        self.assertNotIn('name', expected['creators'][1]['person_or_org'])
        self.assertNotIn('name', expected['creators'][2]['person_or_org'])

    def test_readback_rejects_person_affiliation_identifier_role_and_order_corruption(self):
        expected = mapping.parse(self.fixture().prepared.body)['metadata']
        changes = {
            'family': lambda rows: rows[1]['person_or_org'].update(family_name='Bodkins'),
            'given': lambda rows: rows[1]['person_or_org'].update(given_name='Jim'),
            'initial_punctuation': lambda rows: rows[2]['person_or_org'].update(given_name='Thomas A'),
            'missing_split_name': lambda rows: rows[1]['person_or_org'].pop('given_name'),
            'derived_name': lambda rows: rows[1]['person_or_org'].update(name='James Bodkin'),
            'person_type': lambda rows: rows[1]['person_or_org'].update(type='organizational'),
            'order': lambda rows: rows.reverse(),
            'missing_affiliation': lambda rows: rows[1].pop('affiliations'),
            'empty_affiliation': lambda rows: rows[1].update(affiliations=[]),
            'affiliation_swap': lambda rows: rows[1].update(affiliations=copy.deepcopy(rows[2]['affiliations'])),
            'affiliation_shortening': lambda rows: rows[1]['affiliations'][0].update(name='U.S. Geological Survey'),
            'affiliation_duplicate': lambda rows: rows[1]['affiliations'].append(copy.deepcopy(rows[1]['affiliations'][0])),
            'ror_id': lambda rows: rows[1]['affiliations'][0].update(id='https://ror.org/035a68863'),
            'affiliation_identifiers': lambda rows: rows[1]['affiliations'][0].update(identifiers=[{'scheme': 'ror', 'identifier': '035a68863'}]),
            'affiliation_extra': lambda rows: rows[1]['affiliations'][0].update(country='US'),
            'ui_affiliation_shape': lambda rows: rows[1].update(affiliations=[[1, rows[1]['affiliations'][0]['name']]]),
            'person_identifier': lambda rows: rows[1]['person_or_org'].update(identifiers=[{'scheme': 'orcid', 'identifier': '0000-0002-1825-0097'}]),
            'creator_role': lambda rows: rows[1].update(role={'id': 'contactperson'}),
            'creator_roles': lambda rows: rows[1].update(roles=[]),
            'person_extra': lambda rows: rows[1]['person_or_org'].update(extra='unreviewed'),
            'organization_split_name': lambda rows: rows[0]['person_or_org'].update(family_name='Council'),
            'organization_affiliation': lambda rows: rows[0].update(affiliations=[{'name': 'unreviewed'}]),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                value = {'metadata': copy.deepcopy(expected)}
                canonical_person_names(0, 200, value)
                change(value['metadata']['creators'])
                with self.assertRaises(ValueError):
                    mapping.compare_metadata(value['metadata'], expected)

    def test_bad_create_person_affiliation_role_or_identifier_blocks_next_mutation(self):
        changes = [lambda rows: rows[2]['person_or_org'].update(given_name='Thomas'),
                   lambda rows: rows[1]['affiliations'][0].update(id='unapproved-ror'),
                   lambda rows: rows[1].update(role={'id': 'contactperson'}),
                   lambda rows: rows[1]['person_or_org'].update(identifiers=[{'scheme': 'orcid', 'identifier': 'unapproved'}])]
        for index, change in enumerate(changes):
            with self.subTest(change=index):
                fixture = self.fixture()
                def mutate(i, status, value, change=change):
                    canonical_person_names(i, status, value)
                    if i == 0:
                        change(value['metadata']['creators'])
                    return status, value
                fixture.transport.change = mutate
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual([(method, path) for method, path, _ in fixture.transport.calls], [('POST', '/api/records')])

    def test_canonical_person_names_complete_create_files_capture_qa_release_publication_retry(self):
        fixture = self.fixture()
        fixture.transport.change = canonical_person_names
        harness = organizational_tests.PublicationFixture(fixture)
        base = '/api/records/19000001/draft'
        file = base + '/files/' + self.representative + '.xml'
        self.assertEqual([call for call in fixture.transport.calls if call[0] != 'GET'], [
            ('POST', '/api/records', fixture.prepared.body),
            ('POST', base + '/files', mapping.encode([{'key': self.representative + '.xml'}])),
            ('PUT', file + '/content', fixture.prepared.xml), ('POST', file + '/commit', None)])
        self.assertEqual(fixture.runner().run(read_only=True)['counts'], draft.LIMITS)
        harness.prepared, harness.bound = harness.bridge()
        documents = harness.ready()
        row = mapping.parse(documents['qa'].read_bytes())['records'][0]
        self.assertEqual(row['agent_evidence']['prepared_evidence']['schema_version'], 4)
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['published_verified'])
        self.assertTrue(result['community_submission_verified'])
        retry = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(retry['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual(sum(call[0] == 'POST' for call in harness.transport.calls), 2)
        self.assertFalse(retry['community_membership_verified'])
        self.assertFalse(retry['doi_registration_verified'])

    def test_changed_person_before_publication_or_after_publish_blocks_next_write(self):
        for response_index in (0, 5):
            with self.subTest(response_index=response_index):
                fixture = self.fixture()
                fixture.transport.change = canonical_person_names
                harness = organizational_tests.PublicationFixture(fixture)
                documents = harness.ready()
                def corrupt(index, response, wanted=response_index):
                    if index != wanted:
                        return response
                    status, media, raw = response
                    value = mapping.parse(raw)
                    value['metadata']['creators'][2]['person_or_org']['given_name'] = 'Thomas'
                    return status, media, mapping.encode(value)
                harness.transport.change = corrupt
                with self.assertRaises(ValueError):
                    harness.runner(documents=documents).run()
                posts = [call for call in harness.transport.calls if call[0] == 'POST']
                self.assertEqual(len(posts), int(response_index == 5))
                self.assertFalse(any(call[1].endswith('/communities') for call in posts))

    def test_uncertain_create_cannot_repeat_after_journal_loss_or_new_grant(self):
        for effect in (False, True):
            with self.subTest(effect=effect):
                fixture = self.fixture()
                fixture.transport.fail_index, fixture.transport.effect_before_fail = 0, effect
                runner = fixture.runner()
                with self.assertRaises(ValueError):
                    runner.run()
                intent = runner.intent_path.read_bytes()
                row = mapping.parse(runner.journal_path.read_bytes())['targets'][self.representative]
                self.assertEqual(row['counts']['create'], 1)
                self.assertIsNone(row['identity'])
                runner.journal_path.unlink()
                fixture.change_proof(reviewed_by='New offline independent reviewer')
                fixture.change_grant(reviewed_by='New offline parent reviewer')
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(runner.intent_path.read_bytes(), intent)
                self.assertEqual(len(fixture.transport.calls), 1)

    def test_rehashed_qa_cannot_substitute_organizational_policy_or_creator_authority(self):
        harness = organizational_tests.PublicationFixture(self.fixture())
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        for key, value in (('schema_version', 3), ('policy', mapping.DIRECT_POLICY),
                           ('mapping_manifest_sha256', mapping.DIRECT_SHA), ('creator_profile_sha256', mapping.PROFILE_SHA)):
            with self.subTest(field=key):
                evidence = copy.deepcopy(harness.prepared.evidence)
                evidence[key] = value
                prepared = replace(harness.prepared, evidence=evidence, binding=mapping.sha(mapping.encode(evidence)))
                bound = copy.deepcopy(harness.bound)
                bound['preparation_binding'] = prepared.binding
                bound['binding'] = mapping.sha(mapping.encode({k: v for k, v in bound.items() if k != 'binding'}))
                saved = copy.deepcopy(snapshot)
                saved['bridge_binding'] = bound['binding']
                duplicate = raw_duplicates(prepared, bridge=bound, snapshot=saved, now=publication_tests.NOW)
                with self.assertRaises(ValueError):
                    qa.assess(prepared, bound, saved, duplicate, now=publication_tests.NOW)
        self.assertEqual(harness.transport.calls, [])

    def test_previous2733_policy_members_do_not_depend_on_exxon_mapping(self):
        original = mapping.cohort()
        extension = mapping.parse(mapping.EXTENSION.read_bytes())
        direct = mapping.parse(mapping.DIRECT_PROFILE.read_bytes())
        expected = {row['source_id']: {'schema_version': 1, 'policy': mapping.POLICY}
                    for row in original['members']}
        expected.update({row['source_id']: {'schema_version': 2, 'policy': mapping.EXTENSION_POLICY,
                         'mapping_manifest_sha256': mapping.EXTENSION_SHA, 'creator_cohort': row['creator_cohort']}
                         for row in extension['members']})
        expected.update({row['source_id']: {'schema_version': 3, 'policy': mapping.DIRECT_POLICY,
                         'mapping_manifest_sha256': mapping.DIRECT_SHA, 'creator_cohort': group['profile']}
                         for group in direct['groups'] for row in group['members']})
        self.assertEqual(len(expected), 2733)
        with patch.object(mapping, 'EXXON_MAPPING', self.root / 'missing-exxon.json'):
            for sid, policy in expected.items():
                with self.subTest(source=sid):
                    self.assertEqual(mapping.source_policy(sid)[1], policy)
            for sid, version in (('FGDC-141', 1), ('FGDC-696', 2), ('FGDC-95', 3)):
                self.assertEqual(self.fixture(sid).prepared.evidence['schema_version'], version)

    def test_pr37_prior_policies_bridge_capture_and_preserve_original_spent_history(self):
        for sid, version in (('FGDC-141', 1), ('FGDC-696', 2), ('FGDC-95', 3)):
            with self.subTest(source=sid):
                harness = organizational_tests.PublicationFixture(self.fixture(sid))
                current = harness.prepared
                original_calls = list(harness.fixture.transport.calls)
                retained = save_historical_runtime(harness, publication.PR37_RUNTIME)
                harness.prepared, harness.bound = harness.bridge()
                self.assertEqual(harness.prepared, current)
                self.assertEqual(current.evidence['schema_version'], version)
                self.assertEqual(harness.bound['original_runtime_sha256'], publication.PR37_RUNTIME)
                self.assertEqual(harness.bound['preparation_binding'], current.binding)
                harness.grant('capture')
                result = harness.runner('capture').run()
                self.assertTrue(result['capture_verified'])
                self.assertEqual(result['counts'], publication.CAPTURE_LIMITS)
                self.assertEqual({path: path.read_bytes() for path in retained}, retained)
                self.assertEqual(harness.fixture.transport.calls[:len(original_calls)], original_calls)
                self.assertTrue(all(call[0] == 'GET' for call in harness.fixture.transport.calls[len(original_calls):]))

    def test_new_policy_rejects_all_historical_runtimes_before_dispatch(self):
        for runtime in (publication.PR34_RUNTIME, publication.PR35_RUNTIME, publication.PR36_RUNTIME, publication.PR37_RUNTIME):
            with self.subTest(runtime=runtime):
                harness = organizational_tests.PublicationFixture(self.fixture())
                retained = save_historical_runtime(harness, runtime)
                with self.assertRaises(ValueError):
                    harness.bridge()
                harness.grant('capture')
                with self.assertRaises(ValueError):
                    harness.runner('capture').run()
                self.assertEqual(harness.transport.calls, [])
                self.assertEqual({path: path.read_bytes() for path in retained}, retained)


if __name__ == '__main__':
    unittest.main()
