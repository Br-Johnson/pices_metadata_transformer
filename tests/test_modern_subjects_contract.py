"""Exact modern wire subjects and safe error receipts before contract rejection."""

import json
import unittest
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch

from scripts import modern_owned_continuation as r
from scripts import modern_synthetic_canary as m
from tests import test_modern_owned_continuation as owned_fixture
from tests import test_modern_synthetic_canary as fixture


class StopBeforeAdapter(BaseException):
    pass


class ModernSubjectsContractTests(unittest.TestCase):
    def case(self, owned=False):
        case = (owned_fixture.OwnedContinuationTests('test_complete_recovery_then_read_only_retry_keeps_all_lifetime_counts')
                if owned else fixture.ModernCanaryTests('test_complete_durable_identity_readback_and_unchanged_retry'))
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def test_projection_changes_only_keyword_field_without_mutating_frozen_inputs(self):
        m.packet()
        for name in ('create.json', 'metadata-put.json'):
            source = m.load(m.PACKET / name)
            before = deepcopy(source)
            wire = m.modern_wire_payload(source)
            self.assertEqual(source, before)
            self.assertNotIn('keywords', wire['metadata'])
            self.assertEqual(wire['metadata']['subjects'], [{'subject': m.NAMESPACE}])
            restored = deepcopy(wire)
            restored['metadata'].pop('subjects')
            restored['metadata']['keywords'] = [m.NAMESPACE]
            self.assertEqual(restored, before)
            self.assertNotIn('publisher', wire['metadata'])
        self.assertEqual(m.PACKET_SHA, '0f54838bf45ebecccaf575db4145c5a51cdd01507f0aaa6e9b418aadd786db13')

    def test_shape_or_run_identity_drift_is_rejected_without_normalization(self):
        source = m.load(m.PACKET / 'create.json')
        for keywords in (None, [], ['other-run'], [m.NAMESPACE, 'extra'], m.NAMESPACE,
                         [{'subject': m.NAMESPACE}]):
            changed = deepcopy(source)
            changed['metadata']['keywords'] = keywords
            with self.subTest(keywords=keywords), self.assertRaises(m.Held):
                m.modern_wire_payload(changed)
        source['metadata']['subjects'] = [{'subject': m.NAMESPACE}]
        with self.assertRaises(m.Held):
            m.modern_wire_payload(source)

    def test_full_subject_objects_must_match_and_legacy_keyword_response_is_rejected(self):
        expected = m.modern_wire_payload(m.load(m.PACKET / 'create.json'))['metadata']
        m.validate_metadata(deepcopy(expected), expected)
        for subjects in ([], [{'subject': 'other-run'}], [{'subject': m.NAMESPACE, 'id': 'private-id'}],
                         [{'subject': m.NAMESPACE, 'scheme': 'unexpected'}], [m.NAMESPACE]):
            actual = deepcopy(expected)
            actual['subjects'] = subjects
            with self.subTest(subjects=subjects), self.assertRaises(m.Held):
                m.validate_metadata(actual, expected)
        actual = deepcopy(expected)
        actual['keywords'] = [m.NAMESPACE]
        with self.assertRaises(m.Held):
            m.validate_metadata(actual, expected)
        with self.assertRaises(m.Held):
            m.validate_metadata(m.load(m.PACKET / 'create.json')['metadata'], expected)

    def test_exact_shared_execute_prepares_corrected_post_and_put_without_adapter_calls(self):
        for owned in (False, True):
            with self.subTest(owned=owned):
                case = self.case(owned)
                expected = m.modern_wire_payload(m.load(m.PACKET / ('metadata-put.json' if owned else 'create.json')))
                captured = []

                def capture(session, prepared, _captured=captured, _expected=expected, **options):
                    decoded = json.loads(prepared.body)
                    _captured.append(decoded)
                    self.assertEqual(decoded, _expected)
                    self.assertNotIn('keywords', decoded['metadata'])
                    self.assertEqual(prepared.headers['Content-Type'], 'application/json')
                    self.assertEqual(prepared.headers['Content-Length'], str(len(prepared.body)))
                    self.assertEqual(prepared.headers['Authorization'], 'Bearer ' + fixture.TOKEN)
                    self.assertFalse(options['allow_redirects'])
                    raise StopBeforeAdapter()

                with (patch.object(m, 'datetime') as clock,
                      patch.object(r, 'datetime') as owned_clock,
                      patch('requests.sessions.Session.send', capture),
                      patch('requests.adapters.HTTPAdapter.send', side_effect=AssertionError('adapter called')) as adapter):
                    clock.now.return_value = case.clock
                    clock.fromisoformat.side_effect = datetime.fromisoformat
                    owned_clock.now.return_value = case.clock
                    with self.assertRaises(m.Held):
                        m._execute_controller(case.stage, fixture.TOKEN, r.Controller if owned else m.Controller)
                self.assertEqual(adapter.call_count, 0)
                self.assertEqual(len(captured), 1)
                state = m.load(case.stage / 'state.json')
                self.assertTrue(state['failed'])
                self.assertEqual(state['counts']['metadata' if owned else 'create'], 1)
                if owned:
                    self.assertEqual(case.old_snapshot, {p.name: p.read_bytes() for p in case.original_stage.iterdir()})

    def test_success_status_and_http400_validation_flags_survive_failure_before_followup(self):
        for owned, status in ((False, 201), (True, 200), (True, 400)):
            with self.subTest(owned=owned, status=status):
                case = self.case(owned)
                data = deepcopy(case.remote)
                data['errors'] = [{'field': 'metadata.subjects', 'messages': ['private-provider-message']},
                                  {'field': 'metadata.creators', 'messages': ['private-creator-name']},
                                  {'field': 'private-unrecognized-path', 'messages': ['private-detail']}]
                calls = []

                def response(*args, _calls=calls, _data=data, _status=status, **kwargs):
                    _calls.append(args[0])
                    return fixture.Response(_data, _status)

                with self.assertRaises(m.Held):
                    (r.Controller if owned else m.Controller)(case.stage, fixture.TOKEN, response, lambda _case=case: _case.clock).run()
                state = m.load(case.stage / 'state.json')
                flags = state['responses'][-1]['validation_errors']
                self.assertTrue(flags['metadata_subjects_error_present'])
                self.assertTrue(flags['metadata_creators_error_present'])
                self.assertTrue(flags['unknown_error_field_present'])
                self.assertEqual(flags['errors_count'], 3)
                self.assertEqual(calls, ['PUT' if owned else 'POST'])
                self.assertTrue(state['failed'])
                self.assertEqual(state['counts']['init'], 0)
                self.assertNotIn('private-', json.dumps(state))
                with self.assertRaises(m.Held):
                    (r.Controller if owned else m.Controller)(case.stage, fixture.TOKEN, response, lambda _case=case: _case.clock)
                self.assertEqual(len(calls), 1)

    def test_credential_echoed_errors_are_not_projected_or_persisted_as_messages(self):
        case = self.case(True)
        data = {'errors': [{'field': 'metadata.subjects', 'messages': [fixture.TOKEN]}]}
        with self.assertRaises(m.Held):
            r.Controller(case.stage, fixture.TOKEN, lambda *a, **k: fixture.Response(data, 400), lambda: case.clock).run()
        state = m.load(case.stage / 'state.json')
        self.assertNotIn('validation_errors', state['responses'][-1])
        self.assertNotIn(fixture.TOKEN, json.dumps(state))
        self.assertEqual(state['counts']['metadata'], 1)
        self.assertEqual(state['counts']['get'], 1)

    def test_old_runtime_binding_cannot_be_reused_or_mutated(self):
        original = {'modern_synthetic_canary.py': '4865590399aa47d5a24ce52605500b5c2fcf12a4479d49cda1ec18d40566e435',
                    'modern_canary_errors.py': '2f1f68bf7fee4e39099b5969e2013e1bc01f30b9edef6a2cb7f44a275fbb5bf3'}
        with patch.object(m, 'runtime_binding', return_value=original):
            case = self.case()
        # Every previously executed private stage already has its controller lock.
        (case.stage / 'controller.lock').touch(mode=0o600)
        before = {p.name: p.read_bytes() for p in case.stage.iterdir()}
        with patch('requests.sessions.Session.send') as send, self.assertRaises(m.Held):
            m.execute(case.stage, fixture.TOKEN)
        send.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in case.stage.iterdir()})


if __name__ == '__main__':
    unittest.main()
