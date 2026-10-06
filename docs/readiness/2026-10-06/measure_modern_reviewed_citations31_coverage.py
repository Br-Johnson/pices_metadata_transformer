"""Finite citations31 guarded measurement at exact frozen bindings.

Each of31 is freshly classified once and prepared twice. Prior3605 singletons and203 pairs
are prepared once from exact historical inputs/times. Full legacy metadata, wire
and all nonruntime evidence remain exact. Prior helpers are never imported.
Parent's separate first10 focused smoke precedes this four-shard measurement.
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

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
    directory = output / 'citations31'
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
        assert selected['creators'] == source['creators']
        assert selected['modern_creators'] == source['modern_creators']
        assert selected['creator_authority_kind'] == kind
        assert fields == {'schema_version': EVIDENCE_SCHEMA, 'policy': POLICY,
                          'mapping_manifest_sha256': MAPPING_SHA, 'creator_authority_kind': kind,
                          'creator_cohort': cohort}
        current, repeated = mapping.prepare(json_file, paths), mapping.prepare(json_file, paths)
        assert current == repeated and raw == json_file.read_bytes()
        metadata, source_sha, artifact, _ = assess(json_file, paths)
        assert payload['metadata']['creators'] == metadata['creators'] == source['creators']
        assert current.evidence == expected_new_evidence(mapping.ROOT, sid, source, metadata, payload,
                                                        sha(raw), sha(current.body), EXPECTED_RUNTIME_SHA, manifest)
        assert current.evidence['artifact_contract'] == artifact
        assert current.evidence['creator_profile_sha256'] == profile_sha
        assert current.binding == sha(encode(current.evidence))
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        check_new_wire(json.loads(current.body), metadata, source, mapping.ROOT)
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
            print('NEW_CITATIONS31_PROGRESS', index, 'of', len(ids), flush=True)
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
    prior, retained, classes, frozen, profiles, previous = retained3808(repo)
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
    source, review, approved = approved31(repo)
    manifest = reviewed_manifest(repo, source, approved)
    holds = hold_sets(repo, review)
    prior_remaining = {m['source_id'] for g in prior['remaining']['singleton_categories'].values() for m in g['members']}
    assert all({m['source_id'] for m in group} <= prior_remaining for group in holds.values())
    assert mapping.CITATIONS31_POLICY == POLICY and mapping.CITATIONS31 == repo / MAPPING
    assert mapping.CITATIONS31_SHA == MAPPING_SHA and mapping.CITATIONS31_CONTEXT_SHA == CONTEXT_SHA
    assert mapping.CITATIONS31_DOCUMENTS == SOURCE_DOCUMENTS
    assert mapping.CITATIONS31_DIRECT_BINDINGS == repo / DIRECT_BINDINGS
    assert mapping.CITATIONS31_DIRECT_BINDINGS_SHA == DIRECT_BINDINGS_SHA
    assert not set(approved) & (set(retained) | {sid for c in classes.values() for sid in c['source_ids']})
    assert set(approved) <= {m['source_id'] for g in prior['remaining']['singleton_categories'].values() for m in g['members']}
    assert all(digest(inside(repo, relative)) == wanted
               for relative, wanted in previous['policy_input_bindings'].items())
    policy_inputs = {repo / relative: wanted for relative, wanted in previous['policy_input_bindings'].items()}
    policy_inputs.update({repo / MAPPING: MAPPING_SHA, repo / PRIOR: PRIOR_SHA,
                         repo / DIRECT_BINDINGS: DIRECT_BINDINGS_SHA})
    policy_inputs.update({repo / value['path']: value['sha256'] for value in SOURCE_DOCUMENTS.values()})
    # Preserve every current source-authority profile alongside all47 old policy bindings.
    policy_inputs.update({repo / 'docs/readiness' / relative: digest(repo / 'docs/readiness' / relative)
                         for relative in PROFILE_RELATIVES})
    assert all(path.is_relative_to(repo) and path.resolve() == path for path in policy_inputs)
    assert all(digest(path) == wanted for path, wanted in policy_inputs.items())
    assert all(digest(repo / 'contracts/schemas/zenodo-modern' / name) == wanted for name, wanted in SCHEMAS.items())
    all_new, all_old, all_classes = sorted(approved, key=source_order), sorted(retained, key=source_order), sorted(classes)
    index = args.shard_index
    new_ids, old_ids, class_ids = all_new[index::4], all_old[index::4], all_classes[index::4]
    assert (len(new_ids), len(old_ids), len(class_ids)) == (NEW_COUNTS[index], OLD_COUNTS[index], CLASS_COUNTS[index])
    print('CITATIONS31_SHARD_START', index, len(new_ids), len(old_ids), len(class_ids), flush=True)
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
    write_json(artifact, {'citations31_rows': rows, 'retained3605_rows': compatibility, 'retained203_class_rows': class_rows})
    write_json(baseline, {'public_baseline_files': frozen, 'exact_public_profile_files': profiles})
    receipt = output / 'coverage.json'
    write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_CITATIONS31_SHARD_COVERAGE_PASS',
        'actual_checkout_revision': revision, 'code_state': code_state(),
        'helper_sha256': args.expected_helper_sha256,
        'runtime_sha256': runtime_sha, 'guard_sha256': GUARD_SHA, 'prior3808_validation_sha256': PRIOR_SHA,
        'mapping_manifest_sha256': MAPPING_SHA, 'source_documents_sha256': sha(encode(SOURCE_DOCUMENTS)),
        'independent_review_document_sha256s': {key: value['sha256'] for key, value in SOURCE_DOCUMENTS.items()
                                               if key.endswith('_review')},
        'policy': POLICY, 'evidence_schema_version': EVIDENCE_SCHEMA,
        'environment_cleared_dummy_credentials_only': True, 'assessment_time': ASSESSMENT_TIME,
        'policy_input_bindings': {str(path.relative_to(repo)): wanted for path, wanted in policy_inputs.items()},
        'source_bindings_before': before, 'source_tree_sha256': bindings_sha(before), 'source_bindings_unchanged': True,
        'sharding': {'index': index, 'count': 4, 'assignment': 'numeric singleton IDs and lexical class IDs, ids[index::4]',
            'new_manifest_members': 31, 'retained_baseline_members': 3605, 'retained_baseline_classes': 203,
            'sorted_new_ids_sha256': sha(encode(all_new)), 'sorted_retained_ids_sha256': sha(encode(all_old)),
            'sorted_retained_class_ids_sha256': sha(encode(all_classes)),
            'assigned_new_source_ids': new_ids, 'assigned_retained_source_ids': old_ids, 'assigned_retained_class_ids': class_ids,
            'actual_new_preparations': len(rows), 'actual_new_prepare_calls': 2 * len(rows),
            'actual_fresh_classifications': len(rows),
            'actual_retained_comparisons': len(compatibility), 'actual_retained_prepare_calls': len(compatibility),
            'actual_retained_class_comparisons': len(class_rows), 'actual_retained_class_prepare_calls': len(class_rows),
            'all_shards_complete_claimed': False},
        'prepared_root': str(prepared_root), 'classification_sha256': digest(report_path),
        'classification_counts': {'supported': len(rows), 'held': 0, 'failed': 0},
        'fresh_classification_assigned_citations31_members': True,
        'retained_hold_sets': holds, 'retained_class_alias_holds_preserved': True, 'source_status_unchanged': prior['source_status_unchanged'],
        'wire_artifact_manifest_path': artifact.name, 'wire_artifact_manifest_sha256': digest(artifact),
        'retained_file_manifest_path': baseline.name, 'retained_file_manifest_sha256': digest(baseline),
        'all3808_retained_file_hashes_verified_before_and_after': True,
        'retained_file_count': len(frozen), 'exact_public_profile_file_count': len(profiles),
        'retained_paths_and_bytes_unchanged': True, 'original_hashes': originals, 'original_hashes_sha256': ORIGINALS_SHA,
        'original_files_verified_before_and_after': 4206, 'guard': guard.counts,
        'unexpected_guard_events': guard.blocked_call_sites,
        'in_process_read_only_git_queries': guard.metadata_queries, 'elapsed_seconds': time.monotonic() - started,
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Only exact31 reviewed citations are admitted;69 singleton holds,25 pairs and5 protected identities remain. '
                 'Only assigned fresh classification and twice-preparation of approved31; prior3605 singleton and203 '
                 'paired targets once at exact original inputs/times. Full legacy metadata, prior wires and all nonruntime '
                 'evidence remain exact. Complete3839-target coverage requires four saved receipts. No class execution, '
                 'source promotion, remote identity, duplicate absence, grant, QA/community acceptance or release asserted.'})
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('CITATIONS31_SHARD_RESULT', json.dumps({'shard_index': index, 'receipt_sha256': digest(receipt),
                                               'guard': guard.counts}), flush=True)


if __name__ == '__main__':
    main()
