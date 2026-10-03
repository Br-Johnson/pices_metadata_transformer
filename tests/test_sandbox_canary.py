"""Offline source-pinned sandbox exception regressions; no credentials/provider writes."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.sandbox_canary import SandboxCanary
from scripts.path_config import OutputPaths
from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
from scripts.upload_service import DraftUploadService, atomic_json, read_json

PACKET = Path(__file__).resolve().parents[1] / 'docs/handoff/sandbox-canary-20261002'
PLAN = PACKET / 'legacy-duplicate-exception.json'


class SandboxCanaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        shutil.copytree(PACKET / 'actual-data', Path(self.tmp.name) / 'data')
        self.paths = OutputPaths(self.tmp.name, 'sandbox')
        self.file = Path(self.paths.zenodo_json_dir) / 'FGDC-100.json'
        self.plan = SandboxCanary(str(PLAN), 'sandbox')
        self.payload = json.loads(self.file.read_text())
        with patch('scripts.pre_upload_duplicate_check.get_logger'), patch(
                'scripts.pre_upload_duplicate_check.create_zenodo_client') as factory:
            factory.return_value.base_url = 'https://sandbox.zenodo.org'
            self.checker = PreUploadDuplicateChecker(output_dir=self.tmp.name, canary_plan=str(PLAN))

    def inventory(self, created='2025-01-01T00:00:00+00:00', marker=False, identifier=42):
        md = dict(self.payload['metadata'])
        md['keywords'] = [self.plan.plan['marker']] if marker else []
        record = {'id': identifier, 'created': created, 'metadata': md, 'title': md['title'], 'state': 'done'}
        return {'inventory_complete': True, 'titles': {md['title'].casefold()},
                'title_to_record': {md['title'].casefold(): record}, 'identifiers': set(), 'records': [record]}

    def check(self, inventory):
        return self.checker.check_file_for_duplicates(str(self.file), inventory)

    def test_historical_exact_match_allowed_only_with_explicit_plan(self):
        inventory = self.inventory()
        self.assertTrue(self.check(inventory)['safe_to_upload'])
        self.checker.canary = None
        self.assertFalse(self.check(inventory)['safe_to_upload'])

    def test_production_rejects_before_client(self):
        with patch('scripts.pre_upload_duplicate_check.create_zenodo_client') as client:
            with self.assertRaises(ValueError):
                PreUploadDuplicateChecker(sandbox=False, canary_plan=str(PLAN))
            client.assert_not_called()
        with self.assertRaises(ValueError):
            DraftUploadService(OutputPaths(self.tmp.name, 'production'), 'production', canary_plan=str(PLAN))

    def test_changed_plan_rejected(self):
        p = Path(self.tmp.name) / 'plan.json'; p.write_bytes(PLAN.read_bytes()+b' ')
        with self.assertRaises(ValueError):
            SandboxCanary(str(p), 'sandbox')

    def test_changed_payload_or_unknown_source_rejected(self):
        self.payload['metadata']['description'] += 'changed'
        self.file.write_text(json.dumps(self.payload))
        self.assertFalse(self.check(self.inventory())['safe_to_upload'])
        unknown = self.file.with_name('FGDC-102.json'); unknown.write_bytes(self.file.read_bytes())
        self.assertFalse(self.checker.check_file_for_duplicates(str(unknown), self.inventory())['safe_to_upload'])

    def test_recent_or_undated_duplicates_rejected(self):
        for date in ('2026-10-02T00:00:00+00:00', '2026-10-02T01:00:00+00:00', None, 'bad-date'):
            with self.subTest(date=date):
                self.assertFalse(self.check(self.inventory(created=date))['safe_to_upload'])

    def test_missing_own_run_ledger_is_not_historical(self):
        self.assertFalse(self.check(self.inventory(marker=True))['safe_to_upload'])

    def test_other_canary_namespace_not_historical(self):
        inventory = self.inventory()
        inventory['records'][0]['metadata']['keywords'] = ['pices-sandbox-canary:other-run']
        self.assertFalse(self.check(inventory)['safe_to_upload'])

    def test_duplicate_identifier_is_never_waived(self):
        inventory = self.inventory()
        inventory['identifiers'] = {'10.1234/test'}
        inventory['records'][0]['metadata']['doi'] = '10.1234/test'
        # Even when the title match is historical, explicit payload DOI identity is not an exception.
        self.payload['metadata']['doi'] = '10.1234/test'
        self.file.write_text(json.dumps(self.payload))
        self.assertFalse(self.check(inventory)['safe_to_upload'])

    def test_client_origin_must_match_exactly(self):
        service = DraftUploadService(self.paths, 'sandbox', canary_plan=str(PLAN))
        for host in ('http://sandbox.zenodo.org', 'https://zenodo.org', 'https://sandbox.zenodo.org.evil', 'https://sandbox.zenodo.org:444'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                service.upload(str(self.file), Mock(base_url=host))

    def test_production_rejects_exception_inventory_without_explicit_optin(self):
        paths = OutputPaths(self.tmp.name, 'production')
        atomic_json(paths.safe_to_upload_path, {'environment':'production','sandbox_canary':self.plan.binding})
        with self.assertRaises(ValueError):
            DraftUploadService(paths,'production').upload(str(self.file),Mock(base_url='https://zenodo.org'))

    def service_fixture(self):
        from datetime import datetime, timedelta, timezone
        from scripts.upload_service import prepare_metadata, metadata_hash
        from scripts.artifact_contract import prepare_artifact
        md,xp,sha=prepare_metadata(str(self.file),self.paths)
        artifact=prepare_artifact(self.payload,xp)
        atomic_json(self.paths.safe_to_upload_path, {'environment':'sandbox','inventory_complete':True,
            'sandbox_canary':self.plan.binding,'files':[self.file.name],'canary_create_files':[self.file.name],
            'metadata_hashes':{self.file.name:metadata_hash(md)},
            'valid_until':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()})
        atomic_json(self.paths.uploads_registry_path, {'_sandbox_canary':self.plan.binding})
        remote={'id':71,'state':'unsubmitted','submitted':False,'metadata':md,'files':[]}
        client=Mock(base_url='https://sandbox.zenodo.org')
        client.create_deposition.return_value={'id':71}
        client.get_deposition.side_effect=lambda identifier:dict(remote)
        def upload(*args,**kwargs):
            f=artifact['files'][0]
            remote['files']=[{'filename':f['name'],'filesize':f['size'],'checksum':'md5:'+f['md5']}]
        client.upload_file.side_effect=upload
        return DraftUploadService(self.paths,'sandbox',canary_plan=str(PLAN)),client,remote

    def test_unchanged_retry_reuses_id_and_does_not_create_or_upload(self):
        service,client,remote=self.service_fixture()
        first=service.upload(str(self.file),client)
        self.assertTrue(first['success'])
        self.assertIn(self.plan.plan['marker'],client.create_deposition.call_args.args[0]['keywords'])
        second=service.upload(str(self.file),client)
        self.assertTrue(second['success'])
        self.assertEqual(first['deposition_id'],second['deposition_id'])
        self.assertEqual(client.create_deposition.call_count,1)
        self.assertEqual(client.upload_file.call_count,1)
        client.publish_deposition.assert_not_called()
        client.delete_deposition.assert_not_called()
        self.assertEqual(read_json(self.paths.uploads_registry_path)['_sandbox_canary'],self.plan.binding)

    def test_uncertain_create_cannot_repeat(self):
        service,client,_=self.service_fixture()
        client.create_deposition.side_effect=RuntimeError('Unknown result')
        self.assertFalse(service.upload(str(self.file),client)['success'])
        with self.assertRaises(ValueError):
            service.upload(str(self.file),client)
        self.assertEqual(client.create_deposition.call_count,1)

    def test_known_own_run_requires_exact_ledger_identity(self):
        service,client,_=self.service_fixture()
        self.assertTrue(service.upload(str(self.file),client)['success'])
        inv=self.inventory(marker=True,identifier=71)
        inv['records'][0].update(state='unsubmitted',submitted=False)
        self.assertTrue(self.check(inv)['safe_to_upload'])
        inv['records'][0]['id']=72
        self.assertFalse(self.check(inv)['safe_to_upload'])

    def test_publisher_rejects_canary_ledger_before_client(self):
        from scripts.publish_records import RecordPublisher
        service,client,_=self.service_fixture()
        self.assertTrue(service.upload(str(self.file),client)['success'])
        with patch('scripts.publish_records.create_zenodo_client') as factory:
            with self.assertRaises(ValueError):
                RecordPublisher(output_dir=self.tmp.name)
            factory.assert_not_called()

    def test_generic_service_cannot_consume_exception_or_marked_payload(self):
        service,client,_=self.service_fixture()
        with self.assertRaises(ValueError):
            DraftUploadService(self.paths,'sandbox').upload(str(self.file),client)
        client.create_deposition.assert_not_called()

    def test_full_remote_match_set_cannot_hide_recent_duplicate(self):
        inv=self.inventory()
        inv['records'] += self.inventory(created='2026-10-02T01:00:00+00:00',identifier=43)['records']
        self.assertFalse(self.check(inv)['safe_to_upload'])

    def test_fresh_complete_inventory_still_required(self):
        inv=self.inventory();inv['inventory_complete']=False
        self.assertFalse(self.check(inv)['safe_to_upload'])
        service,client,_=self.service_fixture()
        safe=read_json(self.paths.safe_to_upload_path);safe['valid_until']='2000-01-01T00:00:00+00:00'
        atomic_json(self.paths.safe_to_upload_path,safe)
        with self.assertRaises(ValueError):
            service.upload(str(self.file),client)
        client.create_deposition.assert_not_called()

    def test_plan_mutation_after_constructor_rejected(self):
        p=Path(self.tmp.name)/'reviewed.json';p.write_bytes(PLAN.read_bytes())
        plan=SandboxCanary(str(p),'sandbox');p.write_bytes(PLAN.read_bytes()+b' ')
        with self.assertRaises(ValueError):
            plan.authorize(str(self.file),self.paths)

    def test_lost_ledger_cannot_reuse_consumed_inventory_to_create_again(self):
        service,client,_=self.service_fixture()
        self.assertTrue(service.upload(str(self.file),client)['success'])
        Path(self.paths.uploads_registry_path).unlink()
        with self.assertRaises(ValueError):
            service.upload(str(self.file),client)
        self.assertEqual(client.create_deposition.call_count,1)

    def test_successful_retry_rejects_unexpected_publication(self):
        service,client,remote=self.service_fixture()
        self.assertTrue(service.upload(str(self.file),client)['success'])
        remote.update(state='done',submitted=True)
        with self.assertRaises(ValueError):
            service.upload(str(self.file),client)
        self.assertEqual(client.create_deposition.call_count,1)

    def test_lost_single_entry_cannot_reuse_consumed_grant(self):
        service,client,_=self.service_fixture()
        self.assertTrue(service.upload(str(self.file),client)['success'])
        atomic_json(self.paths.uploads_registry_path, {'_sandbox_canary':self.plan.binding})
        with self.assertRaises(ValueError):
            service.upload(str(self.file),client)
        self.assertEqual(client.create_deposition.call_count,1)

    def test_checker_initializes_bound_ledger_from_real_scan_results(self):
        inventory=self.inventory()
        with patch.object(self.checker,'load_existing_zenodo_records',return_value=inventory), patch('builtins.print'):
            summary=self.checker.check_all_files()
            self.assertEqual(summary['summary']['safe_to_upload'],3)
            self.checker.generate_upload_list()
        ledger=read_json(self.paths.uploads_registry_path)
        self.assertEqual(ledger,{'_sandbox_canary':self.plan.binding})
        self.assertEqual(summary['historical_duplicate_exceptions']['FGDC-100.json'],[42])
        service=DraftUploadService(self.paths,'sandbox',canary_plan=str(PLAN))
        self.assertEqual(len(service.pending_files()),3)

    def test_changed_namespace_and_cross_source_ledger_are_rejected(self):
        service,client,_=self.service_fixture()
        for registry in ({'_sandbox_canary':{'plan_sha256':'wrong','run_namespace':'other'}},
                         {'_sandbox_canary':self.plan.binding,'FGDC-999':{}}):
            atomic_json(self.paths.uploads_registry_path,registry)
            with self.assertRaises(ValueError):
                service.upload(str(self.file),client)
        client.create_deposition.assert_not_called()

    def test_all_selected_unchanged_retry_uses_three_creates_total(self):
        from scripts.upload_service import prepare_metadata, metadata_hash
        from scripts.artifact_contract import prepare_artifact
        service,client,_=self.service_fixture()
        safe=read_json(self.paths.safe_to_upload_path)
        files=sorted(Path(self.paths.zenodo_json_dir).glob('*.json'))
        safe['files']=[p.name for p in files]
        safe['canary_create_files']=[p.name for p in files]
        safe['metadata_hashes']={p.name:metadata_hash(prepare_metadata(str(p),self.paths)[0]) for p in files}
        atomic_json(self.paths.safe_to_upload_path,safe)
        remotes={}
        def create(metadata):
            identifier=71+len(remotes)
            remotes[identifier]={'id':identifier,'state':'unsubmitted','submitted':False,'metadata':metadata,'files':[]}
            return {'id':identifier}
        def upload(identifier,path,filename):
            raw=Path(path).read_bytes()
            remotes[identifier]['files']=[{'filename':filename,'filesize':len(raw),'checksum':'md5:'+hashlib.md5(raw).hexdigest()}]
        client.create_deposition.side_effect=create
        client.get_deposition.side_effect=lambda identifier:remotes[identifier]
        client.upload_file.side_effect=upload
        for file in files:
            self.assertTrue(service.upload(str(file),client)['success'])
        for file in files:
            self.assertTrue(service.upload(str(file),client)['success'])
        self.assertEqual(client.create_deposition.call_count,3)
        self.assertEqual(client.upload_file.call_count,3)
        self.assertEqual(len(remotes),3)
        client.publish_deposition.assert_not_called();client.delete_deposition.assert_not_called()

    def test_refresh_does_not_regrant_creation_for_existing_entry(self):
        service,client,_=self.service_fixture()
        self.assertTrue(service.upload(str(self.file),client)['success'])
        inv=self.inventory(marker=True,identifier=71)
        inv['records'][0].update(state='unsubmitted',submitted=False)
        result=self.check(inv);self.assertTrue(result['safe_to_upload'])
        self.checker.safe_to_upload=[result]
        with patch('builtins.print'):
            self.checker.generate_upload_list()
        atomic_json(self.paths.uploads_registry_path, {'_sandbox_canary':self.plan.binding})
        with self.assertRaises(ValueError):
            service.upload(str(self.file),client)
        self.assertEqual(client.create_deposition.call_count,1)
