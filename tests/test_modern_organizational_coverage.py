"""Finite organizational coverage, source fidelity and real offline execution."""

import copy
import html
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_publication_qa as qa
from scripts import modern_singleton as mapping
from scripts import modern_singleton_executor as draft
from scripts.agent_qa import assess_source
from scripts.path_config import OutputPaths
from tests import modern_singleton_fixtures as fixtures
from tests import test_modern_publication as publication_tests
from tests.test_modern_publication_qa import raw_duplicates

EXTENSION_SHA = 'c78074384f29310e5cdc0c23dddc6b47161e516bc0222ddbbe0a36dfbc9a1dcf'
REPRESENTATIVE = 'FGDC-696'


class PublicationFixture:
    """Compose existing reviewed helpers without discovering their TestCase twice."""

    bridge = publication_tests.ModernPublicationTests.bridge
    grant = publication_tests.ModernPublicationTests.grant
    runner = publication_tests.ModernPublicationTests.runner
    ready = publication_tests.ModernPublicationTests.ready

    def __init__(self, fixture):
        self.fixture = fixture
        self.temp = SimpleNamespace(name=str(fixture.root))
        fixture.runner().run()
        self.packet = fixture.root / 'preparation.json'
        self.packet.write_bytes(mapping.encode({'binding': fixture.prepared.binding,
                                               'evidence': fixture.prepared.evidence, 'provider_requests': 0}))
        self.prepared, self.bound = self.bridge()
        self.transport = publication_tests.Transport(fixture)
        self.grant_path = fixture.root / 'new-grant.json'


class ModernOrganizationalCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.source_tmp.cleanup)
        cls.extension = json.loads(mapping.EXTENSION.read_bytes())
        cls.members = cls.extension['members']
        ids = [row['source_id'] for row in cls.members] + [row['source_id'] for row in mapping.cohort()['members']]
        cls.prepared_root = fixtures.prepare_sources(cls.source_tmp.name, ids=ids)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def fixture(self, source_id=REPRESENTATIVE):
        directory = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(directory.cleanup)
        return fixtures.Fixture(directory.name, self.prepared_root, source_id=source_id)

    def paths(self):
        output = self.root / 'prepared'
        shutil.copytree(self.prepared_root, output)
        return OutputPaths(str(output), 'production')

    def test_all_86_preserve_originals_literal_creator_order_complete_metadata_and_rights(self):
        self.assertEqual(mapping.sha(mapping.EXTENSION.read_bytes()), EXTENSION_SHA)
        self.assertEqual(len(self.members), 86)
        self.assertEqual(len({row['source_id'] for row in self.members}), 86)
        self.assertEqual(len({row['creator_cohort'] for row in self.members}), 37)
        paths = self.paths()
        profile = json.loads(mapping.PROFILE.read_bytes())
        cohorts = {row['profile']: row for row in profile['cohorts']}
        for member in self.members:
            sid = member['source_id']
            with self.subTest(source=sid):
                json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
                original_input = json_file.read_bytes()
                prepared = mapping.prepare(json_file, paths)
                metadata, source_sha, artifact, _ = assess_source(json_file, paths)
                expected_creators = cohorts[member['creator_cohort']]['creators']
                wire = mapping.parse(prepared.body)
                meta = wire['metadata']
                self.assertEqual(prepared.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                self.assertLessEqual(len(prepared.xml), draft.MAX_BYTES)
                self.assertLessEqual(len(prepared.body), draft.MAX_BYTES)
                self.assertEqual(mapping.sha(prepared.xml), member['source_sha256'])
                self.assertEqual(source_sha, member['source_sha256'])
                self.assertEqual(prepared.evidence['artifact_contract'], artifact)
                self.assertEqual(metadata['creators'], expected_creators)
                self.assertEqual(meta['creators'], [{'person_or_org': {'type': 'organizational', 'name': c['name']}}
                                                    for c in expected_creators])
                preserved = meta['additional_descriptions'][0]['description']
                self.assertTrue(preserved.startswith('<p>' + mapping.PRESERVATION_LABEL + '</p><pre>'))
                self.assertEqual(json.loads(html.unescape(preserved.split('<pre>', 1)[1][:-6])), metadata)
                for key in ('title', 'description', 'publication_date'):
                    self.assertEqual(meta[key], metadata[key])
                self.assertEqual(meta['subjects'], [{'subject': k} for k in metadata.get('keywords', [])])
                self.assertEqual(meta['publisher'], 'Zenodo')
                self.assertEqual(meta['resource_type'], {'id': 'other'})
                self.assertNotIn('rights', meta)
                self.assertNotIn('license', meta)
                self.assertEqual(wire['access'], {'record': 'public', 'files': 'restricted'})
                self.assertEqual(prepared.evidence['legacy_metadata_sha256'], mapping.sha(mapping.encode(metadata)))
                self.assertEqual(prepared.evidence['prepared_input_sha256'], mapping.sha(original_input))
                self.assertEqual(prepared.evidence['source_sha256'], source_sha)
                self.assertEqual(prepared.evidence['wire_sha256'], mapping.sha(prepared.body))
                self.assertEqual(prepared.binding, mapping.sha(mapping.encode(prepared.evidence)))
                self.assertEqual(json_file.read_bytes(), original_input)
                self.assertEqual({k: prepared.evidence[k] for k in
                                  ('schema_version', 'policy', 'mapping_manifest_sha256', 'creator_cohort')},
                                 {'schema_version': 2, 'policy': 'modern-xml-organizations86-v1',
                                  'mapping_manifest_sha256': EXTENSION_SHA, 'creator_cohort': member['creator_cohort']})

    def test_19_existing_sources_keep_exact_v1_policy_and_do_not_depend_on_extension_file(self):
        original = mapping.cohort()
        for member in original['members']:
            cohort, fields = mapping.source_policy(member['source_id'])
            self.assertEqual(cohort, original)
            self.assertEqual(fields, {'schema_version': 1, 'policy': 'modern-xml-ncdc19-v1'})
        with patch.object(mapping, 'EXTENSION', self.root / 'missing-extension.json'):
            fixture = self.fixture('FGDC-141')
            self.assertEqual(fixture.prepared.evidence['schema_version'], 1)
            self.assertNotIn('mapping_manifest_sha256', fixture.prepared.evidence)
            self.assertNotIn('creator_cohort', fixture.prepared.evidence)

    def test_missing_changed_or_wrongly_pinned_extension_cannot_prepare_new_sources(self):
        fixture = self.fixture()
        changed = self.root / 'changed-extension.json'
        changed.write_bytes(mapping.EXTENSION.read_bytes() + b' ')
        for path in (changed, self.root / 'missing.json'):
            with self.subTest(path=path.name), patch.object(mapping, 'EXTENSION', path):
                with self.assertRaises((ValueError, OSError)):
                    mapping.prepare(fixture.json_file, fixture.paths)
        with patch.object(mapping, 'EXTENSION_SHA', '0' * 64), self.assertRaises(ValueError):
            mapping.prepare(fixture.json_file, fixture.paths)

    def test_manifest_member_hash_and_creator_cohort_cannot_be_self_reassigned(self):
        fixture = self.fixture()
        for key, value in (('source_sha256', '0' * 64), ('creator_cohort', mapping.COHORT)):
            with self.subTest(field=key):
                manifest = copy.deepcopy(self.extension)
                member = next(row for row in manifest['members'] if row['source_id'] == REPRESENTATIVE)
                member[key] = value
                changed = self.root / 'rehashed-extension.json'
                changed.write_bytes(mapping.encode(manifest))
                with patch.object(mapping, 'EXTENSION', changed), \
                        patch.object(mapping, 'EXTENSION_SHA', mapping.sha(changed.read_bytes())), \
                        self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)

    def test_held_untyped_personal_paired_and_protected_sources_remain_blocked(self):
        fixture = self.fixture()
        # PICES26 and the reviewed citation/program groups have separate policies; SPOT remains held.
        for sid in ('FGDC-710', 'FGDC-859', 'FGDC-885', 'FGDC-2953', 'FGDC-3181',
                    'FGDC-1238', 'FGDC-2043', 'FGDC-2057', 'FGDC-2725', 'FGDC-2731'):
            with self.subTest(source=sid):
                changed = fixture.json_file.with_name(sid + '.json')
                changed.write_bytes(fixture.json_file.read_bytes())
                with self.assertRaises(ValueError):
                    mapping.source_policy(sid)
                with self.assertRaises(ValueError):
                    mapping.prepare(changed, fixture.paths)

    def test_reordered_or_inferred_creators_and_changed_date_rights_or_source_hold(self):
        fixture = self.fixture()
        original = fixture.json_file.read_bytes()
        expected = mapping.parse(original)['metadata']['creators']
        self.assertEqual(len(expected), 2)
        changes = [('creators', list(reversed(expected))),
                   ('creators', [{'name': creator['name']} for creator in expected]),
                   ('publication_date', '2026-10-05'), ('license', 'cc-by-4.0'), ('access_right', 'open'),
                   ('description', 'Invented abstract')]
        for key, value in changes:
            with self.subTest(field=key, value=value):
                payload = mapping.parse(original)
                payload['metadata'][key] = value
                fixture.json_file.write_bytes(mapping.encode(payload))
                with self.assertRaises(ValueError):
                    mapping.prepare(fixture.json_file, fixture.paths)
        fixture.json_file.write_bytes(original)
        raw = Path(fixture.paths.original_fgdc_dir) / (REPRESENTATIVE + '.xml')
        raw.write_bytes(raw.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            mapping.prepare(fixture.json_file, fixture.paths)

    def test_new_source_runs_draft_capture_qa_release_publish_and_unchanged_retry(self):
        fixture = self.fixture()
        harness = PublicationFixture(fixture)
        base = '/api/records/19000001/draft'
        file = base + '/files/' + REPRESENTATIVE + '.xml'
        self.assertEqual([call for call in fixture.transport.calls if call[0] != 'GET'], [
            ('POST', '/api/records', fixture.prepared.body),
            ('POST', base + '/files', mapping.encode([{'key': REPRESENTATIVE + '.xml'}])),
            ('PUT', file + '/content', fixture.prepared.xml),
            ('POST', file + '/commit', None),
        ])
        draft_retry = fixture.runner().run(read_only=True)
        self.assertEqual(draft_retry['counts'], draft.LIMITS)
        # The preserved creation journal now includes the allowed read-only retry.
        harness.prepared, harness.bound = harness.bridge()
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        self.assertEqual(len(snapshot['responses']), 5)
        self.assertTrue(any(row['path'].endswith('/' + REPRESENTATIVE + '.xml/content')
                            for row in snapshot['responses']))
        manifest = mapping.parse(documents['qa'].read_bytes())
        self.assertEqual(manifest['records'][0]['fgdc_id'], REPRESENTATIVE)
        self.assertEqual(manifest['records'][0]['agent_evidence']['prepared_evidence']['schema_version'], 2)
        result = harness.runner(documents=documents).run()
        self.assertTrue(result['published_verified'])
        self.assertTrue(result['community_submission_verified'])
        result = harness.runner(documents=documents).run(read_only=True)
        self.assertEqual(result['counts'], publication.PUBLISH_LIMITS)
        self.assertEqual([call[0] for call in harness.transport.calls if call[0] != 'GET'], ['PUT', 'POST'])
        self.assertFalse(result['doi_registration_verified'])
        self.assertTrue(result['community_membership_verified'])
        self.assertTrue(result['release_complete'])

    def test_new_source_uncertain_create_is_spent_and_never_replayed_after_journal_loss(self):
        for effect in (False, True):
            with self.subTest(effect_before_response_loss=effect):
                fixture = self.fixture()
                fixture.transport.fail_index = 0
                fixture.transport.effect_before_fail = effect
                runner = fixture.runner()
                with self.assertRaises(ValueError):
                    runner.run()
                intent = runner.intent_path.read_bytes()
                row = mapping.parse(runner.journal_path.read_bytes())['targets'][REPRESENTATIVE]
                self.assertEqual(row['counts']['create'], 1)
                self.assertIsNone(row['identity'])
                for readonly in (False, True):
                    with self.assertRaises(ValueError):
                        fixture.runner().run(read_only=readonly)
                runner.journal_path.unlink()
                fixture.change_proof(reviewed_by='Another independent fixture reviewer')
                with self.assertRaises(ValueError):
                    fixture.runner().run()
                self.assertEqual(runner.intent_path.read_bytes(), intent)
                self.assertEqual(len(fixture.transport.calls), 1)

    def test_qa_rejects_rehashed_new_policy_manifest_or_cohort_substitutions(self):
        harness = PublicationFixture(self.fixture())
        documents = harness.ready()
        snapshot = mapping.parse(documents['snapshot'].read_bytes())
        changes = [('schema_version', 1), ('policy', mapping.POLICY),
                   ('mapping_manifest_sha256', '0' * 64), ('creator_cohort', mapping.COHORT)]
        for key, value in changes:
            with self.subTest(field=key):
                evidence = copy.deepcopy(harness.prepared.evidence)
                evidence[key] = value
                forged = replace(harness.prepared, evidence=evidence, binding=mapping.sha(mapping.encode(evidence)))
                bound = copy.deepcopy(harness.bound)
                bound['preparation_binding'] = forged.binding
                bound['binding'] = mapping.sha(mapping.encode({k: v for k, v in bound.items() if k != 'binding'}))
                saved = copy.deepcopy(snapshot)
                saved['bridge_binding'] = bound['binding']
                duplicate = raw_duplicates(forged, bridge=bound, snapshot=saved, now=publication_tests.NOW)
                with self.assertRaises(ValueError):
                    qa.assess(forged, bound, saved, duplicate, now=publication_tests.NOW)
        self.assertEqual(harness.transport.calls, [])

    def test_old_runtime_pins_cannot_authorize_new_policy_even_with_rebound_history(self):
        for runtime in (publication.PR34_RUNTIME, publication.PR35_RUNTIME):
            with self.subTest(runtime=runtime):
                harness = PublicationFixture(self.fixture())
                fixture = harness.fixture
                packet = mapping.parse(harness.packet.read_bytes())
                packet['evidence']['runtime_sha256'] = runtime
                packet['binding'] = mapping.sha(mapping.encode(packet['evidence']))
                harness.packet.write_bytes(mapping.encode(packet))
                fixture.change_proof(binding=packet['binding'])
                fixture.change_grant(binding=packet['binding'])
                journal_path = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
                journal = mapping.parse(journal_path.read_bytes())
                row = journal['targets'][REPRESENTATIVE]
                row['binding'] = packet['binding']
                row['grant_sha256'] = mapping.sha(fixture.grant_path.read_bytes())
                intent_path = draft.state_root(fixture.paths) / (REPRESENTATIVE + '.modern-create-v1.intent.json')
                intent = mapping.parse(intent_path.read_bytes())
                intent.update(binding=packet['binding'], grant_sha256=row['grant_sha256'])
                intent_path.write_bytes(mapping.encode(intent))
                row['intent_sha256'] = mapping.sha(intent_path.read_bytes())
                journal_path.write_bytes(mapping.encode(journal))
                before = journal_path.read_bytes(), intent_path.read_bytes()
                with self.assertRaises(ValueError):
                    harness.bridge()
                harness.grant('capture')
                with self.assertRaises(ValueError):
                    harness.runner('capture').run()
                self.assertEqual(harness.transport.calls, [])
                self.assertEqual((journal_path.read_bytes(), intent_path.read_bytes()), before)


if __name__ == '__main__':
    unittest.main()
