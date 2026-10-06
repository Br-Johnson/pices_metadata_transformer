"""Finite31 source projections, contextual disclosure and historical boundaries.

All31 source/review vectors use static reads. Ten diverse new records and one
old program record are freshly prepared by the guarded runner, never at import.
All execution below injects synthetic transports and grants; no live authority.
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

MANIFEST_SHA = '62f32e602ac1389ecdbffb07ed5627b2aadb047d777fd8469295680bb93729cc'
CONTEXT_SHA = '0f4282bf079c301a2c1d4d5d18a3740bb501845179d465cc4b8a1691b9121929'
PROGRAM20_RUNTIME = '78e3fdd4f3170a804aa49b25bf4e01586a2a18a5ef914a76b2be9ac4ceb72ea2'
APPROVED = tuple('FGDC-' + str(i) for i in (
    184, 197, 248, 249, 250, 251, 254, 261, 262, 296, 723, 725, 755, 757,
    760, 770, 785, 817, 1905, 1941, 2559, 2597, 2709, 3600, 3789, 3793,
    3794, 3809, 3810, 3812, 4068))
SAMPLES = ('FGDC-184', 'FGDC-2709', 'FGDC-723', 'FGDC-817', 'FGDC-2559',
           'FGDC-2597', 'FGDC-3793', 'FGDC-3794', 'FGDC-4068', 'FGDC-3809')
OLD_SAMPLES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839', 'FGDC-1319',
               'FGDC-59', 'FGDC-3875', 'FGDC-1', 'FGDC-355')


def pointed(document, pointer):
    collection, index = pointer.strip('/').split('/')
    return document[collection][int(index)]


def rebind_synthetic_sidecars(test, harness, historical_runtime):
    """Finish a synthetic old graph before taking preservation beforeimages.

    The original diagnostics remain byte-identical. New diagnostic files bind
    the synthetic old grant, and only synthetic receipt pointers are replaced.
    This helper is fixture generation, not a runtime migration mechanism.
    """
    fixture = harness.fixture
    sid = fixture.prepared.source_id
    previous_grant_sha = mapping.sha(fixture.grant_path.read_bytes())
    exxon_tests.save_historical_runtime(harness, historical_runtime)
    journal_path = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
    journal = mapping.parse(journal_path.read_bytes())
    row = journal['targets'][sid]
    grant_sha = mapping.sha(fixture.grant_path.read_bytes())
    test.assertNotEqual(grant_sha, previous_grant_sha)
    old_sidecars = {}
    for index, receipt in enumerate(row['requests']):
        pointer = receipt['response_evidence']
        old_path = journal_path.parent / pointer['filename']
        raw = old_path.read_bytes()
        test.assertEqual(mapping.sha(raw), pointer['sha256'])
        evidence = mapping.parse(raw)
        test.assertEqual(evidence['grant_sha256'], previous_grant_sha)
        test.assertEqual(evidence['source_id'], sid)
        test.assertEqual(evidence['request_index'], index)
        test.assertEqual(evidence['request'], {k: v for k, v in receipt.items() if k != 'response_evidence'})
        old_sidecars[old_path] = raw
        evidence['grant_sha256'] = grant_sha
        name = f'{journal_path.name}.{sid}.{grant_sha}.{index}.response.json'
        test.assertNotEqual(name, pointer['filename'])
        draft.permanent_intent(journal_path.parent / name, evidence)
        receipt['response_evidence'] = {'filename': name, 'sha256': mapping.sha(mapping.encode(evidence))}
    journal_path.write_bytes(mapping.encode(journal))
    harness.bound['draft_row_sha256'] = mapping.sha(mapping.encode(row))
    harness.bound['binding'] = mapping.sha(mapping.encode(
        {key: value for key, value in harness.bound.items() if key != 'binding'}))
    test.assertEqual(len(old_sidecars), len(row['requests']))
    test.assertEqual({path: path.read_bytes() for path in old_sidecars}, old_sidecars)
    for index, receipt in enumerate(row['requests']):
        pointer = receipt['response_evidence']
        name = f'{journal_path.name}.{sid}.{grant_sha}.{index}.response.json'
        test.assertEqual(pointer['filename'], name)
        raw = (journal_path.parent / name).read_bytes()
        test.assertEqual(mapping.sha(raw), pointer['sha256'])
        evidence = mapping.parse(raw)
        old_path = journal_path.parent / f'{journal_path.name}.{sid}.{previous_grant_sha}.{index}.response.json'
        test.assertEqual(evidence, dict(mapping.parse(old_sidecars[old_path]), grant_sha256=grant_sha))
        test.assertEqual(evidence['grant_sha256'], row['grant_sha256'])
        test.assertEqual(evidence['request'], {k: v for k, v in receipt.items() if k != 'response_evidence'})


class ModernReviewedCitations31Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.CITATIONS31.read_bytes())
        cls.rows = {row['source_id']: row for row in cls.manifest['rows']}
        cls.documents = {key: mapping.parse((mapping.ROOT / spec['path']).read_bytes())
                         for key, spec in cls.manifest['source_documents'].items()}
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=list(SAMPLES))

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        forbidden = patch.object(draft, 'Transport', side_effect=AssertionError('Real transport forbidden'))
        forbidden.start()
        self.addCleanup(forbidden.stop)

    def fixture(self, sid='FGDC-3793'):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        root = self.prepared_root
        if sid == 'FGDC-355':
            # Separate old-policy classification; the new-source smoke stays ten.
            source = tempfile.TemporaryDirectory(dir=self.root)
            self.addCleanup(source.cleanup)
            root = fixtures.prepare_sources(source.name, ids=[sid])
        return fixtures.Fixture(directory.name, root, source_id=sid)

    def test_exact31_complete_vectors_roots_authorities_and_context_match_independent_source_documents(self):
        self.assertEqual(mapping.CITATIONS31_SHA, MANIFEST_SHA)
        self.assertEqual(mapping.sha(mapping.CITATIONS31.read_bytes()), MANIFEST_SHA)
        self.assertEqual(tuple(self.rows), APPROVED)
        self.assertEqual(self.manifest['member_count'], 31)
        self.assertEqual(Counter(row['projection_partition'] for row in self.rows.values()),
                         {'basis3': 3, 'contract8': 8, 'direct10': 10, 'office10': 10})
        self.assertEqual(Counter(row['creator_authority_kind'] for row in self.rows.values()),
                         {'creator426': 3, 'direct': 28})
        self.assertEqual(len({mapping.encode(row['modern_creators']) for row in self.rows.values()}), 19)
        self.assertEqual(sum(len(row['modern_creators']) for row in self.rows.values()), 65)
        self.assertEqual(mapping.CITATIONS31_CONTEXT_SHA, CONTEXT_SHA)
        self.assertEqual(mapping.sha(mapping.encode({sid: row['additional_preservation_paragraphs']
                                                    for sid, row in self.rows.items()})), CONTEXT_SHA)
        self.assertEqual(self.manifest['source_documents'], mapping.CITATIONS31_DOCUMENTS)
        for spec in self.manifest['source_documents'].values():
            self.assertEqual(mapping.sha((mapping.ROOT / spec['path']).read_bytes()), spec['sha256'])
        profiles = {row['profile']: row for row in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']}
        bindings = {row['source_id']: row for row in mapping.pinned(
            mapping.CITATIONS31_DIRECT_BINDINGS, mapping.CITATIONS31_DIRECT_BINDINGS_SHA)['members']}
        targets = {row['record_target_id']: row for row in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        approvals = set(self.documents['direct_review']['approved_source_ids'])
        for name in ('basis', 'contract', 'office'):
            approvals.update(member['source_id'] for member in self.documents[name + '_review']['approved_members'])
        self.assertEqual(approvals, set(APPROVED))
        for sid, row in self.rows.items():
            with self.subTest(source=sid):
                raw = (mapping.ROOT / row['source_path']).read_bytes()
                root = ET.fromstring(raw)
                proposal = pointed(self.documents[row['source_proposal_document']], row['proposal_row_pointer'])
                review = pointed(self.documents[row['source_review_document']], row['independent_decision_pointer'])
                self.assertEqual(row['source_path'], 'FGDC/' + sid + '.xml')
                self.assertEqual((len(raw), mapping.sha(raw)), (row['source_bytes'], row['source_sha256']))
                self.assertEqual(mapping.sha(mapping.encode(source_element(root))), row['source_root_sha256'])
                self.assertEqual([source_element(node) for node in root.findall('./idinfo/citation/citeinfo/origin')],
                                 row['primary_origins'])
                self.assertEqual(mapping.sha(mapping.encode(proposal)), row['proposal_row_sha256'])
                self.assertEqual(mapping.sha(mapping.encode(review)), row['independent_decision_sha256'])
                self.assertEqual(proposal['source_id'], sid)
                partition = row['projection_partition']
                if partition == 'direct10':
                    self.assertEqual(review['decision'], 'APPROVE_EXACT_COMPLETE_SOURCE_PROJECTION')
                    self.assertEqual(source_element(root), proposal['complete_source_root'])
                    self.assertEqual(row['creators'], proposal['retained_legacy']['full_payload']['metadata']['creators'])
                    self.assertEqual(row['creators'], review['complete_legacy_creators'])
                    reviewed = review['approved_modern_creators']
                    self.assertEqual(reviewed, proposal['proposed_modern_creators'])
                    expected = copy.deepcopy(reviewed)
                    for creator in expected:
                        person = creator['person_or_org']
                        self.assertEqual(set(person), {'type', 'family_name', 'given_names'})
                        person['given_name'] = person.pop('given_names')
                    # No splitting, spelling change, affiliation insertion, or role inference.
                    self.assertEqual(row['modern_creators'], expected)
                elif partition == 'office10':
                    self.assertEqual(review['decision'], 'APPROVE_EXACT_QUALIFIED_ORGANIZATIONAL_CREDIT')
                    self.assertEqual(raw, proposal['complete_original_xml'].encode())
                    self.assertEqual(row['creators'], review['complete_legacy_creators'])
                    reviewed = review['complete_approved_modern_creators']
                    self.assertEqual(reviewed, proposal['proposed_complete_modern_creators'])
                    self.assertEqual(row['additional_preservation_paragraphs'], [review['required_preservation_note']])
                    self.assertEqual(row['modern_creators'], reviewed)
                    self.assertEqual(reviewed, [{'person_or_org': {'type': 'organizational',
                                                                  'name': row['creators'][0]['name']}}])
                else:
                    self.assertEqual(source_element(root), proposal['source_root'])
                    self.assertIn({'source_id': sid, 'source_sha256': row['source_sha256']}, review['members'])
                    self.assertEqual(row['creators'], proposal['complete_legacy_creators'])
                    reviewed = review['approved_complete_modern_creators']
                    self.assertEqual(reviewed, proposal['proposed_complete_modern_creators'])
                    self.assertEqual(row['modern_creators'], reviewed)
                    if partition == 'contract8':
                        self.assertEqual(review['verdict'], 'APPROVE_FINITE_COMPLETE_ARRAY_SOURCE_ONLY')
                        self.assertEqual(row['additional_preservation_paragraphs'],
                                         [proposal['required_full_citation_and_role_preservation_text']])
                    else:
                        self.assertEqual(review['verdict'],
                                         'APPROVE_FINITE_COMPLETE_ARRAY_SOURCE_PROJECTION_WITH_EXPLICIT_BOUNDARY_INFERENCE')
                        self.assertEqual(row['creators'], review['complete_current_legacy_creators'])
                self.assertEqual(row['reviewed_source_creators'], reviewed)
                self.assertEqual(len(row['additional_preservation_paragraphs']), 1)
                self.assertTrue(row['additional_preservation_paragraphs'][0].strip())
                if row['creator_authority_kind'] == 'creator426':
                    authority = profiles[row['creator_cohort']]
                    self.assertEqual(authority, proposal['complete_current_creator426_cohort'])
                    self.assertIn({'source_id': sid, 'source_sha256': row['source_sha256']}, authority['members'])
                    self.assertEqual(authority['creators'], row['creators'])
                else:
                    self.assertIsNone(row['creator_cohort'])
                    authority = bindings[sid]
                    self.assertEqual(authority['complete_creator_objects'], row['creators'])
                    self.assertFalse(any(sid == member['source_id'] for profile in profiles.values()
                                         for member in profile['members']))
                self.assertEqual(mapping.sha(mapping.encode(authority)), row['creator_authority_object_sha256'])
                target = targets[sid]
                self.assertEqual(mapping.sha(mapping.encode(target)), row['source_plan_target_sha256'])
                self.assertEqual(target['source_ids'], [sid])
                self.assertEqual(target['source_semantic_status'], 'supported')
                self.assertEqual(target['source_sha256'], row['source_sha256'])
                self.assertIsNone(target['identity_decision']['production_record_id'])
                self.assertIsNone(target['identity_decision']['production_doi'])
                self.assertNotIn(sid, mapping.PROTECTED)
        self.assertEqual(self.rows['FGDC-2597']['modern_creators'], [
            {'person_or_org': {'type': 'personal', 'family_name': 'Hatakeyama', 'given_name': 'Hisanao'}}])
        self.assertIn('external identity enrichment', self.rows['FGDC-2597']['additional_preservation_paragraphs'][0])
        self.assertIn('source inconsistency remains unresolved', self.rows['FGDC-3793']['additional_preservation_paragraphs'][0])
        self.assertEqual(self.rows['FGDC-3793']['modern_creators'], self.rows['FGDC-3794']['modern_creators'])
        self.assertNotEqual(self.rows['FGDC-3793']['source_sha256'], self.rows['FGDC-3794']['source_sha256'])
        self.assertNotEqual(self.rows['FGDC-3793']['additional_preservation_paragraphs'],
                            self.rows['FGDC-3794']['additional_preservation_paragraphs'])
        self.assertIn('Elmajjati', self.rows['FGDC-3809']['additional_preservation_paragraphs'][0])
        self.assertEqual(self.rows['FGDC-3809']['modern_creators'][4]['person_or_org']['family_name'], 'Elmajatii')

    def test_ten_fresh_preparations_repeat_and_preserve_complete_legacy_xml_restrictions_and_context(self):
        paths = OutputPaths(str(self.prepared_root), 'production')
        for sid in SAMPLES:
            with self.subTest(source=sid):
                json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
                before = json_file.read_bytes()
                prepared = mapping.prepare(json_file, paths)
                self.assertEqual(prepared, mapping.prepare(json_file, paths))
                metadata, source_sha, artifact, _ = assess_source(json_file, paths)
                row = self.rows[sid]
                meta = mapping.parse(prepared.body)['metadata']
                context = ''.join('<p>' + html.escape(value) + '</p>'
                                  for value in row['additional_preservation_paragraphs'])
                preserved = meta['additional_descriptions'][0]['description']
                self.assertEqual(preserved, '<p>' + mapping.PRESERVATION_LABEL + '</p>' + context
                                 + '<pre>' + html.escape(mapping.encode(metadata).decode()) + '</pre>')
                self.assertEqual(mapping.parse(html.unescape(preserved.split('<pre>', 1)[1][:-6]).encode()), metadata)
                self.assertEqual(metadata['creators'], row['creators'])
                self.assertEqual(meta['creators'], row['modern_creators'])
                for key in ('title', 'description', 'publication_date'):
                    self.assertEqual(meta[key], metadata[key])
                self.assertEqual(meta['subjects'], [{'subject': value} for value in metadata.get('keywords', [])])
                self.assertEqual((metadata['access_right'], metadata['license']), ('restricted', ''))
                self.assertEqual(mapping.parse(prepared.body)['access'], {'record': 'public', 'files': 'restricted'})
                self.assertNotIn('rights', meta)
                self.assertNotIn('license', meta)
                self.assertEqual(prepared.xml, (mapping.ROOT / row['source_path']).read_bytes())
                self.assertEqual(prepared.xml, (Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes())
                self.assertEqual(source_sha, row['source_sha256'])
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(prepared.evidence['legacy_metadata_sha256'], mapping.sha(mapping.encode(metadata)))
                self.assertEqual(prepared.evidence['prepared_input_sha256'], mapping.sha(before))
                self.assertEqual(prepared.evidence['wire_sha256'], mapping.sha(prepared.body))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))
                self.assertEqual(prepared.evidence['schema_version'], 10)
                self.assertEqual(prepared.evidence['policy'], mapping.CITATIONS31_POLICY)
                self.assertEqual(prepared.evidence['creator_authority_kind'], row['creator_authority_kind'])
                self.assertEqual(prepared.evidence['creator_profile_sha256'],
                                 mapping.PROFILE_SHA if row['creator_authority_kind'] == 'creator426' else MANIFEST_SHA)
                policy = mapping.parse(before)['artifact_policy']
                if row['creator_authority_kind'] == 'creator426':
                    self.assertEqual(policy['creator_interpretation']['manifest_sha256'], mapping.PROFILE_SHA)
                else:
                    self.assertNotIn('creator_interpretation', policy)
                self.assertEqual(json_file.read_bytes(), before)

    def test_missing_or_changed_new_evidence_holds_new_sources_without_changing_nine_prior_routes(self):
        fixture = self.fixture()
        old = {sid: mapping.source_policy(sid) for sid in OLD_SAMPLES}
        self.assertEqual([value[1]['schema_version'] for value in old.values()], list(range(1, 10)))
        for key in ('manifest', *mapping.CITATIONS31_DOCUMENTS, 'direct bindings'):
            for missing in (True, False):
                with self.subTest(evidence=key, missing=missing):
                    path = self.root / ('missing' if missing else 'wrong-digest')
                    if not missing:
                        original = (mapping.CITATIONS31 if key == 'manifest' else
                                    mapping.CITATIONS31_DIRECT_BINDINGS if key == 'direct bindings' else
                                    mapping.ROOT / mapping.CITATIONS31_DOCUMENTS[key]['path'])
                        path.write_bytes(original.read_bytes() + b' ')
                    if key in ('manifest', 'direct bindings'):
                        attribute = 'CITATIONS31' if key == 'manifest' else 'CITATIONS31_DIRECT_BINDINGS'
                        replacement = patch.object(mapping, attribute, path)
                    else:
                        documents = copy.deepcopy(mapping.CITATIONS31_DOCUMENTS)
                        documents[key]['path'] = str(path)
                        replacement = patch.object(mapping, 'CITATIONS31_DOCUMENTS', documents)
                    with replacement:
                        with self.assertRaises((ValueError, OSError)):
                            fixture.runner().run()
                        self.assertEqual({sid: mapping.source_policy(sid) for sid in OLD_SAMPLES}, old)
                    self.assertEqual(fixture.transport.calls, [])
        self.assertFalse((draft.state_root(fixture.paths) / (fixture.prepared.source_id + '.modern-create-v1.intent.json')).exists())

    def test_held_whole_arrays_protected_sources_and_pair_members_cannot_enter_citations31(self):
        held = {'FGDC-771', 'FGDC-411', 'FGDC-287', 'FGDC-2235', 'FGDC-2668', 'FGDC-3599'}
        held.update(member['source_id'] for member in self.documents['basis_review']['held_members'])
        program = mapping.parse(mapping.PROGRAM20.read_bytes())
        held.update(member['source_id'] for member in program['retained_held_members'])
        self.assertIn('FGDC-3680', held)  # Literal Navis array remains unresolved.
        self.assertTrue({'FGDC-3814', 'FGDC-3816', 'FGDC-3817', 'FGDC-3838'} <= held)  # Farley suffix.
        self.assertTrue({'FGDC-545', 'FGDC-581'} <= held)  # UNaAMI remains a whole-array hold.
        self.assertTrue(held.isdisjoint(self.rows))
        for sid in sorted(held):
            with self.subTest(held=sid), self.assertRaises(ValueError):
                mapping.source_policy(sid)
        plan = mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']
        pairs = {sid for target in plan if len(target['source_ids']) == 2 for sid in target['source_ids']}
        self.assertTrue(pairs)
        self.assertTrue(pairs.isdisjoint(self.rows))
        self.assertTrue(set(mapping.PROTECTED).isdisjoint(self.rows))
        self.assertTrue({'FGDC-2953', 'FGDC-3181'} <= pairs)
        for sid in [*mapping.PROTECTED, 'FGDC-2953', 'FGDC-3181']:
            with self.subTest(excluded=sid), self.assertRaises(ValueError):
                mapping.reviewed_citation_source_policy(sid)

    def test_self_rehashed_manifest_cannot_change_scope_source_authority_context_or_ordered_array(self):
        fixture = self.fixture('FGDC-3809')
        index = next(i for i, row in enumerate(self.manifest['rows']) if row['source_id'] == 'FGDC-3809')
        for label, mutate in (
                ('missing member', lambda m: m['rows'].pop()),
                ('scope', lambda m: m['rows'][index].update(source_id='FGDC-771')),
                ('source', lambda m: m['rows'][index].update(source_sha256='0' * 64)),
                ('root', lambda m: m['rows'][index].update(source_root_sha256='0' * 64)),
                ('primary origin', lambda m: m['rows'][index]['primary_origins'][0].update(text='Invented')),
                ('plan', lambda m: m['rows'][index].update(source_plan_target_sha256='0' * 64)),
                ('authority kind', lambda m: m['rows'][index].update(creator_authority_kind='direct')),
                ('authority object', lambda m: m['rows'][index].update(creator_authority_object_sha256='0' * 64)),
                ('cohort', lambda m: m['rows'][index].update(creator_cohort=None)),
                ('legacy order', lambda m: m['rows'][index]['creators'].reverse()),
                ('modern order', lambda m: m['rows'][index]['modern_creators'].reverse()),
                ('truncated array', lambda m: m['rows'][index]['modern_creators'].pop()),
                ('person correction', lambda m: m['rows'][index]['modern_creators'][4]['person_or_org'].update(family_name='Elmajjati')),
                ('affiliation', lambda m: m['rows'][index]['modern_creators'][0].update(affiliations=[{'name': 'Invented'}])),
                ('role', lambda m: m['rows'][index]['modern_creators'][0].update(role={'id': 'supervisor'})),
                ('context missing', lambda m: m['rows'][index].update(additional_preservation_paragraphs=[])),
                ('context changed', lambda m: m['rows'][index].update(additional_preservation_paragraphs=['All identities verified.'])),
                ('review pointer', lambda m: m['rows'][index].update(independent_decision_pointer='/complete_array_decisions/0'))):
            with self.subTest(change=label):
                changed = copy.deepcopy(self.manifest)
                mutate(changed)
                path = self.root / 'self-rehashed.json'
                path.write_bytes(mapping.encode(changed))
                with patch.object(mapping, 'CITATIONS31', path), \
                        patch.object(mapping, 'CITATIONS31_SHA', mapping.sha(path.read_bytes())):
                    # Preparation must fail before a preexisting grant-binding mismatch.
                    with self.assertRaises(ValueError):
                        mapping.prepare(fixture.json_file, fixture.paths)
                self.assertEqual(fixture.transport.calls, [])
        self.assertEqual(mapping.prepare(fixture.json_file, fixture.paths), fixture.prepared)

    def test_original_payload_and_artifact_reference_changes_prevent_any_dispatch(self):
        for sid in ('FGDC-3793', 'FGDC-3809'):
            fixture = self.fixture(sid)
            before = fixture.json_file.read_bytes()
            payload = mapping.parse(before)
            replacements = [('creators', list(reversed(payload['metadata']['creators'])) if sid == 'FGDC-3809'
                             else [{'name': 'Mark Halverson'}]),
                            ('title', payload['metadata']['title'] + ' corrected'),
                            ('description', payload['metadata']['description'] + ' corrected'),
                            ('publication_date', '2026-10-06'), ('access_right', 'open'), ('license', 'cc-by-4.0')]
            for key, value in replacements:
                with self.subTest(source=sid, field=key):
                    changed = copy.deepcopy(payload)
                    changed['metadata'][key] = value
                    fixture.json_file.write_bytes(mapping.encode(changed))
                    with self.assertRaises(ValueError):
                        fixture.runner().run()
                    self.assertEqual(fixture.transport.calls, [])
            for reference in (None, {'manifest_path': str(mapping.PROFILE), 'manifest_sha256': MANIFEST_SHA}):
                with self.subTest(source=sid, reference=reference):
                    changed = copy.deepcopy(payload)
                    changed['artifact_policy']['creator_interpretation'] = reference
                    fixture.json_file.write_bytes(mapping.encode(changed))
                    with self.assertRaises(ValueError):
                        fixture.runner().run()
            fixture.json_file.write_bytes(before)
            copied = Path(fixture.paths.original_fgdc_dir) / (sid + '.xml')
            original = copied.read_bytes()
            copied.write_bytes(original + b' ')
            with self.assertRaises(ValueError):
                fixture.runner().run()
            copied.write_bytes(original)
            self.assertEqual(mapping.prepare(fixture.json_file, fixture.paths), fixture.prepared)
            self.assertEqual(fixture.transport.calls, [])

    def test_missing_changed_or_reordered_readback_context_holds_before_next_mutation(self):
        for corruption in ('missing', 'changed', 'moved', 'different source'):
            with self.subTest(corruption=corruption):
                fixture = self.fixture('FGDC-3793')
                expected = mapping.parse(fixture.prepared.body)['metadata']
                changed = copy.deepcopy(expected)
                block = changed['additional_descriptions'][0]
                context = '<p>' + html.escape(self.rows['FGDC-3793']['additional_preservation_paragraphs'][0]) + '</p>'
                if corruption == 'missing':
                    block['description'] = block['description'].replace(context, '')
                elif corruption == 'changed':
                    block['description'] = block['description'].replace('remains unresolved', 'has been corrected')
                elif corruption == 'moved':
                    block['description'] = block['description'].replace(context, '') + context
                else:
                    block['description'] = block['description'].replace(
                        context, '<p>' + html.escape(self.rows['FGDC-2597']['additional_preservation_paragraphs'][0]) + '</p>')
                self.assertNotEqual(changed, expected)
                with self.assertRaises(ValueError):
                    mapping.compare_metadata(changed, expected)

                def corrupt(index, status, value, *, actual=changed):
                    if index == 0:
                        value['metadata'] = copy.deepcopy(actual)
                    return status, value

                fixture.transport.change = corrupt
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual([call[0] for call in fixture.transport.calls], ['POST'])
                self.assertEqual(fixture.transport.calls[0][1], '/api/records')
                # A failed exact readback never licenses a create replay.
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(len(fixture.transport.calls), 1)

    def test_qa_enforces_both_authorities_and_community_flow_retries_without_new_writes(self):
        for sid in ('FGDC-3793', 'FGDC-3809'):
            with self.subTest(source=sid):
                fixture = self.fixture(sid)
                fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
                harness = PublicationFixture(fixture)
                documents = harness.ready()
                snapshot = mapping.parse(documents['snapshot'].read_bytes())
                duplicate = mapping.parse(documents['duplicate'].read_bytes())
                evidence = qa.assess(harness.prepared, harness.bound, snapshot, duplicate,
                                     now=PUBLICATION_NOW, community=harness.community_authority)
                self.assertEqual(evidence['prepared_evidence'], harness.prepared.evidence)
                expected_authority = mapping.PROFILE_SHA if sid == 'FGDC-3809' else MANIFEST_SHA
                self.assertEqual(harness.prepared.evidence['creator_profile_sha256'], expected_authority)
                for key, value in (
                        ('creator_profile_sha256', MANIFEST_SHA if sid == 'FGDC-3809' else mapping.PROFILE_SHA),
                        ('creator_authority_kind', 'direct' if sid == 'FGDC-3809' else 'creator426'),
                        ('creator_cohort', None if sid == 'FGDC-3809' else self.rows['FGDC-3809']['creator_cohort']),
                        ('schema_version', 9), ('policy', mapping.PROGRAM_POLICY)):
                    with self.subTest(source=sid, evidence=key):
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
                            qa.assess(prepared, bound, saved, proof, now=PUBLICATION_NOW,
                                      community=harness.community_authority)
                if sid == 'FGDC-3809':
                    continue  # The distinct authority is checked; no duplicate publication exercise.
                first = harness.runner(documents=documents).run()
                self.assertTrue(first['release_complete'])
                self.assertTrue(first['community_membership_verified'])
                self.assertEqual(first['counts'], {'get': 16, 'review': 1, 'submit': 1})
                writes = [call for call in harness.transport.calls if call[0] != 'GET']
                self.assertEqual([call[0] for call in writes], ['PUT', 'POST'])
                journal = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
                before = journal.read_bytes()
                draft_calls = list(fixture.transport.calls)
                again = harness.runner(documents=documents).run(read_only=True)
                self.assertTrue(again['release_complete'])
                self.assertEqual(again['counts'], publication.PUBLISH_LIMITS)
                self.assertEqual([call for call in harness.transport.calls if call[0] != 'GET'], writes)
                base, file = fixture.transport.base, fixture.transport.file
                # The publication fixture translates the published readback fence.
                expected_inner_gets = [('GET', base, None), ('GET', base + '/files', None),
                                       ('GET', file, None), ('GET', file + '/content', None),
                                       ('GET', base, None)]
                self.assertEqual(fixture.transport.calls, draft_calls + expected_inner_gets)
                self.assertEqual(journal.read_bytes(), before)

    def test_schema10_rejects_all_prior_runtimes_including_program20_before_historical_state_reads(self):
        fixture = self.fixture()
        self.assertEqual(fixture.prepared.evidence['schema_version'], 10)
        self.assertEqual(publication.PROGRAM20_RUNTIME, PROGRAM20_RUNTIME)
        runtimes = [getattr(publication, f'PR{number}_RUNTIME') for number in range(34, 47)]
        runtimes += [publication.REVIEWED194_RUNTIME, PROGRAM20_RUNTIME]
        before = {path: path.read_bytes() for path in fixture.root.rglob('*') if path.is_file()}
        for runtime in runtimes:
            with self.subTest(runtime=runtime):
                evidence = dict(fixture.prepared.evidence, runtime_sha256=runtime)
                self.assertNotEqual(runtime, fixture.prepared.evidence['runtime_sha256'])
                packet = self.root / ('backdated-' + runtime + '.json')
                packet.write_bytes(mapping.encode({'evidence': evidence, 'binding': mapping.sha(mapping.encode(evidence)),
                                                   'provider_requests': 0}))
                with patch.object(draft, 'read_document', wraps=draft.read_document) as reads:
                    with self.assertRaises(ValueError):
                        publication.bridge(fixture.json_file, fixture.paths, packet, fixture.grant_path, fixture.proof_path)
                self.assertEqual([call.args[0] for call in reads.call_args_list], [packet])
                self.assertEqual(fixture.transport.calls, [])
                self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_program20_historical_graph_bridges_preserving_all_receipts_sidecars_and_nonruntime_evidence(self):
        fixture = self.fixture('FGDC-355')
        fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
        harness = PublicationFixture(fixture)
        self.assertEqual(harness.prepared.evidence['schema_version'], 9)
        rebind_synthetic_sidecars(self, harness, PROGRAM20_RUNTIME)
        packet = mapping.parse(harness.packet.read_bytes())
        self.assertEqual(packet['evidence'], dict(harness.prepared.evidence, runtime_sha256=PROGRAM20_RUNTIME))
        originals = {path: path.read_bytes() for path in fixture.root.rglob('*') if path.is_file()}
        calls = list(fixture.transport.calls)
        prepared, bound = harness.bridge()
        self.assertEqual(prepared, harness.prepared)
        self.assertEqual(bound, harness.bound)
        self.assertEqual(bound['original_runtime_sha256'], PROGRAM20_RUNTIME)
        self.assertNotEqual(bound['runtime_sha256'], PROGRAM20_RUNTIME)
        self.assertEqual(bound['runtime_sha256'], prepared.evidence['runtime_sha256'])
        self.assertEqual(fixture.transport.calls, calls)
        self.assertEqual({path: path.read_bytes() for path in originals}, originals)
        journal = mapping.parse(Path(fixture.paths.uploads_registry_path + '.modern-v1.json').read_bytes())
        self.assertEqual(journal['targets']['FGDC-355']['counts'],
                         {'get': 5, 'create': 1, 'init': 1, 'content': 1, 'commit': 0})


if __name__ == '__main__':
    unittest.main()
