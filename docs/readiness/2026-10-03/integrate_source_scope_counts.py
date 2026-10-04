"""Integrate exact measured source deltas into frozen corpus status accounting.

Reads only cached public classification/evidence, never XML, tokens or provider
state. This is a reproducible status ledger, not a new transformation/corpus audit
or release decision. Unrelated baseline statuses remain exact.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

DOCS = Path(__file__).resolve().parent
BASELINE_SHA = '0ec37de02ea67af81d3b433a65e523c6c05f30220c667324e2fc3b6a367c8708'
PINS = {
    'cnf_copy_media_bounded_delta.json': 'f7c74308d39bed987971a9702e5095b5ecb1ec0944754c9a86e250f4dde50d1a',
    'resource_scope_bounded_delta_106.json': 'dd559b5767dd3e8193b3a668176a58d8a018bb27ec13388bd8ff6c7976ef026d',
    'finite_source_resource_access_514.json': '203c050735a9dc755712acde70c0447b91f2bd6131dde53dd8195a0f2923d9a2',
    'source_scope_reconciliation_904.json': '242024bcf750e0fd3ea0097ee34eb47fb86f0674fb554fe2e0b78ddce4a589c1',
    'pices-remaining31-exception-decisions.json': '2edf6b9f599329ebff9f5449ff5e9c363baa3a049521edb3f88a55066416e387',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('Frozen source-status accounting invariant failed')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def integrate(baseline_raw):
    require(digest(baseline_raw) == BASELINE_SHA)
    baseline = json.loads(baseline_raw)
    original = {row['source_id']: row for row in baseline['records']}
    require(len(original) == len(baseline['records']) == 4206)
    require(Counter(row['source_status'] for row in original.values()) ==
            {'supported': 3468, 'held': 732, 'failed': 6})
    inputs = {}
    for name, pin in PINS.items():
        raw = (DOCS / name).read_bytes()
        require(digest(raw) == pin)
        inputs[name] = json.loads(raw)
    resource = inputs['finite_source_resource_access_514.json']['members'][491:]
    scope = inputs['source_scope_reconciliation_904.json']['members'][821:]
    selected = {row['source_id']: row['source_sha256'] for row in resource + scope}
    require(len(resource) == 23 and len(scope) == 83 and len(selected) == 106)
    status = {sid: row['source_status'] for sid, row in original.items()}
    promoted = set()
    for name, count in (('cnf_copy_media_bounded_delta.json', 22),
                        ('resource_scope_bounded_delta_106.json', 106)):
        delta = inputs[name]
        require(delta['baseline_report_sha256'] == BASELINE_SHA and delta['limit'] == count
                and delta['provider_requests'] == 0
                and delta['selected_before'] == {'supported': 0, 'held': count, 'failed': 0}
                and delta['selected_after'] == {'supported': count, 'held': 0, 'failed': 0}
                and delta['all_other_source_memberships_unchanged_by_additive_profile'] is True
                and len(delta['rows']) == count)
        seen = set()
        for row in delta['rows']:
            sid = row['source_id']
            require(sid in original and sid not in seen and sid not in promoted
                    and status[sid] == row['before_status'] == 'held'
                    and row['after_status'] == 'supported'
                    and row['source_sha256'] == original[sid]['source_sha256']
                    and row['baseline_payload_sha256'] == original[sid]['prepared_payload_sha256']
                    and row['complete_raw_metadata_unchanged'] is True
                    and row['original_and_copied_XML_unchanged'] is True
                    and not original[sid]['exact_copy_aliases'])
            seen.add(sid)
            status[sid] = 'supported'
        if count == 106:
            require(seen == set(selected)
                    and all(selected[sid] == original[sid]['source_sha256'] for sid in seen)
                    and delta['prior22_delta_sha256'] == PINS['cnf_copy_media_bounded_delta.json'])
        promoted.update(seen)
    require(len(promoted) == 128)
    exceptions = inputs['pices-remaining31-exception-decisions.json']
    require(exceptions['member_count'] == len(exceptions['rows']) == 31)
    held31 = {row['source_id'] for row in exceptions['rows']}
    require(len(held31) == 31 and not held31.intersection(promoted)
            and all(status[sid] == 'held' for sid in held31)
            and status['FGDC-4060'] == 'held')
    require(all(status[sid] == row['source_status'] for sid, row in original.items() if sid not in promoted))
    aliases = {sid for sid, row in original.items() if row['exact_copy_aliases']}
    require(len(aliases) == 456 and all(status[sid] == 'held' for sid in aliases))
    counts = Counter(status.values())
    require(counts == {'supported': 3596, 'held': 604, 'failed': 6})
    records = [{'source_id': sid, 'source_sha256': original[sid]['source_sha256'],
                'source_status': status[sid], 'evidence': 'measured_delta' if sid in promoted else 'frozen_baseline'}
               for sid in sorted(status)]
    return {
        'schema_version': 1,
        'kind': 'integrated_source_status_accounting',
        'scope': 'Complete frozen baseline plus exact independently reviewed measured22/106 deltas; no fresh corpus audit',
        'baseline_report_sha256': BASELINE_SHA,
        'input_sha256': PINS,
        'integrated_counts': {'supported': counts['supported'], 'held': counts['held'], 'malformed': counts['failed']},
        'source_count': len(records), 'promoted_source_count': len(promoted),
        'new106_provenance_counts': {'SOURCE_BACKED': len(resource), 'REVIEWER_RECONCILED': len(scope)},
        'per_source_status_sha256': digest(canonical(records)),
        'held31_exception_ids': sorted(held31),
        'held31_exception_membership_sha256': exceptions['membership_sha256'],
        'fgdc4060_still_held': True, 'all456_alias_identities_still_held': True,
        'all_unselected_baseline_statuses_unchanged': True,
        'original_xml_reads': 0, 'provider_requests': 0,
        'remote_verification_or_publication_approval_added': False,
        'records': records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = integrate(args.baseline.read_bytes())
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print({key: value for key, value in result.items() if key != 'records'})


if __name__ == '__main__':
    main()
