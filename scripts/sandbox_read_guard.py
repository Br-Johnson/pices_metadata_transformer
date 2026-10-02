"""Bounded read-only sandbox inventory guard with safe milestone receipts.

Returned descriptive links are inert. Only outgoing requests and actionable
pagination are origin restricted. No credentials, URLs, bodies or owner IDs
are retained in receipts; this guard never authorizes writes or publication.
"""
from copy import deepcopy
import hashlib
import json
from urllib.parse import parse_qsl, urlsplit

import requests

from scripts.zenodo_api import ZenodoAPIError, _exception_diagnostics, _validate_token


class SandboxInventoryGuard:
    def __init__(self, token, expected_owner_id, *, max_requests=1, max_bytes=12 * 1024 * 1024):
        self._token = _validate_token(token)
        if type(expected_owner_id) is not int or expected_owner_id < 1:
            raise ValueError('Expected owner must be a positive private identifier')
        if type(max_requests) is not int or not 1 <= max_requests <= 240:
            raise ValueError('Read guard request bound must be between 1 and 240')
        if type(max_bytes) is not int or not 1 <= max_bytes <= 12 * 1024 * 1024:
            raise ValueError('Read guard byte bound is invalid')
        self._owner = expected_owner_id
        self.max_requests, self.max_bytes = max_requests, max_bytes
        self._state = {'transport_attempts': 0, 'owned_pages': 0, 'community_pages': 0,
                       'writes_performed': 0, 'observations': []}
        self._original_send = None

    def receipt(self):
        return deepcopy(self._state)

    def __enter__(self):
        if self._original_send is not None:
            raise ValueError('Read guard already active')
        self._original_send = requests.sessions.Session.send
        original = self._original_send
        def guarded(session, request, **kwargs):
            return self.send(original, session, request, **kwargs)
        requests.sessions.Session.send = guarded
        return self

    def __exit__(self, *_):
        requests.sessions.Session.send = self._original_send
        self._original_send = None

    @staticmethod
    def _require(condition, observation, reason, stage, *, exception_type='ValueError'):
        if not condition:
            observation['failure_code'] = reason
            raise ZenodoAPIError('Sandbox inventory guard stopped', stage=stage,
                                 exception_type=exception_type, status=observation['status'],
                                 retryable=False)

    def _url(self, value, observation, stage, path=None):
        try:
            parsed = urlsplit(value)
            port = parsed.port
            pairs = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=64)
        except (ValueError, TypeError, AttributeError):
            self._require(False, observation, 'malformed_actionable_url', stage)
        self._require(parsed.scheme == 'https' and parsed.hostname == 'sandbox.zenodo.org'
                      and port in (None, 443) and parsed.username is None and parsed.password is None
                      and not parsed.fragment, observation, 'unexpected_actionable_origin', stage)
        actual_path = parsed.path.rstrip('/')
        self._require(actual_path in ('/api/deposit/depositions', '/api/records')
                      and (path is None or actual_path == path),
                      observation, 'unexpected_actionable_path', stage)
        forbidden = {'access_token', 'token', 'authorization', 'api_key'}
        self._require(not any(key.casefold() in forbidden for key, _ in pairs),
                      observation, 'credential_query_forbidden', stage)
        return actual_path, pairs

    def _links(self, data, observation, path):
        # These root-level links participate in inventory pagination. Per-record
        # DOI, HTML, citation, bucket and action links are data, never followed.
        links = data.get('links') if isinstance(data, dict) else None
        if links is None:
            return
        self._require(isinstance(links, dict), observation, 'malformed_pagination_links', 'response_links')
        for key in ('self', 'next', 'prev'):
            value = links.get(key)
            if value is not None:
                self._require(isinstance(value, str) and bool(value), observation,
                              'malformed_pagination_link', 'response_links')
                self._url(value, observation, 'response_links', path)

    def send(self, original_send, session, request, **kwargs):
        observation = {'request_prepared': False, 'transport_entered': False,
                       'response_received': False, 'status': None, 'status_validated': False,
                       'json_validated': False, 'owner_validated': False,
                       'links_validated': False, 'completed': False}
        self._state['observations'].append(observation)
        stage = 'request_prepare'
        response = None
        try:
            path, _ = self._url(request.url, observation, stage)
            self._require(request.method == 'GET', observation, 'write_or_method_forbidden', stage)
            self._require(request.headers.get('Authorization') == 'Bearer ' + self._token,
                          observation, 'bearer_value_changed', stage)
            self._require(self._state['transport_attempts'] < self.max_requests,
                          observation, 'request_bound_exceeded', stage)
            observation['request_prepared'] = True
            kwargs.update(allow_redirects=False, timeout=(10, 30), stream=True)
            stage = 'transport'
            self._state['transport_attempts'] += 1
            observation['transport_entered'] = True
            response = original_send(session, request, **kwargs)
            observation['response_received'] = True
            status = response.status_code
            observation['status'] = status if type(status) is int and 100 <= status <= 599 else None
            stage = 'response_status'
            self._require(observation['status'] == 200, observation, 'unexpected_http_status', stage,
                          exception_type='HTTPStatus')
            observation['status_validated'] = True
            stage = 'response_json'
            chunks, length = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                length += len(chunk)
                self._require(length <= self.max_bytes, observation, 'response_size_bound_exceeded', stage)
                chunks.append(chunk)
            raw = b''.join(chunks)
            self._require(self._token.encode('ascii') not in raw, observation, 'credential_echo_rejected', stage)
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                self._require(False, observation, 'non_json_response', stage, exception_type='JSONDecodeError')
            if path == '/api/deposit/depositions':
                self._require(isinstance(data, list), observation, 'owned_inventory_not_array', stage)
                observation['json_validated'] = True
                stage = 'response_owner'
                for item in data:
                    self._require(isinstance(item, dict) and type(item.get('owner')) is int
                                  and item['owner'] == self._owner, observation,
                                  'owned_inventory_missing_or_mismatched_owner', stage)
                observation['owned_items'] = len(data)
                # Empty inventory is a valid response, not evidence of owner identity.
                observation['owner_validated'] = bool(data)
            else:
                self._require(isinstance(data, dict) and isinstance(data.get('hits'), dict)
                              and isinstance(data['hits'].get('hits'), list), observation,
                              'community_inventory_malformed_hits', stage)
                self._require(all(isinstance(item, dict) for item in data['hits']['hits']),
                              observation, 'community_inventory_malformed_hit', stage)
                observation['json_validated'] = True
                # Public community records may belong to other owners.
            stage = 'response_links'
            self._links(data, observation, path)
            observation['links_validated'] = True
            observation['bytes'] = len(raw)
            observation['sha256'] = hashlib.sha256(raw).hexdigest()
            response._content, response._content_consumed = raw, True
        except Exception as exc:
            diagnostics = _exception_diagnostics(exc, stage)
            if diagnostics['status'] is None:
                diagnostics['status'] = observation['status']
            observation['diagnostics'] = diagnostics
            raise ZenodoAPIError('Sandbox inventory guard stopped', **diagnostics) from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception as exc:
                    # Preserve an existing sanitized primary failure. Cleanup
                    # must neither leak its exception nor mask a known status.
                    if 'diagnostics' not in observation:
                        diagnostics = _exception_diagnostics(exc, 'response_cleanup')
                        diagnostics['status'] = observation['status']
                        observation['failure_code'] = 'response_cleanup_failed'
                        observation['diagnostics'] = diagnostics
                        raise ZenodoAPIError('Sandbox inventory cleanup failed', **diagnostics) from None
        observation['completed'] = True
        self._state['owned_pages' if path == '/api/deposit/depositions' else 'community_pages'] += 1
        return response
