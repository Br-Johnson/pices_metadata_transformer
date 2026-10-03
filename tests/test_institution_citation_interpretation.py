"""Exact institutional citation profiles; source attribution is not XML authorship."""
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
from scripts.upload_service import atomic_json, metadata_hash, prepare_metadata, read_json

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / 'docs/readiness/2026-10-03/institution_citation_interpretation.json'
DOCS = REPO / 'docs/readiness/2026-10-02'


class InstitutionCitationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = read_json(MANIFEST)
        self.reference = {'manifest_path': str(MANIFEST),
                          'manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
        self.cohorts = self.manifest['cohorts']
        self.members = [member for cohort in self.cohorts for member in cohort['members']]
        # Four first members are ordinary creator-only sources in the audited cohort.
        self.examples = [cohort['members'][0]['source_id'] for cohort in self.cohorts]
        self.reviewed_at = datetime.now(timezone.utc).isoformat()

    def validate(self, cohort, member, reference=None, root=None):
        if root is None:
            root = ET.parse(REPO/'FGDC'/(member['source_id']+'.xml')).getroot()
        return validate_creator_interpretation(reference or self.reference,
            member['source_id'],member['source_sha256'],root)

    def prepared(self, tmp, enabled=True, source_ids=None, manifest=MANIFEST):
        from scripts.collection_qa import classify_collection
        source=Path(tmp)/'sources';source.mkdir(exist_ok=True)
        for source_id in source_ids or self.examples:
            shutil.copyfile(REPO/'FGDC'/(source_id+'.xml'),source/(source_id+'.xml'))
        kwargs=dict(authority_manifest=DOCS/'rehosting_authority.json',
            access_interpretation_manifest=DOCS/'contact_source_interpretation.json',
            creator_interpretation_manifest=DOCS/'exxon_citation_interpretation.json',
            dataset_access_interpretation_manifest=DOCS/'registration_access_interpretation.json',
            contributor_access_interpretation_manifest=DOCS/'contributor_source_interpretation.json',
            collective_creator_interpretation_manifest=REPO/'docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json')
        if enabled:
            kwargs['institution_creator_interpretation_manifest']=manifest
        report=classify_collection(source,Path(tmp)/'output',self.reviewed_at,**kwargs)
        paths=OutputPaths(str(Path(tmp)/'output'),'sandbox')
        return report,paths

    def test_all_72_exact_source_hashes_and_full_literal_creator_objects(self):
        self.assertEqual([len(c['members']) for c in self.cohorts],[26,19,20,7])
        self.assertEqual(len({m['source_id'] for m in self.members}),72)
        for cohort in self.cohorts:
            for member in cohort['members']:
                raw=(REPO/'FGDC'/(member['source_id']+'.xml')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),member['source_sha256'])
                self.assertEqual(self.validate(cohort,member,root=ET.fromstring(raw)),cohort['creators'])

    def test_rehashed_membership_name_type_affiliation_or_cohort_forgery_rejected(self):
        cohort=self.cohorts[0];member=cohort['members'][0]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'forged.json'
            for fault in ('add','remove','hash','swap','split','expand','type','affiliation','identifier','scope'):
                m=copy.deepcopy(self.manifest);c=m['cohorts'][0]
                if fault=='add':c['members'].append({'source_id':'outside','source_sha256':'0'*64})
                elif fault=='remove':c['members'].pop()
                elif fault=='hash':c['members'][0]['source_sha256']='0'*64
                elif fault=='swap':c['members'][0],m['cohorts'][1]['members'][0]=m['cohorts'][1]['members'][0],c['members'][0]
                elif fault=='split':c['creators']=[{'name':'North Pacific'},{'name':'Marine Science Organization'}]
                elif fault=='expand':c['creators'][0]['name']='Expanded inferred name'
                elif fault=='type':c['creators'][0]['type']='Organization'
                elif fault=='affiliation':c['creators'][0]['affiliation']='Inferred hierarchy'
                elif fault=='identifier':c['creators'][0]['orcid']='inferred'
                else:m['scope']='xml_authorship'
                p.write_text(json.dumps(m))
                ref={'manifest_path':str(p),'manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                with self.subTest(fault=fault),self.assertRaises(ValueError):self.validate(cohort,member,ref)

    def test_changed_source_shape_identity_and_same_literal_nonmember_are_rejected(self):
        c=self.cohorts[0];m=c['members'][0]
        for fault in ('text','attribute','child','repeated'):
            root=ET.parse(REPO/'FGDC'/(m['source_id']+'.xml')).getroot()
            node=root.find('./idinfo/citation/citeinfo/origin')
            if fault=='text':node.text+=' and Another Person'
            elif fault=='attribute':node.set('role','author')
            elif fault=='child':ET.SubElement(node,'extra').text='New author'
            else:root.find('./idinfo/citation/citeinfo').append(copy.deepcopy(node))
            with self.subTest(fault=fault),self.assertRaises(ValueError):self.validate(c,m,root=root)
        for field,value in [('source_id','outside'),('source_sha256','0'*64)]:
            root=ET.parse(REPO/'FGDC'/(m['source_id']+'.xml')).getroot()
            with self.subTest(field=field),self.assertRaises(ValueError):self.validate(c,{**m,field:value},root=root)

    def test_opt_in_preserves_entire_metadata_original_rights_and_authorship_caveat(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            before,paths=self.prepared(tmp,False)
            old={sid:read_json(Path(paths.zenodo_json_dir)/(sid+'.json'))['metadata'] for sid in self.examples}
            self.assertEqual(before['summary']['source_status_counts']['held'],4)
            after,paths=self.prepared(tmp)
            self.assertEqual(after['summary']['source_status_counts']['supported'],4)
            for sid in self.examples:
                p=Path(paths.zenodo_json_dir)/(sid+'.json');payload=read_json(p)
                self.assertEqual(payload['metadata'],old[sid])
                self.assertEqual(payload['metadata']['license'],'')
                self.assertEqual(payload['metadata']['access_right'],'restricted')
                self.assertIn('XML authorship is not independently established',payload['metadata']['notes'])
                self.assertEqual((Path(paths.original_fgdc_dir)/(sid+'.xml')).read_bytes(),(REPO/'FGDC'/(sid+'.xml')).read_bytes())
                assess_source(str(p),paths)
            self.assertEqual(after['summary']['remote_verified'],0)
            self.assertEqual(after['summary']['publication_approved'],0)

    def test_agent_full_creator_objects_and_independent_date_rights_remain_checked(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            _,paths=self.prepared(tmp);p=Path(paths.zenodo_json_dir)/(self.examples[0]+'.json')
            original=read_json(p)
            for fault in ('name','split','type','affiliation','identifier','withdraw','date','license','access','authority'):
                payload=copy.deepcopy(original)
                if fault=='name':payload['metadata']['creators'][0]['name']='Inferred author'
                elif fault=='split':payload['metadata']['creators'].append({'name':'Contact Person'})
                elif fault=='type':payload['metadata']['creators'][0]['type']='Organization'
                elif fault=='affiliation':payload['metadata']['creators'][0]['affiliation']='Inferred affiliation'
                elif fault=='identifier':payload['metadata']['creators'][0]['orcid']='inferred'
                elif fault=='withdraw':payload['artifact_policy'].pop('creator_interpretation')
                elif fault=='date':payload['metadata']['publication_date']='2000-01-01'
                elif fault=='license':payload['metadata']['license']='cc-by-4.0'
                elif fault=='access':payload['metadata']['access_right']='open'
                else:payload['artifact_policy'].pop('rehosting_authority')
                atomic_json(p,payload)
                with self.subTest(fault=fault),self.assertRaises(ValueError):assess_source(str(p),paths)

    def test_human_schema1_and_schema2_recheck_manifest_and_full_creator_objects(self):
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import prepare_manifest,validate_approval,QA_CHECKS
        with tempfile.TemporaryDirectory() as tmp:
            _,paths=self.prepared(tmp);sid=self.examples[0];p=Path(paths.zenodo_json_dir)/(sid+'.json')
            original=read_json(p);metadata,source,digest=prepare_metadata(str(p),paths)
            artifact=prepare_artifact(original,source)
            entry={'environment':'sandbox','zenodo_url':'https://sandbox.zenodo.org/deposit/123',
                'deposition_id':123,'upload_status':'success','publish_status':'draft','success':True,
                'json_file':str(p),'source_sha256':digest,'metadata_sha256':metadata_hash(metadata),'artifact_contract':artifact}
            atomic_json(paths.uploads_registry_path,{sid:entry})
            manifest=prepare_manifest(paths);record=manifest['records'][0]
            record['qa'].update(approved=True,reviewer_type='human',reviewer='Offline fixture only',
                reviewed_at=self.reviewed_at,rationale='Dummy human QA for contract test, not real approval',
                checks=dict.fromkeys(QA_CHECKS,True),run_id='fixture',review_revision=manifest['source_revision'],evidence=['fixture'])
            record['duplicate_review'].update(status='reviewed',classification='checked_no_match',rationale='fixture',evidence=['fixture'])
            for schema in (1,2):
                manifest['schema_version']=schema
                self.assertTrue(validate_approval(manifest,sid,entry,paths,metadata)['qa']['approved'])
                for fault in ('name','affiliation','digest','withdraw'):
                    payload=copy.deepcopy(original)
                    if fault in ('name','affiliation'):payload['metadata']['creators'][0][fault]='Changed'
                    elif fault=='digest':payload['artifact_policy']['creator_interpretation']['manifest_sha256']='0'*64
                    else:payload['artifact_policy'].pop('creator_interpretation')
                    atomic_json(p,payload)
                    with self.subTest(schema=schema,fault=fault),self.assertRaises(ValueError):validate_approval(manifest,sid,entry,paths,metadata)
                    atomic_json(p,original)

    def test_explicit_withdrawal_corruption_and_resume_rederive_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            first,paths=self.prepared(tmp)
            self.assertEqual(first,self.prepared(tmp)[0])
            p=Path(paths.zenodo_json_dir)/(self.examples[0]+'.json')
            payload=read_json(p);payload['metadata']['creators'][0]['name']='Wrong';atomic_json(p,payload)
            self.assertEqual(first,self.prepared(tmp)[0])
            self.assertEqual(self.prepared(tmp,False)[0]['summary']['source_status_counts']['held'],4)
            missing=Path(tmp)/'missing.json'
            self.assertEqual(self.prepared(tmp,manifest=missing)[0]['summary']['source_status_counts']['held'],4)

    def test_independent_long_title_hold_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            report,_=self.prepared(tmp,source_ids=['FGDC-1917'])
            self.assertEqual(report['summary']['source_status_counts']['held'],1)
            self.assertTrue(any('character limit' in reason for reason in report['records'][0]['hold_reasons']))

    def test_all_72_candidates_retain_the_nine_independent_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            report,_=self.prepared(tmp,source_ids=[m['source_id'] for m in self.members])
            self.assertEqual(report['summary']['source_status_counts'],{'supported':63,'held':9,'failed':0})
            held={r['source_id']:r['hold_reasons'] for r in report['records'] if r['source_status']=='held'}
            self.assertEqual(set(held),{'FGDC-1917','FGDC-1922','FGDC-1923','FGDC-1924','FGDC-1925',
                                       'FGDC-1930','FGDC-1933','FGDC-1935','FGDC-2578'})
            self.assertTrue(any('access' in reason.casefold() for reason in held['FGDC-2578']))
