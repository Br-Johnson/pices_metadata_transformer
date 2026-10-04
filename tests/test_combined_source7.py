"""Combined finite profiles preserve both reviews, source bytes and QA gates."""

import hashlib
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import dataset_access_interpretation as interpretation
from scripts.upload_service import read_json
from tests import test_npafc_report2_reconciliation as pair
from tests import test_residual_source_access as five

REPO = pair.REPO
DOCS = REPO / 'docs/readiness/2026-10-04'
NEW = DOCS / 'finite_source_resource_access_563.json'
IDS = pair.IDS | five.IDS


class CombinedSource7Tests(unittest.TestCase):
    prepared = pair.NPAFCReport2Tests.prepared
    classify = pair.NPAFCReport2Tests.classify
    human_routes = pair.NPAFCReport2Tests.human_routes

    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def test_every_previous_interpretation_and_exact_review_block_is_preserved(self):
        combined = read_json(NEW)
        self.assertEqual(len(combined['members']), 563)
        self.assertEqual(len({m['source_id'] for m in combined['members']}), 563)
        self.assertEqual({m['source_id'] for m in combined['members'][556:]}, IDS)
        self.assertEqual(hashlib.sha256(NEW.read_bytes()).hexdigest(),
                         interpretation.COMBINED_SOURCE_MANIFEST_SHA256)
        for old_path, review in ((pair.NEW, 'npafc_report_notification_review'),
                                 (five.NEW, 'residual_source_review')):
            old = read_json(old_path)
            self.assertEqual(combined[review], old[review])
            self.assertEqual(combined['resource_reconciliation_review'], old['resource_reconciliation_review'])
            self.assertEqual(combined['source_contexts'], old['source_contexts'])
            for sid, value in old['acquisition_contexts'].items():
                self.assertEqual(combined['acquisition_contexts'][sid], value)
            # Compare shared 556 once, then each disjoint addition.
            members = old['members'] if old_path == pair.NEW else old['members'][556:]
            for member in members:
                root = ET.parse(REPO / 'FGDC' / (member['source_id'] + '.xml')).getroot()
                kwargs = {**member, 'root': root, 'reviewed_at': self.reviewed_at}
                self.assertEqual(
                    interpretation.validate_dataset_access_interpretation(five.REFERENCE(NEW), **kwargs),
                    interpretation.validate_dataset_access_interpretation(five.REFERENCE(old_path), **kwargs))

    def test_separate_review_times_and_live_evidence_cannot_fall_back(self):
        profile = read_json(NEW)
        for key in ('npafc_report_notification_review', 'residual_source_review'):
            review = profile[key]
            too_early = (datetime.fromisoformat(review['reviewed_at']) - timedelta(seconds=1)).isoformat()
            for member in review['members']:
                root = ET.parse(REPO / 'FGDC' / (member['source_id'] + '.xml')).getroot()
                with self.assertRaises(ValueError):
                    interpretation.validate_dataset_access_interpretation(
                        five.REFERENCE(NEW), **member, root=root, reviewed_at=too_early)
        original_read = Path.read_bytes
        refs = {e['manifest_path'] for key in interpretation.REVIEW_BLOCKS if key in profile
                for e in profile[key]['original_statement_references']}
        for relative in refs:
            target = REPO / relative
            def altered(path, _target=target):
                return original_read(path) + b' ' if path == _target else original_read(path)
            with patch.object(Path, 'read_bytes', altered):
                self.assertEqual(interpretation.dataset_access_member_ids(five.REFERENCE(NEW)), frozenset())
        with patch.object(interpretation, 'COMBINED_SOURCE_MANIFEST_SHA256', 'unaccepted'):
            self.assertEqual(interpretation.dataset_access_member_ids(five.REFERENCE(NEW)), frozenset())

    def test_measured_seven_delta_reproduces_committed_counts_and_preservation(self):
        spec = importlib.util.spec_from_file_location('combined_source7_validation', DOCS / 'validate_combined_source7.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            result = module.validate(Path(tmp), self.reviewed_at)
            actual = read_json(Path(tmp) / 'integrated_source_status.json')
        saved = read_json(DOCS / 'combined_source7_integrated_source_status.json')
        self.assertEqual(actual['records'], saved['records'])
        self.assertEqual(result['measured_promotions'], 7)
        self.assertEqual(result['combined_counts_computed'], {'supported': 3645, 'held': 555, 'failed': 6})
        self.assertTrue(result['all4206_original_xml_sha256_verified_before_and_after'])
        self.assertTrue(result['all456_alias_identities_and31_exceptions_still_held'])
        before = {r['source_id']: r for r in read_json(module.LEDGER)['records']}
        self.assertEqual({r['source_id'] for r in actual['records'] if r != before[r['source_id']]}, IDS)
        self.assertEqual(Counter(r['source_status'] for r in saved['records']), result['combined_counts_computed'])
        saved_delta = read_json(DOCS / 'combined_source7_validation.json')
        self.assertEqual(saved['combined_validation_canonical_sha256'], module.digest(module.canonical(saved_delta)))
        self.assertEqual(saved['per_source_status_sha256'], module.digest(module.canonical(saved['records'])))

    def test_combined_profile_agent_and_both_human_routes_preserve_authority_and_rights(self):
        for sid in sorted(IDS):
            self.human_routes(sid, 'dataset_access_interpretation', NEW)


if __name__ == '__main__':
    unittest.main()
