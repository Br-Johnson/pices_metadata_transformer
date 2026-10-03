"""Pinned primary-citation interpretations, never a generic creator override.

Exact manifest bytes pin membership, evidence and full creator objects. Original
XML is checked again at QA; this grants no rights, aliases or release authority.
"""
import hashlib
import json
from pathlib import Path

MANIFEST_SHA256 = 'ee49147aec99d83cf54cb7fa4e59f7e50229967af0f08f5408e97144367e99e5'
DFO_MANIFEST_SHA256 = '6587234a935a8eb893f6890ad3ec01a330c7ff4e8c55dcaeb6c03800bf157b0d'


def validate_creator_interpretation(reference, source_id, source_sha256, root):
    """Return the pinned creator objects only for an exact audited source member."""
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') not in (MANIFEST_SHA256, DFO_MANIFEST_SHA256)):
        raise ValueError('Creator interpretation requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Creator interpretation manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Creator interpretation manifest differs from the reviewed profile')
    manifest = json.loads(raw)
    if not any(member['source_id'] == source_id and member['source_sha256'] == source_sha256
               for member in manifest['members']):
        raise ValueError('Source ID/hash is outside reviewed creator interpretation membership')
    nodes = root.findall(manifest['source_xpath'])
    if (len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib
            or nodes[0].text != manifest['raw_origin']):
        raise ValueError('Creator interpretation requires the exact plain primary citation origin')
    return manifest['creators']
