"""Pinned primary-citation interpretations, never a generic creator override.

Exact manifest bytes pin membership, evidence and full creator objects. Original
XML is checked again at QA; this grants no rights, aliases or release authority.
"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET

MANIFEST_SHA256 = 'ee49147aec99d83cf54cb7fa4e59f7e50229967af0f08f5408e97144367e99e5'
DFO_MANIFEST_SHA256 = '6587234a935a8eb893f6890ad3ec01a330c7ff4e8c55dcaeb6c03800bf157b0d'
INSTITUTION_MANIFEST_SHA256 = '5099ec64f8b12df939f0c4a5816bd04cf44c2554be9768865c8db9aee18325aa'
INSTITUTION_PROGRAM_MANIFEST_SHA256 = '04db21a16750930112589d0cb9ab51df4638499831ac8b61760b179734d18323'
JOINT_COLLECTION_MANIFEST_SHA256 = '43ab11d7da41c6d1b6f8ff7a9582240192505818167725f81a353d4a1ae9e68d'
LITERAL_EXTENSION_MANIFEST_SHA256 = 'd2ba819c774a43f8cb5d90c28f2e4b3d41283747ddea9f282c0241468ab2c749'
SOURCE_CREDIT_MANIFEST_SHA256 = '7526abc74cdc62644fe682b17ebb23213b90ccb80f6f00c61ee149174ae7c257'


def source_element(node, outer=True):
    """Bind parsed content exactly; only the surrounding sibling tail is excluded."""
    return {'tag': node.tag, 'attributes': dict(node.attrib), 'text': node.text,
            'tail': None if outer else node.tail,
            'children': [source_element(child, False) for child in node]}


def validate_creator_interpretation(reference, source_id, source_sha256, root, include_context=False):
    """Return the pinned creator objects only for an exact audited source member."""
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') not in
            (MANIFEST_SHA256, DFO_MANIFEST_SHA256, INSTITUTION_MANIFEST_SHA256,
             INSTITUTION_PROGRAM_MANIFEST_SHA256, JOINT_COLLECTION_MANIFEST_SHA256,
             LITERAL_EXTENSION_MANIFEST_SHA256, SOURCE_CREDIT_MANIFEST_SHA256)):
        raise ValueError('Creator interpretation requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Creator interpretation manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Creator interpretation manifest differs from the reviewed profile')
    manifest = json.loads(raw)
    profiles = (manifest['cohorts'] if reference['manifest_sha256'] in
                (INSTITUTION_MANIFEST_SHA256, INSTITUTION_PROGRAM_MANIFEST_SHA256,
                 JOINT_COLLECTION_MANIFEST_SHA256, LITERAL_EXTENSION_MANIFEST_SHA256,
                 SOURCE_CREDIT_MANIFEST_SHA256)
                else [manifest])
    matches = [profile for profile in profiles
               if any(member['source_id'] == source_id and member['source_sha256'] == source_sha256
                      for member in profile['members'])]
    if len(matches) != 1:
        raise ValueError('Source ID/hash is outside reviewed creator interpretation membership')
    profile = matches[0]
    nodes = root.findall(manifest['source_xpath'])
    exact_credit_profile = reference['manifest_sha256'] == SOURCE_CREDIT_MANIFEST_SHA256
    if exact_credit_profile and profile.get('primary_origin_element') is not None:
        if len(nodes) != 1 or source_element(nodes[0]) != profile['primary_origin_element']:
            raise ValueError('Creator interpretation requires the exact reviewed primary origin element')
    elif (len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib
          or nodes[0].text != profile['raw_origin']):
        raise ValueError('Creator interpretation requires the exact plain primary citation origin')
    if exact_credit_profile:
        for evidence in profile.get('supplemental_source_elements', []):
            elements = root.findall(evidence['xpath'])
            if len(elements) != 1 or source_element(elements[0]) != evidence['element']:
                raise ValueError('Creator interpretation requires the exact supplemental source evidence')
    notes = []
    if exact_credit_profile and profile.get('preservation_required'):
        if profile.get('primary_origin_element') is not None:
            node = deepcopy(nodes[0])
            node.tail = None
            notes.append('Original primary citation origin XML (parsed representation): '
                         + ET.tostring(node, encoding='unicode'))
        else:
            notes.append('Original primary citation origin: ' + nodes[0].text)
        if profile.get('context_note'):
            notes.append(profile['context_note'])
    return ({'creators': profile['creators'], 'preservation_notes': notes}
            if include_context else profile['creators'])


def validate_creator_metadata(reference, source_id, source_sha256, root, metadata):
    """Require complete reviewed objects and the pinned source-role preservation."""
    result = validate_creator_interpretation(reference, source_id, source_sha256, root, True)
    if metadata.get('creators') != result['creators']:
        raise ValueError('Creator objects differ from reviewed primary citation interpretation')
    if any(note not in metadata.get('notes', '') for note in result['preservation_notes']):
        raise ValueError('Reviewed creator interpretation requires preserved source citation context')
