"""Verify this frozen packet and run dummy-only checks; no live entry point.

Usage: python -B verify_and_test.py [--parser-check] [--parser-deps PATH]
No dependency installation, credential lookup, provider call or ledger migration.
"""
import argparse
import contextlib
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def check_packet():
    manifest = json.loads((ROOT / 'TRANSFER_MANIFEST.json').read_text())
    expected = manifest['files']
    actual = {str(path.relative_to(ROOT)) for path in ROOT.rglob('*') if path.is_file()}
    if actual != set(expected) | {'TRANSFER_MANIFEST.json'}:
        raise AssertionError('Packet membership differs from manifest')
    for name, item in expected.items():
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise AssertionError('Packet path is not a regular contained file')
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise AssertionError('Packet hash mismatch')
    return manifest


def namespace(name, directory):
    module = types.ModuleType(name)
    module.__path__ = [str(directory)]
    sys.modules[name] = module


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    original = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        # Preserve exact reviewed files while neutralizing their historical paths.
        sys.path[:] = original
    return module


def install_guard(temporary):
    denied = {'socket.__new__', 'socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname',
              'socket.gethostbyaddr', 'socket.sendto', 'socket.sendmsg',
              'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty'}
    private_parts = {'.aws', '.codex', '.agents', '.git'}
    private_names = {'secrets.txt', '.netrc', '_netrc', '.env'}
    def absolute(value, dir_fd=None):
        if isinstance(value, int):
            return Path(os.readlink('/proc/self/fd/' + str(value))).resolve()
        target = Path(os.fsdecode(value))
        if not target.is_absolute():
            anchor = (Path(os.readlink('/proc/self/fd/' + str(dir_fd)))
                      if isinstance(dir_fd, int) and dir_fd >= 0 else Path.cwd())
            target = anchor / target
        return target.resolve()
    def audit(event, args):
        if event in denied:
            raise AssertionError('Offline transfer check blocked network/process access')
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            target = Path(os.fsdecode(args[0])).resolve()
            if target.name in private_names or target.name.startswith('.env.') or set(target.parts) & private_parts:
                raise AssertionError('Offline transfer check blocked private-file access')
            mode, flags = args[1], args[2]
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or bool(
                (flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing and not target.is_relative_to(temporary):
                raise AssertionError('Offline transfer check blocked nonfixture write')
        if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename'}:
            if event == 'os.rename':
                candidates = ((args[0], args[2]), (args[1], args[3]))
            elif event == 'os.mkdir':
                candidates = ((args[0], args[2]),)
            else:
                candidates = ((args[0], args[1]),)
            for value, dir_fd in candidates:
                if not absolute(value, dir_fd).is_relative_to(temporary):
                    raise AssertionError('Offline transfer check blocked nonfixture mutation')
        if event in {'os.symlink', 'os.link', 'os.truncate', 'os.chmod', 'os.chown',
                     'os.utime', 'os.setxattr', 'os.removexattr'}:
            raise AssertionError('Offline transfer check blocked unused mutation')
    sys.addaudithook(audit)


def check_guard():
    # Audit-only probes perform no operation if a guard regresses.
    for event, args in [('os.remove', ('outside-fixture', -1)),
                        ('os.rename', ('outside-a', 'outside-b', -1, -1)),
                        ('socket.__new__', (None, 2, 1, 0)),
                        ('os.symlink', ('outside-a', 'outside-b', -1))]:
        try:
            sys.audit(event, *args)
        except AssertionError:
            continue
        raise AssertionError('Offline guard self-check failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parser-check', action='store_true')
    parser.add_argument('--parser-deps', type=Path)
    args = parser.parse_args()
    manifest = check_packet()
    if tuple(sys.version_info[:3]) != (3, 12, 14):
        raise AssertionError('Reproduction is pinned to Python 3.12.14')
    os.environ.clear()
    with tempfile.TemporaryDirectory(prefix='pices-transfer-offline-') as fixture:
        temporary = Path(fixture).resolve()
        tempfile.tempdir = str(temporary)
        install_guard(temporary)
        check_guard()
        for package, version in manifest['transport_versions'].items():
            if importlib.metadata.version(package) != version:
                raise AssertionError('Pinned transport dependency mismatch')
        namespace('scripts', ROOT / 'support/scripts')
        load('scripts.modern_canary_errors', 'support/scripts/modern_canary_errors.py')
        load('scripts.modern_synthetic_canary', 'support/scripts/modern_synthetic_canary.py')
        namespace('response', ROOT / 'response')
        capture = load('response.response_capture', 'response/response_capture.py')
        sys.modules['response_capture'] = capture
        load('write_observer', 'write_observer.py')
        modules = [load('test_write_observer', 'test_write_observer.py'),
                   load('test_observer_adversarial', 'review/test_observer_adversarial.py'),
                   load('test_response_capture', 'response/test_response_capture.py')]
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        if not result.wasSuccessful() or result.testsRun != 40:
            raise AssertionError('Offline component checks failed')
        demo_output = io.StringIO()
        with contextlib.redirect_stdout(demo_output):
            runpy.run_path(str(ROOT / 'offline_demo.py'), run_name='__main__')
        demo = json.loads(demo_output.getvalue())
        assert demo['normal']['local_body_send_completed'] is True
        assert demo['proxy']['local_body_send_completed'] is True
        assert demo['suppressed_partial_write']['write_failure_observed'] is True
        assert demo['suppressed_partial_write']['local_body_send_completed'] is False
        parser_cases = None
        if args.parser_check:
            if args.parser_deps is not None:
                sys.path.insert(0, str(args.parser_deps.resolve()))
            for package, version in manifest['parser_versions'].items():
                if importlib.metadata.version(package) != version:
                    raise AssertionError('Pinned parser dependency mismatch')
            parser_output = io.StringIO()
            with contextlib.redirect_stdout(parser_output):
                runpy.run_path(str(ROOT / 'concurrency/reproduce_if_match.py'), run_name='__main__')
            parsed = json.loads(parser_output.getvalue())
            assert parsed['passed'] is True and parsed['test_client_requests'] == 8
            parser_cases = 8
        print(json.dumps({'packet_verified': True, 'offline_tests_passed': result.testsRun,
                          'simulated_demo_passed': True, 'parser_cases_passed': parser_cases,
                          'live_zenodo_requests': 0, 'approved_for_live_dispatch': False}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
