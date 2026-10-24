"""Build the held37 lane: evidence manifests, proposal, mapping manifest, pending review and resource types r6.

Purpose: Brett answered the held-sources evidence sheet on 2026-10-23 (held_sources_decisions.json):
22 access holds, 10 creator holds and 5 metadata-date holds were cleared; six records stay held and two
are retired. This builder turns the answers into the pinned evidence the offline classification reads,
then proposes the modern creator vector, the resource type and the preservation paragraph of every
cleared record with its evidence, and writes the mapping manifest and a review file that starts closed,
so `scripts.modern_singleton` holds every member until an independent reviewer approves it (the
creators64 pattern, ADR 0016).

Two stages, run from the repository root:

  python -B docs/readiness/2026-10-23/build_held37_manifests.py evidence
      writes source_scope_decisions_926.json (the reconciled904 plus the 22 access members),
      source_citation_credits_436.json (the 426 cohorts plus ten decided creator cohorts) and
      metadata_date_corrections_5.json; their SHA256 are then pinned in scripts/.

  python -B -m scripts.collection_qa --source-dir <the 37 XML files> --output-dir <qa-output-dir> \
      <the runbook manifest set, with the three files above> --reviewed-at 2026-10-23T22:00:00+00:00
  python -B docs/readiness/2026-10-23/build_held37_manifests.py lane --classified <qa-output-dir> --baseline <runbook-set-output-dir>
      writes held37_proposals.json, modern_reviewed_held37.json, modern_reviewed_held37_review.json and
      resource_types_r6.json; their SHA256 are then pinned in scripts/.

Invariants: original XML is read, never written. Legacy creator arrays are those the fresh classification
produced; a decided creator vector is Brett's answer verbatim; every other vector keeps the literal
credit, typed organisational exactly as cited, except where the record itself settles a split (288,
4027) or a role clause (1864), and the paragraph says so. A hold Brett did not decide stays a hold
(FGDC-2817's access text).
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.citation_creator_interpretation import source_element  # noqa: E402
from scripts.modern_singleton import (  # noqa: E402
    EXXON_MAPPING,
    EXXON_MAPPING_SHA,
    EXXON_PROFILE,
    EXXON_SHA,
    INSTITUTION_MAPPING,
    PLAN,
    PLAN_SHA,
    PROFILE,
    PROFILE_SHA,
    encode,
    pinned,
    sha,
)
from scripts.production_mutations import PROTECTED  # noqa: E402

OUT = ROOT / 'docs/readiness/2026-10-23'
POLICY = 'modern-xml-reviewed-held37-v1'
REVIEWED_AT = '2026-10-23T22:00:00+00:00'  # the lane's fixed classification time: after Brett's decisions, in the past
PROPOSED_BY = 'Claude Fable 5.1 (deep-coder subagent of session a49e1cd3), 2026-10-23'
INSTRUCTION = ('Brett Johnson, 2026-10-23: answers to the questions in held_sources_evidence.md, recorded in '
               'held_sources_decisions.json; a cleared hold is not a publication approval.')
DECISIONS = ROOT / 'docs/readiness/2026-10-23/held_sources_decisions.json'
SHEET = ROOT / 'docs/readiness/2026-10-22/held_sources_evidence.md'
SCOPE_904 = ROOT / 'docs/readiness/2026-10-03/source_scope_reconciliation_904.json'
CREDITS_426 = PROFILE
R5 = ROOT / 'docs/readiness/2026-10-22/resource_types_r5.json'
SCOPE_OUT = OUT / 'source_scope_decisions_926.json'
CREDITS_OUT = OUT / 'source_citation_credits_436.json'
DATES_OUT = OUT / 'metadata_date_corrections_5.json'
CONSTRAINT_XPATHS = ('./idinfo/accconst', './idinfo/useconst', './metainfo/metac', './metainfo/metuc')
CONTEXT_XPATHS = ('./idinfo/citation/citeinfo/title', './idinfo/descript/abstract', './idinfo/descript/purpose')
CONTACT_XPATH = './idinfo/ptcontac/cntinfo/cntperp/cntper'
ORIGIN_XPATH = './idinfo/citation/citeinfo/origin'
GROUPS = {'A': 'access', 'B': 'creators', 'C': 'metadata_date'}
MEANINGS = {
    'A1': 'the access and use texts restrict only the underlying data or product; the catalogue description '
          'was public in the PICES GeoNetwork catalogue',
    'A2': 'the FGDC record is the public catalogue entry, not a copy of the restricted product it describes',
    'A3': '"May require password access" refers to the POST data service, as in the published sister record '
          'FGDC-4064, not to this project description',
}
DFO_ORIGIN = 'Fisheries and Oceans Canada - Ocean Science And Productivity, Pacific'
NOAA_NEIGHBOURS = ['FGDC-' + str(n) for n in range(1410, 1436) if n not in (1422, 1423)]

# ------------------------------------------------------------------ conventions

CONVENTIONS = {
    'scope': 'Only the 37 sources Brett cleared on 2026-10-23: 22 access holds (A1, A2, A3), 10 creator holds '
             '(B1 to B4) and 5 metadata-date holds (C1, C2). FGDC-909, 3850, 4185, 21, 4077 and 4184 stay held; '
             'FGDC-3373 and 3484 are retired. Every one of the 37 is a target of the frozen publication plan '
             'with source_semantic_status "held"; this lane is the reviewed clearing of that hold.',
    'undecided_blockers': 'A record with a second blocker Brett did not decide stays held with that blocker named: '
                          'FGDC-2817 keeps its creators B2 but its access text ("Check with Contributor" with the use '
                          'text "Refer to webstite URL: http://www.csa.com/") was not on the evidence sheet and is '
                          'not cleared.',
    'access': 'The 22 access members enter the third generation of the source-scope attestation '
              '(source_scope_decisions_926.json): the reconciled904 verbatim plus one cohort per question. Their '
              'constraint texts stay unchanged in the record; v2 maps them to the rights statement and no licence is '
              'granted.',
    'decided_creators': 'A decided creator vector (B1 to B4) is Brett\'s answer verbatim: the names, the order and '
                        'the entity type he gave. It enters the tenth generation of the source-credit manifest '
                        '(source_citation_credits_436.json) as the legacy creators of the prepared input, with the '
                        'original origin element preserved in the notes, and the mapping manifest as the modern '
                        'creators.',
    'other_creators': 'Every other member keeps its literal legacy credit: an organisational name exactly as cited '
                      '(including the reviewed creator426 cohorts of 710, 4027 and 4063 and the Exxon821 projection '
                      'of 1994). A credit is split into people only where the record itself settles the boundary '
                      '(288: the inverted contact name and natural order; 4027: the reviewed cohort note and the '
                      'inverted contact name), and a role or support clause is moved into the paragraph (1864: '
                      '"Ed (by support of ... as compilers)"). No spelling is changed and no name is imported.',
    'affiliations': 'An affiliation object is added only for an explicit attachment the citation makes with "of" to a '
                    'connected list (288) or already made in the reviewed Exxon821 projection (1994); every other '
                    'institution stays in the preserved citation.',
    'metadata_dates': 'A corrected metadata date (C1: 2080207 is 20080207; C2: a blank metd takes 2003-05-30, the '
                      'metd of the 21 neighbouring NOAA records) is pinned in metadata_date_corrections_5.json, '
                      'bound to the exact source bytes and source value. The original XML is unchanged; the corrected '
                      'day is the prepared input\'s publication date and, in v2, the publication date when the '
                      'citation gives no exact date, with a note.',
    'preservation_paragraph': 'Every member carries one paragraph that quotes the literal source values, states the '
                              'decision with its question, answer and date, and says what the record keeps. It is '
                              'rendered into the v1 preservation block (as the citations31 and creators64 policies '
                              'do) and, for this lane only, into the v2 technical-info description, so the public '
                              'record carries the source citation text and the date correction.',
    'resource_types': 'Dataset or Report by the pinned rule from each record\'s own XML; a call with a plausible '
                      'alternative is listed as low confidence in resource_types_r6.json.',
}

# ------------------------------------------------------------------ per-record decisions


def person(family, given, affiliation=None):
    creator = {'person_or_org': {'type': 'personal', 'family_name': family, 'given_name': given}}
    if affiliation:
        creator['affiliations'] = [{'name': affiliation}]
    return creator


def org(name):
    return {'person_or_org': {'type': 'organizational', 'name': name}}


UAF = 'University of Alaska, Fairbanks'
JODC = 'Japan Oceanographic Data Center'
JMA = 'Japan Meteorological Agency'
NAVY = 'United States Navy, Office of the Chief of Naval Operations'
RDMDB = ['FGDC-3683', 'FGDC-3975', 'FGDC-3976', 'FGDC-3977', 'FGDC-3978']
RRTDB = ['FGDC-3919', 'FGDC-3920']

# Modern creators that are not simply the legacy credit typed organisational.
MODERN = {
    'FGDC-288': [person('Smith', 'Stacy', UAF), person('Henrichs', 'Susan M.', UAF)],
    'FGDC-1864': [org('Pacific Oceanological Institute (POI)')],
    'FGDC-4027': [org('Japan Agency for Marine-Earth Science and Technology (JAMSTEC)'),
                  org('National Space Development Agency (NASDA), Japan'), person('Akimoto', 'Hajime'),
                  person('Takahashi', 'Masaaki'), person('Takigawa', 'Masayuki')],
    'FGDC-4063': [org('Census of Marine Life'), org('Vancouver Aquarium')],
    'FGDC-1206': [person('Biryukova', 'I.V.'), person('Matrosov', 'V.V.'), person('Evdokimov', 'V.V.')],
    'FGDC-2817': [person('Kavakina', 'S.V.'), person('Sapozhnikov', 'V.V.')],
    'FGDC-2586': [org(NAVY)],
    **{sid: [org(JODC)] for sid in RDMDB},
    **{sid: [org(JMA)] for sid in RRTDB},
}

# Legacy creators of the decided cohorts (the 436 manifest), in the legacy payload format.
DECIDED_LEGACY = {
    'FGDC-1206': [{'name': 'Biryukova, I.V.'}, {'name': 'Matrosov, V.V.'}, {'name': 'Evdokimov, V.V.'}],
    'FGDC-2817': [{'name': 'Kavakina, S.V.'}, {'name': 'Sapozhnikov, V.V.'}],
    'FGDC-2586': [{'name': NAVY, 'type': 'Organization'}],
    **{sid: [{'name': JODC, 'type': 'Organization'}] for sid in RDMDB},
    **{sid: [{'name': JMA, 'type': 'Organization'}] for sid in RRTDB},
}

TYPES = {
    'FGDC-227': ('dataset', 'landing statistics and catch composition data (PacFIN); the entry describes the data'),
    'FGDC-288': ('dataset', 'stable isotope measurements of sediment trap and plankton samples; the entry describes the data'),
    'FGDC-572': ('dataset', 'ADF&G/NBS data layer: subsistence seal kill locations'),
    'FGDC-648': ('dataset', 'ADEC database of the August 1990 shoreline survey files'),
    'FGDC-710': ('dataset', 'satellite telemetry data of harbor and spotted seals'),
    'FGDC-711': ('dataset', 'moose aerial survey data, 1994-1995'),
    'FGDC-758': ('dataset', 'subsistence harvest areas by community'),
    'FGDC-759': ('dataset', 'food sample sites on beaches in the EVOS area'),
    'FGDC-761': ('dataset', 'subsistence harvest areas by interviewed households'),
    'FGDC-766': ('dataset', 'subsistence harvest areas for 14 resources'),
    'FGDC-802': ('dataset', 'the Digital Chart of the World vector basemap, a data product on CD-ROM'),
    'FGDC-862': ('dataset', 'relational database of species occurrences, sites and managed areas'),
    'FGDC-870': ('publication-report', 'an atlas of maps and legal descriptions of 31 state refuges, critical habitat '
                 'areas and sanctuaries, with free hard copies; the entry describes the printed atlas, typed as the '
                 'Alaska Intertidal Survey Atlas (FGDC-3422) and Alaska\'s Fisheries Atlas (FGDC-3040); low confidence, '
                 'the GIS atlases FGDC-881 and FGDC-2104 are typed dataset'),
    'FGDC-1770': ('dataset', 'SeaWiFS satellite ocean colour data'),
    'FGDC-1771': ('dataset', 'CZCS satellite ocean colour data'),
    'FGDC-1864': ('dataset', 'oceanographic temperature and salinity database'),
    'FGDC-3687': ('dataset', 'image database of ichthyology type specimens'),
    'FGDC-4027': ('dataset', 'forecast system output (daily chemical weather maps); the entry describes the model '
                  'system and its products, typed as the OFES model output FGDC-4039; low confidence'),
    'FGDC-4039': ('dataset', 'OFES model output (climatology and hindcast at 0.1 and 0.5 degree), typed as the '
                  'siblings FGDC-4037 and FGDC-4038'),
    'FGDC-1318': ('dataset', 'a CD-ROM compilation of 150 maps and tables about Alaska, a data product; typed as the '
                  'CD-ROM data synthesis FGDC-1995; low confidence'),
    'FGDC-1994': ('publication-report', 'GEM nearshore literature-metadatabase entry describing a 1977 ADF&G report '
                  '("This report references harvest data ..."), typed as the sibling entry FGDC-1993 and the 409 '
                  'Exxon412 literature entries'),
    'FGDC-4063': ('dataset', 'project description of the POST acoustic tracking array, no document described; typed '
                  'as the POST Project Database FGDC-4064 and the ONR project descriptions FGDC-3593 and FGDC-3596'),
    'FGDC-1206': ('publication-report', 'a journal article (Tsitologiia / Journal of Cytology, 1998); the abstract is '
                  'the paper abstract, typed as the bibliography entry FGDC-1205'),
    'FGDC-2817': ('publication-report', 'a journal article (Okeanologiya 1993; Oceanology 33:768-773, 1995); purpose '
                  '"To report on ..."; typed as the sibling paper FGDC-2816 and the related FGDC-2664'),
    'FGDC-2586': ('publication-report', 'NOAA/NCDC Foreign Data Library holding: a printed atlas of monthly normal '
                  'pressure-altitude charts ("Publication Title: ..."), typed as the sibling holding FGDC-2585'),
    **{sid: ('dataset', 'NEAR-GOOS RDMDB global data set served with a user account, typed as the sibling RDMDB sets '
                        'FGDC-3951 to FGDC-3969') for sid in RDMDB},
    **{sid: ('dataset', 'NEAR-GOOS RRTDB GTS report set served with a user account') for sid in RRTDB},
    'FGDC-4139': ('dataset', 'moored sediment trap data 1982-2000, typed as the DFO OSAP siblings FGDC-4140 and FGDC-4180'),
    'FGDC-4161': ('dataset', 'oceanographic observations of the Haida eddy, 1999-2000'),
    'FGDC-4181': ('dataset', 'ship-of-opportunity surface carbon and nutrient data, 1980-present'),
    'FGDC-1422': ('dataset', 'cruise mooring retrieval and deployment data (MF2002-01 leg 1), typed as the neighbour FGDC-1421'),
    'FGDC-1423': ('dataset', 'bottom trawl survey data (MF2002-01 leg 2)'),
}
LOW_CONFIDENCE = ['FGDC-870', 'FGDC-1318', 'FGDC-4027']

HOLD = {
    'FGDC-2817': ('Brett decided the creators (B2), but the record has a second blocker he did not decide: its metadata '
                  'access text "Check with Contributor" with the use text "Refer to webstite URL: http://www.csa.com/" '
                  'is outside the exact821 scope answer (which binds four identical "Check with Contributor" fields) '
                  'and was not a question on the evidence sheet. The decided creators are recorded here for the day '
                  'the access text is decided; until then the record stays held.'),
}

# The creator sentence of each paragraph: how the modern creators relate to the literal credit.
CREATOR_SENTENCES = {
    'FGDC-288': (
        'The primary citation reads "Stacy Smith, Susan M. Henrichs of the University of Alaska, Fairbanks". The legacy '
        'metadata typed this compound as one organisation because it contains the word University; the record credits '
        'two people, who are credited personally in source order, Smith, Stacy and Henrichs, Susan M., with the shared '
        'affiliation University of Alaska, Fairbanks, which the citation attaches to the connected list with "of". The '
        'point of contact, Henrichs, Susan M., confirms the second family name; the first name is in natural order. '
        'No spelling is changed.'),
    'FGDC-1864': (
        'The primary citation reads "Pacific Oceanological Institute (POI), Ed (by support of Russian NODC, Nav ODC '
        'and others as compilers)". The institute is credited as an organisational creator under its cited name, '
        'Pacific Oceanological Institute (POI); the abbreviation Ed and the compiler-support clause naming Russian '
        'NODC, Nav ODC and others are roles and support, not name parts, and are preserved here; no supporting body '
        'is added as a creator.'),
    'FGDC-4027': (
        'The primary citation lists Japan Agency for Marine-Earth Science and Technology (JAMSTEC); National Space '
        'Development Agency (NASDA), Japan; Hajime Akimoto; Atmospheric Composition Research Program, Frontier '
        'Research System for Global Change (FRSGC); Masaaki Takahashi and Masayuki Takigawa; Center for Climate '
        'System Research, University of Tokyo. The two institutional credits are credited as organisational creators '
        'and the three named people personally, in source order and natural name order (Akimoto, Hajime; Takahashi, '
        'Masaaki; Takigawa, Masayuki); the point of contact, Akimoto, Hajime, confirms the first family name. The '
        'semicolon-separated programme and university qualifications stay in this preserved citation and are not '
        'added as affiliations, as the reviewed creator426 cohort note says.'),
    'FGDC-4063': (
        'The primary citation displays Census of Marine Life and Vancouver Aquarium separated by a line break; both '
        'are credited as organisational creators in source order without merging, as the reviewed creator426 cohort '
        'note says. Their relationship is not resolved and the point of contact, Tsang, Peggy, is not promoted.'),
    'FGDC-1994': (
        'The primary citation reads "Exxon Valdez Oil Spill Trustee Council, James Bodkin of the U.S. Geological '
        'Survey, Anchorage, Alaska and Thomas A. Dean of Coastal Resources Associates, Inc., Carlsbad, California." '
        'and is credited as the reviewed Exxon821 projection, as the 412 published Exxon singletons are: the Trustee '
        'Council as an organisation, Bodkin, James and Dean, Thomas A. personally with the affiliations the citation '
        'attaches with "of".'),
    'FGDC-710': (
        'The primary citation credits Wildlife Conservation Division, Alaska Department of Fish and Game, credited as '
        'an organisational creator exactly as cited (reviewed creator426 cohort plain_institution_program_37_FGDC-710).'),
}

DECIDED_SENTENCES = {
    'FGDC-1206': (
        'Creators: the primary citation origin of this FGDC record reads "Journal of Cytology", the journal in which '
        'the work appeared, not an author. Brett Johnson decided on 2026-10-23 (held-sources question B1, asked '
        '"Credit Biryukova, I.V.; Matrosov, V.V.; Evdokimov, V.V., in this order?", answered "Yes, three authors") '
        'that the creators are Biryukova, I.V.; Matrosov, V.V.; Evdokimov, V.V., in this order, credited personally. '
        'The evidence recorded on the sheet: a 2006 Curonian Spit National Park scientific collection (vol. 4, '
        'reference 5) gives "Бирюкова И.В., Матросов В.В., Евдокимов В.В." for Tsitologiia 1998, vol. 40, no. 1, '
        'pp. 5-9, and a thesis gives the same three names in the same order; the article itself was not checked. The '
        'point of contact, Biryukova, Inga V., is a separate role; the initials are kept as cited and not expanded '
        'from it. The journal stays in this preserved citation.'),
    'FGDC-2817': (
        'Creators: the primary citation origin of this FGDC record reads "Okeanologiya. Moscow", the journal, not an '
        'author. Brett Johnson decided on 2026-10-23 (held-sources question B2, asked "Credit Kavakina, S.V.; '
        'Sapozhnikov, V.V., in this order?", answered "Yes, both") that the creators are Kavakina, S.V.; Sapozhnikov, '
        'V.V., in this order, credited personally. The evidence recorded on the sheet: a 2008 paper cites "Kavakina SV, '
        'Sapozhnikov VV", Oceanology 33:768-773, the 1995 English edition of the 1993 Russian article, and the related '
        'record FGDC-2664 is published with the creator Sapozhnikov, V. V. The point of contact, Kavakina, S.V., '
        'confirms the first name. The journal stays in this preserved citation.'),
    'FGDC-2586': (
        'Creators: the primary citation origin of this FGDC record reads "Published by direction of the Chief of Naval '
        'Operations.", an instruction to publish, not a named producer. Brett Johnson decided on 2026-10-23 '
        '(held-sources question B3, asked "Credit the issuer, \'United States Navy, Office of the Chief of Naval '
        'Operations\', as an organisation creator?", answered "Yes, the Navy office") that the issuer, United States '
        'Navy, Office of the Chief of Naval Operations, is credited as an organisational creator. The NOAA/NCEI '
        'holding SN-240, box AA96144, confirms the 1953 title and names no author. The contact, NOAA Central Library, '
        'is the holding library and is not promoted.'),
    **{sid: (
        'Creators: the primary citation origin of this FGDC record is empty. Brett Johnson decided on 2026-10-23 '
        '(held-sources question B4, asked "Which creator for the seven NEAR-GOOS records with an empty origin?", '
        'answered "JODC / JMA by operator") that the operator of the database is credited: the Japan Oceanographic '
        'Data Center, which operates the NEAR-GOOS Regional Delayed Mode Data Base (RDMDB) this record describes, '
        'credited as an organisational creator. The RDMDB manual says "The Japan Oceanographic Data Center (JODC) '
        'operates the RDMDB". The point of contact, Okano, Hirofumi, is a separate role and is not promoted; no data '
        'producer is named as a creator.') for sid in RDMDB},
    **{sid: (
        'Creators: the primary citation origin of this FGDC record is empty. Brett Johnson decided on 2026-10-23 '
        '(held-sources question B4, asked "Which creator for the seven NEAR-GOOS records with an empty origin?", '
        'answered "JODC / JMA by operator") that the operator of the database is credited: the Japan Meteorological '
        'Agency, which operates the NEAR-GOOS Regional Real Time Data Base (RRTDB) at goos.kishou.go.jp this record '
        'describes, credited as an organisational creator. The point of contact, Yoshida, Takashi, is a separate role '
        'and is not promoted; no data producer is named as a creator.') for sid in RRTDB},
}

CONTEXT_NOTES = {
    sid: 'Reviewed citation context: ' + sentence + ' No XML authorship, rights, access meaning or release is inferred.'
    for sid, sentence in DECIDED_SENTENCES.items()
}

# ------------------------------------------------------------------ helpers


def norm(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def recursive_text(node):
    return norm(''.join(node.itertext()))


def field(root, xpath):
    node = root.find(xpath)
    return recursive_text(node) if node is not None else ''


def elements(root, xpath):
    result = []
    for node in root.findall(xpath):
        node = deepcopy(node)
        node.tail = None
        result.append(ET.tostring(node, encoding='unicode'))
    return result


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def dumps(value):
    return (json.dumps(value, indent=1, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')


def reference(path):
    return {'manifest_path': str(path.relative_to(ROOT)), 'manifest_sha256': sha(path.read_bytes())}


def quote(path, needle):
    raw = path.read_text(encoding='utf-8')
    if needle not in raw:
        raise SystemExit(f'quote not found in {path}: {needle[:80]}')
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes()), 'quote': needle}


def sheet_row(number):
    for line in SHEET.read_text(encoding='utf-8').splitlines():
        if line.startswith('| ' + str(number) + ' |') or line.startswith('| **' + str(number) + '** |'):
            return line
    raise SystemExit(f'no evidence sheet row for {number}')


def xml_evidence(root, xpath, label):
    return [{'kind': 'xml', 'xpath': xpath, 'label': label, 'text': recursive_text(node)} for node in root.findall(xpath)]


def load_decisions():
    decisions = json.loads(DECISIONS.read_bytes())
    questions, groups = {}, {}
    for row in decisions['decisions']:
        if row['effect'] == 'stays held' or row['question'] == 'D1':
            continue
        for sid in row['sources']:
            assert sid not in questions
            questions[sid] = row
            groups[sid] = GROUPS[row['question'][0]]
    members = sorted(questions, key=lambda s: int(s[5:]))
    assert len(members) == decisions['cleared_for_review'] == 37
    assert not set(members) & set(decisions['stay_held']) and not set(members) & set(decisions['retired'])
    return decisions, questions, groups, members


def parsed(sid):
    raw = (ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
    return raw, sha(raw), ET.fromstring(raw)


# ------------------------------------------------------------------ stage 1: evidence manifests


def build_scope(decisions, questions, groups, members):
    base = json.loads(SCOPE_904.read_bytes())
    assert len(base['members']) == 904
    access = [sid for sid in members if groups[sid] == 'access']
    assert len(access) == 22
    by_question = {}
    for sid in access:
        by_question.setdefault(questions[sid]['question'], []).append(sid)
    added = []
    for sid in access:
        raw, digest, root = parsed(sid)
        question = questions[sid]['question']
        for xpath in CONSTRAINT_XPATHS:
            nodes = root.findall(xpath)
            assert len(nodes) == 1 and not list(nodes[0]) and not nodes[0].attrib, (sid, xpath)
        assert field(root, './metainfo/metac') == field(root, './idinfo/accconst'), sid
        assert field(root, './metainfo/metuc') == field(root, './idinfo/useconst'), sid
        assert root.find('./metainfo/metsi') is None and root.find('./metainfo/metextns') is None
        added.append({
            'cohort': 'held_access_' + question, 'decision_question': question,
            'constraint_elements': {xpath: elements(root, xpath) for xpath in CONSTRAINT_XPATHS},
            'context_elements_sha256': {xpath: canonical(elements(root, xpath)) for xpath in CONTEXT_XPATHS},
            'question_membership_sha256': canonical([{'source_id': s, 'source_sha256': parsed(s)[1]}
                                                     for s in by_question[question]]),
            'source_id': sid, 'source_sha256': digest})
    cohorts = {}
    for question, ids in by_question.items():
        row = questions[ids[0]]
        cohorts['held_access_' + question] = {
            'question': question, 'asked': row['asked'], 'answer': row['answer'], 'effect': row['effect'],
            'meaning': MEANINGS[question], 'count': len(ids), 'members': ids,
            'membership_sha256': canonical([{'source_id': s, 'source_sha256': parsed(s)[1]} for s in ids])}
    block = {
        'status': 'USER_ATTESTED', 'evidence_type': 'USER_ATTESTED', 'decided_by': decisions['decided_by'],
        'decided_at': decisions['decided_at'], 'attested_at': '2026-10-23T00:00:00Z', 'timestamp_precision': 'day',
        'channel': decisions['channel'],
        'statement': ('Brett Johnson answered the held-sources evidence sheet on 2026-10-23: A1 "Yes, data only"; '
                      'A2 "Yes, catalogue entry"; A3 "Yes, data service". A cleared hold is not a publication approval.'),
        'meaning': 'underlying_data_or_product_restrictions_catalogue_record_previously_public',
        'cohorts': cohorts, 'added_member_count': len(added),
        'original_statement_references': [
            {'key': 'reconciled904', **reference(SCOPE_904), 'statement': base['statement'],
             'original_attested_at': base['attested_at'], 'original_scope': base['scope'],
             'original_limits': base['restrictions_preserved']},
            {'key': 'held_sources_decisions', **reference(DECISIONS), 'statement': None,
             'original_attested_at': decisions['decided_at'], 'original_scope': 'questions A1, A2 and A3 of the sheet',
             'original_limits': decisions['note']},
            {'key': 'held_sources_evidence_sheet', **reference(SHEET), 'statement': None, 'original_attested_at': None,
             'original_scope': 'the evidence and the questions Brett answered', 'original_limits': None}],
        'restrictions_preserved': (
            'All original constraints and XML remain intact. The constraint texts stay in the public record exactly '
            'as they are: the v2 record maps them to a rights statement and no licence is granted. Separate '
            'user-attested rehosting authority keeps the XML artifact policy restricted and unlicensed. No '
            'attribution, date, title or alias hold is cleared by this decision.'),
        'grants_rehosting': False, 'grants_new_license': False, 'underlying_data_rights_granted': False,
        'publication_approved': False, 'new_user_attestation_event': True, 'original_904_membership_enlarged': True,
    }
    manifest = deepcopy(base)
    manifest['members'] = base['members'] + added
    manifest['held_sources_decisions_2026_10_23'] = block
    SCOPE_OUT.write_bytes(dumps(manifest))
    return {'reconciled_object_sha256': canonical(base), 'decided_manifest_sha256': sha(SCOPE_OUT.read_bytes()),
            'added': len(added)}


def build_credits(decisions, questions, groups, members):
    base = json.loads(CREDITS_426.read_bytes())
    assert len(base['cohorts']) == 249 and base['profile'] == 'source_citation_credits_426'
    covered = {m['source_id'] for c in base['cohorts'] for m in c['members']}
    creators = [sid for sid in members if groups[sid] == 'creators']
    assert creators == sorted(DECIDED_LEGACY, key=lambda s: int(s[5:])) and not set(creators) & covered
    cohorts = []
    for sid in creators:
        raw, digest, root = parsed(sid)
        origins = root.findall(ORIGIN_XPATH)
        assert len(origins) == 1 and not origins[0].attrib and not list(origins[0]), sid
        row = questions[sid]
        supplemental = [{'xpath': xpath, 'element': source_element(root.find(xpath))}
                        for xpath in (CONTACT_XPATH, './idinfo/citation/citeinfo/title') if root.find(xpath) is not None]
        cohorts.append({
            'profile': 'held_creators_' + row['question'] + '_' + sid,
            'members': [{'source_id': sid, 'source_sha256': digest}],
            'creators': DECIDED_LEGACY[sid], 'raw_origin': origins[0].text,
            'primary_origin_element': source_element(origins[0]), 'preservation_required': True,
            'context_note': CONTEXT_NOTES[sid], 'evidence_type': 'USER_DECIDED',
            'decision': {'question': row['question'], 'asked': row['asked'], 'answer': row['answer'],
                         'effect': row['effect'], 'decided_by': decisions['decided_by'], 'decided_at': decisions['decided_at']},
            'supplemental_source_elements': supplemental})
    manifest = deepcopy(base)
    manifest.update({
        'profile': 'source_citation_credits_436', 'prior_manifest_sha256': sha(CREDITS_426.read_bytes()),
        'previous_cohort_count': len(base['cohorts']), 'reviewed_decisions_sha256': sha(DECISIONS.read_bytes()),
        'interpretation': (
            'Preserve all 426 prior members and 249 cohort objects verbatim. Add ten cohorts for the creator holds '
            'Brett Johnson decided on 2026-10-23 (held_sources_decisions.json, questions B1 to B4): three personal '
            'creators for FGDC-1206, two for FGDC-2817, the issuing Navy office for FGDC-2586, the Japan Oceanographic '
            'Data Center for the five RDMDB records and the Japan Meteorological Agency for the two RRTDB records. '
            'Each cohort binds the exact origin element, the contact and title elements and the decision; the '
            'original origin is preserved in the notes. No XML authorship, access meaning, licence or release is '
            'granted; FGDC-2817 keeps its separate access hold.'),
        'held_sources_decision_review': {
            'evidence_type': 'USER_DECIDED', 'decided_by': decisions['decided_by'], 'decided_at': decisions['decided_at'],
            'channel': decisions['channel'], 'decisions': reference(DECISIONS), 'evidence_sheet': reference(SHEET),
            'cohort_profiles': [c['profile'] for c in cohorts],
            'limits': 'Primary citation attribution for ten exact sources only; roles, rights, dates and access are unchanged.'},
        'cohorts': base['cohorts'] + cohorts})
    CREDITS_OUT.write_bytes(dumps(manifest))
    return {'credits_manifest_sha256': sha(CREDITS_OUT.read_bytes()), 'added': len(cohorts)}


def metd_of(sid):
    raw, digest, root = parsed(sid)
    return field(root, './metainfo/metd')


def build_dates(decisions, questions, groups, members):
    dates = [sid for sid in members if groups[sid] == 'metadata_date']
    assert dates == ['FGDC-1422', 'FGDC-1423', 'FGDC-4139', 'FGDC-4161', 'FGDC-4181']
    # The neighbour evidence the sheet gives, checked against the files.
    dfo = [p.stem for p in sorted((ROOT / 'FGDC').glob('FGDC-*.xml'), key=lambda p: int(p.stem[5:]))
           if p.stem not in ('FGDC-21', 'FGDC-4077', 'FGDC-4184', 'FGDC-4185', 'FGDC-3373', 'FGDC-3484')
           and field(ET.fromstring(p.read_bytes()), ORIGIN_XPATH) == DFO_ORIGIN]
    dfo_dates = {sid: metd_of(sid) for sid in dfo if sid not in ('FGDC-4139', 'FGDC-4161', 'FGDC-4181')}
    assert len(dfo_dates) == 31 and min(dfo_dates.values()) == '20070418' and max(dfo_dates.values()) == '20080211'
    exact = sorted(sid for sid, value in dfo_dates.items() if value == '20080207')
    assert len(exact) == 7 and {'FGDC-4140', 'FGDC-4180'} <= set(exact)
    noaa_dates = {sid: metd_of(sid) for sid in NOAA_NEIGHBOURS if (ROOT / 'FGDC' / (sid + '.xml')).exists()}
    noaa = {sid for sid, value in noaa_dates.items() if value == '20030530'}
    assert len(noaa) == 21 and 'FGDC-1421' in noaa, sorted(noaa_dates.items())
    corrections = {}
    for sid in dates:
        raw, digest, root = parsed(sid)
        row = questions[sid]
        nodes = root.findall('./metainfo/metd')
        assert len(nodes) == 1 and not list(nodes[0]) and not nodes[0].attrib
        if row['question'] == 'C1':
            assert field(root, './metainfo/metd') == '2080207' and field(root, ORIGIN_XPATH) == DFO_ORIGIN
            corrections[sid] = {
                'source_sha256': digest, 'source_value': '2080207', 'corrected_value': '2008-02-07',
                'question': 'C1', 'asked': row['asked'], 'answer': row['answer'],
                'reason': ('A seven-digit value. Brett confirmed on 2026-10-23 that it is a typo for 20080207. The other 31 '
                           'DFO Ocean Science and Productivity records are dated 20070418 to 20080211, seven of them '
                           'exactly 20080207, including the neighbouring records FGDC-4140 and FGDC-4180.'),
                'neighbours': {'origin': DFO_ORIGIN, 'count': len(dfo_dates), 'earliest': '20070418',
                               'latest': '20080211', 'exactly_20080207': exact}}
        else:
            assert field(root, './metainfo/metd') == '' and field(root, ORIGIN_XPATH) == 'National Oceanic and Atmospheric Administration (NOAA)'
            corrections[sid] = {
                'source_sha256': digest, 'source_value': '', 'corrected_value': '2003-05-30',
                'question': 'C2', 'asked': row['asked'], 'answer': row['answer'],
                'reason': ('A blank value. Brett decided on 2026-10-23 that the metadata date is 2003-05-30, the metd of '
                           'all 21 neighbouring NOAA records FGDC-1410 to FGDC-1435, including FGDC-1421, also a 2002 survey.'),
                'neighbours': {'range': 'FGDC-1410 to FGDC-1435', 'count': len(noaa), 'metd': '20030530',
                               'members': sorted(noaa, key=lambda s: int(s[5:]))}}
    manifest = {
        'schema_version': 1, 'kind': 'pices-metadata-date-corrections-v1', 'status': 'USER_DECIDED',
        'evidence_type': 'USER_DECIDED', 'decided_by': decisions['decided_by'], 'decided_at': decisions['decided_at'],
        'channel': decisions['channel'], 'source_xpath': './metainfo/metd',
        'original_statement_references': [{'key': 'held_sources_decisions', **reference(DECISIONS)},
                                          {'key': 'held_sources_evidence_sheet', **reference(SHEET)}],
        'originals_unchanged': ('The FGDC files keep their source values. The corrected day is the prepared input\'s '
                                'publication date, enters the artifact policy\'s date evidence, and is the v2 '
                                'publication date when the citation gives no exact date, with a note that gives the '
                                'source value, the corrected value, the reason and the decision.'),
        'grants_rehosting': False, 'grants_new_license': False, 'publication_approved': False,
        'corrections': corrections}
    DATES_OUT.write_bytes(dumps(manifest))
    return {'date_corrections_sha256': sha(DATES_OUT.read_bytes()), 'corrections': len(corrections)}


def evidence():
    decisions, questions, groups, members = load_decisions()
    result = {}
    result.update(build_scope(decisions, questions, groups, members))
    result.update(build_credits(decisions, questions, groups, members))
    result.update(build_dates(decisions, questions, groups, members))
    print(json.dumps(result, indent=1, sort_keys=True))


# ------------------------------------------------------------------ stage 2: proposals, manifest, review, r6


def access_paragraph(sid, root, row):
    accconst, useconst = field(root, './idinfo/accconst'), field(root, './idinfo/useconst')
    return ('Access and use constraints: this FGDC record\'s metadata access and use fields (metainfo/metac and metuc) '
            'repeat its data access and use fields (idinfo/accconst and useconst) word for word; the access text reads "'
            + accconst + '" and the use text "' + useconst + '". Brett Johnson decided on 2026-10-23 (held-sources question '
            + row['question'] + ', asked "' + row['asked'] + '", answered "' + row['answer'] + '") that ' + MEANINGS[row['question']]
            + '. The texts are kept unchanged in this record and no licence is granted.')


def date_paragraph(sid, root, row, correction):
    if row['question'] == 'C1':
        return ('Metadata date: this FGDC record\'s metadata date (metainfo/metd) reads "2080207", seven digits. Brett '
                'Johnson confirmed on 2026-10-23 (held-sources question C1, asked "' + row['asked'] + '", answered "'
                + row['answer'] + '") that it is a typo for 20080207: the other 31 DFO Ocean Science and Productivity '
                'records are dated 20070418 to 20080211, seven of them exactly 20080207, including the neighbouring '
                'records FGDC-4140 and FGDC-4180. The publication date of this record is the corrected metadata date '
                '2008-02-07; the citation gives no exact date and the original XML is unchanged.')
    return ('Metadata date: this FGDC record\'s metadata date (metainfo/metd) is blank. Brett Johnson decided on 2026-10-23 '
            '(held-sources question C2, asked "' + row['asked'] + '", answered "' + row['answer'] + '") that the metadata '
            'date is 2003-05-30, the metd of all 21 neighbouring NOAA records FGDC-1410 to FGDC-1435, including FGDC-1421, '
            'also a 2002 survey. The publication date of this record is that corrected metadata date; the citation gives '
            'no exact date and the original XML is unchanged.')


def creator_sentence(sid, legacy):
    if sid in CREATOR_SENTENCES:
        return CREATOR_SENTENCES[sid]
    assert len(legacy) == 1, (sid, legacy)
    if legacy == [{'name': DFO_ORIGIN}]:
        return ('The primary citation credits ' + DFO_ORIGIN + ', credited as an organisational creator exactly as '
                'cited, as the reviewed institutional policy publishes the sibling records FGDC-4140 and FGDC-4180.')
    assert legacy[0].get('type') == 'Organization', (sid, legacy)
    return ('The primary citation credits ' + legacy[0]['name']
            + ', credited as an organisational creator exactly as cited.')


def lane(classified, baseline):
    decisions, questions, groups, members = load_decisions()
    classification = json.loads((classified / 'classification.json').read_text())
    assert classification['reviewed_at'] == REVIEWED_AT, classification['reviewed_at']
    class_rows = {row['source_id']: row for row in classification['records']}
    baseline_rows = {row['source_id']: row for row in json.loads((baseline / 'classification.json').read_text())['records']}
    assert set(class_rows) == set(baseline_rows) == set(members)
    credits = json.loads(CREDITS_OUT.read_bytes())
    cohort_by_member = {m['source_id']: c for c in credits['cohorts'] for m in c['members']}
    exxon = pinned(EXXON_PROFILE, EXXON_SHA)
    exxon_modern = pinned(EXXON_MAPPING, EXXON_MAPPING_SHA)['modern_creators']
    exxon_members = {m['source_id']: m['source_sha256'] for m in exxon['members']}
    scope = json.loads(SCOPE_OUT.read_bytes())
    scope_members = {m['source_id']: m for m in scope['members'][904:]}
    dates = json.loads(DATES_OUT.read_bytes())['corrections']
    targets = {row['record_target_id']: row for row in pinned(PLAN, PLAN_SHA)['targets']}
    inputs = {str(path.relative_to(ROOT)): sha(path.read_bytes())
              for path in (DECISIONS, SHEET, SCOPE_OUT, CREDITS_OUT, DATES_OUT, PLAN, PROFILE, EXXON_PROFILE, EXXON_MAPPING)}

    proposals, rows, types, type_notes = [], [], {}, {}
    for index, sid in enumerate(members):
        raw, digest, root = parsed(sid)
        row, group = questions[sid], groups[sid]
        target = targets[sid]
        assert target['source_ids'] == [sid] and target['source_semantic_status'] == 'held'
        assert target['source_sha256'] == digest and target['identity_decision']['production_record_id'] is None
        assert target['identity_decision']['production_doi'] is None and sid not in PROTECTED
        fresh = class_rows[sid]
        input_path = classified / 'data/zenodo_json' / (sid + '.json')
        payload = json.loads(input_path.read_text()) if input_path.exists() else None
        legacy = payload['metadata']['creators'] if payload else None
        policy = payload['artifact_policy'] if payload else {}
        creator_reference = policy.get('creator_interpretation')
        decision = 'hold' if sid in HOLD else 'admit'
        if decision == 'admit':
            assert fresh['source_status'] == 'supported' and fresh['hold_reasons'] == [], (sid, fresh['hold_reasons'])
        else:
            assert fresh['source_status'] == 'held' and fresh['hold_reasons'] == [
                'Metadata access terms need source-backed adjudication',
                'Contradictory or unsupported source access constraints require adjudication'], (sid, fresh['hold_reasons'])
        # Which authority produced the legacy creators of the fresh input.
        if sid in cohort_by_member:
            cohort = cohort_by_member[sid]
            kind, cohort_name, authority_object = 'credits', cohort['profile'], cohort
            assert cohort['creators'] == legacy and creator_reference['manifest_sha256'] == sha(CREDITS_OUT.read_bytes())
            if group == 'creators':
                assert cohort['profile'].startswith('held_creators_' + row['question'])
        elif sid in exxon_members:
            kind, cohort_name, authority_object = 'exxon', exxon['profile'], exxon
            assert exxon['creators'] == legacy and creator_reference['manifest_sha256'] == EXXON_SHA
        else:
            # The default primary-citation reading of the fresh input: an organisation the transformer recognised,
            # or (the three DFO OSAP records) the literal name the institution91 policy publishes organisational.
            kind, cohort_name, authority_object = 'direct', None, legacy
            assert creator_reference is None and legacy and all(
                set(c) in ({'name'}, {'name', 'type'}) and c.get('type', 'Organization') == 'Organization'
                for c in legacy), (sid, legacy)
            assert all('type' in c or c['name'] == DFO_ORIGIN for c in legacy), (sid, legacy)
        modern = MODERN.get(sid) or (exxon_modern if kind == 'exxon' else [org(c['name']) for c in legacy])
        correction = None
        if group == 'metadata_date':
            entry = dates[sid]
            assert policy['metadata_date_correction']['manifest_sha256'] == sha(DATES_OUT.read_bytes())
            assert payload['metadata']['publication_date'] == entry['corrected_value']
            correction = {'source_value': entry['source_value'], 'corrected_value': entry['corrected_value'],
                          'question': entry['question']}
        if group == 'access':
            assert policy['source_scope_attestation']['manifest_sha256'] == sha(SCOPE_OUT.read_bytes())
            assert scope_members[sid]['cohort'] == 'held_access_' + row['question']
        paragraph = (access_paragraph(sid, root, row) + ' ' + creator_sentence(sid, legacy) if group == 'access' else
                     DECIDED_SENTENCES[sid] if group == 'creators' else
                     date_paragraph(sid, root, row, correction) + ' ' + creator_sentence(sid, legacy))
        evidence = [{'kind': 'xml', **item} for item in
                    xml_evidence(root, ORIGIN_XPATH, 'citation origin')
                    + xml_evidence(root, './idinfo/citation/citeinfo/title', 'citation title')
                    + xml_evidence(root, './idinfo/citation/citeinfo/pubdate', 'citation publication date')
                    + xml_evidence(root, './idinfo/descript/purpose', 'purpose')
                    + xml_evidence(root, './idinfo/descript/abstract', 'abstract')
                    + xml_evidence(root, CONTACT_XPATH, 'point of contact person')
                    + xml_evidence(root, './idinfo/accconst', 'data access constraints')
                    + xml_evidence(root, './idinfo/useconst', 'data use constraints')
                    + xml_evidence(root, './metainfo/metac', 'metadata access constraints')
                    + xml_evidence(root, './metainfo/metuc', 'metadata use constraints')
                    + xml_evidence(root, './metainfo/metd', 'metadata date')]
        evidence.append({'kind': 'file', **quote(DECISIONS, '"question": "' + row['question'] + '"')})
        evidence.append({'kind': 'file', **quote(DECISIONS, '"answer": "' + row['answer'] + '"')})
        evidence.append({'kind': 'file', **quote(SHEET, sheet_row(int(sid[5:])))})
        if kind == 'credits' and group != 'creators':
            evidence.append({'kind': 'file', **quote(CREDITS_426, '"profile": "' + cohort_name + '"')})
        if kind == 'exxon':
            evidence.append({'kind': 'file', **quote(EXXON_PROFILE, '"source_id": "' + sid + '"')})
        if legacy == [{'name': DFO_ORIGIN}]:
            evidence.append({'kind': 'file', **quote(INSTITUTION_MAPPING, '"name": "' + DFO_ORIGIN + '"')})
        resource_type, type_note = TYPES[sid]
        proposal = {
            'source_id': sid, 'source_sha256': digest, 'source_path': 'FGDC/' + sid + '.xml', 'source_bytes': len(raw),
            'hold_group': group, 'decision_question': row['question'], 'decision': decision,
            'reason': HOLD.get(sid) or ('Admitted: Brett\'s ' + row['question'] + ' answer clears the only hold the '
                                        'runbook classification raised; see the preservation paragraph.'),
            'owner_decision': {'question': row['question'], 'asked': row['asked'], 'answer': row['answer'],
                               'effect': row['effect'], 'decided_by': decisions['decided_by'],
                               'decided_at': decisions['decided_at']},
            'baseline_hold_reasons': baseline_rows[sid]['hold_reasons'],
            'remaining_hold_reasons': fresh['hold_reasons'],
            'citation_origin_texts': [recursive_text(node) for node in root.findall(ORIGIN_XPATH)],
            'primary_origin_elements': [source_element(node) for node in root.findall(ORIGIN_XPATH)],
            'source_root_sha256': sha(encode(source_element(root))),
            'legacy_creators': legacy,
            'legacy_creator_authority': {'kind': kind, 'creator_cohort': cohort_name,
                                         'object_sha256': sha(encode(authority_object))},
            'proposed_creators': modern if decision == 'admit' else None,
            'decided_creators': modern if group == 'creators' else None,
            'metadata_date_correction': correction,
            'additional_preservation_paragraph': paragraph if decision == 'admit' else None,
            'paragraph_if_admitted': paragraph if decision == 'hold' else None,
            'proposed_resource_type': resource_type, 'resource_type_note': type_note,
            'fresh_classification': {'reviewed_at': classification['reviewed_at'], 'source_status': fresh['source_status'],
                                     'prepared_input_sha256': fresh.get('prepared_payload_sha256')},
            'evidence': evidence,
        }
        proposals.append(proposal)
        types[sid], type_notes[sid] = resource_type, type_note
        if decision == 'admit':
            rows.append({
                'source_id': sid, 'source_sha256': digest, 'source_path': 'FGDC/' + sid + '.xml',
                'source_bytes': len(raw), 'source_root_sha256': proposal['source_root_sha256'],
                'source_plan_target_sha256': sha(encode(target)), 'hold_group': group,
                'decision_question': row['question'], 'creator_authority_kind': kind, 'creator_cohort': cohort_name,
                'creator_authority_object_sha256': proposal['legacy_creator_authority']['object_sha256'],
                'creators': legacy, 'modern_creators': modern, 'primary_origins': proposal['primary_origin_elements'],
                'metadata_date_correction': correction, 'additional_preservation_paragraphs': [paragraph],
                'proposal_row_pointer': '/proposals/' + str(index), 'proposal_row_sha256': sha(encode(proposal))})

    admitted = [{'source_id': r['source_id'], 'source_sha256': r['source_sha256']} for r in rows]
    held = [{'source_id': p['source_id'], 'source_sha256': p['source_sha256']} for p in proposals if p['decision'] == 'hold']
    proposals_document = {
        'schema_version': 1, 'kind': 'held37-source-proposals-v1',
        'status': 'PROPOSAL_PENDING_INDEPENDENT_REVIEW_NOT_EXECUTION_AUTHORITY',
        'proposed_by': PROPOSED_BY, 'instruction': INSTRUCTION, 'policy': POLICY, 'conventions': CONVENTIONS,
        'inputs': inputs,
        'fresh_classification': {
            'command': ('python -B -m scripts.collection_qa over the 37 XML files with the runbook manifest set '
                        '(docs/readiness/2026-10-06/first_pices_record_runbook.md L57) with '
                        'docs/readiness/2026-10-23/source_citation_credits_436.json as the institution creator manifest, '
                        'docs/readiness/2026-10-23/source_scope_decisions_926.json as the source scope manifest and '
                        '--metadata-date-correction-manifest docs/readiness/2026-10-23/metadata_date_corrections_5.json, '
                        '--reviewed-at ' + REVIEWED_AT),
            'reviewed_at': REVIEWED_AT, 'profile_sha256': classification['profile_sha256'],
            'summary': classification['summary']['source_status_counts']},
        'counts': {'members': len(members), 'admit': len(admitted), 'hold': len(held),
                   'admit_by_group': dict(sorted(_count(rows, 'hold_group').items())),
                   'admit_by_question': dict(sorted(_count(rows, 'decision_question').items())),
                   'admit_by_creator_authority': dict(sorted(_count(rows, 'creator_authority_kind').items())),
                   'modern_creator_objects': sum(len(r['modern_creators']) for r in rows)},
        'members': [{'source_id': sid, 'source_sha256': targets[sid]['source_sha256']} for sid in members],
        'admitted_members': admitted, 'held_members': held, 'proposals': proposals,
    }
    proposals_path = OUT / 'held37_proposals.json'
    proposals_path.write_bytes(dumps(proposals_document))
    proposals_sha = sha(proposals_path.read_bytes())

    manifest = {
        'schema_version': 1, 'kind': 'modern-reviewed-held37-v1', 'policy': POLICY,
        'source_plan_sha256': PLAN_SHA, 'creator426_profile_sha256': PROFILE_SHA,
        'exxon_profile_sha256': EXXON_SHA, 'exxon_mapping_sha256': EXXON_MAPPING_SHA,
        'decisions_path': str(DECISIONS.relative_to(ROOT)), 'decisions_sha256': sha(DECISIONS.read_bytes()),
        'credits_path': str(CREDITS_OUT.relative_to(ROOT)), 'credits_sha256': sha(CREDITS_OUT.read_bytes()),
        'scope_path': str(SCOPE_OUT.relative_to(ROOT)), 'scope_sha256': sha(SCOPE_OUT.read_bytes()),
        'date_corrections_path': str(DATES_OUT.relative_to(ROOT)), 'date_corrections_sha256': sha(DATES_OUT.read_bytes()),
        'proposals_path': str(proposals_path.relative_to(ROOT)), 'proposals_sha256': proposals_sha,
        'member_count': len(rows), 'members': admitted, 'membership_sha256': sha(encode(admitted)),
        'authority_counts': dict(sorted(_count(rows, 'creator_authority_kind').items())),
        'hold_group_counts': dict(sorted(_count(rows, 'hold_group').items())),
        'modern_creator_object_count': sum(len(r['modern_creators']) for r in rows),
        'context_sha256': sha(encode({r['source_id']: r['additional_preservation_paragraphs'] for r in rows})),
        'conventions': CONVENTIONS, 'rows': rows,
    }
    manifest_path = OUT / 'modern_reviewed_held37.json'
    manifest_path.write_bytes(dumps(manifest))
    manifest_sha = sha(manifest_path.read_bytes())

    review = {
        'schema_version': 1, 'kind': 'modern-reviewed-held37-review-v1', 'policy': POLICY,
        'status': 'proposal pending independent review',
        'mapping_manifest_path': str(manifest_path.relative_to(ROOT)), 'mapping_manifest_sha256': manifest_sha,
        'proposals_path': str(proposals_path.relative_to(ROOT)), 'proposals_sha256': proposals_sha,
        'proposed_by': PROPOSED_BY, 'reviewer': None, 'reviewed_at': None,
        'members': admitted, 'membership_sha256': sha(encode(admitted)),
        'approved_members': [], 'held_members': [],
        'decisions': {r['source_id']: {'decision': 'pending', 'note': None} for r in rows},
        'reviewer_checklist': [
            'Read every row against FGDC/<id>.xml and docs/readiness/2026-10-23/held_sources_decisions.json: the row\'s '
            'decision_question names the question Brett answered, its sources list this record, and the answer is '
            'applied verbatim (creators B1 to B4, dates C1 and C2, access A1 to A3).',
            'Access rows (22): the four constraint fields are the literal texts quoted in the paragraph, metac equals '
            'accconst and metuc equals useconst, and the record carries no new licence; the modern creator is the '
            'literal legacy credit typed organisational, except 288 (two people with the "of" affiliation), 1864 '
            '(the institute without the role clause), 4027 (two organisations and three people, as the creator426 '
            'note reads), 4063 (two organisations) and 1994 (the Exxon821 projection). Hold any of these five the '
            'record does not settle.',
            'Creator rows (9 admitted, 2817 held): the names, order and entity type are Brett\'s answers; the context '
            'note and paragraph quote the origin text or say it is empty, name the contact as a separate role and '
            'name the evidence the sheet gave.',
            'Date rows (5): the correction manifest binds the exact source value ("2080207" or blank) and the corrected '
            'day; the paragraph gives the source value, the corrected value, the reason and the decision; the '
            'publication date of the v1 wire is the corrected day.',
            'Resource types (37): each type follows the pinned rule from the record\'s own XML; the low-confidence calls '
            '(870, 1318, 4027) are listed in resource_types_r6.json.',
            'Confirm FGDC-2817 stays held (its access text was not decided) and that FGDC-909, 3850, 4185, 21, 4077, '
            '4184, 3373 and 3484 are not members.',
        ],
        'how_to_approve': (
            'Set status to "approved", fill reviewer and reviewed_at, set each decision to "approved" or "held" with a '
            'note, list the approved and held members, keep mapping_manifest_sha256 and proposals_sha256 unchanged, '
            'then pin this file\'s new SHA256 in scripts.modern_singleton.HELD37_REVIEW_SHA. scripts.modern_singleton '
            'admits a source only when this file is approved, pinned, and lists that source as approved; everything '
            'else stays held.'),
    }
    review_path = OUT / 'modern_reviewed_held37_review.json'
    review_path.write_bytes(dumps(review))

    r5 = json.loads(R5.read_bytes())
    assert not set(types) & set(r5['types'])
    r6 = deepcopy(r5)
    r6['types'].update(types)
    r6['notes'].update(type_notes)
    r6['confidence_low'] = sorted(set(r5['confidence_low']) | set(LOW_CONFIDENCE), key=lambda s: int(s[5:]))
    r6['low_confidence'] = len(r6['confidence_low'])
    r6['counts'] = {value: sum(1 for v in r6['types'].values() if v == value) for value in ('dataset', 'publication-report')}
    r6['supersedes'] = {'path': str(R5.relative_to(ROOT)), 'sha256': sha(R5.read_bytes()),
                        'change': ('the 37 held sources Brett cleared on 2026-10-23 added from held37_proposals.json '
                                   '(36 admitted, FGDC-2817 held for its access text); nothing else changes')}
    r6['held37_reviewer'] = PROPOSED_BY + ', from the XML of each record under the pinned rule'
    r6_path = OUT / 'resource_types_r6.json'
    r6_path.write_bytes(dumps(r6))
    print(json.dumps({'members': len(members), 'admitted': len(admitted), 'held': len(held),
                      'modern_creator_objects': manifest['modern_creator_object_count'],
                      'authority_counts': manifest['authority_counts'], 'hold_group_counts': manifest['hold_group_counts'],
                      'proposals_sha256': proposals_sha, 'manifest_sha256': manifest_sha,
                      'review_sha256': sha(review_path.read_bytes()), 'resource_types_r6_sha256': sha(r6_path.read_bytes()),
                      'types': len(r6['types'])}, indent=1))


def _count(items, key):
    counts = {}
    for item in items:
        counts[item[key]] = counts.get(item[key], 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='stage', required=True)
    sub.add_parser('evidence')
    lane_parser = sub.add_parser('lane')
    lane_parser.add_argument('--classified', required=True, help='collection_qa output dir for the 37 sources (lane manifest set)')
    lane_parser.add_argument('--baseline', required=True, help='collection_qa output dir for the 37 sources (runbook manifest set)')
    args = parser.parse_args()
    if args.stage == 'evidence':
        evidence()
    else:
        lane(Path(args.classified), Path(args.baseline))


if __name__ == '__main__':
    main()
