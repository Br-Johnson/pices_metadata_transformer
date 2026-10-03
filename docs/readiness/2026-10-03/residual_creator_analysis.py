"""Audit the pinned PR8 residuals; write evidence only, never an eligibility profile.

Original XML and prepared artifacts are read-only. Exact literal groups identify
the next source review; creator-only diagnostics do not prove future promotion.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


BASE_COMMIT = 'a70e56bd67bd85c0ee38c29aa387d03207461738'
REPORT_SHA256 = '7151a1fcf26db347a0a3e8fed392c82c8059d02c7cf0b7525e13cf3694d8d0a7'
NEXT_GROUPS = {
    'NOAA NMFS AFSC RACE': 'National Oceanic and Atmospheric Administration (NOAA), National Marine Fisheries Service (NMFS), Alaska Fisheries Science Center (AFSC), Resource Assessment and Conservation Engineering (RACE)',
    'Northwest Fisheries Science Center': 'Northwest Fisheries Science Center (NWFSC), National Marine Fisheries Service (NMFS), National Oceanographic and Atmospheric Administration (NOAA)',
    'Auke Bay Laboratory': 'Auke Bay Laboratory (ABL), Alaska Fisheries Science Center (AFSC), National Marine Fisheries Service (NMFS), National Oceanic and Atmospheric Administration (NOAA)',
    'DFO Ocean Sciences and Productivity': 'Fisheries and Oceans Canada, Ocean Sciences & Productivity Division',
    'Scripps': 'Scripps Institution of Oceanography (SIO)',
    'NEAR-GOOS': 'North-East Asian Regional - Global Ocean Observing System (NEAR-GOOS)',
    'National Science Museum': 'National Science Museum, Tokyo, Division of Fishes',
}
LARGER_GROUPS = {
    'Ecotrust joint citation': 'Ecotrust, Pacific GIS, and Conservation International',
    'USDA Alaska DNR joint citation': 'USDA Forest Service, Alaska Department of Natural Resources, Division of Support Services-Land Records Information Section',
    'Unaami collection citation': 'Unaami Arctic Data Collection',
}
CONSTRAINT_PATHS = {
    'dataset_access': './idinfo/accconst', 'dataset_use': './idinfo/useconst',
    'metadata_access': './metainfo/metac', 'metadata_use': './metainfo/metuc',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def audit(classification, prepared, comparison):
    root = Path(__file__).resolve().parents[3]
    report_bytes = classification.read_bytes()
    assert digest(report_bytes) == REPORT_SHA256, 'Unexpected classification checkpoint'
    report = json.loads(report_bytes)
    status_counts = Counter(row['source_status'] for row in report['records'])
    assert status_counts == {'supported': 2121, 'held': 2079, 'failed': 6}
    ids = [row['source_id'] for row in report['records']]
    assert len(ids) == len(set(ids)) == 4206
    assert {p.stem for p in (root / 'FGDC').glob('*.xml')} == set(ids)
    selected = defaultdict(list)
    all_creators = defaultdict(list)
    inventory = []
    copy_count = metadata_count = payload_count = 0
    for row in report['records']:
        sid = row['source_id']
        raw = (root / 'FGDC' / (sid + '.xml')).read_bytes()
        assert digest(raw) == row['source_sha256'], sid
        inventory.append({'source_id': sid, 'source_sha256': row['source_sha256']})
        if row['source_status'] == 'failed':
            continue
        copied = prepared / 'data/original_fgdc' / (sid + '.xml')
        assert copied.read_bytes() == raw, sid
        copy_count += 1
        payload_path = prepared / 'data/zenodo_json' / (sid + '.json')
        payload = None
        if payload_path.exists():
            payload_raw = payload_path.read_bytes()
            assert digest(payload_raw) == row['prepared_payload_sha256'], sid
            payload = json.loads(payload_raw)
            previous = json.loads((comparison / 'data/zenodo_json' / (sid + '.json')).read_bytes())
            assert payload['metadata'] == previous['metadata'], sid
            metadata_count += 1
            payload_count += 1
        if row['source_status'] != 'held':
            continue
        xml = ET.fromstring(raw)
        origins = xml.findall('./idinfo/citation/citeinfo/origin')
        origin_texts = tuple(''.join(node.itertext()) for node in origins)
        if any('Creator semantics' in reason for reason in row['hold_reasons']):
            all_creators[origin_texts].append(row)
        labels = [label for label, name in {**NEXT_GROUPS, **LARGER_GROUPS}.items()
                  if origin_texts == (name,)]
        if not labels:
            continue
        assert len(labels) == 1 and len(origins) == 1
        assert not list(origins[0]) and not origins[0].attrib
        assert not row['exact_copy_aliases'] and payload is not None
        assert row['new_reuse_license'] == 'not_granted_by_rehosting_attestation'
        metadata = payload['metadata']
        assert metadata['access_right'] == 'restricted' and metadata.get('license') == ''
        assert metadata['creators'][0]['name'] == origin_texts[0]
        assert len(metadata['creators']) == 1
        selected[labels[0]].append({
            'source_id': sid, 'source_sha256': row['source_sha256'],
            'prepared_payload_sha256': row['prepared_payload_sha256'],
            'metadata_sha256': digest(canonical(metadata).encode()),
            'current_creators': metadata['creators'],
            'current_hold_reasons': row['hold_reasons'],
            'creator_only_diagnostic': row['hold_reasons'] == ['Creator semantics are ambiguous'],
            'exact_metadata_date': row['raw_metadata_date'],
            'constraints': {key: [''.join(n.itertext()) for n in xml.findall(path)]
                            for key, path in CONSTRAINT_PATHS.items()},
            'preserved_rights': {
                'access_right': metadata['access_right'], 'license': metadata.get('license'),
                'access_conditions': metadata.get('access_conditions'),
                'rehosting_authority': row['rehosting_authority'],
                'new_reuse_license': row['new_reuse_license'],
            },
        })
    assert copy_count == 4200 and metadata_count == payload_count == 4194
    assert {label: len(selected[label]) for label in NEXT_GROUPS} == {
        'NOAA NMFS AFSC RACE': 9, 'Northwest Fisheries Science Center': 4,
        'Auke Bay Laboratory': 3, 'DFO Ocean Sciences and Productivity': 4,
        'Scripps': 3, 'NEAR-GOOS': 2, 'National Science Museum': 2,
    }
    assert {label: len(selected[label]) for label in LARGER_GROUPS} == {
        'Ecotrust joint citation': 37, 'USDA Alaska DNR joint citation': 31,
        'Unaami collection citation': 23,
    }

    def cohort(label, name):
        members = sorted(selected[label], key=lambda item: item['source_id'])
        partition = Counter(canonical(member['constraints']) for member in members)
        return {'label': label, 'raw_origin': name, 'source_xpath': './idinfo/citation/citeinfo/origin',
                'member_count': len(members), 'members_sha256': digest(canonical(members).encode()),
                'creator_only_diagnostic_count': sum(m['creator_only_diagnostic'] for m in members),
                'constraint_partitions': [{'fields': json.loads(key), 'count': count}
                                          for key, count in sorted(partition.items())],
                'members': members}

    next_batch = [cohort(label, name) for label, name in NEXT_GROUPS.items()]
    assert sum(c['member_count'] for c in next_batch) == 27
    assert sum(c['creator_only_diagnostic_count'] for c in next_batch) == 16
    reasons = Counter(tuple(row['hold_reasons']) for row in report['records']
                      if row['source_status'] == 'held')
    return {
        'analysis_only': True, 'eligibility_delta': 0,
        'source_checkpoint': BASE_COMMIT, 'classification_sha256': REPORT_SHA256,
        'current_summary': report['summary'],
        'preservation': {'original_hashes_checked': len(inventory), 'copied_xml_checked': copy_count,
                         'prepared_payload_hashes_checked': payload_count,
                         'complete_metadata_objects_equal_to_previous_checkpoint': metadata_count,
                         'source_inventory_sha256': digest(canonical(sorted(inventory, key=lambda i: i['source_id'])).encode())},
        'hold_reason_partitions': [{'reasons': list(key), 'count': count}
                                   for key, count in sorted(reasons.items(), key=lambda item: (-item[1], item[0]))],
        'largest_creator_diagnostic_clusters': [
            {'raw_origins': list(names), 'count': len(rows),
             'creator_only_diagnostic_count': sum(row['hold_reasons'] == ['Creator semantics are ambiguous'] for row in rows),
             'source_ids': sorted(row['source_id'] for row in rows)}
            for names, rows in sorted(all_creators.items(), key=lambda item: (-len(item[1]), item[0]))[:12]],
        'next_literal_citation_batch': next_batch,
        'larger_role_or_access_review_groups': [cohort(label, name) for label, name in LARGER_GROUPS.items()],
        'provider_requests': 0, 'provider_writes': 0,
        'caveat': 'Creator-only is the current diagnostic, not a validated promotion. No profile is installed; all statuses, full creator objects, dates, constraints and rights remain unchanged.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--classification', type=Path, required=True)
    parser.add_argument('--prepared-dir', type=Path, required=True)
    parser.add_argument('--comparison-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.classification, args.prepared_dir, args.comparison_dir)
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
    print(json.dumps({'output_sha256': digest(args.output.read_bytes()),
                      'preservation': result['preservation'], 'current_summary': result['current_summary'],
                      'next_batch_members': 27, 'creator_only_diagnostics': 16, 'eligibility_delta': 0}, indent=2))


if __name__ == '__main__':
    main()
