"""Reproduce finite access evidence from the frozen merged source-QA report.

Reads original XML and hashes every source. Writes only explicitly named evidence
outputs; it cannot change a source, provider identity, approval or runtime policy.
"""
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[3]
DOCS = Path(__file__).resolve().parent
BASELINE_SHA256 = 'dd6a9775ca3124f796a7280189072a446ddbd3256ead34a02ef24013dab87247'
CONSTRAINTS = ('./metainfo/metac', './metainfo/metuc', './idinfo/accconst', './idinfo/useconst')
CONTEXT = ('./idinfo/citation/citeinfo/title', './idinfo/descript/abstract', './idinfo/descript/purpose')
EXPLICIT_WORDINGS = ('Check with Contributor about how to obtain data.',
                     'Check with Source about how to obtain data.')
PMEL_ACCESS = 'Check with this URLs : http://www.pmel.noaa.gov/pubs/publications.shtml'
PMEL_USE = 'Refer to webstite URL: http://www.pmel.noaa.gov/pubs/publications.shtml'
ADDITIONAL_IDS = ('FGDC-183', 'FGDC-1910', 'FGDC-198', 'FGDC-204', 'FGDC-206', 'FGDC-209',
    'FGDC-2276', 'FGDC-2279', 'FGDC-2299', 'FGDC-231', 'FGDC-234', 'FGDC-235', 'FGDC-236',
    'FGDC-237', 'FGDC-238', 'FGDC-239', 'FGDC-268', 'FGDC-270', 'FGDC-271', 'FGDC-274',
    'FGDC-275', 'FGDC-277', 'FGDC-278', 'FGDC-279', 'FGDC-280', 'FGDC-281', 'FGDC-282',
    'FGDC-283', 'FGDC-285', 'FGDC-56', 'FGDC-768')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def text(root, xpath):
    node = root.find(xpath)
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip() if node is not None else ''


def elements(root, xpath):
    # Exclude only outer sibling tails. The complete source hash binds all bytes.
    result = []
    for node in root.findall(xpath):
        node = copy.deepcopy(node)
        node.tail = None
        result.append(ET.tostring(node, encoding='unicode'))
    return result


def build(baseline):
    raw = baseline.read_bytes()
    if digest(raw) != BASELINE_SHA256:
        raise ValueError('Use the frozen final merged source report, not an earlier draft')
    report = json.loads(raw)
    assert report['summary']['source_status_counts'] == {'supported': 2288, 'held': 1912, 'failed': 6}
    queue = json.loads((DOCS / 'remaining_source_credit_candidates_86.json').read_bytes())
    joint = json.loads((DOCS / 'joint_collection_source_decisions.json').read_bytes())
    protected86 = {m['source_id'] for m in queue['members']}
    protected90 = {m['source_id'] for g in joint['remaining_meaning_decisions'] for m in g['members']}
    assert len(protected86) == 86 and len(protected90) == 90 and not protected86 & protected90
    grouped = defaultdict(list)
    candidates, contexts, originals = [], {}, []
    for row in report['records']:
        source = REPO / 'FGDC' / (row['source_id'] + '.xml')
        source_raw = source.read_bytes()
        assert digest(source_raw) == row['source_sha256'], row['source_id']
        originals.append({'source_id': row['source_id'], 'source_sha256': row['source_sha256']})
        if (row['source_status'] != 'held' or row['exact_copy_aliases']
                or 'Metadata access terms need source-backed adjudication' not in row['hold_reasons']):
            continue
        root = ET.fromstring(source_raw)
        terms = tuple(text(root, p) for p in CONSTRAINTS)
        member = {'source_id': row['source_id'], 'source_sha256': row['source_sha256'],
                  'title': text(root, CONTEXT[0]), 'hold_reasons': row['hold_reasons'],
                  'protected_access_queue': ('86-source-credit' if row['source_id'] in protected86 else
                                             '90-joint-collection' if row['source_id'] in protected90 else None),
                  'constraint_elements': {p: elements(root, p) for p in CONSTRAINTS},
                  'context_elements_sha256': {p: digest(encoded(elements(root, p))) for p in CONTEXT}}
        grouped[terms].append(member)
        meaning = ('underlying_dataset_acquisition' if terms[0] in EXPLICIT_WORDINGS else
                   'underlying_publication_referral' if terms == (PMEL_ACCESS, PMEL_USE, PMEL_ACCESS, PMEL_USE) else
                   'public_metadata_with_underlying_data_permission' if row['source_id'] == 'FGDC-1910' else
                   'underlying_resource_availability' if row['source_id'] in ADDITIONAL_IDS else None)
        if meaning is None or row['source_id'] in protected86 | protected90:
            continue
        assert root.find('./metainfo/metsi') is None and root.find('./metainfo/metextns') is None
        plain = {}
        for xpath in CONSTRAINTS:
            nodes = root.findall(xpath)
            assert len(nodes) == 1 and not list(nodes[0]) and not nodes[0].attrib
            plain[xpath] = nodes[0].text
        candidates.append({k: row[k] for k in ('source_id', 'source_sha256')})
        contexts[row['source_id']] = {'constraints': plain, 'meaning': meaning,
            'context_elements': {p: elements(root, p) for p in CONTEXT},
            'rationale': ('The abstract explicitly distinguishes metadata available for public use from datasets requiring original-owner permission.'
                          if row['source_id'] == 'FGDC-1910' else
                          'Finite source-reviewed data acquisition, resource availability or publication referral; exact constraints/context retained. No underlying data/report is attached, and no current-site terms or reuse license are inferred.')}
    assert len(originals) == 4206 and len(candidates) == 142
    assert Counter(c['meaning'] for c in contexts.values()) == {
        'underlying_dataset_acquisition': 36, 'underlying_publication_referral': 75,
        'public_metadata_with_underlying_data_permission': 1, 'underlying_resource_availability': 30}
    groups = []
    for terms, members in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        members.sort(key=lambda m: m['source_id'])
        bindings = [{k: m[k] for k in ('source_id', 'source_sha256')} for m in members]
        groups.append({'constraint_texts': dict(zip(CONSTRAINTS, terms)), 'member_count': len(members),
                       'membership_sha256': digest(encoded(bindings)),
                       'protected_access_queue_counts': dict(Counter(m['protected_access_queue'] for m in members
                                                                   if m['protected_access_queue'])),
                       'members': members})
    census = {'schema_version': 1, 'scope': 'read-only evidence; no access interpretation or release grant',
              'merged_source_commit': '4b131266cee68798fffed1c309e447a48a420185',
              'baseline_report_sha256': BASELINE_SHA256, 'baseline_summary': report['summary'],
              'all_4206_original_hashes_verified': True, 'original_bindings_sha256': digest(encoded(originals)),
              'nonalias_access_held_members': sum(len(m) for m in grouped.values()),
              'exact_normalized_constraint_groups': len(groups), 'groups': groups,
              'preserved_access_queue86': sorted(protected86), 'preserved_access_queue90': sorted(protected90),
              'source_status_promotions': 0, 'new_licenses': 0, 'provider_requests': 0}
    original = json.loads((REPO / 'docs/readiness/2026-10-02/registration_access_interpretation.json').read_bytes())
    manifest = copy.deepcopy(original)
    manifest.update(profile='finite_source_resource_access_264_2026_10_03',
                    scope='historical_geonetwork_finite_resource_access_scope',
                    meaning='finite_source_resource_access_scope',
                    registration_wording=manifest.pop('wording'),
                    registration_paired_use_wording=manifest.pop('paired_use_wording'),
                    acquisition_contexts=contexts)
    manifest['members'].extend(sorted(candidates, key=lambda m: m['source_id']))
    manifest['evidence'] = {'predecessor_manifest_sha256': digest((REPO / 'docs/readiness/2026-10-02/registration_access_interpretation.json').read_bytes()),
        'baseline_report_sha256': BASELINE_SHA256, 'merged_source_commit': census['merged_source_commit'],
        'previous_122_member_objects_and_source_contexts_unchanged': True,
        'additional_members': 142, 'additional_members_sha256': digest(encoded(sorted(candidates, key=lambda m: m['source_id']))),
        'additional_meaning_counts': dict(Counter(c['meaning'] for c in contexts.values())),
        'preserved_access_queue86': True, 'preserved_access_queue90': True,
        'rationale': 'Finite independently reviewed sources distinguish data/resource acquisition, publication referrals, or explicit public metadata from underlying-data permission. This supplies no license, data permission or release approval. Separate restricted, unlicensed rehosting authority remains mandatory.'}
    return census, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--census-output', type=Path, required=True)
    parser.add_argument('--manifest-output', type=Path, required=True)
    args = parser.parse_args()
    census, manifest = build(args.baseline)
    for output, value in ((args.census_output, census), (args.manifest_output, manifest)):
        output.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
        print(output.name, digest(output.read_bytes()))


if __name__ == '__main__':
    main()
