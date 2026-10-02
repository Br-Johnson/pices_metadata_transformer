"""Collection attestation removes authority holds without inventing licenses."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths
from scripts.rehosting_authority import STATEMENT
from scripts.upload_service import read_json
from tests.test_collection_qa import SUPPORTED


class CollectionAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sources = Path(self.tmp.name, 'sources'); self.sources.mkdir()
        self.output = Path(self.tmp.name, 'output')
        self.authority = Path(self.tmp.name, 'authority.json')
        self.raw = SUPPORTED.replace(b'CC BY 4.0', b'Unknown')
        (self.sources / 'sample.xml').write_bytes(self.raw)
        self.manifest = {'schema_version': 1, 'attested_by': 'Brett', 'attested_at': '2026-10-02',
                         'statement': STATEMENT, 'scope': 'historical_geonetwork_metadata',
                         'grants_rehosting': True, 'grants_new_license': False,
                         'sources': {'sample': hashlib.sha256(self.raw).hexdigest()}}
        self.authority.write_text(json.dumps(self.manifest))

    def run_collection(self, authority):
        return classify_collection(self.sources, self.output, '2026-10-02T12:20:58Z', authority)

    def test_attestation_resolves_scope_not_license_or_release(self):
        before = self.run_collection(None)
        after = self.run_collection(self.authority)
        self.assertEqual(before['records'][0]['source_status'], 'held')
        self.assertEqual(after['records'][0]['source_status'], 'supported')
        self.assertEqual(after['records'][0]['rehosting_authority'], 'USER_ATTESTED')
        self.assertFalse(after['records'][0]['publication_approved'])
        self.assertFalse(after['records'][0]['remote_verified'])
        payload = read_json(Path(OutputPaths(str(self.output), 'sandbox').zenodo_json_dir, 'sample.json'))
        self.assertEqual(payload['metadata']['license'], '')
        self.assertEqual(payload['metadata']['access_right'], 'restricted')
        self.assertIn('Unknown', payload['artifact_policy']['rights_evidence'])
        self.assertEqual((self.sources / 'sample.xml').read_bytes(), self.raw)

    def test_changed_scope_invalidates_resume_and_restores_hold(self):
        before = self.run_collection(self.authority)
        self.manifest['sources'] = {}
        self.authority.write_text(json.dumps(self.manifest))
        after = self.run_collection(self.authority)
        self.assertNotEqual(before['profile_sha256'], after['profile_sha256'])
        self.assertEqual(after['records'][0]['source_status'], 'held')
        self.assertEqual(after['records'][0]['rehosting_authority'], 'not_established')
        self.assertFalse(after['records'][0]['publication_approved'])

    def test_exact_sea_grant_citation_preserves_organization_and_restricted_authority(self):
        raw = self.raw.replace(b'Example Marine Institute', b'Washington Sea Grant Program')
        raw = raw.replace(b'</idinfo>',
                          b'<ptcontac><cntinfo><cntperp><cntper>Smith, Jane</cntper>'
                          b'<cntorg>Washington Sea Grant Program</cntorg></cntperp>'
                          b'</cntinfo></ptcontac></idinfo>')
        source = self.sources / 'sample.xml'
        source.write_bytes(raw)
        self.manifest['sources']['sample'] = hashlib.sha256(raw).hexdigest()
        self.authority.write_text(json.dumps(self.manifest))
        report = self.run_collection(self.authority)
        row = report['records'][0]
        self.assertEqual(row['source_status'], 'supported', row['hold_reasons'])
        self.assertFalse(row['publication_approved'])
        self.assertFalse(row['remote_verified'])
        payload = read_json(Path(OutputPaths(str(self.output), 'sandbox').zenodo_json_dir, 'sample.json'))
        self.assertEqual(payload['metadata']['creators'],
                         [{'name': 'Washington Sea Grant Program', 'type': 'Organization'}])
        self.assertEqual(payload['metadata']['publication_date'], '2002-04-30')
        self.assertEqual(payload['metadata']['license'], '')
        self.assertEqual(payload['metadata']['access_right'], 'restricted')
        self.assertIn('XML authorship is not independently established', payload['metadata']['notes'])
        self.assertEqual(payload['metadata']['contributors'][0],
                         {'name': 'Smith, Jane', 'type': 'ContactPerson'})
        self.assertEqual(source.read_bytes(), raw)

    def test_sea_grant_name_does_not_resolve_mixed_origins_or_source_access(self):
        for origin, access in (
                (b'Washington Sea Grant Program, Alice Smith and Bob Jones', b''),
                (b'Washington Sea Grant Program; Alice Smith', b''),
                (b'Washington Sea Grant Program', b'<metac>Contact Source.</metac>')):
            with self.subTest(origin=origin, access=access):
                raw = self.raw.replace(b'Example Marine Institute', origin)
                raw = raw.replace(b'<metainfo>', b'<metainfo>' + access)
                source = self.sources / 'sample.xml'
                source.write_bytes(raw)
                self.manifest['sources']['sample'] = hashlib.sha256(raw).hexdigest()
                self.authority.write_text(json.dumps(self.manifest))
                row = self.run_collection(self.authority)['records'][0]
                self.assertEqual(row['source_status'], 'held')
                self.assertFalse(row['publication_approved'])
                self.assertFalse(row['remote_verified'])
                self.assertEqual(source.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
