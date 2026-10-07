"""Operator toolkit contracts: bounded inventory capture and executor-accepted minting."""

import hashlib
import io
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import modern_operator as operator
from scripts import modern_singleton_executor as executor
from scripts.modern_singleton import Held, encode, sha
from scripts.production_mutations import PROTECTED
from tests import modern_singleton_fixtures as fixtures

NOW = fixtures.NOW


class ListingTransport:
    """Offline listing and detail pages; the token is never in a response unless a test puts it there."""

    def __init__(self, pages, details=None, status=200, mime='application/json'):
        self.pages, self.details = pages, details or {}
        self.status, self.mime, self.calls = status, mime, []

    def request(self, method, path, body, *, timeout, accept=executor.MIME):
        self.calls.append((method, path, body, timeout, accept))
        if path.startswith(operator.LIST_PATH + '/'):
            record_id = path.rsplit('/', 1)[1]
            payload = self.details.get(record_id, {'id': int(record_id), 'files': []})
            return self.status, self.mime, payload if isinstance(payload, bytes) else encode(payload)
        page = int(path.split('page=')[1].split('&')[0])
        raw = self.pages[page - 1] if page <= len(self.pages) else []
        return self.status, self.mime, raw if isinstance(raw, bytes) else encode(raw)


def owned(record_id, title, files=(), md5='0' * 32, **extra):
    return {'id': record_id, 'owner': 123, 'title': title, 'state': 'done', 'submitted': True,
            'files': [{'filename': name, 'checksum': 'md5:' + md5, 'filesize': 10} for name in files], **extra}


class OperatorInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.evidence = Path(self.temporary.name) / 'evidence'

    def test_inventory_pages_until_empty_fetches_missing_files_and_retains_receipts(self):
        transport = ListingTransport([[owned(1, 'Other record', ['x.xml']), owned(2, 'No files listed')], [owned(3, 'Third', ['y.xml'])], []],
                                     details={'2': {'id': 2, 'files': [{'filename': 'hidden.xml', 'checksum': 'md5:' + 'a' * 32}]}})
        out, document = operator.capture_inventory(transport, fixtures.TOKEN, self.evidence, 'capture agent', now=lambda: NOW, pace=0)
        paths = [call[1] for call in transport.calls]
        self.assertEqual(paths, [operator.listing_path(1), operator.listing_path(2), operator.listing_path(3), operator.detail_path('2')])
        self.assertTrue(all(call[4] == 'application/json' and call[2] is None for call in transport.calls))
        self.assertEqual((document['kind'], document['complete'], document['record_count'], len(document['details'])),
                         (operator.INVENTORY_KIND, True, 3, 1))
        self.assertEqual((document['captured_at'], document['completed_at']), (NOW.isoformat(), NOW.isoformat()))
        by_id = {row['id']: row for row in document['records']}
        self.assertEqual((by_id['1']['files_source'], by_id['2']['files_source'], by_id['3']['files_source']),
                         ('listing', 'detail', 'listing'))
        self.assertEqual(by_id['2']['files'], [{'name': 'hidden.xml', 'md5': 'a' * 32, 'size': None}])
        self.assertEqual(by_id['1']['files'], [{'name': 'x.xml', 'md5': '0' * 32, 'size': 10}])
        self.assertEqual(sha(out.read_bytes()), sha(encode(document)))
        for receipt in document['pages'] + document['details']:
            self.assertEqual(sha((self.evidence / receipt['raw']).read_bytes()), receipt['response_sha256'])
        self.assertEqual(sorted(p.name for p in self.evidence.iterdir() if p.name.endswith('.partial')), [])
        self.assertNotIn(fixtures.TOKEN.encode(), out.read_bytes())

    def test_inventory_holds_on_errors_bounds_screens_and_shapes_without_leaving_an_inventory(self):
        cases = (('status', ListingTransport([[]], status=403), {}),
                 ('mime', ListingTransport([[]], mime='text/html'), {}),
                 ('shape', ListingTransport([{'hits': []}]), {}),
                 ('bad_id', ListingTransport([[{'id': 'x', 'title': 't'}], []]), {}),
                 ('duplicate_id', ListingTransport([[owned(1, 'a', ['a'])], [owned(1, 'a', ['a'])], []]), {}),
                 ('bound', ListingTransport([[owned(1, 'a', ['a'])], [owned(2, 'b', ['b'])], [owned(3, 'c', ['c'])]]), {'max_pages': 2}),
                 ('too_many_details', ListingTransport([[owned(1, 'a')], []]), {'max_details': 0}),
                 ('detail_mismatch', ListingTransport([[owned(1, 'a')], []], details={'1': {'id': 9, 'files': []}}), {}),
                 ('echo', ListingTransport([[owned(1, 'leak ' + fixtures.TOKEN, ['a'])], []]), {}),
                 ('credential_pattern', ListingTransport([[owned(1, 'x', ['a'], note='access_token: abc')], []]), {}))
        for label, transport, kwargs in cases:
            with self.subTest(label=label):
                evidence = self.evidence / label
                with self.assertRaises(Held):
                    operator.capture_inventory(transport, fixtures.TOKEN, evidence, 'capture agent', now=lambda: NOW, pace=0, **kwargs)
                leftovers = [p.name for p in evidence.iterdir()] if evidence.exists() else []
                self.assertTrue(all(name.endswith('.partial') for name in leftovers), leftovers)


    def test_inventory_summary_over_the_document_bound_holds_with_partial_receipts_only(self):
        transport = ListingTransport([[owned(1, 'a' * 400, ['a.xml'])], []])
        with patch('scripts.modern_singleton_executor.MAX_BYTES', 500), self.assertRaises(Held):
            operator.capture_inventory(transport, fixtures.TOKEN, self.evidence, 'capture agent', now=lambda: NOW, pace=0)
        names = [p.name for p in self.evidence.iterdir()]
        self.assertTrue(names and all(name.endswith('.partial') for name in names), names)

    def test_known_records_are_not_detail_fetched_and_are_named_in_the_summary(self):
        """RDM drafts list no files in the legacy listing; the journal pins the ones this chain made."""
        transport = ListingTransport([[owned(1, 'Listed', ['x.xml']), owned(2, 'Known draft'), owned(3, 'Unknown')], []],
                                     details={'3': {'id': 3, 'files': [{'filename': 'late.xml', 'checksum': 'md5:' + 'a' * 32}]}})
        out, document = operator.capture_inventory(transport, fixtures.TOKEN, self.evidence, 'capture agent',
                                                   now=lambda: NOW, pace=0, known={2}, max_details=1)
        self.assertEqual([call[1] for call in transport.calls],
                         [operator.listing_path(1), operator.listing_path(2), operator.detail_path('3')])
        self.assertEqual((document['skipped_details'], len(document['details'])), (['2'], 1))
        by_id = {row['id']: row for row in document['records']}
        self.assertEqual((by_id['2']['files_source'], by_id['2']['files'], by_id['3']['files_source']), ('none', [], 'detail'))
        self.assertEqual(operator.rebuild_records(out, document), document['records'])
        # The matcher still treats the skipped record as known and every other record on its own evidence.
        self.assertEqual(operator.inventory_matches(document['records'], 'FGDC-141', 'nothing', b'<x/>', known={'2'}), [])
        self.assertEqual(operator.inventory_matches(document['records'], 'FGDC-141', 'nothing', b'<x/>'),
                         [{'id': '2', 'reasons': ['files_unverified']}])
        with self.assertRaises(Held):  # a known id must look like a record id
            operator.capture_inventory(transport, fixtures.TOKEN, self.evidence / 'bad', 'capture agent',
                                       now=lambda: NOW, pace=0, known={'x'})
        self.assertFalse((self.evidence / 'bad').exists())
        self.assertIn('2', operator.known_records(None, ('2',)))

    def test_cli_inventory_settles_known_ids_before_the_token_stage(self):
        from scripts.path_config import OutputPaths
        output = Path(self.temporary.name) / 'out'
        journal = Path(OutputPaths(str(output), 'production').uploads_registry_path + '.modern-v1.json')
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_bytes(encode({'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {
            'FGDC-9': {'identity': {'id': '2', 'parent_id': '20', 'owner': '123', 'created': NOW.isoformat()}}}}))
        transport = ListingTransport([[owned(1, 'Listed', ['x.xml']), owned(2, 'Journal draft'), owned(5, 'Flagged'),
                                       owned(3, 'Unknown')], []],
                                     details={'3': {'id': 3, 'files': [{'filename': 'late.xml', 'checksum': 'md5:' + 'a' * 32}]}})
        argv = ['modern_operator', 'inventory', '--evidence-dir', str(self.evidence), '--captured-by', 'capture agent',
                '--output-dir', str(output), '--known-record', '5', '--max-details', '1', '--token-keychain', 'pices-test']
        with patch('sys.argv', argv), patch('scripts.modern_operator.time.sleep'), \
                patch('scripts.modern_singleton_executor.production_token', return_value=fixtures.TOKEN) as token, \
                patch('scripts.modern_singleton_executor.Transport', return_value=transport), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(operator.main(), 0)
        result = json.loads(out.getvalue())
        self.assertEqual((result['record_count'], result['details'], result['skipped_details'], result['provider_requests']),
                         (4, 1, 2, 3))
        self.assertEqual([call[1] for call in transport.calls],
                         [operator.listing_path(1), operator.listing_path(2), operator.detail_path('3')])
        self.assertEqual(token.call_args.kwargs, {'action': 'inventory'})
        # An output directory without a journal holds before any token is read.
        missing = argv[:6] + ['--output-dir', str(output / 'missing'), '--token-keychain', 'pices-test']
        with patch('sys.argv', missing), patch('scripts.modern_singleton_executor.production_token') as token, \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(operator.main(), 1)
        self.assertEqual((token.call_count, json.loads(out.getvalue())['held']), (0, True))


class OperatorMintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=['FGDC-141'])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = fixtures.Fixture(Path(self.temporary.name) / 'f', self.prepared_root)
        self.root = Path(self.temporary.name)
        self.count = 0

    def inventory(self, raw_records, captured=None, details=None, terminal_count=0, tamper=False, edit=False,
                  skipped=()):
        """A complete inventory with raw receipts beside it, exactly as capture writes them."""
        self.count += 1
        stamp = f'{self.count}'
        page1, page2 = encode(raw_records), encode([owned(99, 'z', ['z'])] * terminal_count)
        (self.root / f'inventory-{stamp}.page-1.json').write_bytes(page1)
        (self.root / f'inventory-{stamp}.page-2.json').write_bytes(page2)
        detail_rows, detail_by_id = [], {}
        for record_id, detail in (details or {}).items():
            raw = encode(detail)
            (self.root / f'inventory-{stamp}.detail-{record_id}.json').write_bytes(raw)
            detail_rows.append({'id': record_id, 'path': operator.detail_path(record_id), 'response_sha256': sha(raw),
                                'raw': f'inventory-{stamp}.detail-{record_id}.json'})
            detail_by_id[int(record_id)] = detail
        document = {'schema_version': 1, 'kind': operator.INVENTORY_KIND, 'origin': executor.ORIGIN,
                    'captured_by': 'capture agent', 'captured_at': (captured or NOW - timedelta(minutes=5)).isoformat(),
                    'page_size': operator.PAGE_SIZE,
                    'pages': [{'page': 1, 'path': operator.listing_path(1), 'http_status': 200, 'count': len(raw_records),
                               'response_sha256': sha(page1), 'raw': f'inventory-{stamp}.page-1.json'},
                              {'page': 2, 'path': operator.listing_path(2), 'http_status': 200, 'count': terminal_count,
                               'response_sha256': sha(page2), 'raw': f'inventory-{stamp}.page-2.json'}],
                    'details': detail_rows, 'skipped_details': list(skipped), 'complete': True,
                    'record_count': len(raw_records),
                    'records': [operator.summarize(r, detail_by_id.get(r['id'])) for r in raw_records]}
        if tamper:
            (self.root / f'inventory-{stamp}.page-1.json').write_bytes(page1 + b' ')
        if edit:
            document['records'] = document['records'][1:]
            document['record_count'] = len(document['records'])
        path = self.root / f'inventory-{stamp}.json'
        path.write_bytes(encode(document))
        return path

    def mint(self, inventory, **overrides):
        kwargs = dict(window=600, now=lambda: NOW)
        kwargs.update(overrides)
        self.count += 1
        return operator.mint_create(self.fixture.json_file, self.fixture.paths, inventory, '123', 'review agent',
                                    'c' * 64, self.root / f'grant-{self.count}.json', self.root / f'proof-{self.count}.json', **kwargs)

    def test_minted_documents_pass_the_executor_contract(self):
        inventory = self.inventory([owned(1, 'Unrelated title', ['other.xml'])])
        result = self.mint(inventory)
        grant_path, proof_path = self.root / f'grant-{self.count}.json', self.root / f'proof-{self.count}.json'
        grant, grant_sha = executor.read_document(grant_path)
        proof, proof_sha = executor.read_document(proof_path)
        executor.authorize(self.fixture.prepared, self.fixture.paths, grant_path, proof_path, NOW + timedelta(seconds=599))
        self.assertEqual(result['grant_sha256'], grant_sha)
        self.assertEqual((grant['duplicate_proof_sha256'], proof['inventory_sha256']), (proof_sha, sha(inventory.read_bytes())))
        self.assertEqual((grant['owner'], grant['reviewed_by'], grant['draft_only'], grant['limits']),
                         ('123', 'review agent', True, executor.LIMITS))
        self.assertEqual((proof['matched_record_ids'], proof['matched_dois'], result['provider_requests']), ([], [], 0))
        with self.assertRaises(Held):
            executor.authorize(self.fixture.prepared, self.fixture.paths, grant_path, proof_path, NOW + timedelta(seconds=601))

    def test_refusals_leave_no_documents_behind(self):
        xml = self.fixture.prepared.xml
        title = json.loads(self.fixture.prepared.body)['metadata']['title']
        protected_id = next(iter(PROTECTED.values()))[0]
        cases = {
            'file': (self.inventory([owned(7, 'x', ['FGDC-141.xml'])]), {}),
            'title': (self.inventory([owned(8, '  ' + title.upper() + ' ', ['a'])]), {}),
            'md5': (self.inventory([owned(9, 'x', ['renamed.xml'], md5=hashlib.md5(xml, usedforsecurity=False).hexdigest())]), {}),
            'sha256': (self.inventory([owned(10, 'x', ['a'], note='digest ' + sha(xml))]), {}),
            'mention': (self.inventory([owned(11, 'x', ['a'], description='restored fgdc_0141 record')]), {}),
            'files_unverified': (self.inventory([owned(12, 'x')]), {}),
            'owner': (self.inventory([dict(owned(13, 'x', ['a']), owner=999)]), {}),
            'stale': (self.inventory([owned(20, 'x', ['a'])], captured=NOW - timedelta(minutes=51)), {}),
            'future': (self.inventory([owned(21, 'x', ['a'])], captured=NOW + timedelta(minutes=1)), {}),
            'window': (self.inventory([owned(22, 'x', ['a'])]), {'window': 601}),
            'empty_listing': (self.inventory([]), {}),
            'edited_summary': (self.inventory([owned(23, 'x', ['a']), owned(24, 'y', ['b'])], edit=True), {}),
            'tampered_page': (self.inventory([owned(14, 'x', ['a'])], tamper=True), {}),
            'not_terminal': (self.inventory([owned(15, 'x', ['a'])], terminal_count=1), {}),
            'skipped_names_a_listed_file': (self.inventory([owned(25, 'x', ['a'])], skipped=['25']), {}),
        }
        for label, (inventory, overrides) in cases.items():
            with self.subTest(label=label):
                before = sorted(p.name for p in self.root.iterdir())
                with self.assertRaises(Held):
                    self.mint(inventory, **overrides)
                self.assertEqual(sorted(p.name for p in self.root.iterdir()), before)
        # Known records and records whose files came from a detail fetch are acceptable.
        self.mint(self.inventory([owned(protected_id, 'x'), owned(16, 'y')]), known=('16',))
        self.mint(self.inventory([owned(17, 'x')], details={'17': {'id': 17, 'files': [{'filename': 'a.xml'}]}}))

    def test_existing_intent_or_journal_row_refuses_minting(self):
        inventory = self.inventory([owned(30, 'Unrelated', ['a'])])
        intent = executor.state_root(self.fixture.paths) / 'FGDC-141.modern-create-v1.intent.json'
        intent.write_bytes(b'{}')
        with self.assertRaises(Held):
            self.mint(inventory)
        intent.unlink()
        journal = Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json')
        journal.write_bytes(encode({'schema_version': 1, 'kind': 'modern-production-draft-attempts',
                                    'targets': {'FGDC-141': {'identity': None}}}))
        with self.assertRaises(Held):
            self.mint(inventory)
        journal.unlink()
        legacy = Path(self.fixture.paths.uploads_registry_path)
        legacy.write_bytes(encode({'FGDC-141': {'deposition_id': 5}}))
        with self.assertRaises(Held):
            self.mint(inventory)
        legacy.unlink()
        self.mint(inventory)

    def test_a_failure_after_the_first_write_removes_both_documents(self):
        inventory = self.inventory([owned(31, 'Unrelated', ['a'])])
        with patch('scripts.modern_singleton_executor.authorize', side_effect=Held('refused')), self.assertRaises(Held):
            self.mint(inventory)
        self.assertFalse(list(self.root.glob('grant-*.json')) or list(self.root.glob('proof-*.json')))
        self.mint(inventory)
        self.assertTrue(list(self.root.glob('grant-*.json')) and list(self.root.glob('proof-*.json')))

    def test_resume_minting_needs_a_started_row_with_the_same_candidate(self):
        inventory = self.inventory([owned(40, 'Unrelated', ['a']),
                                    owned(19000001, json.loads(self.fixture.prepared.body)['metadata']['title'])])
        packet = self.root / 'packet.json'
        packet.write_bytes(encode({'binding': self.fixture.prepared.binding,
                                   'evidence': self.fixture.prepared.evidence, 'provider_requests': 0}))
        journal = Path(self.fixture.paths.uploads_registry_path + '.modern-v1.json')
        with self.assertRaises(Held):  # no started row
            self.mint(inventory, preparation=str(packet), resume='19000001')
        journal.write_bytes(encode({'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': {
            'FGDC-141': {'phase': 'started', 'identity': None, 'untrusted_candidate_id': '19000001',
                         'counts': {'get': 0, 'create': 1, 'init': 0, 'content': 0, 'commit': 0}, 'requests': [{}]}}}))
        with self.assertRaises(Held):  # the candidate must match
            self.mint(inventory, preparation=str(packet), resume='19000002')
        with self.assertRaises(Held):  # without resume, the started row itself refuses a fresh create
            self.mint(inventory)
        with self.assertRaises(Held):  # the packet and the candidate go together
            self.mint(inventory, preparation=str(packet))
        with self.assertRaises(Held):
            self.mint(inventory, resume='19000001')
        result = self.mint(inventory, preparation=str(packet), resume='19000001')
        self.assertEqual((result['resume_candidate'], result['binding']), ('19000001', self.fixture.prepared.binding))
        twin = self.inventory([owned(19000001, 'x'), owned(19000002, json.loads(self.fixture.prepared.body)['metadata']['title'], ['a'])])
        with self.assertRaises(Held):  # another record with the same title is still a candidate
            self.mint(twin, preparation=str(packet), resume='19000001')

    def test_summaries_normalize_mentions_checksums_and_digest_literals(self):
        row = operator.summarize(owned(10, 'x', ['FGDC-9.xml'], note='see FGDC 141, fgdc-0141 and FGDC-1410; ' + 'b' * 64))
        self.assertEqual(row['mentions'], ['FGDC-141', 'FGDC-1410', 'FGDC-9'])
        self.assertEqual(row['sha256_literals'], ['b' * 64])
        self.assertEqual(row['files'][0]['md5'], '0' * 32)
        self.assertEqual(operator.inventory_matches([row], 'FGDC-141', 'nothing', b'<x/>'), [{'id': '10', 'reasons': ['source_id']}])
        self.assertEqual(operator.inventory_matches([operator.summarize(owned(11, 'x', ['a'], note='FGDC-1410 only'))],
                                                    'FGDC-141', 'nothing', b'<x/>'), [])


if __name__ == '__main__':
    unittest.main()
