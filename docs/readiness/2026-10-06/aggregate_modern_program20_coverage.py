"""aggregate four actual program20 saved receipts only.

No project/helper imports, classification, preparation, tests or provider calls.
Read pinned public files; write one new /tmp JSON document for independent review.
"""

import argparse
import copy
import hashlib
import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

# Shared saved-file validation block; no earlier helper or project import.
PRIOR = Path('docs/readiness/2026-10-06/modern_reviewed_creators194_validation.json')
PRIOR_SHA = '0e75f1113cdf7e6c328869cf79a0d6c62a36e9a680002cf84110078d0fd652fb'
PRIOR_HELPER_SHA = '25cb9b2b51d4163963f1f5c4ab71ad0fb7da356afd313ef69d6d35f4a629be9a'
PRIOR_AGGREGATE_SHA = '953e1b7e903d0f4ea4072f88a76e9ed713f001eddf7fccef77d2967862733e69'
PRIOR_RUNTIME = '6cc86a1740fcd93e65d42e21b1c199c160974c607be54db71f43d3e25466349e'
PRIOR_ROOTS = tuple(Path(f'/tmp/pices-reviewed194-shard{i}-v1') for i in range(4))
PRIOR_RECEIPTS = (
    '297a65b72561415e4642fef51502f38c3dabe7b90faae51c7a91bb190b04cf04',
    '519141c185a73685452802a618cda1dbca55681cdcf8697ae2cc0a8316676dbf',
    '019976a50f96f403cccd95d79589e82dc4caf4184f1547bb03b7aa4945306345',
    '6200a6be050323e37a63e0f720a07505b7161dd82f55aa5f61eded434b0ccb78')
GUARD_SHA = '1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05'
ORIGINALS_SHA = '3430315763379ef81c393cca00eb776952df3ad3f66856ef4b15edd48e396013'
MEMBERSHIP_SHA = '4bd64950f6cf4e24d2895f6fbb5cc97f6c3088f1be045769d79c88c2a3828d93'
SOURCE_REVIEW = Path('docs/readiness/2026-10-06/modern_program20_source_review.json')
SOURCE_REVIEW_SHA = '56f6e99cefe31bcba6802781e2746771947d448cd2c9ad4cde4c66d58c35653d'
INDEPENDENT_REVIEW = Path('docs/readiness/2026-10-06/modern_program20_independent_review.json')
INDEPENDENT_REVIEW_SHA = 'f0cfcd9a0fe12cdac1d52cd399355c2da09033c0e42a2279140c555bb2bd983b'
PERSONAL_REVIEW = Path('docs/readiness/2026-10-06/modern_reviewed_creators194_review.json')
PERSONAL_REVIEW_SHA = '20c585d143cc0a295bdbbce54b2e3fa5bace5846802534b2f7bf40bb3f04b271'
PROGRAM_HOLDS_SHA = '2008c0340f7481296d61fc36fe71a631a9ef06f9c5e88811924333ff281f1210'
POLICY = 'modern-xml-program-organizations20-v1'
EVIDENCE_SCHEMA = 9
ASSESSMENT_TIME = '2026-10-05T18:00:00+00:00'
NEW_COUNTS, OLD_COUNTS, CLASS_COUNTS = (5, 5, 5, 5), (897, 896, 896, 896), (51, 51, 51, 50)
DRAFT_ONLY = False
MAPPING = Path('docs/readiness/2026-10-06/modern_program20.json')
MAPPING_SHA = '0485e9c5e24566df94ad59397b8bdf2ebde375e88504d9f419bc61b71a0b20e1'
EXPECTED_RUNTIME_SHA = '78e3fdd4f3170a804aa49b25bf4e01586a2a18a5ef914a76b2be9ac4ceb72ea2'
EXPECTED_SOURCE_TEST_SHA = '9d71d97f47992d10d8c331aa60d072dc7bba40e6f1ea8f6e1e6a1a5b6d405dd7'
EXPECTED_SOURCE_TEST_COUNT = 188
# Actual base HEAD beneath frozen staged files; never claim it contains new20 code.
EXPECTED_REVISION = '8b84f9db5ea2d536de3ed01a60f147fc6cbc6246'
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
PROFILE = Path('docs/readiness/2026-10-04/source_citation_credits_426.json')
PROFILE_SHA = '15c654dc714849327b827363071a1da3ad7c3fa20c2c95a990d7868e75e96bd2'
PLAN = Path('docs/readiness/2026-10-04/publication_plan.json')
PLAN_SHA = '39d2894d518fa5a10d87cc784ce40064e6757529f23219eea153f25805f506ad'


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


def retained3788(repo):
    """Load latest saved194 bindings and original input roots; never prepare."""
    prior = pin(repo / PRIOR, PRIOR_SHA)
    assert prior['status'] == 'GUARDED_REVIEWED194_AGGREGATE_PASS' and prior['all_shards_complete']
    assert prior['helper_sha256'] == PRIOR_HELPER_SHA and prior['runtime_sha256'] == PRIOR_RUNTIME
    assert prior['aggregation_script_sha256'] == PRIOR_AGGREGATE_SHA
    assert digest(repo / 'docs/readiness/2026-10-06/measure_modern_reviewed_creators194_coverage.py') == PRIOR_HELPER_SHA
    assert digest(repo / 'docs/readiness/2026-10-06/aggregate_modern_reviewed_creators194_coverage.py') == PRIOR_AGGREGATE_SHA
    assert prior['coverage']['total_wire_prepared_targets'] == 3788
    assert prior['coverage']['total_singletons'] == 3585 and prior['coverage']['total_class_targets'] == 203
    assert prior['original_hashes_sha256'] == ORIGINALS_SHA
    assert len(prior['remaining']['protected_identity_preservation']) == 5
    proof194 = {row['source_id']: row for row in prior['rows']}
    assert len(proof194) == len(prior['rows']) == 194
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
                # Newly retained194 inputs reference the frozen194 main checkout only.
                prefix = Path('/workspace/pices-main/docs/readiness')
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
        assert receipt['status'] == 'GUARDED_REVIEWED194_SHARD_COVERAGE_PASS'
        assert receipt['guard_sha256'] == GUARD_SHA
        assert receipt['environment_cleared_dummy_credentials_only']
        assert receipt['guard']['bootstrap'] == {'network': 4, 'private_reads': 1, 'processes': 1, 'writes': 1}
        assert receipt['wire_artifact_manifest_sha256'] == shard['artifact_manifest_sha256']
        assert receipt['retained_file_manifest_sha256'] == shard['retained_file_manifest_sha256']
        assert receipt['classification_sha256'] == shard['classification_sha256']
        assert receipt['runtime_sha256'] == PRIOR_RUNTIME and receipt['helper_sha256'] == PRIOR_HELPER_SHA
        assert receipt['original_hashes_sha256'] == ORIGINALS_SHA and receipt['original_files_verified_before_and_after'] == 4206
        assert receipt['source_bindings_unchanged'] and receipt['retained_paths_and_bytes_unchanged']
        assert receipt['all3594_retained_file_hashes_verified_before_and_after']
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert not receipt['unexpected_guard_events'] and not any(receipt['guard']['tests'].values())
        assert receipt['prepared_root'] == str(root / 'prepared')
        assert receipt['assessment_time'] == ASSESSMENT_TIME
        track(root / 'prepared/classification.json', shard['classification_sha256'], True)
        assert [r['source_id'] for r in data['reviewed194_rows']] == receipt['sharding']['assigned_new_source_ids']
        assert [r['source_id'] for r in data['retained3391_rows']] == receipt['sharding']['assigned_retained_source_ids']
        assert [r['record_target_id'] for r in data['retained203_class_rows']] == receipt['sharding']['assigned_retained_class_ids']
        assert len(data['reviewed194_rows']) == (49, 49, 48, 48)[index]
        assert len(data['retained3391_rows']) == (848, 848, 848, 847)[index]
        assert len(data['retained203_class_rows']) == CLASS_COUNTS[index]
        receipts.append(receipt)
        for row in data['retained3391_rows']:
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
        for row in data['reviewed194_rows']:
            sid = row['source_id']
            assert sid not in singles and proof194[sid] == row | {'shard_index': index}
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
    assert len(previous_file_manifest['public_baseline_files']) == 34652
    assert len(previous_file_manifest['exact_public_profile_files']) == 26
    assert len(frozen) == 39232 and len(profiles) == 32
    assert sha(encode(frozen)) == 'bd067524796237dbf8a666c98d68bbba3dca812035d15b3ebddfc47dacf1001a'
    assert sha(encode(profiles)) == '239115dbb1b4c695812a2d51563a53227dbcb4ea11c10fcd1153f25217fcfa2d'
    for path, wanted in profiles.items():
        relative = path.split('/docs/readiness/', 1)[1]
        assert relative in PROFILE_RELATIVES
        assert digest(repo / 'docs/readiness' / relative) == wanted
    assert len(receipts[0]['policy_input_bindings']) == 43
    assert len(singles) == 3585 and len(classes) == 203
    assert len({sid for c in classes.values() for sid in c['source_ids']}) == 406
    assert not set(singles) & {sid for c in classes.values() for sid in c['source_ids']}
    assert sha(encode(sorted(old_rows, key=lambda r: source_order(r['source_id'])))) == prior['retained3391_comparison_rows_sha256']
    assert sha(encode(sorted(class_rows, key=lambda r: r['record_target_id']))) == prior['retained203_class_comparison_rows_sha256']
    for key in ('source_bindings_before', 'runtime_sha256', 'policy_input_bindings', 'original_hashes', 'assessment_time'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    assert all(digest(Path(path)) == wanted for path, wanted in (frozen | profiles).items())
    return prior, singles, classes, frozen, profiles, receipts[0]


SCHEMAS = {
    'record-v6.0.0.json': 'bf029b1a74d851ff9c5474a9a528a0c4a0530026abf1698caf67f8efe6b95b88',
    'record-definitions-v2.0.0.json': '09060efec922d22bee3103e6b259e11a3fc0c1bdfa8eafc3df6335aba0199865',
    'definitions-v1.0.0.json': 'eeb99397c4c4712990222c969b8f8a22566eecf32818434f32b1982ed5eaab74',
    'definitions-v2.0.0.json': '319e15bd15d15d7947c3298bee7c2db30f1b6c1de6e9500b869631b0828e13d6',
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
            'base_revision_is_new20_code_commit': False, 'runtime_sha256': EXPECTED_RUNTIME_SHA,
            'source_tree_sha256': EXPECTED_SOURCE_TEST_SHA, 'source_tree_file_count': EXPECTED_SOURCE_TEST_COUNT}


def write_json(path, value):
    # Additive output only; never update a retained receipt.
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def public_roots(frozen):
    roots = {Path('/tmp') / Path(path).relative_to('/tmp').parts[0] for path in frozen}
    assert len(roots) == 29 and all(root != Path('/tmp') for root in roots)
    assert set(PRIOR_ROOTS) <= roots
    return roots


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def utf8_sha(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def hold_sets(repo, review):
    personal = pin(repo / PERSONAL_REVIEW, PERSONAL_REVIEW_SHA)['preserved_held_members']
    program = review['held_members']
    assert len(personal) == len(program) == 29
    assert sha(encode(program)) == PROGRAM_HOLDS_SHA
    personal_ids, program_ids = {m['source_id'] for m in personal}, {m['source_id'] for m in program}
    assert len(personal_ids) == len(program_ids) == 29 and not personal_ids & program_ids
    return {'personal29': personal, 'program_unaami29': program}


def approved20(repo):
    source = pin(repo / SOURCE_REVIEW, SOURCE_REVIEW_SHA)
    review = pin(repo / INDEPENDENT_REVIEW, INDEPENDENT_REVIEW_SHA)
    manifest = pin(repo / MAPPING, MAPPING_SHA)
    assert review['decision'] == 'APPROVE_EXACT20_COMPLETE_ORGANIZATIONAL_PROJECTIONS_RETAIN29_COMPLETE_ARRAY_HOLDS'
    assert not review['material_findings'] and review['proposal']['sha256'] == SOURCE_REVIEW_SHA
    assert source['approved_members'] == review['approved_members'] == manifest['members']
    assert len(source['approved_members']) == 20
    assert source['held_members'] == review['held_members'] == manifest['retained_held_members']
    assert sha(encode(manifest['members'])) == MEMBERSHIP_SHA == review['approved_membership_sha256']
    assert utf8_sha(source['approved_members']) == source['approved_membership_sha256'] == MEMBERSHIP_SHA
    assert utf8_sha(source['source_rows']) == source['source_rows_sha256']
    assert sha(encode(review['source_rows'])) == review['source_rows_sha256']
    assert len(source['source_rows']) == len(review['source_rows']) == 49
    rows = {row['source_id']: row for row in manifest['rows']}
    assert len(rows) == len(manifest['rows']) == 20
    assert set(rows) == {member['source_id'] for member in source['approved_members']}
    for held in hold_sets(repo, review).values():
        assert not set(rows) & {member['source_id'] for member in held}
    return source, review, rows


def authority(row, repo):
    profile = pin(repo / PROFILE, PROFILE_SHA)
    matches = [c for c in profile['cohorts'] if c['profile'] == row['creator_cohort']]
    assert len(matches) == 1
    cohort = matches[0]
    assert sha(encode(cohort)) == row['creator_authority_object_sha256']
    assert cohort['creators'] == row['creators']
    assert {'source_id': row['source_id'], 'source_sha256': row['source_sha256']} in cohort['members']
    assert row['creator_authority_kind'] == 'creator426'
    return 'creator426', cohort['profile'], PROFILE_SHA


def reviewed_manifest(repo, source, rows):
    manifest = pin(repo / MAPPING, MAPPING_SHA)
    review = pin(repo / INDEPENDENT_REVIEW, INDEPENDENT_REVIEW_SHA)
    sources = {r['source_id']: r for r in source['source_rows']}
    reviews = {r['source_id']: r for r in review['source_rows']}
    assert len(sources) == len(reviews) == 49 and set(sources) == set(reviews)
    plans = {r['record_target_id']: r for r in pin(repo / PLAN, PLAN_SHA)['targets']}
    expected = []
    for member in manifest['members']:
        sid = member['source_id']
        proposed, independent = sources[sid], reviews[sid]
        original = (repo / 'FGDC' / (sid + '.xml')).read_bytes()
        root = ET.fromstring(original)
        assert sha(original) == member['source_sha256'] == proposed['source_sha256'] == independent['source_sha256']
        assert len(original) == proposed['source_bytes'] == independent['source_bytes']
        root_object = source_node(root)
        assert root_object == proposed['source_root']
        assert utf8_sha(root_object) == proposed['source_root_sha256']
        assert sha(encode(root_object)) == independent['source_root_sha256']
        origins = [source_node(node) for node in root.findall('./idinfo/citation/citeinfo/origin')]
        assert origins == proposed['exact_primary_origin_elements'] == independent['exact_primary_origin_elements']
        cohort = proposed['complete_current_creator_cohort']
        assert cohort == independent['complete_current_creator_cohort']
        assert utf8_sha(cohort) == proposed['complete_current_creator_cohort_sha256']
        assert sha(encode(cohort)) == independent['complete_current_creator_cohort_sha256']
        creators = proposed['complete_legacy_creators']
        modern = proposed['proposed_complete_modern_creators']
        assert creators == independent['complete_legacy_creators'] == cohort['creators']
        assert proposed['decision'] == 'APPROVE_ORGANIZATIONAL_PROJECTION'
        assert independent['decision'] == 'APPROVE_FINITE_COMPLETE_ORGANIZATIONAL_ARRAY'
        assert modern == independent['approved_complete_modern_creators']
        assert modern == [{'person_or_org': {'name': c['name'], 'type': 'organizational'}} for c in creators]
        target = plans[sid]
        assert target == independent['source_plan_target']
        assert sha(encode(target)) == independent['source_plan_target_sha256']
        assert target['source_ids'] == [sid] and target['source_semantic_status'] == 'supported'
        assert target['source_sha256'] == member['source_sha256']
        assert target['identity_decision']['production_record_id'] is None
        assert target['identity_decision']['production_doi'] is None
        assert all(target[k] is False for k in ('executable', 'upload_eligible', 'remote_verified', 'publication_approved'))
        expected.append({
            'source_id': sid, 'source_sha256': member['source_sha256'], 'source_path': 'FGDC/' + sid + '.xml',
            'source_bytes': len(original), 'source_root_sha256': sha(encode(root_object)), 'primary_origins': origins,
            'creator_authority_kind': 'creator426', 'creator_cohort': cohort['profile'],
            'creator_authority_object_sha256': sha(encode(cohort)), 'source_plan_target_sha256': sha(encode(target)),
            'creators': creators, 'creators_sha256': sha(encode(creators)),
            'modern_creators': modern, 'modern_creators_sha256': sha(encode(modern)),
            'source_packet_row_sha256_utf8': utf8_sha(proposed),
            'independent_review_row_sha256_ascii': sha(encode(independent)),
            'source_contexts_sha256_ascii': sha(encode(proposed['source_contexts'])),
            'raw_four_constraints_sha256_ascii': sha(encode(proposed['raw_four_constraints'])),
            'source_dates_sha256_ascii': sha(encode(proposed['source_dates']))})
    expected.sort(key=lambda row: source_order(row['source_id']))
    header = {'schema_version': 1, 'kind': 'modern-program-organizations20-v1', 'policy': POLICY,
        'creator426_profile_sha256': PROFILE_SHA, 'source_plan_sha256': PLAN_SHA,
        'source_packet_path': str(SOURCE_REVIEW), 'source_packet_sha256': SOURCE_REVIEW_SHA,
        'independent_review_path': str(INDEPENDENT_REVIEW), 'independent_review_sha256': INDEPENDENT_REVIEW_SHA,
        'member_count': 20, 'complete_array_group_count': 17, 'modern_creator_object_count': 29,
        'members': source['approved_members'], 'membership_sha256': MEMBERSHIP_SHA,
        'retained_held_member_count': 29, 'retained_held_members': source['held_members'],
        'retained_held_membership_sha256': PROGRAM_HOLDS_SHA}
    assert manifest == header | {'rows': expected}
    assert len({sha(encode(r['creators'])) for r in expected}) == 17
    assert sum(len(r['modern_creators']) for r in expected) == 29
    assert rows == {r['source_id']: r for r in expected}
    for row in expected:
        authority(row, repo)
    return manifest


def expected_new_evidence(repo, sid, source, metadata, payload, input_sha, wire_sha, runtime, manifest):
    original = (repo / 'FGDC' / (sid + '.xml')).read_bytes()
    policy, classification = payload['artifact_policy'], dict(payload['content_classification'])
    kind, cohort, profile_sha = authority(source, repo)
    assert policy['schema_version'] == 1 and policy['object_kind'] == 'original_fgdc_xml'
    assert policy['source_sha256'] == sha(original) and policy['resource_type'] == 'other'
    assert policy['reviewed_at'] == classification['reviewed_at'] == ASSESSMENT_TIME
    assert kind == 'creator426' and profile_sha == PROFILE_SHA
    assert policy['creator_interpretation']['manifest_sha256'] == PROFILE_SHA
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
    assert metadata['creators'] == payload['metadata']['creators'] == source['creators']
    check_wire(wire, metadata, source['modern_creators'])
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
MEASUREMENT_HELPER = Path('docs/readiness/2026-10-06/measure_modern_program20_coverage.py')
MEASUREMENT_HELPER_SHA = 'f18b89e2d66b78f91b811431bf43484f14cc542974121cd344462fb874da92b8'
RECEIPT_SHAS = (
    'aea074d5820c620f7a26435d138f21eb009cd7e61a1f3c030e329d5388031f48',
    '66bcf5c3ef6f33b1a14efec4cc3103afda980c10a4905cb3eb8f9243729fa3de',
    'a669d237a405931033fc0a2bd6bb0165d887c3604de218bc64e2bd2423c0cc40',
    'a1e7da43f5bb88863c8a864a8ec7b48d2641c91150bbc9f5982046031a883a78',
)


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
    prior, singles, classes, frozen, profiles, previous = retained3788(repo)
    baseline_roots = public_roots(frozen)
    assert all(not a.is_relative_to(b) and not b.is_relative_to(a) for a in roots for b in baseline_roots)
    assert not any(output.is_relative_to(root) for root in set(roots) | baseline_roots)
    source, review, approved = approved20(repo)
    manifest = reviewed_manifest(repo, source, approved)
    holds = hold_sets(repo, review)
    prior_remaining = {m['source_id'] for g in prior['remaining']['singleton_categories'].values() for m in g['members']}
    assert all({m['source_id'] for m in group} <= prior_remaining for group in holds.values())
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
                           str(INDEPENDENT_REVIEW): INDEPENDENT_REVIEW_SHA, str(PRIOR): PRIOR_SHA,
                           str(PERSONAL_REVIEW): PERSONAL_REVIEW_SHA})
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
        assert receipt['status'] == 'GUARDED_PROGRAM20_SHARD_COVERAGE_PASS'
        assert receipt['helper_sha256'] == MEASUREMENT_HELPER_SHA and receipt['runtime_sha256'] == runtime
        assert receipt['actual_checkout_revision'] == EXPECTED_REVISION
        assert receipt['code_state'] == code_state()
        assert receipt['guard_sha256'] == GUARD_SHA and receipt['prior3788_validation_sha256'] == PRIOR_SHA
        assert receipt['mapping_manifest_sha256'] == MAPPING_SHA
        assert receipt['source_review_sha256'] == SOURCE_REVIEW_SHA and receipt['independent_review_sha256'] == INDEPENDENT_REVIEW_SHA
        assert receipt['policy'] == POLICY and receipt['evidence_schema_version'] == EVIDENCE_SCHEMA
        assert receipt['source_bindings_before'] == before and receipt['source_tree_sha256'] == EXPECTED_SOURCE_TEST_SHA
        assert receipt['original_hashes'] == originals and receipt['original_hashes_sha256'] == ORIGINALS_SHA
        assert receipt['original_files_verified_before_and_after'] == 4206
        assert receipt['source_bindings_unchanged'] and receipt['environment_cleared_dummy_credentials_only']
        assert receipt['retained_paths_and_bytes_unchanged'] and receipt['all3788_retained_file_hashes_verified_before_and_after']
        assert receipt['retained_file_count'] == 39232 and receipt['exact_public_profile_file_count'] == 32
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert not receipt['unexpected_guard_events'] and not any(receipt['guard']['tests'].values())
        assert receipt['guard']['bootstrap'] == {'network': 4, 'private_reads': 1, 'processes': 1, 'writes': 1}
        assert receipt['assessment_time'] == ASSESSMENT_TIME
        assert receipt['source_status_unchanged'] == prior['source_status_unchanged']
        assert receipt['retained_class_alias_holds_preserved'] and receipt['retained_hold_sets'] == holds
        assert receipt['fresh_classification_assigned_program20_members']
        assert receipt['policy_input_bindings'] == expected_policy
        for relative, wanted in expected_policy.items():
            assert digest(inside(repo, relative)) == wanted
        assigned = receipt['sharding']
        new_ids, old_ids, class_ids = all_new[index::4], all_old[index::4], all_classes[index::4]
        assert assigned['index'] == index and assigned['count'] == 4 and assigned['all_shards_complete_claimed'] is False
        assert assigned['new_manifest_members'] == 20 and assigned['retained_baseline_members'] == 3585
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
        assert [r['source_id'] for r in data['program20_rows']] == new_ids
        assert [r['source_id'] for r in data['retained3585_rows']] == old_ids
        assert [r['record_target_id'] for r in data['retained203_class_rows']] == class_ids
        for row in data['program20_rows']:
            verify_new(repo, root, row, approved[row['source_id']], manifest, runtime)
            for path_key, sha_key in (('prepared_input_path', 'prepared_input_sha256'), ('wire_path', 'wire_sha256'),
                                      ('preparation_path', 'preparation_sha256'), ('original_copy_path', 'source_sha256')):
                saved_digests[str(inside(root, row[path_key]))] = row[sha_key]
            saved_digests[str(root / 'sources' / (row['source_id'] + '.xml'))] = row['source_sha256']
            rows.append(row | {'shard_index': index})
        for row in data['retained3585_rows']:
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
    assert len(rows) == len({r['source_id'] for r in rows}) == 20
    assert len(old_rows) == len({r['source_id'] for r in old_rows}) == 3585
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
    assert len(removed) == 20 and set(removed) == set(approved)
    assert remaining['pairs'] == prior['remaining']['pairs'] and len(remaining['pairs']) == 25
    held = {r['source_id'] for group in holds.values() for r in group}
    assert len(held) == 58
    remaining_ids = {r['source_id'] for g in remaining['singleton_categories'].values() for r in g['members']}
    assert held <= remaining_ids and len(remaining_ids) == 100
    remaining['supported_singletons'] = 100
    assert remaining['paired_targets'] == 25
    remaining['supported_targets_outside_modern_mapping'] = 125
    result = {'schema_version': 1, 'status': 'GUARDED_PROGRAM20_AGGREGATE_PASS', 'all_shards_complete': True,
        'runtime_sha256': runtime, 'helper_sha256': MEASUREMENT_HELPER_SHA,
        'aggregation_script_sha256': digest(Path(__file__).resolve()), 'prior3788_validation_sha256': PRIOR_SHA,
        'mapping_manifest_sha256': MAPPING_SHA, 'source_review_sha256': SOURCE_REVIEW_SHA,
        'independent_review_sha256': INDEPENDENT_REVIEW_SHA, 'source_tree_sha256': bindings_sha(before),
        'actual_checkout_revisions': [EXPECTED_REVISION], 'code_state': code_state(),
        'coverage': {'prior_retained_singletons': 3585, 'prior_retained_class_targets': 203,
            'new_program_singletons': 20, 'total_singletons': 3605, 'total_class_targets': 203,
            'total_wire_prepared_targets': 3808, 'total_represented_originals': 4011,
            'fresh_new_prepare_calls': 40, 'retained_input_prepare_comparisons': 3585,
            'retained_class_prepare_comparisons': 203, 'new_class_execution_enabled': False},
        'rows': sorted(rows, key=lambda r: source_order(r['source_id'])), 'shards': shards,
        'retained3585_comparison_rows_sha256': sha(encode(sorted(old_rows, key=lambda r: source_order(r['source_id'])))),
        'retained203_class_comparison_rows_sha256': sha(encode(sorted(class_rows, key=lambda r: r['record_target_id']))),
        'all_saved_digests_reverified': True, 'retained_public_file_count': len(frozen), 'retained_profile_file_count': len(profiles),
        'original_hashes_sha256': ORIGINALS_SHA, 'original_files_verified_before_and_after': 4206,
        'source_bindings_unchanged': True, 'source_status_unchanged': prior['source_status_unchanged'],
        'retained_hold_sets': holds, 'alias_source_holds_preserved': True, 'remaining': remaining, 'provider_requests': 0, 'provider_mutations': 0,
        'scope': '20 approved sources freshly classified/prepared twice; all3585 prior singleton wires/full legacy '
                 'metadata/nonruntime evidence and203 pairs once at original paths/time. All4206 originals unchanged. '
                 'Both29 personal and29 program/Unaami holds retained. No class execution, source promotion, remote identity, duplicate absence, '
                 'provider grant, QA/PICES/community approval or release established.'}
    write_json(output, result)
    print(json.dumps({'path': str(output), 'sha256': digest(output), 'coverage': result['coverage'], 'remaining': 125}))


if __name__ == '__main__':
    main()
