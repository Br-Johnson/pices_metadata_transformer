"""Verify the finite access delta, whole metadata equality and every source byte."""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DOCS = Path(__file__).resolve().parent
BASELINE_SHA = 'dd6a9775ca3124f796a7280189072a446ddbd3256ead34a02ef24013dab87247'
MANIFEST_SHA = '5c141ea3e0fae8e9b6673a2dc3f5aadba0d16c949767f80b5892ac589e6a0dbf'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def audit(before_dir, after_dir):
    before_raw = (before_dir / 'classification.json').read_bytes()
    after_raw = (after_dir / 'classification.json').read_bytes()
    assert sha(before_raw) == BASELINE_SHA
    before, after = json.loads(before_raw), json.loads(after_raw)
    assert before['summary']['source_status_counts'] == {'supported': 2288, 'held': 1912, 'failed': 6}
    assert after['summary']['source_status_counts'] == {'supported': 2430, 'held': 1770, 'failed': 6}
    for field in set(before['summary']) - {'source_status_counts'}:
        assert before['summary'][field] == after['summary'][field], field
    assert before['reviewed_at'] == after['reviewed_at']
    left = {r['source_id']: r for r in before['records']}
    right = {r['source_id']: r for r in after['records']}
    manifest_path = DOCS / 'finite_source_resource_access_264.json'
    assert sha(manifest_path.read_bytes()) == MANIFEST_SHA
    manifest = json.loads(manifest_path.read_bytes())
    previous = json.loads((REPO / 'docs/readiness/2026-10-02/registration_access_interpretation.json').read_bytes())
    assert manifest['members'][:122] == previous['members']
    assert manifest['source_contexts'] == previous['source_contexts']
    selected = {m['source_id'] for m in manifest['members']}
    promoted = set(manifest['acquisition_contexts'])
    queue86 = {m['source_id'] for m in json.loads((DOCS / 'remaining_source_credit_candidates_86.json').read_bytes())['members']}
    queue90 = {m['source_id'] for g in json.loads((DOCS / 'joint_collection_source_decisions.json').read_bytes())['remaining_meaning_decisions'] for m in g['members']}
    assert len(selected) == 264 and len(promoted) == 142 and len(queue86 | queue90) == 176
    assert not promoted & (queue86 | queue90)
    reference = {'manifest_path': str(manifest_path.relative_to(REPO)), 'manifest_sha256': MANIFEST_SHA}
    originals, copies, payloads, metadata_objects = [], [], [], []
    buckets = defaultdict(list)
    changed_payloads, changed_assessed_fingerprints = [], []
    sources = sorted((REPO / 'FGDC').glob('*.xml'))
    assert {p.stem for p in sources} == set(left) == set(right)
    for source in sources:
        sid, raw = source.stem, source.read_bytes()
        l, r = left[sid], right[sid]
        assert l['source_sha256'] == r['source_sha256'] == sha(raw), sid
        originals.append({'source_id': sid, 'source_sha256': sha(raw)})
        buckets[sha(raw)].append(sid)
        assert l['technical_metadata'] == r['technical_metadata']
        assert l['exact_copy_aliases'] == r['exact_copy_aliases']
        assert not r['remote_verified'] and not r['publication_approved']
        if sid in promoted:
            assert l['source_status'] == 'held' and r['source_status'] == 'supported'
            assert l['hold_reasons'] == ['Metadata access terms need source-backed adjudication',
                                       'Contradictory or unsupported source access constraints require adjudication']
            assert not r['hold_reasons'] and not r['exact_copy_aliases']
        else:
            assert l['source_status'] == r['source_status'] and l['hold_reasons'] == r['hold_reasons']
        if sid in queue86 | queue90:
            assert r['source_status'] == 'held'
        if l.get('metadata_sha256') != r.get('metadata_sha256'):
            assert sid in selected
            changed_assessed_fingerprints.append(sid)
        if r['source_status'] == 'failed':
            continue
        for directory in (before_dir, after_dir):
            assert (directory / 'data/original_fgdc' / source.name).read_bytes() == raw
        copies.append({'source_id': sid, 'source_sha256': sha(raw)})
        if not r.get('prepared_payload_sha256'):
            assert not l.get('prepared_payload_sha256')
            continue
        raw_payloads = [(directory / 'data/zenodo_json' / (sid + '.json')).read_bytes()
                        for directory in (before_dir, after_dir)]
        assert sha(raw_payloads[0]) == l['prepared_payload_sha256']
        assert sha(raw_payloads[1]) == r['prepared_payload_sha256']
        old, new = map(json.loads, raw_payloads)
        expected = deepcopy(old)
        if sid in selected:
            expected['artifact_policy']['dataset_access_interpretation'] = reference
            changed_payloads.append(sid)
        else:
            assert raw_payloads[0] == raw_payloads[1]
        assert expected == new, sid
        assert old['metadata'] == new['metadata']
        assert new['metadata']['access_right'] == 'restricted' and new['metadata']['license'] == ''
        payloads.append({'source_id': sid, 'prepared_payload_sha256': sha(raw_payloads[1])})
        metadata_objects.append({'source_id': sid, 'metadata_sha256': fingerprint(new['metadata'])})
    assert len(originals) == 4206 and len(copies) == 4200 and len(payloads) == len(metadata_objects) == 4194
    assert set(changed_payloads) == selected
    aliases = sorted(sorted(ids) for ids in buckets.values() if len(ids) > 1)
    assert len(aliases) == 228 and sum(map(len, aliases)) == 456
    return {'scope': 'Exact finite source interpretation; no remote verification or publication',
        'baseline_report_sha256': sha(before_raw), 'after_report_sha256': sha(after_raw),
        'manifest_sha256': MANIFEST_SHA, 'reviewed_at': after['reviewed_at'],
        'summary': after['summary'], 'promoted_source_ids': sorted(promoted), 'promotions': 142,
        'previous_122_members_and_contexts_unchanged': True,
        'full_metadata_objects_unchanged': 4194, 'payload_bytes_unchanged': 4194 - len(selected),
        'dataset_policy_references_changed': len(changed_payloads),
        'assessed_artifact_fingerprints_changed': len(changed_assessed_fingerprints),
        'preserved_access_holds86': True, 'preserved_joint_access_holds90': True,
        'all_other_statuses_and_hold_reasons_unchanged': True,
        'originals_verified': 4206, 'copies_verified': 4200, 'payloads_verified': 4194,
        'original_inventory_sha256': fingerprint(originals), 'copy_inventory_sha256': fingerprint(copies),
        'payload_inventory_sha256': fingerprint(payloads), 'metadata_inventory_sha256': fingerprint(metadata_objects),
        'exact_copy_groups_sha256': fingerprint(aliases), 'alias_identities_held': 456,
        'new_licenses': 0, 'provider_requests': 0, 'provider_writes': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.before, args.after), indent=2))


if __name__ == '__main__':
    main()
