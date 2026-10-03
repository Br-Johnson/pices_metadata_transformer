"""Source-only collection classification and restart behavior, entirely offline."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths
from scripts.rehosting_authority import STATEMENT
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

    def test_resume_recomputes_semantic_verdicts_and_source_only_flags(self):
        raw = SUPPORTED.replace(b'CC BY 4.0', b'Unknown').replace(
            b'No restrictions', b'Sensitive; permission required')
        source = self.sources / 'restricted.xml'; source.write_bytes(raw)
        authority = Path(self.tmp.name, 'authority.json')
        authority.write_text(json.dumps({
            'schema_version': 1, 'attested_by': 'Brett', 'attested_at': '2026-10-02',
            'statement': STATEMENT, 'scope': 'historical_geonetwork_metadata',
            'grants_rehosting': True, 'grants_new_license': False,
            'sources': {'restricted': hashlib.sha256(raw).hexdigest()}}))
        for route, manifest in (('xml_rights', None), ('attested', authority)):
            with self.subTest(route=route):
                output = Path(self.tmp.name, route)
                original = classify_collection(self.sources, output, self.reviewed_at, manifest)
                self.assertEqual(original['records'][0]['source_status'], 'held')
                paths = OutputPaths(str(output), 'sandbox')
                payload = Path(paths.zenodo_json_dir, 'restricted.json')
                payload_hash = hashlib.sha256(payload.read_bytes()).hexdigest()
                report_path = output / 'classification.json'
                cached = read_json(report_path)
                cached['records'][0].update(source_status='supported',
                    source_status_without_aliases='supported', hold_reasons=[],
                    publication_approved=True, remote_verified=True)
                report_path.write_text(json.dumps(cached))
                with patch('scripts.collection_qa.FGDCToZenodoTransformer._build_zenodo_metadata',
                           side_effect=AssertionError('Verified payload should be reused')):
                    resumed = classify_collection(self.sources, output, self.reviewed_at, manifest)
                fresh = classify_collection(self.sources, Path(self.tmp.name, route + '-fresh'),
                                            self.reviewed_at, manifest)
                row = resumed['records'][0]
                self.assertEqual(row['source_status'], 'held')
                self.assertTrue(row['hold_reasons'])
                self.assertFalse(row['publication_approved'])
                self.assertFalse(row['remote_verified'])
                self.assertEqual(resumed['records'], fresh['records'])
                self.assertEqual(resumed['summary'], fresh['summary'])
                self.assertEqual(resumed['profile_sha256'], original['profile_sha256'])
                self.assertEqual(hashlib.sha256(payload.read_bytes()).hexdigest(), payload_hash)
                self.assertEqual(source.read_bytes(), raw)

    def test_resume_recomputes_failed_rows_without_constructed_payloads(self):
        raw = b'<metadata><not-closed>'
        source = self.sources / 'malformed.xml'; source.write_bytes(raw)
        original = self.classify()
        self.assertEqual(original['records'][0]['source_status'], 'failed')
        self.assertEqual(original['records'][0]['technical_metadata'], 'not_constructed')
        report_path = self.output / 'classification.json'
        cached = read_json(report_path)
        cached['records'][0].update(source_status='supported',
            source_status_without_aliases='supported', hold_reasons=[],
            parse_error='Edited cached parse evidence', publication_approved=True,
            remote_verified=True)
        report_path.write_text(json.dumps(cached))
        resumed = self.classify()
        self.assertEqual(resumed, original)
        self.assertEqual(source.read_bytes(), raw)

    def test_resume_rebuilds_payloads_that_change_collection_policy_routes(self):
        source = self.sources / 'sample.xml'
        authority = Path(self.tmp.name, 'authority.json')
        for route in ('dataset_instead_of_xml', 'xml_license_instead_of_attestation'):
            with self.subTest(route=route):
                raw = (SUPPORTED.replace(b'122003', b'20200102').replace(b'CC BY 4.0', b'Unknown')
                       .replace(b'No restrictions', b'Sensitive; permission required')
                       if route == 'dataset_instead_of_xml' else SUPPORTED)
                source.write_bytes(raw)
                manifest = None
                if route == 'xml_license_instead_of_attestation':
                    authority.write_text(json.dumps({
                        'schema_version': 1, 'attested_by': 'Brett', 'attested_at': '2026-10-02',
                        'statement': STATEMENT, 'scope': 'historical_geonetwork_metadata',
                        'grants_rehosting': True, 'grants_new_license': False,
                        'sources': {'sample': hashlib.sha256(raw).hexdigest()}}))
                    manifest = authority
                output = Path(self.tmp.name, route)
                original = classify_collection(self.sources, output, self.reviewed_at, manifest)
                paths = OutputPaths(str(output), 'sandbox')
                payload_path = Path(paths.zenodo_json_dir, 'sample.json')
                original_payload = payload_path.read_bytes()
                payload = read_json(payload_path)
                if route == 'dataset_instead_of_xml':
                    self.assertEqual(original['records'][0]['source_status'], 'held')
                    payload['artifact_policy'] = None
                    payload['metadata'].update(title='Metadata catalogue',
                        publication_date='2020-01-02', license='cc-zero', access_right='open')
                else:
                    self.assertEqual(original['records'][0]['source_status'], 'supported')
                    del payload['artifact_policy']['rehosting_authority']
                    payload['artifact_policy']['license'] = 'cc-by-4.0'
                    payload['metadata'].update(license='cc-by-4.0', access_right='open')
                payload['metadata'].pop('access_conditions', None)
                payload_path.write_text(json.dumps(payload))
                report_path = output / 'classification.json'
                cached = read_json(report_path)
                cached['records'][0]['prepared_payload_sha256'] = hashlib.sha256(payload_path.read_bytes()).hexdigest()
                report_path.write_text(json.dumps(cached))
                resumed = classify_collection(self.sources, output, self.reviewed_at, manifest)
                self.assertEqual(resumed, original)
                self.assertEqual(payload_path.read_bytes(), original_payload)
                self.assertEqual(source.read_bytes(), raw)

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

    def test_long_source_titles_are_preserved_and_over_limit_titles_held(self):
        paths = OutputPaths(str(self.output), 'sandbox')
        for length, expected in ((240, 'supported'), (260, 'held')):
            title = 'A' * length
            raw = SUPPORTED.replace(b'Metadata catalogue', title.encode())
            source = self.sources / f'title{length}.xml'; source.write_bytes(raw)
            report = self.classify()
            row = next(item for item in report['records'] if item['source_id'] == source.stem)
            payload = read_json(Path(paths.zenodo_json_dir, source.stem + '.json'))
            self.assertEqual(payload['metadata']['title'], title)
            self.assertEqual(len(payload['metadata']['title']), length)
            self.assertEqual(row['source_status'], expected)
            self.assertEqual(row['technical_metadata'], 'pass' if length == 240 else 'held')
            self.assertFalse(row['publication_approved'])
            self.assertEqual(source.read_bytes(), raw)

    def test_math_and_literal_placeholders_are_escaped_without_losing_source_text(self):
        raw = SUPPORTED.replace(b'Original descriptive metadata.',
                                b'Observed x &lt; 3 and y &gt; 2; literal &lt;REQUIRED&gt; &amp; &lt;Unknown&gt;.')
        source = self.sources / 'angles.xml'; source.write_bytes(raw)
        report = self.classify()
        row = report['records'][0]
        self.assertEqual(row['source_status'], 'supported', row['hold_reasons'])
        self.assertEqual(row['technical_metadata'], 'pass')
        paths = OutputPaths(str(self.output), 'sandbox')
        description = read_json(Path(paths.zenodo_json_dir, 'angles.json'))['metadata']['description']
        self.assertIn('x &lt; 3 and y &gt; 2', description)
        self.assertIn('&lt;REQUIRED&gt; &amp; &lt;Unknown&gt;', description)
        self.assertNotIn('<REQUIRED>', description)
        self.assertFalse(row['publication_approved'])
        self.assertEqual(source.read_bytes(), raw)
        self.assertEqual(Path(paths.original_fgdc_dir, source.name).read_bytes(), raw)

    def test_safe_formatting_does_not_resolve_unknown_rights_or_promote_contacts(self):
        raw = SUPPORTED.replace(b'Metadata catalogue', b'T' * 240).replace(
            b'Original descriptive metadata.', b'Literal &lt;REQUIRED&gt; placeholder.').replace(
            b'<metuc>CC BY 4.0', b'<metuc>Unknown')
        source = self.sources / 'unknown-rights.xml'; source.write_bytes(raw)
        report = self.classify(); row = report['records'][0]
        self.assertEqual(row['source_status'], 'held')
        self.assertFalse(row['has_supported_xml_grant'])
        self.assertFalse(row['publication_approved'])
        self.assertEqual(source.read_bytes(), raw)
        no_author = SUPPORTED.replace(b'<origin>Example Marine Institute</origin>', b'').replace(
            b'</idinfo>', b'<ptcontac><cntinfo><cntorgp><cntorg>Contact Marine Institute</cntorg></cntorgp></cntinfo></ptcontac></idinfo>')
        (self.sources / 'contact-only.xml').write_bytes(no_author)
        rows = {item['source_id']: item for item in self.classify()['records']}
        self.assertEqual(rows['contact-only']['source_status'], 'held')
        self.assertFalse(rows['contact-only']['publication_approved'])


if __name__ == '__main__':
    unittest.main()
