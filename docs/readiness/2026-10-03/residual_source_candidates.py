"""Freeze reviewed next-source evidence without installing an interpretation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
REPORT_SHA256 = 'f6b68ea0bbc328bd44f6bba06a9b504c8b438c232fc10dcc868d628e2867ec91'
TYPED = [126, 130, 1390, 1756, 1795, 1797, 2287, 2549, 2572, 2615, 2616, 3539, 361, 3872, 3881]
UNTYPED = [129, 1765, 1789, 1791, 1827, 1946, 2294, 2296, 2604, 2633, 350, 3776, 3777, 3781,
           3782, 3784, 3873, 3970, 4017, 4065, 439, 444, 543, 600]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def audit(prepared, comparison):
    raw_report = (prepared / 'classification.json').read_bytes()
    assert digest(raw_report) == REPORT_SHA256
    report = json.loads(raw_report)
    manifest = json.loads((ROOT / 'docs/readiness/2026-10-03/joint_collection_citation_190.json').read_bytes())
    reviewed = {m['source_id'] for c in manifest['cohorts'] for m in c['members']}
    selected = [row for row in report['records'] if row['source_status'] == 'held'
                and not row['exact_copy_aliases'] and row['source_id'] not in reviewed
                and not any(any(word in reason.casefold() for word in ('access', 'relation', 'title'))
                            for reason in row['hold_reasons'])]
    rows = {row['source_id']: row for row in selected}
    membership = sorted([{'source_id': row['source_id'], 'source_sha256': row['source_sha256']}
                         for row in selected], key=lambda item: item['source_id'])
    assert len(membership) == 164
    assert fingerprint(membership) == '2f0a004c51a96e1a1186a74198b54bf52af4f1fc0a24b21c8fb26d417630fd52'
    evidence, copies, payloads = {}, 0, 0
    for row in selected:
        sid = row['source_id']
        source = ROOT / 'FGDC' / (sid + '.xml')
        raw = source.read_bytes()
        assert digest(raw) == row['source_sha256']
        assert (prepared / 'data/original_fgdc' / source.name).read_bytes() == raw
        copies += 1
        root = ET.fromstring(raw)
        origins = root.findall('./idinfo/citation/citeinfo/origin')
        constraints = {label: [''.join(n.itertext()) for n in root.findall(path)] for label, path in {
            'dataset_access': './idinfo/accconst', 'dataset_use': './idinfo/useconst',
            'metadata_access': './metainfo/metac', 'metadata_use': './metainfo/metuc'}.items()}
        item = {'source_id': sid, 'source_sha256': row['source_sha256'],
                'current_hold_reasons': row['hold_reasons'],
                'raw_primary_origins': [''.join(n.itertext()) for n in origins],
                'plain_origins': [not list(n) and not n.attrib for n in origins],
                'raw_metadata_date': root.findtext('./metainfo/metd'),
                'raw_metadata_review_date': root.findtext('./metainfo/metrd'),
                'constraints': constraints}
        path = prepared / 'data/zenodo_json' / (sid + '.json')
        if path.exists():
            raw_payload = path.read_bytes()
            assert digest(raw_payload) == row['prepared_payload_sha256']
            payload = json.loads(raw_payload)
            before = json.loads((comparison / 'data/zenodo_json' / path.name).read_bytes())
            assert payload['metadata'] == before['metadata']
            assert payload['metadata']['access_right'] == 'restricted' and payload['metadata']['license'] == ''
            assert not payload['metadata']['related_identifiers']
            assert [c['name'] for c in payload['metadata']['creators']] == [
                re.sub(r'\s+', ' ', ''.join(n.itertext())).strip() for n in origins]
            item.update(prepared_payload_sha256=digest(raw_payload),
                        prepared_metadata_sha256=fingerprint(payload['metadata']),
                        existing_full_creators=payload['metadata']['creators'],
                        publication_date=payload['metadata']['publication_date'])
            payloads += 1
        else:
            assert 'prepared_payload_sha256' not in row
        evidence[sid] = item
    assert copies == 164 and payloads == 158

    def cohort(label, numbers, expected_sha, recommendation):
        ids = sorted('FGDC-' + str(n) for n in numbers)
        members = [{'source_id': sid, 'source_sha256': rows[sid]['source_sha256']} for sid in ids]
        assert fingerprint(members) == expected_sha
        return {'label': label, 'members': members, 'membership_sha256': expected_sha,
                'recommendation': recommendation, 'source_evidence': [evidence[sid] for sid in ids],
                'diagnostic_only': True, 'eligibility_delta': 0}

    typed = cohort('plain_institution_full_Organization_objects_15', TYPED,
        'b68bf3a16b7df992e81edf11e0a9dd09c84f743ee8a068dd4914c91db55c4c48',
        'First candidate batch: preserve entire existing Organization objects and exact source spellings/whitespace. Pin exact raw plain origins and normalized full creator objects; no generic parser, modernization, XML authorship or access grant.')
    untyped = cohort('literal_untyped_institution_program_objects_24', UNTYPED,
        '6d64251642fcb74f993352fb830843f62042759998a9aa7d7f1c620b9dfdca0d',
        'Second candidate batch: preserve entire untyped literal institution/program objects; no legal-institution type or modern identity inference. Keep five same-origin access-held siblings outside membership.')
    for group in (typed, untyped):
        assert all(e['plain_origins'] == [True] for e in group['source_evidence'])
        assert all(re.fullmatch(r'\d{8}|\d{4}-\d{2}-\d{2}', e['raw_metadata_date']) for e in group['source_evidence'])
    all_rows = {row['source_id']: row for row in report['records']}
    raw_origin_members = {}
    for group in (typed, untyped):
        names = {e['raw_primary_origins'][0] for e in group['source_evidence']}
        matched = []
        for source in sorted((ROOT / 'FGDC').glob('*.xml')):
            try:
                nodes = ET.fromstring(source.read_bytes()).findall('./idinfo/citation/citeinfo/origin')
            except ET.ParseError:
                continue
            if len(nodes) == 1 and ''.join(nodes[0].itertext()) in names:
                matched.append(source.stem)
        selected_ids = {m['source_id'] for m in group['members']}
        raw_origin_members[group['label']] = sorted(set(matched) - selected_ids)
    assert raw_origin_members[typed['label']] == []
    assert raw_origin_members[untyped['label']] == ['FGDC-121', 'FGDC-1767', 'FGDC-336', 'FGDC-533', 'FGDC-535']
    for sid in raw_origin_members[untyped['label']]:
        assert all_rows[sid]['source_status'] == 'held'
        assert any('access' in reason.casefold() for reason in all_rows[sid]['hold_reasons'])
    smaller = [
        cohort('USFWS_Alaska_DNR_two_credit_review_2', [601, 618],
               '8fa981cd515babd4b4921555439e87aefa22144292567b3ac8802fefc974cc3b',
               'Dedicated full two-credit after-image review before splitting the combined institutional creator.'),
        cohort('literal_single_person_credit_review_4', [1424, 1532, 1754, 794],
               'c6ae8205b1b6406dad59d2b77088603b9e3a3a771c0cfaaee08824c05435939b',
               'Review literal untyped single-person primary credits; no contacts, affiliations or normalized inferred identities.'),
        cohort('explicit_person_list_afterimage_review_5', [1, 1220, 1904, 2587, 450],
               '7b745c9c130f222b542fce26b34c2f6009bd366d4799f14b22415403a1bc78e0',
               'Dedicated source-order full after-image review for each explicit list; no generic comma split.')]
    mixed = sorted(sid for sid, e in evidence.items() if e['raw_metadata_date'] == '20050225'
                   and not all(e['plain_origins']))
    mixed_group = cohort('BASIS_mixed_XML_role_order_review_35', [source.split('-')[1] for source in mixed],
        'f462ec511358b5a87b00a9c3a19312ad99f8de5e03608f8c98b67e5291de626a',
        'Dedicated role/order review; existing combined Organization objects do not establish that named people are organizations. Preserve primary Nancy Navis versus abstract N. Davis pending authoritative evidence.')
    empty = cohort('empty_primary_origins_21', [3683, 3919, 3920, *range(3951, 3955), *range(3956, 3960),
        3961, *range(3965, 3970), *range(3975, 3979)],
        '5c09ef73462a850866552792b3b69561a637090cc4e8fc80e60fcbd9e8dc3f3f',
        'Require authoritative per-record primary attribution. Exact metadata date and registration/hosting context cannot establish creators; do not fill from contacts.')
    dates = cohort('unsupported_metadata_dates_6', [1422, 1423, 3850, 4139, 4161, 4181],
        '693d255df75ccc8993508fec7d33f0dbf3433121ebd4856a1e9b44b26d2ccc46',
        'Require a verified metadata creation or last-update day. Three blank metd fields and three literal 2080207 fields also have no metadata review-date field (metrd); review is not a creation/update substitute. Do not substitute publication dates or invent 20080207.')
    return {'analysis_only': True, 'eligibility_delta': 0, 'source_checkpoint':
            '0188b1f93c459d2427c10d9f1964966289f8576c', 'classification_sha256': REPORT_SHA256,
            'source_summary_unchanged': report['summary'], 'non_alias_screen_members': membership,
            'non_alias_screen_sha256': fingerprint(membership),
            'screen_preservation': {'original_hashes': 164, 'copied_XML': 164, 'prepared_payloads': 158,
                                    'complete_metadata_equal_to_fresh_baseline': 158},
            'recommended_literal_batches': [typed, untyped], 'same_raw_origin_outside_selected_scope': raw_origin_members,
            'smaller_afterimage_reviews': smaller, 'mixed_role_order_review': mixed_group,
            'irreducible_missing_source_evidence': [empty, dates],
            'scope': 'Read-only ranked source evidence. Current diagnostics do not prove promotion; no interpretation/profile/correction, source date, access meaning, alias identity, license or release authority is installed.',
            'provider_requests': 0, 'provider_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--comparison', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.prepared, args.comparison), indent=2, ensure_ascii=False))
