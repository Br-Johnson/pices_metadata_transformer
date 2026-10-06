"""Frozen: aggregate four actual citations31 saved receipts only.

Saved-file reads only: no project/helper imports, classification, preparation,
tests or provider calls. Future PASS output requires reviewed frozen bindings
and all four actual successful receipt pins; expectations are not measurements.
Retain complete legacy metadata, original bytes and nonruntime evidence.
"""

import argparse
import copy
import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

# Shared saved-file validation block; no earlier helper or project import.
PRIOR = Path('docs/readiness/2026-10-06/modern_program20_validation.json')
PRIOR_SHA = '23efeba9c464769f8050af26224679aabbe3995c3b725c9ae436b56498a00a8e'
PRIOR_HELPER_SHA = 'f18b89e2d66b78f91b811431bf43484f14cc542974121cd344462fb874da92b8'
PRIOR_AGGREGATE_SHA = 'c0dc12e752f0836077d66ee722347da96b1ec04b99f1ebbf5eb8f497f0d8824a'
PRIOR_RUNTIME = '78e3fdd4f3170a804aa49b25bf4e01586a2a18a5ef914a76b2be9ac4ceb72ea2'
PRIOR_ROOTS = tuple(Path(f'/tmp/pices-program20-shard{i}-v1') for i in range(4))
PRIOR_RECEIPTS = (
    'aea074d5820c620f7a26435d138f21eb009cd7e61a1f3c030e329d5388031f48',
    '66bcf5c3ef6f33b1a14efec4cc3103afda980c10a4905cb3eb8f9243729fa3de',
    'a669d237a405931033fc0a2bd6bb0165d887c3604de218bc64e2bd2423c0cc40',
    'a1e7da43f5bb88863c8a864a8ec7b48d2641c91150bbc9f5982046031a883a78')
GUARD_SHA = '1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05'
ORIGINALS_SHA = '3430315763379ef81c393cca00eb776952df3ad3f66856ef4b15edd48e396013'
MEMBERSHIP_SHA = '1602de63f4dafe4c0eabdf7ab366a955c4e479ed57f1b75680d620f89160bc4b'
CONTEXT_SHA = '0f4282bf079c301a2c1d4d5d18a3740bb501845179d465cc4b8a1691b9121929'
DIRECT_BINDINGS = Path('docs/readiness/2026-10-06/modern_institution91_source_bindings.json')
DIRECT_BINDINGS_SHA = '0cdf17201243f9bdaeaca90c4ae1f46b573d0be9429359942a8b7eb89a73d633'
SOURCE_DOCUMENTS = {
    'basis_proposal': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-basis19-modern-personal-source-proposals.json',
                       'sha256': '3dffa1313c1b31a9950277658df01b334b0632ac204c982054abe1cf54672faf'},
    'basis_review': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-basis19-independent-complete-array-review.json',
                    'sha256': '0f791b51da0294d494053393ba48a40170dbd4f26c049007486d5568e658b7da'},
    'contract_proposal': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-contract-chain9-modern-source-proposals.json',
                          'sha256': '1ee3bc21bb5d02a201a311fe794f503ad4fbb2c89d850c5be75b0aba5e26e9a1'},
    'contract_review': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-contract-chain9-independent-source-review.json',
                        'sha256': '2ce5c267e37168aaa8c8c1202c756a167459c9c031b96e16dc34aa760ff58d83'},
    'direct_primary_evidence': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-direct14-primary-evidence.json',
                                'sha256': '17f91192d3b7d8770134ef587a111bed7821b38ebf50798b288aeba9d23a97e7'},
    'direct_proposal': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-direct14-modern-source-proposals.json',
                        'sha256': '5ce44b703e5b7881e0fb3067cf74ed1ecd90e46d4ff869ead8df4e5cb202d1a0'},
    'direct_review': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-direct14-independent-source-review.json',
                      'sha256': '8caff527a8752db3975470806d88623b3fdc4bd9100ba40a393471c1c4c09597'},
    'office_primary_evidence': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-role-office11-primary-evidence.json',
                                'sha256': '168e1e1aec48c12b0c3210c6b0716edca3a35ea5e3a6452c13b8b4a1af45fb66'},
    'office_proposal': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-role-office11-modern-source-proposals.json',
                        'sha256': '971d4d09365acbd69d4b1c23972bcb30807a61b18dc40665afbfe820b32892cd'},
    'office_review': {'path': 'docs/readiness/2026-10-06/next_source_review/pices-role-office11-independent-source-review.json',
                      'sha256': 'dbde3f4c6a36b9368b75683e21ab9dff1098968285eef0abd9eba896a37fc673'},
}
POLICY = 'modern-xml-reviewed-citations31-v1'
EVIDENCE_SCHEMA = 10
ASSESSMENT_TIME = '2026-10-05T18:00:00+00:00'
NEW_COUNTS, OLD_COUNTS, CLASS_COUNTS = (8, 8, 8, 7), (902, 901, 901, 901), (51, 51, 51, 50)
DRAFT_ONLY = False
MAPPING = Path('docs/readiness/2026-10-06/modern_reviewed_citations31.json')
MAPPING_SHA = '62f32e602ac1389ecdbffb07ed5627b2aadb047d777fd8469295680bb93729cc'
EXPECTED_RUNTIME_SHA = '108fe0804b7e625d431d5510698fdb7a7aa63292cecd10dbcbc853dbe848d713'
EXPECTED_SOURCE_TEST_SHA = '5f784b892c7bb6183d9d46145cde712d37b093ed4607090e21c773fdedf24562'
EXPECTED_SOURCE_TEST_COUNT = 189
# Actual base HEAD beneath frozen staged files; never claim it contains new31 code.
EXPECTED_REVISION = 'c612e0e8e522fcf9ecc993b4b3c64ce12ae1fc53'
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


def retained3808(repo):
    """Load the latest saved program20 outputs; never import old helpers or prepare.

    Each public path is byte-verified once during loading under the frozen manifest.
    A separate complete post-run pass detects changes during the guarded work.
    """
    prior = pin(repo / PRIOR, PRIOR_SHA)
    assert prior['status'] == 'GUARDED_PROGRAM20_AGGREGATE_PASS' and prior['all_shards_complete']
    assert prior['helper_sha256'] == PRIOR_HELPER_SHA and prior['runtime_sha256'] == PRIOR_RUNTIME
    assert prior['aggregation_script_sha256'] == PRIOR_AGGREGATE_SHA
    assert digest(repo / 'docs/readiness/2026-10-06/measure_modern_program20_coverage.py') == PRIOR_HELPER_SHA
    assert digest(repo / 'docs/readiness/2026-10-06/aggregate_modern_program20_coverage.py') == PRIOR_AGGREGATE_SHA
    assert prior['coverage']['total_wire_prepared_targets'] == 3808
    assert prior['coverage']['total_singletons'] == 3605 and prior['coverage']['total_class_targets'] == 203
    assert prior['original_hashes_sha256'] == ORIGINALS_SHA
    assert len(prior['remaining']['protected_identity_preservation']) == 5
    proof20 = {row['source_id']: row for row in prior['rows']}
    assert len(proof20) == len(prior['rows']) == 20
    frozen, profiles, singles, classes, receipts = {}, {}, {}, {}, []
    previous_file_manifest = None
    old_rows, class_rows, verified = [], [], {}

    def verify_once(path, wanted):
        key = str(path)
        if key in verified:
            assert verified[key] == wanted
        else:
            assert digest(Path(path)) == wanted
            verified[key] = wanted

    def track(path, wanted, newly_saved=False):
        path = Path(path)
        if newly_saved:
            assert any(path.is_relative_to(root) for root in PRIOR_ROOTS)
        else:
            # Existing baseline paths are permitted only by exact inherited pins.
            assert str(path) in frozen and frozen[str(path)] == wanted
        assert str(path) not in frozen or frozen[str(path)] == wanted
        verify_once(path, wanted)
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
                # Latest program20 inputs reference the existing public main profile paths.
                prefix = Path('/workspace/pices-main/docs/readiness')
                assert public.is_relative_to(prefix)
                relative = public.relative_to(prefix)
                assert str(relative) in PROFILE_RELATIVES
                verify_once(repo / 'docs/readiness' / relative, wanted)
            verify_once(public, wanted)
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
        assert receipt['status'] == 'GUARDED_PROGRAM20_SHARD_COVERAGE_PASS'
        assert receipt['guard_sha256'] == GUARD_SHA
        assert receipt['environment_cleared_dummy_credentials_only']
        assert receipt['guard']['bootstrap'] == {'network': 4, 'private_reads': 1, 'processes': 1, 'writes': 1}
        assert receipt['wire_artifact_manifest_sha256'] == shard['artifact_manifest_sha256']
        assert receipt['retained_file_manifest_sha256'] == shard['retained_file_manifest_sha256']
        assert receipt['classification_sha256'] == shard['classification_sha256']
        assert receipt['runtime_sha256'] == PRIOR_RUNTIME and receipt['helper_sha256'] == PRIOR_HELPER_SHA
        assert receipt['original_hashes_sha256'] == ORIGINALS_SHA and receipt['original_files_verified_before_and_after'] == 4206
        assert receipt['source_bindings_unchanged'] and receipt['retained_paths_and_bytes_unchanged']
        assert receipt['all3788_retained_file_hashes_verified_before_and_after']
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert not receipt['unexpected_guard_events'] and not any(receipt['guard']['tests'].values())
        assert receipt['prepared_root'] == str(root / 'prepared')
        assert receipt['assessment_time'] == ASSESSMENT_TIME
        track(root / 'prepared/classification.json', shard['classification_sha256'], True)
        assert [r['source_id'] for r in data['program20_rows']] == receipt['sharding']['assigned_new_source_ids']
        assert [r['source_id'] for r in data['retained3585_rows']] == receipt['sharding']['assigned_retained_source_ids']
        assert [r['record_target_id'] for r in data['retained203_class_rows']] == receipt['sharding']['assigned_retained_class_ids']
        assert len(data['program20_rows']) == 5
        assert len(data['retained3585_rows']) == (897, 896, 896, 896)[index]
        assert len(data['retained203_class_rows']) == CLASS_COUNTS[index]
        receipts.append(receipt)
        for row in data['retained3585_rows']:
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
        for row in data['program20_rows']:
            sid = row['source_id']
            assert sid not in singles and proof20[sid] == row | {'shard_index': index}
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
    assert len(previous_file_manifest['public_baseline_files']) == prior['retained_public_file_count'] == 39232
    assert len(previous_file_manifest['exact_public_profile_files']) == prior['retained_profile_file_count'] == 32
    assert sha(encode(previous_file_manifest['public_baseline_files'])) == 'bd067524796237dbf8a666c98d68bbba3dca812035d15b3ebddfc47dacf1001a'
    # 4 receipts/manifests/classifications per shard, 3788 fresh comparison
    # packets, and five files for each of the newly retained20 sources.
    assert len(frozen) == 39232 + 4 * 4 + 3788 + 5 * 20 == 43136
    assert len(profiles) == 32
    assert sha(encode(profiles)) == '239115dbb1b4c695812a2d51563a53227dbcb4ea11c10fcd1153f25217fcfa2d'
    for path, wanted in profiles.items():
        relative = path.split('/docs/readiness/', 1)[1]
        assert relative in PROFILE_RELATIVES
        verify_once(repo / 'docs/readiness' / relative, wanted)
    assert len(receipts[0]['policy_input_bindings']) == 47
    assert len(singles) == 3605 and len(classes) == 203
    assert len({sid for c in classes.values() for sid in c['source_ids']}) == 406
    assert not set(singles) & {sid for c in classes.values() for sid in c['source_ids']}
    assert sha(encode(sorted(old_rows, key=lambda r: source_order(r['source_id'])))) == prior['retained3585_comparison_rows_sha256']
    assert sha(encode(sorted(class_rows, key=lambda r: r['record_target_id']))) == prior['retained203_class_comparison_rows_sha256']
    for key in ('source_bindings_before', 'runtime_sha256', 'policy_input_bindings', 'original_hashes', 'assessment_time'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    for path, wanted in (frozen | profiles).items():
        verify_once(path, wanted)
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
             DIRECT_BINDINGS_SHA, CONTEXT_SHA, MEMBERSHIP_SHA)):
        raise RuntimeError('Disabled draft: finalize exact inputs, independent helper review and code freeze first')
    if not __debug__ or not isinstance(EXPECTED_SOURCE_TEST_COUNT, int):
        raise RuntimeError('Assertions and an exact frozen source/test file count are required')
    if not isinstance(EXPECTED_REVISION, str) or len(EXPECTED_REVISION) != 40 or not all(c in '0123456789abcdef' for c in EXPECTED_REVISION):
        raise RuntimeError('Exact base HEAD of the frozen staged working tree is required')


def code_state():
    return {'kind': 'frozen_staged_working_tree', 'base_revision': EXPECTED_REVISION,
            'base_revision_is_new31_code_commit': False, 'runtime_sha256': EXPECTED_RUNTIME_SHA,
            'source_tree_sha256': EXPECTED_SOURCE_TEST_SHA, 'source_tree_file_count': EXPECTED_SOURCE_TEST_COUNT}


def write_json(path, value):
    # Additive output only; never update a retained receipt.
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def public_roots(frozen):
    roots = {Path('/tmp') / Path(path).relative_to('/tmp').parts[0] for path in frozen}
    assert len(roots) == 33 and all(root != Path('/tmp') for root in roots)
    assert set(PRIOR_ROOTS) <= roots
    return roots


def fingerprint(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def utf8_sha(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def hold_sets(repo, manifest):
    """Derive exact remaining membership; never change source eligibility."""
    prior = pin(repo / PRIOR, PRIOR_SHA)
    approved = {m['source_id'] for m in manifest['members']}
    prior_members = [m for group in prior['remaining']['singleton_categories'].values() for m in group['members']]
    assert len(prior_members) == len({m['source_id'] for m in prior_members}) == 100
    remaining = sorted((m for m in prior_members if m['source_id'] not in approved),
                       key=lambda m: source_order(m['source_id']))
    old = prior['retained_hold_sets']
    personal = [m for m in old['personal29'] if m['source_id'] not in approved]
    program = [m for m in old['program_unaami29'] if m['source_id'] not in approved]
    assert len(remaining) == 69 and len(personal) == 26 and len(program) == 29
    assert {m['source_id'] for m in personal + program} <= {m['source_id'] for m in remaining}
    return {'remaining_singletons69': remaining, 'prior_personal26': personal, 'prior_program_unaami29': program}


def pointed(document, pointer):
    assert isinstance(pointer, str) and re.fullmatch(
        r'/(source_rows|rows|complete_array_decisions|source_decisions)/[0-9]+', pointer)
    collection, index = pointer[1:].split('/')
    return document[collection][int(index)]


def approved31(repo):
    documents = {key: pin(repo / value['path'], value['sha256']) for key, value in SOURCE_DOCUMENTS.items()}
    manifest = pin(repo / MAPPING, MAPPING_SHA)
    plans = {row['record_target_id']: row for row in pin(repo / PLAN, PLAN_SHA)['targets']}
    approved = []
    for prefix, count in (('basis', 3), ('contract', 8), ('office', 10), ('direct', 10)):
        review = documents[prefix + '_review']
        members = ([{'source_id': sid, 'source_sha256': plans[sid]['source_sha256']}
                    for sid in review['approved_source_ids']] if prefix == 'direct' else review['approved_members'])
        assert len(members) == count
        approved.extend(members)
    approved.sort(key=lambda m: source_order(m['source_id']))
    assert len(approved) == len({m['source_id'] for m in approved}) == 31
    assert manifest['members'] == approved and sha(encode(approved)) == MEMBERSHIP_SHA
    rows = {row['source_id']: row for row in manifest['rows']}
    assert len(rows) == len(manifest['rows']) == 31 and set(rows) == {m['source_id'] for m in approved}
    return documents, manifest, rows


def authority(row, repo):
    profile = pin(repo / PROFILE, PROFILE_SHA)
    sid = row['source_id']
    member = {'source_id': sid, 'source_sha256': row['source_sha256']}
    matches = [c for c in profile['cohorts'] if member in c['members']]
    if row['creator_authority_kind'] == 'creator426':
        assert len(matches) == 1
        cohort = matches[0]
        assert cohort['profile'] == row['creator_cohort'] and cohort['creators'] == row['creators']
        assert sha(encode(cohort)) == row['creator_authority_object_sha256']
        return 'creator426', cohort['profile'], PROFILE_SHA
    assert row['creator_authority_kind'] == 'direct' and row['creator_cohort'] is None
    assert not matches and not any(m['source_id'] == sid for c in profile['cohorts'] for m in c['members'])
    bindings = pin(repo / DIRECT_BINDINGS, DIRECT_BINDINGS_SHA)['members']
    direct = [r for r in bindings if r['source_id'] == sid]
    assert len(direct) == 1 and direct[0]['source_sha256'] == row['source_sha256']
    assert direct[0]['complete_creator_objects'] == row['creators']
    assert sha(encode(direct[0])) == row['creator_authority_object_sha256']
    return 'direct', None, MAPPING_SHA


def reviewed_manifest(repo, documents, rows):
    manifest = pin(repo / MAPPING, MAPPING_SHA)
    header = {'schema_version': 1, 'kind': 'modern-reviewed-citations31-v1', 'policy': POLICY,
        'source_plan_sha256': PLAN_SHA, 'creator426_profile_sha256': PROFILE_SHA,
        'direct_binding_sha256': DIRECT_BINDINGS_SHA, 'source_documents': SOURCE_DOCUMENTS,
        'member_count': 31, 'partition_counts': {'basis3': 3, 'contract8': 8, 'office10': 10, 'direct10': 10},
        'authority_counts': {'creator426': 3, 'direct': 28}, 'members': manifest['members'],
        'membership_sha256': MEMBERSHIP_SHA, 'complete_vector_count': 19,
        'modern_creator_object_count': 65, 'context_sha256': CONTEXT_SHA}
    assert manifest == header | {'rows': list(rows.values())}
    assert sha(encode({sid: row['additional_preservation_paragraphs'] for sid, row in rows.items()})) == CONTEXT_SHA
    plans = {r['record_target_id']: r for r in pin(repo / PLAN, PLAN_SHA)['targets']}
    for member in manifest['members']:
        sid, row = member['source_id'], rows[member['source_id']]
        prefix = {'basis3': 'basis', 'contract8': 'contract', 'office10': 'office', 'direct10': 'direct'}[row['projection_partition']]
        assert row['source_proposal_document'] == prefix + '_proposal'
        assert row['source_review_document'] == prefix + '_review'
        proposed = pointed(documents[prefix + '_proposal'], row['proposal_row_pointer'])
        independent = pointed(documents[prefix + '_review'], row['independent_decision_pointer'])
        assert sha(encode(proposed)) == row['proposal_row_sha256']
        assert sha(encode(independent)) == row['independent_decision_sha256']
        original = (repo / 'FGDC' / (sid + '.xml')).read_bytes()
        root = ET.fromstring(original)
        current_root = source_node(root)
        origins = [source_node(node) for node in root.findall('./idinfo/citation/citeinfo/origin')]
        assert proposed['source_id'] == sid
        assert sha(original) == row['source_sha256'] == member['source_sha256']
        assert row['source_path'] == 'FGDC/' + sid + '.xml' and len(original) == row['source_bytes']
        assert sha(encode(current_root)) == row['source_root_sha256']
        assert origins == row['primary_origins']
        if prefix in ('basis', 'contract'):
            assert member in independent['members']
            assert current_root == proposed['source_root'] and origins == proposed['primary_origin_elements']
            assert len(original) == proposed['source_bytes'] and sha(original) == proposed['source_sha256']
            assert row['creators'] == proposed['complete_legacy_creators'] == independent[
                'complete_current_legacy_creators' if prefix == 'basis' else 'complete_legacy_creators']
            modern = independent['approved_complete_modern_creators']
            assert modern == proposed['proposed_complete_modern_creators']
            verdict = ('APPROVE_FINITE_COMPLETE_ARRAY_SOURCE_PROJECTION_WITH_EXPLICIT_BOUNDARY_INFERENCE'
                       if prefix == 'basis' else 'APPROVE_FINITE_COMPLETE_ARRAY_SOURCE_ONLY')
            assert independent['verdict'] == verdict
            if prefix == 'basis':
                assert proposed['complete_current_creator426_cohort']['creators'] == row['creators']
                assert sha(encode(proposed['complete_current_creator426_cohort'])) == row['creator_authority_object_sha256']
            else:
                assert row['additional_preservation_paragraphs'] == [proposed['required_full_citation_and_role_preservation_text']]
        elif prefix == 'office':
            assert original == proposed['complete_original_xml'].encode()
            assert independent['source_id'] == sid and independent['source_sha256'] == sha(original)
            assert independent['decision'] == 'APPROVE_EXACT_QUALIFIED_ORGANIZATIONAL_CREDIT'
            assert row['creators'] == proposed['complete_legacy_creators'] == independent['complete_legacy_creators']
            modern = independent['complete_approved_modern_creators']
            assert modern == proposed['proposed_complete_modern_creators']
            assert row['additional_preservation_paragraphs'] == [independent['required_preservation_note']]
        else:
            assert current_root == proposed['complete_source_root'] and origins == proposed['primary_origin_elements']
            assert sha(original) == proposed['source_binding']['source_sha256']
            assert len(original) == proposed['source_binding']['source_bytes']
            assert independent['source_id'] == sid and independent['decision'] == 'APPROVE_EXACT_COMPLETE_SOURCE_PROJECTION'
            assert row['creators'] == proposed['retained_legacy']['full_payload']['metadata']['creators'] == independent['complete_legacy_creators']
            modern = independent['approved_modern_creators']
            assert modern == proposed['proposed_modern_creators']
        assert modern == row['reviewed_source_creators']
        service = json.loads(encode(modern))
        if prefix == 'direct':
            for creator in service:
                person = creator['person_or_org']
                assert set(person) == {'type', 'family_name', 'given_names'} and person['type'] == 'personal'
                person['given_name'] = person.pop('given_names')
        assert service == row['modern_creators']
        target = plans[sid]
        assert sha(encode(target)) == row['source_plan_target_sha256']
        assert target['source_ids'] == [sid] and target['source_semantic_status'] == 'supported'
        assert target['source_sha256'] == member['source_sha256']
        assert target['identity_decision']['production_record_id'] is None
        assert target['identity_decision']['production_doi'] is None
        assert all(target[k] is False for k in ('executable', 'upload_eligible', 'remote_verified', 'publication_approved'))
        authority(row, repo)
    assert len({sha(encode(r['modern_creators'])) for r in rows.values()}) == 19
    assert sum(len(r['modern_creators']) for r in rows.values()) == 65
    assert sum(r['creator_authority_kind'] == 'creator426' for r in rows.values()) == 3
    return manifest


def historical_metadata(repo, source):
    """Use the pinned source packet's complete old metadata, not its old path."""
    reference = SOURCE_DOCUMENTS[source['source_proposal_document']]
    proposal = pointed(pin(repo / reference['path'], reference['sha256']), source['proposal_row_pointer'])
    assert sha(encode(proposal)) == source['proposal_row_sha256']
    partition = source['projection_partition']
    if partition == 'direct10':
        old = proposal['retained_legacy']['full_payload']['metadata']
    elif partition == 'office10':
        old = proposal['historical_raw_payload']['complete_metadata']
    else:
        old = proposal['historical_public_raw_metadata_preservation_example']['complete_metadata']
    assert isinstance(old, dict) and old['creators'] == source['creators']
    return old


def check_new_wire(wire, metadata, source, repo):
    check_wire(wire, metadata, source['modern_creators'])
    # Source-policy schema10 adds exact reviewed context before the untouched JSON block.
    label = ('Legacy assembled metadata, preserved without field loss. Publisher values in this '
             'block are legacy mapping values, not independently source-attested publishers. '
             'The current publisher Zenodo identifies the repository hosting this restored XML '
             'artifact. Its publication date is the approved source metadata date, not the date '
             'of hosting on Zenodo. Underlying dataset citation and access conditions remain '
             'source evidence; no new license is granted.')
    context = ''.join('<p>' + html.escape(text) + '</p>' for text in source['additional_preservation_paragraphs'])
    assert wire['metadata']['additional_descriptions'] == [{'type': {'id': 'other'}, 'description':
        '<p>' + label + '</p>' + context + '<pre>' + html.escape(encode(metadata).decode()) + '</pre>'}]
    # Full raw metadata is checked separately; date/access cannot normalize away.
    old = historical_metadata(repo, source)
    for key in ('publication_date', 'access_right', 'license', 'access_conditions'):
        assert metadata.get(key) == old.get(key)


def expected_normalized_metadata(raw_metadata, original, artifact_sha):
    """Independent, finite existing XML-artifact envelope; no source reclassification."""
    metadata = json.loads(encode(raw_metadata))
    legacy_note = ('Record is migrated FGDC metadata from the archived PICES GeoNetwork '
                   'metadata catalogue; dataset is metadata-only.')
    migration_note = ('Record includes migrated FGDC metadata from the archived PICES GeoNetwork '
                      'metadata catalogue; deposited research-data availability is classified separately.')
    notes = (metadata.get('notes', '') or '').replace(legacy_note, '').strip()
    parts = [notes] if notes else []
    if migration_note not in notes:
        parts.append(migration_note)
    xml = original.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').strip()
    xml_block = 'Original FGDC metadata (XML):\n\n```xml\n' + xml + '\n```'
    if xml_block not in notes:
        parts.append(xml_block)
    metadata['notes'] = '\n\n'.join(parts).strip()
    tags = {'pices-metadata-only', 'pices-data-included', 'pices-content-mixed', 'pices-content-unknown'}
    metadata['keywords'] = [word for word in metadata.get('keywords', []) if word.strip().casefold() not in tags]
    metadata['keywords'].append('pices-metadata-only')
    content_notes = (
        'Deposited content: descriptive metadata only; underlying research data are not included.',
        'Deposited content: research data are included for the described scope.',
        'Deposited content: research data are included for part of the described scope; other content is descriptive metadata only.',
        'Deposited content: availability of underlying research data in this deposit has not been verified.')
    description = metadata.get('description', '') or ''
    for note in content_notes:
        description = description.replace('<p>' + note + '</p>', '').replace(note, '')
    metadata['description'] = description.strip() + '\n\n<p>' + content_notes[0] + '</p>'
    artifact_note = ('Deposited object: original FGDC XML metadata artifact; underlying research data are not included. '
                     'Artifact contract SHA-256: ' + artifact_sha)
    if artifact_note not in metadata['notes']:
        metadata['notes'] += '\n\n' + artifact_note
    return metadata


def expected_new_evidence(repo, sid, source, metadata, payload, input_sha, wire_sha, runtime, manifest):
    original = (repo / 'FGDC' / (sid + '.xml')).read_bytes()
    policy, classification = payload['artifact_policy'], dict(payload['content_classification'])
    kind, cohort, profile_sha = authority(source, repo)
    assert policy['schema_version'] == 1 and policy['object_kind'] == 'original_fgdc_xml'
    assert policy['source_sha256'] == sha(original) and policy['resource_type'] == 'other'
    assert policy['reviewed_at'] == classification['reviewed_at'] == ASSESSMENT_TIME
    if kind == 'creator426':
        assert profile_sha == PROFILE_SHA
        assert policy['creator_interpretation']['manifest_sha256'] == PROFILE_SHA
    else:
        assert kind == 'direct' and profile_sha == MAPPING_SHA
        assert 'creator_interpretation' not in policy
    assert payload['metadata'] == historical_metadata(repo, source)
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
    assert metadata == expected_normalized_metadata(payload['metadata'], original, artifact['sha256'])
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
    check_new_wire(wire, metadata, source, repo)
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
MEASUREMENT_HELPER = Path('docs/readiness/2026-10-06/measure_modern_reviewed_citations31_coverage.py')
MEASUREMENT_HELPER_SHA = '92ad83deb2d4ea71d62819e70b61ee3a5985275e9014d3af69b2e4a76f1e6982'
RECEIPT_SHAS = ('568c486be74f1901b18e032377d8fb3c1505794c3944900b1e5d66c30b3f6cdb', '21bce3e3427e279130fcba9e22d5e86a579df05612e86ef41deaf5dea17ebe60', '064af9613f78bc318e3d155307b0bc28a61afe0942bf7360e5f5e6e1f02b86ea', '595ab244a4ce9e25d0409b852d8a844ae00a86ca5da1e56560a7add2f82795dc')


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
    if len(RECEIPT_SHAS) != 4 or not all(valid_sha(value) for value in (MEASUREMENT_HELPER_SHA, *RECEIPT_SHAS)):
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
    prior, singles, classes, frozen, profiles, previous = retained3808(repo)
    baseline_roots = public_roots(frozen)
    assert all(not a.is_relative_to(b) and not b.is_relative_to(a) for a in roots for b in baseline_roots)
    assert not any(output.is_relative_to(root) for root in set(roots) | baseline_roots)
    documents, manifest, approved = approved31(repo)
    assert reviewed_manifest(repo, documents, approved) == manifest
    holds = hold_sets(repo, manifest)
    prior_remaining = {m['source_id'] for g in prior['remaining']['singleton_categories'].values() for m in g['members']}
    assert len(prior_remaining) == 100 and set(approved) <= prior_remaining
    assert all({m['source_id'] for m in group} <= prior_remaining for group in holds.values())
    assert not set(approved) & (set(singles) | {sid for c in classes.values() for sid in c['source_ids']})
    assert not set(approved) & {m['source_id'] for group in holds.values() for m in group}
    assert prior['source_status_unchanged']['supported_targets'] == 3933
    assert prior['source_status_unchanged']['source_promotions'] == 0
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
    assert len(SOURCE_DOCUMENTS) == 10
    assert len({entry['path'] for entry in SOURCE_DOCUMENTS.values()}) == 10
    source_documents_sha = sha(encode(SOURCE_DOCUMENTS))
    independent_review_document_shas = {key: value['sha256'] for key, value in SOURCE_DOCUMENTS.items()
                                        if key.endswith('_review')}
    expected_policy.update({str(MAPPING): MAPPING_SHA, str(PRIOR): PRIOR_SHA,
                           str(DIRECT_BINDINGS): DIRECT_BINDINGS_SHA})
    expected_policy.update({entry['path']: entry['sha256'] for entry in SOURCE_DOCUMENTS.values()})
    expected_policy.update({'docs/readiness/' + relative: digest(repo / 'docs/readiness' / relative)
                            for relative in PROFILE_RELATIVES})
    all_new, all_old, all_classes = sorted(approved, key=source_order), sorted(singles, key=source_order), sorted(classes)
    assert (len(all_new), len(all_old), len(all_classes)) == (31, 3605, 203)
    assert NEW_COUNTS == (8, 8, 8, 7) and OLD_COUNTS == (902, 901, 901, 901)
    assert CLASS_COUNTS == (51, 51, 51, 50)
    rows, old_rows, class_rows, receipts, shards = [], [], [], [], []
    saved_digests = {}

    def saved_pin(path, wanted):
        assert str(path) not in saved_digests or saved_digests[str(path)] == wanted
        saved_digests[str(path)] = wanted
        return pin(path, wanted)

    for index, root in enumerate(roots):
        receipt = saved_pin(root / 'coverage.json', RECEIPT_SHAS[index])
        receipts.append(receipt)
        assert receipt['status'] == 'GUARDED_CITATIONS31_SHARD_COVERAGE_PASS'
        assert receipt['helper_sha256'] == MEASUREMENT_HELPER_SHA and receipt['runtime_sha256'] == runtime
        assert receipt['actual_checkout_revision'] == EXPECTED_REVISION
        assert receipt['code_state'] == code_state()
        assert receipt['guard_sha256'] == GUARD_SHA and receipt['prior3808_validation_sha256'] == PRIOR_SHA
        assert receipt['mapping_manifest_sha256'] == MAPPING_SHA
        assert receipt['source_documents_sha256'] == source_documents_sha
        assert receipt['independent_review_document_sha256s'] == independent_review_document_shas
        assert receipt['policy'] == POLICY and receipt['evidence_schema_version'] == EVIDENCE_SCHEMA
        assert receipt['source_bindings_before'] == before and receipt['source_tree_sha256'] == EXPECTED_SOURCE_TEST_SHA
        assert receipt['original_hashes'] == originals and receipt['original_hashes_sha256'] == ORIGINALS_SHA
        assert receipt['original_files_verified_before_and_after'] == 4206
        assert receipt['source_bindings_unchanged'] and receipt['environment_cleared_dummy_credentials_only']
        assert receipt['retained_paths_and_bytes_unchanged'] and receipt['all3808_retained_file_hashes_verified_before_and_after']
        assert receipt['retained_file_count'] == len(frozen) == 43136
        assert receipt['exact_public_profile_file_count'] == len(profiles) == 32
        assert receipt['provider_requests'] == receipt['provider_mutations'] == 0
        assert not receipt['unexpected_guard_events'] and not any(receipt['guard']['tests'].values())
        assert receipt['guard']['bootstrap'] == {'network': 4, 'private_reads': 1, 'processes': 1, 'writes': 1}
        assert receipt['assessment_time'] == ASSESSMENT_TIME
        assert receipt['source_status_unchanged'] == prior['source_status_unchanged']
        assert receipt['retained_class_alias_holds_preserved'] and receipt['retained_hold_sets'] == holds
        assert receipt['fresh_classification_assigned_citations31_members']
        assert receipt['policy_input_bindings'] == expected_policy
        for relative, wanted in expected_policy.items():
            assert digest(inside(repo, relative)) == wanted
        assigned = receipt['sharding']
        new_ids, old_ids, class_ids = all_new[index::4], all_old[index::4], all_classes[index::4]
        assert assigned['index'] == index and assigned['count'] == 4 and assigned['all_shards_complete_claimed'] is False
        assert assigned['new_manifest_members'] == 31 and assigned['retained_baseline_members'] == 3605
        assert assigned['retained_baseline_classes'] == 203
        assert assigned['sorted_new_ids_sha256'] == sha(encode(all_new))
        assert assigned['sorted_retained_ids_sha256'] == sha(encode(all_old))
        assert assigned['sorted_retained_class_ids_sha256'] == sha(encode(all_classes))
        assert assigned['assigned_new_source_ids'] == new_ids and assigned['assigned_retained_source_ids'] == old_ids
        assert assigned['assigned_retained_class_ids'] == class_ids
        assert assigned['actual_new_preparations'] == len(new_ids) == NEW_COUNTS[index]
        assert assigned['actual_fresh_classifications'] == len(new_ids)
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
        assert [r['source_id'] for r in data['citations31_rows']] == new_ids
        assert [r['source_id'] for r in data['retained3605_rows']] == old_ids
        assert [r['record_target_id'] for r in data['retained203_class_rows']] == class_ids
        for row in data['citations31_rows']:
            verify_new(repo, root, row, approved[row['source_id']], manifest, runtime)
            for path_key, sha_key in (('prepared_input_path', 'prepared_input_sha256'), ('wire_path', 'wire_sha256'),
                                      ('preparation_path', 'preparation_sha256'), ('original_copy_path', 'source_sha256')):
                saved_digests[str(inside(root, row[path_key]))] = row[sha_key]
            saved_digests[str(root / 'sources' / (row['source_id'] + '.xml'))] = row['source_sha256']
            rows.append(row | {'shard_index': index})
        for row in data['retained3605_rows']:
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
    assert len(rows) == len({r['source_id'] for r in rows}) == 31
    assert len(old_rows) == len({r['source_id'] for r in old_rows}) == 3605
    assert len(class_rows) == len({r['record_target_id'] for r in class_rows}) == 203
    for key in ('source_bindings_before', 'runtime_sha256', 'helper_sha256', 'policy_input_bindings',
                'original_hashes', 'original_hashes_sha256', 'actual_checkout_revision'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    assert all(digest(Path(path)) == wanted for path, wanted in (frozen | profiles | saved_digests).items())
    assert all(digest(inside(repo, relative)) == wanted for relative, wanted in expected_policy.items())
    assert digest(repo / MEASUREMENT_HELPER) == MEASUREMENT_HELPER_SHA
    assert before == source_tree_bindings(repo)
    assert originals == {p.name: digest(p) for p in sorted((repo / 'FGDC').glob('*.xml'))}
    remaining = copy.deepcopy(prior['remaining'])
    removed = []
    for group in remaining['singleton_categories'].values():
        removed.extend(r['source_id'] for r in group['members'] if r['source_id'] in approved)
        group['members'] = [r for r in group['members'] if r['source_id'] not in approved]
        group['count'] = len(group['members'])
        group['membership_sha256'] = sha(encode(group['members']))
    assert len(removed) == 31 and set(removed) == set(approved)
    assert remaining['pairs'] == prior['remaining']['pairs'] and len(remaining['pairs']) == 25
    assert remaining['protected_identity_preservation'] == prior['remaining']['protected_identity_preservation']
    assert len(remaining['protected_identity_preservation']) == 5
    held = {r['source_id'] for group in holds.values() for r in group}
    remaining_ids = {r['source_id'] for g in remaining['singleton_categories'].values() for r in g['members']}
    assert held <= remaining_ids and len(remaining_ids) == 69
    assert {r['source_id'] for r in holds['remaining_singletons69']} == remaining_ids
    assert len(holds['prior_personal26']) == 26 and len(holds['prior_program_unaami29']) == 29
    remaining['supported_singletons'] = 69
    assert remaining['paired_targets'] == 25
    remaining['supported_targets_outside_modern_mapping'] = 94
    assert 3636 + 203 + remaining['supported_targets_outside_modern_mapping'] == 3933
    result = {'schema_version': 1, 'status': 'GUARDED_CITATIONS31_AGGREGATE_PASS', 'all_shards_complete': True,
        'runtime_sha256': runtime, 'helper_sha256': MEASUREMENT_HELPER_SHA,
        'aggregation_script_sha256': digest(Path(__file__).resolve()), 'prior3808_validation_sha256': PRIOR_SHA,
        'mapping_manifest_sha256': MAPPING_SHA, 'source_documents_sha256': source_documents_sha,
        'independent_review_document_sha256s': independent_review_document_shas, 'source_tree_sha256': bindings_sha(before),
        'actual_checkout_revisions': [EXPECTED_REVISION], 'code_state': code_state(),
        'coverage': {'prior_retained_singletons': 3605, 'prior_retained_class_targets': 203,
            'new_citations31_singletons': 31, 'total_singletons': 3636, 'total_class_targets': 203,
            'total_wire_prepared_targets': 3839, 'total_represented_originals': 4042,
            'fresh_new_classifications': 31, 'fresh_new_prepare_calls': 62,
            'retained_input_prepare_comparisons': 3605,
            'retained_class_prepare_comparisons': 203, 'new_class_execution_enabled': False},
        'rows': sorted(rows, key=lambda r: source_order(r['source_id'])), 'shards': shards,
        'retained3605_comparison_rows_sha256': sha(encode(sorted(old_rows, key=lambda r: source_order(r['source_id'])))),
        'retained203_class_comparison_rows_sha256': sha(encode(sorted(class_rows, key=lambda r: r['record_target_id']))),
        'all_saved_digests_reverified': True, 'retained_public_file_count': len(frozen), 'retained_profile_file_count': len(profiles),
        'original_hashes_sha256': ORIGINALS_SHA, 'original_files_verified_before_and_after': 4206,
        'source_bindings_unchanged': True, 'source_status_unchanged': prior['source_status_unchanged'],
        'retained_hold_sets': holds, 'alias_source_holds_preserved': True, 'remaining': remaining, 'provider_requests': 0, 'provider_mutations': 0,
        'scope': '31 citations31 approved sources freshly classified once and prepared twice; all 3605 prior singleton wires/full legacy '
                 'metadata/nonruntime evidence and 203 pairs once at original paths/time. All 4206 originals unchanged. '
                 'All 69 remaining singleton members, 25 remaining pair targets and five protected entries retained. '
                 'Prior personal26 and program/Unaami29 subsets retained. No class execution, source promotion, remote identity, duplicate absence, '
                 'provider grant, QA/PICES/community approval or release established.'}
    write_json(output, result)
    print(json.dumps({'path': str(output), 'sha256': digest(output), 'coverage': result['coverage'], 'remaining': 94}))


if __name__ == '__main__':
    main()
