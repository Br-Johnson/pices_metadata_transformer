"""Reproduce cached all4206 source accounting plus the measured two-report delta.

No source transformation, provider operation, credential read or release claim.
The previous ledger and every unselected status object remain intact.
"""

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

from integrate_resource42_counts import integrate42
from integrate_source_scope_counts import canonical, digest, require

DOCS = Path(__file__).resolve().parent
PINS = {
    'resource_reconciliation_integrated_source_status.json': 'e9f248c1730aa59f4d89f9ddf66aedf05dd172c73dab190709ea3e8c6683b061',
    'finite_source_resource_access_556.json': '81c719c546146eb7ad39e04db115710747935df6cb142aaf5854127bf8ddcc6a',
    'finite_source_resource_access_558.json': 'a9dee2d1191eab69d85a20e3a3c856b9e56eec7283e024a50db91974cdd316a0',
    'npafc_report2_source_proposals.json': 'd68b56f27e2fa908a88d142d9690f3ef9f0ee40e3997476d478c457dbbc44459',
    'npafc_report2_source_review.json': '0dc1a02fd6d2e0f41edf8c32f8eff82680467e7854d64b1c52fadaa53937079b',
    'npafc_report2_bounded_delta.json': '4df4cc18ddf8b501d5621481ae3577a5ba6acdbc0f26cbc7d82ab88d07cd85a5',
}


def integrate2(baseline_raw):
    previous = integrate42(baseline_raw)
    inputs = {}
    for name, pin in PINS.items():
        raw = (DOCS / name).read_bytes()
        require(digest(raw) == pin)
        inputs[name] = json.loads(raw)
    require(previous == inputs['resource_reconciliation_integrated_source_status.json'])
    old = inputs['finite_source_resource_access_556.json']
    profile = inputs['finite_source_resource_access_558.json']
    review = profile['npafc_report_notification_review']
    members = profile['members'][556:]
    require(profile['members'][:556] == old['members'] and len(profile['members']) == 558
            and profile['source_contexts'] == old['source_contexts']
            and profile['resource_reconciliation_review'] == old['resource_reconciliation_review']
            and all(profile['acquisition_contexts'][sid] == value
                    for sid, value in old['acquisition_contexts'].items()))
    require(members == inputs['npafc_report2_source_proposals.json']['members'] == review['members']
            and review['source_proposal_sha256'] == PINS['npafc_report2_source_proposals.json']
            and review['source_independent_review_sha256'] == PINS['npafc_report2_source_review.json'])
    selected = {m['source_id']: m['source_sha256'] for m in members}
    require(set(selected) == {'FGDC-885', 'FGDC-887'})
    delta = inputs['npafc_report2_bounded_delta.json']
    require(delta['limit'] == 2 and delta['provider_requests'] == 0
            and delta['selected_before'] == {'supported': 0, 'held': 2, 'failed': 0}
            and delta['selected_after'] == {'supported': 2, 'held': 0, 'failed': 0}
            and delta['baseline_report_sha256'] == previous['baseline_report_sha256']
            and delta['prior_integrated_ledger_sha256'] == PINS['resource_reconciliation_integrated_source_status.json'])
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
                and row['only_added_policy_key'] == 'dataset_access_interpretation'
                and row['provenance'] == 'REVIEWER_RECONCILED'
                and not baseline[sid]['exact_copy_aliases'])
        seen.add(sid)
        records[sid].update(source_status='supported', evidence='measured_npafc_report2')
    require(seen == set(selected))
    require(all(records[r['source_id']] == r for r in previous['records'] if r['source_id'] not in seen))
    require(not seen.intersection(previous['held31_exception_ids'])
            and all(records[sid]['source_status'] == 'held' for sid in previous['held31_exception_ids']))
    aliases = {sid for sid, row in baseline.items() if row['exact_copy_aliases']}
    require(len(aliases) == 456 and all(records[sid]['source_status'] == 'held' for sid in aliases))
    require(Counter(r['source_status'] for r in result['records']) == {'supported': 3640, 'held': 560, 'failed': 6})
    result.update(
        scope='Frozen all4206 baseline and measured disjoint22/106/42/2 deltas; no fresh full-corpus or remote audit',
        input_sha256={**previous['input_sha256'], **PINS},
        integrated_counts={'supported': 3640, 'held': 560, 'malformed': 6},
        promoted_source_count=172, npafc_report2_provenance_counts={'REVIEWER_RECONCILED': 2},
        per_source_status_sha256=digest(canonical(result['records'])),
        all_unselected_prior_status_objects_unchanged=True,
        measured_npafc_report2_source_ids=sorted(selected),
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = integrate2(args.baseline.read_bytes())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print({key: result[key] for key in ('integrated_counts', 'promoted_source_count', 'per_source_status_sha256')})


if __name__ == '__main__':
    main()
