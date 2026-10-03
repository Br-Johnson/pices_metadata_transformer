"""Use the observed canonical sandbox search path without following redirects."""
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs
import requests
from scripts.zenodo_api import ZenodoAPIClient, ZenodoAPIError
from scripts.sandbox_read_guard import SandboxInventoryGuard
from tests.test_sandbox_read_guard import response, TOKEN, OWNER


class SandboxSearchEndpointTests(unittest.TestCase):
    def test_each_search_page_uses_slashless_path_and_exact_query(self):
        calls=[]
        def transport(session,request,**kwargs):
            parsed=urlsplit(request.url);calls.append((parsed,kwargs))
            self.assertFalse(kwargs['allow_redirects'])
            if parsed.path=='/api/deposit/depositions':return response([{'id':1,'owner':OWNER}])
            self.assertEqual(parsed.path,'/api/records')
            query=parse_qs(parsed.query)
            self.assertEqual(query['q'],['communities:pices']);self.assertEqual(query['size'],['200'])
            page=int(query['page'][0])
            return response({'hits':{'total':2,'hits':[{'id':page}]},
                'links':{'next':'https://sandbox.zenodo.org/api/records?page=2'} if page==1 else {}})
        with patch('requests.sessions.Session.send',transport),patch.object(ZenodoAPIClient,'_rate_limit_check'):
            with SandboxInventoryGuard(TOKEN,OWNER,max_requests=3) as guard:
                client=ZenodoAPIClient(TOKEN,sandbox=True);client.max_retries=0
                self.assertEqual([r['id'] for r in client.get_records_by_query(q='communities:pices',size=200)],[1,2])
                client.close()
        self.assertEqual(guard.receipt()['transport_attempts'],3)
        self.assertEqual(len(calls),3)

    def test_301_location_is_never_followed_or_treated_as_inventory(self):
        for location in ['https://sandbox.zenodo.org/api/records?q=communities%3Apices',
                         'https://evil.test/api/records',None]:
            calls=[]
            def transport(session,request,**kwargs):
                calls.append(request.url);self.assertFalse(kwargs['allow_redirects'])
                if urlsplit(request.url).path=='/api/deposit/depositions':return response([])
                result=response({},301)
                if location:result.headers['Location']=location
                return result
            with self.subTest(location=location),patch('requests.sessions.Session.send',transport),patch.object(ZenodoAPIClient,'_rate_limit_check'):
                with SandboxInventoryGuard(TOKEN,OWNER,max_requests=3) as guard:
                    client=ZenodoAPIClient(TOKEN,sandbox=True);client.max_retries=0
                    with self.assertRaises(ZenodoAPIError):client.get_records_by_query(q='communities:pices',size=200)
                    client.close()
                self.assertEqual(len(calls),2)
                self.assertEqual(guard.receipt()['observations'][-1]['status'],301)

    def test_search_itself_disables_redirects_even_outside_guard(self):
        client=object.__new__(ZenodoAPIClient);client.sandbox=True
        with patch.object(client,'_make_request',return_value=response({'hits':{'hits':[],'total':0}})) as call:
            client.search_records(q='communities:pices',size=200,page=1)
            call.assert_called_once_with('GET','records',params={'q':'communities:pices','size':200,'page':1},allow_redirects=False)
