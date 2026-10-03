"""Standalone offline audit of exact access-held credit cleanup and all source bytes."""
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


def source_element(node, outer=True):
    return {'tag': node.tag, 'attributes': dict(node.attrib), 'text': node.text,
            'tail': None if outer else node.tail,
            'children': [source_element(child, False) for child in node]}


def source_notes(profile, root):
    nodes = root.findall('./idinfo/citation/citeinfo/origin')
    assert len(nodes) == 1
    node = nodes[0]
    if profile.get('primary_origin_element') is not None:
        assert source_element(node) == profile['primary_origin_element']
        node = deepcopy(node)
        node.tail = None
        notes = ['Original primary citation origin XML (parsed representation): ' + ET.tostring(node, encoding='unicode')]
    else:
        assert not list(node) and not node.attrib and node.text == profile['raw_origin']
        notes = ['Original primary citation origin: ' + node.text]
    for evidence in profile.get('supplemental_source_elements', []):
        ns = root.findall(evidence['xpath'])
        assert len(ns) == 1 and source_element(ns[0]) == evidence['element']
    if profile.get('context_note'):
        notes.append(profile['context_note'])
    return notes


def audit(before_dir, after_dir, reviewed_dir):
    raw_reports = [(p / 'classification.json').read_bytes() for p in (before_dir, after_dir, reviewed_dir)]
    assert digest(raw_reports[2]) == 'e075199e01caef6a1018160be2a74c73f76b3d42190eac72511a14d0f9a0eb26'
    reports = list(map(json.loads, raw_reports))
    assert len({r['reviewed_at'] for r in reports}) == 1
    assert all(r['summary']['source_status_counts'] == {'supported': 2288, 'held': 1912, 'failed': 6} for r in reports)
    rows = [{r['source_id']: r for r in report['records']} for report in reports]
    left_rows, right_rows, prior_rows = rows
    manifest_path = DOCS / 'access_held_source_citations_396.json'
    manifest_raw = manifest_path.read_bytes()
    assert digest(manifest_raw) == '7b45346be4435fc9fa6bfecfeb3cbc175610abf37a3e59a6b43b9731028e6b8c'
    manifest = json.loads(manifest_raw)
    previous = json.loads((DOCS / 'source_credit_citations_319.json').read_bytes())
    assert manifest['cohorts'][:143] == previous['cohorts']
    profiles = {m['source_id']: (m, c) for c in manifest['cohorts'] for m in c['members']}
    new_ids = {m['source_id'] for c in manifest['cohorts'][143:] for m in c['members']}
    queue_path = DOCS / 'remaining_source_credit_candidates_86.json'
    assert digest(queue_path.read_bytes()) == 'e81f08548c86a454cf96d4b3d5ca2efd75f87ba518bc793c1f8f7d83194c5843'
    queue = {m['source_id']: m for m in json.loads(queue_path.read_bytes())['members']}
    excluded = {f'FGDC-{i}' for i in [10, 1257, 1258, 1262, 1273, 2664, 2817, 4063, 4064]}
    assert len(profiles) == 396 and len(new_ids) == 77 and new_ids == set(queue) - excluded
    reference = {'manifest_path': str(manifest_path.relative_to(ROOT)), 'manifest_sha256': digest(manifest_raw)}
    caveat = '\nSource dataset citation originators are preserved for attribution; XML authorship is not independently established.'
    originals, copies, payloads, metadata_inventory, new_after_images = [], [], [], [], []
    buckets = defaultdict(list)
    copied_ids, payload_ids, changed_metadata, changed_creators, changed_policy, changed_holds = set(), set(), [], [], [], []
    assessed_fp_changed = []
    sources = sorted((ROOT / 'FGDC').glob('*.xml'))
    assert all({s.stem for s in sources} == set(row_map) for row_map in rows)
    for path in sources:
        sid, raw = path.stem, path.read_bytes()
        sha = digest(raw)
        left, right, prior = left_rows[sid], right_rows[sid], prior_rows[sid]
        assert left['source_sha256'] == right['source_sha256'] == prior['source_sha256'] == sha
        originals.append({'source_id': sid, 'source_sha256': sha})
        buckets[sha].append(sid)
        assert left['source_status'] == right['source_status'] == prior['source_status']
        assert left['technical_metadata'] == right['technical_metadata']
        assert left['exact_copy_aliases'] == right['exact_copy_aliases']
        assert not right['remote_verified'] and not right['publication_approved']
        if sid in new_ids:
            assert right['source_status'] == 'held' and not right['exact_copy_aliases']
            assert left['hold_reasons'] == ['Metadata access terms need source-backed adjudication', 'Creator semantics are ambiguous']
            assert right['hold_reasons'] == ['Metadata access terms need source-backed adjudication', 'Contradictory or unsupported source access constraints require adjudication']
            changed_holds.append(sid)
        else:
            assert left['hold_reasons'] == right['hold_reasons']
        if left.get('metadata_sha256') != right.get('metadata_sha256'):
            assert sid in profiles and sid not in new_ids and left['source_status'] == 'supported'
            assessed_fp_changed.append(sid)
        if right['source_status'] == 'failed':
            continue
        for directory in (before_dir, after_dir, reviewed_dir):
            assert (directory / 'data/original_fgdc' / path.name).read_bytes() == raw
        copied_ids.add(sid)
        copies.append({'source_id': sid, 'source_sha256': sha})
        if not right.get('prepared_payload_sha256'):
            assert not left.get('prepared_payload_sha256') and not prior.get('prepared_payload_sha256')
            continue
        raw_payloads = [(directory / 'data/zenodo_json' / (sid + '.json')).read_bytes() for directory in (before_dir, after_dir, reviewed_dir)]
        assert all(digest(value) == row['prepared_payload_sha256'] for value, row in zip(raw_payloads, (left, right, prior)))
        assert raw_payloads[0] == raw_payloads[2]
        left_payload, right_payload = map(json.loads, raw_payloads[:2])
        expected = deepcopy(left_payload)
        root = ET.fromstring(raw)
        if sid in profiles:
            member, profile = profiles[sid]
            assert member['source_sha256'] == sha
            expected['artifact_policy']['creator_interpretation'] = reference
            changed_policy.append(sid)
            if sid in new_ids:
                old_creators = expected['metadata']['creators']
                expected['metadata']['creators'] = profile['creators']
                date = left['raw_metadata_date']
                old_decision = json.dumps({'metadata': {'creators': old_creators, 'license': '', 'publication_date': date}}, sort_keys=True)
                new_decision = json.dumps({'metadata': {'creators': profile['creators'], 'license': '', 'publication_date': date}}, sort_keys=True)
                notes = expected['metadata']['notes']
                assert notes.count('Curator decision: ' + old_decision) == 1 and notes.endswith(caveat)
                notes = notes[:-len(caveat)].replace('Curator decision: ' + old_decision, 'Curator decision: ' + new_decision)
                expected['metadata']['notes'] = notes + ''.join('\n' + n for n in source_notes(profile, root)) + caveat
                if old_creators != profile['creators']:
                    changed_creators.append(sid)
                assert expected['artifact_policy'].get('source_access_interpretation') is None
                assert expected['artifact_policy'].get('dataset_access_interpretation') is None
                for xpath, text in queue[sid]['exact_source_constraints'].items():
                    n = root.find(xpath)
                    assert (''.join(n.itertext()) if n is not None else None) == text
                assert queue[sid]['existing_full_creators'] == old_creators
                assert queue[sid]['raw_metadata_date'] == ''.join(root.find('./metainfo/metd').itertext())
                new_after_images.append({'source_id': sid, 'source_sha256': sha, 'metadata': expected['metadata']})
        assert expected == right_payload, sid
        if expected['metadata'] != left_payload['metadata']:
            changed_metadata.append(sid)
        if sid not in profiles:
            assert raw_payloads[0] == raw_payloads[1]
        assert expected['metadata']['access_right'] == 'restricted' and expected['metadata']['license'] == ''
        payload_ids.add(sid)
        payloads.append({'source_id': sid, 'prepared_payload_sha256': digest(raw_payloads[1])})
        metadata_inventory.append({'source_id': sid, 'metadata_sha256': fingerprint(expected['metadata'])})
    assert len(originals) == 4206 and len(copies) == 4200 and len(payloads) == 4194
    assert set(changed_metadata) == set(changed_holds) == new_ids
    assert set(changed_policy) == set(profiles)
    for directory in (before_dir, after_dir):
        assert {p.stem for p in (directory / 'data/original_fgdc').glob('*.xml')} == copied_ids
        assert {p.stem for p in (directory / 'data/zenodo_json').glob('*.json')} == payload_ids
    groups = [{'source_sha256': sha, 'source_ids': sorted(ids)} for sha, ids in sorted(buckets.items()) if len(ids) > 1]
    aliases = json.loads((DOCS / 'source_alias_candidates.json').read_bytes())
    assert fingerprint(groups) == aliases['exact_copy_groups_sha256']
    for name, sha in aliases['public_evidence_files'].items():
        assert digest((ROOT / name).read_bytes()) == sha
    for sid, proof in aliases['source_alias_to_candidate_canonical'].items():
        assert right_rows[sid]['source_status'] == 'held' and right_rows[sid]['hold_reasons'] == proof['hold_reasons']
        assert right_rows[sid]['prepared_payload_sha256'] == proof['prepared_payload_sha256']
    assert digest((DOCS / 'joint_collection_source_decisions.json').read_bytes()) == '8b94c19e501c060c458a5a71cfe0ebd123701f8101f659f34406e77e394a9b37'
    old190 = json.loads((DOCS / 'joint_collection_citation_190.json').read_bytes())
    old_access = {m['source_id'] for c in old190['cohorts'][11:] for m in c['members'] if prior_rows[m['source_id']]['source_status'] == 'held'}
    assert len(old_access) == 90 and all(right_rows[sid]['source_status'] == 'held' for sid in old_access)
    assert len(assessed_fp_changed) == 209
    return {'scope': 'Exact source-credit cleanup only; all 86 access holds remains. No source-support promotion or release approval.',
            'baseline_report_sha256': digest(raw_reports[0]), 'after_report_sha256': digest(raw_reports[1]),
            'reviewed_baseline_report_sha256': digest(raw_reports[2]), 'manifest_sha256': digest(manifest_raw),
            'source_queue_sha256': digest(queue_path.read_bytes()), 'reviewed_at': reports[1]['reviewed_at'],
            'source_summary': reports[1]['summary'], 'source_status_delta': 0,
            'previous_319_cohort_objects_unchanged': True, 'reviewed_baseline_payload_bytes_reproduced': len(payload_ids),
            'source_credit_metadata_corrections': len(changed_metadata), 'full_creator_objects_changed': len(changed_creators),
            'creator_changed_source_ids': sorted(changed_creators), 'corrected_source_ids': sorted(new_ids),
            'notes_only_corrections': len(changed_metadata) - len(changed_creators),
            'complete_prepared_metadata_objects_unchanged': len(payload_ids) - len(changed_metadata),
            'policy_references_changed': len(changed_policy), 'administrative_previous_policy_rebindings': 319,
            'whole_prepared_payload_bytes_unchanged': len(payload_ids) - len(changed_policy),
            'previously_supported_assessed_fingerprint_changes_from_policy_rebinding': len(assessed_fp_changed),
            'creator_diagnostics_cleared_but_access_holds_retained': len(changed_holds),
            'all86_access_holds_preserved': True, 'excluded_creator_role_source_ids': sorted(excluded),
            'verified_original_hashes': len(originals), 'verified_XML_copy_bytes': len(copies),
            'verified_prepared_payload_hashes': len(payload_ids),
            'inventory_sha256': {'original': fingerprint(originals), 'copy': fingerprint(copies),
                                 'payload': fingerprint(payloads), 'metadata': fingerprint(metadata_inventory)},
            'complete_77_prepared_metadata_after_images_sha256': fingerprint(new_after_images),
            'exact_copy_groups_sha256': fingerprint(groups), 'alias_holds_preserved': 456,
            'joint_collection_access_holds_preserved': 90, 'all_other_hold_reasons_unchanged': True,
            'provider_requests': 0, 'provider_writes': 0, 'remote_verified': 0, 'publication_approved': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', required=True, type=Path)
    parser.add_argument('--reviewed-baseline', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.before, args.after, args.reviewed_baseline), indent=2, ensure_ascii=False))
