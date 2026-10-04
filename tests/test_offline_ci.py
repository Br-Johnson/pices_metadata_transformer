"""Guard policy contracts use isolated dummy guard instances, never real I/O."""

import os
import tempfile
import unittest
from pathlib import Path

from ci.run_offline_tests import (
    DUMMY_TOKEN,
    TOKEN_KEYS,
    GuardViolation,
    OfflineGuard,
    checkout_revision,
    clean_environment,
)


class OfflineCITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / 'checkout'
        self.repo.mkdir()
        self.fixtures = root / 'fixtures'
        self.fixtures.mkdir()
        self.guard = OfflineGuard(self.repo, self.fixtures)
        self.guard.phase = 'tests'

    def test_all_transport_and_process_events_are_rejected_without_launching_anything(self):
        for event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto',
                      'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.fork'):
            with self.assertRaises(GuardViolation):
                self.guard.audit(event, ())
        with self.assertRaises(GuardViolation):
            self.guard.no_network('dummy request value never included in error')
        self.assertEqual(self.guard.counts['bootstrap']['network'], 0)

    def test_real_private_paths_reject_and_dummy_private_fixture_paths_remain_usable(self):
        for path in (self.repo / 'secrets.txt', self.repo / '.env.sandbox',
                     self.repo / '.git/config',
                     self.repo / 'logs/evidence.json', self.repo.parent / 'private/evidence.json',
                     self.repo.parent / '.aws/config', self.repo.parent / '.netrc'):
            with self.assertRaises(GuardViolation):
                self.guard.audit('open', (str(path), 'r', 0))
        self.guard.audit('open', (str(self.fixtures / '.env.sandbox'), 'w', os.O_WRONLY))
        self.guard.audit('open', (str(self.repo / 'scripts/module.py'), 'r', 0))

    def test_writes_require_dummy_root_and_all_repo_mutation_routes_reject(self):
        self.guard.audit('open', (str(self.fixtures / 'output.json'), 'w', os.O_CREAT))
        for event, args in (
            ('open', (str(self.repo / 'new.py'), 'w', os.O_WRONLY)),
            ('open', (str(self.repo.parent / 'outside.json'), 'w', os.O_CREAT)),
            ('os.mkdir', (str(self.repo / 'new'), 0o700, -1)),
            ('os.remove', (str(self.repo / 'old'), -1)),
            ('os.rename', (str(self.fixtures / 'old'), str(self.repo / 'new'), -1, -1)),
            ('os.link', (str(self.repo / 'old'), str(self.fixtures / 'new'), -1, -1)),
            ('os.symlink', ('uninspected-target', str(self.repo / 'link'), -1)),
            ('os.chmod', (str(self.repo / 'old'), 0o600, -1)),
            ('os.truncate', (str(self.repo / 'old'), 0)),
            ('os.utime', (str(self.repo / 'old'), None, None, -1)),
            ('os.chown', (str(self.repo / 'old'), 0, 0, -1)),
        ):
            with self.assertRaises(GuardViolation):
                self.guard.audit(event, args)

    def test_descriptor_relative_mutations_resolve_both_source_and_destination(self):
        fd = os.open(self.repo, os.O_RDONLY)
        self.addCleanup(os.close, fd)
        for event, args in (
            ('os.remove', ('relative.py', fd)),
            ('os.rename', (str(self.fixtures / 'old'), 'relative.py', -1, fd)),
            ('os.symlink', ('unused-target', 'relative.py', fd)),
            ('os.utime', ('relative.py', None, None, fd)),
            ('os.chown', ('relative.py', 0, 0, fd)),
        ):
            with self.assertRaises(GuardViolation):
                self.guard.audit(event, args)
        self.assertEqual(self.guard.absolute_path('relative.py', fd), self.repo / 'relative.py')

    def test_symlinked_reads_and_writes_cannot_escape_dummy_fixture_exemption(self):
        target = self.repo / 'secrets.txt'
        link = self.fixtures / 'link'
        link.symlink_to(target)
        with self.assertRaises(GuardViolation):
            self.guard.audit('open', (str(link), 'r', 0))
        with self.assertRaises(GuardViolation):
            self.guard.audit('open', (str(link), 'w', os.O_WRONLY))
        # Unlink operates on the link itself, without following its target.
        self.guard.audit('os.remove', (str(link), -1))

    def test_sanitized_environment_contains_only_dummy_tokens_and_no_parent_settings(self):
        value = clean_environment(self.fixtures)
        self.assertEqual(set(value), {'PATH', 'TMPDIR', 'PYTHONDONTWRITEBYTECODE', *TOKEN_KEYS})
        self.assertTrue(all(value[key] == DUMMY_TOKEN for key in TOKEN_KEYS))
        self.assertEqual(value['TMPDIR'], str(self.fixtures))

    def test_arbitrary_outside_stage_names_and_directory_reads_are_rejected(self):
        outside = self.repo.parent / 'pices-sandbox-run-unknown'
        for event, args in (('open', (str(outside / 'beforeimage.json'), 'r', 0)),
                            ('os.scandir', (str(outside),)), ('os.listdir', (str(outside),))):
            with self.assertRaises(GuardViolation):
                self.guard.audit(event, args)

    def test_only_exact_checkout_revision_query_is_served_without_a_process(self):
        self.guard.revision = 'a' * 40
        self.assertEqual(self.guard.metadata_output(['git', 'rev-parse', 'HEAD'],
                                                   cwd=self.repo, text=True), 'a' * 40 + '\n')
        self.assertEqual(self.guard.metadata_queries, 1)
        for command, kwargs in ((['git', 'config', '--list'], {'cwd': self.repo, 'text': True}),
                                (['git', 'rev-parse', 'HEAD'], {'cwd': self.repo, 'text': True, 'shell': True}),
                                (['git', 'rev-parse', 'HEAD'], {'cwd': self.fixtures, 'text': True})):
            with self.assertRaises(GuardViolation):
                self.guard.metadata_output(command, **kwargs)

    def test_checkout_metadata_supports_detached_symbolic_packed_and_rejects_traversal(self):
        gitdir = self.repo / '.git'
        gitdir.mkdir()
        head = gitdir / 'HEAD'
        head.write_text('b' * 40 + '\n')
        self.assertEqual(checkout_revision(self.repo), 'b' * 40)
        head.write_text('ref: refs/heads/main\n')
        (gitdir / 'packed-refs').write_text('c' * 40 + ' refs/heads/main\n')
        self.assertEqual(checkout_revision(self.repo), 'c' * 40)
        (gitdir / 'refs/heads').mkdir(parents=True)
        (gitdir / 'refs/heads/main').write_text('d' * 40 + '\n')
        self.assertEqual(checkout_revision(self.repo), 'd' * 40)
        head.write_text('ref: refs/heads/../../config\n')
        with self.assertRaises(AssertionError):
            checkout_revision(self.repo)


if __name__ == '__main__':
    unittest.main()
