"""Finite paired wire preparation preserves originals and closed execution gates."""

import copy
import html
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts import content_class_targets as classes
from scripts import modern_content_class as mapping
from scripts import modern_publication as publication
from scripts import modern_singleton as singleton
from scripts import modern_singleton_executor as executor
from scripts.path_config import OutputPaths
from scripts.release_manifest import prepare_release, validate_release
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_exxon_coverage as exxon_tests
from tests import test_modern_organizational_coverage as organizational_tests
from tests.test_modern_upload_compatibility import CompatibilityTransport

OLD_SOURCES = ('FGDC-141', 'FGDC-696', 'FGDC-95', 'FGDC-1839', 'FGDC-1319', 'FGDC-59')
STAMP = fixtures.NOW.isoformat()


class ModernContentClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.MAPPING.read_bytes())
        rows = cls.manifest['targets']
        cls.samples = [rows[i] for i in (0, 50, 100, 150, 202)]
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=[
            sid for row in cls.samples for sid in row['source_ids']])
        cls.old_sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.old_sources.cleanup)
        cls.old_prepared = fixtures.prepare_sources(cls.old_sources.name, ids=list(OLD_SOURCES))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(self.prepared_root, self.root / 'prepared')
        self.paths = OutputPaths(str(self.root / 'prepared'), 'production')
        self.row = self.samples[0]
        self.target_id = self.row['record_target_id']

    def prepare(self, target_id=None):
        return mapping.prepare(target_id or self.target_id, self.paths, reviewed_at=STAMP)

    def test_all203_members_bind_exact_original_profile_plan_and_review(self):
        self.assertEqual(mapping.sha(mapping.MAPPING.read_bytes()), mapping.MAPPING_SHA)
        self.assertEqual(mapping.sha(mapping.REVIEW.read_bytes()), mapping.REVIEW_SHA)
        self.assertEqual(mapping.sha(mapping.SERVICE.read_bytes()), mapping.SERVICE_SHA)
        profile = singleton.pinned(singleton.EXXON_PROFILE, singleton.EXXON_SHA)
        profile_ids = {m['source_id']: m['source_sha256'] for m in profile['members']}
        expected = [r for r in classes.load_representation()['classes']
                    if all(profile_ids.get(sid) == r['source_sha256'] for sid in r['source_ids'])]
        self.assertEqual(self.manifest['targets'], sorted(expected, key=lambda r: r['record_target_id']))
        self.assertEqual(len(expected), 203)
        seen = set()
        for row in expected:
            _, selected, planned = mapping.source_policy(row['record_target_id'])
            self.assertEqual(row, selected)
            self.assertEqual(planned['source_semantic_status'], 'supported')
            for sid, filename in zip(row['source_ids'], row['source_filenames'], strict=True):
                self.assertNotIn(sid, seen)
                seen.add(sid)
                self.assertEqual(mapping.sha((mapping.ROOT / 'FGDC' / filename).read_bytes()), row['source_sha256'])
                self.assertEqual(profile_ids[sid], row['source_sha256'])
        self.assertEqual(len(seen), 406)

    def test_five_pairs_repeat_preserves_complete_legacy_wire_and_two_files(self):
        for row in self.samples:
            with self.subTest(target=row['record_target_id']):
                prepared = self.prepare(row['record_target_id'])
                self.assertEqual(prepared, self.prepare(row['record_target_id']))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))
                target = classes.prepare_class_target(row['record_target_id'], self.paths, reviewed_at=STAMP)
                self.assertEqual(prepared.legacy_target, target)
                self.assertFalse(hasattr(prepared, 'source_id'))
                self.assertFalse(hasattr(prepared, 'xml'))
                wire = mapping.parse(prepared.body)
                singleton.validate_payload(wire)
                meta = target['metadata']
                preservation = wire['metadata']['additional_descriptions'][0]['description']
                self.assertEqual(mapping.parse(html.unescape(preservation.split('<pre>', 1)[1][:-6]).encode()), meta)
                self.assertEqual(wire['metadata']['creators'], exxon_tests.MODERN_CREATORS)
                for field in ('title', 'publication_date', 'description'):
                    self.assertEqual(wire['metadata'][field], meta[field])
                self.assertEqual(wire['metadata']['subjects'], [{'subject': k} for k in meta['keywords']])
                self.assertEqual((meta['access_right'], meta['license']), ('restricted', ''))
                self.assertEqual([name for name, _ in prepared.originals], row['source_filenames'])
                for name, raw in prepared.originals:
                    self.assertEqual(raw, (mapping.ROOT / 'FGDC' / name).read_bytes())
                    self.assertIn(name, meta['notes'])
                self.assertEqual(prepared.originals[0][1], prepared.originals[1][1])
                self.assertEqual(len(prepared.evidence['inputs']), 2)
                self.assertEqual(prepared.evidence['artifact_contract'], target['artifact_contract'])
                for key in ('upload_eligible', 'remote_verified', 'publication_approved'):
                    self.assertIs(prepared.evidence[key], False)

    def test_other25_classes_singletons_and_protected_sources_are_outside(self):
        admitted = {r['record_target_id'] for r in self.manifest['targets']}
        others = [r['record_target_id'] for r in classes.load_representation()['classes']
                  if r['record_target_id'] not in admitted]
        self.assertEqual(len(others), 25)
        for identity in others + list(OLD_SOURCES) + list(singleton.PROTECTED) + self.row['source_ids']:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                self.prepare(identity)

    def test_missing_changed_and_renamed_second_original_hold_whole_class(self):
        path = Path(self.paths.original_fgdc_dir) / self.row['source_filenames'][1]
        original = path.read_bytes()
        path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.prepare()
        renamed = path.with_name('FGDC-99999.xml')
        renamed.write_bytes(original)
        with self.assertRaises((ValueError, OSError)):
            self.prepare()
        path.write_bytes(original + b' ')
        with self.assertRaises(ValueError):
            self.prepare()

    def test_missing_second_payload_and_changed_policy_or_metadata_hold(self):
        path = Path(self.paths.zenodo_json_dir) / (self.row['source_ids'][1] + '.json')
        original = path.read_bytes()
        path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.prepare()
        for mutate in (
                lambda p: p['artifact_policy'].pop('creator_interpretation'),
                lambda p: p['artifact_policy']['creator_interpretation'].update(manifest_sha256='0' * 64),
                lambda p: p['metadata'].update(publication_date='1900-01-01'),
                lambda p: p['metadata']['creators'][1].update(name='Bodkin, Invented'),
                lambda p: p['metadata'].update(license='cc-by-4.0')):
            payload = mapping.parse(original)
            mutate(payload)
            path.write_bytes(mapping.encode(payload))
            with self.subTest(payload=payload['metadata']['title']), self.assertRaises(ValueError):
                self.prepare()

    def test_semantically_held_rebuilt_target_is_not_accepted(self):
        target = classes.prepare_class_target(self.target_id, self.paths, reviewed_at=STAMP)
        target['member_assessments'][1]['source_semantic_status'] = 'held'
        target['source_semantic_status'] = 'held'
        with patch.object(classes, 'prepare_class_target', return_value=target), self.assertRaises(ValueError):
            self.prepare()

    def test_withdrawn_mapping_review_projection_and_pair_authority_hold(self):
        for module, attr in ((mapping, 'MAPPING'), (mapping, 'REVIEW'), (mapping, 'SERVICE'),
                             (singleton, 'EXXON_MAPPING'), (classes, 'AUTHORITY_PATH')):
            with self.subTest(evidence=attr), patch.object(module, attr, self.root / 'missing.json'):
                with self.assertRaises((ValueError, OSError)):
                    self.prepare()

    def test_rehashed_manifest_cannot_forge_membership_creators_or_authority(self):
        for mutate in (
                lambda m: m['targets'].pop(),
                lambda m: m['targets'][0]['source_ids'].reverse(),
                lambda m: m['targets'][0].update(canonical_source_id=m['targets'][0]['source_ids'][0]),
                lambda m: m['targets'][0].update(source_sha256='0' * 64),
                lambda m: m['modern_creators'][1]['person_or_org'].update(given_name='Invented'),
                lambda m: m['creators'][1].update(affiliation='Invented'),
                lambda m: m.update(pair_authority_sha256='0' * 64)):
            value = copy.deepcopy(self.manifest)
            mutate(value)
            path = self.root / 'changed.json'
            path.write_bytes(mapping.encode(value))
            with patch.object(mapping, 'MAPPING', path), \
                    patch.object(mapping, 'MAPPING_SHA', mapping.sha(path.read_bytes())), self.assertRaises(ValueError):
                self.prepare()

    def test_fixed_aware_nonfuture_assessment_time_required(self):
        for stamp in (None, '2026-10-05', '2999-01-01T00:00:00Z'):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                mapping.prepare(self.target_id, self.paths, reviewed_at=stamp)

    def test_self_rehashed_wire_target_and_inventory_edits_cannot_validate(self):
        original = self.prepare()
        self.assertEqual(mapping.validate_prepared(original, self.paths), original)
        for kind in ('wire', 'target', 'inventory', 'evidence'):
            value = copy.deepcopy(original)
            if kind == 'wire':
                body = mapping.parse(value.body)
                body['metadata']['title'] = 'Invented'
                value = replace(value, body=mapping.encode(body))
                value.evidence['wire_sha256'] = mapping.sha(value.body)
            elif kind == 'target':
                value.legacy_target['metadata']['title'] = 'Invented'
                value.evidence['legacy_target_sha256'] = mapping.sha(mapping.encode(value.legacy_target))
            elif kind == 'inventory':
                value = replace(value, originals=(value.originals[0], value.originals[0]))
            else:
                value.evidence['upload_eligible'] = True
            value = replace(value, binding=mapping.sha(mapping.encode(value.evidence)))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                mapping.validate_prepared(value, self.paths)

    def test_member_and_renamed_pair_bytes_cannot_reach_singleton_executor_or_bridge(self):
        transport = type('NoTransport', (), {'request': lambda *a, **k: self.fail('Provider reached')})()
        missing = self.root / 'missing.json'
        inputs = [Path(self.paths.zenodo_json_dir) / (sid + '.json') for sid in self.row['source_ids']]
        renamed = Path(self.paths.zenodo_json_dir) / 'FGDC-99999.json'
        shutil.copyfile(inputs[0], renamed)
        shutil.copyfile(Path(self.paths.original_fgdc_dir) / self.row['source_filenames'][0],
                        Path(self.paths.original_fgdc_dir) / 'FGDC-99999.xml')
        for path in inputs + [renamed]:
            with self.subTest(path=path.name):
                with self.assertRaises(ValueError):
                    singleton.prepare(path, self.paths)
                with self.assertRaises(ValueError):
                    executor.Runner(path, self.paths, missing, missing, fixtures.TOKEN, transport)
                with self.assertRaises(ValueError):
                    publication.bridge(path, self.paths, missing, missing, missing)

    def test_class_target_cannot_enter_legacy_release_even_with_invented_qa(self):
        target = self.prepare().legacy_target
        row = dict(target, fgdc_id=self.target_id, qa={'approved': True})
        qa = {'schema_version': 2, 'environment': 'production', 'records': [row]}
        with self.assertRaises(ValueError):
            prepare_release(qa)
        with self.assertRaises(ValueError):
            validate_release({}, qa, self.target_id, row)

    def test_pr42_six_singleton_policies_bridge_without_rewriting_completed_history(self):
        for index, sid in enumerate(OLD_SOURCES):
            with self.subTest(source=sid):
                fixture = fixtures.Fixture(self.root / str(index), self.old_prepared, source_id=sid)
                fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
                harness = organizational_tests.PublicationFixture(fixture)
                retained = exxon_tests.save_historical_runtime(harness, publication.PR42_RUNTIME)
                calls = list(fixture.transport.calls)
                _, bound = harness.bridge()
                self.assertEqual(bound['original_runtime_sha256'], publication.PR42_RUNTIME)
                self.assertEqual(fixture.transport.calls, calls)
                self.assertEqual({p: p.read_bytes() for p in retained}, retained)


if __name__ == '__main__':
    unittest.main()
