"""Exact821 answer plus finite83 reviewer reconciliation; no rights or release.

The historical metadata-public statement is bound to the asked question, source
bytes and complete constraint/context elements. Separate restricted, unlicensed
XML rehosting authority remains mandatory; unrelated ambiguities stay held.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_SHA256 = '3e2bc71f6cd409769a8ccb34912ec2c1a7a3802f3444c2446038e347dbc5a657'
RECONCILED_MANIFEST_SHA256 = '242024bcf750e0fd3ea0097ee34eb47fb86f0674fb554fe2e0b78ddce4a589c1'
ORIGINAL_OBJECT_SHA256 = 'a07feaa7f99b0b0f22dd274036bf660346cf8acfdcfc61d2103f1ec8951b2a6f'
ATTESTED_AT = '2026-10-03T20:20:00Z'
STATEMENT = 'they reply to the underlying data. all these metadata records were public before'


def _manifest(reference):
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') not in (MANIFEST_SHA256, RECONCILED_MANIFEST_SHA256)):
        raise ValueError('Source scope requires an exact reviewed finite attestation/reconciliation reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Source scope attestation is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Source scope attestation differs from the pinned question/source profile')
    manifest = json.loads(raw)
    if reference['manifest_sha256'] == RECONCILED_MANIFEST_SHA256:
        original = deepcopy(manifest)
        review = original.pop('reconciled_scope_review')
        if len(original['members']) != 904:
            raise ValueError('Reconciliation requires the exact821 plus83 membership')
        original['members'] = original['members'][:821]
        digest = hashlib.sha256(json.dumps(original, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if digest != ORIGINAL_OBJECT_SHA256:
            raise ValueError('Original821 question, answer and members must remain verbatim')
        for evidence in review['original_statement_references']:
            try:
                raw_evidence = (Path(__file__).resolve().parents[1] / evidence['manifest_path']).read_bytes()
            except OSError as exc:
                raise ValueError('Original statement evidence is unavailable') from exc
            if hashlib.sha256(raw_evidence).hexdigest() != evidence['manifest_sha256']:
                raise ValueError('Reconciliation requires unchanged original statement evidence')
    return manifest


def scope_member_ids(reference):
    """Invalid or withdrawn evidence cannot select any source for an exception."""
    try:
        manifest = _manifest(reference)
    except ValueError:
        return frozenset()
    return frozenset(member['source_id'] for member in manifest['members'])


def _elements(root, xpath):
    result = []
    for node in root.findall(xpath):
        node = deepcopy(node)
        node.tail = None
        result.append(ET.tostring(node, encoding='unicode'))
    return result


def validate_scope_attestation(reference, source_id, source_sha256, root, reviewed_at):
    """Recheck immutable evidence, exact XML fields and post-attestation time."""
    manifest = _manifest(reference)
    members = [m for m in manifest['members'] if m['source_id'] == source_id
               and m['source_sha256'] == source_sha256]
    if len(members) != 1:
        raise ValueError('Source ID/hash is outside the exact finite scope membership')
    member = members[0]
    reconciled = member['cohort'] == 'ordinary_contact_unknown_placeholder83'
    for xpath, expected in member['constraint_elements'].items():
        nodes = root.findall(xpath)
        if (len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib
                or _elements(root, xpath) != expected):
            raise ValueError('Source scope requires exact plain four-field constraint elements')
    for xpath, expected in member['context_elements_sha256'].items():
        actual = hashlib.sha256(json.dumps(_elements(root, xpath), sort_keys=True,
                                           separators=(',', ':')).encode()).hexdigest()
        if actual != expected:
            raise ValueError('Source scope requires the complete question-bound source context')
    if root.find('./metainfo/metsi') is not None or root.find('./metainfo/metextns') is not None:
        raise ValueError('Metadata security/extensions require separate adjudication')
    try:
        stamp = datetime.fromisoformat(reviewed_at.replace('Z', '+00:00'))
        attested = datetime.fromisoformat(ATTESTED_AT.replace('Z', '+00:00'))
        if reconciled:
            attested = max(attested, datetime.fromisoformat(manifest['reconciled_scope_review']['reviewed_at']))
        if stamp.tzinfo is None or stamp < attested or stamp > datetime.now(timezone.utc):
            raise ValueError
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('Source scope assessment must use current aware time after the exact user attestation') from exc
    result = {'status': 'REVIEWER_RECONCILED' if reconciled else 'USER_ATTESTED',
            'statement': STATEMENT, 'attested_at': ATTESTED_AT,
            'cohort': member['cohort'], 'source_id': source_id, 'source_sha256': source_sha256,
            'meaning': manifest['meaning'], 'grants_rehosting': False, 'grants_new_license': False,
            'underlying_data_rights_granted': False, 'publication_approved': False}
    if reconciled:
        result.update(meaning=manifest['reconciled_scope_review']['meaning'],
                      reconciliation_reviewed_at=manifest['reconciled_scope_review']['reviewed_at'],
                      new_user_attestation_event=False, original_direct_question_membership_enlarged=False)
    return result


def validate_scope_policy(policy, source_id, source_sha256, root, metadata):
    """Common agent/human gate: scope clarification never supplies XML authority."""
    from scripts.rehosting_authority import (
        validate_authority,
        validate_restricted_metadata,
    )
    if any(policy.get(key) is not None for key in
           ('source_access_interpretation', 'dataset_access_interpretation')):
        raise ValueError('Conflicting source scope interpretations require separate adjudication')
    authority = policy.get('rehosting_authority')
    if authority is None:
        raise ValueError('Source scope clarification requires separate rehosting authority')
    validate_authority(authority, source_id, source_sha256)
    validate_restricted_metadata(metadata)
    if (policy.get('license') not in ('', None) or policy.get('rights_scope') != 'original_fgdc_xml'
            or policy.get('rights_source_xpath') != './metainfo/metuc'
            or policy.get('date_semantics') != 'source_metadata_date'):
        raise ValueError('Source scope clarification requires restricted unlicensed original XML policy')
    return validate_scope_attestation(policy.get('source_scope_attestation'), source_id,
                                      source_sha256, root, policy.get('reviewed_at'))
