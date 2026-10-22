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

    def test_other25_classes_are_the_nonexxon_policy_and_singletons_and_protected_sources_are_outside(self):
        admitted = {r['record_target_id'] for r in self.manifest['targets']}
        others = sorted(r['record_target_id'] for r in classes.load_representation()['classes']
                        if r['record_target_id'] not in admitted)
        self.assertEqual(len(others), 25)
        nonexxon = mapping.parse(mapping.NONEXXON_MAPPING.read_bytes())
        self.assertEqual([r['record_target_id'] for r in nonexxon['targets']], others)
        for identity in others:  # the Exxon policy still refuses them; only the second policy admits them
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                mapping.source_policy(identity)
            self.assertEqual(mapping.pair_rule(identity).policy, mapping.NONEXXON_POLICY)
        for identity in list(OLD_SOURCES) + list(singleton.PROTECTED) + self.row['source_ids']:
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


EXXON_PAIR_TARGET = 'sha256:0025e59c5556d26b1c14ceac8c4c840057a271724b524c087db2dd0fb4315025'
EXXON_PAIR = ('FGDC-2953', 'FGDC-3181')
# The v1 wire of that published Exxon pair at fixtures.NOW, measured before the second policy existed.
EXXON_PAIR_WIRE_SHA = 'a2eeb7be5b6cf6100da6685e3cc33566e43307a983a9b985bc208e317689f583'
EXXON_EVIDENCE_KEYS = {
    'schema_version', 'kind', 'policy', 'record_target_id', 'source_ids', 'source_sha256', 'reviewed_at',
    'mapping_manifest_sha256', 'source_review_sha256', 'source_plan_sha256', 'creator_profile_sha256',
    'creator_projection_sha256', 'service_contract_sha256', 'representation_sha256', 'pair_map_sha256',
    'pair_authority_sha256', 'inputs', 'artifact_contract', 'legacy_target_sha256', 'legacy_metadata_sha256',
    'wire_sha256', 'schema_sha256', 'runtime_sha256', 'production_reconciliation_status', 'execution_status',
    'upload_eligible', 'remote_verified', 'publication_approved'}
FOODHABITS_TARGET = 'sha256:8bef14fd05c7b1ea1ab936bfeb4c5325c29c34f33b46d40b6f82f72055973237'
FOODHABITS_CREATORS = [{'person_or_org': {'type': 'personal', 'given_name': 'Pat', 'family_name': 'Livingston'}},
                       {'person_or_org': {'type': 'personal', 'given_name': 'Douglas', 'family_name': 'Smith'}}]
PROPOSAL = mapping.NONEXXON_MAPPING.with_name('resource_types_pairs25_proposal.json')


class NonExxonPairPolicyTests(unittest.TestCase):
    """The second pinned pair policy (ADR 0015): 25 non-Exxon pairs from 50 originals."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = mapping.parse(mapping.NONEXXON_MAPPING.read_bytes())
        cls.proposal = mapping.parse(PROPOSAL.read_bytes())
        cls.group_of = {tid: group for group in cls.manifest['groups'] for tid in group['record_target_ids']}
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(cls.sources.name, ids=[
            sid for row in cls.manifest['targets'] for sid in row['source_ids']] + list(EXXON_PAIR))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copytree(self.prepared_root, self.root / 'prepared')
        self.paths = OutputPaths(str(self.root / 'prepared'), 'production')

    def prepare(self, target_id):
        return mapping.prepare(target_id, self.paths, reviewed_at=STAMP)

    def rehashed(self, name, document):
        path = self.root / name
        path.write_bytes(mapping.encode(document))
        return path, mapping.sha(path.read_bytes())

    def test_manifest_is_pinned_and_derived_from_the_archived_reviews(self):
        for path, digest in ((mapping.NONEXXON_MAPPING, mapping.NONEXXON_MAPPING_SHA),
                             (mapping.NONEXXON_REVIEW, mapping.NONEXXON_REVIEW_SHA),
                             (mapping.FOODHABITS_SUPPLEMENT, mapping.FOODHABITS_SUPPLEMENT_SHA),
                             (mapping.FOODHABITS_BINDINGS, mapping.FOODHABITS_BINDINGS_SHA)):
            self.assertEqual(mapping.sha(path.read_bytes()), digest, path.name)
        groups, targets, origins = mapping.reviewed_groups()
        self.assertEqual((self.manifest['groups'], self.manifest['targets']), (groups, targets))
        self.assertEqual((len(targets), len(groups), len(origins)), (25, 5, 50))
        exxon = {r['record_target_id'] for r in mapping.parse(mapping.MAPPING.read_bytes())['targets']}
        ids = {r['record_target_id'] for r in targets}
        self.assertEqual(len(ids & exxon), 0)
        self.assertEqual(len(ids | exxon), 228)
        sources = [sid for row in targets for sid in row['source_ids']]
        self.assertEqual(len(set(sources)), 50)
        for row in targets:
            for filename in row['source_filenames']:
                self.assertEqual(mapping.sha((mapping.ROOT / 'FGDC' / filename).read_bytes()), row['source_sha256'])
            _, selected, planned, group, reviewed_origins = mapping.nonexxon_source_policy(row['record_target_id'])
            self.assertEqual((selected, planned['source_semantic_status'], group), (row, 'supported', self.group_of[row['record_target_id']]))
            self.assertEqual(sorted(reviewed_origins), sorted(row['source_ids']))
        foodhabits = self.group_of[FOODHABITS_TARGET]
        self.assertEqual((foodhabits['review'], foodhabits['creator_authority'], foodhabits['modern_creators']),
                         (mapping.FOODHABITS_SUPPLEMENT.name, mapping.CREATOR426, FOODHABITS_CREATORS))
        self.assertEqual(foodhabits['creators'], [{'name': 'Pat Livingston'}, {'name': 'Douglas Smith'}])
        for group in groups:
            if group['group_id'] != foodhabits['group_id']:
                self.assertEqual((group['review'], group['creator_authority']),
                                 (mapping.NONEXXON_REVIEW.name, mapping.LITERAL_PRIMARY))
                self.assertEqual([c['type'] for c in group['creators']], ['Organization'])
                self.assertEqual(group['modern_creators'], [{'person_or_org': {
                    'name': group['creators'][0]['name'], 'type': 'organizational'}}])
        self.assertEqual(sum(len(g['record_target_ids']) for g in groups), 25)

    def test_every_admitted_pair_prepares_and_its_v1_and_v2_wires_validate(self):
        from scripts import modern_bulk as bulk
        from scripts import modern_wire_v2 as wire_v2

        types = self.proposal['types']
        for row in self.manifest['targets']:
            target_id = row['record_target_id']
            group = self.group_of[target_id]
            with self.subTest(target=target_id):
                prepared = self.prepare(target_id)
                self.assertEqual(prepared, self.prepare(target_id))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))
                self.assertEqual(mapping.validate_prepared(prepared, self.paths), prepared)
                self.assertEqual(prepared.source_ids, tuple(row['source_ids']))
                self.assertEqual([name for name, _ in prepared.originals], row['source_filenames'])
                for name, raw in prepared.originals:
                    self.assertEqual(raw, (mapping.ROOT / 'FGDC' / name).read_bytes())
                self.assertEqual(prepared.originals[0][1], prepared.originals[1][1])
                evidence = prepared.evidence
                self.assertEqual((evidence['policy'], evidence['mapping_manifest_sha256'], evidence['group_id'],
                                  evidence['creator_authority'], evidence['source_review_sha256'],
                                  evidence['foodhabits_supplement_sha256']),
                                 (mapping.NONEXXON_POLICY, mapping.NONEXXON_MAPPING_SHA, group['group_id'],
                                  group['creator_authority'], mapping.NONEXXON_REVIEW_SHA,
                                  mapping.FOODHABITS_SUPPLEMENT_SHA))
                for key in ('upload_eligible', 'remote_verified', 'publication_approved'):
                    self.assertIs(evidence[key], False)
                wire = mapping.parse(prepared.body)
                singleton.validate_payload(wire)
                meta = prepared.legacy_target['metadata']
                self.assertEqual(meta['creators'], group['creators'])
                self.assertEqual(wire['metadata']['creators'], group['modern_creators'])
                self.assertEqual((meta['access_right'], meta['license']), ('restricted', ''))
                preservation = wire['metadata']['additional_descriptions'][0]['description']
                self.assertEqual(mapping.parse(html.unescape(preservation.split('<pre>', 1)[1][:-6]).encode()), meta)
                pair = bulk.PairPrepared(prepared)
                self.assertEqual((pair.source_id, pair.source_ids), (row['source_ids'][0], row['source_ids']))
                resource_type = types[pair.source_id]
                self.assertIn(resource_type, wire_v2.RESOURCE_TYPES)
                v2 = wire_v2.build(mapping.parse(pair.body), pair.xml, pair.source_ids, resource_type)
                wire_v2.validate(v2)
                self.assertEqual(mapping.parse(bulk.WireV2(pair, resource_type).body), v2)
                self.assertEqual(v2['metadata']['creators'], group['modern_creators'])
                self.assertEqual(v2['metadata']['resource_type'], {'id': resource_type})
                self.assertEqual(v2['metadata']['title'], wire_v2.strip_suffix(wire['metadata']['title']))
                self.assertFalse(v2['metadata']['title'].endswith(wire_v2.ARTIFACT_SUFFIX))
                self.assertEqual(v2['access'], {'record': 'public', 'files': 'public'})

    def test_foodhabits_pair_carries_the_supplement_vector_over_name_only_legacy_credits(self):
        prepared = self.prepare(FOODHABITS_TARGET)
        self.assertEqual(prepared.source_ids, ('FGDC-2837', 'FGDC-3065'))
        self.assertEqual(mapping.parse(prepared.body)['metadata']['creators'], FOODHABITS_CREATORS)
        self.assertEqual(prepared.legacy_target['metadata']['creators'],
                         [{'name': 'Pat Livingston'}, {'name': 'Douglas Smith'}])
        self.assertEqual((prepared.evidence['creator_authority'], prepared.evidence['creator_profile_sha256']),
                         (mapping.CREATOR426, singleton.PROFILE_SHA))
        for sid in prepared.source_ids:
            payload = mapping.parse((Path(self.paths.zenodo_json_dir) / (sid + '.json')).read_bytes())
            self.assertEqual(payload['artifact_policy']['creator_interpretation']['manifest_sha256'], singleton.PROFILE_SHA)

    def test_exxon_pair_wire_and_evidence_are_unchanged_by_the_second_policy(self):
        prepared = self.prepare(EXXON_PAIR_TARGET)
        self.assertEqual((prepared.evidence['policy'], mapping.sha(prepared.body)), (mapping.POLICY, EXXON_PAIR_WIRE_SHA))
        self.assertEqual(set(prepared.evidence), EXXON_EVIDENCE_KEYS)
        self.assertEqual(prepared.evidence['creator_profile_sha256'], singleton.EXXON_SHA)
        self.assertEqual(mapping.pair_rule(EXXON_PAIR_TARGET).creator_authority, mapping.EXXON821)

    def test_pairs_outside_or_withdrawn_from_the_reviews_hold(self):
        organizational = self.manifest['groups'][1]['record_target_ids'][0]
        for identity in ('FGDC-2949', 'FGDC-141', *EXXON_PAIR, *singleton.PROTECTED, 'sha256:' + '0' * 64, ''):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                self.prepare(identity)
        review = mapping.parse(mapping.NONEXXON_REVIEW.read_bytes())
        supplement = mapping.parse(mapping.FOODHABITS_SUPPLEMENT.read_bytes())
        # A review that holds one organizational pair, rehashed consistently through the supplement's pin,
        # refuses that pair and, because the policy is finite, every other pair as well.
        held = copy.deepcopy(review)
        pair = next(p for p in held['pairs'] if p['record_target_id'] == organizational)
        pair.update(verdict='hold_personal_name_parts', proposed_modern_creators=None, actual_blocker='withdrawn')
        review_path, review_sha = self.rehashed('review.json', held)
        chained = copy.deepcopy(supplement)
        chained['existing_pair_review']['sha256'] = review_sha
        supplement_path, supplement_sha = self.rehashed('supplement.json', chained)
        with patch.object(mapping, 'NONEXXON_REVIEW', review_path), patch.object(mapping, 'NONEXXON_REVIEW_SHA', review_sha), \
                patch.object(mapping, 'FOODHABITS_SUPPLEMENT', supplement_path), \
                patch.object(mapping, 'FOODHABITS_SUPPLEMENT_SHA', supplement_sha):
            for identity in (organizational, FOODHABITS_TARGET):
                with self.subTest(withdrawn=identity), self.assertRaises(ValueError):
                    self.prepare(identity)
        # The Food Habits pair holds when its supplement no longer approves the vector, or changes it.
        for mutate in (lambda s: s.update(complete_modern_projection_approved_for_source_review=False),
                       lambda s: s['remaining_limits'].update(source_boundary_hold_for_this_exact_vector=True),
                       lambda s: s['approved_complete_modern_creators'][0]['person_or_org'].update(given_name='Patricia'),
                       lambda s: s['approved_complete_modern_creators'].pop(),
                       lambda s: s.update(verdict='HOLD_COMPLETE_PAIR_DOUGLAS_EXACT_PARTS_UNRESOLVED')):
            changed = copy.deepcopy(supplement)
            mutate(changed)
            path, digest = self.rehashed('changed-supplement.json', changed)
            with patch.object(mapping, 'FOODHABITS_SUPPLEMENT', path), patch.object(mapping, 'FOODHABITS_SUPPLEMENT_SHA', digest), \
                    self.assertRaises(ValueError):
                self.prepare(FOODHABITS_TARGET)
        # A rehashed manifest cannot change membership, groups or creators.
        for mutate in (lambda m: m['targets'].pop(),
                       lambda m: m['targets'][0]['source_ids'].reverse(),
                       lambda m: m['groups'][1]['modern_creators'][0]['person_or_org'].update(name='Invented'),
                       lambda m: m['groups'][0]['modern_creators'][1]['person_or_org'].update(family_name='Douglas', given_name='Smith'),
                       lambda m: m['groups'][0]['record_target_ids'].append(m['groups'][1]['record_target_ids'].pop()),
                       lambda m: m.update(creator_profile_sha256='0' * 64),
                       lambda m: m.update(foodhabits_supplement_sha256='0' * 64)):
            changed = copy.deepcopy(self.manifest)
            mutate(changed)
            path, digest = self.rehashed('changed-manifest.json', changed)
            with patch.object(mapping, 'NONEXXON_MAPPING', path), patch.object(mapping, 'NONEXXON_MAPPING_SHA', digest):
                for identity in (organizational, FOODHABITS_TARGET):
                    with self.subTest(manifest=identity), self.assertRaises(ValueError):
                        self.prepare(identity)
        for attr in ('NONEXXON_MAPPING', 'NONEXXON_REVIEW', 'FOODHABITS_SUPPLEMENT', 'FOODHABITS_BINDINGS'):
            with self.subTest(evidence=attr), patch.object(mapping, attr, self.root / 'missing.json'), \
                    self.assertRaises((ValueError, OSError)):
                self.prepare(organizational)

    def test_prepared_inputs_bound_to_another_creator_authority_hold(self):
        organizational = self.manifest['groups'][1]['record_target_ids'][0]
        row = next(r for r in self.manifest['targets'] if r['record_target_id'] == organizational)
        for target_id, sid, mutate in (
                (organizational, row['source_ids'][1],
                 lambda p: p['artifact_policy'].update(creator_interpretation={'manifest_sha256': singleton.PROFILE_SHA})),
                (organizational, row['source_ids'][0],
                 lambda p: p['metadata']['creators'][0].pop('type')),
                (FOODHABITS_TARGET, 'FGDC-3065', lambda p: p['artifact_policy'].pop('creator_interpretation')),
                (FOODHABITS_TARGET, 'FGDC-2837',
                 lambda p: p['artifact_policy']['creator_interpretation'].update(manifest_sha256=singleton.EXXON_SHA)),
                (FOODHABITS_TARGET, 'FGDC-2837', lambda p: p['metadata']['creators'].append({'name': 'Bailey, Michael'}))):
            path = Path(self.paths.zenodo_json_dir) / (sid + '.json')
            original = path.read_bytes()
            payload = mapping.parse(original)
            mutate(payload)
            path.write_bytes(mapping.encode(payload))
            try:
                with self.subTest(target=target_id, source=sid), self.assertRaises(ValueError):
                    self.prepare(target_id)
            finally:
                path.write_bytes(original)
        self.assertEqual(self.prepare(organizational).evidence['policy'], mapping.NONEXXON_POLICY)


if __name__ == '__main__':
    unittest.main()
