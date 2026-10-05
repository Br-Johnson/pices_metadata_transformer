"""Record QA never implies production release; exact selection is independently bound."""
import copy
import unittest
from unittest.mock import Mock, patch

from scripts.release_manifest import prepare_release, validate_release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.entry = {'environment': 'production', 'deposition_id': 123, 'source_sha256': 'source',
                      'metadata_sha256': 'metadata', 'artifact_contract': None}
        self.manifest = {'schema_version': 1, 'environment': 'production', 'records': [
            dict(self.entry, fgdc_id='one', qa={'approved': True}),
            dict(self.entry, fgdc_id='held', deposition_id=124, qa={'approved': False}),
            dict(self.entry, fgdc_id='two', deposition_id=125, qa={'approved': True})]}

    def authorized_release(self):
        release = prepare_release(self.manifest, ['one'])
        release['release'].update(approved=True, authority='Fixture release authority',
                                  authorized_at='2026-10-02', rationale='Offline fixture release')
        return release

    def test_preparation_does_not_approve_release(self):
        release = prepare_release(self.manifest, ['one'])
        self.assertFalse(release['release']['approved'])
        with self.assertRaisesRegex(ValueError, 'explicit human publication release'):
            validate_release(release, self.manifest, 'one', self.entry)
        with self.assertRaises(ValueError):
            prepare_release(self.manifest, ['held'])

    def test_exact_release_selection_and_manifest_changes(self):
        release = self.authorized_release()
        validate_release(release, self.manifest, 'one', self.entry)
        with self.assertRaisesRegex(ValueError, 'outside'):
            validate_release(release, self.manifest, 'two', dict(self.entry, deposition_id=125))
        changed = copy.deepcopy(self.manifest)
        changed['records'][0]['qa']['approved'] = False
        with self.assertRaises(ValueError):
            validate_release(release, changed, 'one', self.entry)
        with self.assertRaises(ValueError):
            validate_release(release, self.manifest, 'one', dict(self.entry, metadata_sha256='changed'))

    def test_agent_qa_is_not_human_release_authority(self):
        self.manifest['schema_version'] = 2
        release = self.authorized_release()
        release['release']['authority_type'] = 'agent'
        with self.assertRaises(ValueError):
            validate_release(release, self.manifest, 'one', self.entry)
        with self.assertRaises(ValueError):
            validate_release(None, self.manifest, 'one', self.entry)

    def test_agent_qa_publication_requires_program_review_and_separate_release(self):
        from tests.test_agent_qa import AgentQATests
        from scripts.production_mutations import MutationJournal
        from scripts.publish_records import RecordPublisher
        from scripts.qa_manifest import approved_population_hash
        from scripts.upload_service import atomic_json
        fixture = AgentQATests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        # This fixture represents a fresh journaled draft, not a legacy draft
        # whose missing attempt history must hold publication.
        fixture.entry['doi'] = '10.5281/zenodo.123'
        atomic_json(fixture.paths.uploads_registry_path, {'sample': fixture.entry})
        journal = MutationJournal(fixture.paths)
        journal.begin('sample', dict(fixture.entry, deposition_id=None), 'create')
        journal.confirm('sample', fixture.entry, 'create', fixture.remote['body'])
        manifest = fixture.build()
        self.assertTrue(manifest['records'][0]['qa']['approved'])
        release = prepare_release(manifest)
        release['release'].update(approved=True, authority='Fixture human release authority',
                                  authorized_at='2026-10-02', rationale='Offline fixture only')
        remote = copy.deepcopy(fixture.remote['body'])
        client = Mock(base_url='https://zenodo.org')
        client.get_deposition.side_effect = lambda _: copy.deepcopy(remote)
        def publish(_):
            remote.update(state='done', submitted=True)
            return copy.deepcopy(remote)
        client.publish_deposition.side_effect = publish
        with patch('scripts.publish_records.create_zenodo_client', return_value=client), patch('scripts.publish_records.get_logger', return_value=Mock()):
            publisher = RecordPublisher(False, fixture.tmp.name, manifest, release)
        self.assertFalse(publisher._publish_single_record(fixture.entry)['publish_successful'])
        client.get_deposition.assert_not_called()
        digest = approved_population_hash(manifest)
        for name in manifest['program_review']:
            manifest['program_review'][name] = {
                'status': 'reviewed', 'reviewer_type': 'agent', 'reviewer': 'Independent fixture assessor',
                'reviewed_at': '2026-10-02', 'rationale': 'Offline fixture review',
                'population_sha256': digest, 'evidence': [{'scope': 'Offline fixture only', 'reference': 'fixture'}],
                'sampled_ids': ['sample'], 'risk_strata': ['Explicit XML scope grant']}
        # Changing program-review evidence invalidates an already prepared release.
        self.assertFalse(publisher._publish_single_record(fixture.entry)['publish_successful'])
        client.get_deposition.assert_not_called()
        release = prepare_release(manifest)
        release['release'].update(approved=True, authority='Fixture human release authority',
                                  authorized_at='2026-10-02', rationale='Offline fixture only')
        publisher.release_manifest = release
        self.assertTrue(publisher._publish_single_record(fixture.entry)['publish_successful'])
        self.assertTrue(publisher._publish_single_record(fixture.entry)['already_published'])
        client.publish_deposition.assert_called_once_with(123)


if __name__ == '__main__':
    unittest.main()
