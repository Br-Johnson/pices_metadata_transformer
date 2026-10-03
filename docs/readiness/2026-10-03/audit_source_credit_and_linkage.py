"""Verify the complete bounded source-credit/linkage delta without network access."""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / 'docs/readiness/2026-10-03'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def audit(before_dir, after_dir, reviewed_dir):
    from scripts.citation_creator_interpretation import validate_creator_interpretation
    from scripts.source_link_interpretation import validate_source_link_policy
    before_raw = (before_dir / 'classification.json').read_bytes()
    after_raw = (after_dir / 'classification.json').read_bytes()
    reviewed_raw = (reviewed_dir / 'classification.json').read_bytes()
    assert digest(reviewed_raw) == '64a9c6fca4527c3f3901ca14e014690a18cc0ee4a455fa902bf7c35483c3c0e7'
    before, after, reviewed = map(json.loads, (before_raw, after_raw, reviewed_raw))
    assert before['reviewed_at'] == after['reviewed_at'] == reviewed['reviewed_at']
    assert before['summary']['source_status_counts'] == {'supported': 2177, 'held': 2023, 'failed': 6}
    assert after['summary']['source_status_counts'] == {'supported': 2288, 'held': 1912, 'failed': 6}
    creator_path, link_path = DOCS / 'source_credit_citations_319.json', DOCS / 'historical_dataset_linkage_21.json'
    assert digest(creator_path.read_bytes()) == '7526abc74cdc62644fe682b17ebb23213b90ccb80f6f00c61ee149174ae7c257'
    assert digest(link_path.read_bytes()) == '53b8f4cf4b2c84755653328916d0abfb8439984bd31906e0359f7588e5bd6168'
    manifest, links = json.loads(creator_path.read_bytes()), json.loads(link_path.read_bytes())
    previous = json.loads((DOCS / 'literal_citation_extension_229.json').read_bytes())
    assert manifest['cohorts'][:53] == previous['cohorts']
    profiles = {m['source_id']: (m, c) for c in manifest['cohorts'] for m in c['members']}
    new_ids = {m['source_id'] for c in manifest['cohorts'][53:] for m in c['members']}
    link_ids = {m['source_id'] for m in links['members']}
    assert len(profiles) == 319 and len(new_ids) == 90 and len(link_ids) == 21
    assert new_ids.isdisjoint(link_ids)
    creator_ref = {'manifest_path': str(creator_path.relative_to(ROOT)), 'manifest_sha256': digest(creator_path.read_bytes())}
    link_ref = {'manifest_path': str(link_path.relative_to(ROOT)), 'manifest_sha256': digest(link_path.read_bytes())}
    rows = [{r['source_id']: r for r in x['records']} for x in (before, after, reviewed)]
    before_rows, after_rows, reviewed_rows = rows
    sources = sorted((ROOT / 'FGDC').glob('*.xml'))
    assert all({p.stem for p in sources} == set(r) for r in rows)
    inventories = {name: [] for name in ('original', 'copy', 'payload', 'metadata')}
    buckets = defaultdict(list)
    payload_ids, copy_ids = set(), set()
    changed_status, policy_changed, metadata_changed, creator_changed = [], [], [], []
    caveat = '\nSource dataset citation originators are preserved for attribution; XML authorship is not independently established.'
    for source in sources:
        sid, raw = source.stem, source.read_bytes()
        sha = digest(raw)
        left, right, ancestral = before_rows[sid], after_rows[sid], reviewed_rows[sid]
        assert left['source_sha256'] == right['source_sha256'] == ancestral['source_sha256'] == sha
        inventories['original'].append({'source_id': sid, 'source_sha256': sha})
        buckets[sha].append(sid)
        assert left['technical_metadata'] == right['technical_metadata']
        assert left['exact_copy_aliases'] == right['exact_copy_aliases']
        assert not right['remote_verified'] and not right['publication_approved']
        if left['source_status'] != right['source_status']:
            assert sid in new_ids | link_ids and left['source_status'] == 'held' and right['source_status'] == 'supported'
            assert left['hold_reasons'] == [('Creator semantics are ambiguous' if sid in new_ids else 'Relations require explicit record-level adjudication')]
            assert not right['hold_reasons']
            changed_status.append(sid)
        else:
            assert left['hold_reasons'] == right['hold_reasons']
        if sid in profiles or sid in link_ids:
            assert not right['exact_copy_aliases']
        if right['source_status'] == 'failed':
            continue
        for directory in (before_dir, after_dir, reviewed_dir):
            assert (directory / 'data/original_fgdc' / source.name).read_bytes() == raw
        copy_ids.add(sid)
        inventories['copy'].append({'source_id': sid, 'source_sha256': sha})
        if not right.get('prepared_payload_sha256'):
            assert not left.get('prepared_payload_sha256') and not ancestral.get('prepared_payload_sha256')
            continue
        filename = sid + '.json'
        left_raw, right_raw, prior_raw = [(d / 'data/zenodo_json' / filename).read_bytes() for d in (before_dir, after_dir, reviewed_dir)]
        assert digest(left_raw) == left['prepared_payload_sha256']
        assert digest(right_raw) == right['prepared_payload_sha256']
        assert digest(prior_raw) == ancestral['prepared_payload_sha256']
        # Fresh baseline fully reproduces the reviewed source checkpoint, including policy.
        assert left_raw == prior_raw
        left_payload, right_payload = json.loads(left_raw), json.loads(right_raw)
        expected = deepcopy(left_payload)
        root = ET.fromstring(raw)
        if sid in profiles:
            member, profile = profiles[sid]
            assert member['source_sha256'] == sha
            expected['artifact_policy']['creator_interpretation'] = creator_ref
            if sid in new_ids:
                result = validate_creator_interpretation(creator_ref, sid, sha, root, True)
                old_creators = expected['metadata']['creators']
                expected['metadata']['creators'] = profile['creators']
                date = left['raw_metadata_date']
                old_decision = json.dumps({'metadata': {'creators': old_creators, 'license': '', 'publication_date': date}}, sort_keys=True)
                new_decision = json.dumps({'metadata': {'creators': profile['creators'], 'license': '', 'publication_date': date}}, sort_keys=True)
                old_notes = expected['metadata']['notes']
                assert old_notes.count('Curator decision: ' + old_decision) == 1 and old_notes.endswith(caveat)
                prefix = old_notes[:-len(caveat)].replace('Curator decision: ' + old_decision, 'Curator decision: ' + new_decision)
                expected['metadata']['notes'] = prefix + ''.join('\n' + n for n in result['preservation_notes']) + caveat
                if old_creators != profile['creators']:
                    creator_changed.append(sid)
        if sid in link_ids:
            expected['artifact_policy']['source_link_interpretation'] = link_ref
            expected['metadata']['related_identifiers'] = []
            expected['metadata']['notes'] += '\n\n' + links['preservation_note']
            validate_source_link_policy(expected['artifact_policy'], sid, sha, root, expected['metadata'])
        assert expected == right_payload, sid
        if expected != left_payload:
            policy_changed.append(sid)
        else:
            assert left_raw == right_raw
        if expected['metadata'] != left_payload['metadata']:
            metadata_changed.append(sid)
        assert expected['metadata']['access_right'] == 'restricted' and expected['metadata']['license'] == ''
        payload_ids.add(sid)
        inventories['payload'].append({'source_id': sid, 'prepared_payload_sha256': digest(right_raw)})
        inventories['metadata'].append({'source_id': sid, 'metadata_sha256': fingerprint(right_payload['metadata'])})
    assert list(map(len, inventories.values())) == [4206, 4200, 4194, 4194]
    assert set(changed_status) == new_ids | link_ids
    assert set(metadata_changed) == new_ids | link_ids
    assert set(policy_changed) == set(profiles) | link_ids
    for directory in (before_dir, after_dir):
        assert {p.stem for p in (directory / 'data/original_fgdc').glob('*.xml')} == copy_ids
        assert {p.stem for p in (directory / 'data/zenodo_json').glob('*.json')} == payload_ids
    groups = [{'source_sha256': sha, 'source_ids': sorted(ids)} for sha, ids in sorted(buckets.items()) if len(ids) > 1]
    aliases = json.loads((DOCS / 'source_alias_candidates.json').read_bytes())
    assert fingerprint(groups) == aliases['exact_copy_groups_sha256']
    for filename, expected_sha in aliases['public_evidence_files'].items():
        assert digest((ROOT / filename).read_bytes()) == expected_sha
    for sid, item in aliases['source_alias_to_candidate_canonical'].items():
        assert after_rows[sid]['source_status'] == 'held' and after_rows[sid]['hold_reasons'] == item['hold_reasons']
        assert after_rows[sid]['prepared_payload_sha256'] == item['prepared_payload_sha256']
    assert digest((DOCS / 'joint_collection_source_decisions.json').read_bytes()) == '8b94c19e501c060c458a5a71cfe0ebd123701f8101f659f34406e77e394a9b37'
    old190 = json.loads((DOCS / 'joint_collection_citation_190.json').read_bytes())
    access_ids = [m['source_id'] for c in old190['cohorts'][11:] for m in c['members'] if before_rows[m['source_id']]['source_status'] == 'held']
    assert len(access_ids) == 90 and all(after_rows[sid]['source_status'] == 'held' for sid in access_ids)
    return {'scope': 'Complete offline bounded source-credit and historical-link correction; no provider identity or release approval.',
            'baseline_report_sha256': digest(before_raw), 'after_report_sha256': digest(after_raw),
            'reviewed_baseline_report_sha256': digest(reviewed_raw), 'reviewed_at': after['reviewed_at'],
            'creator_manifest_sha256': creator_ref['manifest_sha256'], 'source_link_manifest_sha256': link_ref['manifest_sha256'],
            'source_summary': after['summary'], 'previous_229_cohort_objects_unchanged': True,
            'fresh_baseline_payload_bytes_equal_to_reviewed_dfeff4ce': len(payload_ids),
            'promoted_source_ids': sorted(changed_status), 'source_status_delta': len(changed_status),
            'source_credit_metadata_corrections': len(new_ids), 'historical_dataset_linkage_corrections': len(link_ids),
            'full_creator_objects_changed': len(creator_changed), 'creator_changed_source_ids': sorted(creator_changed),
            'complete_metadata_objects_unchanged': len(payload_ids) - len(metadata_changed),
            'policy_references_changed': len(policy_changed), 'administrative_previous_policy_rebindings': 229,
            'whole_prepared_payload_bytes_unchanged': len(payload_ids) - len(policy_changed),
            'verified_original_hashes': len(inventories['original']), 'verified_XML_copy_bytes': len(copy_ids),
            'verified_prepared_payload_hashes': len(payload_ids),
            'inventory_sha256': {name: fingerprint(items) for name, items in inventories.items()},
            'exact_copy_groups_sha256': fingerprint(groups), 'alias_holds_preserved': 456,
            'joint_collection_access_holds_preserved': 90, 'all_other_hold_reasons_unchanged': True,
            'provider_requests': 0, 'provider_writes': 0, 'remote_verified': 0, 'publication_approved': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--reviewed-baseline', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.before, args.after, args.reviewed_baseline), indent=2, ensure_ascii=False))
