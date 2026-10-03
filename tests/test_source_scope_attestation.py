"""Exact user scope clarification preserves XML, restrictions and independent holds."""
import copy
import hashlib
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts.path_config import OutputPaths
from scripts.upload_service import (
    atomic_json,
    metadata_hash,
    prepare_metadata,
    read_json,
)

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-03'
MANIFEST = DOCS / 'source_scope_attestation_821.json'


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class SourceScopeAttestationTests(unittest.TestCase):
    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.manifest = read_json(MANIFEST)
        self.members = {m['source_id']: m for m in self.manifest['members']}

    def prepared(self, tmp, ids=('FGDC-1238', 'FGDC-2731', 'FGDC-335'), enabled=True, authority=True, evidence=MANIFEST):
        from scripts.collection_qa import classify_collection
        source = Path(tmp) / 'sources'; source.mkdir(exist_ok=True)
        for sid in ids:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        old = REPO / 'docs/readiness/2026-10-02'
        options = {'authority_manifest': old / 'rehosting_authority.json' if authority else None,
            'access_interpretation_manifest': old / 'contact_source_interpretation.json',
            'creator_interpretation_manifest': old / 'exxon_citation_interpretation.json',
            'dataset_access_interpretation_manifest': DOCS / 'finite_source_resource_access_264.json',
            'contributor_access_interpretation_manifest': old / 'contributor_source_interpretation.json',
            'collective_creator_interpretation_manifest': DOCS / 'dfo_staff_citation_interpretation.json',
            'institution_creator_interpretation_manifest': DOCS / 'source_citation_credits_401.json',
            'source_link_interpretation_manifest': DOCS / 'historical_dataset_linkage_21.json',
            'source_title_interpretation_manifest': DOCS / 'source_display_titles_8.json'}
        if enabled:
            options['source_scope_attestation_manifest'] = evidence
        output = Path(tmp) / 'output'
        report = classify_collection(source, output, self.reviewed_at, **options)
        return report, OutputPaths(str(output), 'sandbox')

    def test_new_attested_scope_is_accepted_for_three_exact_cohorts(self):
        from scripts.agent_qa import assess_source
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, enabled=False)
            for sid in ('FGDC-1238', 'FGDC-2731', 'FGDC-335'):
                path = Path(paths.zenodo_json_dir) / (sid + '.json')
                payload = read_json(path)
                payload['artifact_policy']['source_scope_attestation'] = reference(MANIFEST)
                atomic_json(path, payload)
                metadata, _, _, _ = assess_source(str(path), paths)
                self.assertEqual(metadata['access_right'], 'restricted')
                self.assertEqual(metadata['license'], '')

    def test_exact821_question_context_bindings_and_user_provenance(self):
        from scripts.source_scope_attestation import validate_scope_attestation
        self.assertEqual(len(self.members), 821)
        question = read_json(DOCS / 'remaining_source_scope_questions_821.json')
        self.assertEqual(self.manifest['original_questions'], question['questions'])
        self.assertEqual(self.manifest['statement'], 'they reply to the underlying data. all these metadata records were public before')
        self.assertEqual(self.manifest['provenance']['message_id'], 'Sentinel_e28f30cd7f308191b3ea2f19487dd34a')
        for sid, member in self.members.items():
            raw = (REPO / 'FGDC' / (sid + '.xml')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
            result = validate_scope_attestation(reference(MANIFEST), sid, member['source_sha256'], ET.fromstring(raw), self.reviewed_at)
            self.assertEqual(result['status'], 'USER_ATTESTED')
            self.assertEqual(result['cohort'], member['cohort'])
            self.assertFalse(result['grants_rehosting'])
            self.assertFalse(result['grants_new_license'])
            self.assertFalse(result['publication_approved'])
            self.assertFalse(result['underlying_data_rights_granted'])

    def test_wrong_source_context_scope_timestamps_and_rehashed_manifests_are_rejected(self):
        from scripts.source_scope_attestation import validate_scope_attestation
        sid = 'FGDC-1238'; member = self.members[sid]
        root = ET.parse(REPO / 'FGDC' / (sid + '.xml')).getroot()
        def validate(value=root, ref=None, stamp=None, source=sid, digest=member['source_sha256']):
            return validate_scope_attestation(reference(MANIFEST) if ref is None else ref, source, digest, value, self.reviewed_at if stamp is None else stamp)
        for xpath in tuple(member['constraint_elements']) + tuple(member['context_elements_sha256']):
            for mutation in ('text', 'child', 'attribute', 'duplicate', 'missing'):
                value = copy.deepcopy(root); node = value.find(xpath); parent = value.find(xpath.rsplit('/', 1)[0])
                if mutation == 'text': node.text = 'Different scope'
                elif mutation == 'child': ET.SubElement(node, 'extra').text = 'Changed'
                elif mutation == 'attribute': node.set('scope', 'different')
                elif mutation == 'duplicate': parent.append(copy.deepcopy(node))
                else: parent.remove(node)
                with self.subTest(xpath=xpath, mutation=mutation), self.assertRaises(ValueError): validate(value)
        for tag in ('metsi', 'metextns'):
            value = copy.deepcopy(root); ET.SubElement(value.find('./metainfo'), tag)
            with self.assertRaises(ValueError): validate(value)
        for stamp in ('2026-10-03T20:19:59Z', '2099-01-01T00:00:00Z', '2026-10-03T20:20:00', None):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                validate_scope_attestation(reference(MANIFEST), sid, member['source_sha256'], root, stamp)
        for source,digest in [('FGDC-121',member['source_sha256']),(sid,'0'*64)]:
            with self.assertRaises(ValueError): validate(source=source,digest=digest)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'changed.json'
            for key,value in [('statement','yes'),('grants_new_license',True),('members',[]),('question_sha256','0'*64)]:
                forged = copy.deepcopy(self.manifest); forged[key] = value; atomic_json(path,forged)
                with self.subTest(key=key), self.assertRaises(ValueError): validate(ref=reference(path))

    def test_opt_in_withdrawal_resume_and_unrelated_holds_preserve_metadata_and_xml(self):
        ids = ('FGDC-1238', 'FGDC-2731', 'FGDC-335', 'FGDC-10', 'FGDC-2664', 'FGDC-1369', 'FGDC-121')
        with tempfile.TemporaryDirectory() as tmp:
            before,paths = self.prepared(tmp,ids,enabled=False)
            old = {sid:read_json(Path(paths.zenodo_json_dir)/(sid+'.json')) for sid in ids}
            after,paths = self.prepared(tmp,ids)
            rows = {r['source_id']:r for r in after['records']}
            for sid in ids:
                payload=read_json(Path(paths.zenodo_json_dir)/(sid+'.json'))
                self.assertEqual(old[sid]['metadata'],payload['metadata'])
                self.assertEqual((Path(paths.original_fgdc_dir)/(sid+'.xml')).read_bytes(),(REPO/'FGDC'/(sid+'.xml')).read_bytes())
                self.assertEqual(rows[sid]['source_status'],'supported' if sid in ids[:3] else 'held')
                self.assertFalse(rows[sid]['remote_verified']);self.assertFalse(rows[sid]['publication_approved'])
            self.assertIn('Creator semantics are ambiguous',rows['FGDC-10']['hold_reasons'])
            self.assertTrue(any('title' in reason for reason in rows['FGDC-1369']['hold_reasons']))
            again,_=self.prepared(tmp,ids);self.assertEqual(after,again)
            withdrawn,_=self.prepared(tmp,ids,enabled=False);self.assertEqual(before,withdrawn)

    def test_missing_changed_or_forged_evidence_keeps_selected_members_held(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing=Path(tmp)/'missing.json'
            for evidence in (missing,):
                report,paths=self.prepared(tmp,evidence=evidence)
                self.assertTrue(all(r['source_status']=='held' for r in report['records']))
                self.assertTrue(all('source_scope_attestation' not in read_json(Path(paths.zenodo_json_dir)/(r['source_id']+'.json'))['artifact_policy'] for r in report['records']))
            forged=copy.deepcopy(self.manifest);forged['meaning']='unrestricted_data';atomic_json(missing,forged)
            report,_=self.prepared(tmp,evidence=missing);self.assertTrue(all(r['source_status']=='held' for r in report['records']))

    def test_authority_unlicensed_restricted_xml_and_no_conflicting_interpretations_required(self):
        from scripts.agent_qa import assess_source
        from scripts.source_scope_attestation import validate_scope_policy
        with tempfile.TemporaryDirectory() as tmp:
            report,_=self.prepared(tmp,authority=False);self.assertTrue(all(r['source_status']=='held' for r in report['records']))
            _,paths=self.prepared(tmp);path=Path(paths.zenodo_json_dir)/'FGDC-1238.json';original=read_json(path)
            root=ET.parse(REPO/'FGDC/FGDC-1238.xml').getroot()
            for fault in ('authority','open','license','policy_license','source_conflict','dataset_conflict','withdraw'):
                payload=copy.deepcopy(original);policy=payload['artifact_policy']
                if fault=='authority':policy.pop('rehosting_authority')
                elif fault=='open':payload['metadata']['access_right']='open'
                elif fault=='license':payload['metadata']['license']='cc-zero'
                elif fault=='policy_license':policy['license']='cc-zero'
                elif fault=='source_conflict':policy['source_access_interpretation']=reference(MANIFEST)
                elif fault=='dataset_conflict':policy['dataset_access_interpretation']=reference(MANIFEST)
                else:policy.pop('source_scope_attestation')
                atomic_json(path,payload)
                with self.subTest(fault=fault),self.assertRaises(ValueError):assess_source(str(path),paths)
                if fault!='withdraw':
                    with self.subTest(shared=fault),self.assertRaises(ValueError):validate_scope_policy(policy,'FGDC-1238',self.members['FGDC-1238']['source_sha256'],root,payload['metadata'])

    def test_both_human_schemas_recheck_external_attestation_bytes_and_withdrawal(self):
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval
        with tempfile.TemporaryDirectory() as tmp:
            _,paths=self.prepared(tmp,('FGDC-1238',));path=Path(paths.zenodo_json_dir)/'FGDC-1238.json';payload=read_json(path)
            external=Path(tmp)/'attestation.json';external.write_bytes(MANIFEST.read_bytes())
            payload['artifact_policy']['source_scope_attestation']=reference(external);atomic_json(path,payload)
            metadata,source,digest=prepare_metadata(str(path),paths);artifact=prepare_artifact(payload,source)
            entry={'environment':'sandbox','deposition_id':123,'json_file':str(path),'source_sha256':digest,'metadata_sha256':metadata_hash(metadata),'artifact_contract':artifact,'zenodo_url':'https://sandbox.zenodo.org/deposit/123'}
            record={'fgdc_id':'FGDC-1238','deposition_id':123,'source_sha256':digest,'metadata_sha256':metadata_hash(metadata),'artifact_contract':artifact,'qa':{'approved':True,'reviewer_type':'human','reviewer':'Offline fixture','reviewed_at':self.reviewed_at,'rationale':'Fixture only','checks':dict.fromkeys(QA_CHECKS,True),'run_id':'fixture','review_revision':'fixture','evidence':['Fixture only']},'duplicate_review':{'status':'reviewed','classification':'checked_no_match','rationale':'Fixture only','evidence':['Fixture only']}}
            for schema in (1,2):
                manifest={'schema_version':schema,'source_revision':'fixture','environment':'sandbox','records':[record]}
                validate_approval(manifest,'FGDC-1238',entry,paths)
                external.write_bytes(MANIFEST.read_bytes()+b'\n')
                with self.assertRaises(ValueError):validate_approval(manifest,'FGDC-1238',entry,paths)
                external.write_bytes(MANIFEST.read_bytes());changed=copy.deepcopy(payload);changed['artifact_policy'].pop('source_scope_attestation');atomic_json(path,changed)
                with self.assertRaises(ValueError):validate_approval(manifest,'FGDC-1238',entry,paths)
                atomic_json(path,payload)


if __name__ == '__main__':
    unittest.main()
