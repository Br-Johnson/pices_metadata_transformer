"""Build the creators64 proposal, mapping manifest, pending review and resource-type proposal.

Purpose: the 64 single-record FGDC sources with no reviewed creator policy (remaining100
minus citations31 minus the five protected records) are decided one by one here. Every
decision is written out with its evidence so an independent reviewer can check it; the
mapping manifest holds the admitted sources only, and the review manifest starts as
"proposal pending independent review", so `scripts.modern_singleton` holds every member
until a reviewer replaces that file with an approved one.

Invariants: original XML is read, never written. Legacy creator arrays come from the pinned
creator426 profile (creator426 kind) or the pinned institution91 bindings (direct kind) and
are checked against a fresh offline classification. Modern vectors keep every literal
source part; nothing is corrected, expanded or inferred from a name alone.

Run from the repository root:
  python -B docs/readiness/2026-10-22/build_creators64_manifests.py --classified <qa-output-dir>
where <qa-output-dir> is a `scripts.collection_qa` run over the 64 XML files with the
runbook manifest set and `--reviewed-at 2026-10-20T00:00:00+00:00`.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.citation_creator_interpretation import source_element  # noqa: E402
from scripts.modern_singleton import (  # noqa: E402
    CITATIONS31,
    CITATIONS31_DIRECT_BINDINGS,
    CITATIONS31_DIRECT_BINDINGS_SHA,
    PLAN,
    PLAN_SHA,
    PROFILE,
    PROFILE_SHA,
    encode,
    pinned,
    sha,
)
from scripts.production_mutations import PROTECTED  # noqa: E402

OUT = ROOT / 'docs/readiness/2026-10-22'
POLICY = 'modern-xml-reviewed-creators64-v1'
RECONCILIATION = ROOT / 'docs/readiness/2026-10-06/modern_program20_remaining100_reconciliation.json'
NEXT = ROOT / 'docs/readiness/2026-10-06/next_source_review'
PROPOSED_BY = 'Claude Fable 5.1 (deep-coder subagent of session a49e1cd3), 2026-10-22'
INSTRUCTION = 'Brett Johnson, 2026-10-22: "take on the 64 unreviewed singletons"'

# ------------------------------------------------------------------ conventions

CONVENTIONS = {
    'scope': 'Only the exact 64 sources: remaining100 of the program20 reconciliation minus the 31 '
             'citations31 members minus the five protected records. Every one is a supported singleton '
             'in the frozen publication plan; none is in the remaining45 (39 held, 6 failed).',
    'literal_parts': 'Creator names keep every literal source part in source order. No spelling is '
                     'corrected, no initial is expanded, no person is added from a contact, abstract or '
                     'external work, and no entity type is inferred from a name alone.',
    'entity_category': 'A credit is admitted as organisational only when the record itself shows the '
                       'named body acting (a laboratory, office, university, commission, agency named as '
                       'the credited party). A credit that names a data collection, data product, '
                       'satellite platform, forecast system or observation network is held: Zenodo '
                       'creators are personal or organisational and the source does not supply that '
                       'category.',
    'name_parts': 'A person is split into family and given names only when the record settles the '
                  'boundary: an inverted form in the citation or embedded reference, an initials-plus-'
                  'family pattern, a matching inverted contact name, or an honorific that fixes natural '
                  'order (Mr./Dr. Given Family).',
    'suffix': 'Generational suffixes (Jr., III) stay with the given names in the inverted citation form '
              'the sources themselves use ("Farley, E.V., Jr."): family_name "Farley", given_name '
              '"Edward V., Jr.". The provider displays family_name, given_name, so the record reads '
              '"Farley, Edward V., Jr." and the DataCite familyName stays the family name. This is a '
              'representation convention for the independent reviewer to confirm, not a claim that the '
              'suffix is a given name; InvenioRDM has no suffix field.',
    'honorific_rank_role': 'Honorifics (Dr., Mr.), military ranks (CWO3) and stated roles (editor) are '
                           'not name parts. They are left out of the name fields and preserved verbatim '
                           'in the preservation paragraph, as the citations31 policy did for FGDC-2597 '
                           '("Dr. Hatakeyama, former Director-General ..." -> Hatakeyama).',
    'particle': 'A nobility particle stays where the source\'s own inverted form puts it '
                '("Boguslawski, G. Von" -> family_name "Boguslawski", given_name "G. Von").',
    'affiliations': 'Direct-kind sources follow the citations31 direct10 convention: an affiliation '
                    'object is added only for an explicit, unambiguous attachment in the citation '
                    '("... of INSTITUTION" shared by the connected list, or a parenthetical after one '
                    'name). creator426-kind sources follow their reviewed cohort notes, which add no '
                    'affiliation objects; institutions stay in the preserved citation.',
    'literal_conflict': 'A personal name whose literal spelling conflicts with the record\'s own '
                        'embedded reference, the referenced work\'s byline or the record\'s own contact '
                        'name is held (Navis/Davis, Uran/Urano, Bugae/Bugaev, Kandzela/Kondzela, '
                        'Herman/Hermann). The project does not correct source text, and publishing a '
                        'known-conflicting personal name needs an owner decision.',
    'preservation_paragraph': 'Every admitted source carries one paragraph, rendered into the v1 '
                              'preservation block as the citations31 policy does, that quotes the '
                              'complete literal credit and states what was left out of the name fields.',
}

SUFFIX_NOTE = ('The generational suffix is kept with the given names in the inverted citation form the '
               'source itself uses; it is not part of the family name.')


def person(family, given, affiliation=None):
    creator = {'person_or_org': {'type': 'personal', 'family_name': family, 'given_name': given}}
    if affiliation:
        creator['affiliations'] = [{'name': affiliation}]
    return creator


def org(name):
    return {'person_or_org': {'type': 'organizational', 'name': name}}


NRL = 'Naval Research Laboratory, Stennis Space Center, MS'
BASIS678 = [person('Farley', 'Edward V., Jr.'), person('Wing', 'Bruce'), person('Middleton', 'Angela'), person('Pohl', 'John'),
            person('Hulbert', 'Lee'), person('Moss', 'Jamal'), person('Trudel', 'Marc'), person('Parks', 'Edward'),
            person('Hamilton', 'Ted'), person('Lagoudakis', 'Cynthia'), person('McCallum', 'Danielle'),
            org('North Pacific Anadromous Fish Commission')]
BASIS816 = [person('Farley', 'Edward V., Jr.'), person('Murphy', 'James M.'), person('Middleton', 'Angela'),
            person('Eisner', 'Lisa'), person('Moss', 'Jamal'), person('Pohl', 'John'), person('Ivanov', 'Oleg'),
            person('Kuznetsova', 'Natalia'), person('Trudel', 'Marc'), person('Drew', 'Mary'),
            person('Lagoudakis', 'Cynthia'), person('Yaska', 'George'), org('North Pacific Anadromous Fish Commission')]

BASIS_REVIEW = 'docs/readiness/2026-10-06/next_source_review/pices-basis19-independent-complete-array-review.json'
BASIS_EVIDENCE = 'docs/readiness/2026-10-06/next_source_review/pices-basis19-primary-evidence.json'
BASIS_PROPOSAL = 'docs/readiness/2026-10-06/next_source_review/pices-basis19-modern-personal-source-proposals.json'
DIRECT_REVIEW = 'docs/readiness/2026-10-06/next_source_review/pices-direct14-independent-source-review.json'
DIRECT_PROPOSAL = 'docs/readiness/2026-10-06/next_source_review/pices-direct14-modern-source-proposals.json'
CONTRACT_REVIEW = 'docs/readiness/2026-10-06/next_source_review/pices-contract-chain9-independent-source-review.json'
OFFICE_ADDENDUM = 'docs/readiness/2026-10-06/next_source_review/pices-role-qualified-411-2709-office-capacity-addendum.json'
PROGRAM_REVIEW = 'docs/readiness/2026-10-06/modern_program20_independent_review.json'
RECON = 'docs/readiness/2026-10-06/modern_program20_remaining100_reconciliation.json'
CIT31 = 'docs/readiness/2026-10-06/modern_reviewed_citations31.json'
CREATOR426 = 'docs/readiness/2026-10-04/source_citation_credits_426.json'

BASIS_PARTS_QUOTE = ('Resolved: literal Edward V. / Farley / Jr. and other complete source credits; '
                     'no missing person or new permission question')
BASIS_HOLD_QUOTE = 'Current proposed family_name Farley, Jr. lacks a supported suffix-placement convention'
HATAKEYAMA_QUOTE = ('The primary source credits Dr. Hatakeyama, former Director-General of the Japan Meteorological '
                    'Agency, in connection with the 1964 Climate of Asia volume. The given name Hisanao is an '
                    'explicitly reviewed external identity enrichment')

UNAAMI = ['FGDC-' + str(n) for n in (545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 556, 557, 558,
                                      559, 560, 573, 574, 575, 576, 578, 579, 580, 581)]
NAVIS = ['FGDC-' + str(n) for n in (3680, 3681, 3800, 3802, 3803, 3804, 3805, 3806, 3807, 3808)]

UNAAMI_REASON = (
    'The citation origin credits a data collection, not a person or an organisation. The record\'s own '
    'purpose text calls the Unaami Data Collection "an interdisciplinary, diverse collection of Arctic '
    'variables", and its constraints ask users to "acknowledge the Unaami Data Collection and the original '
    'source of the data". Zenodo creators are personal or organisational; no source evidence establishes a '
    'same-named organisational collective, and the contact (Overland, James E., unaami-team@noaa.gov) is a '
    'separate role that may not be promoted. The program20 independent review and the remaining100 '
    'reconciliation held all 23 for this reason. Release needs an owner decision on how a data-collection '
    'credit is represented, or a source-owner record naming the responsible organisation.')
NAVIS_REASON = (
    'The literal "Nancy Navis" conflicts with the record\'s own embedded reference ("Tanaka, H, N. Davis, '
    'T. Onuma, M. Yamada, Y. Yamamoto, and S. Tsuchiya") and with the referenced NPAFC Doc. 622 byline '
    '("Nancy Davis"); the basis19 independent review held all ten arrays for this literal conflict. The '
    'project does not correct source spellings, and publishing a known-conflicting personal name needs an '
    'owner decision. The other five people and the trailing NPAFC credit are not approved separately.')

# ------------------------------------------------------------------ decisions
# Each admitted entry: group, modern creators, paragraph, resource type, extra evidence quotes.
# Each held entry: group, reason, extra evidence quotes. XML evidence is added automatically.

ADMIT = {
    'FGDC-3814': {
        'group': 'basis_doc678_farley', 'modern_creators': BASIS678, 'resource_type': 'publication-report',
        'type_note': 'NPAFC Doc. 678 cruise report; purpose "To report research cruise ..."; the sibling '
                     'cruise report FGDC-3809 is typed publication-report',
        'paragraph': (
            'The primary citation lists Edward V. Farley, Jr., Bruce Wing, Angela Middleton, John Pohl and '
            'Lee Hulbert of NOAA, NMFS, Alaska Fisheries Science Center, Auke Bay Laboratory; Jamal Moss of '
            'the School of Aquatic and Fisheries Sciences, University of Washington; Marc Trudel of Pacific '
            'Biological Station, Nanaimo; Edward Parks and Ted Hamilton of Yukon River Drainage Fisheries '
            'Association; Cynthia Lagoudakis of the U.S. Forest Service; Danielle McCallum of NWO, Inc.; and '
            'the North Pacific Anadromous Fish Commission as the trailing credit. The literal names and order '
            'are retained; the institutions named after "of" stay in this preserved citation and are not added '
            'as affiliations. ' + SUFFIX_NOTE + ' The commission is credited as the source lists it, the body '
            'the report was submitted to; no report or XML authorship is asserted for it. The embedded '
            'reference (Farley, E.V., Jr., B. Wing, A. Middleton, J. Pohl, L. Hulbert, J. Moss, M. Trudel, E. '
            'Parks, T. Hamilton, C. Lagoudakis, and D. McCallum. 2003. NPAFC Doc. 678) confirms the family names.'),
        'evidence': [
            (BASIS_REVIEW, BASIS_PARTS_QUOTE), (BASIS_REVIEW, BASIS_HOLD_QUOTE),
            (BASIS_EVIDENCE, 'Farley, E.V., Jr., B. Wing, A. Middleton, J. Pohl'),
            (BASIS_EVIDENCE, 'Danielle McCallum')]},
    'FGDC-3816': {'group': 'basis_doc678_farley', 'modern_creators': BASIS678, 'resource_type': 'dataset',
                  'type_note': 'the entry describes midwater rope trawl fish data collected during the 2002 BASIS survey',
                  'paragraph': None, 'evidence': [(BASIS_REVIEW, BASIS_PARTS_QUOTE), (BASIS_REVIEW, BASIS_HOLD_QUOTE),
                                                  (BASIS_EVIDENCE, 'Farley, E.V., Jr., B. Wing, A. Middleton, J. Pohl')]},
    'FGDC-3817': {'group': 'basis_doc678_farley', 'modern_creators': BASIS678, 'resource_type': 'dataset',
                  'type_note': 'the entry describes oceanographic (CTD and plankton) data collected during the 2002 BASIS survey',
                  'paragraph': None, 'evidence': [(BASIS_REVIEW, BASIS_PARTS_QUOTE), (BASIS_REVIEW, BASIS_HOLD_QUOTE),
                                                  (BASIS_EVIDENCE, 'Farley, E.V., Jr., B. Wing, A. Middleton, J. Pohl')]},
    'FGDC-3838': {
        'group': 'basis_doc816_farley', 'modern_creators': BASIS816, 'resource_type': 'publication-report',
        'type_note': 'NPAFC Doc. 816 cruise report; purpose "To report on the Ocean Carrying Capacity (OCC) program fall 2003 survey"',
        'paragraph': (
            'The primary citation lists Edward V. Farley, Jr., James M. Murphy, Angela Middleton, Lisa Eisner, '
            'Jamal Moss and John Pohl of NOAA, NMFS, Alaska Fisheries Science Center, Auke Bay Laboratory; Oleg '
            'Ivanov and Natalia Kuznetsova of Pacific Fisheries Research Center (TINRO-Center), Vladivostok; '
            'Marc Trudel of Pacific Biological Station, Nanaimo; Mary Drew of Pacific States Marine Fisheries '
            'Commission; Cynthia Lagoudakis of the U.S. Forest Service; George Yaska of Yukon River Drainage '
            'Fisheries Association; and the North Pacific Anadromous Fish Commission as the trailing credit. '
            'The literal names, the initial M. and the order are retained; the institutions named after "of" '
            'stay in this preserved citation and are not added as affiliations. ' + SUFFIX_NOTE + ' The '
            'commission is credited as the source lists it, the body the report was submitted to; no report or '
            'XML authorship is asserted for it. The embedded reference (Farley, E.V., Jr., J. Murphy, A. '
            'Middleton, L. Eisner, J. Moss, J. Pohl, O. Ivanov, N. Kuznetsova, M. Trudel, M. Drew, C. '
            'Lagoudakis, and G. Yaska. 2004. NPAFC Doc. 816) confirms the family names.'),
        'evidence': [(BASIS_REVIEW, 'Resolved: Edward V. / Farley / Jr., and literal James M. Murphy plus the remaining source credits; preserve all initials and order'),
                     (BASIS_REVIEW, 'Same unsupported Farley suffix-placement choice as Doc678 arrays'),
                     (BASIS_EVIDENCE, 'Farley, E.V., Jr., J. Murphy, A. Middleton, L. Eisner'),
                     (BASIS_EVIDENCE, 'James M. Murphy'), (BASIS_EVIDENCE, 'George Yaska')]},
    'FGDC-885': {
        'group': 'bristol_bay_doc499',
        'modern_creators': [person('Farley', 'Edward V., Jr.'), person('Haight', 'Richard E.'), person('Guthrie', 'Charles M. III'),
                            person('Pohl', 'John E.')],
        'resource_type': 'publication-report',
        'type_note': 'the entry describes the NPAFC Doc. 499 report of the August 2000 survey ("Report submitted to the '
                     'North Pacific Anadromous Fish Commission"), as the sibling cruise reports FGDC-3809 and FGDC-3814',
        'paragraph': (
            'The primary citation lists Edward V. Farley, Jr., Richard E. Haight, Charles M. Guthrie III and John E. '
            'Pohl, followed on a separate line by Auke Bay Laboratory (ABL), Alaska Fisheries Science Center (AFSC), '
            'National Marine Fisheries Service (NMFS), National Oceanic and Atmospheric Administration (NOAA). The '
            'literal names, initials and order are retained. The generational suffixes Jr. and III are kept with '
            'the given names in inverted citation form and are not part of the family names. The institutional '
            'line stays in this preserved citation and is not added as an affiliation. The embedded reference '
            '(Farley, E.V., Jr., R.E. Haight, C.M. Guthrie, and J.E. Pohl. 2000. NPAFC Doc. 499) confirms the '
            'family names.'),
        'evidence': [(RECON, 'Four explicitly named primary citation credits are retained in source order, including the literal Jr. and III suffixes')]},
    'FGDC-887': {
        'group': 'bristol_bay_1999',
        'modern_creators': [person('Farley', 'E.V., Jr.'), person('Murphy', 'J.M.'), person('Haight', 'R.E.'), person('Guthrie', 'G.M.'),
                            person('Baier', 'C.T.'), person('Adkison', 'M.D.'), person('Radchenko', 'V.I.'), person('Satterfield', 'F.R.')],
        'resource_type': 'publication-report',
        'type_note': 'the entry describes the 1999 NPAFC report of the July and September 1999 surveys (embedded reference "... 1999. Eastern Bering Sea (Bristol Bay) Coastal ...")',
        'paragraph': (
            'The primary citation lists Farley, E.V., Jr., J.M. Murphy, R.E. Haight, G.M. Guthrie, C.T. Baier, '
            'M.D. Adkison, V.I. Radchenko and F.R. Satterfield, followed by Auke Bay Laboratory, Alaska Fisheries '
            'Science Center, NMFS, NOAA. The exact initials and order are retained as given, including G.M. '
            'Guthrie; nothing is expanded or replaced from another record. The first name is already in inverted '
            'form in the source; its suffix Jr. stays with the initials and is not part of the family name. The '
            'institutional line stays in this preserved citation and is not added as an affiliation. The embedded '
            'reference repeats the same eight names in the same order.'),
        'evidence': [(RECON, 'Eight explicitly named primary citation credits retain their exact source initials, order, family-first Farley form and Jr. suffix, including G.M. Guthrie')]},
    'FGDC-2413': {
        'group': 'editor_wespestad', 'modern_creators': [person('Wespestad', 'Vidar')], 'resource_type': 'dataset',
        'type_note': 'the entry describes Soviet trawl survey and exploratory fishing data (CPUE, length-weight, species composition)',
        'paragraph': (
            'The primary citation credits Dr. Vidar Wespestad, editor, followed by Alaska Fisheries Science Center '
            '(AFSC), National Marine Fisheries Service (NMFS), National Oceanic and Atmospheric Administration '
            '(NOAA). The credit is limited to the stated editor role; the honorific Dr. and the role are not name '
            'parts and are preserved here rather than in the name fields. The point of contact, Wespestad, Vidar, '
            'confirms the family and given names. No survey or XML authorship is inferred and the institutional '
            'line is not added as an affiliation.'),
        'evidence': [(RECON, 'The primary citation identifies Dr. Vidar Wespestad specifically as editor'),
                     (CIT31, HATAKEYAMA_QUOTE)]},
    'FGDC-542': {
        'group': 'donut_hole_database',
        'modern_creators': [person('Jo', 'Hynn-Su'), person('Janusz', 'Jerzy'), person('Low', 'Loh-Lee'), org('Shanghai Fisheries University')],
        'resource_type': 'dataset',
        'type_note': 'the entry describes a historical catch database by statistical block (1984-1991)',
        'paragraph': (
            'The primary citation credits Korean data to Mr. Hynn-Su Jo of National Fisheries Research and '
            'Development Agency, Pujan, Republic of Korea; Polish data to Dr. Jerzy Janusz of Sea Fisheries '
            'Institute, Gdynia, Poland; and Chinese data to Loh-Lee Low and Shanghai Fisheries University. These '
            'are scoped data-by credits, retained in source order and spelling; the honorifics Mr. and Dr. are not '
            'name parts and are preserved here, and the institutions named after "of" stay in this preserved '
            'citation rather than as affiliations. The point of contact, Low, Loh-Lee, confirms that family name; '
            'the honorific-first natural order fixes the other two. Shanghai Fisheries University is credited as '
            'the organisation the source names.'),
        'evidence': [(CREATOR426, 'Honorifics, Hynn-Su, Pujan and the original institutional qualifications remain literal in the preserved source; no personal affiliation objects are added'),
                     (CIT31, HATAKEYAMA_QUOTE)]},
    'FGDC-2587': {
        'group': 'boguslawski_1878', 'modern_creators': [person('Boguslawski', 'G. Von')], 'resource_type': 'publication-report',
        'type_note': 'NOAA Central Library foreign data collection holding; the entry describes a printed lecture ("Publication Title: ..."), typed as the other library holdings',
        'paragraph': (
            'The primary citation origin, Rud. Virchow and Fr. v. Holtzenforff, is the collection-level editorial '
            'credit of the lecture series and is preserved as context; the source abstract names the author of '
            'this lecture explicitly as Boguslawski, G. Von. That inverted form supplies the name parts used here, '
            'family name Boguslawski and given name G. Von, with the particle kept where the source places it. No '
            'spelling is corrected and no editor role is inferred for the series editors.'),
        'evidence': [(CREATOR426, 'The creator name collapses the two internal spaces and omits the sentence-ending period only')]},
    'FGDC-2674': {
        'group': 'audubon_graham', 'modern_creators': [person('Graham', 'Frank, Jr.')], 'resource_type': 'publication-report',
        'type_note': 'the entry describes a magazine article (Audubon, July-August 1991)',
        'paragraph': (
            'The primary citation credits Frank Graham, Jr. of the Audubon Magazine; the embedded reference (F. '
            'Graham Jr., "U.S. and Soviet Environmentalists Join Forces Across the Bering Strait," Audubon, '
            'July-August 1991) confirms the family name. ' + SUFFIX_NOTE + ' The magazine is the publication '
            'venue and is not added as an affiliation or creator.'),
        'evidence': [(RECON, 'Frank Graham, Jr. has a suffix and no inspected explicit inverted source boundary')]},
    'FGDC-2683': {
        'group': 'national_geographic_munoz', 'modern_creators': [person('Munoz', 'Juan')], 'resource_type': 'publication-report',
        'type_note': 'the entry describes a magazine article (National Geographic Magazine 105(1), 1954)',
        'paragraph': (
            'The primary citation origin, The National Geographic Magazine, is the publication venue and is '
            'preserved as context; the source abstract cites the article as Juan Munoz. 1954. Cliff Dwellers of '
            'the Bering Sea ..., National Geographic Magazine 105(1):129-146, which supplies the personal credit '
            'used here in natural name order. The venue is not substituted as an author.'),
        'evidence': [(CREATOR426, 'Juan Munoz is credited in the source abstract reference for the same primary-cited 1954 Cliff Dwellers of the Bering Sea article')]},
    'FGDC-2234': {
        'group': 'uscg_anderson', 'modern_creators': [person('Anderson', 'James Mike')], 'resource_type': 'dataset',
        'type_note': 'the entry describes a database of Coast Guard boardings',
        'paragraph': (
            'The primary citation credits CWO3 James Mike Anderson. The military rank CWO3 is not a name part and '
            'is preserved here rather than in the name fields; the given names James Mike and the family name '
            'Anderson are retained as written. The point of contact, Busch, Gregory C., is a separate role and is '
            'not promoted.'),
        'evidence': [(RECON, 'CWO3 James Mike Anderson includes a military rank and potentially ambiguous given-name components')]},
    'FGDC-2668': {
        'group': 'usgs_bering_shelf_1987',
        'modern_creators': [person('Nelson', 'C. Hans'), person('Johnson', 'Kirk R.', 'Denver Museum of Natural History'),
                            person('Barber', 'John H., Jr.'), person('Phillips', 'Robert L.')],
        'resource_type': 'publication-report',
        'type_note': 'the entry describes a journal article (Journal of Sedimentary Petrology 57(3), 1987)',
        'paragraph': (
            'The primary citation credits C. Hans Nelson, Kirk R. Johnson (Denver Museum of Natural History), John '
            'H. Barber, Jr., and Robert L. Phillips: U.S. Geological Survey. All four named people are retained in '
            'source order; the embedded reference to the 1987 Journal of Sedimentary Petrology article lists only '
            'Nelson, Johnson and Barber, and that difference is preserved, not resolved. Johnson\'s parenthetical '
            'museum is the only explicit personal affiliation and the only one mapped; the trailing U.S. '
            'Geological Survey phrase has no unambiguous scope and stays in this preserved citation. ' + SUFFIX_NOTE),
        'evidence': [(DIRECT_REVIEW, 'Hold the whole array. Four primary-origin people versus three in the same-title article citation'),
                     (DIRECT_PROPOSAL, 'No Phillips deletion, lost Jr.suffix, indiscriminate USGS affiliation, library creator, or new article DOI.')]},
    'FGDC-3599': {
        'group': 'onr_japan_east_sea',
        'modern_creators': [org('U.S. Navy, Office of Naval Research'), person('Hurlburt', 'Harley', NRL),
                            person('Hogan', 'Pat', NRL), person('Jacobs', 'Gregg', NRL)],
        'resource_type': 'dataset',
        'type_note': 'ONR Japan/East Sea research-project description with no document described; the sibling '
                     'project descriptions FGDC-3593 and FGDC-3596 are typed dataset',
        'paragraph': (
            'The primary citation credits U.S. Navy, Office of Naval Research and Harley Hurlburt, Pat Hogan, and '
            'Gregg Jacobs of Naval Research Laboratory, Stennis Space Center, MS. The Office of Naval Research is '
            'retained as the first credited party; the source abstract describes its role as having supported the '
            'Japan/East Sea research during 1998-2000, so its listing is the source\'s own credit, not a claim of '
            'authorship. The three named people share the Naval Research Laboratory affiliation the source attaches '
            'to them with "of"; the sentence-ending period after MS is not part of the name, and Pat is not '
            'expanded. The point of contact, Jacobs, Gregg, confirms that family name. Collaborators named in the '
            'abstract (Rainer Bleck, Dong-Kyu Lee) are not added.'),
        'evidence': [(DIRECT_REVIEW, 'Neither dropping ONR nor converting support into an unqualified author is approved.'),
                     (CONTRACT_REVIEW, 'The approved representation lists the two already source-credited organizational party groups separately, in source order, while retaining the entire original contract clause'),
                     (CIT31, 'Mark Halverson, Rich Pawlowicz, and Randall Lee with University of British Columbia, Department of Earth and Ocean Sciences. The literal names and shared source affiliation are retained')]},
}

HOLD = {
    **{sid: {'group': 'unaami_literal_collection23', 'reason': UNAAMI_REASON,
             'evidence': [(PROGRAM_REVIEW, 'The exact29 holds are resource/system/platform credits or unresolved identity/role meanings'),
                          (RECON, 'Named data collection is established, but a same-named human organizational collective is not.')]}
       for sid in UNAAMI},
    'FGDC-419': {'group': 'program_identity', 'reason': (
        'The literal "Word Wright" could be a person\'s name, a trade name or a publisher; the record (a book, '
        'Alaska Geographic vol. 26 no. 3) gives no context that settles the entity category, and the contact, '
        'Richard P. Emanuel, may not be promoted. Held by the program20 independent review for the same gap.'),
        'evidence': [(RECON, 'The source primary name Word Wright and book description do not distinguish a publisher/trade brand from a personal credit')]},
    'FGDC-715': {'group': 'program_identity', 'reason': (
        '"CIA World Bank II" credits a data product (the abstract describes "the CIA World Data Bank II", a '
        'declassified compilation of coastline files), not a person or an organisation, and the literal is a '
        'variant of the product name. Not a creator category the provider carries without an owner decision.'),
        'evidence': [(RECON, 'Primary CIA World Bank II is a literal databank/collection credit.')]},
    'FGDC-859': {'group': 'program_identity', 'reason': (
        'The credit names a satellite platform ("The French Earth Observation Satellite, SPOT" in the abstract), '
        'not an agent; typing it organisational would substitute the operator, SPOT Image, which the source names '
        'separately.'),
        'evidence': [(RECON, 'Exact legacy name credits a platform; an organizational type would replace platform meaning with its operator')]},
    'FGDC-2296': {'group': 'program_identity', 'reason': (
        'The expansion "Campaign for Development and Solidarity" names a Norwegian development NGO, while the '
        'record (a Tromso satellite surveillance database, contact Hans A. Tommervik) points to the Tromso research '
        'foundation of the same acronym; the program20 review recorded this identity conflict. Publishing the '
        'literal as an organisational creator would attribute the database to a possibly wrong real organisation.'),
        'evidence': [(RECON, 'The complete FORUT expansion points to one NGO while scientific data, Tromso address and official historical research foundation suggest a different FORUT.')]},
    'FGDC-3873': {'group': 'program_identity', 'reason': (
        'The credit names a nowcast-forecast system (models and an observing network, as the abstract describes), '
        'not an organisation; the host or developer cannot be inferred from the contact.'),
        'evidence': [(RECON, 'Source credits a named nowcast-forecast system and describes models, instrumentation and monitoring sites.')]},
    'FGDC-3970': {'group': 'program_identity', 'reason': (
        'The credit names an observation network; the abstract attributes observation to "the associated agencies '
        'of the Ports and Harbous Bureau of MLIT" and analysis to the Port and Airport Research Institute, so the '
        'network name is the data resource, not the acting organisation.'),
        'evidence': [(RECON, 'does not yet establish the exact credited name as a human organizational collective rather than the instrument/network resource')]},
    **{sid: {'group': 'basis_doc622_navis', 'reason': NAVIS_REASON,
             'evidence': [(BASIS_REVIEW, 'Do not correct Navis to Davis or infer an identity link.'),
                          (BASIS_EVIDENCE, 'Tanaka, H, N. Davis')]} for sid in NAVIS},
    'FGDC-3825': {'group': 'basis_doc717_uran', 'reason': (
        'The literal "Akihisa Uran" conflicts with the record\'s own embedded reference ("A. Urano") and the NPAFC '
        'Doc. 717 byline ("Akihisa Urano"); the embedded reference also orders the authors differently. Held by the '
        'basis19 independent review; no correction or reordering is approved.'),
        'evidence': [(BASIS_REVIEW, 'Do not substitute Urano, use different report byline order, or approve other people separately.'),
                     (BASIS_EVIDENCE, 'Akihisa Urano')]},
    'FGDC-3831': {'group': 'basis_doc763_bugae', 'reason': (
        'The literal "Alexander V. Bugae" conflicts with the record\'s own embedded reference ("Bugaev A.V.") and the '
        'NPAFC Doc. 763 byline ("Alexander V. Bugaev"). Held by the basis19 independent review; the spelling is not '
        'corrected and no identity is asserted.'),
        'evidence': [(BASIS_REVIEW, 'Do not correct the source surname or replace it with the related report credit.'),
                     (BASIS_EVIDENCE, 'Alexander V. Bugaev')]},
    'FGDC-893': {'group': 'literal_conflict_contact', 'reason': (
        'The literal "Christine Kandzela" conflicts with the record\'s own point of contact, "Kondzela, Christine", '
        'and "Richard Wilmot." carries a stray period. The same literal-conflict rule that holds Navis, Uran and '
        'Bugae applies; the spelling is not corrected.'),
        'evidence': [(RECON, 'The saved complete array has no approved finite personal name-part/type after-image')]},
    'FGDC-3851': {'group': 'literal_conflict_contact', 'reason': (
        'The literal "Al Herman" conflicts with the record\'s own point of contact, "Hermann, Albert J.", in both the '
        'given-name form and the surname spelling; neither is corrected or inferred.'),
        'evidence': [(RECON, 'Al Herman differs in both name/abbreviation and surname spelling from Albert J. Hermann in the contact.')]},
    'FGDC-287': {'group': 'direct_compound', 'reason': (
        'The compound credit mixes two institutions, an explicit support credit (SEBSCC) and two people without a '
        'separator; which parties are creators and which are affiliations or support is not settled by the record. '
        'Held by the direct14 independent review.'),
        'evidence': [(DIRECT_REVIEW, 'The compound primary origin mixes two institutions, explicit SEBSCC support and two people without an unambiguous boundary.')]},
    'FGDC-411': {'group': 'direct_unnamed_person', 'reason': (
        'The credit is an unnamed person ("Professor Emeritus of the University of Alaska Fairbanks ..."); no '
        'personal creator can be formed without a name, the office reading is unsupported, and the contact, Hood, '
        'Donald W., may not be promoted. Held by the role-office11 review and its addendum.'),
        'evidence': [(OFFICE_ADDENDUM, 'Professor Emeritus remains an individual academic status qualified by institutional affiliation.')]},
    'FGDC-771': {'group': 'direct_contract_chain', 'reason': (
        'A two-stage contract chain whose terminal "Chugach National Forest, U.S. Bureau of land Management" '
        'grouping is unresolved (one party, two parties, or an affiliation). Held by the contract-chain9 '
        'independent review.'),
        'evidence': [(CONTRACT_REVIEW, 'the terminal comma and U.S. Bureau of land Management do not establish the final attachment/grouping')]},
    'FGDC-2229': {'group': 'direct_document_venue', 'reason': (
        '"MS Thesis, University of Washington (UW)" is a work and venue label, not a creator; the thesis author is '
        'not in the citation and the contact, McDermott, Susanne F., may not be promoted.'),
        'evidence': [(RECON, 'MS Thesis or Technical Report is a work/degree/series label, not a creator')]},
    'FGDC-2235': {'group': 'direct_et_al', 'reason': (
        '"Cliff Mass et al." explicitly names unnamed co-originators; a one-person vector would truncate the credit '
        'and the department cannot stand for the people. Held by the direct14 independent review.'),
        'evidence': [(DIRECT_REVIEW, 'Explicit et al. leaves additional originators unresolved.')]},
    'FGDC-2824': {'group': 'direct_document_venue', 'reason': (
        '"Technical Report, International Pacific Halibut Commission [TECH. REP. IPHC]" joins a series label to the '
        'commission; the report\'s authors are not in the citation and the contact, Hoag, S.H., may not be promoted.'),
        'evidence': [(RECON, 'MS Thesis or Technical Report is a work/degree/series label, not a creator')]},
    'FGDC-3786': {'group': 'direct_jodc_programs', 'reason': (
        'JODC is an organisation, but CSK and KER are credited only in the origin; nothing in the record describes '
        'them as acting bodies, so typing them organisational would infer the category from their names, which the '
        'conventions forbid, and dropping them would truncate the literal credit.'),
        'evidence': [(RECON, 'JODC plus CSK/KER labels have unresolved distinct production/research roles')]},
}

# ------------------------------------------------------------------ helpers


def norm(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def recursive_text(node):
    return norm(''.join(node.itertext()))


def quote(path, needle):
    raw = (ROOT / path).read_text(encoding='utf-8')
    if needle not in raw:
        raise SystemExit(f'quote not found in {path}: {needle[:80]}')
    return {'path': path, 'sha256': sha((ROOT / path).read_bytes()), 'quote': needle}


def xml_evidence(root, xpath, label):
    nodes = root.findall(xpath)
    return [{'xpath': xpath, 'label': label, 'text': recursive_text(node)} for node in nodes]


def embedded_references(root):
    abstract = root.find('./idinfo/descript/abstract')
    if abstract is None:
        return []
    found = []
    for paragraph in [abstract, *abstract.iter()]:
        text = recursive_text(paragraph) if paragraph is abstract and len(abstract) == 0 else norm(paragraph.text)
        if 'Reference' in text or re.search(r'\b(Author|Munoz)\b', text):
            found.append(text)
    return list(dict.fromkeys(found))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--classified', required=True,
                        help='collection_qa output dir for the 64 sources (runbook manifest set, reviewed-at 2026-10-20T00:00:00+00:00)')
    args = parser.parse_args()
    classified = Path(args.classified)
    classification = json.loads((classified / 'classification.json').read_text())
    class_rows = {row['source_id']: row for row in classification['records']}

    reconciliation = pinned(RECONCILIATION, sha(RECONCILIATION.read_bytes()))
    remaining100 = {row['source_id'] for row in reconciliation['remaining100_after_set_subtraction']}
    citations31 = {row['source_id'] for row in pinned(CITATIONS31, sha(CITATIONS31.read_bytes()))['members']}
    members = sorted(remaining100 - citations31 - set(PROTECTED), key=lambda s: int(s[5:]))
    assert len(members) == 64 and set(ADMIT) | set(HOLD) == set(members) and not set(ADMIT) & set(HOLD)
    recon_rows = {row['source_id']: row for row in reconciliation['rows']}
    lanes = {m['source_id']: p['lane'] for p in reconciliation['partitions'] for m in p['members']}

    profiles = pinned(PROFILE, PROFILE_SHA)['cohorts']
    profile_by_member = {m['source_id']: row for row in profiles for m in row['members']}
    bindings = {row['source_id']: row for row in pinned(CITATIONS31_DIRECT_BINDINGS, CITATIONS31_DIRECT_BINDINGS_SHA)['members']}
    targets = {row['record_target_id']: row for row in pinned(PLAN, PLAN_SHA)['targets']}

    proposals, rows, types, type_notes = [], [], {}, {}
    for index, sid in enumerate(members):
        raw = (ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        digest = sha(raw)
        root = ET.fromstring(raw)
        origins = root.findall('./idinfo/citation/citeinfo/origin')
        target = targets[sid]
        assert target['source_ids'] == [sid] and target['source_semantic_status'] == 'supported'
        assert target['source_sha256'] == digest and target['identity_decision']['production_record_id'] is None
        assert target['identity_decision']['production_doi'] is None and sid not in PROTECTED
        fresh = json.loads((classified / 'data/zenodo_json' / (sid + '.json')).read_text())
        legacy = fresh['metadata']['creators']
        reference = fresh['artifact_policy'].get('creator_interpretation')
        if sid in profile_by_member:
            profile = profile_by_member[sid]
            kind, cohort, authority = 'creator426', profile['profile'], profile
            assert profile['creators'] == legacy and reference and reference['manifest_sha256'] == PROFILE_SHA
            assert {'source_id': sid, 'source_sha256': digest} in profile['members']
        else:
            binding = bindings[sid]
            kind, cohort, authority = 'direct', None, binding
            assert binding['complete_creator_objects'] == legacy and reference is None
            assert binding['source_sha256'] == digest
        recon = recon_rows[sid]
        assert recon['source_sha256'] == digest
        decision = 'admit' if sid in ADMIT else 'hold'
        spec = ADMIT.get(sid) or HOLD[sid]
        paragraph = spec.get('paragraph')
        if decision == 'admit' and paragraph is None:
            paragraph = ADMIT['FGDC-3814']['paragraph']  # the three Doc. 678 members share one credit
        evidence = [{'kind': 'xml', **item} for item in
                    xml_evidence(root, './idinfo/citation/citeinfo/origin', 'citation origin')
                    + xml_evidence(root, './idinfo/citation/citeinfo/title', 'citation title')
                    + xml_evidence(root, './idinfo/ptcontac/cntinfo/cntperp/cntper', 'point of contact person')]
        evidence += [{'kind': 'xml', 'xpath': './idinfo/descript/abstract', 'label': 'embedded reference or author line',
                      'text': text} for text in embedded_references(root)]
        evidence += [{'kind': 'file', **quote(path, needle)} for path, needle in spec['evidence']]
        evidence.append({'kind': 'file', **quote(RECON, recon['independent_decision'])})
        proposal = {
            'source_id': sid, 'source_sha256': digest, 'source_path': 'FGDC/' + sid + '.xml',
            'source_bytes': len(raw), 'lane': lanes[sid], 'group': spec['group'], 'decision': decision,
            'reason': spec.get('reason') or 'Admitted: the literal credit, its name parts and the entity categories are settled by the record and the cited evidence; see the preservation paragraph.',
            'citation_origin_texts': [recursive_text(node) for node in origins],
            'primary_origin_elements': [source_element(node) for node in origins],
            'source_root_sha256': sha(encode(source_element(root))),
            'legacy_creators': legacy,
            'legacy_creator_authority': {'kind': kind, 'creator_cohort': cohort,
                                         'object_sha256': sha(encode(authority))},
            'prior_decision': recon['independent_decision'],
            'proposed_creators': spec.get('modern_creators'),
            'additional_preservation_paragraph': paragraph if decision == 'admit' else None,
            'proposed_resource_type': spec.get('resource_type'),
            'resource_type_note': spec.get('type_note'),
            'fresh_classification': {'reviewed_at': classification['reviewed_at'],
                                     'source_status': class_rows[sid]['source_status'],
                                     'prepared_input_sha256': class_rows[sid]['prepared_payload_sha256']},
            'evidence': evidence,
        }
        proposals.append(proposal)
        if decision == 'admit':
            rows.append({
                'source_id': sid, 'source_sha256': digest, 'source_path': 'FGDC/' + sid + '.xml',
                'source_bytes': len(raw), 'source_root_sha256': proposal['source_root_sha256'],
                'source_plan_target_sha256': sha(encode(target)), 'group': spec['group'],
                'creator_authority_kind': kind, 'creator_cohort': cohort,
                'creator_authority_object_sha256': sha(encode(authority)),
                'creators': legacy, 'modern_creators': spec['modern_creators'],
                'primary_origins': proposal['primary_origin_elements'],
                'additional_preservation_paragraphs': [paragraph],
                'proposal_row_pointer': '/proposals/' + str(index),
                'proposal_row_sha256': sha(encode(proposal))})
            types[sid] = spec['resource_type']
            type_notes[sid] = spec['type_note']

    admitted = [{'source_id': r['source_id'], 'source_sha256': r['source_sha256']} for r in rows]
    held = [{'source_id': p['source_id'], 'source_sha256': p['source_sha256']} for p in proposals if p['decision'] == 'hold']
    inputs = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in
              (RECONCILIATION, CITATIONS31, PROFILE, CITATIONS31_DIRECT_BINDINGS, PLAN)}
    proposals_document = {
        'schema_version': 1, 'kind': 'creators64-source-proposals-v1',
        'status': 'PROPOSAL_PENDING_INDEPENDENT_REVIEW_NOT_EXECUTION_AUTHORITY',
        'proposed_by': PROPOSED_BY, 'instruction': INSTRUCTION,
        'policy': POLICY, 'conventions': CONVENTIONS, 'inputs': inputs,
        'fresh_classification': {'command': 'python -B -m scripts.collection_qa with the runbook manifest set '
                                            '(docs/readiness/2026-10-06/first_pices_record_runbook.md) and '
                                            '--reviewed-at 2026-10-20T00:00:00+00:00 over the 64 XML files',
                                 'profile_sha256': classification['profile_sha256'],
                                 'summary': classification['summary']['source_status_counts']},
        'counts': {'members': len(members), 'admit': len(admitted), 'hold': len(held),
                   'admit_by_group': dict(sorted(_count(rows, 'group').items())),
                   'hold_by_group': dict(sorted(_count([p for p in proposals if p['decision'] == 'hold'], 'group').items())),
                   'modern_creator_objects': sum(len(r['modern_creators']) for r in rows)},
        'members': [{'source_id': sid, 'source_sha256': targets[sid]['source_sha256']} for sid in members],
        'admitted_members': admitted, 'held_members': held,
        'proposals': proposals,
    }
    proposals_path = OUT / 'creators64_proposals.json'
    proposals_path.write_bytes(dumps(proposals_document))
    proposals_sha = sha(proposals_path.read_bytes())

    manifest = {
        'schema_version': 1, 'kind': 'modern-reviewed-creators64-v1', 'policy': POLICY,
        'source_plan_sha256': PLAN_SHA, 'creator426_profile_sha256': PROFILE_SHA,
        'direct_binding_sha256': CITATIONS31_DIRECT_BINDINGS_SHA,
        'proposals_path': 'docs/readiness/2026-10-22/creators64_proposals.json',
        'proposals_sha256': proposals_sha,
        'member_count': len(rows), 'members': admitted, 'membership_sha256': sha(encode(admitted)),
        'authority_counts': dict(sorted(_count(rows, 'creator_authority_kind').items())),
        'modern_creator_object_count': sum(len(r['modern_creators']) for r in rows),
        'context_sha256': sha(encode({r['source_id']: r['additional_preservation_paragraphs'] for r in rows})),
        'conventions': {key: CONVENTIONS[key] for key in ('suffix', 'honorific_rank_role', 'particle', 'affiliations')},
        'rows': rows,
    }
    manifest_path = OUT / 'modern_reviewed_creators64.json'
    manifest_path.write_bytes(dumps(manifest))
    manifest_sha = sha(manifest_path.read_bytes())

    review = {
        'schema_version': 1, 'kind': 'modern-reviewed-creators64-review-v1', 'policy': POLICY,
        'status': 'proposal pending independent review',
        'mapping_manifest_path': 'docs/readiness/2026-10-22/modern_reviewed_creators64.json',
        'mapping_manifest_sha256': manifest_sha,
        'proposals_path': 'docs/readiness/2026-10-22/creators64_proposals.json', 'proposals_sha256': proposals_sha,
        'proposed_by': PROPOSED_BY, 'reviewer': None, 'reviewed_at': None,
        'members': admitted, 'membership_sha256': sha(encode(admitted)),
        'approved_members': [], 'held_members': [],
        'decisions': {r['source_id']: {'decision': 'pending', 'note': None} for r in rows},
        'reviewer_checklist': [
            'Read every admitted row against FGDC/<id>.xml: the literal origin, the embedded reference, the contact names.',
            'Confirm the family/given split of every person from the evidence quoted in creators64_proposals.json, not from the name alone.',
            'Confirm or reject the suffix convention (given_name carries "Jr."/"III" in inverted citation form) for FGDC-885, 887, 2668, 2674, 3814, 3816, 3817 and 3838; a rejection holds those sources.',
            'Confirm that dropping Dr./Mr./CWO3 and the editor role from the name fields (FGDC-542, 2234, 2413) and keeping them in the paragraph follows the FGDC-2597 precedent.',
            'Confirm the organisational typing of Shanghai Fisheries University (FGDC-542) and U.S. Navy, Office of Naval Research (FGDC-3599), and the affiliation objects on FGDC-2668 and FGDC-3599.',
            'Confirm every held reason; a hold the reviewer lifts needs a new proposal row and manifest, not an edit of this file alone.',
        ],
        'how_to_approve': (
            'Set status to "approved", fill reviewer and reviewed_at, set each decision to "approved" or "held" '
            'with a note, list the approved and held members, keep mapping_manifest_sha256 and proposals_sha256 '
            'unchanged, then pin this file\'s new SHA256 in scripts.modern_singleton.CREATORS64_REVIEW_SHA. '
            'scripts.modern_singleton admits a source only when this file is approved, pinned, and lists that '
            'source as approved; everything else stays held.'),
    }
    review_path = OUT / 'modern_reviewed_creators64_review.json'
    review_path.write_bytes(dumps(review))

    rule = pinned(ROOT / 'docs/readiness/2026-10-22/resource_types.json',
                  sha((ROOT / 'docs/readiness/2026-10-22/resource_types.json').read_bytes()))['rule']
    type_document = {
        'kind': 'pices-resource-types-creators64-proposal-v1',
        'status': 'proposal pending independent review; not pinned',
        'proposed_by': PROPOSED_BY, 'rule': rule, 'policy': POLICY,
        'mapping_manifest_sha256': manifest_sha,
        'counts': {value: sum(1 for v in types.values() if v == value) for value in ('dataset', 'publication-report')},
        'types': dict(sorted(types.items(), key=lambda kv: int(kv[0][5:]))),
        'notes': dict(sorted(type_notes.items(), key=lambda kv: int(kv[0][5:]))),
        'how_to_adopt': 'After the creator review is approved, add these entries to the pinned resource-type '
                        'manifest in a new file and re-pin scripts.modern_bulk.RESOURCE_TYPES_SHA, as the '
                        '2026-10-22 manifest superseded the 2026-10-20 one.',
    }
    (OUT / 'resource_types_creators64_proposal.json').write_bytes(dumps(type_document))
    print(json.dumps({'members': len(members), 'admitted': len(admitted), 'held': len(held),
                      'proposals_sha256': proposals_sha, 'manifest_sha256': manifest_sha,
                      'review_sha256': sha(review_path.read_bytes())}, indent=1))


def _count(items, key):
    counts = {}
    for item in items:
        counts[item[key]] = counts.get(item[key], 0) + 1
    return counts


def dumps(value):
    return (json.dumps(value, indent=1, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')


if __name__ == '__main__':
    main()
