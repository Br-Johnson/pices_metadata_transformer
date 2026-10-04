"""Exact two-report reconciliation preserves earlier reviews and all source bytes."""

import copy
import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import dataset_access_interpretation as interpretation
from scripts.upload_service import read_json
from tests import test_resource_scope_reconciliation as previous

REPO, DOCS = previous.REPO, previous.DOCS
OLD = DOCS / 'finite_source_resource_access_556.json'
NEW = DOCS / 'finite_source_resource_access_558.json'
NEW_SHA = 'a9dee2d1191eab69d85a20e3a3c856b9e56eec7283e024a50db91974cdd316a0'
MEMBERS = read_json(NEW)['members'][556:]
IDS = {'FGDC-885', 'FGDC-887'}


class NPAFCReport2Tests(unittest.TestCase):
    prepared = previous.ResourceScopeReconciliationTests.prepared
    human_routes = previous.ResourceScopeReconciliationTests.human_routes

    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def classify(self, tmp, ids, profile=NEW, authority=True):
        return self.prepared(tmp, ids, authority=authority, replacements={
            'dataset_access_interpretation_manifest': profile,
            'source_scope_attestation_manifest': previous.SCOPE_NEW})

    def validate(self, member, profile=NEW, root=None, stamp=None):
        if root is None:
            root = ET.parse(REPO / 'FGDC' / (member['source_id'] + '.xml')).getroot()
        return interpretation.validate_dataset_access_interpretation(
            previous.reference(profile), **member, root=root,
            reviewed_at=self.reviewed_at if stamp is None else stamp)

    def test_additive_profile_preserves_every_prior_object_and_review_time(self):
        old, new = read_json(OLD), read_json(NEW)
        self.assertEqual(hashlib.sha256(NEW.read_bytes()).hexdigest(), NEW_SHA)
        self.assertEqual(len(new['members']), 558)
        self.assertEqual({m['source_id'] for m in MEMBERS}, IDS)
        self.assertEqual(new['members'][:556], old['members'])
        self.assertEqual(new['source_contexts'], old['source_contexts'])
        for sid, context in old['acquisition_contexts'].items():
            self.assertEqual(context, new['acquisition_contexts'][sid])
        for key in ('remaining_source_review', 'cnf_copy_media_review',
                    'resource_confidentiality_review', 'resource_reconciliation_review'):
            self.assertEqual(new[key], old[key])
        self.assertFalse(IDS.intersection(m['source_id'] for m in read_json(previous.SCOPE_NEW)['members']))
        earlier = '2026-10-04T06:00:00+00:00'
        for index in (0, 263, 264, 468, 469, 490, 491, 513, 514, 555):
            member = old['members'][index]
            self.assertEqual(self.validate(member, stamp=earlier),
                             self.validate(member, OLD, stamp=earlier))
        for member in MEMBERS:
            with self.assertRaises(ValueError):
                self.validate(member, stamp=earlier)
        with patch.object(interpretation, 'NPAFC_REPORT_MANIFEST_SHA256', 'unaccepted'):
            with self.assertRaises(ValueError):
                self.validate(MEMBERS[0])

    def test_exact_hash_context_constraints_and_timing_fail_closed(self):
        for member in MEMBERS:
            raw = (REPO / 'FGDC' / (member['source_id'] + '.xml')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
            result = self.validate(member)
            self.assertEqual(result['status'], 'REVIEWER_RECONCILED')
            self.assertEqual(result['reconciliation_reviewed_at'],
                             read_json(NEW)['npafc_report_notification_review']['reviewed_at'])
            for name in ('new_user_attestation_event', 'original_direct_question_membership_enlarged',
                         'underlying_data_rights_granted', 'grants_rehosting', 'grants_new_license', 'publication_approved'):
                self.assertFalse(result[name])
            with self.assertRaises(ValueError):
                self.validate({**member, 'source_sha256': '0' * 64})
            for xpath in ('./idinfo/accconst', './idinfo/useconst', './metainfo/metac',
                          './metainfo/metuc', './idinfo/descript/abstract', './distinfo/distliab'):
                changed = ET.fromstring(raw)
                changed.find(xpath).text = 'Changed source context'
                with self.subTest(source=member['source_id'], xpath=xpath), self.assertRaises(ValueError):
                    self.validate(member, root=changed)
            for stamp in ('', '2026-10-04T06:00:00Z', '2026-10-04T07:00:00', '2099-01-01T00:00:00Z'):
                with self.assertRaises(ValueError):
                    self.validate(member, stamp=stamp)

    def test_original_statement_evidence_remains_a_live_dependency(self):
        original_read = Path.read_bytes
        for evidence in read_json(NEW)['npafc_report_notification_review']['original_statement_references']:
            target = REPO / evidence['manifest_path']
            def altered(path, _target=target):
                return original_read(path) + b' ' if path == _target else original_read(path)
            with patch.object(Path, 'read_bytes', altered):
                self.assertEqual(interpretation.dataset_access_member_ids(previous.reference(NEW)), frozenset())
                with self.assertRaises(ValueError):
                    self.validate(MEMBERS[0])

    def test_measured_two_delta_preserves_complete_payload_repeat_and_withdrawal(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.classify(tmp, IDS, OLD)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 2, 'failed': 0})
            payloads = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json')) for sid in IDS}
            after, paths = self.classify(tmp, IDS)
            self.assertEqual(after['summary']['source_status_counts'], {'supported': 2, 'held': 0, 'failed': 0})
            for row in after['records']:
                sid = row['source_id']
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                stripped = copy.deepcopy(payload)
                stripped['artifact_policy'].pop('dataset_access_interpretation')
                self.assertEqual(stripped, payloads[sid])
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertEqual(row['dataset_access_interpretation'], 'REVIEWER_RECONCILED')
                self.assertFalse(row['remote_verified'] or row['publication_approved'])
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(),
                                 (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            self.assertEqual(after, self.classify(tmp, IDS)[0])
            self.assertEqual(before, self.classify(tmp, IDS, OLD)[0])

    def test_missing_authority_forged_profile_and_other_holds_remain_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            held, _ = self.classify(tmp, IDS, authority=False)
            self.assertTrue(all(r['source_status'] == 'held' for r in held['records']))
            forged = Path(tmp) / 'forged.json'
            forged.write_bytes(NEW.read_bytes() + b' ')
            held, _ = self.classify(tmp, IDS, forged)
            self.assertTrue(all(r['source_status'] == 'held' for r in held['records']))
            controls = {'FGDC-563', 'FGDC-1318', 'FGDC-1864'}
            self.assertFalse(controls.intersection(interpretation.dataset_access_member_ids(previous.reference(NEW))))
            held, _ = self.classify(tmp, controls)
            self.assertTrue(all(r['source_status'] == 'held' for r in held['records']))

    def test_agent_and_both_human_routes_preserve_rights_and_authority_gates(self):
        for sid in sorted(IDS):
            self.human_routes(sid, 'dataset_access_interpretation', NEW)

    def test_cached_accounting_changes_only_the_two_measured_records(self):
        old = read_json(DOCS / 'resource_reconciliation_integrated_source_status.json')
        new = read_json(DOCS / 'npafc_report2_integrated_source_status.json')
        delta = read_json(DOCS / 'npafc_report2_bounded_delta.json')
        before = {row['source_id']: row for row in old['records']}
        after = {row['source_id']: row for row in new['records']}
        self.assertEqual(len(before), 4206)
        self.assertEqual(set(before), set(after))
        self.assertEqual({sid for sid in before if before[sid] != after[sid]}, IDS)
        self.assertEqual({r['source_id'] for r in delta['rows']}, IDS)
        for row in delta['rows']:
            sid = row['source_id']
            self.assertEqual(before[sid]['source_status'], 'held')
            self.assertEqual(after[sid], {**before[sid], 'source_status': 'supported', 'evidence': 'measured_npafc_report2'})
            self.assertEqual(row['provenance'], 'REVIEWER_RECONCILED')
            self.assertTrue(row['complete_raw_metadata_unchanged'] and row['original_and_copied_XML_unchanged'])
        self.assertEqual(Counter(r['source_status'] for r in after.values()),
                         {'supported': 3640, 'held': 560, 'failed': 6})
        self.assertTrue(all(after[sid]['source_status'] == 'held' for sid in old['held31_exception_ids']))
        for filename, digest in new['input_sha256'].items():
            self.assertEqual(hashlib.sha256((DOCS / filename).read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
