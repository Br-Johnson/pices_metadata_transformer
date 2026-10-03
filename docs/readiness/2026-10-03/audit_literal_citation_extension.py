"""Verify the complete offline 39-source delta; no provider or source mutations."""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / 'docs/readiness/2026-10-03'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def audit(before_dir, after_dir, reviewed_dir=None):
    before_raw = (before_dir / 'classification.json').read_bytes()
    after_raw = (after_dir / 'classification.json').read_bytes()
    before, after = json.loads(before_raw), json.loads(after_raw)
    reviewed_raw, reviewed_rows = None, None
    if reviewed_dir is not None:
        reviewed_raw = (reviewed_dir / 'classification.json').read_bytes()
        assert digest(reviewed_raw) == 'f6b68ea0bbc328bd44f6bba06a9b504c8b438c232fc10dcc868d628e2867ec91'
        reviewed_rows = {r['source_id']: r for r in json.loads(reviewed_raw)['records']}
    assert before['reviewed_at'] == after['reviewed_at']
    assert before['summary']['source_status_counts'] == {'supported': 2138, 'held': 2062, 'failed': 6}
    assert after['summary']['source_status_counts'] == {'supported': 2177, 'held': 2023, 'failed': 6}
    manifest_path = DOCS / 'literal_citation_extension_229.json'
    raw_manifest = manifest_path.read_bytes()
    assert digest(raw_manifest) == 'd2ba819c774a43f8cb5d90c28f2e4b3d41283747ddea9f282c0241468ab2c749'
    manifest = json.loads(raw_manifest)
    previous = json.loads((DOCS / 'joint_collection_citation_190.json').read_bytes())
    assert manifest['cohorts'][:14] == previous['cohorts']
    profiles = {m['source_id']: (m, c) for c in manifest['cohorts'] for m in c['members']}
    new_ids = {m['source_id'] for c in manifest['cohorts'][14:] for m in c['members']}
    candidates = json.loads((DOCS / 'residual_source_candidates.json').read_bytes())
    assert new_ids == {m['source_id'] for c in candidates['recommended_literal_batches'] for m in c['members']}
    assert len(profiles) == 229 and len(new_ids) == 39
    reference = {'manifest_path': str(manifest_path.relative_to(ROOT)), 'manifest_sha256': digest(raw_manifest)}
    before_rows = {r['source_id']: r for r in before['records']}
    after_rows = {r['source_id']: r for r in after['records']}
    sources = sorted((ROOT / 'FGDC').glob('*.xml'))
    assert {p.stem for p in sources} == set(before_rows) == set(after_rows)
    originals, copies, payloads, metadata = [], [], [], []
    buckets = defaultdict(list)
    copied_ids, payload_ids, policy_changed, status_changed = set(), set(), [], []
    for source in sources:
        sid, raw = source.stem, source.read_bytes()
        sha = digest(raw)
        left, right = before_rows[sid], after_rows[sid]
        assert left['source_sha256'] == right['source_sha256'] == sha
        if reviewed_rows is not None:
            assert reviewed_rows[sid]['source_sha256'] == sha
        originals.append({'source_id': sid, 'source_sha256': sha})
        buckets[sha].append(sid)
        assert left['technical_metadata'] == right['technical_metadata']
        assert left['exact_copy_aliases'] == right['exact_copy_aliases']
        assert not right['remote_verified'] and not right['publication_approved']
        if left['source_status'] != right['source_status']:
            assert sid in new_ids and left['source_status'] == 'held' and right['source_status'] == 'supported'
            assert left['hold_reasons'] == ['Creator semantics are ambiguous'] and not right['hold_reasons']
            status_changed.append(sid)
        else:
            assert left['hold_reasons'] == right['hold_reasons']
        if sid in profiles:
            member, cohort = profiles[sid]
            assert member['source_sha256'] == sha
            assert not right['exact_copy_aliases']
        if right['source_status'] == 'failed':
            continue
        for directory in (before_dir, after_dir):
            assert (directory / 'data/original_fgdc' / source.name).read_bytes() == raw
        copied_ids.add(sid)
        copies.append({'source_id': sid, 'source_sha256': sha})
        if not right.get('prepared_payload_sha256'):
            assert not left.get('prepared_payload_sha256')
            continue
        name = sid + '.json'
        left_raw = (before_dir / 'data/zenodo_json' / name).read_bytes()
        right_raw = (after_dir / 'data/zenodo_json' / name).read_bytes()
        assert digest(left_raw) == left['prepared_payload_sha256']
        assert digest(right_raw) == right['prepared_payload_sha256']
        left_payload, right_payload = json.loads(left_raw), json.loads(right_raw)
        if reviewed_dir is not None:
            prior_raw = (reviewed_dir / 'data/zenodo_json' / name).read_bytes()
            assert digest(prior_raw) == reviewed_rows[sid]['prepared_payload_sha256']
            assert left_payload['metadata'] == json.loads(prior_raw)['metadata']
        assert left_payload['metadata'] == right_payload['metadata']
        expected = deepcopy(left_payload)
        if sid in profiles:
            assert right_payload['metadata']['creators'] == profiles[sid][1]['creators']
            expected['artifact_policy']['creator_interpretation'] = reference
            policy_changed.append(sid)
            assert digest(left_raw) != digest(right_raw)
        else:
            assert left_raw == right_raw
        assert right_payload == expected
        assert right_payload['metadata']['access_right'] == 'restricted'
        assert right_payload['metadata']['license'] == ''
        payload_ids.add(sid)
        payloads.append({'source_id': sid, 'prepared_payload_sha256': digest(right_raw)})
        metadata.append({'source_id': sid, 'prepared_metadata_sha256': fingerprint(right_payload['metadata'])})
    assert len(originals) == 4206 and len(copies) == 4200 and len(payloads) == len(metadata) == 4194
    assert set(status_changed) == new_ids and set(policy_changed) == set(profiles)
    for directory in (before_dir, after_dir):
        assert {p.stem for p in (directory / 'data/original_fgdc').glob('*.xml')} == copied_ids
        assert {p.stem for p in (directory / 'data/zenodo_json').glob('*.json')} == payload_ids
    groups = [{'source_sha256': sha, 'source_ids': sorted(ids)}
              for sha, ids in sorted(buckets.items()) if len(ids) > 1]
    alias_map = json.loads((DOCS / 'source_alias_candidates.json').read_bytes())
    for relative_path, expected_sha in alias_map['public_evidence_files'].items():
        assert digest((ROOT / relative_path).read_bytes()) == expected_sha
    assert fingerprint(groups) == alias_map['exact_copy_groups_sha256']
    for sid, row in alias_map['source_alias_to_candidate_canonical'].items():
        current = after_rows[sid]
        assert current['source_status'] == 'held' and current['hold_reasons'] == row['hold_reasons']
        assert current['prepared_payload_sha256'] == row['prepared_payload_sha256']
    decisions_path = DOCS / 'joint_collection_source_decisions.json'
    assert digest(decisions_path.read_bytes()) == '8b94c19e501c060c458a5a71cfe0ebd123701f8101f659f34406e77e394a9b37'
    previous_new = {m['source_id'] for c in previous['cohorts'][11:] for m in c['members']}
    access_held = sorted(sid for sid in previous_new if before_rows[sid]['source_status'] == 'held')
    assert len(access_held) == 90
    assert all(after_rows[sid]['source_status'] == 'held' for sid in access_held)
    outside = ['FGDC-121', 'FGDC-1767', 'FGDC-336', 'FGDC-533', 'FGDC-535']
    assert set(outside).isdisjoint(profiles)
    assert all(after_rows[sid]['source_status'] == 'held' for sid in outside)
    for cohort in candidates['irreducible_missing_source_evidence'] + [candidates['mixed_role_order_review']]:
        for member in cohort['members']:
            sid = member['source_id']
            assert sid not in profiles and after_rows[sid]['source_status'] == 'held'
    return {'analysis_scope': 'Complete offline source delta; no remote state, ownership or release authority.',
            'manifest_sha256': digest(raw_manifest), 'previous_190_cohort_objects_unchanged': True,
            'baseline_report_sha256': digest(before_raw), 'after_report_sha256': digest(after_raw),
            'reviewed_baseline_report_sha256': digest(reviewed_raw) if reviewed_raw else None,
            'fresh_baseline_complete_metadata_equal_to_reviewed_d1efbe0': len(metadata) if reviewed_dir else None,
            'reviewed_at': after['reviewed_at'], 'source_summary': after['summary'],
            'promoted_source_ids': sorted(status_changed), 'source_status_delta': 39,
            'verified_original_hashes': len(originals), 'verified_before_after_XML_copies': len(copies),
            'verified_before_after_prepared_payload_hashes': len(payloads),
            'complete_metadata_objects_unchanged': len(metadata),
            'creator_objects_changed': 0, 'policy_references_changed': len(policy_changed),
            'whole_prepared_payload_bytes_unchanged': len(payloads) - len(policy_changed),
            'new_policy_references': 39, 'administrative_policy_rebindings': 190,
            'changed_policy_source_ids': sorted(policy_changed),
            'source_inventory_sha256': fingerprint(originals), 'copied_inventory_sha256': fingerprint(copies),
            'prepared_inventory_sha256': fingerprint(payloads), 'complete_metadata_inventory_sha256': fingerprint(metadata),
            'exact_copy_groups_sha256': fingerprint(groups), 'alias_holds_preserved': 456,
            'joint_collection_access_holds_preserved': 90, 'same_origin_siblings_excluded': outside,
            'empty_origin_date_and_mixed_role_holds_preserved': True,
            'provider_requests': 0, 'provider_writes': 0, 'remote_verified': 0, 'publication_approved': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--reviewed-baseline', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.before, args.after, args.reviewed_baseline), indent=2, ensure_ascii=False))
