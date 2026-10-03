"""Finite remaining-source corrections preserve old evidence and release gates."""
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
CREDITS = DOCS / 'source_citation_credits_409.json'
TITLES = DOCS / 'source_display_titles_35.json'
ACCESS = DOCS / 'finite_source_resource_access_469.json'
CREATOR_IDS = {'FGDC-' + str(i) for i in (1257, 1258, 1262, 1273, 2587, 3788, 4063, 4064)}
RETAINED_CREATOR_ACCESS = CREATOR_IDS - {'FGDC-2587', 'FGDC-3788'}


def reference(path):
    return {'manifest_path': str(path), 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class RemainingSourceCohortTests(unittest.TestCase):
    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.title_ids = {m['source_id'] for m in read_json(TITLES)['members'][8:]}
        self.access_ids = {m['source_id'] for m in read_json(ACCESS)['members'][264:]}

    def prepared(self, tmp, ids, enabled=True, authority=True, replacements=None):
        from scripts.collection_qa import classify_collection
        source = Path(tmp) / 'sources'; source.mkdir(exist_ok=True)
        for stale in source.glob('*.xml'):
            if stale.stem not in ids:
                stale.unlink()
        for sid in ids:
            shutil.copyfile(REPO / 'FGDC' / (sid + '.xml'), source / (sid + '.xml'))
        old = REPO / 'docs/readiness/2026-10-02'
        options = {'authority_manifest': old / 'rehosting_authority.json' if authority else None,
            'access_interpretation_manifest': old / 'contact_source_interpretation.json',
            'creator_interpretation_manifest': old / 'exxon_citation_interpretation.json',
            'contributor_access_interpretation_manifest': old / 'contributor_source_interpretation.json',
            'collective_creator_interpretation_manifest': DOCS / 'dfo_staff_citation_interpretation.json',
            'dataset_access_interpretation_manifest': ACCESS if enabled else DOCS / 'finite_source_resource_access_264.json',
            'institution_creator_interpretation_manifest': CREDITS if enabled else DOCS / 'source_citation_credits_401.json',
            'source_title_interpretation_manifest': TITLES if enabled else DOCS / 'source_display_titles_8.json',
            'source_link_interpretation_manifest': DOCS / 'historical_dataset_linkage_21.json',
            'source_scope_attestation_manifest': DOCS / 'source_scope_attestation_821.json'}
        options.update(replacements or {})
        output = Path(tmp) / 'output'
        return classify_collection(source, output, self.reviewed_at, **options), OutputPaths(str(output), 'sandbox')

    def test_all_240_selected_sources_preserve_only_reviewed_changes_and_six_access_holds(self):
        ids = CREATOR_IDS | self.title_ids | self.access_ids
        self.assertEqual(len(ids), 240)
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, ids, False)
            self.assertEqual(before['summary']['source_status_counts'], {'supported': 0, 'held': 240, 'failed': 0})
            payloads = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + '.json')) for sid in ids}
            after, paths = self.prepared(tmp, ids)
            self.assertEqual(after['summary']['source_status_counts'], {'supported': 234, 'held': 6, 'failed': 0})
            for row in after['records']:
                sid = row['source_id']; old = payloads[sid]['metadata']
                new = read_json(Path(paths.zenodo_json_dir) / (sid + '.json'))['metadata']
                changed = {'creators', 'notes'} if sid in CREATOR_IDS else {'title', 'notes'} if sid in self.title_ids else set()
                self.assertEqual({k:v for k,v in old.items() if k not in changed}, {k:v for k,v in new.items() if k not in changed})
                self.assertEqual(row['source_status'], 'held' if sid in RETAINED_CREATOR_ACCESS else 'supported')
                self.assertFalse(row['remote_verified']); self.assertFalse(row['publication_approved'])
                self.assertEqual(new['access_right'], 'restricted'); self.assertEqual(new['license'], '')
                self.assertEqual((Path(paths.original_fgdc_dir) / (sid + '.xml')).read_bytes(), (REPO / 'FGDC' / (sid + '.xml')).read_bytes())
            again, _ = self.prepared(tmp, ids); self.assertEqual(after, again)
            withdrawn, _ = self.prepared(tmp, ids, False); self.assertEqual(before, withdrawn)

    def test_additive_profiles_preserve_all_previous_members_verbatim(self):
        from scripts.citation_creator_interpretation import (
            validate_creator_interpretation,
        )
        from scripts.dataset_access_interpretation import (
            validate_dataset_access_interpretation,
        )
        from scripts.source_title_interpretation import (
            validate_source_title_interpretation,
        )
        credits = read_json(CREDITS); titles = read_json(TITLES); access = read_json(ACCESS)
        old_credit = DOCS / 'source_citation_credits_401.json'; old_title = DOCS / 'source_display_titles_8.json'; old_access = DOCS / 'finite_source_resource_access_264.json'
        self.assertEqual(credits['cohorts'][:225], read_json(old_credit)['cohorts'])
        self.assertEqual(titles['members'][:8], read_json(old_title)['members'])
        self.assertEqual(access['members'][:264], read_json(old_access)['members'])
        for sid, context in read_json(old_access)['acquisition_contexts'].items():
            self.assertEqual(access['acquisition_contexts'][sid], context)
        for path, previous in ((CREDITS, old_credit), (TITLES, old_title), (ACCESS, old_access)):
            self.assertEqual(read_json(path)['prior_manifest_sha256'], reference(previous)['manifest_sha256'])
        bindings = [(CREDITS, m, validate_creator_interpretation) for c in credits['cohorts'][225:] for m in c['members']]
        bindings += [(TITLES, m, validate_source_title_interpretation) for m in titles['members'][8:]]
        bindings += [(ACCESS, m, validate_dataset_access_interpretation) for m in access['members'][264:]]
        self.assertEqual(len(bindings), 240)
        for path, member, validate in bindings:
            raw = (REPO / 'FGDC' / (member['source_id'] + '.xml')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), member['source_sha256'])
            validate(reference(path), member['source_id'], member['source_sha256'], ET.fromstring(raw))

    def test_access_context_constraints_and_security_fail_closed(self):
        from scripts.dataset_access_interpretation import (
            validate_dataset_access_interpretation,
        )
        manifest = read_json(ACCESS)
        for sid in ('FGDC-199', 'FGDC-223', 'FGDC-2293', 'FGDC-707'):
            member = next(m for m in manifest['members'] if m['source_id'] == sid)
            root = ET.parse(REPO / 'FGDC' / (sid + '.xml')).getroot()
            def validate(value, sid=sid, member=member):
                return validate_dataset_access_interpretation(reference(ACCESS), sid, member['source_sha256'], value)
            result = validate(root); self.assertFalse(result['grants_new_license']); self.assertFalse(result['publication_approved'])
            evidence = manifest['acquisition_contexts'][sid]
            for xpath in tuple(evidence['constraints']) + tuple(evidence['context_elements']):
                altered = copy.deepcopy(root); node = altered.find(xpath)
                if node is None:
                    continue
                node.set('inferred', 'true')
                with self.subTest(sid=sid, xpath=xpath), self.assertRaises(ValueError): validate(altered)
            for tag in ('metsi', 'metextns'):
                altered = copy.deepcopy(root); ET.SubElement(altered.find('./metainfo'), tag)
                with self.assertRaises(ValueError): validate(altered)

    def test_tampered_missing_evidence_unrelated_sources_and_authority_cannot_clear_holds(self):
        ids = {'FGDC-2587', 'FGDC-1447', 'FGDC-223', 'FGDC-233', 'FGDC-10', 'FGDC-2664', 'FGDC-1422', 'FGDC-218'}
        with tempfile.TemporaryDirectory() as tmp:
            report, _ = self.prepared(tmp, ids, authority=False)
            self.assertTrue(all(r['source_status'] == 'held' for r in report['records']))
            for key, path in (('institution_creator_interpretation_manifest', CREDITS), ('source_title_interpretation_manifest', TITLES), ('dataset_access_interpretation_manifest', ACCESS)):
                forged = read_json(path); forged['profile'] = 'expanded'
                target = Path(tmp) / 'forged.json'; atomic_json(target, forged)
                for replacement in (target, Path(tmp) / 'missing.json'):
                    report, _ = self.prepared(tmp, ids, replacements={key: replacement})
                    rows = {r['source_id']:r for r in report['records']}
                    selected = 'FGDC-2587' if path == CREDITS else 'FGDC-1447' if path == TITLES else 'FGDC-223'
                    self.assertEqual(rows[selected]['source_status'], 'held')
                    self.assertTrue(all(rows[sid]['source_status'] == 'held' for sid in ('FGDC-233','FGDC-10','FGDC-2664','FGDC-1422','FGDC-218')))

    def test_agent_and_both_human_schemas_recheck_whole_preservation_and_external_evidence(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval
        for sid, key, evidence in (('FGDC-2587','creator_interpretation',CREDITS), ('FGDC-1447','source_title_interpretation',TITLES), ('FGDC-223','dataset_access_interpretation',ACCESS)):
            with tempfile.TemporaryDirectory() as tmp:
                _, paths = self.prepared(tmp, {sid}); path = Path(paths.zenodo_json_dir) / (sid + '.json'); payload = read_json(path)
                external = Path(tmp) / 'evidence.json'; external.write_bytes(evidence.read_bytes())
                payload['artifact_policy'][key] = reference(external); atomic_json(path, payload)
                metadata, source, digest = prepare_metadata(str(path), paths)
                entry = {'environment':'sandbox','deposition_id':123,'json_file':str(path),'source_sha256':digest,'metadata_sha256':metadata_hash(metadata),'artifact_contract':prepare_artifact(payload, source),'zenodo_url':'https://sandbox.zenodo.org/deposit/123'}
                record = {'fgdc_id':sid,'deposition_id':123,'source_sha256':digest,'metadata_sha256':metadata_hash(metadata),'artifact_contract':entry['artifact_contract'],'qa':{'approved':True,'reviewer_type':'human','reviewer':'Offline fixture','reviewed_at':self.reviewed_at,'rationale':'Fixture only','checks':dict.fromkeys(QA_CHECKS, True),'run_id':'fixture','review_revision':'fixture','evidence':['fixture']},'duplicate_review':{'status':'reviewed','classification':'checked_no_match','rationale':'Fixture only','evidence':['fixture']}}
                for schema in (1, 2):
                    manifest = {'schema_version':schema,'source_revision':'fixture','environment':'sandbox','records':[record]}
                    validate_approval(manifest, sid, entry, paths); assess_source(str(path), paths)
                    external.write_bytes(evidence.read_bytes() + b' ')
                    with self.assertRaises(ValueError): assess_source(str(path), paths)
                    with self.assertRaises(ValueError): validate_approval(manifest, sid, entry, paths)
                    external.write_bytes(evidence.read_bytes())
                    faults = ('withdraw','license','open') + (('title','notes') if sid in self.title_ids else ('creators','notes') if sid in CREATOR_IDS else ('conflict',))
                    for fault in faults:
                        changed = copy.deepcopy(payload)
                        if fault == 'withdraw': changed['artifact_policy'].pop(key)
                        elif fault == 'license': changed['metadata']['license'] = 'cc-zero'
                        elif fault == 'open': changed['metadata']['access_right'] = 'open'
                        elif fault == 'conflict': changed['artifact_policy']['source_scope_attestation'] = reference(DOCS / 'source_scope_attestation_821.json')
                        elif fault == 'creators': changed['metadata']['creators'][0]['orcid'] = 'Inferred'
                        else: changed['metadata'][fault] = 'Discarded context'
                        atomic_json(path, changed)
                        with self.subTest(sid=sid, schema=schema, fault=fault), self.assertRaises(ValueError): assess_source(str(path), paths)
                        with self.subTest(sid=sid, schema=schema, fault=fault), self.assertRaises(ValueError): validate_approval(manifest, sid, entry, paths)
                        atomic_json(path, payload)


if __name__ == '__main__':
    unittest.main()
