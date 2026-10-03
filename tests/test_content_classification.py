"""Offline content roles, export idempotence and transformation boundaries."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from scripts.content_classification import classify_content, export_content_metadata, STATUS_TAGS
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.dto import build_canonical_dto
from scripts.validate_zenodo import ZenodoValidator
from scripts.fgdc_utils import build_metadata_notes, LEGACY_METADATA_ONLY_NOTE
from tests.test_metadata_contracts import SOURCE


class ContentClassificationTests(unittest.TestCase):
    def declaration(self, files, **kwargs):
        return dict(inventory_complete=True, reviewer='Fixture reviewer', reviewed_at='2026-10-01',
                    rationale='Reviewed synthetic file roles', files=files, **kwargs)

    def role(self, name, role):
        return {'name': name, 'role': role, 'evidence': 'Inspected fixture content and object scope'}

    def test_descriptive_xml_is_metadata_only_by_role(self):
        result = classify_content(self.declaration([self.role('source.xml', 'descriptive_metadata')]))
        self.assertEqual(result['content_status'], 'metadata_only')
        self.assertEqual(classify_content({'files': [{'name': 'source.xml'}]})['content_status'], 'unknown')

    def test_data_and_metadata_are_data_included_with_complete_coverage(self):
        files = [self.role('source.xml', 'descriptive_metadata'), self.role('values.csv', 'research_data')]
        self.assertEqual(classify_content(self.declaration(files, data_coverage='complete'))['content_status'], 'data_included')
        self.assertEqual(classify_content(self.declaration(files, data_coverage='partial'))['content_status'], 'mixed')
        self.assertEqual(classify_content(self.declaration(files))['content_status'], 'unknown')

    def test_external_data_links_do_not_establish_deposited_data(self):
        declaration = self.declaration([self.role('source.xml', 'descriptive_metadata')], external_availability={'status': 'available', 'url': 'https://example.invalid/data'})
        self.assertEqual(classify_content(declaration)['content_status'], 'metadata_only')
        self.assertEqual(classify_content({'external_availability': declaration['external_availability']})['content_status'], 'unknown')

    def test_ambiguous_or_unreviewed_files_are_unknown(self):
        for declaration in ({}, self.declaration([self.role('data.xml', 'unknown')]), self.declaration([{'name': 'data.csv', 'role': 'research_data'}], data_coverage='complete')):
            self.assertEqual(classify_content(declaration)['content_status'], 'unknown')
        with self.assertRaises(ValueError):
            classify_content({'content_status': 'metadata_only'})

    def test_review_provenance_and_file_evidence_are_explicit_text(self):
        declaration = self.declaration([self.role('source.xml', 'descriptive_metadata')])
        declaration['reviewer'] = True
        self.assertEqual(classify_content(declaration)['content_status'], 'unknown')
        declaration = self.declaration([{'name': 'source.xml', 'role': 'descriptive_metadata', 'evidence': True}])
        self.assertEqual(classify_content(declaration)['content_status'], 'unknown')
        duplicate = self.declaration([self.role('source.xml', 'descriptive_metadata'), self.role('source.xml', 'research_data')], data_coverage='complete')
        with self.assertRaises(ValueError):
            classify_content(duplicate)

    def test_keywords_and_notes_replace_stale_status_idempotently(self):
        original = {'title': 'Fixture', 'keywords': ['Oceanography', 'pices-content-mixed', 'pices-data-included'], 'description': 'Original description', 'license': 'cc-by-4.0', 'doi': '10.1234/test', 'upload_type': 'dataset'}
        classification = classify_content(self.declaration([self.role('source.xml', 'descriptive_metadata')]))
        first = export_content_metadata(original, classification)
        self.assertEqual(export_content_metadata(first, classification), first)
        self.assertEqual(first['keywords'], ['Oceanography', 'pices-metadata-only'])
        self.assertEqual(original['description'], 'Original description')
        for key in ('license', 'doi', 'upload_type'):
            self.assertEqual(first[key], original[key])
        unknown = export_content_metadata(first, classify_content())
        self.assertNotIn('pices-metadata-only', unknown['keywords'])
        self.assertNotIn('descriptive metadata only;', unknown['description'])
        self.assertEqual(len(set(unknown['keywords']) & set(STATUS_TAGS.values())), 1)

    def test_migration_notes_do_not_guess_deposited_data_status(self):
        notes = build_metadata_notes(LEGACY_METADATA_ONLY_NOTE + '\n\nScientific notes', '<metadata/>')
        self.assertNotIn('dataset is metadata-only', notes)
        self.assertIn('Scientific notes', notes)
        self.assertEqual(build_metadata_notes(notes, '<metadata/>'), notes)
        with self.assertRaises(ValueError):
            classify_content([])

    def test_transformation_retains_evidence_internally_not_api_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'sample.xml'
            source.write_text(SOURCE)
            declaration = self.declaration([self.role('sample.xml', 'descriptive_metadata')])
            declaration['files'][0]['evidence'] = 'INTERNAL_ROLE_EVIDENCE_MARKER'
            decision = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'reviewer': 'Fixture reviewer', 'reviewed_at': '2026-10-01', 'rationale': 'Source reviewed', 'content_classification': declaration}
            with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
                result = FGDCToZenodoTransformer({'sample': decision}).transform_file(str(source))
            self.assertIsNotNone(result)
            self.assertEqual(result['content_classification']['content_status'], 'metadata_only')
            self.assertNotIn('content_status', result['metadata'])
            self.assertNotIn('INTERNAL_ROLE_EVIDENCE_MARKER', json.dumps(result['metadata']))
            self.assertIn('pices-metadata-only', result['metadata']['keywords'])
            self.assertEqual(source.read_text(), SOURCE)
            issues, _ = ZenodoValidator().validate_metadata(result['metadata'])
            self.assertEqual(issues, [])
            dto = build_canonical_dto(source_path=str(source), zenodo_metadata=result['metadata'], extra_metadata={'content_classification': result['content_classification']})
            self.assertEqual(dto.to_json()['extra_metadata']['content_classification']['content_status'], 'metadata_only')
