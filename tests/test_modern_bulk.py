"""Offline contracts for the bulk draft and publication route (ADR 0013).

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
from scripts import modern_operator as operator
from scripts import modern_singleton_executor as draft
from scripts.modern_singleton import Held, encode, parse, prepare
from scripts.path_config import OutputPaths
from scripts.production_mutations import reject_modern_attempt
from tests import modern_singleton_fixtures as fixtures

OWNER = '123'
TOKEN = 'dummy-modern-bulk-offline-only'
SOURCES = ('FGDC-1915', 'FGDC-1916', 'FGDC-1917', 'FGDC-1924', 'FGDC-2708')


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
    """Synthetic InvenioRDM: drafts, files, community submission and the legacy listing."""

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
            'pending': set(), 'review': None, 'status': 'draft', 'request': None}
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
                 'access': {'record': 'public', 'files': 'restricted'},
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
                      'review': None, 'status': 'draft', 'request': None}
            self.records[record_id] = record
            return 201, self.document(record)
        parts = path.split('/')
        record = self.records[parts[3]]
        rest = '/'.join(parts[4:])
        if rest == 'draft' and method == 'GET':
            if record['status'] == 'published':
                return 404, {'status': 404, 'message': 'not found'}
            return 200, self.document(record)
        if rest == 'draft/files' and method == 'POST':
            key = parse(body)[0]['key']
            record['files'][key] = b''
            record['pending'].add(key)
            return 201, {'entries': [self.entry(record, key)]}
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
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=list(SOURCES))

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
        release, release_sha = bulk.load_release(self.paths, release_file)
        runner = self.runner('publish')
        return runner.run(release['records'], lambda sid: runner.publish_member(sid, release_sha))

    def writes(self):
        return [(m, p) for m, p in self.provider.calls if m != 'GET']

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
                                                'submit': 0, 'get': 2})
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
        self.assertEqual((outcome['phase'], outcome['allowed_again']), ('initialized', ['content']))
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


def result_outcomes(paths, result):
    return json.loads(Path(result['ledger']).read_text())['outcomes']


if __name__ == '__main__':
    unittest.main()
