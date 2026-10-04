"""One exact editorial title preserves every work-title word and all source context."""

import copy
import hashlib
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts import source_title_interpretation as interpretation
from scripts.citation_creator_interpretation import source_element
from scripts.path_config import OutputPaths
from scripts.source_link_interpretation import fingerprint
from scripts.upload_service import (
    atomic_json,
    metadata_hash,
    prepare_metadata,
    read_json,
)

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-04'
PREVIOUS = REPO / 'docs/readiness/2026-10-03/source_display_titles_35.json'
NEW = DOCS / 'source_display_titles_36.json'
PROPOSAL = DOCS / 'fgdc233_display_title_proposal.json'
SID = 'FGDC-233'


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class ResidualTitle233Tests(unittest.TestCase):
    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.proposal = read_json(PROPOSAL)
        self.member = read_json(NEW)['members'][-1]

    def prepared(self, tmp, titles=NEW, authority=True):
        from scripts.collection_qa import classify_collection

        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        for sid in (SID, 'FGDC-621', 'FGDC-4063'):
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        older = REPO / 'docs/readiness/2026-10-02'
        previous = REPO / 'docs/readiness/2026-10-03'
        report = classify_collection(
            source, Path(tmp) / 'output', self.reviewed_at,
            authority_manifest=older / 'rehosting_authority.json' if authority else None,
            access_interpretation_manifest=older / 'contact_source_interpretation.json',
            creator_interpretation_manifest=older / 'exxon_citation_interpretation.json',
            dataset_access_interpretation_manifest=DOCS / 'finite_source_resource_access_596.json',
            contributor_access_interpretation_manifest=older / 'contributor_source_interpretation.json',
            collective_creator_interpretation_manifest=previous / 'dfo_staff_citation_interpretation.json',
            institution_creator_interpretation_manifest=DOCS / 'source_citation_credits_412.json',
            source_link_interpretation_manifest=previous / 'historical_dataset_linkage_21.json',
            source_title_interpretation_manifest=titles,
            source_scope_attestation_manifest=previous / 'source_scope_reconciliation_904.json',
        )
        paths = OutputPaths(str(Path(tmp) / 'output'), 'sandbox')
        payloads = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                    for sid in (SID, 'FGDC-621', 'FGDC-4063')}
        return report, paths, payloads

    def test_additive_profile_and_exact_work_words_full_citation_preservation(self):
        old, new = read_json(PREVIOUS), read_json(NEW)
        self.assertEqual(new['members'][:35], old['members'])
        self.assertEqual(len(new['members']), 36)
        self.assertEqual(new['prior_manifest_sha256'], reference(PREVIOUS)['manifest_sha256'])
        self.assertEqual(reference(NEW)['manifest_sha256'], interpretation.TITLE233_MANIFEST_SHA256)
        self.assertEqual(self.member['source_id'], SID)
        self.assertEqual(self.member['display_title'], self.proposal['proposed_display_title'])
        self.assertEqual(len(self.member['display_title']), 250)
        self.assertEqual('91-08 ' + self.member['display_title'] + '.',
                         self.proposal['complete_normalized_work_title_clause'])
        self.assertIn(self.proposal['original_complete_citation_title_verbatim'],
                      self.member['preservation_note'])
        self.assertEqual(self.member['preservation_note'], self.proposal['required_preservation_note'])
        for member in new['members']:
            sid = member['source_id']
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            root = ET.fromstring(raw)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
            self.assertEqual(interpretation.validate_source_title_interpretation(
                reference(NEW), sid, member['source_sha256'], root), member)
            if sid != SID:
                self.assertEqual(interpretation.validate_source_title_interpretation(
                    reference(PREVIOUS), sid, member['source_sha256'], root), member)

    def test_current_before_after_repeat_withdrawal_and_controls_preserve_whole_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            before_report, _, before = self.prepared(tmp, PREVIOUS)
            after_report, paths, after = self.prepared(tmp)
            repeat_report, _, repeat = self.prepared(tmp)
            withdrawn_report, _, withdrawn = self.prepared(tmp, PREVIOUS)
            self.assertEqual(before_report['summary']['source_status_counts'],
                             {'supported': 1, 'held': 2, 'failed': 0})
            self.assertEqual(after_report['summary']['source_status_counts'],
                             {'supported': 2, 'held': 1, 'failed': 0})
            self.assertEqual(after_report, repeat_report)
            self.assertEqual(after, repeat)
            self.assertEqual(before_report, withdrawn_report)
            self.assertEqual(before, withdrawn)
            self.assertEqual(before[SID]['metadata'], self.proposal['baseline_complete_raw_metadata'])
            self.assertEqual(after[SID]['metadata'], self.proposal['projected_after_complete_raw_metadata'])
            for sid in before:
                old, new = before[sid], after[sid]
                stripped = copy.deepcopy(new)
                if sid == SID:
                    self.assertEqual(stripped['artifact_policy'].pop('source_title_interpretation'), reference(NEW))
                    stripped['metadata'] = copy.deepcopy(old['metadata'])
                elif sid == 'FGDC-621':
                    self.assertEqual(new['metadata'], old['metadata'])
                    self.assertEqual(stripped['artifact_policy']['source_title_interpretation'], reference(NEW))
                    stripped['artifact_policy']['source_title_interpretation'] = reference(PREVIOUS)
                self.assertEqual(stripped, old)
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(),
                                 (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            for row in after_report['records']:
                self.assertFalse(row['remote_verified'])
                self.assertFalse(row['publication_approved'])

    def test_exact_source_ref_before_and_after_metadata_guards(self):
        raw = (REPO / 'FGDC' / (SID + '.xml')).read_bytes()
        root = ET.fromstring(raw)
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(source_element(root.find('./idinfo/citation/citeinfo/title')),
                         self.member['title_element'])
        for sid, digest in ((SID, '0' * 64), ('FGDC-4063', sha)):
            with self.assertRaises(ValueError):
                interpretation.validate_source_title_interpretation(reference(NEW), sid, digest, root)
        changed = copy.deepcopy(root)
        changed.find('./idinfo/citation/citeinfo/title').set('inferred', 'true')
        with self.assertRaises(ValueError):
            interpretation.validate_source_title_interpretation(reference(NEW), SID, sha, changed)
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / 'missing.json'
            forged = Path(tmp) / 'forged.json'
            forged.write_bytes(NEW.read_bytes() + b' ')
            for path in (missing, forged):
                ref = {'manifest_path': str(path), 'manifest_sha256': reference(NEW)['manifest_sha256']}
                with self.assertRaises(ValueError):
                    interpretation.validate_source_title_interpretation(ref, SID, sha, root)
            modified = read_json(NEW)
            modified['members'][-1]['display_title'] = 'Invented'
            atomic_json(forged, modified)
            with self.assertRaises(ValueError):
                interpretation.validate_source_title_interpretation(reference(forged), SID, sha, root)
        before = self.proposal['baseline_complete_raw_metadata']
        after = interpretation.apply_source_title_interpretation(self.member, before)
        self.assertEqual(fingerprint(before), self.member['metadata_before_sha256'])
        self.assertEqual(fingerprint(after), self.member['metadata_after_sha256'])
        for field in ('title', 'notes', 'creators', 'publication_date', 'license', 'related_identifiers'):
            for metadata, function in ((before, lambda m: interpretation.apply_source_title_interpretation(self.member, m)),
                                       (after, lambda m: interpretation.validate_source_title_policy(
                                           {'source_title_interpretation': reference(NEW)}, SID, sha, root, m))):
                altered = copy.deepcopy(metadata)
                altered[field] = 'Discarded source context'
                with self.subTest(field=field), self.assertRaises(ValueError):
                    function(altered)

    def test_agent_and_both_human_schemas_reject_withdrawal_tampering_and_missing_authority(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, prepare_manifest, validate_approval

        with tempfile.TemporaryDirectory() as tmp:
            _, paths, payloads = self.prepared(tmp)
            path = Path(paths.zenodo_json_dir) / (SID + '.json')
            payload = payloads[SID]
            assess_source(str(path), paths)
            metadata, source, source_sha = prepare_metadata(str(path), paths)
            entry = {'environment': 'sandbox', 'zenodo_url': 'https://sandbox.zenodo.org/deposit/123',
                     'deposition_id': 123, 'upload_status': 'success', 'publish_status': 'draft',
                     'success': True, 'json_file': str(path), 'source_sha256': source_sha,
                     'metadata_sha256': metadata_hash(metadata), 'artifact_contract': prepare_artifact(payload, source)}
            atomic_json(paths.uploads_registry_path, {SID: entry})
            manifest = prepare_manifest(paths)
            record = manifest['records'][0]
            record['qa'].update(approved=True, reviewer_type='human', reviewer='Offline fixture',
                                reviewed_at=self.reviewed_at, rationale='Fixture only', checks=dict.fromkeys(QA_CHECKS, True),
                                run_id='fixture', review_revision=manifest['source_revision'], evidence=['fixture'])
            record['duplicate_review'].update(status='reviewed', classification='checked_no_match',
                                              rationale='Fixture only', evidence=['fixture'])
            for schema in (1, 2):
                manifest['schema_version'] = schema
                self.assertTrue(validate_approval(manifest, SID, entry, paths, metadata)['qa']['approved'])
                for fault in ('withdraw', 'notes', 'title', 'creator', 'rights', 'authority'):
                    changed = copy.deepcopy(payload)
                    if fault == 'withdraw':
                        changed['artifact_policy'].pop('source_title_interpretation')
                    elif fault == 'authority':
                        changed['artifact_policy'].pop('rehosting_authority')
                    elif fault == 'creator':
                        changed['metadata']['creators'] = [{'name': 'Invented'}]
                    elif fault == 'rights':
                        changed['metadata']['license'] = 'cc-by-4.0'
                    else:
                        changed['metadata'][fault] = 'Discarded source context'
                    atomic_json(path, changed)
                    with self.subTest(schema=schema, fault=fault), self.assertRaises(ValueError):
                        assess_source(str(path), paths)
                    with self.subTest(schema=schema, fault=fault), self.assertRaises(ValueError):
                        validate_approval(manifest, SID, entry, paths, metadata)
                    atomic_json(path, payload)
            report, _, _ = self.prepared(tmp, authority=False)
            row = next(row for row in report['records'] if row['source_id'] == SID)
            self.assertEqual(row['source_status'], 'held')
            self.assertEqual(row['rehosting_authority'], 'not_established')
