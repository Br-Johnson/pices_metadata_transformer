"""Literal collective attribution is source-bound and cannot invent identities."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from scripts.citation_creator_interpretation import validate_creator_interpretation

MANIFEST = Path('docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json')

class DFOStaffInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_bytes())
        self.reference = {'manifest_path': str(MANIFEST), 'manifest_sha256': hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}
        self.member = self.manifest['members'][0]
        self.root = ET.parse('FGDC/' + self.member['source_id'] + '.xml').getroot()

    def validate(self, reference=None, member=None, root=None):
        m = member or self.member
        return validate_creator_interpretation(reference or self.reference, m['source_id'], m['source_sha256'], root if root is not None else self.root)

    def test_all_seventy_exact_members_preserve_literal_collective(self):
        self.assertEqual(len(self.manifest['members']),70)
        for member in self.manifest['members']:
            raw = Path('FGDC',member['source_id']+'.xml').read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),member['source_sha256'])
            self.assertEqual(self.validate(member=member,root=ET.fromstring(raw)),[{'name':'DFO Staff'}])

    def test_rehashed_creator_or_membership_forgery_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp,'manifest.json')
            for mutation in ('person','type','affiliation','expand','add_member','remove_member'):
                m=copy.deepcopy(self.manifest)
                if mutation=='person':m['creators']=[{'name':'Invented, Person'}]
                elif mutation=='type':m['creators'][0]['type']='Organization'
                elif mutation=='affiliation':m['creators'][0]['affiliation']='Inferred hierarchy'
                elif mutation=='expand':m['creators'][0]['name']='Fisheries and Oceans Canada Staff'
                elif mutation=='add_member':m['members'].append({'source_id':'new','source_sha256':'0'*64})
                else:m['members'].pop()
                p.write_text(json.dumps(m))
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                    self.validate(reference={'manifest_path':str(p),'manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})

    def test_identity_shape_and_reference_fail_closed(self):
        for field,value in [('source_id','unknown'),('source_sha256','0'*64)]:
            with self.subTest(field=field),self.assertRaises(ValueError):self.validate(member={**self.member,field:value})
        for mutation in ('text','attribute','child','repeat'):
            root=copy.deepcopy(self.root);node=root.find('./idinfo/citation/citeinfo/origin')
            if mutation=='text':node.text+=' and someone else'
            elif mutation=='attribute':node.set('role','author')
            elif mutation=='child':ET.SubElement(node,'extra').text='extra'
            else:root.find('./idinfo/citation/citeinfo').append(copy.deepcopy(node))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.validate(root=root)

    def prepared(self, tmp, enabled=True):
        from datetime import datetime, timezone
        import shutil
        from scripts.collection_qa import classify_collection
        from scripts.path_config import OutputPaths
        source=Path(tmp,'sources');source.mkdir(exist_ok=True)
        shutil.copyfile('FGDC/FGDC-4078.xml',source/'FGDC-4078.xml')
        docs=Path('docs/readiness/2026-10-02')
        report=classify_collection(source,Path(tmp,'output'),'2026-10-03T00:00:00Z',
            authority_manifest=docs/'rehosting_authority.json',
            collective_creator_interpretation_manifest=MANIFEST if enabled else None)
        paths=OutputPaths(str(Path(tmp,'output')),'sandbox')
        return report,paths,Path(paths.zenodo_json_dir)/'FGDC-4078.json'

    def test_opt_in_preserves_entire_metadata_and_original(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            before,paths,path=self.prepared(tmp,False);metadata=json.loads(path.read_bytes())['metadata']
            self.assertEqual(before['records'][0]['source_status'],'held')
            after,paths,path=self.prepared(tmp)
            self.assertEqual(after['records'][0]['source_status'],'supported')
            self.assertEqual(json.loads(path.read_bytes())['metadata'],metadata)
            self.assertEqual(metadata['license'],'');self.assertEqual(metadata['access_right'],'restricted')
            self.assertEqual((Path(paths.original_fgdc_dir)/'FGDC-4078.xml').read_bytes(),Path('FGDC/FGDC-4078.xml').read_bytes())
            self.assertFalse(after['records'][0]['publication_approved']);self.assertFalse(after['records'][0]['remote_verified'])
            assess_source(str(path),paths)

    def test_qa_rechecks_full_creator_reference_and_independent_date(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            _,paths,path=self.prepared(tmp);original=json.loads(path.read_bytes())
            for mutation in ('type','name','affiliation','drop_reference','date','grant'):
                payload=copy.deepcopy(original)
                if mutation=='type':payload['metadata']['creators'][0]['type']='Organization'
                elif mutation=='name':payload['metadata']['creators'][0]['name']='Inferred collective'
                elif mutation=='affiliation':payload['metadata']['creators'][0]['affiliation']='Inferred institution'
                elif mutation=='drop_reference':payload['artifact_policy'].pop('creator_interpretation')
                elif mutation=='date':payload['metadata']['publication_date']='2004-06-10'
                else:payload['artifact_policy'].pop('rehosting_authority')
                path.write_text(json.dumps(payload))
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):assess_source(str(path),paths)

    def test_resume_rederives_evidence_and_withdrawal_restores_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            first,paths,path=self.prepared(tmp)
            self.assertEqual(self.prepared(tmp)[0],first)
            payload=json.loads(path.read_bytes());payload['metadata']['creators'][0]['name']='Wrong'
            path.write_text(json.dumps(payload))
            self.assertEqual(self.prepared(tmp)[0],first)
            self.assertEqual(json.loads(path.read_bytes())['metadata']['creators'],[{'name':'DFO Staff'}])
            self.assertEqual(self.prepared(tmp,False)[0]['records'][0]['source_status'],'held')
