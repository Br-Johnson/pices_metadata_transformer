"""Evidence-based deposited-content classification and legacy keyword export.

File names/extensions and external links never establish data availability.
Reviewed role declarations describe an intended deposit, not a completed upload.
"""
from copy import deepcopy

STATUS_TAGS = {
    'metadata_only': 'pices-metadata-only',
    'data_included': 'pices-data-included',
    'mixed': 'pices-content-mixed',
    'unknown': 'pices-content-unknown',
}
CONTENT_NOTES = {
    'metadata_only': 'Deposited content: descriptive metadata only; underlying research data are not included.',
    'data_included': 'Deposited content: research data are included for the described scope.',
    'mixed': 'Deposited content: research data are included for part of the described scope; other content is descriptive metadata only.',
    'unknown': 'Deposited content: availability of underlying research data in this deposit has not been verified.',
}


def classify_content(declaration=None):
    """Classify only a complete, reviewed inventory of explicitly evidenced roles."""
    declaration = {} if declaration is None else deepcopy(declaration)
    if not isinstance(declaration, dict):
        raise ValueError('Content declaration must be an object')
    files = declaration.get('files', [])
    if not isinstance(files, list) or any(not isinstance(item, dict) for item in files):
        raise ValueError('Content files must be a list of role declarations')
    roles = []
    complete = (declaration.get('inventory_complete') is True and files
                and all(isinstance(declaration.get(key), str) and declaration[key].strip()
                        for key in ('reviewer', 'reviewed_at', 'rationale')))
    names = set()
    for item in files:
        role = item.get('role', 'unknown')
        if role not in ('descriptive_metadata', 'research_data', 'other', 'unknown'):
            raise ValueError('Unsupported deposited file role')
        if not all(isinstance(item.get(key), str) and item[key].strip() for key in ('name', 'evidence')):
            complete = False
        else:
            if item['name'] in names:
                raise ValueError('Duplicate file role declaration')
            names.add(item['name'])
        roles.append(role)
    status = 'unknown'
    if complete and all(role == 'descriptive_metadata' for role in roles):
        status = 'metadata_only'
    elif complete and 'research_data' in roles and all(role in ('research_data', 'descriptive_metadata') for role in roles):
        coverage = declaration.get('data_coverage')
        status = {'complete': 'data_included', 'partial': 'mixed'}.get(coverage, 'unknown')
    claimed = declaration.get('content_status')
    if claimed is not None and claimed != status:
        raise ValueError('Claimed content status is not supported by reviewed file roles')
    declaration['content_status'] = status
    return declaration


def export_content_metadata(metadata, classification):
    """Replace project status tags/notes idempotently; evidence stays internal."""
    status = classification['content_status']
    if status not in STATUS_TAGS:
        raise ValueError('Unsupported content status')
    result = deepcopy(metadata)
    keywords = result.get('keywords') or []
    if not isinstance(keywords, list) or any(not isinstance(keyword, str) for keyword in keywords):
        raise ValueError('Zenodo keywords must be a list of strings')
    tags = set(STATUS_TAGS.values())
    result['keywords'] = [keyword for keyword in keywords if keyword.strip().casefold() not in tags]
    result['keywords'].append(STATUS_TAGS[status])
    description = result.get('description') or ''
    if not isinstance(description, str):
        raise ValueError('Zenodo description must be text')
    for note in CONTENT_NOTES.values():
        description = description.replace('<p>' + note + '</p>', '').replace(note, '')
    result['description'] = description.strip() + '\n\n<p>' + CONTENT_NOTES[status] + '</p>'
    return result
