"""Offline prepared-body evidence and pure canonical readback diagnostics.

The CLI captures two frozen fictional bodies before Session.send can dispatch.
It never opens a provider stage, changes a ledger, or sends a request. Private
token mode is exclusively for the parent-dispatched sole provider executor.
Local preparation cannot prove historical transmission or provider processing.
"""

import argparse
import base64
import json
import os
import re
from contextlib import ExitStack
from unittest.mock import patch
from urllib.parse import quote

import requests

from scripts import modern_owned_continuation as owned
from scripts import modern_synthetic_canary as modern
from scripts.modern_canary_errors import (
    VALIDATION_ERROR_FIELDS,
    credential_echoed,
    validation_errors_projection,
)

FIXTURE_TOKEN = 'offline-body-diagnostic-fixture-token'
MAX_BODY = 65536
FIELDS = ('title', 'publication_date', 'description', 'keywords', 'resource_type', 'creators')
ERROR_FIELDS = VALIDATION_ERROR_FIELDS


class CaptureStop(BaseException):
    """Trusted local stop, before any adapter entry."""


class NetworkBlocked(BaseException):
    """Trusted local backstop; no exception details are exposed."""


def forbidden(*args, **kwargs):
    raise NetworkBlocked()


def valid_token(token):
    modern.require(isinstance(token, str) and 20 <= len(token) <= 4096
                   and token.isascii() and not any(ch.isspace() for ch in token),
                   'Offline diagnostic token unavailable or invalid')


def echoed(raw, data, token):
    """Reject raw, JSON-escaped, URL-encoded and base64 credential variants."""
    variants = (token, quote(token, safe=''), base64.b64encode(token.encode()).decode(),
                base64.urlsafe_b64encode(token.encode()).decode())
    return any(value.encode() in raw or credential_echoed(data, value)
               for value in (*variants, *(value.rstrip('=') for value in variants[2:])))


def label(value):
    return {str: 'string', bytes: 'bytes', dict: 'object', list: 'array', int: 'integer',
            bool: 'boolean', type(None): 'null'}.get(type(value), 'other')


def prepared_projection(prepared, expected, token, method, url, options):
    """Closed labels and booleans; never return body/header/URL/private values."""
    valid_token(token)
    raw = prepared.body
    result = {'body_type': label(raw), 'credential_echoed': False}
    if not isinstance(raw, (bytes, str)):
        return {**result, 'body_supported': False}
    raw = raw.encode() if isinstance(raw, str) else raw
    if len(raw) > MAX_BODY:
        return {**result, 'body_within_limit': False}
    try:
        decoded = json.loads(raw)
    except (ValueError, RecursionError):
        decoded = None
    if echoed(raw, decoded, token):
        return {'credential_echoed': True, 'safe_body_projection': False}
    length = prepared.headers.get('Content-Length')
    numeric = (int(length) if isinstance(length, str) and re.fullmatch(r'[0-9]{1,5}', length)
               and int(length) <= MAX_BODY else None)
    metadata = decoded.get('metadata') if isinstance(decoded, dict) else None
    access = decoded.get('access') if isinstance(decoded, dict) else None
    result.update(body_supported=True, body_within_limit=True, safe_body_projection=True,
                  body_bytes=len(raw), body_sha256=modern.sha(raw),
                  content_type_json=prepared.headers.get('Content-Type') == 'application/json',
                  content_length_type=label(length), content_length_numeric=numeric,
                  content_length_matches=numeric == len(raw),
                  decoded_json_type=label(decoded), decoded_exact_payload_matches=decoded == expected,
                  method_matches=prepared.method == method, canonical_url_matches=prepared.url == url,
                  intended_auth_matches=prepared.headers.get('Authorization') == 'Bearer ' + token,
                  accept_matches=prepared.headers.get('Accept') == modern.ACCEPT,
                  allow_redirects_false=options.get('allow_redirects') is False,
                  verify_enabled=options.get('verify') not in (None, False, ''),
                  stream_true=options.get('stream') is True,
                  six_metadata_fields_present=isinstance(metadata, dict) and all(
                      (('subjects' if 'subjects' in expected['metadata'] else 'keywords') if k == 'keywords' else k)
                      in metadata for k in FIELDS),
                  access_matches=access == expected['access'])
    return result


def capture_fixed_bodies(token, modern_wire=True):
    """Prepare the supported Session.request route; replace send before use.

    All adapters and socket/DNS boundaries are also blocked. No fallback to the
    original send is possible. Existing executor environment routing is prepared
    normally in explicit private mode, but routing values are never inspected.
    """
    valid_token(token)
    modern.packet()
    results = []
    with ExitStack() as blocks:
        for name in ('requests.adapters.HTTPAdapter.send', 'socket.socket.connect',
                     'socket.socket.connect_ex', 'socket.create_connection', 'socket.getaddrinfo'):
            blocks.enter_context(patch(name, forbidden))
        with requests.Session() as session:
            original_send = session.send
            try:
                for name, method, path in (('create.json', 'POST', '/api/records'),
                                           ('metadata-put.json', 'PUT', '/api/records/101/draft')):
                    raw = (modern.PACKET / name).read_bytes()
                    expected = modern.modern_wire_payload(json.loads(raw)) if modern_wire else json.loads(raw)
                    captures = []
                    url = modern.ORIGIN + path

                    def capture(prepared, _captures=captures, _expected=expected,
                                _method=method, _url=url, **options):
                        _captures.append(prepared_projection(prepared, _expected, token, _method, _url, options))
                        raise CaptureStop()

                    session.send = capture
                    try:
                        session.request(method, url, json=expected,
                                        headers={'Authorization': 'Bearer ' + token,
                                                 'Accept': modern.ACCEPT, 'Content-Type': 'application/json'},
                                        timeout=20, allow_redirects=False, verify=True, stream=True)
                    except CaptureStop:
                        pass
                    modern.require(len(captures) == 1, 'Offline capture did not complete')
                    results.append({'input': name, 'input_bytes': len(raw),
                                    'input_sha256': modern.sha(raw), **captures[0]})
            finally:
                session.send = original_send
    return {'kind': 'pices_modern_offline_prepared_body_v1', 'provider_requests': 0,
            'adapter_calls': 0, 'historical_transmission_proven': False,
            'payload_mode': 'modern_subjects_wire' if modern_wire else 'historical_source_body',
            'packet_sha256': modern.PACKET_SHA, 'captures': results}


def error_projection(data):
    """Retained pure-helper interface; implementation is also runtime-bound."""
    return validation_errors_projection(data)


def canonical_readback_projection(raw, token, expected_identity, owner):
    """Pure projection for a separately granted GET, never a request or adoption.

    Caller alone validates status/deadline/complete response and retains a private
    raw beforeimage only after this credential check. Identity values stay private.
    """
    valid_token(token)
    modern.require(isinstance(raw, bytes) and len(raw) <= MAX_BODY)
    data = json.loads(raw)
    modern.require(isinstance(data, dict))
    if echoed(raw, data, token):
        return {'credential_echoed': True, 'safe_beforeimage_to_retain': False}
    modern.packet()
    historical = modern.load(modern.PACKET / 'metadata-put.json')
    expected = modern.modern_wire_payload(historical)
    metadata = data.get('metadata') if isinstance(data.get('metadata'), dict) else {}
    parent = data.get('parent') if isinstance(data.get('parent'), dict) else {}
    parent_access = parent.get('access') if isinstance(parent.get('access'), dict) else {}
    ownership = parent_access.get('owned_by') if isinstance(parent_access.get('owned_by'), dict) else {}
    versions = data.get('versions') if isinstance(data.get('versions'), dict) else {}
    files = data.get('files') if isinstance(data.get('files'), dict) else {}
    links = data.get('links') if isinstance(data.get('links'), dict) else {}
    rid = modern.record_id(expected_identity['id'])
    identity = {'id': data.get('id'), 'parent_id': parent.get('id'), 'created': data.get('created')}
    return {'credential_echoed': False, 'safe_beforeimage_to_retain': True,
            'body_bytes': len(raw), 'body_sha256': modern.sha(raw),
            'identity_matches': identity == {k: expected_identity[k] for k in identity},
            'owner_matches': isinstance(ownership.get('user'), str) and ownership['user'] == str(owner),
            'first_unpublished_draft': data.get('is_published') is False and data.get('status') == 'draft'
            and type(versions.get('index')) is int and versions['index'] == 1,
            'canonical_links_match': links.get('self') == modern.ORIGIN + '/api/records/' + rid + '/draft'
            and links.get('files') == modern.ORIGIN + '/api/records/' + rid + '/draft/files',
            'files_remain_empty': files.get('enabled') is True and files.get('entries') == {}
            and type(files.get('count')) is int and files['count'] == 0
            and type(files.get('total_bytes')) is int and files['total_bytes'] == 0,
            'keywords_present': 'keywords' in metadata,
            'keywords_type': label(metadata.get('keywords')) if 'keywords' in metadata else 'missing',
            'keywords_matches': metadata.get('keywords') == historical['metadata']['keywords'],
            **owned.metadata_diagnostics(data, expected), **error_projection(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--use-existing-private-sandbox-token', action='store_true')
    parser.add_argument('--historical-source-body', action='store_true')
    args = parser.parse_args()
    try:
        if args.use_existing_private_sandbox_token:
            result = capture_fixed_bodies(os.environ.get('ZENODO_SANDBOX_TOKEN'), not args.historical_source_body)
            result['token_mode'] = 'sole_executor_private'
        else:
            with patch.dict(os.environ, {}, clear=True), patch('requests.sessions.get_netrc_auth', return_value=None):
                result = capture_fixed_bodies(FIXTURE_TOKEN, not args.historical_source_body)
            result['token_mode'] = 'fixture'
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException:
        # Never print provider/environment exceptions or partial sensitive captures.
        print(json.dumps({'held': True, 'provider_requests': 0, 'safe_offline_capture_failed': True}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
