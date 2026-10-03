"""User-attested rehosting scope is not a new public XML license grant."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from scripts.agent_qa import assess_source
from scripts.rehosting_authority import (AUTHORITY_ACCESS_CONDITIONS, STATEMENT,
                                         validate_authority)
from tests import test_agent_qa as agent_fixtures


class RehostingAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = agent_fixtures.AgentQATests(methodName='test_supported_source_metadata_date_org_xml_grant_approved_with_honest_provenance')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.path = Path(self.fixture.tmp.name, 'authority.json')
        self.manifest = {'schema_version': 1, 'attested_by': 'Brett Johnson', 'attested_at': '2026-10-02',
                         'statement': STATEMENT, 'scope': 'historical_geonetwork_metadata',
                         'grants_rehosting': True, 'grants_new_license': False,
                         'independently_verified_agreement': False, 'evidence_type': 'USER_ATTESTED',
                         'sources': {'sample': hashlib.sha256(self.fixture.raw).hexdigest()}}
        self.write_authority()

    def write_authority(self):
        self.path.write_text(json.dumps(self.manifest))
        self.reference = {'manifest_path': str(self.path), 'manifest_sha256': hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def authority_payload(self):
        fixture = self.fixture
        fixture.raw = fixture.raw.replace(b'<metuc>CC BY 4.0', b'<metuc>Reuse rights unresolved')
        fixture.source.write_bytes(fixture.raw)
        digest = hashlib.sha256(fixture.raw).hexdigest()
        self.manifest['sources']['sample'] = digest
        self.write_authority()
        fixture.payload['artifact_policy'].update(source_sha256=digest, license=None,
                                                  rehosting_authority=copy.deepcopy(self.reference),
                                                  rights_evidence='USER_ATTESTED permission to rehost; no new XML license asserted')
        fixture.payload['metadata'].update(license='', access_right='restricted',
                                            access_conditions=AUTHORITY_ACCESS_CONDITIONS)
        fixture.sync()

    def assess(self):
        with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
            return assess_source(str(self.fixture.file), self.fixture.paths)

    def test_exact_manifest_membership_preserves_honest_user_attestation(self):
        result = validate_authority(self.reference, 'sample', self.manifest['sources']['sample'])
        self.assertEqual(result['status'], 'USER_ATTESTED')
        self.assertTrue(result['grants_rehosting'])
        self.assertFalse(result['grants_new_license'])
        self.assertEqual(result['statement'], STATEMENT)

    def test_missing_stale_membership_and_digest_are_rejected(self):
        for mutation in ('missing', 'digest', 'member', 'source_hash'):
            with self.subTest(mutation=mutation):
                reference = copy.deepcopy(self.reference)
                source_id, source_hash = 'sample', self.manifest['sources']['sample']
                if mutation == 'missing': reference['manifest_path'] += '.missing'
                elif mutation == 'digest': reference['manifest_sha256'] = '0' * 64
                elif mutation == 'member': source_id = 'outside-scope'
                else: source_hash = '0' * 64
                with self.assertRaises(ValueError): validate_authority(reference, source_id, source_hash)
        self.path.write_text(self.path.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            validate_authority(self.reference, 'sample', self.manifest['sources']['sample'])

    def test_new_license_or_verified_agreement_claim_is_rejected(self):
        baseline = copy.deepcopy(self.manifest)
        for key, value in [('grants_new_license', True), ('license', 'cc-by-4.0'),
                           ('independently_verified_agreement', True), ('evidence_type', 'VERIFIED_AGREEMENT'),
                           ('statement', 'I own all data and grant CC0.')]:
            with self.subTest(key=key):
                self.manifest = copy.deepcopy(baseline); self.manifest[key] = value; self.write_authority()
                with self.assertRaises(ValueError):
                    validate_authority(self.reference, 'sample', self.manifest['sources']['sample'])

    def test_restricted_blank_license_with_source_bound_permission_is_supported(self):
        self.authority_payload()
        metadata, digest, artifact, _ = self.assess()
        self.assertEqual(metadata['license'], '')
        self.assertEqual(metadata['access_right'], 'restricted')
        self.assertIn('USER_ATTESTED', metadata['access_conditions'])
        self.assertEqual(digest, self.manifest['sources']['sample'])
        self.assertIsNotNone(artifact)
        manifest = self.fixture.build()
        record = manifest['records'][0]
        self.assertTrue(record['qa']['approved'], record.get('hold_reasons'))
        self.assertIn('rehosting_authority.py', record['agent_evidence']['rules_sha256'])

    def test_authority_cannot_approve_open_files_new_license_or_missing_conditions(self):
        self.authority_payload()
        baseline = copy.deepcopy(self.fixture.payload)
        for changes in ({'access_right': 'open'}, {'license': 'cc-zero'}, {'access_conditions': ''}):
            self.fixture.payload = copy.deepcopy(baseline)
            self.fixture.payload['metadata'].update(changes)
            self.fixture.file.write_text(json.dumps(self.fixture.payload))
            with self.assertRaises(ValueError): self.assess()
        self.fixture.payload = copy.deepcopy(baseline)
        self.fixture.payload['artifact_policy']['license'] = 'cc-by-4.0'
        self.fixture.file.write_text(json.dumps(self.fixture.payload))
        with self.assertRaises(ValueError): self.assess()

    def test_sensitive_source_constraints_still_block_attested_rehosting(self):
        self.authority_payload()
        self.fixture.raw = self.fixture.raw.replace(b'<metainfo>', b'<metainfo><metac>Sensitive; permission required</metac>')
        self.fixture.source.write_bytes(self.fixture.raw)
        digest = hashlib.sha256(self.fixture.raw).hexdigest()
        self.manifest['sources']['sample'] = digest; self.write_authority()
        self.fixture.payload['artifact_policy'].update(source_sha256=digest, rehosting_authority=self.reference)
        self.fixture.sync()
        with self.assertRaisesRegex(ValueError, 'access constraints'): self.assess()

    def test_changed_attestation_cannot_silently_extend_existing_artifact_policy(self):
        self.authority_payload()
        self.manifest['sources']['additional'] = '0' * 64
        self.write_authority()
        # Existing payload retains the older digest even though source bytes are unchanged.
        with self.assertRaisesRegex(ValueError, 'stale'): self.assess()


if __name__ == '__main__':
    unittest.main()
