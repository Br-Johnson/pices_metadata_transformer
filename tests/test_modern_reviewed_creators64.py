"""Creators64: a proposal pinned behind an independent review that starts closed.

The proposal, mapping manifest and pending review are read statically. The 14 admitted
sources are freshly prepared only under a synthetic approved review; the 50 held proposals,
the protected records and every prior policy are checked to be unaffected. No transport.
"""

import copy
import html
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scripts import modern_bulk as bulk
from scripts import modern_singleton as mapping
from scripts.agent_qa import assess_source
from scripts.citation_creator_interpretation import source_element
from scripts.path_config import OutputPaths
from tests import modern_singleton_fixtures as fixtures

MANIFEST_SHA = '966e24e6509caa4a09a066f7ee712d44e451f2aed505770f81070b47886997d5'
PROPOSALS_SHA = '69dcb3fede50f6b55d79721e6189a6975b8e2c7d9b60c97f8920145e3eb5f111'
PENDING_REVIEW_SHA = 'e5bf62776e936e3badc12d0e31f97b914f991b539cbae35b6f90bff07e141458'  # round 2, before the review
REVIEW_SHA = '522ed5f563c5aae4f13bc42fedbf1b2c07724c0b8436d6639b388cbeb1277694'  # the independent review: 56 approved
UNAAMI = tuple('FGDC-' + str(i) for i in (545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 556, 557, 558,
                                            559, 560, 573, 574, 575, 576, 578, 579, 580, 581))
WAKATAKE = tuple('FGDC-' + str(i) for i in (3680, 3681, 3800, 3802, 3803, 3804, 3805, 3806, 3807, 3808))
# Round 2 (2026-10-22): the 14 first-round vectors (885, 2587 and 3817 re-proposed), the 23 Unaami and six
# product/system credits admitted by Brett as organisations, and 14 spelling conflicts resolved from the
# records' own bylines by Brett's decision; seven compound, venue and unnamed credits stay held.
ADMITTED = tuple(sorted(tuple('FGDC-' + str(i) for i in (419, 542, 715, 859, 885, 887, 893, 2234, 2296, 2413, 2587,
                                                         2668, 2674, 2683, 3599, 3814, 3816, 3817, 3825, 3831, 3838,
                                                         3851, 3873, 3970)) + UNAAMI + WAKATAKE,
                        key=lambda s: int(s[5:])))
HELD_SAMPLE = ('FGDC-287', 'FGDC-411', 'FGDC-771', 'FGDC-2229', 'FGDC-2235', 'FGDC-2824', 'FGDC-3786')
OLD_SAMPLES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839', 'FGDC-1319',
               'FGDC-59', 'FGDC-3875', 'FGDC-1', 'FGDC-355', 'FGDC-184')
TYPES = mapping.parse((mapping.ROOT / 'docs/readiness/2026-10-22/resource_types_creators64_proposal.json').read_bytes())


def approved_review(directory, decisions=None, **changes):
    """A synthetic approved copy of the pending review, written under `directory`."""
    review = mapping.parse(mapping.CREATORS64_REVIEW.read_bytes())
    members = review['members']
    decisions = decisions or {row['source_id']: 'approved' for row in members}
    review.update(status='approved', reviewer='Offline fixture reviewer', reviewed_at='2026-10-22T00:00:00+00:00',
                  decisions={sid: {'decision': decision, 'note': None} for sid, decision in decisions.items()},
                  approved_members=[row for row in members if decisions.get(row['source_id']) == 'approved'],
                  held_members=[row for row in members if decisions.get(row['source_id']) != 'approved'])
    review.update(changes)
    path = Path(directory) / 'creators64-review.json'
    path.write_bytes(mapping.encode(review))
    return path


@contextmanager
def review_file(path):
    with patch.object(mapping, 'CREATORS64_REVIEW', path), \
            patch.object(mapping, 'CREATORS64_REVIEW_SHA', mapping.sha(path.read_bytes())):
        yield


def policy_or_hold(sid):
    try:
        return mapping.source_policy(sid)[1]['policy']
    except mapping.Held:
        return None


class ModernReviewedCreators64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.CREATORS64.read_bytes())
        cls.proposals = mapping.parse(mapping.CREATORS64_PROPOSALS.read_bytes())
        cls.review = mapping.parse(mapping.CREATORS64_REVIEW.read_bytes())
        cls.rows = {row['source_id']: row for row in cls.manifest['rows']}
        cls.by_source = {row['source_id']: row for row in cls.proposals['proposals']}
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=list(ADMITTED))

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.approved = approved_review(self.root)

    def paths(self):
        copied = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(copied.cleanup)
        prepared = Path(copied.name) / 'prepared'
        import shutil
        shutil.copytree(self.prepared_root, prepared)
        return OutputPaths(str(prepared), 'production')

    def test_pinned_files_proposal_scope_and_the_independent_review(self):
        for path, digest, expected in ((mapping.CREATORS64, mapping.CREATORS64_SHA, MANIFEST_SHA),
                                       (mapping.CREATORS64_PROPOSALS, mapping.CREATORS64_PROPOSALS_SHA, PROPOSALS_SHA),
                                       (mapping.CREATORS64_REVIEW, mapping.CREATORS64_REVIEW_SHA, REVIEW_SHA)):
            self.assertEqual(digest, expected)
            self.assertEqual(mapping.sha(path.read_bytes()), expected)
        reconciliation = mapping.parse((mapping.ROOT / 'docs/readiness/2026-10-06/modern_program20_remaining100_reconciliation.json').read_bytes())
        remaining = {row['source_id'] for row in reconciliation['remaining100_after_set_subtraction']}
        citations = {row['source_id'] for row in mapping.parse(mapping.CITATIONS31.read_bytes())['members']}
        members = sorted(remaining - citations - set(mapping.PROTECTED), key=lambda s: int(s[5:]))
        self.assertEqual(len(members), 64)
        self.assertEqual([row['source_id'] for row in self.proposals['members']], members)
        self.assertEqual(Counter(row['decision'] for row in self.proposals['proposals']), {'admit': 57, 'hold': 7})
        self.assertEqual(len(ADMITTED), 57)
        self.assertEqual(tuple(self.rows), ADMITTED)
        self.assertEqual(self.manifest['member_count'], 57)
        self.assertEqual(self.manifest['authority_counts'], {'creator426': 55, 'direct': 2})
        self.assertEqual(self.manifest['modern_creator_object_count'], 192)
        self.assertEqual(self.proposals['round'], 2)
        self.assertEqual(set(self.proposals['owner_decisions']), {'unaami_as_organisation', 'credited_name_as_org', 'records_own_byline'})
        self.assertEqual(self.review['status'], 'approved')
        self.assertIn('independent reviewer', self.review['reviewer'])
        self.assertEqual([row['source_id'] for row in self.review['held_members']], ['FGDC-3851'])
        self.assertEqual(self.review['mapping_manifest_sha256'], MANIFEST_SHA)
        self.assertEqual(self.review['proposals_sha256'], PROPOSALS_SHA)
        self.assertEqual(self.review['members'], self.manifest['members'])
        # The review admits exactly its approved members; its hold, the proposal's holds and others stay held.
        for sid in (sid for sid in ADMITTED if sid != 'FGDC-3851'):
            with self.subTest(source=sid):
                self.assertEqual(mapping.source_policy(sid)[1]['policy'], mapping.CREATORS64_POLICY)
        for sid in ('FGDC-3851', *HELD_SAMPLE, *mapping.PROTECTED, 'FGDC-2953'):
            with self.subTest(source=sid), self.assertRaises(mapping.Held):
                mapping.source_policy(sid)
        self.assertEqual([mapping.source_policy(sid)[1]['schema_version'] for sid in OLD_SAMPLES], list(range(1, 11)))

    def test_rows_rebuild_from_proposals_originals_plan_and_creator_authorities(self):
        profiles = {row['profile']: row for row in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']}
        bindings = {row['source_id']: row for row in mapping.pinned(
            mapping.CITATIONS31_DIRECT_BINDINGS, mapping.CITATIONS31_DIRECT_BINDINGS_SHA)['members']}
        targets = {row['record_target_id']: row for row in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        held = {row['source_id'] for row in self.proposals['held_members']}
        self.assertEqual(len(held), 7)
        for proposal in self.proposals['proposals']:
            sid = proposal['source_id']
            with self.subTest(source=sid):
                raw = (mapping.ROOT / proposal['source_path']).read_bytes()
                root = ET.fromstring(raw)
                self.assertEqual((len(raw), mapping.sha(raw)), (proposal['source_bytes'], proposal['source_sha256']))
                self.assertEqual(mapping.sha(mapping.encode(source_element(root))), proposal['source_root_sha256'])
                self.assertEqual([source_element(n) for n in root.findall('./idinfo/citation/citeinfo/origin')],
                                 proposal['primary_origin_elements'])
                self.assertTrue(proposal['reason'].strip())
                self.assertTrue(any(item['kind'] == 'xml' and item['label'] == 'citation origin' for item in proposal['evidence']))
                for item in proposal['evidence']:
                    if item['kind'] == 'file':
                        text = (mapping.ROOT / item['path']).read_text(encoding='utf-8')
                        self.assertEqual(mapping.sha((mapping.ROOT / item['path']).read_bytes()), item['sha256'])
                        self.assertIn(item['quote'], text)
                if proposal['decision'] == 'hold':
                    self.assertIn(sid, held)
                    self.assertIsNone(proposal['proposed_creators'])
                    self.assertNotIn(sid, self.rows)
                    continue
                row = self.rows[sid]
                self.assertEqual(row['modern_creators'], proposal['proposed_creators'])
                self.assertEqual(row['creators'], proposal['legacy_creators'])
                self.assertEqual(row['additional_preservation_paragraphs'], [proposal['additional_preservation_paragraph']])
                self.assertEqual(row['proposal_row_sha256'], mapping.sha(mapping.encode(proposal)))
                self.assertEqual(self.proposals['proposals'][int(row['proposal_row_pointer'].rsplit('/', 1)[1])], proposal)
                self.assertEqual(mapping.sha(mapping.encode(targets[sid])), row['source_plan_target_sha256'])
                self.assertEqual(targets[sid]['source_semantic_status'], 'supported')
                self.assertEqual(targets[sid]['source_ids'], [sid])
                if row['creator_authority_kind'] == 'creator426':
                    profile = profiles[row['creator_cohort']]
                    self.assertEqual(profile['creators'], row['creators'])
                    self.assertIn({'source_id': sid, 'source_sha256': row['source_sha256']}, profile['members'])
                    self.assertEqual(mapping.sha(mapping.encode(profile)), row['creator_authority_object_sha256'])
                else:
                    self.assertIsNone(row['creator_cohort'])
                    self.assertEqual(bindings[sid]['complete_creator_objects'], row['creators'])
                    self.assertEqual(mapping.sha(mapping.encode(bindings[sid])), row['creator_authority_object_sha256'])
                for creator in row['modern_creators']:
                    mapping.modern_creator_shape(creator)
                # Every literal family name and organisation name is a substring of the citation origin
                # or of the source's own reference line: nothing is corrected or imported.
                evidence = ' '.join(item['text'] for item in proposal['evidence'] if item['kind'] == 'xml')
                for creator in row['modern_creators']:
                    person = creator['person_or_org']
                    for key in ('family_name', 'name'):
                        if key in person:
                            self.assertIn(person[key], evidence)
                    for affiliation in creator.get('affiliations', []):
                        self.assertIn(affiliation['name'], evidence)
        self.assertEqual(self.rows['FGDC-3814']['modern_creators'], self.rows['FGDC-3816']['modern_creators'])
        self.assertEqual(self.rows['FGDC-885']['modern_creators'][0]['person_or_org'],
                         {'type': 'personal', 'family_name': 'Farley', 'given_name': 'Edward V., Jr.'})
        self.assertEqual(self.rows['FGDC-885']['modern_creators'][2]['person_or_org']['given_name'], 'Charles M., III')
        self.assertNotIn('editor', self.rows['FGDC-2587']['additional_preservation_paragraphs'][0])
        self.assertIn('of Auke Bay Laboratory, Alaska Fisheries Science Center, NMFS, Juneau, AK, USA',
                      self.rows['FGDC-3817']['additional_preservation_paragraphs'][0])
        self.assertNotIn('NOAA', self.rows['FGDC-3817']['additional_preservation_paragraphs'][0])
        for sid in UNAAMI:
            self.assertEqual(self.rows[sid]['modern_creators'],
                             [{'person_or_org': {'type': 'organizational', 'name': 'Unaami Arctic Data Collection'}}])
            self.assertEqual(self.rows[sid]['creators'], [{'name': 'Unaami Arctic Data Collection'}])
        for sid, name in (('FGDC-419', 'Word Wright'), ('FGDC-715', 'CIA World Bank II'),
                          ('FGDC-859', "Satellite Pour l'Ovservation de la Terre (SPOT)"),
                          ('FGDC-2296', 'FORUT (Campaign for Development and Solidarity)'),
                          ('FGDC-3873', 'Prince William Sound Nowcast-Forecast System (PWS NFS)'),
                          ('FGDC-3970', 'Nationwide Ocean Wave Information Network for Ports and HArbourS (NOWPHAS), Japan')):
            self.assertEqual(self.rows[sid]['modern_creators'], [{'person_or_org': {'type': 'organizational', 'name': name}}])
            self.assertEqual(self.rows[sid]['creators'], [{'name': name}])
        # A spelling taken from the record's own byline: the quoted element carries it, the paragraph keeps the citation's.
        for sid, family, cited in (*((sid, 'Davis', 'Navis') for sid in WAKATAKE), ('FGDC-3825', 'Urano', 'Uran'),
                                   ('FGDC-3831', 'Bugaev', 'Bugae'), ('FGDC-893', 'Kondzela', 'Kandzela'),
                                   ('FGDC-3851', 'Hermann', 'Herman')):
            with self.subTest(source=sid):
                proposal = self.by_source[sid]
                self.assertEqual(proposal['owner_decision'], 'records_own_byline')
                self.assertIn(family, proposal['byline_spelling_evidence'][family]['text'])
                self.assertIn(family, [c['person_or_org'].get('family_name') for c in self.rows[sid]['modern_creators']])
                self.assertNotIn(cited, [c['person_or_org'].get('family_name') for c in self.rows[sid]['modern_creators']])
                self.assertIn(cited, self.rows[sid]['additional_preservation_paragraphs'][0])
                self.assertIn(cited, ' '.join(c['name'] for c in self.rows[sid]['creators']))
        self.assertEqual(self.rows['FGDC-3825']['modern_creators'][8]['person_or_org'],
                         {'type': 'personal', 'family_name': 'Urano', 'given_name': 'Akihisa'})
        self.assertEqual(self.rows['FGDC-3851']['modern_creators'],
                         [{'person_or_org': {'type': 'personal', 'family_name': 'Hermann', 'given_name': 'Al'}}])
        self.assertEqual(self.rows['FGDC-2587']['modern_creators'][0]['person_or_org']['given_name'], 'G. Von')
        self.assertEqual(self.rows['FGDC-2413']['modern_creators'],
                         [{'person_or_org': {'type': 'personal', 'family_name': 'Wespestad', 'given_name': 'Vidar'}}])
        self.assertIn('editor', self.rows['FGDC-2413']['additional_preservation_paragraphs'][0])
        self.assertEqual(self.rows['FGDC-3599']['modern_creators'][0]['person_or_org']['type'], 'organizational')
        self.assertEqual(TYPES['types'], {sid: self.by_source[sid]['proposed_resource_type'] for sid in ADMITTED})
        self.assertTrue(set(TYPES['types'].values()) <= {'dataset', 'publication-report'})

    def test_approved_review_admits_the_fourteen_repeatably_and_v2_wires_validate(self):
        paths = self.paths()
        with review_file(self.approved):
            for sid in ADMITTED:
                with self.subTest(source=sid):
                    json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
                    before = json_file.read_bytes()
                    prepared = mapping.prepare(json_file, paths)
                    self.assertEqual(prepared, mapping.prepare(json_file, paths))
                    metadata, source_sha, artifact, _ = assess_source(json_file, paths)
                    row = self.rows[sid]
                    meta = mapping.parse(prepared.body)['metadata']
                    context = ''.join('<p>' + html.escape(v) + '</p>' for v in row['additional_preservation_paragraphs'])
                    preserved = meta['additional_descriptions'][0]['description']
                    self.assertEqual(preserved, '<p>' + mapping.PRESERVATION_LABEL + '</p>' + context
                                     + '<pre>' + html.escape(mapping.encode(metadata).decode()) + '</pre>')
                    self.assertEqual(metadata['creators'], row['creators'])
                    self.assertEqual(meta['creators'], row['modern_creators'])
                    self.assertEqual((metadata['access_right'], metadata['license']), ('restricted', ''))
                    self.assertEqual(prepared.xml, (mapping.ROOT / row['source_path']).read_bytes())
                    self.assertEqual(source_sha, row['source_sha256'])
                    self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                    self.assertEqual(prepared.evidence['schema_version'], 11)
                    self.assertEqual(prepared.evidence['policy'], mapping.CREATORS64_POLICY)
                    self.assertEqual(prepared.evidence['mapping_manifest_sha256'], MANIFEST_SHA)
                    self.assertEqual(prepared.evidence['creator_authority_kind'], row['creator_authority_kind'])
                    self.assertEqual(prepared.evidence['creator_profile_sha256'],
                                     mapping.PROFILE_SHA if row['creator_authority_kind'] == 'creator426' else MANIFEST_SHA)
                    policy = mapping.parse(before)['artifact_policy']
                    if row['creator_authority_kind'] == 'creator426':
                        self.assertEqual(policy['creator_interpretation']['manifest_sha256'], mapping.PROFILE_SHA)
                    else:
                        self.assertNotIn('creator_interpretation', policy)
                    self.assertEqual(json_file.read_bytes(), before)
                    for resource_type in ('dataset', 'publication-report'):
                        wire = bulk.WireV2(prepared, resource_type)
                        meta2 = mapping.parse(wire.body)['metadata']
                        self.assertEqual(meta2['creators'], row['modern_creators'])
                        self.assertEqual(meta2['resource_type'], {'id': resource_type})
                        self.assertEqual(wire.evidence['v1_wire_sha256'], prepared.evidence['wire_sha256'])
            # Approval does not reach a held proposal, a protected record, a pair member or a prior policy.
            for sid in (*HELD_SAMPLE, *mapping.PROTECTED, 'FGDC-2953'):
                with self.subTest(held=sid), self.assertRaises(mapping.Held):
                    mapping.source_policy(sid)
            self.assertEqual([mapping.source_policy(sid)[1]['schema_version'] for sid in OLD_SAMPLES], list(range(1, 11)))

    def test_review_must_be_approved_bound_and_complete_and_may_hold_single_members(self):
        paths = self.paths()
        json_file = Path(paths.zenodo_json_dir) / 'FGDC-2413.json'
        partial = approved_review(self.root / 'partial', decisions={
            **{sid: 'approved' for sid in ADMITTED}, 'FGDC-2413': 'held'}) if (self.root / 'partial').mkdir() is None else None
        with review_file(partial):
            with self.assertRaises(mapping.Held):
                mapping.prepare(json_file, paths)
            self.assertEqual(mapping.source_policy('FGDC-885')[1]['policy'], mapping.CREATORS64_POLICY)
        for label, changes in (
                ('status', {'status': 'proposal pending independent review'}),
                ('other status', {'status': 'APPROVED'}),
                ('no reviewer', {'reviewer': None}),
                ('blank reviewer', {'reviewer': ' '}),
                ('no time', {'reviewed_at': None}),
                ('manifest binding', {'mapping_manifest_sha256': '0' * 64}),
                ('proposal binding', {'proposals_sha256': '0' * 64}),
                ('kind', {'kind': 'modern-reviewed-citations31-v1'}),
                ('policy', {'policy': mapping.CITATIONS31_POLICY}),
                ('members', {'members': self.review['members'][:-1]}),
                ('approved list', {'approved_members': self.review['members'][:-1]}),
                ('extra decision', {'decisions': {**{sid: {'decision': 'approved', 'note': None} for sid in ADMITTED},
                                                  'FGDC-545': {'decision': 'approved', 'note': None}}}),
                ('nothing approved', {'decisions': {sid: {'decision': 'held', 'note': None} for sid in ADMITTED},
                                      'approved_members': [], 'held_members': self.review['members']})):
            with self.subTest(change=label):
                (self.root / label).mkdir()
                path = approved_review(self.root / label, **changes)
                with review_file(path), self.assertRaises(mapping.Held):
                    mapping.prepare(json_file, paths)
        # An approved review whose digest is not the pinned one is just as closed.
        with patch.object(mapping, 'CREATORS64_REVIEW', self.approved), self.assertRaises(mapping.Held):
            mapping.prepare(json_file, paths)

    def test_rehashed_manifest_or_proposals_cannot_change_vectors_scope_or_context(self):
        paths = self.paths()
        json_file = Path(paths.zenodo_json_dir) / 'FGDC-2668.json'
        index = next(i for i, row in enumerate(self.manifest['rows']) if row['source_id'] == 'FGDC-2668')
        with review_file(self.approved):
            baseline = mapping.prepare(json_file, paths)
            for label, mutate in (
                    ('missing member', lambda m: m['rows'].pop()),
                    ('held source', lambda m: m['rows'][index].update(source_id='FGDC-287')),
                    ('source hash', lambda m: m['rows'][index].update(source_sha256='0' * 64)),
                    ('root', lambda m: m['rows'][index].update(source_root_sha256='0' * 64)),
                    ('origin', lambda m: m['rows'][index]['primary_origins'][0].update(text='Invented')),
                    ('plan', lambda m: m['rows'][index].update(source_plan_target_sha256='0' * 64)),
                    ('authority kind', lambda m: m['rows'][index].update(creator_authority_kind='creator426')),
                    ('authority object', lambda m: m['rows'][index].update(creator_authority_object_sha256='0' * 64)),
                    ('legacy array', lambda m: m['rows'][index]['creators'].append({'name': 'Invented'})),
                    ('modern order', lambda m: m['rows'][index]['modern_creators'].reverse()),
                    ('dropped Phillips', lambda m: m['rows'][index]['modern_creators'].pop()),
                    ('spelling', lambda m: m['rows'][index]['modern_creators'][0]['person_or_org'].update(family_name='Nelsen')),
                    ('suffix moved', lambda m: m['rows'][index]['modern_creators'][2]['person_or_org'].update(
                        family_name='Barber, Jr.', given_name='John H.')),
                    ('affiliation', lambda m: m['rows'][index]['modern_creators'][0].update(affiliations=[{'name': 'U.S. Geological Survey'}])),
                    ('role', lambda m: m['rows'][index]['modern_creators'][0].update(role={'id': 'editor'})),
                    ('identifier', lambda m: m['rows'][index]['modern_creators'][0]['person_or_org'].update(identifiers=[])),
                    ('context', lambda m: m['rows'][index].update(additional_preservation_paragraphs=['All affiliations verified.'])),
                    ('pointer', lambda m: m['rows'][index].update(proposal_row_pointer='/proposals/0'))):
                with self.subTest(change=label):
                    changed = copy.deepcopy(self.manifest)
                    mutate(changed)
                    path = self.root / 'rehashed-manifest.json'
                    path.write_bytes(mapping.encode(changed))
                    with patch.object(mapping, 'CREATORS64', path), \
                            patch.object(mapping, 'CREATORS64_SHA', mapping.sha(path.read_bytes())), \
                            self.assertRaises(mapping.Held):
                        mapping.prepare(json_file, paths)
            # Rewriting the proposals (and the manifest from them) breaks the review's binding.
            proposals = copy.deepcopy(self.proposals)
            target = next(row for row in proposals['proposals'] if row['source_id'] == 'FGDC-2668')
            target['proposed_creators'].pop()
            proposals_path = self.root / 'rehashed-proposals.json'
            proposals_path.write_bytes(mapping.encode(proposals))
            manifest = copy.deepcopy(self.manifest)
            manifest['rows'][index]['modern_creators'].pop()
            manifest['rows'][index]['proposal_row_sha256'] = mapping.sha(mapping.encode(target))
            manifest['proposals_sha256'] = mapping.sha(proposals_path.read_bytes())
            manifest['modern_creator_object_count'] -= 1
            manifest_path = self.root / 'rehashed-manifest-2.json'
            manifest_path.write_bytes(mapping.encode(manifest))
            with patch.object(mapping, 'CREATORS64_PROPOSALS', proposals_path), \
                    patch.object(mapping, 'CREATORS64_PROPOSALS_SHA', mapping.sha(proposals_path.read_bytes())), \
                    patch.object(mapping, 'CREATORS64', manifest_path), \
                    patch.object(mapping, 'CREATORS64_SHA', mapping.sha(manifest_path.read_bytes())), \
                    self.assertRaises(mapping.Held):
                mapping.prepare(json_file, paths)
            self.assertEqual(mapping.prepare(json_file, paths), baseline)

    def test_changed_payload_source_copy_or_authority_reference_holds(self):
        paths = self.paths()
        with review_file(self.approved):
            for sid in ('FGDC-885', 'FGDC-3599'):
                json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
                original = json_file.read_bytes()
                payload = mapping.parse(original)
                # The abstract is an editable field for every policy; the executor's binding, not
                # preparation, catches a changed description. The fields below are source-bound.
                for key, value in (('creators', [{'name': 'Invented'}]), ('title', payload['metadata']['title'] + ' changed'),
                                   ('publication_date', '2026-10-22'), ('access_right', 'open'), ('license', 'cc-by-4.0')):
                    with self.subTest(source=sid, field=key):
                        changed = copy.deepcopy(payload)
                        changed['metadata'][key] = value
                        json_file.write_bytes(mapping.encode(changed))
                        with self.assertRaises(ValueError):
                            mapping.prepare(json_file, paths)
                kind = self.rows[sid]['creator_authority_kind']
                wrong = {'manifest_path': 'docs/readiness/2026-10-04/source_citation_credits_426.json',
                         'manifest_sha256': mapping.DFO_PROFILE_SHA if kind == 'creator426' else mapping.PROFILE_SHA}
                for reference in (None, wrong):
                    with self.subTest(source=sid, reference=reference):
                        changed = copy.deepcopy(payload)
                        changed['artifact_policy']['creator_interpretation'] = reference
                        json_file.write_bytes(mapping.encode(changed))
                        with self.assertRaises(ValueError):
                            mapping.prepare(json_file, paths)
                json_file.write_bytes(original)
                copied = Path(paths.original_fgdc_dir) / (sid + '.xml')
                raw = copied.read_bytes()
                copied.write_bytes(raw + b' ')
                with self.assertRaises(ValueError):
                    mapping.prepare(json_file, paths)
                copied.write_bytes(raw)
                mapping.prepare(json_file, paths)

    def test_withdrawn_evidence_holds_members_and_leaves_ten_prior_policies_alone(self):
        paths = self.paths()
        json_file = Path(paths.zenodo_json_dir) / 'FGDC-3838.json'
        old = {sid: mapping.source_policy(sid) for sid in OLD_SAMPLES}
        for attribute in ('CREATORS64', 'CREATORS64_PROPOSALS'):
            for missing in (True, False):
                with self.subTest(evidence=attribute, missing=missing):
                    path = self.root / (attribute + ('-missing' if missing else '-changed'))
                    if not missing:
                        path.write_bytes(getattr(mapping, attribute).read_bytes() + b' ')
                    with review_file(self.approved), patch.object(mapping, attribute, path):
                        with self.assertRaises((ValueError, OSError)):
                            mapping.prepare(json_file, paths)
                        self.assertEqual({sid: mapping.source_policy(sid) for sid in OLD_SAMPLES}, old)


if __name__ == '__main__':
    unittest.main()
