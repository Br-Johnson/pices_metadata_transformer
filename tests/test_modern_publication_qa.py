"""Modern draft QA preserves explicit approval and exact raw evidence bindings."""

import base64
import copy
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import timedelta

from scripts import modern_publication_qa as qa
from scripts import modern_singleton as mapping
from scripts.matching.evidence import snapshot_inventory
from scripts.qa_manifest import QA_CHECKS, approved_population_hash
from tests.modern_singleton_fixtures import NOW, Fixture, prepare_sources


def raw_duplicates(prepared, *, bridge, snapshot, now=NOW):
    """Test-only independently reviewed production proof plus raw external search."""
    node = ET.fromstring(prepared.xml).find('./idinfo/citation/citeinfo/title')
    title = re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()
    raw_snapshot = {
        'repository': 'Offline fixture repository', 'endpoint': 'https://example.invalid/dois',
        'retrieved_at': now.isoformat(), 'query': title,
        'scope': 'Offline fixture source-title search; not a real global absence claim',
        'http_status': 200, 'format': 'datacite', 'scope_complete': True,
        'body': {'data': [], 'links': {}, 'meta': {'total': 0}},
    }
    production = {
        'schema_version': 1, 'kind': 'modern-production-duplicate-v1', 'origin': 'https://zenodo.org',
        'owner': bridge['identity']['owner'], 'binding': bridge['binding'],
        'preparation_binding': prepared.binding, 'state_root': bridge['state_root'],
        'source_id': prepared.source_id, 'source_sha256': mapping.sha(prepared.xml),
        'wire_sha256': mapping.sha(prepared.body), 'own_records': [copy.deepcopy(bridge['identity'])],
        'matched_record_ids': [bridge['identity']['id']], 'matched_dois': [],
        'excluded_record_ids': [bridge['identity']['id']], 'excluded_dois': [],
        'unresolved_candidates': [], 'unresolved_attempts': [],
        'historical_exception': {key: bridge[key] for key in ('draft_row_sha256', 'create_intent_sha256')},
        'complete': True, 'history_reconciled': True, 'checked_at': now.isoformat(),
        'expires_at': (now + timedelta(hours=1)).isoformat(),
        'inventory_sha256': mapping.sha(b'Offline synthetic owner inventory capture'),
        'history_sha256': mapping.sha(b'Offline synthetic source history reconciliation'),
        'captured_by': 'Offline capture fixture', 'reviewed_by': 'Offline production evidence reviewer',
        'reviewer_type': 'agent', 'reviewed_at': now.isoformat(),
        'rationale': 'Explicit independent test-only owner, own draft and source history reconciliation',
        'evidence': [],
    }
    for role, scope in qa.PRODUCTION_SCOPES.items():
        production['evidence'].append({
            'role': role, 'scope': scope, 'origin': 'https://zenodo.org', 'owner': bridge['identity']['owner'],
            'reference': 'offline-synthetic-capture:' + role,
            'sha256': production['inventory_sha256' if role == 'owner_inventory' else 'history_sha256'],
            'observed_at': now.isoformat(),
        })
    production['reviewed_projection_sha256'] = qa.production_projection_hash(production)
    return {
        'schema_version': 1, 'status': 'checked_no_match', 'inventory_complete': True,
        'environment': 'production', 'fgdc_id': prepared.source_id,
        'source_sha256': mapping.sha(prepared.xml), 'metadata_sha256': mapping.sha(prepared.body),
        'candidates': [], 'scope': 'Offline fixture source-title search',
        'checked_at': now.isoformat(), 'valid_until': (now + timedelta(hours=1)).isoformat(),
        'production': production,
        'evidence': [{'status': 'checked_no_match', 'inventory_complete': True,
                      'endpoint': raw_snapshot['endpoint'], 'scope': raw_snapshot['scope'],
                      'response_sha256': snapshot_inventory(raw_snapshot)['response_sha256'], 'snapshot': raw_snapshot}],
    }


def approve(manifest, *, now=NOW, reviewer_type='agent'):
    """Explicit test-only review by named independent synthetic assessors."""
    manifest = copy.deepcopy(manifest)
    row = manifest['records'][0]
    row['qa'].update(approved=True, reviewer_type=reviewer_type, reviewer='Offline record assessor',
                     run_id='offline-modern-qa-review', review_revision=manifest['source_revision'],
                     reviewed_at=now.isoformat(), rationale='Inspected the exact synthetic evidence',
                     checks=dict.fromkeys(QA_CHECKS, True))
    row['duplicate_review'] = {
        'status': 'reviewed', 'classification': 'checked_no_match',
        'rationale': 'Inspected the complete empty raw source-title inventory',
        'evidence': [copy.deepcopy(row['agent_evidence']['duplicate_snapshot'])],
    }
    population = approved_population_hash(manifest)
    for name in ('independent_review', 'risk_stratified_spotcheck'):
        manifest['program_review'][name] = {
            'status': 'reviewed', 'reviewer_type': 'agent', 'reviewer': 'Offline independent assessor',
            'reviewed_at': now.isoformat(), 'rationale': 'Independent synthetic program review',
            'population_sha256': population,
            'evidence': [{'scope': 'Offline modern singleton review', 'reference': 'test-only-evidence'}],
        }
    manifest['program_review']['risk_stratified_spotcheck'].update(
        sampled_ids=[row['fgdc_id']], risk_strata=['Original XML, restricted rights, organization creator'])
    return manifest


class ModernPublicationQATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.source_tmp.cleanup)
        cls.source_root = prepare_sources(cls.source_tmp.name, ids=['FGDC-141'])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.fixture = Fixture(directory.name, self.source_root)
        self.prepared = self.fixture.prepared
        self.bridge = {
            'kind': 'modern-singleton-bridge-v1', 'preparation_binding': self.prepared.binding,
            'identity': {'id': '19000001', 'parent_id': '19000000', 'owner': '123', 'created': NOW.isoformat()},
            'verified_revision': 2, 'state_root': self.fixture.grant['state_root'],
            'draft_row_sha256': 'd' * 64, 'create_intent_sha256': 'e' * 64,
        }
        self.bridge['binding'] = mapping.sha(mapping.encode(self.bridge))
        remote = self.fixture.transport
        remote.created = remote.initialized = remote.uploaded = remote.complete = True
        remote.revision = 2
        record, entry = remote.record(), remote.entry()
        routes = [(remote.base, record), (remote.base + '/files', {'entries': [entry]}),
                  (remote.file, entry), (remote.file + '/content', self.prepared.xml), (remote.base, record)]
        responses = []
        for path, body in routes:
            binary = isinstance(body, bytes)
            raw = body if binary else mapping.encode(body)
            responses.append({'method': 'GET', 'path': path, 'http_status': 200,
                              'media_type': 'application/octet-stream' if binary else 'application/vnd.inveniordm.v1+json',
                              'body_base64': base64.b64encode(raw).decode(), 'response_sha256': mapping.sha(raw)})
        self.snapshot = {
            'schema_version': 1, 'kind': 'modern-draft-snapshot-v1', 'bridge_binding': self.bridge['binding'],
            'identity': copy.deepcopy(self.bridge['identity']), 'revision_id': 2,
            'captured_at': NOW.isoformat(), 'responses': responses,
        }
        self.duplicate = raw_duplicates(self.prepared, bridge=self.bridge, snapshot=self.snapshot)

    def pending(self):
        return qa.pending_manifest(self.prepared, self.bridge, self.snapshot, self.duplicate,
                                   source_revision='offline-reviewed-revision', now=NOW)

    def assess(self):
        return qa.assess(self.prepared, self.bridge, self.snapshot, self.duplicate, now=NOW)

    def validate(self, manifest, **overrides):
        args = {'prepared': self.prepared, 'bridge': self.bridge, 'snapshot': self.snapshot,
                'duplicate': self.duplicate, 'now': NOW}
        args.update(overrides)
        return qa.validate(manifest, **args)

    def refresh_raw_digest(self):
        proof = self.duplicate['evidence'][0]
        proof['response_sha256'] = snapshot_inventory(proof['snapshot'])['response_sha256']

    def rebind_bridge(self):
        self.bridge['binding'] = mapping.sha(mapping.encode({k: v for k, v in self.bridge.items() if k != 'binding'}))
        self.snapshot['bridge_binding'] = self.bridge['binding']
        self.snapshot['identity'] = copy.deepcopy(self.bridge['identity'])
        self.duplicate = raw_duplicates(self.prepared, bridge=self.bridge, snapshot=self.snapshot)

    def resign_production(self):
        production = self.duplicate['production']
        production['reviewed_projection_sha256'] = qa.production_projection_hash(production)

    def test_pending_manifest_supplies_evidence_without_any_approval(self):
        before = copy.deepcopy((self.bridge, self.snapshot, self.duplicate))
        manifest = self.pending()
        self.assertEqual(manifest['kind'], 'modern-singleton-qa-v1')
        self.assertEqual(manifest['records'][0]['deposition_id'], '19000001')
        self.assertIs(manifest['records'][0]['qa']['approved'], False)
        self.assertFalse(any(manifest['records'][0]['qa']['checks'].values()))
        self.assertEqual(manifest['records'][0]['duplicate_review']['status'], 'pending')
        self.assertTrue(all(review['status'] == 'pending' for review in manifest['program_review'].values()))
        self.assertEqual(before, (self.bridge, self.snapshot, self.duplicate))
        with self.assertRaisesRegex(ValueError, 'explicit record approval'):
            self.validate(manifest)

    def test_explicit_agent_and_human_approval_pass_with_independent_program_review(self):
        for reviewer_type in ('agent', 'human'):
            with self.subTest(reviewer_type=reviewer_type):
                manifest = approve(self.pending(), reviewer_type=reviewer_type)
                self.assertIs(self.validate(manifest), manifest['records'][0])
        self.assertEqual(self.fixture.transport.calls, [])

    def test_evidence_contains_exact_source_wire_bridge_snapshot_and_raw_proof(self):
        evidence = self.assess()
        self.assertEqual(evidence['prepared_evidence'], self.prepared.evidence)
        self.assertEqual(evidence['source_sha256'], mapping.sha(self.prepared.xml))
        self.assertEqual(evidence['metadata_sha256'], mapping.sha(self.prepared.body))
        self.assertNotEqual(evidence['metadata_sha256'], self.prepared.evidence['legacy_metadata_sha256'])
        self.assertEqual(evidence['bridge']['sha256'], mapping.sha(mapping.encode(self.bridge)))
        self.assertEqual(evidence['remote_snapshot']['sha256'], mapping.sha(mapping.encode(self.snapshot)))
        self.assertEqual(evidence['raw_duplicate_proof'], self.duplicate)
        evidence['raw_duplicate_proof']['evidence'].clear()
        evidence['prepared_evidence']['artifact_contract']['files'].clear()
        self.assertEqual(len(self.duplicate['evidence']), 1)
        self.assertEqual(len(self.prepared.evidence['artifact_contract']['files']), 1)

    def test_manifest_population_and_review_revision_cannot_be_swapped(self):
        for field, value in (('schema_version', 1), ('kind', 'legacy-qa'), ('environment', 'sandbox'),
                             ('source_revision', ''), ('source_revision', 'another-reviewed-revision')):
            with self.subTest(field=field, value=value):
                manifest = approve(self.pending())
                manifest[field] = value
                with self.assertRaises(ValueError):
                    self.validate(manifest)
        for rows in ([], [None], [self.pending()['records'][0]] * 2):
            with self.subTest(rows=len(rows)):
                manifest = approve(self.pending())
                manifest['records'] = rows
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_record_identity_source_wire_and_artifact_tampering_hold(self):
        changes = [('fgdc_id', 'FGDC-142'), ('deposition_id', 19000001), ('deposition_id', '19000002'),
                   ('source_sha256', '0' * 64), ('metadata_sha256', '0' * 64), ('artifact_contract', {})]
        for key, value in changes:
            with self.subTest(field=key, value=value):
                manifest = approve(self.pending())
                manifest['records'][0][key] = value
                with self.assertRaisesRegex(ValueError, 'identity or evidence'):
                    self.validate(manifest)

    def test_all_record_checks_and_honest_reviewer_provenance_are_required(self):
        mutations = [(key, '') for key in ('reviewer', 'run_id', 'review_revision', 'reviewed_at', 'rationale')]
        mutations += [('approved', 1), ('reviewer_type', 'automatically approved'), ('evidence', [])]
        for key, value in mutations:
            with self.subTest(field=key):
                manifest = approve(self.pending())
                manifest['records'][0]['qa'][key] = value
                with self.assertRaises(ValueError):
                    self.validate(manifest)
        for check in QA_CHECKS:
            with self.subTest(check=check):
                manifest = approve(self.pending())
                manifest['records'][0]['qa']['checks'][check] = 1
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_program_review_is_independent_and_bound_to_exact_approved_population(self):
        for change in ('pending', 'same_assessor', 'wrong_population', 'sample_elsewhere', 'missing_strata'):
            with self.subTest(change=change):
                manifest = approve(self.pending())
                independent = manifest['program_review']['independent_review']
                spotcheck = manifest['program_review']['risk_stratified_spotcheck']
                if change == 'pending':
                    independent['status'] = 'pending'
                elif change == 'same_assessor':
                    independent['reviewer'] = manifest['records'][0]['qa']['reviewer']
                elif change == 'wrong_population':
                    independent['population_sha256'] = '0' * 64
                elif change == 'sample_elsewhere':
                    spotcheck['sampled_ids'] = ['FGDC-142']
                else:
                    spotcheck['risk_strata'] = []
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_population_hash_covers_entire_modern_agent_evidence(self):
        original = approve(self.pending())
        population = approved_population_hash(original)
        for component in ('prepared_evidence', 'bridge', 'remote_snapshot', 'duplicate_snapshot', 'raw_duplicate_proof'):
            with self.subTest(component=component):
                manifest = copy.deepcopy(original)
                manifest['records'][0]['agent_evidence'][component]['tampered'] = True
                self.assertNotEqual(approved_population_hash(manifest), population)
                with self.assertRaisesRegex(ValueError, 'stale or altered'):
                    self.validate(manifest)
        original['records'][0]['qa']['evidence'] = ['f' * 64]
        with self.assertRaises(ValueError):
            self.validate(original)

    def test_duplicate_adjudication_requires_exact_raw_proof_reference(self):
        for key, value in (('status', 'pending'), ('classification', 'waived_unavailable'),
                           ('classification', 'different_dataset'), ('classification', 'same_work'),
                           ('rationale', ''), ('evidence', []), ('evidence', [{'sha256': '0' * 64}])):
            with self.subTest(field=key, value=value):
                manifest = approve(self.pending())
                manifest['records'][0]['duplicate_review'][key] = value
                with self.assertRaisesRegex(ValueError, 'duplicate adjudication'):
                    self.validate(manifest)

    def test_approval_cannot_follow_changed_compatible_bridge_or_revision(self):
        manifest = approve(self.pending())
        self.bridge['compatibility_note'] = 'Another explicit reviewed bridge'
        self.rebind_bridge()
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            self.validate(manifest)
        manifest = approve(self.pending())
        self.bridge['verified_revision'] = 3
        self.rebind_bridge()
        with self.assertRaisesRegex(ValueError, 'revision differs'):
            self.validate(manifest)
        self.snapshot['revision_id'] = 3
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            self.validate(manifest)

    def test_snapshot_response_bytes_and_full_snapshot_are_bound(self):
        manifest = approve(self.pending())
        response = self.snapshot['responses'][0]
        response['body_base64'] = base64.b64encode(b'changed body').decode()
        with self.assertRaisesRegex(ValueError, 'response bytes differ'):
            self.validate(manifest)
        response['response_sha256'] = mapping.sha(b'changed body')
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            self.validate(manifest)

    def test_partial_redirected_or_corrupt_snapshot_is_not_evidence(self):
        original = copy.deepcopy(self.snapshot)
        for change in ('missing', 'redirect', 'not_get', 'base64', 'hash'):
            with self.subTest(change=change):
                self.snapshot = copy.deepcopy(original)
                if change == 'missing':
                    self.snapshot['responses'].pop()
                elif change == 'redirect':
                    self.snapshot['responses'][0]['http_status'] = 301
                elif change == 'not_get':
                    self.snapshot['responses'][0]['method'] = 'POST'
                elif change == 'base64':
                    self.snapshot['responses'][0]['body_base64'] = '@not-base64'
                else:
                    self.snapshot['responses'][0]['response_sha256'] = '0' * 64
                with self.assertRaises(ValueError):
                    self.assess()

    def test_source_bytes_and_wire_bytes_cannot_be_replaced(self):
        manifest = approve(self.pending())
        for prepared in (replace(self.prepared, xml=self.prepared.xml + b'\n'),
                         replace(self.prepared, body=self.prepared.body + b' '),
                         replace(self.prepared, binding='0' * 64)):
            with self.subTest(binding=prepared.binding):
                with self.assertRaisesRegex(ValueError, 'prepared source'):
                    self.validate(manifest, prepared=prepared)

    def test_protected_or_excluded_record_and_parent_ids_cannot_be_reviewed(self):
        for field in ('id', 'parent_id'):
            for identifier in ('17317855', '17317851', '17317859', '17317857', '17317853', '10042430', '15046283'):
                with self.subTest(field=field, identifier=identifier):
                    self.bridge['identity'] = {'id': '19000001', 'parent_id': '19000000',
                                               'owner': '123', 'created': NOW.isoformat()}
                    self.bridge['identity'][field] = identifier
                    self.rebind_bridge()
                    with self.assertRaisesRegex(ValueError, 'protected or excluded'):
                        self.assess()

    def test_digest_only_creation_proof_is_insufficient_for_publication_qa(self):
        self.duplicate = copy.deepcopy(self.fixture.proof)
        with self.assertRaisesRegex(ValueError, 'duplicate evidence'):
            self.assess()

    def test_duplicate_evidence_is_bound_to_production_source_and_wire_not_legacy_payload(self):
        original = copy.deepcopy(self.duplicate)
        changes = [('environment', 'sandbox'), ('fgdc_id', 'FGDC-142'), ('source_sha256', '0' * 64),
                   ('metadata_sha256', self.prepared.evidence['legacy_metadata_sha256']),
                   ('inventory_complete', False), ('candidates', [{'id': 'unexpected-candidate'}])]
        for key, value in changes:
            with self.subTest(field=key):
                self.duplicate = copy.deepcopy(original)
                self.duplicate[key] = value
                with self.assertRaisesRegex(ValueError, 'duplicate evidence'):
                    self.assess()

    def test_source_title_query_is_exact_and_not_modern_display_title(self):
        expected = self.duplicate['evidence'][0]['snapshot']['query']
        display = mapping.parse(self.prepared.body)['metadata']['title']
        self.assertNotEqual(expected, display)
        for query in (display, expected.casefold(), 'unrelated title', ''):
            with self.subTest(query=query):
                self.duplicate['evidence'][0]['snapshot']['query'] = query
                with self.assertRaisesRegex(ValueError, 'wrongly scoped'):
                    self.assess()

    def test_partial_total_next_page_or_malformed_raw_response_never_proves_absence(self):
        original = copy.deepcopy(self.duplicate)
        changes = [({'data': [], 'links': {}, 'meta': {'total': 1}}, True),
                   ({'data': [], 'links': {'next': 'https://example.invalid/page2'}, 'meta': {'total': 0}}, True),
                   ({'data': [], 'links': {}, 'meta': {'total': 0}}, False),
                   ({'data': [], 'links': {}, 'meta': {'total': False}}, True),
                   ({'data': [{'unparseable': True}], 'links': {}, 'meta': {'total': 1}}, True),
                   ('<html>Not an inventory</html>', True)]
        for body, complete in changes:
            with self.subTest(body=body, complete=complete):
                self.duplicate = copy.deepcopy(original)
                raw = self.duplicate['evidence'][0]['snapshot']
                raw['body'], raw['scope_complete'] = body, complete
                self.refresh_raw_digest()
                with self.assertRaisesRegex(ValueError, 'raw duplicate inventory'):
                    self.assess()

    def test_nonempty_crossref_inventory_cannot_be_approved_as_no_match(self):
        raw = self.duplicate['evidence'][0]['snapshot']
        raw.update(format='crossref', body={'message': {'items': [{'DOI': '10.1234/fixture',
                    'title': [raw['query']], 'author': [{'family': 'Fixture'}]}], 'total-results': 1}})
        self.refresh_raw_digest()
        self.assertTrue(snapshot_inventory(raw)['inventory_complete'])
        with self.assertRaisesRegex(ValueError, 'raw duplicate inventory'):
            self.assess()

    def test_raw_response_hash_endpoint_scope_and_format_must_match(self):
        original = copy.deepcopy(self.duplicate)
        for key, value in (('response_sha256', '0' * 64), ('endpoint', 'https://example.invalid/other'),
                           ('scope', 'Another claimed scope'), ('format', 'records'), ('http_status', 429)):
            with self.subTest(field=key):
                self.duplicate = copy.deepcopy(original)
                proof = self.duplicate['evidence'][0]
                target = proof['snapshot'] if key in ('format', 'http_status') else proof
                target[key] = value
                with self.assertRaises(ValueError):
                    self.assess()

    def test_snapshot_duplicate_and_raw_inventory_freshness_and_expiry_are_independent(self):
        stamp = (NOW - timedelta(hours=24, seconds=1)).isoformat()
        original_duplicate, original_snapshot = copy.deepcopy(self.duplicate), copy.deepcopy(self.snapshot)
        for field in ('snapshot', 'checked_at', 'retrieved_at', 'valid_until'):
            with self.subTest(field=field):
                self.duplicate, self.snapshot = copy.deepcopy(original_duplicate), copy.deepcopy(original_snapshot)
                if field == 'snapshot':
                    self.snapshot['captured_at'] = stamp
                elif field == 'retrieved_at':
                    self.duplicate['evidence'][0]['snapshot'][field] = stamp
                else:
                    self.duplicate[field] = stamp
                with self.assertRaises(ValueError):
                    self.assess()

    def test_future_naive_or_missing_evidence_time_holds(self):
        for value in ((NOW + timedelta(seconds=1)).isoformat(), NOW.replace(tzinfo=None).isoformat(), '', 'invalid'):
            with self.subTest(value=value):
                self.snapshot['captured_at'] = value
                with self.assertRaises(ValueError):
                    self.assess()

    def test_updated_duplicate_proof_requires_new_record_and_program_review(self):
        manifest = approve(self.pending())
        self.duplicate['valid_until'] = (NOW + timedelta(hours=2)).isoformat()
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            self.validate(manifest)
        current = self.assess()
        manifest['records'][0]['agent_evidence'] = current
        manifest['records'][0]['qa']['evidence'] = [mapping.sha(mapping.encode(current))]
        manifest['records'][0]['duplicate_review']['evidence'] = [current['duplicate_snapshot']]
        with self.assertRaisesRegex(ValueError, 'Program'):
            self.validate(manifest)

    def test_record_and_program_review_cannot_predate_evidence_or_claim_future_review(self):
        for target, offset in (('record', -1), ('record', 1), ('program', -1), ('program', 1)):
            with self.subTest(target=target, offset=offset):
                manifest = approve(self.pending())
                stamp = (NOW + timedelta(seconds=offset)).isoformat()
                if target == 'record':
                    manifest['records'][0]['qa']['reviewed_at'] = stamp
                else:
                    manifest['program_review']['independent_review']['reviewed_at'] = stamp
                with self.assertRaises(ValueError):
                    self.validate(manifest)

    def test_new_duplicate_check_or_raw_retrieval_invalidates_earlier_claimed_review(self):
        old = NOW - timedelta(minutes=30)
        review_time = NOW - timedelta(minutes=1)
        self.bridge['identity']['created'] = (old - timedelta(minutes=1)).isoformat()
        self.rebind_bridge()
        self.snapshot['captured_at'] = old.isoformat()
        for field in ('checked_at', 'retrieved_at'):
            with self.subTest(field=field):
                self.duplicate = raw_duplicates(self.prepared, bridge=self.bridge, snapshot=self.snapshot, now=old)
                target = self.duplicate if field == 'checked_at' else self.duplicate['evidence'][0]['snapshot']
                target[field] = NOW.isoformat()
                pending = self.pending()
                with self.assertRaisesRegex(ValueError, 'record review must follow all saved'):
                    self.validate(approve(pending, now=review_time))
                self.assertTrue(self.validate(approve(pending))['qa']['approved'])

    def test_external_searches_and_old_create_proof_cannot_replace_production_reconciliation(self):
        approved = approve(self.pending())
        production = self.duplicate.pop('production')
        with self.assertRaisesRegex(ValueError, 'production reconciliation is required'):
            self.validate(approved)
        self.duplicate['production'] = copy.deepcopy(self.fixture.proof)
        with self.assertRaisesRegex(ValueError, 'production reconciliation is required'):
            self.assess()
        self.duplicate['production'] = production
        self.assertIs(qa.validate_production(self.prepared, self.bridge, self.snapshot, production, now=NOW), production)

    def test_production_owner_environment_root_source_wire_and_bridge_are_exact(self):
        original = copy.deepcopy(self.duplicate['production'])
        changes = [('schema_version', True), ('kind', 'generic-duplicate-proof'),
                   ('origin', 'https://sandbox.zenodo.org'), ('owner', '124'), ('state_root', '/another/root'),
                   ('source_id', 'FGDC-142'), ('source_sha256', '0' * 64), ('wire_sha256', '0' * 64),
                   ('binding', '0' * 64), ('preparation_binding', '0' * 64)]
        for key, value in changes:
            with self.subTest(field=key):
                self.duplicate['production'] = copy.deepcopy(original)
                self.duplicate['production'][key] = value
                self.resign_production()
                with self.assertRaisesRegex(ValueError, 'production owner, source'):
                    self.assess()

    def test_only_exact_own_draft_may_match_or_be_excluded_from_production_inventory(self):
        original = copy.deepcopy(self.duplicate['production'])
        own = self.bridge['identity']['id']
        changes = [('own_records', []), ('own_records', [self.bridge['identity']] * 2),
                   ('matched_record_ids', []), ('matched_record_ids', [own, '19000002']),
                   ('matched_dois', ['10.1234/new-duplicate']), ('excluded_record_ids', []),
                   ('excluded_record_ids', [own, '19000002']), ('excluded_dois', ['10.1234/hidden'])]
        for key, value in changes:
            with self.subTest(field=key, value=value):
                self.duplicate['production'] = copy.deepcopy(original)
                self.duplicate['production'][key] = value
                self.resign_production()
                with self.assertRaisesRegex(ValueError, 'only the exact own draft'):
                    self.assess()
        for key, value in (('parent_id', '19000002'), ('owner', '124'),
                           ('created', (NOW - timedelta(seconds=1)).isoformat())):
            with self.subTest(identity_field=key):
                self.duplicate['production'] = copy.deepcopy(original)
                self.duplicate['production']['own_records'][0][key] = value
                self.resign_production()
                with self.assertRaisesRegex(ValueError, 'only the exact own draft'):
                    self.assess()

    def test_partial_inventory_or_unresolved_history_holds_despite_empty_external_search(self):
        original = copy.deepcopy(self.duplicate['production'])
        changes = [('complete', False), ('history_reconciled', False),
                   ('unresolved_candidates', ['another matching source']),
                   ('unresolved_attempts', [{'source_id': self.prepared.source_id, 'status': 'uncertain'}])]
        for key, value in changes:
            with self.subTest(field=key):
                self.duplicate['production'] = copy.deepcopy(original)
                self.duplicate['production'][key] = value
                self.resign_production()
                with self.assertRaisesRegex(ValueError, 'no unresolved history'):
                    self.assess()
        self.duplicate['production'] = copy.deepcopy(original)
        self.duplicate['production']['historical_exception']['draft_row_sha256'] = '0' * 64
        self.resign_production()
        with self.assertRaisesRegex(ValueError, 'preserved own draft row and intent'):
            self.assess()
        self.duplicate['production']['historical_exception'] = {
            'draft_row_sha256': self.bridge['draft_row_sha256'], 'create_intent_sha256': '0' * 64}
        self.resign_production()
        with self.assertRaisesRegex(ValueError, 'preserved own draft row and intent'):
            self.assess()

    def test_production_capture_has_both_reviewed_owner_and_history_references(self):
        original = copy.deepcopy(self.duplicate['production'])
        for change in ('missing_history', 'duplicate_role', 'wrong_scope', 'wrong_origin', 'wrong_owner',
                       'missing_reference', 'wrong_capture_hash'):
            with self.subTest(change=change):
                self.duplicate['production'] = copy.deepcopy(original)
                evidence = self.duplicate['production']['evidence']
                if change == 'missing_history':
                    evidence.pop()
                elif change == 'duplicate_role':
                    evidence[1] = copy.deepcopy(evidence[0])
                else:
                    key, value = {
                        'wrong_scope': ('scope', 'arbitrary external title search'),
                        'wrong_origin': ('origin', 'https://example.invalid'), 'wrong_owner': ('owner', '124'),
                        'missing_reference': ('reference', ''), 'wrong_capture_hash': ('sha256', '0' * 64),
                    }[change]
                    evidence[0][key] = value
                self.resign_production()
                with self.assertRaises(ValueError):
                    self.assess()

    def test_production_projection_requires_independent_review_of_its_exact_content(self):
        original = copy.deepcopy(self.duplicate['production'])
        for key, value in (('captured_by', ''), ('reviewed_by', '  OFFLINE CAPTURE FIXTURE  '),
                           ('reviewer_type', 'unattended'), ('rationale', ''), ('reviewed_projection_sha256', '0' * 64)):
            with self.subTest(field=key):
                self.duplicate['production'] = copy.deepcopy(original)
                self.duplicate['production'][key] = value
                if key != 'reviewed_projection_sha256':
                    self.resign_production()
                with self.assertRaisesRegex(ValueError, 'independent review must bind'):
                    self.assess()
        self.duplicate['production'] = copy.deepcopy(original)
        self.duplicate['production']['evidence'][0]['reference'] = 'different-capture-reference'
        with self.assertRaisesRegex(ValueError, 'independent review must bind'):
            self.assess()

    def test_production_window_cannot_be_stale_future_overlong_or_predate_snapshot(self):
        original = copy.deepcopy(self.duplicate['production'])
        for key, value in (('expires_at', NOW.isoformat()),
                           ('expires_at', (NOW + timedelta(hours=1, seconds=1)).isoformat()),
                           ('checked_at', (NOW - timedelta(seconds=1)).isoformat()),
                           ('checked_at', (NOW + timedelta(seconds=1)).isoformat()),
                           ('reviewed_at', (NOW - timedelta(seconds=1)).isoformat()),
                           ('reviewed_at', (NOW + timedelta(seconds=1)).isoformat())):
            with self.subTest(field=key, value=value):
                self.duplicate['production'] = copy.deepcopy(original)
                self.duplicate['production'][key] = value
                self.resign_production()
                with self.assertRaisesRegex(ValueError, 'one-hour window'):
                    self.assess()
        for offset in (-1, 1):
            with self.subTest(capture_offset=offset):
                self.duplicate['production'] = copy.deepcopy(original)
                self.duplicate['production']['evidence'][0]['observed_at'] = (NOW + timedelta(seconds=offset)).isoformat()
                self.resign_production()
                with self.assertRaisesRegex(ValueError, 'production capture must be current'):
                    self.assess()

    def test_new_production_capture_or_review_invalidates_prior_qa_and_program_approval(self):
        original_manifest = approve(self.pending())
        self.duplicate['production']['evidence'][0]['reference'] = 'new-independently-reviewed-owner-capture'
        self.resign_production()
        with self.assertRaisesRegex(ValueError, 'stale or altered'):
            self.validate(original_manifest)
        old = NOW - timedelta(minutes=30)
        self.bridge['identity']['created'] = (old - timedelta(minutes=1)).isoformat()
        self.rebind_bridge()
        self.snapshot['captured_at'] = old.isoformat()
        self.duplicate = raw_duplicates(self.prepared, bridge=self.bridge, snapshot=self.snapshot, now=old)
        production = self.duplicate['production']
        production['reviewed_at'] = NOW.isoformat()
        pending = self.pending()
        with self.assertRaisesRegex(ValueError, 'record review must follow all saved'):
            self.validate(approve(pending, now=NOW - timedelta(minutes=1)))
        self.assertTrue(self.validate(approve(pending))['qa']['approved'])


if __name__ == '__main__':
    unittest.main()
