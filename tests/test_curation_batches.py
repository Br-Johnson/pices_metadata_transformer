"""Offline correction cohorts compile to the existing, source-bound decisions."""
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from copy import deepcopy
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

    def run_cli(self, argv):
        # Exercise the actual parser/main while inheriting the offline I/O guards.
        from scripts.curation_batches import main
        error = io.StringIO()
        with redirect_stderr(error):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, error.getvalue()

    def test_cli_compiles_exact_cohort_without_modifying_originals(self):
        manifest = self.root / 'batches.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'batches': [self.batch]}))
        decisions = self.root / 'decisions.json'
        audit = self.root / 'audit.json'
        code, error = self.run_cli([
            '--sources', str(self.sources),
            '--manifest', str(manifest), '--decisions-out', str(decisions),
            '--audit-out', str(audit)])
        self.assertEqual(code, 0, error)
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

    def test_all_active_equal_owners_must_be_superseded(self):
        equal = dict(deepcopy(self.batch), batch_id='equal')
        later = dict(deepcopy(self.batch), batch_id='later', supersedes=['example-date'])
        later['correction']['metadata']['publication_date'] = '2002-05-01'
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.compile([self.batch, equal, later])
        later['supersedes'].append('equal')
        decisions, audit = self.compile([self.batch, equal, later])
        self.assertEqual(decisions['FGDC1']['metadata']['publication_date'], '2002-05-01')
        self.assertEqual(audit['overlaps'][-1]['resolution'], 'superseded')

    def test_residual_selector_is_exact_and_rejects_missing_or_malformed(self):
        batch = deepcopy(self.batch)
        batch['selector'] = {'normalization': 'strip_xml_text', 'source_ids': ['FGDC1']}
        batch['members'] = batch['members'][:1]
        decisions, _ = self.compile([batch])
        self.assertEqual(list(decisions), ['FGDC1'])
        for source_id in ('absent', 'broken'):
            (self.sources / 'broken.xml').write_bytes(b'<broken')
            batch['selector']['source_ids'] = [source_id]
            with self.assertRaises(ValueError):
                self.compile([batch])

    def test_artifact_tokens_bind_each_source_and_validate(self):
        from scripts.curation_batches import validate_outputs
        batch = deepcopy(self.batch)
        provenance = {key: batch[key] for key in ('reviewer', 'reviewed_at', 'rationale')}
        batch['correction']['artifact_policy'] = dict(provenance, schema_version=1,
            object_kind='original_fgdc_xml', resource_type='other',
            date_semantics='source_metadata_date', rights_evidence='Fixture CC BY 4.0',
            date_evidence='Fixture metd', source_sha256='$source_sha256')
        batch['correction']['content_classification'] = dict(provenance,
            inventory_complete=True, files=[{'name': '$source_filename',
            'role': 'descriptive_metadata', 'evidence': 'Fixture original XML'}])
        batch['correction']['artifact_policy'].update(rights_scope='original_fgdc_xml',
            rights_source_xpath='./metainfo/metuc', license='cc-by-4.0')
        batch['correction']['artifact_policy']['creator_interpretation'] = {
            'manifest_path': 'reviewed-profile.json', 'manifest_sha256': 'a' * 64}
        decisions, _ = self.compile([batch])
        self.assertEqual(decisions['FGDC1']['artifact_policy']['creator_interpretation'],
                         batch['correction']['artifact_policy']['creator_interpretation'])
        self.assertEqual(decisions['FGDC1']['artifact_policy']['source_sha256'], hashlib.sha256(RAW).hexdigest())
        self.assertEqual(decisions['FGDC2']['content_classification']['files'][0]['name'], 'FGDC2.xml')
        self.assertEqual(validate_outputs(decisions, self.sources)['validated_count'], 2)
        for key, value in (('rights_scope', 'underlying_data'),
                           ('rights_source_xpath', './idinfo/useconst'), ('license', 42)):
            invalid = deepcopy(batch)
            invalid['correction']['artifact_policy'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.compile([invalid])
        batch['correction']['artifact_policy']['creator_interpretation']['manifest_sha256'] = 'invalid'
        with self.assertRaises(ValueError):
            self.compile([batch])
        batch['correction']['artifact_policy'].pop('creator_interpretation')
        batch['correction']['artifact_policy']['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.compile([batch])

    def test_source_change_and_source_output_overwrite_fail(self):
        from scripts.curation_batches import validate_outputs
        decisions, _ = self.compile()
        (self.sources / 'FGDC1.xml').write_bytes(RAW + b' ')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            validate_outputs(decisions, self.sources)
        manifest = self.root / 'batches.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'batches': [self.batch]}))
        code, _ = self.run_cli([
            '--sources', str(self.sources), '--manifest', str(manifest),
            '--decisions-out', str(self.sources / 'FGDC1.xml'),
            '--audit-out', str(self.root / 'audit.json')])
        self.assertNotEqual(code, 0)
        self.assertEqual((self.sources / 'FGDC1.xml').read_bytes(), RAW + b' ')
        self.assertFalse((self.root / 'audit.json').exists())

    def test_explicit_blank_license_is_preserved_without_inferred_grant(self):
        self.batch['correction']['metadata']['license'] = ''
        decisions, _ = self.compile()
        self.assertEqual(decisions['FGDC1']['metadata']['license'], '')

    def test_existing_output_hardlink_cannot_overwrite_original(self):
        import os
        target = self.root / 'decisions.json'
        os.link(self.sources / 'FGDC1.xml', target)
        manifest = self.root / 'batches.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'batches': [self.batch]}))
        code, _ = self.run_cli([
            '--sources', str(self.sources), '--manifest', str(manifest),
            '--decisions-out', str(target), '--audit-out', str(self.root / 'audit.json')])
        self.assertNotEqual(code, 0)
        self.assertEqual((self.sources / 'FGDC1.xml').read_bytes(), RAW)

    def test_structured_evidence_survives_and_inventory_is_deterministic(self):
        self.batch['evidence'].append({'kind': 'source_xpath_exact', 'text': 'Example Marine Institute'})
        first = self.compile()
        self.assertEqual(first, self.compile())
        self.assertEqual(first[0]['FGDC1']['curation_batches'][0]['evidence'], self.batch['evidence'])
        (self.sources / 'broken.xml').write_bytes(b'<broken')
        _, audit = self.compile()
        self.assertEqual(audit['unparsed_sources'][0]['source_id'], 'broken')
        (self.sources / 'linked.xml').symlink_to(self.sources / 'FGDC1.xml')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.compile()

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
