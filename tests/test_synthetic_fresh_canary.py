"""Fresh-run isolation and actual transaction fixtures; network is always mocked."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests
from scripts import synthetic_canary_controller as c, synthetic_fresh_canary as f
from scripts.upload_service import atomic_json, read_json, require_inventory
import test_synthetic_canary_controller as base

TOKEN, OWNER = base.TOKEN, base.OWNER


class FreshCanaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.old = Path(self.tmp.name) / 'spent-original' / 'synthetic'
        self.old.mkdir(parents=True)
        atomic_json(self.old / 'original-controller.json', {'failed': True, 'create': 1, 'gets': 190})
        self.old_bytes = {p: p.read_bytes() for p in self.old.iterdir()}
        oldpatch = patch.object(c, 'RUN', self.old); oldpatch.start(); self.addCleanup(oldpatch.stop)
        self.stage = Path(self.tmp.name) / f.SOURCE
        f.stage_packet(self.stage)
        self.paths, self.file, self.metadata, self.artifact, self.plan = f.bindings(self.stage)
        self.folder = self.stage / 'state/sandbox'
        env = patch.dict(os.environ, {'ZENODO_SANDBOX_TOKEN': TOKEN}); env.start(); self.addCleanup(env.stop)
        self.calls = []; self.mutation = None
        self.remote = {'id': 101, 'owner': OWNER, 'submitted': False, 'state': 'unsubmitted',
                       'created': datetime.now(timezone.utc).isoformat(),
                       'metadata': {'prereserve_doi': {'doi': '10.5072/test.101'}}, 'files': [],
                       'links': {'bucket': c.ORIGIN + base.BUCKET}}

    def transport(self, session, request, **kwargs):
        self.calls.append((request.method, request.path_url))
        state = read_json(self.folder / f.STATE); journal = read_json(self.folder / f.JOURNAL)
        self.assertEqual(journal['state_sha256'], c.sha((self.folder / f.STATE).read_bytes()))
        self.assertEqual(journal['counts'], state['counts'])
        self.assertFalse(kwargs['allow_redirects']); self.assertTrue(kwargs['stream'])
        self.assertEqual(request.headers['Authorization'], 'Bearer ' + TOKEN)
        self.assertEqual(kwargs['timeout'], (10, 30))
        method, path = request.method, request.path_url
        if method == 'GET' and path == '/api/deposit/depositions':
            if self.mutation == 'empty_owner': return base.response([])
            if isinstance(self.mutation, str) and self.mutation.startswith('bad_control_'):
                item = {'id': 3, 'owner': OWNER, 'metadata': {}, 'files': []}
                if self.mutation == 'bad_control_metadata': item.pop('metadata')
                elif self.mutation == 'bad_control_files': item.pop('files')
                elif self.mutation == 'bad_control_title': item['metadata']['title'] = None
                elif self.mutation == 'bad_control_alias': item['files'] = [{'filename': 'Unrelated', 'key': 3}]
                elif self.mutation == 'bad_control_absent_alias': item['files'] = [{}]
                elif self.mutation == 'bad_control_empty_alias': item['files'] = [{'filename': ''}]
                else: item['files'] = [{'key': f.SOURCE + '.xml'}]
                return base.response([item])
            md = {'title': f.TITLE} if self.mutation == 'collision' else {'title': 'Unrelated historical item'}
            return base.response([{'id': 3, 'owner': OWNER, 'metadata': md, 'files': []}])
        if method == 'POST':
            self.assertEqual(state['counts']['create'], 1)
            self.assertTrue(read_json(self.paths.uploads_registry_path)[f.SOURCE]['needs_reconciliation'])
            if self.mutation == 'uncertain': raise requests.ConnectionError('untrusted ' + TOKEN)
            if self.mutation == 'server500':
                r = base.response(('<html><h1>Internal Server Error</h1>owner=987654321 token=' + TOKEN + '</html>').encode(), 500)
                r.headers['Content-Type'] = 'text/html; charset=utf-8'; r.headers['X-Secret'] = TOKEN
                return r
            if self.mutation == 'json500':
                r = base.response({'message': 'Internal server error: ' + TOKEN, 'owner': 987654321, 'secret': TOKEN}, 500)
                r.headers['Content-Type'] = 'application/json'; return r
            if self.mutation == 'large500': return base.response(b'x' * 65537, 500)
            if self.mutation == 'redirect':
                r = base.response({}, 302); r.headers['Location'] = 'https://evil.test/' + TOKEN; return r
            if self.mutation == 'old_created': self.remote['created'] = '2020-01-01T00:00:00+00:00'
            if self.mutation == 'missing_created': self.remote.pop('created')
            if self.mutation == 'future_created': self.remote['created'] = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
            if self.mutation == 'known_id': self.remote['id'] = 3
            if self.mutation == 'owner': self.remote['owner'] = 8
            if self.mutation == 'published': self.remote['submitted'] = True
            if self.mutation == 'crossbucket': self.remote['links']['bucket'] = 'https://evil.test' + base.BUCKET
            if self.mutation == 'echo': self.remote['private_echo'] = TOKEN
            return base.response(self.remote, 201)
        if method == 'PUT' and path == '/api/deposit/depositions/101':
            self.assertEqual(state['id'], 101)
            self.assertEqual(read_json(self.paths.uploads_registry_path)[f.SOURCE]['deposition_id'], 101)
            self.remote['metadata'] = json.loads(request.body)['metadata']
            self.remote['metadata']['prereserve_doi'] = {'doi': '10.5072/test.101'}
            return base.response(self.remote)
        if method == 'PUT' and path.startswith(base.BUCKET):
            target = self.artifact['files'][0]
            self.remote['files'] = [{'filename': target['name'], 'filesize': target['size'],
                'checksum': 'md5:' + target['md5'], 'links': {'download': c.ORIGIN + base.BUCKET + '/' + target['name']}}]
            return base.response({'key': target['name']}, 201)
        if method == 'GET' and path.startswith(base.BUCKET):
            return base.response(Path(self.paths.original_fgdc_dir, f.SOURCE + '.xml').read_bytes())
        if method == 'GET' and path == '/api/deposit/depositions/101':
            if self.mutation == 'changed_created': self.remote['created'] = datetime.now(timezone.utc).isoformat()
            if self.mutation == 'drop_doi' and self.remote['files']:
                self.remote['metadata'].pop('prereserve_doi', None)
            return base.response(self.remote)
        self.fail('Unexpected request')

    def execute(self):
        with patch('requests.sessions.Session.send', self.transport), patch('scripts.zenodo_api.ZenodoAPIClient._rate_limit_check'):
            return f.execute(self.stage, OWNER)

    def test_complete_new_identity_exact_readback_unchanged_retry_and_cached_rerun(self):
        result = self.execute(); self.assertTrue(result['completed'], result)
        self.assertEqual(result['counts'], f.LIMITS)
        self.assertEqual(result['cumulative_gets'], 198)
        self.assertTrue(result['exact_readback']); self.assertTrue(result['unchanged_retry'])
        self.assertEqual(result['source_id'], f.SOURCE)
        self.assertEqual(read_json(self.paths.uploads_registry_path)[f.SOURCE]['deposition_id'], 101)
        self.assertEqual(len(result['responses']), 11)
        count = len(self.calls); grant = Path(self.paths.safe_to_upload_path).read_bytes()
        again = self.execute(); self.assertTrue(again['cached']); self.assertFalse(again['fresh_remote_check'])
        self.assertEqual(len(self.calls), count); self.assertEqual(Path(self.paths.safe_to_upload_path).read_bytes(), grant)
        self.assertEqual({p: p.read_bytes() for p in self.old.iterdir()}, self.old_bytes)
        self.assertFalse((self.folder / 'synthetic-controller.json').exists())

    def test_new_clock_is_exact_thirty_minutes_and_not_renewed(self):
        now = datetime.now(timezone.utc); self.assertTrue(self.execute()['completed'])
        grant = read_json(self.paths.safe_to_upload_path)
        self.assertGreaterEqual(datetime.fromisoformat(grant['started_at']), now)
        self.assertEqual(datetime.fromisoformat(grant['valid_until']) - datetime.fromisoformat(grant['started_at']), timedelta(minutes=30))
        before = Path(self.paths.safe_to_upload_path).read_bytes(); self.execute()
        self.assertEqual(Path(self.paths.safe_to_upload_path).read_bytes(), before)

    def test_staging_cannot_reset_existing_or_bind_original_source_root(self):
        with self.assertRaises(FileExistsError): f.stage_packet(self.stage)
        with self.assertRaises(c.ZenodoAPIError): f.stage_packet(self.old)
        for nested in (self.old / f.SOURCE, self.old.parent / f.SOURCE):
            with self.subTest(nested=nested), self.assertRaises(c.ZenodoAPIError): f.stage_packet(nested)
            self.assertFalse(nested.exists())
        self.assertEqual({p: p.read_bytes() for p in self.old.iterdir()}, self.old_bytes)

    def test_changed_source_payload_packet_or_stage_binding_blocks_before_transport(self):
        for p in (self.file, Path(self.paths.original_fgdc_dir) / (f.SOURCE + '.xml'), self.stage / 'fresh-stage-binding.json'):
            raw = p.read_bytes(); p.write_bytes(raw + b' ')
            try:
                # Harmless JSON whitespace is rejected for payload/source; the stage
                # binding compares its full fixed value, so change its run explicitly.
                if p.name == 'fresh-stage-binding.json': atomic_json(p, {'source': c.SOURCE})
                with self.assertRaises((ValueError, c.ZenodoAPIError)): self.execute()
                self.assertEqual(self.calls, [])
            finally: p.write_bytes(raw)
        with patch.object(f, 'PACKET_SHA', '0' * 64), self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.calls, [])

    def test_generic_production_and_old_controller_cannot_consume_new_grant(self):
        self.folder.mkdir(parents=True, exist_ok=True); f.prepare_grant(self.paths, self.metadata, OWNER)
        for environment in ('sandbox', 'production'):
            with self.subTest(environment=environment), self.assertRaises(c.ZenodoAPIError):
                require_inventory(read_json(self.paths.safe_to_upload_path), environment)
        self.assertEqual(self.calls, [])

    def test_uncertain_create_remains_spent_with_lost_ledger_or_state(self):
        self.mutation = 'uncertain'; result = self.execute()
        self.assertTrue(result['failed']); self.assertEqual(result['counts']['create'], 1)
        self.assertNotIn(TOKEN, json.dumps(result)); count = len(self.calls)
        Path(self.paths.uploads_registry_path).unlink()
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        (self.folder / f.STATE).unlink()
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(len(self.calls), count)
        self.assertTrue((self.folder / f.JOURNAL).exists())

    def test_html_and_json_server_failures_retain_safe_diagnostics_and_stop(self):
        for mutation in ('server500', 'json500', 'large500'):
            obj = FreshCanaryTests('test_complete_new_identity_exact_readback_unchanged_retry_and_cached_rerun'); obj.setUp()
            try:
                obj.mutation = mutation; result = obj.execute()
                self.assertTrue(result['failed'], result); self.assertEqual(result['counts']['create'], 1)
                self.assertFalse(any(method == 'PUT' for method, _ in obj.calls))
                saved = read_json(obj.folder / f.EVIDENCE); text = json.dumps([result, saved])
                self.assertNotIn(TOKEN, text); self.assertNotIn('987654321', text); self.assertNotIn('evil.test', text)
                last = saved['responses'][-1]; self.assertEqual(last['status'], 500)
                self.assertEqual(len(last['body_sha256']), 64)
                if mutation != 'large500': self.assertIn('internal server error', last['error_categories'])
                else: self.assertFalse(last['body_complete'])
                count = len(obj.calls)
                with self.assertRaises(c.ZenodoAPIError): obj.execute()
                self.assertEqual(len(obj.calls), count)
            finally: obj.doCleanups()

    def test_redirect_collision_empty_owner_known_id_timestamp_echo_and_doi_drop_stop(self):
        for mutation in ('redirect', 'collision', 'empty_owner', 'known_id', 'old_created', 'missing_created',
                         'future_created', 'changed_created', 'owner', 'published', 'crossbucket', 'echo', 'drop_doi'):
            obj = FreshCanaryTests('test_complete_new_identity_exact_readback_unchanged_retry_and_cached_rerun'); obj.setUp()
            try:
                obj.mutation = mutation; result = obj.execute(); self.assertTrue(result['failed'], result)
                if mutation != 'drop_doi': self.assertFalse(any(method == 'PUT' for method, _ in obj.calls))
                self.assertNotIn(TOKEN, json.dumps(result))
                count = len(obj.calls)
                with self.assertRaises(c.ZenodoAPIError): obj.execute()
                self.assertEqual(len(obj.calls), count)
            finally: obj.doCleanups()

    def test_expired_grant_stops_without_clock_changes_or_requests(self):
        self.folder.mkdir(parents=True, exist_ok=True); f.prepare_grant(self.paths, self.metadata, OWNER)
        grant = read_json(self.paths.safe_to_upload_path)
        class Later(datetime):
            @classmethod
            def now(cls, tz=None): return datetime.fromisoformat(grant['valid_until']) + timedelta(seconds=1)
        before = Path(self.paths.safe_to_upload_path).read_bytes()
        with patch.object(f, 'datetime', Later), self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.calls, []); self.assertEqual(Path(self.paths.safe_to_upload_path).read_bytes(), before)

    def test_observed_control_identity_fields_and_every_file_alias_are_required(self):
        for mutation in ('bad_control_metadata', 'bad_control_files', 'bad_control_title', 'bad_control_alias',
                         'bad_control_absent_alias', 'bad_control_empty_alias', 'bad_control_own_file'):
            obj = FreshCanaryTests('test_complete_new_identity_exact_readback_unchanged_retry_and_cached_rerun'); obj.setUp()
            try:
                obj.mutation = mutation; result = obj.execute()
                self.assertTrue(result['failed'], result); self.assertEqual(result['counts']['create'], 0)
                self.assertEqual(len(obj.calls), 1)
            finally: obj.doCleanups()

    def test_changed_clock_or_durable_journal_binding_cannot_reconstruct_controls(self):
        self.folder.mkdir(parents=True, exist_ok=True); f.prepare_grant(self.paths, self.metadata, OWNER)
        f.FreshTransport(TOKEN, OWNER, self.paths, self.metadata, self.artifact, self.plan)
        p = Path(self.paths.safe_to_upload_path); original = p.read_bytes(); grant = read_json(p)
        grant['valid_until'] = (datetime.fromisoformat(grant['valid_until']) + timedelta(seconds=1)).isoformat(); atomic_json(p, grant)
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        p.write_bytes(original)
        journal = self.folder / f.JOURNAL; journal.write_bytes(journal.read_bytes() + b' ')
        # JSON whitespace keeps the value equivalent; changing its checksum does not.
        atomic_json(journal, {'state_sha256': '0' * 64})
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.calls, [])

    def test_production_publish_delete_and_nonmatching_put_paths_never_reach_transport(self):
        self.folder.mkdir(parents=True, exist_ok=True); f.prepare_grant(self.paths, self.metadata, OWNER)
        guard = f.FreshTransport(TOKEN, OWNER, self.paths, self.metadata, self.artifact, self.plan)
        for url, method in (('https://zenodo.org/api/deposit/depositions', 'POST'),
                            (c.ORIGIN + '/api/deposit/depositions/101/actions/publish', 'POST'),
                            (c.ORIGIN + '/api/deposit/depositions/101', 'DELETE')):
            guard.state['failed'] = False
            request = requests.Request(method, url, json={}, headers={'Authorization': 'Bearer ' + TOKEN}).prepare()
            with self.assertRaises(c.ZenodoAPIError): guard.send(requests.Session(), request)
        self.assertEqual(self.calls, []); self.assertEqual(guard.state['counts'], dict.fromkeys(f.LIMITS, 0))

    def test_cli_failure_has_no_arbitrary_exception_text(self):
        import contextlib, io, sys
        owner = Path(self.tmp.name) / 'owner.json'; atomic_json(owner, OWNER)
        capture = io.StringIO()
        with patch.object(sys, 'argv', ['fresh', '--stage', str(self.stage), '--owner-file', str(owner)]), \
                patch.object(f, 'execute', side_effect=RuntimeError(TOKEN)), contextlib.redirect_stdout(capture):
            code = f.main()
        self.assertEqual(code, 1); self.assertNotIn(TOKEN, capture.getvalue())


if __name__ == '__main__': unittest.main()
