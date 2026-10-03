"""Dummy-only response/request guard tests; no credentials or network."""
import json
import unittest
from unittest.mock import Mock, patch
import requests
from scripts.sandbox_read_guard import SandboxInventoryGuard
from scripts.zenodo_api import ZenodoAPIClient, ZenodoAPIError

TOKEN='NetworkSecret(dummy-read-guard)'
OWNER=7


def response(data, status=200):
    r=requests.Response();r.status_code=status;r._content=json.dumps(data).encode()
    r._content_consumed=True;r.url='https://sandbox.zenodo.org/api/deposit/depositions'
    return r


def prepared(url='https://sandbox.zenodo.org/api/deposit/depositions', method='GET', token=TOKEN):
    return requests.Request(method,url,headers={'Authorization':'Bearer '+token}).prepare()


class ReadGuardTests(unittest.TestCase):
    def run_guard(self, data=None, *, status=200, request=None, exception=None):
        transport=Mock(return_value=response(data if data is not None else [],status),side_effect=exception)
        guard=SandboxInventoryGuard(TOKEN,OWNER,max_requests=1)
        guard.send(transport,requests.Session(),request or prepared())
        return guard,transport

    def test_inert_external_links_never_restrict_inventory_origin(self):
        item={'id':1,'owner':OWNER,'links':{'doi':'https://handle.test.datacite.org/10.5072/test',
             'latest_html':'http://example.org/citation','self':'https://sandbox.zenodo.org/api/deposit/depositions/1'}}
        guard,transport=self.run_guard([item])
        self.assertEqual(guard.receipt()['owned_pages'],1)
        self.assertEqual(transport.call_count,1)

    def test_external_pagination_link_rejected_after_status_recorded(self):
        guard=SandboxInventoryGuard(TOKEN,OWNER,max_requests=1)
        data={'hits':{'hits':[],'total':0},'links':{'next':'https://example.org/api/records'}}
        with self.assertRaises(ZenodoAPIError) as caught:
            guard.send(Mock(return_value=response(data)),requests.Session(),
                prepared('https://sandbox.zenodo.org/api/records?q=communities%3Apices'))
        self.assertEqual(caught.exception.diagnostics['stage'],'response_links')
        self.assertEqual(caught.exception.diagnostics['status'],200)
        self.assertTrue(guard.receipt()['observations'][0]['response_received'])

    def test_no_outgoing_cross_host_or_write(self):
        for url,method in [('https://example.org/api/records','GET'),
                           ('http://sandbox.zenodo.org/api/records','GET'),
                           ('https://sandbox.zenodo.org/api/deposit/depositions','POST'),
                           ('https://sandbox.zenodo.org/api/deposit/depositions/1/actions/publish','GET')]:
            guard=SandboxInventoryGuard(TOKEN,OWNER,max_requests=1);transport=Mock()
            with self.subTest(url=url,method=method),self.assertRaises(ZenodoAPIError):
                guard.send(transport,requests.Session(),prepared(url,method))
            transport.assert_not_called()

    def test_blank_credential_query_rejected(self):
        for suffix in ('?token=','?%61ccess_token=','?AUTHORIZATION='):
            guard=SandboxInventoryGuard(TOKEN,OWNER);transport=Mock()
            with self.subTest(suffix=suffix),self.assertRaises(ZenodoAPIError):
                guard.send(transport,requests.Session(),prepared('https://sandbox.zenodo.org/api/deposit/depositions'+suffix))
            transport.assert_not_called()

    def test_status_and_owner_failure_survive_constructor(self):
        with patch('scripts.zenodo_api.get_logger'), patch('requests.sessions.Session.send',return_value=response([{'id':1,'owner':99}])):
            with SandboxInventoryGuard(TOKEN,OWNER,max_requests=1) as guard:
                with self.assertRaises(ZenodoAPIError) as caught:
                    ZenodoAPIClient(TOKEN)
        self.assertEqual(caught.exception.diagnostics['stage'],'response_owner')
        self.assertEqual(caught.exception.diagnostics['status'],200)
        self.assertNotIn('99',str(caught.exception))
        self.assertNotIn(TOKEN,json.dumps(guard.receipt()))

    def test_http_failure_status_and_transport_null_status(self):
        for status in (401,403,429,503):
            guard=SandboxInventoryGuard(TOKEN,OWNER)
            with self.subTest(status=status),self.assertRaises(ZenodoAPIError) as caught:
                guard.send(Mock(return_value=response({},status)),requests.Session(),prepared())
            self.assertEqual(caught.exception.diagnostics['status'],status)
            self.assertEqual(caught.exception.diagnostics['stage'],'response_status')
        guard=SandboxInventoryGuard(TOKEN,OWNER)
        with self.assertRaises(ZenodoAPIError) as caught:
            guard.send(Mock(side_effect=requests.exceptions.ProxyError(TOKEN)),requests.Session(),prepared())
        self.assertIsNone(caught.exception.diagnostics['status'])
        self.assertEqual(caught.exception.diagnostics['exception_type'],'ProxyError')
        self.assertNotIn(TOKEN,str(caught.exception))

    def test_constructor_one_request_restores_patch(self):
        with patch('scripts.zenodo_api.get_logger'),patch('requests.sessions.Session.send',return_value=response([])) as transport:
            original=requests.sessions.Session.send
            with SandboxInventoryGuard(TOKEN,OWNER,max_requests=1) as guard:
                client=ZenodoAPIClient(TOKEN);self.addCleanup(client.close)
                with self.assertRaises(ZenodoAPIError):
                    client.get_all_my_depositions()
            self.assertIs(requests.sessions.Session.send,original)
            self.assertEqual(transport.call_count,1)
            self.assertIs(transport.call_args.kwargs['allow_redirects'],False)
        self.assertEqual(guard.receipt()['transport_attempts'],1)

    def test_changed_bearer_rejected_without_transport_or_disclosure(self):
        guard=SandboxInventoryGuard(TOKEN,OWNER);transport=Mock()
        with self.assertRaises(ZenodoAPIError) as caught:
            guard.send(transport,requests.Session(),prepared(token='dummy-other-secret'))
        transport.assert_not_called()
        self.assertNotIn('dummy-other-secret',str(caught.exception))
        self.assertNotIn(TOKEN,json.dumps(guard.receipt()))

    def test_json_escaped_credential_keys_and_values_are_rejected(self):
        token='DUMMY-review-token\\with"escape'
        for field in ({'notes':token},{token:'unrelated'}):
            guard=SandboxInventoryGuard(token,OWNER)
            data=[{'id':1,'owner':OWNER,'metadata':field}]
            with self.subTest(field=field),self.assertRaises(ZenodoAPIError):
                guard.send(Mock(return_value=response(data)),requests.Session(),prepared(token=token))
            self.assertEqual(guard.receipt()['observations'][-1]['failure_code'],'credential_echo_rejected')
            self.assertNotIn(token,json.dumps(guard.receipt()))

    def test_oversized_echo_and_nonjson_bodies_fail_safely(self):
        cases=[(b'x'*20,10,'response_size_bound_exceeded'),
               (TOKEN.encode(),1000,'credential_echo_rejected'),
               (b'<html>dummy-private-body</html>',1000,'non_json_response')]
        for raw,bound,reason in cases:
            with self.subTest(reason=reason):
                guard=SandboxInventoryGuard(TOKEN,OWNER,max_bytes=bound)
                r=response([]);r._content=raw
                with self.assertRaises(ZenodoAPIError) as caught:
                    guard.send(Mock(return_value=r),requests.Session(),prepared())
                observation=guard.receipt()['observations'][0]
                self.assertEqual(observation['failure_code'],reason)
                self.assertEqual(observation['status'],200)
                self.assertEqual(caught.exception.diagnostics['stage'],'response_json')
                self.assertNotIn('dummy-private-body',str(caught.exception))
                self.assertNotIn(TOKEN,json.dumps(guard.receipt()))

    def test_malformed_owned_shape_and_owner_fail_at_separate_stages(self):
        for data,stage in [({},'response_json'),([{}],'response_owner'),
                           ([{'owner':True}],'response_owner'),([{'owner':str(OWNER)}],'response_owner')]:
            guard=SandboxInventoryGuard(TOKEN,OWNER)
            with self.subTest(data=data),self.assertRaises(ZenodoAPIError) as caught:
                guard.send(Mock(return_value=response(data)),requests.Session(),prepared())
            self.assertEqual(caught.exception.diagnostics['stage'],stage)
            self.assertEqual(caught.exception.diagnostics['status'],200)

    def test_community_shape_never_defaults_missing_hits_to_empty(self):
        for data in ({},{'hits':{}},{'hits':{'hits':{}}},{'hits':{'hits':[None]}}):
            guard=SandboxInventoryGuard(TOKEN,OWNER)
            with self.subTest(data=data),self.assertRaises(ZenodoAPIError):
                guard.send(Mock(return_value=response(data)),requests.Session(),prepared('https://sandbox.zenodo.org/api/records'))
            self.assertEqual(guard.receipt()['community_pages'],0)

    def test_public_community_owners_and_inert_links_are_not_owned_inventory(self):
        data={'hits':{'hits':[{'id':3,'owner':999,'links':{'doi':'https://doi.org/example'}}],'total':1},
              'links':{'self':'https://sandbox.zenodo.org/api/records?q=communities%3Apices'}}
        guard,_=self.run_guard(data,request=prepared('https://sandbox.zenodo.org/api/records?q=communities%3Apices'))
        self.assertEqual(guard.receipt()['community_pages'],1)
        self.assertEqual(guard.receipt()['owned_pages'],0)

    def test_navigation_credentials_and_malformed_port_have_safe_classification(self):
        for link in ('https://sandbox.zenodo.org/api/records?token=',
                     'https://sandbox.zenodo.org:invalid/api/records',
                     'https://name:password@sandbox.zenodo.org/api/records',
                     '/api/records?page=2',
                     'https://sandbox.zenodo.org/api/deposit/depositions'):
            guard=SandboxInventoryGuard(TOKEN,OWNER)
            data={'hits':{'hits':[],'total':0},'links':{'next':link}}
            with self.subTest(link=link),self.assertRaises(ZenodoAPIError) as caught:
                guard.send(Mock(return_value=response(data)),requests.Session(),prepared('https://sandbox.zenodo.org/api/records'))
            self.assertEqual(caught.exception.diagnostics['stage'],'response_links')
            self.assertNotIn('password',str(caught.exception))
            self.assertNotIn('invalid/api',json.dumps(guard.receipt()))

    def test_preparation_parse_failure_is_not_transport_failure(self):
        guard=SandboxInventoryGuard(TOKEN,OWNER);transport=Mock()
        request=prepared();request.url='https://sandbox.zenodo.org:bad/api/records'
        with self.assertRaises(ZenodoAPIError) as caught:
            guard.send(transport,requests.Session(),request)
        self.assertEqual(caught.exception.diagnostics['stage'],'request_prepare')
        self.assertIsNone(caught.exception.diagnostics['status'])
        self.assertFalse(guard.receipt()['observations'][0]['transport_entered'])
        transport.assert_not_called()

    def test_cleanup_error_is_sanitized_and_does_not_claim_completion(self):
        marker='dummy-private-close-marker'
        for status,stage in ((200,'response_cleanup'),(403,'response_status')):
            guard=SandboxInventoryGuard(TOKEN,OWNER)
            r=response([],status);r.close=Mock(side_effect=ValueError(marker))
            with self.subTest(status=status),self.assertRaises(ZenodoAPIError) as caught:
                guard.send(Mock(return_value=r),requests.Session(),prepared())
            self.assertEqual(caught.exception.diagnostics['stage'],stage)
            self.assertEqual(caught.exception.diagnostics['status'],status)
            self.assertFalse(guard.receipt()['observations'][0]['completed'])
            self.assertEqual(guard.receipt()['owned_pages'],0)
            self.assertNotIn(marker,str(caught.exception))
            self.assertNotIn(marker,json.dumps(guard.receipt()))

    def test_streamed_response_is_bounded_and_cached_for_caller(self):
        import io
        class Stream(io.BytesIO):
            def release_conn(self):
                self.close()
        r=requests.Response();r.status_code=200;r.raw=Stream(b'[]')
        guard=SandboxInventoryGuard(TOKEN,OWNER)
        result=guard.send(Mock(return_value=r),requests.Session(),prepared())
        self.assertEqual(result.json(),[])
        self.assertEqual(guard.receipt()['observations'][0]['bytes'],2)
        self.assertTrue(r.raw.closed)

    def test_streamed_failure_retains_status_without_body_or_exception(self):
        marker='dummy-private-stream-marker'
        for chunks,reason in (([b'x'*100],'response_size_bound_exceeded'),
                              ([b'{bad}'],'non_json_response'),
                              ([TOKEN.encode()],'credential_echo_rejected')):
            guard=SandboxInventoryGuard(TOKEN,OWNER,max_bytes=50)
            r=response([]);r.iter_content=Mock(return_value=iter(chunks))
            with self.subTest(reason=reason),self.assertRaises(ZenodoAPIError):
                guard.send(Mock(return_value=r),requests.Session(),prepared())
            self.assertEqual(guard.receipt()['observations'][0]['failure_code'],reason)
        guard=SandboxInventoryGuard(TOKEN,OWNER)
        r=response([]);r.iter_content=Mock(side_effect=requests.exceptions.ConnectionError(marker))
        with self.assertRaises(ZenodoAPIError) as caught:
            guard.send(Mock(return_value=r),requests.Session(),prepared())
        self.assertEqual(caught.exception.diagnostics['stage'],'response_json')
        self.assertEqual(caught.exception.diagnostics['status'],200)
        self.assertNotIn(marker,str(caught.exception))

    def test_empty_owned_page_does_not_claim_owner_identity(self):
        guard,_=self.run_guard([])
        observation=guard.receipt()['observations'][0]
        self.assertEqual(observation['owned_items'],0)
        self.assertFalse(observation['owner_validated'])
        self.assertTrue(observation['completed'])
