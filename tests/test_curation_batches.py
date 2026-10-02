"""Offline correction cohorts compile to the existing, source-bound decisions."""
import hashlib
import json
from copy import deepcopy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


RAW = (b'<metadata><idinfo><citation><citeinfo><title>Example survey</title>'
       b'<origin>Example Marine Institute</origin><pubdate>20020101</pubdate>'
       b'</citeinfo></citation><descript><abstract>Original survey description.</abstract>'
       b'</descript><useconst>CC BY 4.0</useconst></idinfo>'
       b'<metainfo><metd>20020430</metd><metuc>CC BY 4.0</metuc></metainfo></metadata>')


class CurationBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = self.root / 'FGDC'
        self.sources.mkdir()
        for name in ('FGDC1', 'FGDC2'):
            (self.sources / (name + '.xml')).write_bytes(RAW)
        (self.sources / 'FGDC3.xml').write_bytes(RAW.replace(
            b'Example Marine Institute', b'Other Marine Institute'))
        self.batch = {
            'batch_id': 'example-date', 'version': 1,
            'selector': {'normalization': 'strip_xml_text', 'fgdc_paths_equal': {
                'idinfo/citation/citeinfo/origin': ['Example Marine Institute']}},
            'members': [{'source_id': name, 'source_sha256': hashlib.sha256(RAW).hexdigest()}
                        for name in ('FGDC1', 'FGDC2')],
            'correction': {'metadata': {'publication_date': '2002-04-30'}},
            'reviewer': 'Fixture reviewer', 'reviewed_at': '2026-01-01T00:00:00Z',
            'rationale': 'Fixture metadata date correction, supported by metainfo/metd.',
            'evidence': ['Source XML metainfo/metd: 20020430'],
        }

    def test_cli_compiles_exact_cohort_without_modifying_originals(self):
        manifest = self.root / 'batches.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'batches': [self.batch]}))
        decisions = self.root / 'decisions.json'
        audit = self.root / 'audit.json'
        result = subprocess.run([
            sys.executable, '-m', 'scripts.curation_batches', '--sources', str(self.sources),
            '--manifest', str(manifest), '--decisions-out', str(decisions),
            '--audit-out', str(audit)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        compiled = json.loads(decisions.read_text())
        self.assertEqual(set(compiled), {'FGDC1', 'FGDC2'})
        for name in compiled:
            self.assertEqual(compiled[name]['metadata'], {'publication_date': '2002-04-30'})
            self.assertEqual(compiled[name]['source_sha256'], hashlib.sha256(RAW).hexdigest())
            self.assertEqual((self.sources / (name + '.xml')).read_bytes(), RAW)
        receipt = json.loads(audit.read_text())
        self.assertEqual(receipt['batches'][0]['member_count'], 2)
        self.assertEqual(receipt['output_validation']['validated_count'], 2)

    def compile(self, batches=None):
        from scripts.curation_batches import compile_batches
        return compile_batches([{'schema_version': 1, 'batches': batches or [self.batch]}], self.sources)

    def test_invalid_or_unknown_contract_fields_fail_closed(self):
        from scripts.curation_batches import compile_batches
        for location, key, value in (
                ('root', 'schema_version', 2), ('root', 'new_policy', True),
                ('batch', 'version', 2), ('batch', 'new_policy', True),
                ('batch', 'reviewer', ''), ('batch', 'reviewed_at', '2026-01-01'),
                ('batch', 'rationale', ''), ('batch', 'evidence', []),
                ('selector', 'normalization', 'eval'),
                ('selector', 'code', 'anything'),
                ('correction', 'notes', 'Not an allowed raw metadata override')):
            batch = deepcopy(self.batch)
            manifest = {'schema_version': 1, 'batches': [batch]}
            target = manifest if location == 'root' else batch if location == 'batch' else batch[location]
            target[key] = value
            with self.subTest(location=location, key=key), self.assertRaises(ValueError):
                compile_batches([manifest], self.sources)
        for overrides in ({'title': 'New title'}, {'creators': []},
                          {'creators': [{'name': 'Person', 'invented_field': 'Anything'}]},
                          {'publication_date': 'Unknown'}, {'license': None}):
            batch = deepcopy(self.batch)
            batch['correction']['metadata'] = overrides
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.compile([batch])

    def test_stale_missing_extra_and_duplicate_members_fail_closed(self):
        for members in (self.batch['members'][:1], self.batch['members'] + self.batch['members'][:1],
                        self.batch['members'] + [{'source_id': 'FGDC3', 'source_sha256': '0' * 64}],
                        [dict(member, source_sha256='0' * 64) for member in self.batch['members']]):
            batch = dict(self.batch, members=members)
            with self.subTest(members=members), self.assertRaises(ValueError):
                self.compile([batch])

    def test_conflicting_overlap_requires_explicit_prior_batch_supersession(self):
        later = deepcopy(self.batch)
        later.update(batch_id='later-date', correction={'metadata': {'publication_date': '2002-05-01'}})
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.compile([self.batch, later])
        later['supersedes'] = ['example-date']
        decisions, audit = self.compile([self.batch, later])
        self.assertEqual(decisions['FGDC1']['metadata']['publication_date'], '2002-05-01')
        self.assertEqual([item['batch_id'] for item in decisions['FGDC1']['curation_batches']],
                         ['example-date', 'later-date'])
        self.assertEqual(len(audit['overlaps']), 2)
        later['supersedes'] = ['absent']
        with self.assertRaises(ValueError):
            self.compile([self.batch, later])

    def test_disjoint_fields_and_identical_values_preserve_every_review(self):
        later = deepcopy(self.batch)
        later.update(batch_id='creator-fix', reviewer='Second reviewer',
                     correction={'metadata': {'creators': [{'name': 'Example Marine Institute', 'type': 'Organization'}]}})
        same = dict(deepcopy(self.batch), batch_id='same-date')
        decisions, audit = self.compile([self.batch, later, same])
        value = decisions['FGDC1']
        self.assertEqual(set(value['metadata']), {'publication_date', 'creators'})
        self.assertEqual([item['batch_id'] for item in value['curation_batches']],
                         ['example-date', 'creator-fix', 'same-date'])
        self.assertIn('Second reviewer', value['reviewer'])
        self.assertEqual(len(audit['overlaps']), 2)

    def test_duplicate_batch_ids_and_json_keys_are_rejected(self):
        from scripts.curation_batches import load_manifest
        with self.assertRaises(ValueError):
            self.compile([self.batch, self.batch])
        path = self.root / 'duplicate.json'
        path.write_text('{"schema_version":1,"schema_version":2,"batches":[]}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            load_manifest(path)


if __name__ == '__main__':
    unittest.main()
