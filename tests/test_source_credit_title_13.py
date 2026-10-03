"""Bounded source credits/titles preserve full context and independent gates."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.citation_creator_interpretation import validate_creator_interpretation
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, read_json, metadata_hash, prepare_metadata

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-03'
CREDITS = DOCS / 'source_citation_credits_401.json'
PREVIOUS = DOCS / 'access_held_source_citations_396.json'
TITLES = DOCS / 'source_display_titles_8.json'
CREDIT_IDS = {'FGDC-3779', 'FGDC-3815', 'FGDC-3958', 'FGDC-3959', 'FGDC-3965'}


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class SourceCreditTitleTests(unittest.TestCase):
    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.titles = {m['source_id']: m for m in read_json(TITLES)['members']}

    def prepared(self, tmp, ids, credits=CREDITS, titles=TITLES):
        from scripts.collection_qa import classify_collection
        source = Path(tmp) / 'sources'
        source.mkdir(exist_ok=True)
        for stale in source.glob('*.xml'):
            if stale.stem not in ids:
                stale.unlink()
        for sid in ids:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        output = Path(tmp) / 'output'
        old = REPO / 'docs/readiness/2026-10-02'
        report = classify_collection(source, output, self.reviewed_at,
            authority_manifest=old / 'rehosting_authority.json',
            access_interpretation_manifest=old / 'contact_source_interpretation.json',
            creator_interpretation_manifest=old / 'exxon_citation_interpretation.json',
            dataset_access_interpretation_manifest=DOCS / 'finite_source_resource_access_264.json',
            contributor_access_interpretation_manifest=old / 'contributor_source_interpretation.json',
            collective_creator_interpretation_manifest=DOCS / 'dfo_staff_citation_interpretation.json',
            institution_creator_interpretation_manifest=credits,
            source_link_interpretation_manifest=DOCS / 'historical_dataset_linkage_21.json',
            source_title_interpretation_manifest=titles)
        return report, OutputPaths(str(output), 'sandbox')

    def test_exact_401_creators_preserve_previous_396_and_all_source_bindings(self):
        manifest = read_json(CREDITS)
        self.assertEqual(manifest['cohorts'][:220], read_json(PREVIOUS)['cohorts'])
        self.assertEqual(manifest['prior_manifest_sha256'], reference(PREVIOUS)['manifest_sha256'])
        added = {m['source_id'] for c in manifest['cohorts'][220:] for m in c['members']}
        self.assertEqual(added, CREDIT_IDS)
        self.assertEqual(sum(len(c['members']) for c in manifest['cohorts']), 401)
        for c in manifest['cohorts']:
            for m in c['members']:
                raw = (REPO / 'FGDC' / (m['source_id'] + '.xml')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), m['source_sha256'])
                self.assertEqual(validate_creator_interpretation(reference(CREDITS), m['source_id'], m['source_sha256'], ET.fromstring(raw)), c['creators'])
        self.assertTrue(all('type' not in creator for c in manifest['cohorts'][220:] for creator in c['creators']))

    def test_all_13_bounded_corrections_and_context_preservation(self):
        ids = CREDIT_IDS | set(self.titles)
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, ids, PREVIOUS, None)
            old = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json')) for sid in ids}
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 13, 'failed': 0})
            after, paths = self.prepared(tmp, ids)
            self.assertEqual(after['summary']['source_status_counts'], {'supported': 13, 'held': 0, 'failed': 0})
            for row in after['records']:
                sid = row['source_id']; payload = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))
                changed = {'title', 'notes'} if sid in self.titles else {'creators', 'notes'}
                self.assertEqual({k:v for k,v in old[sid]['metadata'].items() if k not in changed}, {k:v for k,v in payload['metadata'].items() if k not in changed})
                if sid in self.titles:
                    self.assertTrue(payload['metadata']['notes'].startswith(old[sid]['metadata']['notes']))
                else:
                    node = ET.parse(REPO / 'FGDC' / (sid + '.xml')).getroot()
                    result = validate_creator_interpretation(reference(CREDITS), sid, row['source_sha256'], node, True)
                    restored = payload['metadata']['notes']
                    for note in result['preservation_notes']:
                        self.assertIn(note, restored)
                        restored = restored.replace('\n' + note, '', 1)
                    old_line = next(line for line in old[sid]['metadata']['notes'].splitlines() if line.startswith('Curator decision: '))
                    new_line = next(line for line in restored.splitlines() if line.startswith('Curator decision: '))
                    old_decision = json.loads(old_line.removeprefix('Curator decision: '))
                    new_decision = json.loads(new_line.removeprefix('Curator decision: '))
                    new_decision['metadata']['creators'] = old_decision['metadata']['creators']
                    self.assertEqual(new_decision, old_decision)
                    self.assertEqual(restored.replace(new_line, old_line, 1), old[sid]['metadata']['notes'])
                self.assertEqual(payload['metadata']['access_right'], 'restricted')
                self.assertEqual(payload['metadata']['license'], '')
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(), (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
                self.assertFalse(row['remote_verified']); self.assertFalse(row['publication_approved'])
                if sid in self.titles:
                    self.assertEqual(payload['metadata']['title'], self.titles[sid]['display_title'])
                    self.assertIn(self.titles[sid]['preservation_note'], payload['metadata']['notes'])
                    self.assertLessEqual(len(payload['metadata']['title']), 250)

    def test_exact_title_context_full_after_images_and_unchanged_retry_fail_closed(self):
        from scripts.source_title_interpretation import validate_source_title_policy, validate_source_title_interpretation
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, self.titles)
            for sid,m in self.titles.items():
                path = Path(paths.zenodo_json_dir) / (sid + '.json'); payload = read_json(path)
                root = ET.parse(REPO / 'FGDC' / (sid + '.xml')).getroot()
                validate_source_title_policy(payload['artifact_policy'], sid, m['source_sha256'], root, payload['metadata'])
                for field in ('title', 'notes', 'creators', 'publication_date', 'license', 'related_identifiers'):
                    altered = copy.deepcopy(payload['metadata']); altered[field] = [{'name':'Invented'}] if field=='creators' else [{'identifier':'https://example.invalid/','relation':'isPartOf'}] if field=='related_identifiers' else 'Invented'
                    with self.subTest(sid=sid,field=field), self.assertRaises(ValueError):
                        validate_source_title_policy(payload['artifact_policy'], sid, m['source_sha256'], root, altered)
                altered = copy.deepcopy(root); altered.find('./idinfo/citation/citeinfo/title').set('inferred','true')
                with self.assertRaises(ValueError): validate_source_title_interpretation(reference(TITLES),sid,m['source_sha256'],altered)
                atomic_json(path, {'metadata':{},'artifact_policy':payload['artifact_policy']})
            first,_ = self.prepared(tmp, self.titles)
            second,_ = self.prepared(tmp, self.titles)
            self.assertEqual(first, second)

    def test_withdrawal_missing_rehashed_evidence_and_independent_holds(self):
        ids = CREDIT_IDS | set(self.titles) | {'FGDC-121','FGDC-565','FGDC-541','FGDC-1422','FGDC-1238'}
        with tempfile.TemporaryDirectory() as tmp:
            accepted,_ = self.prepared(tmp, ids)
            outside = {r['source_id']:r['source_status'] for r in accepted['records'] if r['source_id'] not in CREDIT_IDS | set(self.titles)}
            self.assertTrue(all(status=='held' for status in outside.values()))
            for credits,titles in [(PREVIOUS,None),(Path(tmp)/'missing-creators.json',Path(tmp)/'missing-titles.json')]:
                report,_ = self.prepared(tmp, ids, credits, titles)
                self.assertTrue(all(r['source_status']=='held' for r in report['records']))
            forged = read_json(TITLES); forged['members'][0]['display_title']='Invented'
            path = Path(tmp)/'forged.json'; atomic_json(path,forged)
            report,_ = self.prepared(tmp, self.titles, CREDITS,path)
            self.assertTrue(all(r['source_status']=='held' for r in report['records']))

    def test_agent_and_both_human_schemas_enforce_title_and_creator_evidence(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import prepare_manifest, validate_approval, QA_CHECKS
        for sid in ('FGDC-1922','FGDC-1930','FGDC-3815','FGDC-3958'):
            with tempfile.TemporaryDirectory() as tmp:
                _,paths = self.prepared(tmp,[sid]); path = Path(paths.zenodo_json_dir)/(sid+'.json'); payload=read_json(path)
                assess_source(str(path),paths)
                metadata,source,source_sha=prepare_metadata(str(path),paths)
                entry={'environment':'sandbox','zenodo_url':'https://sandbox.zenodo.org/deposit/123','deposition_id':123,'upload_status':'success','publish_status':'draft','success':True,'json_file':str(path),'source_sha256':source_sha,'metadata_sha256':metadata_hash(metadata),'artifact_contract':prepare_artifact(payload,source)}
                atomic_json(paths.uploads_registry_path,{sid:entry}); manifest=prepare_manifest(paths);record=manifest['records'][0]
                record['qa'].update(approved=True,reviewer_type='human',reviewer='Offline fixture',reviewed_at=self.reviewed_at,rationale='Fixture only',checks=dict.fromkeys(QA_CHECKS,True),run_id='fixture',review_revision=manifest['source_revision'],evidence=['fixture'])
                record['duplicate_review'].update(status='reviewed',classification='checked_no_match',rationale='fixture only',evidence=['fixture'])
                for schema in (1,2):
                    manifest['schema_version']=schema
                    self.assertTrue(validate_approval(manifest,sid,entry,paths,metadata)['qa']['approved'])
                    for fault in ('notes','title','creators','withdraw','external_bytes'):
                        changed=copy.deepcopy(payload)
                        if fault=='withdraw': changed['artifact_policy'].pop('source_title_interpretation' if sid in self.titles else 'creator_interpretation')
                        elif fault=='external_bytes':
                            target=TITLES if sid in self.titles else CREDITS; external=Path(tmp)/'external.json';external.write_bytes(target.read_bytes()+b' ')
                            changed['artifact_policy']['source_title_interpretation' if sid in self.titles else 'creator_interpretation']={'manifest_path':str(external),'manifest_sha256':reference(target)['manifest_sha256']}
                        elif fault=='creators':changed['metadata']['creators'][0]['orcid']='Inferred'
                        else:changed['metadata'][fault]='Discarded source context'
                        atomic_json(path,changed)
                        with self.subTest(sid=sid,schema=schema,fault=fault),self.assertRaises(ValueError):assess_source(str(path),paths)
                        with self.subTest(sid=sid,schema=schema,fault=fault),self.assertRaises(ValueError):validate_approval(manifest,sid,entry,paths,metadata)
                        atomic_json(path,payload)


if __name__ == '__main__':
    unittest.main()
