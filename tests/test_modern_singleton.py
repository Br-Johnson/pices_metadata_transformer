"""Real-source mapping fidelity for the exact finite NCDC cohort; no live I/O."""

import copy
import html
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import modern_singleton as mapping
from scripts.agent_qa import assess_source
from scripts.path_config import OutputPaths
from tests.modern_singleton_fixtures import prepare_sources


class ModernSingletonMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.prepared_root = prepare_sources(cls.fixture.name)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        prepared = Path(self.temp.name) / 'prepared'
        shutil.copytree(self.prepared_root, prepared)
        self.paths = OutputPaths(str(prepared), 'production')
        self.json_file = Path(self.paths.zenodo_json_dir) / 'FGDC-141.json'

    def test_all_19_preserve_complete_legacy_metadata_and_original_bytes(self):
        for member in mapping.cohort()['members']:
            sid = member['source_id']
            with self.subTest(source=sid):
                json_file = Path(self.paths.zenodo_json_dir) / (sid + '.json')
                first = mapping.prepare(json_file, self.paths)
                self.assertEqual(first, mapping.prepare(json_file, self.paths))
                metadata, digest, artifact, _ = assess_source(json_file, self.paths)
                value = mapping.parse(first.body)
                self.assertEqual(mapping.sha(first.xml), digest)
                self.assertEqual(first.xml, (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes())
                self.assertEqual(first.evidence['artifact_contract'], artifact)
                preserved = value['metadata']['additional_descriptions'][0]['description']
                self.assertTrue(preserved.startswith('<p>' + mapping.PRESERVATION_LABEL + '</p><pre>'))
                self.assertEqual(json.loads(html.unescape(preserved.split('<pre>', 1)[1][:-6])), metadata)
                self.assertEqual(value['metadata']['publication_date'], metadata['publication_date'])
                self.assertEqual(value['metadata']['publisher'], 'Zenodo')
                self.assertEqual(value['access'], {'record': 'public', 'files': 'restricted'})
                self.assertNotIn('rights', value['metadata'])

    def test_141_uses_exact_metadata_date_and_org_not_dataset_date_or_person(self):
        prepared = mapping.prepare(self.json_file, self.paths)
        value = mapping.parse(prepared.body)['metadata']
        self.assertEqual(value['publication_date'], '1999-05-25')
        self.assertIn(b'<pubdate>19420301</pubdate>', prepared.xml)
        self.assertEqual(value['creators'][0]['person_or_org']['type'], 'organizational')
        self.assertEqual(value['creators'][0]['person_or_org']['name'], mapping.cohort()['creators'][0]['name'])
        self.assertEqual(len(prepared.xml), 4523)
        self.assertEqual(mapping.sha(prepared.xml), '3f53f9d0d1d49631ccb6c2885312d3282870c32bd392abe57bd035f8cc139b27')

    def test_missing_or_modified_finite_evidence_holds(self):
        for name in ('PROFILE', 'PLAN'):
            changed = Path(self.temp.name) / (name + '.json')
            changed.write_bytes(getattr(mapping, name).read_bytes() + b' ')
            with self.subTest(evidence=name), patch.object(mapping, name, changed), self.assertRaises(ValueError):
                mapping.prepare(self.json_file, self.paths)

    def test_outside_cohort_and_protected_or_class_member_cannot_prepare(self):
        for sid in ('FGDC-885', 'FGDC-1238', 'FGDC-2953'):
            changed = Path(self.paths.zenodo_json_dir) / (sid + '.json')
            changed.write_bytes(self.json_file.read_bytes())
            with self.subTest(source=sid), self.assertRaises(ValueError):
                mapping.prepare(changed, self.paths)

    def test_changed_creator_date_rights_or_raw_source_fails_fresh_assessment(self):
        original = self.json_file.read_bytes()
        for key, value in [('creators', [{'name': 'Invented', 'type': 'Organization'}]),
                           ('publication_date', '2026-10-05'), ('license', 'cc-by-4.0'),
                           ('access_right', 'open')]:
            payload = mapping.parse(original)
            payload['metadata'][key] = value
            self.json_file.write_bytes(mapping.encode(payload))
            with self.subTest(field=key), self.assertRaises(ValueError):
                mapping.prepare(self.json_file, self.paths)
        self.json_file.write_bytes(original)
        raw = Path(self.paths.original_fgdc_dir) / 'FGDC-141.xml'
        raw.write_bytes(raw.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            mapping.prepare(self.json_file, self.paths)

    def test_modern_remote_comparison_preserves_html_and_semantic_fields(self):
        expected = mapping.parse(mapping.prepare(self.json_file, self.paths).body)['metadata']
        actual = copy.deepcopy(expected)
        actual['resource_type']['title'] = {'en': 'Other'}
        actual['additional_descriptions'][0]['type']['title'] = {'en': 'Other'}
        actual['creators'][0]['person_or_org']['identifiers'] = []
        actual['rights'] = []
        mapping.compare_metadata(actual, expected)
        for key, value in [('publisher', 'Another host'), ('rights', [{'id': 'cc-by-4.0'}]),
                           ('related_identifiers', [{'identifier': 'invented'}]),
                           ('description', expected['description'] + 'Changed')]:
            changed = copy.deepcopy(actual)
            changed[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                mapping.compare_metadata(changed, expected)
        actual['additional_descriptions'][0]['description'] = actual['additional_descriptions'][0]['description'].replace('<pre>', '')
        with self.assertRaises(ValueError):
            mapping.compare_metadata(actual, expected)

    def test_separate_legacy_wire_source_and_policy_bindings(self):
        prepared = mapping.prepare(self.json_file, self.paths)
        evidence = prepared.evidence
        self.assertNotEqual(evidence['legacy_metadata_sha256'], evidence['wire_sha256'])
        self.assertEqual(evidence['wire_sha256'], mapping.sha(prepared.body))
        self.assertEqual(prepared.binding, mapping.sha(mapping.encode(evidence)))
        with patch.object(mapping, 'runtime_binding', return_value='f' * 64):
            self.assertNotEqual(prepared.binding, mapping.prepare(self.json_file, self.paths).binding)


class SameTextTests(unittest.TestCase):
    def test_quote_entities_compare_equal_and_nothing_else_is_repaired(self):
        from scripts.modern_singleton import same_text
        self.assertTrue(same_text('a "b" c', 'a &quot;b&quot; c'))
        self.assertTrue(same_text("it's", 'it&#39;s'))
        self.assertTrue(same_text('x &quot;y&quot;', 'x "y"'))
        self.assertFalse(same_text('<p>a</p>', '&lt;p&gt;a&lt;/p&gt;'))
        self.assertFalse(same_text('a &amp; b', 'a & b'))
        self.assertFalse(same_text('a "b"', 'a "c"'))
        self.assertFalse(same_text(None, 'a'))

    def test_width_folding_compares_equal_and_other_sanitizer_repairs_do_not(self):
        """ftfy.fix_text folds half-width and full-width forms and composes to NFC; nothing wider."""
        from scripts.modern_singleton import WIDTH_FOLD, same_text
        self.assertEqual((len(WIDTH_FOLD), WIDTH_FOLD[0x3000], WIDTH_FOLD[0xFF92]), (226, ' ', '\u30e1'))
        self.assertTrue(same_text('People\u30e1s Republic', 'People\uff92s Republic'))  # U+FF92 stored as U+30E1
        self.assertTrue(same_text('13\u30e824 km', '13\uff9624 km'))
        self.assertTrue(same_text('4 \u1172 10 m', '4 \uffd7 10 m'))
        self.assertTrue(same_text('\u30ac', '\uff76\uff9e'))  # half-width KA + voiced mark compose to GA
        self.assertTrue(same_text('\uac00', '\uffa1\uffc2'))  # half-width jamo compose to a syllable
        self.assertTrue(same_text('A 1', '\uff21\u3000\uff11'))  # full-width Latin and the ideographic space
        self.assertTrue(same_text('\u00e9', 'e\u0301'))  # NFC composition on both sides
        self.assertFalse(same_text('fi', '\ufb01'))  # ligatures are not folded: not observed
        self.assertFalse(same_text('1', '\u2460'))  # other compatibility characters stay literal
        self.assertFalse(same_text('\u03bc', '\u00b5'))  # the micro sign is not folded
        self.assertFalse(same_text('a b', 'a\u00a0b'))  # the no-break space stays literal
        self.assertFalse(same_text("it's", 'it\u2019s'))  # curly quotes stay literal
        self.assertFalse(same_text('ab', 'a\u200bb'))  # zero-width space removal is not tolerated
        self.assertFalse(same_text('ab', 'a\x08b'))  # nor control-character removal
        self.assertFalse(same_text('ab', ' ab'))  # nor stripped whitespace
        self.assertFalse(same_text('e\u0301', 'e'))  # a real difference still differs

    def test_compare_metadata_accepts_folded_descriptions_but_not_folded_titles(self):
        from scripts.modern_singleton import Held, compare_metadata
        expected = {'resource_type': {'id': 'other'}, 'title': 'T \uff92', 'publisher': 'Zenodo',
                    'publication_date': '2001-01-01', 'description': 'People\uff92s Republic',
                    'subjects': [{'subject': 'a'}],
                    'creators': [{'person_or_org': {'type': 'organizational', 'name': 'Org'}}],
                    'additional_descriptions': [{'type': {'id': 'other'}, 'description': '<pre>13\uff9624</pre>'}]}
        stored = {**expected, 'description': 'People\u30e1s Republic',
                  'additional_descriptions': [{'type': {'id': 'other', 'title': {'en': 'Other'}},
                                               'description': '<pre>13\u30e824</pre>'}]}
        compare_metadata(stored, expected)
        with self.assertRaises(Held):  # the title comparison stays byte-exact
            compare_metadata({**stored, 'title': 'T \u30e1'}, expected)
        with self.assertRaises(Held):
            compare_metadata({**stored, 'description': 'People\u2019s Republic'}, expected)

    def test_compare_metadata_accepts_decoded_quotes_in_descriptions_only(self):
        from scripts.modern_singleton import Held, compare_metadata
        expected = {'resource_type': {'id': 'other'}, 'title': 'T &quot;q&quot;', 'publisher': 'Zenodo',
                    'publication_date': '2001-01-01', 'description': 'about &quot;x&quot; here',
                    'subjects': [{'subject': 'a'}],
                    'creators': [{'person_or_org': {'type': 'organizational', 'name': 'Org'}}],
                    'additional_descriptions': [{'type': {'id': 'other'}, 'description': '<pre>{&quot;k&quot;:1}</pre>'}]}
        stored = {**expected, 'description': 'about "x" here',
                  'additional_descriptions': [{'type': {'id': 'other', 'title': {'en': 'Other'}},
                                               'description': '<pre>{"k":1}</pre>'}]}
        compare_metadata(stored, expected)
        with self.assertRaises(Held):
            compare_metadata({**stored, 'title': 'T "q"'}, expected)
        with self.assertRaises(Held):
            compare_metadata({**stored, 'description': 'about "y" here'}, expected)


if __name__ == '__main__':
    unittest.main()
