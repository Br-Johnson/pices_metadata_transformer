"""Guarded finite reviewed194 measurement at explicit working-tree bindings.

Run only after root freezes code, tests, exact pins and independent helper review.
All194 are freshly classified then prepared twice. Prior3391 singletons and203
pairs are each prepared once from exact historical inputs/times; retain complete
wire, legacy metadata and nonruntime evidence. No earlier helper is imported.
"""

import argparse
import hashlib
import html
import json
import os
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

# This block is duplicated verbatim in measurement and aggregate drafts.
# It reads saved public receipts only; it imports no runtime or earlier helper.
PRIOR = Path('docs/readiness/2026-10-06/modern_citationorg129_validation.json')
PRIOR_SHA = '07965171ce10dee00d7645f9567e01e10d620e8697696dbaac6e93629244c4bb'
PRIOR_HELPER_SHA = '37582f5ede3aaacec169f8328ab956de6c6c9418c7e809f3d161b76ad16169ac'
PRIOR_RUNTIME = '62eeaad6183950bae245937f79a7d4e16df546a6635d9ea4dfbb7c4c2bf5902d'
PRIOR_ROOTS = tuple(Path(f'/tmp/pices-citationorg129-shard{i}-v1') for i in range(4))
PRIOR_RECEIPTS = (
    '7703d37bc0b776217f32fadbdf9df933b96a52659cb294aaf7b6019683fe3259',
    'a12011e4916a9d67f6e0910e53f91f52789d43abacb06d7ca7991988fa723e64',
    '54967d5f2873b97f7e8162fdd6e5a810f12a795d978319a933ce31beb9ecfa92',
    'e2127b8015f9310ecf815e4965910834ecca91faa85dffac24e2ce8b11ee8b58')
GUARD_SHA = '1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05'
ORIGINALS_SHA = '3430315763379ef81c393cca00eb776952df3ad3f66856ef4b15edd48e396013'
MEMBERSHIP_SHA = '04dd181e8eeb31fe144bdc174809e874ffc00229e94cb78f9872aa342332ef48'
SOURCE_REVIEW = Path('docs/readiness/2026-10-06/modern_reviewed_creators194_source.json')
SOURCE_REVIEW_SHA = '1dbb3af3945a0993e705e56a94b307cb02ca444451a98ef8e36ade366eddaad1'
INDEPENDENT_REVIEW = Path('docs/readiness/2026-10-06/modern_reviewed_creators194_review.json')
INDEPENDENT_REVIEW_SHA = '20c585d143cc0a295bdbbce54b2e3fa5bace5846802534b2f7bf40bb3f04b271'
POLICY = 'modern-xml-reviewed-creators194-v1'
EVIDENCE_SCHEMA = 8
ASSESSMENT_TIME = '2026-10-05T18:00:00+00:00'
NEW_COUNTS, OLD_COUNTS, CLASS_COUNTS = (49, 49, 48, 48), (848, 848, 848, 847), (51, 51, 51, 50)
DRAFT_ONLY = False
# Required after root freezes integration; no placeholder is a valid SHA256.
MAPPING = Path('docs/readiness/2026-10-06/modern_reviewed_creators194.json')
MAPPING_SHA = 'c7d0b522bf7e9a9c990b6cbdf93797280ff1e57979e6bd133186905c4deec6c3'
EXPECTED_RUNTIME_SHA = '6cc86a1740fcd93e65d42e21b1c199c160974c607be54db71f43d3e25466349e'
EXPECTED_SOURCE_TEST_SHA = '0c85c0b50742897f13122e5ebc7b5987884356b940e188cd41452386a191f84e'
EXPECTED_SOURCE_TEST_COUNT = 187
# This is the base HEAD beneath the frozen staged working tree, not a new code commit.
EXPECTED_REVISION = '6deff6bbc9c739dbb09192412c0548863007cdea'
# Independent helper review freezes the helper in a separate CLI argument.
PROFILE_RELATIVES = {
    '2026-10-02/contact_source_interpretation.json',
    '2026-10-02/contributor_source_interpretation.json',
    '2026-10-02/rehosting_authority.json',
    '2026-10-02/exxon_citation_interpretation.json',
    '2026-10-03/dfo_staff_citation_interpretation.json',
    '2026-10-03/historical_dataset_linkage_21.json',
    '2026-10-03/source_scope_reconciliation_904.json',
    '2026-10-04/finite_source_resource_access_655.json',
    '2026-10-04/source_citation_credits_426.json',
    '2026-10-04/source_display_titles_42.json',
}


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink()
    return sha(path.read_bytes())


def pin(path, wanted):
    assert digest(path) == wanted, str(path)
    return json.loads(Path(path).read_bytes())


def inside(root, relative):
    assert isinstance(relative, str) and relative and not Path(relative).is_absolute()
    path = root / relative
    assert path.resolve() == path and path.is_relative_to(root) and not path.is_symlink()
    return path


def source_order(sid):
    return int(sid[5:])


def nonruntime(evidence):
    return {key: value for key, value in evidence.items() if key != 'runtime_sha256'}


def source_tree_bindings(repo):
    roots = ('scripts', 'tests', 'contracts', 'ci', '.github/workflows')
    paths = sorted(path for root in roots for path in (repo / root).rglob('*')
                   if path.is_file() and '__pycache__' not in path.parts)
    return {str(path.relative_to(repo)): digest(path) for path in paths}


def bindings_sha(bindings):
    # This is the CI source-tree recipe, deliberately not compact encode().
    return sha(json.dumps(bindings, sort_keys=True).encode())


def source_node(element, outer=True):
    return {'tag': element.tag, 'attributes': dict(element.attrib), 'text': element.text,
            'tail': None if outer else element.tail,
            'children': [source_node(child, False) for child in element]}


def closed_class(value):
    assert value['production_reconciliation_status'] == 'pending'
    assert value['execution_status'] == 'class_execution_not_implemented'
    assert all(value[key] is False for key in ('upload_eligible', 'remote_verified', 'publication_approved'))


def preserved_metadata(wire):
    block = wire['metadata']['additional_descriptions'][0]['description']
    assert block.startswith('<p>') and '<pre>' in block and block.endswith('</pre>')
    return json.loads(html.unescape(block.split('<pre>', 1)[1][:-6]))


def check_wire(wire, metadata, modern_creators=None):
    assert preserved_metadata(wire) == metadata
    for key in ('title', 'description', 'publication_date'):
        assert wire['metadata'][key] == metadata[key]
    assert wire['metadata']['subjects'] == [{'subject': word} for word in metadata.get('keywords', [])]
    assert metadata['access_right'] == 'restricted' and metadata['license'] == ''
    assert wire['metadata']['publisher'] == 'Zenodo'
    assert wire['metadata']['resource_type'] == {'id': 'other'}
    assert wire['access'] == {'record': 'public', 'files': 'restricted'}
    assert wire['files'] == {'enabled': True}
    assert 'rights' not in wire['metadata'] and 'license' not in wire['metadata']
    if modern_creators is not None:
        assert wire['metadata']['creators'] == modern_creators


def retained3594(repo):
    """Load latest saved129 bindings and original input roots; never prepare."""
    prior = pin(repo / PRIOR, PRIOR_SHA)
    assert prior['status'] == 'GUARDED_CITATIONORG129_AGGREGATE_PASS' and prior['all_shards_complete']
    assert prior['helper_sha256'] == PRIOR_HELPER_SHA and prior['runtime_sha256'] == PRIOR_RUNTIME
    assert prior['coverage']['total_wire_prepared_targets'] == 3594
    assert prior['coverage']['total_singletons'] == 3391 and prior['coverage']['total_class_targets'] == 203
    assert prior['original_hashes_sha256'] == ORIGINALS_SHA
    proof129 = {row['source_id']: row for row in prior['rows']}
    assert len(proof129) == len(prior['rows']) == 129
    frozen, profiles, singles, classes, receipts = {}, {}, {}, {}, []
    previous_file_manifest = None
    old_rows, class_rows = [], []

    def track(path, wanted, newly_saved=False):
        path = Path(path)
        if newly_saved:
            assert any(path.is_relative_to(root) for root in PRIOR_ROOTS)
        else:
            # Existing baseline paths are permitted only by exact inherited pins.
            assert str(path) in frozen and frozen[str(path)] == wanted
        assert str(path) not in frozen or frozen[str(path)] == wanted
        assert digest(path) == wanted
        frozen[str(path)] = wanted
        return path

    def register_profiles(payload, old_paths_only):
        for value in payload['artifact_policy'].values():
            if not isinstance(value, dict) or 'manifest_path' not in value:
                continue
            public, wanted = Path(value['manifest_path']), value['manifest_sha256']
            assert public.is_absolute() and not public.is_symlink() and public.resolve() == public
            if old_paths_only:
                assert str(public) in profiles and profiles[str(public)] == wanted
            else:
                # Newly retained129 inputs reference the frozen129 checkout only.
                prefix = Path('/workspace/pices-modern-citationorg129-20261006/docs/readiness')
                assert public.is_relative_to(prefix)
                relative = public.relative_to(prefix)
                assert str(relative) in PROFILE_RELATIVES
                assert digest(repo / 'docs/readiness' / relative) == wanted
            assert digest(public) == wanted
            assert str(public) not in profiles or profiles[str(public)] == wanted
            profiles[str(public)] = wanted

    for index, shard in enumerate(prior['shards']):
        root = PRIOR_ROOTS[index]
        assert shard['index'] == index and shard['root'] == str(root)
        assert shard['receipt_sha256'] == PRIOR_RECEIPTS[index]
        receipt = json.loads(track(root / 'coverage.json', PRIOR_RECEIPTS[index], True).read_bytes())
        data = json.loads(track(root / 'wire_artifact_manifest.json', shard['artifact_manifest_sha256'], True).read_bytes())
        files = json.loads(track(root / 'retained_file_manifest.json', shard['retained_file_manifest_sha256'], True).read_bytes())
        if previous_file_manifest is None:
            previous_file_manifest = files
            for path, wanted in files['public_baseline_files'].items():
                assert path not in frozen or frozen[path] == wanted
                frozen[path] = wanted
            profiles.update(files['exact_public_profile_files'])
        else:
            assert files == previous_file_manifest
        assert receipt['status'] == 'GUARDED_CITATIONORG129_SHARD_COVERAGE_PASS'
        assert receipt['guard_sha256'] == GUARD_SHA
        assert receipt['environment_cleared_dummy_credentials_only']
        assert receipt['guard']['bootstrap'] == {'network': 4, 'private_reads': 1, 'processes': 1, 'writes': 1}
        assert receipt['wire_artifact_manifest_sha256'] == shard['artifact_manifest_sha256']
        assert receipt['retained_file_manifest_sha256'] == shard['retained_file_manifest_sha256']
        assert receipt['classification_sha256'] == shard['classification_sha256']
        assert receipt['runtime_sha256'] == PRIOR_RUNTIME and receipt['helper_sha256'] == PRIOR_HELPER_SHA
        assert receipt['original_hashes_sha256'] == ORIGINALS_SHA and receipt['original_files_verified_before_and_after'] == 4206
        assert receipt['source_bindings_unchanged'] and receipt['retained_paths_and_bytes_unchanged']
        assert receipt['all3465_retained_file_hashes_verified_before_and_after']
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert not receipt['unexpected_guard_events'] and not any(receipt['guard']['tests'].values())
        assert receipt['prepared_root'] == str(root / 'prepared')
        assert receipt['assessment_time'] == ASSESSMENT_TIME
        track(root / 'prepared/classification.json', shard['classification_sha256'], True)
        assert [r['source_id'] for r in data['citationorg_rows']] == receipt['sharding']['assigned_new_source_ids']
        assert [r['source_id'] for r in data['retained3262_rows']] == receipt['sharding']['assigned_retained_source_ids']
        assert [r['record_target_id'] for r in data['retained203_class_rows']] == receipt['sharding']['assigned_retained_class_ids']
        assert len(data['citationorg_rows']) == (33, 32, 32, 32)[index]
        assert len(data['retained3262_rows']) == (816, 816, 815, 815)[index]
        assert len(data['retained203_class_rows']) == CLASS_COUNTS[index]
        receipts.append(receipt)
        for row in data['retained3262_rows']:
            sid = row['source_id']
            packet_path = track(inside(root, row['current_preparation_path']), row['current_preparation_sha256'], True)
            packet = json.loads(packet_path.read_bytes())
            assert sid not in singles and packet['source_id'] == sid
            assert packet['binding'] == row['current_binding'] == sha(encode(packet['evidence']))
            assert packet['evidence']['runtime_sha256'] == PRIOR_RUNTIME
            assert row['wire_and_nonruntime_evidence_equal']
            assert sha(encode(nonruntime(packet['evidence']))) == row['nonruntime_evidence_sha256']
            input_path = track(Path(row['prepared_input_path']), packet['evidence']['prepared_input_sha256'])
            payload = json.loads(input_path.read_bytes())
            assert sha(encode(payload['metadata'])) == row['raw_input_metadata_sha256']
            wire_path = track(Path(row['wire_path']), row['wire_sha256'])
            assert row['wire_sha256'] == packet['evidence']['wire_sha256']
            register_profiles(payload, True)
            old_rows.append(row)
            singles[sid] = {key: row[key] for key in ('source_id', 'source_sha256', 'prepared_root',
                            'prepared_input_path', 'wire_path', 'wire_sha256', 'raw_input_metadata_sha256')}
            singles[sid].update(prepared_input_sha256=packet['evidence']['prepared_input_sha256'],
                preparation_path=str(packet_path), preparation_sha256=row['current_preparation_sha256'],
                evidence=packet['evidence'], binding=packet['binding'])
        for row in data['citationorg_rows']:
            sid = row['source_id']
            assert sid not in singles and proof129[sid] == row | {'shard_index': index}
            packet_path = track(inside(root, row['preparation_path']), row['preparation_sha256'], True)
            packet = json.loads(packet_path.read_bytes())
            input_path = track(inside(root, row['prepared_input_path']), row['prepared_input_sha256'], True)
            payload = json.loads(input_path.read_bytes())
            wire_path = track(inside(root, row['wire_path']), row['wire_sha256'], True)
            wire = json.loads(wire_path.read_bytes())
            copy_path = track(inside(root, row['original_copy_path']), row['source_sha256'], True)
            source_path = track(root / 'sources' / (sid + '.xml'), row['source_sha256'], True)
            assert packet['source_id'] == sid and packet['binding'] == row['binding'] == sha(encode(packet['evidence']))
            assert packet['evidence']['runtime_sha256'] == PRIOR_RUNTIME
            assert packet['evidence']['prepared_input_sha256'] == row['prepared_input_sha256']
            assert packet['evidence']['wire_sha256'] == row['wire_sha256']
            assert packet['complete_raw_input_metadata'] == payload['metadata']
            assert row['prepare_calls'] == 2 and packet['unchanged_repeat_equal']
            assert row['fresh_source_assessment_true'] and packet['complete_legacy_metadata_preserved']
            assert sha(encode(payload['metadata'])) == row['raw_input_metadata_sha256']
            assert sha(encode(packet['complete_legacy_metadata'])) == row['normalized_legacy_metadata_sha256']
            assert row['normalized_legacy_metadata_sha256'] == packet['evidence']['legacy_metadata_sha256']
            assert copy_path.read_bytes() == source_path.read_bytes() == (repo / 'FGDC' / (sid + '.xml')).read_bytes()
            check_wire(wire, packet['complete_legacy_metadata'])
            register_profiles(payload, False)
            singles[sid] = {'source_id': sid, 'source_sha256': row['source_sha256'],
                'prepared_root': str(root / 'prepared'), 'prepared_input_path': str(input_path),
                'prepared_input_sha256': row['prepared_input_sha256'], 'wire_path': str(wire_path),
                'wire_sha256': row['wire_sha256'], 'raw_input_metadata_sha256': row['raw_input_metadata_sha256'],
                'preparation_path': str(packet_path), 'preparation_sha256': row['preparation_sha256'],
                'evidence': packet['evidence'], 'binding': packet['binding']}
        for row in data['retained203_class_rows']:
            tid = row['record_target_id']
            assert tid not in classes
            packet_path = track(inside(root, row['current_preparation_path']), row['current_preparation_sha256'], True)
            packet = json.loads(packet_path.read_bytes())
            assert packet['record_target_id'] == tid and packet['source_ids'] == row['source_ids']
            assert packet['binding'] == row['current_binding'] == sha(encode(packet['evidence']))
            assert packet['evidence']['runtime_sha256'] == PRIOR_RUNTIME
            assert row['wire_legacy_and_nonruntime_evidence_equal'] and row['current_prepare_calls'] == 1
            assert sha(encode(nonruntime(packet['evidence']))) == row['nonruntime_evidence_sha256']
            wire_path = track(Path(row['wire_path']), row['wire_sha256'])
            legacy_path = track(Path(row['legacy_target_path']), row['legacy_target_sha256'])
            legacy = json.loads(legacy_path.read_bytes())
            assert packet['evidence']['legacy_target_sha256'] == sha(encode(legacy))
            assert packet['evidence']['wire_sha256'] == row['wire_sha256']
            assert legacy['reviewed_at'] == packet['evidence']['reviewed_at'] == row['reviewed_at'] == ASSESSMENT_TIME
            closed_class(legacy)
            closed_class(packet['evidence'])
            assert preserved_metadata(json.loads(wire_path.read_bytes())) == legacy['metadata']
            assert len(row['members']) == 2 and [m['source_id'] for m in row['members']] == row['source_ids']
            for member in row['members']:
                payload = json.loads(track(Path(member['prepared_input_path']), member['prepared_input_sha256']).read_bytes())
                original = track(Path(member['original_copy_path']), member['source_sha256'])
                source_copy = track(Path(member['source_copy_path']), member['source_sha256'])
                assert original.read_bytes() == source_copy.read_bytes() == (repo / 'FGDC' / member['name']).read_bytes()
                register_profiles(payload, True)
            class_rows.append(row)
            classes[tid] = {key: value for key, value in row.items() if key not in
                           ('current_binding', 'current_preparation_path', 'current_preparation_sha256',
                            'current_prepare_calls', 'nonruntime_evidence_sha256', 'wire_legacy_and_nonruntime_evidence_equal')}
            classes[tid].update(preparation_path=str(packet_path), preparation_sha256=row['current_preparation_sha256'],
                                evidence=packet['evidence'], binding=packet['binding'])
    assert len(prior['shards']) == len(receipts) == 4
    assert len(previous_file_manifest['public_baseline_files']) == 30526
    assert len(previous_file_manifest['exact_public_profile_files']) == 21
    assert len(frozen) == 34652 and len(profiles) == 26
    assert sha(encode(frozen)) == '08b5805936c56dbc332f48fd649b253932bb695b79fe81ed206a781031456040'
    assert sha(encode(profiles)) == 'c900b633afbb3a311baec7f4cb9cd28811d449e99d4455fdcd65fcc4c2d79e5b'
    for path, wanted in profiles.items():
        relative = path.split('/docs/readiness/', 1)[1]
        assert relative in PROFILE_RELATIVES
        assert digest(repo / 'docs/readiness' / relative) == wanted
    assert len(receipts[0]['policy_input_bindings']) == 38
    assert len(singles) == 3391 and len(classes) == 203
    assert len({sid for c in classes.values() for sid in c['source_ids']}) == 406
    assert not set(singles) & {sid for c in classes.values() for sid in c['source_ids']}
    assert sha(encode(sorted(old_rows, key=lambda r: source_order(r['source_id'])))) == prior['retained3262_comparison_rows_sha256']
    assert sha(encode(sorted(class_rows, key=lambda r: r['record_target_id']))) == prior['retained203_class_comparison_rows_sha256']
    for key in ('source_bindings_before', 'runtime_sha256', 'policy_input_bindings', 'original_hashes', 'assessment_time'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    assert all(digest(Path(path)) == wanted for path, wanted in (frozen | profiles).items())
    return prior, singles, classes, frozen, profiles, receipts[0]


def approved194(repo):
    source = pin(repo / SOURCE_REVIEW, SOURCE_REVIEW_SHA)
    review = pin(repo / INDEPENDENT_REVIEW, INDEPENDENT_REVIEW_SHA)
    assert review['verdict'] == 'APPROVE_EXACT194_COMPOSITION_RETAIN29_HOLDS_SOURCE_ONLY'
    assert not review['material_findings'] and not review['material_composition_blockers']
    assert source['members'] == review['approved_members']
    assert sha(encode(source['members'])) == MEMBERSHIP_SHA == review['approved_membership_sha256']
    assert source['proposed_source_count'] == review['approved_source_count'] == 194
    assert sha(encode(source['source_rows'])) == source['source_rows_sha256'] == review['approved_source_rows_sha256']
    rows = {row['source_id']: row for row in source['source_rows']}
    assert len(rows) == len(source['source_rows']) == 194
    assert not set(rows) & {row['source_id'] for row in review['preserved_held_members']}
    assert len(review['preserved_held_members']) == 29
    for row in rows.values():
        original = (repo / 'FGDC' / (row['source_id'] + '.xml')).read_bytes()
        assert sha(original) == row['source_sha256']
        assert sha(encode(source_node(ET.fromstring(original)))) == row['source_root_sha256']
        assert sha(encode(row['complete_legacy_creators'])) == row['complete_legacy_creators_sha256']
        assert sha(encode(row['proposed_modern_creators'])) == row['proposed_modern_creators_sha256']
    return source, review, rows

SCHEMAS = {
    'record-v6.0.0.json': 'bf029b1a74d851ff9c5474a9a528a0c4a0530026abf1698caf67f8efe6b95b88',
    'record-definitions-v2.0.0.json': '09060efec922d22bee3103e6b259e11a3fc0c1bdfa8eafc3df6335aba0199865',
    'definitions-v1.0.0.json': 'eeb99397c4c4712990222c969b8f8a22566eecf32818434f32b1982ed5eaab74',
    'definitions-v2.0.0.json': '319e15bd15d15d7947c3298bee7c2db30f1b6c1de6e9500b869631b0828e13d6',
}
AUTHORITY_KINDS = {
    'existing_creator426_cohort': 'creator426',
    'existing_dfo_literal_collective_profile': 'dfo70',
    'existing_default_primary_citation_legacy_route_no_creator426_or_dfo_profile': 'direct',
}


def valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def require_freeze():
    if DRAFT_ONLY or not all(valid_sha(value) for value in
            (MAPPING_SHA, EXPECTED_RUNTIME_SHA, EXPECTED_SOURCE_TEST_SHA,
             SOURCE_REVIEW_SHA, INDEPENDENT_REVIEW_SHA)):
        raise RuntimeError('Disabled draft: finalize exact inputs, independent helper review and code freeze first')
    if not __debug__ or not isinstance(EXPECTED_SOURCE_TEST_COUNT, int):
        raise RuntimeError('Assertions and an exact frozen source/test file count are required')
    if len(EXPECTED_REVISION) != 40 or not all(c in '0123456789abcdef' for c in EXPECTED_REVISION):
        raise RuntimeError('Exact base HEAD of the frozen staged working tree is required')


def code_state():
    return {'kind': 'frozen_staged_working_tree', 'base_revision': EXPECTED_REVISION,
            'base_revision_is_new194_code_commit': False, 'runtime_sha256': EXPECTED_RUNTIME_SHA,
            'source_tree_sha256': EXPECTED_SOURCE_TEST_SHA, 'source_tree_file_count': EXPECTED_SOURCE_TEST_COUNT}


def write_json(path, value):
    # Additive output only; never update a retained receipt.
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def public_roots(frozen):
    roots = {Path('/tmp') / Path(path).relative_to('/tmp').parts[0] for path in frozen}
    assert len(roots) == 25 and all(root != Path('/tmp') for root in roots)
    assert set(PRIOR_ROOTS) <= roots
    return roots


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def authority(row, repo):
    current = row['current_creator_authority']
    kind = AUTHORITY_KINDS[current['kind']]
    if kind == 'direct':
        return kind, None, MAPPING_SHA
    reference = current['reference']
    relative = reference['file'].split('/docs/readiness/', 1)[1]
    assert relative in PROFILE_RELATIVES
    path = repo / 'docs/readiness' / relative
    value = json.loads(path.read_bytes())
    for token in reference['json_pointer'].split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    assert sha(encode(value)) == reference['object_sha256']
    assert value['creators'] == row['complete_legacy_creators']
    assert {'source_id': row['source_id'], 'source_sha256': row['source_sha256']} in value['members']
    return kind, current['profile'], digest(path)


def reviewed_manifest(repo, source, rows):
    manifest = pin(repo / MAPPING, MAPPING_SHA)
    assert manifest['kind'] == 'modern-reviewed-creators194-v1'
    assert manifest['schema_version'] == 1 and manifest['policy'] == POLICY
    assert manifest['source_packet_sha256'] == SOURCE_REVIEW_SHA
    assert manifest['independent_review_sha256'] == INDEPENDENT_REVIEW_SHA
    members = sorted([{'source_id': row['source_id'], 'source_sha256': row['source_sha256']}
                      for row in manifest['rows']], key=lambda row: source_order(row['source_id']))
    assert len(manifest['rows']) == 194 and members == source['members']
    assert len({row['source_id'] for row in manifest['rows']}) == 194
    public_objects = {}
    for row in rows.values():
        authority(row, repo)
        for key in ('current_source_plan_target', 'original_rehosting_authority'):
            reference = row[key]
            relative = reference['file'].split('/docs/readiness/', 1)[1]
            assert relative in PROFILE_RELATIVES | {'2026-10-04/publication_plan.json'}
            if relative not in public_objects:
                public_objects[relative] = json.loads((repo / 'docs/readiness' / relative).read_bytes())
            value = public_objects[relative]
            for token in reference['json_pointer'].split('/')[1:]:
                token = token.replace('~1', '/').replace('~0', '~')
                value = value[int(token)] if isinstance(value, list) else value[token]
            assert sha(encode(value)) == reference['object_sha256']
            if key == 'current_source_plan_target':
                assert value['record_target_id'] == row['source_id']
                assert value['source_ids'] == [row['source_id']] and value['source_semantic_status'] == 'supported'
                assert value['source_sha256'] == row['source_sha256']
                assert value['identity_decision']['production_record_id'] is None
                assert value['identity_decision']['production_doi'] is None
    assert manifest['source_plan_sha256'] == digest(repo / 'docs/readiness/2026-10-04/publication_plan.json')
    expected_rows = []
    for row in source['source_rows']:
        current = row['current_creator_authority']
        expected_rows.append({
            'source_id': row['source_id'], 'source_sha256': row['source_sha256'],
            'approval_partition': row['approval_partition'],
            'creator_authority_kind': AUTHORITY_KINDS[current['kind']], 'creator_cohort': current.get('profile'),
            'creator_authority_object_sha256': current['reference'].get('object_sha256'),
            'source_plan_target_sha256': row['current_source_plan_target']['object_sha256'],
            'creators': row['complete_legacy_creators'], 'modern_creators': row['proposed_modern_creators'],
            'primary_origins': row['original_primary_origin_elements'], 'source_root_sha256': row['source_root_sha256']})
    expected_header = {'schema_version': 1, 'kind': 'modern-reviewed-creators194-v1', 'policy': POLICY,
        'source_packet_sha256': SOURCE_REVIEW_SHA, 'independent_review_sha256': INDEPENDENT_REVIEW_SHA,
        'source_plan_sha256': digest(repo / 'docs/readiness/2026-10-04/publication_plan.json'),
        'creator426_profile_sha256': digest(repo / 'docs/readiness/2026-10-04/source_citation_credits_426.json'),
        'dfo_profile_sha256': digest(repo / 'docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json'),
        'member_count': 194, 'authority_counts': {'creator426': 82, 'direct': 42, 'dfo70': 70}}
    assert manifest == expected_header | {'rows': expected_rows}
    return manifest


def expected_new_evidence(repo, sid, source, metadata, payload, input_sha, wire_sha, runtime, manifest):
    original = (repo / 'FGDC' / (sid + '.xml')).read_bytes()
    policy, classification = payload['artifact_policy'], dict(payload['content_classification'])
    kind, cohort, profile_sha = authority(source, repo)
    assert policy['schema_version'] == 1 and policy['object_kind'] == 'original_fgdc_xml'
    assert policy['source_sha256'] == sha(original) and policy['resource_type'] == 'other'
    assert policy['reviewed_at'] == classification['reviewed_at'] == ASSESSMENT_TIME
    if kind in ('creator426', 'dfo70'):
        assert policy['creator_interpretation']['manifest_sha256'] == profile_sha
    else:
        assert 'creator_interpretation' not in policy
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
    return {'schema_version': EVIDENCE_SCHEMA, 'policy': POLICY, 'mapping_manifest_sha256': MAPPING_SHA,
            'creator_authority_kind': kind, 'creator_cohort': cohort,
            'source_id': sid, 'source_sha256': sha(original), 'prepared_input_sha256': input_sha,
            'legacy_metadata_sha256': sha(encode(metadata)), 'wire_sha256': wire_sha,
            'artifact_contract': artifact, 'creator_profile_sha256': profile_sha,
            'source_plan_sha256': manifest['source_plan_sha256'], 'runtime_sha256': runtime, 'schema_sha256': SCHEMAS}


def verify_new(repo, root, row, source, manifest, runtime):
    sid = source['source_id']
    assert row['source_id'] == sid and row['source_sha256'] == source['source_sha256']
    assert row['prepare_calls'] == 2 and row['fresh_source_assessment_true'] is True
    input_path = inside(root, row['prepared_input_path'])
    assert input_path == root / 'prepared/data/zenodo_json' / (sid + '.json')
    payload = pin(input_path, row['prepared_input_sha256'])
    packet = pin(inside(root, row['preparation_path']), row['preparation_sha256'])
    wire_path = inside(root, row['wire_path'])
    wire = pin(wire_path, row['wire_sha256'])
    original = (repo / 'FGDC' / (sid + '.xml')).read_bytes()
    assert original == inside(root, row['original_copy_path']).read_bytes() == (root / 'sources' / (sid + '.xml')).read_bytes()
    assert row['original_copy_path'] == 'prepared/data/original_fgdc/' + sid + '.xml'
    assert sha(original) == source['source_sha256']
    assert sha(encode(source_node(ET.fromstring(original)))) == source['source_root_sha256']
    assert row['xml_bytes'] == len(original) and row['body_bytes'] == wire_path.stat().st_size
    assert row['xml_bytes'] <= 1024 * 1024 and row['body_bytes'] <= 1024 * 1024
    assert packet['source_id'] == sid and packet['complete_raw_input_metadata'] == payload['metadata']
    assert all(packet[key] is True for key in ('complete_legacy_metadata_preserved', 'unchanged_repeat_equal',
                                              'fresh_source_assessment_true', 'exact_source_root_verified'))
    metadata = packet['complete_legacy_metadata']
    assert metadata['creators'] == payload['metadata']['creators'] == source['complete_legacy_creators']
    check_wire(wire, metadata, source['proposed_modern_creators'])
    assert row['raw_input_metadata_sha256'] == sha(encode(payload['metadata']))
    expected = expected_new_evidence(repo, sid, source, metadata, payload,
                                    row['prepared_input_sha256'], row['wire_sha256'], runtime, manifest)
    assert packet['evidence'] == expected
    assert packet['binding'] == row['binding'] == sha(encode(expected))
    assert row['normalized_legacy_metadata_sha256'] == expected['legacy_metadata_sha256']
    assert row['creator_authority_kind'] == expected['creator_authority_kind']
    assert row['creator_cohort'] == expected['creator_cohort'] and row['policy'] == POLICY


def measure_new(ids, approved, manifest, output, mapping, fixtures, paths_class, assess, max_bytes, originals):
    prepared_root = fixtures(output, ids=ids)
    paths = paths_class(str(prepared_root), 'production')
    report_path = prepared_root / 'classification.json'
    report = json.loads(report_path.read_bytes())
    assert len(report['records']) == len(ids) and {r['source_id'] for r in report['records']} == set(ids)
    assert report['summary']['source_status_counts'] == {'supported': len(ids), 'held': 0, 'failed': 0}
    assert all(r['source_status'] == 'supported' and r['remote_verified'] is False
               and r['publication_approved'] is False for r in report['records'])
    assert {p.stem for p in (output / 'sources').glob('*.xml')} == set(ids)
    assert {p.stem for p in Path(paths.zenodo_json_dir).glob('*.json')} == set(ids)
    directory = output / 'reviewed194'
    directory.mkdir()
    rows = []
    for index, sid in enumerate(ids, 1):
        source = approved[sid]
        json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw = json_file.read_bytes()
        payload = json.loads(raw)
        selected, fields = mapping.source_policy(sid)
        kind, cohort, profile_sha = authority(source, mapping.ROOT)
        assert selected['members'] == [{'source_id': sid, 'source_sha256': source['source_sha256']}]
        assert selected['creators'] == source['complete_legacy_creators']
        assert selected['modern_creators'] == source['proposed_modern_creators']
        assert selected['creator_authority_kind'] == kind
        assert fields == {'schema_version': EVIDENCE_SCHEMA, 'policy': POLICY,
                          'mapping_manifest_sha256': MAPPING_SHA, 'creator_authority_kind': kind,
                          'creator_cohort': cohort}
        current, repeated = mapping.prepare(json_file, paths), mapping.prepare(json_file, paths)
        assert current == repeated and raw == json_file.read_bytes()
        metadata, source_sha, artifact, _ = assess(json_file, paths)
        assert payload['metadata']['creators'] == metadata['creators'] == source['complete_legacy_creators']
        assert current.evidence == expected_new_evidence(mapping.ROOT, sid, source, metadata, payload,
                                                        sha(raw), sha(current.body), EXPECTED_RUNTIME_SHA, manifest)
        assert current.evidence['artifact_contract'] == artifact
        assert current.evidence['creator_profile_sha256'] == profile_sha
        assert current.binding == sha(encode(current.evidence))
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        check_wire(json.loads(current.body), metadata, source['proposed_modern_creators'])
        original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        assert sha(encode(source_node(ET.fromstring(original)))) == source['source_root_sha256']
        copy_path = Path(paths.original_fgdc_dir) / (sid + '.xml')
        assert current.xml == original == copy_path.read_bytes() == (output / 'sources' / (sid + '.xml')).read_bytes()
        assert sha(original) == source_sha == source['source_sha256'] == originals[sid + '.xml']
        wire_path = directory / (sid + '.wire.json')
        packet_path = directory / (sid + '.preparation.json')
        with wire_path.open('xb') as stream:
            stream.write(current.body)
        write_json(packet_path, {'source_id': sid, 'binding': current.binding, 'evidence': current.evidence,
            'complete_raw_input_metadata': payload['metadata'], 'complete_legacy_metadata': metadata,
            'complete_legacy_metadata_preserved': True, 'fresh_source_assessment_true': True,
            'exact_source_root_verified': True, 'unchanged_repeat_equal': True})
        rows.append({'source_id': sid, 'source_sha256': source_sha, 'binding': current.binding,
            'policy': POLICY, 'creator_authority_kind': kind, 'creator_cohort': cohort,
            'prepared_input_path': str(json_file.relative_to(output)), 'prepared_input_sha256': sha(raw),
            'raw_input_metadata_sha256': sha(encode(payload['metadata'])),
            'normalized_legacy_metadata_sha256': sha(encode(metadata)),
            'original_copy_path': str(copy_path.relative_to(output)), 'wire_path': str(wire_path.relative_to(output)),
            'wire_sha256': digest(wire_path), 'preparation_path': str(packet_path.relative_to(output)),
            'preparation_sha256': digest(packet_path), 'body_bytes': len(current.body), 'xml_bytes': len(original),
            'prepare_calls': 2, 'fresh_source_assessment_true': True})
        if index % 10 == 0 or index == len(ids):
            print('NEW_REVIEWED194_PROGRESS', index, 'of', len(ids), flush=True)
    return prepared_root, report_path, rows


def retained_paths_class(paths_class):
    class RetainedPaths(paths_class):
        def _prepare_dir(self, new_path, legacy_path=None, migrate_patterns=None):
            assert Path(new_path).is_dir()
            return new_path

        def _prepare_file(self, new_path, legacy_path=None):
            assert Path(new_path).parent.is_dir()
            return new_path
    return RetainedPaths


def compare_retained(ids, retained, output, mapping, paths_class, max_bytes, originals):
    directory = output / 'retained'
    directory.mkdir()
    paths_by_root, rows = {}, []
    for index, sid in enumerate(ids, 1):
        saved = retained[sid]
        root = saved['prepared_root']
        if root not in paths_by_root:
            paths_by_root[root] = retained_paths_class(paths_class)(root, 'production')
        current = mapping.prepare(Path(saved['prepared_input_path']), paths_by_root[root])
        assert current.source_id == sid
        assert current.body == Path(saved['wire_path']).read_bytes()
        assert nonruntime(current.evidence) == nonruntime(saved['evidence'])
        assert current.evidence['runtime_sha256'] == EXPECTED_RUNTIME_SHA
        assert current.binding == sha(encode(current.evidence))
        assert current.xml == (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        assert current.xml == (Path(root) / 'data/original_fgdc' / (sid + '.xml')).read_bytes()
        assert sha(current.xml) == originals[sid + '.xml'] == saved['source_sha256']
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        assert digest(Path(saved['prepared_input_path'])) == saved['prepared_input_sha256']
        wire = json.loads(current.body)
        metadata = preserved_metadata(wire)
        assert sha(encode(metadata)) == current.evidence['legacy_metadata_sha256']
        check_wire(wire, metadata)
        packet_path = directory / (sid + '.preparation.json')
        write_json(packet_path, {'source_id': sid, 'binding': current.binding, 'evidence': current.evidence})
        rows.append({key: value for key, value in saved.items() if key != 'evidence'} | {
            'current_binding': current.binding, 'current_preparation_path': str(packet_path.relative_to(output)),
            'current_preparation_sha256': digest(packet_path), 'wire_and_nonruntime_evidence_equal': True,
            'nonruntime_evidence_sha256': sha(encode(nonruntime(current.evidence))), 'current_prepare_calls': 1})
        if index % 100 == 0 or index == len(ids):
            print('RETAINED_SINGLETON_PROGRESS', index, 'of', len(ids), flush=True)
    return rows


def compare_retained_classes(ids, retained, output, modern, mapping, paths_class, max_bytes, originals):
    directory = output / 'retained_classes'
    directory.mkdir()
    paths_by_root, rows = {}, []
    for index, tid in enumerate(ids, 1):
        saved = retained[tid]
        root = saved['prepared_root']
        if root not in paths_by_root:
            paths_by_root[root] = retained_paths_class(paths_class)(root, 'production')
        current = modern.prepare(tid, paths_by_root[root], reviewed_at=saved['reviewed_at'])
        assert current.record_target_id == tid and list(current.source_ids) == saved['source_ids']
        assert current.body == Path(saved['wire_path']).read_bytes()
        assert current.legacy_target == json.loads(Path(saved['legacy_target_path']).read_bytes())
        assert nonruntime(current.evidence) == nonruntime(saved['evidence'])
        assert current.evidence['runtime_sha256'] == EXPECTED_RUNTIME_SHA
        assert current.binding == sha(encode(current.evidence)) and len(current.body) <= max_bytes
        closed_class(current.legacy_target)
        closed_class(current.evidence)
        assert len(current.originals) == len(saved['members']) == 2
        for (filename, raw), member in zip(current.originals, saved['members'], strict=True):
            assert filename == member['name'] == member['source_id'] + '.xml'
            assert raw == Path(member['original_copy_path']).read_bytes() == Path(member['source_copy_path']).read_bytes()
            assert raw == (mapping.ROOT / 'FGDC' / filename).read_bytes()
            assert sha(raw) == member['source_sha256'] == saved['source_sha256'] == originals[filename]
            assert len(raw) == member['size'] and len(raw) <= max_bytes
            assert digest(Path(member['prepared_input_path'])) == member['prepared_input_sha256']
        packet_path = directory / ('XMLCLASS-' + tid.split(':')[1] + '.preparation.json')
        write_json(packet_path, {'record_target_id': tid, 'source_ids': list(current.source_ids),
                                'binding': current.binding, 'evidence': current.evidence})
        rows.append({key: value for key, value in saved.items() if key != 'evidence'} | {
            'current_binding': current.binding, 'current_preparation_path': str(packet_path.relative_to(output)),
            'current_preparation_sha256': digest(packet_path), 'wire_legacy_and_nonruntime_evidence_equal': True,
            'nonruntime_evidence_sha256': sha(encode(nonruntime(current.evidence))), 'current_prepare_calls': 1})
        if index % 10 == 0 or index == len(ids):
            print('RETAINED_CLASS_PROGRESS', index, 'of', len(ids), flush=True)
    return rows


def main():
    require_freeze()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shard-index', type=int, choices=range(4), required=True)
    parser.add_argument('--expected-helper-sha256', required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    helper = Path(__file__).resolve()
    assert valid_sha(args.expected_helper_sha256) and digest(helper) == args.expected_helper_sha256
    os.environ.clear()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    prior, retained, classes, frozen, profiles, previous = retained3594(repo)
    roots = public_roots(frozen)
    if (not output.is_relative_to('/tmp') or output == Path('/tmp') or output.exists()
            or output.is_relative_to(repo) or not output.parent.is_dir()
            or any(output.is_relative_to(root) or root.is_relative_to(output) for root in roots)):
        raise ValueError('Choose fresh /tmp output outside every retained baseline')
    assert digest(repo / 'ci/run_offline_tests.py') == GUARD_SHA
    from ci.run_offline_tests import (
        OfflineGuard,
        checkout_revision,
        clean_environment,
        source_bindings,
    )

    revision = checkout_revision(repo)
    assert revision == EXPECTED_REVISION
    allowed = {Path(path) for path in frozen} | {Path(path) for path in profiles}
    for path in frozen:
        allowed.update(parent for parent in Path(path).parents if any(parent.is_relative_to(root) for root in roots))
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)
    guard = OfflineGuard(repo, output, revision)
    guard.library_files.update(allowed | {helper})
    guard.install()
    guard.self_check()
    output.mkdir()
    started = time.monotonic()
    import scripts.logger
    scripts.logger.get_logger = lambda *a, **kw: Mock()
    from scripts import modern_content_class as modern
    from scripts import modern_singleton as mapping
    from scripts.agent_qa import assess_source
    from scripts.modern_singleton_executor import MAX_BYTES
    from scripts.path_config import OutputPaths
    from tests.modern_singleton_fixtures import NOW, prepare_sources

    assert mapping.ROOT.resolve() == repo
    before = source_bindings(repo)
    assert before == source_tree_bindings(repo)
    assert len(before) == EXPECTED_SOURCE_TEST_COUNT and bindings_sha(before) == EXPECTED_SOURCE_TEST_SHA
    runtime_sha = mapping.runtime_binding()
    assert runtime_sha == EXPECTED_RUNTIME_SHA
    assert runtime_sha == sha(encode({p.name: digest(p) for p in sorted((repo / 'scripts').glob('*.py'))}))
    originals = {p.name: digest(p) for p in sorted((repo / 'FGDC').glob('*.xml'))}
    assert len(originals) == 4206 and originals == previous['original_hashes'] and sha(encode(originals)) == ORIGINALS_SHA
    assert NOW.isoformat() == ASSESSMENT_TIME
    source, review, approved = approved194(repo)
    manifest = reviewed_manifest(repo, source, approved)
    assert mapping.REVIEWED_CREATORS_POLICY == POLICY
    assert mapping.REVIEWED_CREATORS_MAPPING == repo / MAPPING
    assert mapping.REVIEWED_CREATORS_SOURCE == repo / SOURCE_REVIEW
    assert mapping.REVIEWED_CREATORS_REVIEW == repo / INDEPENDENT_REVIEW
    assert not set(approved) & (set(retained) | {sid for c in classes.values() for sid in c['source_ids']})
    assert set(approved) <= {m['source_id'] for g in prior['remaining']['singleton_categories'].values() for m in g['members']}
    assert all(digest(inside(repo, relative)) == wanted
               for relative, wanted in previous['policy_input_bindings'].items())
    policy_inputs = {repo / relative: wanted for relative, wanted in previous['policy_input_bindings'].items()}
    policy_inputs.update({repo / MAPPING: MAPPING_SHA, repo / SOURCE_REVIEW: SOURCE_REVIEW_SHA,
                         repo / INDEPENDENT_REVIEW: INDEPENDENT_REVIEW_SHA, repo / PRIOR: PRIOR_SHA})
    # Preserve every current source-authority profile alongside all 38 old policy bindings.
    policy_inputs.update({repo / 'docs/readiness' / relative: digest(repo / 'docs/readiness' / relative)
                         for relative in PROFILE_RELATIVES})
    assert all(path.is_relative_to(repo) and path.resolve() == path for path in policy_inputs)
    assert all(digest(path) == wanted for path, wanted in policy_inputs.items())
    assert all(digest(repo / 'contracts/schemas/zenodo-modern' / name) == wanted for name, wanted in SCHEMAS.items())
    all_new, all_old, all_classes = sorted(approved, key=source_order), sorted(retained, key=source_order), sorted(classes)
    index = args.shard_index
    new_ids, old_ids, class_ids = all_new[index::4], all_old[index::4], all_classes[index::4]
    assert (len(new_ids), len(old_ids), len(class_ids)) == (NEW_COUNTS[index], OLD_COUNTS[index], CLASS_COUNTS[index])
    print('REVIEWED194_SHARD_START', index, len(new_ids), len(old_ids), len(class_ids), flush=True)
    prepared_root, report_path, rows = measure_new(new_ids, approved, manifest, output, mapping,
                                                 prepare_sources, OutputPaths, assess_source, MAX_BYTES, originals)
    compatibility = compare_retained(old_ids, retained, output, mapping, OutputPaths, MAX_BYTES, originals)
    class_rows = compare_retained_classes(class_ids, classes, output, modern, mapping, OutputPaths, MAX_BYTES, originals)
    assert [r['source_id'] for r in rows] == new_ids and [r['source_id'] for r in compatibility] == old_ids
    assert [r['record_target_id'] for r in class_rows] == class_ids
    assert originals == {p.name: digest(p) for p in sorted((repo / 'FGDC').glob('*.xml'))}
    assert before == source_bindings(repo) and runtime_sha == mapping.runtime_binding()
    assert digest(helper) == args.expected_helper_sha256
    assert all(digest(path) == wanted for path, wanted in policy_inputs.items())
    assert all(digest(Path(path)) == wanted for path, wanted in (frozen | profiles).items())
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    artifact, baseline = output / 'wire_artifact_manifest.json', output / 'retained_file_manifest.json'
    write_json(artifact, {'reviewed194_rows': rows, 'retained3391_rows': compatibility, 'retained203_class_rows': class_rows})
    write_json(baseline, {'public_baseline_files': frozen, 'exact_public_profile_files': profiles})
    receipt = output / 'coverage.json'
    write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_REVIEWED194_SHARD_COVERAGE_PASS',
        'actual_checkout_revision': revision, 'code_state': code_state(),
        'helper_sha256': args.expected_helper_sha256,
        'runtime_sha256': runtime_sha, 'guard_sha256': GUARD_SHA, 'prior3594_validation_sha256': PRIOR_SHA,
        'mapping_manifest_sha256': MAPPING_SHA, 'source_review_sha256': SOURCE_REVIEW_SHA,
        'independent_review_sha256': INDEPENDENT_REVIEW_SHA, 'policy': POLICY, 'evidence_schema_version': EVIDENCE_SCHEMA,
        'environment_cleared_dummy_credentials_only': True, 'assessment_time': ASSESSMENT_TIME,
        'policy_input_bindings': {str(path.relative_to(repo)): wanted for path, wanted in policy_inputs.items()},
        'source_bindings_before': before, 'source_tree_sha256': bindings_sha(before), 'source_bindings_unchanged': True,
        'sharding': {'index': index, 'count': 4, 'assignment': 'numeric singleton IDs and lexical class IDs, ids[index::4]',
            'new_manifest_members': 194, 'retained_baseline_members': 3391, 'retained_baseline_classes': 203,
            'sorted_new_ids_sha256': sha(encode(all_new)), 'sorted_retained_ids_sha256': sha(encode(all_old)),
            'sorted_retained_class_ids_sha256': sha(encode(all_classes)),
            'assigned_new_source_ids': new_ids, 'assigned_retained_source_ids': old_ids, 'assigned_retained_class_ids': class_ids,
            'actual_new_preparations': len(rows), 'actual_new_prepare_calls': 2 * len(rows),
            'actual_retained_comparisons': len(compatibility), 'actual_retained_prepare_calls': len(compatibility),
            'actual_retained_class_comparisons': len(class_rows), 'actual_retained_class_prepare_calls': len(class_rows),
            'all_shards_complete_claimed': False},
        'prepared_root': str(prepared_root), 'classification_sha256': digest(report_path),
        'classification_counts': {'supported': len(rows), 'held': 0, 'failed': 0},
        'fresh_classification_all194_including_stale_historical_inputs': True,
        'retained_class_alias_holds_preserved': True, 'source_status_unchanged': prior['source_status_unchanged'],
        'wire_artifact_manifest_path': artifact.name, 'wire_artifact_manifest_sha256': digest(artifact),
        'retained_file_manifest_path': baseline.name, 'retained_file_manifest_sha256': digest(baseline),
        'all3594_retained_file_hashes_verified_before_and_after': True,
        'retained_file_count': len(frozen), 'exact_public_profile_file_count': len(profiles),
        'retained_paths_and_bytes_unchanged': True, 'original_hashes': originals, 'original_hashes_sha256': ORIGINALS_SHA,
        'original_files_verified_before_and_after': 4206, 'guard': guard.counts,
        'unexpected_guard_events': guard.blocked_call_sites,
        'in_process_read_only_git_queries': guard.metadata_queries, 'elapsed_seconds': time.monotonic() - started,
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Only assigned fresh classification and twice-preparation of approved194; prior3391 singleton and203 '
                 'paired targets once at exact original inputs/times. Full legacy metadata, prior wires and all nonruntime '
                 'evidence remain exact. Complete3788-target coverage requires four saved receipts. No class execution, '
                 'source promotion, remote identity, duplicate absence, grant, QA/community acceptance or release asserted.'})
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('REVIEWED194_SHARD_RESULT', json.dumps({'shard_index': index, 'receipt_sha256': digest(receipt),
                                               'guard': guard.counts}), flush=True)


if __name__ == '__main__':
    main()
