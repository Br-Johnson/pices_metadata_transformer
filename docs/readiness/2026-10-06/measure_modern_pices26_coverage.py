"""Guarded PICES26 coverage; run only after runtime/test freeze.

Reuse the digest-bound PR38 helper for the old2733 catalogue, preservation and
retained comparisons. Four shards classify only their26-member assignment,
prepare each new source twice, and prepare each retained3145 input once at its
original path. Only fresh /tmp output is writable. No executable grant exists.
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
from pathlib import Path
from unittest.mock import Mock

HELPER = Path('docs/readiness/2026-10-06/measure_modern_exxon_coverage.py')
HELPER_SHA = '4376cf168a0410ac17e324d0c7434d94d4525f901eaa01fe833fe9fa4f70b7c7'
EXXON_VALIDATION = Path('docs/readiness/2026-10-06/modern_exxon_validation.json')
EXXON_VALIDATION_SHA = '2d69977b9daf91506fb171df92af9dc0830541c188a6ceffdc679ea3566ae34c'
EXXON_ROOTS = [Path(f'/tmp/pices-exxon-shard{index}-v1') for index in range(4)]
EXXON_PROFILES = Path('/workspace/pices-modern-remaining-citations-20261006/docs/readiness')
PICES_REVIEW = Path('docs/readiness/2026-10-06/modern_pices26_source_review.json')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_helper(repo):
    path = repo / HELPER
    assert digest(path) == HELPER_SHA
    spec = importlib.util.spec_from_file_location('frozen_exxon_measurement', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def retained3145(repo, base):
    """Bind original PR37 inputs plus every actual PR38 preparation and412 input."""
    retained, frozen, profiles, roots = base.retained_catalogue(repo)
    original_frozen, original_profiles = dict(frozen), dict(profiles)
    aggregate_path = repo / EXXON_VALIDATION
    assert digest(aggregate_path) == EXXON_VALIDATION_SHA
    aggregate = json.loads(aggregate_path.read_bytes())
    assert aggregate['all_shards_complete'] and aggregate['coverage']['total'] == 3145
    assert len(aggregate['rows']) == 412 and len(aggregate['retained2733_comparisons']) == 2733
    new_proofs = {row['source_id']: row for row in aggregate['rows']}
    old_proofs = {row['source_id']: row for row in aggregate['retained2733_comparisons']}
    assert len(new_proofs) == 412 and set(old_proofs) == set(retained)
    assert not set(new_proofs) & set(retained)
    seen_new, seen_old = set(), set()

    def track(path, pin):
        path = Path(path)
        assert not path.is_symlink() and path.resolve() == path
        assert any(path.is_relative_to(root) for root in EXXON_ROOTS)
        assert str(path) not in frozen or frozen[str(path)] == pin
        assert digest(path) == pin
        frozen[str(path)] = pin
        return path

    assert [shard['index'] for shard in aggregate['shards']] == list(range(4))
    for shard in aggregate['shards']:
        root = EXXON_ROOTS[shard['index']]
        assert shard['root'] == str(root)
        coverage = json.loads(track(root / 'coverage.json', shard['receipt_sha256']).read_bytes())
        manifest = json.loads(track(root / 'wire_artifact_manifest.json',
                                   shard['artifact_manifest_sha256']).read_bytes())
        prior_files = json.loads(track(root / 'retained_file_manifest.json',
                                      shard['retained_file_manifest_sha256']).read_bytes())
        assert prior_files == {'public_baseline_files': original_frozen,
                               'exact_public_profile_files': original_profiles}
        prepared_root = root / 'prepared'
        assert coverage['prepared_root'] == str(prepared_root)
        track(prepared_root / 'classification.json', shard['classification_sha256'])
        assert len(manifest['exxon_rows']) == shard['new_source_count'] == 103
        assert len(manifest['retained2733_rows']) == shard['retained_source_count']
        assert [row['source_id'] for row in manifest['exxon_rows']] == coverage['sharding']['assigned_new_source_ids']
        assert [row['source_id'] for row in manifest['retained2733_rows']] == coverage['sharding']['assigned_retained_source_ids']
        for prior in manifest['retained2733_rows']:
            sid = prior['source_id']
            assert sid not in seen_old
            seen_old.add(sid)
            old = retained[sid]
            for key in ('source_sha256', 'prepared_input_path', 'prepared_root', 'wire_path', 'wire_sha256'):
                assert prior[key] == old[key]
            proof = old_proofs[sid]
            assert proof['shard_index'] == shard['index']
            assert prior['current_binding'] == proof['current_binding']
            assert prior['nonruntime_evidence_sha256'] == proof['nonruntime_evidence_sha256']
            path = track(root / prior['current_preparation_path'], prior['current_preparation_sha256'])
            current = json.loads(path.read_bytes())
            assert current['source_id'] == sid and current['binding'] == proof['current_binding']
            assert current['binding'] == hashlib.sha256(base.encode(current['evidence'])).hexdigest()
            assert base.nonruntime(current['evidence']) == base.nonruntime(old['evidence'])
            assert hashlib.sha256(base.encode(base.nonruntime(current['evidence']))).hexdigest() == proof['nonruntime_evidence_sha256']
            old.update(evidence=current['evidence'], binding=current['binding'],
                       preparation_path=str(path), preparation_sha256=prior['current_preparation_sha256'])
        for prior in manifest['exxon_rows']:
            sid = prior['source_id']
            assert sid not in seen_new and sid not in retained
            seen_new.add(sid)
            proof = new_proofs[sid]
            assert proof['shard_index'] == shard['index']
            assert all(prior[key] == value for key, value in proof.items() if key != 'shard_index')
            path = track(root / prior['preparation_path'], prior['preparation_sha256'])
            preparation = json.loads(path.read_bytes())
            evidence = preparation['evidence']
            assert preparation['source_id'] == evidence['source_id'] == sid
            assert preparation['binding'] == prior['binding'] == hashlib.sha256(base.encode(evidence)).hexdigest()
            assert evidence['runtime_sha256'] == aggregate['runtime_sha256']
            assert evidence['source_sha256'] == prior['source_sha256']
            input_path = track(root / prior['prepared_input_path'], prior['prepared_input_sha256'])
            assert input_path == prepared_root / 'data/zenodo_json' / (sid + '.json')
            wire_path = track(root / prior['wire_path'], prior['wire_sha256'])
            track(root / prior['original_copy_path'], prior['source_sha256'])
            track(root / 'sources' / (sid + '.xml'), prior['source_sha256'])
            payload = json.loads(input_path.read_bytes())
            for reference in payload['artifact_policy'].values():
                if not isinstance(reference, dict) or 'manifest_path' not in reference:
                    continue
                public = Path(reference['manifest_path'])
                assert public.resolve() == public and not public.is_symlink() and public.is_relative_to(EXXON_PROFILES)
                relative = public.relative_to(EXXON_PROFILES)
                assert str(relative) in base.PROFILE_FILES | {'2026-10-02/exxon_citation_interpretation.json'}
                pin = reference['manifest_sha256']
                assert digest(public) == pin == digest(repo / 'docs/readiness' / relative)
                assert str(public) not in profiles or profiles[str(public)] == pin
                profiles[str(public)] = pin
            retained[sid] = {'source_id': sid, 'source_sha256': prior['source_sha256'],
                             'prepared_root': str(prepared_root), 'prepared_input_path': str(input_path),
                             'wire_path': str(wire_path), 'wire_sha256': prior['wire_sha256'],
                             'preparation_path': str(path), 'preparation_sha256': prior['preparation_sha256'],
                             'evidence': evidence, 'binding': preparation['binding']}
    assert seen_old == set(old_proofs) and seen_new == set(new_proofs) and len(retained) == 3145
    for prior in retained.values():
        raw_metadata = json.loads(Path(prior['prepared_input_path']).read_bytes())['metadata']
        wire = json.loads(Path(prior['wire_path']).read_bytes())
        block = wire['metadata']['additional_descriptions'][0]['description']
        normalized = json.loads(html.unescape(block.split('<pre>', 1)[1][:-6]))
        prior['raw_input_metadata_sha256'] = hashlib.sha256(base.encode(raw_metadata)).hexdigest()
        assert hashlib.sha256(base.encode(normalized)).hexdigest() == prior['evidence']['legacy_metadata_sha256']
    return retained, frozen, profiles, [*roots, *EXXON_ROOTS]


def measure_new(ids, manifest, output, mapping, fixtures, paths_class, assess, max_bytes, originals, base):
    prepared_root = fixtures(output, ids=ids)
    paths = paths_class(str(prepared_root), 'production')
    report_path = prepared_root / 'classification.json'
    report = json.loads(report_path.read_bytes())
    assert len(report['records']) == len(ids) and {row['source_id'] for row in report['records']} == set(ids)
    assert report['summary']['source_status_counts'] == {'supported': len(ids), 'held': 0, 'failed': 0}
    assert {path.stem for path in (output / 'sources').glob('*.xml')} == set(ids)
    assert {path.stem for path in Path(paths.zenodo_json_dir).glob('*.json')} == set(ids)
    members = {member['source_id']: member for member in manifest['members']}
    directory = output / 'pices'
    directory.mkdir()
    rows = []
    for index, sid in enumerate(ids, 1):
        started = time.monotonic()
        json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw = json_file.read_bytes()
        raw_metadata = mapping.parse(raw)['metadata']
        current, repeated = mapping.prepare(json_file, paths), mapping.prepare(json_file, paths)
        assert current == repeated and raw == json_file.read_bytes()
        metadata, source_sha, artifact, _ = assess(json_file, paths)
        assert raw_metadata['creators'] == metadata['creators'] == manifest['creators']
        assert mapping.parse(raw)['artifact_policy']['creator_interpretation']['manifest_sha256'] == mapping.PROFILE_SHA
        assert current.evidence['schema_version'] == 5 and current.evidence['policy'] == mapping.PICES_POLICY
        assert current.evidence['mapping_manifest_sha256'] == mapping.PICES_MAPPING_SHA
        assert current.evidence['creator_profile_sha256'] == mapping.PROFILE_SHA
        assert current.evidence['artifact_contract'] == artifact
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        wire = base.check_preservation(mapping, current, metadata)
        assert wire['metadata']['creators'] == manifest['modern_creators']
        original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        copy_path = Path(paths.original_fgdc_dir) / (sid + '.xml')
        assert current.xml == original == copy_path.read_bytes() == (output / 'sources' / (sid + '.xml')).read_bytes()
        assert mapping.sha(original) == source_sha == members[sid]['source_sha256'] == originals[sid + '.xml']
        wire_path, evidence_path = directory / (sid + '.wire.json'), directory / (sid + '.preparation.json')
        with wire_path.open('xb') as stream:
            stream.write(current.body)
        base.write_json(evidence_path, {'source_id': sid, 'binding': current.binding, 'evidence': current.evidence,
                                      'complete_raw_input_metadata': raw_metadata,
                                      'complete_legacy_metadata': metadata, 'complete_legacy_metadata_preserved': True,
                                      'exact_creators_date_access_and_rights': True, 'unchanged_repeat_equal': True})
        rows.append({'source_id': sid, 'source_sha256': source_sha, 'binding': current.binding,
                     'policy': current.evidence['policy'], 'prepared_input_path': str(json_file.relative_to(output)),
                     'prepared_input_sha256': mapping.sha(raw), 'raw_input_metadata_sha256': mapping.sha(mapping.encode(raw_metadata)),
                     'normalized_legacy_metadata_sha256': current.evidence['legacy_metadata_sha256'],
                     'original_copy_path': str(copy_path.relative_to(output)),
                     'wire_path': str(wire_path.relative_to(output)), 'wire_sha256': digest(wire_path),
                     'preparation_path': str(evidence_path.relative_to(output)), 'preparation_sha256': digest(evidence_path),
                     'body_bytes': len(current.body), 'xml_bytes': len(current.xml), 'prepare_calls': 2,
                     'elapsed_seconds': time.monotonic() - started})
        if index % 50 == 0 or index == len(ids):
            print('NEW_PICES_PROGRESS', index, 'of', len(ids), flush=True)
    return prepared_root, report_path, rows


def main():
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
    base = load_helper(repo)
    assert digest(repo / 'ci/run_offline_tests.py') == base.GUARD_SHA
    retained, frozen, profile_files, roots = retained3145(repo, base)
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
    assert len(originals) == 4206
    helper_sha, runtime_sha = digest(Path(__file__)), mapping.runtime_binding()
    manifest = mapping.pinned(mapping.PICES_MAPPING, mapping.PICES_MAPPING_SHA)
    profile = next(row for row in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']
                   if row['profile'] == 'pices_literal_26')
    assert manifest['policy'] == mapping.PICES_POLICY == 'modern-xml-pices26-v1'
    assert manifest['creators'] == profile['creators'] == [{'name': 'North Pacific Marine Science Organization (PICES)'}]
    assert manifest['modern_creators'] == [{'person_or_org': {'name': profile['raw_origin'], 'type': 'organizational'}}]
    members = {member['source_id']: member for member in manifest['members']}
    assert manifest['members'] == profile['members'] and len(members) == len(manifest['members']) == 26
    assert not set(members) & set(retained)
    assert all(originals[sid + '.xml'] == member['source_sha256'] for sid, member in members.items())
    policy_inputs = {mapping.PICES_MAPPING: mapping.PICES_MAPPING_SHA, mapping.PROFILE: mapping.PROFILE_SHA,
                     mapping.EXXON_MAPPING: mapping.EXXON_MAPPING_SHA, mapping.EXXON_PROFILE: mapping.EXXON_SHA,
                     mapping.EXTENSION: mapping.EXTENSION_SHA, mapping.DIRECT_PROFILE: mapping.DIRECT_SHA,
                     mapping.PLAN: mapping.PLAN_SHA, repo / PICES_REVIEW: manifest['review_sha256'],
                     repo / EXXON_VALIDATION: EXXON_VALIDATION_SHA, repo / HELPER: HELPER_SHA}
    for path, pin in profile_files.items():
        path = Path(path)
        relative = path.relative_to(base.OLD_PROFILES if path.is_relative_to(base.OLD_PROFILES) else EXXON_PROFILES)
        current = repo / 'docs/readiness' / relative
        assert current not in policy_inputs or policy_inputs[current] == pin
        policy_inputs[current] = pin
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    assert all(digest(Path(path)) == pin for path, pin in frozen.items())
    assert all(digest(Path(path)) == pin for path, pin in profile_files.items())
    all_new, all_old = sorted(members, key=base.source_order), sorted(retained, key=base.source_order)
    new_ids, old_ids = all_new[args.shard_index::4], all_old[args.shard_index::4]
    print('PICES_SHARD_START', args.shard_index, 'new', len(new_ids), 'retained', len(old_ids), flush=True)
    new_started = time.monotonic()
    prepared_root, report_path, rows = measure_new(new_ids, manifest, output, mapping, prepare_sources,
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
    artifact = output / 'wire_artifact_manifest.json'
    baseline = output / 'retained_file_manifest.json'
    base.write_json(artifact, {'pices_rows': rows, 'retained3145_rows': compatibility})
    base.write_json(baseline, {'public_baseline_files': frozen, 'exact_public_profile_files': profile_files})
    receipt = output / 'coverage.json'
    base.write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_PICES_SHARD_COVERAGE_PASS', 'actual_checkout_revision': revision,
        'helper_sha256': helper_sha, 'reused_helper_sha256': HELPER_SHA, 'runtime_sha256': runtime_sha,
        'guard_sha256': base.GUARD_SHA, 'environment_cleared_dummy_credentials_only': True,
        'exxon_validation_sha256': EXXON_VALIDATION_SHA, 'prior2733_validation_sha256': base.AGGREGATE_SHA,
        'old105_baseline_sha256': base.OLD105_SHA, 'pices_mapping_sha256': mapping.PICES_MAPPING_SHA,
        'creator_profile_sha256': mapping.PROFILE_SHA, 'policy': mapping.PICES_POLICY, 'evidence_schema_version': 5,
        'policy_input_bindings': {str(path.relative_to(repo)): pin for path, pin in policy_inputs.items()},
        'sharding': {'index': args.shard_index, 'count': 4, 'assignment': 'numeric IDs, independently ids[index::4]',
                     'new_manifest_members': 26, 'retained_baseline_members': 3145,
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
        'all3145_retained_file_hashes_verified_before_and_after': True,
        'retained_file_count': len(frozen), 'exact_public_profile_file_count': len(profile_files),
        'retained_paths_and_bytes_unchanged': True, 'source_bindings_before': before, 'source_bindings_unchanged': True,
        'original_hashes': originals, 'original_hashes_sha256': mapping.sha(mapping.encode(originals)),
        'original_files_verified_before_and_after': 4206, 'guard': guard.counts,
        'unexpected_guard_events': guard.blocked_call_sites, 'in_process_read_only_git_queries': guard.metadata_queries,
        'elapsed_seconds': {'new_classification_and_repeat_preparation': new_finished - new_started,
                            'retained_comparisons_and_final_verification': time.monotonic() - new_finished,
                            'total': time.monotonic() - started},
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Only actual assigned fresh PICES classification/repeat preparation and assigned retained '
                 'PR38 preparation once at exact original inputs, with identical wire/nonruntime evidence. '
                 'Raw input metadata and normalized complete legacy preservation blocks are separately bound. '
                 'Aggregate3171 coverage/762 remaining requires all four receipts; no live compatibility, '
                 'duplicate absence, executable grant, production identity, QA approval or release asserted.',
    })
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('PICES_SHARD_RESULT', json.dumps({'shard_index': args.shard_index, 'actual_new_preparations': len(rows),
          'actual_retained_comparisons': len(compatibility), 'receipt_sha256': digest(receipt), 'guard': guard.counts}),
          flush=True)


if __name__ == '__main__':
    main()
