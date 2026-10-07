"""Bounded modern singleton drafts, with durable attempts and read-only recovery.

Four writes at most: create, initialize, upload, commit. No metadata PUT, DOI,
publication, deletion, redirects or automatic retries. The production executor
must separately obtain a reviewed source-bound grant and duplicate/history proof.
"""

import argparse
import base64
import copy
import getpass
import hashlib
import http.client
import os
import platform
import re
import signal
import ssl
import subprocess
import sys
import time
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.mac_sandbox_canary import echoed
from scripts.modern_draft_schema import expected_empty_file_warning
from scripts.modern_response_evidence import (
    MAX_RESPONSE_BYTES,
    Response,
    diagnostic,
    normalize_response,
)
from scripts.modern_singleton import (
    Held,
    Prepared,
    compare_metadata,
    encode,
    parse,
    prepare,
    require,
    sha,
)
from scripts.path_config import OutputPaths
from scripts.production_mutations import EXCLUDED, PROTECTED
from scripts.upload_service import atomic_json, ledger_lock, read_json

ORIGIN = 'https://zenodo.org'
EXECUTOR = '01a0f3ae-ee1c-7046-9b04-36d35803903c'
LIMITS = {'get': 10, 'create': 1, 'init': 1, 'content': 1, 'commit': 1}
TIMEOUT = 20
MAX_BYTES = MAX_RESPONSE_BYTES
MIME = 'application/vnd.inveniordm.v1+json'
# zenodo.org's edge firewall answers requests that carry no User-Agent with an
# HTML 403 ("unusual traffic from your network") before they reach the API;
# the sandbox does not enforce this. Zenodo asks clients to identify themselves:
# https://blog.zenodo.org/2026/09/15/2026-09-15-stability-and-performance-updates/
USER_AGENT = 'pices-metadata-transformer/1.0 (+https://github.com/Br-Johnson/pices_metadata_transformer; johnson@psc.org)'
# An invalid header value must fail at import, never after an attempt is spent.
require(USER_AGENT.isascii() and USER_AGENT.isprintable() and USER_AGENT == USER_AGENT.strip())
KEYCHAIN_SERVICE_PATTERN = r'pices-[A-Za-z0-9._-]{1,120}'
KEYCHAIN_HELP = ('Read the production token from the macOS login Keychain item with this service '
                 'name (security find-generic-password) instead of prompting for it; never for publish')
TOKEN_HELD = ('{"held":true,"stage":"token","instruction":"No attempt was started and nothing is spent: the '
              'token stage held (missing or malformed Keychain item, no Mac terminal, or a Keychain token '
              'requested for publish); fix that and rerun"}')
KEYCHAIN_ACTIONS = frozenset({'execute', 'resume', 'readback', 'capture', 'observe', 'inventory'})
# Runtimes under which a started row may be resumed after the live runtime changed:
# the first PICES26 create (FGDC-1319) and the PICES26 draft batch (FGDC-1938).
RESUME_RUNTIMES = ('e23b81aba71ac50d348f25c60d4ac4c1d60bd88e3dc89f356d5599597d3d023c',
                   '74e3a233de0f2b56ca573a8ea3613a6c37c87a45356ec495e7ae1ded0e2e85a5')
RESUME_CLOCK_SKEW = timedelta(seconds=60)  # the provider stamps `created` on its own clock


def production_token(prompt, keychain=None, *, action):
    """Obtain the production token from the macOS Keychain or an interactive prompt.

    Both routes need a Mac terminal. The Keychain route lets the sole Mac executor
    run without anyone typing the token; the item must already exist, and only
    the listed read, draft and capture actions may use it, never publish. The value stays in memory and is
    never logged; a missing item, failed lookup or malformed value holds before
    any attempt can be spent.
    """
    require(platform.system() == 'Darwin' and sys.stdin.isatty())
    require(keychain is None or action in KEYCHAIN_ACTIONS)
    if keychain is None:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            token = getpass.getpass(prompt)
    else:
        require(isinstance(keychain, str) and re.fullmatch(KEYCHAIN_SERVICE_PATTERN, keychain) is not None)
        completed = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', keychain, '-w'],
                                   stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False)
        require(completed.returncode == 0)
        token = completed.stdout.rstrip('\r\n')
    require(isinstance(token, str) and 16 <= len(token) <= 4096 and all(33 <= ord(c) <= 126 for c in token))
    return token


BINARY_MEDIA = {'application/octet-stream', 'application/xml', 'text/xml'}


def response_media_type(value, *, binary=False):
    """Accept only the observed identical, bare binary header duplication."""
    require(isinstance(value, str) and value
            and all(32 <= ord(character) < 127 for character in value))
    if ',' in value:
        members = [member.strip().lower() for member in value.split(',')]
        require(binary and members[0] in BINARY_MEDIA
                and all(member == members[0] for member in members))
        return members[0]
    media = value.split(';', 1)[0].strip().lower()
    if binary:
        require(media in BINARY_MEDIA)
    return media


def instant(value):
    require(isinstance(value, str))
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None and result.utcoffset().total_seconds() == 0)
    return result


def identifier(value):
    require(isinstance(value, str) and re.fullmatch('[1-9][0-9]{0,19}', value))
    require(int(value) not in EXCLUDED | {pair[0] for pair in PROTECTED.values()})
    return value


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value))


def completed_on_content(row, prepared):
    """Validate the durable completion decision, never infer it from commit=0.

    This hash-bound marker records prior full validation in our trusted journal;
    it does not reconstruct the provider response. Fresh full readback is required.
    """
    require(isinstance(row, dict))
    if 'upload_completion' not in row:
        return False
    marker = row['upload_completion']
    require(isinstance(marker, dict) and set(marker) == {
        'schema_version', 'kind', 'request_index', 'response_sha256'}
        and type(marker['schema_version']) is int and marker['schema_version'] == 1
        and marker['kind'] == 'content-completed-v1'
        and type(marker['request_index']) is int and marker['request_index'] == 2)
    digest(marker['response_sha256'])
    counts, requests = row.get('counts'), row.get('requests')
    require(isinstance(counts, dict) and set(counts) == set(LIMITS)
            and all(type(counts[key]) is int and 0 <= counts[key] <= limit for key, limit in LIMITS.items())
            and all(counts[key] == 1 for key in ('create', 'init', 'content')) and counts['commit'] == 0
            and isinstance(requests, list) and len(requests) == 3 + counts['get'])
    require(isinstance(row.get('identity'), dict))
    base = '/api/records/' + identifier(row['identity'].get('id')) + '/draft'
    file = base + '/files/' + prepared.source_id + '.xml'
    expected = [
        ('create', 'POST', '/api/records', 201, sha(prepared.body)),
        ('init', 'POST', base + '/files', 201, sha(encode([{'key': prepared.source_id + '.xml'}]))),
        ('content', 'PUT', file + '/content', 200, sha(prepared.xml)),
    ]
    prior = None
    for receipt, wanted in zip(requests[:3], expected, strict=True):
        require(isinstance(receipt, dict)
                and tuple(receipt.get(key) for key in ('kind', 'method', 'path', 'http_status', 'body_sha256')) == wanted
                and receipt.get('credential_suppressed') is False and receipt.get('status') == 'uncertain'
                and type(receipt.get('bytes')) is int and 0 <= receipt['bytes'] <= MAX_BYTES)
        digest(receipt.get('response_sha256'))
        attempted = instant(receipt.get('attempted_at'))
        require(prior is None or prior <= attempted)
        prior = attempted
    require(marker['response_sha256'] == requests[2]['response_sha256'])
    require(all(isinstance(receipt, dict) and receipt.get('kind') == 'get'
                and receipt.get('method') == 'GET' and receipt.get('body_sha256') is None
                and receipt.get('path') in (base, base + '/files', file, file + '/content')
                for receipt in requests[3:]))
    return True


def read_document(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_BYTES)
    raw = path.read_bytes()
    require(len(raw) <= MAX_BYTES)
    return parse(raw), sha(raw)


def state_root(paths):
    require(paths.environment == 'production')
    path = Path(paths.uploads_registry_path).absolute().parent
    require(path == path.resolve() and all(not p.is_symlink() for p in (path, *path.parents)))
    return path


def authorize(prepared, paths, grant_path, duplicate_path, now):
    """Validate an explicitly reviewed projection, never manufacture absence.

    The approving parent must independently verify the underlying inventory and
    history receipts. This local contract does not authenticate a human signer or
    convert an old incomplete inventory into evidence of absence.
    """
    grant, grant_sha = read_document(grant_path)
    proof, proof_sha = read_document(duplicate_path)
    root = str(state_root(paths))
    require(set(grant) == {'schema_version', 'approved', 'executor', 'origin', 'binding',
                          'state_root', 'owner', 'limits', 'started_at', 'expires_at',
                          'duplicate_proof_sha256', 'reviewed_by', 'token_scope',
                          'draft_only', 'canary_receipt_sha256'})
    require(type(grant['schema_version']) is int and grant['schema_version'] == 1
            and grant['approved'] is True and grant['executor'] == EXECUTOR
            and grant['origin'] == ORIGIN and grant['binding'] == prepared.binding
            and grant['state_root'] == root and grant['limits'] == LIMITS
            and all(type(v) is int for v in grant['limits'].values())
            and grant['token_scope'] == 'deposit:write' and grant['draft_only'] is True
            and isinstance(grant['reviewed_by'], str) and grant['reviewed_by'].strip())
    require(isinstance(grant['owner'], str) and re.fullmatch('[1-9][0-9]{0,19}', grant['owner']))
    digest(grant['canary_receipt_sha256'])
    start, end = instant(grant['started_at']), instant(grant['expires_at'])
    require(start <= now < end and 0 < (end - start).total_seconds() <= 600)
    require(set(proof) == {'schema_version', 'origin', 'owner', 'binding', 'state_root',
                          'complete', 'history_reconciled', 'checked_at', 'expires_at',
                          'matched_record_ids', 'matched_dois', 'inventory_sha256',
                          'history_sha256', 'reviewed_by'})
    require(type(proof['schema_version']) is int and proof['schema_version'] == 1
            and proof['origin'] == ORIGIN and proof['owner'] == grant['owner']
            and proof['binding'] == prepared.binding and proof['state_root'] == root
            and proof['complete'] is True and proof['history_reconciled'] is True
            and proof['matched_record_ids'] == [] and proof['matched_dois'] == []
            and isinstance(proof['reviewed_by'], str) and proof['reviewed_by'].strip()
            and grant['duplicate_proof_sha256'] == proof_sha)
    checked, expiry = instant(proof['checked_at']), instant(proof['expires_at'])
    require(checked <= start <= now < end <= expiry and 0 < (expiry - checked).total_seconds() <= 3600)
    digest(proof['inventory_sha256'])
    digest(proof['history_sha256'])
    return grant, grant_sha


def bridged_preparation(json_file, paths, preparation_path):
    """The original preparation of a started row, when only the runtime has changed since.

    Every non-runtime evidence field must still match the live preparation; the
    wire and XML bytes are the live ones, which the evidence hashes pin.
    """
    prepared = prepare(json_file, paths)
    packet, _ = read_document(preparation_path)
    require(set(packet) == {'binding', 'evidence', 'provider_requests'}
            and type(packet['provider_requests']) is int and packet['provider_requests'] == 0)
    evidence = packet['evidence']
    require(isinstance(evidence, dict) and set(evidence) == set(prepared.evidence)
            and evidence['runtime_sha256'] in (prepared.evidence['runtime_sha256'], *RESUME_RUNTIMES)
            and packet['binding'] == sha(encode(evidence))
            and {k: v for k, v in evidence.items() if k != 'runtime_sha256'}
            == {k: v for k, v in prepared.evidence.items() if k != 'runtime_sha256'})
    return Prepared(prepared.source_id, prepared.body, prepared.xml, evidence, packet['binding'])


def permanent_intent(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(encode(value))
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def retain_response(journal_path, source_id, grant_sha, request_index, receipt, response, token, save):
    """Save minimal status first, then an exclusive diagnostic beside the journal.

    Sidecars keep bounded body evidence out of the existing 1 MiB journal. They
    grant no identity, reset, redirect or replay authority, even when incomplete.
    """
    response = normalize_response(response)
    evidence = diagnostic(response, token)
    receipt.update(http_status=response.status, bytes=len(response.body),
                   credential_suppressed=evidence['credential_suppressed'],
                   response_sha256=evidence['response_sha256'])
    save()
    require(re.fullmatch(r'FGDC-[1-9][0-9]*', source_id)
            and type(request_index) is int and request_index >= 0)
    digest(grant_sha)
    name = f'{journal_path.name}.{source_id}.{grant_sha}.{request_index}.response.json'
    evidence['request'] = dict(receipt)
    evidence.update(source_id=source_id, grant_sha256=grant_sha, request_index=request_index)
    permanent_intent(journal_path.parent / name, evidence)
    receipt['response_evidence'] = {'filename': name, 'sha256': sha(encode(evidence))}
    save()
    return evidence


class Transport:
    """Explicit Mac token, verified TLS and a whole-request deadline; no discovery."""

    def __init__(self, token):
        require(platform.system() == 'Darwin')
        self.token = token

    def request(self, method, path, body, *, timeout, accept=MIME):
        require(0 < timeout <= TIMEOUT)
        require(accept in (MIME, 'application/json'))
        headers = {'Authorization': 'Bearer ' + self.token, 'Accept': accept,
                   'Accept-Encoding': 'identity', 'Connection': 'close',
                   'User-Agent': USER_AGENT}
        if body is not None:
            headers['Content-Type'] = 'application/octet-stream' if path.endswith('/content') else 'application/json'
            headers['Content-Length'] = str(len(body))
        deadline = time.monotonic() + timeout
        def expired(*_):
            raise Held('Modern request timed out; attempt remains spent')
        old_handler = signal.signal(signal.SIGALRM, expired)
        old_timer = signal.setitimer(signal.ITIMER_REAL, timeout)
        connection = None
        response = None
        chunks, size = [], 0
        mime, location = '', None
        try:
            context = ssl.create_default_context()
            context.keylog_filename = None
            require(context.keylog_filename is None)
            remaining = deadline - time.monotonic()
            require(remaining > 0)
            connection = http.client.HTTPSConnection('zenodo.org', timeout=remaining, context=context)
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            mime = response.getheader('Content-Type', '')
            location = response.getheader('Location')
            while True:
                left = deadline - time.monotonic()
                require(left > 0)
                if connection.sock is not None:
                    connection.sock.settimeout(left)
                chunk = response.read1(min(8192, MAX_BYTES + 1 - size))
                if not chunk:
                    outstanding = response.length
                    if ((type(outstanding) is int and outstanding > 0)
                            or (response.chunked is True and response.chunk_left is not None)):
                        return Response(response.status, mime, b''.join(chunks), location,
                                        False, 'incomplete_body')
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_BYTES:
                    return Response(response.status, mime, b''.join(chunks)[:MAX_BYTES], location,
                                    False, 'body_limit')
            return Response(response.status, mime, b''.join(chunks), location)
        except Exception:
            if response is not None:
                return Response(response.status, mime, b''.join(chunks)[:MAX_BYTES], location,
                                False, 'read_interrupted')
            raise Held('Modern request interrupted before response headers; attempt remains spent') from None
        finally:
            signal.setitimer(signal.ITIMER_REAL, *old_timer)
            signal.signal(signal.SIGALRM, old_handler)
            if connection is not None:
                connection.close()


class Runner:
    def __init__(self, json_file, paths, grant_path, duplicate_path, token, transport=None, now=None,
                 *, preparation=None):
        self.json_file, self.paths = Path(json_file), paths
        self.grant_path, self.duplicate_path = Path(grant_path), Path(duplicate_path)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.preparation = Path(preparation) if preparation is not None else None
        self.prepared = self.preparation_now()
        self.resume_from = None
        self.resume_pending = False
        self.grant, self.grant_sha = authorize(self.prepared, paths, grant_path, duplicate_path, self.now())
        require(isinstance(token, str) and 16 <= len(token) <= 4096
                and all(33 <= ord(c) <= 126 for c in token))
        require(not any(echoed(raw, token) for raw in
                        (self.prepared.body, self.prepared.xml, encode(self.grant), self.duplicate_path.read_bytes())))
        self.token, self.transport = token, transport or Transport(token)
        self.journal_path = Path(paths.uploads_registry_path + '.modern-v1.json')
        self.intent_path = state_root(paths) / (self.prepared.source_id + '.modern-create-v1.intent.json')
        self.expected = parse(self.prepared.body)
        require(len(self.prepared.body) <= MAX_BYTES and len(self.prepared.xml) <= MAX_BYTES)
        self.key = self.prepared.source_id + '.xml'
        self.deadline = time.monotonic() + 600
        self.row = None
        self.journal = None

    def save(self):
        atomic_json(self.journal_path, self.journal)

    def preparation_now(self):
        if self.preparation is None:
            return prepare(self.json_file, self.paths)
        return bridged_preparation(self.json_file, self.paths, self.preparation)

    def current(self):
        require(self.preparation_now() == self.prepared)
        require(authorize(self.prepared, self.paths, self.grant_path, self.duplicate_path, self.now())
                == (self.grant, self.grant_sha))
        require(time.monotonic() < self.deadline)

    def load(self):
        self.current()
        # Existing or uncertain legacy identity must use a separately reviewed correction/recovery route.
        legacy = read_json(self.paths.uploads_registry_path, {})
        old_journal = read_json(self.paths.uploads_registry_path + '.mutations.json', {'targets': {}})
        require(isinstance(legacy, dict) and isinstance(old_journal, dict)
                and isinstance(old_journal.get('targets'), dict)
                and self.prepared.source_id not in legacy
                and self.prepared.source_id not in old_journal['targets'])
        self.legacy_ids = {str(value['deposition_id']) for container in (legacy, old_journal['targets'])
                           for value in container.values() if isinstance(value, dict)
                           and value.get('deposition_id') is not None}
        require(not self.journal_path.is_symlink() and not self.intent_path.is_symlink())
        self.journal = (read_document(self.journal_path)[0] if self.journal_path.exists() else
                        {'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {}})
        require(set(self.journal) == {'schema_version', 'kind', 'targets'}
                and type(self.journal['schema_version']) is int and self.journal['schema_version'] == 1
                and self.journal['kind'] == 'modern-production-draft-attempts'
                and isinstance(self.journal['targets'], dict))
        self.row = self.journal['targets'].get(self.prepared.source_id)
        seen, claims = set(), {}
        for sid, row in self.journal['targets'].items():
            require(isinstance(sid, str) and re.fullmatch(r'FGDC-[1-9][0-9]*', sid)
                    and isinstance(row, dict) and isinstance(row.get('requests'), list)
                    and isinstance(row.get('counts'), dict) and set(row['counts']) == set(LIMITS))
            require(all(isinstance(r, dict) and r.get('kind') in LIMITS for r in row['requests']))
            for kind, limit in LIMITS.items():
                require(type(row['counts'][kind]) is int and 0 <= row['counts'][kind] <= limit
                        and row['counts'][kind] == sum(r.get('kind') == kind for r in row['requests']))
            if row.get('identity') is not None:
                rid = identifier(row['identity']['id'])
                parent = identifier(row['identity']['parent_id'])
                require(row['counts']['create'] == 1 and rid != parent
                        and rid not in seen and parent not in seen
                        and rid not in self.legacy_ids and parent not in self.legacy_ids)
                seen.add(rid)
                seen.add(parent)
            candidate = row.get('untrusted_candidate_id')
            if candidate is not None:
                require(isinstance(candidate, str) and re.fullmatch('[1-9][0-9]{0,19}', candidate))
                if row.get('identity') is not None:
                    require(candidate == row['identity']['id'])
            claimed = {candidate} if candidate is not None else set()
            if row.get('identity') is not None:
                claimed.update((row['identity']['id'], row['identity']['parent_id']))
            for record_id in claimed:
                require(claims.get(record_id, sid) == sid)
                claims[record_id] = sid
        if self.row is not None:
            require(self.row['binding'] == self.prepared.binding
                    and self.row['intent_sha256'] == sha(self.intent_path.read_bytes())
                    and self.row['phase'] in ('started', 'verified'))
            if self.resume_pending:
                # The second grant is persisted only when the retained create body binds the identity.
                require(self.row['phase'] == 'started' and self.row['identity'] is None
                        and self.row.get('resume_grant_sha256') is None and self.grant_sha != self.row['grant_sha256'])
            elif self.row.get('resume_grant_sha256') is not None:
                require(self.grant_sha == self.row['resume_grant_sha256'])  # the create grant is retired
            else:
                require(self.grant_sha == self.row['grant_sha256'])
            if self.row['phase'] == 'verified':
                require(type(self.row.get('verified_revision')) is int and self.row['verified_revision'] >= 1
                        and self.row['identity'] is not None and self.row['counts']['get'] >= 5)
            require(set(self.row['counts']) == set(LIMITS) and all(
                type(self.row['counts'][k]) is int and 0 <= self.row['counts'][k] <= v for k, v in LIMITS.items()))
            completed_on_content(self.row, self.prepared)

    def routes(self):
        require(self.row is not None and self.row.get('identity') is not None)
        base = '/api/records/' + identifier(self.row['identity']['id']) + '/draft'
        return base, base + '/files/' + self.key

    def call(self, kind, method, path, status, body=None, binary=False):
        self.current()
        require(self.row is not None and kind in LIMITS)
        if 'upload_completion' in self.row:
            require(completed_on_content(self.row, self.prepared) and kind == 'get')
        if kind == 'create':
            require((method, path, status, body) == ('POST', '/api/records', 201, self.prepared.body)
                    and self.row['identity'] is None)
        else:
            base, file = self.routes()
            allowed = {'init': ('POST', base + '/files', 201, encode([{'key': self.key}])),
                       'content': ('PUT', file + '/content', 200, self.prepared.xml),
                       'commit': ('POST', file + '/commit', 200, None)}
            require((kind == 'get' and method == 'GET' and status == 200 and body is None
                     and path in (base, base + '/files', file, file + '/content'))
                    or allowed.get(kind) == (method, path, status, body))
        require(kind == 'get' or self.row['phase'] == 'started')
        require(self.row['counts'][kind] < LIMITS[kind])
        self.row['counts'][kind] += 1
        receipt = {'kind': kind, 'method': method, 'path': path,
                   'body_sha256': sha(body) if body is not None else None,
                   'attempted_at': self.now().isoformat(), 'status': 'uncertain'}
        self.row['requests'].append(receipt)
        self.save()  # File and directory fsync complete before any request.
        self.current()  # Recheck evidence, grant and deadline after durable intent.
        remaining = min(TIMEOUT, self.deadline - time.monotonic(),
                        (instant(self.grant['expires_at']) - self.now()).total_seconds())
        require(remaining > 0)
        try:
            response = self.transport.request(method, path, body, timeout=remaining)
        except Exception:
            raise Held('Modern request interrupted; attempt remains spent') from None
        response = normalize_response(response)
        evidence = retain_response(self.journal_path, self.prepared.source_id, self.grant_sha,
                                   len(self.row['requests']) - 1, receipt, response, self.token, self.save)
        observed, mime, raw = response.status, response.mime, response.body
        require(response.complete and not evidence['credential_suppressed']
                and observed == status and isinstance(mime, str))
        media = response_media_type(mime, binary=binary)
        require(media in (BINARY_MEDIA if binary else {MIME}))
        self.current()
        value = raw if binary else parse(raw)
        if kind == 'create' and isinstance(value, dict):
            candidate = value.get('id')
            if isinstance(candidate, str) and re.fullmatch('[1-9][0-9]{0,19}', candidate):
                # Evidence only: never used as a dispatch identity until full validation.
                self.row['untrusted_candidate_id'] = candidate
                self.save()
        return value

    def record(self, data, completed, revision=None, *, bind=True):
        require(isinstance(data, dict) and data.get('is_published') is False
                and data.get('status') == 'draft' and data.get('pids') == {}
                and data.get('doi') in (None, '') and data.get('parent', {}).get('pids', {}) == {}
                and data.get('versions', {}).get('index') == 1
                and type(data['versions']['index']) is int)
        identity = {'id': identifier(data.get('id')), 'parent_id': identifier(data.get('parent', {}).get('id')),
                    'owner': data.get('parent', {}).get('access', {}).get('owned_by', {}).get('user'),
                    'created': data.get('created')}
        require(identity['owner'] == self.grant['owner'])
        require(identity['id'] != identity['parent_id'])
        created = instant(identity['created'])
        if self.row['identity'] is None:
            since = self.resume_from or instant(self.grant['started_at'])
            require(not completed and since <= created <= self.now())
            require(identity['id'] not in self.legacy_ids and identity['parent_id'] not in self.legacy_ids)
            require(all(other.get('untrusted_candidate_id') not in (identity['id'], identity['parent_id'])
                        for sid, other in self.journal['targets'].items() if sid != self.prepared.source_id))
            require(all(not ({other['identity']['id'], other['identity']['parent_id']}
                            & {identity['id'], identity['parent_id']})
                        for sid, other in self.journal['targets'].items()
                        if sid != self.prepared.source_id and other.get('identity')))
        else:
            require(identity == self.row['identity'])
        base = '/api/records/' + identity['id'] + '/draft'
        require(data.get('links', {}).get('self') == ORIGIN + base
                and data.get('links', {}).get('files') == ORIGIN + base + '/files')
        observed = data.get('revision_id')
        require(type(observed) is int and observed >= 1)
        if revision is not None:
            require(observed == revision)
        compare_metadata(data.get('metadata'), self.expected['metadata'])
        access = data.get('access', {})
        require(access.get('record') == 'public' and access.get('files') == 'restricted')
        files = data.get('files', {})
        require(files.get('enabled') is True and isinstance(files.get('entries'), dict)
                and set(files['entries']) == ({self.key} if completed else set())
                and type(files.get('count')) is int and files['count'] == int(completed)
                and type(files.get('total_bytes')) is int
                and files['total_bytes'] == (len(self.prepared.xml) if completed else 0))
        if completed:
            self.file(files['entries'][self.key], True, links=False)
            require(data.get('errors', []) == [])
        else:
            expected_empty_file_warning(data)
        if self.row['identity'] is None:
            if not bind:
                return observed  # rehearsal: every check passed, nothing recorded
            self.row['identity'] = identity
            self.row['create_revision'] = observed
            self.save()  # Only a fully validated create response can bind identity.
        require(observed >= self.row['create_revision'])
        return observed

    def file(self, data, completed, links=True):
        require(isinstance(data, dict) and data.get('key') == self.key)
        if links:
            _, file = self.routes()
            require(data.get('status') == ('completed' if completed else 'pending')
                    and data.get('transfer', {}).get('type') == 'L')
            require(all(data.get('links', {}).get(k) == ORIGIN + file + suffix
                        for k, suffix in (('self', ''), ('content', '/content'), ('commit', '/commit'))))
        if completed:
            require(type(data.get('size')) is int and data['size'] == len(self.prepared.xml)
                    and data.get('checksum') == 'md5:' + hashlib.md5(self.prepared.xml, usedforsecurity=False).hexdigest())

    def readback(self, revision=None):
        base, file = self.routes()
        observed = self.record(self.call('get', 'GET', base, 200), True, revision)
        listing = self.call('get', 'GET', base + '/files', 200)
        require(isinstance(listing, dict) and isinstance(listing.get('entries'), list)
                and len(listing['entries']) == 1)
        self.file(listing['entries'][0], True)
        self.file(self.call('get', 'GET', file, 200), True)
        require(self.call('get', 'GET', file + '/content', 200, binary=True) == self.prepared.xml)
        # Bracket component reads with the same metadata/identity/revision.
        self.record(self.call('get', 'GET', base, 200), True, observed)
        return observed

    def saved_create(self):
        """The retained, hash-bound 201 body of the single create request of a started row."""
        receipt = self.row['requests'][0]
        name = f"{self.journal_path.name}.{self.prepared.source_id}.{self.row['grant_sha256']}.0.response.json"
        evidence, evidence_sha = read_document(self.journal_path.parent / name)
        require(receipt.get('response_evidence', {}).get('sha256') == evidence_sha)
        require(receipt.get('kind') == 'create' and receipt.get('http_status') == 201
                and receipt.get('status') == 'uncertain' and receipt.get('body_sha256') == sha(self.prepared.body)
                and receipt.get('response_evidence', {}).get('filename') == name
                and evidence.get('kind') == 'modern-response-diagnostic-v1'
                and evidence.get('source_id') == self.prepared.source_id
                and evidence.get('grant_sha256') == self.row['grant_sha256'] and evidence.get('request_index') == 0
                and evidence.get('http_status') == 201 and evidence.get('response_complete') is True
                and evidence.get('body_status') == 'complete' and evidence.get('credential_suppressed') is False
                and evidence.get('retained_bytes') == evidence.get('received_bytes')
                and evidence.get('response_sha256') == receipt.get('response_sha256'))
        body = base64.b64decode(evidence['body_base64'], validate=True)
        require(len(body) == evidence['retained_bytes'] and sha(body) == evidence['retained_sha256']
                == receipt['response_sha256'])
        return parse(body)

    def complete_upload(self):
        base, file = self.routes()
        initialized = self.call('init', 'POST', base + '/files', 201, encode([{'key': self.key}]))
        require(isinstance(initialized, dict) and isinstance(initialized.get('entries'), list)
                and len(initialized['entries']) == 1)
        self.file(initialized['entries'][0], False)
        uploaded = self.call('content', 'PUT', file + '/content', 200, self.prepared.xml)
        require(isinstance(uploaded, dict))
        completed = uploaded.get('status') == 'completed'
        self.file(uploaded, completed)
        if completed:
            self.row['upload_completion'] = {
                'schema_version': 1, 'kind': 'content-completed-v1', 'request_index': 2,
                'response_sha256': self.row['requests'][2]['response_sha256']}
            require(completed_on_content(self.row, self.prepared))
            self.save()  # Persist the validated branch before any readback.
        else:
            self.file(self.call('commit', 'POST', file + '/commit', 200), True)
        return self.readback()

    def resumable(self, candidate):
        """The retained 201 body of a started row that may be completed under this grant."""
        require(self.row is not None and self.row['phase'] == 'started'
                and self.row['identity'] is None and self.row.get('untrusted_candidate_id') is not None
                and self.row.get('resume_grant_sha256') is None and self.row['grant_sha256'] != self.grant_sha
                and self.row['counts'] == {'get': 0, 'create': 1, 'init': 0, 'content': 0, 'commit': 0}
                and len(self.row['requests']) == 1 and self.intent_path.exists())
        require(isinstance(candidate, str) and candidate == self.row['untrusted_candidate_id'])
        saved = self.saved_create()
        require(identifier(saved.get('id')) == candidate)
        self.resume_from = instant(self.row['requests'][0]['attempted_at']) - RESUME_CLOCK_SKEW
        return saved

    def rehearse_resume(self, candidate):
        """Every resume validation against the retained body, with no request and no write."""
        self.resume_pending = True
        with ledger_lock(self.paths):
            self.load()
            saved = self.resumable(candidate)
            row, journal = copy.deepcopy(self.row), copy.deepcopy(self.journal)
            self.record(saved, False, bind=False)
            require(self.row == row and self.journal == journal)
        return {'resume_rehearsed': True, 'candidate': candidate, 'provider_requests': 0}

    def run(self, read_only=False, resume=None):
        self.resume_pending = resume is not None
        with ledger_lock(self.paths):
            self.load()
            if resume is not None:
                # A started row whose create returned 201 but whose response validation
                # held: bind the identity from the retained body under a fresh grant. The
                # second grant is persisted by the binding save; a refusal leaves the row
                # exactly as it was, still resumable.
                require(not read_only)
                saved = self.resumable(resume)
                self.row['resume_grant_sha256'] = self.grant_sha
                self.row['resumed_at'] = self.now().isoformat()
                self.record(saved, False)
                revision = self.complete_upload()
            elif read_only:
                require(self.row is not None and self.row['identity'] is not None)
                completed = completed_on_content(self.row, self.prepared)
                require(all(self.row['counts'][kind] == 1 for kind in ('create', 'init', 'content'))
                        and self.row['counts']['commit'] == int(not completed))
                require(self.row['counts']['get'] + 5 <= LIMITS['get'])
                revision = self.readback(self.row.get('verified_revision'))
            else:
                require(self.row is None and not self.intent_path.exists())
                intent = {'schema_version': 1, 'binding': self.prepared.binding,
                          'grant_sha256': self.grant_sha, 'state_root': str(state_root(self.paths))}
                permanent_intent(self.intent_path, intent)
                self.row = {'binding': self.prepared.binding, 'grant_sha256': self.grant_sha,
                            'intent_sha256': sha(encode(intent)), 'identity': None,
                            'phase': 'started', 'counts': dict.fromkeys(LIMITS, 0), 'requests': []}
                self.journal['targets'][self.prepared.source_id] = self.row
                self.save()
                self.record(self.call('create', 'POST', '/api/records', 201, self.prepared.body), False)
                revision = self.complete_upload()
            self.row.update(phase='verified', verified_revision=revision)
            self.save()
            return {'draft_verified': True, 'read_only': read_only, 'binding': self.prepared.binding,
                    'identity': self.row['identity'], 'revision_id': revision,
                    'counts': self.row['counts'].copy(), 'publication_approved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'preflight', 'execute', 'resume', 'readback'))
    parser.add_argument('--json-file', required=True, type=Path)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--grant', type=Path)
    parser.add_argument('--duplicate-proof', type=Path)
    parser.add_argument('--token-keychain', metavar='SERVICE', help=KEYCHAIN_HELP)
    parser.add_argument('--preparation', type=Path,
                        help='Original preparation packet of a started row whose runtime has changed (resume)')
    parser.add_argument('--resume-candidate', metavar='RECORD_ID',
                        help='The started row\'s own draft id that resume or its preflight rehearsal completes')
    args = parser.parse_args()
    try:
        paths = OutputPaths(args.output_dir, 'production')
        resuming = args.action == 'resume' or (args.action == 'preflight' and args.resume_candidate is not None)
        require((args.preparation is not None) == resuming and (args.resume_candidate is not None) == resuming)
        prepared = (bridged_preparation(args.json_file, paths, args.preparation) if args.preparation is not None
                    else prepare(args.json_file, paths))
        if args.action == 'prepare':
            result = {'binding': prepared.binding, 'evidence': prepared.evidence, 'provider_requests': 0}
        else:
            require(args.grant is not None and args.duplicate_proof is not None)
            authorize(prepared, paths, args.grant, args.duplicate_proof, datetime.now(timezone.utc))
            if args.action == 'preflight':
                result = {'binding': prepared.binding, 'provider_requests': 0}
                if resuming:
                    runner = Runner(args.json_file, paths, args.grant, args.duplicate_proof,
                                    'dummy-preflight-token-only', object(), preparation=args.preparation)
                    result.update(runner.rehearse_resume(args.resume_candidate))
            else:
                try:
                    token = production_token('Production token (memory only; deposit:write): ',
                                             args.token_keychain, action=args.action)
                except BaseException:
                    print(TOKEN_HELD)
                    return 1
                runner = Runner(args.json_file, paths, args.grant, args.duplicate_proof, token,
                                preparation=args.preparation)
                result = runner.run(read_only=args.action == 'readback',
                                    resume=args.resume_candidate if args.action == 'resume' else None)
        print(encode(result).decode())
        return 0
    except BaseException:
        print('{"held":true,"instruction":"Preserve all evidence and spent attempts; no reset or automatic retry"}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
