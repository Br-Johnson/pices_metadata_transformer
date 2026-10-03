"""Offline boundary evidence: no real sockets, provider stage or credential input."""
import contextlib
import io
import json
import sys
import threading
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import requests

from scripts import modern_synthetic_canary as m
from tests import test_modern_synthetic_canary as fixtures

TOKEN = fixtures.TOKEN
Response = fixtures.Response


class ModernTransportDiagnosticTests(unittest.TestCase):
    setUp = fixtures.ModernCanaryTests.setUp

    def live_fixture(self):
        now = datetime.now(timezone.utc)
        self.grant.update(started_at=now.isoformat(), valid_until=(now + timedelta(minutes=30)).isoformat())
        m.atomic(self.stage / 'approval.json', self.grant)

    def held(self, invoke):
        with self.assertRaises(m.Held) as caught:
            invoke()
        state = m.load(self.stage / 'state.json')
        self.assertEqual(state['counts']['create'], 1)
        self.assertTrue(state['failed'])
        self.assertEqual(state['pending']['kind'], 'create')
        self.assertIsNone(state['identity'])
        self.assertEqual(caught.exception.diagnostic, state['attempt_diagnostics'][-1])
        self.assertIsNotNone(datetime.fromisoformat(state['attempt_diagnostics'][-1]['failure']['captured_at']).tzinfo)
        self.assertEqual(m.load(self.stage / 'journal.json')['state_sha256'], m.sha((self.stage / 'state.json').read_bytes()))
        return state['attempt_diagnostics'][-1]

    def test_preparation_failure_proves_no_send_and_redacts_cli(self):
        self.live_fixture()
        failure = requests.exceptions.InvalidHeader('Bearer ' + TOKEN + ' https://private.test/path')
        with patch('requests.sessions.Session.prepare_request', side_effect=failure), \
                patch('requests.sessions.Session.send') as send:
            diagnostic = self.held(lambda: m.execute(self.stage, TOKEN))
            send.assert_not_called()
        self.assertEqual(diagnostic['failure']['phase'], 'request_preparation')
        self.assertEqual(diagnostic['failure']['exception'], 'invalid_header')
        self.assertFalse(diagnostic['send_call_started'])
        self.assertFalse(diagnostic['adapter_entered'])
        self.assertFalse(diagnostic['response_seen'])
        output = io.StringIO()
        safe = m.Held('fixed', diagnostic)
        with patch.object(sys, 'argv', ['canary', 'execute', '--stage', str(self.stage)]), \
                patch.object(m, 'execute', side_effect=safe), contextlib.redirect_stdout(output):
            self.assertEqual(m.main(), 1)
        self.assertEqual(json.loads(output.getvalue())['diagnostic'], diagnostic)
        self.assertNotIn(TOKEN, output.getvalue())
        self.assertNotIn('private.test', output.getvalue())

    def test_adapter_failure_is_evidence_of_entry_not_transmission(self):
        self.live_fixture()
        failure = requests.exceptions.ConnectionError('Bearer ' + TOKEN)
        def dispatch(session, request, **options):
            # Allow only this in-memory adapter fixture under the suite's send guard.
            return session.get_adapter(request.url).send(request, **options)
        with patch('requests.sessions.Session.send', dispatch), \
                patch('requests.adapters.HTTPAdapter.send', side_effect=failure) as send:
            diagnostic = self.held(lambda: m.execute(self.stage, TOKEN))
            self.assertEqual(send.call_count, 1)
        self.assertTrue(diagnostic['send_call_started'])
        self.assertTrue(diagnostic['adapter_entered'])
        self.assertFalse(diagnostic['response_seen'])
        self.assertEqual(diagnostic['failure']['phase'], 'adapter_entry')
        self.assertEqual(diagnostic['failure']['exception'], 'connection_error')
        with patch('requests.sessions.Session.send') as send, self.assertRaises(m.Held):
            m.execute(self.stage, TOKEN)
        send.assert_not_called()

    def test_non_main_thread_signal_setup_and_cleanup_are_safe(self):
        self.live_fixture()
        caught = []
        def run():
            try:
                m.execute(self.stage, TOKEN)
            except m.Held as error:
                caught.append(error)
        with patch('requests.sessions.Session.send') as send:
            thread = threading.Thread(target=run)
            thread.start()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            send.assert_not_called()
        self.assertEqual(len(caught), 1)
        diagnostic = caught[0].diagnostic
        self.assertEqual(diagnostic['failure']['phase'], 'deadline_setup')
        self.assertEqual(diagnostic['failure']['exception'], 'value_error')
        self.assertEqual(diagnostic['cleanup_failure']['phase'], 'deadline_cleanup')
        self.assertEqual(diagnostic['cleanup_failure']['exception'], 'value_error')
        self.assertFalse(diagnostic['send_call_started'])

    def test_projection_failure_preserves_observed_http_status(self):
        self.live_fixture()
        response = Response({'message': 'Internal server error'}, 500)
        with patch('requests.sessions.Session.send', return_value=response), \
                patch.object(m, 'response_projection', side_effect=RuntimeError(TOKEN)):
            diagnostic = self.held(lambda: m.execute(self.stage, TOKEN))
        self.assertTrue(diagnostic['response_seen'])
        self.assertEqual(diagnostic['status'], 500)
        self.assertEqual(diagnostic['failure']['phase'], 'response_projection')
        self.assertEqual(diagnostic['failure']['exception'], 'unclassified')
        self.assertEqual(m.load(self.stage / 'state.json')['responses'], [])
        self.assertTrue(response.closed)

    def test_status_decode_and_close_failures_keep_first_failure(self):
        for mode in ('status', 'decode', 'close'):
            with self.subTest(mode=mode):
                self.setUp()
                self.live_fixture()
                response = Response(b'not-json', 500 if mode == 'status' else 201)
                if mode == 'close':
                    response.close = lambda: (_ for _ in ()).throw(OSError(TOKEN))
                with patch('requests.sessions.Session.send', return_value=response):
                    diagnostic = self.held(lambda: m.execute(self.stage, TOKEN))
                self.assertEqual(diagnostic['status'], response.status_code)
                self.assertEqual(diagnostic['failure']['phase'], 'response_validation' if mode == 'status' else 'response_decode')
                self.assertEqual(diagnostic['failure']['exception'], 'contract' if mode == 'status' else 'invalid_json')
                if mode == 'close':
                    self.assertEqual(diagnostic['cleanup_failure']['phase'], 'response_close')
                    self.assertEqual(diagnostic['cleanup_failure']['exception'], 'os_error')

    def test_alarm_failure_has_exact_deadline_category_without_send(self):
        self.live_fixture()
        handler = []
        def install(sig, callback):
            handler.append(callback)
        def arm(timer, seconds):
            if seconds:
                handler[-1](None, None)
        with patch.object(m.signal, 'signal', install), patch.object(m.signal, 'setitimer', arm), \
                patch('requests.sessions.Session.send') as send:
            diagnostic = self.held(lambda: m.execute(self.stage, TOKEN))
            send.assert_not_called()
        self.assertEqual(diagnostic['failure']['phase'], 'deadline_setup')
        self.assertEqual(diagnostic['failure']['exception'], 'wall_deadline')

    def test_unknown_exception_names_and_messages_are_never_projected(self):
        secret_exception = type(TOKEN + '_PrivateClass', (requests.exceptions.ConnectionError,), {})
        self.assertEqual(m.exception_code(secret_exception(TOKEN)), 'unclassified')
        self.assertNotIn(TOKEN, json.dumps({'exception': m.exception_code(secret_exception(TOKEN))}))

    def test_old_runtime_binding_cannot_be_migrated_or_replayed(self):
        state = m.load(self.stage / 'state.json')
        state['binding']['runtime_sha256']['modern_synthetic_canary.py'] = '0' * 64
        state['counts']['create'] = 1
        state['failed'] = True
        m.save(self.stage, state)
        before = (self.stage / 'state.json').read_bytes()
        with patch('requests.sessions.Session.send') as send, self.assertRaises(m.Held):
            m.execute(self.stage, TOKEN)
        send.assert_not_called()
        self.assertEqual((self.stage / 'state.json').read_bytes(), before)

    def test_pre_intent_expiry_does_not_relabel_previous_successful_attempt(self):
        fixture = fixtures.ModernCanaryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        controller = fixture.controller()
        acknowledged = controller.acknowledge
        previous = []
        def expire_after_create():
            acknowledged()
            if controller.state['counts']['create'] == 1:
                previous.append(deepcopy(controller.state['attempt_diagnostics']))
                fixture.clock += timedelta(minutes=31)
        controller.acknowledge = expire_after_create
        with self.assertRaises(m.Held) as caught:
            controller.run()
        state = m.load(fixture.stage / 'state.json')
        self.assertEqual(len(fixture.calls), 1)
        self.assertEqual(state['counts']['create'], 1)
        self.assertEqual(state['counts']['doi'], 0)
        self.assertIsNone(state['pending'])
        self.assertTrue(state['failed'])
        self.assertEqual(state['attempt_diagnostics'], previous[0])
        self.assertNotIn('failure', state['attempt_diagnostics'][0])
        self.assertEqual(state['controller_failure']['phase'], 'outside_pending_attempt')
        self.assertEqual(state['controller_failure']['exception'], 'contract')
        self.assertEqual(caught.exception.diagnostic, {'controller_failure': state['controller_failure']})


if __name__ == '__main__':
    unittest.main()
