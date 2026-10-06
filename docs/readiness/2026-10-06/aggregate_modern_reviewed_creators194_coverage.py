"""Aggregate four pinned, completed reviewed194 saved receipts.

No project/helper imports, classification, preparation, tests or provider calls.
Read pinned public artifacts; write one new /tmp JSON document for later review.
Final helper and actual successful receipt SHA256 values remain mandatory.
"""

import argparse
import copy
import hashlib
import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

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

# Populate only from the final independently reviewed helper and actual successful
# shard completion receipts. These are not hypothetical/current coverage claims.
MEASUREMENT_HELPER = Path('docs/readiness/2026-10-06/measure_modern_reviewed_creators194_coverage.py')
MEASUREMENT_HELPER_SHA = '25cb9b2b51d4163963f1f5c4ab71ad0fb7da356afd313ef69d6d35f4a629be9a'
RECEIPT_SHAS = ('297a65b72561415e4642fef51502f38c3dabe7b90faae51c7a91bb190b04cf04', '519141c185a73685452802a618cda1dbca55681cdcf8697ae2cc0a8316676dbf', '019976a50f96f403cccd95d79589e82dc4caf4184f1547bb03b7aa4945306345', '6200a6be050323e37a63e0f720a07505b7161dd82f55aa5f61eded434b0ccb78')


def verify_retained_single(repo, root, row, saved, runtime):
    assert all(row[key] == value for key, value in saved.items() if key != 'evidence')
    packet = pin(inside(root, row['current_preparation_path']), row['current_preparation_sha256'])
    assert packet['source_id'] == row['source_id']
    assert packet['binding'] == row['current_binding'] == sha(encode(packet['evidence']))
    assert packet['evidence']['runtime_sha256'] == runtime
    assert nonruntime(packet['evidence']) == nonruntime(saved['evidence'])
    assert row['nonruntime_evidence_sha256'] == sha(encode(nonruntime(packet['evidence'])))
    assert row['wire_and_nonruntime_evidence_equal'] is True and row['current_prepare_calls'] == 1
    assert digest(Path(row['prepared_input_path'])) == saved['prepared_input_sha256'] == packet['evidence']['prepared_input_sha256']
    assert digest(Path(row['wire_path'])) == row['wire_sha256'] == packet['evidence']['wire_sha256']
    wire = json.loads(Path(row['wire_path']).read_bytes())
    metadata = preserved_metadata(wire)
    assert sha(encode(metadata)) == packet['evidence']['legacy_metadata_sha256']
    check_wire(wire, metadata)
    original = (repo / 'FGDC' / (row['source_id'] + '.xml')).read_bytes()
    assert sha(original) == row['source_sha256']
    assert original == (Path(row['prepared_root']) / 'data/original_fgdc' / (row['source_id'] + '.xml')).read_bytes()


def verify_retained_class(repo, root, row, saved, runtime):
    assert all(row[key] == value for key, value in saved.items() if key != 'evidence')
    packet = pin(inside(root, row['current_preparation_path']), row['current_preparation_sha256'])
    assert packet['record_target_id'] == row['record_target_id'] and packet['source_ids'] == row['source_ids']
    assert packet['binding'] == row['current_binding'] == sha(encode(packet['evidence']))
    assert packet['evidence']['runtime_sha256'] == runtime
    assert nonruntime(packet['evidence']) == nonruntime(saved['evidence'])
    assert row['nonruntime_evidence_sha256'] == sha(encode(nonruntime(packet['evidence'])))
    assert row['wire_legacy_and_nonruntime_evidence_equal'] is True and row['current_prepare_calls'] == 1
    wire = pin(Path(row['wire_path']), row['wire_sha256'])
    assert row['wire_sha256'] == packet['evidence']['wire_sha256']
    legacy = pin(Path(row['legacy_target_path']), row['legacy_target_sha256'])
    assert sha(encode(legacy)) == packet['evidence']['legacy_target_sha256']
    assert legacy['reviewed_at'] == row['reviewed_at'] == packet['evidence']['reviewed_at'] == ASSESSMENT_TIME
    closed_class(legacy)
    closed_class(packet['evidence'])
    assert preserved_metadata(wire) == legacy['metadata']
    assert len(row['members']) == 2 and [m['source_id'] for m in row['members']] == row['source_ids']
    for member in row['members']:
        assert digest(Path(member['prepared_input_path'])) == member['prepared_input_sha256']
        original = (repo / 'FGDC' / member['name']).read_bytes()
        assert original == Path(member['original_copy_path']).read_bytes() == Path(member['source_copy_path']).read_bytes()
        assert sha(original) == member['source_sha256'] == row['source_sha256']


def main():
    require_freeze()
    if not all(valid_sha(value) for value in (MEASUREMENT_HELPER_SHA, *RECEIPT_SHAS)):
        raise RuntimeError('Require reviewed final helper hash and all four actual successful receipt hashes')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--roots', type=Path, nargs=4, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo, roots, output = args.repo.resolve(), [p.resolve() for p in args.roots], args.output.resolve()
    assert len(set(roots)) == 4 and all(root.is_relative_to('/tmp') and root != Path('/tmp') for root in roots)
    assert all(not a.is_relative_to(b) for a in roots for b in roots if a != b)
    assert not output.exists() and output.parent.is_dir() and output.is_relative_to('/tmp')
    assert digest(repo / MEASUREMENT_HELPER) == MEASUREMENT_HELPER_SHA
    assert digest(repo / 'ci/run_offline_tests.py') == GUARD_SHA
    prior, singles, classes, frozen, profiles, previous = retained3594(repo)
    baseline_roots = public_roots(frozen)
    assert all(not a.is_relative_to(b) and not b.is_relative_to(a) for a in roots for b in baseline_roots)
    assert not any(output.is_relative_to(root) for root in set(roots) | baseline_roots)
    source, review, approved = approved194(repo)
    manifest = reviewed_manifest(repo, source, approved)
    assert not set(approved) & (set(singles) | {sid for c in classes.values() for sid in c['source_ids']})
    originals = {p.name: digest(p) for p in sorted((repo / 'FGDC').glob('*.xml'))}
    assert len(originals) == 4206 and originals == previous['original_hashes'] and sha(encode(originals)) == ORIGINALS_SHA
    before = source_tree_bindings(repo)
    assert bindings_sha(before) == EXPECTED_SOURCE_TEST_SHA and len(before) == EXPECTED_SOURCE_TEST_COUNT
    runtime = sha(encode({p.name: digest(p) for p in sorted((repo / 'scripts').glob('*.py'))}))
    assert runtime == EXPECTED_RUNTIME_SHA
    assert all(digest(repo / 'contracts/schemas/zenodo-modern' / name) == wanted for name, wanted in SCHEMAS.items())
    assert all(digest(inside(repo, relative)) == wanted
               for relative, wanted in previous['policy_input_bindings'].items())
    expected_policy = dict(previous['policy_input_bindings'])
    expected_policy.update({str(MAPPING): MAPPING_SHA, str(SOURCE_REVIEW): SOURCE_REVIEW_SHA,
                           str(INDEPENDENT_REVIEW): INDEPENDENT_REVIEW_SHA, str(PRIOR): PRIOR_SHA})
    expected_policy.update({'docs/readiness/' + relative: digest(repo / 'docs/readiness' / relative)
                            for relative in PROFILE_RELATIVES})
    all_new, all_old, all_classes = sorted(approved, key=source_order), sorted(singles, key=source_order), sorted(classes)
    rows, old_rows, class_rows, receipts, shards = [], [], [], [], []
    saved_digests = {}

    def saved_pin(path, wanted):
        assert str(path) not in saved_digests or saved_digests[str(path)] == wanted
        saved_digests[str(path)] = wanted
        return pin(path, wanted)

    for index, root in enumerate(roots):
        receipt = saved_pin(root / 'coverage.json', RECEIPT_SHAS[index])
        receipts.append(receipt)
        assert receipt['status'] == 'GUARDED_REVIEWED194_SHARD_COVERAGE_PASS'
        assert receipt['helper_sha256'] == MEASUREMENT_HELPER_SHA and receipt['runtime_sha256'] == runtime
        assert receipt['actual_checkout_revision'] == EXPECTED_REVISION
        assert receipt['code_state'] == code_state()
        assert receipt['guard_sha256'] == GUARD_SHA and receipt['prior3594_validation_sha256'] == PRIOR_SHA
        assert receipt['mapping_manifest_sha256'] == MAPPING_SHA
        assert receipt['source_review_sha256'] == SOURCE_REVIEW_SHA and receipt['independent_review_sha256'] == INDEPENDENT_REVIEW_SHA
        assert receipt['policy'] == POLICY and receipt['evidence_schema_version'] == EVIDENCE_SCHEMA
        assert receipt['source_bindings_before'] == before and receipt['source_tree_sha256'] == EXPECTED_SOURCE_TEST_SHA
        assert receipt['original_hashes'] == originals and receipt['original_hashes_sha256'] == ORIGINALS_SHA
        assert receipt['original_files_verified_before_and_after'] == 4206
        assert receipt['source_bindings_unchanged'] and receipt['environment_cleared_dummy_credentials_only']
        assert receipt['retained_paths_and_bytes_unchanged'] and receipt['all3594_retained_file_hashes_verified_before_and_after']
        assert receipt['retained_file_count'] == 34652 and receipt['exact_public_profile_file_count'] == 26
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert not receipt['unexpected_guard_events'] and not any(receipt['guard']['tests'].values())
        assert receipt['guard']['bootstrap'] == {'network': 4, 'private_reads': 1, 'processes': 1, 'writes': 1}
        assert receipt['assessment_time'] == ASSESSMENT_TIME
        assert receipt['source_status_unchanged'] == prior['source_status_unchanged']
        assert receipt['retained_class_alias_holds_preserved']
        assert receipt['fresh_classification_all194_including_stale_historical_inputs']
        assert receipt['policy_input_bindings'] == expected_policy
        for relative, wanted in expected_policy.items():
            assert digest(inside(repo, relative)) == wanted
        assigned = receipt['sharding']
        new_ids, old_ids, class_ids = all_new[index::4], all_old[index::4], all_classes[index::4]
        assert assigned['index'] == index and assigned['count'] == 4 and assigned['all_shards_complete_claimed'] is False
        assert assigned['new_manifest_members'] == 194 and assigned['retained_baseline_members'] == 3391
        assert assigned['retained_baseline_classes'] == 203
        assert assigned['sorted_new_ids_sha256'] == sha(encode(all_new))
        assert assigned['sorted_retained_ids_sha256'] == sha(encode(all_old))
        assert assigned['sorted_retained_class_ids_sha256'] == sha(encode(all_classes))
        assert assigned['assigned_new_source_ids'] == new_ids and assigned['assigned_retained_source_ids'] == old_ids
        assert assigned['assigned_retained_class_ids'] == class_ids
        assert assigned['actual_new_preparations'] == len(new_ids) == NEW_COUNTS[index]
        assert assigned['actual_new_prepare_calls'] == 2 * len(new_ids)
        assert assigned['actual_retained_comparisons'] == assigned['actual_retained_prepare_calls'] == len(old_ids) == OLD_COUNTS[index]
        assert assigned['actual_retained_class_comparisons'] == assigned['actual_retained_class_prepare_calls'] == len(class_ids) == CLASS_COUNTS[index]
        assert receipt['prepared_root'] == str(root / 'prepared')
        data = saved_pin(inside(root, receipt['wire_artifact_manifest_path']), receipt['wire_artifact_manifest_sha256'])
        files = saved_pin(inside(root, receipt['retained_file_manifest_path']), receipt['retained_file_manifest_sha256'])
        assert files == {'public_baseline_files': frozen, 'exact_public_profile_files': profiles}
        report = saved_pin(root / 'prepared/classification.json', receipt['classification_sha256'])
        assert report['summary']['source_status_counts'] == receipt['classification_counts'] == {'supported': len(new_ids), 'held': 0, 'failed': 0}
        assert len(report['records']) == len(new_ids) and {r['source_id'] for r in report['records']} == set(new_ids)
        assert all(r['source_status'] == 'supported' and r['remote_verified'] is False
                   and r['publication_approved'] is False for r in report['records'])
        assert [r['source_id'] for r in data['reviewed194_rows']] == new_ids
        assert [r['source_id'] for r in data['retained3391_rows']] == old_ids
        assert [r['record_target_id'] for r in data['retained203_class_rows']] == class_ids
        for row in data['reviewed194_rows']:
            verify_new(repo, root, row, approved[row['source_id']], manifest, runtime)
            for path_key, sha_key in (('prepared_input_path', 'prepared_input_sha256'), ('wire_path', 'wire_sha256'),
                                      ('preparation_path', 'preparation_sha256'), ('original_copy_path', 'source_sha256')):
                saved_digests[str(inside(root, row[path_key]))] = row[sha_key]
            saved_digests[str(root / 'sources' / (row['source_id'] + '.xml'))] = row['source_sha256']
            rows.append(row | {'shard_index': index})
        for row in data['retained3391_rows']:
            verify_retained_single(repo, root, row, singles[row['source_id']], runtime)
            saved_digests[str(inside(root, row['current_preparation_path']))] = row['current_preparation_sha256']
            old_rows.append(row)
        for row in data['retained203_class_rows']:
            verify_retained_class(repo, root, row, classes[row['record_target_id']], runtime)
            saved_digests[str(inside(root, row['current_preparation_path']))] = row['current_preparation_sha256']
            class_rows.append(row)
        shards.append({'index': index, 'root': str(root), 'receipt_sha256': RECEIPT_SHAS[index],
            'artifact_manifest_sha256': receipt['wire_artifact_manifest_sha256'],
            'retained_file_manifest_sha256': receipt['retained_file_manifest_sha256'],
            'classification_sha256': receipt['classification_sha256'], 'new_source_count': len(new_ids),
            'retained_source_count': len(old_ids), 'retained_class_count': len(class_ids),
            'guard': receipt['guard'], 'elapsed_seconds': receipt['elapsed_seconds']})
    assert len(rows) == len({r['source_id'] for r in rows}) == 194
    assert len(old_rows) == len({r['source_id'] for r in old_rows}) == 3391
    assert len(class_rows) == len({r['record_target_id'] for r in class_rows}) == 203
    for key in ('source_bindings_before', 'runtime_sha256', 'helper_sha256', 'policy_input_bindings',
                'original_hashes', 'original_hashes_sha256', 'actual_checkout_revision'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    assert all(digest(Path(path)) == wanted for path, wanted in (frozen | profiles | saved_digests).items())
    assert before == source_tree_bindings(repo)
    assert originals == {p.name: digest(p) for p in sorted((repo / 'FGDC').glob('*.xml'))}
    remaining = copy.deepcopy(prior['remaining'])
    removed = []
    for group in remaining['singleton_categories'].values():
        removed.extend(r['source_id'] for r in group['members'] if r['source_id'] in approved)
        group['members'] = [r for r in group['members'] if r['source_id'] not in approved]
        group['count'] = len(group['members'])
        group['membership_sha256'] = sha(encode(group['members']))
    assert len(removed) == 194 and set(removed) == set(approved)
    assert remaining['pairs'] == prior['remaining']['pairs'] and len(remaining['pairs']) == 25
    held = {r['source_id'] for r in review['preserved_held_members']}
    remaining_ids = {r['source_id'] for g in remaining['singleton_categories'].values() for r in g['members']}
    assert held <= remaining_ids and len(remaining_ids) == 120
    remaining['supported_singletons'] = 120
    assert remaining['paired_targets'] == 25
    remaining['supported_targets_outside_modern_mapping'] = 145
    result = {'schema_version': 1, 'status': 'GUARDED_REVIEWED194_AGGREGATE_PASS', 'all_shards_complete': True,
        'runtime_sha256': runtime, 'helper_sha256': MEASUREMENT_HELPER_SHA,
        'aggregation_script_sha256': digest(Path(__file__).resolve()), 'prior3594_validation_sha256': PRIOR_SHA,
        'mapping_manifest_sha256': MAPPING_SHA, 'source_review_sha256': SOURCE_REVIEW_SHA,
        'independent_review_sha256': INDEPENDENT_REVIEW_SHA, 'source_tree_sha256': bindings_sha(before),
        'actual_checkout_revisions': [EXPECTED_REVISION], 'code_state': code_state(),
        'coverage': {'prior_retained_singletons': 3391, 'prior_retained_class_targets': 203,
            'new_reviewed_singletons': 194, 'total_singletons': 3585, 'total_class_targets': 203,
            'total_wire_prepared_targets': 3788, 'total_represented_originals': 3991,
            'fresh_new_prepare_calls': 388, 'retained_input_prepare_comparisons': 3391,
            'retained_class_prepare_comparisons': 203, 'new_class_execution_enabled': False},
        'rows': sorted(rows, key=lambda r: source_order(r['source_id'])), 'shards': shards,
        'retained3391_comparison_rows_sha256': sha(encode(sorted(old_rows, key=lambda r: source_order(r['source_id'])))),
        'retained203_class_comparison_rows_sha256': sha(encode(sorted(class_rows, key=lambda r: r['record_target_id']))),
        'all_saved_digests_reverified': True, 'retained_public_file_count': len(frozen), 'retained_profile_file_count': len(profiles),
        'original_hashes_sha256': ORIGINALS_SHA, 'original_files_verified_before_and_after': 4206,
        'source_bindings_unchanged': True, 'source_status_unchanged': prior['source_status_unchanged'],
        'alias_source_holds_preserved': True, 'remaining': remaining, 'provider_requests': 0, 'provider_mutations': 0,
        'scope': '194 approved sources freshly classified/prepared twice; all3391 prior singleton wires/full legacy '
                 'metadata/nonruntime evidence and203 pairs once at original paths/time. All4206 originals unchanged. '
                 '29 personal holds retained. No class execution, source promotion, remote identity, duplicate absence, '
                 'provider grant, QA/PICES/community approval or release established.'}
    write_json(output, result)
    print(json.dumps({'path': str(output), 'sha256': digest(output), 'coverage': result['coverage'], 'remaining': 145}))


if __name__ == '__main__':
    main()
