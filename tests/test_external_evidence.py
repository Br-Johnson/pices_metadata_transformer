"""External repository failures must remain distinct from checked absence."""

import unittest
from unittest.mock import Mock, patch

from scripts.bibliographic_linkage import build_candidates
from scripts.dto import build_canonical_dto
from scripts.matching.datacite_adapter import DataCiteAdapter
from scripts.matching.engine import MatchingEngine
from scripts.matching.evidence import review_candidates, snapshot_inventory, validate_json_payload


class ExternalEvidenceTests(unittest.TestCase):
    def snapshot(self, **overrides):
        return dict({'repository': 'AquaDocs fixture', 'endpoint': 'https://example.invalid/oai/request',
                     'retrieved_at': '2026-01-01T00:00:00Z', 'scope': 'Synthetic test inventory',
                     'query': 'Fixture', 'http_status': 200, 'scope_complete': True,
                     'format': 'records', 'body': {'records': []}}, **overrides)

    def test_malformed_nested_payloads_preserve_unavailable_provenance(self):
        for format_name, body in (('crossref', {'message': None}), ('datacite', {'data': [], 'links': None}), ('dspace', {'_embedded': []}), ('crossref', {'message': {'items': [{'DOI': '10.1234/test', 'title': [{'unexpected': 'nested'}]}]}})):
            result = snapshot_inventory(self.snapshot(format=format_name, body=body))
            with self.subTest(format=format_name, body=body):
                self.assertFalse(result['inventory_complete'])
                self.assertIn(result['status'], ('unchecked_unavailable', 'unchecked_partial'))
                self.assertTrue(result['response_sha256'])

    def test_optional_external_fields_require_matching_safe_types(self):
        for field in ('identifiers', 'abstract'):
            record = {'title': 'Example dataset', 'identifier': '10.x/y', field: ['wrong'] if field == 'abstract' else '10.x/y'}
            result = snapshot_inventory(self.snapshot(body={'records': [record]}))
            self.assertEqual(result['status'], 'unchecked_unavailable')
            self.assertFalse(result['inventory_complete'])

    def test_api_inventory_missing_pagination_proof_cannot_mean_complete(self):
        for format_name, body in (('crossref', {'message': {'items': []}}), ('datacite', {'data': []})):
            result = snapshot_inventory(self.snapshot(format=format_name, body=body))
            self.assertFalse(result['inventory_complete'])

    def test_http200_angular_shell_is_unavailable_not_no_match(self):
        inventory = snapshot_inventory(self.snapshot(format='oai', content_type='text/html',
                                                      body='<html><app-root></app-root></html>'))
        self.assertEqual(inventory['status'], 'unchecked_unavailable')
        self.assertFalse(inventory['inventory_complete'])
        self.assertIn('OAI-PMH', inventory['error'])

    def test_http503_preserves_endpoint_time_status_and_failure(self):
        snapshot = self.snapshot(http_status=503, body='Service unavailable')
        inventory = snapshot_inventory(snapshot)
        self.assertEqual(inventory['endpoint'], snapshot['endpoint'])
        self.assertEqual(inventory['retrieved_at'], snapshot['retrieved_at'])
        self.assertEqual(inventory['http_status'], 503)
        self.assertTrue(inventory['response_sha256'])
        self.assertEqual(inventory['status'], 'unchecked_unavailable')

    def test_oai_identify_does_not_establish_empty_inventory(self):
        inventory = snapshot_inventory(self.snapshot(format='oai', body='<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><Identify><repositoryName>Fixture</repositoryName></Identify></OAI-PMH>'))
        self.assertEqual(inventory['status'], 'unchecked_identify_only')
        self.assertFalse(inventory['inventory_complete'])

    def test_partial_empty_inventory_cannot_establish_no_match(self):
        dto = build_canonical_dto(source_path='sample.xml', zenodo_metadata={'title': 'Example'})
        partial = snapshot_inventory(self.snapshot(scope_complete=False))
        self.assertEqual(review_candidates(dto, partial)['status'], 'unchecked_partial')
        complete = snapshot_inventory(self.snapshot())
        self.assertEqual(review_candidates(dto, complete)['status'], 'checked_no_match')

    def test_identifier_match_is_deferred_without_claiming_same_work(self):
        dto = build_canonical_dto(source_path='sample.xml', zenodo_metadata={'title': 'Different title', 'doi': 'https://doi.org/10.1234/example'})
        inventory = snapshot_inventory(self.snapshot(body={'records': [{'title': 'Another title', 'identifier': '10.1234/EXAMPLE'}]}))
        review = review_candidates(dto, inventory)
        self.assertEqual(review['status'], 'candidate_matches')
        self.assertTrue(review['candidates'][0]['identifier_match'])
        self.assertEqual(review['candidates'][0]['decision'], 'defer')
        self.assertIsNone(review['candidates'][0]['classification'])

    def test_malformed_json_and_wrong_response_shape_fail_closed(self):
        for body in ['<html>application shell</html>', {'unexpected': []}, {'records': [{'title': 'No identifier'}]}]:
            inventory = snapshot_inventory(self.snapshot(body=body))
            self.assertEqual(inventory['status'], 'unchecked_unavailable')
            self.assertFalse(inventory['inventory_complete'])
        with self.assertRaises(ValueError):
            validate_json_payload({'_embedded': {}}, 'dspace')

    def test_adapter_failure_is_recorded_not_reported_as_no_duplicates(self):
        adapter = Mock(BASE_URL='https://example.invalid/search')
        adapter.search.side_effect = ValueError('HTML shell')
        evidence = []
        dto = build_canonical_dto(source_path='sample.xml', zenodo_metadata={'title': 'Example'})
        with patch('scripts.bibliographic_linkage.get_logger', return_value=Mock()):
            self.assertEqual(build_candidates(dto, MatchingEngine(), {'fixture': adapter}, evidence), [])
        self.assertEqual(evidence[0]['status'], 'unchecked_unavailable')
        self.assertEqual(evidence[0]['error'], 'HTML shell')

    def test_datacite_uses_doi_collection_and_rejects_wrong_shape(self):
        session = Mock()
        session.get.return_value = Mock(status_code=200, headers={'Content-Type': 'application/json'})
        session.get.return_value.json.return_value = {'unexpected': []}
        with patch('scripts.matching.datacite_adapter.get_logger', return_value=Mock()):
            adapter = DataCiteAdapter(session=session)
        with self.assertRaises(ValueError):
            adapter.search('Example', [])
        self.assertEqual(session.get.call_args.args[0], 'https://api.datacite.org/dois')
