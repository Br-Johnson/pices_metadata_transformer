"""Offline recovery of the exact failed v2 canary; transport always mocked."""
from datetime import datetime, timezone, timedelta
import contextlib
import io
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests
from scripts import synthetic_canary_controller as c
from scripts.upload_service import atomic_json, read_json, require_inventory
import test_synthetic_canary_controller as base
from test_synthetic_canary_controller import OWNER, TOKEN, response

RECOVERY_STATE = 'synthetic-owned-recovery-controller.json'
RECOVERY_PAGES = 'synthetic-owned-recovery-pages'
FAILURE_RECEIPT = 'synthetic-owned-pages-failure-receipt.json'


class SyntheticRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.obj = base.SyntheticControllerTests('test_complete_create_readback_retry_and_process_rerun')
        self.obj.setUp(); self.addCleanup(self.obj.doCleanups)
        self.folder = self.obj.stage / 'state/sandbox'
        (self.folder / c.OWNED_STATE).unlink()
        self.obj.pagination_fixture(count=16538)
        original = self.obj.inventory_transport
        def historical(session, request, **kwargs):
            r = original(session, request, **kwargs)
            if 'page=63&' in request.path_url:
                data = json.loads(r.content)
                for item in data[-9:]: item['metadata'] = {}
                return response(data)
            return r
        self.obj.inventory_transport = historical
        compatible = c.check_owned_page
        def old_checker(records, metadata, owner, seen):
            c.require(all('title' in item.get('metadata', {}) for item in records), 'response_json')
            return compatible(records, metadata, owner, seen)
        with patch.object(c, 'check_owned_page', old_checker):
            failed = self.obj.run_inventory()
        self.assertEqual((failed['get_attempts'], failed['verified_pages']), (64, 62))
        atomic_json(self.folder / FAILURE_RECEIPT, failed)
        self.previous = self.old_bytes()
        self.calls = []; self.count = 16538; self.fault = None

    def old_bytes(self):
        files = [self.folder / c.OWNED_STATE, self.folder / FAILURE_RECEIPT]
        files += sorted((self.folder / 'synthetic-owned-pages').iterdir())
        return {str(p.relative_to(self.folder)): p.read_bytes() for p in files}

    def transport(self, session, request, **kwargs):
        self.calls.append(request.path_url)
        state = read_json(self.folder / RECOVERY_STATE)
        self.assertEqual(state['get_attempts'], self.durable_start + len(self.calls))
        self.assertEqual(request.method, 'GET')
        self.assertEqual(request.headers['Authorization'], 'Bearer ' + TOKEN)
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(urlsplit(request.url).path, '/api/deposit/depositions')
        params = parse_qs(urlsplit(request.url).query)
        if not params: return response([{'id':3, 'owner':OWNER}])
        self.assertEqual(set(params), {'page', 'size'}); self.assertEqual(params['size'], ['100'])
        page = int(params['page'][0])
        if self.fault == ('transport', page): raise requests.ConnectionError('private ' + TOKEN)
        if self.fault == ('redirect', page):
            r = response({}, 301); r.headers['Location'] = 'https://evil.test'; return r
        start = (page - 1) * 100
        data = [{'id':i+1000, 'owner':OWNER, 'metadata':{'title':'Historical title'}, 'files':[]}
                for i in range(start, min(start+100, self.count))]
        if page == 63:
            for item in data[-9:]: item['metadata'] = {}
        if self.fault == ('collision', page): data[-1]['metadata']['notes'] = c.SOURCE
        if self.fault == ('change', page): data[0]['metadata']['title'] = 'Changed retained page'
        if self.fault == ('echo', page):
            data[0]['metadata']['notes'] = TOKEN
            escaped = ''.join('\\u%04x' % ord(ch) for ch in TOKEN)
            raw = json.dumps(data).encode().replace(TOKEN.encode(), escaped.encode())
            self.assertNotIn(TOKEN.encode(), raw)
            return response(raw)
        return response(data)

    def run_recovery(self, resume=False):
        state = read_json(self.folder / RECOVERY_STATE, {})
        self.durable_start = state.get('get_attempts', 0); self.calls = []
        with patch('requests.sessions.Session.send', self.transport), patch('scripts.zenodo_api.ZenodoAPIClient._rate_limit_check'):
            return c.inventory(self.obj.stage, OWNER, resume=resume, recovery=True)

    def test_complete_recovery_binds_evidence_then_original_write_readback_retry(self):
        result = self.run_recovery()
        self.assertTrue(result['completed'], result)
        self.assertEqual((result['get_attempts'], result['prior_observed_gets'], result['cumulative_inventory_gets']), (167, 80, 247))
        self.assertEqual(result['maximum_cumulative_gets'], 305)
        self.assertEqual(result['inventory_scope'], 'synthetic_owned_namespace_recovery_v3')
        state = read_json(self.folder / RECOVERY_STATE)
        self.assertEqual(state['recovery_binding']['compatibility_commit'], '58bbf0d501cda9244804734d52a1d425d47bd0c3')
        self.assertEqual(state['recovery_binding']['failed_receipt_sha256'], c.sha((self.folder / FAILURE_RECEIPT).read_bytes()))
        self.assertEqual(self.old_bytes(), self.previous)
        write = self.obj.execute()
        self.assertTrue(write['completed'], write)
        self.assertEqual(write['counts'], {'get':8, 'create':1, 'metadata':1, 'file':1})
        calls = len(self.obj.calls)
        self.assertTrue(self.obj.execute()['cached']); self.assertEqual(len(self.obj.calls), calls)
        self.assertEqual(self.old_bytes(), self.previous)

    def test_expired_original_lifetime_is_preserved_and_new_clock_starts_now(self):
        p = self.folder / c.OWNED_STATE; prior = read_json(p)
        prior['started_at'] = '2020-01-01T00:00:00+00:00'
        prior['expires_at'] = '2020-01-01T00:30:00+00:00'; atomic_json(p, prior)
        before = self.old_bytes(); started = datetime.now(timezone.utc)
        self.count = 120; result = self.run_recovery(); self.assertTrue(result['completed'])
        state = read_json(self.folder / RECOVERY_STATE)
        self.assertGreaterEqual(datetime.fromisoformat(state['started_at']), started)
        self.assertEqual(datetime.fromisoformat(state['expires_at']) - datetime.fromisoformat(state['started_at']), timedelta(minutes=30))
        self.assertEqual(self.old_bytes(), before)

    def test_wrong_prior_failure_or_missing_receipt_blocks_before_transport(self):
        p = self.folder / c.OWNED_STATE; original = p.read_bytes()
        for change in ({'get_attempts':65}, {'completed':True}, {'resume_allowed':True},
                       {'owner':8}, {'inventory_scope':'other'}, {'schema_version':3}):
            prior = json.loads(original); prior.update(change); atomic_json(p, prior)
            with self.subTest(change=change), self.assertRaises(c.ZenodoAPIError): self.run_recovery()
            self.assertEqual(self.calls, []); self.assertFalse((self.folder / RECOVERY_STATE).exists())
        p.write_bytes(original); (self.folder / FAILURE_RECEIPT).unlink()
        with self.assertRaises((c.ZenodoAPIError, FileNotFoundError)): self.run_recovery()
        self.assertEqual(self.calls, [])

    def test_wrong_guard_receipt_or_response_hash_blocks_before_transport(self):
        p = self.folder / FAILURE_RECEIPT; original = p.read_bytes()
        for fault in ('counts', 'owner', 'status', 'hash', 'diagnostics'):
            prior = json.loads(original)
            if fault == 'counts': prior['guard']['transport_attempts'] = 63
            elif fault == 'owner': prior['guard']['observations'][-1]['owner_validated'] = False
            elif fault == 'status': prior['guard']['observations'][-1]['status'] = 301
            elif fault == 'hash': prior['guard']['observations'][1]['sha256'] = '0'*64
            else: prior['diagnostics']['stage'] = 'response_owner'
            atomic_json(p, prior)
            with self.subTest(fault=fault), self.assertRaises(c.ZenodoAPIError): self.run_recovery()
            self.assertEqual(self.calls, [])
        p.write_bytes(original)

    def test_old_page_tampering_and_orphans_block_without_overwriting_evidence(self):
        p = self.folder / 'synthetic-owned-pages/page-002.json'; before = p.read_bytes()
        p.write_bytes(before + b' ')
        with self.assertRaises(c.ZenodoAPIError): self.run_recovery()
        self.assertEqual(p.read_bytes(), before + b' '); self.assertEqual(self.calls, [])
        p.write_bytes(before); orphan = self.folder / 'synthetic-owned-pages/page-063.json'
        atomic_json(orphan, [])
        with self.assertRaises(c.ZenodoAPIError): self.run_recovery()
        self.assertTrue(orphan.exists()); self.assertEqual(self.calls, [])

    def test_transport_resume_replays_recovery_pages_without_renewing_clock(self):
        self.count = 220; self.fault = ('transport', 3)
        first = self.run_recovery(); self.assertTrue(first['resume_allowed'])
        p = self.folder / RECOVERY_STATE; before = read_json(p)
        self.fault = None; result = self.run_recovery(resume=True)
        self.assertTrue(result['completed']); self.assertEqual(result['get_attempts'], 8)
        self.assertEqual(result['cumulative_inventory_gets'], 88)
        self.assertEqual(self.calls, ['/api/deposit/depositions', '/api/deposit/depositions?page=1&size=100',
                                     '/api/deposit/depositions?page=2&size=100', '/api/deposit/depositions?page=3&size=100'])
        after = read_json(p)
        self.assertEqual((after['started_at'], after['expires_at']), (before['started_at'], before['expires_at']))
        self.assertEqual(after['failures'], before['failures']); self.assertEqual(self.old_bytes(), self.previous)

    def test_retained_recovery_page_drift_or_changed_prior_receipt_rejects_resume(self):
        self.count = 220; self.fault = ('transport', 3)
        self.assertTrue(self.run_recovery()['resume_allowed'])
        self.fault = ('change', 2); result = self.run_recovery(resume=True)
        self.assertTrue(result['failed']); self.assertFalse(result['resume_allowed'])
        self.assertFalse(read_json(self.obj.paths.safe_to_upload_path)['inventory_complete'])
        with self.assertRaises(c.ZenodoAPIError): self.run_recovery(resume=True)
        self.assertEqual(self.calls, []); self.assertEqual(self.old_bytes(), self.previous)

    def test_recovery_read_budget_is_durable_and_cumulative_ceiling_is_305(self):
        self.count = 120; self.fault = ('transport', 1)
        self.assertTrue(self.run_recovery()['resume_allowed'])
        p = self.folder / RECOVERY_STATE; state = read_json(p)
        state['get_attempts'] = 223; atomic_json(p, state)
        self.fault = None; result = self.run_recovery(resume=True)
        self.assertTrue(result['failed']); self.assertEqual(result['get_attempts'], 225)
        self.assertEqual(result['cumulative_inventory_gets'], 305)
        self.assertFalse(result['resume_allowed']); self.assertEqual(len(self.calls), 2)
        with self.assertRaises(c.ZenodoAPIError): self.run_recovery(resume=True)
        self.assertEqual(self.calls, []); self.assertEqual(self.old_bytes(), self.previous)

    def test_recovery_expiry_and_bound_evidence_cannot_be_renewed(self):
        self.count = 220; self.fault = ('transport', 3)
        self.assertTrue(self.run_recovery()['resume_allowed'])
        p = self.folder / RECOVERY_STATE; original = p.read_bytes()
        for fault in ('expired', 'budget', 'binding', 'receipt'):
            state = json.loads(original)
            if fault == 'expired':
                state['started_at'] = '2020-01-01T00:00:00+00:00'; state['expires_at'] = '2020-01-01T00:30:00+00:00'
            elif fault == 'budget': state['prior_observed_gets'] = 79
            elif fault == 'binding': state['recovery_binding']['compatibility_commit'] = 'other'
            else:
                receipt = self.folder / FAILURE_RECEIPT; receipt.write_bytes(receipt.read_bytes() + b' ')
            atomic_json(p, state)
            with self.subTest(fault=fault), self.assertRaises(c.ZenodoAPIError): self.run_recovery(resume=True)
            self.assertEqual(self.calls, [])

    def test_late_own_run_collision_never_grants_inventory(self):
        self.fault = ('collision', 166); result = self.run_recovery()
        self.assertTrue(result['failed']); self.assertFalse(result['resume_allowed'])
        self.assertFalse(read_json(self.obj.paths.safe_to_upload_path)['inventory_complete'])
        with self.assertRaises(c.ZenodoAPIError): self.obj.execute()
        self.assertEqual(self.old_bytes(), self.previous)

    def test_redirect_never_grants_or_automatically_retries(self):
        self.fault = ('redirect', 1); result = self.run_recovery()
        self.assertTrue(result['failed']); self.assertFalse(result['resume_allowed'])
        self.assertEqual(result['get_attempts'], 2); self.assertEqual(len(self.calls), 2)
        self.assertFalse(read_json(self.obj.paths.safe_to_upload_path)['inventory_complete'])
        with self.assertRaises(c.ZenodoAPIError): self.run_recovery(resume=True)
        self.assertEqual(self.calls, []); self.assertEqual(self.old_bytes(), self.previous)

    def test_escaped_token_echo_is_rejected_before_page_persistence(self):
        self.fault = ('echo', 63); result = self.run_recovery()
        self.assertTrue(result['failed']); self.assertFalse(result['resume_allowed'])
        self.assertEqual(result['get_attempts'], 64); self.assertEqual(result['verified_pages'], 62)
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertFalse((self.folder / RECOVERY_PAGES / 'page-063.json').exists())
        self.assertNotIn(TOKEN, (self.folder / RECOVERY_STATE).read_text())
        self.assertEqual(self.old_bytes(), self.previous)

    def test_changed_prior_receipt_blocks_write_before_create(self):
        self.count = 120; self.assertTrue(self.run_recovery()['completed'])
        p = self.folder / FAILURE_RECEIPT; p.write_bytes(p.read_bytes() + b' ')
        self.obj.calls = []
        with self.assertRaises(c.ZenodoAPIError): self.obj.execute()
        self.assertEqual(self.obj.calls, []); self.assertFalse((self.folder / 'synthetic-controller.json').exists())

    def test_original_write_ledger_or_uncertain_create_cannot_be_recreated(self):
        atomic_json(self.obj.paths.uploads_registry_path, {c.SOURCE:{'needs_reconciliation':True}})
        with self.assertRaises(c.ZenodoAPIError): self.run_recovery()
        self.assertEqual(self.calls, []); self.assertFalse((self.folder / RECOVERY_STATE).exists())

    def test_uncertain_create_consumes_original_allowance_after_recovery(self):
        self.count = 120; self.assertTrue(self.run_recovery()['completed'])
        self.obj.mutation = 'uncertain'; result = self.obj.execute()
        self.assertTrue(result['failed']); self.assertEqual(result['counts']['create'], 1)
        calls = len(self.obj.calls)
        with self.assertRaises(c.ZenodoAPIError): self.obj.execute()
        self.assertEqual(len(self.obj.calls), calls); self.assertEqual(self.old_bytes(), self.previous)

    def test_retained_diagnostic_hash_is_bound_and_cannot_change(self):
        failed = read_json(self.folder / FAILURE_RECEIPT)
        p = self.folder / c.RECOVERY_DIAGNOSTIC
        atomic_json(p, {'guard':{'observations':[{'sha256':failed['guard']['observations'][-1]['sha256']}]}})
        self.count = 220; self.fault = ('transport', 3)
        self.assertTrue(self.run_recovery()['resume_allowed'])
        state = read_json(self.folder / RECOVERY_STATE)
        self.assertEqual(state['recovery_binding']['diagnostic_receipt_sha256'], c.sha(p.read_bytes()))
        p.write_bytes(p.read_bytes() + b' ')
        with self.assertRaises(c.ZenodoAPIError): self.run_recovery(resume=True)
        self.assertEqual(self.calls, [])

    def test_recovery_cli_dispatch_requires_inventory_only_and_forwards_resume(self):
        import sys
        owner = self.folder / 'owner.json'; atomic_json(owner, OWNER)
        for inventory_only, resume in ((False, False), (True, False), (True, True)):
            args = ['controller', '--owner-file', str(owner), '--recover-inventory']
            if inventory_only: args.append('--inventory-only')
            if resume: args.append('--resume-inventory')
            with patch.object(sys, 'argv', args), patch.object(c, 'inventory', return_value={'completed':True}) as scan, \
                    patch.object(c, 'execute') as execute, contextlib.redirect_stdout(io.StringIO()):
                code = c.main()
            execute.assert_not_called()
            if inventory_only:
                self.assertEqual(code, 0)
                scan.assert_called_once_with(c.RUN, OWNER, resume=resume, recovery=True)
            else:
                self.assertEqual(code, 1); scan.assert_not_called()

    def test_recovery_grant_cannot_be_consumed_by_generic_or_production(self):
        self.count = 120; self.assertTrue(self.run_recovery()['completed'])
        safe = read_json(self.obj.paths.safe_to_upload_path)
        for environment in ('sandbox', 'production'):
            with self.subTest(environment=environment), self.assertRaises((ValueError, c.ZenodoAPIError)):
                require_inventory(safe, environment)

    def test_completed_recovery_cannot_be_refreshed_or_downgraded(self):
        self.count = 120; self.assertTrue(self.run_recovery()['completed'])
        for resume in (False, True):
            with self.assertRaises(c.ZenodoAPIError): self.run_recovery(resume=resume)
            self.assertEqual(self.calls, [])
        count = len(self.obj.calls)
        with self.assertRaises(c.ZenodoAPIError): self.obj.run_inventory()
        self.assertEqual(len(self.obj.calls), count)


if __name__ == '__main__': unittest.main()
