"""Bounded creator/context and historical-link corrections preserve source contracts."""
import copy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.citation_creator_interpretation import validate_creator_interpretation
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, metadata_hash, prepare_metadata, read_json

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-03'
CREATORS = DOCS / 'source_credit_citations_319.json'
LINKS = DOCS / 'historical_dataset_linkage_21.json'
PREVIOUS = DOCS / 'literal_citation_extension_229.json'
HOLDS = ['FGDC-1206', 'FGDC-1314', 'FGDC-2552', 'FGDC-2586', 'FGDC-2587', 'FGDC-3779', 'FGDC-3788', 'FGDC-3815']


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class SourceCreditAndLinkageTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(CREATORS)
        self.new = self.manifest['cohorts'][self.manifest['previous_cohort_count']:]
        self.ids = [m['source_id'] for c in self.new for m in c['members']]
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def prepared(self, tmp, ids, creators=CREATORS, links=LINKS):
        from scripts.collection_qa import classify_collection
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        for sid in ids:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        output = Path(tmp) / 'output'
        old = REPO / 'docs/readiness/2026-10-02'
        report = classify_collection(source, output, self.reviewed_at,
            authority_manifest=old / 'rehosting_authority.json',
            access_interpretation_manifest=old / 'contact_source_interpretation.json',
            creator_interpretation_manifest=old / 'exxon_citation_interpretation.json',
            dataset_access_interpretation_manifest=old / 'registration_access_interpretation.json',
            contributor_access_interpretation_manifest=old / 'contributor_source_interpretation.json',
            collective_creator_interpretation_manifest=DOCS / 'dfo_staff_citation_interpretation.json',
            institution_creator_interpretation_manifest=creators,
            source_link_interpretation_manifest=links)
        return report, OutputPaths(str(output), 'sandbox')

    def test_all_319_exact_bindings_and_previous_229_objects(self):
        prior = read_json(PREVIOUS)
        self.assertEqual(self.manifest['cohorts'][:53], prior['cohorts'])
        self.assertEqual(self.manifest['prior_manifest_sha256'], reference(PREVIOUS)['manifest_sha256'])
        self.assertEqual(len(self.ids), 90)
        self.assertTrue(set(self.ids).isdisjoint(HOLDS))
        self.assertEqual(sum(len(c['members']) for c in self.manifest['cohorts']), 319)
        for c in self.manifest['cohorts']:
            for m in c['members']:
                raw = (REPO / 'FGDC' / (m['source_id'] + '.xml')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), m['source_sha256'])
                self.assertEqual(validate_creator_interpretation(reference(CREATORS), m['source_id'],
                    m['source_sha256'], ET.fromstring(raw)), c['creators'])

    def test_mixed_element_and_supplemental_evidence_must_be_exact_without_tree_mutation(self):
        for sid in ['FGDC-3680', 'FGDC-3592', 'FGDC-2243', 'FGDC-2683', 'FGDC-152']:
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            root = ET.fromstring(raw)
            sha = hashlib.sha256(raw).hexdigest()
            before = ET.tostring(root)
            validate_creator_interpretation(reference(CREATORS), sid, sha, root)
            self.assertEqual(ET.tostring(root), before)
            for fault in ('text', 'tail', 'attribute', 'order', 'extra'):
                changed = copy.deepcopy(root)
                node = changed.find('./idinfo/citation/citeinfo/origin') if sid in ('FGDC-3680', 'FGDC-3592') else changed.find('./idinfo/descript/abstract')
                if fault == 'text': node.text = 'Forged credit'
                elif fault == 'tail':
                    if list(node): node[0].tail = 'Forged internal context'
                    else: node.text += 'Forged context'
                elif fault == 'attribute': node.set('role', 'author')
                elif fault == 'order':
                    if len(node) > 1: node[:] = list(reversed(list(node)))
                    else: node.text = 'Different source order'
                else: ET.SubElement(node, 'author').text = 'Inferred'
                with self.subTest(sid=sid, fault=fault), self.assertRaises(ValueError):
                    validate_creator_interpretation(reference(CREATORS), sid, sha, changed)

    def test_forged_creator_context_or_link_membership_fails_even_when_rehashed(self):
        from scripts.source_link_interpretation import validate_source_link_interpretation
        with tempfile.TemporaryDirectory() as tmp:
            for path, sid in ((CREATORS, 'FGDC-3592'), (LINKS, 'FGDC-4186')):
                raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
                root = ET.fromstring(raw)
                for field in ('membership', 'context', 'object', 'scope'):
                    value = read_json(path)
                    if path == CREATORS:
                        c = value['cohorts'][53]
                        if field == 'membership': c['members'][0]['source_id'] = 'FGDC-3815'
                        elif field == 'context': c['context_note'] = 'All original authors'
                        elif field == 'object': c['creators'][0]['orcid'] = 'Invented'
                        else: value['scope'] = 'XML authorship'
                        check = validate_creator_interpretation
                    else:
                        if field == 'membership': value['members'][0]['source_id'] = 'FGDC-3815'
                        elif field == 'context': value['preservation_note'] = 'Modernized URL'
                        elif field == 'object': value['raw_onlink'] = 'https://example.invalid/'
                        else: value['scope'] = 'identity'
                        check = validate_source_link_interpretation
                    forged = Path(tmp) / 'forged.json'
                    atomic_json(forged, value)
                    with self.subTest(path=path.name, field=field), self.assertRaises(ValueError):
                        check(reference(forged), sid, hashlib.sha256(raw).hexdigest(), root)

    def test_actual_90_creators_and_21_links_have_only_declared_metadata_changes(self):
        ids = self.ids + [f'FGDC-{i}' for i in range(4186, 4207)] + HOLDS
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, ids, PREVIOUS, None)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 119, 'failed': 0})
            old = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json')) for sid in ids}
            after, paths = self.prepared(tmp, ids)
            self.assertEqual(after['summary']['source_status_counts'], {'supported': 111, 'held': 8, 'failed': 0})
            profiles = {m['source_id']: c for c in self.new for m in c['members']}
            for sid in ids:
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                metadata = payload['metadata']
                unchanged = {k: v for k, v in metadata.items() if k not in ('creators', 'notes', 'related_identifiers')}
                self.assertEqual(unchanged, {k: v for k, v in old[sid]['metadata'].items() if k not in ('creators', 'notes', 'related_identifiers')})
                if sid in profiles:
                    self.assertEqual(metadata['creators'], profiles[sid]['creators'])
                    self.assertEqual(metadata['related_identifiers'], old[sid]['metadata']['related_identifiers'])
                    self.assertIn('Original primary citation origin', metadata['notes'])
                    if 'primary_origin_element' in profiles[sid]:
                        self.assertIn('XML (parsed representation)', metadata['notes'])
                    if profiles[sid].get('context_note'):
                        self.assertIn(profiles[sid]['context_note'], metadata['notes'])
                elif sid not in HOLDS:
                    self.assertEqual(metadata['creators'], old[sid]['metadata']['creators'])
                    self.assertEqual(metadata['related_identifiers'], [])
                    self.assertEqual(metadata['notes'], old[sid]['metadata']['notes'] + '\n\n' + read_json(LINKS)['preservation_note'])
                else: self.assertEqual(payload, old[sid])
                self.assertEqual(metadata['license'], '')
                self.assertEqual(metadata['access_right'], 'restricted')
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(), (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            self.assertEqual(after, self.prepared(tmp, ids)[0])
            self.assertEqual(after['summary']['remote_verified'], 0)
            self.assertEqual(after['summary']['publication_approved'], 0)

    def test_opt_in_withdrawal_missing_manifest_and_tampered_cache_restore_exact_holds(self):
        ids = ['FGDC-3592', 'FGDC-2645', 'FGDC-152', 'FGDC-4186']
        with tempfile.TemporaryDirectory() as tmp:
            first, paths = self.prepared(tmp, ids)
            self.assertEqual(first['summary']['source_status_counts']['supported'], 4)
            path = Path(paths.zenodo_json_dir) / 'FGDC-4186.json'
            original = read_json(path)
            forged = copy.deepcopy(original)
            forged['metadata']['notes'] = 'Discarded original citation'
            atomic_json(path, forged)
            self.assertEqual(first, self.prepared(tmp, ids)[0])
            self.assertEqual(read_json(path), original)
            for creators, links in ((PREVIOUS, None), (Path(tmp) / 'missing.json', Path(tmp) / 'absent.json'), (None, None)):
                report, _ = self.prepared(tmp, ids, creators, links)
                self.assertEqual(report['summary']['source_status_counts'], {'supported': 0, 'held': 4, 'failed': 0})
                self.assertEqual(read_json(path)['metadata']['related_identifiers'], [{'identifier': 'http://near-goos.coi.gov.cn/', 'relation': 'isAlternateIdentifier'}])

    def test_all_21_link_elements_and_complete_before_after_metadata_hashes(self):
        from scripts.source_link_interpretation import apply_source_link_interpretation, validate_source_link_policy
        from scripts.source_link_interpretation import validate_source_link_interpretation
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, [f'FGDC-{i}' for i in range(4186, 4207)], PREVIOUS, None)
            for m in read_json(LINKS)['members']:
                sid = m['source_id']
                root = ET.parse(REPO / 'FGDC' / (sid + '.xml')).getroot()
                before = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))['metadata']
                profile = validate_source_link_interpretation(reference(LINKS), sid, m['source_sha256'], root)
                after = apply_source_link_interpretation(profile, before)
                policy = {'source_link_interpretation': reference(LINKS)}
                validate_source_link_policy(policy, sid, m['source_sha256'], root, after)
                for fault in ('notes', 'url', 'creator', 'date', 'rights'):
                    changed = copy.deepcopy(after)
                    if fault == 'notes': changed['notes'] = before['notes']
                    elif fault == 'url': changed['related_identifiers'] = [{'identifier': 'https://example.invalid/', 'relation': 'isPartOf'}]
                    elif fault == 'creator': changed['creators'][0]['name'] = 'Invented'
                    elif fault == 'date': changed['publication_date'] = '2000-01-01'
                    else: changed['license'] = 'cc-by-4.0'
                    with self.subTest(sid=sid, fault=fault), self.assertRaises(ValueError):
                        validate_source_link_policy(policy, sid, m['source_sha256'], root, changed)
                changed = copy.deepcopy(root)
                changed.find('./idinfo/citation/citeinfo/onlink').set('role', 'alternate')
                with self.assertRaises(ValueError): validate_source_link_interpretation(reference(LINKS), sid, m['source_sha256'], changed)

    def test_agent_and_both_human_schemas_enforce_credits_context_link_preservation_and_independent_guards(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import prepare_manifest, validate_approval, QA_CHECKS
        for sid in ('FGDC-3592', 'FGDC-2645', 'FGDC-152', 'FGDC-2243', 'FGDC-4186'):
            with tempfile.TemporaryDirectory() as tmp:
                _, paths = self.prepared(tmp, [sid])
                path = Path(paths.zenodo_json_dir) / (sid + '.json')
                payload = read_json(path)
                assess_source(str(path), paths)
                metadata, source, source_sha = prepare_metadata(str(path), paths)
                entry = {'environment': 'sandbox', 'zenodo_url': 'https://sandbox.zenodo.org/deposit/123', 'deposition_id': 123,
                    'upload_status': 'success', 'publish_status': 'draft', 'success': True, 'json_file': str(path),
                    'source_sha256': source_sha, 'metadata_sha256': metadata_hash(metadata), 'artifact_contract': prepare_artifact(payload, source)}
                atomic_json(paths.uploads_registry_path, {sid: entry})
                manifest = prepare_manifest(paths)
                record = manifest['records'][0]
                record['qa'].update(approved=True, reviewer_type='human', reviewer='Offline fixture', reviewed_at=self.reviewed_at,
                    rationale='Dummy fixture, not release authority', checks=dict.fromkeys(QA_CHECKS, True), run_id='fixture',
                    review_revision=manifest['source_revision'], evidence=['fixture'])
                record['duplicate_review'].update(status='reviewed', classification='checked_no_match', rationale='fixture only', evidence=['fixture'])
                for schema in (1, 2):
                    manifest['schema_version'] = schema
                    self.assertTrue(validate_approval(manifest, sid, entry, paths, metadata)['qa']['approved'])
                    for fault in ('type', 'context', 'withdraw', 'license', 'date', 'relation'):
                        changed = copy.deepcopy(payload)
                        if fault == 'type': changed['metadata']['creators'][0]['type'] = 'Person' if sid == 'FGDC-4186' else 'Organization'
                        elif fault == 'context': changed['metadata']['notes'] = 'No source context'
                        elif fault == 'withdraw':
                            changed['artifact_policy'].pop('source_link_interpretation' if sid == 'FGDC-4186' else 'creator_interpretation')
                        elif fault == 'license': changed['metadata']['license'] = 'cc-by-4.0'
                        elif fault == 'date': changed['metadata']['publication_date'] = '2000-01-01'
                        else: changed['metadata']['related_identifiers'] = [{'identifier': 'https://example.invalid/', 'relation': 'isPartOf'}]
                        atomic_json(path, changed)
                        with self.subTest(sid=sid, schema=schema, fault=fault), self.assertRaises(ValueError): assess_source(str(path), paths)
                        with self.subTest(sid=sid, schema=schema, fault=fault), self.assertRaises(ValueError): validate_approval(manifest, sid, entry, paths, metadata)
                        atomic_json(path, payload)


if __name__ == '__main__':
    unittest.main()
