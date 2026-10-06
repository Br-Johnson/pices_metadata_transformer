"""Adversarial tests for finite, GET-only unknown-create observations.

Synthetic failed-create evidence is generated using the existing fixture.
No fixture supplies actual packet authority or proves modern inventory coverage.
"""

import base64
import copy
import re
import stat
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import modern_singleton_executor as draft
from scripts import modern_unknown_create as recovery
from scripts.modern_response_evidence import MAX_DIAGNOSTIC_BYTES, Response
from scripts.modern_singleton import encode, parse, sha
from tests import modern_singleton_fixtures as fixtures

NOW = fixtures.NOW + timedelta(hours=1)
TOKEN = 'dummy-unknown-create-observation-only'
RID = '19000001'
PARENT = '19000000'
FLAGS = {'original_create_spent': True, 'replay_authorized': False,
         'identity_adoption_authorized': False, 'modern_inventory_coverage_proven': False,
         'provider_mutation_authorized': False, 'modern_create_outcome': 'unresolved'}


def listed(rid=RID, **overrides):
    # Deliberately sparse, synthetic legacy data. Missing files/metadata do not
    # establish an exclusion; only integer ID and expected owner are required.
    return {'id': int(rid), 'owner': 123, 'files': [], **overrides}


class Original403:
    def __init__(self):
        self.calls = []

    def request(self, method, path, body, *, timeout):
        self.calls.append((method, path, body, timeout))
        assert method == 'POST' and path == '/api/records'
        return Response(403, 'text/html', b'<p>Synthetic original403; outcome unknown.</p>')


class ObservationTransport:
    def __init__(self, pages=None, candidates=None):
        self.pages = pages if pages is not None else {1: [listed()], 2: []}
        self.candidates = candidates or {}
        self.calls = []
        self.before_dispatch = lambda index, method, path: None
        self.transform = lambda index, method, path, response: response

    def request(self, method, path, body, *, timeout, accept):
        # Independent closed-route oracle, intentionally not recovery.page_path.
        assert method == 'GET' and body is None and 0 < timeout <= 20
        index = len(self.calls)
        self.before_dispatch(index, method, path)
        self.calls.append((method, path, body, timeout, accept))
        page = re.fullmatch(r'/api/deposit/depositions\?page=([1-9][0-9]*)&size=100&sort=mostrecent&all_versions=true', path)
        candidate = re.fullmatch(r'/api/records/([1-9][0-9]*)/draft', path)
        if page:
            assert accept == 'application/json'
            value = self.pages[int(page[1])]
            response = value if isinstance(value, Response) else Response(200, accept, encode(value))
        else:
            assert candidate is not None and accept == draft.MIME
            value = self.candidates.get(candidate[1], Response(404, 'application/json', b'{"message":"not found fixture"}'))
            response = value if isinstance(value, Response) else Response(200, accept, encode(value))
        return self.transform(index, method, path, response)


class HistoricalFixture:
    def __init__(self, directory, prepared_root):
        self.root = Path(directory)
        self.fixture = fixtures.Fixture(self.root, prepared_root)
        f = self.fixture
        self.original_transport = Original403()
        self.original_runner = draft.Runner(f.json_file, f.paths, f.grant_path, f.proof_path,
                                           fixtures.TOKEN, transport=self.original_transport, now=lambda: fixtures.NOW)
        try:
            self.original_runner.run()
        except ValueError:
            pass
        else:
            raise AssertionError('Synthetic original403 must be held')
        assert len(self.original_transport.calls) == 1
        self.documents = {'original_grant': f.grant_path, 'original_proof': f.proof_path}
        for role, value in {
            'preparation': {'binding': f.prepared.binding, 'evidence': f.prepared.evidence, 'provider_requests': 0},
            'parent_packet': {'synthetic': True, 'role': 'parent-reviewed failed-attempt fixture'},
            'owner_proof': {'synthetic': True, 'role': 'separately reviewed owner fixture'},
            'network_recovery_proof': {'synthetic': True, 'role': 'separately reviewed network fixture'},
        }.items():
            path = self.root / (role + '.json')
            path.write_bytes(encode(value))
            self.documents[role] = path
        wire = self.root / 'submitted-wire.json'
        wire.write_bytes(self.original_transport.calls[0][2])
        self.documents['submitted_wire'] = wire
        self.context = recovery.failed_context(f.json_file, f.paths, self.documents)
        self.grant_path = self.root / 'recovery-grant.json'
        self.grant = {
            'schema_version': 1, 'kind': 'modern-unknown-create-read-grant-v1', 'approved': True,
            'executor': draft.EXECUTOR, 'origin': 'https://zenodo.org', 'binding': self.context['binding'],
            'limits': {'get': 240, 'pages': 200}, 'started_at': NOW.isoformat(),
            'expires_at': (NOW + timedelta(seconds=600)).isoformat(), 'reviewed_by': 'Synthetic independent reviewer',
            'clock_skew_seconds': 0, 'candidate_scope': 'all_returned_owned_ids_including_protected_read_only',
            'read_only': True, 'no_create_replay': True, 'token_scope': 'deposit:write'}
        self.grant_path.write_bytes(encode(self.grant))
        self.originals = {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}

    def candidate(self, rid=RID, parent=PARENT):
        value = copy.deepcopy(self.fixture.transport.record())
        value['id'], value['parent']['id'] = rid, parent
        base = 'https://zenodo.org/api/records/' + rid + '/draft'
        value['links'] = {'self': base, 'files': base + '/files'}
        return value

    def runner(self, transport=None, now=None):
        f = self.fixture
        return recovery.Runner(f.json_file, f.paths, self.documents, self.grant_path, TOKEN,
                               transport=transport or ObservationTransport(), now=now or (lambda: NOW))

    def assert_originals(self, test, changed=()):
        changed = set(changed)
        for path, raw in self.originals.items():
            if path not in changed:
                test.assertTrue(path.is_file(), str(path))
                test.assertEqual(path.read_bytes(), raw, str(path))


class ModernUnknownCreateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_dir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.source_dir.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.source_dir.name), ids=['FGDC-141'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index = 0

    def fixture(self):
        self.index += 1
        return HistoricalFixture(Path(self.temp.name) / str(self.index), self.prepared_root)

    def assert_flags(self, row):
        for key, value in FLAGS.items():
            self.assertEqual(row[key], value)
        self.assertIs(type(row['received_body_bytes']), int)
        self.assertGreaterEqual(row['received_body_bytes'], 0)
        self.assertNotIn('raw_bytes', row)
        for key in ('unobserved_ids', 'unresolved_ids', 'exact_body_candidates'):
            self.assertIsInstance(row[key], list)
        self.assertIs(type(row['multiple_exact_candidates']), bool)
        self.assertIs(type(row['observation_complete']), bool)

    def assert_summary(self, row, *, unobserved, unresolved, exact, complete, multiple=False, phase='held'):
        self.assertEqual(row['unobserved_ids'], unobserved)
        self.assertEqual(row['unresolved_ids'], unresolved)
        self.assertEqual(row['exact_body_candidates'], exact)
        self.assertIs(row['observation_complete'], complete)
        self.assertIs(row['multiple_exact_candidates'], multiple)
        self.assertEqual(row['phase'], phase)
        self.assert_flags(row)

    def held(self, fixture, transport, *, runner=None, changed=()):
        runner = runner or fixture.runner(transport)
        with self.assertRaises(ValueError):
            runner.run()
        row = parse(runner.journal_path.read_bytes())
        self.assertEqual(row['phase'], 'held')
        self.assertEqual(row['counts']['get'], len(row['requests']))
        self.assert_flags(row)
        fixture.assert_originals(self, changed)
        return runner, row

    def test_short_page_empty_terminal_all_ids_then_repeat_is_observation_only(self):
        f = self.fixture()
        transport = ObservationTransport(candidates={RID: f.candidate()})
        runner = f.runner(transport)
        self.assertEqual(transport.calls, [])
        result = runner.run()
        self.assertEqual([call[1] for call in transport.calls], [
            '/api/deposit/depositions?page=1&size=100&sort=mostrecent&all_versions=true',
            '/api/deposit/depositions?page=2&size=100&sort=mostrecent&all_versions=true',
            '/api/records/19000001/draft',
            '/api/deposit/depositions?page=1&size=100&sort=mostrecent&all_versions=true'])
        self.assertEqual(result['counts'], {'get': 4, 'pages': 2})
        self.assertEqual(result['exact_body_candidates'], [RID])
        self.assert_summary(result, unobserved=[], unresolved=[], exact=[RID], complete=True, phase='captured')
        self.assertTrue(result['legacy_terminal_observed'])
        self.assertTrue(result['first_page_repeat_consistent'])
        self.assert_flags(result)
        f.assert_originals(self)
        with self.assertRaises(ValueError):
            f.runner(transport).run()
        self.assertEqual(len(transport.calls), 4)

    def test_empty_inventory_still_needs_bound_owner_proof_and_repeat(self):
        f = self.fixture()
        transport = ObservationTransport(pages={1: []})
        result = f.runner(transport).run()
        self.assertEqual(result['counts'], {'get': 2, 'pages': 1})
        self.assert_summary(result, unobserved=[], unresolved=[], exact=[], complete=True, phase='captured')
        self.assert_flags(result)
        f.assert_originals(self)
        missing = self.fixture()
        missing.documents['owner_proof'].unlink()
        other = ObservationTransport(pages={1: []})
        with self.assertRaises((ValueError, OSError)):
            missing.runner(other)
        self.assertEqual(other.calls, [])

    def test_missing_original_documents_or_spent_state_hold_before_transport(self):
        for role in ('preparation', 'submitted_wire', 'original_grant', 'original_proof',
                     'parent_packet', 'owner_proof', 'network_recovery_proof', 'failed_journal', 'create_intent'):
            with self.subTest(role=role):
                f = self.fixture()
                path = f.context['paths'][role]
                path.unlink()
                transport = ObservationTransport()
                with self.assertRaises((ValueError, OSError)):
                    f.runner(transport)
                self.assertEqual(transport.calls, [])
                self.assertFalse(path.exists())

    def test_packet_digest_without_actual_submitted_wire_cannot_be_rebuilt(self):
        f = self.fixture()
        f.documents['submitted_wire'].write_bytes(encode({'wire_sha256': sha(f.fixture.prepared.body)}))
        transport = ObservationTransport()
        with self.assertRaises(ValueError):
            f.runner(transport)
        self.assertEqual(transport.calls, [])
        self.assertEqual(f.documents['submitted_wire'].read_bytes(), encode({'wire_sha256': sha(f.fixture.prepared.body)}))

    def test_mutated_original_row_and_identity_cannot_be_rebound_as_unknown403(self):
        mutations = (
            lambda row: row.update(identity={'id': RID, 'parent_id': PARENT, 'owner': '123'}),
            lambda row: row.update(untrusted_candidate_id=RID),
            lambda row: row.update(phase='verified'),
            lambda row: row['counts'].update(init=1),
            lambda row: row['counts'].update(create=True),
            lambda row: row['requests'][0].update(path='/api/deposit/depositions'),
            lambda row: row['requests'][0].update(body_sha256='0' * 64),
            lambda row: row['requests'][0].update(http_status=201),
        )
        for mutate in mutations:
            f = self.fixture()
            path = f.original_runner.journal_path
            value = parse(path.read_bytes())
            mutate(value['targets']['FGDC-141'])
            path.write_bytes(encode(value))
            # Test the historical context itself; a stale recovery-grant hash
            # must not be the reason an incompatible original row is rejected.
            with self.assertRaises(ValueError):
                recovery.failed_context(f.fixture.json_file, f.fixture.paths, f.documents)

    def test_context_pins_raw_prepared_input_and_complete_current_preparation(self):
        f = self.fixture()
        raw = f.fixture.json_file.read_bytes()
        self.assertEqual(f.context['paths']['prepared_input'], f.fixture.json_file)
        self.assertEqual(f.context['before']['prepared_input'], raw)
        self.assertEqual(f.context['binding']['files']['prepared_input'], sha(raw))
        self.assertEqual(f.context['current_prepared'], f.fixture.prepared)
        self.assertEqual(f.context['binding']['current_preparation_binding'], f.fixture.prepared.binding)
        f.assert_originals(self)

    def test_original_grant_expired_now_is_valid_only_at_original_attempt(self):
        f = self.fixture()
        self.assertLess(draft.instant(f.context['original_grant']['expires_at']), NOW)
        self.assertEqual(f.context['attempted_at'], fixtures.NOW)
        result = f.runner(ObservationTransport(pages={1: []})).run()
        self.assertEqual(result['counts']['get'], 2)
        self.assert_flags(result)
        f.assert_originals(self)

    def test_wrong_recovery_authority_and_unbounded_grants_hold_without_calls(self):
        variants = (
            {'origin': 'https://sandbox.zenodo.org'}, {'executor': 'other'}, {'read_only': False},
            {'no_create_replay': False}, {'candidate_scope': 'all'}, {'token_scope': 'deposit:actions'},
            {'limits': {'get': 241, 'pages': 200}}, {'limits': {'get': 240, 'pages': 201}},
            {'clock_skew_seconds': 61}, {'clock_skew_seconds': True}, {'approved': False},
            {'expires_at': (NOW + timedelta(seconds=601)).isoformat()},
        )
        for change in variants:
            with self.subTest(change=change):
                f = self.fixture()
                f.grant_path.write_bytes(encode(f.grant | change))
                transport = ObservationTransport()
                with self.assertRaises(ValueError):
                    f.runner(transport)
                self.assertEqual(transport.calls, [])

    def test_listing_owner_id_and_schema_faults_never_become_empty_inventory(self):
        cases = ([listed(owner=124)], [listed(owner='123')], [listed(owner=True)],
                 [listed(id=True)], [listed(id=0)], [listed(id=-1)], [listed(id=RID)],
                 [listed(), listed()], [None], {'hits': {'hits': []}}, [listed(str(19000001 + n)) for n in range(101)])
        for page in cases:
            with self.subTest(kind=type(page).__name__):
                f = self.fixture()
                transport = ObservationTransport(pages={1: page})
                _, row = self.held(f, transport)
                self.assertEqual(len(transport.calls), 1)
                self.assertFalse(row['legacy_terminal_observed'])
                self.assertFalse(row['first_page_repeat_consistent'])

    def test_missing_file_counterexamples_and_old_sparse_rows_all_get_observed(self):
        f = self.fixture()
        # Synthetic replicas of the documented list/detail omission pattern;
        # these IDs do not represent the historical provider bodies.
        ids = ['19000011', '19000012', '19000013']
        rows = [listed(ids[0], metadata={'title': 'Unrelated-looking title'}, created='2000-01-01T00:00:00Z'),
                listed(ids[1], metadata={}, files=[]), listed(ids[2], record_id=19000014, conceptrecid='19000010')]
        transport = ObservationTransport(pages={1: rows, 2: []})
        result = f.runner(transport).run()
        observed_paths = [call[1] for call in transport.calls if '/api/records/' in call[1]]
        self.assertEqual(observed_paths, ['/api/records/' + rid + '/draft' for rid in ids])
        self.assertEqual(result['listed_ids'], ids)
        self.assertEqual([r['record_id'] for r in result['observations']], ids)
        self.assert_summary(result, unobserved=[], unresolved=ids, exact=[], complete=True)
        self.assert_flags(result)
        f.assert_originals(self)

    def test_cross_page_duplicates_hold_without_deduplicating(self):
        f = self.fixture()
        transport = ObservationTransport(pages={1: [listed()], 2: [listed()], 3: []})
        _, row = self.held(f, transport)
        self.assertEqual(len(transport.calls), 2)
        self.assertFalse(row['legacy_terminal_observed'])
        self.assertEqual(row['listed_ids'], [RID])
        self.assert_summary(row, unobserved=[RID], unresolved=[RID], exact=[], complete=False)

    def test_changed_final_first_page_even_whitespace_holds(self):
        for mode in ('whitespace', 'new_item'):
            f = self.fixture()
            transport = ObservationTransport()
            def alter(index, method, path, response, mode=mode):
                if index == 3:
                    raw = response.body + b' ' if mode == 'whitespace' else encode([listed(), listed('19000002')])
                    return Response(200, 'application/json', raw)
                return response
            transport.transform = alter
            _, row = self.held(f, transport)
            self.assertEqual(len(transport.calls), 4)
            self.assertTrue(row['legacy_terminal_observed'])
            self.assertFalse(row['first_page_repeat_consistent'])
            self.assert_summary(row, unobserved=[], unresolved=[RID], exact=[], complete=False)

    def test_every_protected_id_can_be_read_but_never_becomes_unclaimed_identity(self):
        f = self.fixture()
        protected = str(next(iter(draft.PROTECTED.values()))[0])
        transport = ObservationTransport(pages={1: [listed(protected)], 2: []},
                                         candidates={protected: f.candidate(protected, '19999999')})
        result = f.runner(transport).run()
        self.assertIn('/api/records/' + protected + '/draft', [call[1] for call in transport.calls])
        self.assertFalse(result['observations'][0]['checks']['distinct_unclaimed_identity'])
        self.assert_summary(result, unobserved=[], unresolved=[protected], exact=[], complete=True)
        self.assert_flags(result)
        f.assert_originals(self)

    def test_multiple_exact_body_candidates_do_not_adopt_first_or_newest(self):
        f = self.fixture()
        other = '19000002'
        transport = ObservationTransport(pages={1: [listed(), listed(other)], 2: []},
                                         candidates={RID: f.candidate(), other: f.candidate(other, '19000003')})
        result = f.runner(transport).run()
        self.assert_summary(result, unobserved=[], unresolved=[], exact=[RID, other], complete=True, multiple=True)
        f.assert_originals(self)
        old = parse(f.original_runner.journal_path.read_bytes())['targets']['FGDC-141']
        self.assertIsNone(old['identity'])
        self.assertNotIn('untrusted_candidate_id', old)

    def test_candidate_body_owner_identity_access_metadata_and_files_conflicts(self):
        mutations = (
            lambda d: d['parent']['access']['owned_by'].update(user='124'),
            lambda d: d.update(id='19000009'), lambda d: d['parent'].update(id=RID),
            lambda d: d['links'].update(self='https://elsewhere.invalid/record'),
            lambda d: d.update(is_published=True, status='published'),
            lambda d: d.update(pids={'doi': {'identifier': '10.5281/zenodo.19000001'}}),
            lambda d: d['access'].update(files='public'),
            lambda d: d['metadata'].update(title='Different metadata'),
            lambda d: d['files'].update(entries={'unexpected.xml': {}}, count=1),
            lambda d: d.update(revision_id=True),
            lambda d: d['parent'].update(review={'id': 'existing-review'}),
            lambda d: d.update(review={'id': 'top-level-review'}),
        )
        for mutate in mutations:
            f = self.fixture()
            candidate = f.candidate()
            mutate(candidate)
            transport = ObservationTransport(candidates={RID: candidate})
            result = f.runner(transport).run()
            self.assert_summary(result, unobserved=[], unresolved=[RID], exact=[], complete=True)
            self.assertFalse(result['observations'][0]['exact_body_candidate'])
            if candidate.get('review') or candidate['parent'].get('review'):
                self.assertFalse(result['observations'][0]['checks']['no_existing_review'])
            self.assert_flags(result)
            f.assert_originals(self)

    def test_created_before_actual_attempt_is_not_original_window_match(self):
        f = self.fixture()
        context = dict(f.context, attempted_at=fixtures.NOW + timedelta(minutes=5))
        candidate = f.candidate()
        candidate['created'] = (fixtures.NOW + timedelta(seconds=1)).isoformat()
        checks = recovery.candidate_checks(candidate, RID, context, 0)
        self.assertFalse(checks['conservative_attempt_window'])
        candidate['created'] = (context['attempted_at'] - timedelta(seconds=30)).isoformat()
        self.assertTrue(recovery.candidate_checks(candidate, RID, context, 30)['conservative_attempt_window'])
        self.assertFalse(recovery.candidate_checks(candidate, RID, context, 29)['conservative_attempt_window'])

    def test_parent_claimed_by_other_listed_record_is_not_an_exact_candidate(self):
        other = '19000002'
        other_concept = '19000003'
        for parent in (other, other_concept):
            with self.subTest(parent=parent):
                f = self.fixture()
                transport = ObservationTransport(
                    pages={1: [listed(conceptrecid=PARENT), listed(other, conceptrecid=other_concept)], 2: []},
                    candidates={RID: f.candidate(parent=parent)})
                result = f.runner(transport).run()
                self.assertFalse(result['observations'][0]['checks']['distinct_unclaimed_identity'])
                self.assert_summary(result, unobserved=[], unresolved=[RID, other], exact=[], complete=True)
                self.assert_flags(result)
                f.assert_originals(self)

    def test_candidate404_is_observed_unresolved_and_has_no_fallback_route(self):
        f = self.fixture()
        transport = ObservationTransport()
        result = f.runner(transport).run()
        self.assertEqual(result['observations'][0]['checks'], {'draft_endpoint_available': False})
        self.assertFalse(result['observations'][0]['exact_body_candidate'])
        self.assert_summary(result, unobserved=[], unresolved=[RID], exact=[], complete=True)
        self.assertEqual(len(transport.calls), 4)
        self.assert_flags(result)
        f.assert_originals(self)

    def test_candidate403_or_timeout_holds_with_no_automatic_retry(self):
        for fault in ('403', 'timeout'):
            f = self.fixture()
            transport = ObservationTransport()
            def fail(index, method, path, response, fault=fault):
                if '/api/records/' in path:
                    if fault == 'timeout':
                        raise TimeoutError('dummy transport ' + TOKEN)
                    return Response(403, 'text/html', b'Forbidden fixture')
                return response
            transport.transform = fail
            runner, row = self.held(f, transport)
            self.assertEqual(len(transport.calls), 3)
            self.assertEqual(row['listed_ids'], [RID])
            self.assertFalse(row['first_page_repeat_consistent'])
            self.assert_summary(row, unobserved=[RID], unresolved=[RID], exact=[], complete=False)
            with self.assertRaises(ValueError):
                f.runner(transport).run()
            self.assertEqual(len(transport.calls), 3)
            self.assertNotIn(TOKEN, runner.journal_path.read_text())

    def test_prior_exact_match_is_preserved_when_next_candidate_fails(self):
        other = '19000002'
        for fault in ('403', 'timeout'):
            with self.subTest(fault=fault):
                f = self.fixture()
                transport = ObservationTransport(pages={1: [listed(), listed(other)], 2: []},
                                                 candidates={RID: f.candidate()})
                def fail(index, method, path, response, fault=fault):
                    if path == '/api/records/' + other + '/draft':
                        if fault == 'timeout':
                            raise TimeoutError('Synthetic candidate interruption ' + TOKEN)
                        return Response(403, 'text/html', b'Forbidden synthetic second candidate')
                    return response
                transport.transform = fail
                runner, row = self.held(f, transport)
                self.assertEqual(len(transport.calls), 4)
                self.assertEqual(row['counts'], {'get': 4, 'pages': 2})
                self.assert_summary(row, unobserved=[other], unresolved=[other], exact=[RID], complete=False)
                self.assertEqual(len(row['observations']), 1)
                self.assertEqual(row['observations'][0]['record_id'], RID)
                self.assertTrue(row['observations'][0]['exact_body_candidate'])
                self.assertFalse(row['first_page_repeat_consistent'])
                self.assertEqual(parse(runner.journal_path.read_bytes())['exact_body_candidates'], [RID])
                with self.assertRaises(ValueError):
                    f.runner(transport).run()
                self.assertEqual(len(transport.calls), 4)

    def test_shared_modern_parent_invalidates_both_previously_matching_bodies(self):
        f = self.fixture()
        other = '19000002'
        transport = ObservationTransport(pages={1: [listed(), listed(other)], 2: []},
                                         candidates={RID: f.candidate(), other: f.candidate(other, PARENT)})
        result = f.runner(transport).run()
        self.assert_summary(result, unobserved=[], unresolved=[RID, other], exact=[], complete=True)
        self.assertEqual(len(result['observations']), 2)
        self.assertTrue(all(row['parent_id'] == PARENT for row in result['observations']))
        self.assertTrue(all(row['checks']['exact_original_metadata'] for row in result['observations']))
        self.assertTrue(all(row['checks']['distinct_unclaimed_identity'] is False for row in result['observations']))
        self.assertTrue(all(row['exact_body_candidate'] is False for row in result['observations']))
        f.assert_originals(self)

    def test_exact_match_survives_failed_final_repeat_but_observation_stays_incomplete(self):
        f = self.fixture()
        transport = ObservationTransport(candidates={RID: f.candidate()})
        transport.transform = lambda index, method, path, response: (
            Response(200, 'application/json', response.body + b' ') if index == 3 else response)
        _, row = self.held(f, transport)
        self.assertEqual(len(transport.calls), 4)
        self.assert_summary(row, unobserved=[], unresolved=[], exact=[RID], complete=False)
        self.assertFalse(row['first_page_repeat_consistent'])

    def test_page_and_total_request_ceilings_reserve_repeat_and_keep_all_ids(self):
        f = self.fixture()
        ids = [str(19100000 + i) for i in range(199)]
        pages = {i + 1: [listed(rid)] for i, rid in enumerate(ids)} | {200: []}
        transport = ObservationTransport(pages=pages)
        runner = f.runner(transport)
        # The prepared source is independently exercised by the binding/fault
        # tests. Hold its pure result fixed here to isolate440 bounded requests
        # across the two page-cap tests without repeating source classification.
        with patch.object(recovery, 'prepare', return_value=f.fixture.prepared):
            result = runner.run()
        self.assertEqual(result['counts'], {'get': 240, 'pages': 200})
        self.assertEqual(len(transport.calls), 240)
        self.assertEqual(len(result['observations']), 39)
        self.assert_summary(result, unobserved=ids[39:], unresolved=ids, exact=[], complete=False)
        self.assertTrue(result['first_page_repeat_consistent'])
        self.assertEqual(transport.calls[-1][1], '/api/deposit/depositions?page=1&size=100&sort=mostrecent&all_versions=true')
        self.assert_flags(result)
        f.assert_originals(self)
        with self.assertRaises(ValueError):
            recovery.Runner.page_path(201)

    def test_nonempty_page200_holds_without_page201_or_candidate_dispatch(self):
        f = self.fixture()
        pages = {index: [listed(str(19200000 + index))] for index in range(1, 201)}
        transport = ObservationTransport(pages=pages)
        runner = f.runner(transport)
        with patch.object(recovery, 'prepare', return_value=f.fixture.prepared):
            _, row = self.held(f, transport, runner=runner)
        self.assertEqual(row['counts'], {'get': 200, 'pages': 200})
        self.assertEqual(len(transport.calls), 200)
        self.assertEqual(len(row['listed_ids']), 200)
        self.assertFalse(row['legacy_terminal_observed'])
        self.assertFalse(row['first_page_repeat_consistent'])
        self.assertEqual(row['observations'], [])
        ids = [str(19200000 + index) for index in range(1, 201)]
        self.assert_summary(row, unobserved=ids, unresolved=ids, exact=[], complete=False)
        self.assertTrue(all('/api/deposit/depositions?' in call[1] for call in transport.calls))

    def test_full_raw_inventory_above_diagnostic_cap_is_retained_exactly(self):
        f = self.fixture()
        page = [listed(opaque_notes='x' * (MAX_DIAGNOSTIC_BYTES + 2048))]
        raw = encode(page)
        transport = ObservationTransport(pages={1: page, 2: []})
        runner = f.runner(transport)
        result = runner.run()
        receipt = result['requests'][0]
        path = runner.root / receipt['raw_evidence']['filename']
        self.assertFalse(path.is_symlink())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(sha(path.read_bytes()), receipt['raw_evidence']['sha256'])
        packet = parse(path.read_bytes())
        self.assertEqual(base64.b64decode(packet['body_base64']), raw)
        self.assertEqual(packet['response_sha256'], sha(raw))
        diagnostic_path = runner.root / receipt['response_evidence']['filename']
        diagnostic = parse(diagnostic_path.read_bytes())
        self.assertLess(diagnostic['retained_bytes'], len(raw))
        self.assert_summary(result, unobserved=[], unresolved=[RID], exact=[], complete=True)
        self.assertEqual(result['received_body_bytes'], sum(receipt['bytes'] for receipt in result['requests']))
        f.assert_originals(self)

    def test_redirect_partial_oversized_and_credential_pages_never_complete_scan(self):
        responses = (
            Response(301, 'application/json', b'[]', location='https://example.invalid/never-follow'),
            Response(200, 'application/json', b'[]', complete=False, read_error='incomplete_body'),
            Response(200, 'application/json', b'x' * draft.MAX_BYTES, complete=False, read_error='body_limit'),
            Response(200, 'application/json', encode([listed(note=TOKEN)])),
            Response(200, 'text/html', b'[]'),
        )
        for response in responses:
            f = self.fixture()
            transport = ObservationTransport(pages={1: response})
            runner, row = self.held(f, transport)
            self.assertEqual(len(transport.calls), 1)
            self.assertFalse(row['legacy_terminal_observed'])
            self.assertFalse(row['first_page_repeat_consistent'])
            for path in runner.root.glob('*unknown-create*'):
                if path.is_file():
                    self.assertNotIn(TOKEN, path.read_text())

    def test_original_input_whitespace_change_after_first_get_blocks_next_get(self):
        f = self.fixture()
        transport = ObservationTransport()
        path = f.fixture.json_file
        def change(index, method, request_path, response):
            if index == 0:
                path.write_bytes(path.read_bytes() + b'\n')
            return response
        transport.transform = change
        _, row = self.held(f, transport, changed=(path,))
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(row['counts']['get'], 1)
        self.assertEqual(path.read_bytes(), f.originals[path] + b'\n')

    def test_bound_document_or_whole_original_journal_change_stops_next_get(self):
        for role in ('parent_packet', 'owner_proof', 'network_recovery_proof', 'failed_journal'):
            f = self.fixture()
            transport = ObservationTransport()
            path = f.context['paths'][role]
            def change(index, method, request_path, response, path=path):
                if index == 0:
                    path.write_bytes(path.read_bytes() + b' ')
                return response
            transport.transform = change
            self.held(f, transport, changed=(path,))
            self.assertEqual(len(transport.calls), 1)

    def test_get_counter_is_durable_before_each_dispatch(self):
        f = self.fixture()
        transport = ObservationTransport()
        runner = f.runner(transport)
        def inspect(index, method, path):
            row = parse(runner.journal_path.read_bytes())
            self.assertEqual(row['counts']['get'], index + 1)
            self.assertEqual(len(row['requests']), index + 1)
            self.assertEqual(row['requests'][-1]['path'], path)
            self.assertEqual(row['requests'][-1]['method'], 'GET')
            self.assertTrue(runner.intent_path.is_file())
        transport.before_dispatch = inspect
        runner.run()
        f.assert_originals(self)

    def test_failed_initial_intent_or_journal_persistence_allows_zero_calls(self):
        for point in ('intent', 'journal'):
            f = self.fixture()
            transport = ObservationTransport()
            runner = f.runner(transport)
            target = patch.object(draft, 'permanent_intent', side_effect=OSError('dummy intent fsync')) if point == 'intent' else patch.object(runner, 'save', side_effect=OSError('dummy journal fsync'))
            with target, self.assertRaises(OSError):
                runner.run()
            self.assertEqual(transport.calls, [])
            f.assert_originals(self)

    def test_raw_sidecar_failure_keeps_spent_get_and_blocks_next(self):
        f = self.fixture()
        transport = ObservationTransport()
        runner = f.runner(transport)
        original = draft.permanent_intent
        def fail(path, value):
            if str(path).endswith('.raw.json'):
                raise OSError('dummy raw evidence fsync')
            return original(path, value)
        with patch.object(draft, 'permanent_intent', side_effect=fail):
            _, row = self.held(f, transport, runner=runner)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(row['counts']['get'], 1)
        self.assertNotIn('raw_evidence', row['requests'][0])
        self.assertIn('response_evidence', row['requests'][0])
        with self.assertRaises(ValueError):
            f.runner(transport).run()
        self.assertEqual(len(transport.calls), 1)

    def test_missing_recovery_journal_and_changed_grant_cannot_reset_barrier(self):
        f = self.fixture()
        transport = ObservationTransport(pages={1: Response(403, 'text/html', b'held fixture')})
        runner, _ = self.held(f, transport)
        runner.journal_path.unlink()
        f.grant['reviewed_by'] = 'Another synthetic reviewer'
        f.grant_path.write_bytes(encode(f.grant))
        reopened = f.runner(transport)
        with self.assertRaises(ValueError):
            reopened.run()
        self.assertEqual(len(transport.calls), 1)
        self.assertFalse(runner.journal_path.exists())
        self.assertTrue(runner.intent_path.is_file())
        f.assert_originals(self, changed=(f.grant_path,))

    def test_methods_routes_ids_and_response_links_cannot_expand_dispatch(self):
        f = self.fixture()
        transport = ObservationTransport(pages={1: [listed(links={'next': 'https://example.invalid/POST'})], 2: []})
        runner = f.runner(transport)
        illegal = (
            ('/api/records', {'candidate_id': RID}),
            ('/api/records/' + RID + '/draft/actions/publish', {'candidate_id': RID}),
            ('/api/records/19000009/draft', {'candidate_id': '19000009'}),
            ('/api/deposit/depositions?page=1&size=200', {'page': 1}),
        )
        def attack_while_started(index, method, path):
            if index != 2:
                return
            self.assertEqual(runner.journal['phase'], 'started')
            self.assertIn(RID, runner.journal['listed_ids'])
            counters = runner.journal['counts'].copy()
            for illegal_path, kwargs in illegal:
                with self.assertRaises(ValueError):
                    runner.get(illegal_path, **kwargs)
                self.assertEqual(runner.journal['counts'], counters)
            with self.assertRaises(TypeError):
                runner.get('/api/records/' + RID + '/draft', candidate_id=RID, method='POST')
            self.assertEqual(runner.journal['counts'], counters)
        transport.before_dispatch = attack_while_started
        result = runner.run()
        self.assertEqual(len(transport.calls), 4)
        self.assertEqual(result['counts']['get'], 4)
        self.assertTrue(all(call[0] == 'GET' and call[2] is None for call in transport.calls))
        f.assert_originals(self)

    def test_identity_adopting_runner_and_mutation_methods_are_never_invoked(self):
        f = self.fixture()
        transport = ObservationTransport(candidates={RID: f.candidate()})
        runner = f.runner(transport)
        with (patch.object(draft.Runner, 'record', side_effect=AssertionError('Identity adoption forbidden')),
              patch.object(draft.Runner, 'run', side_effect=AssertionError('Mutation runner forbidden'))):
            result = runner.run()
        self.assertEqual(result['exact_body_candidates'], [RID])
        self.assert_flags(result)
        f.assert_originals(self)

    def test_grant_expiry_during_first_response_prevents_second_get(self):
        f = self.fixture()
        clock = [NOW]
        transport = ObservationTransport()
        def expire(index, method, path, response):
            clock[0] = NOW + timedelta(seconds=600)
            return response
        transport.transform = expire
        runner = f.runner(transport, now=lambda: clock[0])
        self.held(f, transport, runner=runner)
        self.assertEqual(len(transport.calls), 1)
        self.assertLessEqual(transport.calls[0][3], 20)


if __name__ == '__main__':
    unittest.main()
