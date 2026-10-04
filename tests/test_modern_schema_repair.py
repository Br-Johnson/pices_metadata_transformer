"""Complete local schemas, source component oracles and a357-file dummy repair."""

import ast
import base64
import json
import shutil
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

from scripts import modern_canary_errors as errors
from scripts import modern_draft_schema as schema
from scripts import modern_run02_schema_repair as repair
from scripts import modern_run02_subjects_repair as prior
from scripts import modern_synthetic_canary as modern
from tests import test_modern_run02_subjects_repair as old_fixture
from tests import test_modern_synthetic_canary as fixture


class ModernSchemaTests(unittest.TestCase):
    def body(self):
        return schema.synthetic_payload(modern.load(modern.PACKET / 'metadata-put.json'))

    def test_all_submitted_fields_validate_and_only_publisher_changes_from_prior_wire(self):
        source = modern.load(modern.PACKET / 'metadata-put.json')
        before = deepcopy(source)
        body = schema.synthetic_payload(source)
        self.assertEqual(source, before)
        previous = modern.modern_wire_payload(source)
        previous['metadata']['publisher'] = 'Zenodo'
        self.assertEqual(body, previous)
        self.assertTrue(schema.validate_payload(body))
        self.assertNotIn('publisher', before['metadata'])
        self.assertNotIn('pids', body)
        prepared = requests.Request('PUT', modern.ORIGIN + '/api/records/101/draft', json=body).prepare()
        self.assertEqual(len(prepared.body), 517)
        self.assertEqual(modern.sha(prepared.body), repair.PREPARED_PUT_SHA)

    def test_every_required_field_and_each_nested_input_rejects_before_transport(self):
        body = self.body()
        for field in body['metadata']:
            changed = deepcopy(body)
            changed['metadata'].pop(field)
            with self.subTest(missing=field), self.assertRaises(modern.Held):
                schema.validate_payload(changed)
        changes = [({'publisher': ''}), ({'creators': []}), ({'creators': [{'person_or_org': {'name': 'x'}}]}),
                   ({'creators': [{'person_or_org': {'type': 'organizational'}}]}),
                   ({'resource_type': {'id': 'not-a-vocabulary-id'}}), ({'title': 'x'}),
                   ({'publication_date': '2026-13-03'}), ({'publication_date': '2026-10'}),
                   ({'subjects': [{'subject': modern.NAMESPACE, 'secret': 'fixture'}]}),
                   ({'keywords': [modern.NAMESPACE]}), ({'description': 7})]
        for fields in changes:
            changed = deepcopy(body)
            changed['metadata'].update(fields)
            with self.subTest(fields=list(fields)), self.assertRaises(modern.Held):
                schema.validate_payload(changed)
        for changed in [dict(body, pids={}), dict(body, files={'enabled': False}), dict(body, files={'enabled': 1}),
                        dict(body, files={'enabled': True, 'entries': {}}),
                        dict(body, access={'record': 'public', 'files': 'public'}),
                        dict(body, access={'files': 'restricted'})]:
            with self.assertRaises(modern.Held):
                schema.validate_payload(changed)

    def test_pinned_schema_tampering_and_unsealed_source_reject_locally(self):
        body = self.body()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in schema.SCHEMA_FILES:
                shutil.copyfile(schema.SCHEMAS / name, root / name)
            (root / 'record-v6.0.0.json').write_bytes((root / 'record-v6.0.0.json').read_bytes() + b' ')
            with patch.object(schema, 'SCHEMAS', root), self.assertRaises(modern.Held):
                schema.validate_payload(body)
        source = modern.load(modern.PACKET / 'metadata-put.json')
        source['metadata']['publisher'] = 'invented-source-publisher'
        with self.assertRaises(modern.Held):
            schema.synthetic_payload(source)

    def test_exact_official_component_methods_reproduce_publisher_and_empty_file_errors(self):
        path = Path(__file__).parent / 'fixtures/zenodo-modern/components.py'
        tree = ast.parse(path.read_text())

        def method(owner_name, method_name, base):
            owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner_name)
            function = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == method_name)
            node = ast.ClassDef(name=owner_name, bases=[ast.Name(id='Base', ctx=ast.Load())],
                                keywords=[], body=[function], decorator_list=[])
            module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
            namespace = {'Base': base, '_': lambda value: value, 'ValidationError': ValueError}
            exec(compile(module, str(path), 'exec'), namespace)
            return namespace[owner_name]

        class PIDBase:
            def validate(self, *args, **kwargs):
                return True, []

        provider = method('DataCitePIDProvider', 'validate', PIDBase)()
        for publisher, expected in ((None, ['metadata.publisher']), ('Zenodo', [])):
            record = {'metadata': {'publisher': publisher}, 'pids': {}}
            success, found = provider.validate(record, identifier=None)
            self.assertEqual([error['field'] for error in found], expected)
            self.assertEqual(success, not bool(expected))

        class FileBase:
            files_data_key = 'files'

            def get_record_files(self, record):
                return record.files

            def assign_files_enabled(self, record, enabled):
                record.files.enabled = enabled

            def assign_files_default_preview(self, *args):
                pass

        for can_toggle, items, expected in ((True, [], [schema.EMPTY_FILE_MESSAGES[0]]),
                                           (False, [], [schema.EMPTY_FILE_MESSAGES[1]]), (True, [object()], [])):
            component = method('BaseRecordFilesComponent', 'update_draft', FileBase)()
            component.service = SimpleNamespace(check_permission=lambda *a, value=can_toggle, **k: value,
                                                config=SimpleNamespace(default_files_enabled=True))
            record = SimpleNamespace(files=SimpleNamespace(enabled=True, items=lambda value=items: value))
            found = []
            component.update_draft(None, data={'files': {'enabled': True}}, record=record, errors=found)
            self.assertEqual([message for error in found for message in error['messages']], expected)
            self.assertTrue(all(error['field'] == 'files.enabled' for error in found))

    def test_safe_unknown_paths_are_diagnosable_but_values_credentials_and_unsafe_names_are_suppressed(self):
        secret = 'dummy_canary_credential_1234567890'
        data = {'errors': [{'field': field, 'messages': ['private-value', secret]} for field in (
            'metadata.publisher', 'files.enabled', 'metadata.creators.0.person_or_org.family_name',
            'custom_fields.unknown_name', 'metadata.creators[0].role',
            'metadata.' + secret, 'metadata.' + base64.b64encode(secret.encode()).decode(),
            'metadata.' + 'a' * 128, 'https://bad.invalid/path', 'metadata.a\nheader',
            'private-unrecognized-path', 'metadata.' + 'a' * 32)]}
        result = errors.validation_errors_projection(data, secret)
        self.assertEqual(result['error_fields'], sorted([
            'metadata.publisher', 'files.enabled', 'metadata.creators.0.person_or_org.family_name',
            'custom_fields.unknown_name', 'metadata.creators[0].role']))
        self.assertTrue(result['error_field_names_suppressed'])
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn('private-value', json.dumps(result))
        self.assertNotIn('https', json.dumps(result))

    def test_field_names_have_finite_count_length_and_malformed_shape_flags(self):
        data = {'errors': [{'field': f'metadata.field_{index}', 'messages': []} for index in range(40)]}
        result = errors.validation_errors_projection(data, fixture.TOKEN)
        self.assertEqual(len(result['error_fields']), 16)
        self.assertTrue(result['error_field_names_truncated'])
        self.assertEqual(result['errors_count'], 40)
        for value in (None, 'private', {'private': 'value'}, [None, {}, {'field': []}]):
            result = errors.validation_errors_projection({'errors': value}, fixture.TOKEN)
            self.assertFalse(result['errors_shape_supported'])
            self.assertEqual(result['error_fields'], [])

    def test_warning_policy_rejects_null_malformed_or_same_field_permission_errors(self):
        for value in (None, {}, '', [None], [{'field': 'files.enabled', 'messages': None}],
                      [{'field': 'files.enabled', 'messages': ["You don't have permissions to manage files options."]}]):
            with self.subTest(error_type=type(value).__name__), self.assertRaises(modern.Held):
                schema.expected_empty_file_warning({'errors': value})
        self.assertFalse(schema.expected_empty_file_warning({}))
        self.assertFalse(schema.expected_empty_file_warning({'errors': []}))


class ModernSchemaRepairTests(unittest.TestCase):
    def setUp(self):
        self.old = old_fixture.SubjectsRepairTests('test_exact_two_action_repair_preserves_history_and_cannot_reenter')
        self.old.setUp()
        self.addCleanup(self.old.doCleanups)
        old_stage = self.old.stage
        old_response = deepcopy(self.old.case.remote)
        old_response['errors'] = [{'field': 'metadata.publisher', 'messages': ['private-publisher-detail']},
                                  {'field': 'files.enabled', 'messages': [schema.EMPTY_FILE_MESSAGES[0]]}]
        controller = prior.Controller(old_stage, fixture.TOKEN, None, lambda: self.old.case.clock)

        def old_transport(method, url, body, headers, **options):
            prepared = requests.Request(method, url, headers=headers, json=body).prepare()
            controller.check_prepared(prepared)
            return fixture.Response(old_response)

        controller.transport = old_transport
        with self.assertRaises(modern.Held):
            controller.run()
        # Emulate the actual frozen older projection: names were not saved.
        state = modern.load(old_stage / 'state.json')
        for name in ('error_fields', 'error_field_names_suppressed', 'error_field_names_truncated'):
            state['responses'][0]['validation_errors'].pop(name)
        modern.save(old_stage, state)
        patcher = patch.object(repair, 'PRIOR_RUNTIME', prior.runtime_binding())
        patcher.start()
        self.addCleanup(patcher.stop)
        base = Path(self.old.case.temp.name)
        padding = base / 'additional-retained-history'
        padding.mkdir(mode=0o700)
        self.roots = [*self.old.roots, old_stage, padding]
        actual = [p for root in self.roots for p in root.rglob('*') if p.is_file()]
        for index in range(357 - len(actual)):
            modern.atomic(padding / f'receipt-{index:03d}.json', {'fixture': index})
        actual = [p for root in self.roots for p in root.rglob('*') if p.is_file()]
        self.assertEqual(len(actual), 357)
        self.manifest = base / 'sealed357.json'
        modern.atomic(self.manifest, {'schema_version': 1, 'files_sha256': {str(p): modern.sha(p.read_bytes()) for p in actual}})
        self.before = {str(p): (p.read_bytes(), p.stat().st_mode) for p in actual}
        self.stage = base / repair.NAMESPACE
        self.calls, self.fault = [], None
        self.remote = deepcopy(self.old.case.remote)

    def stage_and_grant(self):
        staged = repair.stage_packet(self.stage, self.old.stage, self.roots, fixture.TOKEN, self.manifest)
        self.assertEqual(staged['preserved_file_inventory']['count'], 358)
        snapshot = {p.name: p.read_bytes() for p in self.stage.iterdir()}
        result = repair.preflight(self.stage, fixture.TOKEN)
        self.assertEqual(snapshot, {p.name: p.read_bytes() for p in self.stage.iterdir()})
        self.assertEqual(result['declared_manifest_files'], 357)
        self.assertTrue(result['local_schema_valid'])
        self.assertEqual(result['provider_requests'], 0)
        self.assertFalse((self.stage / 'approval.json').exists())
        grant = {'schema_version': 1, 'approved': True, 'approval_reference': 'OFFLINE FULL SCHEMA REPAIR ONLY',
                 'executor': modern.EXECUTOR, 'binding': repair.binding(self.stage), 'limits': repair.LIMITS,
                 'started_at': self.old.case.clock.isoformat(),
                 'valid_until': (self.old.case.clock + timedelta(minutes=10)).isoformat(),
                 'owner': fixture.OWNER, 'known_ids': self.old.case.original_grant['known_ids'],
                 'existing_candidate_only': True, 'no_create_or_reset': True,
                 'controlled_full_schema_repair': True, 'allow_exact_missing_upload_warning': True,
                 'historical_get_intents': 197, 'preserved_file_inventory': staged['preserved_file_inventory']}
        modern.atomic(self.stage / 'approval.json', grant)
        return grant

    def model(self, method, body):
        self.calls.append(method)
        if self.fault == 'uncertain':
            raise RuntimeError('PRIVATE ' + fixture.TOKEN)
        if self.fault == 'redirect':
            return fixture.Response({}, 302, {'Location': 'https://bad.invalid/' + fixture.TOKEN})
        if method == 'PUT':
            self.assertTrue(schema.validate_payload(body))
            self.remote['metadata'], self.remote['access'] = deepcopy(body['metadata']), deepcopy(body['access'])
        data = deepcopy(self.remote)
        data['errors'] = [{'field': 'files.enabled', 'messages': [schema.EMPTY_FILE_MESSAGES[0]]}]
        if self.fault == 'short_warning':
            data['errors'][0]['messages'] = [schema.EMPTY_FILE_MESSAGES[1]]
        if self.fault == 'no_errors':
            data.pop('errors')
        if self.fault == 'null_errors':
            data['errors'] = None
        if self.fault == 'all_metadata_absent':
            data['metadata'] = {}
            data['errors'].append({'field': 'metadata.publisher', 'messages': ['private-message']})
        if self.fault == 'http400':
            return fixture.Response(data, 400)
        if self.fault == 'publisher':
            data['metadata'].pop('publisher')
            data['errors'].append({'field': 'metadata.publisher', 'messages': ['private-message']})
        if self.fault == 'unknown':
            data['errors'].append({'field': 'metadata.future_field', 'messages': ['private-message']})
        if self.fault == 'permission':
            data['errors'][0]['messages'] = ["You don't have permissions to manage files options."]
        if self.fault == 'warning_value':
            data['errors'][0]['messages'].append('private-extra')
        if self.fault == 'owner':
            data['parent']['access']['owned_by']['user'] = '999'
        if self.fault == 'access':
            data['access']['files'] = 'public'
        if self.fault == 'files':
            data['files']['count'] = 1
        if self.fault == 'doi':
            data['pids'] = {'doi': {'provider': 'datacite', 'identifier': '10.5072/zenodo.101'}}
        if self.fault == 'credential':
            data['errors'][0]['messages'] = [fixture.TOKEN]
        if self.fault == 'readback' and method == 'GET':
            data['metadata']['publisher'] = 'wrong-publisher'
        return fixture.Response(data)

    def transport(self, method, url, body, headers, **options):
        self.assertEqual(url, modern.ORIGIN + '/api/records/101/draft')
        self.assertFalse(options['allow_redirects'])
        self.assertTrue(options['verify'])
        prepared = requests.Request(method, url, headers=headers, json=body).prepare()
        self.active.check_prepared(prepared)
        return self.model(method, body)

    def controller(self):
        self.active = repair.Controller(self.stage, fixture.TOKEN, self.transport, lambda: self.old.case.clock)
        return self.active

    def assert_preserved(self):
        self.assertEqual(self.before, {name: (Path(name).read_bytes(), Path(name).stat().st_mode) for name in self.before})

    def test_full357_manifest_stage_no_grant_preflight_and_controller_warning_readback(self):
        self.stage_and_grant()
        result = self.controller().run()
        self.assertEqual(self.calls, ['PUT', 'GET'])
        self.assertTrue(result['completed'])
        self.assertTrue(result['put_validated'])
        self.assertTrue(result['prepared_put_verified'])
        self.assertFalse(result['publication_ready'])
        self.assertEqual(result['accepted_empty_file_warnings'], 2)
        self.assertEqual(result['historical_get_intents'], 198)
        self.assertEqual(result['run02_metadata_put_intents'], 3)
        self.assertEqual(result['run02_create_intents'], 1)
        self.assertEqual(result['responses'][0]['validation_errors']['error_fields'], ['files.enabled'])
        self.assertNotIn('Missing uploaded', json.dumps(result))
        self.assert_preserved()
        with self.assertRaises(modern.Held):
            self.controller()

    def test_exact_shared_execute_session_prepares_517bytes_without_real_transport(self):
        self.stage_and_grant()

        def send(session, prepared, **options):
            self.assertFalse(options['allow_redirects'])
            self.assertEqual(prepared.url, modern.ORIGIN + '/api/records/101/draft')
            body = json.loads(prepared.body) if prepared.body is not None else None
            if body is not None:
                self.assertEqual(modern.sha(prepared.body), repair.PREPARED_PUT_SHA)
            return self.model(prepared.method, body)

        with patch('requests.sessions.Session.send', send), patch.object(modern, 'datetime') as clock, patch.object(repair, 'datetime') as repair_clock:
            for value in (clock, repair_clock):
                value.now.return_value = self.old.case.clock
                value.fromisoformat.side_effect = datetime.fromisoformat
            result = modern._execute_controller(self.stage, fixture.TOKEN, repair.Controller)
        self.assertTrue(result['completed'])
        self.assertEqual(self.calls, ['PUT', 'GET'])
        self.assert_preserved()

    def test_second_exact_warning_and_no_warning_are_supported_only_with_complete_draft(self):
        for fault, expected in (('short_warning', 2), ('no_errors', 0)):
            with self.subTest(fault=fault):
                if self.calls:
                    self.doCleanups()
                    self.setUp()
                self.stage_and_grant()
                self.fault = fault
                result = self.controller().run()
                self.assertEqual(result['accepted_empty_file_warnings'], expected)
                self.assertTrue(result['completed'])
                self.assertEqual(self.calls, ['PUT', 'GET'])
                self.assert_preserved()

    def test_any_other_error_or_identity_access_files_pid_fault_stops_before_get(self):
        for fault in ('publisher', 'unknown', 'permission', 'warning_value', 'null_errors', 'all_metadata_absent', 'http400',
                      'owner', 'access', 'files', 'doi', 'credential', 'redirect', 'uncertain'):
            with self.subTest(fault=fault):
                if self.calls:
                    self.doCleanups()
                    self.setUp()
                self.stage_and_grant()
                self.fault = fault
                with self.assertRaises(modern.Held):
                    self.controller().run()
                self.assertEqual(self.calls, ['PUT'])
                state = modern.load(self.stage / 'state.json')
                self.assertEqual(state['counts'], {'metadata': 1, 'get': 0})
                self.assertTrue(state['failed'])
                self.assertFalse(state['put_validated'])
                self.assertNotIn(fixture.TOKEN, json.dumps(state))
                self.assertNotIn('private-message', json.dumps(state))
                if fault == 'unknown':
                    self.assertIn('metadata.future_field', state['responses'][0]['validation_errors']['error_fields'])
                with self.assertRaises(modern.Held):
                    self.controller()
                self.assert_preserved()

    def test_failed_readback_permanently_spends_both_intents(self):
        self.stage_and_grant()
        self.fault = 'readback'
        with self.assertRaises(modern.Held):
            self.controller().run()
        self.assertEqual(self.calls, ['PUT', 'GET'])
        self.assertEqual(modern.load(self.stage / 'state.json')['counts'], repair.LIMITS)
        with self.assertRaises(modern.Held):
            self.controller()
        self.assert_preserved()

    def test_missing_inventory_or_unsafe_destination_rejects_before_staging(self):
        manifest = modern.load(self.manifest)
        manifest['files_sha256'].pop(str(self.old.stage / 'state.json'))
        modern.atomic(self.manifest, manifest)
        with self.assertRaises(modern.Held):
            repair.stage_packet(self.stage, self.old.stage, self.roots, fixture.TOKEN, self.manifest)
        self.assertFalse(self.stage.exists())
        for target in (self.old.stage / repair.NAMESPACE, self.stage.parent / 'unused' / '..' / repair.NAMESPACE):
            with self.assertRaises(modern.Held):
                repair.stage_packet(target, self.old.stage, [], fixture.TOKEN, self.manifest)
            self.assertFalse(target.exists())
        self.assert_preserved()

    def test_fresh_window_and_warning_grant_are_mandatory_and_no_extra_route_exists(self):
        grant = self.stage_and_grant()
        for change in ({'allow_exact_missing_upload_warning': False}, {'controlled_full_schema_repair': False},
                       {'valid_until': (self.old.case.clock + timedelta(minutes=11)).isoformat()}):
            value = {**deepcopy(grant), **change}
            modern.atomic(self.stage / 'approval.json', value)
            with self.assertRaises(modern.Held):
                self.controller()
        modern.atomic(self.stage / 'approval.json', grant)
        controller = self.controller()
        for kind, method, path in (('create', 'POST', '/api/records'), ('doi', 'POST', controller.base() + '/pids/doi'),
                                   ('init', 'POST', controller.base() + '/files'), ('metadata', 'PUT', controller.base() + '/'),
                                   ('get', 'GET', controller.base())):
            with self.assertRaises(modern.Held):
                controller.request(kind, method, path, 200)
        self.assertEqual(self.calls, [])
        self.assertEqual(modern.load(self.stage / 'state.json')['counts'], {'metadata': 0, 'get': 0})


if __name__ == '__main__':
    unittest.main()
