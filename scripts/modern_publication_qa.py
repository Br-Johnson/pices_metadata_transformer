"""Offline QA for one source-backed modern draft; never approve or publish it.

Callers must freshly prepare the source and validate the compatibility bridge and
the five-response draft snapshot with the publication controller. This adapter
binds those inputs to explicit record and independent program review. It reuses
the raw inventory parser, without projecting modern records into legacy drafts.
"""

from __future__ import annotations

import base64
import binascii
import copy
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from scripts.matching.evidence import snapshot_inventory
from scripts.modern_singleton import (
    DIRECT_POLICY,
    DIRECT_SHA,
    PROFILE_SHA,
    encode,
    parse,
    sha,
    source_policy,
    validate_payload,
)
from scripts.production_mutations import EXCLUDED, PROTECTED
from scripts.qa_manifest import QA_CHECKS, validate_program_review

KIND = 'modern-singleton-qa-v1'
PRODUCTION_SCOPES = {
    'owner_inventory': 'all_owned_draft_and_published_records_versions_and_file_descriptors',
    'source_history': 'all_retained_source_identity_and_mutation_attempts_in_original_state_root',
}
PRODUCTION_REVIEW_FIELDS = {
    'reviewed_by', 'reviewer_type', 'reviewed_at', 'rationale', 'reviewed_projection_sha256',
}


def _require(condition, reason):
    if not condition:
        raise ValueError('Modern publication QA: ' + reason)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _time(value):
    _require(_text(value), 'an aware evidence timestamp is required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('Modern publication QA: malformed evidence timestamp') from None
    _require(result.tzinfo is not None and result.utcoffset() is not None,
             'an aware evidence timestamp is required')
    return result


def _fresh(value, now):
    result = _time(value)
    _require(timedelta(0) <= now - result <= timedelta(hours=24),
             'saved evidence is stale or from the future')
    return result


def _source_title(xml):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise ValueError('Modern publication QA: invalid source XML') from None
    for path in ('./idinfo/citation/citeinfo/title', './title'):
        node = root.find(path)
        if node is not None:
            title = re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()
            if title:
                return title
    raise ValueError('Modern publication QA: source title is missing')


def production_projection_hash(production):
    """The independent reviewer attests the complete projection, not empty flags."""
    return sha(encode({key: value for key, value in production.items() if key not in PRODUCTION_REVIEW_FIELDS}))


def validate_production(prepared, bridge, snapshot, production, *, now):
    """Validate the independently reviewed production capture projection.

    Capture authenticity and completeness require actual independent review by
    the parent, as for a bounded provider grant. Hashes bind that decision; they
    cannot establish its truth. Generic external searches and historical create
    proofs cannot supply this separate current owner/source/history gate.
    """
    _require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() is not None,
             'an aware production reconciliation time is required')
    keys = {
        'schema_version', 'kind', 'origin', 'owner', 'binding', 'preparation_binding',
        'state_root', 'source_id', 'source_sha256', 'wire_sha256', 'own_records',
        'matched_record_ids', 'matched_dois', 'excluded_record_ids', 'excluded_dois',
        'unresolved_candidates', 'unresolved_attempts', 'historical_exception',
        'complete', 'history_reconciled', 'checked_at', 'expires_at', 'inventory_sha256',
        'history_sha256', 'captured_by', 'evidence',
    } | PRODUCTION_REVIEW_FIELDS
    _require(isinstance(production, dict) and set(production) == keys,
             'fresh independently reviewed production reconciliation is required')
    identity = bridge['identity']
    _require(type(production['schema_version']) is int and production['schema_version'] == 1
             and production['kind'] == 'modern-production-duplicate-v1'
             and production['origin'] == 'https://zenodo.org' and production['owner'] == identity['owner']
             and production['binding'] == bridge['binding']
             and production['preparation_binding'] == prepared.binding
             and _text(bridge.get('state_root')) and production['state_root'] == bridge['state_root']
             and production['source_id'] == prepared.source_id
             and production['source_sha256'] == sha(prepared.xml)
             and production['wire_sha256'] == sha(prepared.body),
             'production owner, source, wire, bridge or original state root differs')
    _require(production['complete'] is True and production['history_reconciled'] is True
             and production['own_records'] == [identity]
             and production['matched_record_ids'] == [identity['id']]
             and production['matched_dois'] == []
             and production['excluded_record_ids'] == [identity['id']]
             and production['excluded_dois'] == []
             and production['unresolved_candidates'] == [] and production['unresolved_attempts'] == [],
             'production reconciliation permits only the exact own draft and no unresolved history')
    _require(all(_digest(bridge.get(key)) for key in ('draft_row_sha256', 'create_intent_sha256'))
             and production['historical_exception'] == {
                 key: bridge[key] for key in ('draft_row_sha256', 'create_intent_sha256')},
             'production history exception must identify the preserved own draft row and intent')
    _require(all(_text(production[key]) for key in ('captured_by', 'reviewed_by', 'rationale'))
             and production['reviewer_type'] in ('human', 'agent')
             and production['captured_by'].strip().casefold() != production['reviewed_by'].strip().casefold()
             and _digest(production['reviewed_projection_sha256'])
             and production['reviewed_projection_sha256'] == production_projection_hash(production),
             'independent review must bind the exact production projection')
    checked, expiry, reviewed = (_time(production[key]) for key in ('checked_at', 'expires_at', 'reviewed_at'))
    captured = _time(snapshot['captured_at'])
    _require(_time(identity['created']) <= captured <= checked <= reviewed <= now < expiry
             and timedelta(0) < expiry - checked <= timedelta(hours=1),
             'production reconciliation is stale, unreviewed or outside its one-hour window')
    evidence = production['evidence']
    _require(isinstance(evidence, list) and len(evidence) == 2
             and all(isinstance(item, dict) and set(item) == {
                 'role', 'scope', 'origin', 'owner', 'reference', 'sha256', 'observed_at'}
                 and isinstance(item['role'], str) for item in evidence)
             and {item['role'] for item in evidence} == set(PRODUCTION_SCOPES),
             'both owner inventory and source history capture references are required')
    for item in evidence:
        role = item['role']
        digest = production['inventory_sha256' if role == 'owner_inventory' else 'history_sha256']
        _require(item['scope'] == PRODUCTION_SCOPES[role] and item['origin'] == 'https://zenodo.org'
                 and item['owner'] == identity['owner'] and _text(item['reference'])
                 and _digest(digest) and item['sha256'] == digest,
                 'production capture scope, owner, origin or digest differs')
        observed = _time(item['observed_at'])
        _require(captured <= observed <= checked and expiry <= observed + timedelta(hours=1),
                 'production capture must be current and precede its reviewed reconciliation')
    return production


def _duplicate_evidence(prepared, bridge, snapshot, duplicate, *, now):
    _require(isinstance(duplicate, dict)
             and type(duplicate.get('schema_version')) is int and duplicate['schema_version'] == 1
             and duplicate.get('status') == 'checked_no_match'
             and duplicate.get('inventory_complete') is True
             and duplicate.get('environment') == 'production'
             and duplicate.get('fgdc_id') == prepared.source_id
             and duplicate.get('source_sha256') == sha(prepared.xml)
             and duplicate.get('metadata_sha256') == sha(prepared.body)
             and duplicate.get('candidates') == [] and _text(duplicate.get('scope'))
             and isinstance(duplicate.get('evidence'), list) and duplicate['evidence'],
             'complete source and modern wire-scoped duplicate evidence is required')
    _fresh(duplicate.get('checked_at'), now)
    _require(_time(duplicate.get('valid_until')) > now, 'duplicate evidence has expired')
    validate_production(prepared, bridge, snapshot, duplicate.get('production'), now=now)
    title = _source_title(prepared.xml)
    for proof in duplicate['evidence']:
        _require(isinstance(proof, dict) and proof.get('status') == 'checked_no_match'
                 and proof.get('inventory_complete') is True and _text(proof.get('endpoint'))
                 and _text(proof.get('scope')) and _digest(proof.get('response_sha256')),
                 'raw duplicate proof provenance is incomplete')
        raw = proof.get('snapshot')
        _require(isinstance(raw, dict) and raw.get('format') in ('oai', 'datacite', 'crossref', 'dspace'),
                 'a recognized raw repository snapshot is required')
        inventory = snapshot_inventory(raw)
        _require(inventory['inventory_complete'] is True and inventory['records'] == []
                 and inventory['response_sha256'] == proof['response_sha256']
                 and inventory['endpoint'] == proof['endpoint'] and inventory['scope'] == proof['scope']
                 and raw.get('query') == title,
                 'raw duplicate inventory is partial, nonempty, altered or wrongly scoped')
        _fresh(raw.get('retrieved_at'), now)


def assess(prepared, bridge: dict, snapshot: dict, duplicate: dict, *, now: datetime) -> dict:
    """Bind validated modern inputs and complete raw duplicate evidence, offline.

Successful assessment supplies evidence only. It does not imply a reviewer has
approved a record, reviewed the program, or authorized release.
    """
    _require(isinstance(now, datetime) and now.tzinfo is not None and now.utcoffset() is not None,
             'an aware assessment time is required')
    evidence = prepared.evidence
    _, policy_fields = source_policy(prepared.source_id)
    policy_keys = {'schema_version', 'policy', 'mapping_manifest_sha256', 'creator_cohort'}
    _require(isinstance(evidence, dict) and type(evidence.get('schema_version')) is int
             and {key: evidence[key] for key in policy_keys if key in evidence} == policy_fields
             and evidence.get('creator_profile_sha256') ==
             (DIRECT_SHA if policy_fields['policy'] == DIRECT_POLICY else PROFILE_SHA)
             and evidence.get('source_id') == prepared.source_id
             and evidence.get('source_sha256') == sha(prepared.xml)
             and evidence.get('wire_sha256') == sha(prepared.body)
             and prepared.binding == sha(encode(evidence))
             and prepared.source_id not in PROTECTED,
             'prepared source, XML or modern wire binding differs')
    validate_payload(parse(prepared.body))
    artifact = evidence.get('artifact_contract')
    _require(isinstance(artifact, dict) and artifact.get('source_id') == prepared.source_id
             and isinstance(artifact.get('files'), list) and len(artifact['files']) == 1
             and isinstance(artifact['files'][0], dict)
             and artifact['files'][0].get('sha256') == sha(prepared.xml),
             'the original XML artifact binding differs')
    _require(isinstance(bridge, dict) and bridge.get('kind') == 'modern-singleton-bridge-v1'
             and bridge.get('preparation_binding') == prepared.binding
             and bridge.get('binding') == sha(encode({k: v for k, v in bridge.items() if k != 'binding'})),
             'the validated compatibility bridge differs')
    identity = bridge.get('identity')
    _require(isinstance(identity, dict) and set(identity) == {'id', 'parent_id', 'owner', 'created'},
             'complete modern identity is required')
    _require(all(isinstance(identity[key], str)
                 and re.fullmatch('[1-9][0-9]{0,19}', identity[key]) for key in ('id', 'parent_id', 'owner'))
             and identity['id'] != identity['parent_id'], 'modern identities must be distinct decimal strings')
    prohibited = EXCLUDED | {value[0] for value in PROTECTED.values()}
    _require(not {int(identity['id']), int(identity['parent_id'])} & prohibited,
             'protected or excluded modern identity')
    _require(_time(identity['created']) <= now, 'modern creation time is in the future')
    revision = bridge.get('verified_revision')
    _require(type(revision) is int and revision >= 0, 'verified modern revision is missing')
    _require(isinstance(snapshot, dict) and type(snapshot.get('schema_version')) is int
             and snapshot['schema_version'] == 1 and snapshot.get('kind') == 'modern-draft-snapshot-v1'
             and snapshot.get('bridge_binding') == bridge['binding'] and snapshot.get('identity') == identity
             and type(snapshot.get('revision_id')) is int and snapshot['revision_id'] == revision,
             'draft snapshot identity, bridge or revision differs')
    _fresh(snapshot.get('captured_at'), now)
    responses = snapshot.get('responses')
    _require(isinstance(responses, list) and len(responses) == 5,
             'all five saved draft responses are required')
    for response in responses:
        _require(isinstance(response, dict) and response.get('method') == 'GET'
                 and type(response.get('http_status')) is int and response['http_status'] == 200
                 and _text(response.get('path')) and _text(response.get('media_type'))
                 and _digest(response.get('response_sha256'))
                 and isinstance(response.get('body_base64'), str), 'saved draft response is incomplete')
        try:
            raw = base64.b64decode(response['body_base64'], validate=True)
        except (ValueError, binascii.Error):
            raise ValueError('Modern publication QA: malformed saved response bytes') from None
        _require(sha(raw) == response['response_sha256'], 'saved draft response bytes differ')
    _duplicate_evidence(prepared, bridge, snapshot, duplicate, now=now)
    return copy.deepcopy({
        'schema_version': 1, 'kind': 'modern-singleton-qa-evidence-v1',
        'checks': dict.fromkeys(QA_CHECKS, True), 'source_id': prepared.source_id,
        'source_sha256': sha(prepared.xml), 'metadata_sha256': sha(prepared.body),
        'preparation_binding': prepared.binding, 'prepared_evidence': evidence,
        'artifact_contract': artifact,
        'bridge': {'sha256': sha(encode(bridge)), 'binding': bridge['binding'],
                   'identity': identity, 'verified_revision': revision},
        'remote_snapshot': {'sha256': sha(encode(snapshot)), 'captured_at': snapshot['captured_at'],
                            'revision_id': revision},
        'duplicate_snapshot': {'sha256': sha(encode(duplicate))}, 'raw_duplicate_proof': duplicate,
    })


def pending_manifest(prepared, bridge, snapshot, duplicate, *, source_revision: str, now: datetime) -> dict:
    """Produce an unapproved schema 2 manifest, retaining evidence for reviewers."""
    _require(_text(source_revision), 'source revision is required')
    evidence = assess(prepared, bridge, snapshot, duplicate, now=now)
    row = {
        'fgdc_id': prepared.source_id, 'deposition_id': bridge['identity']['id'],
        'source_sha256': evidence['source_sha256'], 'metadata_sha256': evidence['metadata_sha256'],
        'artifact_contract': copy.deepcopy(evidence['artifact_contract']), 'agent_evidence': evidence,
        'qa': {'approved': False, 'reviewer_type': '', 'reviewer': '', 'run_id': '',
               'review_revision': '', 'reviewed_at': '', 'rationale': '',
               'checks': dict.fromkeys(QA_CHECKS, False), 'evidence': [sha(encode(evidence))]},
        'duplicate_review': {'status': 'pending', 'classification': None, 'rationale': '', 'evidence': []},
    }
    return {'schema_version': 2, 'kind': KIND, 'environment': 'production',
            'source_revision': source_revision, 'prepared_at': now.isoformat(), 'records': [row],
            'program_review': {name: {'status': 'pending', 'evidence': []}
                               for name in ('independent_review', 'risk_stratified_spotcheck')}}


def validate(manifest, prepared, bridge, snapshot, duplicate, *, now: datetime) -> dict:
    """Require explicit record approval and independently bound program review."""
    current = assess(prepared, bridge, snapshot, duplicate, now=now)
    _require(isinstance(manifest, dict) and type(manifest.get('schema_version')) is int
             and manifest['schema_version'] == 2 and manifest.get('kind') == KIND
             and manifest.get('environment') == 'production' and _text(manifest.get('source_revision')),
             'a versioned production modern QA manifest is required')
    rows = manifest.get('records')
    _require(isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict),
             'exactly one modern singleton QA record is required')
    row = rows[0]
    _require(row.get('fgdc_id') == prepared.source_id
             and row.get('deposition_id') == bridge['identity']['id']
             and row.get('source_sha256') == current['source_sha256']
             and row.get('metadata_sha256') == current['metadata_sha256']
             and row.get('artifact_contract') == current['artifact_contract']
             and row.get('agent_evidence') == current, 'approved identity or evidence is stale or altered')
    qa = row.get('qa')
    _require(isinstance(qa, dict) and qa.get('approved') is True
             and qa.get('reviewer_type') in ('human', 'agent')
             and all(_text(qa.get(key)) for key in ('reviewer', 'run_id', 'rationale'))
             and qa.get('review_revision') == manifest['source_revision']
             and qa.get('evidence') == [sha(encode(current))]
             and isinstance(qa.get('checks'), dict)
             and all(qa['checks'].get(key) is True for key in QA_CHECKS),
             'explicit record approval, reviewer provenance and all QA checks are required')
    reviewed = _time(qa.get('reviewed_at'))
    evidence_times = [_time(snapshot['captured_at']), _time(duplicate['checked_at']),
                      _time(duplicate['production']['reviewed_at'])]
    evidence_times.extend(_time(proof['snapshot']['retrieved_at']) for proof in duplicate['evidence'])
    _require(max(evidence_times) <= reviewed <= now,
             'record review must follow all saved draft and duplicate evidence')
    adjudication = row.get('duplicate_review')
    _require(isinstance(adjudication, dict) and adjudication.get('status') == 'reviewed'
             and adjudication.get('classification') == 'checked_no_match'
             and _text(adjudication.get('rationale'))
             and adjudication.get('evidence') == [current['duplicate_snapshot']],
             'explicit duplicate adjudication must bind the checked raw evidence')
    validate_program_review(manifest)
    for name in ('independent_review', 'risk_stratified_spotcheck'):
        _require(reviewed <= _time(manifest['program_review'][name]['reviewed_at']) <= now,
                 'program review must follow record approval')
    return row
