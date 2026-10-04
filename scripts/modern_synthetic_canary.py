"""Fixed fictional modern Sandbox transaction; no grant is minted by this CLI.

Every attempt is durable before transport. Interrupted or failed transactions
stay held; only a completed transaction has an unchanged read-only retry. This
module is isolated from legacy grants, upload services and production adapters.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests

from scripts.modern_canary_errors import (
    credential_echoed,
    response_projection,
    validation_errors_projection,
)

NAMESPACE = 'pices-modern-synthetic-20261003-code-02'
ORIGIN = 'https://sandbox.zenodo.org'
ACCEPT = 'application/vnd.inveniordm.v1+json'
PACKET = Path(__file__).resolve().parents[1] / 'docs/handoff/modern-synthetic-canary-20261003-code-02'
PACKET_SHA = '0f54838bf45ebecccaf575db4145c5a51cdd01507f0aaa6e9b418aadd786db13'
LIMITS = {'create': 1, 'doi': 1, 'metadata': 1, 'init': 1, 'content': 1, 'commit': 1, 'get': 8}
EXECUTOR = '01a0fed7-bf71-7384-95fd-3434599df03f'
FILES = {'binding.json', 'state.json', 'journal.json', 'controller.lock', 'approval.json',
         'synthetic.xml', 'create.json', 'metadata-put.json'}


class Held(ValueError):
    """Fixed safe message; provider exceptions and credential values are never printed."""

    def __init__(self, message, diagnostic=None):
        super().__init__(message)
        self.diagnostic = diagnostic


class WallDeadline(Held):
    """Trusted local alarm category; carries no provider exception text."""


def exception_code(error):
    """Exact trusted types only: never inspect exception names, arguments or text."""
    types = ((Held, 'contract'), (WallDeadline, 'wall_deadline'),
             (ValueError, 'value_error'), (TypeError, 'type_error'),
             (KeyError, 'key_error'), (OSError, 'os_error'),
             (KeyboardInterrupt, 'interrupted'), (json.JSONDecodeError, 'invalid_json'),
             (requests.exceptions.InvalidHeader, 'invalid_header'),
             (requests.exceptions.InvalidURL, 'invalid_url'),
             (requests.exceptions.InvalidSchema, 'invalid_schema'),
             (requests.exceptions.MissingSchema, 'missing_schema'),
             (requests.exceptions.ConnectTimeout, 'connect_timeout'),
             (requests.exceptions.ReadTimeout, 'read_timeout'),
             (requests.exceptions.Timeout, 'timeout'),
             (requests.exceptions.SSLError, 'tls_error'),
             (requests.exceptions.ConnectionError, 'connection_error'),
             (requests.exceptions.ChunkedEncodingError, 'chunked_body'),
             (requests.exceptions.ContentDecodingError, 'body_decoding'))
    return next((code for cls, code in types if type(error) is cls), 'unclassified')


def require(ok, reason='Modern canary contract failed; preserve stage for reconciliation'):
    if not ok:
        raise Held(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True).encode() + b'\n'


def load(path):
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError, RecursionError):
        raise Held('Required private stage file missing or invalid; no reset') from None


def atomic(path, value):
    """Private replace + file/directory fsync; journal mismatch stops crash recovery."""
    temp = path.with_name('.' + path.name + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(encoded(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temp.exists():
            temp.unlink()


def secure_stage(stage):
    stage = Path(stage)
    require(stage.is_absolute() and stage.name == NAMESPACE)
    for path in (stage, *stage.parents):
        require(not path.is_symlink())
    require(stage.is_dir() and stage.resolve() == stage and stage.stat().st_mode & 0o077 == 0)
    for path in stage.iterdir():
        require(path.name in FILES and not path.is_symlink() and path.is_file()
                and path.stat().st_nlink == 1 and path.stat().st_mode & 0o077 == 0)
    return stage


def packet():
    raw = (PACKET / 'INVENTORY.json').read_bytes()
    require(sha(raw) == PACKET_SHA)
    for item in json.loads(raw):
        raw_file = (PACKET / item['path']).read_bytes()
        require(len(raw_file) == item['bytes'] and sha(raw_file) == item['sha256'])
    selection = load(PACKET / 'selection.json')
    require(selection['namespace'] == NAMESPACE and selection['origin'] == ORIGIN
            and selection['limits'] == LIMITS and selection['approved'] is False)
    return selection


def runtime_binding():
    return {name: sha(Path(__file__).with_name(name).read_bytes())
            for name in ('modern_synthetic_canary.py', 'modern_canary_errors.py')}


def binding(stage):
    return {'schema_version': 1, 'namespace': NAMESPACE, 'stage': str(stage),
            'packet_sha256': PACKET_SHA, 'runtime_sha256': runtime_binding()}


def save(stage, state):
    atomic(stage / 'state.json', state)
    atomic(stage / 'journal.json', {'state_sha256': sha((stage / 'state.json').read_bytes()),
                                   'counts': state['counts'], 'binding': state['binding']})


def stage_packet(stage):
    """Offline exclusive staging; state and journal are created before any grant."""
    stage = Path(stage)
    require(stage.is_absolute() and stage.name == NAMESPACE)
    for path in (stage, *stage.parents):
        require(not path.is_symlink())
    packet()
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ('synthetic.xml', 'create.json', 'metadata-put.json'):
        fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write((PACKET / name).read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
    bound = binding(stage)
    atomic(stage / 'binding.json', bound)
    save(stage, {'binding': bound, 'grant_sha256': None, 'counts': dict.fromkeys(LIMITS, 0),
                 'pending': None, 'failed': False, 'completed': False, 'retry_completed': False,
                 'create_started_at': None, 'create_received_at': None,
                 'identity': None, 'uncertain_candidate_id': None, 'responses': [],
                 'attempt_diagnostics': [], 'controller_failure': None})
    return {'staged': True, 'provider_requests': 0, 'namespace': NAMESPACE,
            'packet_sha256': PACKET_SHA, 'runtime_sha256': bound['runtime_sha256']}


def datetime_aware(value):
    require(isinstance(value, str))
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise Held('Invalid canary timestamp') from None
    require(result.tzinfo is not None)
    return result


def record_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,19}', value))
    return value


def approval(stage, now):
    grant = load(stage / 'approval.json')
    expected_keys = {'schema_version', 'approved', 'approval_reference', 'executor', 'binding',
                     'limits', 'started_at', 'valid_until', 'owner', 'known_ids',
                     'exclusive_namespace_confirmed', 'deposit_write_user_reported',
                     'prior_create_allowances_permanently_spent'}
    require(isinstance(grant, dict) and set(grant) == expected_keys,
            'Separate exact parent approval required; no grant is generated here')
    require(grant['schema_version'] == 1 and grant['approved'] is True
            and isinstance(grant['approval_reference'], str) and 1 <= len(grant['approval_reference']) <= 200
            and grant['executor'] == EXECUTOR and grant['binding'] == binding(stage)
            and grant['limits'] == LIMITS and grant['exclusive_namespace_confirmed'] is True
            and grant['deposit_write_user_reported'] is True
            and grant['prior_create_allowances_permanently_spent'] is True
            and type(grant['owner']) is int and grant['owner'] > 0)
    require(isinstance(grant['known_ids'], list) and len(grant['known_ids']) <= 20000
            and len(set(grant['known_ids'])) == len(grant['known_ids']))
    for value in grant['known_ids']:
        record_id(value)
    started, expires = datetime_aware(grant['started_at']), datetime_aware(grant['valid_until'])
    require(expires == started + timedelta(seconds=1800) and started <= now < expires,
            'Exact modern canary approval window is inactive')
    return grant


def modern_wire_payload(source):
    """Project the fixed historical fictional input; never mutate its evidence.

    RDM uses free-text subjects. Only this exact canary namespace is converted;
    production/source transforms and general keyword normalization are untouched.
    The changed runtime hash binds this projection, invalidating old live grants.
    """
    require(isinstance(source, dict) and isinstance(source.get('metadata'), dict))
    require(source['metadata'].get('keywords') == [NAMESPACE]
            and 'subjects' not in source['metadata'])
    result = deepcopy(source)
    result['metadata'].pop('keywords')
    result['metadata']['subjects'] = [{'subject': NAMESPACE}]
    return result


def validate_metadata(actual, expected):
    require(isinstance(actual, dict))
    for key in ('title', 'publication_date', 'description', 'subjects'):
        require(actual.get(key) == expected[key])
    require(isinstance(actual.get('resource_type'), dict)
            and actual['resource_type'].get('id') == expected['resource_type']['id'])
    require(set(actual['resource_type']) <= {'id', 'title'})
    creators = actual.get('creators')
    require(isinstance(creators, list) and len(creators) == 1 and isinstance(creators[0], dict))
    person = creators[0].get('person_or_org')
    require(isinstance(person, dict) and all(person.get(k) == v for k, v in expected['creators'][0]['person_or_org'].items())
            and not creators[0].get('affiliations') and not person.get('identifiers'))
    require(set(creators[0]) <= {'person_or_org', 'affiliations', 'role'}
            and creators[0].get('role') in (None, {})
            and set(person) <= {'name', 'type', 'identifiers'}
            and person.get('identifiers') in (None, []))
    # Server vocabulary labels and standard empty/default fields may be returned.
    allowed = set(expected) | {'publisher', 'dates', 'subjects', 'contributors', 'rights',
                               'identifiers', 'related_identifiers', 'additional_titles',
                               'additional_descriptions', 'languages', 'locations',
                               'funding', 'references', 'version', 'sizes', 'formats'}
    require(set(actual) <= allowed)
    for key in set(actual) - set(expected) - {'publisher'}:
        require(actual[key] in (None, '', [], {}))
    require(actual.get('publisher') in (None, '', 'Zenodo'))


class Controller:
    """One exact sequence; injectable transport supports meaningful offline tests."""
    validate_stage = staticmethod(secure_stage)

    def stage_binding(self):
        return binding(self.stage)

    def __init__(self, stage, token, transport, now=None):
        self.stage = secure_stage(stage)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.plan = packet()
        require(load(self.stage / 'binding.json') == binding(self.stage))
        for name in ('synthetic.xml', 'create.json', 'metadata-put.json'):
            require((self.stage / name).read_bytes() == (PACKET / name).read_bytes())
        self.grant = approval(self.stage, self.now())
        require(isinstance(token, str) and token and token.isascii()
                and all(33 <= ord(ch) <= 126 for ch in token), 'Invalid Sandbox token format')
        self.token, self.transport = token, transport
        self.state = load(self.stage / 'state.json')
        journal = load(self.stage / 'journal.json')
        require(self.state['binding'] == binding(self.stage) and journal == {
            'state_sha256': sha((self.stage / 'state.json').read_bytes()),
            'counts': self.state['counts'], 'binding': self.state['binding']})
        require(set(self.state['counts']) == set(LIMITS) and all(type(v) is int and 0 <= v <= LIMITS[k]
                for k, v in self.state['counts'].items()))
        require(self.state['failed'] is False and self.state['pending'] is None,
                'Failed or interrupted modern stage remains held; no replay or reset')
        digest = sha((self.stage / 'approval.json').read_bytes())
        if self.state['grant_sha256'] is None:
            require(not any(self.state['counts'].values()) and not self.state['responses']
                    and self.state['identity'] is None and self.state['completed'] is False)
            self.state['grant_sha256'] = digest
            save(self.stage, self.state)
        require(self.state['grant_sha256'] == digest)
        self.initial = modern_wire_payload(load(self.stage / 'create.json'))
        self.updated = modern_wire_payload(load(self.stage / 'metadata-put.json'))
        self.content = (self.stage / 'synthetic.xml').read_bytes()
        self.key = self.plan['file_key']

    def persist(self):
        self.validate_stage(self.stage)
        save(self.stage, self.state)

    def fail(self):
        self.state['failed'] = True
        self.persist()

    def observe(self, phase, **observations):
        """Durable local observations, never evidence that bytes reached the server."""
        require(phase in {'intent', 'transport_entry', 'deadline_setup', 'request_preparation',
                          'request_prepared', 'send_call', 'adapter_entry', 'response_headers',
                          'body_read', 'response_projection', 'response_validation',
                          'response_decode', 'credential_validation', 'identity_validation',
                          'response_close', 'deadline_cleanup'})
        require(set(observations) <= {'send_call_started', 'adapter_entered',
                                     'response_seen', 'status'})
        for key, value in observations.items():
            require(type(value) is bool if key != 'status' else
                    value is None or type(value) is int and 100 <= value <= 599)
        diagnostic = self.state['attempt_diagnostics'][-1]
        diagnostic.update(phase=phase, **observations)
        self.persist()

    def capture_failure(self, error, phase=None):
        if self.state['pending'] is None:
            failure = {'phase': phase or 'outside_pending_attempt', 'exception': exception_code(error),
                       'captured_at': self.now().isoformat()}
            if self.state['controller_failure'] is None:
                self.state['controller_failure'] = failure
            elif phase in ('response_close', 'deadline_cleanup'):
                self.state['controller_failure']['cleanup_failure'] = failure
            self.fail()
            return {'controller_failure': deepcopy(self.state['controller_failure'])}
        if not self.state['attempt_diagnostics']:
            return None
        diagnostic = self.state['attempt_diagnostics'][-1]
        failure = {'phase': phase or diagnostic['phase'], 'exception': exception_code(error),
                   'captured_at': self.now().isoformat()}
        diagnostic.setdefault('failure', failure)
        if phase in ('response_close', 'deadline_cleanup') and diagnostic['failure'] != failure:
            diagnostic['cleanup_failure'] = failure
        self.fail()
        return deepcopy(diagnostic)

    def base(self):
        require(isinstance(self.state['identity'], dict))
        return '/api/records/' + record_id(self.state['identity']['id']) + '/draft'

    def filebase(self):
        return self.base() + '/files/' + quote(self.key, safe='')

    def request(self, kind, method, path, status, body=None, binary=False):
        """Spend exact action before invoking a transport; never follow response URLs."""
        require(method in ('GET', 'POST', 'PUT') and path.startswith('/api/records'))
        routes = {'create': ('POST', '/api/records'),
                  'doi': ('POST', self.base() + '/pids/doi') if kind != 'create' else None,
                  'metadata': ('PUT', self.base()) if kind != 'create' else None,
                  'init': ('POST', self.base() + '/files') if kind != 'create' else None,
                  'content': ('PUT', self.filebase() + '/content') if kind != 'create' else None,
                  'commit': ('POST', self.filebase() + '/commit') if kind != 'create' else None}
        if kind == 'get':
            require(method == 'GET' and path in (self.base(), self.base() + '/files', self.filebase(), self.filebase() + '/content'))
        else:
            require(routes.get(kind) == (method, path))
        require(self.now() < datetime_aware(self.grant['valid_until']) and self.state['counts'][kind] < LIMITS[kind])
        require(sha((self.stage / 'approval.json').read_bytes()) == self.state['grant_sha256'])
        require(self.stage_binding() == self.state['binding'])
        for name in ('synthetic.xml', 'create.json', 'metadata-put.json'):
            require((self.stage / name).read_bytes() == (PACKET / name).read_bytes())
        self.state['counts'][kind] += 1
        if kind == 'create':
            require(self.state['create_started_at'] is None and self.state['create_received_at'] is None)
            self.state['create_started_at'] = self.now().isoformat()
        self.state['pending'] = {'kind': kind, 'method': method, 'path_sha256': sha(path.encode())}
        self.state['attempt_diagnostics'].append({'action': kind, 'phase': 'intent',
            'send_call_started': False, 'adapter_entered': False,
            'response_seen': False, 'status': None})
        self.persist()
        raw = b''
        response = None
        projected = False
        try:
            # Fsync may consume the last part of the window; never dispatch after it.
            require(self.now() < datetime_aware(self.grant['valid_until']))
            self.observe('transport_entry')
            response = self.transport(method, ORIGIN + path, body,
                                      {'Accept': ACCEPT, 'Authorization': 'Bearer ' + self.token,
                                       'Content-Type': 'application/octet-stream' if binary else 'application/json'},
                                      timeout=20, allow_redirects=False, verify=True, stream=True)
            self.observe('response_headers', response_seen=True)
            observed_status = response.status_code
            self.observe('response_headers', response_seen=True,
                         status=observed_status if type(observed_status) is int
                         and 100 <= observed_status <= 599 else None)
            if kind == 'create':
                self.state['create_received_at'] = self.now().isoformat()
                self.persist()
            self.observe('body_read')
            complete = True
            for chunk in response.iter_content(chunk_size=4096):
                require(self.now() < datetime_aware(self.grant['valid_until']))
                require(isinstance(chunk, bytes))
                remaining = 65536 - len(raw)
                raw += chunk[:remaining]
                if len(chunk) > remaining:
                    complete = False
                    break
            require(self.now() < datetime_aware(self.grant['valid_until']))
            self.observe('response_projection')
            projection = response_projection(raw, response, method, self.token)
            projection.update(action=kind, body_complete=complete)
            self.state['responses'].append(projection)
            projected = True
            self.persist()
            if complete and not binary and self.token.encode() not in raw:
                # Capture safe schema flags even on HTTP400 before status rejection.
                # Never persist parsed data, messages or credential-bearing fields.
                try:
                    diagnostic_data = json.loads(raw)
                except (ValueError, RecursionError):
                    diagnostic_data = None
                if isinstance(diagnostic_data, dict) and not credential_echoed(diagnostic_data, self.token):
                    projection['validation_errors'] = validation_errors_projection(diagnostic_data)
                    self.persist()
            self.observe('response_validation')
            require(complete and response.status_code == status,
                    'Provider response failed bounded status/body contract; attempt remains spent')
            self.observe('response_decode')
            data = raw if binary and method == 'GET' else json.loads(raw)
            # A safe candidate ID is a private reconciliation handle, never adoption
            # authority. Persist it even when another response field echoes a token.
            if (kind == 'create' and isinstance(data, dict) and isinstance(data.get('id'), str)
                    and re.fullmatch(r'[1-9][0-9]{0,19}', data['id'])
                    and self.token not in data['id']):
                self.state['uncertain_candidate_id'] = data['id']
                self.persist()
            self.observe('credential_validation')
            require(self.token.encode() not in raw and not credential_echoed(data, self.token),
                    'Provider echoed credential; attempt remains spent')
            self.observe('identity_validation')
            return data
        except BaseException as error:  # noqa: BLE001 - interruption also permanently spends the attempted action
            # Pending identity/action is retained even on interruption or partial body.
            diagnostic = self.capture_failure(error)
            if response is not None and not projected:
                try:
                    projection = response_projection(raw, response, method, self.token)
                    projection.update(action=kind, body_complete=False)
                    self.state['responses'].append(projection)
                    self.persist()
                except BaseException:  # noqa: BLE001,S110 - never log arbitrary exceptions
                    pass
            raise Held('Modern canary held after attempted request; preserve private stage', diagnostic) from None
        finally:
            if response is not None:
                try:
                    response.close()
                except BaseException as error:  # noqa: BLE001 - close also cannot reopen the allowance
                    diagnostic = self.capture_failure(error, 'response_close')
                    raise Held('Modern response cleanup failed; preserve private stage', diagnostic) from None

    def acknowledge(self):
        self.state['pending'] = None
        self.persist()

    def doi(self, data, required):
        pids = data.get('pids')
        require(isinstance(pids, dict) and set(pids) <= {'doi'})
        doi = pids.get('doi')
        if 'doi' not in pids:
            require(not required)
            return None
        require(isinstance(doi, dict) and doi.get('provider') == 'datacite'
                and isinstance(doi.get('identifier'), str)
                and re.fullmatch(r'10\.5072/[A-Za-z0-9][A-Za-z0-9._;-]{0,180}', doi['identifier'])
                and set(doi) <= {'identifier', 'provider', 'client'}
                and doi.get('client') in (None, 'datacite'))
        return deepcopy(doi)

    def creation_grant(self):
        return self.grant

    def identity_fields(self, data, file_completed=False):
        """Ownership, first-draft and file identity; metadata is checked separately."""
        require(isinstance(data, dict) and ('errors' not in data or data['errors'] == []))
        rid = record_id(data.get('id'))
        require(rid not in self.grant['known_ids'] and data.get('is_published') is False
                and data.get('status') == 'draft' and type(data.get('versions', {}).get('index')) is int
                and data['versions']['index'] == 1)
        parent_id = record_id(data.get('parent', {}).get('id'))
        user = data.get('parent', {}).get('access', {}).get('owned_by', {}).get('user')
        require(isinstance(user, str) and re.fullmatch(r'[1-9][0-9]*', user) and user == str(self.grant['owner']))
        created = datetime_aware(data.get('created'))
        if self.state['identity'] is None:
            started = datetime_aware(self.state['create_started_at'])
            received = datetime_aware(self.state['create_received_at'])
            require(datetime_aware(self.creation_grant()['started_at']) <= started <= received
                    <= started + timedelta(seconds=20)
                    and started - timedelta(seconds=5) <= created <= received + timedelta(seconds=5))
        links = data.get('links')
        require(isinstance(links, dict) and links.get('self') == ORIGIN + '/api/records/' + rid + '/draft'
                and links.get('files') == ORIGIN + '/api/records/' + rid + '/draft/files')
        files = data.get('files')
        require(isinstance(files, dict) and files.get('enabled') is True and isinstance(files.get('entries'), dict))
        require(set(files['entries']) == ({self.key} if file_completed else set()))
        require(type(files.get('count')) is int and files['count'] == (1 if file_completed else 0)
                and type(files.get('total_bytes')) is int
                and files['total_bytes'] == (len(self.content) if file_completed else 0))
        identity = {'id': rid, 'parent_id': parent_id, 'created': data['created']}
        if self.state['identity'] is not None:
            require(all(identity[k] == self.state['identity'][k] for k in identity))
        if file_completed:
            entry = files['entries'][self.key]
            require(isinstance(entry, dict) and entry.get('key') == self.key
                    and type(entry.get('size')) is int and entry['size'] == len(self.content)
                    and entry.get('checksum') == 'md5:' + hashlib.md5(self.content).hexdigest())
        return identity

    def record(self, data, expected, file_completed=False, allow_no_doi=False):
        identity = self.identity_fields(data, file_completed)
        validate_metadata(data.get('metadata'), expected['metadata'])
        require(data.get('access', {}).get('record') == expected['access']['record']
                and data.get('access', {}).get('files') == expected['access']['files'])
        identity['doi'] = self.doi(data, not allow_no_doi)
        if self.state['identity'] is not None and self.state['identity']['doi'] is not None:
            require(identity['doi'] == self.state['identity']['doi'])
        return identity

    def file(self, data, completed):
        require(isinstance(data, dict) and data.get('key') == self.key
                and data.get('status') == ('completed' if completed else 'pending')
                and data.get('transfer', {}).get('type') == 'L')
        links = data.get('links')
        require(isinstance(links, dict) and links.get('self') == ORIGIN + self.filebase()
                and links.get('content') == ORIGIN + self.filebase() + '/content'
                and links.get('commit') == ORIGIN + self.filebase() + '/commit')
        if completed:
            require(type(data.get('size')) is int and data['size'] == len(self.content)
                    and data.get('checksum') == 'md5:' + hashlib.md5(self.content).hexdigest())

    def readback(self):
        self.record(self.request('get', 'GET', self.base(), 200), self.updated, True)
        self.acknowledge()
        listing = self.request('get', 'GET', self.base() + '/files', 200)
        require(isinstance(listing, dict) and isinstance(listing.get('entries'), list) and len(listing['entries']) == 1)
        self.file(listing['entries'][0], True)
        self.acknowledge()
        self.file(self.request('get', 'GET', self.filebase(), 200), True)
        self.acknowledge()
        require(self.request('get', 'GET', self.filebase() + '/content', 200, binary=True) == self.content)
        self.acknowledge()

    def run(self, retry=False):
        try:
            if retry:
                require(self.state['completed'] is True and self.state['retry_completed'] is False
                        and self.state['counts']['get'] == 4)
                self.readback()
                self.state['retry_completed'] = True
                self.persist()
            else:
                require(not self.state['completed'] and not any(self.state['counts'].values()),
                        'Only a pristine exact stage may create; use explicit unchanged retry after completion')
                created = self.request('create', 'POST', '/api/records', 201, self.initial)
                self.state['identity'] = self.record(created, self.initial, allow_no_doi=True)
                self.state['uncertain_candidate_id'] = None
                self.acknowledge()
                if self.state['identity']['doi'] is None:
                    reserved = self.request('doi', 'POST', self.base() + '/pids/doi', 201)
                    self.state['identity'] = self.record(reserved, self.initial)
                    self.acknowledge()
                update = deepcopy(self.updated)
                update['pids'] = {'doi': self.state['identity']['doi']}
                self.record(self.request('metadata', 'PUT', self.base(), 200, update), self.updated)
                self.acknowledge()
                init = self.request('init', 'POST', self.base() + '/files', 201, [{'key': self.key}])
                require(isinstance(init, dict) and isinstance(init.get('entries'), list) and len(init['entries']) == 1)
                self.file(init['entries'][0], False)
                self.acknowledge()
                self.file(self.request('content', 'PUT', self.filebase() + '/content', 200, self.content, binary=True), False)
                self.acknowledge()
                self.file(self.request('commit', 'POST', self.filebase() + '/commit', 200), True)
                self.acknowledge()
                self.readback()
                self.state['completed'] = True
                self.persist()
            return self.receipt()
        except BaseException as error:  # noqa: BLE001 - preserve pending intent on all interruptions
            if self.state['pending'] is not None or any(self.state['counts'].values()) and not self.state['completed']:
                diagnostic = self.capture_failure(error)
            else:
                diagnostic = None
            raise Held('Modern canary contract held; no automatic retry or reset', diagnostic) from None

    def receipt(self):
        return {'namespace': NAMESPACE, 'packet_sha256': PACKET_SHA, 'runtime_sha256': runtime_binding(),
                'counts': self.state['counts'], 'completed': self.state['completed'],
                'unchanged_retry': self.state['retry_completed'], 'failed': self.state['failed'],
                'identity_retained_privately': self.state['identity'] is not None,
                'responses': self.state['responses'], 'provider_requests': sum(self.state['counts'].values()),
                'request_count_semantics': 'durable_action_intents_not_confirmed_transmissions',
                'attempt_diagnostics': self.state['attempt_diagnostics'],
                'controller_failure': self.state['controller_failure']}


def _execute_controller(stage, token, controller_type, retry=False):
    """Shared approved Session route; each fixed controller validates its own ledger."""
    stage = controller_type.validate_stage(stage)
    fd = os.open(stage / 'controller.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with requests.Session() as session:
            # Keep the official Session.request environment/CA route and existing
            # adapters. Observe this instance only; never replace trusted routing.
            original_prepare = session.prepare_request
            original_send = session.send
            observed_adapters = []

            def prepared(request):
                controller.observe('request_preparation')
                result = original_prepare(request)
                controller.observe('request_prepared')
                require(result.headers.get('Authorization') == 'Bearer ' + token
                        and result.url == request.url and result.method == request.method)
                checker = getattr(controller, 'check_prepared', None)
                if checker is not None:
                    checker(result)
                require(datetime.now(timezone.utc) < datetime_aware(controller.grant['valid_until']))
                return result

            def sent(request, **options):
                require(options.get('allow_redirects') is False
                        and options.get('verify') not in (None, False, ''))
                adapter = session.get_adapter(request.url)
                require(getattr(getattr(adapter, 'max_retries', None), 'total', None) == 0,
                        'Approved transport must have zero retries; route unchanged')
                controller.observe('send_call', send_call_started=True)
                require(datetime.now(timezone.utc) < datetime_aware(controller.grant['valid_until']))
                return original_send(request, **options)

            def observed_adapter(original):
                def dispatch(*args, **kwargs):
                    controller.observe('adapter_entry', adapter_entered=True)
                    require(datetime.now(timezone.utc) < datetime_aware(controller.grant['valid_until']))
                    return original(*args, **kwargs)
                return dispatch

            session.prepare_request = prepared
            session.send = sent
            for adapter in dict.fromkeys(session.adapters.values()):
                original = adapter.send
                observed_adapters.append((adapter, original))
                adapter.send = observed_adapter(original)

            def transport(method, url, body, headers, **options):
                kwargs = {'data': body} if isinstance(body, bytes) else {'json': body}
                return session.request(method, url, headers=headers, **kwargs, **options)
            # Requests' read timeout is per read; enforce a total20s request/body wall deadline.
            original_handler = signal.getsignal(signal.SIGALRM)
            def expired(*_):
                raise WallDeadline('Modern request wall deadline expired')
            def bounded(*args, **kwargs):
                controller.observe('deadline_setup')
                remaining = (datetime_aware(load(stage / 'approval.json')['valid_until'])
                             - datetime.now(timezone.utc)).total_seconds()
                require(remaining > 0)
                signal.signal(signal.SIGALRM, expired)
                signal.setitimer(signal.ITIMER_REAL, min(20, remaining))
                return transport(*args, **kwargs)
            class DeadlineController(controller_type):
                def request(self, *args, **kwargs):
                    try:
                        return super().request(*args, **kwargs)
                    except BaseException as error:  # capture pre-intent before cleanup
                        if self.state['pending'] is None:
                            diagnostic = self.capture_failure(error)
                            raise Held('Modern pre-intent contract held; preserve private stage', diagnostic) from None
                        raise
                    finally:
                        try:
                            signal.setitimer(signal.ITIMER_REAL, 0)
                            signal.signal(signal.SIGALRM, original_handler)
                        except BaseException as error:  # noqa: BLE001 - keep initial and cleanup diagnoses
                            diagnostic = self.capture_failure(error, 'deadline_cleanup')
                            raise Held('Modern deadline cleanup failed; preserve private stage', diagnostic) from None
            try:
                controller = DeadlineController(stage, token, bounded)
                return controller.run(retry)
            finally:
                session.prepare_request = original_prepare
                session.send = original_send
                for adapter, original in observed_adapters:
                    adapter.send = original
    except BlockingIOError:
        raise Held('Modern stage already locked; no concurrent execution') from None
    finally:
        os.close(fd)


def execute(stage, token, retry=False):
    """Provider executor only, following separate approval; no account/probe requests."""
    return _execute_controller(stage, token, Controller, retry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage', 'execute', 'retry'])
    parser.add_argument('--stage', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'stage':
            result = stage_packet(args.stage)
        else:
            # No file/production fallback and no secret echo. Root never calls this path.
            result = execute(args.stage, os.environ.get('ZENODO_SANDBOX_TOKEN'), args.action == 'retry')
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Held, OSError, ValueError, KeyError, TypeError) as error:
        result = {'completed': False, 'held': True,
                  'reason': 'Separate approval or stage/transport contract failed; preserve all state'}
        if type(error) is Held and error.diagnostic is not None:
            result['diagnostic'] = error.diagnostic
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
