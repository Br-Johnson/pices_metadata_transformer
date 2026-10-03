"""Exact access-held citation cleanup never promotes source or invents rights."""
import copy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.citation_creator_interpretation import validate_creator_interpretation, validate_creator_metadata
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, read_json

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-03'
MANIFEST = DOCS / 'access_held_source_citations_396.json'
PREVIOUS = DOCS / 'source_credit_citations_319.json'
QUEUE = DOCS / 'remaining_source_credit_candidates_86.json'
EXCLUDED = {'FGDC-10', 'FGDC-1257', 'FGDC-1258', 'FGDC-1262', 'FGDC-1273', 'FGDC-2664', 'FGDC-2817', 'FGDC-4063', 'FGDC-4064'}
SIBLINGS = {'FGDC-121', 'FGDC-1767', 'FGDC-336', 'FGDC-533', 'FGDC-535'}


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class AccessHeldSourceCreditTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(MANIFEST)
        self.new = self.manifest['cohorts'][143:]
        self.profiles = {m['source_id']: c for c in self.new for m in c['members']}
        self.queue = {m['source_id']: m for m in read_json(QUEUE)['members']}
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def prepared(self, tmp, ids, manifest=MANIFEST):
        from scripts.collection_qa import classify_collection
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        for sid in ids:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        output = Path(tmp) / 'output'
        old = REPO / 'docs/readiness/2026-10-02'
        report = classify_collection(source, output, self.reviewed_at,
            authority_manifest=old / 'rehosting_authority.json',
            access_interpretation_manifest=old / 'contact_source_interpretation.json',
            creator_interpretation_manifest=old / 'exxon_citation_interpretation.json',
            dataset_access_interpretation_manifest=old / 'registration_access_interpretation.json',
            contributor_access_interpretation_manifest=old / 'contributor_source_interpretation.json',
            collective_creator_interpretation_manifest=DOCS / 'dfo_staff_citation_interpretation.json',
            institution_creator_interpretation_manifest=manifest,
            source_link_interpretation_manifest=DOCS / 'historical_dataset_linkage_21.json')
        return report, OutputPaths(str(output), 'sandbox')

    def test_all_396_bindings_preserve_previous_319_and_exact_reviewed_77(self):
        self.assertEqual(self.manifest['cohorts'][:143], read_json(PREVIOUS)['cohorts'])
        self.assertEqual(self.manifest['prior_manifest_sha256'], reference(PREVIOUS)['manifest_sha256'])
        self.assertEqual(self.manifest['reviewed_source_queue_sha256'], reference(QUEUE)['manifest_sha256'])
        self.assertEqual(set(self.profiles), set(self.queue) - EXCLUDED)
        self.assertEqual(len(self.profiles), 77)
        self.assertTrue(SIBLINGS.issubset(self.profiles))
        self.assertEqual(sum(len(c['members']) for c in self.manifest['cohorts']), 396)
        for c in self.manifest['cohorts']:
            for m in c['members']:
                raw = (REPO / 'FGDC' / (m['source_id'] + '.xml')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), m['source_sha256'])
                self.assertEqual(validate_creator_interpretation(reference(MANIFEST), m['source_id'], m['source_sha256'], ET.fromstring(raw)), c['creators'])
        for sid in SIBLINGS:
            self.assertEqual(self.profiles[sid]['creators'], self.queue[sid]['existing_full_creators'])

    def test_all_86_remain_access_held_and_only_77_creator_diagnostics_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, self.queue, PREVIOUS)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 86, 'failed': 0})
            old = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json')) for sid in self.queue}
            after, paths = self.prepared(tmp, self.queue)
            self.assertEqual(after['summary']['source_status_counts'], before['summary']['source_status_counts'])
            for row in after['records']:
                sid = row['source_id']
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                self.assertIn('Metadata access terms need source-backed adjudication', row['hold_reasons'])
                self.assertFalse(row['remote_verified'])
                self.assertFalse(row['publication_approved'])
                if sid in self.profiles:
                    self.assertNotIn('Creator semantics are ambiguous', row['hold_reasons'])
                    self.assertIn('Contradictory or unsupported source access constraints require adjudication', row['hold_reasons'])
                    self.assertEqual(payload['metadata']['creators'], self.profiles[sid]['creators'])
                    self.assertIn('Original primary citation origin', payload['metadata']['notes'])
                    self.assertEqual(payload['artifact_policy']['creator_interpretation'], reference(MANIFEST))
                    left = {k: v for k, v in old[sid]['metadata'].items() if k not in ('creators', 'notes')}
                    self.assertEqual(left, {k: v for k, v in payload['metadata'].items() if k not in ('creators', 'notes')})
                    unchanged_policy = {k: v for k, v in payload['artifact_policy'].items() if k != 'creator_interpretation'}
                    self.assertEqual(unchanged_policy, old[sid]['artifact_policy'])
                    self.assertNotIn('source_access_interpretation', payload['artifact_policy'])
                    self.assertNotIn('dataset_access_interpretation', payload['artifact_policy'])
                else:
                    self.assertIn('Creator semantics are ambiguous', row['hold_reasons'])
                    self.assertEqual(payload, old[sid])
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(), (REPO / 'FGDC' / (sid + '.xml')).read_bytes())

    def test_required_source_roles_full_objects_and_abstracts_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ids = ['FGDC-28', 'FGDC-1265', 'FGDC-289', 'FGDC-906', 'FGDC-724', 'FGDC-2197', 'FGDC-2228', 'FGDC-2701']
            _, paths = self.prepared(tmp, ids)
            for sid in ids:
                raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
                root, sha = ET.fromstring(raw), hashlib.sha256(raw).hexdigest()
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                validate_creator_metadata(reference(MANIFEST), sid, sha, root, payload['metadata'])
                before = ET.tostring(root)
                for fault in ('context', 'name', 'type', 'affiliation', 'identifier'):
                    metadata = copy.deepcopy(payload['metadata'])
                    if fault == 'context': metadata['notes'] = 'Missing original role/context'
                    elif fault == 'identifier': metadata['creators'][0]['orcid'] = 'Inferred'
                    else: metadata['creators'][0][fault] = 'Inferred'
                    with self.subTest(sid=sid, fault=fault), self.assertRaises(ValueError): validate_creator_metadata(reference(MANIFEST), sid, sha, root, metadata)
                changed = copy.deepcopy(root)
                changed.find('./idinfo/descript/abstract').text = 'Invented role evidence'
                with self.assertRaises(ValueError): validate_creator_interpretation(reference(MANIFEST), sid, sha, changed)
                self.assertEqual(ET.tostring(root), before)
            self.assertIn('(Ed)', self.profiles['FGDC-289']['context_note'])
            self.assertIn('(comp.)', self.profiles['FGDC-906']['context_note'])
            self.assertIn('no author role is inferred', self.profiles['FGDC-289']['context_note'])
            for sid in ('FGDC-1269', 'FGDC-1271'):
                self.assertNotIn('publication-venue', self.profiles[sid]['context_note'])
                self.assertIn('literal magazine/source context', self.profiles[sid]['context_note'])
            self.assertNotIn('hierarchy', self.profiles['FGDC-28']['context_note'])
            self.assertNotIn('hierarchy', self.profiles['FGDC-70']['context_note'])

    def test_withdrawal_missing_forged_profiles_and_cache_tampering_preserve_access_holds(self):
        ids = ['FGDC-121', 'FGDC-906', 'FGDC-2197', 'FGDC-2228']
        with tempfile.TemporaryDirectory() as tmp:
            first, paths = self.prepared(tmp, ids)
            path = Path(paths.zenodo_json_dir) / 'FGDC-2197.json'
            original = read_json(path)
            tampered = copy.deepcopy(original)
            tampered['metadata']['creators'][0]['name'] = 'Invented author'
            atomic_json(path, tampered)
            self.assertEqual(first, self.prepared(tmp, ids)[0])
            self.assertEqual(read_json(path), original)
            for manifest in (PREVIOUS, None, Path(tmp) / 'missing.json'):
                report, _ = self.prepared(tmp, ids, manifest)
                self.assertTrue(all('Creator semantics are ambiguous' in row['hold_reasons'] for row in report['records']))
                self.assertTrue(all('Metadata access terms need source-backed adjudication' in row['hold_reasons'] for row in report['records']))
            forged = read_json(MANIFEST)
            forged['cohorts'][143]['members'][0]['source_id'] = 'FGDC-1257'
            forged_path = Path(tmp) / 'forged.json'
            atomic_json(forged_path, forged)
            report, _ = self.prepared(tmp, ids, forged_path)
            self.assertEqual(report['summary']['source_status_counts'], {'supported': 0, 'held': 4, 'failed': 0})
            self.assertTrue(all('Creator semantics are ambiguous' in row['hold_reasons'] for row in report['records']))

    def test_nine_unresolved_roles_cannot_enter_the_exact_profile(self):
        for sid in EXCLUDED:
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                validate_creator_interpretation(reference(MANIFEST), sid, hashlib.sha256(raw).hexdigest(), ET.fromstring(raw))


if __name__ == '__main__':
    unittest.main()
