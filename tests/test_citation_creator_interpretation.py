"""Pinned citation profile never broadens source or creator authority."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.citation_creator_interpretation import validate_creator_interpretation, MANIFEST_SHA256

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / 'docs/readiness/2026-10-02/exxon_citation_interpretation.json'


class CitationCreatorInterpretationTests(unittest.TestCase):
    def setUp(self):
        from datetime import datetime, timezone
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.manifest = json.loads(MANIFEST.read_bytes())
        self.reference = {'manifest_path': str(MANIFEST), 'manifest_sha256': MANIFEST_SHA256}
        self.member = self.manifest['members'][0]
        self.root = ET.parse(REPO / 'FGDC' / (self.member['source_id'] + '.xml')).getroot()

    def validate(self, reference=None, member=None, root=None):
        member = member or self.member
        return validate_creator_interpretation(reference or self.reference, member['source_id'],
                                               member['source_sha256'], root if root is not None else self.root)

    def test_exact_citation_preserves_full_affiliations(self):
        self.assertEqual(self.validate(), self.manifest['creators'])

    def test_source_id_and_hash_are_both_required(self):
        for field, value in [('source_id', 'FGDC-unknown'), ('source_sha256', '0' * 64)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(member={**self.member, field: value})

    def test_mixed_repeated_attributed_or_changed_origin_is_rejected(self):
        for mutation in ('mixed', 'repeated', 'attribute', 'changed'):
            root = copy.deepcopy(self.root)
            origin = root.find('./idinfo/citation/citeinfo/origin')
            if mutation == 'mixed':
                ET.SubElement(origin, 'b').text = 'extra'
            elif mutation == 'repeated':
                root.find('./idinfo/citation/citeinfo').append(copy.deepcopy(origin))
            elif mutation == 'attribute':
                origin.set('interpretation', 'extra')
            else:
                origin.text += ' Extra person'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.validate(root=root)

    def test_rehashed_arbitrary_manifest_cannot_grant_new_interpretation(self):
        for field, value in [('creators', [{'name': 'Invented, Person'}]),
                             ('members', []), ('scope', 'xml_authorship'),
                             ('publication_approved', True), ('evidence', [])]:
            manifest = {**self.manifest, field: value}
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'forged.json'
                path.write_text(json.dumps(manifest))
                reference = {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.validate(reference=reference)

    def test_missing_and_stale_manifest_rejected(self):
        for reference in ({}, {**self.reference, 'manifest_path': '/missing'},
                          {**self.reference, 'manifest_sha256': '0' * 64}):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                validate_creator_interpretation(reference, self.member['source_id'], self.member['source_sha256'], self.root)

    def prepared(self, tmp, enabled=True):
        from scripts.collection_qa import classify_collection
        from scripts.path_config import OutputPaths
        from datetime import datetime, timezone
        import shutil
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        shutil.copyfile(REPO / 'FGDC' / 'FGDC-1839.xml', source / 'FGDC-1839.xml')
        output = Path(tmp) / 'output'
        docs = REPO / 'docs/readiness/2026-10-02'
        report = classify_collection(source, output, self.reviewed_at,
            docs / 'rehosting_authority.json', docs / 'contact_source_interpretation.json',
            MANIFEST if enabled else None)
        paths = OutputPaths(str(output), 'sandbox')
        return report, paths, Path(paths.zenodo_json_dir) / 'FGDC-1839.json'

    def test_opt_in_only_and_preserves_rights_source_and_caveat(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            default, _, _ = self.prepared(tmp, False)
            self.assertEqual(default['summary']['source_status_counts']['held'], 1)
            report, paths, path = self.prepared(tmp)
            self.assertEqual(report['summary']['source_status_counts']['supported'], 1)
            payload = json.loads(path.read_bytes())
            metadata = payload['metadata']
            self.assertEqual(metadata['creators'], self.manifest['creators'])
            self.assertEqual(metadata['license'], '')
            self.assertEqual(metadata['access_right'], 'restricted')
            self.assertIn('XML authorship is not independently established', metadata['notes'])
            self.assertFalse(report['records'][0]['publication_approved'])
            self.assertFalse(report['records'][0]['remote_verified'])
            self.assertEqual((Path(paths.original_fgdc_dir) / 'FGDC-1839.xml').read_bytes(),
                             (REPO / 'FGDC' / 'FGDC-1839.xml').read_bytes())
            assess_source(str(path), paths)

    def test_qa_revalidates_complete_creators_and_manifest_reference(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            _, paths, path = self.prepared(tmp)
            original = json.loads(path.read_bytes())
            for mutation in ('affiliation', 'identifier', 'order', 'reference', 'drop_reference'):
                payload = copy.deepcopy(original)
                if mutation == 'affiliation':
                    payload['metadata']['creators'][1]['affiliation'] = 'Invented institution'
                elif mutation == 'identifier':
                    payload['metadata']['creators'][1]['orcid'] = '0000-0002-1825-0097'
                elif mutation == 'order':
                    payload['metadata']['creators'].reverse()
                elif mutation == 'reference':
                    payload['artifact_policy']['creator_interpretation']['manifest_sha256'] = '0' * 64
                else:
                    del payload['artifact_policy']['creator_interpretation']
                path.write_text(json.dumps(payload))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    assess_source(str(path), paths)

    def test_cache_cannot_drop_profile_or_change_affiliation(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            _, paths, path = self.prepared(tmp)
            payload = json.loads(path.read_bytes())
            payload['metadata']['creators'][1]['affiliation'] = 'Invented institution'
            path.write_text(json.dumps(payload))
            report, paths, path = self.prepared(tmp)
            self.assertEqual(report['summary']['source_status_counts']['supported'], 1)
            self.assertEqual(assess_source(str(path), paths)[0]['creators'], self.manifest['creators'])

    def test_human_qa_all_schemas_recheck_manifest_bytes_and_full_creators(self):
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval
        from scripts.upload_service import metadata_hash, prepare_metadata
        import shutil
        for schema in (1, 2):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as tmp:
                _, paths, path = self.prepared(tmp)
                evidence = Path(tmp) / 'creator-evidence.json'
                shutil.copyfile(MANIFEST, evidence)
                payload = json.loads(path.read_bytes())
                payload['artifact_policy']['creator_interpretation']['manifest_path'] = str(evidence)
                path.write_text(json.dumps(payload))
                metadata, source, digest = prepare_metadata(str(path), paths)
                artifact = prepare_artifact(payload, source)
                entry = {'environment': 'sandbox', 'deposition_id': 123, 'json_file': str(path),
                         'source_sha256': digest, 'metadata_sha256': metadata_hash(metadata),
                         'artifact_contract': artifact, 'zenodo_url': 'https://sandbox.zenodo.org/deposit/123'}
                record = {'fgdc_id': 'FGDC-1839', 'deposition_id': 123, 'source_sha256': digest,
                          'metadata_sha256': metadata_hash(metadata), 'artifact_contract': artifact,
                          'qa': {'approved': True, 'reviewer_type': 'human', 'reviewer': 'Offline test fixture',
                                 'reviewed_at': '2026-10-02T21:00:00Z', 'rationale': 'Fixture source review',
                                 'checks': dict.fromkeys(QA_CHECKS, True), 'run_id': 'fixture',
                                 'review_revision': 'fixture', 'evidence': ['Fixture evidence']},
                          'duplicate_review': {'status': 'reviewed', 'classification': 'checked_no_match',
                                               'rationale': 'Fixture only', 'evidence': ['Fixture only']}}
                manifest = {'schema_version': schema, 'source_revision': 'fixture', 'environment': 'sandbox',
                            'records': [record]}
                validate_approval(manifest, 'FGDC-1839', entry, paths)
                for mutation in ('changed_bytes', 'missing_file', 'reference', 'affiliation', 'identifier'):
                    shutil.copyfile(MANIFEST, evidence)
                    candidate = copy.deepcopy(payload)
                    if mutation == 'changed_bytes':
                        evidence.write_bytes(evidence.read_bytes() + b'\n')
                    elif mutation == 'missing_file':
                        evidence.unlink()
                    elif mutation == 'reference':
                        candidate['artifact_policy']['creator_interpretation']['manifest_sha256'] = '0' * 64
                    elif mutation == 'affiliation':
                        candidate['metadata']['creators'][1]['affiliation'] = 'Invented'
                    else:
                        candidate['metadata']['creators'][1]['orcid'] = '0000-0002-1825-0097'
                    path.write_text(json.dumps(candidate))
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        validate_approval(manifest, 'FGDC-1839', entry, paths)

    def test_coherently_rehashed_cache_cannot_approve_changed_affiliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, path = self.prepared(tmp)
            payload = json.loads(path.read_bytes())
            payload['metadata']['creators'][1]['affiliation'] = 'Invented institution'
            path.write_text(json.dumps(payload))
            report_path = Path(tmp) / 'output/classification.json'
            cached = json.loads(report_path.read_bytes())
            cached['records'][0]['prepared_payload_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            report_path.write_text(json.dumps(cached))
            report, _, _ = self.prepared(tmp)
            self.assertEqual(report['summary']['source_status_counts']['supported'], 0)
            self.assertEqual(report['summary']['source_status_counts']['held'], 1)
            self.assertTrue(any('Creator objects differ' in reason for reason in report['records'][0]['hold_reasons']))
