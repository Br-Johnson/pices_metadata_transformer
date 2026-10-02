"""Source-only collection classification and restart behavior, entirely offline."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths
from scripts.upload_service import read_json


SUPPORTED = (b'<metadata><idinfo><citation><citeinfo><title>Metadata catalogue</title>'
             b'<origin>Example Marine Institute</origin><pubdate>122003</pubdate></citeinfo></citation>'
             b'<descript><abstract>Original descriptive metadata.</abstract></descript>'
             b'<useconst>CC0</useconst></idinfo><metainfo><metd>20020430</metd>'
             b'<metuc>CC BY 4.0</metuc><metac>No restrictions</metac></metainfo></metadata>')


class CollectionQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sources = Path(self.tmp.name, 'sources'); self.sources.mkdir()
        self.output = Path(self.tmp.name, 'classified')
        self.reviewed_at = '2026-01-01T00:00:00Z'

    def classify(self):
        return classify_collection(self.sources, self.output, self.reviewed_at)

    def test_supported_held_and_malformed_sources_have_distinct_honest_statuses(self):
        fixtures = {'supported': SUPPORTED,
                    'rights': SUPPORTED.replace(b'<metuc>CC BY 4.0', b'<metuc>Unknown'),
                    'restricted': SUPPORTED.replace(b'No restrictions', b'Restricted metadata'),
                    'date': SUPPORTED.replace(b'20020430', b'122003'),
                    'creators': SUPPORTED.replace(b'Example Marine Institute', b'Alice and Bob'),
                    'malformed': b'<metadata><not-closed>'}
        for name, raw in fixtures.items(): (self.sources / (name + '.xml')).write_bytes(raw)
        report = self.classify()
        rows = {row['source_id']: row for row in report['records']}
        self.assertEqual(rows['supported']['source_status'], 'supported')
        for name in ('rights', 'restricted', 'date', 'creators'):
            self.assertEqual(rows[name]['source_status'], 'held')
            self.assertTrue(rows[name]['hold_reasons'])
        self.assertEqual(rows['malformed']['source_status'], 'failed')
        self.assertTrue(rows['malformed']['parse_error'])
        self.assertEqual(report['summary']['source_status_counts'], {'supported': 1, 'held': 4, 'failed': 1})
        self.assertEqual(report['summary']['remote_verified'], 0)
        self.assertEqual(report['summary']['publication_approved'], 0)
        self.assertTrue(all(not row['publication_approved'] and not row['remote_verified'] for row in rows.values()))
        for name, raw in fixtures.items(): self.assertEqual((self.sources / (name + '.xml')).read_bytes(), raw)
        paths = OutputPaths(str(self.output), 'sandbox')
        self.assertEqual(Path(paths.original_fgdc_dir, 'supported.xml').read_bytes(), SUPPORTED)
        payload = read_json(Path(paths.zenodo_json_dir, 'supported.json'))
        self.assertEqual(payload['metadata']['publication_date'], '2002-04-30')
        self.assertEqual(payload['metadata']['upload_type'], 'other')
        self.assertEqual(payload['metadata']['license'], 'cc-by-4.0')
        self.assertEqual(payload['metadata']['creators'][0]['name'], 'Example Marine Institute')
        self.assertIn('source-only', report['summary']['coverage'])

    def test_resume_unchanged_evidence_does_not_retransform_sources(self):
        (self.sources / 'supported.xml').write_bytes(SUPPORTED)
        original = self.classify()
        with patch('scripts.collection_qa.FGDCToZenodoTransformer._build_zenodo_metadata', side_effect=AssertionError('Unchanged source should resume')):
            resumed = self.classify()
        self.assertEqual(resumed, original)

    def test_exact_aliases_are_held_and_removing_alias_restores_source_status(self):
        (self.sources / 'first.xml').write_bytes(SUPPORTED)
        (self.sources / 'alias.xml').write_bytes(SUPPORTED)
        first = self.classify()
        self.assertEqual(first['summary']['source_status_counts']['held'], 2)
        self.assertEqual(first['summary']['exact_copy_groups'], 1)
        self.assertTrue(all(row['source_status_without_aliases'] == 'supported' for row in first['records']))
        (self.sources / 'alias.xml').unlink()
        resumed = self.classify()
        self.assertEqual(resumed['summary']['source_status_counts'], {'supported': 1, 'held': 0, 'failed': 0})
        self.assertEqual(resumed['summary']['exact_copy_groups'], 0)
        row = resumed['records'][0]
        self.assertEqual(row['exact_copy_aliases'], [])
        self.assertNotIn('Exact-copy aliases require identity adjudication', row['hold_reasons'])

    def test_changed_source_is_reclassified_while_unchanged_source_resumes(self):
        first = self.sources / 'first.xml'; first.write_bytes(SUPPORTED)
        second = self.sources / 'second.xml'; second.write_bytes(SUPPORTED + b'\n')
        before = self.classify()
        second.write_bytes(SUPPORTED.replace(b'<metuc>CC BY 4.0', b'<metuc>Unknown'))
        after = self.classify()
        before_rows = {row['source_id']: row for row in before['records']}
        rows = {row['source_id']: row for row in after['records']}
        self.assertEqual(rows['first'], before_rows['first'])
        self.assertNotEqual(rows['second']['source_sha256'], before_rows['second']['source_sha256'])
        self.assertEqual(rows['second']['source_status'], 'held')

    def test_resume_repairs_missing_or_tampered_generated_artifacts(self):
        (self.sources / 'supported.xml').write_bytes(SUPPORTED)
        self.classify()
        paths = OutputPaths(str(self.output), 'sandbox')
        payload_path = Path(paths.zenodo_json_dir, 'supported.json')
        source_copy = Path(paths.original_fgdc_dir, 'supported.xml')
        for mutation in ('missing_payload', 'tampered_payload', 'missing_copy', 'tampered_copy'):
            with self.subTest(mutation=mutation):
                if mutation == 'missing_payload': payload_path.unlink()
                elif mutation == 'tampered_payload': payload_path.write_text('{"metadata":{"license":"cc-zero"}}')
                elif mutation == 'missing_copy': source_copy.unlink()
                else: source_copy.write_bytes(b'<tampered/>')
                report = self.classify()
                self.assertEqual(report['records'][0]['technical_metadata'], 'pass')
                self.assertTrue(payload_path.exists())
                self.assertEqual(read_json(payload_path)['metadata']['license'], 'cc-by-4.0')
                self.assertEqual(source_copy.read_bytes(), SUPPORTED)

    def test_changed_classification_dependency_invalidates_cached_profile(self):
        (self.sources / 'supported.xml').write_bytes(SUPPORTED)
        before = self.classify()
        original_read_bytes = Path.read_bytes
        def changed_dependency(path):
            raw = original_read_bytes(path)
            return raw + b'\n# changed semantic policy\n' if path.name == 'content_classification.py' else raw
        with patch.object(Path, 'read_bytes', changed_dependency):
            after = self.classify()
        self.assertNotEqual(after['profile_sha256'], before['profile_sha256'])


if __name__ == '__main__':
    unittest.main()
