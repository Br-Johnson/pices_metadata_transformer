"""Exact source-bound user attestation of rehosting permission, not a license grant.

This preserves what Brett stated. It neither verifies an agreement nor supplies
permission to apply a new Creative Commons license or expose restricted files.
"""
import hashlib
import json
from pathlib import Path
import re

STATEMENT = ('I have permission and instruction to rehost this metadata which was '
             'originally published on a geonetwork catalogue that we lost access to.')
AUTHORITY_ACCESS_CONDITIONS = (
    'Descriptive metadata are publicly readable. Original XML files remain restricted '
    'while reuse rights are unresolved. Permission to rehost is USER_ATTESTED; '
    'no new license grant is asserted.')


def validate_authority(reference, source_id, source_sha256):
    """Validate a raw-file manifest digest and exact source membership offline."""
    if (not isinstance(reference, dict) or not isinstance(reference.get('manifest_path'), str)
            or not reference['manifest_path'].strip()
            or not isinstance(reference.get('manifest_sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', reference['manifest_sha256'])):
        raise ValueError('Exact rehosting authority manifest path and SHA-256 required')
    path = Path(reference['manifest_path'])
    try:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError('Rehosting authority manifest is missing or malformed') from exc
    if digest != reference['manifest_sha256']:
        raise ValueError('Rehosting authority manifest digest is stale')
    if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int
            or manifest['schema_version'] != 1 or manifest.get('scope') != 'historical_geonetwork_metadata'
            or manifest.get('attested_by') not in ('Brett', 'Brett Johnson')
            or manifest.get('attested_at') != '2026-10-02' or manifest.get('statement') != STATEMENT
            or manifest.get('grants_rehosting') is not True or manifest.get('grants_new_license') is not False
            or manifest.get('status', 'USER_ATTESTED') != 'USER_ATTESTED'
            or manifest.get('evidence_type', 'USER_ATTESTED') != 'USER_ATTESTED'
            or any(manifest.get(key) for key in ('license', 'new_license', 'verified_agreement',
                                               'independently_verified_agreement'))):
        raise ValueError('Authority must preserve the exact USER_ATTESTED rehosting-only statement')
    sources = manifest.get('sources')
    if (not isinstance(sources, dict) or not isinstance(source_id, str)
            or not isinstance(source_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', source_sha256)
            or sources.get(source_id) != source_sha256
            or any(not isinstance(key, str) or not isinstance(value, str)
                   or not re.fullmatch(r'[0-9a-f]{64}', value) for key, value in sources.items())):
        raise ValueError('Source is missing or changed outside the attested rehosting scope')
    return {'status': 'USER_ATTESTED', 'attested_by': manifest['attested_by'],
            'attested_at': manifest['attested_at'], 'statement': manifest['statement'],
            'scope': manifest['scope'], 'grants_rehosting': True, 'grants_new_license': False,
            'manifest_path': str(path.resolve()), 'manifest_sha256': digest,
            'source_id': source_id, 'source_sha256': source_sha256}


def validate_restricted_metadata(metadata):
    """The attestation cannot silently create open files or new license grants."""
    conditions = metadata.get('access_conditions')
    if (metadata.get('access_right') != 'restricted' or metadata.get('license') != ''
            or not isinstance(conditions, str) or conditions.strip() != AUTHORITY_ACCESS_CONDITIONS):
        raise ValueError('User-attested rehosting requires restricted XML, blank license and explicit unresolved-rights conditions')
