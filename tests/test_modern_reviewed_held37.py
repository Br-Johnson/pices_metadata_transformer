"""Held37: the 37 sources Brett cleared on 2026-10-23, behind a proposal and a review that starts closed.

The decisions file, the three classification evidence manifests (decided scope 926, source credits 436,
metadata date corrections 5), the proposal, the mapping manifest and the pending review are read
statically. The 36 admitted sources are classified with the lane manifest set and freshly prepared only
under a synthetic approved review; FGDC-2817, the six records Brett kept held, the two he retired, the
protected records and every prior policy are checked to be unaffected. No transport.
"""

import copy
import hashlib
import html
import shutil
import socket
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scripts import citation_creator_interpretation as credits
from scripts import metadata_date_correction as dates
from scripts import modern_bulk as bulk
from scripts import modern_singleton as mapping
from scripts import modern_wire_v2 as wire_v2
from scripts import source_scope_attestation as scope
from scripts.agent_qa import assess_source
from scripts.citation_creator_interpretation import source_element
from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths

REPO = mapping.ROOT
DOCS = REPO / 'docs/readiness/2026-10-23'
MANIFEST_SHA = '5f63983694a33ff6df365bbba79ce95e4fe473d5f484fe7d097b812fd656afe0'
PROPOSALS_SHA = '3a543430de6f9ffe4ca7f30db3a135476c6a6735de45db08f490a5fbe7078b0d'
PENDING_REVIEW_SHA = 'd25bf58b29a396659b005bdb0e471a2e281cf83763fe667b7649a3f6574113a9'
DECISIONS_SHA = '47ec54fb08eb2748fac64a74b6b0728bb4869ffca5cef17f0c08921f53d2c7af'
REVIEWED_AT = '2026-10-23T22:00:00+00:00'  # the lane's fixed classification time, after Brett's decisions
ACCESS = tuple('FGDC-' + str(i) for i in (227, 288, 572, 648, 710, 711, 758, 759, 761, 766, 802, 862, 870, 1770, 1771,
                                            1864, 3687, 4027, 4039, 1318, 1994, 4063))
CREATORS = tuple('FGDC-' + str(i) for i in (1206, 2817, 2586, 3683, 3975, 3976, 3977, 3978, 3919, 3920))
DATES = tuple('FGDC-' + str(i) for i in (4139, 4161, 4181, 1422, 1423))
MEMBERS = tuple(sorted(ACCESS + CREATORS + DATES, key=lambda s: int(s[5:])))
HELD = ('FGDC-2817',)
ADMITTED = tuple(sid for sid in MEMBERS if sid not in HELD)
STAY_HELD = ('FGDC-909', 'FGDC-3850', 'FGDC-4185', 'FGDC-21', 'FGDC-4077', 'FGDC-4184')
RETIRED = ('FGDC-3373', 'FGDC-3484')
OLD_SAMPLES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839', 'FGDC-1319',
               'FGDC-59', 'FGDC-3875', 'FGDC-1', 'FGDC-355', 'FGDC-184', 'FGDC-885')
CORRECTED = {'FGDC-4139': '2008-02-07', 'FGDC-4161': '2008-02-07', 'FGDC-4181': '2008-02-07',
             'FGDC-1422': '2003-05-30', 'FGDC-1423': '2003-05-30'}


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def prepare_held37_sources(directory, ids=MEMBERS):
    """Classify the lane's sources offline with the runbook manifest set plus the lane's three evidence manifests."""
    root = Path(directory)
    source = root / 'sources'
    source.mkdir()
    for sid in ids:
        shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
    old, previous, docs = REPO / 'docs/readiness/2026-10-02', REPO / 'docs/readiness/2026-10-03', REPO / 'docs/readiness/2026-10-04'
    options = {
        'authority_manifest': old / 'rehosting_authority.json',
        'access_interpretation_manifest': old / 'contact_source_interpretation.json',
        'creator_interpretation_manifest': old / 'exxon_citation_interpretation.json',
        'contributor_access_interpretation_manifest': old / 'contributor_source_interpretation.json',
        'collective_creator_interpretation_manifest': previous / 'dfo_staff_citation_interpretation.json',
        'institution_creator_interpretation_manifest': mapping.HELD37_CREDITS,
        'source_link_interpretation_manifest': previous / 'historical_dataset_linkage_21.json',
        'source_title_interpretation_manifest': docs / 'source_display_titles_42.json',
        'source_scope_attestation_manifest': mapping.HELD37_SCOPE,
        'dataset_access_interpretation_manifest': docs / 'finite_source_resource_access_655.json',
        'metadata_date_correction_manifest': mapping.HELD37_DATES,
    }
    output = root / 'prepared'
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline classification')):
        report = classify_collection(source, output, REVIEWED_AT, **options)
    return output, report


def approved_review(directory, decisions=None, **changes):
    """A synthetic approved copy of the pending review, written under `directory`."""
    review = mapping.parse(mapping.HELD37_REVIEW.read_bytes())
    members = review['members']
    decisions = decisions or {row['source_id']: 'approved' for row in members}
    review.update(status='approved', reviewer='Offline fixture reviewer', reviewed_at='2026-10-23T23:00:00+00:00',
                  decisions={sid: {'decision': decision, 'note': None} for sid, decision in decisions.items()},
                  approved_members=[row for row in members if decisions.get(row['source_id']) == 'approved'],
                  held_members=[row for row in members if decisions.get(row['source_id']) != 'approved'])
    review.update(changes)
    path = Path(directory) / 'held37-review.json'
    path.write_bytes(mapping.encode(review))
    return path


@contextmanager
def review_file(path):
    with patch.object(mapping, 'HELD37_REVIEW', path), \
            patch.object(mapping, 'HELD37_REVIEW_SHA', mapping.sha(path.read_bytes())):
        yield


class ModernReviewedHeld37Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.HELD37.read_bytes())
        cls.proposals = mapping.parse(mapping.HELD37_PROPOSALS.read_bytes())
        cls.review = mapping.parse(mapping.HELD37_REVIEW.read_bytes())
        cls.decisions = mapping.parse(mapping.HELD37_DECISIONS.read_bytes())
        cls.rows = {row['source_id']: row for row in cls.manifest['rows']}
        cls.by_source = {row['source_id']: row for row in cls.proposals['proposals']}
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root, cls.report = prepare_held37_sources(cls.sources.name)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.approved = approved_review(self.root)

    def paths(self):
        copied = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(copied.cleanup)
        prepared = Path(copied.name) / 'prepared'
        shutil.copytree(self.prepared_root, prepared)
        return OutputPaths(str(prepared), 'production')

    def test_pinned_files_decisions_scope_and_the_closed_review(self):
        for path, digest, expected in ((mapping.HELD37, mapping.HELD37_SHA, MANIFEST_SHA),
                                       (mapping.HELD37_PROPOSALS, mapping.HELD37_PROPOSALS_SHA, PROPOSALS_SHA),
                                       (mapping.HELD37_REVIEW, mapping.HELD37_REVIEW_SHA, PENDING_REVIEW_SHA),
                                       (mapping.HELD37_DECISIONS, mapping.HELD37_DECISIONS_SHA, DECISIONS_SHA),
                                       (mapping.HELD37_CREDITS, credits.SOURCE_CREDIT_436_MANIFEST_SHA256, None),
                                       (mapping.HELD37_SCOPE, scope.DECIDED_MANIFEST_SHA256, None),
                                       (mapping.HELD37_DATES, dates.MANIFEST_SHA256, None)):
            with self.subTest(path=path.name):
                self.assertEqual(mapping.sha(path.read_bytes()), digest)
                if expected:
                    self.assertEqual(digest, expected)
        # The members are exactly the sources the decisions file clears; nothing held or retired is among them.
        cleared = {sid for row in self.decisions['decisions'] if row['effect'] != 'stays held' and row['question'] != 'D1'
                   for sid in row['sources']}
        self.assertEqual(cleared, set(MEMBERS))
        self.assertEqual(self.decisions['stay_held'], list(STAY_HELD))
        self.assertEqual(self.decisions['retired'], list(RETIRED))
        self.assertEqual([row['source_id'] for row in self.proposals['members']], list(MEMBERS))
        self.assertEqual(Counter(row['decision'] for row in self.proposals['proposals']), {'admit': 36, 'hold': 1})
        self.assertEqual([row['source_id'] for row in self.proposals['held_members']], list(HELD))
        self.assertEqual(tuple(self.rows), ADMITTED)
        self.assertEqual(self.manifest['member_count'], 36)
        self.assertEqual(self.manifest['authority_counts'], {'credits': 12, 'direct': 23, 'exxon': 1})
        self.assertEqual(self.manifest['hold_group_counts'], {'access': 22, 'creators': 9, 'metadata_date': 5})
        self.assertEqual(self.manifest['modern_creator_object_count'], 46)
        self.assertEqual(self.proposals['inputs'][str(mapping.HELD37_DECISIONS.relative_to(REPO))], DECISIONS_SHA)
        self.assertEqual(self.review['status'], 'proposal pending independent review')
        self.assertEqual(self.review['mapping_manifest_sha256'], MANIFEST_SHA)
        self.assertEqual(self.review['proposals_sha256'], PROPOSALS_SHA)
        self.assertEqual(self.review['members'], self.manifest['members'])
        self.assertEqual(set(self.review['decisions']), set(ADMITTED))
        # A pending review admits nothing; the holds, the retired and the protected records are closed too.
        for sid in (*MEMBERS, *STAY_HELD, *RETIRED, *mapping.PROTECTED, 'FGDC-2953'):
            with self.subTest(source=sid), self.assertRaises(mapping.Held):
                mapping.source_policy(sid)
        self.assertEqual([mapping.source_policy(sid)[1]['schema_version'] for sid in OLD_SAMPLES], list(range(1, 12)))

    def test_rows_rebuild_from_proposals_originals_plan_decisions_and_evidence(self):
        targets = {row['record_target_id']: row for row in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
        questions = {row['question']: row for row in self.decisions['decisions']}
        cohorts = {m['source_id']: c for c in mapping.parse(mapping.HELD37_CREDITS.read_bytes())['cohorts'] for m in c['members']}
        corrections = mapping.parse(mapping.HELD37_DATES.read_bytes())['corrections']
        exxon = mapping.pinned(mapping.EXXON_PROFILE, mapping.EXXON_SHA)
        for proposal in self.proposals['proposals']:
            sid = proposal['source_id']
            with self.subTest(source=sid):
                raw = (REPO / proposal['source_path']).read_bytes()
                root = ET.fromstring(raw)
                self.assertEqual((len(raw), mapping.sha(raw)), (proposal['source_bytes'], proposal['source_sha256']))
                self.assertEqual(mapping.sha(mapping.encode(source_element(root))), proposal['source_root_sha256'])
                self.assertEqual([source_element(n) for n in root.findall('./idinfo/citation/citeinfo/origin')],
                                 proposal['primary_origin_elements'])
                question = questions[proposal['decision_question']]
                self.assertIn(sid, question['sources'])
                self.assertEqual(proposal['owner_decision']['answer'], question['answer'])
                self.assertEqual(proposal['hold_group'],
                                 {'A': 'access', 'B': 'creators', 'C': 'metadata_date'}[question['question'][0]])
                self.assertTrue(proposal['baseline_hold_reasons'])
                self.assertEqual(targets[sid]['source_semantic_status'], 'held')
                self.assertEqual(targets[sid]['source_ids'], [sid])
                for item in proposal['evidence']:
                    if item['kind'] == 'file':
                        path = REPO / item['path']
                        self.assertEqual(mapping.sha(path.read_bytes()), item['sha256'])
                        self.assertIn(item['quote'], path.read_text(encoding='utf-8'))
                if proposal['decision'] == 'hold':
                    self.assertEqual(sid, 'FGDC-2817')
                    self.assertIsNone(proposal['proposed_creators'])
                    self.assertIn('Metadata access terms need source-backed adjudication', proposal['remaining_hold_reasons'])
                    self.assertNotIn(sid, self.rows)
                    continue
                self.assertEqual(proposal['remaining_hold_reasons'], [])
                row = self.rows[sid]
                self.assertEqual(row['modern_creators'], proposal['proposed_creators'])
                self.assertEqual(row['creators'], proposal['legacy_creators'])
                self.assertEqual(row['additional_preservation_paragraphs'], [proposal['additional_preservation_paragraph']])
                self.assertEqual(row['proposal_row_sha256'], mapping.sha(mapping.encode(proposal)))
                self.assertEqual(self.proposals['proposals'][int(row['proposal_row_pointer'].rsplit('/', 1)[1])], proposal)
                self.assertEqual(mapping.sha(mapping.encode(targets[sid])), row['source_plan_target_sha256'])
                for creator in row['modern_creators']:
                    mapping.modern_creator_shape(creator)
                kind = row['creator_authority_kind']
                if kind == 'credits':
                    self.assertEqual(cohorts[sid]['creators'], row['creators'])
                    self.assertEqual(mapping.sha(mapping.encode(cohorts[sid])), row['creator_authority_object_sha256'])
                elif kind == 'exxon':
                    self.assertEqual(sid, 'FGDC-1994')
                    self.assertEqual(exxon['creators'], row['creators'])
                else:
                    self.assertEqual(mapping.sha(mapping.encode(row['creators'])), row['creator_authority_object_sha256'])
                    self.assertTrue(all(c.get('type', 'Organization') == 'Organization' for c in row['creators']))
                if row['hold_group'] == 'metadata_date':
                    self.assertEqual(row['metadata_date_correction']['corrected_value'], CORRECTED[sid])
                    self.assertEqual(corrections[sid]['source_value'], row['metadata_date_correction']['source_value'])
                else:
                    self.assertIsNone(row['metadata_date_correction'])
                # The paragraph quotes the decision and, for a changed creator reading, the literal origin.
                paragraph = row['additional_preservation_paragraphs'][0]
                self.assertIn('Brett Johnson', paragraph)
                self.assertIn('2026-10-23', paragraph)
                self.assertIn('question ' + row['decision_question'], paragraph)
        # Brett's creator decisions verbatim.
        self.assertEqual([c['person_or_org'] for c in self.rows['FGDC-1206']['modern_creators']],
                         [{'type': 'personal', 'family_name': 'Biryukova', 'given_name': 'I.V.'},
                          {'type': 'personal', 'family_name': 'Matrosov', 'given_name': 'V.V.'},
                          {'type': 'personal', 'family_name': 'Evdokimov', 'given_name': 'V.V.'}])
        self.assertEqual(self.rows['FGDC-2586']['modern_creators'], [{'person_or_org': {
            'type': 'organizational', 'name': 'United States Navy, Office of the Chief of Naval Operations'}}])
        for sid in ('FGDC-3683', 'FGDC-3975', 'FGDC-3976', 'FGDC-3977', 'FGDC-3978'):
            self.assertEqual(self.rows[sid]['modern_creators'],
                             [{'person_or_org': {'type': 'organizational', 'name': 'Japan Oceanographic Data Center'}}])
        for sid in ('FGDC-3919', 'FGDC-3920'):
            self.assertEqual(self.rows[sid]['modern_creators'],
                             [{'person_or_org': {'type': 'organizational', 'name': 'Japan Meteorological Agency'}}])
        self.assertEqual(self.by_source['FGDC-2817']['decided_creators'][0]['person_or_org'],
                         {'type': 'personal', 'family_name': 'Kavakina', 'given_name': 'S.V.'})
        # Literal organisational credits for the access rows, except the four the record itself settles.
        for sid in ACCESS:
            row = self.rows[sid]
            if sid in ('FGDC-288', 'FGDC-1864', 'FGDC-4027', 'FGDC-1994'):
                continue
            self.assertEqual([c['person_or_org'] for c in row['modern_creators']],
                             [{'type': 'organizational', 'name': c['name']} for c in row['creators']])
        self.assertEqual(self.rows['FGDC-288']['modern_creators'], [
            {'person_or_org': {'type': 'personal', 'family_name': 'Smith', 'given_name': 'Stacy'},
             'affiliations': [{'name': 'University of Alaska, Fairbanks'}]},
            {'person_or_org': {'type': 'personal', 'family_name': 'Henrichs', 'given_name': 'Susan M.'},
             'affiliations': [{'name': 'University of Alaska, Fairbanks'}]}])
        self.assertEqual(self.rows['FGDC-1864']['modern_creators'],
                         [{'person_or_org': {'type': 'organizational', 'name': 'Pacific Oceanological Institute (POI)'}}])
        self.assertEqual([c['person_or_org'].get('family_name') for c in self.rows['FGDC-4027']['modern_creators']],
                         [None, None, 'Akimoto', 'Takahashi', 'Takigawa'])
        self.assertEqual(self.rows['FGDC-1994']['modern_creators'],
                         mapping.pinned(mapping.EXXON_MAPPING, mapping.EXXON_MAPPING_SHA)['modern_creators'])
        # Resource types r6: r5 plus the 37, nothing else changed.
        r6 = mapping.parse(bulk.RESOURCE_TYPES_PATH.read_bytes())
        r5 = mapping.parse((REPO / r6['supersedes']['path']).read_bytes())
        self.assertEqual(mapping.sha((REPO / r6['supersedes']['path']).read_bytes()), r6['supersedes']['sha256'])
        self.assertEqual({k: v for k, v in r6['types'].items() if k not in MEMBERS}, r5['types'])
        self.assertEqual({k: v for k, v in r6['notes'].items() if k not in MEMBERS}, r5['notes'])
        self.assertEqual(set(r6['types']) - set(r5['types']), set(MEMBERS))
        self.assertEqual({sid: r6['types'][sid] for sid in MEMBERS},
                         {sid: self.by_source[sid]['proposed_resource_type'] for sid in MEMBERS})
        self.assertEqual(set(r6['confidence_low']) - set(r5['confidence_low']), {'FGDC-870', 'FGDC-1318', 'FGDC-4027'})
        self.assertEqual(r6['low_confidence'], len(r6['confidence_low']))
        self.assertEqual(Counter(r6['types'][sid] for sid in MEMBERS), {'dataset': 32, 'publication-report': 5})

    def test_classification_evidence_manifests_validate_against_the_originals(self):
        reviewed_at = REVIEWED_AT
        decided = mapping.parse(mapping.HELD37_SCOPE.read_bytes())
        self.assertEqual(len(decided['members']), 926)
        statuses = Counter()
        for member in decided['members'][904:]:
            root = ET.fromstring((REPO / 'FGDC' / (member['source_id'] + '.xml')).read_bytes())
            result = scope.validate_scope_attestation(reference(mapping.HELD37_SCOPE), member['source_id'],
                                                      member['source_sha256'], root, reviewed_at)
            statuses[(result['status'], result['decision_question'])] += 1
            self.assertEqual(result['attested_at'], '2026-10-23T00:00:00Z')
            self.assertFalse(result['grants_rehosting'] or result['grants_new_license'] or result['publication_approved'])
            with self.assertRaises(ValueError):  # before Brett's decision
                scope.validate_scope_attestation(reference(mapping.HELD37_SCOPE), member['source_id'],
                                                 member['source_sha256'], root, '2026-10-20T00:00:00+00:00')
        self.assertEqual(statuses, {('USER_ATTESTED', 'A1'): 19, ('USER_ATTESTED', 'A2'): 2, ('USER_ATTESTED', 'A3'): 1})
        self.assertEqual({m['source_id'] for m in decided['members'][904:]}, set(ACCESS))
        first = decided['members'][0]  # a reconciled904 member still validates through the decided file, at its old time
        root = ET.fromstring((REPO / 'FGDC' / (first['source_id'] + '.xml')).read_bytes())
        self.assertEqual(scope.validate_scope_attestation(reference(mapping.HELD37_SCOPE), first['source_id'],
                                                          first['source_sha256'], root, '2026-10-20T00:00:00+00:00')['status'],
                         'USER_ATTESTED')
        self.assertEqual(len(scope.scope_member_ids(reference(mapping.HELD37_SCOPE))), 926)
        # A rewritten decided file (one member more, or a member moved to another question) is refused.
        for label, mutate in (('extra member', lambda m: m['members'].append(dict(m['members'][-1], source_id='FGDC-909'))),
                              ('moved question', lambda m: m['members'][-1].update(cohort='held_access_A1')),
                              ('changed answer', lambda m: m['held_sources_decisions_2026_10_23']['cohorts']['held_access_A3'].update(answer='No'))):
            with self.subTest(change=label):
                changed = copy.deepcopy(decided)
                mutate(changed)
                path = self.root / (label + '.json')
                path.write_bytes(mapping.encode(changed))
                self.assertEqual(scope.scope_member_ids(reference(path)), frozenset())
                with patch.object(scope, 'DECIDED_MANIFEST_SHA256', mapping.sha(path.read_bytes())):
                    self.assertEqual(scope.scope_member_ids(reference(path)), frozenset())
        # Source credits 436: every cohort validates and the ten new ones carry the decision and the origin note.
        manifest = mapping.parse(mapping.HELD37_CREDITS.read_bytes())
        self.assertEqual(len(manifest['cohorts']), 259)
        self.assertEqual(manifest['prior_manifest_sha256'], mapping.PROFILE_SHA)
        base = mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)
        self.assertEqual(manifest['cohorts'][:249], base['cohorts'])
        new = manifest['cohorts'][249:]
        self.assertEqual({m['source_id'] for c in new for m in c['members']}, set(CREATORS))
        for cohort in new:
            member = cohort['members'][0]
            root = ET.fromstring((REPO / 'FGDC' / (member['source_id'] + '.xml')).read_bytes())
            result = credits.validate_creator_interpretation(reference(mapping.HELD37_CREDITS), member['source_id'],
                                                             member['source_sha256'], root, True)
            self.assertEqual(result['creators'], cohort['creators'])
            self.assertEqual(len(result['preservation_notes']), 2)
            self.assertTrue(result['preservation_notes'][0].startswith('Original primary citation origin XML'))
            self.assertIn('Brett Johnson decided on 2026-10-23', result['preservation_notes'][1])
            self.assertEqual(cohort['decision']['decided_at'], '2026-10-23')
            with self.assertRaises(ValueError):
                credits.validate_creator_interpretation(reference(mapping.HELD37_CREDITS), member['source_id'], '0' * 64, root)
        for sid in ('FGDC-710', 'FGDC-4027', 'FGDC-4063'):  # the 426 cohorts still answer through the 436 file
            root = ET.fromstring((REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            digest = mapping.sha((REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            self.assertEqual(credits.validate_creator_interpretation(reference(mapping.HELD37_CREDITS), sid, digest, root),
                             credits.validate_creator_interpretation(reference(mapping.PROFILE), sid, digest, root))
        # Metadata date corrections: the exact source value and bytes, nothing else.
        corrections = mapping.parse(mapping.HELD37_DATES.read_bytes())['corrections']
        self.assertEqual(set(corrections), set(DATES))
        self.assertEqual(dates.correction_member_ids(reference(mapping.HELD37_DATES)), frozenset(DATES))
        for sid, entry in corrections.items():
            root = ET.fromstring((REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            result = dates.validate_metadata_date_correction(reference(mapping.HELD37_DATES), sid, entry['source_sha256'], root)
            self.assertEqual((result['source_value'], result['corrected_value']),
                             ('2080207' if entry['question'] == 'C1' else '', CORRECTED[sid]))
            self.assertEqual(result['status'], 'USER_DECIDED')
        neighbour = ET.fromstring((REPO / 'FGDC/FGDC-4140.xml').read_bytes())
        with self.assertRaises(ValueError):  # the right hash, another file's metd
            dates.validate_metadata_date_correction(reference(mapping.HELD37_DATES), 'FGDC-4139',
                                                    corrections['FGDC-4139']['source_sha256'], neighbour)
        with self.assertRaises(ValueError):
            dates.validate_metadata_date_correction(reference(mapping.HELD37_DATES), 'FGDC-4140',
                                                    mapping.sha((REPO / 'FGDC/FGDC-4140.xml').read_bytes()), neighbour)
        self.assertEqual(dates.correction_member_ids({'manifest_path': str(mapping.HELD37_DATES), 'manifest_sha256': '0' * 64}),
                         frozenset())

    def test_classification_applies_each_decision_to_its_exact_source_only(self):
        rows = {row['source_id']: row for row in self.report['records']}
        self.assertEqual(self.report['summary']['source_status_counts'], {'supported': 36, 'held': 1, 'failed': 0})
        self.assertEqual(rows['FGDC-2817']['hold_reasons'],
                         ['Metadata access terms need source-backed adjudication',
                          'Contradictory or unsupported source access constraints require adjudication'])
        paths = OutputPaths(str(self.prepared_root), 'production')
        for sid in DATES:
            with self.subTest(source=sid):
                row = rows[sid]
                self.assertEqual((row['metadata_date_correction'], row['metadata_date_precision']), ('USER_DECIDED', 'day'))
                payload = mapping.parse((Path(paths.zenodo_json_dir) / (sid + '.json')).read_bytes())
                self.assertEqual(payload['metadata']['publication_date'], CORRECTED[sid])
                self.assertEqual(payload['artifact_policy']['metadata_date_correction']['manifest_sha256'], dates.MANIFEST_SHA256)
                self.assertIn('corrected to ' + CORRECTED[sid], payload['artifact_policy']['date_evidence'])
                self.assertTrue(payload['artifact_policy']['date_evidence'].startswith('Source metainfo/metd: ' + row['raw_metadata_date']))
                metadata, _, _, _ = assess_source(str(Path(paths.zenodo_json_dir) / (sid + '.json')), paths)
                self.assertEqual(metadata['publication_date'], CORRECTED[sid])
        for sid in ACCESS:
            self.assertEqual(rows[sid]['source_scope_attestation'], 'USER_ATTESTED')
            self.assertNotIn('metadata_date_correction', rows[sid])
        for sid in CREATORS:
            self.assertEqual(rows[sid]['creator_interpretation'], 'source_primary_citation_attribution')
        # A date correction that no longer matches its policy, and the same date without its evidence, hold.
        copied = self.paths()
        json_file = Path(copied.zenodo_json_dir) / 'FGDC-4139.json'
        payload = mapping.parse(json_file.read_bytes())
        changed = copy.deepcopy(payload)
        changed['metadata']['publication_date'] = '2008-02-11'
        json_file.write_bytes(mapping.encode(changed))
        with self.assertRaises(ValueError):
            assess_source(str(json_file), copied)
        changed = copy.deepcopy(payload)
        del changed['artifact_policy']['metadata_date_correction']
        json_file.write_bytes(mapping.encode(changed))
        with self.assertRaises(ValueError):
            assess_source(str(json_file), copied)

    def test_approved_review_admits_the_36_repeatably_with_dates_notes_and_v2_wires(self):
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
                    self.assertEqual(prepared.xml, (REPO / row['source_path']).read_bytes())
                    self.assertEqual(source_sha, row['source_sha256'])
                    self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                    self.assertEqual(prepared.evidence['schema_version'], 12)
                    self.assertEqual(prepared.evidence['policy'], mapping.HELD37_POLICY)
                    self.assertEqual(prepared.evidence['mapping_manifest_sha256'], MANIFEST_SHA)
                    self.assertEqual(prepared.evidence['hold_group'], row['hold_group'])
                    self.assertEqual(prepared.evidence['decision_question'], row['decision_question'])
                    self.assertEqual(prepared.evidence['public_notes'], row['additional_preservation_paragraphs'])
                    self.assertEqual(prepared.evidence['metadata_date_correction'], row['metadata_date_correction'])
                    kind = row['creator_authority_kind']
                    self.assertEqual(prepared.evidence['creator_profile_sha256'],
                                     {'credits': credits.SOURCE_CREDIT_436_MANIFEST_SHA256, 'exxon': mapping.EXXON_SHA,
                                      'direct': MANIFEST_SHA}[kind])
                    policy = mapping.parse(before)['artifact_policy']
                    if kind == 'direct':
                        self.assertNotIn('creator_interpretation', policy)
                    else:
                        self.assertEqual(policy['creator_interpretation']['manifest_sha256'],
                                         prepared.evidence['creator_profile_sha256'])
                    if sid in DATES:
                        self.assertEqual(meta['publication_date'], CORRECTED[sid])
                    self.assertEqual(json_file.read_bytes(), before)
                    wire = bulk.WireV2(prepared, bulk.resource_type_of(sid))
                    meta2 = mapping.parse(wire.body)['metadata']
                    self.assertEqual(meta2['creators'], row['modern_creators'])
                    self.assertEqual(meta2['resource_type'], {'id': self.by_source[sid]['proposed_resource_type']})
                    self.assertEqual(wire.evidence['v1_wire_sha256'], prepared.evidence['wire_sha256'])
                    technical = meta2['additional_descriptions'][-1]['description']
                    self.assertTrue(technical.endswith('<p>' + html.escape(row['additional_preservation_paragraphs'][0], quote=False) + '</p>'))
                    root = ET.fromstring(prepared.xml)
                    if sid in DATES:
                        self.assertEqual(meta2['publication_date'], CORRECTED[sid])
                        self.assertIn('see the metadata date note', technical)
                        self.assertIn('Publication date taken from the corrected FGDC metadata date', technical)
                    else:
                        self.assertNotIn('metadata date note', technical)
                        self.assertEqual(meta2['publication_date'], wire_v2.publication_date(root)[0])
                    if sid in ACCESS:  # the constraint texts stay as they are, as a rights statement, no licence
                        rights = meta2['rights'][0]['description']['en']
                        self.assertIn('Access constraints: ' + wire_v2.text_of(root.find('./idinfo/accconst')), rights)
                        self.assertNotIn('id', meta2['rights'][0])
            # Approval does not reach the held proposal, the records Brett kept held, the retired, the protected or a pair member.
            for sid in (*HELD, *STAY_HELD, *RETIRED, *mapping.PROTECTED, 'FGDC-2953'):
                with self.subTest(held=sid), self.assertRaises(mapping.Held):
                    mapping.source_policy(sid)
            with self.assertRaises(ValueError):
                mapping.prepare(Path(paths.zenodo_json_dir) / 'FGDC-2817.json', paths)
            self.assertEqual([mapping.source_policy(sid)[1]['schema_version'] for sid in OLD_SAMPLES], list(range(1, 12)))

    def test_review_must_be_approved_bound_and_complete_and_may_hold_single_members(self):
        paths = self.paths()
        json_file = Path(paths.zenodo_json_dir) / 'FGDC-4139.json'
        (self.root / 'partial').mkdir()
        partial = approved_review(self.root / 'partial', decisions={**{sid: 'approved' for sid in ADMITTED}, 'FGDC-4139': 'held'})
        with review_file(partial):
            with self.assertRaises(mapping.Held):
                mapping.prepare(json_file, paths)
            self.assertEqual(mapping.source_policy('FGDC-1206')[1]['policy'], mapping.HELD37_POLICY)
        for label, changes in (
                ('status', {'status': 'proposal pending independent review'}),
                ('other status', {'status': 'APPROVED'}),
                ('no reviewer', {'reviewer': None}),
                ('blank reviewer', {'reviewer': ' '}),
                ('no time', {'reviewed_at': None}),
                ('manifest binding', {'mapping_manifest_sha256': '0' * 64}),
                ('proposal binding', {'proposals_sha256': '0' * 64}),
                ('kind', {'kind': 'modern-reviewed-creators64-review-v1'}),
                ('policy', {'policy': mapping.CREATORS64_POLICY}),
                ('members', {'members': self.review['members'][:-1]}),
                ('approved list', {'approved_members': self.review['members'][:-1]}),
                ('extra decision', {'decisions': {**{sid: {'decision': 'approved', 'note': None} for sid in ADMITTED},
                                                  'FGDC-2817': {'decision': 'approved', 'note': None}}}),
                ('nothing approved', {'decisions': {sid: {'decision': 'held', 'note': None} for sid in ADMITTED},
                                      'approved_members': [], 'held_members': self.review['members']})):
            with self.subTest(change=label):
                (self.root / label).mkdir()
                path = approved_review(self.root / label, **changes)
                with review_file(path), self.assertRaises(mapping.Held):
                    mapping.prepare(json_file, paths)
        # An approved review whose digest is not the pinned one is just as closed.
        with patch.object(mapping, 'HELD37_REVIEW', self.approved), self.assertRaises(mapping.Held):
            mapping.prepare(json_file, paths)

    def test_rehashed_manifest_or_proposals_cannot_change_vectors_dates_notes_or_scope(self):
        paths = self.paths()
        json_file = Path(paths.zenodo_json_dir) / 'FGDC-4139.json'
        index = next(i for i, row in enumerate(self.manifest['rows']) if row['source_id'] == 'FGDC-4139')
        other = next(i for i, row in enumerate(self.manifest['rows']) if row['source_id'] == 'FGDC-288')
        with review_file(self.approved):
            baseline = mapping.prepare(json_file, paths)
            for label, mutate in (
                    ('missing member', lambda m: m['rows'].pop()),
                    ('held source', lambda m: m['rows'][index].update(source_id='FGDC-2817')),
                    ('source hash', lambda m: m['rows'][index].update(source_sha256='0' * 64)),
                    ('root', lambda m: m['rows'][index].update(source_root_sha256='0' * 64)),
                    ('origin', lambda m: m['rows'][index]['primary_origins'][0].update(text='Invented')),
                    ('plan', lambda m: m['rows'][index].update(source_plan_target_sha256='0' * 64)),
                    ('group', lambda m: m['rows'][index].update(hold_group='access')),
                    ('question', lambda m: m['rows'][index].update(decision_question='C2')),
                    ('authority kind', lambda m: m['rows'][index].update(creator_authority_kind='credits')),
                    ('authority object', lambda m: m['rows'][index].update(creator_authority_object_sha256='0' * 64)),
                    ('legacy array', lambda m: m['rows'][index]['creators'].append({'name': 'Invented'})),
                    ('modern type', lambda m: m['rows'][index]['modern_creators'][0]['person_or_org'].update(
                        type='personal', family_name='Canada', given_name='Fisheries and Oceans')),
                    ('corrected day', lambda m: m['rows'][index]['metadata_date_correction'].update(corrected_value='2008-02-11')),
                    ('source value', lambda m: m['rows'][index]['metadata_date_correction'].update(source_value='2080208')),
                    ('dropped correction', lambda m: m['rows'][index].update(metadata_date_correction=None)),
                    ('note', lambda m: m['rows'][index].update(additional_preservation_paragraphs=['All dates verified.'])),
                    ('pointer', lambda m: m['rows'][index].update(proposal_row_pointer='/proposals/0')),
                    ('split undone', lambda m: m['rows'][other].update(modern_creators=[{'person_or_org': {
                        'type': 'organizational', 'name': 'Stacy Smith, Susan M. Henrichs of the University of Alaska, Fairbanks'}}])),
                    ('affiliation', lambda m: m['rows'][other]['modern_creators'][0].pop('affiliations'))):
                with self.subTest(change=label):
                    changed = copy.deepcopy(self.manifest)
                    mutate(changed)
                    path = self.root / 'rehashed-manifest.json'
                    path.write_bytes(mapping.encode(changed))
                    with patch.object(mapping, 'HELD37', path), \
                            patch.object(mapping, 'HELD37_SHA', mapping.sha(path.read_bytes())), \
                            self.assertRaises(mapping.Held):
                        mapping.prepare(json_file, paths)
            # Rewriting the proposals (and the manifest from them) breaks the review's binding.
            proposals = copy.deepcopy(self.proposals)
            target = next(row for row in proposals['proposals'] if row['source_id'] == 'FGDC-4139')
            target['metadata_date_correction']['corrected_value'] = '2008-02-11'
            proposals_path = self.root / 'rehashed-proposals.json'
            proposals_path.write_bytes(mapping.encode(proposals))
            manifest = copy.deepcopy(self.manifest)
            manifest['rows'][index]['metadata_date_correction']['corrected_value'] = '2008-02-11'
            manifest['rows'][index]['proposal_row_sha256'] = mapping.sha(mapping.encode(target))
            manifest['proposals_sha256'] = mapping.sha(proposals_path.read_bytes())
            manifest_path = self.root / 'rehashed-manifest-2.json'
            manifest_path.write_bytes(mapping.encode(manifest))
            with patch.object(mapping, 'HELD37_PROPOSALS', proposals_path), \
                    patch.object(mapping, 'HELD37_PROPOSALS_SHA', mapping.sha(proposals_path.read_bytes())), \
                    patch.object(mapping, 'HELD37', manifest_path), \
                    patch.object(mapping, 'HELD37_SHA', mapping.sha(manifest_path.read_bytes())), \
                    self.assertRaises(mapping.Held):
                mapping.prepare(json_file, paths)
            self.assertEqual(mapping.prepare(json_file, paths), baseline)

    def test_changed_payload_evidence_reference_or_source_copy_holds(self):
        paths = self.paths()
        with review_file(self.approved):
            for sid in ('FGDC-4139', 'FGDC-227', 'FGDC-1206'):
                json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
                original = json_file.read_bytes()
                payload = mapping.parse(original)
                for key, value in (('creators', [{'name': 'Invented'}]), ('title', payload['metadata']['title'] + ' changed'),
                                   ('publication_date', '2026-10-23'), ('access_right', 'open'), ('license', 'cc-by-4.0')):
                    with self.subTest(source=sid, field=key):
                        changed = copy.deepcopy(payload)
                        changed['metadata'][key] = value
                        json_file.write_bytes(mapping.encode(changed))
                        with self.assertRaises(ValueError):
                            mapping.prepare(json_file, paths)
                evidence_key = {'FGDC-4139': 'metadata_date_correction', 'FGDC-227': 'source_scope_attestation',
                                'FGDC-1206': 'creator_interpretation'}[sid]
                for reference_value in (None, {'manifest_path': payload['artifact_policy'][evidence_key]['manifest_path'],
                                               'manifest_sha256': mapping.PROFILE_SHA}):
                    with self.subTest(source=sid, evidence=evidence_key, reference=reference_value):
                        changed = copy.deepcopy(payload)
                        if reference_value is None:
                            del changed['artifact_policy'][evidence_key]
                        else:
                            changed['artifact_policy'][evidence_key] = reference_value
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

    def test_withdrawn_evidence_holds_members_and_leaves_eleven_prior_policies_alone(self):
        paths = self.paths()
        json_file = Path(paths.zenodo_json_dir) / 'FGDC-3683.json'
        old = {sid: mapping.source_policy(sid) for sid in OLD_SAMPLES}
        for attribute in ('HELD37', 'HELD37_PROPOSALS', 'HELD37_DECISIONS', 'HELD37_CREDITS', 'HELD37_SCOPE', 'HELD37_DATES'):
            for missing in (True, False):
                with self.subTest(evidence=attribute, missing=missing):
                    path = self.root / (attribute + ('-missing' if missing else '-changed'))
                    if not missing:
                        path.write_bytes(getattr(mapping, attribute).read_bytes() + b' ')
                    with review_file(self.approved), patch.object(mapping, attribute, path):
                        with self.assertRaises((ValueError, OSError)):
                            mapping.prepare(json_file, paths)
                        self.assertEqual({sid: mapping.source_policy(sid) for sid in OLD_SAMPLES}, old)


class WireV2CorrectionTests(unittest.TestCase):
    def fgdc(self, pubdate, metd):
        return ET.fromstring(('<metadata><idinfo><citation><citeinfo><title>T</title><pubdate>' + pubdate + '</pubdate>'
                              '</citeinfo></citation></idinfo><metainfo><metd>' + metd + '</metd></metainfo></metadata>').encode())

    def test_a_reviewed_correction_stands_in_for_the_metadata_date_only_when_the_citation_is_inexact(self):
        self.assertEqual(wire_v2.publication_date(self.fgdc('Unknown', '2080207'), '2008-02-07'),
                         ('2008-02-07', 'metadata-corrected'))
        self.assertEqual(wire_v2.publication_date(self.fgdc('19870301', '2080207'), '2008-02-07'), ('1987-03-01', 'citation'))
        with self.assertRaises(mapping.Held):
            wire_v2.publication_date(self.fgdc('Unknown', '2080207'))
        for bad in ('20080207', '2008-02-30', '2008-2-7', ''):
            with self.subTest(value=bad), self.assertRaises(mapping.Held):
                wire_v2.publication_date(self.fgdc('Unknown', '2080207'), bad)

    def test_build_binds_the_correction_to_the_source_value_and_appends_the_notes_last(self):
        v1 = {'metadata': {'title': 'T - FGDC XML metadata artifact', 'creators': [
            {'person_or_org': {'type': 'organizational', 'name': 'Org'}}], 'description': 'd', 'subjects': []}}
        xml = ET.tostring(self.fgdc('Unknown', '2080207'))
        correction = {'source_value': '2080207', 'corrected_value': '2008-02-07', 'question': 'C1'}
        record = wire_v2.build(v1, xml, ['FGDC-4139'], 'dataset', date_correction=correction,
                               notes=['Metadata date: a reviewed note.', 'Creators: another note.'])
        self.assertEqual(record['metadata']['publication_date'], '2008-02-07')
        technical = record['metadata']['additional_descriptions'][-1]['description']
        self.assertIn('dated 2008-02-07 (a reviewed correction of the source value "2080207"; see the metadata date note)', technical)
        self.assertTrue(technical.endswith('<p>Metadata date: a reviewed note.</p><p>Creators: another note.</p>'))
        plain = wire_v2.build(v1, ET.tostring(self.fgdc('Unknown', '20080207')), ['FGDC-4140'], 'dataset')
        self.assertEqual(plain['metadata']['publication_date'], '2008-02-07')
        self.assertNotIn('reviewed correction', plain['metadata']['additional_descriptions'][-1]['description'])
        with self.assertRaises(mapping.Held):  # another record's metd does not match the bound source value
            wire_v2.build(v1, ET.tostring(self.fgdc('Unknown', '20080207')), ['FGDC-4140'], 'dataset', date_correction=correction)
        with self.assertRaises(mapping.Held):
            wire_v2.build(v1, xml, ['FGDC-4139'], 'dataset', date_correction=correction, notes=[''])
        blank = ET.tostring(ET.fromstring(b'<metadata><idinfo><citation><citeinfo><title>T</title><pubdate>Unknown</pubdate>'
                                          b'</citeinfo></citation></idinfo><metainfo><metd /></metainfo></metadata>'))
        record = wire_v2.build(v1, blank, ['FGDC-1422'], 'dataset',
                               date_correction={'source_value': '', 'corrected_value': '2003-05-30', 'question': 'C2'})
        self.assertIn('dated 2003-05-30 (a reviewed correction of the source value left blank; see the metadata date note)',
                      record['metadata']['additional_descriptions'][-1]['description'])


if __name__ == '__main__':
    unittest.main()
