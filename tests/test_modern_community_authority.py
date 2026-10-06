"""Pure offline validation of reviewed PICES destination authority."""

import copy
import unittest
from datetime import timedelta

from scripts import modern_publication_qa as qa
from tests.test_modern_publication import NOW, community


class CommunityAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.bound = {'identity': {'owner': '123', 'id': '19000001'}}
        self.value = community(self.bound)

    def resign(self, value):
        value['reviewed_projection_sha256'] = qa.community_projection_hash(value)
        return value

    def validate(self, value):
        return qa.validate_community(value, self.bound, now=NOW)

    def test_effective_include_permission_can_be_false_without_implying_completion(self):
        self.value['permissions']['include_directly'] = False
        self.assertEqual(self.validate(self.resign(self.value)), self.value)

    def test_members_review_policy_does_not_broaden_submission_policy(self):
        self.assertEqual(self.value['review_policy'], 'members')
        self.assertEqual(self.validate(self.value), self.value)
        self.value['submission_policy'] = 'members'
        with self.assertRaises(ValueError):
            self.validate(self.resign(self.value))

    def test_verified_immediate_parent_is_explicit(self):
        self.value['parent_id'] = '00000000-0000-4000-8000-000000000099'
        self.assertEqual(self.validate(self.resign(self.value)), self.value)
        self.value.pop('parent_id')
        with self.assertRaises(ValueError):
            self.validate(self.resign(self.value))

    def test_missing_or_untyped_effective_permissions_hold(self):
        for key in ('manage', 'read_draft', 'submit_record', 'include_directly'):
            for replacement in (None, 0, 1, 'true'):
                with self.subTest(key=key, replacement=replacement):
                    value = copy.deepcopy(self.value)
                    value['permissions'][key] = replacement
                    with self.assertRaises(ValueError):
                        self.validate(self.resign(value))
        for key in ('manage', 'read_draft', 'submit_record'):
            value = copy.deepcopy(self.value)
            value['permissions'][key] = False
            with self.assertRaises(ValueError):
                self.validate(self.resign(value))

    def test_wrong_origin_owner_identity_slug_visibility_or_unknown_policy_hold(self):
        changes = {'origin': 'https://sandbox.zenodo.org', 'owner': '456', 'record_id': '19000002',
                   'slug': 'another-community', 'visibility': 'restricted',
                   'submission_policy': '', 'review_policy': 'unknown', 'id': None,
                   'parent_id': self.value['id'], 'schema_version': True}
        for key, replacement in changes.items():
            with self.subTest(key=key):
                value = copy.deepcopy(self.value)
                value[key] = replacement
                with self.assertRaises(ValueError):
                    self.validate(self.resign(value))

    def test_review_and_evidence_cannot_be_omitted_or_silently_changed(self):
        for key in self.value:
            value = copy.deepcopy(self.value)
            value.pop(key)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.validate(value)
        self.value['submission_policy'] = 'closed'
        with self.assertRaises(ValueError):
            self.validate(self.value)
        self.assertEqual(self.validate(self.resign(self.value)), self.value)

    def test_capture_review_window_and_independence_hold(self):
        changes = [('reviewed_by', 'dummy mac'), ('checked_at', (NOW + timedelta(seconds=1)).isoformat()),
                   ('reviewed_at', (NOW + timedelta(seconds=1)).isoformat()),
                   ('expires_at', NOW.isoformat()),
                   ('expires_at', (NOW + timedelta(hours=1, seconds=1)).isoformat())]
        for key, replacement in changes:
            value = copy.deepcopy(self.value)
            value[key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(self.resign(value))

    def test_both_hashed_capture_roles_are_required(self):
        for alteration in ('hash', 'duplicate-role', 'empty-reference', 'missing'):
            value = copy.deepcopy(self.value)
            if alteration == 'hash':
                value['evidence'][0]['sha256'] = 'bad'
            elif alteration == 'duplicate-role':
                value['evidence'][1]['role'] = 'community'
            elif alteration == 'empty-reference':
                value['evidence'][1]['reference'] = ''
            else:
                value['evidence'].pop()
            with self.subTest(alteration=alteration), self.assertRaises(ValueError):
                self.validate(self.resign(value))
