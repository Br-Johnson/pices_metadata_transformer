"""Aggregate frozen citationorg129 measurements without runtime imports.

The exact helper and four saved receipt hashes are pinned. Read public evidence
and create additive aggregate/check documents. Never classify sources, prepare
wires, import runtime/helper code or contact a provider. Retain original PR43
class paths and assessment times. Run only with all saved inputs available.
"""

import argparse
import copy
import hashlib
import html
import json
import re
from pathlib import Path

PRIOR = Path('docs/readiness/2026-10-06/modern_exxon203_validation.json')
PRIOR_SHA = '49460d21fefe455fc3036a198704ae0587d5b7f453b408b7cc679601abcf21b4'
PRIOR_ROOTS = [Path(f'/tmp/pices-exxon203-shard{i}-v1') for i in range(4)]
PRIOR_PROFILE_ROOT = Path('/workspace/pices-modern-exxon-pairs203-20261006/docs/readiness')
MAPPING = Path('docs/readiness/2026-10-06/modern_citation_organizations129.json')
MAPPING_SHA = '8ac4f141433dbbc58513ee968942ec23d2f484949b751fa01cba6bbcc393aee3'
SOURCE_REVIEW = Path('docs/readiness/2026-10-06/modern_citationorg129_source_review.json')
SOURCE_REVIEW_SHA = 'ceeaec8fdd29b3a56dceb700d2b3c47395ec54d0755c4bc3018a01f50d359168'
REVIEW = Path('docs/readiness/2026-10-06/modern_citationorg129_independent_review.json')
REVIEW_SHA = 'dc9033829412054b0aed2a5ec354e9133889736859a39d727aeba98e59ae88c3'
HELPER_SHA = '37582f5ede3aaacec169f8328ab956de6c6c9418c7e809f3d161b76ad16169ac'
RECEIPT_SHAS = ['7703d37bc0b776217f32fadbdf9df933b96a52659cb294aaf7b6019683fe3259', 'a12011e4916a9d67f6e0910e53f91f52789d43abacb06d7ca7991988fa723e64', '54967d5f2873b97f7e8162fdd6e5a810f12a795d978319a933ce31beb9ecfa92', 'e2127b8015f9310ecf815e4965910834ecca91faa85dffac24e2ce8b11ee8b58']
GUARD_SHA = '1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05'
ORIGINALS_SHA = '3430315763379ef81c393cca00eb776952df3ad3f66856ef4b15edd48e396013'
SCHEMAS = {
    'record-v6.0.0.json': 'bf029b1a74d851ff9c5474a9a528a0c4a0530026abf1698caf67f8efe6b95b88',
    'record-definitions-v2.0.0.json': '09060efec922d22bee3103e6b259e11a3fc0c1bdfa8eafc3df6335aba0199865',
    'definitions-v1.0.0.json': 'eeb99397c4c4712990222c969b8f8a22566eecf32818434f32b1982ed5eaab74',
    'definitions-v2.0.0.json': '319e15bd15d15d7947c3298bee7c2db30f1b6c1de6e9500b869631b0828e13d6',
}


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def digest(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink()
    return sha(path.read_bytes())


def pin(path, expected):
    assert digest(path) == expected, str(path)
    return json.loads(Path(path).read_bytes())


def inside(root, relative):
    assert isinstance(relative, str) and relative and not Path(relative).is_absolute()
    path = root / relative
    assert path.resolve() == path and path.is_relative_to(root) and not path.is_symlink()
    return path


def numeric(row):
    return int(row['source_id'][5:])


def nonruntime(evidence):
    return {key: value for key, value in evidence.items() if key != 'runtime_sha256'}


def source_bindings(repo):
    roots = ('scripts', 'tests', 'contracts', 'ci', '.github/workflows')
    paths = sorted(path for root in roots for path in (repo / root).rglob('*')
                   if path.is_file() and '__pycache__' not in path.parts)
    return {str(path.relative_to(repo)): digest(path) for path in paths}


def closed_class(value):
    assert value['production_reconciliation_status'] == 'pending'
    assert value['execution_status'] == 'class_execution_not_implemented'
    assert all(value[key] is False for key in ('upload_eligible', 'remote_verified', 'publication_approved'))


def retained3465(repo, prior):
    """Reconstruct PR43's actual saved preparations, never its source classifier."""
    singles, classes, frozen, profiles, old_rows = {}, {}, {}, {}, []
    original_manifest = None
    proofs = {row['record_target_id']: row for row in prior['rows']}
    assert len(proofs) == len(prior['rows']) == 203
    assert [row['index'] for row in prior['shards']] == list(range(4))

    def track(path, wanted):
        assert any(path.is_relative_to(root) for root in PRIOR_ROOTS)
        assert str(path) not in frozen or frozen[str(path)] == wanted
        assert digest(path) == wanted
        frozen[str(path)] = wanted
        return path

    for shard in prior['shards']:
        index, root = shard['index'], PRIOR_ROOTS[shard['index']]
        assert shard['root'] == str(root)
        receipt = json.loads(track(root / 'coverage.json', shard['receipt_sha256']).read_bytes())
        data = json.loads(track(root / 'wire_artifact_manifest.json', shard['artifact_manifest_sha256']).read_bytes())
        files = json.loads(track(root / 'retained_file_manifest.json', shard['retained_file_manifest_sha256']).read_bytes())
        if original_manifest is None:
            original_manifest = files
            for path, wanted in files['public_baseline_files'].items():
                assert path not in frozen or frozen[path] == wanted
                frozen[path] = wanted
            profiles.update(files['exact_public_profile_files'])
        else:
            assert files == original_manifest
        assert receipt['status'] == 'GUARDED_EXXON203_CLASS_SHARD_COVERAGE_PASS'
        assert receipt['helper_sha256'] == prior['helper_sha256']
        assert receipt['runtime_sha256'] == prior['runtime_sha256']
        assert receipt['source_bindings_unchanged'] and not receipt['unexpected_guard_events']
        assert not any(receipt['guard']['tests'].values())
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert receipt['prepared_root'] == str(root / 'prepared')
        track(root / 'prepared/classification.json', shard['classification_sha256'])
        assert [row['source_id'] for row in data['retained3262_rows']] == receipt['sharding']['assigned_retained_source_ids']
        assert [row['record_target_id'] for row in data['exxon_class_rows']] == receipt['sharding']['assigned_new_target_ids']
        assert len(data['retained3262_rows']) == shard['retained_source_count'] == (816, 816, 815, 815)[index]
        assert len(data['exxon_class_rows']) == shard['new_class_count'] == (51, 51, 51, 50)[index]
        old_rows.extend(data['retained3262_rows'])
        for row in data['retained3262_rows']:
            sid = row['source_id']
            packet_path = track(inside(root, row['current_preparation_path']), row['current_preparation_sha256'])
            packet = json.loads(packet_path.read_bytes())
            assert sid not in singles and packet['source_id'] == sid
            assert packet['binding'] == row['current_binding'] == sha(encode(packet['evidence']))
            assert packet['evidence']['runtime_sha256'] == prior['runtime_sha256']
            singles[sid] = {key: row[key] for key in ('source_id', 'source_sha256', 'prepared_root',
                            'prepared_input_path', 'wire_path', 'wire_sha256', 'raw_input_metadata_sha256')}
            singles[sid].update(preparation_path=str(packet_path), preparation_sha256=digest(packet_path),
                                binding=packet['binding'], evidence=packet['evidence'])
        for row in data['exxon_class_rows']:
            target = row['record_target_id']
            assert target not in classes and proofs[target] == row | {'shard_index': index}
            packet_path = track(inside(root, row['preparation_path']), row['preparation_sha256'])
            legacy_path = track(inside(root, row['legacy_target_path']), row['legacy_target_sha256'])
            wire_path = track(inside(root, row['wire_path']), row['wire_sha256'])
            packet, legacy = json.loads(packet_path.read_bytes()), json.loads(legacy_path.read_bytes())
            evidence = packet['evidence']
            assert packet['record_target_id'] == evidence['record_target_id'] == target
            assert packet['source_ids'] == evidence['source_ids'] == row['source_ids']
            assert packet['binding'] == row['binding'] == sha(encode(evidence))
            assert evidence['runtime_sha256'] == prior['runtime_sha256']
            assert evidence['wire_sha256'] == row['wire_sha256']
            assert evidence['legacy_target_sha256'] == sha(encode(legacy))
            assert evidence['reviewed_at'] == legacy['reviewed_at'] == receipt['assessment_time']
            closed_class(evidence)
            closed_class(legacy)
            members = []
            for item in row['members']:
                member = dict(item)
                for key, hash_key in (('prepared_input_path', 'prepared_input_sha256'),
                                      ('original_copy_path', 'source_sha256'), ('source_copy_path', 'source_sha256')):
                    member[key] = str(track(inside(root, item[key]), item[hash_key]))
                payload = json.loads(Path(member['prepared_input_path']).read_bytes())
                for reference in payload['artifact_policy'].values():
                    if not isinstance(reference, dict) or 'manifest_path' not in reference:
                        continue
                    path, wanted = Path(reference['manifest_path']), reference['manifest_sha256']
                    assert path.is_relative_to(PRIOR_PROFILE_ROOT)
                    assert digest(path) == wanted == digest(repo / 'docs/readiness' / path.relative_to(PRIOR_PROFILE_ROOT))
                    assert str(path) not in profiles or profiles[str(path)] == wanted
                    profiles[str(path)] = wanted
                members.append(member)
            classes[target] = {
                'record_target_id': target, 'source_ids': row['source_ids'], 'source_sha256': row['source_sha256'],
                'prepared_root': str(root / 'prepared'), 'reviewed_at': receipt['assessment_time'],
                'wire_path': str(wire_path), 'wire_sha256': row['wire_sha256'],
                'legacy_target_path': str(legacy_path), 'legacy_target_sha256': row['legacy_target_sha256'],
                'preparation_path': str(packet_path), 'preparation_sha256': row['preparation_sha256'],
                'binding': packet['binding'], 'members': members, 'evidence': evidence}
    assert len(singles) == 3262 and len(classes) == 203
    assert sha(encode(sorted(old_rows, key=numeric))) == prior['retained3262_comparison_rows_sha256']
    assert not set(singles) & {sid for row in classes.values() for sid in row['source_ids']}
    return singles, classes, frozen, profiles


def verify_new(repo, root, row, member, group, manifest, runtime):
    sid = member['source_id']
    assert row['source_id'] == sid and row['source_sha256'] == member['source_sha256']
    assert row['creator_cohort'] == member['creator_cohort'] and row['policy'] == manifest['policy']
    assert row['prepare_calls'] == 2 and row['fresh_source_assessment_true'] is True
    input_path = inside(root, row['prepared_input_path'])
    assert input_path == root / 'prepared/data/zenodo_json' / (sid + '.json')
    payload = pin(input_path, row['prepared_input_sha256'])
    packet = pin(inside(root, row['preparation_path']), row['preparation_sha256'])
    wire_path = inside(root, row['wire_path'])
    wire = pin(wire_path, row['wire_sha256'])
    original = (repo / 'FGDC' / (sid + '.xml')).read_bytes()
    copy_path = inside(root, row['original_copy_path'])
    assert copy_path == root / 'prepared/data/original_fgdc' / (sid + '.xml')
    assert original == copy_path.read_bytes() == (root / 'sources' / (sid + '.xml')).read_bytes()
    assert sha(original) == row['source_sha256']
    assert row['xml_bytes'] == len(original) and row['body_bytes'] == wire_path.stat().st_size
    assert row['xml_bytes'] <= 1024 * 1024 and row['body_bytes'] <= 1024 * 1024
    assert packet['source_id'] == sid and packet['complete_raw_input_metadata'] == payload['metadata']
    assert all(packet[key] is True for key in ('complete_legacy_metadata_preserved', 'unchanged_repeat_equal',
                                              'fresh_source_assessment_true'))
    metadata = packet['complete_legacy_metadata']
    block = wire['metadata']['additional_descriptions'][0]['description']
    assert block.endswith('</pre>') and json.loads(html.unescape(block.split('<pre>', 1)[1][:-6])) == metadata
    assert metadata['creators'] == payload['metadata']['creators'] == group['creators']
    assert wire['metadata']['creators'] == group['modern_creators']
    assert all(wire['metadata'][key] == metadata[key] for key in ('title', 'description', 'publication_date'))
    assert wire['metadata']['subjects'] == [{'subject': value} for value in metadata.get('keywords', [])]
    assert metadata['access_right'] == 'restricted' and metadata['license'] == ''
    assert wire['access'] == {'record': 'public', 'files': 'restricted'} and wire['files'] == {'enabled': True}
    assert wire['metadata']['resource_type'] == {'id': 'other'} and wire['metadata']['publisher'] == 'Zenodo'
    assert 'rights' not in wire['metadata'] and 'license' not in wire['metadata']
    assert row['raw_input_metadata_sha256'] == sha(encode(payload['metadata']))
    policy, classification = payload['artifact_policy'], dict(payload['content_classification'])
    assert policy['schema_version'] == 1 and policy['object_kind'] == 'original_fgdc_xml'
    assert policy['source_sha256'] == sha(original) and policy['resource_type'] == 'other'
    assert policy['creator_interpretation']['manifest_sha256'] == manifest['creator_profile_sha256']
    assert classification.get('content_status') in (None, 'metadata_only')
    classification['content_status'] = 'metadata_only'
    assert classification['inventory_complete'] is True and len(classification['files']) == 1
    assert classification['files'][0]['name'] == sid + '.xml'
    assert classification['files'][0]['role'] == 'descriptive_metadata'
    artifact = {'schema_version': 1, 'object_kind': 'original_fgdc_xml', 'source_id': sid,
                'policy_sha256': fingerprint(policy), 'classification_sha256': fingerprint(classification),
                'files': [{'name': sid + '.xml', 'size': len(original), 'sha256': sha(original),
                           'md5': hashlib.md5(original, usedforsecurity=False).hexdigest(), 'role': 'descriptive_metadata'}]}
    artifact['sha256'] = fingerprint(artifact)
    expected = {'schema_version': 7, 'policy': manifest['policy'], 'mapping_manifest_sha256': MAPPING_SHA,
                'creator_cohort': member['creator_cohort'], 'source_id': sid, 'source_sha256': sha(original),
                'prepared_input_sha256': row['prepared_input_sha256'], 'legacy_metadata_sha256': sha(encode(metadata)),
                'wire_sha256': row['wire_sha256'], 'artifact_contract': artifact,
                'creator_profile_sha256': manifest['creator_profile_sha256'],
                'source_plan_sha256': manifest['source_plan_sha256'], 'runtime_sha256': runtime, 'schema_sha256': SCHEMAS}
    assert packet['evidence'] == expected
    assert packet['binding'] == row['binding'] == sha(encode(expected))
    assert row['normalized_legacy_metadata_sha256'] == expected['legacy_metadata_sha256']


def verify_retained_class(repo, root, row, saved, runtime):
    assert all(row[key] == value for key, value in saved.items() if key != 'evidence')
    packet = pin(inside(root, row['current_preparation_path']), row['current_preparation_sha256'])
    assert packet['record_target_id'] == row['record_target_id'] and packet['source_ids'] == row['source_ids']
    assert packet['binding'] == row['current_binding'] == sha(encode(packet['evidence']))
    assert packet['evidence']['runtime_sha256'] == runtime
    assert nonruntime(packet['evidence']) == nonruntime(saved['evidence'])
    assert row['nonruntime_evidence_sha256'] == sha(encode(nonruntime(packet['evidence'])))
    assert row['wire_legacy_and_nonruntime_evidence_equal'] is True and row['current_prepare_calls'] == 1
    assert digest(Path(row['wire_path'])) == row['wire_sha256'] == packet['evidence']['wire_sha256']
    legacy = pin(Path(row['legacy_target_path']), row['legacy_target_sha256'])
    assert sha(encode(legacy)) == packet['evidence']['legacy_target_sha256']
    assert legacy['reviewed_at'] == row['reviewed_at'] == packet['evidence']['reviewed_at']
    closed_class(legacy)
    closed_class(packet['evidence'])
    assert len(row['members']) == 2 and [m['source_id'] for m in row['members']] == row['source_ids']
    for member in row['members']:
        assert digest(Path(member['prepared_input_path'])) == member['prepared_input_sha256']
        raw = (repo / 'FGDC' / member['name']).read_bytes()
        assert raw == Path(member['original_copy_path']).read_bytes() == Path(member['source_copy_path']).read_bytes()
        assert sha(raw) == member['source_sha256'] == row['source_sha256']


def main():
    if not __debug__:
        raise RuntimeError('Assertions must remain enabled')
    if not all(re.fullmatch('[0-9a-f]{64}', value) for value in
               [MAPPING_SHA, SOURCE_REVIEW_SHA, REVIEW_SHA, HELPER_SHA, *RECEIPT_SHAS]):
        raise RuntimeError('All mapping, source review, independent review, helper and four receipt SHA256 pins are required')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--roots', type=Path, nargs=4,
                        default=[Path(f'/tmp/pices-citationorg129-shard{i}-v1') for i in range(4)])
    parser.add_argument('--helper', type=Path, default=Path('docs/readiness/2026-10-06/measure_modern_citationorg129_coverage.py'))
    parser.add_argument('--focused-log', type=Path)
    args = parser.parse_args()
    repo, roots = args.repo.resolve(), [path.resolve() for path in args.roots]
    assert len(set(roots)) == 4 and all(root.is_relative_to('/tmp') and root != Path('/tmp') for root in roots)
    assert all(not a.is_relative_to(b) for a in roots for b in roots if a != b)
    assert all(not a.is_relative_to(b) and not b.is_relative_to(a) for a in roots for b in PRIOR_ROOTS)
    assert digest(args.helper.resolve()) == HELPER_SHA
    assert digest(repo / 'ci/run_offline_tests.py') == GUARD_SHA
    prior, manifest = pin(repo / PRIOR, PRIOR_SHA), pin(repo / MAPPING, MAPPING_SHA)
    review, source_review = pin(repo / REVIEW, REVIEW_SHA), pin(repo / SOURCE_REVIEW, SOURCE_REVIEW_SHA)
    assert prior['status'] == 'GUARDED_EXXON203_CLASS_AGGREGATE_PASS' and prior['all_shards_complete']
    assert prior['coverage']['total_wire_prepared_targets'] == 3465
    assert manifest['schema_version'] == 1 and manifest['kind'] == 'modern-citation-organizations129-v1'
    assert manifest['member_count'] == 129 and manifest['group_count'] == len(manifest['groups']) == 53
    assert manifest['source_review_sha256'] == SOURCE_REVIEW_SHA and manifest['independent_review_sha256'] == REVIEW_SHA
    assert review['verdict'] == 'APPROVE_EXACT_FINITE_WIRE_PROJECTION_WITH_PRESERVATION_CONDITIONS'
    selected = {row['source_id']: row for group in manifest['groups'] for row in group['members']}
    groups = {row['source_id']: group for group in manifest['groups'] for row in group['members']}
    assert len(selected) == sum(len(group['members']) for group in manifest['groups']) == 129
    members = sorted([{'source_id': sid, 'source_sha256': row['source_sha256']} for sid, row in selected.items()], key=numeric)
    assert members == review['approved_members'] == source_review['members']
    assert sha(encode(members)) == review['approved_membership_sha256']
    singles, classes, frozen, profiles = retained3465(repo, prior)
    assert not set(selected) & (set(singles) | {sid for row in classes.values() for sid in row['source_ids']})
    originals = {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert len(originals) == 4206 and sha(encode(originals)) == ORIGINALS_SHA
    assert all(originals[sid + '.xml'] == row['source_sha256'] for sid, row in selected.items())
    before = source_bindings(repo)
    runtime = sha(encode({path.name: digest(path) for path in sorted((repo / 'scripts').glob('*.py'))}))
    for name, wanted in SCHEMAS.items():
        assert digest(repo / 'contracts/schemas/zenodo-modern' / name) == wanted
    rows, old_rows, class_rows, receipts, shards = [], [], [], [], []
    for index, root in enumerate(roots):
        receipt = pin(root / 'coverage.json', RECEIPT_SHAS[index])
        receipts.append(receipt)
        assert receipt['status'] == 'GUARDED_CITATIONORG129_SHARD_COVERAGE_PASS'
        assert receipt['helper_sha256'] == HELPER_SHA and receipt['runtime_sha256'] == runtime
        assert receipt['guard_sha256'] == GUARD_SHA and receipt['prior3465_validation_sha256'] == PRIOR_SHA
        assert receipt['mapping_manifest_sha256'] == MAPPING_SHA
        assert receipt['source_review_sha256'] == SOURCE_REVIEW_SHA and receipt['independent_review_sha256'] == REVIEW_SHA
        assert receipt['source_bindings_before'] == before and receipt['original_hashes'] == originals
        assert receipt['original_hashes_sha256'] == ORIGINALS_SHA and receipt['original_files_verified_before_and_after'] == 4206
        assert receipt['source_bindings_unchanged'] and receipt['environment_cleared_dummy_credentials_only']
        assert receipt['retained_paths_and_bytes_unchanged']
        assert receipt['all3465_retained_file_hashes_verified_before_and_after']
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert not receipt['unexpected_guard_events'] and not any(receipt['guard']['tests'].values())
        assert receipt['guard']['bootstrap'] == {'network': 4, 'private_reads': 1, 'processes': 1, 'writes': 1}
        assignment = receipt['sharding']
        assert assignment['index'] == index and assignment['count'] == 4 and assignment['all_shards_complete_claimed'] is False
        new_ids = sorted(selected, key=lambda sid: int(sid[5:]))[index::4]
        new_count = (33, 32, 32, 32)[index]
        old_ids = sorted(singles, key=lambda sid: int(sid[5:]))[index::4]
        class_ids = sorted(classes)[index::4]
        assert assignment['assigned_new_source_ids'] == new_ids
        assert assignment['assigned_retained_source_ids'] == old_ids
        assert assignment['assigned_retained_class_ids'] == class_ids
        assert assignment['actual_new_preparations'] == len(new_ids) == new_count
        assert assignment['actual_new_prepare_calls'] == (66, 64, 64, 64)[index]
        assert assignment['actual_retained_comparisons'] == assignment['actual_retained_prepare_calls'] == len(old_ids)
        assert len(old_ids) == (816, 816, 815, 815)[index]
        assert assignment['actual_retained_class_comparisons'] == assignment['actual_retained_class_prepare_calls'] == len(class_ids)
        assert len(class_ids) == (51, 51, 51, 50)[index]
        assert receipt['prepared_root'] == str(root / 'prepared')
        data = pin(inside(root, receipt['wire_artifact_manifest_path']), receipt['wire_artifact_manifest_sha256'])
        files = pin(inside(root, receipt['retained_file_manifest_path']), receipt['retained_file_manifest_sha256'])
        assert files == {'public_baseline_files': frozen, 'exact_public_profile_files': profiles}
        classification = pin(root / 'prepared/classification.json', receipt['classification_sha256'])
        assert classification['summary']['source_status_counts'] == {'supported': new_count, 'held': 0, 'failed': 0}
        assert len(classification['records']) == new_count and {row['source_id'] for row in classification['records']} == set(new_ids)
        assert all(row['source_status'] == 'supported' and row['remote_verified'] is False
                   and row['publication_approved'] is False for row in classification['records'])
        assert [row['source_id'] for row in data['citationorg_rows']] == new_ids
        assert [row['source_id'] for row in data['retained3262_rows']] == old_ids
        assert [row['record_target_id'] for row in data['retained203_class_rows']] == class_ids
        for row in data['citationorg_rows']:
            verify_new(repo, root, row, selected[row['source_id']], groups[row['source_id']], manifest, runtime)
            rows.append(row | {'shard_index': index})
        for row in data['retained3262_rows']:
            saved = singles[row['source_id']]
            assert all(row[key] == value for key, value in saved.items() if key != 'evidence')
            packet = pin(inside(root, row['current_preparation_path']), row['current_preparation_sha256'])
            assert packet['source_id'] == row['source_id']
            assert packet['binding'] == row['current_binding'] == sha(encode(packet['evidence']))
            assert packet['evidence']['runtime_sha256'] == runtime
            assert nonruntime(packet['evidence']) == nonruntime(saved['evidence'])
            assert row['nonruntime_evidence_sha256'] == sha(encode(nonruntime(packet['evidence'])))
            assert digest(Path(row['wire_path'])) == row['wire_sha256'] == packet['evidence']['wire_sha256']
            assert digest(Path(row['prepared_input_path'])) == packet['evidence']['prepared_input_sha256']
            assert originals[row['source_id'] + '.xml'] == row['source_sha256'] and row['wire_and_nonruntime_evidence_equal']
            old_rows.append(row)
        for row in data['retained203_class_rows']:
            verify_retained_class(repo, root, row, classes[row['record_target_id']], runtime)
            class_rows.append(row)
        for relative, wanted in receipt['policy_input_bindings'].items():
            assert digest(inside(repo, relative)) == wanted
        shards.append({'index': index, 'root': str(root), 'receipt_sha256': RECEIPT_SHAS[index],
                       'artifact_manifest_sha256': receipt['wire_artifact_manifest_sha256'],
                       'retained_file_manifest_sha256': receipt['retained_file_manifest_sha256'],
                       'classification_sha256': receipt['classification_sha256'], 'new_source_count': new_count,
                       'retained_source_count': len(old_ids), 'retained_class_count': len(class_ids),
                       'guard': receipt['guard'], 'elapsed_seconds': receipt['elapsed_seconds']})
    assert len(rows) == len({row['source_id'] for row in rows}) == 129
    assert len(old_rows) == len({row['source_id'] for row in old_rows}) == 3262
    assert len(class_rows) == len({row['record_target_id'] for row in class_rows}) == 203
    for field in ('source_bindings_before', 'runtime_sha256', 'helper_sha256', 'policy_input_bindings',
                  'original_hashes', 'original_hashes_sha256'):
        assert all(receipt[field] == receipts[0][field] for receipt in receipts)
    for path, wanted in (frozen | profiles).items():
        assert digest(Path(path)) == wanted
    assert before == source_bindings(repo)
    assert originals == {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    remaining = copy.deepcopy(prior['remaining'])
    removed = []
    for group in remaining['singleton_categories'].values():
        removed.extend(row['source_id'] for row in group['members'] if row['source_id'] in selected)
        group['members'] = [row for row in group['members'] if row['source_id'] not in selected]
        group['count'] = len(group['members'])
        group['membership_sha256'] = sha(encode(group['members']))
    assert len(removed) == 129 and set(removed) == set(selected)
    assert remaining['singleton_categories']['creator426']['count'] == 160
    assert remaining['pairs'] == prior['remaining']['pairs'] and len(remaining['pairs']) == 25
    remaining['supported_singletons'] = sum(group['count'] for group in remaining['singleton_categories'].values())
    assert remaining['supported_singletons'] == 314 and remaining['paired_targets'] == 25
    remaining['supported_targets_outside_modern_mapping'] = 339
    result = {
        'schema_version': 1, 'status': 'GUARDED_CITATIONORG129_AGGREGATE_PASS', 'all_shards_complete': True,
        'runtime_sha256': runtime, 'helper_sha256': HELPER_SHA, 'aggregation_script_sha256': digest(Path(__file__).resolve()),
        'prior3465_validation_sha256': PRIOR_SHA, 'mapping_manifest_sha256': MAPPING_SHA,
        'source_review_sha256': SOURCE_REVIEW_SHA, 'independent_review_sha256': REVIEW_SHA,
        'source_tree_sha256': sha(json.dumps(before, sort_keys=True).encode()),
        'actual_checkout_revisions': sorted({receipt['actual_checkout_revision'] for receipt in receipts}),
        'coverage': {'prior_retained_singletons': 3262, 'prior_retained_class_targets': 203,
                     'new_citation_organization_singletons': 129, 'total_singletons': 3391,
                     'total_class_targets': 203, 'total_wire_prepared_targets': 3594,
                     'total_represented_originals': 3797, 'fresh_new_prepare_calls': 258,
                     'retained_input_prepare_comparisons': 3262, 'retained_class_prepare_comparisons': 203,
                     'new_class_execution_enabled': False},
        'rows': sorted(rows, key=numeric), 'shards': shards,
        'retained3262_comparison_rows_sha256': sha(encode(sorted(old_rows, key=numeric))),
        'retained203_class_comparison_rows_sha256': sha(encode(sorted(class_rows, key=lambda row: row['record_target_id']))),
        'all_saved_digests_reverified': True, 'retained_public_file_count': len(frozen), 'retained_profile_file_count': len(profiles),
        'original_hashes_sha256': ORIGINALS_SHA, 'original_files_verified_before_and_after': 4206,
        'source_bindings_unchanged': True, 'source_status_unchanged': prior['source_status_unchanged'],
        'alias_source_holds_preserved': True, 'remaining': remaining, 'provider_requests': 0, 'provider_mutations': 0,
        'scope': '129 fresh finite citation-organization singleton preparations plus unchanged 3262 retained singleton '
                 'wires/nonruntime evidence and203 class wires/full legacy targets/nonruntime evidence at exact original '
                 'paths and assessment times. Historical stale raw inputs are not baselines for new129 sources. No class '
                 'execution/adoption, source promotion, remote identity, duplicate absence, grant, PICES inclusion, QA '
                 'approval or release is established.'}
    focused = None
    if args.focused_log is not None:
        marker = 'PICES_OFFLINE_CI_RESULT '
        lines = [line.split(marker, 1)[1] for line in args.focused_log.read_text().splitlines() if marker in line]
        assert len(lines) == 1
        focused = json.loads(lines[0])
        assert focused['successful'] and focused['failures'] == focused['errors'] == 0 and focused['tests_run'] > 0
        assert focused['source_bindings_unchanged'] and focused['environment_cleared_dummy_credentials_only']
        assert not focused['unexpected_guard_call_sites'] and not any(focused['guard_blocks']['tests'].values())
        assert focused['source_tree_sha256'] == result['source_tree_sha256']
        result['focused_result_sha256'] = sha(encode(focused))
        result['focused_log_sha256'] = digest(args.focused_log.resolve())
    docs = repo / 'docs/readiness/2026-10-06'
    output, checks = docs / 'modern_citationorg129_validation.json', docs / 'modern_citationorg129_focused_checks.json'
    assert not output.exists() and (focused is None or not checks.exists())
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    if focused is not None:
        with checks.open('x') as stream:
            json.dump(focused, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps({'path': str(output), 'sha256': digest(output), 'coverage': result['coverage'],
                      'remaining': 339, 'focused_result_copied': focused is not None}))


if __name__ == '__main__':
    main()
