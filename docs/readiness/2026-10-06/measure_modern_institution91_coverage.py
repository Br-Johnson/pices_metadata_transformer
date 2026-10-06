"""Guarded institutional coverage; run only after the runtime/test freeze.

Reuse the pinned PR41 and PR38 helpers for retained catalogues, complete legacy
preservation and unchanged-wire comparisons. Four shards prepare their share
of 91 new sources twice and their share of 3171 retained inputs once, at the
exact original paths. Only a fresh /tmp output is writable. No provider grant,
live compatibility, duplicate absence, QA approval or release is established.
"""

import argparse
import hashlib
import html
import importlib.util
import json
import os
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

HELPER = Path('docs/readiness/2026-10-06/measure_modern_pices26_coverage.py')
HELPER_SHA = '2ff6859c7b024f0eb7bcf2b10d6239dfe54a0795b337ba50a9af87fcb9211ec4'
PICES_VALIDATION = Path('docs/readiness/2026-10-06/modern_pices26_validation.json')
PICES_VALIDATION_SHA = 'effab194b3621fc867542ab366b57d7f1091400b4ba6ebfabf6f0270955bc208'
PICES_ROOTS = [Path(f'/tmp/pices-pices26-shard{index}-v1') for index in range(4)]
PICES_PROFILES = Path('/workspace/pices-modern-residual-20261006/docs/readiness')
SOURCE_REVIEW = Path('docs/readiness/2026-10-06/modern_institution91_source_review.json')
BINDING_REVIEW = Path('docs/readiness/2026-10-06/modern_institution91_source_bindings.json')
INDEPENDENT_REVIEW = Path('docs/readiness/2026-10-06/modern_institution91_independent_review.json')
INDEPENDENT_REVIEW_SHA = '5904019eb6edf096bf6a27798c9f001d154604fcf2a18fa62d75cbe4e1602a44'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_helpers(repo):
    path = repo / HELPER
    assert digest(path) == HELPER_SHA
    spec = importlib.util.spec_from_file_location('frozen_pices26_measurement', path)
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    return prior, prior.load_helper(repo)


def retained3171(repo, prior, base):
    """Advance every retained binding through actual PR41 saved preparations."""
    retained, frozen, profiles, roots = prior.retained3145(repo, base)
    original_frozen, original_profiles = dict(frozen), dict(profiles)
    aggregate_path = repo / PICES_VALIDATION
    assert digest(aggregate_path) == PICES_VALIDATION_SHA
    aggregate = json.loads(aggregate_path.read_bytes())
    assert aggregate['status'] == 'GUARDED_PICES26_AGGREGATE_PASS'
    assert aggregate['all_shards_complete'] and aggregate['coverage'] == {
        'fresh_new_prepare_calls': 52, 'new_PICES_singletons': 26, 'paired_targets_added': 0,
        'prior_retained_singletons': 3145, 'retained_input_prepare_comparisons': 3145, 'total': 3171}
    assert aggregate['helper_sha256'] == HELPER_SHA
    assert aggregate['prior3145_validation_sha256'] == prior.EXXON_VALIDATION_SHA
    assert aggregate['provider_requests'] == aggregate['provider_mutations'] == 0
    assert aggregate['source_bindings_unchanged'] and aggregate['all_saved_digests_reverified']
    proofs = {row['source_id']: row for row in aggregate['rows']}
    assert len(proofs) == len(aggregate['rows']) == 26 and not set(proofs) & set(retained)
    old_ids = set(retained)
    seen_old, seen_new, old_rows, receipts = set(), set(), [], []

    def track(path, pin):
        path = Path(path)
        assert not path.is_symlink() and path.resolve() == path
        assert any(path.is_relative_to(root) for root in PICES_ROOTS)
        assert str(path) not in frozen or frozen[str(path)] == pin
        assert digest(path) == pin
        frozen[str(path)] = pin
        return path

    assert [shard['index'] for shard in aggregate['shards']] == list(range(4))
    for shard in aggregate['shards']:
        index = shard['index']
        root = PICES_ROOTS[index]
        assert shard['root'] == str(root)
        coverage = json.loads(track(root / 'coverage.json', shard['receipt_sha256']).read_bytes())
        receipts.append(coverage)
        assert coverage['status'] == 'GUARDED_PICES_SHARD_COVERAGE_PASS'
        assert coverage['runtime_sha256'] == aggregate['runtime_sha256']
        assert coverage['helper_sha256'] == HELPER_SHA
        assert coverage['reused_helper_sha256'] == prior.HELPER_SHA
        assert coverage['guard_sha256'] == base.GUARD_SHA
        assert coverage['environment_cleared_dummy_credentials_only']
        assert coverage['source_bindings_unchanged'] and coverage['retained_paths_and_bytes_unchanged']
        assert coverage['all3145_retained_file_hashes_verified_before_and_after']
        assert coverage['original_files_verified_before_and_after'] == 4206
        assert coverage['provider_requests'] == coverage['provider_mutations'] == 0
        assert not coverage['unexpected_guard_events'] and not any(coverage['guard']['tests'].values())
        assert coverage['guard'] == shard['guard']
        assert coverage['sharding']['index'] == index and coverage['sharding']['count'] == 4
        manifest = json.loads(track(root / 'wire_artifact_manifest.json',
                                   shard['artifact_manifest_sha256']).read_bytes())
        assert coverage['wire_artifact_manifest_sha256'] == shard['artifact_manifest_sha256']
        previous_files = json.loads(track(root / 'retained_file_manifest.json',
                                         shard['retained_file_manifest_sha256']).read_bytes())
        assert coverage['retained_file_manifest_sha256'] == shard['retained_file_manifest_sha256']
        assert previous_files == {'public_baseline_files': original_frozen,
                                  'exact_public_profile_files': original_profiles}
        prepared_root = root / 'prepared'
        assert coverage['prepared_root'] == str(prepared_root)
        report = json.loads(track(prepared_root / 'classification.json',
                                  shard['classification_sha256']).read_bytes())
        assert coverage['classification_sha256'] == shard['classification_sha256']
        new, old = manifest['pices_rows'], manifest['retained3145_rows']
        expected_new = sorted(proofs, key=base.source_order)[index::4]
        expected_old = sorted(old_ids, key=base.source_order)[index::4]
        assert [row['source_id'] for row in new] == expected_new
        assert [row['source_id'] for row in old] == expected_old
        assert coverage['sharding']['assigned_new_source_ids'] == expected_new
        assert coverage['sharding']['assigned_retained_source_ids'] == expected_old
        assert len(new) == shard['new_source_count'] == (7, 7, 6, 6)[index]
        assert len(old) == shard['retained_source_count'] == (787, 786, 786, 786)[index]
        assert report['summary']['source_status_counts'] == {'supported': len(new), 'held': 0, 'failed': 0}
        assert {row['source_id'] for row in report['records']} == set(expected_new)
        old_rows.extend(old)
        for saved in old:
            sid = saved['source_id']
            assert sid not in seen_old
            seen_old.add(sid)
            original = retained[sid]
            for key, value in original.items():
                if key != 'evidence':
                    assert saved[key] == value
            path = track(root / saved['current_preparation_path'], saved['current_preparation_sha256'])
            packet = json.loads(path.read_bytes())
            assert packet['source_id'] == packet['evidence']['source_id'] == sid
            assert packet['binding'] == saved['current_binding'] == hashlib.sha256(base.encode(packet['evidence'])).hexdigest()
            assert packet['evidence']['runtime_sha256'] == aggregate['runtime_sha256']
            assert base.nonruntime(packet['evidence']) == base.nonruntime(original['evidence'])
            assert saved['nonruntime_evidence_sha256'] == hashlib.sha256(base.encode(base.nonruntime(packet['evidence']))).hexdigest()
            assert saved['wire_and_nonruntime_evidence_equal']
            original.update(evidence=packet['evidence'], binding=packet['binding'],
                            preparation_path=str(path), preparation_sha256=saved['current_preparation_sha256'])
        for saved in new:
            sid = saved['source_id']
            assert sid not in seen_new and sid not in retained
            seen_new.add(sid)
            assert proofs[sid] == saved | {'shard_index': index}
            path = track(root / saved['preparation_path'], saved['preparation_sha256'])
            packet = json.loads(path.read_bytes())
            evidence = packet['evidence']
            assert packet['source_id'] == evidence['source_id'] == sid
            assert packet['binding'] == saved['binding'] == hashlib.sha256(base.encode(evidence)).hexdigest()
            assert evidence['runtime_sha256'] == aggregate['runtime_sha256']
            assert evidence['source_sha256'] == saved['source_sha256']
            assert evidence['wire_sha256'] == saved['wire_sha256']
            input_path = track(root / saved['prepared_input_path'], saved['prepared_input_sha256'])
            assert input_path == prepared_root / 'data/zenodo_json' / (sid + '.json')
            assert evidence['prepared_input_sha256'] == saved['prepared_input_sha256']
            wire_path = track(root / saved['wire_path'], saved['wire_sha256'])
            copy_path = track(root / saved['original_copy_path'], saved['source_sha256'])
            assert copy_path == prepared_root / 'data/original_fgdc' / (sid + '.xml')
            track(root / 'sources' / (sid + '.xml'), saved['source_sha256'])
            payload = json.loads(input_path.read_bytes())
            assert packet['complete_raw_input_metadata'] == payload['metadata']
            assert packet['complete_legacy_metadata_preserved'] and packet['unchanged_repeat_equal']
            for reference in payload['artifact_policy'].values():
                if not isinstance(reference, dict) or 'manifest_path' not in reference:
                    continue
                public = Path(reference['manifest_path'])
                assert public.resolve() == public and not public.is_symlink()
                assert public.is_relative_to(PICES_PROFILES)
                relative = public.relative_to(PICES_PROFILES)
                assert str(relative) in base.PROFILE_FILES
                pin = reference['manifest_sha256']
                assert digest(public) == pin == digest(repo / 'docs/readiness' / relative)
                assert str(public) not in profiles or profiles[str(public)] == pin
                profiles[str(public)] = pin
            retained[sid] = {
                'source_id': sid, 'source_sha256': saved['source_sha256'],
                'prepared_root': str(prepared_root), 'prepared_input_path': str(input_path),
                'wire_path': str(wire_path), 'wire_sha256': saved['wire_sha256'],
                'preparation_path': str(path), 'preparation_sha256': saved['preparation_sha256'],
                'evidence': evidence, 'binding': packet['binding'],
                'raw_input_metadata_sha256': saved['raw_input_metadata_sha256']}
    assert seen_old == old_ids and seen_new == set(proofs) and len(retained) == 3171
    old_rows.sort(key=lambda row: base.source_order(row['source_id']))
    assert hashlib.sha256(base.encode(old_rows)).hexdigest() == aggregate['retained3145_comparison_rows_sha256']
    for key in ('source_bindings_before', 'runtime_sha256', 'helper_sha256', 'policy_input_bindings',
                'original_hashes', 'original_hashes_sha256'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    assert receipts[0]['original_hashes_sha256'] == aggregate['original_hashes_sha256']
    for saved in retained.values():
        payload = json.loads(Path(saved['prepared_input_path']).read_bytes())
        assert digest(Path(saved['prepared_input_path'])) == saved['evidence']['prepared_input_sha256']
        assert digest(Path(saved['wire_path'])) == saved['wire_sha256'] == saved['evidence']['wire_sha256']
        assert hashlib.sha256(base.encode(payload['metadata'])).hexdigest() == saved['raw_input_metadata_sha256']
        wire = json.loads(Path(saved['wire_path']).read_bytes())
        block = wire['metadata']['additional_descriptions'][0]['description']
        normalized = json.loads(html.unescape(block.split('<pre>', 1)[1][:-6]))
        assert hashlib.sha256(base.encode(normalized)).hexdigest() == saved['evidence']['legacy_metadata_sha256']
    return retained, frozen, profiles, [*roots, *PICES_ROOTS], receipts[0]


def measure_new(ids, members, groups, output, mapping, fixtures, paths_class, assess, max_bytes, originals, base):
    prepared_root = fixtures(output, ids=ids)
    paths = paths_class(str(prepared_root), 'production')
    report_path = prepared_root / 'classification.json'
    report = json.loads(report_path.read_bytes())
    assert len(report['records']) == len(ids) and {row['source_id'] for row in report['records']} == set(ids)
    assert report['summary']['source_status_counts'] == {'supported': len(ids), 'held': 0, 'failed': 0}
    assert {path.stem for path in (output / 'sources').glob('*.xml')} == set(ids)
    assert {path.stem for path in Path(paths.zenodo_json_dir).glob('*.json')} == set(ids)
    directory = output / 'institutions'
    directory.mkdir()
    rows = []
    for index, sid in enumerate(ids, 1):
        started = time.monotonic()
        group = groups[sid]
        json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw = json_file.read_bytes()
        payload = mapping.parse(raw)
        raw_metadata = payload['metadata']
        current, repeated = mapping.prepare(json_file, paths), mapping.prepare(json_file, paths)
        assert current == repeated and raw == json_file.read_bytes()
        metadata, source_sha, artifact, _ = assess(json_file, paths)
        assert raw_metadata['creators'] == metadata['creators'] == group['creators']
        assert 'creator_interpretation' not in payload['artifact_policy']
        assert current.evidence['schema_version'] == 6 and current.evidence['policy'] == mapping.INSTITUTION_POLICY
        assert current.evidence['mapping_manifest_sha256'] == mapping.INSTITUTION_MAPPING_SHA
        assert current.evidence['creator_profile_sha256'] == mapping.INSTITUTION_MAPPING_SHA
        assert current.evidence['creator_cohort'] == group['profile']
        assert current.evidence['artifact_contract'] == artifact
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        wire = base.check_preservation(mapping, current, metadata)
        assert wire['metadata']['creators'] == group['modern_creators']
        original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        origins = ET.fromstring(original).findall('./idinfo/citation/citeinfo/origin')
        assert [mapping.source_element(node) for node in origins] in group['primary_origin_variants']
        copy_path = Path(paths.original_fgdc_dir) / (sid + '.xml')
        assert current.xml == original == copy_path.read_bytes() == (output / 'sources' / (sid + '.xml')).read_bytes()
        assert mapping.sha(original) == source_sha == members[sid]['source_sha256'] == originals[sid + '.xml']
        wire_path, evidence_path = directory / (sid + '.wire.json'), directory / (sid + '.preparation.json')
        with wire_path.open('xb') as stream:
            stream.write(current.body)
        base.write_json(evidence_path, {
            'source_id': sid, 'binding': current.binding, 'evidence': current.evidence,
            'complete_raw_input_metadata': raw_metadata, 'complete_legacy_metadata': metadata,
            'complete_legacy_metadata_preserved': True, 'exact_creators_date_access_and_rights': True,
            'exact_primary_origin_variant': True, 'unchanged_repeat_equal': True})
        rows.append({
            'source_id': sid, 'source_sha256': source_sha, 'binding': current.binding,
            'policy': current.evidence['policy'], 'creator_cohort': group['profile'],
            'prepared_input_path': str(json_file.relative_to(output)), 'prepared_input_sha256': mapping.sha(raw),
            'raw_input_metadata_sha256': mapping.sha(mapping.encode(raw_metadata)),
            'normalized_legacy_metadata_sha256': current.evidence['legacy_metadata_sha256'],
            'original_copy_path': str(copy_path.relative_to(output)),
            'wire_path': str(wire_path.relative_to(output)), 'wire_sha256': digest(wire_path),
            'preparation_path': str(evidence_path.relative_to(output)), 'preparation_sha256': digest(evidence_path),
            'body_bytes': len(current.body), 'xml_bytes': len(current.xml), 'prepare_calls': 2,
            'elapsed_seconds': time.monotonic() - started})
        if index % 10 == 0 or index == len(ids):
            print('NEW_INSTITUTION_PROGRESS', index, 'of', len(ids), flush=True)
    return prepared_root, report_path, rows


def main():
    if not __debug__:
        raise RuntimeError('Assertions must remain enabled for this measurement')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shard-index', type=int, choices=range(4), required=True)
    parser.add_argument('--shard-count', type=int, choices=(4,), default=4)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    os.environ.clear()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    prior, base = load_helpers(repo)
    assert digest(repo / 'ci/run_offline_tests.py') == base.GUARD_SHA
    retained, frozen, profile_files, roots, previous_receipt = retained3171(repo, prior, base)
    if (not output.is_relative_to(Path('/tmp')) or output == Path('/tmp') or output.exists()
            or output.is_relative_to(repo) or not output.parent.is_dir()
            or any(output.is_relative_to(root) for root in roots)):
        raise ValueError('Choose fresh /tmp output outside every retained baseline')
    from ci.run_offline_tests import (
        OfflineGuard,
        checkout_revision,
        clean_environment,
        source_bindings,
    )

    revision = checkout_revision(repo)
    allowed = {Path(path) for path in frozen} | {Path(path) for path in profile_files}
    for path in frozen:
        allowed.update(parent for parent in Path(path).parents if any(parent.is_relative_to(root) for root in roots))
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)
    guard = OfflineGuard(repo, output, revision)
    guard.library_files.update(allowed | {Path(__file__).resolve()})
    guard.install()
    guard.self_check()
    output.mkdir()
    started = time.monotonic()
    import scripts.logger
    scripts.logger.get_logger = lambda *args, **kwargs: Mock()
    from scripts import modern_singleton as mapping
    from scripts.agent_qa import assess_source
    from scripts.modern_singleton_executor import MAX_BYTES
    from scripts.path_config import OutputPaths
    from tests.modern_singleton_fixtures import prepare_sources

    before = source_bindings(repo)
    originals = {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert len(originals) == 4206 and originals == previous_receipt['original_hashes']
    helper_sha, runtime_sha = digest(Path(__file__)), mapping.runtime_binding()
    manifest = mapping.pinned(mapping.INSTITUTION_MAPPING, mapping.INSTITUTION_MAPPING_SHA)
    assert manifest['policy'] == mapping.INSTITUTION_POLICY == 'modern-xml-institutions91-v1'
    assert manifest['schema_version'] == 1 and manifest['kind'] == 'modern-institutional-singletons-v1'
    assert manifest['member_count'] == 91 and manifest['group_count'] == len(manifest['groups']) == 9
    assert manifest['source_plan_sha256'] == mapping.PLAN_SHA
    all_members = [member for group in manifest['groups'] for member in group['members']]
    members = {member['source_id']: member for member in all_members}
    groups = {member['source_id']: group for group in manifest['groups'] for member in group['members']}
    assert len(members) == len(all_members) == 91 and not set(members) & set(retained)
    assert all(originals[sid + '.xml'] == member['source_sha256'] for sid, member in members.items())
    policy_inputs = {repo / path: pin for path, pin in previous_receipt['policy_input_bindings'].items()}
    policy_inputs.update({
        mapping.INSTITUTION_MAPPING: mapping.INSTITUTION_MAPPING_SHA,
        repo / SOURCE_REVIEW: manifest['review_sha256'], repo / BINDING_REVIEW: manifest['binding_review_sha256'],
        repo / INDEPENDENT_REVIEW: INDEPENDENT_REVIEW_SHA,
        repo / PICES_VALIDATION: PICES_VALIDATION_SHA, repo / HELPER: HELPER_SHA})
    assert all(path.is_relative_to(repo) and path.resolve() == path for path in policy_inputs)
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    review = json.loads((repo / SOURCE_REVIEW).read_bytes())
    independent = json.loads((repo / INDEPENDENT_REVIEW).read_bytes())
    assert review['retained_census_sha256'] == manifest['source_census_sha256']
    assert review['independent_binding_evidence_sha256'] == manifest['binding_review_sha256']
    sorted_members = sorted(all_members, key=lambda row: base.source_order(row['source_id']))
    assert sorted_members == review['recommendation']['members']
    membership_sha = mapping.sha(json.dumps(sorted_members, sort_keys=True, ensure_ascii=False,
                                            separators=(',', ':')).encode())
    assert membership_sha == review['recommendation']['candidate_membership_sha256']
    assert independent['verdict'] == 'APPROVE_FINITE_SOURCE_SEMANTICS_ONLY'
    assert independent['selected']['membership_sha256'] == membership_sha
    assert independent['selected']['source_count'] == 91 and independent['selected']['group_count'] == 9
    assert all(digest(Path(path)) == pin for path, pin in frozen.items())
    assert all(digest(Path(path)) == pin for path, pin in profile_files.items())
    all_new, all_old = sorted(members, key=base.source_order), sorted(retained, key=base.source_order)
    new_ids, old_ids = all_new[args.shard_index::4], all_old[args.shard_index::4]
    assert len(new_ids) == (23, 23, 23, 22)[args.shard_index]
    assert len(old_ids) == (793, 793, 793, 792)[args.shard_index]
    print('INSTITUTION_SHARD_START', args.shard_index, 'new', len(new_ids), 'retained', len(old_ids), flush=True)
    new_started = time.monotonic()
    prepared_root, report_path, rows = measure_new(new_ids, members, groups, output, mapping, prepare_sources,
                                                 OutputPaths, assess_source, MAX_BYTES, originals, base)
    new_finished = time.monotonic()
    compatibility = base.compare_retained(old_ids, retained, output, mapping, OutputPaths, MAX_BYTES, originals)
    for row in compatibility:
        row['body_bytes'] = Path(row['wire_path']).stat().st_size
        row['xml_bytes'] = (mapping.ROOT / 'FGDC' / (row['source_id'] + '.xml')).stat().st_size
    assert [row['source_id'] for row in rows] == new_ids
    assert [row['source_id'] for row in compatibility] == old_ids
    assert originals == {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert before == source_bindings(repo) and runtime_sha == mapping.runtime_binding()
    assert helper_sha == digest(Path(__file__))
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    assert all(digest(Path(path)) == pin for path, pin in frozen.items())
    assert all(digest(Path(path)) == pin for path, pin in profile_files.items())
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    artifact, baseline = output / 'wire_artifact_manifest.json', output / 'retained_file_manifest.json'
    base.write_json(artifact, {'institution_rows': rows, 'retained3171_rows': compatibility})
    base.write_json(baseline, {'public_baseline_files': frozen, 'exact_public_profile_files': profile_files})
    receipt = output / 'coverage.json'
    base.write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_INSTITUTION_SHARD_COVERAGE_PASS',
        'actual_checkout_revision': revision, 'helper_sha256': helper_sha,
        'reused_helpers_sha256': {str(HELPER): HELPER_SHA, str(prior.HELPER): prior.HELPER_SHA},
        'runtime_sha256': runtime_sha, 'guard_sha256': base.GUARD_SHA,
        'environment_cleared_dummy_credentials_only': True,
        'pices26_validation_sha256': PICES_VALIDATION_SHA,
        'exxon_validation_sha256': prior.EXXON_VALIDATION_SHA,
        'prior2733_validation_sha256': base.AGGREGATE_SHA, 'old105_baseline_sha256': base.OLD105_SHA,
        'institution_mapping_sha256': mapping.INSTITUTION_MAPPING_SHA,
        'creator_profile_sha256': mapping.INSTITUTION_MAPPING_SHA,
        'policy': mapping.INSTITUTION_POLICY, 'evidence_schema_version': 6,
        'policy_input_bindings': {str(path.relative_to(repo)): pin for path, pin in policy_inputs.items()},
        'sharding': {
            'index': args.shard_index, 'count': 4, 'assignment': 'numeric IDs, independently ids[index::4]',
            'new_manifest_members': 91, 'retained_baseline_members': 3171,
            'sorted_new_ids_sha256': mapping.sha(mapping.encode(all_new)),
            'sorted_retained_ids_sha256': mapping.sha(mapping.encode(all_old)),
            'assigned_new_source_ids': new_ids, 'assigned_retained_source_ids': old_ids,
            'actual_new_preparations': len(rows), 'actual_new_prepare_calls': len(rows) * 2,
            'actual_retained_comparisons': len(compatibility), 'actual_retained_prepare_calls': len(compatibility),
            'all_shards_complete_claimed': False},
        'prepared_root': str(prepared_root), 'classification_sha256': digest(report_path),
        'classification_counts': {'supported': len(rows), 'held': 0, 'failed': 0},
        'wire_artifact_manifest_path': artifact.name, 'wire_artifact_manifest_sha256': digest(artifact),
        'retained_file_manifest_path': baseline.name, 'retained_file_manifest_sha256': digest(baseline),
        'all3171_retained_file_hashes_verified_before_and_after': True,
        'retained_file_count': len(frozen), 'exact_public_profile_file_count': len(profile_files),
        'retained_paths_and_bytes_unchanged': True, 'source_bindings_before': before, 'source_bindings_unchanged': True,
        'original_hashes': originals, 'original_hashes_sha256': mapping.sha(mapping.encode(originals)),
        'original_files_verified_before_and_after': 4206, 'guard': guard.counts,
        'unexpected_guard_events': guard.blocked_call_sites,
        'in_process_read_only_git_queries': guard.metadata_queries,
        'elapsed_seconds': {
            'new_classification_and_repeat_preparation': new_finished - new_started,
            'retained_comparisons_and_final_verification': time.monotonic() - new_finished,
            'total': time.monotonic() - started},
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Only actual assigned fresh institutional classification/repeat preparation and assigned retained '
                 'PR41 preparation once at exact original inputs, with identical wire/nonruntime evidence. '
                 'Raw input metadata and normalized complete legacy preservation blocks are separately bound. '
                 'Aggregate3262 coverage/671 remaining requires all four receipts; no live compatibility, '
                 'duplicate absence, executable grant, production identity, QA approval or release asserted.'})
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('INSTITUTION_SHARD_RESULT', json.dumps({
        'shard_index': args.shard_index, 'actual_new_preparations': len(rows),
        'actual_retained_comparisons': len(compatibility), 'receipt_sha256': digest(receipt), 'guard': guard.counts}),
        flush=True)


if __name__ == '__main__':
    main()
