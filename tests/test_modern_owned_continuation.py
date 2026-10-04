"""Owned recovery has no create, no old-state reset, and strict post-PUT gates."""

import json
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import modern_owned_continuation as r
from scripts import modern_synthetic_canary as m
from tests import test_modern_synthetic_canary as fixture


class OwnedContinuationTests(fixture.unittest.TestCase):
    file = fixture.ModernCanaryTests.file

    def setUp(self):
        fixture.ModernCanaryTests.setUp(self)
        self.original_stage = self.stage
        self.original_grant = deepcopy(self.grant)
        self.remote['metadata'] = {}
        self.remote['access']['files'] = 'public'
        with self.assertRaises(m.Held):
            m.Controller(self.original_stage, fixture.TOKEN,
                         lambda *a, **k: fixture.Response(self.remote, 201), lambda: self.clock).run()
        original_state = m.load(self.original_stage / 'state.json')
        original_state['attempt_diagnostics'][0].update(send_call_started=True, adapter_entered=True)
        m.save(self.original_stage, original_state)
        self.beforeimage = Path(self.temp.name) / 'beforeimage.json'
        self.diagnostics = Path(self.temp.name) / 'diagnostics.json'
        m.atomic(self.beforeimage, self.remote)
        m.atomic(self.diagnostics, {'status': 200, 'identity_matches': True, 'get_intents': 1})
        for name, value in [('ORIGINAL_RUNTIME', m.runtime_binding()),
                            ('CREATE_RESPONSE_SHA', original_state['responses'][0]['body_sha256']),
                            ('BEFOREIMAGE_SHA', m.sha(self.beforeimage.read_bytes())),
                            ('DIAGNOSTICS_SHA', m.sha(self.diagnostics.read_bytes()))]:
            mocked = patch.object(r, name, value)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.stage = Path(self.temp.name) / r.NAMESPACE
        self.old_snapshot = {p.name: p.read_bytes() for p in self.original_stage.iterdir()}
        r.stage_packet(self.stage, self.original_stage, self.beforeimage, self.diagnostics, fixture.TOKEN)
        self.clock += timedelta(minutes=35)
        self.grant = {'schema_version': 1, 'approved': True,
                      'approval_reference': 'OFFLINE SEPARATE CONTINUATION FIXTURE',
                      'executor': m.EXECUTOR, 'binding': r.binding(self.stage), 'limits': m.LIMITS,
                      'started_at': self.clock.isoformat(),
                      'valid_until': (self.clock + timedelta(minutes=30)).isoformat(),
                      'owner': fixture.OWNER, 'known_ids': self.original_grant['known_ids'],
                      'window_mode': 'specifically_authorized_continuation_window',
                      'original_valid_until': self.original_grant['valid_until'],
                      'existing_candidate_only': True, 'no_create_or_reset': True,
                      'additional_get_limit': 6,
                      'preserved_file_inventory': {'count': 305, 'sha256': 'a' * 64}}
        m.atomic(self.stage / 'approval.json', self.grant)
        self.calls = []
        self.mutate = None

    def controller(self):
        return r.Controller(self.stage, fixture.TOKEN, self.transport, lambda: self.clock)

    def transport(self, method, url, body, headers, **options):
        state = m.load(self.stage / 'state.json')
        action = state['pending']['kind']
        self.assertNotEqual(action, 'create')
        self.assertEqual(m.load(self.stage / 'journal.json')['state_sha256'], m.sha((self.stage / 'state.json').read_bytes()))
        self.assertEqual(headers['Authorization'], 'Bearer ' + fixture.TOKEN)
        self.assertFalse(options['allow_redirects'])
        self.assertTrue(options['verify'])
        self.calls.append((method, url))
        if action == 'metadata':
            self.assertEqual(method, 'PUT')
            self.assertNotIn('pids', body)
            if self.mutate == 'uncertain':
                raise RuntimeError('PRIVATE ' + fixture.TOKEN)
            if self.mutate == 'redirect':
                return fixture.Response({}, 301, {'Location': 'https://evil.test/' + fixture.TOKEN})
            self.remote['metadata'] = deepcopy(body['metadata'])
            self.remote['access'] = deepcopy(body['access'])
            if self.mutate == 'metadata':
                self.remote['metadata'] = {}
            elif self.mutate == 'access':
                self.remote['access']['files'] = 'public'
            elif self.mutate == 'owner':
                self.remote['parent']['access']['owned_by']['user'] = '99'
            elif self.mutate == 'credential':
                self.remote['metadata']['description'] = fixture.TOKEN
            elif self.mutate == 'aggregate':
                self.remote['files']['count'] = True
            elif self.mutate == 'doi_on_put':
                self.remote['pids'] = {'doi': {'identifier': '10.5072/zenodo.101', 'provider': 'datacite'}}
            return fixture.Response(self.remote)
        if action == 'doi':
            self.remote['pids'] = {'doi': {'identifier': '10.5072/zenodo.101', 'provider': 'datacite'}}
            return fixture.Response(self.remote, 201)
        if action == 'init':
            return fixture.Response({'entries': [self.file()]}, 201)
        if action == 'content':
            self.assertEqual(body, (m.PACKET / 'synthetic.xml').read_bytes())
            return fixture.Response(self.file())
        if action == 'commit':
            self.file_complete = True
            content = (m.PACKET / 'synthetic.xml').read_bytes()
            entry = self.file()
            self.remote['files'].update(count=1, total_bytes=len(content), entries={self.key(): entry})
            return fixture.Response(entry)
        if action == 'get':
            if url.endswith('/content'):
                return fixture.Response(b'wrong' if self.mutate == 'bytes' else (m.PACKET / 'synthetic.xml').read_bytes())
            if url.endswith('/files'):
                entry = self.file()
                if self.mutate == 'list_missing_checksum':
                    entry.pop('checksum')
                return fixture.Response({'entries': [entry]})
            return fixture.Response(self.remote)
        self.fail('Unapproved recovery route')

    def key(self):
        return m.packet()['file_key']

    def test_complete_recovery_then_read_only_retry_keeps_all_lifetime_counts(self):
        result = self.controller().run()
        self.assertTrue(result['completed'])
        self.assertEqual(result['counts'], {**m.LIMITS, 'get': 4})
        self.assertEqual(len(self.calls), 8)
        self.assertEqual(self.calls[0], ('PUT', m.ORIGIN + '/api/records/101/draft'))
        result = self.controller().run(True)
        self.assertTrue(result['unchanged_retry'])
        self.assertEqual(result['counts']['get'], 7)
        self.assertEqual(result['historical_get_intents'], 202)
        self.assertEqual(result['additional_provider_intents'], 11)
        self.assertEqual([method for method, _ in self.calls[-3:]], ['GET'] * 3)
        self.assertEqual(self.old_snapshot, {p.name: p.read_bytes() for p in self.original_stage.iterdir()})
        self.assertFalse(any(method == 'POST' and url == m.ORIGIN + '/api/records' for method, url in self.calls))
        self.assertNotIn(fixture.TOKEN, json.dumps(result))

    def test_doi_supplied_on_put_leaves_allocation_unused(self):
        self.mutate = 'doi_on_put'
        result = self.controller().run()
        self.assertEqual(result['counts']['doi'], 0)
        self.assertEqual(len(self.calls), 7)

    def test_bad_put_stops_before_any_upload_and_keeps_failure_spent(self):
        for mutation in ('metadata', 'access', 'owner', 'credential', 'aggregate', 'redirect', 'uncertain'):
            with self.subTest(mutation=mutation):
                if self.calls:
                    self.setUp()
                self.mutate = mutation
                with self.assertRaises(m.Held):
                    self.controller().run()
                state = m.load(self.stage / 'state.json')
                self.assertTrue(state['failed'])
                self.assertEqual(state['counts']['metadata'], 1)
                self.assertEqual(state['counts']['init'], 0)
                self.assertEqual(state['counts']['get'], 1)
                self.assertEqual(len(self.calls), 1)
                with self.assertRaises(m.Held):
                    self.controller()
                self.assertEqual(self.old_snapshot, {p.name: p.read_bytes() for p in self.original_stage.iterdir()})
                self.assertNotIn(fixture.TOKEN, json.dumps(state))

    def test_incomplete_file_list_or_changed_bytes_hold_without_detail_fallback(self):
        for mutation in ('list_missing_checksum', 'bytes'):
            with self.subTest(mutation=mutation):
                if self.calls:
                    self.setUp()
                self.mutate = mutation
                with self.assertRaises(m.Held):
                    self.controller().run()
                self.assertTrue(m.load(self.stage / 'state.json')['failed'])
                self.assertFalse(any(url.endswith('.xml') for _, url in self.calls))

    def test_grant_cannot_silently_extend_original_expiry_or_replenish_reads(self):
        mutations = {'approved': False, 'window_mode': 'original_window', 'additional_get_limit': 7,
                     'original_valid_until': self.clock.isoformat(), 'no_create_or_reset': False,
                     'owner': 99, 'known_ids': [], 'preserved_file_inventory': {'count': 288, 'sha256': 'a' * 64}}
        for key, value in mutations.items():
            grant = deepcopy(self.grant)
            grant[key] = value
            m.atomic(self.stage / 'approval.json', grant)
            with self.subTest(key=key), self.assertRaises(m.Held):
                self.controller()
            self.assertEqual(self.calls, [])
        m.atomic(self.stage / 'approval.json', self.grant)
        self.controller()
        with self.assertRaises(m.Held):
            r.stage_packet(self.stage, self.original_stage, self.beforeimage, self.diagnostics, fixture.TOKEN)

    def test_identity_predicates_and_sealed_origin_are_not_relaxed(self):
        original = m.load(self.stage / 'beforeimage.json')
        for kind in ('owner', 'published', 'version', 'metadata', 'files', 'link', 'created'):
            image = deepcopy(original)
            if kind == 'owner':
                image['parent']['access']['owned_by']['user'] = '99'
            elif kind == 'published':
                image['is_published'] = True
            elif kind == 'version':
                image['versions']['index'] = 2
            elif kind == 'metadata':
                image['metadata'] = {'title': 'Another draft'}
            elif kind == 'files':
                image['files']['count'] = 1
            elif kind == 'link':
                image['links']['self'] = 'https://evil.test/'
            else:
                image['created'] = '2020-01-01T00:00:00Z'
            m.atomic(self.stage / 'beforeimage.json', image)
            with patch.object(r, 'BEFOREIMAGE_SHA', m.sha((self.stage / 'beforeimage.json').read_bytes())):
                m.atomic(self.stage / 'binding.json', r.binding(self.stage))
                state = m.load(self.stage / 'state.json')
                state['binding'] = r.binding(self.stage)
                m.save(self.stage, state)
                grant = deepcopy(self.grant)
                grant['binding'] = r.binding(self.stage)
                m.atomic(self.stage / 'approval.json', grant)
                with self.subTest(kind=kind), self.assertRaises(m.Held):
                    self.controller()
        self.assertEqual(self.calls, [])

    def test_fixed_metadata_diagnostics_never_emit_private_values_or_unknown_keys(self):
        expected = m.load(m.PACKET / 'metadata-put.json')
        checks = r.metadata_diagnostics({'metadata': {}, 'access': {'files': 'public', 'record': 'public'},
                                         fixture.TOKEN: {'private': fixture.TOKEN}}, expected)
        self.assertFalse(checks['title_present'])
        self.assertEqual(checks['title_type'], 'missing')
        self.assertFalse(checks['access_files_matches'])
        self.assertTrue(checks['access_record_matches'])
        self.assertNotIn(fixture.TOKEN, json.dumps(checks))
        checks = r.metadata_diagnostics(expected, expected)
        self.assertTrue(checks['metadata_contract_matches'])

    def test_nested_destination_is_rejected_before_touching_original_stage(self):
        nested = self.original_stage / r.NAMESPACE
        with self.assertRaises(m.Held):
            r.stage_packet(nested, self.original_stage, self.beforeimage, self.diagnostics, fixture.TOKEN)
        self.assertFalse(nested.exists())
        self.assertEqual(self.old_snapshot, {p.name: p.read_bytes() for p in self.original_stage.iterdir()})

    def test_original_window_clips_dispatch_and_expiry_spends_no_action(self):
        self.clock -= timedelta(minutes=20)
        grant = deepcopy(self.grant)
        grant['window_mode'] = 'original_window'
        grant['started_at'] = self.clock.isoformat()
        grant['valid_until'] = self.original_grant['valid_until']
        m.atomic(self.stage / 'approval.json', grant)
        controller = self.controller()
        self.clock += timedelta(minutes=15)
        with self.assertRaises(m.Held):
            controller.run()
        state = m.load(self.stage / 'state.json')
        self.assertEqual(state['counts']['metadata'], 0)
        self.assertTrue(state['failed'])
        self.assertEqual(self.calls, [])

    def test_old_failed_non201_or_incomplete_create_cannot_be_rebound(self):
        state = m.load(self.original_stage / 'state.json')
        for mutation in ('status', 'digest', 'incomplete', 'attempt_status', 'no_response', 'wrong_phase'):
            changed = deepcopy(state)
            if mutation == 'status':
                changed['responses'][0]['status'] = 500
            elif mutation == 'digest':
                changed['responses'][0]['body_sha256'] = '0' * 64
            elif mutation == 'incomplete':
                changed['responses'][0]['body_complete'] = False
            elif mutation == 'attempt_status':
                changed['attempt_diagnostics'][0]['status'] = 500
            elif mutation == 'no_response':
                changed['attempt_diagnostics'][0]['response_seen'] = False
            else:
                changed['attempt_diagnostics'][0]['failure']['phase'] = 'credential_validation'
            m.save(self.original_stage, changed)
            target = Path(self.temp.name) / mutation / r.NAMESPACE
            with self.subTest(mutation=mutation), self.assertRaises(m.Held):
                r.stage_packet(target, self.original_stage, self.beforeimage, self.diagnostics, fixture.TOKEN)
        m.save(self.original_stage, state)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    fixture.unittest.main()
