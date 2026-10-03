"""Eight reviewed display titles preserve complete source titles and metadata.

Finite source/hash/element and whole before/after bindings supply no generic
truncation rule, rights, creator inference, provider identity or release authority.
"""
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path

from scripts.citation_creator_interpretation import source_element
from scripts.source_link_interpretation import fingerprint

MANIFEST_SHA256 = 'fa08a25108bbd90a03fe0c107d5b4398403deabd76df2b839830fde05eb46780'
SOURCE_IDS = frozenset(f'FGDC-{i}' for i in (1917, 1922, 1923, 1924, 1925, 1930, 1933, 1935))


def validate_source_title_interpretation(reference, source_id, source_sha256, root):
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') != MANIFEST_SHA256):
        raise ValueError('Display title requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Display title interpretation manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Display title interpretation differs from the reviewed profile')
    manifest = json.loads(raw)
    members = [m for m in manifest['members'] if m['source_id'] == source_id and m['source_sha256'] == source_sha256]
    if len(members) != 1:
        raise ValueError('Source ID/hash is outside reviewed display title membership')
    nodes = root.findall(manifest['source_xpath'])
    if len(nodes) != 1 or source_element(nodes[0]) != members[0]['title_element']:
        raise ValueError('Display title requires the complete reviewed source title element')
    return members[0]


def apply_source_title_interpretation(member, metadata):
    if fingerprint(metadata) != member['metadata_before_sha256']:
        raise ValueError('Display title requires the complete reviewed before metadata')
    result = deepcopy(metadata)
    result['title'] = member['display_title']
    result['notes'] += '\n\n' + member['preservation_note']
    if fingerprint(result) != member['metadata_after_sha256']:
        raise ValueError('Display title differs from the complete reviewed after metadata')
    return result


def validate_source_title_policy(policy, source_id, source_sha256, root, metadata):
    reference = policy.get('source_title_interpretation')
    if reference is None:
        if source_id in SOURCE_IDS:
            nodes = root.findall('./idinfo/citation/citeinfo/title')
            if len(nodes) != 1:
                raise ValueError('Reviewed display title source element is missing')
            # Withdrawal cannot retain a selected title under human approval.
            title = re.sub(r'\s+', ' ', ''.join(nodes[0].itertext())).strip()
            if metadata.get('title') not in (title, title + ' - FGDC XML metadata artifact'):
                raise ValueError('Selected source display title requires reviewed evidence')
        return None
    member = validate_source_title_interpretation(reference, source_id, source_sha256, root)
    if fingerprint(metadata) != member['metadata_after_sha256']:
        raise ValueError('Display title metadata differs from complete reviewed preservation')
    return member['display_title']
