"""Exact42 reviewer reconciliation, live provenance and unchanged old profiles."""

import copy
import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import dataset_access_interpretation as interpretation
from scripts.upload_service import read_json
from tests import test_resource_scope_reconciliation as previous

REPO = previous.REPO
DOCS = previous.DOCS
OLD = DOCS / 'finite_source_resource_access_514.json'
NEW = DOCS / 'finite_source_resource_access_556.json'
NEW_SHA = '81c719c546146eb7ad39e04db115710747935df6cb142aaf5854127bf8ddcc6a'
MEMBERS = read_json(NEW)['members'][514:]
IDS = {m['source_id'] for m in MEMBERS}


class Resource42Tests(unittest.TestCase):
    prepared = previous.ResourceScopeReconciliationTests.prepared
    human_routes = previous.ResourceScopeReconciliationTests.human_routes

    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def classify(self, tmp, ids, profile=NEW, scope=previous.SCOPE_NEW, authority=True):
        return self.prepared(tmp, ids, authority=authority,
                             replacements={'dataset_access_interpretation_manifest': profile,
                                           'source_scope_attestation_manifest': scope})

    def test_profile_acceptance_requires_new_pin_and_preserves_every_old_member_and_context(self):
        old, new = read_json(OLD), read_json(NEW)
        self.assertEqual(hashlib.sha256(NEW.read_bytes()).hexdigest(), NEW_SHA)
        self.assertEqual(new['members'][:514], old['members'])
        self.assertEqual(new['source_contexts'], old['source_contexts'])
        for sid, context in old['acquisition_contexts'].items():
            self.assertEqual(context, new['acquisition_contexts'][sid])
        self.assertEqual(len(new['members']), 556)
        self.assertEqual(len(IDS), 42)
        self.assertFalse(IDS.intersection(m['source_id'] for m in old['members']))
        self.assertFalse(IDS.intersection(m['source_id'] for m in read_json(previous.SCOPE_NEW)['members']))
        member = MEMBERS[0]
        root = ET.parse(REPO / 'FGDC' / (member['source_id'] + '.xml')).getroot()
        with patch.object(interpretation, 'RESOURCE_RECONCILIATION_MANIFEST_SHA256', 'unaccepted-predecessor'):
            with self.assertRaises(ValueError):
                interpretation.validate_dataset_access_interpretation(previous.reference(NEW), **member, root=root, reviewed_at=self.reviewed_at)
        result = interpretation.validate_dataset_access_interpretation(previous.reference(NEW), **member, root=root, reviewed_at=self.reviewed_at)
        self.assertEqual(result['status'], 'REVIEWER_RECONCILED')

    def test_all42_exact_roots_and_timing_have_distinct_provenance_without_new_rights(self):
        for member in MEMBERS:
            sid = member['source_id']
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
            root = ET.fromstring(raw)
            result = interpretation.validate_dataset_access_interpretation(previous.reference(NEW), **member, root=root, reviewed_at=self.reviewed_at)
            self.assertEqual(result['status'], 'REVIEWER_RECONCILED')
            for name in ('new_user_attestation_event', 'original_direct_question_membership_enlarged',
                         'underlying_data_rights_granted', 'grants_rehosting', 'grants_new_license', 'publication_approved'):
                self.assertFalse(result[name])
            changed = copy.deepcopy(root)
            changed.find('./idinfo/descript/abstract').text = 'changed complete context'
            with self.assertRaises(ValueError):
                interpretation.validate_dataset_access_interpretation(previous.reference(NEW), **member, root=changed, reviewed_at=self.reviewed_at)
        for stamp in (None, '2026-10-04T00:00:00Z', '2026-10-04T01:00:00', '2099-01-01T00:00:00Z'):
            with self.assertRaises(ValueError):
                interpretation.validate_dataset_access_interpretation(previous.reference(NEW), **MEMBERS[0],
                                                                     root=ET.parse(REPO / 'FGDC' / (MEMBERS[0]['source_id'] + '.xml')).getroot(), reviewed_at=stamp)
        old = read_json(OLD)['members'][491]
        result = interpretation.validate_dataset_access_interpretation(previous.reference(NEW), **old,
                    root=ET.parse(REPO / 'FGDC' / (old['source_id'] + '.xml')).getroot())
        self.assertEqual(result['status'], 'SOURCE_BACKED')

    def test_five_original_statement_files_are_live_dependencies(self):
        original_read = Path.read_bytes
        for evidence in read_json(NEW)['resource_reconciliation_review']['original_statement_references']:
            target = REPO / evidence['manifest_path']
            def altered(path, _target=target):
                return original_read(path) + b' ' if path == _target else original_read(path)
            with patch.object(Path, 'read_bytes', altered):
                self.assertEqual(interpretation.dataset_access_member_ids(previous.reference(NEW)), frozenset())
                with self.assertRaises(ValueError):
                    interpretation.validate_dataset_access_interpretation(previous.reference(NEW), **MEMBERS[0],
                        root=ET.parse(REPO / 'FGDC' / (MEMBERS[0]['source_id'] + '.xml')).getroot(), reviewed_at=self.reviewed_at)

    def test_ten_then_exact42_actual_delta_raw_preservation_repeat_and_withdrawal(self):
        with tempfile.TemporaryDirectory() as tmp:
            ten, _ = self.classify(tmp, set(sorted(IDS)[:9] + ['FGDC-4060']))
            self.assertEqual(ten['summary']['source_status_counts'], {'supported': 10, 'held': 0, 'failed': 0})
            before, paths = self.classify(tmp, IDS, OLD)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 42, 'failed': 0})
            metadata = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))['metadata'] for sid in IDS}
            after, paths = self.classify(tmp, IDS)
            self.assertEqual(after['summary']['source_status_counts'], {'supported': 42, 'held': 0, 'failed': 0})
            for row in after['records']:
                sid = row['source_id']
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                self.assertEqual(payload['metadata'], metadata[sid])
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertEqual(row['dataset_access_interpretation'], 'REVIEWER_RECONCILED')
                self.assertFalse(row['remote_verified'] or row['publication_approved'])
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(), (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            repeated, _ = self.classify(tmp, IDS)
            self.assertEqual(after, repeated)
            withdrawn, _ = self.classify(tmp, IDS, OLD)
            self.assertEqual(before, withdrawn)

    def test_agent_and_both_human_routes_resource_condition_and_actual_disclaimer(self):
        for sid in ('FGDC-112', 'FGDC-4060'):
            self.human_routes(sid, 'dataset_access_interpretation', NEW)

    def test_missing_authority_forged_profile_and_unrelated_controls_stay_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            held, _ = self.classify(tmp, {'FGDC-112', 'FGDC-4060'}, authority=False)
            self.assertTrue(all(r['source_status'] == 'held' for r in held['records']))
            forged = Path(tmp) / 'forged.json'
            forged.write_bytes(NEW.read_bytes() + b' ')
            held, _ = self.classify(tmp, {'FGDC-112', 'FGDC-4060'}, forged)
            self.assertTrue(all(r['source_status'] == 'held' for r in held['records']))
            for sid in ('FGDC-1318', 'FGDC-1771', 'FGDC-1864'):
                self.assertNotIn(sid, interpretation.dataset_access_member_ids(previous.reference(NEW)))


if __name__ == '__main__':
    unittest.main()
