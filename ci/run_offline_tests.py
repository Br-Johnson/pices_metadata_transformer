"""Portable guarded unittest entry point; only temporary dummy fixtures may write.

Dependency installation happens before this process. Test imports run after the
environment is cleared and transport/private-file/subprocess guards are installed.
The guard prevents accidental I/O; it is not an isolation boundary for hostile code.
"""

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import sysconfig
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

REPO = Path(__file__).resolve().parents[1]
DUMMY_TOKEN = 'dummy-pices-offline-ci-only'
TOKEN_KEYS = ('ZENODO_ACCESS_TOKEN', 'ZENODO_SANDBOX_ACCESS_TOKEN',
              'ZENODO_API_TOKEN', 'ZENODO_SANDBOX_TOKEN')
PRIVATE_NAMES = {'secrets.txt', '.netrc', '_netrc', '.env'}
PRIVATE_PARTS = {'.git', '.aws', '.codex', '.agents', 'private', 'runtime'}
REPO_PRIVATE_PARTS = {'output', 'logs', 'state', 'cache'}
MUTATIONS = {'os.remove', 'os.rename', 'os.rmdir', 'os.mkdir', 'os.link',
             'os.symlink', 'os.chmod', 'os.truncate', 'os.utime', 'os.chown',
             'os.setxattr', 'os.removexattr'}
PROCESS_EVENTS = {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec',
                  'os.fork', 'os.forkpty'}
NETWORK_EVENTS = {'socket.connect', 'socket.getaddrinfo',
                  'socket.gethostbyname', 'socket.gethostbyaddr', 'socket.sendto', 'socket.sendmsg'}


class GuardViolation(AssertionError):
    """Closed error text never includes a path, environment value or request."""


def clean_environment(fixture_root):
    return {'PATH': '/usr/bin:/bin', 'TMPDIR': str(fixture_root),
            'PYTHONDONTWRITEBYTECODE': '1', **dict.fromkeys(TOKEN_KEYS, DUMMY_TOKEN)}


def checkout_revision(repo):
    """Read only HEAD/ref metadata, including worktrees; never invoke Git/config."""
    dotgit = repo / '.git'
    if dotgit.is_dir():
        gitdir = dotgit
    else:
        pointer = dotgit.read_text().strip()
        if not pointer.startswith('gitdir: '):
            raise AssertionError('Invalid checkout metadata')
        gitdir = (repo / pointer[8:]).resolve()
    head = (gitdir / 'HEAD').read_text().strip()
    if re.fullmatch('[0-9a-f]{40}', head):
        return head
    if not head.startswith('ref: '):
        raise AssertionError('Invalid checkout HEAD')
    ref = head[5:]
    if (not re.fullmatch(r'refs/(?:heads|tags)/[A-Za-z0-9_./-]+', ref)
            or any(part in ('', '.', '..') for part in ref.split('/'))):
        raise AssertionError('Invalid checkout reference')
    common_file = gitdir / 'commondir'
    common = (gitdir / common_file.read_text().strip()).resolve() if common_file.exists() else gitdir
    reference = common / ref
    if reference.is_file():
        revision = reference.read_text().strip()
    else:
        revision = ''
        for line in (common / 'packed-refs').read_text().splitlines():
            if line and not line.startswith(('#', '^')):
                digest, name = line.split(' ', 1)
                if name == ref:
                    revision = digest
                    break
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise AssertionError('Invalid checkout revision')
    return revision


class OfflineGuard:
    def __init__(self, repo, fixture_root, revision=None):
        self.repo = Path(repo).resolve()
        self.fixture_root = Path(fixture_root).resolve()
        self.phase = 'bootstrap'
        self.counts = {phase: dict.fromkeys(('network', 'private_reads', 'writes', 'processes'), 0)
                       for phase in ('bootstrap', 'tests')}
        self.original_open = os.open
        self.revision = revision
        self.metadata_queries = 0
        self.blocked_call_sites = []
        self.library_roots = tuple(Path(sysconfig.get_path(name)).resolve()
                                   for name in ('stdlib', 'platstdlib', 'purelib', 'platlib'))
        self.library_files = {root.parent / f'python{sys.version_info.major}{sys.version_info.minor}.zip'
                              for root in self.library_roots[:2]}
        self.system_roots = (Path('/usr/share/zoneinfo'), Path('/etc/ssl/certs'))
        self.system_files = {Path('/etc/localtime').resolve(), Path('/etc/timezone'), Path('/etc/mime.types')}

    def reject(self, category):
        self.counts[self.phase][category] += 1
        if self.phase == 'tests' and len(self.blocked_call_sites) < 16:
            # Code names/line numbers only; never inspect locals or rejected paths.
            frames = []
            frame = sys._getframe(1)
            while frame is not None and len(frames) < 6:
                frames.append([Path(frame.f_code.co_filename).name, frame.f_lineno, frame.f_code.co_name])
                frame = frame.f_back
            self.blocked_call_sites.append({'category': category, 'frames': frames})
        raise GuardViolation('Offline CI blocked ' + category)

    @staticmethod
    def absolute_path(path, dir_fd=None, physical=True):
        if isinstance(path, int):
            path = os.readlink('/proc/self/fd/' + str(path))
        target = Path(os.fsdecode(path))
        if not target.is_absolute() and isinstance(dir_fd, int) and dir_fd >= 0:
            target = Path(os.readlink('/proc/self/fd/' + str(dir_fd))) / target
        return target.resolve() if physical else target.parent.resolve() / target.name

    def fixture(self, path):
        return path.is_relative_to(self.fixture_root)

    def check_write(self, path):
        if path.is_relative_to(self.repo) or not self.fixture(path):
            self.reject('writes')

    def check_read(self, target):
        if self.fixture(target):
            return
        parts, name = set(target.parts), target.name.casefold()
        if (name in PRIVATE_NAMES or name.startswith('.env.') or parts & PRIVATE_PARTS
                or (target.is_relative_to(self.repo) and parts & REPO_PRIVATE_PARTS)):
            self.reject('private_reads')
        if not (target.is_relative_to(self.repo) or target in self.system_files | self.library_files
                or any(target.is_relative_to(root) for root in (*self.library_roots, *self.system_roots))):
            self.reject('private_reads')

    def audit(self, event, args):
        if event in NETWORK_EVENTS:
            self.reject('network')
        if event in PROCESS_EVENTS:
            self.reject('processes')
        if event == 'open':
            path, mode, flags = args
            if not isinstance(path, (str, bytes, os.PathLike, int)):
                return
            if isinstance(path, int) and path in (0, 1, 2):
                return
            target = self.absolute_path(path)
            writing = ((isinstance(mode, str) and any(x in mode for x in 'wax+'))
                       or bool((flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT
                                              | os.O_TRUNC | os.O_APPEND)))
            if writing:
                self.check_write(target)
            self.check_read(target)
        if event in {'os.listdir', 'os.scandir'}:
            self.check_read(self.absolute_path(args[0] if args[0] is not None else os.getcwd()))
        if event in MUTATIONS:
            indexes = (1,) if event == 'os.symlink' else (
                (0, 1) if event in {'os.rename', 'os.link'} else (0,))
            for index in indexes:
                fd_index = (2 + index) if event in {'os.rename', 'os.link'} else (
                    1 if event in {'os.remove', 'os.rmdir'} else (
                        3 if event in {'os.utime', 'os.chown'} else 2))
                fd = args[fd_index] if len(args) > fd_index else None
                physical = event not in {'os.remove', 'os.rmdir', 'os.rename', 'os.symlink'}
                self.check_write(self.absolute_path(args[index], fd, physical))

    def guarded_open(self, path, flags, mode=0o777, *, dir_fd=None):
        # Python's open audit omits dir_fd; resolve descriptor-relative paths first.
        if dir_fd is not None and not Path(os.fsdecode(path)).is_absolute():
            path = str(self.absolute_path(path, dir_fd))
        return self.original_open(path, flags, mode, dir_fd=dir_fd)

    def no_network(self, *args, **kwargs):
        self.reject('network')

    def metadata_output(self, command, *args, **kwargs):
        """Serve only the existing exact read-only revision query in-process."""
        if (command == ['git', 'rev-parse', 'HEAD'] and not args
                and set(kwargs) == {'cwd', 'text'} and kwargs['text'] is True
                and Path(kwargs['cwd']).resolve() == self.repo
                and isinstance(self.revision, str) and re.fullmatch('[0-9a-f]{40}', self.revision)):
            self.metadata_queries += 1
            return self.revision + '\n'
        self.reject('processes')

    def install(self):
        # Clearing PYTHONPATH after startup does not remove injected sys.path entries.
        sys.path[:] = [value for value in sys.path if (
            Path(value or os.getcwd()).resolve().is_relative_to(self.repo)
            or Path(value or os.getcwd()).resolve() in self.library_files
            or any(Path(value or os.getcwd()).resolve().is_relative_to(root) for root in self.library_roots))]
        os.open = self.guarded_open
        sys.addaudithook(self.audit)
        subprocess.check_output = self.metadata_output
        socket.socket.connect = self.no_network
        socket.socket.connect_ex = self.no_network
        socket.create_connection = self.no_network
        socket.getaddrinfo = self.no_network
        socket.gethostbyname = self.no_network
        socket.gethostbyname_ex = self.no_network
        import requests
        requests.sessions.Session.send = self.no_network
        requests.adapters.HTTPAdapter.send = self.no_network

    def self_check(self):
        import requests
        prepared = requests.Request('GET', 'https://example.invalid/').prepare()
        probes = (
            lambda: socket.create_connection(('127.0.0.1', 0)),
            lambda: socket.getaddrinfo('example.invalid', 443),
            lambda: requests.Session().send(prepared),
            lambda: requests.adapters.HTTPAdapter().send(prepared),
            lambda: sys.audit('open', str(self.repo / '.env.pices-ci-probe'), 'r', 0),
            lambda: sys.audit('open', str(self.repo / 'pices-ci-probe'), 'w', os.O_WRONLY),
            lambda: sys.audit('subprocess.Popen', 'unused', [], None, None),
        )
        for probe in probes:
            try:
                probe()
            except GuardViolation:
                continue
            raise AssertionError('Offline CI guard self-check failed')
        if sum(self.counts['bootstrap'].values()) != len(probes):
            raise AssertionError('Offline CI guard self-check accounting failed')
        self.phase = 'tests'


def source_bindings(repo):
    roots = ('scripts', 'tests', 'contracts', 'ci', '.github/workflows')
    paths = sorted(path for root in roots for path in (repo / root).rglob('*')
                   if path.is_file() and '__pycache__' not in path.parts)
    return {str(path.relative_to(repo)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def main():
    # Only this public commit identifier is retained from CI's environment.
    commit = os.environ.get('PICES_EXPECTED_COMMIT', '')
    os.environ.clear()
    if commit and not re.fullmatch('[0-9a-f]{40}', commit):
        raise AssertionError('Invalid public CI commit identifier')
    revision = checkout_revision(REPO)
    if commit and commit != revision:
        raise AssertionError('CI checkout does not match the expected head')
    modules = sys.argv[1:]
    if any(not re.fullmatch(r'tests\.test_[a-z0-9_]+', name) for name in modules):
        raise AssertionError('Only repository contract modules may be selected')
    sys.dont_write_bytecode = True
    with tempfile.TemporaryDirectory(prefix='pices-offline-') as fixture_root:
        os.environ.update(clean_environment(fixture_root))
        tempfile.tempdir = fixture_root
        sys.path.insert(0, str(REPO))
        guard = OfflineGuard(REPO, fixture_root, revision)
        guard.install()
        guard.self_check()
        import scripts.logger
        scripts.logger.get_logger = lambda *args, **kwargs: Mock()
        before = source_bindings(REPO)
        started = time.monotonic()
        suite = (unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in modules)
                 if modules else unittest.defaultTestLoader.discover(str(REPO / 'tests'), 'test_*.py', str(REPO)))
        if not suite.countTestCases():
            raise AssertionError('Offline CI discovered no contracts')
        print('TEST_COUNT', suite.countTestCases(), flush=True)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        unchanged = before == source_bindings(REPO)
        successful = result.wasSuccessful() and unchanged and not any(guard.counts['tests'].values())
        print('PICES_OFFLINE_CI_RESULT', json.dumps({
            'commit': revision, 'selected_modules': modules or ['all'],
            'tests_run': result.testsRun, 'successful': successful,
            'failures': len(result.failures), 'errors': len(result.errors),
            'seconds': round(time.monotonic() - started, 3), 'source_bindings_unchanged': unchanged,
            'guard_blocks': guard.counts, 'environment_cleared_dummy_credentials_only': True,
            'in_process_read_only_git_queries': guard.metadata_queries,
            'unexpected_guard_call_sites': guard.blocked_call_sites,
            'source_tree_sha256': hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
        }, sort_keys=True), flush=True)
        return 0 if successful else 1


if __name__ == '__main__':
    raise SystemExit(main())
