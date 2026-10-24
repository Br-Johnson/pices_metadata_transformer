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
# Third generation (2026-10-23): the reconciled904 plus the 22 access holds Brett cleared on the
# held-sources evidence sheet (questions A1, A2 and A3 of held_sources_decisions.json).
DECIDED_MANIFEST_SHA256 = '045e29e95b75c88847df49372374872a23844c541fa8b4c41faac0f26b73a62d'
ORIGINAL_OBJECT_SHA256 = 'a07feaa7f99b0b0f22dd274036bf660346cf8acfdcfc61d2103f1ec8951b2a6f'
RECONCILED_OBJECT_SHA256 = '76acad88af241f84351d2fdf22225735f75eaae1f154aef54e1ab15384dace6d'
DECISION_BLOCK = 'held_sources_decisions_2026_10_23'
DECIDED_COUNT = 22
ATTESTED_AT = '2026-10-03T20:20:00Z'
STATEMENT = 'they reply to the underlying data. all these metadata records were public before'


def _canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _check_evidence(references, message):
    for evidence in references:
        try:
            raw_evidence = (Path(__file__).resolve().parents[1] / evidence['manifest_path']).read_bytes()
        except OSError as exc:
            raise ValueError('Original statement evidence is unavailable') from exc
        if hashlib.sha256(raw_evidence).hexdigest() != evidence['manifest_sha256']:
            raise ValueError(message)


def _check_decided(manifest):
    """The decided926: the reconciled904 verbatim plus 22 members that mirror Brett's decisions file."""
    reconciled = deepcopy(manifest)
    block = reconciled.pop(DECISION_BLOCK)
    if len(reconciled['members']) != 904 + DECIDED_COUNT:
        raise ValueError('Decided scope requires the exact904 plus22 membership')
    added = reconciled['members'][904:]
    reconciled['members'] = reconciled['members'][:904]
    if _canonical(reconciled) != RECONCILED_OBJECT_SHA256:
        raise ValueError('Reconciled904 question, answer, review and members must remain verbatim')
    if (block.get('status') != 'USER_ATTESTED' or block.get('decided_by') != 'Brett Johnson'
            or block.get('decided_at') != '2026-10-23' or not isinstance(block.get('cohorts'), dict)
            or any(block.get(key) is not False for key in
                   ('grants_rehosting', 'grants_new_license', 'underlying_data_rights_granted', 'publication_approved'))):
        raise ValueError('Decided scope must preserve the exact 2026-10-23 user decisions')
    _check_evidence(block['original_statement_references'], 'Decided scope requires unchanged decision evidence')
    decisions = next(evidence for evidence in block['original_statement_references']
                     if evidence['key'] == 'held_sources_decisions')
    answered = json.loads((Path(__file__).resolve().parents[1] / decisions['manifest_path']).read_bytes())
    questions = {row['question']: row for row in answered['decisions']}
    cleared = {(row['question'], source) for row in answered['decisions']
               if row['effect'] == 'access hold cleared' for source in row['sources']}
    decided = {(block['cohorts'][member['cohort']]['question'], member['source_id']) for member in added
               if member['cohort'] in block['cohorts']}
    if len(decided) != len(added) or decided != cleared:
        raise ValueError('Decided scope members must be exactly the access holds the decisions file clears')
    for cohort in block['cohorts'].values():
        # The question, Brett's answer and its effect are his words from the decisions file, verbatim.
        row = questions.get(cohort.get('question'))
        if row is None or any(cohort.get(key) != row[key] for key in ('asked', 'answer', 'effect')):
            raise ValueError('Decided scope cohorts must quote the decisions file verbatim')
    return reconciled


def _check_reconciled(manifest):
    original = deepcopy(manifest)
    review = original.pop('reconciled_scope_review')
    if len(original['members']) != 904:
        raise ValueError('Reconciliation requires the exact821 plus83 membership')
    original['members'] = original['members'][:821]
    if _canonical(original) != ORIGINAL_OBJECT_SHA256:
        raise ValueError('Original821 question, answer and members must remain verbatim')
    _check_evidence(review['original_statement_references'],
                    'Reconciliation requires unchanged original statement evidence')


def _manifest(reference):
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') not in (MANIFEST_SHA256, RECONCILED_MANIFEST_SHA256,
                                                      DECIDED_MANIFEST_SHA256)):
        raise ValueError('Source scope requires an exact reviewed finite attestation/reconciliation reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Source scope attestation is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Source scope attestation differs from the pinned question/source profile')
    manifest = json.loads(raw)
    reconciled = manifest
    if reference['manifest_sha256'] == DECIDED_MANIFEST_SHA256:
        reconciled = _check_decided(manifest)
    if reference['manifest_sha256'] in (RECONCILED_MANIFEST_SHA256, DECIDED_MANIFEST_SHA256):
        _check_reconciled(reconciled)
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
    block = manifest.get(DECISION_BLOCK)
    decided = block is not None and member['cohort'] in block['cohorts']
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
        if decided:
            attested = max(attested, datetime.fromisoformat(block['attested_at'].replace('Z', '+00:00')))
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
    if decided:
        # Brett's 2026-10-23 answer to the exact question the evidence sheet asked about this record.
        cohort = block['cohorts'][member['cohort']]
        result.update(statement=cohort['asked'] + ' ' + cohort['answer'], attested_at=block['attested_at'],
                      decided_by=block['decided_by'], decided_at=block['decided_at'],
                      decision_question=cohort['question'], meaning=cohort['meaning'],
                      new_user_attestation_event=True, original_direct_question_membership_enlarged=False)
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
