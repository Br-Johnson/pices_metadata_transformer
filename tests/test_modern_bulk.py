"""Offline contracts for the bulk draft and publication route (ADR 0013) and its v2 wire (ADR 0014).

A synthetic InvenioRDM provider stands in for zenodo.org; real prepared sources
supply the wire and the original XML. No network, token or production state.
"""

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import modern_batch as batch
from scripts import modern_bulk as bulk
from scripts import modern_content_class as content_class
from scripts import modern_operator as operator
from scripts import modern_singleton_executor as draft
from scripts.modern_singleton import Held, encode, parse, prepare
from scripts.path_config import OutputPaths
from scripts.production_mutations import reject_modern_attempt
from tests import modern_singleton_fixtures as fixtures

OWNER = '123'
TOKEN = 'dummy-modern-bulk-offline-only'
SOURCES = ('FGDC-1915', 'FGDC-1916', 'FGDC-1917', 'FGDC-1924', 'FGDC-2708')
PAIR = ('FGDC-2953', 'FGDC-3181')
PAIR_TARGET = 'sha256:0025e59c5556d26b1c14ceac8c4c840057a271724b524c087db2dd0fb4315025'
TWIN_PAIR = ('FGDC-2921', 'FGDC-3149')
TWIN_PAIR_TARGET = 'sha256:4c7a232a36c52b9da730f8300fc168c94f8baa500a4ee2c4588abb9165092f34'
TWIN_SINGLETON = 'FGDC-1849'
# Two of the 25 non-Exxon pairs (ADR 0015): an ADF&G report-series pair and the Food Habits personal pair.
ADFG_PAIR = ('FGDC-2949', 'FGDC-3177')
ADFG_TARGET = 'sha256:26fdd51ab6cf1a96245eb1609d7732dd34fe8a74ffe9b0ff3b780c8d750ca8a8'
FOODHABITS_PAIR = ('FGDC-2837', 'FGDC-3065')
FOODHABITS_TARGET = 'sha256:8bef14fd05c7b1ea1ab936bfeb4c5325c29c34f33b46d40b6f82f72055973237'
PROPOSAL = bulk.RESOURCE_TYPES_PATH.parents[1] / '2026-10-22/resource_types_pairs25_proposal.json'


class Clock:
    def __init__(self):
        self.value = fixtures.NOW + timedelta(hours=2)
        self.ticks = 0.0

    def now(self):
        self.value += timedelta(seconds=1)
        return self.value

    def monotonic(self):
        self.ticks += 1.0
        return self.ticks

    def sleep(self, seconds):
        self.ticks += seconds


class Provider:
    """Synthetic InvenioRDM: drafts, files, community submission, edits of published records and the legacy listing."""

    def __init__(self, clock):
        self.clock = clock
        self.records = {}
        self.next_id = 30000001
        self.calls = []
        self.fail_at = None          # raise before call N takes effect
        self.lose_at = None          # call N takes effect, then its answer is lost
        self.reject = None           # reject(index, method, path) -> (status, value) before any effect
        self.change = None           # change(index, method, path, status, value) -> (status, value)
        self.complete_on_put = True
        self.accept_on_submit = True
        self.foreign = []            # legacy-listing records owned by the account but not created here
        self.community_parent = None
        self.include_directly = True

    def add_draft(self, wire, key, xml, *, files=True):
        record_id, parent_id = str(self.next_id + 1), str(self.next_id)
        self.next_id += 2
        self.records[record_id] = {
            'id': record_id, 'parent': parent_id, 'metadata': copy.deepcopy(wire['metadata']),
            'created': self.clock.now().isoformat(), 'revision': 1, 'files': {key: xml} if files else {},
            'pending': set(), 'review': None, 'status': 'draft', 'request': None, 'access': copy.deepcopy(wire['access']),
            'edit': None}
        return record_id

    def entry(self, record, key, *, published=False):
        xml = record['files'][key]
        base = '/api/records/' + record['id'] + ('' if published else '/draft')
        value = {'key': key, 'status': 'pending' if key in record['pending'] else 'completed',
                 'transfer': {'type': 'L'},
                 'links': {'self': draft.ORIGIN + base + '/files/' + key,
                           'content': draft.ORIGIN + base + '/files/' + key + '/content'}}
        if key not in record['pending']:
            value.update(size=len(xml), checksum='md5:' + hashlib.md5(xml, usedforsecurity=False).hexdigest())
        return value

    def document(self, record, *, published=False):
        base = '/api/records/' + record['id'] + ('' if published else '/draft')
        done = {k: v for k, v in record['files'].items() if k not in record['pending']}
        value = {'id': record['id'], 'created': record['created'], 'revision_id': record['revision'],
                 'metadata': copy.deepcopy(record['metadata']),
                 'access': copy.deepcopy(record.get('access') or {'record': 'public', 'files': 'restricted'}),
                 'is_published': published, 'status': 'published' if published else record['status'],
                 'pids': {}, 'versions': {'index': 1},
                 'parent': {'id': record['parent'], 'access': {'owned_by': {'user': OWNER}}, 'communities': {},
                            'pids': {}},
                 'links': {'self': draft.ORIGIN + base, 'files': draft.ORIGIN + base + '/files'},
                 'files': {'enabled': True, 'entries': {k: {'key': k, 'size': len(v),
                                                            'checksum': 'md5:' + hashlib.md5(v, usedforsecurity=False).hexdigest()}
                                                        for k, v in done.items()},
                           'count': len(done), 'total_bytes': sum(len(v) for v in done.values())}}
        if not done:
            value['errors'] = [{'field': 'files.enabled', 'messages': ['Missing uploaded files.']}]
        if record['review'] and not published:
            value['parent']['review'] = {'id': record['request'], 'type': 'community-submission',
                                         'receiver': {'community': record['review']}}
        if published:
            value['pids'] = {'doi': {'provider': 'datacite', 'identifier': '10.5281/zenodo.' + record['id']},
                             'oai': {'provider': 'oai', 'identifier': 'oai:zenodo.org:' + record['id']}}
            value['parent']['pids'] = {'doi': {'provider': 'datacite', 'identifier': '10.5281/zenodo.' + record['parent']}}
            ids = [record['review']] + ([self.community_parent] if self.community_parent else [])
            value['parent']['communities'] = {'ids': ids, 'default': record['review']}
            del value['links']['files']
            value['links']['files'] = draft.ORIGIN + base + '/files'
        return value

    def edit_document(self, record):
        """An edit draft of a published record: the published document with the draft's own values."""
        value = self.document(record, published=True)
        edit = record['edit']
        base = '/api/records/' + record['id'] + '/draft'
        value.update(metadata=copy.deepcopy(edit['metadata']), access=copy.deepcopy(edit['access']),
                     revision_id=edit['revision'], custom_fields=copy.deepcopy(edit['custom_fields']))
        value['links'] = {'self': draft.ORIGIN + base, 'files': draft.ORIGIN + base + '/files'}
        return value

    def request_document(self, record):
        status = record['request_status']
        return {'id': record['request'], 'type': 'community-submission', 'status': status,
                'is_open': status == 'submitted', 'is_closed': status == 'accepted',
                'topic': {'record': record['id']}, 'receiver': {'community': record['review']},
                'created_by': {'user': OWNER}}

    def listing(self):
        rows = []
        for record in sorted(self.records.values(), key=lambda r: -int(r['id'])):
            rows.append({'id': int(record['id']), 'owner': int(OWNER), 'title': record['metadata']['title'],
                         'files': [], 'state': 'done' if record['status'] == 'published' else 'unsubmitted',
                         'submitted': record['status'] == 'published', 'doi': None})
        return self.foreign + rows

    def answer(self, method, path, body, accept):
        if path == '/api/communities/' + bulk.PICES_COMMUNITY:
            return 200, {'id': bulk.PICES_COMMUNITY, 'slug': 'pices',
                         'access': {'visibility': 'public', 'record_submission_policy': 'open', 'review_policy': 'open'},
                         'parent': {'id': self.community_parent} if self.community_parent else None,
                         'ui': {'permissions': {'can_submit_record': True, 'can_update': True,
                                                'can_include_directly': self.include_directly}}}
        if path.startswith(operator.LIST_PATH + '?'):
            page = int(path.split('page=')[1].split('&')[0])
            rows = self.listing()[(page - 1) * operator.PAGE_SIZE: page * operator.PAGE_SIZE]
            return 200, rows
        if path.startswith(operator.LIST_PATH + '/'):
            record_id = path.rsplit('/', 1)[1]
            row = next(r for r in self.listing() if str(r['id']) == record_id)
            return 200, dict(row, files=row.get('detail_files', []))
        if method == 'POST' and path == '/api/records':
            wire = parse(body)
            record_id, parent_id = str(self.next_id + 1), str(self.next_id)
            self.next_id += 2
            record = {'id': record_id, 'parent': parent_id, 'metadata': wire['metadata'],
                      'created': self.clock.now().isoformat(), 'revision': 1, 'files': {}, 'pending': set(),
                      'review': None, 'status': 'draft', 'request': None, 'access': wire['access'], 'edit': None}
            self.records[record_id] = record
            return 201, self.document(record)
        parts = path.split('/')
        record = self.records[parts[3]]
        rest = '/'.join(parts[4:])
        if rest == 'draft' and method == 'GET':
            if record['status'] == 'published':
                if record.get('edit'):
                    return 200, self.edit_document(record)
                return 404, {'status': 404, 'message': 'not found'}
            return 200, self.document(record)
        if rest == 'draft' and method == 'POST':  # edit a published record; an open edit draft is returned as is
            assert record['status'] == 'published' and body is None
            if not record.get('edit'):
                record['edit'] = {'metadata': copy.deepcopy(record['metadata']), 'access': copy.deepcopy(record['access']),
                                  'custom_fields': {'legacy:test': 'kept'}, 'revision': record['revision'] + 1}
            return 201, self.edit_document(record)
        if rest == 'draft' and method == 'PUT' and record['status'] != 'published':  # save an unpublished draft
            data = parse(body)
            record.update(metadata=data['metadata'], access=data['access'], revision=record['revision'] + 1)
            return 200, self.document(record)
        if rest == 'draft' and method == 'PUT':
            data = parse(body)
            published = self.document(record, published=True)
            assert data['pids'] == published['pids'] and data['custom_fields'] == record['edit']['custom_fields']
            errors = []
            for index, feature in enumerate((data['metadata'].get('locations') or {}).get('features', [])):
                if feature['geometry']['type'] not in ('Point', 'Polygon'):  # as zenodo.org answers
                    errors.append({'field': f'metadata.locations.features.{index}.geometry.type',
                                   'messages': ['Unsupported value: ' + feature['geometry']['type']]})
                    del feature['geometry']
            record['edit'].update(metadata=data['metadata'], access=data['access'],
                                  revision=record['edit']['revision'] + 1)
            value = self.edit_document(record)
            if errors:
                value['errors'] = errors
            return 200, value
        if rest == 'draft/actions/publish' and method == 'POST':
            edit = record['edit']
            record.update(metadata=edit['metadata'], access=edit['access'], revision=edit['revision'] + 1, edit=None)
            return 202, self.document(record, published=True)
        if rest == 'draft/files' and method == 'POST':
            keys = [item['key'] for item in parse(body)]
            for key in keys:
                record['files'][key] = b''
                record['pending'].add(key)
            return 201, {'entries': [self.entry(record, key) for key in keys]}
        if rest == 'draft/files' and method == 'GET':
            return 200, {'entries': [self.entry(record, k) for k in record['files']]}
        if rest.endswith('/content') and method == 'PUT':
            key = parts[6]
            record['files'][key] = body
            if self.complete_on_put:
                record['pending'].discard(key)
            return 200, self.entry(record, key)
        if rest.endswith('/commit') and method == 'POST':
            key = parts[6]
            record['pending'].discard(key)
            record['revision'] += 1
            return 200, self.entry(record, key)
        if rest == 'draft/review' and method == 'PUT':
            record['review'] = parse(body)['receiver']['community']
            record['request'] = 'req-' + record['id']
            record['request_status'] = 'created'
            record['status'] = 'draft_with_review'
            return 200, self.request_document(record)
        if rest == 'draft/actions/submit-review' and method == 'POST':
            assert parse(body) == {'require_review': False}
            record['request_status'] = 'accepted' if self.accept_on_submit else 'submitted'
            if self.accept_on_submit:
                record['status'] = 'published'
            return 202, self.request_document(record)
        if rest == '' and method == 'GET':
            if record['status'] != 'published':
                return 404, {'status': 404}
            return 200, self.document(record, published=True)
        if rest == 'files' and method == 'GET':
            if accept != 'application/json':  # production answers 406 for the vendor type here
                return 406, {'status': 406, 'message': "Invalid 'Accept' header. Expected one of: application/json"}
            return 200, {'entries': [self.entry(record, k, published=True) for k in record['files']]}
        raise AssertionError('unexpected fake route ' + method + ' ' + path)

    def request(self, method, path, body, *, timeout, accept=draft.MIME):
        assert 0 < timeout <= draft.TIMEOUT
        index = len(self.calls)
        self.calls.append((method, path))
        if self.fail_at == index:
            raise TimeoutError('dummy interruption ' + TOKEN)
        rejected = self.reject(index, method, path) if self.reject is not None else None
        status, value = rejected if rejected is not None else self.answer(method, path, body, accept)
        if self.lose_at == index:
            raise TimeoutError('dummy lost answer ' + TOKEN)
        if self.change is not None:
            status, value = self.change(index, method, path, status, copy.deepcopy(value))
        if isinstance(value, bytes):
            return status, 'text/html', value
        media = 'application/json' if (accept == 'application/json' or path.startswith(operator.LIST_PATH)) else draft.MIME
        return status, media, encode(value)


class BulkRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=[
            *SOURCES, *PAIR, *TWIN_PAIR, TWIN_SINGLETON, *ADFG_PAIR, *FOODHABITS_PAIR])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / 'prepared'
        shutil.copytree(self.prepared_root, root)
        self.paths = OutputPaths(str(root), 'production')
        self.clock = Clock()
        self.provider = Provider(self.clock)

    # ---- helpers

    def plan(self, batch_id, ids, **kwargs):
        manifest = batch.build_manifest(self.paths, ids, batch_id=batch_id, owner=OWNER, built_by='Planner',
                                        now=self.clock.now, **kwargs)
        manifest_file = batch.write_manifest(self.paths, manifest)
        sheet = bulk.build_sheet(self.paths, manifest, draft.sha(manifest_file.read_bytes()), 'Planner',
                                 now=self.clock.now)
        return bulk.write_exclusive(bulk.sheet_path(self.paths, batch_id), sheet), sheet

    def review(self, batch_id, sheet, held=(), reviewer='Reviewer agent'):
        decisions = {row['source_id']: ({'decision': 'held', 'note': 'test hold'} if row['source_id'] in held
                                        else {'decision': 'approved'}) for row in sheet['rows']}
        examined = [row['source_id'] for row in sheet['rows']]
        sheet_sha = draft.sha(bulk.sheet_path(self.paths, batch_id).read_bytes())
        document = bulk.build_review(sheet, sheet_sha, decisions, reviewer, examined, 'ok', now=self.clock.now)
        return bulk.write_exclusive(bulk.review_path(self.paths, batch_id), document)

    def runner(self, stage):
        return bulk.Bulk(self.paths, self.provider, TOKEN, owner=OWNER, stage=stage, now=self.clock.now,
                         clock=self.clock.monotonic, sleep=self.clock.sleep, captured_by='Bulk test')

    def drafts(self, review_file, limit=None):
        _, _, order, members = bulk.load_review(self.paths, review_file)
        runner = self.runner('drafts')
        return runner.run([members[s] for s in order if members[s]['approved']], runner.draft_member, limit=limit)

    def release(self, review_files, name='release-1'):
        document = bulk.build_release(self.paths, review_files, authority='Brett Johnson',
                                      instruction='Publish all appropriate records', instructed_at='2026-10-20',
                                      prepared_by='Bulk test', now=self.clock.now)
        return bulk.write_exclusive(bulk.bulk_root(self.paths) / 'releases' / (name + '.json'), document)

    def publish(self, release_file):
        release, release_sha, _ = bulk.load_release(self.paths, release_file)
        runner = self.runner('publish')
        return runner.run(release['records'], lambda sid: runner.publish_member(sid, release_sha))

    def writes(self):
        return [(m, p) for m, p in self.provider.calls if m != 'GET']

    def published_v1(self, batch_id, ids):
        review_file = self.review(batch_id, self.plan(batch_id, ids)[1])
        self.drafts(review_file)
        self.assertEqual(self.publish(self.release([review_file], name='release-' + batch_id))['counts'],
                         {'published': len(ids)})
        return review_file

    def v2_review(self, base_review, held=()):
        sheet = bulk.build_v2_sheet(self.paths, base_review, 'Planner', now=self.clock.now)
        bulk.write_exclusive(bulk.sheet_path(self.paths, sheet['batch_id']), sheet)
        return self.review(sheet['batch_id'], sheet, held=held), sheet

    def update_release(self, review_files, name='update-1', only=None):
        document = bulk.build_release(self.paths, review_files, authority='Brett Johnson',
                                      instruction='Apply the v2 mapping to the published records by in-place edit',
                                      instructed_at='2026-10-20', prepared_by='Bulk test', now=self.clock.now,
                                      action='update', only=only)
        return bulk.write_exclusive(bulk.bulk_root(self.paths) / 'releases' / (name + '.json'), document)

    def update(self, release_file):
        release, release_sha, members = bulk.load_release(self.paths, release_file, 'update')
        runner = self.runner('update')
        return runner.run(release['records'], lambda sid: runner.update_member(sid, release_sha, members[sid]))

    def ready_update(self, batch_id, sid):
        """One published v1 record with an approved v2 review and an update release; the next call index."""
        base = self.published_v1(batch_id, [sid])
        release_file = self.update_release([self.v2_review(base)[0]], name='update-' + batch_id)
        return release_file, len(self.provider.calls)

    # ---- tests

    def test_reviewed_members_are_drafted_and_published_exactly_once(self):
        review_file = self.review('bulk-001', self.plan('bulk-001', list(SOURCES[:3]))[1])
        result = self.drafts(review_file)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['counts'], {'drafted': 3})
        creates = [c for c in self.provider.calls if c == ('POST', '/api/records')]
        self.assertEqual(len(creates), 3)
        for sid in SOURCES[:3]:
            record = bulk.load_record(self.paths, sid)
            self.assertEqual(record['phase'], 'draft-verified')
            self.assertEqual(record['counts'], {'create': 1, 'init': 1, 'content': 1, 'commit': 0, 'review': 0,
                                                'submit': 0, 'edit': 0, 'update': 0, 'publish': 0, 'get': 2})
            self.assertTrue(bulk.intent_path(self.paths, sid).exists())
            evidence = sorted(p.name for p in bulk.evidence_dir(self.paths, sid).iterdir())
            self.assertEqual(evidence, ['000.create.json', '001.init.json', '002.content.json', '003.get.json',
                                        '004.get.json'])
            self.assertNotIn(TOKEN, ''.join(p.read_text() for p in bulk.evidence_dir(self.paths, sid).iterdir()))
        before = len(self.provider.calls)
        again = self.drafts(review_file)
        self.assertEqual(again['counts'], {'already-drafted': 3})
        self.assertTrue(all(m == 'GET' for m, _ in self.provider.calls[before:]))  # only the inventory
        release_file = self.release([review_file])
        result = self.publish(release_file)
        self.assertEqual(result['counts'], {'published': 3})
        for sid in SOURCES[:3]:
            record = bulk.load_record(self.paths, sid)
            self.assertEqual(record['phase'], 'published')
            self.assertEqual(record['request_status'], 'accepted')
            self.assertEqual(record['pids']['record']['doi']['identifier'], '10.5281/zenodo.' + record['identity']['id'])
        reviews = [c for c in self.writes() if c[1].endswith('/draft/review')]
        submits = [c for c in self.writes() if c[1].endswith('/actions/submit-review')]
        self.assertEqual((len(reviews), len(submits)), (3, 3))
        before = len(self.provider.calls)
        self.assertEqual(self.publish(release_file)['counts'], {'already-published': 3})
        self.assertEqual(len(self.provider.calls), before)

    def test_commit_follows_a_pending_upload(self):
        self.provider.complete_on_put = False
        review_file = self.review('bulk-002', self.plan('bulk-002', ['FGDC-1915'])[1])
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertEqual(record['counts']['commit'], 1)

    def test_review_holds_are_never_drafted_or_released(self):
        _, sheet = self.plan('bulk-003', ['FGDC-1915', 'FGDC-1916'])
        review_file = self.review('bulk-003', sheet, held=('FGDC-1916',))
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        self.assertIsNone(bulk.load_record(self.paths, 'FGDC-1916'))
        release = json.loads(self.release([review_file]).read_text())
        self.assertEqual(release['records'], ['FGDC-1915'])

    def test_owner_inventory_match_holds_before_any_create(self):
        title = parse(prepare(Path(self.paths.zenodo_json_dir) / 'FGDC-1915.json', self.paths).body)['metadata']['title']
        self.provider.foreign = [{'id': 999, 'owner': int(OWNER), 'title': title, 'files': [
            {'filename': 'other.pdf', 'checksum': 'a' * 32, 'filesize': 1}], 'state': 'done', 'submitted': True}]
        review_file = self.review('bulk-004', self.plan('bulk-004', ['FGDC-1915', 'FGDC-1916'])[1])
        result = self.drafts(review_file)
        self.assertEqual(result['counts'], {'held': 1, 'drafted': 1})
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertEqual((record['phase'], record['requests']), ('planned', []))
        self.assertIn('inventory', record['hold']['reason'])
        self.assertFalse(bulk.intent_path(self.paths, 'FGDC-1915').exists())
        self.assertEqual([c for c in self.writes() if c[1] == '/api/records'], [('POST', '/api/records')])
        self.assertRaises(Held, bulk.unhold, self.paths, 'FGDC-1916', 'x', 'y')
        bulk.unhold(self.paths, 'FGDC-1915', 'Reviewer agent', 'the match is a different report')
        self.assertIsNone(bulk.load_record(self.paths, 'FGDC-1915')['hold'])

    def test_provider_metadata_change_parks_the_record_and_the_run_continues(self):
        def change(index, method, path, status, value):
            if path == '/api/records' and value['metadata']['title'].startswith('PICES'):
                value['metadata']['title'] += ' changed'
            return status, value
        self.provider.change = change
        review_file = self.review('bulk-005', self.plan('bulk-005', ['FGDC-1915', 'FGDC-1916'])[1])
        result = self.drafts(review_file)
        held = [sid for sid, value in result_outcomes(self.paths, result).items() if value == 'held']
        self.assertTrue(held)
        for sid in held:
            record = bulk.load_record(self.paths, sid)
            self.assertIsNone(record['identity'])
            self.assertIsNotNone(record['candidate_id'])
            self.assertEqual(record['counts']['create'], 1)
            self.assertEqual(record['counts']['init'], 0)

    def test_lost_upload_answer_is_observed_by_get_only(self):
        review_file = self.review('bulk-006', self.plan('bulk-006', ['FGDC-1915', 'FGDC-1916'])[1])
        self.provider.lose_at = 1 + 2  # one listing page, then create, init and the content PUT
        result = self.drafts(review_file)
        self.assertEqual(result['status'], 'stopped')
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertEqual((record['phase'], record['requests'][-1]['status']), ('initialized', 'uncertain'))
        self.assertIsNotNone(record['hold'])
        self.assertIsNone(bulk.load_record(self.paths, 'FGDC-1916'))
        self.provider.lose_at = None
        before = len(self.provider.calls)
        outcome = self.runner('reconcile').reconcile('FGDC-1915')
        self.assertTrue(all(m == 'GET' for m, _ in self.provider.calls[before:]))
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('draft-verified', []))
        self.assertEqual(self.drafts(review_file)['counts'], {'already-drafted': 1, 'drafted': 1})

    def test_upload_that_never_arrived_is_allowed_once_more(self):
        review_file = self.review('bulk-018', self.plan('bulk-018', ['FGDC-1915'])[1])
        self.provider.fail_at = 1 + 2
        self.assertEqual(self.drafts(review_file)['status'], 'stopped')
        self.provider.fail_at = None
        outcome = self.runner('reconcile').reconcile('FGDC-1915')
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('initialized', ['content:FGDC-1915.xml']))
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertEqual((record['counts']['content'], record['allowances']), (2, {'content': 1}))
        self.assertEqual([r['status'] for r in record['requests'] if r['kind'] == 'content'],
                         ['unanswered', 'answered'])

    def test_lost_create_is_bound_from_the_inventory_and_blocks_others_until_then(self):
        review_file = self.review('bulk-019', self.plan('bulk-019', ['FGDC-1915', 'FGDC-1916'])[1])
        self.provider.lose_at = 1  # the first create takes effect, its answer is lost
        self.assertEqual(self.drafts(review_file)['status'], 'stopped')
        self.provider.lose_at = None
        result = self.drafts(review_file)  # the orphan draft has no visible files: nothing may be created
        self.assertEqual(result['counts'], {'held-earlier': 1, 'held': 1})
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 1)
        outcome = self.runner('reconcile').reconcile('FGDC-1915')
        self.assertEqual(outcome['phase'], 'created')
        bulk.unhold(self.paths, 'FGDC-1916', 'Bulk test', 'the unknown record was FGDC-1915')
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 2})
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 2)

    def test_create_refused_at_the_edge_is_allowed_again_only_after_two_clean_inventories(self):
        review_file = self.review('bulk-020', self.plan('bulk-020', ['FGDC-1915'])[1])
        self.provider.fail_at = 1
        self.drafts(review_file)
        self.provider.fail_at = None
        self.assertRaises(Held, self.runner('reconcile').reconcile, 'FGDC-1915')  # too recent to judge
        self.clock.value += timedelta(minutes=5)
        first = self.runner('reconcile').reconcile('FGDC-1915')
        self.assertEqual((first['held'], first['absence_observations'], first['allowed_again']), (True, 1, []))
        self.assertEqual(self.drafts(review_file)['counts'], {'held-earlier': 1})
        self.clock.value += timedelta(minutes=11)
        second = self.runner('reconcile').reconcile('FGDC-1915')
        self.assertEqual((second['phase'], second['allowed_again']), ('creating', ['create']))
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 2)

    def test_resent_create_is_blocked_when_the_fresh_inventory_shows_an_unknown_record(self):
        review_file = self.review('bulk-022', self.plan('bulk-022', ['FGDC-1915'])[1])
        self.provider.fail_at = 1
        self.drafts(review_file)
        self.provider.fail_at = None
        for minutes in (5, 11):
            self.clock.value += timedelta(minutes=minutes)
            self.runner('reconcile').reconcile('FGDC-1915')
        self.provider.foreign = [{'id': 998, 'owner': int(OWNER), 'title': 'Untitled', 'files': [], 'state': 'unsubmitted',
                                  'submitted': False}]
        result = self.drafts(review_file)
        self.assertEqual(result['counts'], {'held': 1})
        self.assertIn('re-sent create blocked', bulk.load_record(self.paths, 'FGDC-1915')['hold']['reason'])
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 1)

    def test_create_answer_that_failed_validation_is_rebound_from_the_retained_body(self):
        review_file = self.review('bulk-023', self.plan('bulk-023', ['FGDC-1915'])[1])
        real = bulk.check_draft
        calls = []

        def flaky(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise bulk.RecordHold('simulated interruption after the 201')
            return real(*args, **kwargs)
        with patch.object(bulk, 'check_draft', flaky):
            self.assertEqual(self.drafts(review_file)['counts'], {'held': 1})
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertIsNone(record['identity'])
        self.assertIsNotNone(record['candidate_id'])
        before = len(self.provider.calls)
        outcome = self.runner('reconcile').reconcile('FGDC-1915')
        self.assertEqual(len(self.provider.calls), before)  # bound from the retained answer
        self.assertEqual(outcome['phase'], 'created')
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})

    def test_inventory_failure_stops_without_holding_the_member(self):
        review_file = self.review('bulk-024', self.plan('bulk-024', ['FGDC-1915'])[1])
        self.drafts(review_file)
        self.provider.reject = lambda index, method, path: (429, {'status': 429}) if 'depositions' in path else None
        result = self.drafts(review_file)
        self.assertEqual(result['status'], 'stopped')
        self.assertIsNone(bulk.load_record(self.paths, 'FGDC-1915')['hold'])

    def test_inventory_of_another_owner_stops_before_any_create(self):
        self.provider.foreign = [{'id': 997, 'owner': 999, 'title': 'Other account', 'files': [
            {'filename': 'x.pdf', 'checksum': 'b' * 32, 'filesize': 1}], 'state': 'done', 'submitted': True}]
        review_file = self.review('bulk-025', self.plan('bulk-025', ['FGDC-1915'])[1])
        self.assertEqual(self.drafts(review_file)['status'], 'stopped')
        self.assertEqual(self.writes(), [])

    def test_publication_requires_direct_inclusion_and_follows_a_parent_community(self):
        review_file = self.review('bulk-026', self.plan('bulk-026', ['FGDC-1915'])[1])
        self.drafts(review_file)
        release_file = self.release([review_file])
        self.provider.include_directly = False
        self.assertEqual(self.publish(release_file)['status'], 'stopped')
        self.assertFalse(any(p.endswith('/draft/review') for _, p in self.writes()))
        self.provider.include_directly = True
        self.provider.community_parent = '00000000-0000-4000-8000-000000000009'
        self.assertEqual(self.publish(release_file)['counts'], {'published': 1})
        record = bulk.load_record(self.paths, 'FGDC-1915')
        reads = [p for m, p in self.provider.calls if m == 'GET' and p.endswith('/draft')]
        self.assertGreaterEqual(len(reads), 2)  # before the review PUT and again before the submit
        self.assertEqual(record['phase'], 'published')

    def test_reviewed_false_inventory_match_is_allowed_for_that_source_only(self):
        title = parse(prepare(Path(self.paths.zenodo_json_dir) / 'FGDC-1915.json', self.paths).body)['metadata']['title']
        self.provider.foreign = [{'id': 996, 'owner': int(OWNER), 'title': title, 'files': [
            {'filename': 'report.pdf', 'checksum': 'c' * 32, 'filesize': 1}], 'state': 'done', 'submitted': True}]
        review_file = self.review('bulk-027', self.plan('bulk-027', ['FGDC-1915'])[1])
        self.assertEqual(self.drafts(review_file)['counts'], {'held': 1})
        bulk.unhold(self.paths, 'FGDC-1915', 'Reviewer agent', 'record 996 is the report PDF, not this metadata',
                    allow_inventory=['996'])
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})

    def test_rate_limit_and_edge_rejections_stop_the_run(self):
        review_file = self.review('bulk-007', self.plan('bulk-007', ['FGDC-1915', 'FGDC-1916'])[1])
        self.provider.reject = lambda index, method, path: (403, b'<html>unusual traffic</html>') \
            if path == '/api/records' else None
        result = self.drafts(review_file)
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 1)
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertEqual(record['requests'][0]['http_status'], 403)
        self.assertIsNotNone(record['hold'])
        self.provider.reject = None
        result = self.drafts(review_file)
        self.assertEqual(result['counts'], {'held-earlier': 1, 'drafted': 1})
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 2)
        self.provider.reject = lambda index, method, path: (429, {'status': 429})
        self.assertEqual(self.drafts(review_file)['status'], 'stopped')

    def test_pending_community_review_stops_publication(self):
        review_file = self.review('bulk-008', self.plan('bulk-008', ['FGDC-1915', 'FGDC-1916'])[1])
        self.drafts(review_file)
        self.provider.accept_on_submit = False
        result = self.publish(self.release([review_file]))
        self.assertEqual(result['status'], 'stopped')
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertEqual((record['phase'], record['request_status']), ('review-set', 'submitted'))
        self.assertEqual(len([c for c in self.writes() if c[1].endswith('submit-review')]), 1)

    def test_verified_modern_v1_draft_is_adopted_then_published(self):
        prepared = prepare(Path(self.paths.zenodo_json_dir) / 'FGDC-1915.json', self.paths)
        record_id = self.provider.add_draft(parse(prepared.body), 'FGDC-1915.xml', prepared.xml)
        provider_record = self.provider.records[record_id]
        identity = {'id': record_id, 'parent_id': provider_record['parent'], 'owner': OWNER,
                    'created': provider_record['created']}
        root = draft.state_root(self.paths)
        (root / 'FGDC-1915.modern-create-v1.intent.json').write_text('{}')
        journal = {'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {
            'FGDC-1915': {'phase': 'verified', 'identity': identity, 'verified_revision': 1,
                          'untrusted_candidate_id': record_id, 'binding': 'x', 'counts': {}, 'requests': []}}}
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))
        review_file = self.review('bulk-009', self.plan('bulk-009', ['FGDC-1915', 'FGDC-1916'])[1])
        self.assertEqual(self.drafts(review_file)['counts'], {'adopted': 1, 'drafted': 1})
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 1)
        self.assertEqual(self.publish(self.release([review_file]))['counts'], {'published': 2})
        self.assertEqual(bulk.load_record(self.paths, 'FGDC-1915')['identity'], identity)

    def test_unverified_modern_v1_row_is_held(self):
        journal = {'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {
            'FGDC-1915': {'phase': 'started', 'identity': None, 'binding': 'x', 'counts': {}, 'requests': []}}}
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))
        review_file = self.review('bulk-010', self.plan('bulk-010', ['FGDC-1915'])[1])
        self.assertEqual(self.drafts(review_file)['counts'], {'held': 1})
        self.assertEqual(self.writes(), [])

    def test_review_must_differ_from_builder_and_examine_flagged_and_sampled_rows(self):
        _, sheet = self.plan('bulk-011', ['FGDC-1915', 'FGDC-1916'])
        sheet_sha = draft.sha(bulk.sheet_path(self.paths, 'bulk-011').read_bytes())
        decisions = {row['source_id']: {'decision': 'approved'} for row in sheet['rows']}
        with self.assertRaises(Held):
            bulk.build_review(sheet, sheet_sha, decisions, 'Planner', list(decisions), '')
        with self.assertRaises(Held):
            bulk.build_review(sheet, sheet_sha, decisions, 'Reviewer', [], '')
        with self.assertRaises(Held):
            bulk.build_review(sheet, sheet_sha, {'FGDC-1915': {'decision': 'approved'}}, 'Reviewer',
                              list(decisions), '')
        with self.assertRaises(Held):
            bulk.build_review(sheet, sheet_sha, dict(decisions, **{'FGDC-1915': {'decision': 'held'}}),
                              'Reviewer', list(decisions), '')

    def test_release_names_only_drafted_unheld_approved_records_and_publish_follows_it(self):
        review_file = self.review('bulk-012', self.plan('bulk-012', ['FGDC-1915', 'FGDC-1916'])[1])
        self.drafts(review_file, limit=1)
        release = json.loads(self.release([review_file]).read_text())
        self.assertEqual(release['records'], ['FGDC-1915'])
        tampered = dict(release, records=['FGDC-1915', 'FGDC-1917'], record_count=2)
        path = bulk.write_exclusive(bulk.bulk_root(self.paths) / 'releases' / 'tampered.json', tampered)
        self.assertRaises(Held, bulk.load_release, self.paths, path)

    def test_bulk_attempts_join_every_barrier(self):
        review_file = self.review('bulk-013', self.plan('bulk-013', ['FGDC-1915'])[1])
        self.drafts(review_file)
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertIn(record['identity']['id'], operator.known_records(self.paths))
        self.assertEqual(batch.journal_phases(self.paths)['FGDC-1915'], 'bulk:draft-verified')
        self.assertTrue(operator.source_already_attempted(self.paths, 'FGDC-1915'))
        with self.assertRaises(ValueError):
            reject_modern_attempt(self.paths, 'FGDC-1915')

    def test_twins_need_an_allowance_across_batches(self):
        review_file = self.review('bulk-014', self.plan('bulk-014', ['FGDC-1924'])[1])
        self.drafts(review_file)
        with self.assertRaises(Held):
            self.plan('bulk-015', ['FGDC-2708'])
        batch.record_allowance(self.paths, 'cccc-workshop-1997', ['FGDC-1924', 'FGDC-2708'],
                               'Brett Johnson, 2026-10-07', 'distinct source records of one workshop')
        _, sheet = self.plan('bulk-016', ['FGDC-2708'])
        self.assertEqual(sheet['member_count'], 1)

    def test_reviewed_exclusions_are_never_created(self):
        review_file = self.review('bulk-021', self.plan('bulk-021', ['FGDC-1915', 'FGDC-1916'])[1])
        bulk.exclude(self.paths, 'FGDC-1915', 'duplicates FGDC-1916 in the source collection', 'Reviewer agent')
        self.assertEqual(self.drafts(review_file)['counts'], {'held': 1, 'drafted': 1})
        self.assertEqual(len([c for c in self.writes() if c[1] == '/api/records']), 1)
        self.assertRaises(Held, bulk.exclude, self.paths, 'FGDC-1916', 'late', 'Reviewer agent')
        self.assertNotIn('FGDC-1915', bulk.candidates(self.paths))

    def test_pair_targets_publish_one_record_with_both_originals(self):
        reviewed_at = fixtures.NOW.isoformat()
        sheet = bulk.build_pair_sheet(self.paths, 'pairs-001', [PAIR_TARGET], 'Planner', reviewed_at,
                                      now=self.clock.now)
        bulk.write_exclusive(bulk.sheet_path(self.paths, 'pairs-001'), sheet)
        row = sheet['rows'][0]
        self.assertEqual((row['source_id'], row['target']['source_ids']), ('FGDC-2953', list(PAIR)))
        self.assertEqual([f['key'] for f in row['files']], ['FGDC-2953.xml', 'FGDC-3181.xml'])
        review_file = self.review('pairs-001', sheet)
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        record = bulk.load_record(self.paths, 'FGDC-2953')
        self.assertEqual((record['counts']['content'], record['uploaded']), (2, ['FGDC-2953.xml', 'FGDC-3181.xml']))
        self.assertIsNone(bulk.load_record(self.paths, 'FGDC-3181'))
        for sid in PAIR:
            self.assertTrue(bulk.intent_path(self.paths, sid).exists())
            self.assertTrue(operator.source_already_attempted(self.paths, sid))
            self.assertEqual(batch.journal_phases(self.paths)[sid], 'bulk:draft-verified')
            with self.assertRaises(ValueError):
                reject_modern_attempt(self.paths, sid)
        self.assertEqual(self.publish(self.release([review_file]))['counts'], {'published': 1})
        provider = self.provider.records[record['identity']['id']]
        self.assertEqual(sorted(provider['files']), ['FGDC-2953.xml', 'FGDC-3181.xml'])
        self.assertEqual(bulk.load_record(self.paths, 'FGDC-2953')['phase'], 'published')

    def pair_review(self, batch_id, target):
        sheet = bulk.build_pair_sheet(self.paths, batch_id, [target], 'Planner', fixtures.NOW.isoformat(),
                                      now=self.clock.now)
        bulk.write_exclusive(bulk.sheet_path(self.paths, batch_id), sheet)
        return self.review(batch_id, sheet)

    def test_pair_title_twin_with_a_drafted_singleton_needs_an_allowance(self):
        self.drafts(self.review('bulk-030', self.plan('bulk-030', [TWIN_SINGLETON])[1]))
        with self.assertRaises(Held):
            bulk.build_pair_sheet(self.paths, 'pairs-030', [TWIN_PAIR_TARGET], 'Planner', fixtures.NOW.isoformat(),
                                  now=self.clock.now)
        batch.record_allowance(self.paths, 'pair-twin-test', [TWIN_SINGLETON, *TWIN_PAIR], 'Reviewer agent',
                               'different annual reports')
        review_file = self.pair_review('pairs-031', TWIN_PAIR_TARGET)
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})

    def test_drafted_pair_does_not_twin_with_its_own_partner_on_a_rerun(self):
        review_file = self.pair_review('pairs-032', PAIR_TARGET)
        self.provider.lose_at = 1 + 2  # the first upload's answer is lost
        self.assertEqual(self.drafts(review_file)['status'], 'stopped')
        self.provider.lose_at = None
        _, _, order, members = bulk.load_review(self.paths, review_file)
        rows = [{'source_id': m['source_id'], 'source_sha256': m['source_sha256'], 'target': m['target'],
                 'wire': {'title': parse(bulk.prepare_entry(self.paths, m).body)['metadata']['title']}}
                for m in members.values()]
        self.assertEqual(bulk.pair_twins(self.paths, rows), ([], []))

    def test_pair_interrupted_between_its_uploads_is_reconciled_by_get(self):
        review_file = self.pair_review('pairs-033', PAIR_TARGET)
        self.provider.fail_at = 1 + 3  # the second upload never arrives
        self.assertEqual(self.drafts(review_file)['status'], 'stopped')
        self.provider.fail_at = None
        record = bulk.load_record(self.paths, 'FGDC-2953')
        self.assertEqual((record['phase'], record['uploaded']), ('initialized', ['FGDC-2953.xml']))
        before = len(self.provider.calls)
        outcome = self.runner('reconcile').reconcile('FGDC-2953')
        self.assertTrue(all(m == 'GET' for m, _ in self.provider.calls[before:]))
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('initialized', ['content:FGDC-3181.xml']))
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        puts = [p for m, p in self.writes() if m == 'PUT']
        self.assertEqual([p.rsplit('/', 2)[-2] for p in puts], ['FGDC-2953.xml', 'FGDC-3181.xml', 'FGDC-3181.xml'])

    def test_an_answered_upload_is_never_sent_again_without_reconcile(self):
        review_file = self.pair_review('pairs-034', PAIR_TARGET)
        real, calls = bulk.check_file_entry, []

        def crash(entry, expected, **kwargs):
            if entry.get('status') == 'completed' and not calls:
                calls.append(1)
                raise KeyboardInterrupt  # the process dies after the first upload's answer is saved
            return real(entry, expected, **kwargs)
        with patch.object(bulk, 'check_file_entry', crash), self.assertRaises(KeyboardInterrupt):
            self.drafts(review_file)
        record = bulk.load_record(self.paths, 'FGDC-2953')
        self.assertEqual((record['counts']['content'], record['uploaded']), (1, []))
        self.assertEqual(self.drafts(review_file)['counts'], {'held': 1})
        self.assertEqual(len([m for m, _ in self.writes() if m == 'PUT']), 1)
        outcome = self.runner('reconcile').reconcile('FGDC-2953')
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('initialized', []))
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        self.assertEqual(len([m for m, _ in self.writes() if m == 'PUT']), 2)

    def test_publish_reads_the_keychain_only_when_given_and_never_as_the_single_record_action(self):
        with patch.object(bulk.draft, 'production_token', return_value=TOKEN) as token, \
                patch.object(bulk.draft, 'Transport', return_value='transport'):
            self.assertEqual(bulk.transport_and_token('publish', 'pices-zenodo-production'), ('transport', TOKEN))
            token.assert_called_with('Zenodo production token (publish): ', 'pices-zenodo-production',
                                     action='bulk-publish')
            bulk.transport_and_token('publish', None)
            token.assert_called_with('Zenodo production token (publish): ', None, action='publish')
        self.assertIn('bulk-publish', draft.KEYCHAIN_ACTIONS)
        self.assertNotIn('publish', draft.KEYCHAIN_ACTIONS)

    def test_request_starts_are_spaced_by_the_pace(self):
        starts = []
        inner = self.provider.request

        def timed(method, path, body, *, timeout, accept=draft.MIME):
            starts.append(self.clock.ticks)
            self.clock.ticks += 0.5  # the provider takes half a second to answer
            return inner(method, path, body, timeout=timeout, accept=accept)
        self.provider.request = timed
        review_file = self.review('bulk-040', self.plan('bulk-040', ['FGDC-1915'])[1])
        _, _, order, members = bulk.load_review(self.paths, review_file)
        runner = bulk.Bulk(self.paths, self.provider, TOKEN, owner=OWNER, stage='drafts', now=self.clock.now,
                           clock=lambda: self.clock.ticks, sleep=self.clock.sleep, captured_by='Bulk test')
        self.assertEqual(runner.run([members[s] for s in order], runner.draft_member)['counts'], {'drafted': 1})
        gaps = [b - a for a, b in zip(starts, starts[1:], strict=False)]
        self.assertTrue(gaps and all(gap >= bulk.PACE_SECONDS - 1e-9 for gap in gaps), gaps)
        self.assertTrue(any(gap < bulk.PACE_SECONDS + 0.5 for gap in gaps[1:]), gaps)

    def test_sheet_flags_and_sample_are_fixed_by_the_membership(self):
        _, sheet = self.plan('bulk-017', list(SOURCES[:3]))
        self.assertEqual(sheet['sample'], sorted(set(r['source_id'] for r in sheet['rows']) - set(sheet['flagged']),
                                                 key=batch.by_number)[:len(sheet['sample'])] or sheet['sample'])
        for row in sheet['rows']:
            self.assertEqual(row['wire_sha256'], draft.sha(prepare(
                Path(self.paths.zenodo_json_dir) / (row['source_id'] + '.json'), self.paths).body))
        flags = bulk.flags_for({'title': 'A', 'pubdate': 'unknown', 'abstract': 'x' * 50, 'origins': [],
                                'time_period': '', 'keywords': 0, 'metadata_date': '19990101'},
                               {'metadata': {'title': 'B\x07', 'publication_date': '2001', 'description': 'short',
                                             'creators': [{'person_or_org': {'type': 'organizational', 'name': 'n/a'}}],
                                             'subjects': []}})
        self.assertEqual(set(flags), {'title_differs_from_source', 'publication_date_differs_from_metadata_date',
                                      'short_description',
                                      'description_omits_abstract_opening', 'suspicious_creator',
                                      'control_character', 'no_subjects'})


    # ---- v2 wire (ADR 0014)

    def test_v2_sheet_carries_the_approved_unexcluded_members_with_their_v2_wire(self):
        base = self.review('bulk-050', self.plan('bulk-050', list(SOURCES[:3]))[1], held=(SOURCES[2],))
        bulk.exclude(self.paths, SOURCES[1], 'test exclusion', 'Reviewer agent')
        review_file, sheet = self.v2_review(base)
        self.assertEqual((sheet['batch_id'], sheet['wire_version'], sheet['skipped']),
                         ('bulk-050-v2', 2, [SOURCES[1], SOURCES[2]]))
        row = sheet['rows'][0]
        _, _, _, members = bulk.load_review(self.paths, base)
        self.assertEqual((row['source_id'], row['source_sha256'], row['wire_version']),
                         (SOURCES[0], members[SOURCES[0]]['source_sha256'], 2))
        wire = parse(bulk.prepare_entry(self.paths, {'source_id': SOURCES[0]}, 2).body)
        self.assertEqual(row['wire_sha256'], draft.sha(encode(wire)))
        self.assertFalse(wire['metadata']['title'].endswith(' - FGDC XML metadata artifact'))
        self.assertEqual(wire['access'], {'record': 'public', 'files': 'public'})
        self.assertEqual(row['v2']['resource_type'], bulk.resource_types()[SOURCES[0]])
        self.assertEqual(bulk.load_review(self.paths, review_file)[3][SOURCES[0]]['wire_version'], 2)
        with self.assertRaises(Held):
            bulk.build_v2_sheet(self.paths, review_file, 'Planner', now=self.clock.now)

    def test_v2_members_are_created_and_published_with_public_originals(self):
        base = self.review('bulk-051', self.plan('bulk-051', list(SOURCES[:2]))[1])
        review_file, _ = self.v2_review(base)
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 2})
        self.assertEqual(self.publish(self.release([review_file]))['counts'], {'published': 2})
        for sid in SOURCES[:2]:
            record = bulk.load_record(self.paths, sid)
            provider = self.provider.records[record['identity']['id']]
            wire = parse(bulk.prepare_entry(self.paths, record).body)
            self.assertEqual((record['phase'], record['wire_version']), ('published', 2))
            self.assertEqual((provider['metadata'], provider['access']), (wire['metadata'], wire['access']))
        with self.assertRaises(Held):  # nothing is left for an update
            self.update_release([review_file])

    def test_published_v1_records_are_updated_in_place_exactly_once(self):
        base = self.published_v1('bulk-052', list(SOURCES[:2]))
        before = {sid: bulk.load_record(self.paths, sid) for sid in SOURCES[:2]}
        review_file, sheet = self.v2_review(base)
        release_file = self.update_release([review_file])
        start = len(self.provider.calls)
        self.assertEqual(self.update(release_file)['counts'], {'updated': 2})
        writes = [(m, p) for m, p in self.provider.calls[start:] if m != 'GET']
        expected = []
        for sid in SOURCES[:2]:
            record = bulk.load_record(self.paths, sid)
            row = next(r for r in sheet['rows'] if r['source_id'] == sid)
            self.assertEqual((record['phase'], record['wire_version'], record['wire_sha256']), ('published', 2,
                                                                                                 row['wire_sha256']))
            self.assertEqual((record['identity'], record['pids']), (before[sid]['identity'], before[sid]['pids']))
            self.assertEqual(record['update']['previous']['wire_sha256'], before[sid]['wire_sha256'])
            self.assertEqual([record['counts'][k] for k in ('edit', 'update', 'publish')], [1, 1, 1])
            provider = self.provider.records[record['identity']['id']]
            wire = parse(bulk.prepare_entry(self.paths, record).body)
            self.assertEqual((provider['metadata'], provider['access'], provider['edit']),
                             (wire['metadata'], wire['access'], None))
            path = '/api/records/' + record['identity']['id'] + '/draft'
            expected += [('POST', path), ('PUT', path), ('POST', path + '/actions/publish')]
        self.assertEqual(writes, expected)
        start = len(self.provider.calls)
        self.assertEqual(self.update(release_file)['counts'], {'already-updated': 2})
        self.assertEqual(self.provider.calls[start:], [])

    def test_update_holds_before_saving_when_the_published_record_changed_elsewhere(self):
        release_file, start = self.ready_update('bulk-053', SOURCES[0])
        record = bulk.load_record(self.paths, SOURCES[0])
        self.provider.records[record['identity']['id']]['metadata']['title'] = 'Changed by hand'
        result = self.update(release_file)
        self.assertEqual(result['counts'], {'held': 1})
        self.assertIn('published wire', result['holds'][0]['reason'])
        self.assertEqual([m for m, _ in self.provider.calls[start:] if m != 'GET'], ['POST'])
        self.assertEqual(bulk.load_record(self.paths, SOURCES[0])['phase'], 'editing')

    def test_lost_update_answer_is_observed_and_never_sent_twice(self):
        release_file, start = self.ready_update('bulk-054', SOURCES[0])
        self.provider.lose_at = start + 2  # community, edit, then the PUT takes effect and its answer is lost
        self.assertEqual(self.update(release_file)['status'], 'stopped')
        self.provider.lose_at = None
        self.assertEqual(bulk.load_record(self.paths, SOURCES[0])['phase'], 'edit-open')
        before = len(self.provider.calls)
        outcome = self.runner('reconcile').reconcile(SOURCES[0])
        self.assertTrue(all(m == 'GET' for m, _ in self.provider.calls[before:]))
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('edit-saved', []))
        self.assertEqual(self.update(release_file)['counts'], {'updated': 1})
        self.assertEqual([m for m, _ in self.provider.calls[start:] if m != 'GET'], ['POST', 'PUT', 'POST'])

    def test_lost_publish_answer_completes_by_readback_only(self):
        release_file, start = self.ready_update('bulk-055', SOURCES[0])
        self.provider.lose_at = start + 3
        self.assertEqual(self.update(release_file)['status'], 'stopped')
        self.provider.lose_at = None
        outcome = self.runner('reconcile').reconcile(SOURCES[0])
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('edit-published', []))
        before = len(self.provider.calls)
        self.assertEqual(self.update(release_file)['counts'], {'updated': 1})
        self.assertTrue(all(m == 'GET' for m, _ in self.provider.calls[before:]))

    def test_edit_that_never_arrived_is_allowed_once_more_and_a_lost_edit_answer_is_adopted(self):
        release_file, start = self.ready_update('bulk-056', SOURCES[0])
        self.provider.fail_at = start + 1  # the edit request never reaches the provider
        self.assertEqual(self.update(release_file)['status'], 'stopped')
        self.provider.fail_at = None
        outcome = self.runner('reconcile').reconcile(SOURCES[0])
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('editing', ['edit']))
        self.provider.lose_at = len(self.provider.calls) + 1  # this time the edit opens and its answer is lost
        self.assertEqual(self.update(release_file)['status'], 'stopped')
        self.provider.lose_at = None
        outcome = self.runner('reconcile').reconcile(SOURCES[0])
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('edit-open', []))
        self.assertEqual(self.update(release_file)['counts'], {'updated': 1})
        record = bulk.load_record(self.paths, SOURCES[0])
        self.assertEqual([record['counts'][k] for k in ('edit', 'update', 'publish')], [2, 1, 1])
        self.assertRaises(Held, self.runner('reconcile').reconcile, SOURCES[0])  # only held records

    def test_pair_record_is_updated_with_both_originals(self):
        base = self.pair_review('pairs-050', PAIR_TARGET)
        self.drafts(base)
        self.assertEqual(self.publish(self.release([base], name='release-pairs-050'))['counts'], {'published': 1})
        review_file, sheet = self.v2_review(base)
        self.assertEqual(sheet['rows'][0]['target']['source_ids'], list(PAIR))
        self.assertEqual(self.update(self.update_release([review_file]))['counts'], {'updated': 1})
        record = bulk.load_record(self.paths, PAIR[0])
        provider = self.provider.records[record['identity']['id']]
        self.assertEqual((record['wire_version'], sorted(provider['files'])), (2, [s + '.xml' for s in PAIR]))
        self.assertIn('FGDC-2953 and FGDC-3181 (identical records)',
                      provider['metadata']['additional_descriptions'][-1]['description'])

    def test_releases_keep_their_action_and_older_records_load_with_unspent_edits(self):
        base = self.published_v1('bulk-057', [SOURCES[0]])
        release_file = self.update_release([self.v2_review(base)[0]])
        self.assertRaises(Held, bulk.load_release, self.paths, release_file)  # not a publication release
        old = bulk.bulk_root(self.paths) / 'releases' / 'release-bulk-057.json'
        self.assertRaises(Held, bulk.load_release, self.paths, old, 'update')
        path = bulk.record_path(self.paths, SOURCES[0])
        document = json.loads(path.read_text())
        for kind in bulk.EDIT_WRITES:
            del document['counts'][kind]
        path.write_text(json.dumps(document))
        self.assertEqual([bulk.load_record(self.paths, SOURCES[0])['counts'][k] for k in bulk.EDIT_WRITES], [0, 0, 0])

    def test_update_release_from_the_command_line_names_only_the_canary(self):
        base = self.published_v1('bulk-058', list(SOURCES[:2]))
        review_file = self.v2_review(base)[0]
        argv = ['modern_bulk', 'release', '--output-dir', str(Path(self.temp.name) / 'prepared'), '--name', 'update-canary',
                '--review', str(review_file), '--action', 'update', '--only', SOURCES[0], '--authority', 'Brett Johnson',
                '--instruction', 'canary', '--instructed-at', '2026-10-20', '--prepared-by', 'Bulk test']
        with patch.object(bulk.sys, 'argv', argv), patch.object(bulk.draft, 'production_token') as token, \
                patch('builtins.print') as printed:
            self.assertEqual(bulk.main(), 0)
        token.assert_not_called()
        result = json.loads(printed.call_args.args[0])
        self.assertEqual((result['action'], result['records']), ('update', 1))
        release, _, members = bulk.load_release(self.paths, result['release'], 'update')
        self.assertEqual((release['records'], list(members)), ([SOURCES[0]], [SOURCES[0]]))

    def test_partly_refused_save_is_rebound_to_a_newer_reviewed_wire(self):
        base = self.published_v1('bulk-059', [SOURCES[0]])
        first, _ = self.v2_review(base)
        release_file = self.update_release([first], name='update-059')
        real = bulk.wire_v2.build

        def multipolygon(*args, **kwargs):  # the canary's first wire: one MultiPolygon feature
            record = real(*args, **kwargs)
            record['metadata']['locations'] = {'features': [{'description': 'box', 'geometry': {
                'type': 'MultiPolygon', 'coordinates': [[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]]]}}]}
            return record
        with patch.object(bulk.wire_v2, 'build', multipolygon), patch.object(bulk.wire_v2, 'validate'):
            sheet = bulk.build_v2_sheet(self.paths, base, 'Planner', now=self.clock.now, suffix='v2b')
            bulk.write_exclusive(bulk.sheet_path(self.paths, sheet['batch_id']), sheet)
            refused = self.review(sheet['batch_id'], sheet)
            result = self.update(self.update_release([refused], name='update-059b'))
        self.assertEqual(result['counts'], {'held': 1})
        self.assertIn('reviewed v2 wire', result['holds'][0]['reason'])
        record = bulk.load_record(self.paths, SOURCES[0])
        self.assertEqual((record['phase'], record['counts']['update'], record['counts']['publish']), ('edit-open', 1, 0))
        _, _, _, members = bulk.load_review(self.paths, first)
        writes = len(self.writes())
        outcome = self.runner('reconcile').rebind_update(SOURCES[0], members[SOURCES[0]], 'Operator', 'MultiPolygon refused')
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('edit-open', ['update']))
        self.assertEqual(len(self.writes()), writes)  # GET only
        self.assertEqual(self.update(release_file)['counts'], {'updated': 1})
        record = bulk.load_record(self.paths, SOURCES[0])
        self.assertEqual((record['wire_version'], record['counts']['update']), (2, 2))
        self.assertEqual(record['update']['rebound'][0]['decided_by'], 'Operator')
        provider = self.provider.records[record['identity']['id']]
        self.assertEqual(provider['metadata'], parse(bulk.prepare_entry(self.paths, record).body)['metadata'])

    def test_reviewed_source_repairs_apply_exactly_and_must_apply(self):
        base = json.loads(bulk.prepare_entry(self.paths, {'source_id': SOURCES[0]}, 2).body)
        word = base['metadata']['description'].split()[0]
        with patch.object(bulk, 'source_repairs', return_value={SOURCES[0]: [{'from': word, 'to': word + 'X'}]}):
            fixed = bulk.prepare_entry(self.paths, {'source_id': SOURCES[0]}, 2)
            self.assertTrue(json.loads(fixed.body)['metadata']['description'].startswith(word + 'X'))
            self.assertEqual(fixed.evidence['source_repairs'], 1)
        with patch.object(bulk, 'source_repairs', return_value={SOURCES[0]: [{'from': 'no such text', 'to': 'x'}]}), \
                self.assertRaises(Held):
            bulk.prepare_entry(self.paths, {'source_id': SOURCES[0]}, 2)
        self.assertEqual(set(bulk.source_repairs()), {'FGDC-885', 'FGDC-2570', 'FGDC-2583', 'FGDC-2588', 'FGDC-2589',
                                                      'FGDC-2591', 'FGDC-2674', 'FGDC-2733', 'FGDC-2768', 'FGDC-3808'})

    def test_pinned_map_as_text_sources_lose_only_their_map(self):
        sid = SOURCES[0]
        plain = json.loads(bulk.prepare_entry(self.paths, {'source_id': sid}, 2).body)['metadata']
        with patch.object(bulk, 'map_as_text', return_value={sid: 'contradicts its text'}):
            texted = json.loads(bulk.prepare_entry(self.paths, {'source_id': sid}, 2).body)['metadata']
        self.assertIn('locations', plain)
        self.assertNotIn('locations', texted)
        self.assertIn('Bounding coordinates as given', texted['additional_descriptions'][-1]['description'])
        self.assertEqual({k: v for k, v in plain.items() if k not in ('locations', 'additional_descriptions')},
                         {k: v for k, v in texted.items() if k not in ('locations', 'additional_descriptions')})
        self.assertEqual(len(bulk.map_as_text()), 19)

    def test_a_lifted_exclusion_no_longer_bars_the_source_and_the_exclusion_stays(self):
        bulk.exclude(self.paths, SOURCES[0], 'held for source-text repair: test', 'Reviewer agent')
        bulk.exclude(self.paths, SOURCES[2], 'duplicate of FGDC-1915 in the source collection', 'Reviewer agent')
        self.assertRaises(Held, bulk.lift_exclusion, self.paths, SOURCES[2], 'Operator', 'mistaken')
        self.assertIn(SOURCES[0], bulk.exclusions(self.paths))
        self.assertRaises(Held, bulk.lift_exclusion, self.paths, SOURCES[1], 'Operator', 'repaired')
        bulk.lift_exclusion(self.paths, SOURCES[0], 'Operator', 'text repaired in source_repairs.json')
        self.assertNotIn(SOURCES[0], bulk.exclusions(self.paths))
        self.assertTrue((bulk.bulk_root(self.paths) / 'exclusions' / (SOURCES[0] + '.json')).exists())
        self.assertRaises(FileExistsError, bulk.lift_exclusion, self.paths, SOURCES[0], 'Operator', 'again')
        review_file = self.review('bulk-060', self.plan('bulk-060', [SOURCES[0]])[1])
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})

    def test_an_adopted_draft_with_an_old_wire_is_revised_then_published(self):
        prepared = prepare(Path(self.paths.zenodo_json_dir) / 'FGDC-1915.json', self.paths)
        old = parse(prepared.body)
        old['metadata']['subjects'] = old['metadata']['subjects'][:1]  # the draft holds an older, cut wire
        record_id = self.provider.add_draft(old, 'FGDC-1915.xml', prepared.xml)
        provider_record = self.provider.records[record_id]
        identity = {'id': record_id, 'parent_id': provider_record['parent'], 'owner': OWNER,
                    'created': provider_record['created']}
        (draft.state_root(self.paths) / 'FGDC-1915.modern-create-v1.intent.json').write_text('{}')
        journal = {'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {
            'FGDC-1915': {'phase': 'verified', 'identity': identity, 'verified_revision': 1,
                          'untrusted_candidate_id': record_id, 'binding': 'x', 'counts': {}, 'requests': []}}}
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))
        review_file, _ = self.v2_review(self.review('bulk-061', self.plan('bulk-061', ['FGDC-1915'])[1]))
        self.assertEqual(self.drafts(review_file)['counts'], {'adopted': 1})
        self.assertEqual(self.publish(self.release([review_file], name='release-061'))['counts'], {'held': 1})
        record = bulk.load_record(self.paths, 'FGDC-1915')  # the old draft does not match: held before any write
        self.assertEqual((record['phase'], record['counts']['review'], record['hold']['reason']),
                         ('adopted', 0, 'provider metadata differs from the wire'))
        _, _, _, members = bulk.load_review(self.paths, review_file)
        outcome = self.runner('drafts').revise_draft('FGDC-1915', members['FGDC-1915'], 'Operator', 'keyword repaired')
        self.assertEqual(outcome['phase'], 'draft-verified')
        puts = len([m for m, _ in self.writes() if m == 'PUT'])
        again = self.runner('drafts').revise_draft('FGDC-1915', members['FGDC-1915'], 'Operator', 'again')
        self.assertEqual((again['phase'], len([m for m, _ in self.writes() if m == 'PUT'])), ('draft-verified', puts))
        self.assertEqual(self.publish(self.release([review_file], name='release-061b'))['counts'], {'published': 1})
        wire = parse(bulk.prepare_entry(self.paths, bulk.load_record(self.paths, 'FGDC-1915')).body)
        self.assertEqual((provider_record['metadata'], provider_record['access']), (wire['metadata'], wire['access']))

    def test_a_lost_revision_answer_is_recovered_without_a_second_put_when_it_took_effect(self):
        prepared = prepare(Path(self.paths.zenodo_json_dir) / 'FGDC-1915.json', self.paths)
        old = parse(prepared.body)
        old['metadata']['subjects'] = old['metadata']['subjects'][:1]
        record_id = self.provider.add_draft(old, 'FGDC-1915.xml', prepared.xml)
        provider_record = self.provider.records[record_id]
        identity = {'id': record_id, 'parent_id': provider_record['parent'], 'owner': OWNER,
                    'created': provider_record['created']}
        (draft.state_root(self.paths) / 'FGDC-1915.modern-create-v1.intent.json').write_text('{}')
        journal = {'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {
            'FGDC-1915': {'phase': 'verified', 'identity': identity, 'verified_revision': 1,
                          'untrusted_candidate_id': record_id, 'binding': 'x', 'counts': {}, 'requests': []}}}
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))
        review_file, _ = self.v2_review(self.review('bulk-062', self.plan('bulk-062', ['FGDC-1915'])[1]))
        self.drafts(review_file)
        _, _, _, members = bulk.load_review(self.paths, review_file)
        self.provider.lose_at = len(self.provider.calls) + 1  # the GET answers; the PUT takes effect, its answer is lost
        self.assertRaises(Held, self.runner('drafts').revise_draft, 'FGDC-1915', members['FGDC-1915'], 'Operator', 'n')
        self.provider.lose_at = None
        record = bulk.load_record(self.paths, 'FGDC-1915')
        self.assertIn('interrupted', record['hold']['reason'])
        puts = len([m for m, _ in self.writes() if m == 'PUT'])
        self.assertEqual(self.runner('drafts').revise_draft('FGDC-1915', members['FGDC-1915'], 'Operator', 'n')['phase'],
                         'draft-verified')
        self.assertEqual(len([m for m, _ in self.writes() if m == 'PUT']), puts)  # no second PUT
        self.assertEqual(self.publish(self.release([review_file], name='release-062'))['counts'], {'published': 1})

    def unbound_legacy_create(self, sid):
        (draft.state_root(self.paths) / (sid + '.modern-create-v1.intent.json')).write_text('{"intent": 1}')
        journal = {'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {
            sid: {'phase': 'started', 'identity': None, 'binding': 'x', 'requests': [],
                  'counts': {'get': 0, 'create': 1, 'init': 0, 'content': 0, 'commit': 0}}}}
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))

    def inventory_file(self, extra=()):
        records = [dict(r, owner=int(OWNER)) for r in [*self.provider.listing(), *extra]]
        document = {'kind': operator.INVENTORY_KIND, 'complete': True,
                    'captured_at': self.clock.now().replace(microsecond=0).isoformat(),
                    'record_count': len(records), 'records': records}
        path = Path(self.temp.name) / 'inventory.json'
        path.write_text(json.dumps(document))
        return path

    def test_an_unbound_legacy_create_is_released_on_a_clean_inventory_then_created_once(self):
        sid = SOURCES[0]
        self.unbound_legacy_create(sid)
        review_file = self.review('bulk-063', self.plan('bulk-063', [sid])[1])
        self.assertEqual(self.drafts(review_file)['counts'], {'held': 1})  # the claim holds it before any write
        self.assertEqual(self.writes(), [])
        record = bulk.load_record(self.paths, sid)
        record['hold'] = None
        bulk.save_record(self.paths, record)  # a planned barrier hold, released by `unhold` in production
        title = parse(bulk.member_now(self.paths, sid).body)['metadata']['title']
        twin = {'id': 99999999, 'title': title, 'files': [], 'state': 'unsubmitted', 'submitted': False, 'doi': None}
        self.assertRaises(Held, bulk.release_legacy_claim, self.paths, sid, self.inventory_file([twin]), 'Operator',
                          'Brett', 'no record', now=self.clock.now)
        stale = self.inventory_file()
        self.assertRaises(Held, bulk.release_legacy_claim, self.paths, sid, stale, 'Operator', 'Brett', 'no record',
                          now=lambda: self.clock.now() + timedelta(days=2))
        bulk.release_legacy_claim(self.paths, sid, self.inventory_file(), 'Operator', 'Brett Johnson, 2026-10-22',
                                  'the 403 came from the edge firewall', now=self.clock.now)
        self.assertTrue(bulk.legacy_released(self.paths, sid))
        journal = json.loads(Path(self.paths.uploads_registry_path + '.modern-v1.json').read_text())
        bound = dict(journal['targets'][sid], untrusted_candidate_id='30000999')
        self.assertRaises(Held, bulk.release_legacy_claim, self.paths, 'FGDC-1916', self.inventory_file(), 'Operator',
                          'Brett', 'no record', now=self.clock.now)  # no single-record row at all
        journal['targets']['FGDC-1916'] = bound
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))
        self.assertRaises(Held, bulk.release_legacy_claim, self.paths, 'FGDC-1916', self.inventory_file(), 'Operator',
                          'Brett', 'a create that answered 201 has a draft', now=self.clock.now)
        del journal['targets']['FGDC-1916']
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))
        self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 1})
        self.assertEqual(len([c for c in self.writes() if c == ('POST', '/api/records')]), 1)
        journal = json.loads(Path(self.paths.uploads_registry_path + '.modern-v1.json').read_text())
        journal['targets'][sid]['phase'] = 'changed'
        Path(self.paths.uploads_registry_path + '.modern-v1.json').write_text(json.dumps(journal))
        self.assertRaises(Held, bulk.legacy_released, self.paths, sid)  # the release binds the row as it stood

    def test_update_reads_the_keychain_as_its_own_action(self):
        with patch.object(bulk.draft, 'production_token', return_value=TOKEN) as token, \
                patch.object(bulk.draft, 'Transport', return_value='transport'):
            bulk.transport_and_token('update', 'pices-zenodo-production')
            token.assert_called_with('Zenodo production token (update): ', 'pices-zenodo-production',
                                     action='bulk-update')
            bulk.transport_and_token('update', None)
            token.assert_called_with('Zenodo production token (update): ', None, action='publish')
        self.assertIn('bulk-update', draft.KEYCHAIN_ACTIONS)

    # ---- the 25 non-Exxon pairs (ADR 0015)

    def proposed_types(self):
        """The pinned types plus the proposal for the 25 pairs, as the manifest will read once Brett merges it."""
        merged = {**bulk.resource_types(), **parse(PROPOSAL.read_bytes())['types']}
        return patch.object(bulk, 'resource_types', return_value=merged)

    def test_nonexxon_pairs_plan_as_pairs_and_publish_in_v2_with_the_proposed_types(self):
        sheet = bulk.build_pair_sheet(self.paths, 'pairs-060', [ADFG_TARGET, FOODHABITS_TARGET], 'Planner',
                                      fixtures.NOW.isoformat(), now=self.clock.now)
        self.assertEqual([(r['source_id'], r['policy'], r['target']['source_ids']) for r in sheet['rows']],
                         [(ADFG_PAIR[0], content_class.NONEXXON_POLICY, list(ADFG_PAIR)),
                          (FOODHABITS_PAIR[0], content_class.NONEXXON_POLICY, list(FOODHABITS_PAIR))])
        self.assertEqual(sheet['twins'], [])
        bulk.write_exclusive(bulk.sheet_path(self.paths, 'pairs-060'), sheet)
        base = self.review('pairs-060', sheet)
        with self.proposed_types():
            review_file, v2_sheet = self.v2_review(base)
            self.assertEqual([(r['wire_version'], r['v2']['resource_type']) for r in v2_sheet['rows']],
                             [(2, 'publication-report'), (2, 'dataset')])
            self.assertEqual(self.drafts(review_file)['counts'], {'drafted': 2})
            self.assertEqual(self.publish(self.release([review_file], name='release-pairs-060'))['counts'],
                             {'published': 2})
        for pair, resource_type in ((ADFG_PAIR, 'publication-report'), (FOODHABITS_PAIR, 'dataset')):
            record = bulk.load_record(self.paths, pair[0])
            provider = self.provider.records[record['identity']['id']]
            self.assertEqual((record['phase'], record['wire_version'], sorted(provider['files'])),
                             ('published', 2, [s + '.xml' for s in pair]))
            self.assertEqual(provider['metadata']['resource_type'], {'id': resource_type})
            self.assertFalse(provider['metadata']['title'].endswith(bulk.wire_v2.ARTIFACT_SUFFIX))
            self.assertEqual(provider['access'], {'record': 'public', 'files': 'public'})
            self.assertIsNone(bulk.load_record(self.paths, pair[1]))
            for sid in pair:
                self.assertTrue(bulk.intent_path(self.paths, sid).exists())
        foodhabits = self.provider.records[bulk.load_record(self.paths, FOODHABITS_PAIR[0])['identity']['id']]
        self.assertEqual(foodhabits['metadata']['creators'], [
            {'person_or_org': {'type': 'personal', 'given_name': 'Pat', 'family_name': 'Livingston'}},
            {'person_or_org': {'type': 'personal', 'given_name': 'Douglas', 'family_name': 'Smith'}}])
        adfg = self.provider.records[bulk.load_record(self.paths, ADFG_PAIR[0])['identity']['id']]
        self.assertEqual(adfg['metadata']['creators'], [{'person_or_org': {
            'name': 'Alaska Department of Fish and Game (ADF&G), Division of Commercial Fisheries, '
                    'Management and Development Division', 'type': 'organizational'}}])

    def test_v2_pair_without_a_reviewed_resource_type_holds_until_the_manifest_carries_it(self):
        target = {'record_target_id': ADFG_TARGET, 'reviewed_at': fixtures.NOW.isoformat()}
        self.assertEqual(bulk.pair_row(self.paths, target)['policy'], content_class.NONEXXON_POLICY)  # v1 needs no type
        pinned = bulk.resource_types()
        self.assertEqual(pinned[ADFG_PAIR[0]], 'publication-report')  # r4 carries the reviewed type
        without = {k: v for k, v in pinned.items() if k != ADFG_PAIR[0]}
        with patch.object(bulk, 'resource_types', return_value=without), self.assertRaises(bulk.RecordHold) as held:
            bulk.pair_row(self.paths, target, 2)
        self.assertIn('no reviewed resource type for FGDC-2949', str(held.exception))
        row = bulk.pair_row(self.paths, target, 2)
        self.assertEqual((row['wire_version'], row['v2']['resource_type']), (2, 'publication-report'))


def result_outcomes(paths, result):
    return json.loads(Path(result['ledger']).read_text())['outcomes']


if __name__ == '__main__':
    unittest.main()
