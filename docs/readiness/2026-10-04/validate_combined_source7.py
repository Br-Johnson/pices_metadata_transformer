"""Measure seven exact source corrections and preserve all 4,206 originals offline.

Only seven selected sources and one held control are transformed. Earlier receipts
remain immutable; cached accounting does not assert remote verification or release.
"""

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / 'docs/readiness/2026-10-03'
NEW = REPO / 'docs/readiness/2026-10-04/finite_source_resource_access_563.json'
NEW_SHA = '7e9f66fc19968c3f2784ff0ea5ab6d1169c1bd165035e5612c78332567636224'
LEDGER = DOCS / 'resource_reconciliation_integrated_source_status.json'
LEDGER_SHA = 'e9f248c1730aa59f4d89f9ddf66aedf05dd172c73dab190709ea3e8c6683b061'
IDS = {'FGDC-' + str(i) for i in (885, 887, 1257, 1258, 1262, 1273, 4064)}
CONTROL = 'FGDC-4063'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def forbidden(*args, **kwargs):
    raise AssertionError('Provider transport, sockets and DNS forbidden')


def validate(output, reviewed_at):
    sys.path.insert(0, str(REPO))
    os.chdir(REPO)
    ledger_raw = LEDGER.read_bytes()
    require(digest(ledger_raw) == LEDGER_SHA, 'Frozen source ledger changed')
    ledger = json.loads(ledger_raw)
    rows_by_id = {r['source_id']: r for r in ledger['records']}
    require(len(rows_by_id) == len(ledger['records']) == 4206, 'Source accounting mismatch')
    before_counts = Counter(r['source_status'] for r in ledger['records'])
    require(before_counts == {'supported': 3638, 'held': 562, 'failed': 6}, 'Current counts differ')
    require(digest(NEW.read_bytes()) == NEW_SHA, 'Combined profile pin differs')
    new = json.loads(NEW.read_bytes())
    old_path = DOCS / 'finite_source_resource_access_556.json'
    old = json.loads(old_path.read_bytes())
    require(new['members'][:556] == old['members'], 'Prior membership changed')
    require(new['source_contexts'] == old['source_contexts'], 'Prior source contexts changed')
    require(new['resource_reconciliation_review'] == old['resource_reconciliation_review'], 'Prior review changed')
    require(all(new['acquisition_contexts'][k] == v for k, v in old['acquisition_contexts'].items()), 'Prior acquisition context changed')
    pair_path = DOCS / 'finite_source_resource_access_558.json'
    five_path = REPO / 'docs/readiness/2026-10-04/residual_source_access_561.json'
    pair, five = json.loads(pair_path.read_bytes()), json.loads(five_path.read_bytes())
    require(digest(pair_path.read_bytes()) == 'a9dee2d1191eab69d85a20e3a3c856b9e56eec7283e024a50db91974cdd316a0', 'Pair profile changed')
    require(digest(five_path.read_bytes()) == 'b0a0f90f8d61b1908ea1a291284a04d8047186e63b2dc9427181a39af6a292f7', 'Five profile changed')
    members = pair['members'][556:] + five['members'][556:]
    require({m['source_id'] for m in members} == IDS and len(members) == 7, 'Unexpected membership')
    require(new['members'][556:] == members and len(new['members']) == 563, 'Additive profile mismatch')
    for prior, key in ((pair, 'npafc_report_notification_review'), (five, 'residual_source_review')):
        require(new[key] == prior[key], 'Frozen review changed')
        require(all(new['acquisition_contexts'][sid] == value
                    for sid, value in prior['acquisition_contexts'].items()), 'Earlier context changed')
    require(not IDS.intersection({'FGDC-' + str(i) for i in (740, 815, 851, 879)}), 'Reserved overlap')
    original_hashes = {p.stem: digest(p.read_bytes()) for p in (REPO / 'FGDC').glob('*.xml')}
    require(original_hashes == {r['source_id']: r['source_sha256'] for r in ledger['records']}, 'All4206 original hashes differ')
    duplicate_hashes = {h for h, count in Counter(original_hashes.values()).items() if count > 1}
    alias_ids = {sid for sid, h in original_hashes.items() if h in duplicate_hashes}
    require(len(alias_ids) == 456 and not IDS.intersection(alias_ids), 'Alias membership changed')
    require(all(rows_by_id[sid]['source_status'] == 'held' for sid in alias_ids | set(ledger['held31_exception_ids'])), 'Protected hold changed')
    source = output / 'sources'
    source.mkdir(parents=True)
    source_hashes = {}
    for sid in sorted(IDS | {CONTROL}):
        raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
        source_hashes[sid] = digest(raw)
        require(rows_by_id[sid]['source_sha256'] == digest(raw), 'Original hash differs from ledger')
        require(rows_by_id[sid]['source_status'] == 'held', 'Selected record is not held')
        shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
    reports, payloads, evidence_rows = {}, {}, []
    with (
        patch.dict(os.environ, {'ZENODO_SANDBOX_TOKEN': 'offline-fixture-token'}, clear=True),
        patch('requests.sessions.Session.send', forbidden),
        patch('socket.socket.connect', forbidden),
        patch('socket.create_connection', forbidden),
        patch('socket.getaddrinfo', forbidden),
    ):
        import scripts.logger
        with patch.object(scripts.logger, 'get_logger', return_value=Mock()):
            from scripts.collection_qa import classify_collection
            from scripts.path_config import OutputPaths

            older = REPO / 'docs/readiness/2026-10-02'
            options = {
                'authority_manifest': older / 'rehosting_authority.json',
                'access_interpretation_manifest': older / 'contact_source_interpretation.json',
                'creator_interpretation_manifest': older / 'exxon_citation_interpretation.json',
                'contributor_access_interpretation_manifest': older / 'contributor_source_interpretation.json',
                'collective_creator_interpretation_manifest': DOCS / 'dfo_staff_citation_interpretation.json',
                'institution_creator_interpretation_manifest': DOCS / 'source_citation_credits_409.json',
                'source_link_interpretation_manifest': DOCS / 'historical_dataset_linkage_21.json',
                'source_title_interpretation_manifest': DOCS / 'source_display_titles_35.json',
                'source_scope_attestation_manifest': DOCS / 'source_scope_reconciliation_904.json',
            }
            for phase, profile in [('before', old_path), ('after', NEW), ('repeat', NEW), ('withdrawn', old_path)]:
                destination = output / ('after' if phase == 'repeat' else phase)
                reports[phase] = classify_collection(source, destination, reviewed_at,
                    dataset_access_interpretation_manifest=profile, **options)
                paths = OutputPaths(str(destination), 'sandbox')
                payloads[phase] = {}
                for sid in sorted(IDS | {CONTROL}):
                    raw = (Path(paths.zenodo_json_dir) / (sid + '.json')).read_bytes()
                    payloads[phase][sid] = json.loads(raw)
                    require(digest((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes()) == source_hashes[sid], 'Copied XML changed')
                expected = {'supported': 7, 'held': 1, 'failed': 0} if phase in ('after', 'repeat') else {'supported': 0, 'held': 8, 'failed': 0}
                require(reports[phase]['summary']['source_status_counts'] == expected, 'Unexpected bounded counts')
                for row in reports[phase]['records']:
                    require(not row['remote_verified'] and not row['publication_approved'], 'Remote/release authority added')
                    require(row['source_status'] == ('supported' if row['source_id'] in IDS and phase in ('after', 'repeat') else 'held'), 'Unexpected status')
                    if row['source_id'] in IDS and phase in ('after', 'repeat'):
                        require(row['dataset_access_interpretation'] == 'REVIEWER_RECONCILED', 'Unexpected provenance')
            require(reports['after'] == reports['repeat'], 'Resume changed report')
            require(payloads['before'] == payloads['withdrawn'], 'Withdrawal changed payload')
            require(payloads['after'] == payloads['repeat'], 'Resume changed payload')
    for sid in sorted(IDS | {CONTROL}):
        before, after = payloads['before'][sid], payloads['after'][sid]
        require(before['metadata'] == after['metadata'], 'Raw metadata changed')
        require(before['metadata']['access_right'] == 'restricted' and before['metadata']['license'] == '', 'Rights changed')
        require({k: v for k, v in before.items() if k != 'artifact_policy'} == {k: v for k, v in after.items() if k != 'artifact_policy'}, 'Payload envelope changed')
        if sid in IDS:
            policy = copy.deepcopy(after['artifact_policy'])
            policy.pop('dataset_access_interpretation')
            require(policy == before['artifact_policy'], 'Policy changed beyond exact reference')
        else:
            require(before == after, 'Held control changed')
        evidence_rows.append({'source_id': sid, 'source_sha256': source_hashes[sid],
            'before_status': 'held', 'after_status': 'supported' if sid in IDS else 'held',
            'before_payload_canonical_sha256': digest(canonical(before)),
            'after_payload_canonical_sha256': digest(canonical(after)),
            'unchanged_metadata_canonical_sha256': digest(canonical(after['metadata'])),
            'complete_metadata_and_original_copied_xml_unchanged': True})
    proposed = copy.deepcopy(ledger['records'])
    for row in proposed:
        if row['source_id'] in IDS:
            row.update(source_status='supported', evidence='measured_combined_source7')
        else:
            require(row == rows_by_id[row['source_id']], 'Unselected status changed')
    after_counts = Counter(r['source_status'] for r in proposed)
    require(after_counts == {'supported': 3645, 'held': 555, 'failed': 6}, 'Combined count mismatch')
    require(original_hashes == {p.stem: digest(p.read_bytes()) for p in (REPO / 'FGDC').glob('*.xml')}, 'Original XML changed during measurement')
    result = {'schema_version': 1, 'status': 'MEASURED_OFFLINE',
        'scope': 'Eight-source guarded before/after/repeat/withdrawal; frozen4206 ledger plus measured seven delta, not fresh full-corpus QA',
        'reviewed_at': reviewed_at, 'base_main': 'ecfba4ed3496c0a8d400eb2ace46800f0c166708',
        'prior_ledger_sha256': LEDGER_SHA, 'profile_sha256': NEW_SHA,
        'current_counts_recounted': dict(before_counts), 'combined_counts_computed': dict(after_counts),
        'combined_status_rows_sha256': digest(canonical(proposed)), 'measured_promotions': 7,
        'all_unselected_status_objects_unchanged': True, 'unselected_status_objects': 4199,
        'prior556_and_both_batch_member_context_review_objects_unchanged': True,
        'all4206_original_xml_sha256_verified_before_and_after': True,
        'original_xml_inventory_sha256': digest(canonical(original_hashes)),
        'all456_alias_identities_and31_exceptions_still_held': True,
        'resume_identical': True, 'withdrawal_restores_holds': True,
        'provider_requests': 0, 'new_remote_verifications_or_publication_approvals': 0, 'rows': evidence_rows}
    integrated = copy.deepcopy(ledger)
    integrated.update(scope=result['scope'], records=proposed,
        integrated_counts={'supported': 3645, 'held': 555, 'malformed': 6},
        promoted_source_count=177, new7_provenance_counts={'REVIEWER_RECONCILED': 7},
        per_source_status_sha256=result['combined_status_rows_sha256'],
        measured7_source_ids=sorted(IDS), original_xml_inventory_passes=2,
        combined_validation_canonical_sha256=digest(canonical(result)),
        combined_profile_sha256=NEW_SHA,
        all4206_original_xml_sha256_verified_before_and_after=True,
        all_unselected_prior_status_objects_unchanged=True)
    integrated.pop('original_xml_reads', None)
    (output / 'integrated_source_status.json').write_text(json.dumps(integrated, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reviewed-at', default=None)
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists(), 'Use a new output directory')
    result = validate(output, args.reviewed_at or datetime.now(timezone.utc).isoformat())
    (output / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
