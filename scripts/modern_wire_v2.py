"""Second wire mapping for the bulk route (ADR 0014): FGDC content as structured Zenodo fields.

Purpose: build the v2 Zenodo record for a reviewed source from its reviewed v1 wire and the
original FGDC XML, following Brett's 2026-10-20 decisions: public XML file without a license,
the FGDC content in real fields instead of a JSON block, the citation publication date (else
the metadata date), Dataset or Report from a reviewed classification, no title suffix, no
`pices-metadata-only` keyword, Zenodo as publisher.

Invariants: the reviewed v1 fields (creators, title text, description, keywords) are carried
over, never re-derived; every new field comes from the original XML by a fixed rule; nothing
is guessed: a value that does not parse stays as labelled text in a description; contact
details other than names and organisations (emails, phones, addresses) are never put into the
new fields: contacts carry names and organisations only, and an e-mail address inside new free
text is replaced by a pointer to the attached XML, which keeps the original.

Assumptions: the original XML is the exact source the v1 wire was reviewed against; the
resource type comes from a reviewed classification; the provider stores these fields with the
sanitiser tolerances of `same_text` (HTML descriptions) and `same_plain` (plain text).
"""

import calendar
import html
import re
import xml.etree.ElementTree as ET

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from scripts.modern_draft_schema import SCHEMA_FILES, SCHEMAS
from scripts.modern_singleton import Held, pinned, require, same_plain, same_text

ARTIFACT_SUFFIX = ' - FGDC XML metadata artifact'
METADATA_ONLY_TAG = 'pices-metadata-only'
RESOURCE_TYPES = ('dataset', 'publication-report')
FIRST_YEAR, LAST_YEAR = 1800, 2026
MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): number for number, name in enumerate(calendar.month_abbr) if name})
URL = re.compile(r'https?://[^\s<>"]+')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
EMAIL_MARK = '[e-mail address: see the attached FGDC XML]'
MAX_CROSSING_SPAN = 200.0  # a date-line box wider than this has its west and east bounds swapped or mis-signed
REPLACEMENT_MARKS = ('￼', '�')  # object replacement and replacement characters from broken encodings
VOCABULARY_FIELDS = ('title',)  # the provider adds a display title to vocabulary entries


def text_of(node):
    return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


def texts(root, path):
    return [value for value in (text_of(node) for node in root.findall(path)) if value]


def leaf_texts(node):
    """Texts of the elements under `node` that have no children, in document order."""
    if node is None:
        return []
    return [value for value in (text_of(el) for el in node.iter() if el is not node and len(el) == 0) if value]


# ---------------------------------------------------------------- dates

def exact_date(value):
    """EDTF for an exact FGDC date (YYYY, YYYYMM, YYYYMMDD, 'Month YYYY'); None otherwise."""
    value = (value or '').strip()
    match = re.fullmatch(r'(\d{4})(\d{2})?(\d{2})?', value)
    if match and len(value) == 6 and not FIRST_YEAR <= int(value[:4]) <= LAST_YEAR:
        # MMYYYY ("122003", the Exxon Valdez records): unambiguous when YYYYMM is not a year.
        match = re.fullmatch(r'(\d{2})(\d{4})', value)
        year, month, day = int(match.group(2)), match.group(1), None
    elif match:
        year, month, day = int(match.group(1)), match.group(2), match.group(3)
    else:
        match = re.fullmatch(r'([A-Za-z]{3,9})\.?,? (\d{4})', value)
        if not match or match.group(1).lower() not in MONTHS:
            return None
        year, month, day = int(match.group(2)), '%02d' % MONTHS[match.group(1).lower()], None
    if not FIRST_YEAR <= year <= LAST_YEAR:
        return None
    if month is None:
        return '%04d' % year
    if not 1 <= int(month) <= 12:
        return None
    if day is None:
        return '%04d-%s' % (year, month)
    if not 1 <= int(day) <= calendar.monthrange(year, int(month))[1]:
        return None
    return '%04d-%s-%s' % (year, month, day)


def date_bounds(edtf):
    """The first and last day an EDTF date covers, for ordering checks."""
    parts = [int(p) for p in edtf.split('-')]
    year = parts[0]
    month_start = parts[1] if len(parts) > 1 else 1
    month_end = parts[1] if len(parts) > 1 else 12
    day_start = parts[2] if len(parts) > 2 else 1
    day_end = parts[2] if len(parts) > 2 else calendar.monthrange(year, month_end)[1]
    return (year, month_start, day_start), (year, month_end, day_end)


def publication_date(root):
    """The citation publication date when it is an exact date, else the metadata date."""
    cited = exact_date(text_of(root.find('./idinfo/citation/citeinfo/pubdate')))
    if cited is not None:
        return cited, 'citation'
    metadata = exact_date(text_of(root.find('./metainfo/metd')))
    if metadata is None:
        raise Held('neither the citation date nor the metadata date is an exact date')
    return metadata, 'metadata'


def time_period(root):
    """`dates` entries for the time period of the content, and the text of anything unparsed."""
    info = root.find('./idinfo/timeperd/timeinfo')
    current = text_of(root.find('./idinfo/timeperd/current'))
    description = 'Time period of content' + (' (' + current.lower() + ')' if current else '')
    unparsed = []
    if info is None:
        return [], unparsed
    begin, end = text_of(info.find('./rngdates/begdate')), text_of(info.find('./rngdates/enddate'))
    if begin or end:
        start, stop = exact_date(begin), exact_date(end)
        if start and stop and date_bounds(start)[0] <= date_bounds(stop)[1]:
            value = start if start == stop else start + '/' + stop
            return [{'date': value, 'type': {'id': 'collected'}, 'description': description}], unparsed
        if start and not end:  # 499 records: a start date only, which says nothing about the end
            return [{'date': start, 'type': {'id': 'collected'},
                     'description': description + '; begin date only, no end date in the FGDC record'}], unparsed
        unparsed.append('Time period: ' + ' to '.join(v for v in (begin, end) if v))
        return [], unparsed
    singles = texts(info, './/caldate')
    parsed = [exact_date(value) for value in singles]
    if singles and all(parsed):
        if len(parsed) == 1:
            return [{'date': parsed[0], 'type': {'id': 'collected'}, 'description': description}], unparsed
        first = min(parsed, key=lambda d: date_bounds(d)[0])
        last = max(parsed, key=lambda d: date_bounds(d)[1])
        return [{'date': first + '/' + last, 'type': {'id': 'collected'},
                 'description': description + '; ' + str(len(parsed)) + ' dates within this span'}], unparsed
    if singles:
        unparsed.append('Time period: ' + '; '.join(singles))
    return [], unparsed


# ---------------------------------------------------------------- locations

def bounding_box(root, as_text=False):
    """`locations` features for the FGDC bounding box, or the reason it could not be mapped.

    Zenodo accepts Point and Polygon geometries only ("Unsupported value: MultiPolygon", canary of
    2026-10-21), so a box across the date line becomes two Polygon features that meet at 180 degrees.
    """
    names = ('westbc', 'eastbc', 'northbc', 'southbc')
    raw = [text_of(root.find('./idinfo/spdom/bounding/' + name)) for name in names]
    if not any(raw):
        return [], None
    if as_text:  # a reviewed decision: this box contradicts the record's own text, so it is shown, not mapped
        return [], 'Bounding coordinates as given: W {}, E {}, N {}, S {}'.format(*raw)
    try:
        west, east, north, south = (float(value) for value in raw)
    except ValueError:
        return [], 'Bounding coordinates as given: W {}, E {}, N {}, S {}'.format(*raw)
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
        return [], 'Bounding coordinates as given: W {}, E {}, N {}, S {}'.format(*raw)
    if west == east == north == south == 0:  # a placeholder (92 records), not a point off West Africa
        return [], 'Bounding coordinates as given: W {}, E {}, N {}, S {}'.format(*raw)
    # 180 and -180 are one meridian: a box's west edge there is -180 and its east edge 180, so W 180 / E -166
    # is the box from -180 to -166 and W 180 / E -180 (or W -180 / E -180) the whole globe, not slivers.
    west = -180.0 if west == 180 else west
    east = 180.0 if east == -180 else east
    if west > east and east + 360 - west > MAX_CROSSING_SPAN:
        # Read as a date-line crossing this would be a near-global map; the values themselves stay as text.
        return [], 'Bounding coordinates as given: W {}, E {}, N {}, S {}'.format(*raw)
    if (west == east) != (north == south):
        # A box of zero width or zero height is a line, not a place: its midpoint is in no field of the XML.
        return [], 'Bounding coordinates as given: W {}, E {}, N {}, S {}'.format(*raw)
    description = 'Bounding coordinates: W {}, E {}, N {}, S {}'.format(*raw)
    if west == east:  # and north == south: a point
        return [{'geometry': {'type': 'Point', 'coordinates': [west, north]}, 'description': description}], None
    if west < east:
        return [{'geometry': box(west, east, north, south), 'description': description}], None
    return [{'geometry': box(west, 180.0, north, south), 'description': description + '; part west of the date line'},
            {'geometry': box(-180.0, east, north, south), 'description': description + '; part east of the date line'}
            ], None


def box(west, east, north, south):
    return {'type': 'Polygon', 'coordinates': [[[west, south], [east, south], [east, north], [west, north],
                                                [west, south]]]}


# ---------------------------------------------------------------- contributors

def person_or_org(name, organisation, primary):
    """The contributor an FGDC contact names, typed by the element that holds it.

    An organisation-primary contact (`cntorgp`) is always an organisation, commas included. A
    person-primary contact (`cntperp`) is a person when written 'Family, Given', or in natural
    order beside its organisation ('Rick Thomson' of DFO); without an organisation, a several-word
    value is an organisation in the person slot ('NOAA Central Library'), and a bare role word
    ('Librarian') stands for its organisation. All 82 such values in the collection follow this.
    """
    if primary == 'organisation':
        return {'type': 'organizational', 'name': name}, []
    affiliations = [{'name': organisation}] if organisation else []
    if ',' in name:
        family, given = (part.strip() for part in name.split(',', 1))
        if family and given:
            return {'type': 'personal', 'family_name': family, 'given_name': given}, affiliations
    tokens = name.split()
    if organisation and len(tokens) > 1:
        return {'type': 'personal', 'family_name': tokens[-1], 'given_name': ' '.join(tokens[:-1])}, affiliations
    if len(tokens) > 1:
        return {'type': 'organizational', 'name': name}, []
    if organisation:
        return {'type': 'organizational', 'name': organisation}, []
    return None, []


def contacts(root, path):
    """Names and organisations of FGDC contacts at `path`; no emails, phones or addresses."""
    found = []
    for info in root.findall(path):
        if info.find('./cntperp') is not None:
            name = text_of(info.find('./cntperp/cntper'))
            organisation = text_of(info.find('./cntperp/cntorg'))
            primary = 'person'
        else:
            name = text_of(info.find('./cntorgp/cntorg'))
            organisation = ''
            primary = 'organisation'
        if not name and organisation:
            name, organisation, primary = organisation, '', 'organisation'
        if any(mark in name + organisation for mark in REPLACEMENT_MARKS):
            continue  # a garbled name ("Br￼mmer") would be published mangled; leave it in the XML only
        if name:
            person, affiliations = person_or_org(name, organisation, primary)
            if person is not None:
                found.append((person, affiliations))
    return found


def contributors(root, creators):
    """Point of contact as contact person; a distinct distributor as distributor."""
    def key(person):
        return (person.get('name') or person.get('family_name', '') + ', ' + person.get('given_name', '')).casefold()
    entries, seen = [], set()
    for path, role in (('./idinfo/ptcontac/cntinfo', 'contactperson'), ('./distinfo/distrib/cntinfo', 'distributor')):
        for person, affiliations in contacts(root, path):
            if key(person) in seen:
                continue
            seen.add(key(person))
            entry = {'person_or_org': person, 'role': {'id': role}}
            if affiliations:
                entry['affiliations'] = affiliations
            entries.append(entry)
    return entries


# ---------------------------------------------------------------- descriptions, rights, links

def without_contacts(text):
    """Free text with e-mail addresses replaced by a pointer to the attached XML (Brett, 2026-10-20)."""
    return EMAIL.sub(EMAIL_MARK, text)


def paragraphs(items):
    return ''.join('<p>' + html.escape(without_contacts(text), quote=False) + '</p>' for text in items if text)


def labelled(label, value):
    return label + ': ' + value if value else ''


def additional_descriptions(root, source_ids, notes_extra, pubdate_origin):
    notes = [labelled('Purpose', text_of(root.find('./idinfo/descript/purpose'))),
             labelled('Supplemental information', text_of(root.find('./idinfo/descript/supplinf')))]
    quality = [labelled('Logical consistency', text_of(root.find('./dataqual/logic'))),
               labelled('Completeness', text_of(root.find('./dataqual/complete'))),
               labelled('Positional accuracy', text_of(root.find('./dataqual/posacc'))),
               labelled('Attribute accuracy', text_of(root.find('./dataqual/attracc')))]
    for step in root.findall('./dataqual/lineage/procstep'):
        description, date = text_of(step.find('./procdesc')), text_of(step.find('./procdate'))
        quality.append(labelled('Processing step' + (' (' + date + ')' if date else ''), description))
    progress = text_of(root.find('./idinfo/status/progress'))
    update = text_of(root.find('./idinfo/status/update'))
    standard = ' '.join(v for v in (text_of(root.find('./metainfo/metstdn')),
                                    '(' + text_of(root.find('./metainfo/metstdv')) + ')') if v not in ('', '()'))
    metadata_date = exact_date(text_of(root.find('./metainfo/metd')))
    identifiers = ' and '.join(source_ids)
    technical = [
        'Status: ' + '; '.join(v for v in (progress, labelled('maintenance and update frequency', update)) if v)
        if progress or update else '',
        labelled('Native data set environment', text_of(root.find('./idinfo/native'))),
        labelled('Resource description', text_of(root.find('./distinfo/resdesc'))),
        labelled('Ordering', '; '.join(leaf_texts(root.find('./distinfo/stdorder')))),
        labelled('Technical prerequisites', text_of(root.find('./distinfo/techpreq'))),
        *notes_extra,
        'Catalogue record: FGDC metadata ' + (standard + ' ' if standard else '') + 'dated '
        + (metadata_date or text_of(root.find('./metainfo/metd'))) + ', PICES GeoNetwork catalogue '
        + ('identifiers ' if len(source_ids) > 1 else 'identifier ') + identifiers
        + ('' if len(source_ids) == 1 else ' (identical records)') + '. Publication date taken from the '
        + ('citation.' if pubdate_origin == 'citation' else 'FGDC metadata date; the citation gives no exact date.'),
    ]
    result = []
    for kind, items in (('notes', notes), ('methods', quality), ('technical-info', technical)):
        body = paragraphs(items)
        if body:
            result.append({'type': {'id': kind}, 'description': body})
    return result


def rights(root):
    use = text_of(root.find('./idinfo/useconst'))
    access = text_of(root.find('./idinfo/accconst'))
    liability = text_of(root.find('./distinfo/distliab'))
    text = without_contacts('\n'.join(v for v in (labelled('Use constraints', use),
                                                  labelled('Access constraints', access),
                                                  labelled('Distribution liability', liability)) if v))
    if not text:
        return []
    return [{'title': {'en': 'Use and access constraints (from the FGDC record; no license is granted)'},
             'description': {'en': text}}]


def links(root):
    """Online links of the citation as related identifiers; anything not a plain URL stays as text."""
    related, leftover = [], []
    for value in texts(root, './idinfo/citation/citeinfo/onlink'):
        if URL.fullmatch(value):
            item = {'identifier': value, 'scheme': 'url', 'relation_type': {'id': 'describes'}}
            if item not in related:
                related.append(item)
        else:
            leftover.append(labelled('Online link as given', value))
    return related, leftover


def references(root):
    return [{'reference': value} for value in texts(root, './idinfo/citation/citeinfo/othercit')]


# ---------------------------------------------------------------- the record

def strip_suffix(title):
    return title[:-len(ARTIFACT_SUFFIX)] if title.endswith(ARTIFACT_SUFFIX) else title


def build(v1_wire, xml, source_ids, resource_type, map_as_text=False):
    """The v2 record (metadata, access, files) for one reviewed source or pair."""
    require(resource_type in RESOURCE_TYPES and isinstance(source_ids, list) and source_ids)
    meta1 = v1_wire['metadata']
    root = ET.fromstring(xml)
    pubdate, pubdate_origin = publication_date(root)
    dates, unparsed = time_period(root)
    features, location_note = bounding_box(root, as_text=map_as_text)
    related, link_notes = links(root)
    notes_extra = unparsed + ([location_note] if location_note else []) + link_notes
    meta = {
        'resource_type': {'id': resource_type},
        'title': strip_suffix(meta1['title']),
        'creators': meta1['creators'],
        'publication_date': pubdate,
        'publisher': 'Zenodo',
        'description': meta1['description'],
        'subjects': [s for s in meta1['subjects'] if s['subject'] != METADATA_ONLY_TAG],
        'additional_descriptions': additional_descriptions(root, source_ids, notes_extra, pubdate_origin),
    }
    optional = {'dates': dates, 'contributors': contributors(root, meta1['creators']), 'rights': rights(root),
                'related_identifiers': related, 'references': references(root)}
    meta.update({key: value for key, value in optional.items() if value})
    if features:
        meta['locations'] = {'features': features}
    record = {'metadata': meta, 'access': {'record': 'public', 'files': 'public'}, 'files': {'enabled': True}}
    validate(record)
    return record


def validate(record):
    """The v2 record against the pinned InvenioRDM schema, plus the fields the service requires."""
    registry = Registry()
    for name, (uri, digest) in SCHEMA_FILES.items():
        registry = registry.with_resource(uri, Resource(pinned(SCHEMAS / name, digest), DRAFT7))
    require(Draft7Validator({'$ref': 'local://records/record-v6.0.0.json'}, registry=registry).is_valid(record))
    require(set(record) == {'metadata', 'access', 'files'} and record['files'] == {'enabled': True}
            and record['access'] == {'record': 'public', 'files': 'public'})
    meta = record['metadata']
    require(all(f['geometry']['type'] in ('Point', 'Polygon') for f in meta.get('locations', {}).get('features', [])))
    require(meta['resource_type']['id'] in RESOURCE_TYPES and meta['publisher'] == 'Zenodo' and meta['creators']
            and all(isinstance(meta[key], str) and meta[key].strip()
                    for key in ('title', 'description', 'publication_date')))


# ---------------------------------------------------------------- comparison with the stored record

def vocabulary(actual, wanted):
    require(isinstance(actual, dict) and actual.get('id') == wanted['id']
            and set(actual) <= {'id'} | set(VOCABULARY_FIELDS))


def same_person(actual, wanted):
    require(isinstance(actual, dict) and actual.get('type') == wanted['type']
            and all(same_plain(actual.get(k), v) for k, v in wanted.items() if k != 'type')
            and actual.get('identifiers') in (None, []))
    if wanted['type'] == 'personal':
        require(set(actual) <= {'name', 'type', 'family_name', 'given_name', 'identifiers'})
        if 'name' in actual:
            require(same_plain(actual['name'], wanted['family_name'] + ', ' + wanted['given_name']))
    else:
        require(set(actual) <= {'name', 'type', 'identifiers'})


def same_affiliations(actual, wanted):
    if not wanted:
        require(actual in (None, []))
        return
    require(isinstance(actual, list) and len(actual) == len(wanted))
    for value, expected in zip(actual, wanted, strict=True):
        require(isinstance(value, dict) and set(value) <= {'name', 'identifiers', 'id'}
                and same_plain(value.get('name'), expected['name']) and value.get('identifiers') in (None, []))


def compare(actual, expected):
    """The stored v2 metadata equals the wire, allowing only the provider's known rewrites."""
    require(isinstance(actual, dict))
    known = {'resource_type', 'title', 'creators', 'publication_date', 'publisher', 'description', 'subjects',
             'additional_descriptions', 'dates', 'contributors', 'rights', 'related_identifiers', 'references',
             'locations'}
    defaults = {'additional_titles', 'languages', 'funding', 'version', 'sizes', 'formats', 'identifiers'}
    require(set(actual) <= known | defaults and set(expected) <= known)
    require(all(actual[k] in (None, '', [], {}) for k in set(actual) - set(expected)))
    require(actual.get('publication_date') == expected['publication_date'])
    for key in ('title', 'publisher'):
        require(same_plain(actual.get(key), expected[key]))
    require(same_text(actual.get('description'), expected['description']))
    vocabulary(actual.get('resource_type'), expected['resource_type'])
    subjects = actual.get('subjects') or []
    require(len(subjects) == len(expected['subjects']))
    for value, wanted in zip(subjects, expected['subjects'], strict=True):
        require(isinstance(value, dict) and set(value) == set(wanted) and same_plain(value['subject'], wanted['subject']))
    for key in ('creators', 'contributors'):
        values, wanted_list = actual.get(key) or [], expected.get(key, [])
        require(isinstance(values, list) and len(values) == len(wanted_list))
        for value, wanted in zip(values, wanted_list, strict=True):
            require(isinstance(value, dict) and set(value) <= {'person_or_org', 'affiliations', 'role'})
            same_person(value.get('person_or_org'), wanted['person_or_org'])
            same_affiliations(value.get('affiliations'), wanted.get('affiliations', []))
            if 'role' in wanted:
                vocabulary(value.get('role'), wanted['role'])
            else:
                require(value.get('role') in (None, {}))
    descriptions = actual.get('additional_descriptions') or []
    require(len(descriptions) == len(expected['additional_descriptions']))
    for value, wanted in zip(descriptions, expected['additional_descriptions'], strict=True):
        require(isinstance(value, dict) and set(value) <= {'description', 'type', 'lang'}
                and value.get('lang') in (None, {}) and same_text(value.get('description'), wanted['description']))
        vocabulary(value.get('type'), wanted['type'])
    dates = actual.get('dates') or []
    require(len(dates) == len(expected.get('dates', [])))
    for value, wanted in zip(dates, expected.get('dates', []), strict=True):
        require(isinstance(value, dict) and value.get('date') == wanted['date']
                and same_plain(value.get('description', ''), wanted.get('description', '')))
        vocabulary(value.get('type'), wanted['type'])
    rights_values = actual.get('rights') or []
    require(len(rights_values) == len(expected.get('rights', [])))
    for value, wanted in zip(rights_values, expected.get('rights', []), strict=True):
        require(isinstance(value, dict) and 'id' not in value
                and same_plain((value.get('title') or {}).get('en'), wanted['title']['en'])
                and same_plain((value.get('description') or {}).get('en'), wanted['description']['en']))
    related = actual.get('related_identifiers') or []
    require(len(related) == len(expected.get('related_identifiers', [])))
    for value, wanted in zip(related, expected.get('related_identifiers', []), strict=True):
        require(isinstance(value, dict) and value.get('identifier') == wanted['identifier']
                and value.get('scheme') == wanted['scheme'] and value.get('resource_type') in (None, {}))
        vocabulary(value.get('relation_type'), wanted['relation_type'])
    refs = actual.get('references') or []
    require(len(refs) == len(expected.get('references', [])))
    for value, wanted in zip(refs, expected.get('references', []), strict=True):
        require(isinstance(value, dict) and set(value) <= {'reference', 'identifier', 'scheme'}
                and same_plain(value.get('reference'), wanted['reference']))
    if 'locations' in expected:
        features = (actual.get('locations') or {}).get('features')
        wanted_features = expected['locations']['features']
        require(isinstance(features, list) and len(features) == len(wanted_features))
        for value, wanted in zip(features, wanted_features, strict=True):
            require(isinstance(value, dict) and value.get('geometry') == wanted['geometry']
                    and same_plain(value.get('description', ''), wanted.get('description', ''))
                    and set(value) <= {'geometry', 'description', 'place', 'identifiers'})
    else:
        require(actual.get('locations') in (None, {}, {'features': []}))
