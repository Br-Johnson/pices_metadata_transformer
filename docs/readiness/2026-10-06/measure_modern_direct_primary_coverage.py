"""Measure every assigned direct-primary source under the pinned offline guard.

Run after the runtime/profile freeze, with --repo, a fresh --output below /tmp,
--shard-index 0..3 and --shard-count 4 (or index 0/count 1). Each shard freshly
classifies only its assigned IDs and prepares each twice. Shard zero additionally
compares the exact retained PR36 baseline without changing its paths or bytes.
Receipts prove local shard coverage; live compatibility and release are separate.
"""

import argparse
import hashlib
import html
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

GUARD_SHA = '1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05'
BASELINE = Path('/tmp/pices-modern-old105-baseline-20261006/baseline.json')
BASELINE_SHA = '87599287eadabf8a75f26667a39705b64c1c5cba888f67a5a664ae5ec8b183e0'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def write_bytes(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def nonruntime(evidence):
    return {key: value for key, value in evidence.items() if key != 'runtime_sha256'}


def source_order(source_id):
    return int(source_id.removeprefix('FGDC-'))


def baseline_inventory():
    if BASELINE.is_symlink() or digest(BASELINE) != BASELINE_SHA:
        raise ValueError('Frozen public baseline differs')
    old = json.loads(BASELINE.read_bytes())
    root = Path(old['prepared_root']).resolve()
    if not root.is_relative_to(BASELINE.parent) or len(old['rows']) != 105:
        raise ValueError('Frozen baseline root or count differs')
    entries = list(BASELINE.parent.rglob('*'))
    if any(path.is_symlink() for path in entries):
        raise ValueError('Frozen baseline must not contain symlinks')
    files = {path.resolve() for path in entries if path.is_file()}
    directories = {BASELINE.parent, *(path.resolve() for path in entries if path.is_dir())}
    return old, root, files, directories


def retained_comparison(old, old_root, output, mapping, output_paths, max_bytes, originals):
    class RetainedPaths(output_paths):
        # Resolve identical existing paths without even attempting a baseline write.
        def _prepare_dir(self, new_path, legacy_path=None, migrate_patterns=None):
            assert Path(new_path).is_dir()
            return new_path

        def _prepare_file(self, new_path, legacy_path=None):
            assert Path(new_path).parent.is_dir()
            return new_path

    paths = RetainedPaths(str(old_root), 'production')
    rows = []
    prior_ids = [row['source_id'] for row in old['rows']]
    expected = {row['source_id'] for row in mapping.cohort()['members']}
    expected.update(row['source_id'] for row in mapping.pinned(mapping.EXTENSION, mapping.EXTENSION_SHA)['members'])
    assert len(prior_ids) == len(set(prior_ids)) == 105 and set(prior_ids) == expected
    directory = output / 'retained105'
    directory.mkdir()
    for index, prior in enumerate(old['rows'], 1):
        sid = prior['source_id']
        current = mapping.prepare(Path(paths.zenodo_json_dir) / (sid + '.json'), paths)
        assert current.body == mapping.encode(prior['wire'])
        assert mapping.sha(current.xml) == prior['xml_sha256'] == originals[sid + '.xml']
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        assert nonruntime(current.evidence) == nonruntime(prior['evidence'])
        wire_path, evidence_path = directory / (sid + '.wire.json'), directory / (sid + '.preparation.json')
        write_bytes(wire_path, current.body)
        write_json(evidence_path, {'source_id': sid, 'binding': current.binding, 'evidence': current.evidence})
        rows.append({'source_id': sid, 'source_sha256': prior['xml_sha256'],
                     'wire_path': str(wire_path.relative_to(output)), 'wire_sha256': digest(wire_path),
                     'preparation_path': str(evidence_path.relative_to(output)),
                     'preparation_sha256': digest(evidence_path),
                     'nonruntime_evidence_sha256': mapping.sha(mapping.encode(nonruntime(current.evidence))),
                     'original_binding': prior['binding'], 'current_binding': current.binding,
                     'retained_wire_and_nonruntime_evidence_equal': True})
        if index % 50 == 0 or index == len(old['rows']):
            print('RETAINED105_PROGRESS', index, 'of', len(old['rows']), flush=True)
    return rows


def measure_selected(ids, members, output, mapping, prepare_sources, output_paths, assess_source, max_bytes, originals):
    prepared_root = prepare_sources(output, ids=ids)
    paths = output_paths(str(prepared_root), 'production')
    report_path = prepared_root / 'classification.json'
    report = json.loads(report_path.read_bytes())
    assert {row['source_id'] for row in report['records']} == set(ids)
    assert len(report['records']) == len(ids)
    assert report['summary']['source_status_counts'] == {'supported': len(ids), 'held': 0, 'failed': 0}
    assert {path.stem for path in (output / 'sources').glob('*.xml')} == set(ids)
    assert {path.stem for path in Path(paths.zenodo_json_dir).glob('*.json')} == set(ids)
    directory = output / 'direct'
    directory.mkdir()
    rows = []
    for index, sid in enumerate(ids, 1):
        group, member = members[sid]
        json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
        input_raw = json_file.read_bytes()
        current = mapping.prepare(json_file, paths)
        repeated = mapping.prepare(json_file, paths)
        assert current == repeated and len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        assert json_file.read_bytes() == input_raw
        metadata, source_sha, artifact, _ = assess_source(json_file, paths)
        payload, wire = mapping.parse(input_raw), mapping.parse(current.body)
        assert 'creator_interpretation' not in payload['artifact_policy']
        assert metadata['creators'] == group['creators']
        assert current.evidence['schema_version'] == 3 and current.evidence['policy'] == mapping.DIRECT_POLICY
        assert current.evidence['mapping_manifest_sha256'] == mapping.DIRECT_SHA
        assert current.evidence['creator_cohort'] == group['profile']
        assert current.evidence['artifact_contract'] == artifact
        assert wire['metadata']['creators'] == [
            {'person_or_org': {'name': creator['name'], 'type': 'organizational'}} for creator in metadata['creators']]
        for key in ('title', 'description', 'publication_date'):
            assert wire['metadata'][key] == metadata[key]
        assert wire['metadata']['subjects'] == [{'subject': value} for value in metadata.get('keywords', [])]
        assert wire['metadata']['publisher'] == 'Zenodo'
        assert wire['access'] == {'record': 'public', 'files': 'restricted'} and wire['files'] == {'enabled': True}
        assert 'rights' not in wire['metadata'] and 'license' not in wire['metadata']
        assert metadata['access_right'] == 'restricted' and metadata['license'] == ''
        preserved = wire['metadata']['additional_descriptions'][0]['description']
        assert preserved.startswith('<p>' + mapping.PRESERVATION_LABEL + '</p><pre>') and preserved.endswith('</pre>')
        assert json.loads(html.unescape(preserved.split('<pre>', 1)[1][:-6])) == metadata
        original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        source_copy = Path(paths.original_fgdc_dir) / (sid + '.xml')
        assert current.xml == original == source_copy.read_bytes() == (output / 'sources' / (sid + '.xml')).read_bytes()
        assert mapping.sha(current.xml) == source_sha == member['source_sha256'] == originals[sid + '.xml']
        wire_path, evidence_path = directory / (sid + '.wire.json'), directory / (sid + '.preparation.json')
        write_bytes(wire_path, current.body)
        write_json(evidence_path, {
            'source_id': sid, 'binding': current.binding, 'evidence': current.evidence,
            'complete_legacy_metadata': metadata, 'complete_legacy_metadata_preserved': True,
            'exact_creators_date_access_and_rights': True, 'unchanged_repeat_equal': True,
            'prepared_input_path': str(json_file.relative_to(output)),
            'original_copy_path': str(source_copy.relative_to(output)),
            'wire_path': str(wire_path.relative_to(output)),
        })
        rows.append({'source_id': sid, 'source_sha256': source_sha, 'policy': current.evidence['policy'],
                     'creator_cohort': group['profile'], 'binding': current.binding,
                     'prepared_input_path': str(json_file.relative_to(output)),
                     'prepared_input_sha256': mapping.sha(input_raw),
                     'wire_path': str(wire_path.relative_to(output)), 'wire_sha256': digest(wire_path),
                     'preparation_path': str(evidence_path.relative_to(output)),
                     'preparation_sha256': digest(evidence_path),
                     'body_bytes': len(current.body), 'xml_bytes': len(current.xml)})
        if index % 50 == 0 or index == len(ids):
            print('DIRECT_SHARD_PROGRESS', index, 'of', len(ids), flush=True)
    return prepared_root, report_path, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shard-index', type=int, required=True)
    parser.add_argument('--shard-count', type=int, choices=(1, 4), default=4)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    if not 0 <= args.shard_index < args.shard_count:
        raise ValueError('Shard index must be within shard count')
    if (not output.is_relative_to(Path('/tmp')) or output == Path('/tmp')
            or output.is_relative_to(repo) or output.exists() or not output.parent.is_dir()
            or output.is_relative_to(BASELINE.parent)):
        raise ValueError('Choose a fresh /tmp output outside the retained baseline')
    if digest(repo / 'ci/run_offline_tests.py') != GUARD_SHA:
        raise ValueError('Offline guard differs')
    old, old_root, baseline_files, baseline_directories = (
        baseline_inventory() if args.shard_index == 0 else (None, None, set(), set()))
    os.environ.clear()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    from ci.run_offline_tests import (
        OfflineGuard,
        checkout_revision,
        clean_environment,
        source_bindings,
    )

    revision = checkout_revision(repo)
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)
    guard = OfflineGuard(repo, output, revision)
    guard.library_files.update(baseline_files | baseline_directories | {Path(__file__).resolve()})
    guard.install()
    guard.self_check()
    output.mkdir()
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
    baseline_hashes = {str(path): digest(path) for path in baseline_files}
    helper_sha = digest(Path(__file__))
    runtime_sha = mapping.runtime_binding()
    manifest = mapping.pinned(mapping.DIRECT_PROFILE, mapping.DIRECT_SHA)
    assert manifest['schema_version'] == 1 and manifest['policy'] == mapping.DIRECT_POLICY
    assert manifest['member_count'] == 2628 and manifest['group_count'] == len(manifest['groups']) == 294
    policy_inputs = {path: pin for path, pin in (
        (mapping.DIRECT_PROFILE, mapping.DIRECT_SHA), (mapping.PROFILE, mapping.PROFILE_SHA),
        (mapping.EXTENSION, mapping.EXTENSION_SHA), (mapping.PLAN, mapping.PLAN_SHA))}
    for relative, pin in manifest['review_sha256'].items():
        path = (repo / relative).resolve()
        assert path.is_relative_to(repo / 'docs/readiness/2026-10-06')
        policy_inputs[path] = pin
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    members = {}
    for group in manifest['groups']:
        for member in group['members']:
            sid = member['source_id']
            assert sid not in members and originals[sid + '.xml'] == member['source_sha256']
            members[sid] = group, member
    assert len(members) == manifest['member_count']
    all_ids = sorted(members, key=source_order)
    ids = all_ids[args.shard_index::args.shard_count]
    assert ids
    print('DIRECT_SHARD_START', args.shard_index, 'of', args.shard_count, 'assigned', len(ids), flush=True)
    compatibility = (retained_comparison(old, old_root, output, mapping, OutputPaths, MAX_BYTES, originals)
                     if old is not None else [])
    prepared_root, report_path, rows = measure_selected(
        ids, members, output, mapping, prepare_sources, OutputPaths, assess_source, MAX_BYTES, originals)
    assert [row['source_id'] for row in rows] == ids
    assert originals == {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert before == source_bindings(repo) and mapping.runtime_binding() == runtime_sha
    assert helper_sha == digest(Path(__file__)) and all(digest(path) == pin for path, pin in policy_inputs.items())
    if old is not None:
        assert digest(BASELINE) == BASELINE_SHA
        assert baseline_files == {path.resolve() for path in BASELINE.parent.rglob('*') if path.is_file()}
        assert baseline_hashes == {path: digest(Path(path)) for path in baseline_hashes}
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    artifact_manifest = output / 'wire_artifact_manifest.json'
    write_json(artifact_manifest, {'direct_rows': rows, 'retained105_rows': compatibility})
    receipt = output / 'coverage.json'
    write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_DIRECT_PRIMARY_SHARD_COVERAGE_PASS',
        'actual_checkout_revision': revision, 'helper_sha256': helper_sha, 'runtime_sha256': runtime_sha,
        'guard_sha256': GUARD_SHA, 'environment_cleared_dummy_credentials_only': True,
        'direct_profile': str(mapping.DIRECT_PROFILE.relative_to(repo)), 'direct_profile_sha256': mapping.DIRECT_SHA,
        'policy': mapping.DIRECT_POLICY, 'evidence_schema_version': 3,
        'source_census_sha256': manifest['source_census_sha256'], 'review_sha256': manifest['review_sha256'],
        'policy_input_bindings': {str(path.relative_to(repo)): pin for path, pin in policy_inputs.items()},
        'sharding': {'index': args.shard_index, 'count': args.shard_count,
                     'assignment': 'numeric source-ID order, then ids[index::count]',
                     'manifest_members': len(all_ids), 'manifest_groups': len(manifest['groups']),
                     'manifest_sorted_source_ids_sha256': mapping.sha(mapping.encode(all_ids)),
                     'assigned_source_ids': ids, 'actual_assigned_preparations': len(rows),
                     'actual_direct_prepare_calls': len(rows) * 2,
                     'represented_groups': len({members[sid][0]['profile'] for sid in ids}),
                     'all_shards_complete_claimed': False},
        'prepared_root': str(prepared_root), 'classification_sha256': digest(report_path),
        'classification_counts': {'supported': len(rows), 'held': 0, 'failed': 0},
        'wire_artifact_manifest_path': str(artifact_manifest.relative_to(output)),
        'wire_artifact_manifest_sha256': digest(artifact_manifest),
        'source_bindings_before': before, 'source_bindings_unchanged': True,
        'original_hashes': originals, 'original_hashes_sha256': mapping.sha(mapping.encode(originals)),
        'original_files_verified_before_and_after': 4206,
        'retained105': {'performed': old is not None, 'actual_preparations': len(compatibility),
                        'baseline_path': str(BASELINE) if old is not None else None,
                        'baseline_sha256': BASELINE_SHA if old is not None else None,
                        'baseline_files_before_and_after': baseline_hashes,
                        'baseline_paths_and_bytes_unchanged': True if old is not None else None,
                        'baseline_runtime_sha256': old['runtime_sha256'] if old is not None else None,
                        'wire_and_nonruntime_evidence_equal': True if old is not None else None},
        'guard': guard.counts, 'unexpected_guard_events': guard.blocked_call_sites,
        'in_process_read_only_git_queries': guard.metadata_queries,
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Actual assigned source classification, exact creators/date/access/rights, complete legacy '
                 'JSON preservation, raw XML, byte limits and equal repeated preparation. Retained105 '
                 'comparison only on shard zero. Aggregate coverage, live transport compatibility, grants, '
                 'production duplicate/history evidence, QA and human release remain separate.',
    })
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('DIRECT_SHARD_RESULT', json.dumps({'shard_index': args.shard_index, 'shard_count': args.shard_count,
          'actual_assigned_preparations': len(rows), 'retained105_compared': len(compatibility),
          'originals_preserved': 4206, 'receipt_sha256': digest(receipt), 'guard': guard.counts}), flush=True)


if __name__ == '__main__':
    main()
