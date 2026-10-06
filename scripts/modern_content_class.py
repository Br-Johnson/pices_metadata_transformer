"""Offline modern metadata for 203 reviewed Exxon exact-content pairs.

Two source identities, filenames and policies remain distinct even when bytes
match. No singleton identity alias, transport, grant, execution or release is
provided. Every preparation rebuilds both source assessments and the v2 target.
"""

import hashlib
import html
from dataclasses import dataclass
from pathlib import Path

from scripts import content_class_targets as classes
from scripts import modern_singleton as singleton
from scripts.artifact_contract import fingerprint
from scripts.modern_singleton import encode, parse, pinned, require, sha
from scripts.production_mutations import PROTECTED
from scripts.rehosting_authority import validate_restricted_metadata

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / 'docs/readiness/2026-10-06/modern_exxon_pairs203.json'
MAPPING_SHA = '19686d6204a2d42e42dbef735313693e2a47553ec135f674c6e7c235a82ffa58'
POLICY = 'modern-xml-exxon-pairs203-v1'
REVIEW = MAPPING.parent / 'modern_exxon203_source_review.json'
REVIEW_SHA = '51c7266a2da2d270fc52ba70e712faa27a3ffd59cd2ba7b44ff4f7dbdd3bf48d'
SERVICE = MAPPING.parent / 'modern_exxon_creator_contract.json'
SERVICE_SHA = 'e320207b7feda481d7466eaa28e021d64ce24ce7e25f442e0f33e164fe9d88ab'


def source_policy(record_target_id):
    """Finite paired authority is separate from the 412-singleton admission set."""
    manifest = pinned(MAPPING, MAPPING_SHA)
    profile = pinned(singleton.EXXON_PROFILE, singleton.EXXON_SHA)
    projection = pinned(singleton.EXXON_MAPPING, singleton.EXXON_MAPPING_SHA)
    pinned(REVIEW, REVIEW_SHA)
    pinned(SERVICE, SERVICE_SHA)
    representation = classes.load_representation()
    members = {row['source_id']: row['source_sha256'] for row in profile['members']}
    expected = sorted([row for row in representation['classes'] if all(
        members.get(sid) == row['source_sha256'] for sid in row['source_ids'])],
        key=lambda row: row['record_target_id'])
    header = {
        'schema_version': 1, 'kind': 'modern-exxon-content-classes-v1', 'policy': POLICY,
        'profile': profile['profile'], 'creators': profile['creators'],
        'modern_creators': projection['modern_creators'],
        'source_review_sha256': REVIEW_SHA, 'service_contract_sha256': SERVICE_SHA,
        'source_plan_sha256': singleton.PLAN_SHA, 'creator_profile_sha256': singleton.EXXON_SHA,
        'creator_projection_sha256': singleton.EXXON_MAPPING_SHA,
        'representation_sha256': classes.REPRESENTATION_SHA256,
        'pair_map_sha256': classes.MAP_SHA256, 'pair_authority_sha256': classes.AUTHORITY_SHA256,
    }
    require(isinstance(manifest, dict) and set(manifest) == set(header) | {'targets'}
            and type(manifest['schema_version']) is int
            and all(manifest[key] == value for key, value in header.items())
            and projection['creators'] == profile['creators']
            and projection['creator_profile_sha256'] == singleton.EXXON_SHA
            and projection['service_contract_sha256'] == SERVICE_SHA
            and manifest['targets'] == expected and len(expected) == 203)
    selected = [row for row in expected if row['record_target_id'] == record_target_id]
    require(len(selected) == 1 and not set(selected[0]['source_ids']) & set(PROTECTED))
    planned = [row for row in pinned(singleton.PLAN, singleton.PLAN_SHA)['targets']
               if row['record_target_id'] == record_target_id]
    require(len(planned) == 1)
    row, plan = selected[0], planned[0]
    require(plan['source_ids'] == row['source_ids'] and plan['source_sha256'] == row['source_sha256']
            and plan['source_semantic_status'] == 'supported'
            and all(plan['identity_decision'][key] is None for key in
                    ('canonical_source_id', 'production_record_id', 'production_doi')))
    return manifest, row, plan


@dataclass(frozen=True)
class PreparedClass:
    record_target_id: str
    source_ids: tuple[str, str]
    body: bytes
    originals: tuple[tuple[str, bytes], tuple[str, bytes]]
    legacy_target: dict
    evidence: dict
    binding: str


def prepare(record_target_id, paths, *, reviewed_at):
    """Return a source-bound wire proposal; a supported source is not a grant.

    The caller supplies a fixed explicit assessment time and existing prepared
    inputs. No saved target, single preferred member or renamed copy is accepted.
    """
    manifest, row, plan = source_policy(record_target_id)
    target = classes.prepare_class_target(record_target_id, paths, reviewed_at=reviewed_at)
    require(target['source_semantic_status'] == 'supported'
            and all(item['source_semantic_status'] == 'supported'
                    for item in target['member_assessments'])
            and all(target[key] == value for key, value in row.items())
            and target['production_reconciliation_status'] == 'pending'
            and target['execution_status'] == 'class_execution_not_implemented'
            and all(target[key] is False for key in
                    ('upload_eligible', 'remote_verified', 'publication_approved')))
    originals, inputs = [], []
    contract = target['artifact_contract']
    require(contract['schema_version'] == 2 and len(contract['files']) == len(target['members']) == 2
            and contract['sha256'] == fingerprint({k: v for k, v in contract.items() if k != 'sha256'}))
    for sid, filename, member, file in zip(row['source_ids'], row['source_filenames'],
                                         target['members'], contract['files'], strict=True):
        source = Path(paths.original_fgdc_dir) / filename
        path = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw, payload_raw = source.read_bytes(), path.read_bytes()
        payload = parse(payload_raw)
        reference = payload.get('artifact_policy', {}).get('creator_interpretation', {})
        require(isinstance(reference, dict) and reference.get('manifest_sha256') == singleton.EXXON_SHA
                and payload['metadata']['creators'] == manifest['creators']
                and fingerprint(payload['metadata']) == target['common_source_metadata_sha256']
                and member['source_id'] == sid and member['source_filename'] == filename
                and member['source_sha256'] == sha(raw) == row['source_sha256']
                and member['payload_sha256'] == sha(payload_raw)
                and member['policy_sha256'] == fingerprint(payload['artifact_policy'])
                and raw == (ROOT / 'FGDC' / filename).read_bytes())
        descriptor = {'name': filename, 'size': len(raw), 'sha256': sha(raw),
                      'md5': hashlib.md5(raw, usedforsecurity=False).hexdigest(),
                      'role': 'descriptive_metadata'}
        require(file == descriptor and dict(descriptor, source_id=sid, path='FGDC/' + filename)
                in plan['expected_original_files'])
        originals.append((filename, raw))
        inputs.append({'source_id': sid, 'source_path': str(source.resolve()),
                       'prepared_input_path': str(path.resolve()), 'prepared_input_sha256': sha(payload_raw),
                       'member': member})
    require(len(plan['expected_original_files']) == 2 and originals[0][1] == originals[1][1])
    metadata = target['metadata']
    validate_restricted_metadata(metadata)
    require(metadata['creators'] == manifest['creators'])
    keywords = metadata.get('keywords', [])
    require(isinstance(keywords, list) and all(isinstance(k, str) and k.strip() for k in keywords))
    legacy = encode(metadata)
    preservation = '<p>' + singleton.PRESERVATION_LABEL + '</p><pre>' + html.escape(legacy.decode()) + '</pre>'
    wire = {'metadata': {
        'resource_type': {'id': 'other'}, 'title': metadata['title'],
        'creators': manifest['modern_creators'],
        'publication_date': metadata['publication_date'], 'publisher': 'Zenodo',
        'description': metadata['description'], 'subjects': [{'subject': k} for k in keywords],
        'additional_descriptions': [{'type': {'id': 'other'}, 'description': preservation}],
    }, 'access': {'record': 'public', 'files': 'restricted'}, 'files': {'enabled': True}}
    singleton.validate_payload(wire)
    body = encode(wire)
    evidence = {
        'schema_version': 1, 'kind': 'modern-content-class-preparation-v1', 'policy': POLICY,
        'record_target_id': record_target_id, 'source_ids': row['source_ids'],
        'source_sha256': row['source_sha256'], 'reviewed_at': reviewed_at,
        'mapping_manifest_sha256': MAPPING_SHA, 'source_review_sha256': REVIEW_SHA,
        'source_plan_sha256': singleton.PLAN_SHA, 'creator_profile_sha256': singleton.EXXON_SHA,
        'creator_projection_sha256': singleton.EXXON_MAPPING_SHA, 'service_contract_sha256': SERVICE_SHA,
        'representation_sha256': classes.REPRESENTATION_SHA256,
        'pair_map_sha256': classes.MAP_SHA256, 'pair_authority_sha256': classes.AUTHORITY_SHA256,
        'inputs': inputs, 'artifact_contract': contract, 'legacy_target_sha256': sha(encode(target)),
        'legacy_metadata_sha256': sha(legacy), 'wire_sha256': sha(body),
        'schema_sha256': {name: digest for name, (_, digest) in singleton.SCHEMA_FILES.items()},
        'runtime_sha256': singleton.runtime_binding(),
        'production_reconciliation_status': 'pending', 'execution_status': 'class_execution_not_implemented',
        'upload_eligible': False, 'remote_verified': False, 'publication_approved': False,
    }
    return PreparedClass(record_target_id, tuple(row['source_ids']), body, tuple(originals),
                         target, evidence, sha(encode(evidence)))


def validate_prepared(prepared, paths):
    """Self-rehashing an edited wire/target/inventory never establishes validity."""
    require(type(prepared) is PreparedClass)
    rebuilt = prepare(prepared.record_target_id, paths, reviewed_at=prepared.evidence['reviewed_at'])
    require(prepared == rebuilt)
    return rebuilt
