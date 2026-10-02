"""Offline token precedence and opaque-header contracts; dummy values only."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.zenodo_api import ZenodoAPIClient, create_zenodo_client, load_zenodo_token


class TokenTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        previous = os.getcwd()
        os.chdir(directory.name)
        self.addCleanup(os.chdir, previous)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_environment_precedes_file_and_preserves_opaque_value(self):
        Path('.env').write_text('ZENODO_SANDBOX_TOKEN=file-dummy\n')
        value = '  NetworkSecret(dummy-only)=opaque  '
        os.environ['ZENODO_SANDBOX_TOKEN'] = value
        with patch('builtins.open', side_effect=AssertionError('must not read file')):
            self.assertEqual(load_zenodo_token(), value)

    def test_mode_selection_without_file(self):
        os.environ.update(ZENODO_SANDBOX_TOKEN='sandbox-dummy',
                          ZENODO_PRODUCTION_TOKEN='production-dummy')
        self.assertEqual(load_zenodo_token(), 'sandbox-dummy')
        self.assertEqual(load_zenodo_token(False), 'production-dummy')

    def test_legacy_file_and_empty_environment_fallback(self):
        Path('.env').write_text('# comment\nZENODO_SANDBOX_TOKEN = file=dummy \n'
                               'ZENODO_PRODUCTION_TOKEN=production-file-dummy\n')
        os.environ['ZENODO_SANDBOX_TOKEN'] = ''
        self.assertEqual(load_zenodo_token(), 'file=dummy')
        self.assertEqual(load_zenodo_token(False), 'production-file-dummy')

    def test_no_cross_mode_fallback_or_secret_in_errors(self):
        os.environ['ZENODO_PRODUCTION_TOKEN'] = 'private-dummy'
        with self.assertRaises(FileNotFoundError) as caught:
            load_zenodo_token()
        self.assertNotIn('private-dummy', str(caught.exception))
        Path('.env').write_text('ZENODO_PRODUCTION_TOKEN=private-file-dummy\n')
        with self.assertRaises(ValueError) as caught:
            load_zenodo_token()
        self.assertNotIn('private-file-dummy', str(caught.exception))

    def test_explicit_client_token_precedence(self):
        with patch('scripts.zenodo_api.load_zenodo_token', side_effect=AssertionError), \
                patch('scripts.zenodo_api.ZenodoAPIClient') as client:
            create_zenodo_client(False, 'explicit-dummy')
            client.assert_called_once_with('explicit-dummy', False)

    def test_placeholder_session_and_bucket_headers_unchanged(self):
        token = 'NetworkSecret(dummy-only)'
        for sandbox, host in ((True, 'sandbox.zenodo.org'), (False, 'zenodo.org')):
            with self.subTest(sandbox=sandbox), \
                    patch('scripts.zenodo_api.get_logger'), \
                    patch.object(ZenodoAPIClient, '_test_connection'), \
                    patch('requests.sessions.Session.request', side_effect=AssertionError('network forbidden')), \
                    patch('scripts.zenodo_api.requests.put') as put:
                key = 'ZENODO_SANDBOX_TOKEN' if sandbox else 'ZENODO_PRODUCTION_TOKEN'
                os.environ[key] = token
                client = create_zenodo_client(sandbox)
                self.addCleanup(client.close)
                self.assertEqual(client.session.headers['Authorization'], 'Bearer ' + token)
                client.get_deposition = Mock(return_value={'id': 1, 'links': {'bucket':
                    f'https://{host}/api/files/00000000-0000-0000-0000-000000000001'}})
                Path('dummy.xml').write_text('<dummy/>')
                put.return_value.status_code = 201
                put.return_value.json.return_value = {'dummy': True}
                client.upload_file(1, 'dummy.xml')
                self.assertEqual(put.call_args.kwargs['headers'], {'Authorization': 'Bearer ' + token})


if __name__ == '__main__':
    unittest.main()
