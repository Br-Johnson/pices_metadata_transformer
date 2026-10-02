"""Human approval preserves exact authority bindings without automatic adjudication."""
import hashlib
import copy
import unittest

from scripts.qa_manifest import QA_CHECKS, prepare_manifest, validate_approval
from tests import test_rehosting_authority as authority_fixtures


class AuthorityApprovalTests(unittest.TestCase):
    def setUp(self):
        self.authority = authority_fixtures.RehostingAuthorityTests(
            methodName='test_restricted_blank_license_with_source_bound_permission_is_supported')
        self.authority.setUp()
        self.addCleanup(self.authority.doCleanups)
        self.authority.authority_payload()
        self.fixture = self.authority.fixture

    def human_manifest(self, schema):
        manifest = prepare_manifest(self.fixture.paths)
        manifest['schema_version'] = schema
        record = manifest['records'][0]
        record['qa'].update(
            approved=True, reviewer_type='human', reviewer='Fixture human assessor',
            reviewed_at='2026-10-02', rationale='Explicit fixture source adjudication',
            checks={name: True for name in QA_CHECKS}, run_id='fixture-human-review',
            review_revision=manifest['source_revision'], evidence=['Offline fixture review'])
        record['duplicate_review'].update(
            status='reviewed', classification='checked_no_match',
            rationale='Explicit fixture title comparison', evidence=self.fixture.duplicates['evidence'])
        return manifest

    def approve(self, manifest, remote=False):
        args = [manifest, 'sample', self.fixture.entry, self.fixture.paths]
        if remote:
            args.extend((self.fixture.remote['body']['metadata'], self.fixture.remote['body']['files']))
        return validate_approval(*args)

    def test_unchanged_authority_binding_accepts_human_approval_and_readback(self):
        for schema in (1, 2):
            manifest = self.human_manifest(schema)
            for remote in (False, True):
                with self.subTest(schema=schema, remote=remote):
                    self.assertTrue(self.approve(manifest, remote)['qa']['approved'])

    def test_changed_manifest_bytes_invalidate_human_approval_and_readback(self):
        manifests = [self.human_manifest(schema) for schema in (1, 2)]
        self.authority.path.write_text(self.authority.path.read_text() + '\n')
        for manifest in manifests:
            for remote in (False, True):
                with self.subTest(schema=manifest['schema_version'], remote=remote):
                    with self.assertRaisesRegex(ValueError, 'manifest digest is stale'):
                        self.approve(manifest, remote)

    def test_withdrawn_source_membership_invalidates_human_approval_and_readback(self):
        manifests = [self.human_manifest(schema) for schema in (1, 2)]
        self.authority.manifest['sources'] = {}
        self.authority.write_authority()
        for manifest in manifests:
            for remote in (False, True):
                with self.subTest(schema=manifest['schema_version'], remote=remote):
                    with self.assertRaisesRegex(ValueError, 'manifest digest is stale'):
                        self.approve(manifest, remote)

    def test_human_creator_adjudication_is_preserved_with_valid_authority(self):
        self.fixture.raw = self.fixture.raw.replace(b'Example Marine Institute', b'Alice and Bob')
        self.fixture.source.write_bytes(self.fixture.raw)
        self.authority.manifest['sources']['sample'] = hashlib.sha256(self.fixture.raw).hexdigest()
        self.authority.write_authority()
        self.fixture.payload['artifact_policy'].update(
            source_sha256=self.authority.manifest['sources']['sample'],
            rehosting_authority=self.authority.reference)
        self.fixture.payload['metadata']['creators'] = [{'name': 'Alice and Bob'}]
        self.fixture.sync()
        with self.assertRaisesRegex(ValueError, 'Creator semantics are ambiguous'):
            self.authority.assess()
        for schema in (1, 2):
            with self.subTest(schema=schema):
                self.assertTrue(self.approve(self.human_manifest(schema), remote=True)['qa']['approved'])

    def test_human_approval_cannot_change_attested_file_or_license_conditions(self):
        baseline = copy.deepcopy(self.fixture.payload)
        cases = (
            ('open_files', 'metadata', {'access_right': 'open'}),
            ('new_license', 'metadata', {'license': 'cc-zero'}),
            ('missing_blank_license', 'metadata', {'license': None}),
            ('missing_conditions', 'metadata', {'access_conditions': ''}),
            ('policy_license', 'artifact_policy', {'license': 'cc-by-4.0'}),
        )
        for name, target, changes in cases:
            self.fixture.payload = copy.deepcopy(baseline)
            self.fixture.payload[target].update(changes)
            self.fixture.sync()
            for schema in (1, 2):
                manifest = self.human_manifest(schema)
                for remote in (False, True):
                    with self.subTest(case=name, schema=schema, remote=remote):
                        with self.assertRaisesRegex(ValueError, 'restricted XML|cannot grant a policy license'):
                            self.approve(manifest, remote)
