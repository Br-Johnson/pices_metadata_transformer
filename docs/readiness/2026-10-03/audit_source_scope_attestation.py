"""Verify the exact821 scope-only delta and preservation of all source metadata."""
import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DOCS = Path(__file__).resolve().parent
MANIFEST_SHA256 = '3e2bc71f6cd409769a8ccb34912ec2c1a7a3802f3444c2446038e347dbc5a657'
OLD_REPORT_SHA256 = '6213c25a1f3d71cdb08ae19a1ca91762fdad5b3f11524ed7ed137f1b7edb044e'
ACCESS_REASONS = {'Metadata access terms need source-backed adjudication',
                  'Contradictory or unsupported source access constraints require adjudication'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def audit(old_dir, before_dir, after_dir):
    oldraw = (old_dir / 'classification.json').read_bytes()
    assert sha(oldraw) == OLD_REPORT_SHA256
    beforeraw = (before_dir / 'classification.json').read_bytes()
    afterraw = (after_dir / 'classification.json').read_bytes()
    old, before, after = map(json.loads, (oldraw, beforeraw, afterraw))
    assert old['summary'] == before['summary']
    assert before['summary']['source_status_counts'] == {'supported': 2443, 'held': 1757, 'failed': 6}
    assert after['summary']['source_status_counts'] == {'supported': 3234, 'held': 966, 'failed': 6}
    assert before['reviewed_at'] == after['reviewed_at']
    assert {k: v for k, v in before['summary'].items() if k != 'source_status_counts'} == {
        k: v for k, v in after['summary'].items() if k != 'source_status_counts'}
    oldrows, left, right = ({r['source_id']: r for r in data['records']} for data in (old, before, after))
    manifest_path = DOCS / 'source_scope_attestation_821.json'
    rawmanifest = manifest_path.read_bytes()
    assert sha(rawmanifest) == MANIFEST_SHA256
    manifest = json.loads(rawmanifest)
    selected = {m['source_id']: m for m in manifest['members']}
    assert len(selected) == 821
    reference = {'manifest_path': str(manifest_path.relative_to(REPO)), 'manifest_sha256': MANIFEST_SHA256}
    queue86 = {m['source_id'] for m in json.loads((DOCS / 'remaining_source_credit_candidates_86.json').read_bytes())['members']}
    queue90 = {m['source_id'] for g in json.loads((DOCS / 'joint_collection_source_decisions.json').read_bytes())['remaining_meaning_decisions'] for m in g['members']}
    protected = queue86 | queue90
    assert len(protected) == 176 and len(protected & selected.keys()) == 30
    originals, copies, metadata_objects, changed_payloads, promoted, retained = [], [], [], [], [], []
    for source in sorted((REPO / 'FGDC').glob('*.xml')):
        sid, raw = source.stem, source.read_bytes()
        o, l, r = oldrows[sid], left[sid], right[sid]
        assert o['source_sha256'] == l['source_sha256'] == r['source_sha256'] == sha(raw), sid
        originals.append({'source_id': sid, 'source_sha256': sha(raw)})
        assert o['source_status'] == l['source_status'] and o['hold_reasons'] == l['hold_reasons'], sid
        assert l['exact_copy_aliases'] == r['exact_copy_aliases']
        assert l['technical_metadata'] == r['technical_metadata']
        assert not r['remote_verified'] and not r['publication_approved']
        if sid in selected:
            assert l['source_status'] == 'held' and not r['exact_copy_aliases']
            assert r['source_scope_attestation'] == 'USER_ATTESTED'
            expected_holds = [reason for reason in l['hold_reasons'] if reason not in ACCESS_REASONS]
            assert r['hold_reasons'] == expected_holds, (sid, expected_holds, r['hold_reasons'])
            assert r['source_status'] == ('held' if expected_holds else 'supported'), sid
            (retained if expected_holds else promoted).append(sid)
        else:
            assert l['source_status'] == r['source_status'] and l['hold_reasons'] == r['hold_reasons'], sid
            assert 'source_scope_attestation' not in r
        if r['source_status'] == 'failed':
            continue
        for directory in (old_dir, before_dir, after_dir):
            assert (directory / 'data/original_fgdc' / source.name).read_bytes() == raw, sid
        copies.append({'source_id': sid, 'source_sha256': sha(raw)})
        if not r.get('prepared_payload_sha256'):
            assert not o.get('prepared_payload_sha256') and not l.get('prepared_payload_sha256')
            continue
        oldbytes, leftbytes, rightbytes = ((directory / 'data/zenodo_json' / (sid + '.json')).read_bytes()
                                          for directory in (old_dir, before_dir, after_dir))
        assert sha(oldbytes) == o['prepared_payload_sha256']
        assert sha(leftbytes) == l['prepared_payload_sha256']
        assert sha(rightbytes) == r['prepared_payload_sha256']
        oldpayload, lp, rp = map(json.loads, (oldbytes, leftbytes, rightbytes))
        expected = deepcopy(lp)
        if sid in selected:
            expected['artifact_policy']['source_scope_attestation'] = reference
            changed_payloads.append(sid)
        else:
            assert leftbytes == rightbytes, sid
        assert expected == rp, sid
        assert oldpayload['metadata'] == lp['metadata'] == rp['metadata'], sid
        assert rp['metadata']['access_right'] == 'restricted' and rp['metadata']['license'] == ''
        assert 'rehosting_authority' in rp['artifact_policy']
        metadata_objects.append({'source_id': sid, 'metadata_sha256': fingerprint(rp['metadata'])})
    assert len(originals) == 4206 and len(copies) == 4200 and len(metadata_objects) == 4194
    assert set(changed_payloads) == selected.keys() and len(promoted) == 791 and len(retained) == 30
    assert len(set(promoted) & protected) == 28
    assert all(right[sid]['source_status'] == 'held' for sid in protected - set(promoted))
    assert len(protected - set(promoted)) == 148
    groups = {tuple(r['exact_copy_aliases']) for r in right.values() if r['exact_copy_aliases']}
    assert len(groups) == 228 and len({sid for g in groups for sid in g}) == 456
    return {'schema_version': 1, 'scope': 'Exact question-bound USER_ATTESTED scope-only source reassessment; no remote or release authority',
        'frozen_previous_report_sha256': sha(oldraw), 'baseline_report_sha256': sha(beforeraw), 'after_report_sha256': sha(afterraw),
        'manifest_sha256': sha(rawmanifest), 'reviewed_at': after['reviewed_at'], 'summary': after['summary'],
        'selected_sources': 821, 'scope_policy_references_added': len(changed_payloads), 'promotions': len(promoted),
        'promoted_by_cohort': dict(Counter(selected[s]['cohort'] for s in promoted)), 'promoted_source_ids': sorted(promoted),
        'independent_hold_source_ids': sorted(retained), 'independent_holds': {sid: right[sid]['hold_reasons'] for sid in retained},
        'originals_verified': 4206, 'copies_verified': 4200, 'full_metadata_objects_unchanged_vs_frozen_previous_and_current_baseline': 4194,
        'same_timestamp_payload_bytes_unchanged_outside821': 3373, 'original_inventory_sha256': fingerprint(originals),
        'copy_inventory_sha256': fingerprint(copies), 'metadata_inventory_sha256': fingerprint(metadata_objects),
        'protected_access_reassessments_within_explicit821_answer': 30, 'protected_promotions': 28, 'protected_remaining_held': 148,
        'all_other_statuses_and_hold_reasons_unchanged': True, 'alias_identities_held': 456,
        'new_licenses': 0, 'underlying_data_rights_granted': False, 'provider_requests': 0, 'provider_writes': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old', type=Path, required=True)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.old, args.before, args.after), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
