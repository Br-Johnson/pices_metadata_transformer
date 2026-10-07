"""Batch manifest contracts: live bindings, twin detection with allowances, drift refusal."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import modern_batch as batch
from scripts import modern_singleton_executor as executor
from scripts.modern_singleton import Held, encode, prepare, sha
from tests import modern_singleton_fixtures as fixtures

NOW = fixtures.NOW
IDS = ['FGDC-141', 'FGDC-143', 'FGDC-148']
LONG = 'Workshop on the development of cooperative research in coastal regions'


def fact(source_id, title, source='s', binding=None):
    return {'source_id': source_id, 'policy': 'p', 'schema_version': 1, 'source_sha256': source * 64,
            'wire_sha256': 'w' * 64, 'binding': binding or ('b' * 64), 'title_key': batch.title_key(title),
            'journal_phase': None}


def allow(*sources, allowed_by='Brett Johnson (chat, 2026-10-07)', note='', origin='cli'):
    return batch.normalise_allowance({'sources': sorted(sources, key=batch.by_number), 'allowed_by': allowed_by,
                                      'note': note}, origin)


class TwinTests(unittest.TestCase):
    def test_identical_sources_hold_even_with_an_allowance(self):
        facts = [fact('FGDC-1', 'One title', source='a'), fact('FGDC-2', 'Other title', source='a')]
        self.assertEqual(batch.twin_findings(facts), [{'pair': ['FGDC-1', 'FGDC-2'], 'kind': 'identical_source', 'hard': True}])
        with self.assertRaisesRegex(Held, 'Identical sources'):
            batch.resolve_twins(facts, [], [allow('FGDC-1', 'FGDC-2')])

    def test_title_twins_need_a_reviewed_allowance_that_matches_a_twin(self):
        facts = [fact('FGDC-1', ' Report  No. 9: ' + LONG, source='a'), fact('FGDC-2', LONG.upper(), source='b'),
                 fact('FGDC-3', 'Unrelated', source='c')]
        self.assertEqual(batch.twin_findings(facts), [{'pair': ['FGDC-1', 'FGDC-2'], 'kind': 'title_contained', 'hard': False}])
        with self.assertRaisesRegex(Held, 'Title twins without'):
            batch.resolve_twins(facts, [], [])
        twins, used = batch.resolve_twins(facts, [], [allow('FGDC-1', 'FGDC-2', note='one workshop')])
        self.assertEqual((twins, [a['sources'] for a in used]), ([{'pair': ['FGDC-1', 'FGDC-2'], 'kind': 'title_contained'}], [['FGDC-1', 'FGDC-2']]))
        group = allow('FGDC-1', 'FGDC-2', 'FGDC-3')  # a group allowance covers every pair inside it
        self.assertEqual(batch.resolve_twins(facts, [], [group])[1], [group])
        same = [fact('FGDC-1', 'Same title here', source='a'), fact('FGDC-2', 'same   TITLE here', source='b')]
        self.assertEqual(batch.twin_findings(same)[0]['kind'], 'same_title')
        self.assertEqual(batch.twin_findings([fact('FGDC-1', 'short one', source='a'),
                                              fact('FGDC-2', 'a short one indeed', source='b')]), [])
        with self.assertRaisesRegex(Held, 'matches no twin'):  # a stale decision
            batch.resolve_twins(facts, [], [allow('FGDC-1', 'FGDC-3'), allow('FGDC-1', 'FGDC-2')])
        with self.assertRaises(Held):  # a required allowance may only name known sources
            batch.resolve_twins(facts, [], [allow('FGDC-1', 'FGDC-9')])
        for bad in ({'sources': ['FGDC-2', 'FGDC-1'], 'allowed_by': 'x', 'note': ''},  # unsorted
                    {'sources': ['FGDC-1', 'FGDC-1'], 'allowed_by': 'x', 'note': ''},
                    {'sources': ['FGDC-1'], 'allowed_by': 'x', 'note': ''},
                    {'sources': ['FGDC-1', 'FGDC-2'], 'allowed_by': ' ', 'note': ''},
                    {'sources': ['FGDC-1', 'FGDC-2'], 'allowed_by': 'x'}):
            with self.subTest(bad=bad), self.assertRaises(Held):
                batch.normalise_allowance(bad, 'cli')

    def test_registry_allowances_are_optional_and_attempted_twins_still_hold(self):
        members = [fact('FGDC-1', 'The same long title for an attempted record', source='a')]
        attempted = [{'source_id': 'FGDC-7', 'source_sha256': 'b' * 64,
                      'title_key': batch.title_key('the same long title for an attempted record')}]
        with self.assertRaisesRegex(Held, 'Title twins without'):
            batch.resolve_twins(members, attempted, [])
        registry = [allow('FGDC-7', 'FGDC-1', origin='registry:one.json'), allow('FGDC-50', 'FGDC-51', origin='registry:two.json')]
        twins, used = batch.resolve_twins(members, attempted, [], registry)
        self.assertEqual((twins, [a['origin'] for a in used]),
                         ([{'pair': ['FGDC-1', 'FGDC-7'], 'kind': 'same_title'}], ['registry:one.json']))
        # Findings among attempted records only do not concern this batch.
        self.assertEqual(batch.resolve_twins([fact('FGDC-1', 'Distinct', source='a')],
                                             [{'source_id': 'FGDC-7', 'source_sha256': 'b' * 64, 'title_key': batch.title_key(LONG)},
                                              {'source_id': 'FGDC-8', 'source_sha256': 'c' * 64, 'title_key': batch.title_key(LONG)}], [])[0], [])


class RealTwinTests(unittest.TestCase):
    """The pair Brett allowed on 2026-10-07: one workshop described by two source records."""

    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=['FGDC-1915', 'FGDC-1924', 'FGDC-2708'])

    def test_a_core_title_inside_another_is_a_twin_and_series_siblings_are_not(self):
        fixture = fixtures.Fixture(Path(self.sources.name) / 'f', self.prepared_root, source_id='FGDC-1915')
        ids = ['FGDC-1915', 'FGDC-1924', 'FGDC-2708']
        kwargs = dict(batch_id='drafts-pices-twins', owner='266679', built_by='offline test', now=lambda: NOW)
        with self.assertRaisesRegex(Held, 'Title twins without'):
            batch.build_manifest(fixture.paths, ids, **kwargs)
        allowance = [{'sources': ['FGDC-1924', 'FGDC-2708'], 'allowed_by': 'Brett Johnson (chat, 2026-10-07)',
                      'note': 'Scientific Report No. 9 and the workshop record describe the October 1997 CCCC workshop.'}]
        document = batch.build_manifest(fixture.paths, ids, allowances=allowance, **kwargs)
        self.assertEqual(document['twins'], [{'pair': ['FGDC-1924', 'FGDC-2708'], 'kind': 'title_contained'}])
        self.assertEqual([a['origin'] for a in document['allowances']], ['cli'])
        keys = {m['source_id']: m['title_key'] for m in document['members']}
        self.assertTrue(keys['FGDC-2708'] in keys['FGDC-1924'] and not keys['FGDC-2708'].endswith('artifact'))
        self.assertEqual(batch.title_key('A title - FGDC XML metadata artifact'), 'a title')
        self.assertEqual(batch.title_key('Peopleﾒs - FGDC XML metadata artifact'), 'peopleメs')
        # The registry records the decision once; later builds need no command-line allowance.
        path = batch.record_allowance(fixture.paths, 'cccc-workshop-1997', ['FGDC-2708', 'FGDC-1924'],
                                      'Brett Johnson (chat, 2026-10-07)', 'one workshop, two sources', now=lambda: NOW)
        self.assertEqual(path, batch.allowances_dir(fixture.paths) / 'cccc-workshop-1997.json')
        self.assertEqual([a['origin'] for a in batch.load_registry(fixture.paths)], ['registry:cccc-workshop-1997.json'])
        document = batch.build_manifest(fixture.paths, ids, **kwargs)
        self.assertEqual([a['origin'] for a in document['allowances']], ['registry:cccc-workshop-1997.json'])
        with self.assertRaises(FileExistsError):
            batch.record_allowance(fixture.paths, 'cccc-workshop-1997', ['FGDC-1924', 'FGDC-2708'], 'x', 'y', now=lambda: NOW)
        # The manifest freezes the decision it used: removing the registry entry later changes nothing.
        path = batch.write_manifest(fixture.paths, document)
        (batch.allowances_dir(fixture.paths) / 'cccc-workshop-1997.json').unlink()
        batch.validate_manifest(path, fixture.paths)
        (batch.allowances_dir(fixture.paths) / 'broken.json').write_bytes(b'{"kind": "other"}')
        with self.assertRaises(Held):  # a malformed registry file holds every build
            batch.build_manifest(fixture.paths, ids, allowances=allowance, **{**kwargs, 'batch_id': 'drafts-pices-twins-2'})
        # Series siblings share long boilerplate but neither core contains the other.
        siblings = [fact('FGDC-1933', 'PICES Scientific Report No. 17 (2001) - PICES-GLOBEC International Program on Climate Change and Carrying Capacity : Report of the 2000 BASS, MODEL, MONITOR and REX Workshops and the 2001 BASS/MODEL Workshop - FGDC XML metadata artifact', source='a'),
                    fact('FGDC-1935', 'PICES Scientific Report No. 20 (2002) - PICES-GLOBEC International Program on Climate Change and Carrying Capacity : Report of the 2001 BASS/MODEL, MONITOR and REX Workshops and the 2002 MODEL/REX Workshop - FGDC XML metadata artifact', source='b')]
        self.assertEqual(batch.twin_findings(siblings), [])


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.sources.cleanup)
        cls.prepared_root = fixtures.prepare_sources(Path(cls.sources.name), ids=IDS)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = fixtures.Fixture(Path(self.temporary.name) / 'f', self.prepared_root)
        self.paths = self.fixture.paths

    def journal(self, targets):
        path = Path(self.paths.uploads_registry_path + '.modern-v1.json')
        path.write_bytes(encode({'schema_version': 1, 'kind': 'modern-production-draft-attempts', 'targets': targets}))

    def build(self, ids, **overrides):
        kwargs = dict(batch_id='drafts-test-001', owner='123', built_by='offline test', now=lambda: NOW)
        kwargs.update(overrides)
        return batch.build_manifest(self.paths, ids, **kwargs)

    def rewrite(self, path, mutate):
        document = json.loads(path.read_bytes())
        mutate(document)
        other = path.with_name('edited.json')
        other.write_bytes(encode(document))
        return other

    def test_members_pin_the_live_preparation_and_validation_re_derives_them(self):
        document = self.build(IDS[:2])
        self.assertEqual([m['source_id'] for m in document['members']], IDS[:2])
        for member in document['members']:
            prepared = prepare(str(Path(self.paths.zenodo_json_dir) / (member['source_id'] + '.json')), self.paths)
            self.assertEqual((member['binding'], member['source_sha256'], member['policy'], member['journal_phase']),
                             (prepared.binding, prepared.evidence['source_sha256'], prepared.evidence['policy'], None))
        self.assertEqual(document['membership_sha256'], sha(encode([[m['source_id'], m['binding']] for m in document['members']])))
        self.assertEqual((document['kind'], document['stage'], document['state_root'], document['twins'], document['member_count'],
                          document['attempted_count'], document['attempted_sha256'], document['allowances']),
                         (batch.MANIFEST_KIND, 'drafts', str(executor.state_root(self.paths)), [], 2, 0, sha(encode([])), []))
        path = batch.write_manifest(self.paths, document)
        self.assertEqual(path, executor.state_root(self.paths) / 'batches' / 'drafts-test-001.manifest.json')
        validated, document_sha = batch.validate_manifest(path, self.paths)
        self.assertEqual((validated, document_sha), (document, sha(path.read_bytes())))
        with self.assertRaises(FileExistsError):  # never replaced
            batch.write_manifest(self.paths, document)
        self.assertEqual(self.build(IDS[:2])['membership_sha256'], document['membership_sha256'])
        self.assertNotEqual(self.build(IDS[1::-1])['membership_sha256'], document['membership_sha256'])

    def test_validation_refuses_drift_in_members_twins_exclusions_or_the_runtime(self):
        document = self.build(IDS[:2])
        path = batch.write_manifest(self.paths, document)
        batch.validate_manifest(path, self.paths)
        with patch('scripts.modern_batch.runtime_binding', return_value='b' * 64), self.assertRaises(Held):
            batch.validate_manifest(path, self.paths)

        def binding(d):
            d['members'][1]['binding'] = 'c' * 64
            d['membership_sha256'] = batch.membership_sha256(d['members'])

        def title(d):
            d['members'][0]['title_key'] = 'something else'

        def reorder(d):
            d['members'] = d['members'][::-1]

        def twins(d):
            d['twins'] = [{'pair': ['FGDC-141', 'FGDC-143'], 'kind': 'same_title'}]

        def allowance(d):
            d['allowances'] = [{'sources': ['FGDC-141', 'FGDC-143'], 'allowed_by': 'x', 'note': '', 'origin': 'cli'}]

        def exclusion(d):
            d['exclusions'] = [{'source_id': 'FGDC-141', 'reason': 'but it is a member'}]

        def owner(d):
            d['owner'] = '0'

        def attempted(d):
            d['attempted_count'] = 1
        for label, mutate in (('binding', binding), ('title', title), ('reorder', reorder), ('twins', twins),
                              ('allowance', allowance), ('exclusion', exclusion), ('owner', owner), ('attempted', attempted)):
            with self.subTest(label=label), self.assertRaises(Held):
                batch.validate_manifest(self.rewrite(path, mutate), self.paths)
        # A source attempted after the build changes the attempted set, so the manifest must be rebuilt.
        self.journal({'FGDC-148': {'phase': 'verified', 'identity': {'id': '1'}}})
        with self.assertRaises(Held):
            batch.validate_manifest(path, self.paths)

    def test_journal_rows_are_reported_and_attempted_twins_are_checked(self):
        self.journal({'FGDC-148': {'phase': 'verified', 'identity': {'id': '1'}}})
        document = self.build(IDS[:3])
        self.assertEqual({m['source_id']: m['journal_phase'] for m in document['members']},
                         {'FGDC-141': None, 'FGDC-143': None, 'FGDC-148': 'verified'})
        self.assertEqual(document['attempted_count'], 0)
        path = batch.write_manifest(self.paths, document)
        batch.validate_manifest(path, self.paths)
        two = self.build(IDS[:2], batch_id='drafts-test-002')
        self.assertEqual((two['attempted_count'], two['attempted_sha256']), (1, sha(encode(['FGDC-148']))))
        twin = [{'source_id': 'FGDC-148', 'source_sha256': 'z' * 64, 'title_key': document['members'][0]['title_key']}]
        with patch('scripts.modern_batch.attempted_facts', return_value=twin):
            with self.assertRaisesRegex(Held, 'Title twins without'):
                self.build(IDS[:2], batch_id='drafts-test-003')
            allowance = [{'sources': ['FGDC-141', 'FGDC-148'], 'allowed_by': 'Brett Johnson (chat, 2026-10-07)', 'note': ''}]
            allowed = self.build(IDS[:2], batch_id='drafts-test-003', allowances=allowance)
            self.assertEqual(allowed['twins'], [{'pair': ['FGDC-141', 'FGDC-148'], 'kind': 'same_title'}])
        # A journal row whose prepared input is missing holds rather than being ignored.
        self.journal({'FGDC-151': {'phase': 'started'}})
        with self.assertRaises(Held):
            self.build(IDS[:1], batch_id='drafts-test-004')
        self.journal({'FGDC-148': {'identity': None}})  # a malformed row
        with self.assertRaises(Held):
            self.build(IDS[:1], batch_id='drafts-test-005')

    def test_shape_limits_and_exclusions(self):
        cases = {'bad_id': dict(batch_id='Drafts_1'), 'stage': dict(stage='publish'), 'owner': dict(owner='0'),
                 'built_by': dict(built_by=' ')}
        for label, overrides in cases.items():
            with self.subTest(label=label), self.assertRaises(Held):
                self.build(IDS[:1], **overrides)
        for ids in ([], IDS[:1] * 2, ['FGDC-0141'], ['FGDC-999999'], ['FGDC-1'] * 251):
            with self.subTest(ids=ids[:2]), self.assertRaises(Held):
                self.build(ids)
        with self.assertRaises(Held):  # an excluded source cannot also be a member
            self.build(IDS[:1], exclusions=[{'source_id': 'FGDC-141', 'reason': 'deferred'}])
        document = self.build(IDS[:1], exclusions=[{'source_id': 'FGDC-2733', 'reason': 'sanitiser control character'}])
        self.assertEqual(document['exclusions'], [{'source_id': 'FGDC-2733', 'reason': 'sanitiser control character'}])
        with self.assertRaises(Held):
            self.build(IDS[:1], exclusions=[{'source_id': 'FGDC-2733'}])

    def test_cli_builds_validates_records_allowances_and_reports_hold_reasons(self):
        members_file = Path(self.temporary.name) / 'members.json'
        members_file.write_bytes(encode({'kind': 'policy list', 'members': [{'source_id': 'FGDC-143', 'source_sha256': 'x'}]}))
        argv = ['modern_batch', 'build', '--output-dir', self.paths.base, '--batch-id', 'drafts-cli-001', '--owner', '123',
                '--built-by', 'cli test', '--member', 'FGDC-141', '--members-file', str(members_file),
                '--exclude', 'FGDC-2733:sanitiser control character']
        with patch('sys.argv', argv), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 0)
        result = json.loads(out.getvalue())
        manifest = Path(result['manifest'])
        self.assertEqual((result['member_count'], result['twins'], result['attempted_count'], result['provider_requests'],
                          manifest.exists()), (2, [], 0, 0, True))
        self.assertEqual(result['manifest_sha256'], sha(manifest.read_bytes()))
        self.assertEqual([m['source_id'] for m in json.loads(manifest.read_bytes())['members']], ['FGDC-141', 'FGDC-143'])
        with patch('sys.argv', ['modern_batch', 'validate', '--output-dir', self.paths.base, '--manifest', str(manifest)]), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 0)
        self.assertEqual(json.loads(out.getvalue())['valid'], True)
        with patch('sys.argv', argv), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 1)  # the same batch id is never replaced
        self.assertIn('already exists', json.loads(out.getvalue())['reason'])
        with patch('sys.argv', ['modern_batch', 'validate', '--output-dir', self.paths.base, '--manifest', str(manifest) + '.missing']), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 1)
        self.assertEqual(json.loads(out.getvalue())['held'], True)
        with patch('sys.argv', argv[:5] + ['drafts-cli-002'] + argv[6:] + ['--allow', 'FGDC-141,FGDC-143']), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 1)  # an allowance needs --allowed-by
        self.assertFalse((manifest.parent / 'drafts-cli-002.manifest.json').exists())
        with patch('sys.argv', argv[:5] + ['drafts-cli-002'] + argv[6:] + ['--allow', 'FGDC-141,FGDC-143', '--allowed-by', 'x']), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 1)  # these two are not twins, so the allowance is stale
        self.assertIn('matches no twin', json.loads(out.getvalue())['reason'])
        twin = [{'source_id': 'FGDC-148', 'source_sha256': 'z' * 64,
                 'title_key': json.loads(manifest.read_bytes())['members'][0]['title_key']}]
        self.journal({'FGDC-148': {'phase': 'verified'}})
        with patch('scripts.modern_batch.attempted_facts', return_value=twin), \
                patch('sys.argv', argv[:5] + ['drafts-cli-003'] + argv[6:] + ['--allow', 'FGDC-148,FGDC-141', '--allowed-by', 'Brett',
                                                                            '--allow-note', 'two surveys']), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 0)
        recorded = json.loads((manifest.parent / 'drafts-cli-003.manifest.json').read_bytes())['allowances']
        self.assertEqual(recorded, [{'sources': ['FGDC-141', 'FGDC-148'], 'allowed_by': 'Brett', 'note': 'two surveys', 'origin': 'cli'}])
        with patch('sys.argv', ['modern_batch', 'allow', '--output-dir', self.paths.base, '--name', 'sablefish-1980',
                                '--sources', 'FGDC-143,FGDC-141', '--allowed-by', 'Brett', '--note', 'distinct surveys']), \
                patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(batch.main(), 0)
        entry = json.loads(out.getvalue())
        self.assertEqual(json.loads(Path(entry['allowance']).read_bytes())['sources'], ['FGDC-141', 'FGDC-143'])
        self.assertEqual([a['origin'] for a in batch.load_registry(self.paths)], ['registry:sablefish-1980.json'])


if __name__ == '__main__':
    unittest.main()
