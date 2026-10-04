"""Same-draft repair lineage, exact prepared body and permanently spent intents."""

import json
import os
import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import requests

from scripts import modern_owned_continuation as owned
from scripts import modern_run02_subjects_repair as repair
from scripts import modern_synthetic_canary as modern
from tests import test_modern_owned_continuation as previous
from tests import test_modern_synthetic_canary as fixture


class SubjectsRepairTests(unittest.TestCase):
    def setUp(self):
        self.case = previous.OwnedContinuationTests('test_complete_recovery_then_read_only_retry_keeps_all_lifetime_counts')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        with self.assertRaises(modern.Held):
            owned.Controller(self.case.stage, fixture.TOKEN,
                             lambda *a, **k: fixture.Response(self.case.remote), lambda: self.case.clock).run()
        self.prior = self.case.stage
        evidence = Path(self.case.temp.name) / 'latest-read197'
        evidence.mkdir(mode=0o700)
        self.latest = evidence / 'canonical.json'
        modern.atomic(self.latest, self.case.remote)
        for name, value in [('BEFOREIMAGE_SHA', modern.sha(self.latest.read_bytes())),
                            ('PRIOR_RUNTIME', owned.runtime_binding()), ('MIN_PRESERVED_FILES', 1)]:
            p = patch.object(repair, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.stage = Path(self.case.temp.name) / repair.NAMESPACE
        self.roots = [self.case.original_stage, self.prior, evidence]
        self.manifest = evidence / 'preserved.json'
        modern.atomic(self.manifest, {'schema_version': 1, 'files_sha256': {
            str(path): modern.sha(path.read_bytes())
            for root in self.roots for path in root.rglob('*') if path.is_file()}})
        self.snapshot = repair.inventory(self.roots, self.stage)
        repair.stage_packet(self.stage, self.prior, self.latest, self.roots, fixture.TOKEN, self.manifest)
        self.grant = {'schema_version': 1, 'approved': True, 'approval_reference': 'OFFLINE CONTROLLED REPAIR FIXTURE',
                      'executor': modern.EXECUTOR, 'binding': repair.binding(self.stage), 'limits': repair.LIMITS,
                      'started_at': self.case.clock.isoformat(),
                      'valid_until': (self.case.clock + timedelta(minutes=10)).isoformat(),
                      'owner': fixture.OWNER, 'known_ids': self.case.original_grant['known_ids'],
                      'existing_candidate_only': True, 'no_create_or_reset': True, 'controlled_schema_repair': True,
                      'historical_get_intents': 197, 'preserved_file_inventory': repair.inventory_summary(self.snapshot)}
        modern.atomic(self.stage / 'approval.json', self.grant)
        self.calls = []
        self.fault = None

    def controller(self):
        self.active = repair.Controller(self.stage, fixture.TOKEN, self.transport, lambda: self.case.clock)
        return self.active

    def transport(self, method, url, body, headers, **options):
        state = modern.load(self.stage / 'state.json')
        self.assertEqual(state['counts'][state['pending']['kind']], 1)
        self.assertEqual(modern.load(self.stage / 'journal.json')['state_sha256'], modern.sha((self.stage / 'state.json').read_bytes()))
        self.assertEqual(repair.inventory(self.roots, self.stage), self.snapshot)
        self.assertFalse(options['allow_redirects'])
        self.assertEqual(url, modern.ORIGIN + '/api/records/101/draft')
        with requests.Session() as session:
            prepared = session.prepare_request(requests.Request(method, url, headers=headers, json=body))
        self.active.check_prepared(prepared)
        self.calls.append(method)
        if self.fault == 'uncertain':
            raise RuntimeError('PRIVATE ' + fixture.TOKEN)
        if self.fault == 'redirect':
            return fixture.Response({}, 301, {'Location': 'https://evil.invalid/' + fixture.TOKEN})
        data = deepcopy(self.case.remote)
        if method == 'PUT':
            self.assertEqual(modern.sha(prepared.body), repair.PREPARED_PUT_SHA)
            data['metadata'], data['access'] = deepcopy(body['metadata']), deepcopy(body['access'])
            self.case.remote = deepcopy(data)
        if self.fault == 'errors':
            return fixture.Response({'errors': [{'field': 'metadata.subjects', 'messages': ['private-message']}]}, 400)
        if self.fault == 'owner':
            data['parent']['access']['owned_by']['user'] = '999'
        if self.fault == 'access':
            data['access']['files'] = 'public'
        if self.fault == 'doi':
            data['pids'] = {'doi': {'provider': 'datacite', 'identifier': '10.5072/zenodo.101'}}
        if self.fault == 'credential':
            data['metadata']['description'] = fixture.TOKEN
        if self.fault == 'readback' and method == 'GET':
            data['metadata']['subjects'] = [{'subject': 'wrong-run'}]
        return fixture.Response(data)

    def test_exact_two_action_repair_preserves_history_and_cannot_reenter(self):
        receipt = self.controller().run()
        self.assertEqual(self.calls, ['PUT', 'GET'])
        self.assertTrue(receipt['completed'])
        self.assertEqual(receipt['counts'], {'metadata': 1, 'get': 1})
        self.assertEqual(receipt['historical_get_intents'], 198)
        self.assertEqual(receipt['run02_metadata_put_intents'], 2)
        self.assertEqual(receipt['run02_create_intents'], 1)
        self.assertTrue(receipt['prepared_put_verified'])
        self.assertEqual(repair.inventory(self.roots, self.stage), self.snapshot)
        with self.assertRaises(modern.Held):
            self.controller()
        self.assertEqual(self.calls, ['PUT', 'GET'])
        self.assertNotIn(fixture.TOKEN, json.dumps(receipt))

    def test_failed_put_has_no_readback_and_permanently_spends_only_its_new_intent(self):
        for fault in ('uncertain', 'redirect', 'errors', 'owner', 'access', 'doi', 'credential'):
            with self.subTest(fault=fault):
                if self.calls:
                    self.doCleanups()
                    self.setUp()
                self.fault = fault
                with self.assertRaises(modern.Held):
                    self.controller().run()
                state = modern.load(self.stage / 'state.json')
                self.assertEqual(self.calls, ['PUT'])
                self.assertEqual(state['counts'], {'metadata': 1, 'get': 0})
                self.assertTrue(state['failed'])
                self.assertNotIn(fixture.TOKEN, json.dumps(state))
                self.assertNotIn('private-message', json.dumps(state))
                if fault == 'errors':
                    self.assertTrue(state['responses'][0]['validation_errors']['metadata_subjects_error_present'])
                with self.assertRaises(modern.Held):
                    self.controller()
                self.assertEqual(repair.inventory(self.roots, self.stage), self.snapshot)

    def test_readback_failure_never_replenishes_or_replays_either_action(self):
        self.fault = 'readback'
        with self.assertRaises(modern.Held):
            self.controller().run()
        self.assertEqual(self.calls, ['PUT', 'GET'])
        self.assertEqual(modern.load(self.stage / 'state.json')['counts'], repair.LIMITS)
        with self.assertRaises(modern.Held):
            self.controller()

    def test_window_expiry_lineage_inventory_and_grant_tampering_stop_before_transport(self):
        self.case.clock += timedelta(minutes=10)
        with self.assertRaises(modern.Held):
            self.controller()
        self.case.clock -= timedelta(minutes=10)
        original = self.latest.read_bytes()
        self.latest.write_bytes(original + b' ')
        with self.assertRaises(modern.Held):
            self.controller()
        self.latest.write_bytes(original)
        grant = deepcopy(self.grant)
        grant['valid_until'] = (self.case.clock + timedelta(minutes=11)).isoformat()
        modern.atomic(self.stage / 'approval.json', grant)
        with self.assertRaises(modern.Held):
            self.controller()
        self.assertEqual(self.calls, [])

    def test_only_corrected_prepared_put_and_canonical_get_routes_are_allowed(self):
        controller = self.controller()
        for kind, method, path in [('create', 'POST', '/api/records'), ('get', 'GET', controller.base()),
                                   ('metadata', 'PUT', controller.base() + '/'), ('init', 'POST', controller.base() + '/files')]:
            with self.assertRaises(modern.Held):
                controller.request(kind, method, path, 200)
        self.assertEqual(modern.load(self.stage / 'state.json')['counts'], {'metadata': 0, 'get': 0})
        prepared = requests.Request('PUT', modern.ORIGIN + controller.base(), json=controller.updated,
                                    headers={'Authorization': 'Bearer ' + fixture.TOKEN, 'Accept': modern.ACCEPT}).prepare()
        controller.state['pending'] = {'kind': 'metadata'}
        prepared.body += b' '
        with self.assertRaises(modern.Held):
            controller.check_prepared(prepared)
        self.assertFalse(controller.state['prepared_put_verified'])

    def test_shared_execute_checks_real_prepared_body_with_no_adapter_dispatch(self):
        def send(session, prepared, **options):
            self.active = modern.load(self.stage / 'state.json')
            self.assertTrue(self.active['prepared_put_verified'])
            raise RuntimeError('LOCAL STOP ' + fixture.TOKEN)
        with (patch.object(modern, 'datetime') as clock, patch.object(repair, 'datetime') as repair_clock,
              patch('requests.sessions.Session.send', send),
              patch('requests.adapters.HTTPAdapter.send', side_effect=AssertionError('adapter called')) as adapter):
            clock.now.return_value = repair_clock.now.return_value = self.case.clock
            clock.fromisoformat.side_effect = datetime.fromisoformat
            with self.assertRaises(modern.Held):
                modern._execute_controller(self.stage, fixture.TOKEN, repair.Controller)
        adapter.assert_not_called()
        state = modern.load(self.stage / 'state.json')
        self.assertEqual(state['counts'], {'metadata': 1, 'get': 0})
        self.assertTrue(state['failed'])
        self.assertEqual(repair.inventory(self.roots, self.stage), self.snapshot)

    def test_staging_rejects_preserved_tree_overlap_symlink_and_hardlink_without_creation(self):
        candidate = self.roots[0] / repair.NAMESPACE
        with self.assertRaises(modern.Held):
            repair.stage_packet(candidate, self.prior, self.latest, self.roots, fixture.TOKEN, self.manifest)
        self.assertFalse(candidate.exists())
        linked = self.latest.parent / 'hardlinked.json'
        os.link(self.latest, linked)
        candidate = self.stage.with_name('second') / repair.NAMESPACE
        with self.assertRaises(modern.Held):
            repair.stage_packet(candidate, self.prior, self.latest, self.roots, fixture.TOKEN, self.manifest)
        self.assertFalse(candidate.exists())
        linked.unlink()
        linked.symlink_to(self.latest)
        with self.assertRaises(modern.Held):
            repair.stage_packet(candidate, self.prior, self.latest, self.roots, fixture.TOKEN, self.manifest)
        self.assertFalse(candidate.exists())


if __name__ == '__main__':
    unittest.main()
