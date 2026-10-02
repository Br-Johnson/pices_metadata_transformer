"""Validate one source-bound USER_ATTESTED access interpretation offline.

The statement concerns dataset acquisition, not an XML license or publication.
Separate rehosting authority is required by every caller. Raw constraints stay intact.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

STATEMENT = 'It means contact someone (source) to obtain the underlying dataset'
ATTESTED_AT = '2026-10-02T18:26:45Z'
PROVENANCE = {
    'source_thread_id': '01a0f2a9-8da9-7252-b293-c326ee80b018',
    'turn_id': '01a0fdde-64cc-75df-a66a-191efacb0410',
    'user_item_id': '01a0fdde-66ca-7490-b287-0897fa441264',
    'message_id': 'Sentinel_65661711ca288191a37b82e7dd3f9fd2',
    'reply_to_message_id': 'Sentinel_4eb86edc245c8191bb90f333ca044223',
}


def _plain_single(root, xpath):
    nodes = root.findall(xpath)
    if len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib:
        raise ValueError('Access interpretation requires the audited plain source constraint fields')
    return re.sub(r'\s+', ' ', nodes[0].text or '').strip()


def validate_interpretation(reference, source_id, source_sha256, root, reviewed_at):
    """Recheck manifest bytes, original XML and post-attestation assessment time."""
    if (not isinstance(reference, dict) or not isinstance(reference.get('manifest_path'), str)
            or not reference['manifest_path'].strip()
            or not isinstance(reference.get('manifest_sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', reference['manifest_sha256'])):
        raise ValueError('Exact source access interpretation manifest path and SHA-256 required')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
        manifest = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError('Source access interpretation manifest is missing or malformed') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Source access interpretation manifest digest is stale')
    if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int
            or manifest['schema_version'] != 1
            or manifest.get('status') != 'USER_ATTESTED' or manifest.get('evidence_type') != 'USER_ATTESTED'
            or manifest.get('attested_by') != 'Brett' or manifest.get('attested_at') != ATTESTED_AT
            or manifest.get('statement') != STATEMENT or manifest.get('wording') != 'Contact Source.'
            or manifest.get('meaning') != 'underlying_dataset_acquisition'
            or manifest.get('scope') != 'historical_geonetwork_contact_source_access'
            or manifest.get('source_xpath') != './metainfo/metac'
            or manifest.get('paired_dataset_xpath') != './idinfo/accconst'
            or any(manifest.get(key) is not False for key in
                   ('grants_rehosting', 'grants_new_license', 'publication_approved', 'independently_verified_agreement'))
            or any(manifest.get(key) for key in ('license', 'new_license', 'verified_agreement'))
            or not isinstance(manifest.get('provenance'), dict)
            or any(manifest['provenance'].get(key) != value for key, value in PROVENANCE.items())):
        raise ValueError('Access interpretation must preserve the exact USER_ATTESTED dataset-acquisition statement')
    sources = manifest.get('sources')
    if (not isinstance(sources, dict) or not isinstance(source_id, str)
            or not isinstance(source_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', source_sha256)
            or sources.get(source_id) != source_sha256
            or any(not isinstance(key, str) or not isinstance(value, str)
                   or not re.fullmatch(r'[0-9a-f]{64}', value) for key, value in sources.items())):
        raise ValueError('Source is missing or changed outside the attested access interpretation scope')
    if (_plain_single(root, './metainfo/metac') != 'Contact Source.'
            or _plain_single(root, './idinfo/accconst') != 'Contact Source.'):
        raise ValueError('Access interpretation covers only the exact paired Contact Source. wording')
    # Matching use wording is an audited context guard, not a newly inferred use
    # license. Existing rehosting authority keeps XML restricted and unlicensed.
    metadata_use = _plain_single(root, './metainfo/metuc')
    if (metadata_use not in ('Contact Source.', 'Check with Source.', 'None')
            or _plain_single(root, './idinfo/useconst') != metadata_use
            or root.find('./metainfo/metsi') is not None
            or root.find('./metainfo/metextns') is not None):
        raise ValueError('Separate metadata use/security constraints require source-backed adjudication')
    try:
        stamp = datetime.fromisoformat(reviewed_at.replace('Z', '+00:00'))
        attested = datetime.fromisoformat(ATTESTED_AT.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp < attested or stamp > datetime.now(timezone.utc):
            raise ValueError
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('Access interpretation assessment must follow the attestation and use a current timezone-aware timestamp') from exc
    return {'status': 'USER_ATTESTED', 'attested_at': ATTESTED_AT, 'statement': STATEMENT,
            'source_id': source_id, 'source_sha256': source_sha256,
            'meaning': 'underlying_dataset_acquisition', 'grants_new_license': False,
            'publication_approved': False}
