"""Exact product credits preserve earlier cohorts, complete source context and QA gates."""

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import citation_creator_interpretation as interpretation
from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths
from scripts.upload_service import read_json
from tests import test_creator415_institution3 as previous_tests
from tests.test_content_class_targets import current_profiles

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-04'
PREVIOUS = DOCS / 'source_citation_credits_415.json'
NEW = DOCS / 'source_citation_credits_423.json'
EXPECTED = {f'FGDC-{number}': [{'name': 'Japan Meteorological Agency'}]
            for number in (3951, 3952, 3953, 3966, 3967, 3968, 3969)}
EXPECTED['FGDC-1314'] = [{'name': name} for name in ('Evdokimov, V.V.', 'Rodin, V.E.',
                                                        'Viktorovskaya, G.I.', 'Pavlyuchkov, V.A.')]
PRIOR_CONTROL = 'FGDC-3954'
HELD_CONTROL = 'FGDC-3975'


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def compare_notes(before, after, additions):
    restored = after
    for note in additions:
        if '\n' + note not in restored:
            raise AssertionError('Missing exact source/role preservation note')
        restored = restored.replace('\n' + note, '', 1)
    old_lines = [line for line in before.splitlines() if line.startswith('Curator decision: ')]
    new_lines = [line for line in restored.splitlines() if line.startswith('Curator decision: ')]
    if len(old_lines) != 1 or len(new_lines) != 1:
        raise AssertionError('Expected complete curator decision context')
    old = json.loads(old_lines[0].removeprefix('Curator decision: '))
    new = json.loads(new_lines[0].removeprefix('Curator decision: '))
    new['metadata']['creators'] = old['metadata']['creators']
    if new != old or restored.replace(new_lines[0], old_lines[0], 1) != before:
        raise AssertionError('Notes changed beyond exact creator decision and added context')


class DerivedCreatorExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='pices-derived-credit-')
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.reviewed_at = datetime.now(timezone.utc).isoformat()
        cls.source = Path(cls.fixture.name) / 'sources'
        cls.source.mkdir()
        cls.ids = set(EXPECTED) | {PRIOR_CONTROL, HELD_CONTROL}
        for sid in cls.ids:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), cls.source / (sid + '.xml'))
        cls.output = Path(cls.fixture.name) / 'output'
        cls.paths = OutputPaths(str(cls.output), 'sandbox')
        cls.reports, cls.payloads = {}, {}
        for phase in ('before', 'after', 'repeat', 'withdrawn'):
            profiles = current_profiles()
            profiles['institution_creator_interpretation_manifest'] = (
                NEW if phase in ('after', 'repeat') else PREVIOUS)
            cls.reports[phase] = classify_collection(cls.source, cls.output, cls.reviewed_at, **profiles)
            cls.payloads[phase] = {sid: read_json(Path(cls.paths.zenodo_json_dir) / (sid + '.json'))
                                   for sid in cls.ids}
            if phase == 'after':
                cls.after_copy = Path(cls.fixture.name) / 'after'
                shutil.copytree(cls.output, cls.after_copy)

    def setUp(self):
        self.manifest = read_json(NEW)
        self.prior = read_json(PREVIOUS)
        self.added = self.manifest['cohorts'][len(self.prior['cohorts']):]
        self.profiles = {member['source_id']: cohort for cohort in self.added for member in cohort['members']}

    def test_exact_additive_scope_full_source_and_credit_objects(self):
        self.assertEqual(self.manifest['cohorts'][:len(self.prior['cohorts'])], self.prior['cohorts'])
        self.assertEqual(self.manifest['prior_manifest_sha256'], reference(PREVIOUS)['manifest_sha256'])
        self.assertEqual(reference(NEW)['manifest_sha256'], interpretation.SOURCE_CREDIT_423_MANIFEST_SHA256)
        members = [member for cohort in self.manifest['cohorts'] for member in cohort['members']]
        self.assertEqual(len(members), 415 + len(EXPECTED))
        self.assertEqual(len({row['source_id'] for row in members}), len(members))
        self.assertEqual(set(self.profiles), set(EXPECTED))
        for sid, cohort in self.profiles.items():
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            sha, root = hashlib.sha256(raw).hexdigest(), ET.fromstring(raw)
            self.assertEqual(cohort['members'], [{'source_id': sid, 'source_sha256': sha}])
            self.assertEqual(cohort['supplemental_source_elements'],
                             [{'xpath': '.', 'element': interpretation.source_element(root)}])
            self.assertEqual(cohort['creators'], EXPECTED[sid])
            self.assertEqual(interpretation.validate_creator_interpretation(reference(NEW), sid, sha, root),
                             EXPECTED[sid])
            self.assertTrue(cohort['preservation_required'])
            for evidence in cohort['external_evidence_references']:
                self.assertEqual(reference(REPO / evidence['manifest_path'])['manifest_sha256'],
                                 evidence['manifest_sha256'])

    def test_current_complete_metadata_exact_retry_withdrawal_and_unchanged_controls(self):
        self.assertEqual(self.reports['after'], self.reports['repeat'])
        self.assertEqual(self.payloads['after'], self.payloads['repeat'])
        self.assertEqual(self.reports['before'], self.reports['withdrawn'])
        self.assertEqual(self.payloads['before'], self.payloads['withdrawn'])
        for sid in self.ids:
            before, after = self.payloads['before'][sid], self.payloads['after'][sid]
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            self.assertEqual((Path(self.paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(), raw)
            for payload in (before, after):
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertEqual(payload['artifact_policy']['date_semantics'], 'source_metadata_date')
            if sid in EXPECTED:
                self.assertEqual(after['metadata']['creators'], EXPECTED[sid])
                self.assertNotEqual(before['metadata']['creators'], after['metadata']['creators'])
                self.assertEqual({k: v for k, v in before['metadata'].items() if k not in ('creators', 'notes')},
                                 {k: v for k, v in after['metadata'].items() if k not in ('creators', 'notes')})
                result = interpretation.validate_creator_interpretation(
                    reference(NEW), sid, hashlib.sha256(raw).hexdigest(), ET.fromstring(raw), True)
                compare_notes(before['metadata']['notes'], after['metadata']['notes'], result['preservation_notes'])
            else:
                self.assertEqual(before['metadata'], after['metadata'])
        for phase, report in self.reports.items():
            supported = ({PRIOR_CONTROL} | set(EXPECTED) if phase in ('after', 'repeat') else {PRIOR_CONTROL})
            self.assertEqual({row['source_id'] for row in report['records'] if row['source_status'] == 'supported'}, supported)
            self.assertTrue(all(not row['remote_verified'] and not row['publication_approved'] for row in report['records']))

    def test_changed_evidence_context_or_creators_rejects_source_and_both_human_qa_schemas(self):
        from scripts.agent_qa import assess_source
        from scripts.qa_manifest import validate_approval

        with tempfile.TemporaryDirectory() as tmp:
            prepared = Path(tmp) / 'prepared'
            shutil.copytree(self.after_copy, prepared)
            paths = OutputPaths(str(prepared), 'sandbox')
            sid = 'FGDC-3951'
            path, _, metadata, entry, manifest = previous_tests.InstitutionCreator415Tests.human_fixture(self, sid, paths)
            assess_source(str(path), paths)
            for schema in (1, 2):
                manifest['schema_version'] = schema
                self.assertTrue(validate_approval(manifest, sid, entry, paths, metadata)['qa']['approved'])
            original_read = Path.read_bytes
            for evidence in self.profiles[sid]['external_evidence_references']:
                target = (REPO / evidence['manifest_path']).resolve()
                for missing in (True, False):
                    def changed_read(candidate, _target=target, _missing=missing):
                        if candidate.resolve() == _target:
                            if _missing:
                                raise FileNotFoundError('Offline missing evidence fixture')
                            return original_read(candidate) + b' '
                        return original_read(candidate)
                    with patch.object(Path, 'read_bytes', changed_read):
                        previous_tests.InstitutionCreator415Tests.assert_shared_rejection(
                            self, sid, path, paths, metadata, entry, manifest)
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            sha, root = hashlib.sha256(raw).hexdigest(), ET.fromstring(raw)
            for xpath in ('./idinfo/descript/abstract', './metainfo/metd', './idinfo/accconst'):
                changed = copy.deepcopy(root)
                changed.find(xpath).text = 'Unreviewed change'
                with self.assertRaises(ValueError):
                    interpretation.validate_creator_interpretation(reference(NEW), sid, sha, changed)
            for fault in ('creator', 'context'):
                changed = copy.deepcopy(metadata)
                if fault == 'creator':
                    changed['creators'][0]['type'] = 'Organization'
                else:
                    changed['notes'] = 'Source and external role context discarded'
                with self.assertRaises(ValueError):
                    interpretation.validate_creator_metadata(reference(NEW), sid, sha, root, changed)

    def test_new_credit_does_not_replace_rehosting_authority_or_admit_other_gts_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'sources'
            source.mkdir()
            sid = 'FGDC-3951'
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
            profiles = current_profiles()
            profiles.update(authority_manifest=None, institution_creator_interpretation_manifest=NEW)
            report = classify_collection(source, Path(tmp) / 'prepared', self.reviewed_at, **profiles)
            self.assertEqual(report['records'][0]['source_status'], 'held')
            raw = (REPO / 'FGDC' / (HELD_CONTROL + '.xml')).read_bytes()
            with self.assertRaises(ValueError):
                interpretation.validate_creator_interpretation(
                    reference(NEW), HELD_CONTROL, hashlib.sha256(raw).hexdigest(), ET.fromstring(raw))
