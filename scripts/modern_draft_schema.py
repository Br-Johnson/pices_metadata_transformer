"""Pinned local-only modern schemas for the exact fictional run02 payload.

Official record JSON schemas plus service-required and fixed-fixture checks.
No publisher inference for source records, remote schema retrieval or grants.
"""

import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from scripts import modern_synthetic_canary as modern

SCHEMAS = Path(__file__).resolve().parents[1] / 'contracts/schemas/zenodo-modern'
SCHEMA_FILES = {
    'record-v6.0.0.json': ('local://records/record-v6.0.0.json',
                          'bf029b1a74d851ff9c5474a9a528a0c4a0530026abf1698caf67f8efe6b95b88'),
    'record-definitions-v2.0.0.json': ('local://records/definitions-v2.0.0.json',
                                     '09060efec922d22bee3103e6b259e11a3fc0c1bdfa8eafc3df6335aba0199865'),
    'definitions-v1.0.0.json': ('local://definitions-v1.0.0.json',
                               'eeb99397c4c4712990222c969b8f8a22566eecf32818434f32b1982ed5eaab74'),
    'definitions-v2.0.0.json': ('local://definitions-v2.0.0.json',
                               '319e15bd15d15d7947c3298bee7c2db30f1b6c1de6e9500b869631b0828e13d6'),
}
PUBLISHER = 'Zenodo'
EMPTY_FILE_MESSAGES = (
    'Missing uploaded files. To disable files for this record please mark it as metadata-only.',
    'Missing uploaded files.',
)


def schema_binding():
    result = {}
    for name, (_, digest) in SCHEMA_FILES.items():
        raw = (SCHEMAS / name).read_bytes()
        modern.require(modern.sha(raw) == digest, 'Pinned modern schema changed; no repair')
        result[name] = digest
    return result


def validate_payload(value):
    """Validate every submitted field against official schemas, without network.

    Storage schemas intentionally permit partial metadata. The service overlay
    supplies all four MetadataSchema required fields, DataCite publisher, nested
    required names/types and the exact fictional description/subject/access/file
    constraints. The fixed writable shape excludes unrelated schema branches.
    """
    modern.require(isinstance(value, dict) and set(value) == {'metadata', 'access', 'files'})
    metadata = value['metadata']
    modern.require(isinstance(metadata, dict) and set(metadata) == {
        'resource_type', 'creators', 'title', 'publication_date', 'publisher', 'description', 'subjects'})
    schema_binding()
    registry = Registry()
    for name, (uri, _) in SCHEMA_FILES.items():
        contents = json.loads((SCHEMAS / name).read_bytes())
        # Base definition documents contain a named "$schema" definition, not
        # a dialect URI. Their pinned enclosing record explicitly uses draft7.
        registry = registry.with_resource(uri, Resource(contents, DRAFT7))
    validator = Draft7Validator({'$ref': 'local://records/record-v6.0.0.json'}, registry=registry)
    modern.require(validator.is_valid(value), 'Fictional payload failed pinned modern JSON schema')
    modern.require(metadata['resource_type'] == {'id': 'dataset'}
                   and isinstance(metadata['title'], str) and len(metadata['title']) >= 3
                   and metadata['publisher'] == PUBLISHER
                   and isinstance(metadata['description'], str) and len(metadata['description']) >= 3)
    creators = metadata['creators']
    modern.require(isinstance(creators, list) and len(creators) == 1
                   and creators == [{'person_or_org': {'name': 'Synthetic Canary Fixture', 'type': 'organizational'}}])
    modern.require(metadata['subjects'] == [{'subject': modern.NAMESPACE}]
                   and value['access'] == {'record': 'public', 'files': 'restricted'}
                   and value['files'] == {'enabled': True}
                   and type(value['files']['enabled']) is bool and value['files']['enabled'] is True)
    try:
        parsed = date.fromisoformat(metadata['publication_date'])
    except (ValueError, TypeError):
        raise modern.Held('Fictional publication date failed service schema') from None
    modern.require(parsed.isoformat() == metadata['publication_date'] == '2026-10-03')
    return True


def synthetic_payload(source):
    """Add only the documented host publisher to the sealed fictional input."""
    modern.require(any(source == modern.load(modern.PACKET / name)
                       for name in ('create.json', 'metadata-put.json')))
    value = modern.modern_wire_payload(deepcopy(source))
    modern.require('publisher' not in value['metadata'])
    value['metadata']['publisher'] = PUBLISHER
    validate_payload(value)
    return value


def expected_empty_file_warning(data):
    """Exact upstream warning only, after caller verifies the entire draft.

    The same field also reports permission/toggle failures. Names alone never
    allow an error. No provider message is copied into a receipt or state.
    """
    errors = data.get('errors')
    if 'errors' not in data or errors == []:
        return False
    modern.require(isinstance(errors, list) and len(errors) == 1
                   and isinstance(errors[0], dict) and set(errors[0]) == {'field', 'messages'}
                   and errors[0]['field'] == 'files.enabled'
                   and isinstance(errors[0]['messages'], list) and len(errors[0]['messages']) == 1
                   and errors[0]['messages'][0] in EMPTY_FILE_MESSAGES,
                   'Unapproved draft validation error; preserve attempt without followup')
    return True
