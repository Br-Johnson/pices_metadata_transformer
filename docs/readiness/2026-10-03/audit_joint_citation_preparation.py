"""Verify offline citation deltas and prepare source/duplicate identity evidence.

Reads original XML, source-only artifacts and committed public association
evidence. Does not contact a provider, establish remote absence or grant release.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / 'docs/readiness/2026-10-03'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return digest(canonical(value).encode())


def corrected_notes(notes, creators, raw_origin):
    lines = [line for line in notes.splitlines() if line.startswith('Curator decision: ')]
    assert len(lines) == 1
    decision = json.loads(lines[0].removeprefix('Curator decision: '))
    decision['metadata']['creators'] = creators
    updated = notes.replace(lines[0], 'Curator decision: ' + json.dumps(decision, sort_keys=True))
    caveat = '\nSource dataset citation originators are preserved for attribution; '
    assert updated.count(caveat) == 1
    return updated.replace(caveat, '\nOriginal primary citation origin: ' + raw_origin + caveat)


def audit(before_dir, after_dir, reviewed_dir=None):
    before_raw = (before_dir / 'classification.json').read_bytes()
    after_raw = (after_dir / 'classification.json').read_bytes()
    before, after = json.loads(before_raw), json.loads(after_raw)
    if reviewed_dir is not None:
        reviewed_raw = (reviewed_dir / 'classification.json').read_bytes()
        assert digest(reviewed_raw) == '9dfb6e2e6ab4c3cf12e8d9a7db8bf48d44bd5296dde0f90d5d1b6df8289ead6e'
    assert before['reviewed_at'] == after['reviewed_at']
    assert before['summary']['source_status_counts'] == {'supported': 2137, 'held': 2063, 'failed': 6}
    assert after['summary']['source_status_counts'] == {'supported': 2138, 'held': 2062, 'failed': 6}
    previous = json.loads((DOCS / 'institution_program_citation_99.json').read_bytes())
    manifest_path = DOCS / 'joint_collection_citation_190.json'
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    assert manifest['cohorts'][:11] == previous['cohorts']
    profiles = {member['source_id']: (member, cohort) for cohort in manifest['cohorts']
                for member in cohort['members']}
    assert len(profiles) == 190
    new_ids = {member['source_id'] for cohort in manifest['cohorts'][11:] for member in cohort['members']}
    assert len(new_ids) == 91
    corrected_ids = {member['source_id'] for cohort in manifest['cohorts'][11:13] for member in cohort['members']}
    assert len(corrected_ids) == 68
    before_rows = {row['source_id']: row for row in before['records']}
    after_rows = {row['source_id']: row for row in after['records']}
    sources = sorted((ROOT / 'FGDC').glob('*.xml'))
    assert {p.stem for p in sources} == set(before_rows) == set(after_rows)
    inventories = {'original': [], 'copies': [], 'prepared_after': []}
    aliases, titles, normalized_titles = defaultdict(list), defaultdict(list), defaultdict(list)
    changed_status, changed_payloads, changed_metadata = [], [], []
    for source in sources:
        assert not source.is_symlink()
        sid, raw = source.stem, source.read_bytes()
        sha = digest(raw)
        a, b = after_rows[sid], before_rows[sid]
        assert a['source_sha256'] == b['source_sha256'] == sha
        inventories['original'].append({'source_id': sid, 'source_sha256': sha})
        aliases[sha].append(sid)
        if a['source_status'] != b['source_status']:
            changed_status.append(sid)
        if b['source_status'] == 'failed':
            assert a['source_status'] == 'failed'
            continue
        root = ET.fromstring(raw)
        title_node = root.find('./idinfo/citation/citeinfo/title')
        title = ''.join(title_node.itertext()) if title_node is not None else ''
        if title:
            titles[title].append(sid)
            normalized_titles[re.sub(r'\s+', ' ', title).strip().casefold()].append(sid)
        for output in (before_dir, after_dir):
            assert (output / 'data/original_fgdc' / source.name).read_bytes() == raw
        inventories['copies'].append({'source_id': sid, 'source_sha256': sha})
        if 'prepared_payload_sha256' not in b:
            assert 'prepared_payload_sha256' not in a
            continue
        old_raw = (before_dir / 'data/zenodo_json' / (sid + '.json')).read_bytes()
        new_raw = (after_dir / 'data/zenodo_json' / (sid + '.json')).read_bytes()
        assert digest(old_raw) == b['prepared_payload_sha256']
        assert digest(new_raw) == a['prepared_payload_sha256']
        inventories['prepared_after'].append({'source_id': sid, 'prepared_payload_sha256': digest(new_raw)})
        old_payload, new_payload = json.loads(old_raw), json.loads(new_raw)
        if reviewed_dir is not None:
            reviewed_payload = json.loads((reviewed_dir / 'data/zenodo_json' / (sid + '.json')).read_bytes())
            assert old_payload['metadata'] == reviewed_payload['metadata'], sid
        expected = deepcopy(old_payload)
        if sid in profiles:
            member, cohort = profiles[sid]
            assert member['source_sha256'] == sha
            expected['artifact_policy']['creator_interpretation'] = {
                'manifest_path': 'docs/readiness/2026-10-03/joint_collection_citation_190.json',
                'manifest_sha256': digest(manifest_raw)}
            if sid in corrected_ids:
                expected['metadata']['creators'] = cohort['creators']
                expected['metadata']['notes'] = corrected_notes(expected['metadata']['notes'],
                                                               cohort['creators'], cohort['raw_origin'])
            assert new_payload['metadata']['creators'] == cohort['creators']
        assert new_payload == expected, sid
        if old_raw != new_raw:
            changed_payloads.append(sid)
        if old_payload['metadata'] != new_payload['metadata']:
            changed_metadata.append(sid)
        if sid in new_ids:
            assert new_payload['metadata']['access_right'] == 'restricted'
            assert new_payload['metadata']['license'] == ''
            assert 'XML authorship is not independently established' in new_payload['metadata']['notes']
    assert changed_status == ['FGDC-619']
    assert set(changed_payloads) == set(profiles)
    assert set(changed_metadata) == corrected_ids
    assert [len(inventories[key]) for key in ('original', 'copies', 'prepared_after')] == [4206, 4200, 4194]
    for output in (before_dir, after_dir):
        assert {p.stem for p in (output / 'data/original_fgdc').glob('*.xml')} == {
            row['source_id'] for row in inventories['copies']}
        assert {p.stem for p in (output / 'data/zenodo_json').glob('*.json')} == {
            row['source_id'] for row in inventories['prepared_after']}
    groups = [{'source_sha256': sha, 'source_ids': sorted(ids)}
              for sha, ids in sorted(aliases.items()) if len(ids) > 1]
    alias_ids = {sid for group in groups for sid in group['source_ids']}
    assert len(groups) == 228 and len(alias_ids) == 456 and len(aliases) == 3978
    assert all(len(group['source_ids']) == 2 for group in groups)
    for sid, row in after_rows.items():
        assert row.get('exact_copy_aliases', []) == (sorted(aliases[row['source_sha256']]) if sid in alias_ids else [])
    assert all(after_rows[sid]['source_status'] == 'held' for sid in alias_ids)
    assert not alias_ids.intersection(new_ids)
    public_path = ROOT / 'docs/readiness/2026-10-01/five_imports_correction_proposal.json'
    public_raw = public_path.read_bytes()
    protections = sorted([{key: item[key] for key in
                          ('source_id', 'source_sha256', 'record_id', 'doi', 'association_status')}
                          for item in json.loads(public_raw)['records']], key=lambda item: item['source_id'])
    for item in protections:
        assert after_rows[item['source_id']]['source_sha256'] == item['source_sha256']
        assert item['record_id'] != 10042430

    def title_diagnostics(values):
        collisions = [ids for ids in values.values() if len(ids) > 1]
        distinct = [ids for ids in collisions if len({after_rows[sid]['source_sha256'] for sid in ids}) > 1]
        return {'groups': len(collisions), 'files': sum(map(len, collisions)),
                'multiple_raw_contents_groups': len(distinct), 'multiple_raw_contents_files': sum(map(len, distinct))}

    return {'before_report_sha256': digest(before_raw), 'after_report_sha256': digest(after_raw),
            'before': before['summary'], 'after': after['summary'], 'reviewed_at': after['reviewed_at'],
            'combined_manifest_sha256': digest(manifest_raw), 'profile_sha256': after['profile_sha256'],
            'source_inventory_sha256': fingerprint(inventories['original']),
            'copied_inventory_sha256': fingerprint(inventories['copies']),
            'prepared_after_inventory_sha256': fingerprint(inventories['prepared_after']),
            'originals_checked': 4206, 'copied_xml_checked': 4200, 'prepared_payloads_checked': 4194,
            'fresh_baseline_complete_metadata_equal_to_reviewed_37ea595': 4194 if reviewed_dir is not None else None,
            'complete_metadata_objects_unchanged': 4126,
            'creator_and_notes_corrections': changed_metadata, 'policy_reference_changes': changed_payloads,
            'promoted_ids': changed_status, 'retained_new_cohort_access_holds': 90,
            'new_91_source_inventory_sha256': fingerprint([row for row in inventories['original'] if row['source_id'] in new_ids]),
            'exact_copy_groups': groups, 'exact_copy_groups_sha256': fingerprint(groups),
            'exact_source_title_collisions': title_diagnostics(titles),
            'normalized_source_title_collisions': title_diagnostics(normalized_titles),
            'protected_public_associations': protections, 'public_proposal_sha256': digest(public_raw),
            'public_protection_list_sha256': fingerprint(protections),
            'excluded_unrelated_record_id': 10042430, 'provider_requests': 0, 'provider_writes': 0,
            'scope': 'Complete offline source/copy/payload preparation; historical public associations are protection evidence, not current ownership, remote state, duplicate absence or release authority.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--reviewed-baseline', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.before, args.after, args.reviewed_baseline), indent=2, ensure_ascii=False))
