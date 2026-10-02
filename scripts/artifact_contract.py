"""Opt-in original XML artifact identity and exact remote file verification.

No inferred rights, dates, research data, remote operations or source edits.
Legacy records retain their empty-file contract unless explicitly reviewed.
"""
import hashlib
import json
from pathlib import Path

from scripts.content_classification import classify_content, export_content_metadata


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def prepare_artifact(payload, source_path):
    policy = payload.get('artifact_policy')
    if policy is None:
        return None
    if (not isinstance(policy, dict) or policy.get('schema_version') != 1
            or policy.get('object_kind') != 'original_fgdc_xml'
            or policy.get('resource_type') != 'other'
            or policy.get('date_semantics') not in ('metadata_artifact_publication', 'source_metadata_date')
            or any(not isinstance(policy.get(key), str) or not policy[key].strip()
                   for key in ('reviewer', 'reviewed_at', 'rationale', 'rights_evidence', 'date_evidence'))):
        raise ValueError('Reviewed original XML artifact policy and explicit rights/date evidence required')
    source = Path(source_path)
    raw = source.read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    if policy.get('source_sha256') != sha256:
        raise ValueError('Artifact policy source hash is stale')
    if payload['metadata'].get('upload_type') != policy['resource_type']:
        raise ValueError('Artifact resource type must be explicitly set to other')
    classification = classify_content(payload.get('content_classification'))
    files = classification.get('files', [])
    if (classification['content_status'] != 'metadata_only' or len(files) != 1
            or files[0]['name'] != source.name or files[0]['role'] != 'descriptive_metadata'):
        raise ValueError('Reviewed metadata-only inventory must identify exactly the original XML file')
    contract = {'schema_version': 1, 'object_kind': policy['object_kind'],
                'source_id': source.stem, 'policy_sha256': fingerprint(policy),
                'classification_sha256': fingerprint(classification),
                'files': [{'name': source.name, 'size': len(raw), 'sha256': sha256,
                           'md5': hashlib.md5(raw, usedforsecurity=False).hexdigest(),
                           'role': 'descriptive_metadata'}]}
    contract['sha256'] = fingerprint(contract)
    return contract


def artifact_metadata(metadata, payload, contract):
    if contract is None:
        return metadata
    metadata = export_content_metadata(metadata, classify_content(payload['content_classification']))
    note = ('Deposited object: original FGDC XML metadata artifact; underlying research data are not included. '
            'Artifact contract SHA-256: ' + contract['sha256'])
    if note not in metadata.get('notes', ''):
        metadata['notes'] = metadata.get('notes', '') + '\n\n' + note
    return metadata


def validate_files(remote_files, contract, allow_missing=False):
    """Require an exact inventory and checksum/size match; partial resume may miss files."""
    if not isinstance(remote_files, list):
        raise ValueError('Remote files inventory is missing')
    expected = {item['name']: item for item in contract['files']} if contract else {}
    seen = set()
    for item in remote_files:
        if not isinstance(item, dict):
            raise ValueError('Malformed remote file entry')
        name = item.get('filename', item.get('name', item.get('key')))
        size = item.get('filesize', item.get('size'))
        if name not in expected or name in seen:
            raise ValueError('Unexpected or duplicate remote file')
        seen.add(name)
        checksum = item.get('checksum')
        target = expected[name]
        if isinstance(checksum, str) and ':' not in checksum:
            checksum = 'md5:' + checksum
        if (type(size) is not int or size != target['size']
                or checksum not in ('md5:' + target['md5'], 'sha256:' + target['sha256'])):
            raise ValueError('Remote file checksum or size differs from reviewed artifact')
    missing = set(expected) - seen
    if missing and not allow_missing:
        raise ValueError('Expected original XML artifact is missing')
    return missing


def assert_artifact_binding(entry, contract):
    if entry.get('artifact_contract') != contract:
        raise ValueError('Artifact file or policy changed after draft creation')
