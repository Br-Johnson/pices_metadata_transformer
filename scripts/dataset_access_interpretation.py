"""Pinned source-evidenced data acquisition; no authority or license grant.

Finite audited profiles only. Recheck paired raw constraints and per-source
abstract structure/text; separate restricted XML rehosting policy remains required.
"""
import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

MANIFEST_SHA256 = '2d18139656b78f96404561afcee7d2ae77022655873958c3fa98619a2717bdee'
ACQUISITION_MANIFEST_SHA256 = '5c141ea3e0fae8e9b6673a2dc3f5aadba0d16c949767f80b5892ac589e6a0dbf'
EXTENDED_ACQUISITION_MANIFEST_SHA256 = '76a5ca8a8cdadbe0c1b0157d559068c98b16e18619a8561ff66a203a5008730a'
CNF_COPY_MEDIA_MANIFEST_SHA256 = '13e82e2375da3bf17cf352fff7a8cda43fa6d781a3e436ca7321c8428ac77abe'
RESOURCE_CONFIDENTIALITY_MANIFEST_SHA256 = '203c050735a9dc755712acde70c0447b91f2bd6131dde53dd8195a0f2923d9a2'
REGISTRATION_WORDING = 'First time users must register to gain database access.'


def _manifest(reference):
    """Load only reviewed immutable evidence; a refreshed hash cannot expand it."""
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') not in (MANIFEST_SHA256, ACQUISITION_MANIFEST_SHA256,
                                                      EXTENDED_ACQUISITION_MANIFEST_SHA256,
                                                      CNF_COPY_MEDIA_MANIFEST_SHA256,
                                                      RESOURCE_CONFIDENTIALITY_MANIFEST_SHA256)):
        raise ValueError('Dataset access interpretation requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Dataset access interpretation manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Dataset access interpretation manifest differs from the reviewed profile')
    return json.loads(raw)


def dataset_access_member_ids(reference):
    """Select immutable added members once; each selected source is revalidated."""
    try:
        manifest = _manifest(reference)
    except ValueError:
        return frozenset()  # Unsupported access remains held without interpretation.
    return frozenset(manifest.get('acquisition_contexts', {}))


def _elements(root, xpath):
    result = []
    for node in root.findall(xpath):
        node = copy.deepcopy(node)
        node.tail = None
        result.append(ET.tostring(node, encoding='unicode'))
    return result


def validate_dataset_access_interpretation(reference, source_id, source_sha256, root):
    """Return source-backed meaning only for the pinned exact source membership."""
    manifest = _manifest(reference)
    if not any(member['source_id'] == source_id and member['source_sha256'] == source_sha256
               for member in manifest['members']):
        raise ValueError('Source ID/hash is outside reviewed dataset access membership')
    acquisition = manifest.get('acquisition_contexts', {}).get(source_id)
    constraints = (acquisition['constraints'].items() if acquisition else
                   (('./metainfo/metac', REGISTRATION_WORDING),
                    ('./idinfo/accconst', REGISTRATION_WORDING),
                    ('./metainfo/metuc', 'None'), ('./idinfo/useconst', 'None')))
    for xpath, expected in constraints:
        nodes = root.findall(xpath)
        if len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib or nodes[0].text != expected:
            raise ValueError('Dataset access interpretation requires exact plain paired constraints')
    if root.find('./metainfo/metsi') is not None or root.find('./metainfo/metextns') is not None:
        raise ValueError('Metadata security/extensions require separate adjudication')
    if acquisition:
        if any(_elements(root, xpath) != expected
               for xpath, expected in acquisition['context_elements'].items()):
            raise ValueError('Dataset access interpretation requires exact audited source context')
    else:
        abstracts = root.findall('./idinfo/descript/abstract')
        context = manifest['source_contexts'][source_id]
        if (len(abstracts) != 1
                or hashlib.sha256(ET.tostring(abstracts[0], encoding='utf-8')).hexdigest() != context['abstract_xml_sha256']
                or re.sub(r'\s+', ' ', ''.join(abstracts[0].itertext())).strip() != context['abstract_text']):
            raise ValueError('Dataset access interpretation requires exact audited abstract context')
    return {'status': 'SOURCE_BACKED', 'meaning': acquisition['meaning'] if acquisition else 'underlying_dataset_acquisition',
            'source_id': source_id, 'source_sha256': source_sha256,
            'grants_rehosting': False, 'grants_new_license': False, 'publication_approved': False}


def validate_dataset_access_policy(policy, source_id, source_sha256, root, metadata):
    """Common all-QA-route gate: interpretation cannot replace rights authority."""
    from scripts.rehosting_authority import (
        validate_authority,
        validate_restricted_metadata,
    )
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
