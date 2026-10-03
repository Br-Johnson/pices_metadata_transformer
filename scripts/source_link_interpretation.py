"""Pinned historical dataset links preserved without asserting XML artifact identity.

Exactly 21 source/hash and complete before/after metadata bindings are reviewed.
This profile grants no access, rights, alias, provider identity or release authority.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

MANIFEST_SHA256 = '53b8f4cf4b2c84755653328916d0abfb8439984bd31906e0359f7588e5bd6168'
SOURCE_IDS = frozenset(f'FGDC-{i}' for i in range(4186, 4207))
SOURCE_URL = 'http://near-goos.coi.gov.cn/'


def fingerprint(metadata):
    return hashlib.sha256(json.dumps(metadata, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def validate_source_link_interpretation(reference, source_id, source_sha256, root):
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') != MANIFEST_SHA256):
        raise ValueError('Source link interpretation requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Source link interpretation manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Source link interpretation differs from the reviewed profile')
    manifest = json.loads(raw)
    members = [m for m in manifest['members'] if m['source_id'] == source_id and m['source_sha256'] == source_sha256]
    if len(members) != 1:
        raise ValueError('Source ID/hash is outside reviewed source link membership')
    nodes = root.findall(manifest['source_xpath'])
    if (len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib or nodes[0].text != manifest['raw_onlink']
            or root.findall('./idinfo/crossref')):
        raise ValueError('Source link interpretation requires the exact plain primary online linkage')
    return {'member': members[0], 'preservation_note': manifest['preservation_note']}


def apply_source_link_interpretation(profile, metadata):
    """Copy the reviewed before object and verify the complete prescribed after object."""
    if fingerprint(metadata) != profile['member']['metadata_before_sha256']:
        raise ValueError('Source link correction requires the complete reviewed before metadata')
    result = deepcopy(metadata)
    result['related_identifiers'] = []
    result['notes'] += '\n\n' + profile['preservation_note']
    if fingerprint(result) != profile['member']['metadata_after_sha256']:
        raise ValueError('Source link correction differs from the complete reviewed after metadata')
    return result


def validate_source_link_policy(policy, source_id, source_sha256, root, metadata):
    reference = policy.get('source_link_interpretation')
    if reference is None:
        # Withdrawing evidence must not leave this exact bounded correction eligible.
        nodes = root.findall('./idinfo/citation/citeinfo/onlink')
        if (source_id in SOURCE_IDS and len(nodes) == 1 and nodes[0].text == SOURCE_URL
                and not metadata.get('related_identifiers')):
            raise ValueError('Historical source link preservation requires the reviewed interpretation')
        return
    profile = validate_source_link_interpretation(reference, source_id, source_sha256, root)
    if fingerprint(metadata) != profile['member']['metadata_after_sha256']:
        raise ValueError('Source link metadata differs from the complete reviewed preservation correction')
