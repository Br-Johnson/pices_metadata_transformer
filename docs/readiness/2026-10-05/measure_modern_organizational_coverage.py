"""Measure finite modern coverage offline and compare retained PR35 beforeimages.

Only fresh /tmp output is writable. The exact public, guard-produced baseline
and its prepared inputs are read-only exceptions; provider/private I/O is blocked.
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
BASELINE_SHA = '7e1d0ccb825c5114df5abc1e9ae0f7a83ddeda501ef2e0abc56ac70ae3e36940'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def nonruntime(evidence):
    return {key: value for key, value in evidence.items() if key != 'runtime_sha256'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    args = parser.parse_args()
    repo, output, baseline = args.repo.resolve(), args.output.resolve(), args.baseline.resolve()
    if (not output.is_relative_to(Path('/tmp')) or output == Path('/tmp')
            or output.is_relative_to(repo) or output.exists() or not output.parent.is_dir()):
        raise ValueError('Choose a fresh /tmp output directory')
    if digest(repo / 'ci/run_offline_tests.py') != GUARD_SHA or digest(baseline) != BASELINE_SHA:
        raise ValueError('Guard or frozen public baseline differs')
    old = json.loads(baseline.read_bytes())
    old_root = Path(old['prepared_root']).resolve()
    if not old_root.is_relative_to(baseline.parent) or output.is_relative_to(baseline.parent):
        raise ValueError('Preserve baseline directory')
    baseline_files = {p.resolve() for p in baseline.parent.rglob('*') if p.is_file()}
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
    guard.library_files.update(baseline_files | {Path(__file__).resolve()})
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
    originals = {p.name: digest(p) for p in sorted((repo / 'FGDC').glob('*.xml'))}
    assert len(originals) == 4206
    class RetainedPaths(OutputPaths):
        # The normal adapter calls makedirs even for existing directories.
        # Resolve identical retained paths without attempting any baseline write.
        def _prepare_dir(self, new_path, legacy_path=None, migrate_patterns=None):
            assert Path(new_path).is_dir()
            return new_path

        def _prepare_file(self, new_path, legacy_path=None):
            assert Path(new_path).parent.is_dir()
            return new_path

    baseline_hashes = {str(path): digest(path) for path in baseline_files}
    original_paths = RetainedPaths(str(old_root), 'production')
    compatibility = []
    for prior in old['rows']:
        sid = prior['source_id']
        current = mapping.prepare(Path(original_paths.zenodo_json_dir) / (sid + '.json'), original_paths)
        assert current.body == mapping.encode(prior['wire']) and mapping.sha(current.xml) == prior['xml_sha256']
        assert nonruntime(current.evidence) == nonruntime(prior['evidence'])
        compatibility.append({'source_id': sid, 'wire_sha256': mapping.sha(current.body),
                              'nonruntime_evidence_sha256': mapping.sha(mapping.encode(nonruntime(current.evidence))),
                              'original_binding': prior['binding'], 'current_binding': current.binding})
    assert len(compatibility) == 19
    extension = mapping.pinned(mapping.EXTENSION, mapping.EXTENSION_SHA)
    ids = [row['source_id'] for row in extension['members']] + [row['source_id'] for row in old['rows']]
    assert len(ids) == len(set(ids)) == 105
    prepared_root = prepare_sources(output, ids)
    paths = OutputPaths(str(prepared_root), 'production')
    rows = []
    for sid in sorted(ids, key=lambda item: int(item[5:])):
        json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
        current = mapping.prepare(json_file, paths)
        repeated = mapping.prepare(json_file, paths)
        assert current == repeated and len(current.body) <= MAX_BYTES and len(current.xml) <= MAX_BYTES
        metadata, source_sha, _, _ = assess_source(json_file, paths)
        wire = mapping.parse(current.body)
        preserved = wire['metadata']['additional_descriptions'][0]['description'].split('<pre>', 1)[1][:-6]
        assert json.loads(html.unescape(preserved)) == metadata
        assert mapping.sha(current.xml) == source_sha == originals[sid + '.xml']
        rows.append({'source_id': sid, 'binding': current.binding, 'evidence': current.evidence,
                     'body_bytes': len(current.body), 'xml_bytes': len(current.xml),
                     'creator_count': len(metadata['creators']), 'complete_legacy_preserved': True,
                     'unchanged_repeat_equal': True})
    try:
        mapping.source_policy('FGDC-710')
    except mapping.Held:
        pass
    else:
        raise AssertionError('FGDC-710 hold lost')
    assert originals == {name: digest(repo / 'FGDC' / name) for name in originals}
    assert before == source_bindings(repo) and digest(baseline) == BASELINE_SHA
    assert baseline_hashes == {path: digest(Path(path)) for path in baseline_hashes}
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    write(output / 'coverage.json', {
        'schema_version': 1, 'status': 'GUARDED_FINITE_MODERN_105_COVERAGE_PASS',
        'actual_checkout_revision': revision, 'helper_sha256': digest(Path(__file__)),
        'runtime_sha256': mapping.runtime_binding(), 'extension_sha256': mapping.EXTENSION_SHA,
        'baseline_sha256': BASELINE_SHA, 'baseline_runtime_sha256': old['runtime_sha256'],
        'original19_nonruntime_and_wire_equal': compatibility,
        'source_bindings_before': before, 'source_bindings_unchanged': True,
        'original_hashes_sha256': mapping.sha(mapping.encode(originals)),
        'original_files_verified_before_and_after': 4206,
        'coverage': {'prior': 19, 'added': 86, 'total': 105, 'supported_target_total': 3933,
                     'supported_targets_outside_modern_scope': 3828,
                     'unsupported_typed_organization_hold': ['FGDC-710']},
        'rows': rows, 'guard': guard.counts, 'unexpected_guard_events': guard.blocked_call_sites,
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Actual source mapping, payload limits, exact repeat and retained old19 comparison. '
                 'Live transport compatibility, grants, production duplicate/history evidence, '
                 'QA, independent program review and human release remain separate.'})
    print(json.dumps({'coverage': 105, 'added': 86, 'originals_preserved': 4206,
                      'receipt_sha256': digest(output / 'coverage.json'), 'guard': guard.counts}))


if __name__ == '__main__':
    main()
