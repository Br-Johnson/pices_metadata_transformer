"""Pinned source-evidenced registration meaning; no authority or license grant.

One exact audited cohort only. Recheck paired raw constraints and per-source
abstract structure/text; separate restricted XML rehosting policy remains required.
"""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

MANIFEST_SHA256 = '2d18139656b78f96404561afcee7d2ae77022655873958c3fa98619a2717bdee'
REGISTRATION_WORDING = 'First time users must register to gain database access.'


def validate_dataset_access_interpretation(reference, source_id, source_sha256, root):
    """Return source-backed meaning only for the pinned exact source membership."""
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') != MANIFEST_SHA256):
        raise ValueError('Dataset access interpretation requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Dataset access interpretation manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Dataset access interpretation manifest differs from the reviewed profile')
    manifest = json.loads(raw)
    if not any(member['source_id'] == source_id and member['source_sha256'] == source_sha256
               for member in manifest['members']):
        raise ValueError('Source ID/hash is outside reviewed dataset access membership')
    for xpath, expected in (('./metainfo/metac', REGISTRATION_WORDING),
                            ('./idinfo/accconst', REGISTRATION_WORDING),
                            ('./metainfo/metuc', 'None'), ('./idinfo/useconst', 'None')):
        nodes = root.findall(xpath)
        if len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib or nodes[0].text != expected:
            raise ValueError('Dataset access interpretation requires exact plain paired constraints')
    if root.find('./metainfo/metsi') is not None or root.find('./metainfo/metextns') is not None:
        raise ValueError('Metadata security/extensions require separate adjudication')
    abstracts = root.findall('./idinfo/descript/abstract')
    context = manifest['source_contexts'][source_id]
    if (len(abstracts) != 1
            or hashlib.sha256(ET.tostring(abstracts[0], encoding='utf-8')).hexdigest() != context['abstract_xml_sha256']
            or re.sub(r'\s+', ' ', ''.join(abstracts[0].itertext())).strip() != context['abstract_text']):
        raise ValueError('Dataset access interpretation requires exact audited abstract context')
    return {'status': 'SOURCE_BACKED', 'meaning': 'underlying_dataset_acquisition',
            'source_id': source_id, 'source_sha256': source_sha256,
            'grants_rehosting': False, 'grants_new_license': False, 'publication_approved': False}


def validate_dataset_access_policy(policy, source_id, source_sha256, root, metadata):
    """Common all-QA-route gate: interpretation cannot replace rights authority."""
    from scripts.rehosting_authority import validate_authority, validate_restricted_metadata
    if policy.get('source_access_interpretation') is not None:
        raise ValueError('Conflicting access interpretations require separate adjudication')
    authority = policy.get('rehosting_authority')
    if authority is None:
        raise ValueError('Dataset access interpretation requires separate rehosting authority')
    validate_authority(authority, source_id, source_sha256)
    validate_restricted_metadata(metadata)
    if (policy.get('license') not in ('', None) or policy.get('rights_scope') != 'original_fgdc_xml'
            or policy.get('rights_source_xpath') != './metainfo/metuc'
            or policy.get('date_semantics') != 'source_metadata_date'):
        raise ValueError('Dataset access interpretation requires restricted unlicensed XML policy')
    return validate_dataset_access_interpretation(policy.get('dataset_access_interpretation'),
                                                  source_id, source_sha256, root)
