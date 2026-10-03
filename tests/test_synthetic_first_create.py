"""Sealed first-create transactions with dummy transport; no provider access."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import test_synthetic_canary_controller as base
import test_synthetic_canary_recovery as recovery
from test_synthetic_canary_controller import OWNER, response

from scripts import synthetic_canary_controller as c
from scripts import synthetic_first_create as f
from scripts.upload_service import atomic_json, read_json, require_inventory


class FirstCreateTransactionTests(unittest.TestCase):
    def setUp(self):
        self.obj = base.SyntheticControllerTests('test_complete_create_readback_retry_and_process_rerun')
        self.obj.setUp(); self.addCleanup(self.obj.doCleanups)
        self.paths = c.FirstCreatePaths(str(self.obj.stage), 'sandbox')
        self.folder = self.obj.stage / 'state/sandbox'
        self.evidence = {'sealed':'offline dummy receipts', 'prior_gets':185}
        self.ids = list(range(1000, 11000))
        atomic_json(self.folder / c.RECOVERY_STATE, {'ids':self.ids})
        self.evidence_patch = patch.object(f, 'evidence_binding', return_value=(self.evidence, self.ids))
        self.evidence_patch.start(); self.addCleanup(self.evidence_patch.stop)
        self.obj.remote['created'] = datetime.now(timezone.utc).isoformat()
        self.before = {p:p.read_bytes() for p in (Path(self.obj.paths.safe_to_upload_path),
                                                 Path(self.obj.paths.already_uploaded_path))}

    def execute(self):
        with patch('requests.sessions.Session.send', self.obj.transport), patch('scripts.zenodo_api.ZenodoAPIClient._rate_limit_check'):
            return c.execute(self.obj.stage, OWNER, first_create=True)

    def test_create_readback_retry_counts_clock_and_historical_cache_preserved(self):
        now = datetime.now(timezone.utc); result = self.execute()
        self.assertTrue(result['completed'], result)
        self.assertEqual(result['counts'], {'get':8,'create':1,'metadata':1,'file':1})
        self.assertEqual(result['cumulative_gets'], 193); self.assertFalse(result['inventory_complete'])
        grant = read_json(self.paths.safe_to_upload_path)
        self.assertGreaterEqual(datetime.fromisoformat(grant['started_at']), now)
        self.assertEqual(datetime.fromisoformat(grant['valid_until']) - datetime.fromisoformat(grant['started_at']), timedelta(minutes=30))
        self.assertFalse(grant['inventory_complete'])
        self.assertEqual({p:p.read_bytes() for p in self.before}, self.before)
        old = Path(self.paths.safe_to_upload_path).read_bytes(); calls = len(self.obj.calls)
        self.assertTrue(self.execute()['cached']); self.assertEqual(len(self.obj.calls), calls)
        self.assertEqual(Path(self.paths.safe_to_upload_path).read_bytes(), old)

    def test_generic_sandbox_production_and_actual_source_cannot_use_partial_grant(self):
        f.prepare_grant(self.paths, self.obj.metadata, OWNER)
        for environment in ('sandbox','production'):
            with self.subTest(environment=environment), self.assertRaises((ValueError,c.ZenodoAPIError)):
                require_inventory(read_json(self.paths.safe_to_upload_path), environment)
        self.assertEqual(self.obj.calls, [])

    def test_changed_persisted_partial_id_reject_set_blocks_before_transport(self):
        f.prepare_grant(self.paths,self.obj.metadata,OWNER)
        c.SyntheticTransport(base.TOKEN,OWNER,self.paths,self.obj.metadata,self.obj.artifact,self.obj.plan)
        p = self.folder/'synthetic-controller.json'; state = read_json(p)
        state['pre_ids'] = []; atomic_json(p,state)
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.obj.calls,[])

    def test_uncertain_create_never_recreates_even_if_ledger_lost(self):
        self.obj.mutation = 'uncertain'; result = self.execute()
        self.assertTrue(result['failed']); self.assertEqual(result['counts']['create'],1)
        self.assertNotIn(base.TOKEN,json.dumps(result)); calls = len(self.obj.calls)
        for lost in (False, True):
            if lost: Path(self.paths.uploads_registry_path).unlink()
            with self.subTest(lost=lost), self.assertRaises(c.ZenodoAPIError): self.execute()
            self.assertEqual(len(self.obj.calls), calls)

    def test_foreign_old_or_malformed_created_response_stops_before_put(self):
        for fault in ('known_id','missing','naive','old','future','files','metadata','empty_title_metadata','redirect','owner'):
            obj = FirstCreateTransactionTests('test_create_readback_retry_counts_clock_and_historical_cache_preserved')
            obj.setUp()
            try:
                if fault == 'known_id': obj.obj.remote['id'] = 1000
                elif fault == 'missing': obj.obj.remote.pop('created')
                elif fault == 'naive': obj.obj.remote['created'] = '2026-10-03T03:00:00'
                elif fault == 'old': obj.obj.remote['created'] = '2020-01-01T00:00:00+00:00'
                elif fault == 'future': obj.obj.remote['created'] = (datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
                elif fault == 'files': obj.obj.remote['files'] = [{'filename':'historical.xml'}]
                elif fault == 'metadata': obj.obj.remote['metadata']['title'] = 'Historical title'
                elif fault == 'empty_title_metadata': obj.obj.remote['metadata']['description'] = 'Historical content'
                else: obj.obj.mutation = fault
                with self.subTest(fault=fault):
                    result = obj.execute(); self.assertTrue(result['failed'],result)
                    self.assertFalse(any(method=='PUT' for method,_ in obj.obj.calls))
                    calls = len(obj.obj.calls)
                    with self.assertRaises(c.ZenodoAPIError): obj.execute()
                    self.assertEqual(len(obj.obj.calls),calls)
            finally: obj.doCleanups()

    def test_expiry_and_changed_evidence_stop_without_new_clock_or_requests(self):
        f.prepare_grant(self.paths,self.obj.metadata,OWNER)
        original = Path(self.paths.safe_to_upload_path).read_bytes()
        self.evidence['changed'] = True
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.obj.calls,[])
        self.assertEqual(Path(self.paths.safe_to_upload_path).read_bytes(),original)
        self.evidence.pop('changed')
        grant = read_json(self.paths.safe_to_upload_path)
        grant['started_at'] = '2020-01-01T00:00:00+00:00'; grant['valid_until'] = '2020-01-01T00:30:00+00:00'
        atomic_json(self.paths.safe_to_upload_path,grant)
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.obj.calls,[])

    def test_creation_timestamp_is_bound_to_current_post_not_earlier_grant_start(self):
        f.prepare_grant(self.paths,self.obj.metadata,OWNER)
        now = datetime.now(timezone.utc)
        grant = read_json(self.paths.safe_to_upload_path)
        grant.update(started_at=(now-timedelta(minutes=10)).isoformat(), valid_until=(now+timedelta(minutes=20)).isoformat())
        atomic_json(self.paths.safe_to_upload_path,grant)
        self.obj.remote['created'] = (now-timedelta(minutes=2)).isoformat()
        result = self.execute(); self.assertTrue(result['failed'])
        self.assertEqual(result['counts']['create'],1)
        self.assertFalse(any(method=='PUT' for method,_ in self.obj.calls))
        state = read_json(self.folder/'synthetic-controller.json')
        self.assertGreaterEqual(datetime.fromisoformat(state['create_started_at']),now)

    def test_creation_timestamp_cannot_change_on_following_id_readback(self):
        original = self.obj.transport
        def changed(session,request,**kwargs):
            if request.method=='GET' and request.path_url=='/api/deposit/depositions/101':
                self.obj.remote['created'] = datetime.now(timezone.utc).isoformat()
            return original(session,request,**kwargs)
        self.obj.transport = changed
        result = self.execute(); self.assertTrue(result['failed'])
        self.assertFalse(any(method=='PUT' for method,_ in self.obj.calls))

    def test_orphan_grant_and_prior_intent_cannot_start_first_create(self):
        atomic_json(self.paths.already_uploaded_path,{})
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.obj.calls,[])
        Path(self.paths.already_uploaded_path).unlink()
        atomic_json(self.paths.uploads_registry_path,{c.SOURCE:{'needs_reconciliation':True}})
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.obj.calls,[])


class FirstCreateEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.old = recovery.SyntheticRecoveryTests('test_complete_recovery_binds_evidence_then_original_write_readback_retry')
        self.old.setUp(); self.addCleanup(self.old.doCleanups)
        original = self.old.transport
        def failure(session,request,**kwargs):
            if 'page=101&' in request.path_url:
                self.old.calls.append(request.path_url)
                return response({'status':400},400)
            return original(session,request,**kwargs)
        self.old.transport = failure
        result = self.old.run_recovery()
        self.assertEqual((result['get_attempts'],result['verified_pages']),(102,100))
        atomic_json(self.old.folder / f.FAILURE_RECEIPT,result)
        pins = {}
        for name in f.PINNED_DIAGNOSTICS:
            p = self.old.folder.parents[2] / name; atomic_json(p,{'dummy_offline_receipt':name})
            pins[name] = c.sha(p.read_bytes())
        patches = [patch.object(f,'FAILED_STATE_SHA',c.sha((self.old.folder/c.RECOVERY_STATE).read_bytes())),
            patch.object(f,'FAILURE_RECEIPT_SHA',c.sha((self.old.folder/f.FAILURE_RECEIPT).read_bytes())),
            patch.object(f,'PINNED_DIAGNOSTICS',pins)]
        for item in patches: item.start(); self.addCleanup(item.stop)
        self.old.calls = []

    def binding(self):
        return f.evidence_binding(self.old.folder,self.old.obj.metadata,OWNER)

    def test_all_retained_history_and_diagnostics_bound_without_provider_reads(self):
        before = self.old.old_bytes(); evidence,ids = self.binding()
        self.assertEqual(len(ids),10000); self.assertEqual(evidence['prior_read_counts']['total'],185)
        self.assertEqual(len(evidence['retained_page_sha256']),100)
        self.assertEqual(self.old.old_bytes(),before); self.assertEqual(self.old.calls,[])

    def test_changed_failed_state_receipt_page_and_actual_diagnostic_are_rejected(self):
        files = [self.old.folder/c.RECOVERY_STATE,self.old.folder/f.FAILURE_RECEIPT,
                 self.old.folder/c.RECOVERY_PAGES/'page-100.json']
        files += [self.old.folder.parents[2]/name for name in f.PINNED_DIAGNOSTICS]
        for file in files:
            raw = file.read_bytes(); file.write_bytes(raw+b' ')
            with self.subTest(file=file.name), self.assertRaises(c.ZenodoAPIError): self.binding()
            self.assertEqual(file.read_bytes(),raw+b' '); file.write_bytes(raw)
        self.assertEqual(self.old.calls,[])

    def test_missing_or_unpinned_actual_receipts_fail_closed(self):
        with patch.object(f,'PINNED_DIAGNOSTICS',{'unbound.json':'invalid-digest'}), self.assertRaises(c.ZenodoAPIError):
            self.binding()
        p = self.old.folder.parents[2]/next(iter(f.PINNED_DIAGNOSTICS)); p.unlink()
        with self.assertRaises(FileNotFoundError): self.binding()
        self.assertEqual(self.old.calls,[])


if __name__ == '__main__': unittest.main()
