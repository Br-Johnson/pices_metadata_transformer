"""One Mac-only continuation of draft 612988; immutable inputs and spent intents.

No create, PID, publish, delete, redirects, automatic retries or cloud transport.
The transferred checkpoint and a fresh parent-bound grant precede token entry.
"""

import argparse
import base64
import getpass
import hashlib
import http.client
import json
import os
import platform
import re
import signal
import ssl
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'docs/handoff/modern-synthetic-canary-20261003-code-02'
NAMESPACE = 'pices-modern-synthetic-20261003-code-02'
EXECUTOR = '01a0f3ae-ee1c-7046-9b04-36d35803903c'
ORIGIN = 'https://sandbox.zenodo.org'
BASE = '/api/records/612988/draft'
KEY = NAMESPACE + '.xml'
FILE = BASE + '/files/' + KEY
PAYLOAD_SHA = '71830ca80356953b8654dd0e589eeff15b1b46c08c313b98372936c85c09da7a'
XML_SHA = '7cf966d4c1396a3dc54cfad0b049394f70da59a8e02e9ec294dab00c3a8d4c1b'
SOURCE_SHA = '0197c230248e4192866b8662fa60a4cca4b05ed0d060fc67f6a9102bb6180128'
RESULT_SHA = 'f3c68007ac6a84007c1938235f7e7c78bc0741292f11c8ddb74e4d8c55161d39'
BUNDLE_SHA = 'f2141c916b38a53168edca63f0af79b47df3e9913653f3538aba040ca9a20f7c'
MARKER_SHA = '7eeb89d71da59de6953b0a27675e666962ea22c98d3c843a9aee257613d51a93'
LIMITS = {'get': 10, 'metadata': 1, 'init': 1, 'content': 1, 'commit': 1}
TIMEOUT = 20
MAX_BYTES = 65536
STATIC = ('checkpoint.json', 'mac-result.json', 'metadata-put.json', 'synthetic.xml', 'receipt-bundle.zip')
WARNINGS = {
    'Missing uploaded files. To disable files for this record please mark it as metadata-only.',
    'Missing uploaded files.',
}


class Held(Exception):
    """Closed diagnostics: no provider text, credentials, paths or exception text."""


def require(condition):
    if not condition:
        raise Held('Canary held; preserve all evidence and spent intents')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False))


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None and result.utcoffset().total_seconds() == 0)
    return result


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value))


def secure(path, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink())
    for parent in path.parents:
        require(not parent.is_symlink())
    stat = path.stat()
    require(stat.st_mode & 0o077 == 0 and stat.st_uid == os.getuid())
    require(path.is_dir() if directory else path.is_file() and stat.st_nlink == 1)
    return path


def read(path):
    path = secure(path)
    require(path.stat().st_size <= (32 * 1024 * 1024 if path.name == 'receipt-bundle.zip' else MAX_BYTES))
    return path.read_bytes()


def write_new(path, value):
    raw = value if isinstance(value, bytes) else encode(value)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    descriptor = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fixture():
    source = (PACKET / 'metadata-put.json').read_bytes()
    xml = (PACKET / 'synthetic.xml').read_bytes()
    require(sha(source) == SOURCE_SHA and sha(xml) == XML_SHA and len(xml) == 439)
    value = parse(source)
    value['metadata']['subjects'] = [{'subject': value['metadata'].pop('keywords')[0]}]
    value['metadata']['publisher'] = 'Zenodo'
    body = json.dumps(value).encode()
    require(len(body) == 517 and sha(body) == PAYLOAD_SHA)
    return body, xml


def checkpoint(value, raw_result):
    """The Mac executor supplies this projection; parent verifies its provenance.

    This validates the closed transfer contract, not authenticity of a manually
    written projection. Parent approval must bind the independently checked bytes.
    """
    require(set(value) == {'schema_version', 'executor', 'origin', 'marker_sha256',
                          'marker_bytes', 'prior_methods', 'prior_statuses', 'before_revision',
                          'result_sha256', 'history_manifest_sha256', 'prior_intents',
                          'historical_holds_preserved', 'baseline'})
    require(value['schema_version'] == 1 and value['executor'] == EXECUTOR
            and value['origin'] == ORIGIN and value['marker_sha256'] == MARKER_SHA
            and value['marker_bytes'] == 319 and value['before_revision'] == 10
            and value['prior_methods'] == ['GET', 'PUT', 'GET']
            and value['prior_statuses'] == [200, 200, 200]
            and value['historical_holds_preserved'] is True
            and value['result_sha256'] == sha(raw_result) == RESULT_SHA)
    digest(value['history_manifest_sha256'])
    require(isinstance(parse(raw_result), dict))
    counts = value['prior_intents']
    require(isinstance(counts, dict) and counts and all(
        re.fullmatch('[a-z][a-z0-9_]{0,63}', key) and type(number) is int and number >= 0
        for key, number in counts.items()))
    base = value['baseline']
    require(set(base) == {'id', 'owner', 'parent_id', 'created', 'revision_id', 'metadata', 'access'})
    require(base['id'] == '612988' and type(base['revision_id']) is int and base['revision_id'] == 11)
    require(all(isinstance(base[key], str) and re.fullmatch('[1-9][0-9]{0,19}', base[key])
                for key in ('owner', 'parent_id')))
    instant(base['created'])
    require(isinstance(base['metadata'], dict) and all(
        isinstance(base['metadata'].get(key), str) and base['metadata'][key]
        for key in ('title', 'publisher')))
    require(isinstance(base['access'], dict) and set(base['access']) == {'record', 'files'}
            and all(base['access'][key] in ('public', 'restricted') for key in ('record', 'files')))


def binding(stage):
    return {'schema_version': 1, 'stage': str(stage), 'executor': EXECUTOR,
            'namespace': NAMESPACE, 'origin': ORIGIN,
            'runtime_sha256': sha(Path(__file__).read_bytes()),
            'inputs_sha256': {name: sha(read(stage / name)) for name in STATIC}}


def prepare(stage, transfer, result, bundle):
    stage = Path(stage)
    require(stage.is_absolute() and stage.resolve() == stage and not stage.exists())
    transfer_raw, result_raw = read(transfer), read(result)
    checkpoint(parse(transfer_raw), result_raw)
    body, xml = fixture()
    bundle = secure(bundle)
    require(bundle.stat().st_size <= 32 * 1024 * 1024)
    bundle_raw = bundle.read_bytes()
    require(sha(bundle_raw) == BUNDLE_SHA)
    stage.mkdir(mode=0o700)
    for name, raw in zip(STATIC, (transfer_raw, result_raw, body, xml, bundle_raw), strict=True):
        write_new(stage / name, raw)
    bound = binding(stage)
    write_new(stage / 'binding.json', bound)
    return {'prepared': True, 'provider_requests': 0, 'binding': bound}


def preflight(stage):
    stage = secure(stage, directory=True)
    bound = binding(stage)
    require(parse(read(stage / 'binding.json')) == bound)
    checkpoint(parse(read(stage / 'checkpoint.json')), read(stage / 'mac-result.json'))
    body, xml = fixture()
    require(read(stage / 'metadata-put.json') == body and read(stage / 'synthetic.xml') == xml
            and sha(read(stage / 'receipt-bundle.zip')) == BUNDLE_SHA)
    return bound


def approval(stage, path, now):
    bound = preflight(stage)
    raw = read(path)
    grant = parse(raw)
    require(set(grant) == {'approved', 'executor', 'binding', 'limits', 'started_at', 'expires_at',
                           'checkpoint_transfer_verified', 'mac_runtime_reviewed', 'existing_draft_only',
                           'no_create_pid_publish_delete', 'token_scope'})
    require(grant['approved'] is True and grant['executor'] == EXECUTOR and grant['binding'] == bound
            and grant['limits'] == LIMITS and grant['checkpoint_transfer_verified'] is True
            and grant['mac_runtime_reviewed'] is True and grant['existing_draft_only'] is True
            and grant['no_create_pid_publish_delete'] is True and grant['token_scope'] == 'deposit:write')
    start, end = instant(grant['started_at']), instant(grant['expires_at'])
    require(start <= now < end and 0 < (end - start).total_seconds() <= 600)
    return grant, sha(raw)


def echoed(raw, token):
    variants = {token, quote(token, safe=''), base64.b64encode(token.encode()).decode(),
                json.dumps(token)[1:-1]}
    text = raw.decode('utf-8', errors='replace')
    try:
        text += json.dumps(json.loads(raw, object_pairs_hook=list), ensure_ascii=False)
    except (ValueError, UnicodeError):
        pass
    text += unquote(text)
    return any(value in text for value in variants)


class Transport:
    """Mac stdlib TLS, no token/proxy/netrc lookup, redirects or retries."""

    def __init__(self, token):
        require(platform.system() == 'Darwin')
        self.token = token

    def request(self, method, path, body, revision, timeout=TIMEOUT):
        headers = {'Authorization': 'Bearer ' + self.token,
                   'Accept': 'application/vnd.inveniordm.v1+json',
                   'Accept-Encoding': 'identity', 'Connection': 'close'}
        if body is not None:
            headers['Content-Type'] = 'application/octet-stream' if path.endswith('/content') else 'application/json'
            headers['Content-Length'] = str(len(body))
        if revision is not None:
            headers['If-Match'] = str(revision)
        require(0 < timeout <= TIMEOUT)
        deadline = time.monotonic() + timeout
        def expired(*_):
            raise Held('Bounded request timed out; intent remains spent')
        old_handler = signal.signal(signal.SIGALRM, expired)
        old_timer = signal.setitimer(signal.ITIMER_REAL, timeout)
        connection = None
        try:
            context = ssl.create_default_context()
            remaining = deadline - time.monotonic()
            require(remaining > 0)
            connection = http.client.HTTPSConnection('sandbox.zenodo.org', timeout=remaining, context=context)
            require(time.monotonic() < deadline)
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            chunks, size = [], 0
            while True:
                left = deadline - time.monotonic()
                require(left > 0)
                if connection.sock is not None:
                    connection.sock.settimeout(left)
                chunk = response.read1(min(8192, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                require(size <= MAX_BYTES)
            return response.status, response.getheader('Content-Type', ''), b''.join(chunks)
        finally:
            signal.setitimer(signal.ITIMER_REAL, *old_timer)
            signal.signal(signal.SIGALRM, old_handler)
            if connection is not None:
                connection.close()


class Runner:
    def __init__(self, stage, grant_path, token, transport=None, now=None):
        self.stage = secure(stage, directory=True)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.grant_path = secure(grant_path)
        self.grant, self.grant_sha = approval(self.stage, self.grant_path, self.now())
        require(isinstance(token, str) and 16 <= len(token) <= 4096
                and all(33 <= ord(char) <= 126 for char in token))
        # Inspect only the explicitly transferred sanitized files; never discover credentials.
        require(all(not echoed(read(self.stage / name), token) for name in STATIC))
        self.token = token
        self.transport = transport or Transport(token)
        self.bound = self.grant['binding']
        self.base = parse(read(self.stage / 'checkpoint.json'))['baseline']
        self.body = read(self.stage / 'metadata-put.json')
        self.expected = parse(self.body)
        self.xml = read(self.stage / 'synthetic.xml')
        self.counts = dict.fromkeys(LIMITS, 0)
        self.steps = []
        self.deadline = time.monotonic() + 600
        self.phase = None
        self.last_revision = None

    def call(self, kind, method, path, expected_status, body=None, revision=None, binary=False):
        allowed = {'metadata': ('PUT', BASE), 'init': ('POST', BASE + '/files'),
                   'content': ('PUT', FILE + '/content'), 'commit': ('POST', FILE + '/commit')}
        require((kind == 'get' and method == 'GET' and path in (BASE, BASE + '/files', FILE, FILE + '/content'))
                or allowed.get(kind) == (method, path))
        require(self.phase in ('execute', 'retry') and (self.phase != 'retry' or kind == 'get'))
        require(self.counts[kind] < LIMITS[kind] and time.monotonic() < self.deadline
                and instant(self.grant['started_at']) <= self.now() < instant(self.grant['expires_at']))
        require(approval(self.stage, self.grant_path, self.now()) == (self.grant, self.grant_sha))
        if kind == 'metadata':
            require(body == self.body and revision == 11)
        elif kind == 'init':
            require(body == encode([{'key': KEY}]) and revision is None)
        elif kind == 'content':
            require(body == self.xml and revision is None)
        else:
            require(body is None and revision is None)
        self.counts[kind] += 1
        index = len(self.steps)
        stem = self.phase + '-' + str(index).zfill(2)
        intent = {'kind': kind, 'method': method, 'path': path, 'body_sha256': sha(body) if body is not None else None,
                  'if_match': revision, 'counts': self.counts.copy(), 'grant_sha256': self.grant_sha}
        write_new(self.stage / (stem + '.intent.json'), intent)
        require(approval(self.stage, self.grant_path, self.now()) == (self.grant, self.grant_sha))
        remaining = min(TIMEOUT, self.deadline - time.monotonic(),
                        (instant(self.grant['expires_at']) - self.now()).total_seconds())
        require(remaining > 0)  # Recheck after preflight and durable intent fsync.
        status, mime, raw = self.transport.request(method, path, body, revision, timeout=remaining)
        require(type(status) is int and isinstance(raw, bytes) and len(raw) <= MAX_BYTES)
        suppressed = echoed(raw, self.token)
        receipt = {'kind': kind, 'status': status, 'bytes': len(raw), 'credential_suppressed': suppressed,
                   'sha256': None if suppressed else sha(raw)}
        write_new(self.stage / (stem + '.response.json'), receipt)
        self.steps.append({'intent': sha(encode(intent)), 'response': sha(encode(receipt))})
        require(not suppressed and status == expected_status
                and time.monotonic() < self.deadline and self.now() < instant(self.grant['expires_at']))  # Includes every 3xx; never follows Location.
        require(isinstance(mime, str))
        media = mime.split(';', 1)[0].strip().lower()
        require(media in ({'application/octet-stream', 'application/xml', 'text/xml'} if binary else
                         {'application/json', 'application/vnd.inveniordm.v1+json'}))
        return raw if binary else parse(raw)

    def record(self, data, mode, revision=None):
        require(isinstance(data, dict) and data.get('id') == self.base['id']
                and data.get('created') == self.base['created'] and data.get('is_published') is False
                and data.get('status') == 'draft' and data.get('pids') == {})
        require(data.get('versions', {}).get('index') == 1 and type(data['versions']['index']) is int)
        parent = data.get('parent', {})
        require(parent.get('id') == self.base['parent_id']
                and parent.get('access', {}).get('owned_by', {}).get('user') == self.base['owner'])
        links = data.get('links', {})
        require(links.get('self') == ORIGIN + BASE and links.get('files') == ORIGIN + BASE + '/files')
        observed = data.get('revision_id')
        require(type(observed) is int and observed >= 11)
        if revision is not None:
            require(observed == revision)
        self.last_revision = observed
        actual = data.get('metadata')
        require(isinstance(actual, dict))
        if mode == 'baseline':
            require(actual == self.base['metadata'])
        else:
            wanted = self.expected['metadata']
            defaults = {'dates', 'contributors', 'rights', 'identifiers', 'related_identifiers',
                        'additional_titles', 'additional_descriptions', 'languages', 'locations',
                        'funding', 'references', 'version', 'sizes', 'formats'}
            require(set(actual) <= set(wanted) | defaults)
            require(all(actual[key] in (None, '', [], {}) for key in set(actual) - set(wanted)))
            for key in ('title', 'publication_date', 'description', 'subjects', 'publisher'):
                require(actual.get(key) == wanted[key])
            require(isinstance(actual.get('resource_type'), dict)
                    and actual['resource_type'].get('id') == 'dataset'
                    and set(actual['resource_type']) <= {'id', 'title'})
            creators = actual.get('creators')
            require(isinstance(creators, list) and len(creators) == 1 and isinstance(creators[0], dict))
            creator = creators[0]
            person = creator.get('person_or_org')
            require(set(creator) <= {'person_or_org', 'affiliations', 'role'}
                    and creator.get('affiliations') in (None, []) and creator.get('role') in (None, {})
                    and isinstance(person, dict) and set(person) <= {'name', 'type', 'identifiers'}
                    and person.get('identifiers') in (None, [])
                    and all(person.get(key) == value for key, value in wanted['creators'][0]['person_or_org'].items()))
        access = self.base['access'] if mode == 'baseline' else self.expected['access']
        require(all(data.get('access', {}).get(key) == value for key, value in access.items()))
        completed = mode == 'completed'
        files = data.get('files', {})
        require(files.get('enabled') is True and isinstance(files.get('entries'), dict)
                and set(files['entries']) == ({KEY} if completed else set())
                and type(files.get('count')) is int and files['count'] == int(completed)
                and type(files.get('total_bytes')) is int
                and files['total_bytes'] == (len(self.xml) if completed else 0))
        if completed:
            self.file(files['entries'][KEY], completed=True, links=False)
        errors = data.get('errors', [])
        require(isinstance(errors, list))
        if errors:
            require(not completed and isinstance(errors, list) and len(errors) == 1
                    and set(errors[0]) == {'field', 'messages'} and errors[0]['field'] == 'files.enabled'
                    and isinstance(errors[0]['messages'], list) and len(errors[0]['messages']) == 1
                    and errors[0]['messages'][0] in WARNINGS)

    def file(self, data, completed, links=True):
        require(isinstance(data, dict) and data.get('key') == KEY)
        if links:
            require(data.get('status') == ('completed' if completed else 'pending')
                    and data.get('transfer', {}).get('type') == 'L')
            require(all(data.get('links', {}).get(key) == ORIGIN + FILE + suffix
                        for key, suffix in (('self', ''), ('content', '/content'), ('commit', '/commit'))))
        if completed:
            require(type(data.get('size')) is int and data['size'] == len(self.xml)
                    and data.get('checksum') == 'md5:' + hashlib.md5(self.xml).hexdigest())

    def readback(self, revision=None):
        self.record(self.call('get', 'GET', BASE, 200), 'completed', revision)
        observed = self.last_revision
        listing = self.call('get', 'GET', BASE + '/files', 200)
        require(isinstance(listing, dict) and isinstance(listing.get('entries'), list) and len(listing['entries']) == 1)
        self.file(listing['entries'][0], True)
        self.file(self.call('get', 'GET', FILE, 200), True)
        require(self.call('get', 'GET', FILE + '/content', 200, binary=True) == self.xml)
        return observed

    def run(self, retry=False):
        self.phase = 'retry' if retry else 'execute'
        if retry:
            prior = parse(read(self.stage / 'execute.result.json'))
            require(prior['completed'] is True and prior['binding'] == self.bound
                    and prior['grant_sha256'] == self.grant_sha
                    and prior['counts'] == {'get': 6, 'metadata': 1, 'init': 1, 'content': 1, 'commit': 1})
            require(prior['intent_sha256'] == sha(read(self.stage / 'execute.intent.json')))
            for index, step in enumerate(prior['steps']):
                stem = 'execute-' + str(index).zfill(2)
                require(sha(read(self.stage / (stem + '.intent.json'))) == step['intent']
                        and sha(read(self.stage / (stem + '.response.json'))) == step['response'])
            require(len(prior['steps']) == 10)
            self.counts = prior['counts'].copy()
        write_new(self.stage / (self.phase + '.intent.json'),
                  {'binding': self.bound, 'grant_sha256': self.grant_sha})
        # A permanent exclusive phase intent is the lock and replay barrier.
        # Any exception/interruption leaves it spent; no reset/resume command exists.
        if retry:
            revision = self.readback(prior['revision_id'])
        else:
            self.record(self.call('get', 'GET', BASE, 200), 'baseline', 11)
            self.record(self.call('metadata', 'PUT', BASE, 200, self.body, 11), 'updated', 12)
            self.record(self.call('get', 'GET', BASE, 200), 'updated', 12)
            initialized = self.call('init', 'POST', BASE + '/files', 201, encode([{'key': KEY}]))
            require(isinstance(initialized, dict) and isinstance(initialized.get('entries'), list)
                    and len(initialized['entries']) == 1)
            self.file(initialized['entries'][0], False)
            self.file(self.call('content', 'PUT', FILE + '/content', 200, self.xml), False)
            self.file(self.call('commit', 'POST', FILE + '/commit', 200), True)
            revision = self.readback()
            require(revision >= 12)
        result = {'completed': True, 'unchanged_retry': retry, 'binding': self.bound,
                  'grant_sha256': self.grant_sha, 'counts': self.counts, 'steps': self.steps,
                  'revision_id': revision,
                  'intent_sha256': sha(read(self.stage / (self.phase + '.intent.json')))}
        write_new(self.stage / (self.phase + '.result.json'), result)
        return {'completed': True, 'unchanged_retry': retry, 'counts': self.counts,
                'result_sha256': sha(encode(result)), 'provider_mutations_this_phase': 0 if retry else 4}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'preflight', 'execute', 'retry'))
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--mac-result', type=Path)
    parser.add_argument('--grant', type=Path)
    parser.add_argument('--receipt-bundle', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            result = prepare(args.stage, args.checkpoint, args.mac_result, args.receipt_bundle)
        elif args.action == 'preflight':
            result = {'provider_requests': 0, 'binding': preflight(args.stage)}
        else:
            require(platform.system() == 'Darwin' and sys.stdin.isatty())
            approval(args.stage, args.grant, datetime.now(timezone.utc))
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                token = getpass.getpass('Sandbox token (memory only; deposit:write): ')
            result = Runner(args.stage, args.grant, token).run(args.action == 'retry')
            if args.action == 'execute':
                # Reconstruct from durable successful evidence; still no write retry.
                result = Runner(args.stage, args.grant, token).run(retry=True)
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException:
        print('{"held":true,"instruction":"Preserve all evidence and spent intents; no automatic retry/reset"}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
