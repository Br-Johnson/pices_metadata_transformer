"""Reproduce cached all4206 source statuses plus the exact measured42 delta.

No XML transformation, provider/credential read, remote verification or release.
Earlier baseline,22/106 deltas and ledger remain immutable evidence.
"""

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from integrate_source_scope_counts import canonical, digest, integrate, require

DOCS = Path(__file__).resolve().parent
PINS = {
    'resource_scope_integrated_source_status.json': '02c82da229487ccfe77284cf019e0d9b8516eb736e1a2ba79e8ddd7403c381a0',
    'resource_reconciliation_bounded_delta_42.json': 'c15532fbc17243ba1540c854f6e4d2217c0136836775a412f21566a7c409a382',
    'finite_source_resource_access_556.json': '81c719c546146eb7ad39e04db115710747935df6cb142aaf5854127bf8ddcc6a',
    'resource_reconciliation_source_proposals_42.json': '25475fc285f8e4377a051de6b7876436e43f81eaca91ed62dd5693cf82c10198',
    'resource_reconciliation_source_independent_review.json': 'e16e097b3c514898dec823e2fff2b3d2ef9fedf44713e36d1c9720e10f686f75',
}


def integrate42(baseline_raw):
    previous = integrate(baseline_raw)
    inputs = {}
    for name, pin in PINS.items():
        raw = (DOCS / name).read_bytes()
        require(digest(raw) == pin)
        inputs[name] = json.loads(raw)
    require(previous == inputs['resource_scope_integrated_source_status.json'])
    profile = inputs['finite_source_resource_access_556.json']
    members = profile['members'][514:]
    proposal = inputs['resource_reconciliation_source_proposals_42.json']
    require(members == proposal['members'] == profile['resource_reconciliation_review']['members']
            and len(members) == 42)
    selected = {m['source_id']: m['source_sha256'] for m in members}
    require(len(selected) == 42)
    delta = inputs['resource_reconciliation_bounded_delta_42.json']
    require(delta['limit'] == 42 and delta['provider_requests'] == 0
            and delta['selected_before'] == {'supported': 0, 'held': 42, 'failed': 0}
            and delta['selected_after'] == {'supported': 42, 'held': 0, 'failed': 0}
            and delta['baseline_report_sha256'] == previous['baseline_report_sha256']
            and delta['prior_integrated_ledger_sha256'] == PINS['resource_scope_integrated_source_status.json']
            and delta['all_other_source_memberships_unchanged_by_additive_profile'] is True)
    result = copy.deepcopy(previous)
    records = {r['source_id']: r for r in result['records']}
    baseline = {r['source_id']: r for r in json.loads(baseline_raw)['records']}
    seen = set()
    for row in delta['rows']:
        sid = row['source_id']
        require(sid in selected and sid not in seen and records[sid]['source_status'] == 'held'
                and records[sid]['source_sha256'] == selected[sid] == row['source_sha256']
                and baseline[sid]['prepared_payload_sha256'] == row['baseline_payload_sha256']
                and row['before_status'] == 'held' and row['after_status'] == 'supported'
                and row['complete_raw_metadata_unchanged'] is True
                and row['original_and_copied_XML_unchanged'] is True
                and not baseline[sid]['exact_copy_aliases'])
        seen.add(sid)
        records[sid].update(source_status='supported', evidence='measured_delta42')
    require(seen == set(selected))
    require(all(records[r['source_id']] == r for r in previous['records'] if r['source_id'] not in seen))
    require(not seen.intersection(previous['held31_exception_ids'])
            and all(records[sid]['source_status'] == 'held' for sid in previous['held31_exception_ids']))
    aliases = {sid for sid, row in baseline.items() if row['exact_copy_aliases']}
    require(len(aliases) == 456 and all(records[sid]['source_status'] == 'held' for sid in aliases))
    counts = Counter(r['source_status'] for r in result['records'])
    require(counts == {'supported': 3638, 'held': 562, 'failed': 6})
    result.update(
        scope='Frozen all4206 baseline and measured disjoint22/106/42 deltas; no fresh full-corpus or remote audit',
        input_sha256={**previous['input_sha256'], **PINS},
        integrated_counts={'supported': 3638, 'held': 562, 'malformed': 6},
        promoted_source_count=170, new42_provenance_counts={'REVIEWER_RECONCILED': 42},
        per_source_status_sha256=digest(canonical(result['records'])),
        fgdc4060_still_held=False, fgdc4060_source_supported=True,
        all_unselected_prior_status_objects_unchanged=True,
        measured42_source_ids=sorted(selected),
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = integrate42(args.baseline.read_bytes())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print({key: value for key, value in result.items() if key not in ('records', 'input_sha256', 'held31_exception_ids', 'measured42_source_ids')})


if __name__ == '__main__':
    main()
