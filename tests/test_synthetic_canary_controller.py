"""Offline full-controller transactions with dummy transport; never provider writes."""
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import requests
from scripts import synthetic_canary_controller as c
from scripts.upload_service import atomic_json, read_json

TOKEN = 'NetworkSecret(dummy-synthetic-controller)'
OWNER = 7
BUCKET = '/api/files/11111111-1111-4111-8111-111111111111'


def response(data, status=200):
    r = requests.Response(); r.status_code = status
    r._content = data if isinstance(data, bytes) else json.dumps(data).encode()
    r._content_consumed = True
    return r


class SyntheticControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.stage = Path(self.tmp.name) / 'synthetic'
        shutil.copytree(c.PACKET / 'synthetic/data', self.stage / 'data')
        self.runpatch = patch.object(c, 'RUN', self.stage); self.runpatch.start(); self.addCleanup(self.runpatch.stop)
        self.env = patch.dict(os.environ, {'ZENODO_SANDBOX_TOKEN': TOKEN}); self.env.start(); self.addCleanup(self.env.stop)
        self.paths, self.file, self.metadata, self.artifact, self.plan = c.bindings(self.stage)
        atomic_json(self.paths.safe_to_upload_path, {'environment': 'sandbox', 'inventory_scope':c.OWNED_SCOPE,'inventory_complete': True,
            'valid_until': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            'files': [self.file.name], 'metadata_hashes': {self.file.name: c.metadata_hash(self.metadata)}})
        atomic_json(self.paths.already_uploaded_path, {'environment':'sandbox','inventory_scope':c.OWNED_SCOPE,'total_records':0,'records':[]})
        self.save_inventory_binding()
        self.calls = []; self.mutation = None
        self.remote = {'id': 101, 'owner': OWNER, 'submitted': False, 'state': 'unsubmitted',
                       'metadata': {'prereserve_doi': {'doi':'10.5072/test.101'}}, 'files': [],
                       'links': {'bucket': c.ORIGIN + BUCKET}}

    def save_inventory_binding(self):
        atomic_json(self.stage/'state/sandbox/synthetic-owned-inventory-controller.json',
            {'completed':True,'failed':False,'owner':OWNER,'packet':c.INVENTORY_SHA,'inventory_scope':c.OWNED_SCOPE,
             'safe_sha256':c.sha(Path(self.paths.safe_to_upload_path).read_bytes()),
             'retained_sha256':c.sha(Path(self.paths.already_uploaded_path).read_bytes())})

    def transport(self, session, request, **kwargs):
        self.calls.append((request.method, request.path_url))
        self.assertFalse(kwargs['allow_redirects']); self.assertTrue(kwargs['stream'])
        self.assertEqual(request.headers['Authorization'], 'Bearer ' + TOKEN)
        method, path = request.method, request.path_url
        if method == 'GET' and path == '/api/deposit/depositions': return response([{'id': 3, 'owner': OWNER}])
        if method == 'POST':
            if self.mutation == 'uncertain': raise requests.ConnectionError('leak ' + TOKEN)
            if self.mutation == 'redirect':
                r=response({},302);r.headers['Location']='https://evil.test/steal';return r
            if self.mutation == 'owner': self.remote['owner'] = 8
            if self.mutation == 'published': self.remote['submitted'] = True
            if self.mutation == 'crossbucket': self.remote['links']['bucket'] = 'https://evil.test' + BUCKET
            return response(self.remote,201)
        if method == 'PUT' and path == '/api/deposit/depositions/101':
            self.remote['metadata'] = json.loads(request.body)['metadata']
            self.remote['metadata']['prereserve_doi'] = {'doi':'10.5072/test.101'}
            return response(self.remote)
        if method == 'PUT' and path.startswith(BUCKET):
            target = self.artifact['files'][0]
            self.remote['files'] = [{'filename': target['name'], 'filesize':target['size'],
                'checksum':'md5:' + target['md5'], 'links':{'download':c.ORIGIN + BUCKET + '/' + target['name']}}]
            return response({'key':target['name']},201)
        if method == 'GET' and path.startswith(BUCKET):
            raw = Path(self.paths.original_fgdc_dir, c.SOURCE + '.xml').read_bytes()
            return response(raw if self.mutation != 'download' else b'bad')
        if method == 'GET' and path == '/api/deposit/depositions/101':
            if self.mutation == 'id': self.remote['id'] = 102
            if self.mutation == 'metadata' and self.remote['files']: self.remote['metadata']['title'] = 'different'
            return response(self.remote)
        self.fail('unexpected request')

    def execute(self):
        with patch('requests.sessions.Session.send', self.transport), patch('scripts.zenodo_api.ZenodoAPIClient._rate_limit_check'):
            return c.execute(self.stage, OWNER)

    def test_complete_create_readback_retry_and_process_rerun(self):
        result = self.execute()
        self.assertTrue(result['completed'],result)
        self.assertEqual(result['counts'],{'get':8,'create':1,'metadata':1,'file':1})
        count = len(self.calls); again = self.execute()
        self.assertTrue(again['cached']); self.assertFalse(again['fresh_remote_check'])
        self.assertEqual(len(self.calls),count)
        ledger = read_json(self.paths.uploads_registry_path)[c.SOURCE]
        state = read_json(self.stage/'state/sandbox/synthetic-controller.json')
        self.assertEqual(ledger['deposition_id'],state['id'])
        self.assertTrue(ledger['success'])

    def test_uncertain_create_consumed_and_secret_redacted(self):
        self.mutation = 'uncertain'; result = self.execute()
        self.assertTrue(result['failed']); self.assertEqual(result['counts']['create'],1)
        self.assertNotIn(TOKEN,json.dumps(result))
        count = len(self.calls)
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(len(self.calls),count)
        self.assertTrue(read_json(self.paths.uploads_registry_path)[c.SOURCE]['needs_reconciliation'])

    def test_redirect_owner_id_publication_bucket_metadata_and_download_mismatch_stop(self):
        for mutation in ['redirect','owner','id','published','crossbucket','metadata','download']:
            with self.subTest(mutation=mutation):
                # Each scenario is a genuinely independent local fixture.
                obj = SyntheticControllerTests('test_complete_create_readback_retry_and_process_rerun')
                obj.setUp()
                try:
                    obj.mutation = mutation; result = obj.execute()
                    self.assertTrue(result['failed'],result)
                    self.assertLessEqual(sum(m=='POST' for m,_ in obj.calls),1)
                    if mutation in ['redirect','owner','published','crossbucket']:
                        self.assertFalse(any(m=='PUT' for m,_ in obj.calls))
                finally: obj.doCleanups()

    def test_changed_payload_and_stale_inventory_block_before_transport(self):
        self.file.write_bytes(self.file.read_bytes()+b' ')
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.calls,[])

    def test_duplicate_post_and_production_or_crosshost_rejected_before_transport(self):
        guard = c.SyntheticTransport(TOKEN,OWNER,self.paths,self.metadata,self.artifact,self.plan)
        guard.original_send = self.transport
        for url in ['https://zenodo.org/api/deposit/depositions','https://evil.test/api/deposit/depositions']:
            request = requests.Request('POST',url,json={},headers={'Authorization':'Bearer '+TOKEN}).prepare()
            with self.assertRaises(c.ZenodoAPIError): guard.send(requests.Session(),request)
            self.assertEqual(self.calls,[])
        # Counter exhaustion is enforced even if the persisted ID were not yet assigned.
        guard.state.update(failed=False,phase='upload');guard.state['counts']['create']=1
        atomic_json(self.paths.uploads_registry_path,{c.SOURCE:{'environment':'sandbox','source_sha256':self.plan['source_sha256'],
            'metadata_sha256':c.metadata_hash(self.metadata),'artifact_contract':self.artifact,'needs_reconciliation':True}})
        req=requests.Request('POST',c.ORIGIN+'/api/deposit/depositions',json={},headers={'Authorization':'Bearer '+TOKEN}).prepare()
        with self.assertRaises(c.ZenodoAPIError): guard.send(requests.Session(),req)
        self.assertEqual(self.calls,[])

    def test_prior_or_lost_controller_ledger_cannot_recreate(self):
        atomic_json(self.paths.uploads_registry_path,{c.SOURCE:{'needs_reconciliation':True}})
        with self.assertRaises(c.ZenodoAPIError): self.execute()
        self.assertEqual(self.calls,[])

    def test_stale_inventory_rejected_before_any_request(self):
        safe=read_json(self.paths.safe_to_upload_path);safe['valid_until']='2000-01-01T00:00:00+00:00'
        atomic_json(self.paths.safe_to_upload_path,safe)
        self.save_inventory_binding()
        with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.calls,[])

    def test_attempt_and_id_are_durable_before_following_writes(self):
        original=self.transport
        def checked(session,request,**kwargs):
            state=read_json(self.stage/'state/sandbox/synthetic-controller.json')
            if request.method=='POST':self.assertEqual(state['counts']['create'],1)
            if request.method=='PUT':
                self.assertEqual(state['id'],101)
                self.assertEqual(read_json(self.paths.uploads_registry_path)[c.SOURCE]['deposition_id'],101)
            return original(session,request,**kwargs)
        self.transport=checked
        self.assertTrue(self.execute()['completed'])

    def test_wrong_bearer_and_each_forbidden_origin_path_stop_before_transport(self):
        for url,method,token in [(c.ORIGIN+'/api/deposit/depositions','GET','wrong'),
            ('https://zenodo.org/api/deposit/depositions','POST',TOKEN),
            ('https://evil.test/api/deposit/depositions','POST',TOKEN),
            (c.ORIGIN+'/api/deposit/depositions/101/actions/publish','POST',TOKEN),
            (c.ORIGIN+'/api/deposit/depositions?token=','GET',TOKEN),
            ('https://sandbox.zenodo.org:444/api/deposit/depositions','GET',TOKEN)]:
            guard=c.SyntheticTransport(TOKEN,OWNER,self.paths,self.metadata,self.artifact,self.plan)
            guard.original_send=self.transport
            request=requests.Request(method,url,json={},headers={'Authorization':'Bearer '+token}).prepare()
            with self.subTest(url=url),self.assertRaises(c.ZenodoAPIError):guard.send(requests.Session(),request)
            self.assertEqual(self.calls,[])
            # Independent clean local controller state; no transport or ledger exists.
            guard.path.unlink()

    def test_cleanup_error_cannot_leak_or_claim_success(self):
        original=self.transport
        def broken(session,request,**kwargs):
            r=original(session,request,**kwargs)
            if request.method=='POST':
                def close():raise RuntimeError(TOKEN)
                r.close=close
            return r
        self.transport=broken
        result=self.execute();self.assertFalse(result['completed']);self.assertTrue(result['failed'])
        self.assertNotIn(TOKEN,json.dumps(result))
        self.assertEqual(result['diagnostics']['stage'],'response_cleanup')

    def test_cli_failure_is_sanitized_and_has_nonzero_exit(self):
        import contextlib,io,sys
        owner=Path(self.tmp.name,'owner.json');owner.write_text(str(OWNER))
        capture=io.StringIO()
        with patch.object(sys,'argv',['controller','--owner-file',str(owner)]),patch.object(c,'execute',side_effect=RuntimeError(TOKEN)),contextlib.redirect_stdout(capture):
            code=c.main()
        self.assertEqual(code,1);self.assertNotIn(TOKEN,capture.getvalue())

    def test_current_readback_cannot_drop_or_change_reserved_doi(self):
        original=self.transport
        def dropped(session,request,**kwargs):
            r=original(session,request,**kwargs)
            if request.method=='GET' and request.path_url=='/api/deposit/depositions/101' and self.remote['files']:
                body=json.loads(r.content);body['metadata'].pop('prereserve_doi',None)
                return response(body)
            return r
        self.transport=dropped
        result=self.execute()
        self.assertTrue(result['failed']);self.assertFalse(result['completed'])

    def test_empty_constructor_cannot_authorize_first_write(self):
        def empty(session,request,**kwargs):
            self.calls.append((request.method,request.path_url));return response([])
        self.transport=empty
        result=self.execute();self.assertTrue(result['failed'])
        self.assertEqual(result['counts']['create'],0);self.assertEqual(len(self.calls),1)

    def inventory_transport(self, session, request, **kwargs):
        from urllib.parse import urlsplit,parse_qs
        self.calls.append((request.method,request.path_url))
        state=read_json(self.stage/'state/sandbox/synthetic-owned-inventory-controller.json')
        self.assertEqual(state['get_attempts'],len(self.calls))
        self.assertFalse(kwargs['allow_redirects']);self.assertEqual(request.method,'GET')
        path=urlsplit(request.url).path
        self.assertEqual(path,'/api/deposit/depositions')
        if '?' in request.url and self.mutation=='inventory_redirect':
            r=response({},301);r.headers['Location']='https://evil.test/records';return r
        if '?' in request.url and self.mutation=='inventory_bound':
            page=int(parse_qs(urlsplit(request.url).query)['page'][0])
            return response([{'id':page*100+i,'owner':OWNER,'metadata':{'title':'Unrelated'}} for i in range(100)])
        return response([{'id':3,'owner':OWNER,'metadata':{'title':'Unrelated existing item'},'state':'done','files':[]}])

    def run_inventory(self):
        with patch('requests.sessions.Session.send',self.inventory_transport),patch('scripts.zenodo_api.ZenodoAPIClient._rate_limit_check'):
            return c.inventory(self.stage,OWNER)

    def test_inventory_entrypoint_then_separately_dispatched_write_controller(self):
        (self.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
        result=self.run_inventory()
        self.assertTrue(result['completed'],result);self.assertEqual(result['get_attempts'],2)
        count=len(self.calls)
        with self.assertRaises(c.ZenodoAPIError):self.run_inventory()
        self.assertEqual(len(self.calls),count)
        self.assertTrue(self.execute()['completed'])

    def test_inventory_redirect_stops_and_cannot_reset_attempt_budget(self):
        (self.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
        self.mutation='inventory_redirect';result=self.run_inventory()
        self.assertTrue(result['failed']);self.assertEqual(result['get_attempts'],2)
        self.assertFalse(read_json(self.paths.safe_to_upload_path)['inventory_complete'])
        count=len(self.calls)
        with self.assertRaises(c.ZenodoAPIError):self.run_inventory()
        self.assertEqual(len(self.calls),count)
        with self.assertRaises(c.ZenodoAPIError):self.execute()

    def test_owned_inventory_ten_get_cap_preserves_five_prior_attempts(self):
        (self.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
        self.mutation='inventory_bound';result=self.run_inventory()
        self.assertTrue(result['failed']);self.assertEqual(result['get_attempts'],10)
        self.assertEqual(result['prior_observed_gets']+result['get_attempts'],15)
        self.assertEqual(len(self.calls),10)

    def test_synthetic_gate_does_not_request_public_community(self):
        (self.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
        def owned_only(session,request,**kwargs):
            from urllib.parse import urlsplit
            self.assertEqual(urlsplit(request.url).path,'/api/deposit/depositions')
            return response([{'id':3,'owner':OWNER,'metadata':{'title':'Historical unrelated draft'},'files':[]}])
        with patch('requests.sessions.Session.send',owned_only),patch('scripts.zenodo_api.ZenodoAPIClient._rate_limit_check'):
            result=c.inventory(self.stage,OWNER)
        self.assertTrue(result['completed'],result)

    def test_existing_own_run_title_file_or_embedded_identity_requires_reconciliation(self):
        for marker in ('title','file','embedded'):
            obj=SyntheticControllerTests('test_complete_create_readback_retry_and_process_rerun');obj.setUp()
            try:
                (obj.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
                original=obj.inventory_transport
                def collision(session,request,**kwargs):
                    r=original(session,request,**kwargs)
                    if '?' in request.url:
                        body=json.loads(r.content)
                        if marker=='title':body[0]['metadata']['title']=obj.metadata['title']
                        elif marker=='file':body[0]['files']=[{'filename':c.SOURCE+'.xml'}]
                        else:body[0]['metadata']['notes']='Prior source '+c.SOURCE
                        return response(body)
                    return r
                obj.inventory_transport=collision
                with self.subTest(marker=marker):
                    result=obj.run_inventory();self.assertTrue(result['failed']);self.assertFalse(result['completed'])
                    self.assertFalse(read_json(obj.paths.safe_to_upload_path)['inventory_complete'])
                    self.assertTrue(all(m=='GET' for m,_ in obj.calls))
            finally:obj.doCleanups()

    def test_prior_read_only_400_receipt_is_preserved_without_new_community_query(self):
        (self.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
        old=self.stage/'state/sandbox/synthetic-inventory-controller.json'
        atomic_json(old,{'completed':False,'failed':True,'get_attempts':2,'owner':OWNER,
                        'packet':c.INVENTORY_SHA,'diagnostics':{'status':400}})
        before=old.read_bytes();result=self.run_inventory()
        self.assertTrue(result['completed']);self.assertEqual(old.read_bytes(),before)
        state=read_json(self.stage/'state/sandbox/synthetic-owned-inventory-controller.json')
        self.assertEqual(state['previous_attempt_sha256'],c.sha(before))
        self.assertEqual(result['prior_observed_gets'],5)

    def test_nonmatching_prior_attempt_and_uncertain_create_block_new_owned_gate(self):
        (self.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
        old=self.stage/'state/sandbox/synthetic-inventory-controller.json'
        atomic_json(old,{'completed':True,'failed':False,'get_attempts':2,'owner':OWNER,'packet':c.INVENTORY_SHA})
        with self.assertRaises(c.ZenodoAPIError):self.run_inventory()
        self.assertEqual(self.calls,[])
        old.unlink();atomic_json(self.paths.uploads_registry_path,{c.SOURCE:{'needs_reconciliation':True}})
        with self.assertRaises(c.ZenodoAPIError):self.run_inventory()
        self.assertEqual(self.calls,[])

    def test_generic_production_and_actual_source_checkers_still_require_public_inventory(self):
        from unittest.mock import Mock
        from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
        from scripts.upload_service import require_inventory
        for sandbox in (False,True):
            client=Mock();client.get_records_by_query.return_value=[{'id':21,'metadata':{'title':'Public record'}}]
            client.get_all_my_depositions.return_value=[{'id':22,'metadata':{'title':'Owned record'}}]
            with self.subTest(sandbox=sandbox),patch('scripts.pre_upload_duplicate_check.create_zenodo_client',return_value=client):
                checker=PreUploadDuplicateChecker(sandbox=sandbox,output_dir=str(Path(self.tmp.name,'generic-'+str(sandbox))))
                result=checker.load_existing_zenodo_records()
                self.assertEqual({r['id'] for r in result['records']},{21,22})
                client.get_records_by_query.assert_called_once_with(q='communities:pices',size=200)
                client.get_all_my_depositions.assert_called_once_with()
                client.reset_mock();client.get_records_by_query.side_effect=ValueError('Public inventory unavailable')
                with self.assertRaises(ValueError):checker.load_existing_zenodo_records()
                client.get_all_my_depositions.assert_not_called()
                self.assertFalse(read_json(checker.paths.safe_to_upload_path)['inventory_complete'])
        with self.assertRaises(ValueError):require_inventory(read_json(self.paths.safe_to_upload_path),'production')

    def test_owned_grant_cannot_be_consumed_by_generic_upload_paths(self):
        from unittest.mock import Mock
        from scripts.upload_service import DraftUploadService, require_inventory
        (self.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
        self.assertTrue(self.run_inventory()['completed'])
        service=DraftUploadService(self.paths,'sandbox')
        client=Mock(base_url=c.ORIGIN)
        with self.assertRaises(c.ZenodoAPIError):service.pending_files()
        with self.assertRaises(c.ZenodoAPIError):service.upload(str(self.file),client)
        with self.assertRaises(c.ZenodoAPIError):service.upload(str(self.file),client,synthetic_controller=object())
        guard=c.SyntheticTransport(TOKEN,OWNER,self.paths,self.metadata,self.artifact,self.plan)
        with self.assertRaises(c.ZenodoAPIError):service.upload(str(self.file),client,synthetic_controller=guard)
        client.create_deposition.assert_not_called();client.update_deposition_metadata.assert_not_called()
        with self.assertRaises(ValueError):require_inventory(read_json(self.paths.safe_to_upload_path),'production',synthetic_controller=guard)
        self.assertTrue(self.execute()['completed'])

    def test_incomplete_owned_collision_fields_fail_closed(self):
        for bad in [{'id':3,'owner':OWNER},
                    {'id':3,'owner':OWNER,'metadata':{},'files':[]},
                    {'id':3,'owner':OWNER,'metadata':{'title':'Title'}},
                    {'id':3,'owner':OWNER,'metadata':{'title':'Title'},'files':[{}]}]:
            obj=SyntheticControllerTests('test_complete_create_readback_retry_and_process_rerun');obj.setUp()
            try:
                (obj.stage/'state/sandbox/synthetic-owned-inventory-controller.json').unlink()
                original=obj.inventory_transport
                def malformed(session,request,**kwargs):
                    r=original(session,request,**kwargs)
                    return response([bad]) if '?' in request.url else r
                obj.inventory_transport=malformed
                with self.subTest(bad=bad):
                    result=obj.run_inventory();self.assertTrue(result['failed']);self.assertFalse(result['completed'])
                    self.assertFalse(read_json(obj.paths.safe_to_upload_path)['inventory_complete'])
            finally:obj.doCleanups()
