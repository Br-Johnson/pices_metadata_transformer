"""Guarded Exxon measurement: fresh new sources and retained PR37 comparisons.

Run only after the runtime/test freeze. Four shards each classify 103 new IDs
and prepare them twice, while preparing their share of the 2733 retained inputs
once at the original paths. Frozen public inputs and eight exact old-checkout
profile files are read-only exceptions; only a fresh /tmp output may be written.
No live compatibility, provider grant, aggregate completion or release is implied.
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

GUARD_SHA = '1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05'
AGGREGATE = Path('docs/readiness/2026-10-06/modern_direct_primary_validation.json')
AGGREGATE_SHA = 'dee8b89dfb8f452b1d88b5e23face7ba81417ca0b23ba1b4d198b158bf900464'
OLD105 = Path('/tmp/pices-modern-old105-baseline-20261006/baseline.json')
OLD105_SHA = '87599287eadabf8a75f26667a39705b64c1c5cba888f67a5a664ae5ec8b183e0'
OLD_PROFILES = Path('/workspace/pices-modern-primary-organizations-20261006/docs/readiness')
PROFILE_FILES = {
    '2026-10-02/contact_source_interpretation.json',
    '2026-10-02/contributor_source_interpretation.json',
    '2026-10-02/rehosting_authority.json',
    '2026-10-03/historical_dataset_linkage_21.json',
    '2026-10-03/source_scope_reconciliation_904.json',
    '2026-10-04/finite_source_resource_access_655.json',
    '2026-10-04/source_citation_credits_426.json',
    '2026-10-04/source_display_titles_42.json',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def nonruntime(evidence):
    return {key: value for key, value in evidence.items() if key != 'runtime_sha256'}


def source_order(source_id):
    assert re.fullmatch(r'FGDC-[1-9][0-9]*', source_id)
    return int(source_id[5:])


def retained_catalogue(repo):
    """Read only pinned public evidence to derive the exact file allowlist."""
    roots = [Path(f'/tmp/pices-direct-primary-shard{index}-v1') for index in range(4)]
    frozen, retained, profiles = {}, {}, {}

    def track(path, pin=None):
        path = Path(path)
        assert not path.is_symlink() and path.resolve() == path
        assert any(path.is_relative_to(root) for root in [*roots, OLD105.parent])
        if str(path) in frozen:
            assert pin is None or frozen[str(path)] == pin
            return path
        actual = digest(path)
        assert pin is None or actual == pin
        assert str(path) not in frozen or frozen[str(path)] == actual
        frozen[str(path)] = actual
        return path

    aggregate_path = repo / AGGREGATE
    assert digest(aggregate_path) == AGGREGATE_SHA
    aggregate = json.loads(aggregate_path.read_bytes())
    assert aggregate['all_shards_complete'] and aggregate['coverage']['total'] == 2733
    assert len(aggregate['rows']) == 2628 and len(aggregate['retained105_wire_and_nonruntime_comparisons']) == 105
    aggregate_direct = {row['source_id']: row for row in aggregate['rows']}
    aggregate_old105 = {row['source_id']: row for row in aggregate['retained105_wire_and_nonruntime_comparisons']}
    assert len(aggregate_direct) == 2628 and len(aggregate_old105) == 105
    old = json.loads(track(OLD105, OLD105_SHA).read_bytes())
    old_root = Path(old['prepared_root'])
    assert old_root.is_relative_to(OLD105.parent) and len(old['rows']) == 105
    baseline_ids = {row['source_id'] for row in old['rows']}
    assert baseline_ids == set(aggregate_old105)
    assert [row['index'] for row in aggregate['shards']] == list(range(4))

    for shard in aggregate['shards']:
        root = roots[shard['index']]
        assert shard['root'] == str(root)
        coverage = json.loads(track(root / 'coverage.json', shard['receipt_sha256']).read_bytes())
        manifest = json.loads(track(root / 'wire_artifact_manifest.json', shard['artifact_manifest_sha256']).read_bytes())
        prepared_root = Path(coverage['prepared_root'])
        assert prepared_root == root / 'prepared'
        track(prepared_root / 'classification.json', coverage['classification_sha256'])
        assert len(manifest['direct_rows']) == shard['source_count'] == 657
        assert [row['source_id'] for row in manifest['direct_rows']] == coverage['sharding']['assigned_source_ids']
        if shard['index'] == 0:
            for path, pin in coverage['retained105']['baseline_files_before_and_after'].items():
                track(Path(path), pin)
            assert len(manifest['retained105_rows']) == 105
        else:
            assert not manifest['retained105_rows']
        for prior, root_for_input, aggregate_rows in [
            *((row, prepared_root, aggregate_direct) for row in manifest['direct_rows']),
            *((row, old_root, aggregate_old105) for row in manifest['retained105_rows']),
        ]:
            sid = prior['source_id']
            source_order(sid)
            assert sid not in retained
            proof = aggregate_rows[sid]
            for key in ('source_sha256', 'wire_sha256', 'preparation_sha256'):
                assert prior[key] == proof[key]
            preparation_path = track(root / prior['preparation_path'], prior['preparation_sha256'])
            preparation = json.loads(preparation_path.read_bytes())
            evidence = preparation['evidence']
            assert preparation['source_id'] == evidence['source_id'] == sid
            assert evidence['source_sha256'] == prior['source_sha256']
            assert evidence['wire_sha256'] == prior['wire_sha256']
            assert preparation['binding'] == hashlib.sha256(encode(evidence)).hexdigest()
            assert preparation['binding'] == prior.get('binding', prior.get('current_binding'))
            input_path = track(root_for_input / 'data/zenodo_json' / (sid + '.json'), evidence['prepared_input_sha256'])
            wire_path = track(root / prior['wire_path'], prior['wire_sha256'])
            track(root_for_input / 'data/original_fgdc' / (sid + '.xml'), prior['source_sha256'])
            if sid in aggregate_direct:
                track(root / 'sources' / (sid + '.xml'), prior['source_sha256'])
            payload = json.loads(input_path.read_bytes())
            for reference in payload['artifact_policy'].values():
                if not isinstance(reference, dict) or 'manifest_path' not in reference:
                    continue
                path = Path(reference['manifest_path'])
                assert path.is_relative_to(OLD_PROFILES) and path.resolve() == path and not path.is_symlink()
                relative = path.relative_to(OLD_PROFILES)
                assert str(relative) in PROFILE_FILES
                pin = reference['manifest_sha256']
                if str(path) in profiles:
                    assert profiles[str(path)] == pin
                else:
                    assert digest(path) == pin == digest(repo / 'docs/readiness' / relative)
                    profiles[str(path)] = pin
            retained[sid] = {
                'source_id': sid, 'source_sha256': prior['source_sha256'],
                'prepared_root': str(root_for_input), 'prepared_input_path': str(input_path),
                'wire_path': str(wire_path), 'wire_sha256': prior['wire_sha256'],
                'preparation_path': str(preparation_path), 'preparation_sha256': prior['preparation_sha256'],
                'evidence': evidence, 'binding': preparation['binding'],
            }
    assert len(retained) == 2733 and set(retained) == set(aggregate_direct) | set(aggregate_old105)
    assert {str(Path(path).relative_to(OLD_PROFILES)) for path in profiles} == PROFILE_FILES
    return retained, frozen, profiles, [*roots, OLD105.parent]


def check_preservation(mapping, prepared, metadata, personal_display=False):
    wire = mapping.parse(prepared.body)
    preserved = wire['metadata']['additional_descriptions'][0]['description']
    assert preserved.startswith('<p>' + mapping.PRESERVATION_LABEL + '</p><pre>') and preserved.endswith('</pre>')
    assert json.loads(html.unescape(preserved.split('<pre>', 1)[1][:-6])) == metadata
    for key in ('title', 'description', 'publication_date'):
        assert wire['metadata'][key] == metadata[key]
    assert wire['metadata']['subjects'] == [{'subject': value} for value in metadata.get('keywords', [])]
    assert metadata['access_right'] == 'restricted' and metadata['license'] == ''
    assert wire['access'] == {'record': 'public', 'files': 'restricted'} and wire['files'] == {'enabled': True}
    assert wire['metadata']['publisher'] == 'Zenodo'
    assert 'rights' not in wire['metadata'] and 'license' not in wire['metadata']
    mapping.compare_metadata(wire['metadata'], wire['metadata'])
    with_defaults = {**wire['metadata'], 'dates': [], 'rights': [], 'identifiers': [], 'languages': []}
    mapping.compare_metadata(with_defaults, wire['metadata'])
    if personal_display:
        # Exercise only the service-derived display for the new reviewed people.
        displayed = json.loads(json.dumps(with_defaults))
        for creator in displayed['creators']:
            person = creator['person_or_org']
            if person['type'] == 'personal':
                person['name'] = person['family_name'] + ', ' + person['given_name']
        mapping.compare_metadata(displayed, wire['metadata'])
    return wire


def compare_retained(ids, retained, output, mapping, output_paths, max_bytes, originals):
    class RetainedPaths(output_paths):
        def _prepare_dir(self, new_path, legacy_path=None, migrate_patterns=None):
            assert Path(new_path).is_dir()
            return new_path

        def _prepare_file(self, new_path, legacy_path=None):
            assert Path(new_path).parent.is_dir()
            return new_path

    paths_by_root = {}
    directory = output / 'retained'
    directory.mkdir()
    rows = []
    for index, sid in enumerate(ids, 1):
        prior = retained[sid]
        root = prior['prepared_root']
        if root not in paths_by_root:
            paths_by_root[root] = RetainedPaths(root, 'production')
        current = mapping.prepare(Path(prior['prepared_input_path']), paths_by_root[root])
        assert current.body == Path(prior['wire_path']).read_bytes()
        assert nonruntime(current.evidence) == nonruntime(prior['evidence'])
        assert mapping.sha(current.xml) == prior['source_sha256'] == originals[sid + '.xml']
        assert current.xml == (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        legacy = mapping.parse(current.body)['metadata']['additional_descriptions'][0]['description']
        metadata = json.loads(html.unescape(legacy.split('<pre>', 1)[1][:-6]))
        assert mapping.sha(mapping.encode(metadata)) == current.evidence['legacy_metadata_sha256']
        check_preservation(mapping, current, metadata)
        evidence_path = directory / (sid + '.preparation.json')
        write_json(evidence_path, {'source_id': sid, 'binding': current.binding, 'evidence': current.evidence})
        rows.append({key: value for key, value in prior.items() if key != 'evidence'} | {
            'current_binding': current.binding, 'current_preparation_path': str(evidence_path.relative_to(output)),
            'current_preparation_sha256': digest(evidence_path),
            'wire_and_nonruntime_evidence_equal': True,
            'nonruntime_evidence_sha256': mapping.sha(mapping.encode(nonruntime(current.evidence))),
        })
        if index % 50 == 0 or index == len(ids):
            print('RETAINED_PR37_PROGRESS', index, 'of', len(ids), flush=True)
    return rows


def measure_new(ids, members, output, mapping, prepare_sources, output_paths, assess_source, max_bytes, originals):
    prepared_root = prepare_sources(output, ids=ids)
    paths = output_paths(str(prepared_root), 'production')
    report_path = prepared_root / 'classification.json'
    report = json.loads(report_path.read_bytes())
    assert len(report['records']) == len(ids) and {row['source_id'] for row in report['records']} == set(ids)
    assert report['summary']['source_status_counts'] == {'supported': len(ids), 'held': 0, 'failed': 0}
    assert {path.stem for path in (output / 'sources').glob('*.xml')} == set(ids)
    assert {path.stem for path in Path(paths.zenodo_json_dir).glob('*.json')} == set(ids)
    creator_profile = mapping.pinned(mapping.EXXON_PROFILE, mapping.EXXON_SHA)
    directory = output / 'exxon'
    directory.mkdir()
    rows = []
    for index, sid in enumerate(ids, 1):
        json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw = json_file.read_bytes()
        current, repeated = mapping.prepare(json_file, paths), mapping.prepare(json_file, paths)
        assert current == repeated and raw == json_file.read_bytes()
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        metadata, source_sha, artifact, _ = assess_source(json_file, paths)
        assert metadata['creators'] == creator_profile['creators']
        reference = mapping.parse(raw)['artifact_policy']['creator_interpretation']
        assert reference['manifest_sha256'] == mapping.EXXON_SHA
        assert current.evidence['schema_version'] == 4 and current.evidence['policy'] == mapping.EXXON_POLICY
        assert current.evidence['mapping_manifest_sha256'] == mapping.EXXON_MAPPING_SHA
        assert current.evidence['creator_profile_sha256'] == mapping.EXXON_SHA
        assert current.evidence['artifact_contract'] == artifact
        wire = check_preservation(mapping, current, metadata, personal_display=True)
        expected = [{'person_or_org': {'name': metadata['creators'][0]['name'], 'type': 'organizational'}}]
        for creator in metadata['creators'][1:]:
            family, given = creator['name'].split(', ', 1)
            expected.append({'person_or_org': {'type': 'personal', 'family_name': family, 'given_name': given},
                             'affiliations': [{'name': creator['affiliation']}]})
        assert wire['metadata']['creators'] == expected
        original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        copy_path = Path(paths.original_fgdc_dir) / (sid + '.xml')
        assert current.xml == original == copy_path.read_bytes() == (output / 'sources' / (sid + '.xml')).read_bytes()
        assert mapping.sha(current.xml) == source_sha == members[sid]['source_sha256'] == originals[sid + '.xml']
        wire_path, evidence_path = directory / (sid + '.wire.json'), directory / (sid + '.preparation.json')
        with wire_path.open('xb') as stream:
            stream.write(current.body)
        write_json(evidence_path, {'source_id': sid, 'binding': current.binding, 'evidence': current.evidence,
                                  'complete_legacy_metadata': metadata, 'complete_legacy_metadata_preserved': True,
                                  'exact_creators_date_access_and_rights': True, 'unchanged_repeat_equal': True})
        rows.append({'source_id': sid, 'source_sha256': source_sha, 'binding': current.binding,
                     'policy': current.evidence['policy'], 'prepared_input_path': str(json_file.relative_to(output)),
                     'prepared_input_sha256': mapping.sha(raw), 'original_copy_path': str(copy_path.relative_to(output)),
                     'wire_path': str(wire_path.relative_to(output)), 'wire_sha256': digest(wire_path),
                     'preparation_path': str(evidence_path.relative_to(output)), 'preparation_sha256': digest(evidence_path),
                     'body_bytes': len(current.body), 'xml_bytes': len(current.xml)})
        if index % 50 == 0 or index == len(ids):
            print('NEW_EXXON_PROGRESS', index, 'of', len(ids), flush=True)
    return prepared_root, report_path, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shard-index', type=int, choices=range(4), required=True)
    parser.add_argument('--shard-count', type=int, choices=(4,), default=4)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    baseline_roots = [Path(f'/tmp/pices-direct-primary-shard{index}-v1') for index in range(4)] + [OLD105.parent]
    if (not output.is_relative_to(Path('/tmp')) or output == Path('/tmp') or output.exists()
            or output.is_relative_to(repo) or not output.parent.is_dir()
            or any(output.is_relative_to(root) for root in baseline_roots)):
        raise ValueError('Choose a fresh /tmp output outside retained inputs')
    if digest(repo / 'ci/run_offline_tests.py') != GUARD_SHA:
        raise ValueError('Offline guard differs')
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
    retained, frozen, profile_files, baseline_roots = retained_catalogue(repo)
    allowed = {Path(path) for path in frozen} | {Path(path) for path in profile_files}
    # Directory listing is read-only; it does not permit opens of unlisted files.
    for path in frozen:
        allowed.update(parent for parent in Path(path).parents if any(parent.is_relative_to(root) for root in baseline_roots))
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)
    guard = OfflineGuard(repo, output, revision)
    guard.library_files.update(allowed | {Path(__file__).resolve()})
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
    assert all(digest(Path(path)) == pin for path, pin in frozen.items())
    assert all(digest(Path(path)) == pin for path, pin in profile_files.items())
    helper_sha, runtime_sha = digest(Path(__file__)), mapping.runtime_binding()
    manifest = mapping.pinned(mapping.EXXON_MAPPING, mapping.EXXON_MAPPING_SHA)
    assert manifest['policy'] == mapping.EXXON_POLICY
    members = {member['source_id']: member for member in manifest['members']}
    assert len(members) == len(manifest['members']) == 412 and not set(members) & set(retained)
    for sid, member in members.items():
        assert originals[sid + '.xml'] == member['source_sha256']
    all_new, all_old = sorted(members, key=source_order), sorted(retained, key=source_order)
    new_ids, old_ids = all_new[args.shard_index::4], all_old[args.shard_index::4]
    assert len(new_ids) == 103
    policy_inputs = {path: pin for path, pin in [
        (mapping.EXXON_MAPPING, mapping.EXXON_MAPPING_SHA), (mapping.EXXON_PROFILE, mapping.EXXON_SHA),
        (mapping.PROFILE, mapping.PROFILE_SHA), (mapping.EXTENSION, mapping.EXTENSION_SHA),
        (mapping.DIRECT_PROFILE, mapping.DIRECT_SHA), (mapping.PLAN, mapping.PLAN_SHA),
        (repo / AGGREGATE, AGGREGATE_SHA),
        (repo / 'docs/readiness/2026-10-06/modern_exxon_source_review.json', manifest['review_sha256']),
        (repo / 'docs/readiness/2026-10-06/modern_exxon_creator_contract.json', manifest['service_contract_sha256']),
    ]}
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    print('EXXON_SHARD_START', args.shard_index, 'new', len(new_ids), 'retained', len(old_ids), flush=True)
    prepared_root, report_path, rows = measure_new(
        new_ids, members, output, mapping, prepare_sources, OutputPaths, assess_source, MAX_BYTES, originals)
    compatibility = compare_retained(old_ids, retained, output, mapping, OutputPaths, MAX_BYTES, originals)
    assert [row['source_id'] for row in rows] == new_ids
    assert [row['source_id'] for row in compatibility] == old_ids
    assert originals == {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert before == source_bindings(repo) and runtime_sha == mapping.runtime_binding()
    assert helper_sha == digest(Path(__file__))
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    assert all(digest(Path(path)) == pin for path, pin in frozen.items())
    assert all(digest(Path(path)) == pin for path, pin in profile_files.items())
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    artifact_manifest = output / 'wire_artifact_manifest.json'
    write_json(artifact_manifest, {'exxon_rows': rows, 'retained2733_rows': compatibility})
    baseline_manifest = output / 'retained_file_manifest.json'
    write_json(baseline_manifest, {'public_baseline_files': frozen, 'exact_public_profile_files': profile_files})
    receipt = output / 'coverage.json'
    write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_EXXON_SHARD_COVERAGE_PASS', 'actual_checkout_revision': revision,
        'helper_sha256': helper_sha, 'runtime_sha256': runtime_sha, 'guard_sha256': GUARD_SHA,
        'environment_cleared_dummy_credentials_only': True, 'aggregate_baseline_sha256': AGGREGATE_SHA,
        'old105_baseline_sha256': OLD105_SHA, 'exxon_mapping_sha256': mapping.EXXON_MAPPING_SHA,
        'creator_profile_sha256': mapping.EXXON_SHA, 'policy': mapping.EXXON_POLICY, 'evidence_schema_version': 4,
        'policy_input_bindings': {str(path.relative_to(repo)): pin for path, pin in policy_inputs.items()},
        'sharding': {'index': args.shard_index, 'count': 4, 'assignment': 'numeric IDs, independently ids[index::4]',
                     'new_manifest_members': 412, 'retained_baseline_members': 2733,
                     'sorted_new_ids_sha256': mapping.sha(mapping.encode(all_new)),
                     'sorted_retained_ids_sha256': mapping.sha(mapping.encode(all_old)),
                     'assigned_new_source_ids': new_ids, 'assigned_retained_source_ids': old_ids,
                     'actual_new_preparations': len(rows), 'actual_new_prepare_calls': len(rows) * 2,
                     'actual_retained_comparisons': len(compatibility), 'all_shards_complete_claimed': False},
        'prepared_root': str(prepared_root), 'classification_sha256': digest(report_path),
        'classification_counts': {'supported': len(rows), 'held': 0, 'failed': 0},
        'wire_artifact_manifest_path': artifact_manifest.name, 'wire_artifact_manifest_sha256': digest(artifact_manifest),
        'retained_file_manifest_path': baseline_manifest.name, 'retained_file_manifest_sha256': digest(baseline_manifest),
        'all2733_retained_file_hashes_verified_before_and_after': True,
        'retained_file_count': len(frozen), 'exact_public_profile_file_count': len(profile_files),
        'retained_paths_and_bytes_unchanged': True, 'source_bindings_before': before, 'source_bindings_unchanged': True,
        'original_hashes': originals, 'original_hashes_sha256': mapping.sha(mapping.encode(originals)),
        'original_files_verified_before_and_after': 4206, 'guard': guard.counts,
        'unexpected_guard_events': guard.blocked_call_sites, 'in_process_read_only_git_queries': guard.metadata_queries,
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Actual assigned fresh Exxon classification and repeat preparation; retained PR37 preparation '
                 'once per assigned source at exact original paths, with byte-equal wire and equal nonruntime '
                 'evidence. All retained public file hashes and 4206 originals preserved. Expected aggregate 3145 '
                 'coverage and 788 remaining targets require aggregation; no live compatibility, provider grant, '
                 'production identity, QA approval or release is asserted.',
    })
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('EXXON_SHARD_RESULT', json.dumps({'shard_index': args.shard_index, 'actual_new_preparations': len(rows),
          'actual_retained_comparisons': len(compatibility), 'receipt_sha256': digest(receipt), 'guard': guard.counts}),
          flush=True)


if __name__ == '__main__':
    main()
