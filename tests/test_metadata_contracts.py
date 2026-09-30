"""Offline transformation, verification and human-QA contract regression tests."""

import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.bibliographic_linkage import apply_decisions
from scripts.dto import BibliographicLink, build_canonical_dto, save_dto
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.generate_jsonld_catalogue import build_jsonld, validate_records
from scripts.path_config import OutputPaths
from scripts.publish_records import RecordPublisher
from scripts.qa_manifest import prepare_manifest, validate_approval
from scripts.upload_service import DraftUploadService, atomic_json, metadata_hash, prepare_metadata, read_json
from scripts.validate_zenodo import ZenodoValidator
from scripts.verify_uploads import ZenodoVerifier, compare_metadata


SOURCE = '<metadata><idinfo><citation><citeinfo><title>Example dataset</title><origin>Smith, Jane</origin><pubdate>2000</pubdate></citeinfo></citation><descript><abstract>Sample description.</abstract></descript><useconst>CC0</useconst></idinfo></metadata>'


class TransformTests(unittest.TestCase):
    def setUp(self):
        with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
            self.transformer = FGDCToZenodoTransformer()

    def test_dates_are_calendar_valid_and_ambiguous_values_require_review(self):
        for text, expected in [('2000', '2000-01-01'), ('200002', '2000-02-01'),
                               ('20000229', '2000-02-29'), ('1994-12-20', '1994-12-20'),
                               ('December 20, 1994', '1994-12-20')]:
            self.assertEqual(self.transformer._normalize_date(text, 'fixture'), expected)
        for text in ['122003', '1977 through 1978', 'unpublished', 'planned', '20010229', '200013', 'March']:
            self.assertIsNone(self.transformer._normalize_date(text, 'fixture'))

    def test_person_commas_org_abbreviations_and_primary_citation_preserved(self):
        for origin in ['Smith, Jane', 'Canadian Wildlife Service, Northern Forestry Research Centre',
                       'U.S. Dept. of the Interior, Bureau of Commercial Fisheries, 1968']:
            root = ET.fromstring(SOURCE.replace('Smith, Jane', origin).replace('</metadata>', '<crossref><origin>Other Author</origin></crossref></metadata>'))
            creators = self.transformer._extract_creators(root, 'fixture')
            self.assertEqual(len(creators), 1)
            self.assertEqual(creators[0]['name'], origin)

    def test_mixed_xml_names_and_tails_are_not_lost(self):
        root = ET.fromstring(SOURCE.replace('Smith, Jane', 'Jane Smith<br/>John Doe'))
        self.assertEqual(self.transformer._extract_creators(root, 'fixture'),
                         [{'name': 'Smith, Jane'}, {'name': 'Doe, John'}])

    def test_temporal_and_spatial_notes_survive_assembly(self):
        root = ET.fromstring(SOURCE.replace('</idinfo>', '<timeperd><timeinfo><rngdates><begdate>19940101</begdate><enddate>19941231</enddate></rngdates></timeinfo><current>ground condition</current></timeperd><spdom><bounding><westbc>-10</westbc><eastbc>10</eastbc><northbc>60</northbc><southbc>50</southbc></bounding></spdom></idinfo>'))
        metadata = self.transformer._build_zenodo_metadata(root, 'fixture')
        self.assertIn('1994-01-01 to 1994-12-31', metadata['notes'])
        self.assertIn('Spatial coverage:', metadata['notes'])
        self.assertIn('Use constraints: CC0', metadata['notes'])

    def test_ambiguous_primary_date_does_not_use_observation_fallback(self):
        root = ET.fromstring(SOURCE.replace('<pubdate>2000</pubdate>', '<pubdate>122003</pubdate>').replace('</metadata>', '<metd>2020</metd></metadata>'))
        self.assertIsNone(self.transformer._build_zenodo_metadata(root, 'fixture'))

    def test_curator_override_requires_matching_source_hash_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'sample.xml'
            raw = SOURCE.replace('<pubdate>2000</pubdate>', '<pubdate>122003</pubdate>')
            source.write_text(raw)
            self.transformer.decisions = {'sample': {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'reviewer': 'Fixture reviewer', 'reviewed_at': '2026-01-01T00:00:00Z',
                'rationale': 'Synthetic fixture decision; not a real source correction',
                'metadata': {'publication_date': '2003-12-01'}}}
            first = self.transformer.transform_file(str(source))
            second = self.transformer.transform_file(str(source))
            self.assertEqual(first['metadata'], second['metadata'])
            self.assertEqual(first['metadata']['publication_date'], '2003-12-01')
            self.assertIn('Curator decision:', first['metadata']['notes'])
            source.write_text(raw + ' ')
            self.assertIsNone(self.transformer.transform_file(str(source)))

    def test_ancient_date_cannot_pass_validation(self):
        issues, warnings = [], []
        ZenodoValidator()._validate_publication_date({'publication_date': '1220-03-01'}, issues, warnings)
        self.assertTrue(issues)


class LinkAndJsonldTests(unittest.TestCase):
    def test_link_decisions_are_contract_valid_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = OutputPaths(directory)
            dto = build_canonical_dto(source_path='sample.xml', zenodo_metadata={'title': 'Example'})
            path = Path(directory) / 'dto.json'
            save_dto(str(path), dto)
            decisions = [{'decision': 'accept', 'source': 'datacite', 'identifier': '10.1234/example', 'confidence': .9}]
            first = apply_decisions(path, dto, decisions, paths)
            second = apply_decisions(path, first, decisions, paths)
            self.assertEqual(first.to_json(), second.to_json())
            issues, warnings = [], []
            ZenodoValidator()._validate_related_identifiers(first.zenodo_metadata, issues, warnings)
            self.assertEqual(issues, [])

    def test_proposed_or_nonidentity_links_do_not_imply_equivalence(self):
        dto = build_canonical_dto(source_path='sample.xml', zenodo_metadata={
            'title': 'Example', 'notes': 'Free text', 'creators': [{'name': 'NOAA', 'type': 'Organization'}]},
            bibliographic_links=[BibliographicLink('datacite', '10.1234/example', 'references', .9, status='accepted'),
                                 BibliographicLink('crossref', '10.1234/proposed', 'isIdenticalTo', .99)])
        self.assertEqual(len(dto.related_identifiers), 1)
        payload = build_jsonld(dto, 'https://example.invalid/sample.jsonld')
        self.assertEqual(payload['url'], 'https://example.invalid/sample.jsonld')
        self.assertEqual(payload['creator'][0]['@type'], 'Organization')
        self.assertNotIn('sameAs', payload)

    def test_jsonld_health_rejects_prose_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.jsonld'
            path.write_text(json.dumps({'@context': 'https://schema.org', '@type': 'Dataset',
                                        'name': 'Example', '@id': 'https://example.invalid/id', 'url': 'Free text'}))
            self.assertEqual(validate_records([path])['status'], 'fail')


class HumanQATests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.paths = OutputPaths(self.directory.name, 'production')
        self.file = Path(self.paths.zenodo_json_dir) / 'sample.json'
        (Path(self.paths.original_fgdc_dir) / 'sample.xml').write_text(SOURCE)
        with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
            metadata = FGDCToZenodoTransformer()._build_zenodo_metadata(ET.fromstring(SOURCE), 'fixture')
        self.file.write_text(json.dumps({'metadata': metadata}))
        metadata, _, source_hash = prepare_metadata(str(self.file), self.paths)
        self.metadata = metadata
        self.entry = {'environment': 'production', 'zenodo_url': 'https://zenodo.org/deposit/123',
                      'deposition_id': 123, 'json_file': str(self.file), 'upload_status': 'success',
                      'metadata_sha256': metadata_hash(metadata), 'source_sha256': source_hash}
        atomic_json(self.paths.uploads_registry_path, {'sample': self.entry})
        self.manifest = prepare_manifest(self.paths)
        self.publisher = RecordPublisher.__new__(RecordPublisher)
        self.publisher.paths, self.publisher.sandbox = self.paths, False
        self.publisher.logger, self.publisher.client = Mock(), Mock()
        self.publisher.qa_manifest = self.manifest

    def approve(self):
        record = self.manifest['records'][0]
        record['qa'].update(approved=True, reviewer='Fixture reviewer', reviewed_at='2026-01-01T00:00:00Z', rationale='Offline test only')
        record['qa']['checks'] = {check: True for check in record['qa']['checks']}
        record['duplicate_review'].update(status='reviewed', classification='checked_no_match',
                                         rationale='Offline inventory fixture', evidence=[{'source': 'fixture', 'status': 'checked_no_match'}])

    def test_pending_human_qa_blocks_publication_before_client_calls(self):
        result = self.publisher._publish_single_record(self.entry)
        self.assertFalse(result['publish_successful'])
        self.publisher.client.get_deposition.assert_not_called()
        self.publisher.client.publish_deposition.assert_not_called()

    def test_approved_exact_custom_output_draft_can_publish_with_mock(self):
        self.approve()
        self.assertEqual(len(self.publisher.load_upload_log()), 1)
        draft = {'metadata': self.metadata, 'files': [], 'state': 'unsubmitted'}
        done = dict(draft, state='done')
        self.publisher.client.get_deposition.side_effect = [draft, done]
        self.publisher.client.publish_deposition.return_value = done
        result = self.publisher._publish_single_record(self.entry)
        self.assertTrue(result['publish_successful'])
        self.publisher.client.publish_deposition.assert_called_once_with(123)
        self.assertEqual(read_json(self.paths.uploads_registry_path)['sample']['publish_status'], 'published')

    def test_changed_local_source_or_remote_description_invalidates_approval(self):
        self.approve()
        changed = dict(self.metadata, description='Changed description')
        with self.assertRaisesRegex(ValueError, 'Remote draft'):
            validate_approval(self.manifest, 'sample', self.entry, self.paths, changed)
        source = Path(self.paths.original_fgdc_dir) / 'sample.xml'
        source.write_text(SOURCE + ' ')
        with self.assertRaisesRegex(ValueError, 'stale'):
            validate_approval(self.manifest, 'sample', self.entry, self.paths)

    def test_sandbox_identity_cannot_be_used_for_production(self):
        self.approve()
        entry = dict(self.entry, environment='sandbox', zenodo_url='https://sandbox.zenodo.org/deposit/123')
        result = self.publisher._publish_single_record(entry)
        self.assertFalse(result['publish_successful'])
        self.publisher.client.get_deposition.assert_not_called()

    def test_metadata_only_verification_and_meaningful_changes(self):
        verifier = ZenodoVerifier.__new__(ZenodoVerifier)
        verifier.paths, verifier.client, verifier.logger = self.paths, Mock(base_url='https://zenodo.org'), Mock()
        verifier.client.get_deposition.return_value = {'metadata': self.metadata, 'files': []}
        result = verifier._verify_single_record(self.entry)
        self.assertTrue(result['verification_successful'])
        for field in ['description', 'notes', 'publisher', 'related_identifiers']:
            changed = dict(self.metadata, **{field: 'Changed'})
            self.assertTrue(compare_metadata(self.metadata, changed))

    def test_unrelated_unapproved_draft_does_not_block_bounded_selection(self):
        registry = read_json(self.paths.uploads_registry_path)
        registry['aaa-unapproved'] = dict(self.entry, deposition_id=124, zenodo_url='https://zenodo.org/deposit/124')
        atomic_json(self.paths.uploads_registry_path, registry)
        self.approve()
        pending = dict(self.manifest['records'][0], fgdc_id='aaa-unapproved', qa={'approved': False})
        self.manifest['records'].insert(0, pending)
        self.publisher.publish_log, self.publisher.publish_errors = [], []
        self.publisher.stats = {key: 0 for key in ('total_records', 'successful_publishes', 'failed_publishes', 'already_published', 'not_found')}
        self.publisher.publish_log_path = self.paths.publish_log_path
        self.publisher.publish_errors_path = self.paths.publish_errors_path
        self.publisher._save_publish_results = Mock()
        done = {'metadata': self.metadata, 'files': [], 'state': 'done'}
        self.publisher.client.get_deposition.side_effect = [dict(done, state='unsubmitted'), done]
        self.publisher.client.publish_deposition.return_value = done
        summary = self.publisher.publish_records(self.publisher.load_upload_log(), limit=1)
        self.assertEqual(summary['successful_publishes'], 1)
        self.publisher.client.publish_deposition.assert_called_once_with(123)
        self.assertEqual([call.args[0] for call in self.publisher.client.get_deposition.call_args_list], [123, 123])
        self.assertNotIn('publish_status', read_json(self.paths.uploads_registry_path)['aaa-unapproved'])
        self.manifest['records'][1]['metadata_sha256'] = 'stale'
        self.publisher.client.reset_mock()
        self.assertFalse(self.publisher._publish_single_record(self.entry)['publish_successful'])
        self.publisher.client.publish_deposition.assert_not_called()

    def test_already_published_reconciles_ledger_without_new_post(self):
        self.approve()
        self.publisher.client.get_deposition.return_value = {'metadata': self.metadata, 'files': [], 'state': 'done'}
        for _ in range(2):
            self.assertTrue(self.publisher._publish_single_record(self.entry)['already_published'])
        self.publisher.client.publish_deposition.assert_not_called()
        self.assertEqual(read_json(self.paths.uploads_registry_path)['sample']['publish_status'], 'published')

    def test_remote_author_reversal_invalidates_human_approval(self):
        payload = json.loads(self.file.read_text())
        payload['metadata']['creators'] = [{'name': 'First, Alice'}, {'name': 'Second, Bob'}]
        self.file.write_text(json.dumps(payload))
        self.metadata, _, source_hash = prepare_metadata(str(self.file), self.paths)
        self.entry.update(metadata_sha256=metadata_hash(self.metadata), source_sha256=source_hash)
        atomic_json(self.paths.uploads_registry_path, {'sample': self.entry})
        self.manifest = prepare_manifest(self.paths)
        self.publisher.qa_manifest = self.manifest
        self.approve()
        changed = dict(self.metadata, creators=list(reversed(self.metadata['creators'])))
        with self.assertRaisesRegex(ValueError, 'Remote draft'):
            validate_approval(self.manifest, 'sample', self.entry, self.paths, changed)
        self.publisher.client.get_deposition.return_value = {'metadata': changed, 'files': [], 'state': 'unsubmitted'}
        self.assertFalse(self.publisher._publish_single_record(self.entry)['publish_successful'])
        self.publisher.client.publish_deposition.assert_not_called()

    def test_only_explicit_unordered_fields_ignore_order(self):
        for field in ('creators', 'contributors', 'unknown_list'):
            self.assertTrue(compare_metadata({field: ['a', 'b']}, {field: ['b', 'a']}))
        self.assertFalse(compare_metadata({'keywords': ['a', 'b']}, {'keywords': ['b', 'a']}))

    def test_same_work_requires_explicit_reference_decision(self):
        self.approve()
        duplicate = self.manifest['records'][0]['duplicate_review']
        duplicate['classification'] = 'same_work'
        with self.assertRaisesRegex(ValueError, 'referential'):
            validate_approval(self.manifest, 'sample', self.entry, self.paths)
