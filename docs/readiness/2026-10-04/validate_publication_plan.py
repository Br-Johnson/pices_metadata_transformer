"""Measure a finite publication dry run with the existing offline I/O guard.

Fresh output only; preserves original input hashes and compares exact repeated
plans without classifying sources or constructing any provider client.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

GUARD_SHA256 = '1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    if (not output.is_relative_to(Path('/tmp')) or output == Path('/tmp')
            or output.is_relative_to(repo) or output.exists() or not output.parent.is_dir()):
        raise ValueError('Choose a fresh /tmp output directory outside the repository')
    if sha(repo / 'ci/run_offline_tests.py') != GUARD_SHA256:
        raise ValueError('Offline guard changed')
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
    guard.library_files.add(Path(__file__).resolve())
    guard.install()
    guard.self_check()
    output.mkdir()
    before = source_bindings(repo)
    from scripts.publication_plan import PINS, build_plan

    originals = {str(p.relative_to(repo)): sha(p) for p in sorted((repo / 'FGDC').glob('*.xml'))}
    plan = build_plan(repo)
    repeated = build_plan(repo)
    if plan != repeated:
        raise ValueError('Dry-run plan changed on unchanged retry')
    if originals != {path: sha(repo / path) for path in originals}:
        raise ValueError('Original XML changed during planning')
    if before != source_bindings(repo):
        raise ValueError('Runtime/test/contract inputs changed during planning')
    unexpected = guard.blocked_call_sites
    if unexpected or any(guard.counts['tests'].values()):
        raise ValueError('Unexpected guarded I/O')
    write(output / 'publication_plan.json', plan)
    receipt = {
        'schema_version': 1, 'status': 'GUARDED_NONEXECUTABLE_PUBLICATION_PLAN_PASS',
        'actual_checkout_revision': revision, 'helper_sha256': sha(Path(__file__).resolve()),
        'planner_sha256': sha(repo / 'scripts/publication_plan.py'),
        'source_bindings_before': before, 'source_bindings_unchanged': True,
        'profile_and_evidence_pins': PINS, 'original_hashes': originals,
        'original_files_verified_before_and_after': len(originals),
        'unchanged_repeat_equal': True, 'summary': plan['summary'],
        'publication_inputs_sha256': plan['publication_inputs_sha256'],
        'plan_sha256': plan['plan_sha256'],
        'output_file_sha256': sha(output / 'publication_plan.json'),
        'guard': guard.counts, 'unexpected_guard_events': unexpected,
        'provider_requests': 0, 'provider_mutations': 0,
        'source_classification_runs': 0,
        'scope': 'Actual offline manifest and repeated dry run only; no private registry, '
                 'capture import, provider identity adoption, transport or release validation.',
    }
    write(output / 'validation.json', receipt)
    print(json.dumps({'output': str(output), **plan['summary']}, sort_keys=True))


if __name__ == '__main__':
    main()
