"""Offline modern protocol contracts; all transport is an in-memory fixture."""
import hashlib
import json
import os
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from requests.structures import CaseInsensitiveDict

from scripts import modern_synthetic_canary as m

TOKEN = 'FIXTURE-TOKEN-0123456789'
OWNER = 42


class Response:
    def __init__(self, data, status=200, headers=None):
        self.raw = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.status_code = status
        self.headers = CaseInsensitiveDict(headers or {'Content-Type': 'application/json'})
        self.closed = False

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.raw), chunk_size):
            yield self.raw[offset:offset + chunk_size]

    def close(self):
        self.closed = True


class ModernCanaryTests(unittest.TestCase):
    def setUp(self):
        self.__dict__.pop('transport', None)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name) / m.NAMESPACE
        self.clock = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
        m.stage_packet(self.stage)
        self.grant = {'schema_version': 1, 'approved': True, 'approval_reference': 'OFFLINE TEST FIXTURE ONLY',
                      'executor': m.EXECUTOR, 'binding': m.binding(self.stage), 'limits': m.LIMITS,
                      'started_at': self.clock.isoformat(),
                      'valid_until': (self.clock + timedelta(minutes=30)).isoformat(),
                      'owner': OWNER, 'known_ids': ['3'], 'exclusive_namespace_confirmed': True,
                      'deposit_write_user_reported': True, 'prior_create_allowances_permanently_spent': True}
        m.atomic(self.stage / 'approval.json', self.grant)
        self.calls = []
        self.mutate = None
        self.reserved_on_create = False
        self.file_complete = False
        self.remote = deepcopy(m.load(m.PACKET / 'create.json'))
        self.remote.update({'id': '101', 'created': self.clock.isoformat(), 'is_published': False,
                            'status': 'draft', 'versions': {'index': 1},
                            'parent': {'id': '100', 'access': {'owned_by': {'user': str(OWNER)}}},
                            'pids': {}, 'files': {'enabled': True, 'count': 0, 'total_bytes': 0, 'entries': {}},
                            'links': {'self': m.ORIGIN + '/api/records/101/draft',
                                      'files': m.ORIGIN + '/api/records/101/draft/files'}})

    def file(self):
        base = m.ORIGIN + '/api/records/101/draft/files/' + m.packet()['file_key']
        data = {'key': m.packet()['file_key'], 'status': 'completed' if self.file_complete else 'pending',
                'transfer': {'type': 'L'},
                'links': {'self': base, 'content': base + '/content', 'commit': base + '/commit'}}
        if self.file_complete:
            raw = (m.PACKET / 'synthetic.xml').read_bytes()
            data.update(size=len(raw), checksum='md5:' + hashlib.md5(raw).hexdigest())
        return data

    def transport(self, method, url, body, headers, **options):
        self.calls.append((method, url))
        state = m.load(self.stage / 'state.json')
        journal = m.load(self.stage / 'journal.json')
        self.assertEqual(journal['state_sha256'], m.sha((self.stage / 'state.json').read_bytes()))
        self.assertEqual(journal['counts'], state['counts'])
        action = state['pending']['kind']
        self.assertGreater(state['counts'][action], 0)
        self.assertEqual(headers['Authorization'], 'Bearer ' + TOKEN)
        self.assertEqual(headers['Accept'], m.ACCEPT)
        self.assertEqual(options, {'timeout': 20, 'allow_redirects': False, 'verify': True, 'stream': True})
        if action == 'create':
            self.assertIsNone(state['identity'])
            self.assertEqual(body, m.load(m.PACKET / 'create.json'))
            if self.mutate == 'uncertain':
                raise RuntimeError('PRIVATE ' + TOKEN)
            if self.mutate == 'interrupt':
                raise KeyboardInterrupt('PRIVATE ' + TOKEN)
            if self.mutate == '500':
                return Response({'message': 'Internal server error token=' + TOKEN, 'owner': OWNER}, 500)
            if self.mutate == 'redirect':
                return Response({}, 301, {'Location': 'https://evil.test/' + TOKEN})
            if self.mutate == 'oversize':
                return Response(b'a' * 65537, 201)
            if self.reserved_on_create:
                self.remote['pids'] = {'doi': {'identifier': '10.5072/zenodo.101', 'provider': 'datacite'}}
            mutations = {
                'known_id': lambda: self.remote.update(id='3'),
                'integer_id': lambda: self.remote.update(id=101),
                'owner': lambda: self.remote['parent']['access']['owned_by'].update(user='99'),
                'owner_array': lambda: self.remote['parent']['access'].update(owned_by=[{'user': '42'}]),
                'published': lambda: self.remote.update(is_published=True),
                'newversion': lambda: self.remote['versions'].update(index=2),
                'old_created': lambda: self.remote.update(created='2020-01-01T00:00:00+00:00'),
                'future_created': lambda: self.remote.update(created=(self.clock + timedelta(seconds=6)).isoformat()),
                'validation_errors': lambda: self.remote.update(errors=[{'field': 'metadata'}]),
                'namespace': lambda: self.remote['metadata'].update(keywords=['other-run']),
                'crosshost': lambda: self.remote['links'].update(self='https://evil.test/api/records/101/draft'),
                'wrongroute': lambda: self.remote['links'].update(files=m.ORIGIN + '/api/records/102/draft/files'),
                'credential': lambda: self.remote.update(private=TOKEN),
            }
            if self.mutate in mutations:
                mutations[self.mutate]()
            return Response(self.remote, 201)
        self.assertEqual(state['identity']['id'], '101')
        if action == 'doi':
            self.remote['pids'] = {'doi': {'identifier': '10.5072/zenodo.101', 'provider': 'datacite'}}
            return Response(self.remote, 201)
        if action == 'metadata':
            self.assertEqual(body['pids'], self.remote['pids'])
            self.remote['metadata'] = deepcopy(body['metadata'])
            self.assertEqual(state['identity']['doi'], self.remote['pids']['doi'])
            return Response(self.remote)
        if action == 'init':
            self.assertEqual(body, [{'key': m.packet()['file_key']}])
            return Response({'entries': [self.file()]}, 201)
        if action == 'content':
            self.assertEqual(body, (m.PACKET / 'synthetic.xml').read_bytes())
            self.assertEqual(headers['Content-Type'], 'application/octet-stream')
            return Response(self.file())
        if action == 'commit':
            if self.mutate == 'commit500':
                return Response({'message': 'Internal server error'}, 500)
            self.file_complete = True
            raw = (m.PACKET / 'synthetic.xml').read_bytes()
            self.remote['files'].update(count=1, total_bytes=len(raw), entries={m.packet()['file_key']: {
                'key': m.packet()['file_key'], 'size': len(raw), 'checksum': 'md5:' + hashlib.md5(raw).hexdigest()}})
            return Response(self.file())
        if action == 'get':
            if self.mutate == 'readback_checksum' and url.endswith('/content'):
                return Response(b'changed bytes')
            if self.mutate == 'readback_doi':
                self.remote['pids']['doi']['identifier'] = '10.5072/zenodo.102'
            if url.endswith('/content'):
                return Response((m.PACKET / 'synthetic.xml').read_bytes(), headers={'Content-Type': 'application/xml'})
            if url.endswith('/files'):
                return Response({'entries': [self.file()]})
            if url.endswith('.xml'):
                return Response(self.file())
            return Response(self.remote)
        self.fail('Unapproved transport action')

    def controller(self):
        return m.Controller(self.stage, TOKEN, self.transport, lambda: self.clock)

    def test_complete_durable_identity_readback_and_unchanged_retry(self):
        result = self.controller().run()
        self.assertTrue(result['completed'])
        self.assertEqual(result['counts'], {**m.LIMITS, 'get': 4})
        self.assertEqual(len(self.calls), 10)
        first = len(self.calls)
        result = self.controller().run(retry=True)
        self.assertTrue(result['unchanged_retry'])
        self.assertEqual(result['counts'], m.LIMITS)
        self.assertEqual([method for method, _ in self.calls[first:]], ['GET'] * 4)
        self.assertEqual(len(self.calls), 14)
        with self.assertRaises(m.Held):
            self.controller().run(retry=True)
        self.assertEqual(len(self.calls), 14)
        self.assertNotIn(TOKEN, json.dumps(result))

    def test_create_reserved_doi_skips_reservation_without_expanding_budget(self):
        self.reserved_on_create = True
        result = self.controller().run()
        self.assertTrue(result['completed'])
        self.assertEqual(result['counts']['doi'], 0)
        self.assertEqual(len(self.calls), 9)

    def test_bounded_create_clock_skew_is_bound_once(self):
        self.remote['created'] = (self.clock - timedelta(seconds=4)).isoformat()
        result = self.controller().run()
        self.assertTrue(result['completed'])
        state = m.load(self.stage / 'state.json')
        self.assertEqual(state['create_started_at'], self.clock.isoformat())
        self.assertEqual(state['create_received_at'], self.clock.isoformat())
        self.assertEqual(state['identity']['created'], self.remote['created'])

    def test_malformed_existing_doi_or_semantic_metadata_never_falls_back(self):
        for mutation in ('doi_null', 'doi_private', 'doi_client', 'doi_external', 'creator_role',
                         'creator_family', 'resource_subtype', 'errors_dict', 'bool_version', 'bool_count'):
            with self.subTest(mutation=mutation):
                self.setUp()
                doi = {'identifier': '10.5072/zenodo.101', 'provider': 'datacite'}
                self.remote['pids'] = {'doi': doi}
                if mutation == 'doi_null':
                    self.remote['pids']['doi'] = None
                if mutation == 'doi_private':
                    doi['private'] = {'encoded_token': 'PRIVATE'}
                if mutation == 'doi_client':
                    doi['client'] = 'external'
                if mutation == 'doi_external':
                    doi['provider'] = 'external'
                if mutation == 'creator_role':
                    self.remote['metadata']['creators'][0]['role'] = {'id': 'editor'}
                if mutation == 'creator_family':
                    self.remote['metadata']['creators'][0]['person_or_org']['family_name'] = 'Another name'
                if mutation == 'resource_subtype':
                    self.remote['metadata']['resource_type']['subtype'] = 'Another type'
                if mutation == 'errors_dict':
                    self.remote['errors'] = {}
                if mutation == 'bool_version':
                    self.remote['versions']['index'] = True
                if mutation == 'bool_count':
                    self.remote['files']['count'] = False
                with self.assertRaises(m.Held):
                    self.controller().run()
                self.assertEqual(len(self.calls), 1)
                self.assertEqual(m.load(self.stage / 'state.json')['counts']['doi'], 0)
                self.assertNotIn('encoded_token', (self.stage / 'state.json').read_text())

    def test_all_six_mutation_uncertainties_remain_durably_held(self):
        for kind in ('create', 'doi', 'metadata', 'init', 'content', 'commit'):
            with self.subTest(kind=kind):
                self.setUp()
                base = self.transport
                def transport(*args, kind=kind, base=base, **kwargs):
                    current = m.load(self.stage / 'state.json')
                    if current['pending']['kind'] == kind:
                        self.calls.append((args[0], args[1]))
                        self.assertEqual(current['counts'][kind], 1)
                        raise RuntimeError('PRIVATE ' + TOKEN)
                    return base(*args, **kwargs)
                self.transport = transport
                with self.assertRaises(m.Held):
                    self.controller().run()
                state = m.load(self.stage / 'state.json')
                self.assertTrue(state['failed'])
                self.assertEqual(state['pending']['kind'], kind)
                self.assertEqual(state['counts'][kind], 1)
                before = len(self.calls)
                with self.assertRaises(m.Held):
                    self.controller().run()
                self.assertEqual(len(self.calls), before)

    def test_doi_envelope_and_file_mutations_stop_without_extra_write(self):
        for mutation in ('parent', 'created', 'owner', 'metadata', 'pidonly', 'transfer', 'key', 'link', 'checksum'):
            with self.subTest(mutation=mutation):
                self.setUp()
                base = self.transport
                def transport(*args, mutation=mutation, base=base, **kwargs):
                    result = base(*args, **kwargs)
                    action = m.load(self.stage / 'state.json')['pending']['kind']
                    data = json.loads(result.raw)
                    if action == 'doi':
                        if mutation == 'parent':
                            data['parent']['id'] = '999'
                        if mutation == 'created':
                            data['created'] = (self.clock - timedelta(seconds=1)).isoformat()
                        if mutation == 'owner':
                            data['parent']['access']['owned_by']['user'] = '999'
                        if mutation == 'metadata':
                            data['metadata']['title'] = 'Different title'
                        if mutation == 'pidonly':
                            data = {'pids': data['pids']}
                    if action == 'init':
                        if mutation == 'transfer':
                            data['entries'][0]['transfer']['type'] = 'fetch'
                        if mutation == 'key':
                            data['entries'][0]['key'] = 'other.xml'
                        if mutation == 'link':
                            data['entries'][0]['links']['content'] += '?access_token=PRIVATE'
                    if action == 'commit' and mutation == 'checksum':
                        data['checksum'] = 'md5:' + '0' * 32
                    return Response(data, result.status_code, result.headers)
                self.transport = transport
                with self.assertRaises(m.Held):
                    self.controller().run()
                state = m.load(self.stage / 'state.json')
                self.assertTrue(state['failed'])
                if mutation in ('parent', 'created', 'owner', 'metadata', 'pidonly'):
                    self.assertEqual(len(self.calls), 2)
                    self.assertEqual(state['counts']['metadata'], 0)
                else:
                    self.assertEqual(state['counts']['get'], 0)

    def test_partial_and_timeout_body_retains_only_safe_available_evidence(self):
        for mutation in ('oversize', 'timeout'):
            with self.subTest(mutation=mutation):
                self.setUp()
                def transport(*args, mutation=mutation, **kwargs):
                    self.calls.append((args[0], args[1]))
                    response = Response(b'<title>Service unavailable</title>' + b'x' * 70000, 500,
                                        {'Content-Type': 'text/html', 'X-Request-ID': 'a' * 32})
                    if mutation == 'timeout':
                        def chunks(chunk_size):
                            yield b'<title>Service unavailable</title>'
                            raise TimeoutError('PRIVATE ' + TOKEN)
                        response.iter_content = chunks
                    return response
                self.transport = transport
                with self.assertRaises(m.Held):
                    self.controller().run()
                state = m.load(self.stage / 'state.json')
                last = state['responses'][-1]
                self.assertFalse(last['body_complete'])
                self.assertEqual(last['error_message'], 'Service unavailable')
                self.assertEqual(last['trace_identifiers'], {'x-request-id': 'a' * 32})
                self.assertNotIn(TOKEN, json.dumps(state))

    def test_expiry_between_requests_stops_before_next_transport(self):
        base = self.transport
        def transport(*args, **kwargs):
            response = base(*args, **kwargs)
            self.clock += timedelta(minutes=30)
            return response
        self.transport = transport
        with self.assertRaises(m.Held):
            self.controller().run()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(m.load(self.stage / 'state.json')['counts']['create'], 1)

    def test_expiry_during_durable_intent_stops_before_transport(self):
        controller = self.controller()
        original = controller.persist
        def persist():
            original()
            self.clock += timedelta(minutes=30)
        controller.persist = persist
        with self.assertRaises(m.Held):
            controller.run()
        self.assertEqual(self.calls, [])
        state = m.load(self.stage / 'state.json')
        self.assertTrue(state['failed'])
        self.assertEqual(state['counts']['create'], 1)

    def test_failures_spend_create_and_never_retry_or_reset(self):
        for mutation in ('uncertain', 'interrupt', '500', 'redirect', 'oversize', 'known_id', 'integer_id',
                         'owner', 'owner_array', 'published', 'newversion', 'old_created', 'future_created',
                         'validation_errors', 'namespace', 'crosshost', 'wrongroute', 'credential'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.mutate = mutation
                with self.assertRaises(m.Held) as caught:
                    self.controller().run()
                self.assertNotIn(TOKEN, str(caught.exception))
                state = m.load(self.stage / 'state.json')
                self.assertTrue(state['failed'])
                self.assertEqual(state['counts']['create'], 1)
                self.assertEqual(sum(state['counts'].values()), 1)
                before = (self.stage / 'state.json').read_bytes()
                with self.assertRaises(m.Held):
                    self.controller().run()
                self.assertEqual(len(self.calls), 1)
                self.assertEqual((self.stage / 'state.json').read_bytes(), before)
                self.assertNotIn(TOKEN, json.dumps(state))

    def test_echoed_create_retains_only_safe_reconciliation_id_and_stays_held(self):
        self.mutate = 'credential'
        controller = self.controller()
        with self.assertRaises(m.Held):
            controller.run()
        state = m.load(self.stage / 'state.json')
        self.assertEqual(state['uncertain_candidate_id'], '101')
        self.assertIsNone(state['identity'])
        self.assertTrue(state['failed'])
        self.assertEqual(state['pending']['kind'], 'create')
        self.assertEqual(state['counts'], {**dict.fromkeys(m.LIMITS, 0), 'create': 1})
        self.assertNotIn(TOKEN, json.dumps(state))
        self.assertNotIn('uncertain_candidate_id', controller.receipt())
        before = (self.stage / 'state.json').read_bytes()
        with self.assertRaises(m.Held):
            self.controller().run()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((self.stage / 'state.json').read_bytes(), before)

    def test_create_id_that_contains_credential_is_not_persisted(self):
        def transport(*args, **kwargs):
            self.calls.append((args[0], args[1]))
            return Response(self.remote, 201)
        controller = m.Controller(self.stage, '101', transport, lambda: self.clock)
        with self.assertRaises(m.Held):
            controller.run()
        state = m.load(self.stage / 'state.json')
        self.assertIsNone(state['uncertain_candidate_id'])
        self.assertIsNone(state['identity'])
        self.assertTrue(state['failed'])
        self.assertEqual(len(self.calls), 1)

    def test_readback_and_commit_uncertainty_never_issue_more_writes(self):
        for mutation in ('commit500', 'readback_checksum', 'readback_doi'):
            with self.subTest(mutation=mutation):
                self.setUp()
                self.mutate = mutation
                with self.assertRaises(m.Held):
                    self.controller().run()
                state = m.load(self.stage / 'state.json')
                self.assertTrue(state['failed'])
                self.assertEqual(state['counts']['commit'], 1)
                self.assertEqual(state['identity']['id'], '101')
                before = len(self.calls)
                with self.assertRaises(m.Held):
                    self.controller().run()
                self.assertEqual(len(self.calls), before)

    def test_missing_changed_or_expired_approval_blocks_before_requests(self):
        for mutation in ('missing', 'changed_limits', 'expired', 'unapproved', 'runtime', 'stage', 'executor'):
            with self.subTest(mutation=mutation):
                self.setUp()
                if mutation == 'missing':
                    (self.stage / 'approval.json').unlink()
                else:
                    grant = deepcopy(self.grant)
                    if mutation == 'changed_limits':
                        grant['limits'] = {**m.LIMITS, 'create': 2}
                    if mutation == 'expired':
                        self.clock += timedelta(minutes=30)
                    if mutation == 'unapproved':
                        grant['approved'] = False
                    if mutation == 'runtime':
                        grant['binding']['runtime_sha256']['modern_synthetic_canary.py'] = '0' * 64
                    if mutation == 'stage':
                        grant['binding']['stage'] = '/tmp/other'
                    if mutation == 'executor':
                        grant['executor'] = 'another-writer'
                    m.atomic(self.stage / 'approval.json', grant)
                with self.assertRaises(m.Held):
                    self.controller()
                self.assertEqual(self.calls, [])

    def test_missing_journal_or_state_and_interrupted_intent_fail_closed(self):
        for mutation in ('missing_state', 'missing_journal', 'changed_state', 'pending'):
            with self.subTest(mutation=mutation):
                self.setUp()
                if mutation.startswith('missing'):
                    (self.stage / ('state.json' if mutation == 'missing_state' else 'journal.json')).unlink()
                else:
                    state = m.load(self.stage / 'state.json')
                    state['counts']['create'] = 1
                    state['pending'] = {'kind': 'create'}
                    if mutation == 'pending':
                        m.save(self.stage, state)
                    else:
                        m.atomic(self.stage / 'state.json', state)
                with self.assertRaises(m.Held):
                    self.controller()
                self.assertEqual(self.calls, [])

    def test_packet_stage_symlink_hardlink_and_extra_file_fail_closed(self):
        for mutation in ('payload', 'symlink', 'hardlink', 'extra'):
            with self.subTest(mutation=mutation):
                self.setUp()
                file = self.stage / 'synthetic.xml'
                if mutation == 'payload':
                    file.write_bytes(b'changed')
                if mutation == 'symlink':
                    file.unlink()
                    file.symlink_to(m.PACKET / 'synthetic.xml')
                if mutation == 'hardlink':
                    os.link(file, Path(self.temp.name) / 'linked')
                if mutation == 'extra':
                    m.atomic(self.stage / 'another-ledger.json', {})
                with self.assertRaises(m.Held):
                    self.controller()
                self.assertEqual(self.calls, [])

    def test_no_stage_reset_old_state_or_production_paths(self):
        old = Path(self.temp.name) / 'old-failed-controller.json'
        old.write_bytes(b'{"create":1,"failed":true,"gets":190}')
        original = old.read_bytes()
        with self.assertRaises(FileExistsError):
            m.stage_packet(self.stage)
        with self.assertRaises(m.Held):
            m.stage_packet(Path(self.temp.name) / 'production')
        self.controller().run()
        self.assertEqual(old.read_bytes(), original)

    def test_live_transport_configuration_is_mocked_and_locked(self):
        # Exercise real requests configuration, while mocking its only send boundary.
        now = datetime.now(timezone.utc)
        self.grant['started_at'] = now.isoformat()
        self.grant['valid_until'] = (now + timedelta(minutes=30)).isoformat()
        m.atomic(self.stage / 'approval.json', self.grant)
        def send(session, request, **kwargs):
            self.assertFalse(session.trust_env)
            self.assertFalse(kwargs['allow_redirects'])
            self.assertTrue(kwargs['verify'])
            self.assertEqual(request.url, m.ORIGIN + '/api/records')
            return Response({'message': 'Internal server error'}, 500)
        with patch('requests.sessions.Session.send', send), self.assertRaises(m.Held):
            m.execute(self.stage, TOKEN)
        self.assertEqual(m.load(self.stage / 'state.json')['counts']['create'], 1)


if __name__ == '__main__':
    unittest.main()
