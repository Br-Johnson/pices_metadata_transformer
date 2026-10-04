"""Prepared bytes, transport isolation and closed private-value projections."""

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from unittest.mock import patch

import requests

from scripts import modern_request_body_diagnostics as d
from scripts import modern_synthetic_canary as m
from tests import test_modern_synthetic_canary as fixture


class BodyDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.netrc = patch('requests.sessions.get_netrc_auth', return_value=None)
        self.netrc.start()
        self.addCleanup(self.netrc.stop)
        self.expected = m.load(m.PACKET / 'metadata-put.json')

    def test_real_session_prepares_frozen_json_before_any_adapter(self):
        with patch('requests.adapters.HTTPAdapter.send', side_effect=AssertionError('adapter called')) as adapter:
            result = d.capture_fixed_bodies(d.FIXTURE_TOKEN, modern_wire=False)
        self.assertEqual(adapter.call_count, 0)
        self.assertEqual(result['provider_requests'], 0)
        self.assertFalse(result['historical_transmission_proven'])
        for row, length, digest in zip(result['captures'], (458, 481),
                                      ('6699d88705dfc3daa76b8a41ac0cbb41e4fec3fc55c05fa25cb855c2e7d56978',
                                       '1842cd59ad04211ce2368dd1410aa1fdaafa5d760edea5362c784fd02933c788'), strict=True):
            self.assertEqual(row['body_bytes'], length)
            self.assertEqual(row['body_sha256'], digest)
            self.assertTrue(row['content_type_json'])
            self.assertTrue(row['content_length_matches'])
            self.assertTrue(row['decoded_exact_payload_matches'])
            self.assertTrue(row['six_metadata_fields_present'])
            self.assertTrue(row['access_matches'])
            self.assertTrue(row['intended_auth_matches'])
            self.assertTrue(row['canonical_url_matches'])
        self.assertNotIn(d.FIXTURE_TOKEN, json.dumps(result))

    def prepared(self, body=None):
        request = requests.Request('PUT', m.ORIGIN + '/api/records/101/draft',
                                   json=self.expected if body is None else body,
                                   headers={'Authorization': 'Bearer ' + d.FIXTURE_TOKEN,
                                            'Accept': m.ACCEPT, 'Content-Type': 'application/json'})
        return request.prepare()

    def projection(self, prepared, token=d.FIXTURE_TOKEN):
        return d.prepared_projection(prepared, self.expected, token, 'PUT',
                                     m.ORIGIN + '/api/records/101/draft',
                                     {'allow_redirects': False, 'verify': True, 'stream': True})

    def test_body_or_header_rewrite_is_observed_without_private_output(self):
        prepared = self.prepared({'metadata': {}})
        prepared.headers['Content-Type'] = 'private-header-value'
        prepared.headers['Content-Length'] = 'private-header-value'
        prepared.headers['Authorization'] = 'private-other-credential'
        prepared.url = 'https://private.invalid/secret-owner'
        result = self.projection(prepared)
        self.assertFalse(result['decoded_exact_payload_matches'])
        self.assertFalse(result['six_metadata_fields_present'])
        self.assertFalse(result['content_type_json'])
        self.assertFalse(result['content_length_matches'])
        self.assertFalse(result['intended_auth_matches'])
        self.assertFalse(result['canonical_url_matches'])
        self.assertNotIn('private', json.dumps(result))

    def test_raw_and_decoded_credential_echo_suppresses_hash_and_body(self):
        for token in (d.FIXTURE_TOKEN, 'synthetic-quoted-"-credential-\\-test'):
            body = deepcopy(self.expected)
            body['metadata']['description'] = token
            result = self.projection(self.prepared(body), token)
            self.assertEqual(result, {'credential_echoed': True, 'safe_body_projection': False})
            self.assertNotIn(token, json.dumps(result))

    def test_oversize_or_unsupported_body_is_not_hashed(self):
        for body in (b'x' * (d.MAX_BODY + 1), iter([b'private'])):
            prepared = self.prepared()
            prepared.body = body
            result = self.projection(prepared)
            self.assertNotIn('body_sha256', result)

    def test_capture_backstop_failure_cannot_fall_back_to_original_send(self):
        original_request = requests.Session.request

        def bad_route(session, *args, **kwargs):
            session.get_adapter(m.ORIGIN).send(self.prepared())
            return original_request(session, *args, **kwargs)

        with patch('requests.Session.request', bad_route):
            with self.assertRaises(d.NetworkBlocked):
                d.capture_fixed_bodies(d.FIXTURE_TOKEN)

    def test_cli_fixture_ignores_environment_and_prints_only_closed_failure(self):
        with patch.dict(os.environ, {'ZENODO_SANDBOX_TOKEN': 'private-configured-token'}):
            stream = io.StringIO()
            with patch('sys.argv', ['diagnostics']), redirect_stdout(stream):
                self.assertEqual(d.main(), 0)
            self.assertNotIn('private-configured-token', stream.getvalue())
            self.assertEqual(json.loads(stream.getvalue())['token_mode'], 'fixture')
            stream = io.StringIO()
            with patch('sys.argv', ['diagnostics']), patch.object(d, 'capture_fixed_bodies',
                                                               side_effect=RuntimeError('private-exception')), redirect_stdout(stream):
                self.assertEqual(d.main(), 1)
            self.assertNotIn('private-exception', stream.getvalue())

    def remote(self):
        case = fixture.ModernCanaryTests('test_complete_durable_identity_readback_and_unchanged_retry')
        case.setUp()
        self.addCleanup(case.doCleanups)
        return deepcopy(case.remote)

    def readback(self, data):
        identity = {'id': '101', 'parent_id': '100', 'created': data['created']}
        return d.canonical_readback_projection(m.encoded(data), d.FIXTURE_TOKEN, identity, fixture.OWNER)

    def test_canonical_beforeimage_projection_includes_known_errors_but_no_messages(self):
        data = self.remote()
        data['metadata'] = {}
        data['access']['files'] = 'public'
        data['errors'] = [{'field': 'metadata.keywords', 'messages': ['private-provider-message']},
                          {'field': 'private-owner-path', 'messages': ['private-value']}]
        result = self.readback(data)
        self.assertTrue(result['safe_beforeimage_to_retain'])
        self.assertTrue(result['identity_matches'])
        self.assertTrue(result['owner_matches'])
        self.assertTrue(result['first_unpublished_draft'])
        self.assertTrue(result['files_remain_empty'])
        self.assertTrue(result['metadata_keywords_error_present'])
        self.assertTrue(result['unknown_error_field_present'])
        self.assertFalse(result['metadata_contract_matches'])
        self.assertFalse(result['access_files_matches'])
        self.assertNotIn('private', json.dumps(result))

    def test_ten_readback_samples_preserve_status_and_sensitive_values(self):
        for i in range(10):
            with self.subTest(sample=i):
                data = self.remote()
                data['metadata'] = deepcopy(self.expected['metadata'])
                data['access'] = deepcopy(self.expected['access'])
                data['metadata']['private_unknown_field'] = 'private-value'
                if i % 2:
                    data['parent']['access']['owned_by']['user'] = 'private-owner'
                data['errors'] = [] if i % 3 else {'private-error-field': 'private-message'}
                result = self.readback(data)
                self.assertEqual(result['owner_matches'], not bool(i % 2))
                self.assertFalse(result['metadata_contract_matches'])
                self.assertTrue(result['title_matches'])
                self.assertTrue(result['keywords_matches'])
                self.assertEqual(result['errors_shape_supported'], bool(i % 3))
                self.assertNotIn('private', json.dumps(result))

    def test_readback_credential_prevents_beforeimage_persistence(self):
        data = self.remote()
        data['errors'] = [{'field': 'metadata.title', 'messages': [d.FIXTURE_TOKEN]}]
        self.assertEqual(self.readback(data), {'credential_echoed': True, 'safe_beforeimage_to_retain': False})


if __name__ == '__main__':
    unittest.main()
