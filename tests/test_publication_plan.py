"""Offline publication plans cannot authorize uploads or erase identity uncertainty."""

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publication_plan as planner

REPO = Path(__file__).resolve().parents[1]


class PublicationPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = planner.build_plan(REPO)
        cls.rows = {row['record_target_id']: row for row in cls.plan['targets']}
        cls.documents, cls.bindings = planner._read_inputs(REPO)

    def snapshot(self, *entries):
        return {'schema_version': 1, 'kind': 'sanitized_offline_publication_restart_snapshot',
                'environment': 'production',
                'publication_inputs_sha256': self.plan['publication_inputs_sha256'],
                'entries': list(entries)}

    def entry(self, tid='FGDC-1', **changes):
        return {'record_target_id': tid, 'source_sha256': self.rows[tid]['source_sha256'],
                'environment': 'production', 'deposition_id': 99999991, 'doi': None,
                'needs_reconciliation': False, 'upload_status': 'pending',
                'publish_status': 'draft', 'metadata_sha256': 'a' * 64,
                'artifact_contract_sha256': 'b' * 64, **changes}

    def validate(self, snapshot):
        return planner.validate_restart_snapshot(snapshot, self.plan['publication_inputs_sha256'], self.rows)

    def test_complete_membership_whole_pair_batches_and_source_exclusions(self):
        rows = self.plan['targets']
        self.assertEqual(len(rows), 3978)
        ids = [sid for row in rows for sid in row['source_ids']]
        self.assertEqual(len(ids), 4206)
        self.assertEqual(len(set(ids)), 4206)
        paired = [row for row in rows if len(row['source_ids']) == 2]
        self.assertEqual(len(paired), 228)
        paired_ids = {sid for row in paired for sid in row['source_ids']}
        self.assertFalse(paired_ids.intersection(self.rows))
        planned = [tid for batch in self.plan['prospective_batches'] for tid in batch['record_target_ids']]
        self.assertEqual(len(planned), 3933)
        self.assertEqual(len(set(planned)), 3933)
        self.assertTrue(all(len(batch['record_target_ids']) <= 10 for batch in self.plan['prospective_batches']))
        self.assertEqual(sum(batch['original_file_count'] for batch in self.plan['prospective_batches']), 4161)
        held = [row for row in rows if row['source_semantic_status'] != 'supported']
        self.assertEqual(len(held), 45)
        self.assertEqual(sum(row['source_semantic_status'] == 'failed' for row in held), 6)
        self.assertFalse(set(planned).intersection(row['record_target_id'] for row in held))
        self.assertTrue(all(row['source_question_reference']['source_id'] == row['record_target_id'] for row in held))

    def test_identity_evidence_never_becomes_global_absence_or_live_authority(self):
        self.assertEqual(self.plan['protected_existing_imports'], self.documents['prior_identity']['protected_existing_imports'])
        self.assertEqual(self.plan['class_artifact_resolvers'], self.documents['target_projection']['class_assessment_scopes'])
        for row in self.plan['targets']:
            self.assertFalse(row['executable'] or row['publication_approved'] or row['upload_eligible'] or row['remote_verified'])
            self.assertEqual(row['provider_actions'], [])
            self.assertIsNone(row['provider_action_grant'])
            self.assertFalse(row['restart']['safe_to_retry'])
            self.assertIn('missing_state', row['restart']['disposition'])
        pairs = [row for row in self.plan['targets'] if len(row['source_ids']) == 2]
        self.assertTrue(all('reported_zero' in row['identity_decision']['decision'] for row in pairs))
        self.assertTrue(all(row['identity_decision']['production_record_id'] is None for row in pairs))
        self.assertEqual(sum(bool(row['identity_decision']['title_hints_not_identity']) for row in pairs), 2)
        self.assertIn('not_assessed', self.rows['FGDC-1']['identity_decision']['decision'])
        for old in self.plan['protected_existing_imports']:
            current = self.rows[old['source_id']]['identity_decision']
            self.assertEqual((current['production_record_id'], current['production_doi']), (old['record_id'], old['doi']))
        self.assertEqual(self.plan['owner_inventory']['reported_get_count'], 42)
        self.assertFalse(self.plan['artifact_requirements']['new_license_inferred'])
        self.assertEqual(self.plan['artifact_requirements']['required_xml_access'], 'restricted')

    def test_repeat_is_exact_and_limits_reject_partial_or_oversized_batches(self):
        self.assertEqual(planner.build_plan(REPO), self.plan)
        for invalid in (0, 11, True, 1.5):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                planner.build_plan(REPO, batch_size=invalid)
        copy_plan = copy.deepcopy(self.plan)
        saved = copy_plan.pop('plan_sha256')
        self.assertEqual(planner.digest(copy_plan), saved)

    def test_original_and_pinned_evidence_tampering_fails_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'FGDC').mkdir()
            path = root / 'FGDC/FGDC-1.xml'
            raw = b'<metadata>original</metadata>'
            path.write_bytes(raw)
            sources = {'FGDC-1': {'source_sha256': hashlib.sha256(raw).hexdigest()}}
            descriptor = planner._originals(root, sources)['FGDC-1']
            self.assertEqual(descriptor['size'], len(raw))
            self.assertEqual(path.read_bytes(), raw)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Original source changed'):
                planner._originals(root, sources)
            self.assertEqual(path.read_bytes(), b'changed')
            source_name = planner.PINS['source_ledger'][0]
            evidence = root / planner.D04 / source_name
            evidence.parent.mkdir(parents=True)
            evidence.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Pinned evidence changed'):
                planner._read_inputs(root)

    def test_restart_exports_reject_stale_foreign_unknown_and_forged_approval(self):
        good = self.snapshot(self.entry())
        self.assertEqual(len(self.validate(good)[0]), 1)
        bad_cases = []
        for key, value in [('publication_inputs_sha256', '0' * 64), ('environment', 'sandbox')]:
            item = copy.deepcopy(good)
            item[key] = value
            bad_cases.append(item)
        for key, value in [('source_sha256', '0' * 64), ('record_target_id', 'FGDC-99999'),
                           ('deposition_id', True), ('needs_reconciliation', 0),
                           ('upload_status', 'ready_to_create')]:
            item = copy.deepcopy(good)
            item['entries'][0][key] = value
            bad_cases.append(item)
        forged = copy.deepcopy(good)
        forged['entries'][0]['publication_approved'] = True
        bad_cases.append(forged)
        bad_cases.append(self.snapshot(self.entry(), self.entry()))
        for item in bad_cases:
            with self.subTest(snapshot=item), self.assertRaises(ValueError):
                self.validate(item)

    def test_uncertain_partial_published_and_missing_state_remain_nonexecutable(self):
        cases = [
            (None, 'hold_missing_state'),
            (self.entry(needs_reconciliation=True), 'hold_uncertain_create'),
            (self.entry(deposition_id=None), 'hold_missing_identity'),
            (self.entry(metadata_sha256=None), 'hold_missing_payload'),
            (self.entry(upload_status='unknown'), 'hold_unknown_legacy_status'),
            (self.entry(), 'reported_partial_draft'),
            (self.entry(upload_status='success'), 'reported_same_draft'),
            (self.entry(publish_status='published'), 'preserve_reported_published'),
            (self.entry(publish_status='published', deposition_id=None), 'hold_missing_identity'),
            (self.entry(publish_status='published', needs_reconciliation=True), 'hold_uncertain_create'),
        ]
        for entry, expected in cases:
            with self.subTest(expected=expected):
                result = planner._restart_report(entry, None, set(), set())
                self.assertTrue(result['disposition'].startswith(expected))
                self.assertFalse(result['safe_to_retry'])
                self.assertEqual(result['reported_entry'], entry)

    def test_provider_identity_conflicts_and_exclusions_survive_restart_hints(self):
        snapshot = self.snapshot(self.entry('FGDC-1'), self.entry('FGDC-2'),
                                 self.entry('FGDC-3', deposition_id=17317855),
                                 self.entry('FGDC-4', deposition_id=10042430),
                                 self.entry('FGDC-5', deposition_id=99999995, doi='10.5281/ZENODO.17317855'),
                                 self.entry('FGDC-6', deposition_id=99999996, doi='10.1234/duplicate'),
                                 self.entry('FGDC-7', deposition_id=99999997, doi='10.1234/DUPLICATE'),
                                 self.entry('FGDC-1238', deposition_id=17317855, doi='10.5281/zenodo.999'))
        plan = planner.build_plan(REPO, restart_snapshot=snapshot)
        rows = {row['record_target_id']: row for row in plan['targets']}
        for sid in ('FGDC-1', 'FGDC-2', 'FGDC-3', 'FGDC-1238'):
            self.assertIn('shared_by_multiple', rows[sid]['restart']['disposition'])
        self.assertIn('reserved', rows['FGDC-4']['restart']['disposition'])
        self.assertIn('doi_reserved', rows['FGDC-5']['restart']['disposition'])
        for sid in ('FGDC-6', 'FGDC-7'):
            self.assertIn('doi_shared_by_multiple', rows[sid]['restart']['disposition'])
        self.assertEqual(rows['FGDC-7']['restart']['reported_entry']['doi'], '10.1234/DUPLICATE')
        original = self.plan['protected_existing_imports']
        self.assertEqual(plan['protected_existing_imports'], original)
        old = next(item for item in original if item['source_id'] == 'FGDC-1238')
        report = planner._restart_report(snapshot['entries'][-1], old, set(), set())
        self.assertIn('conflict_with_protected', report['disposition'])
        same = self.entry('FGDC-1238', deposition_id=17317855, doi='10.5281/ZENODO.17317855')
        report = planner._restart_report(same, old, set(), set())
        self.assertIn('reported_partial_draft', report['disposition'])
        self.assertEqual(report['reported_entry']['doi'], same['doi'])
        self.assertTrue(all(not row['executable'] for row in rows.values()))

    def test_projection_membership_cannot_split_or_drop_a_pair(self):
        bad = copy.deepcopy(self.documents)
        bad['target_projection']['class_targets'][0]['source_ids'].pop()
        with patch.object(planner, '_read_inputs', return_value=(bad, self.bindings)):
            with self.assertRaisesRegex(ValueError, 'Overlapping or split'):
                planner.build_plan(REPO)


if __name__ == '__main__':
    unittest.main()
