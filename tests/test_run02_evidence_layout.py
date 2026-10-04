"""Full private evidence lineage beneath a shared755workspace; no live requests."""

import os
import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import modern_owned_continuation as owned
from scripts import modern_run02_subjects_repair as repair
from scripts import modern_synthetic_canary as modern
from tests import test_modern_synthetic_canary as fixture


class EvidenceLayoutTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ModernCanaryTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.base = Path(self.case.temp.name)
        self.workspace = self.base / 'workspace'
        self.workspace.mkdir(mode=0o755)
        self.workspace.chmod(0o755)  # Fixture only: reproduce the real immutable shared ancestor.
        self.original = self.workspace / modern.NAMESPACE
        self.case.stage.rename(self.original)
        self.case.stage = self.original
        self.case.grant['binding'] = modern.binding(self.original)
        modern.atomic(self.original / 'binding.json', self.case.grant['binding'])
        modern.atomic(self.original / 'approval.json', self.case.grant)
        state = modern.load(self.original / 'state.json')
        state['binding'] = self.case.grant['binding']
        modern.save(self.original, state)
        self.case.remote['metadata'] = {}
        self.case.remote['access']['files'] = 'public'
        with self.assertRaises(modern.Held):
            modern.Controller(self.original, fixture.TOKEN,
                              lambda *a, **k: fixture.Response(self.case.remote, 201), lambda: self.case.clock).run()
        state = modern.load(self.original / 'state.json')
        state['attempt_diagnostics'][0].update(send_call_started=True, adapter_entered=True)
        modern.save(self.original, state)
        read196 = self.workspace / 'read196'
        read196.mkdir(mode=0o700)
        image196, diagnostics196 = read196 / 'canonical.json', read196 / 'diagnostics.json'
        modern.atomic(image196, self.case.remote)
        modern.atomic(diagnostics196, {'status': 200, 'get_intents': 1, 'identity_matches': True})
        for module, name, value in [
            (owned, 'ORIGINAL_RUNTIME', modern.runtime_binding()),
            (owned, 'CREATE_RESPONSE_SHA', state['responses'][0]['body_sha256']),
            (owned, 'BEFOREIMAGE_SHA', modern.sha(image196.read_bytes())),
            (owned, 'DIAGNOSTICS_SHA', modern.sha(diagnostics196.read_bytes())),
        ]:
            mocked = patch.object(module, name, value)
            mocked.start()
            self.addCleanup(mocked.stop)
        outside = self.base / 'continuations'
        outside.mkdir(mode=0o700)
        self.prior = outside / owned.NAMESPACE
        owned.stage_packet(self.prior, self.original, image196, diagnostics196,
                           fixture.TOKEN, preserved_root=self.workspace)
        self.case.clock += timedelta(minutes=35)
        grant = {'schema_version': 1, 'approved': True, 'approval_reference': 'OFFLINE OLD CONTINUATION',
                 'executor': modern.EXECUTOR, 'binding': owned.binding(self.prior), 'limits': modern.LIMITS,
                 'started_at': self.case.clock.isoformat(),
                 'valid_until': (self.case.clock + timedelta(minutes=30)).isoformat(),
                 'owner': fixture.OWNER, 'known_ids': self.case.grant['known_ids'],
                 'window_mode': 'specifically_authorized_continuation_window',
                 'original_valid_until': self.case.grant['valid_until'], 'existing_candidate_only': True,
                 'no_create_or_reset': True, 'additional_get_limit': 6,
                 'preserved_file_inventory': {'count': 305, 'sha256': 'a' * 64}}
        modern.atomic(self.prior / 'approval.json', grant)
        with self.assertRaises(modern.Held):
            owned.Controller(self.prior, fixture.TOKEN,
                             lambda *a, **k: fixture.Response(self.case.remote), lambda: self.case.clock).run()
        read197 = self.base / 'read197'
        read197.mkdir(mode=0o700)
        self.latest = read197 / 'canonical.json'
        modern.atomic(self.latest, self.case.remote)
        modern.atomic(read197 / 'diagnostics.json', {'historical_get_intents': 197, 'status': 200})
        for name, value in [('BEFOREIMAGE_SHA', modern.sha(self.latest.read_bytes())),
                            ('PRIOR_RUNTIME', owned.runtime_binding())]:
            mocked = patch.object(repair, name, value)
            mocked.start()
            self.addCleanup(mocked.stop)
        history = self.workspace / 'history'
        history.mkdir(mode=0o700)
        self.roots = [self.original, self.prior, read196, read197, history]
        actual = [p for root in self.roots for p in root.rglob('*') if p.is_file()]
        for index in range(353 - len(actual)):
            modern.atomic(history / f'receipt-{index:03d}.json', {'fixture_receipt': index})
        actual = [p for root in self.roots for p in root.rglob('*') if p.is_file()]
        self.assertEqual(len(actual), 353)
        self.declared = {'schema_version': 1, 'files_sha256': {str(p): modern.sha(p.read_bytes()) for p in actual}}
        self.manifest = self.base / 'preserved353.json'
        modern.atomic(self.manifest, self.declared)
        self.unrelated = self.workspace / 'ordinary-repository-file.txt'
        self.unrelated.write_text('Unrelated public repository file; must never be inventoried.')
        self.unrelated.chmod(0o644)
        self.stage = self.base / repair.NAMESPACE
        self.old = {str(p): (p.read_bytes(), p.stat().st_mode) for p in actual}
        self.old_origin = (self.prior / 'origin.json').read_bytes()

    def stage_repair(self, roots=True):
        return repair.stage_packet(self.stage, self.prior, self.latest,
                                   self.roots if roots else [], fixture.TOKEN, self.manifest)

    def grant(self):
        origin = modern.load(self.stage / 'origin.json')
        value = {'schema_version': 1, 'approved': True, 'approval_reference': 'OFFLINE353 FULL REPAIR',
                 'executor': modern.EXECUTOR, 'binding': repair.binding(self.stage), 'limits': repair.LIMITS,
                 'started_at': self.case.clock.isoformat(),
                 'valid_until': (self.case.clock + timedelta(minutes=10)).isoformat(),
                 'owner': fixture.OWNER, 'known_ids': self.case.grant['known_ids'],
                 'existing_candidate_only': True, 'no_create_or_reset': True, 'controlled_schema_repair': True,
                 'historical_get_intents': 197, 'preserved_file_inventory': repair.inventory_summary(origin['inventory'])}
        modern.atomic(self.stage / 'approval.json', value)

    def assert_old_unchanged(self):
        self.assertEqual(self.old, {p: (Path(p).read_bytes(), Path(p).stat().st_mode) for p in self.old})
        self.assertEqual((self.prior / 'origin.json').read_bytes(), self.old_origin)
        self.assertEqual(modern.load(self.prior / 'origin.json')['preserved_root'], str(self.workspace))
        self.assertEqual(self.workspace.stat().st_mode & 0o777, 0o755)

    def test_stage_read_only_preflight_then_full_execute_through_prepared_send(self):
        staged = self.stage_repair()
        self.assertEqual(staged['preserved_file_inventory']['count'], 354)
        before = {p.name: p.read_bytes() for p in self.stage.iterdir()}
        result = repair.preflight(self.stage, fixture.TOKEN)
        self.assertTrue(result['preflight_complete'])
        self.assertEqual(result['provider_requests'], 0)
        self.assertEqual(result['declared_manifest_files'], 353)
        self.assertEqual(result['prepared_put_sha256'], repair.PREPARED_PUT_SHA)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.stage.iterdir()})
        self.assertFalse((self.stage / 'approval.json').exists())
        unapproved = repair.Controller.__new__(repair.Controller)
        unapproved.initialize_inputs(self.stage, fixture.TOKEN, None)
        with self.assertRaises(modern.Held):
            unapproved.run()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.stage.iterdir()})
        self.grant()
        calls = []

        def send(session, prepared, **options):
            self.assertEqual(prepared.url, modern.ORIGIN + '/api/records/101/draft')
            self.assertEqual(prepared.headers['Authorization'], 'Bearer ' + fixture.TOKEN)
            self.assertFalse(options['allow_redirects'])
            self.assertTrue(options['verify'])
            state = modern.load(self.stage / 'state.json')
            self.assertEqual(state['counts'][state['pending']['kind']], 1)
            self.assertTrue(state['prepared_put_verified'])
            calls.append(prepared.method)
            if prepared.method == 'PUT':
                self.assertEqual(modern.sha(prepared.body), repair.PREPARED_PUT_SHA)
                body = modern.modern_wire_payload(modern.load(self.stage / 'metadata-put.json'))
                self.case.remote['metadata'], self.case.remote['access'] = body['metadata'], body['access']
            return fixture.Response(self.case.remote)

        with (patch.object(modern, 'datetime') as clock, patch.object(repair, 'datetime') as repair_clock,
              patch('requests.sessions.Session.send', send),
              patch('requests.adapters.HTTPAdapter.send', side_effect=AssertionError('Live adapter forbidden')) as adapter):
            clock.now.return_value = repair_clock.now.return_value = self.case.clock
            clock.fromisoformat.side_effect = datetime.fromisoformat
            receipt = modern._execute_controller(self.stage, fixture.TOKEN, repair.Controller)
        adapter.assert_not_called()
        self.assertEqual(calls, ['PUT', 'GET'])
        self.assertTrue(receipt['completed'])
        self.assertEqual(receipt['historical_get_intents'], 198)
        self.assertEqual(receipt['run02_metadata_put_intents'], 2)
        self.assertEqual(receipt['run02_create_intents'], 1)
        self.assert_old_unchanged()

    def test_sparse_manifest_supports_shared_ancestor_without_reading_public_siblings(self):
        original_read = Path.read_bytes

        def read(path):
            self.assertNotEqual(path, self.unrelated)
            return original_read(path)

        with patch.object(Path, 'read_bytes', read):
            self.stage_repair(roots=False)
            self.assertTrue(repair.preflight(self.stage, fixture.TOKEN)['preflight_complete'])
        self.assert_old_unchanged()

    def test_incomplete_or_invalid_manifest_and_stage_overlap_fail_before_mkdir(self):
        missing = deepcopy(self.declared)
        missing['files_sha256'].pop(str(self.prior / 'state.json'))
        wrong = deepcopy(self.declared)
        wrong['files_sha256'][str(self.latest)] = '0' * 64
        invalid = deepcopy(self.declared)
        invalid['files_sha256'][str(self.latest)] = 'not-a-sha'
        for value in (missing, wrong, invalid):
            modern.atomic(self.manifest, value)
            with self.assertRaises(modern.Held):
                self.stage_repair(roots=False)
            self.assertFalse(self.stage.exists())
        modern.atomic(self.manifest, self.declared)
        with self.assertRaises(modern.Held):
            repair.stage_packet(self.original / repair.NAMESPACE, self.prior, self.latest,
                                self.roots, fixture.TOKEN, self.manifest)
        self.assertFalse((self.original / repair.NAMESPACE).exists())
        # Sparse leaf roots must not permit mkdir inside either immutable stage.
        for protected in (self.original, self.prior):
            candidate = protected / repair.NAMESPACE
            with self.assertRaises(modern.Held):
                repair.stage_packet(candidate, self.prior, self.latest, [], fixture.TOKEN, self.manifest)
            self.assertFalse(candidate.exists())
        self.assert_old_unchanged()

    def test_public_leaf_writable_directory_symlinks_and_hardlinks_are_rejected(self):
        self.latest.chmod(0o644)
        with self.assertRaises(modern.Held):
            self.stage_repair()
        self.latest.chmod(0o600)
        self.latest.parent.chmod(0o777)
        with self.assertRaises(modern.Held):
            self.stage_repair()
        self.latest.parent.chmod(0o700)
        extra = self.latest.parent / 'linked.json'
        os.link(self.latest, extra)
        with self.assertRaises(modern.Held):
            self.stage_repair()
        extra.unlink()
        extra.symlink_to(self.latest)
        with self.assertRaises(modern.Held):
            self.stage_repair()
        extra.unlink()
        linked_parent = self.base / 'linked-workspace'
        linked_parent.symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaises(modern.Held):
            repair.inventory([linked_parent / 'history'], self.stage, self.declared)
        self.assertFalse(self.stage.exists())
        self.assert_old_unchanged()

    def test_subtree_addition_and_declared_leaf_changes_hold_read_only_preflight(self):
        self.stage_repair()
        before = {p.name: p.read_bytes() for p in self.stage.iterdir()}
        extra = self.roots[-1] / 'unexpected.json'
        modern.atomic(extra, {'new': True})
        with self.assertRaises(modern.Held):
            repair.preflight(self.stage, fixture.TOKEN)
        extra.unlink()
        self.latest.chmod(0o644)
        with self.assertRaises(modern.Held):
            repair.preflight(self.stage, fixture.TOKEN)
        self.latest.chmod(0o600)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.stage.iterdir()})
        self.assert_old_unchanged()


if __name__ == '__main__':
    unittest.main()
