"""Independent offline observer review tests; no writes to implementation files."""
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, '/workspace/scratch/historical-transport-20261004/followup')
import requests
import urllib3.connection
import test_write_observer as fixture
import write_observer as observer


class AdversarialReview(unittest.TestCase):
    setUp = fixture.ObserverTests.setUp
    run_request = fixture.ObserverTests.run_request

    def test_post_response_persistence_failure_closes_unreturned_response(self):
        saved = []
        original_send = requests.sessions.Session.send

        def track_response(session, *args, **kwargs):
            response = original_send(session, *args, **kwargs)
            original_close = response.close
            record = {'response': response, 'closed_by_caller': False}

            def close():
                record['closed_by_caller'] = True
                return original_close()

            response.close = close
            saved.append(record)
            return response

        def fail(receipt):
            if receipt['events'][-1]['event'] == 'response_headers_returned':
                raise RuntimeError('synthetic persistence failure')

        try:
            with patch.object(requests.sessions.Session, 'send', track_response):
                result = self.run_request(persist=fail)
            self.assertEqual(result['exception'], 'ObservationHeld')
            self.assertEqual(len(saved), 1)
            self.assertTrue(saved[0]['closed_by_caller'],
                            'Response was returned by adapter but lost on receipt failure without close()')
        finally:
            for record in saved:
                record['response'].close()

    def test_persistence_failure_before_body_call_never_transmits_body(self):
        def fail(receipt):
            if receipt['events'][-1]['event'] == 'body_send_entered':
                raise RuntimeError('synthetic persistence failure')

        result = self.run_request(persist=fail)
        self.assertEqual(result['exception'], 'ObservationHeld')
        self.assertFalse(result['result']['local_body_send_completed'])
        self.assertNotIn(fixture.BODY, result['socket'].calls)

    def test_persistence_failure_after_body_return_keeps_completion_evidence(self):
        def fail(receipt):
            if receipt['events'][-1]['event'] == 'body_send_returned':
                raise RuntimeError('synthetic persistence failure')

        result = self.run_request(persist=fail)
        self.assertEqual(result['exception'], 'ObservationHeld')
        self.assertTrue(result['result']['local_body_send_completed'])
        self.assertEqual(result['socket'].calls[-1], fixture.BODY)
        self.assertFalse(result['result']['origin_receipt_proved'])

    def test_first_send_error_with_receipt_failure_never_retries(self):
        import errno

        def fail(receipt):
            if receipt['events'][-1]['event'] == 'body_send_exception':
                raise OSError(errno.EPIPE, 'synthetic persistence failure')

        result = self.run_request(code=errno.EPIPE, persist=fail)
        self.assertEqual(result['exception'], 'ObservationHeld')
        self.assertEqual(result['result']['body_send_calls'], 1)
        self.assertEqual(result['socket'].calls.count(fixture.BODY), 1)
        self.assertTrue(result['result']['write_failure_observed'])
        self.assertFalse(result['result']['local_body_send_completed'])

    def test_unexpected_split_body_rejected_before_any_body_write(self):
        original = urllib3.connection.body_to_chunks

        def split(body, *args, **kwargs):
            value = original(body, *args, **kwargs)
            return type(value)(chunks=iter((body[:10], body[10:])),
                               content_length=value.content_length)

        with patch.object(urllib3.connection, 'body_to_chunks', split):
            result = self.run_request()
        self.assertEqual(result['exception'], 'ObservationHeld')
        self.assertEqual(result['result']['body_send_calls'], 0)
        self.assertFalse(result['result']['local_body_send_completed'])
        self.assertEqual(len(result['socket'].calls), 1)  # Headers only.

    def test_unexpected_duplicate_body_never_sends_second_copy(self):
        original = urllib3.connection.body_to_chunks

        def duplicate(body, *args, **kwargs):
            value = original(body, *args, **kwargs)
            return type(value)(chunks=iter((body, body)),
                               content_length=value.content_length)

        with patch.object(urllib3.connection, 'body_to_chunks', duplicate):
            result = self.run_request()
        self.assertEqual(result['exception'], 'ObservationHeld')
        self.assertEqual(result['result']['body_send_calls'], 1)
        self.assertEqual(result['socket'].calls.count(fixture.BODY), 1)
        self.assertTrue(result['result']['local_body_send_completed'])
        self.assertFalse(result['result']['response_returned'])

    def test_keyboard_interrupt_during_body_restores_every_hook(self):
        base = fixture.FakeSocket

        class InterruptingSocket(base):
            def sendall(self, data):
                if bytes(data) == fixture.BODY:
                    raise KeyboardInterrupt('synthetic interruption')
                return super().sendall(data)

        with patch.object(fixture, 'FakeSocket', InterruptingSocket):
            result = self.run_request()
        self.assertEqual(result['exception'], 'KeyboardInterrupt')
        self.assertTrue(result['result']['write_failure_observed'])
        self.assertFalse(result['result']['local_body_send_completed'])
        self.assertEqual(result['result']['body_send_calls'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
