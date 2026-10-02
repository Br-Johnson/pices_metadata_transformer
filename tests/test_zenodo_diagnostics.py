"""Safe constructor/guard diagnostics with dummy secrets and no transport."""
import json
import traceback
import unittest
from unittest.mock import Mock, patch
import requests
from scripts.zenodo_api import ZenodoAPIClient, ZenodoAPIError

SECRET = 'dummy-private-diagnostic-marker'


class DiagnosticTests(unittest.TestCase):
    def capture(self, *, response=None, exception=None):
        with patch('scripts.zenodo_api.get_logger') as logger, \
                patch('requests.sessions.Session.request', return_value=response, side_effect=exception) as request:
            try:
                ZenodoAPIClient('NetworkSecret(dummy-only)')
            except ZenodoAPIError as error:
                rendered = traceback.format_exc()
                self.assertNotIn(SECRET, str(error))
                self.assertNotIn(SECRET, repr(error))
                self.assertNotIn(SECRET, rendered)
                self.assertNotIn(SECRET, json.dumps(error.diagnostics))
                self.assertNotIn(SECRET, str(logger.mock_calls))
                self.assertEqual(request.call_count, 1)
                return error.diagnostics
            self.fail('Expected structured safe failure')

    def test_http_status_is_retained_without_body(self):
        for status in (301,401,403,429,500,503):
            with self.subTest(status=status):
                response=Mock(status_code=status,text=SECRET)
                response.json.return_value={'message':SECRET}
                diagnostics=self.capture(response=response)
                self.assertEqual(diagnostics['stage'],'constructor_probe')
                self.assertEqual(diagnostics['status'],status)
                self.assertEqual(diagnostics['exception_type'],'HTTPStatus')
                self.assertEqual(diagnostics['retryable'],status==429 or status>=500)

    def test_transport_categories_are_fixed_and_single_attempt(self):
        for cls,label,retryable in (
            (requests.exceptions.ProxyError,'ProxyError',False),
            (requests.exceptions.SSLError,'SSLError',False),
            (requests.exceptions.ConnectTimeout,'ConnectTimeout',True),
            (requests.exceptions.ReadTimeout,'ReadTimeout',True),
            (requests.exceptions.InvalidHeader,'InvalidHeader',False),
            (requests.exceptions.ConnectionError,'ConnectionError',True)):
            with self.subTest(label=label):
                diagnostics=self.capture(exception=cls(SECRET))
                self.assertEqual(diagnostics['exception_type'],label)
                self.assertIsNone(diagnostics['status'])
                self.assertEqual(diagnostics['retryable'],retryable)

    def test_guard_failure_before_response_is_not_auth_failure(self):
        for cls in (ValueError,AssertionError):
            diagnostics=self.capture(exception=cls(SECRET))
            self.assertIsNone(diagnostics['status'])
            self.assertFalse(diagnostics['retryable'])
            self.assertEqual(diagnostics['exception_type'],cls.__name__)

    def test_explicit_safe_guard_stage_status_survive_wrapping(self):
        for stage in ('request_prepare','transport','response_status','response_json','response_owner','response_links'):
            with self.subTest(stage=stage):
                observed_status=None if stage in ('request_prepare','transport') else 200
                error=ZenodoAPIError(SECRET,stage=stage,exception_type='ValueError',status=observed_status)
                diagnostics=self.capture(exception=error)
                self.assertEqual(diagnostics['stage'],stage)
                self.assertEqual(diagnostics['status'],observed_status)
                self.assertFalse(diagnostics['retryable'])

    def test_dynamic_exception_name_and_attributes_are_not_exposed(self):
        cls=type(SECRET,(Exception,),{})
        error=cls(SECRET)
        error.status=SECRET;error.stage=SECRET;error.response=Mock(status_code=SECRET)
        diagnostics=self.capture(exception=error)
        self.assertEqual(diagnostics['exception_type'],'unknown')
        self.assertIsNone(diagnostics['status'])

    def test_guard_schema_sanitizes_unsupported_fields(self):
        error=ZenodoAPIError('Guard stopped',stage=SECRET,exception_type=SECRET,status=SECRET,attempt=SECRET)
        self.assertNotIn(SECRET,json.dumps(error.diagnostics))
        self.assertEqual(error.diagnostics['exception_type'],'unknown')
        self.assertIsNone(error.diagnostics['status'])

    def test_constructor_success_retains_existing_endpoint_and_no_hidden_retry(self):
        with patch('scripts.zenodo_api.get_logger'), patch('requests.sessions.Session.request',return_value=Mock(status_code=200)) as request:
            client=ZenodoAPIClient('NetworkSecret(dummy-only)')
            self.addCleanup(client.close)
            self.assertEqual(request.call_args.args,('GET','https://sandbox.zenodo.org/api/deposit/depositions'))
            self.assertEqual(request.call_count,1)
            self.assertNotIn('params',request.call_args.kwargs)
            self.assertIs(request.call_args.kwargs['allow_redirects'],False)
