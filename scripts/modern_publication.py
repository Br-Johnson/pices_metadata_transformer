"""Finite modern singleton publication with immutable draft history and bounded I/O.

Only a verified compatible-runtime draft can cross the versioned bridge. A fresh
read-only capture precedes explicit QA and human release. A PICES review is set
before submission can publish; recovery never dispatches mutations. Accepted
membership and complete readback, not a pending request, establish completion.
"""

import argparse
import base64
import copy
import getpass
import hashlib
import platform
import re
import sys
import time
import uuid
import warnings
from datetime import datetime, timezone
from pathlib import Path

from scripts import modern_singleton_executor as draft
from scripts.mac_sandbox_canary import echoed
from scripts.modern_singleton import (
    CITATION_ORG_POLICY,
    DIRECT_POLICY,
    EXTENSION_POLICY,
    EXXON_POLICY,
    INSTITUTION_POLICY,
    PICES_POLICY,
    POLICY,
    REVIEWED_CREATORS_POLICY,
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
from scripts.production_mutations import PROTECTED, doi_key
from scripts.release_manifest import validate_release
from scripts.upload_service import atomic_json, ledger_lock, read_json

PR34_RUNTIME = '0f0a537dde0d6970ce6c64aad1169cf9ebb290cbcf7b527ab3917ace1393fff5'
PR35_RUNTIME = '30092eff4631d7543f24b8ecabf0a85c294da8fcc4c308ecc97224e38b58b270'
PR36_RUNTIME = '046a7257ed29e6c5b09c8956455ee3dbf0b811fad5ee9e3b36cef493119ea6c4'
PR37_RUNTIME = '7e93a95ba980918cf687221a56bc4a60eb5b219ac53406a8b2175b0f46e0d90a'
PR38_RUNTIME = '1ac72000a7697bedef5b6e76ca0a28252a85f36bb0529a7e521c68aa4177d9e2'
PR39_RUNTIME = '7c3e7184f490cc4e43743f12fa831d58e6b79d8e36f93bd7e9c92a2a637f57be'
PR40_RUNTIME = '999c23a83d9fbcb800f612c150708c474069f9baf0e9ef192e39107cd3633ec9'
PR41_RUNTIME = 'a23fa32cd7312616100a0d34e9b328234a98cd3cd173821d55d494f326ac85d4'
PR42_RUNTIME = 'd09495acd462e7a51c3c1344265758ed8482256e9d901c05b64711734316ef2d'
PR43_RUNTIME = '31dd71eb8bfe8c87f50d7ff3c4cbc22f045d926c099f81c21db2dc6df70614a2'
PR44_RUNTIME = 'd89389d398ddc93f2e0e9fe817130c0b5a01592a147b499f975ad52615bc94a1'
PR45_RUNTIME = 'd1055bf636fe04299be2b670af1b3aeefcae6c64149996b85cea469b672ea4f2'
PR46_RUNTIME = '62eeaad6183950bae245937f79a7d4e16df546a6635d9ea4dfbb7c4c2bf5902d'
REVIEWED194_RUNTIME = '6cc86a1740fcd93e65d42e21b1c199c160974c607be54db71f43d3e25466349e'
CAPTURE_LIMITS = {'get': 5}
PUBLISH_LIMITS = {'get': 22, 'review': 1, 'submit': 1}
JSON = 'application/json'
CAPTURE_TOKEN_SCOPE = 'deposit:write'
PUBLICATION_TOKEN_SCOPE = 'deposit:write deposit:actions'


def canonical_uuid(value):
    require(isinstance(value, str) and str(uuid.UUID(value)) == value)
    return value


def request_identifier(value):
    # Retained request schema establishes an opaque string, not a UUID contract.
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value))
    return value


def validate_request(value, bound, community, request_id, *, created=False):
    require(isinstance(value, dict) and request_identifier(value.get('id')) == request_id
            and value.get('type') == 'community-submission'
            and value.get('topic') == {'record': bound['identity']['id']}
            and value.get('receiver') == {'community': community['id']}
            and value.get('created_by') == {'user': bound['identity']['owner']}
            and type(value.get('is_open')) is bool and type(value.get('is_closed')) is bool
            and (value.get('status'), value.get('is_open'), value.get('is_closed'))
                in ((('created', False, False),) if created else
                    (('submitted', True, False), ('accepted', False, True))))


def bridge(json_file, paths, preparation_path, old_grant_path, old_duplicate_path):
    """Validate old requests at their old times, never revive the old grant.

    PR34/35 cover original19; PR36 also covers86; PR37 adds2628; PR38 adds412.
    Every nonruntime field must match. Original files and receipts stay intact.
    """
    prepared = prepare(json_file, paths)
    packet, packet_sha = draft.read_document(preparation_path)
    require(set(packet) == {'binding', 'evidence', 'provider_requests'}
            and type(packet['provider_requests']) is int and packet['provider_requests'] == 0)
    evidence = packet['evidence']
    compatible = {prepared.evidence['runtime_sha256']}
    if prepared.evidence['policy'] == POLICY and prepared.evidence['schema_version'] == 1:
        compatible.update((PR34_RUNTIME, PR35_RUNTIME, PR36_RUNTIME, PR37_RUNTIME, PR38_RUNTIME))
    elif prepared.evidence['policy'] == EXTENSION_POLICY and prepared.evidence['schema_version'] == 2:
        compatible.update((PR36_RUNTIME, PR37_RUNTIME, PR38_RUNTIME))
    elif prepared.evidence['policy'] == DIRECT_POLICY and prepared.evidence['schema_version'] == 3:
        compatible.update((PR37_RUNTIME, PR38_RUNTIME))
    elif prepared.evidence['policy'] == EXXON_POLICY and prepared.evidence['schema_version'] == 4:
        compatible.add(PR38_RUNTIME)
    if prepared.evidence['policy'] in (POLICY, EXTENSION_POLICY, DIRECT_POLICY, EXXON_POLICY):
        compatible.update((PR39_RUNTIME, PR40_RUNTIME))
    if prepared.evidence['policy'] in (POLICY, EXTENSION_POLICY, DIRECT_POLICY, EXXON_POLICY, PICES_POLICY):
        compatible.add(PR41_RUNTIME)
    if prepared.evidence['policy'] in (POLICY, EXTENSION_POLICY, DIRECT_POLICY, EXXON_POLICY,
                                     PICES_POLICY, INSTITUTION_POLICY):
        compatible.update((PR42_RUNTIME, PR43_RUNTIME, PR44_RUNTIME, PR45_RUNTIME))
    if (prepared.evidence['policy'], prepared.evidence['schema_version']) in (
            (POLICY, 1), (EXTENSION_POLICY, 2), (DIRECT_POLICY, 3), (EXXON_POLICY, 4),
            (PICES_POLICY, 5), (INSTITUTION_POLICY, 6), (CITATION_ORG_POLICY, 7)):
        compatible.add(PR46_RUNTIME)
    if (prepared.evidence['policy'], prepared.evidence['schema_version']) in (
            (POLICY, 1), (EXTENSION_POLICY, 2), (DIRECT_POLICY, 3), (EXXON_POLICY, 4),
            (PICES_POLICY, 5), (INSTITUTION_POLICY, 6), (CITATION_ORG_POLICY, 7),
            (REVIEWED_CREATORS_POLICY, 8)):
        compatible.add(REVIEWED194_RUNTIME)
    require(isinstance(evidence, dict) and set(evidence) == set(prepared.evidence)
            and evidence['runtime_sha256'] in compatible
            and packet['binding'] == sha(encode(evidence))
            and {k: v for k, v in evidence.items() if k != 'runtime_sha256'}
            == {k: v for k, v in prepared.evidence.items() if k != 'runtime_sha256'})
    old = Prepared(prepared.source_id, prepared.body, prepared.xml, evidence, packet['binding'])
    root = draft.state_root(paths)
    history, _ = draft.read_document(paths.uploads_registry_path + '.modern-v1.json')
    require(history.get('schema_version') == 1 and history.get('kind') == 'modern-production-draft-attempts'
            and isinstance(history.get('targets'), dict))
    row = history['targets'].get(prepared.source_id)
    require(isinstance(row, dict) and row.get('phase') == 'verified'
            and row.get('binding') == old.binding and isinstance(row.get('identity'), dict)
            and type(row.get('create_revision')) is int and row['create_revision'] >= 1
            and type(row.get('verified_revision')) is int and row['verified_revision'] >= row['create_revision'])
    identity = row['identity']
    require(set(identity) == {'id', 'parent_id', 'owner', 'created'}
            and draft.identifier(identity['id']) != draft.identifier(identity['parent_id'])
            and row.get('untrusted_candidate_id') == identity['id'])
    base = '/api/records/' + identity['id'] + '/draft'
    file = base + '/files/' + prepared.source_id + '.xml'
    completed = draft.completed_on_content(row, prepared)
    # Historical clients could emit only the marker-free four-write transcript.
    require(not completed or evidence['runtime_sha256'] in
            (prepared.evidence['runtime_sha256'], PR39_RUNTIME, PR40_RUNTIME, PR41_RUNTIME, PR42_RUNTIME, PR43_RUNTIME, PR44_RUNTIME, PR45_RUNTIME, PR46_RUNTIME, REVIEWED194_RUNTIME))
    writes = [('create', 'POST', '/api/records', 201, sha(prepared.body)),
              ('init', 'POST', base + '/files', 201, sha(encode([{'key': prepared.source_id + '.xml'}]))),
              ('content', 'PUT', file + '/content', 200, sha(prepared.xml)),
              ('commit', 'POST', file + '/commit', 200, None)]
    if completed:
        writes = writes[:3]
    reads = [('get', 'GET', p, 200, None) for p in (base, base + '/files', file, file + '/content', base)]
    requests = row.get('requests')
    require(isinstance(requests, list) and len(requests) in (len(writes) + 5, len(writes) + 10)
            and row.get('counts') == dict(get=len(requests) - len(writes), create=1, init=1, content=1,
                                         commit=int(not completed))
            and all(type(v) is int for v in row['counts'].values()))
    wanted = writes + reads * ((len(requests) - len(writes)) // 5)
    grant_sha = None
    prior = None
    for receipt, expectation in zip(requests, wanted, strict=True):
        require(isinstance(receipt, dict)
                and tuple(receipt.get(k) for k in ('kind', 'method', 'path', 'http_status', 'body_sha256')) == expectation
                and receipt.get('credential_suppressed') is False and receipt.get('status') == 'uncertain'
                and type(receipt.get('bytes')) is int and 0 <= receipt['bytes'] <= draft.MAX_BYTES)
        draft.digest(receipt.get('response_sha256'))
        attempted = draft.instant(receipt.get('attempted_at'))
        require(prior is None or prior <= attempted)
        prior = attempted
        grant, grant_sha = draft.authorize(old, paths, old_grant_path, old_duplicate_path, attempted)
        require(identity['owner'] == grant['owner'] and row.get('grant_sha256') == grant_sha
                and draft.instant(grant['started_at']) <= draft.instant(identity['created'])
                < draft.instant(grant['expires_at']))
        # The create receipt precedes the request. The following init receipt is
        # the first retained time known to follow successful identity validation.
        if receipt['kind'] != 'create':
            require(draft.instant(identity['created']) <= attempted)
    intent_path = root / (prepared.source_id + '.modern-create-v1.intent.json')
    intent, intent_sha = draft.read_document(intent_path)
    require(intent == {'schema_version': 1, 'binding': old.binding, 'grant_sha256': grant_sha,
                       'state_root': str(root)} and row.get('intent_sha256') == intent_sha)
    value = {'schema_version': 1, 'kind': 'modern-singleton-bridge-v1',
             'preparation_binding': prepared.binding, 'original_preparation_binding': old.binding,
             'original_runtime_sha256': evidence['runtime_sha256'],
             'runtime_sha256': prepared.evidence['runtime_sha256'],
             'preparation_packet_sha256': packet_sha, 'draft_row_sha256': sha(encode(row)),
             'create_intent_sha256': intent_sha, 'grant_sha256': grant_sha,
             'identity': identity, 'verified_revision': row['verified_revision'], 'state_root': str(root)}
    value['binding'] = sha(encode(value))
    return prepared, value


def draft_validator(prepared, bound):
    """Reuse the exact PR34 wire validator without construction, I/O or adoption."""
    validator = object.__new__(draft.Runner)
    validator.prepared = prepared
    validator.expected = parse(prepared.body)
    validator.key = prepared.source_id + '.xml'
    validator.grant = {'owner': bound['identity']['owner']}
    validator.row = {'identity': bound['identity'], 'create_revision': 1}
    return validator


def routes(prepared, bound, published=False):
    base = '/api/records/' + bound['identity']['id'] + ('' if published else '/draft')
    file = base + '/files/' + prepared.source_id + '.xml'
    return [base, base + '/files', file, file + '/content', base]


def validate_snapshot(prepared, bound, snapshot):
    require(isinstance(snapshot, dict) and set(snapshot) == {'schema_version', 'kind', 'bridge_binding',
            'identity', 'revision_id', 'captured_at', 'responses'}
            and type(snapshot['schema_version']) is int and snapshot['schema_version'] == 1
            and snapshot['kind'] == 'modern-draft-snapshot-v1' and snapshot['bridge_binding'] == bound['binding']
            and snapshot['identity'] == bound['identity'] and snapshot['revision_id'] == bound['verified_revision']
            and type(snapshot['revision_id']) is int)
    draft.instant(snapshot['captured_at'])
    require(isinstance(snapshot['responses'], list) and len(snapshot['responses']) == 5)
    values = []
    for index, (receipt, path) in enumerate(zip(snapshot['responses'], routes(prepared, bound), strict=True)):
        require(isinstance(receipt, dict) and set(receipt) == {'method', 'path', 'http_status', 'media_type',
                'body_base64', 'response_sha256'} and receipt['method'] == 'GET' and receipt['path'] == path
                and type(receipt['http_status']) is int and receipt['http_status'] == 200)
        raw = base64.b64decode(receipt['body_base64'], validate=True)
        require(len(raw) <= draft.MAX_BYTES and sha(raw) == receipt['response_sha256'])
        require(receipt['media_type'] in ({'application/octet-stream', 'application/xml', 'text/xml'}
                                        if index == 3 else {draft.MIME}))
        values.append(raw if index == 3 else parse(raw))
    validator = draft_validator(prepared, bound)
    validator.record(values[0], True, bound['verified_revision'])
    validator.record(values[4], True, bound['verified_revision'])
    require(all(value.get('parent', {}).get('communities', {}).get('ids', []) == []
                and 'review' not in value.get('parent', {})
                and 'review' not in value
                for value in (values[0], values[4])))
    require(isinstance(values[1], dict) and isinstance(values[1].get('entries'), list)
            and len(values[1]['entries']) == 1)
    validator.file(values[1]['entries'][0], True)
    validator.file(values[2], True)
    require(file_identity(values[1]['entries'][0]) == file_identity(values[2]))
    require(values[3] == prepared.xml)
    return values


def file_identity(value):
    # Standalone object identities, distinct from embedded record file row IDs.
    return {k: canonical_uuid(value.get(k)) for k in ('file_id', 'version_id', 'bucket_id')}


def pids(data):
    values = data.get('pids', {})
    parent = data.get('parent', {}).get('pids', {})
    require(isinstance(values, dict) and set(values) == {'doi', 'oai'}
            and isinstance(parent, dict) and set(parent) == {'doi'})
    for value in (values['doi'], parent['doi']):
        require(isinstance(value, dict) and value.get('provider') == 'datacite')
        require(doi_key(value.get('identifier')) is not None)
    require(isinstance(values['oai'], dict) and values['oai'].get('provider') == 'oai'
            and isinstance(values['oai'].get('identifier'), str)
            and values['oai']['identifier'] == 'oai:zenodo.org:' + data['id'])
    require(doi_key(values['doi']['identifier']) != doi_key(parent['doi']['identifier']))
    require(data.get('doi') in (None, '', values['doi']['identifier']))
    return {'record': copy.deepcopy(values), 'parent': copy.deepcopy(parent)}


def published_record(data, prepared, bound, started, now, community, baseline=None):
    require(isinstance(data, dict) and data.get('is_published') is True and data.get('status') == 'published'
            and data.get('id') == bound['identity']['id']
            and data.get('parent', {}).get('id') == bound['identity']['parent_id']
            and data.get('parent', {}).get('access', {}).get('owned_by', {}).get('user') == bound['identity']['owner']
            and type(data.get('revision_id')) is int and data['revision_id'] >= 1
            and type(data.get('versions', {}).get('index')) is int and data['versions']['index'] == 1
            and data.get('errors', []) == [])
    created = draft.instant(data.get('created'))
    # Published records have their own created/revision values; draft history is retained separately.
    require(started <= created <= now)
    base = routes(prepared, bound, True)[0]
    require(data.get('links', {}).get('self') == draft.ORIGIN + base
            and data.get('links', {}).get('files') == draft.ORIGIN + base + '/files')
    compare_metadata(data.get('metadata'), parse(prepared.body)['metadata'])
    require(data.get('access', {}).get('record') == 'public' and data['access'].get('files') == 'restricted')
    key = prepared.source_id + '.xml'
    files = data.get('files', {})
    require(files.get('enabled') is True and isinstance(files.get('entries'), dict)
            and set(files['entries']) == {key} and type(files.get('count')) is int and files['count'] == 1
            and type(files.get('total_bytes')) is int and files['total_bytes'] == len(prepared.xml))
    published_file(files['entries'][key], prepared, bound, links=False)
    membership = data.get('parent', {}).get('communities', {})
    communities = membership.get('ids')
    expected = [community['id']] + ([community['parent_id']] if community['parent_id'] else [])
    require(isinstance(communities, list) and all(isinstance(v, str) for v in communities)
            and sorted(communities) == sorted(expected) and membership.get('default') == community['id']
            and 'review' not in data.get('parent', {}) and 'review' not in data)
    observed = {'created': data['created'], 'revision_id': data['revision_id'], 'pids': pids(data)}
    if baseline is not None:
        require(observed == baseline)
    return observed, communities


def published_file(data, prepared, bound, links=True):
    require(isinstance(data, dict) and data.get('key') == prepared.source_id + '.xml'
            and type(data.get('size')) is int and data['size'] == len(prepared.xml)
            and data.get('checksum') == 'md5:' + hashlib.md5(prepared.xml, usedforsecurity=False).hexdigest())
    if links:
        file = routes(prepared, bound, True)[2]
        require(data.get('status') == 'completed'
                and all(data.get('links', {}).get(k) == draft.ORIGIN + file + suffix
                        for k, suffix in (('self', ''), ('content', '/content'))))


def collision_check(paths, prepared, bound, claims=()):
    """Reject record, parent, candidate and DOI claims across all maintained lanes."""
    sid = prepared.source_id
    own_ids = {bound['identity']['id'], bound['identity']['parent_id']}
    own_dois = {doi_key(d) for d in claims}
    require(None not in own_dois)
    protected_dois = {doi_key('10.5281/zenodo.' + str(v[0])) for v in PROTECTED.values()}
    require(not own_dois & protected_dois)
    legacy = read_json(paths.uploads_registry_path, {})
    journal = read_json(paths.uploads_registry_path + '.mutations.json', {'targets': {}})
    modern = read_json(paths.uploads_registry_path + '.modern-v1.json', {'targets': {}})
    publication = read_json(paths.uploads_registry_path + '.modern-publication-v1.json', {'targets': {}})
    require(all(isinstance(x, dict) for x in (legacy, journal, modern, publication)))
    for container, is_legacy in ((legacy, True), (journal.get('targets'), True),
                                  (modern.get('targets'), False), (publication.get('targets'), False)):
        require(isinstance(container, dict) and (not is_legacy or sid not in container))
        for other_sid, row in container.items():
            if other_sid.startswith('_'):
                continue
            require(isinstance(row, dict))
            if other_sid == sid:
                continue
            ids = {str(row['deposition_id'])} if row.get('deposition_id') is not None else set()
            identity = row.get('identity') or {}
            require(isinstance(identity, dict))
            ids.update(str(identity[k]) for k in ('id', 'parent_id') if identity.get(k) is not None)
            if row.get('untrusted_candidate_id') is not None:
                ids.add(str(row['untrusted_candidate_id']))
            require(not ids & own_ids)
            other_dois = [row['doi']] if row.get('doi') else []
            other_dois += row.get('doi_claims', [])
            require(not {doi_key(d) for d in other_dois} & own_dois)


def authorize(grant, prepared, bound, paths, action, now, documents):
    limits = CAPTURE_LIMITS if action == 'capture' else PUBLISH_LIMITS
    token_scope = CAPTURE_TOKEN_SCOPE if action == 'capture' else PUBLICATION_TOKEN_SCOPE
    expected = {'schema_version', 'kind', 'approved', 'executor', 'origin', 'binding', 'state_root',
                'owner', 'limits', 'started_at', 'expires_at', 'reviewed_by', 'token_scope', 'documents'}
    if action == 'publish':
        expected |= {'exclusive_writer', 'community'}
    version = 1 if action == 'capture' else 2
    require(set(grant) == expected and type(grant['schema_version']) is int and grant['schema_version'] == version
            and grant['kind'] == 'modern-singleton-' + action + '-grant-v' + str(version) and grant['approved'] is True
            and grant['executor'] == draft.EXECUTOR and grant['origin'] == draft.ORIGIN
            and grant['binding'] == bound['binding'] and grant['state_root'] == str(draft.state_root(paths))
            and grant['owner'] == bound['identity']['owner'] and grant['limits'] == limits
            and all(type(v) is int for v in grant['limits'].values())
            and grant['token_scope'] == token_scope and grant['documents'] == documents
            and isinstance(grant['reviewed_by'], str) and grant['reviewed_by'].strip())
    start, end = draft.instant(grant['started_at']), draft.instant(grant['expires_at'])
    require(start <= now < end and 0 < (end - start).total_seconds() <= 600)
    if action == 'publish':
        require(grant['exclusive_writer'] is True)
        from scripts.modern_publication_qa import validate_community
        community = validate_community(grant['community'], bound, now=now)
        require(draft.instant(community['reviewed_at']) <= start
                and end <= draft.instant(community['expires_at']))


class Runner:
    def __init__(self, json_file, paths, preparation, old_grant, old_duplicate, grant, token,
                 *, action, snapshot=None, qa=None, duplicate=None, release=None, transport=None, now=None):
        require(action in ('capture', 'publish'))
        self.json_file, self.paths = Path(json_file), paths
        self.bridge_paths = (Path(preparation), Path(old_grant), Path(old_duplicate))
        self.prepared, self.bound = bridge(json_file, paths, *self.bridge_paths)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.action, self.grant_path = action, Path(grant)
        self.grant, self.grant_sha = draft.read_document(grant)
        self.document_paths = {k: Path(v) for k, v in dict(snapshot=snapshot, qa=qa, duplicate=duplicate, release=release).items()
                               if v is not None}
        require(set(self.document_paths) == (set() if action == 'capture' else {'snapshot', 'qa', 'duplicate', 'release'}))
        self.documents = {k: draft.read_document(p) for k, p in self.document_paths.items()}
        self.document_hashes = {k: v[1] for k, v in self.documents.items()}
        self.file_identity = (file_identity(validate_snapshot(self.prepared, self.bound,
                             self.documents['snapshot'][0])[2]) if action == 'publish' else None)
        self.limits = CAPTURE_LIMITS if action == 'capture' else PUBLISH_LIMITS
        self.root = draft.state_root(paths)
        self.journal_path = Path(paths.uploads_registry_path + '.modern-' + ('capture' if action == 'capture' else 'publication') + '-v1.json')
        self.intent_path = self.root / (self.prepared.source_id + '.modern-' + action + '-v1.intent.json')
        self.snapshot_path = self.root / (self.prepared.source_id + '.modern-snapshot-v1.json')
        self.deadline = time.monotonic() + 600
        self.current()
        require(isinstance(token, str) and 16 <= len(token) <= 4096 and all(33 <= ord(c) <= 126 for c in token))
        require(not any(echoed(raw, token) for raw in (self.prepared.xml, self.prepared.body, encode(self.bound),
                        encode(self.grant), *(p.read_bytes() for p in self.bridge_paths),
                        *(encode(v[0]) for v in self.documents.values()))))
        self.token, self.transport = token, transport or draft.Transport(token)
        self.row = self.journal = None
        self.raw_responses = []

    def current(self):
        require(bridge(self.json_file, self.paths, *self.bridge_paths) == (self.prepared, self.bound))
        require(draft.read_document(self.grant_path) == (self.grant, self.grant_sha))
        require({k: draft.read_document(p) for k, p in self.document_paths.items()} == self.documents)
        authorize(self.grant, self.prepared, self.bound, self.paths, self.action, self.now(), self.document_hashes)
        require(time.monotonic() < self.deadline)
        if self.action == 'publish':
            from scripts.modern_publication_qa import validate
            snapshot, qa, duplicate, release = (self.documents[k][0] for k in ('snapshot', 'qa', 'duplicate', 'release'))
            validate_snapshot(self.prepared, self.bound, snapshot)
            record = validate(qa, self.prepared, self.bound, snapshot, duplicate, now=self.now(),
                              community=self.grant['community'])
            production = duplicate['production']
            require(draft.instant(production['reviewed_at']) <= draft.instant(self.grant['started_at'])
                    and draft.instant(self.grant['expires_at']) <= draft.instant(production['expires_at']))
            validate_release(release, qa, self.prepared.source_id, dict(record, environment='production'))

    def save(self):
        atomic_json(self.journal_path, self.journal)

    def load(self):
        self.current()
        collision_check(self.paths, self.prepared, self.bound)
        require(not self.journal_path.is_symlink() and not self.intent_path.is_symlink())
        kind = 'modern-singleton-' + self.action + '-attempts-v1'
        self.journal = read_document_or_default(self.journal_path, {'schema_version': 1, 'kind': kind, 'targets': {}})
        require(set(self.journal) == {'schema_version', 'kind', 'targets'} and self.journal['schema_version'] == 1
                and self.journal['kind'] == kind and isinstance(self.journal['targets'], dict))
        self.row = self.journal['targets'].get(self.prepared.source_id)
        if self.row is not None:
            # Same canonical v1 state paths preserve old attempts. A new protocol
            # never migrates/reopens an own-source v1 publication row or intent.
            require(self.action == 'capture' or self.row.get('protocol') == 'community-first-v2')
            intent, intent_sha = draft.read_document(self.intent_path)
            require(intent == {'schema_version': 1, 'binding': self.bound['binding'],
                    'grant_sha256': self.grant_sha, 'state_root': str(self.root), 'action': self.action})
            require(self.row.get('binding') == self.bound['binding'] and self.row.get('grant_sha256') == self.grant_sha
                    and self.row.get('identity') == self.bound['identity']
                    and self.row.get('intent_sha256') == intent_sha
                    and isinstance(self.row.get('requests'), list) and set(self.row.get('counts', {})) == set(self.limits))
            for k, limit in self.limits.items():
                require(type(self.row['counts'][k]) is int and 0 <= self.row['counts'][k] <= limit
                        and self.row['counts'][k] == sum(r.get('kind') == k for r in self.row['requests']))
            require(all(r.get('kind') in self.limits for r in self.row['requests']))
            if self.row.get('request_id') is not None:
                request_identifier(self.row['request_id'])
                require(self.action == 'publish' and self.row['counts']['review'] == 1
                        and any(r.get('kind') == 'review' and r.get('method') == 'PUT'
                                and r.get('path') == routes(self.prepared, self.bound)[0] + '/review'
                                and r.get('http_status') == 200 and r.get('credential_suppressed') is False
                                and r.get('response_sha256') == self.row.get('review_response_sha256')
                                for r in self.row['requests']))
                draft.digest(self.row.get('review_response_sha256'))
                review_raw = base64.b64decode(self.row.get('review_response_base64', ''), validate=True)
                require(len(review_raw) <= draft.MAX_BYTES and sha(review_raw) == self.row['review_response_sha256'])
                validate_request(parse(review_raw), self.bound, self.grant['community'],
                                 self.row['request_id'], created=True)
            collision_check(self.paths, self.prepared, self.bound, self.row.get('doi_claims', []))

    def call(self, kind, path, *, binary=False):
        self.current()
        public = routes(self.prepared, self.bound, True)
        drafts = routes(self.prepared, self.bound)
        method, body, expected, accept = 'GET', None, 200, draft.MIME
        if kind == 'review':
            require(self.action == 'publish' and path == drafts[0] + '/review'
                    and self.row.get('initial_draft_verified') is True and self.row['counts']['submit'] == 0)
            method, accept = 'PUT', JSON
            body = encode({'type': 'community-submission', 'receiver': {'community': self.grant['community']['id']}})
        elif kind == 'submit':
            require(self.action == 'publish' and path == drafts[0] + '/actions/submit-review'
                    and self.row.get('review_draft_verified') is True and self.row.get('request_status') == 'created'
                    and self.row['counts']['review'] == 1 and self.row.get('request_id'))
            method, expected, accept = 'POST', 202, JSON
            body = encode({'require_review': False})
        else:
            request_path = ('/api/requests/' + request_identifier(self.row['request_id'])
                            if self.row.get('request_id') else None)
            allowed = drafts if self.action == 'capture' else drafts + public + ([request_path] if request_path else [])
            require(kind == 'get' and path in allowed and (not binary or path in (drafts[3], public[3])))
            if path == request_path:
                accept = JSON
        require(self.row['counts'][kind] < self.limits[kind])
        self.row['counts'][kind] += 1
        receipt = {'kind': kind, 'method': method, 'path': path, 'body_sha256': sha(body) if body else None,
                   'attempted_at': self.now().isoformat(), 'status': 'uncertain'}
        self.row['requests'].append(receipt)
        self.save()
        self.current()
        remaining = min(draft.TIMEOUT, self.deadline - time.monotonic(),
                        (draft.instant(self.grant['expires_at']) - self.now()).total_seconds())
        require(remaining > 0)
        try:
            response = self.transport.request(method, path, body, timeout=remaining, accept=accept)
        except Exception:
            raise Held('Publication request interrupted; attempt remains spent') from None
        response = draft.normalize_response(response)
        evidence = draft.retain_response(self.journal_path, self.prepared.source_id, self.grant_sha,
                                        len(self.row['requests']) - 1, receipt, response, self.token, self.save)
        status, mime, raw = response.status, response.mime, response.body
        require(response.complete and not evidence['credential_suppressed'] and isinstance(mime, str))
        # Receipt of identity evidence is not a new provider action. Retain it
        # even when a grant expires or is revoked while the request is in flight.
        # Preserve the existing reject-only observation boundary before the new
        # stricter header parser can reject an otherwise parseable response.
        observed_media = mime.split(';', 1)[0].strip().lower()
        value = raw if binary else parse(raw)
        if (self.action == 'publish' and (kind == 'submit' or path == public[0])
                and observed_media in (draft.MIME, JSON)):
            self.retain_doi_claims(value)
        media = draft.response_media_type(mime, binary=binary)
        require(status == expected)
        require(media in (draft.BINARY_MEDIA if binary else {accept}))
        self.current()
        if kind == 'review':
            self.row['review_response_base64'] = base64.b64encode(raw).decode()
            self.save()
        if kind == 'get':
            self.raw_responses.append({'method': 'GET', 'path': path, 'http_status': status, 'media_type': media,
                                       'body_base64': base64.b64encode(raw).decode(), 'response_sha256': sha(raw)})
        return value

    def read_draft(self):
        offset = len(self.raw_responses)
        for i, path in enumerate(routes(self.prepared, self.bound)):
            self.call('get', path, binary=i == 3)
        snapshot = {'schema_version': 1, 'kind': 'modern-draft-snapshot-v1', 'bridge_binding': self.bound['binding'],
                    'identity': self.bound['identity'], 'revision_id': self.bound['verified_revision'],
                    'captured_at': self.now().isoformat(), 'responses': self.raw_responses[offset:]}
        validate_snapshot(self.prepared, self.bound, snapshot)
        return snapshot

    def read_review_draft(self):
        """Fence the reviewed draft without assuming a fixed revision increment.

        Review PUT has no demonstrated server-side CAS. The exclusive-writer
        grant and these exact metadata/file/review fences precede submission.
        """
        values = [self.call('get', path, binary=i == 3)
                  for i, path in enumerate(routes(self.prepared, self.bound))]
        validator = draft_validator(self.prepared, self.bound)
        revision = values[0].get('revision_id')
        require(type(revision) is int and revision >= self.bound['verified_revision'])
        for value in (values[0], values[4]):
            # Pinned DraftStatus maps a created review to draft_with_review.
            # Validate that exact state first, then reuse all ordinary draft
            # invariants on a local status-only projection; raw receipts stay intact.
            require(value.get('status') == 'draft_with_review' and 'review' not in value)
            validator.record(dict(value, status='draft'), True, revision)
            parent = value.get('parent', {})
            require(parent.get('communities', {}).get('ids', []) == [])
            review = parent.get('review')
            require(isinstance(review, dict)
                    and {k: review.get(k) for k in ('id', 'type', 'receiver')} == {
                        'id': self.row['request_id'], 'type': 'community-submission',
                        'receiver': {'community': self.grant['community']['id']}})
        require(isinstance(values[1], dict) and isinstance(values[1].get('entries'), list)
                and len(values[1]['entries']) == 1)
        validator.file(values[1]['entries'][0], True)
        validator.file(values[2], True)
        require(file_identity(values[1]['entries'][0]) == file_identity(values[2]) == self.file_identity
                and values[3] == self.prepared.xml)
        self.row['review_draft_verified'] = True
        self.row['review_revision'] = revision
        self.save()

    def retain_doi_claims(self, data):
        # Keep reject-only observations even when metadata, identity or PID
        # validation fails. Neither a collision nor a bad response erases them.
        candidates = []
        if isinstance(data, dict):
            candidates.append(data.get('doi'))
            for container in (data, data.get('parent')):
                if isinstance(container, dict) and isinstance(container.get('pids'), dict):
                    candidate = container['pids'].get('doi')
                    if isinstance(candidate, dict):
                        candidates.append(candidate.get('identifier'))
        for value in candidates:
            try:
                key = doi_key(value)
            except ValueError:
                continue
            if key and key not in {doi_key(d) for d in self.row['doi_claims']}:
                self.row['doi_claims'].append(value)
        self.save()

    def inspect_published(self, data):
        self.retain_doi_claims(data)
        observed, communities = published_record(data, self.prepared, self.bound,
                  draft.instant(self.grant['started_at']), self.now(), self.grant['community'],
                  self.row.get('published_baseline'))
        claims = [observed['pids'][k]['doi']['identifier'] for k in ('record', 'parent')]
        collision_check(self.paths, self.prepared, self.bound, self.row['doi_claims'])
        require({doi_key(d) for d in self.row['doi_claims']} == {doi_key(d) for d in claims})
        self.row['published_baseline'] = observed
        self.row['communities'] = communities
        self.save()

    def read_published(self):
        base, listing, file, content, _ = routes(self.prepared, self.bound, True)
        self.inspect_published(self.call('get', base))
        values = self.call('get', listing)
        require(isinstance(values, dict) and isinstance(values.get('entries'), list) and len(values['entries']) == 1)
        published_file(values['entries'][0], self.prepared, self.bound)
        descriptor = self.call('get', file)
        published_file(descriptor, self.prepared, self.bound)
        require(file_identity(values['entries'][0]) == file_identity(descriptor) == self.file_identity)
        require(self.call('get', content, binary=True) == self.prepared.xml)
        self.inspect_published(self.call('get', base))
        self.row['published_verified'] = True
        self.save()

    def request_record(self, value, *, created=False):
        validate_request(value, self.bound, self.grant['community'], self.row['request_id'], created=created)
        require(self.row.get('request_status') != 'accepted' or value['status'] == 'accepted')
        self.row['request_status'] = value['status']
        self.save()

    def run(self, read_only=False):
        with ledger_lock(self.paths):
            self.load()
            if read_only:
                require(self.action == 'publish' and self.row is not None
                        and self.row['counts']['submit'] == 1 and self.row.get('request_id'))
                # Reserve enough for acceptance plus a complete record/file fence;
                # a pending observation consumes only its actual one GET.
                require(self.row['counts']['get'] + 6 <= self.limits['get'])
            else:
                require(self.row is None and not self.intent_path.exists())
                intent = {'schema_version': 1, 'binding': self.bound['binding'], 'grant_sha256': self.grant_sha,
                          'state_root': str(self.root), 'action': self.action}
                draft.permanent_intent(self.intent_path, intent)
                self.row = {'binding': self.bound['binding'], 'grant_sha256': self.grant_sha,
                            'intent_sha256': sha(encode(intent)), 'identity': self.bound['identity'],
                            'counts': dict.fromkeys(self.limits, 0), 'requests': [], 'doi_claims': []}
                if self.action == 'publish':
                    self.row['protocol'] = 'community-first-v2'
                self.journal['targets'][self.prepared.source_id] = self.row
                self.save()
                snapshot = self.read_draft()
                if self.action == 'capture':
                    draft.permanent_intent(self.snapshot_path, snapshot)
                    self.row['snapshot_sha256'] = sha(encode(snapshot))
                    self.save()
                    return {'capture_verified': True, 'snapshot_path': str(self.snapshot_path),
                            'snapshot_sha256': self.row['snapshot_sha256'], 'counts': self.row['counts']}
                require(file_identity(validate_snapshot(self.prepared, self.bound, snapshot)[2]) == self.file_identity)
                self.row['initial_draft_verified'] = True
                self.save()
                base = routes(self.prepared, self.bound)[0]
                value = self.call('review', base + '/review')
                require(isinstance(value, dict))
                self.row['request_id'] = request_identifier(value.get('id'))
                self.row['review_response_sha256'] = self.row['requests'][-1]['response_sha256']
                self.save()  # Preserve known identity even if later validation fails.
                self.request_record(value, created=True)
                self.read_review_draft()
                # This action can publish. current() validates exact QA, human
                # release, destination and remaining authority before dispatch.
                self.request_record(self.call('submit', base + '/actions/submit-review'))
            self.request_record(self.call('get', '/api/requests/' + self.row['request_id']))
            accepted = self.row['request_status'] == 'accepted'
            if accepted:
                self.read_published()
            complete = accepted and self.row.get('published_verified') is True
            return {'release_complete': complete, 'request_status': self.row['request_status'],
                    'published_verified': complete,
                    'identity': self.bound['identity'], 'pids': self.row.get('published_baseline', {}).get('pids'),
                    'community_submission_verified': self.row['request_status'] in ('submitted', 'accepted'),
                    'community_membership_verified': complete, 'doi_registration_verified': False,
                    'counts': self.row['counts'].copy(), 'read_only': read_only}


def read_document_or_default(path, default):
    return draft.read_document(path)[0] if Path(path).exists() else default


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('bridge', 'capture', 'prepare-qa', 'preflight', 'publish', 'readback'))
    for key in ('json-file', 'output-dir', 'preparation', 'old-grant', 'old-duplicate'):
        parser.add_argument('--' + key, required=True)
    for key in ('grant', 'snapshot', 'qa', 'duplicate', 'release', 'manifest', 'source-revision', 'community'):
        parser.add_argument('--' + key)
    args = parser.parse_args()
    try:
        paths = OutputPaths(args.output_dir, 'production')
        prepared, bound = bridge(args.json_file, paths, args.preparation, args.old_grant, args.old_duplicate)
        if args.action == 'bridge':
            result = {'bridge': bound, 'provider_requests': 0}
        elif args.action == 'prepare-qa':
            from scripts.modern_publication_qa import pending_manifest
            require(args.snapshot and args.duplicate and args.manifest and args.source_revision and args.community)
            snapshot = draft.read_document(args.snapshot)[0]
            validate_snapshot(prepared, bound, snapshot)
            manifest = pending_manifest(prepared, bound, snapshot, draft.read_document(args.duplicate)[0],
                                        source_revision=args.source_revision, now=datetime.now(timezone.utc),
                                        community=draft.read_document(args.community)[0])
            draft.permanent_intent(args.manifest, manifest)
            result = {'qa_prepared': True, 'approved': False, 'provider_requests': 0}
        else:
            require(args.grant is not None)
            action = 'capture' if args.action == 'capture' else 'publish'
            if args.action == 'preflight':
                # Dummy token validates the complete offline contract; no Transport is constructed.
                runner = Runner(args.json_file, paths, args.preparation, args.old_grant, args.old_duplicate,
                                args.grant, 'dummy-preflight-token-only', action=action, snapshot=args.snapshot,
                                qa=args.qa, duplicate=args.duplicate, release=args.release, transport=object())
                runner.load()
                result = {'preflight_verified': True, 'provider_requests': 0}
            else:
                require(platform.system() == 'Darwin' and sys.stdin.isatty())
                with warnings.catch_warnings():
                    warnings.simplefilter('error', getpass.GetPassWarning)
                    scopes = CAPTURE_TOKEN_SCOPE if action == 'capture' else PUBLICATION_TOKEN_SCOPE
                    token = getpass.getpass('Production token (memory only; ' + scopes + '): ')
                runner = Runner(args.json_file, paths, args.preparation, args.old_grant, args.old_duplicate,
                                args.grant, token, action=action, snapshot=args.snapshot, qa=args.qa,
                                duplicate=args.duplicate, release=args.release)
                result = runner.run(read_only=args.action == 'readback')
        print(encode(result).decode())
        return 0
    except BaseException:
        print('{"held":true,"instruction":"Preserve original history, journals and spent attempts; no reset or mutation retry"}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
