"""Synthetic PR42 history compatibility, with no production migration or authority.

Only test-fixture generation rebinds the dummy historical graph. Beforeimages are
captured after generation; recovery must preserve every byte thereafter. The old
403 receipt uses PR42's minimal shape without a response-evidence pointer. Any
unused diagnostic sidecar from the current fixture stays explicitly synthetic.
"""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_singleton_executor as draft
from scripts import modern_unknown_create as recovery
from scripts.modern_singleton import Prepared, encode, parse, sha
from tests import modern_singleton_fixtures as fixtures
from tests.test_modern_unknown_create import (
    FLAGS,
    RID,
    HistoricalFixture,
    ObservationTransport,
)


def rebind_synthetic_pr42(history, *, evidence_change=None):
    """Generate a coherent old dummy graph, never rewrite real historical state."""
    packet_path = history.documents['preparation']
    packet = parse(packet_path.read_bytes())
    evidence = copy.deepcopy(packet['evidence'])
    evidence['runtime_sha256'] = publication.PR42_RUNTIME
    evidence.update(evidence_change or {})
    binding = sha(encode(evidence))
    packet.update(binding=binding, evidence=evidence)
    packet_path.write_bytes(encode(packet))

    proof_path = history.documents['original_proof']
    proof = parse(proof_path.read_bytes())
    proof['binding'] = binding
    proof_path.write_bytes(encode(proof))
    grant_path = history.documents['original_grant']
    grant = parse(grant_path.read_bytes())
    grant.update(binding=binding, duplicate_proof_sha256=sha(proof_path.read_bytes()))
    grant_path.write_bytes(encode(grant))
    grant_sha = sha(grant_path.read_bytes())

    intent_path = history.original_runner.intent_path
    intent = parse(intent_path.read_bytes())
    intent.update(binding=binding, grant_sha256=grant_sha)
    intent_path.write_bytes(encode(intent))
    journal_path = history.original_runner.journal_path
    journal = parse(journal_path.read_bytes())
    row = journal['targets']['FGDC-141']
    row.update(binding=binding, grant_sha256=grant_sha, intent_sha256=sha(intent_path.read_bytes()))
    # PR42 retained status/bytes/suppression/hash, but no diagnostic sidecar link.
    # The fixture's unused current-runtime sidecar is retained, not presented as
    # actual evidence of the production403 response body that was unavailable.
    row['requests'][0].pop('response_evidence', None)
    journal_path.write_bytes(encode(journal))

    # Consistently bind the synthetic recovery grant as well. For the adversarial
    # case failed_context must reject the nonruntime difference before this
    # coherent grant is considered, not merely encounter a stale hash downstream.
    prospective = copy.deepcopy(history.context['binding'])
    prospective.update(original_preparation_binding=binding, failed_row_sha256=sha(encode(row)))
    prospective['files'] = {
        role: sha(path.read_bytes()) if path.exists() else None
        for role, path in history.context['paths'].items()}
    history.grant['binding'] = prospective
    history.grant_path.write_bytes(encode(history.grant))
    history.originals = {path: path.read_bytes() for path in history.root.rglob('*') if path.is_file()}
    return prospective


class ModernUnknownCreateHistoricalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=['FGDC-141'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def assert_historical_graph_coherent(self, history):
        packet = parse(history.documents['preparation'].read_bytes())
        evidence = packet['evidence']
        wire = history.documents['submitted_wire'].read_bytes()
        grant_raw = history.documents['original_grant'].read_bytes()
        proof_raw = history.documents['original_proof'].read_bytes()
        grant, proof = parse(grant_raw), parse(proof_raw)
        journal = parse(history.original_runner.journal_path.read_bytes())
        row = journal['targets']['FGDC-141']
        intent_raw = history.original_runner.intent_path.read_bytes()
        intent = parse(intent_raw)
        self.assertEqual(evidence['runtime_sha256'], publication.PR42_RUNTIME)
        self.assertEqual(packet['binding'], sha(encode(evidence)))
        self.assertEqual(grant['binding'], packet['binding'])
        self.assertEqual(proof['binding'], packet['binding'])
        self.assertEqual(grant['duplicate_proof_sha256'], sha(proof_raw))
        self.assertEqual(row['binding'], packet['binding'])
        self.assertEqual(row['grant_sha256'], sha(grant_raw))
        self.assertEqual(row['intent_sha256'], sha(intent_raw))
        self.assertEqual(intent, {'schema_version': 1, 'binding': packet['binding'],
                                  'grant_sha256': sha(grant_raw),
                                  'state_root': str(draft.state_root(history.fixture.paths))})
        self.assertEqual(row['counts'], {'get': 0, 'create': 1, 'init': 0, 'content': 0, 'commit': 0})
        self.assertEqual(row['phase'], 'started')
        self.assertIsNone(row['identity'])
        self.assertEqual(len(row['requests']), 1)
        request = row['requests'][0]
        self.assertEqual(set(request), {'kind', 'method', 'path', 'body_sha256', 'attempted_at',
                                        'status', 'http_status', 'bytes', 'credential_suppressed',
                                        'response_sha256'})
        self.assertEqual((request['kind'], request['method'], request['path'], request['http_status']),
                         ('create', 'POST', '/api/records', 403))
        self.assertEqual(request['status'], 'uncertain')
        self.assertFalse(request['credential_suppressed'])
        self.assertEqual(request['body_sha256'], sha(wire))
        self.assertEqual(evidence['wire_sha256'], sha(wire))
        self.assertEqual(wire, history.fixture.prepared.body)
        self.assertEqual(wire, history.original_transport.calls[0][2])
        original = Prepared('FGDC-141', wire, history.fixture.prepared.xml, evidence, packet['binding'])
        authorized, authorized_sha = draft.authorize(
            original, history.fixture.paths, history.documents['original_grant'],
            history.documents['original_proof'], draft.instant(request['attempted_at']))
        self.assertEqual((authorized, authorized_sha), (grant, sha(grant_raw)))
        prospective = history.grant['binding']
        self.assertEqual(prospective['original_preparation_binding'], packet['binding'])
        self.assertEqual(prospective['failed_row_sha256'], sha(encode(row)))
        self.assertEqual(prospective['files'], {
            role: sha(path.read_bytes()) if path.exists() else None
            for role, path in history.context['paths'].items()})
        return packet, request

    def test_consistent_pr42_failed403_observation_preserves_all_historical_bytes(self):
        history = HistoricalFixture(Path(self.temp.name), self.prepared_root)
        current = history.fixture.prepared
        self.assertNotEqual(current.evidence['runtime_sha256'], publication.PR42_RUNTIME)
        prospective = rebind_synthetic_pr42(history)
        packet, _ = self.assert_historical_graph_coherent(history)
        self.assertEqual(packet['evidence'], dict(current.evidence, runtime_sha256=publication.PR42_RUNTIME))
        self.assertNotEqual(packet['binding'], current.binding)
        f = history.fixture
        context = recovery.failed_context(f.json_file, f.paths, history.documents)
        self.assertEqual(context['binding'], prospective)
        self.assertEqual(context['prepared'].binding, packet['binding'])
        self.assertEqual(context['prepared'].evidence['runtime_sha256'], publication.PR42_RUNTIME)
        self.assertEqual(context['current_prepared'], current)
        self.assertEqual(context['binding']['runtime_sha256'], current.evidence['runtime_sha256'])
        self.assertEqual(context['binding']['current_preparation_binding'], current.binding)
        transport = ObservationTransport(candidates={RID: history.candidate()})
        with patch.object(draft, 'Transport', side_effect=AssertionError('Real transport forbidden in history fixture')):
            result = history.runner(transport).run()
        self.assertEqual(result['binding'], prospective)
        self.assertEqual(result['counts'], {'get': 4, 'pages': 2})
        self.assertEqual(result['exact_body_candidates'], [RID])
        self.assertEqual(result['phase'], 'captured')
        self.assertTrue(result['observation_complete'])
        self.assertEqual(result['unresolved_ids'], [])
        self.assertEqual(result['unobserved_ids'], [])
        for key, expected in FLAGS.items():
            self.assertEqual(result[key], expected)
        self.assertEqual(len(history.original_transport.calls), 1)
        self.assertEqual(len(transport.calls), 4)
        self.assertTrue(all(call[0] == 'GET' and call[2] is None for call in transport.calls))
        history.assert_originals(self)
        self.assert_historical_graph_coherent(history)

    def test_consistently_rebound_pr42_nonruntime_evidence_mismatch_holds_before_get(self):
        history = HistoricalFixture(Path(self.temp.name), self.prepared_root)
        current = history.fixture.prepared
        prospective = rebind_synthetic_pr42(history, evidence_change={'creator_profile_sha256': '0' * 64})
        packet, _ = self.assert_historical_graph_coherent(history)
        self.assertEqual(packet['evidence']['creator_profile_sha256'], '0' * 64)
        self.assertNotEqual(packet['evidence']['creator_profile_sha256'], current.evidence['creator_profile_sha256'])
        expected_old = dict(current.evidence, runtime_sha256=publication.PR42_RUNTIME)
        self.assertEqual({key for key in expected_old if expected_old[key] != packet['evidence'][key]},
                         {'creator_profile_sha256'})
        self.assertEqual(prospective['current_preparation_binding'], current.binding)
        self.assertEqual(prospective['runtime_sha256'], current.evidence['runtime_sha256'])
        transport = ObservationTransport(candidates={RID: history.candidate()})
        f = history.fixture
        with patch.object(draft, 'Transport', side_effect=AssertionError('Real transport forbidden in history fixture')):
            with self.assertRaises(ValueError):
                recovery.failed_context(f.json_file, f.paths, history.documents)
            with self.assertRaises(ValueError):
                history.runner(transport)
        self.assertEqual(transport.calls, [])
        self.assertEqual(len(history.original_transport.calls), 1)
        root = draft.state_root(f.paths)
        self.assertFalse((root / 'FGDC-141.modern-unknown-create-v1.json').exists())
        self.assertFalse((root / 'FGDC-141.modern-unknown-create-v1.intent.json').exists())
        history.assert_originals(self)
        self.assert_historical_graph_coherent(history)


if __name__ == '__main__':
    unittest.main()
