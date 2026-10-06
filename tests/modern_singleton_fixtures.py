"""Real immutable sources with fake modern provider effects and dummy grants."""

import copy
import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import modern_singleton as mapping
from scripts import modern_singleton_executor as executor
from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths
from tests.test_content_class_targets import current_profiles

NOW = datetime(2026, 10, 5, 18, 0, tzinfo=timezone.utc)
TOKEN = 'dummy-modern-singleton-offline-only'


def prepare_sources(directory, ids=None):
    root = Path(directory)
    source = root / 'sources'
    source.mkdir()
    for sid in ids or [row['source_id'] for row in mapping.cohort()['members']]:
        shutil.copyfile(mapping.ROOT / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
    profiles = current_profiles()
    profiles.update(institution_creator_interpretation_manifest=mapping.PROFILE,
                    source_title_interpretation_manifest=mapping.ROOT / 'docs/readiness/2026-10-04/source_display_titles_42.json',
                    dataset_access_interpretation_manifest=mapping.ROOT / 'docs/readiness/2026-10-04/finite_source_resource_access_655.json')
    output = root / 'prepared'
    classify_collection(source, output, NOW.isoformat(), **profiles)
    return output


class FakeTransport:
    def __init__(self, fixture):
        self.fixture = fixture
        self.calls = []
        self.change = None
        self.created = self.initialized = self.uploaded = self.complete = False
        self.identifier, self.parent = '19000001', '19000000'
        self.fail_index = None
        self.effect_before_fail = False
        self.revision = 1

    @property
    def base(self):
        return '/api/records/' + self.identifier + '/draft'

    @property
    def file(self):
        return self.base + '/files/' + self.fixture.prepared.source_id + '.xml'

    def entry(self, completed=None):
        completed = self.complete if completed is None else completed
        value = {'key': self.fixture.prepared.source_id + '.xml', 'status': 'completed' if completed else 'pending',
                 'transfer': {'type': 'L'}, 'links': {
                     'self': executor.ORIGIN + self.file, 'content': executor.ORIGIN + self.file + '/content',
                     'commit': executor.ORIGIN + self.file + '/commit'}}
        if completed:
            xml = self.fixture.prepared.xml
            value.update(size=len(xml), checksum='md5:' + hashlib.md5(xml, usedforsecurity=False).hexdigest())
        return value

    def record(self):
        expected = mapping.parse(self.fixture.prepared.body)
        return {'id': self.identifier, 'created': NOW.isoformat(), 'revision_id': self.revision,
                'metadata': copy.deepcopy(expected['metadata']), 'access': expected['access'],
                'is_published': False, 'status': 'draft', 'pids': {}, 'versions': {'index': 1},
                'parent': {'id': self.parent, 'access': {'owned_by': {'user': '123'}}},
                'links': {'self': executor.ORIGIN + self.base, 'files': executor.ORIGIN + self.base + '/files'},
                'files': {'enabled': True, 'entries': {self.fixture.prepared.source_id + '.xml': self.entry()} if self.complete else {},
                          'count': int(self.complete), 'total_bytes': len(self.fixture.prepared.xml) if self.complete else 0},
                'errors': [] if self.complete else [{'field': 'files.enabled', 'messages': ['Missing uploaded files.']}]}

    def request(self, method, path, body, *, timeout):
        assert 0 < timeout <= executor.TIMEOUT
        index = len(self.calls)
        self.calls.append((method, path, body))
        if self.fail_index == index and not self.effect_before_fail:
            raise TimeoutError('Dummy transport interruption ' + TOKEN)
        status = 200
        if path == '/api/records' and method == 'POST':
            self.created, status = True, 201
            data = self.record()
        elif path == self.base:
            data = self.record()
        elif path == self.base + '/files':
            if method == 'POST':
                self.initialized, status = True, 201
            data = {'entries': [self.entry()] if self.initialized else []}
        elif path == self.file + '/content':
            if method == 'PUT':
                self.uploaded = True
                data = self.entry()
            else:
                data = self.fixture.prepared.xml if self.uploaded else b''
        elif path == self.file + '/commit':
            self.complete, self.revision = True, 2
            data = self.entry()
        elif path == self.file:
            data = self.entry()
        else:
            raise AssertionError('Unexpected fake route')
        if self.fail_index == index:
            raise TimeoutError('Dummy response loss ' + TOKEN)
        if self.change:
            status, data = self.change(index, status, copy.deepcopy(data))
        binary = isinstance(data, bytes)
        return status, 'application/octet-stream' if binary else executor.MIME, data if binary else mapping.encode(data)


class Fixture:
    def __init__(self, directory, prepared_root, source_id='FGDC-141'):
        self.root = Path(directory)
        prepared_copy = self.root / 'prepared'
        shutil.copytree(prepared_root, prepared_copy)
        self.paths = OutputPaths(str(prepared_copy), 'production')
        self.json_file = Path(self.paths.zenodo_json_dir) / (source_id + '.json')
        self.prepared = mapping.prepare(self.json_file, self.paths)
        state = str(executor.state_root(self.paths))
        self.proof = {'schema_version': 1, 'origin': executor.ORIGIN, 'owner': '123',
                      'binding': self.prepared.binding, 'state_root': state,
                      'complete': True, 'history_reconciled': True, 'checked_at': NOW.isoformat(),
                      'expires_at': (NOW + timedelta(seconds=600)).isoformat(),
                      'matched_record_ids': [], 'matched_dois': [], 'inventory_sha256': 'a' * 64,
                      'history_sha256': 'b' * 64, 'reviewed_by': 'Independent offline fixture'}
        self.proof_path, self.grant_path = self.root / 'duplicate-proof.json', self.root / 'grant.json'
        self.proof_path.write_bytes(mapping.encode(self.proof))
        self.grant = {'schema_version': 1, 'approved': True, 'executor': executor.EXECUTOR,
                      'origin': executor.ORIGIN, 'binding': self.prepared.binding, 'state_root': state,
                      'owner': '123', 'limits': executor.LIMITS.copy(), 'started_at': NOW.isoformat(),
                      'expires_at': (NOW + timedelta(seconds=600)).isoformat(),
                      'duplicate_proof_sha256': mapping.sha(self.proof_path.read_bytes()),
                      'reviewed_by': 'Independent offline fixture', 'token_scope': 'deposit:write',
                      'draft_only': True, 'canary_receipt_sha256': 'c' * 64}
        self.grant_path.write_bytes(mapping.encode(self.grant))
        self.transport = FakeTransport(self)

    def runner(self):
        return executor.Runner(self.json_file, self.paths, self.grant_path, self.proof_path,
                               TOKEN, self.transport, lambda: NOW)

    def change_grant(self, **changes):
        self.grant.update(changes)
        self.grant_path.write_bytes(mapping.encode(self.grant))

    def change_proof(self, **changes):
        self.proof.update(changes)
        self.proof_path.write_bytes(mapping.encode(self.proof))
        self.change_grant(duplicate_proof_sha256=mapping.sha(self.proof_path.read_bytes()))
