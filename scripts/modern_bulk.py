"""Bulk draft and publication route for reviewed records (ADR 0013, ADR 0014).

Purpose: carry reviewed, validation-passing singletons from prepared inputs to
published records in the PICES community in batches, with one journal file per
record instead of the single-record chain's per-record grant documents; and edit
published v1 records in place to their reviewed v2 wire (same DOI, new revision).

Invariants:
- Every provider request is journaled as `uncertain` before dispatch, and every
  write kind (create, init, content, commit, review, submit) is spent at most
  once per record; nothing is retried automatically. A record whose last
  request has no recorded answer is held for `reconcile`, which only reads.
- A source is created at most once: an exclusive intent file precedes the
  create, and the modern-v1 journal, its intents, the legacy registries, the
  protected sources and a fresh owner inventory are all checked first.
- A member is drafted only when its batch review approves it and published only
  when a release names it; the review binds the source and wire SHA256 of
  every member, so a code change between stages strands nothing.
- A record is complete only after the published readback shows the exact wire
  metadata (with the provider tolerances of `same_text` and `same_plain`), the original file by
  size and MD5, the owner, DOI pids and the PICES community as its default.
- The token never reaches a file or output; every retained response is
  credential-screened first. Publication prompts for the token unless the operator passes the
  Keychain item, which Brett allowed for this route on 2026-10-20.

Assumptions: `modern_batch` manifests and the live preparation are the truth
for membership and twins; the owner inventory, this route's journal and the
modern-v1 journal are together the duplicate barrier for the owner's account;
external repositories are not consulted (AquaDocs linkage is deferred).
"""

import argparse
import base64
import gzip
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import modern_batch as batch
from scripts import modern_content_class as content_class
from scripts import modern_operator as operator
from scripts import modern_singleton_executor as draft
from scripts import modern_wire_v2 as wire_v2
from scripts.modern_draft_schema import expected_empty_file_warning
from scripts.modern_publication import pids as published_pids
from scripts.modern_publication import validate_request
from scripts.modern_response_evidence import diagnostic, normalize_response
from scripts.modern_singleton import (
    Held,
    compare_metadata,
    encode,
    parse,
    prepare,
    require,
    sha,
)
from scripts.path_config import OutputPaths
from scripts.production_mutations import EXCLUDED, PROTECTED
from scripts.upload_service import atomic_json, ledger_lock

BULK_DIR = batch.BULK_DIR
RECORD_KIND = batch.BULK_RECORD_KIND
SHEET_KIND = 'modern-bulk-sheet-v1'
REVIEW_KIND = 'modern-bulk-review-v1'
RELEASE_KIND = 'modern-bulk-release-v1'
RUN_KIND = 'modern-bulk-run-v1'
EXCLUSION_KIND = 'modern-bulk-exclusion-v1'
PICES_COMMUNITY = '92279449-f6e1-422d-8610-40802567c58b'
JSON_MEDIA = 'application/json'
WRITES = ('create', 'init', 'content', 'commit', 'review', 'submit', 'edit', 'update', 'publish')
LIMITS = dict.fromkeys(WRITES, 1) | {'get': 40}
EDIT_WRITES = ('edit', 'update', 'publish')  # the in-place update of a published record (ADR 0014)
PHASES = ('planned', 'creating', 'created', 'initialized', 'uploaded', 'draft-verified', 'adopted',
          'review-set', 'accepted', 'published', 'editing', 'edit-open', 'edit-saved', 'edit-published')
UPDATING = ('editing', 'edit-open', 'edit-saved', 'edit-published')
RESOURCE_TYPES_PATH = Path(__file__).resolve().parents[1] / 'docs/readiness/2026-10-23/resource_types_r6.json'
RESOURCE_TYPES_SHA = '950248823b091299be33277679c5e4080a7d3eecfdea9ccf9f3c7565e93c71d8'  # adds the 37 held sources Brett cleared on 2026-10-23; supersedes r5 ef0e8f2b...
SOURCE_REPAIRS_PATH = Path(__file__).resolve().parents[1] / 'docs/readiness/2026-10-22/source_repairs_r2.json'
SOURCE_REPAIRS_SHA = 'eb2028e5e4fd949d6cc8541d7a349adc99ba8b889cf73392203d565828439719'  # adds U+0097 -> U+2014 for 885, 2674, 3808; supersedes 5d8f46aa...
MAP_AS_TEXT_PATH = Path(__file__).resolve().parents[1] / 'docs/readiness/2026-10-24/map_as_text_r2.json'
MAP_AS_TEXT_SHA = '4b36a39726da8170cb723b48dcc7b03ac54efedb0b49d4ba39ac7eb6ae3fcb6f'
EXCLUSION_LIFT_KIND = 'modern-bulk-exclusion-lift-v1'
LEGACY_RELEASE_KIND = 'modern-bulk-legacy-release-v1'
LEGACY_RELEASE_FRESHNESS = timedelta(hours=24)
DRAFTED = ('draft-verified', 'adopted', 'review-set', 'accepted', 'published')
PACE_SECONDS = 0.8
INVENTORY_REFRESH = timedelta(minutes=45)
INVENTORY_MAX_BYTES = 64 * 1024 * 1024
MAX_CONSECUTIVE_HOLDS = 3
MAX_ALLOWANCE = 1  # a write whose effect reconcile did not observe may be sent once more, once
CREATE_SETTLE = timedelta(minutes=2)
ABSENCE_GAP = timedelta(minutes=10)  # a lost create counts as absent only after two inventories this far apart
SAMPLE_FRACTION = 0.10
SAMPLE_MIN = 20
STOP_STATUSES = {401, 403, 408, 425, 429} | set(range(500, 600))
CONTROL = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')
ENCODING = re.compile('[\ufffd\uff61-\uff9f]|\u00c3[\u0080-\u00bf]|\u00e2\u20ac')
PLACEHOLDER = re.compile(r'^(unknown|n/?a|none|null|tbd|staff|anonymous)$', re.IGNORECASE)


class RecordHold(Held):
    """Park this record with its reason; the run continues."""


class StopRun(Held):
    """Stop the run after the current record's journal is saved."""


def record_stop(reason):
    """A stop caused by one record's own request; that record is held as well."""
    stop = StopRun(reason)
    stop.on_record = True
    return stop


def utc_now():
    return datetime.now(timezone.utc)


def stamp(value):
    return value.strftime('%Y%m%dt%H%M%Sz')


def check(condition, reason, kind=RecordHold):
    if not condition:
        raise kind(reason)


# ---------------------------------------------------------------- locations

def bulk_root(paths):
    return draft.state_root(paths) / BULK_DIR


def record_path(paths, source_id):
    require(re.fullmatch(batch.SOURCE_ID, source_id) is not None)
    return bulk_root(paths) / 'records' / (source_id + '.json')


def intent_path(paths, source_id):
    require(re.fullmatch(batch.SOURCE_ID, source_id) is not None)
    return bulk_root(paths) / 'intents' / (source_id + '.create.json')


def evidence_dir(paths, source_id):
    require(re.fullmatch(batch.SOURCE_ID, source_id) is not None)
    return bulk_root(paths) / 'evidence' / source_id


def json_input(paths, source_id):
    return batch.prepared_input(paths, source_id)


def write_exclusive(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    draft.permanent_intent(path, document)
    return path


def load_record(paths, source_id):
    path = record_path(paths, source_id)
    if not path.exists():
        return None
    document, _ = draft.read_document(path)
    counts = document.get('counts') if isinstance(document, dict) else None
    if isinstance(counts, dict) and set(LIMITS) - set(counts) == set(EDIT_WRITES) and set(counts) < set(LIMITS):
        # Forward migration: a record journaled before the update stage existed spent none of its writes.
        document['counts'] = {**counts, **dict.fromkeys(EDIT_WRITES, 0)}
    require(isinstance(document, dict) and document.get('kind') == RECORD_KIND
            and document.get('schema_version') == 1 and document.get('source_id') == source_id
            and document.get('phase') in PHASES and isinstance(document.get('requests'), list)
            and isinstance(document.get('counts'), dict) and set(document['counts']) == set(LIMITS)
            and document.get('wire_version', 1) in (1, 2)
            and isinstance(document.get('allowances'), dict) and set(document['allowances']) <= set(WRITES)
            and all(type(v) is int and 0 < v <= MAX_ALLOWANCE * (len(files_of(document)) if k in ('content', 'commit')
                                                                  else 1)
                    for k, v in document['allowances'].items()))
    for kind in LIMITS:
        limit = write_limit(document, kind)
        require(type(document['counts'][kind]) is int and 0 <= document['counts'][kind] <= limit
                and document['counts'][kind] == sum(r.get('kind') == kind for r in document['requests']))
    return document


def files_of(entry):
    """The original files of a record, sheet row or member: one for a singleton, two for a pair."""
    return entry['files'] if 'files' in entry else [entry['file']]


def source_ids_of(entry):
    target = entry.get('target')
    return list(target['source_ids']) if target else [entry['source_id']]


def write_limit(record, kind):
    """Per-record dispatch limit: one of each write, one upload and commit per file, plus allowances."""
    per_file = len(files_of(record)) if kind in ('content', 'commit') else 1
    return LIMITS[kind] * per_file + record.get('allowances', {}).get(kind, 0)


def save_record(paths, record):
    path = record_path(paths, record['source_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(path, record)


def new_record(source_id, member, origin):
    return {'schema_version': 1, 'kind': RECORD_KIND, 'source_id': source_id, 'origin': origin,
            'source_sha256': member['source_sha256'], 'wire_sha256': member['wire_sha256'],
            **({'files': member['files'], 'target': member['target']} if member.get('target')
               else {'file': member['file']}),
            'review_sha256': member['review_sha256'], 'batch_id': member['batch_id'],
            'wire_version': member.get('wire_version', 1),
            'identity': None, 'candidate_id': None, 'phase': 'planned', 'hold': None,
            'counts': dict.fromkeys(LIMITS, 0), 'allowances': {}, 'requests': [], 'draft_revision': None,
            'request_id': None, 'request_status': None, 'release_sha256': None, 'pids': None,
            'inventory_allowed': [], 'absence': [], 'uploaded': [], 'resend': {}, 'history': []}


def own_identities(paths):
    """Every record id this account's own chains claim: bulk records and modern-v1 rows."""
    return operator.known_records(paths) - {str(value[0]) for value in PROTECTED.values()} - {str(i) for i in EXCLUDED}


# ---------------------------------------------------------------- members

def file_facts(prepared):
    return {'key': prepared.source_id + '.xml', 'size': len(prepared.xml), 'sha256': sha(prepared.xml),
            'md5': hashlib.md5(prepared.xml, usedforsecurity=False).hexdigest()}


def member_now(paths, source_id):
    """The live preparation of one source: wire, original and their hashes."""
    prepared = prepare(str(json_input(paths, source_id)), paths)
    require(prepared.source_id == source_id)
    return prepared


class PairPrepared:
    """A reviewed pair (two byte-identical originals) in the shape the stages use."""

    def __init__(self, prepared):
        names = [name for name, _ in prepared.originals]
        contents = [raw for _, raw in prepared.originals]
        require(len(names) == 2 and contents[0] == contents[1]
                and names == [sid + '.xml' for sid in prepared.source_ids])
        self.source_id = prepared.source_ids[0]
        self.source_ids = list(prepared.source_ids)
        self.record_target_id = prepared.record_target_id
        self.body, self.xml, self.evidence = prepared.body, contents[0], prepared.evidence
        self.contents = dict(prepared.originals)


def pair_now(paths, target):
    """The live preparation of a reviewed pair under whichever pinned pair policy admits it (ADR 0010, 0015)."""
    prepared = content_class.prepare(target['record_target_id'], paths, reviewed_at=target['reviewed_at'])
    pair = PairPrepared(prepared)
    require('source_ids' not in target or pair.source_ids == list(target['source_ids']))
    return pair


def resource_types():
    """The reviewed Dataset or Report classification, by first source id (pinned)."""
    raw = RESOURCE_TYPES_PATH.read_bytes()
    require(RESOURCE_TYPES_SHA is not None and sha(raw) == RESOURCE_TYPES_SHA)
    document = parse(raw)
    require(document.get('kind') == 'pices-resource-types-v1' and isinstance(document.get('types'), dict))
    return document['types']


def source_repairs():
    """Reviewed exact text repairs by source id (pinned): source text the provider sanitiser would damage."""
    raw = SOURCE_REPAIRS_PATH.read_bytes()
    require(sha(raw) == SOURCE_REPAIRS_SHA)
    document = parse(raw)
    require(document.get('kind') == 'pices-source-repairs-v1' and isinstance(document.get('repairs'), dict))
    return document['repairs']


def repaired(metadata, repairs):
    """The metadata with each repair applied to every string value; a repair that applies nowhere holds."""
    require(isinstance(repairs, list) and all(isinstance(r.get('from'), str) and r['from'] and isinstance(r.get('to'), str)
                                              for r in repairs))
    used = [0] * len(repairs)

    def walk(value):
        if isinstance(value, str):
            for index, repair in enumerate(repairs):
                used[index] += value.count(repair['from'])
                value = value.replace(repair['from'], repair['to'])
            return value
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        return value
    result = walk(metadata)
    require(all(used))
    return result
def resource_type_of(source_id):
    """The pinned type of a source or of a pair's first source; a source without one holds its record."""
    types = resource_types()
    check(source_id in types, 'no reviewed resource type for ' + source_id + ' in the pinned manifest')
    return types[source_id]


def map_as_text():
    """Sources whose box contradicts their own text: published with the box as text, no map (pinned)."""
    raw = MAP_AS_TEXT_PATH.read_bytes()
    require(sha(raw) == MAP_AS_TEXT_SHA)
    document = parse(raw)
    require(document.get('kind') == 'pices-map-as-text-v1' and isinstance(document.get('sources'), dict))
    return document['sources']


class WireV2:
    """A prepared source or pair with its v2 wire (ADR 0014); originals and evidence unchanged."""
    wire_version = 2

    def __init__(self, base, resource_type):
        self.source_id = base.source_id
        self.source_ids = list(getattr(base, 'source_ids', [base.source_id]))
        self.record_target_id = getattr(base, 'record_target_id', None)
        self.xml = base.xml
        self.contents = contents_of(base)
        self.v1_body = base.body
        # A held37 member (ADR 0016) carries its reviewed metadata date correction and public notes in its
        # preparation evidence; every other preparation carries neither.
        record = wire_v2.build(parse(base.body), base.xml, self.source_ids, resource_type,
                               map_as_text=base.source_id in map_as_text(),
                               date_correction=base.evidence.get('metadata_date_correction'),
                               notes=base.evidence.get('public_notes') or [])
        repairs = source_repairs().get(base.source_id, [])
        if repairs:  # reviewed text repairs (source_repairs.json); the original XML is unchanged
            record = {**record, 'metadata': repaired(record['metadata'], repairs)}
            wire_v2.validate(record)
        self.body = encode(record)
        self.evidence = {**base.evidence, 'wire_version': 2, 'v1_wire_sha256': sha(base.body),
                         'resource_type': resource_type, 'source_repairs': len(repairs)}


def prepare_entry(paths, entry, wire_version=None):
    """Live preparation of a member or record: a singleton source or a pair target, at its wire version."""
    target = entry.get('target')
    base = pair_now(paths, target) if target else member_now(paths, entry['source_id'])
    if (wire_version or entry.get('wire_version', 1)) == 2:
        return WireV2(base, resource_type_of(base.source_id))
    return base


def contents_of(prepared):
    """File key to original bytes."""
    return getattr(prepared, 'contents', None) or {prepared.source_id + '.xml': prepared.xml}


def files_facts(prepared):
    return [{'key': key, 'size': len(raw), 'sha256': sha(raw),
             'md5': hashlib.md5(raw, usedforsecurity=False).hexdigest()} for key, raw in contents_of(prepared).items()]


def text_of(node):
    return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


def xml_fields(xml):
    root = ET.fromstring(xml)
    single = text_of(root.find('./idinfo/timeperd/timeinfo/sngdate/caldate'))
    begin = text_of(root.find('./idinfo/timeperd/timeinfo/rngdates/begdate'))
    end = text_of(root.find('./idinfo/timeperd/timeinfo/rngdates/enddate'))
    return {'title': text_of(root.find('./idinfo/citation/citeinfo/title')),
            'origins': [text_of(node) for node in root.findall('./idinfo/citation/citeinfo/origin')],
            'pubdate': text_of(root.find('./idinfo/citation/citeinfo/pubdate')),
            'abstract': text_of(root.find('./idinfo/descript/abstract')),
            'time_period': single or ' to '.join(v for v in (begin, end) if v),
            'metadata_date': text_of(root.find('./metainfo/metd')),
            'keywords': len(root.findall('.//keywords/theme/themekey')) + len(root.findall('.//keywords/place/placekey'))}


def creator_name(creator):
    person = creator.get('person_or_org', {})
    if person.get('type') == 'personal':
        return person.get('family_name', '') + ', ' + person.get('given_name', '')
    return person.get('name', '')


def flags_for(source, wire, wire_version=1):
    """Automatic signals for the reviewer; a flag is a reason to look, not a verdict."""
    meta = wire['metadata']
    flags = []
    core = batch.title_key(meta['title'])
    if core != ' '.join(source['title'].casefold().split()):
        flags.append('title_differs_from_source')
    # v1 describes the XML artifact, so its publication date is the metadata date (metd); v2 takes the
    # citation date when it is exact (ADR 0014), which v2_flags checks instead.
    metadata_date = re.sub(r'\D', '', source.get('metadata_date', ''))
    wire_date = meta['publication_date'].replace('-', '')
    if wire_version == 1 and (not metadata_date or metadata_date[:len(wire_date)] != wire_date):
        flags.append('publication_date_differs_from_metadata_date')
    description = meta['description']
    if len(description) < 50:
        flags.append('short_description')
    abstract_head = ' '.join(source['abstract'].split())[:40].casefold()
    if abstract_head and abstract_head not in ' '.join(description.split()).casefold():
        flags.append('description_omits_abstract_opening')
    names = [creator_name(c) for c in meta['creators']]
    if any(len(n.strip(' ,')) < 3 or PLACEHOLDER.match(n.strip(' ,')) or re.search(r'\d', n) for n in names):
        flags.append('suspicious_creator')
    texts = [meta['title'], description, *names, *(s['subject'] for s in meta['subjects'])]
    if any(CONTROL.search(t) for t in texts):
        flags.append('control_character')
    if any(ENCODING.search(t) for t in texts):
        flags.append('encoding_artifact')
    if len(meta['title']) > 300:
        flags.append('long_title')
    if not meta['subjects']:
        flags.append('no_subjects')
    return flags


def v2_summary(prepared):
    """What the reviewer checks in a v2 wire, beside the source fields."""
    meta = parse(prepared.body)['metadata']
    features = (meta.get('locations') or {}).get('features', [])
    polygons = [f['geometry']['coordinates'] for f in features if f['geometry']['type'] == 'Polygon']
    span = sum(max(x for x, _ in polygon[0]) - min(x for x, _ in polygon[0]) for polygon in polygons)
    texts = [d['description'] for d in meta['additional_descriptions']] + [
        r['description']['en'] for r in meta.get('rights', [])]
    return {'resource_type': meta['resource_type']['id'], 'publication_date': meta['publication_date'],
            'dates': [d['date'] for d in meta.get('dates', [])],
            'location': features[0]['description'] if features else '',
            'geometry': '+'.join(f['geometry']['type'] for f in features) or None,
            'longitude_span': round(span, 2),
            'contact_details_removed': any(wire_v2.EMAIL_MARK in t for t in texts),
            'contributors': [creator_name(c) + ' (' + c['role']['id'] + ', ' + c['person_or_org']['type'] + ')'
                             for c in meta.get('contributors', [])],
            'rights': (meta.get('rights') or [{}])[0].get('description', {}).get('en', '')[:300],
            'notes': [d['type']['id'] + ': ' + re.sub('<[^>]+>', ' ', d['description'])[:400]
                      for d in meta['additional_descriptions']],
            'related_identifiers': [r['identifier'] for r in meta.get('related_identifiers', [])],
            'references': [r['reference'][:200] for r in meta.get('references', [])]}


def v2_flags(source, summary):
    """Signals for the new v2 fields; the v1 signals of the same row still apply."""
    flags = []
    if not summary['dates'] and source.get('time_period'):
        flags.append('time_period_not_mapped')
    if not summary['geometry']:
        flags.append('no_map')
    if summary['resource_type'] == 'publication-report' and summary['dates']:
        flags.append('report_with_collection_dates')
    if any(text.startswith('technical-info') and 'as given' in text for text in summary['notes']):
        flags.append('value_kept_as_text')
    if summary['longitude_span'] > 180 and summary['longitude_span'] < 360:
        flags.append('wide_box')
    if summary['contact_details_removed']:
        flags.append('contact_details_removed')
    cited = re.sub(r'\D', '', source.get('pubdate', ''))
    if summary['publication_date'].replace('-', '') not in (cited, re.sub(r'\D', '', source.get('metadata_date', ''))):
        flags.append('publication_date_reformatted')
    return flags


def sheet_row(paths, source_id, wire_version=1):
    prepared = prepare_entry(paths, {'source_id': source_id}, wire_version)
    wire = parse(prepared.body)
    meta = wire['metadata']
    source = xml_fields(prepared.xml)
    return {'source_id': source_id, 'policy': prepared.evidence['policy'],
            'source_sha256': sha(prepared.xml), 'wire_sha256': sha(prepared.body),
            'file': file_facts(prepared),
            'source': {**source, 'abstract': source['abstract'][:500]},
            'wire': {'title': meta['title'], 'creators': [creator_name(c) for c in meta['creators']],
                     'publication_date': meta['publication_date'], 'description': meta['description'][:500],
                     'description_length': len(meta['description']), 'subjects': len(meta['subjects'])},
            'flags': flags_for(source, wire, wire_version)} | v2_row_extra(prepared, source, wire_version)


def v2_row_extra(prepared, source, wire_version):
    if wire_version != 2:
        return {}
    summary = v2_summary(prepared)
    wire = parse(prepared.body)
    return {'wire_version': 2, 'v1_wire_sha256': prepared.evidence['v1_wire_sha256'], 'v2': summary,
            'flags': flags_for(source, wire, 2) + v2_flags(source, summary)}


def pair_row(paths, target, wire_version=1):
    prepared = prepare_entry(paths, {'target': target}, wire_version)
    wire = parse(prepared.body)
    meta = wire['metadata']
    source = xml_fields(prepared.xml)
    return {'source_id': prepared.source_id, 'policy': prepared.evidence['policy'],
            'target': {'kind': 'pair', 'record_target_id': prepared.record_target_id,
                       'source_ids': prepared.source_ids, 'reviewed_at': target['reviewed_at']},
            'source_sha256': sha(prepared.xml), 'wire_sha256': sha(prepared.body), 'files': files_facts(prepared),
            'source': {**source, 'abstract': source['abstract'][:500]},
            'wire': {'title': meta['title'], 'creators': [creator_name(c) for c in meta['creators']],
                     'publication_date': meta['publication_date'], 'description': meta['description'][:500],
                     'description_length': len(meta['description']),
                     'subjects': [s['subject'] for s in meta['subjects']]},
            'flags': flags_for(source, wire, wire_version)} | v2_row_extra(prepared, source, wire_version)


def pair_twins(paths, rows):
    """Twin check for pair rows against every journal source except these pairs' own two ids."""
    facts = [{'source_id': row['source_id'], 'source_sha256': row['source_sha256'],
              'title_key': batch.title_key(row['wire']['title'])} for row in rows]
    own = [sid for row in rows for sid in row['target']['source_ids']]
    attempted = batch.attempted_facts(paths, batch.journal_phases(paths), own)
    return batch.resolve_twins(facts, attempted, [], batch.load_registry(paths))


def build_pair_sheet(paths, batch_id, targets, built_by, reviewed_at, now=utc_now, wire_version=1):
    """Review sheet for reviewed pairs, with the twin check against every journal and each other."""
    require(re.fullmatch(batch.BATCH_ID, batch_id) is not None and 0 < len(targets) <= batch.MAX_MEMBERS)
    draft.instant(reviewed_at)
    rows = [pair_row(paths, {'record_target_id': t, 'reviewed_at': reviewed_at}, wire_version) for t in targets]
    ids = [sid for row in rows for sid in row['target']['source_ids']]
    require(len(set(ids)) == len(ids))
    twins, used = pair_twins(paths, rows)
    membership = sha(encode([[row['source_id'], row['wire_sha256']] for row in rows]))
    size = min(len(rows), max(SAMPLE_MIN, math.ceil(SAMPLE_FRACTION * len(rows))))
    flagged = [row['source_id'] for row in rows if row['flags']]
    others = sorted({row['source_id'] for row in rows} - set(flagged), key=batch.by_number)
    sample = sorted(random.Random(membership).sample(others, min(size, len(others))), key=batch.by_number)
    return {'schema_version': 1, 'kind': SHEET_KIND, 'batch_id': batch_id, 'manifest_sha256': None,
            'membership_sha256': membership, 'built_by': built_by, 'built_at': now().isoformat(),
            'member_count': len(rows), 'flagged': flagged, 'sample': sample, 'twins': twins,
            'allowances': [a['origin'] for a in used], 'rows': rows}


def build_sheet(paths, manifest, manifest_sha, built_by, now=utc_now, wire_version=1):
    rows = [sheet_row(paths, member['source_id'], wire_version) for member in manifest['members']]
    flagged = [row['source_id'] for row in rows if row['flags']]
    others = sorted({row['source_id'] for row in rows} - set(flagged), key=batch.by_number)
    size = min(len(others), max(SAMPLE_MIN, math.ceil(SAMPLE_FRACTION * len(rows))))
    # The sample is fixed by the membership, so a reviewer cannot choose it.
    sample = sorted(random.Random(manifest['membership_sha256']).sample(others, size), key=batch.by_number)
    return {'schema_version': 1, 'kind': SHEET_KIND, 'batch_id': manifest['batch_id'],
            'manifest_sha256': manifest_sha, 'membership_sha256': manifest['membership_sha256'],
            'built_by': built_by, 'built_at': now().isoformat(), 'member_count': len(rows),
            'flagged': flagged, 'sample': sample, 'rows': rows}


def build_v2_sheet(paths, base_review, built_by, now=utc_now, suffix='v2'):
    """The v2 review sheet for the approved members of a reviewed v1 batch (ADR 0014).

    Membership, twins and duplicates were settled by the base review; this sheet carries the same
    originals with their v2 wires for the accuracy review of the new fields. Excluded and
    protected sources are left out and listed.
    """
    review, review_sha, order, members = load_review(paths, base_review)
    require(re.fullmatch('v2[a-z]?', suffix) is not None and not re.search('-v2[a-z]?$', review['batch_id']))
    barred = set(exclusions(paths)) | set(PROTECTED)
    rows, skipped = [], []
    for sid in order:
        member = members[sid]
        if not member['approved'] or set(source_ids_of(member)) & barred:
            skipped.append(sid)
            continue
        row = pair_row(paths, member['target'], 2) if member.get('target') else sheet_row(paths, sid, 2)
        require(row['source_id'] == sid and row['source_sha256'] == member['source_sha256']
                and row['v1_wire_sha256'] == member['wire_sha256'] and files_of(row) == files_of(member))
        rows.append(row)
    require(rows)
    membership = sha(encode([[row['source_id'], row['wire_sha256']] for row in rows]))
    flagged = [row['source_id'] for row in rows if row['flags']]
    others = sorted({row['source_id'] for row in rows} - set(flagged), key=batch.by_number)
    size = min(len(others), max(SAMPLE_MIN, math.ceil(SAMPLE_FRACTION * len(rows))))
    sample = sorted(random.Random(membership).sample(others, size), key=batch.by_number)
    return {'schema_version': 1, 'kind': SHEET_KIND, 'batch_id': review['batch_id'] + '-' + suffix, 'wire_version': 2,
            'base_review': {'path': str(Path(base_review).resolve()), 'sha256': review_sha,
                            'batch_id': review['batch_id']},
            'manifest_sha256': None, 'membership_sha256': membership, 'built_by': built_by,
            'built_at': now().isoformat(), 'member_count': len(rows), 'flagged': flagged, 'sample': sample,
            'skipped': skipped, 'rows': rows}


def sheet_path(paths, batch_id):
    return bulk_root(paths) / 'sheets' / (batch_id + '.sheet.json')


def review_path(paths, batch_id):
    return bulk_root(paths) / 'reviews' / (batch_id + '.review.json')


def validate_sheet(sheet):
    require(isinstance(sheet, dict) and sheet.get('kind') == SHEET_KIND and sheet.get('schema_version') == 1
            and isinstance(sheet.get('rows'), list) and sheet['rows']
            and sheet.get('member_count') == len(sheet['rows'])
            and re.fullmatch(batch.BATCH_ID, str(sheet.get('batch_id'))) is not None)
    ids = [row['source_id'] for row in sheet['rows']]
    require(len(set(ids)) == len(ids) and set(sheet['flagged']) <= set(ids) and set(sheet['sample']) <= set(ids)
            and sheet['flagged'] == [row['source_id'] for row in sheet['rows'] if row['flags']])
    return ids


def build_review(sheet, sheet_sha, decisions, reviewer, examined, summary, now=utc_now):
    """The reviewer's decision for every member, bound to the exact sheet it read."""
    ids = validate_sheet(sheet)
    check(isinstance(reviewer, str) and reviewer.strip()
          and reviewer.strip().casefold() != sheet['built_by'].strip().casefold(),
          'the reviewer must be named and differ from the sheet builder', Held)
    check(isinstance(decisions, dict) and set(decisions) == set(ids),
          'a decision is required for every member and only for members', Held)
    for sid, value in decisions.items():
        check(isinstance(value, dict) and value.get('decision') in ('approved', 'held')
              and isinstance(value.get('note', ''), str)
              and (value['decision'] == 'approved' or value.get('note', '').strip()),
              f'{sid}: decision must be approved, or held with a note', Held)
    examined = sorted(set(examined), key=batch.by_number)
    check(set(sheet['flagged']) | set(sheet['sample']) <= set(examined) <= set(ids),
          'every flagged and sampled member must be examined', Held)
    reviewed_at = now()
    check(draft.instant(sheet['built_at']) <= reviewed_at, 'review precedes the sheet', Held)
    return {'schema_version': 1, 'kind': REVIEW_KIND, 'batch_id': sheet['batch_id'], 'sheet_sha256': sheet_sha,
            'reviewer': reviewer, 'reviewer_type': 'agent', 'reviewed_at': reviewed_at.isoformat(),
            'examined': examined, 'summary': summary,
            'decisions': {sid: {'decision': decisions[sid]['decision'], 'note': decisions[sid].get('note', '')}
                          for sid in ids}}


def load_review(paths, path):
    """A review and the sheet it binds; members carry the hashes the stages require."""
    review, review_sha = draft.read_document(path)
    require(isinstance(review, dict) and review.get('kind') == REVIEW_KIND and review.get('schema_version') == 1)
    sheet, sheet_sha = draft.read_document(sheet_path(paths, review['batch_id']))
    require(sheet_sha == review['sheet_sha256'])
    ids = validate_sheet(sheet)
    require(set(review['decisions']) == set(ids) and isinstance(review.get('reviewer'), str)
            and review['reviewer'].strip().casefold() != sheet['built_by'].strip().casefold()
            and set(sheet['flagged']) | set(sheet['sample']) <= set(review['examined']))
    members = {}
    for row in sheet['rows']:
        members[row['source_id']] = {'source_id': row['source_id'], 'source_sha256': row['source_sha256'],
                                     'wire_sha256': row['wire_sha256'],
                                     **({'files': row['files'], 'target': row['target']} if row.get('target')
                                        else {'file': row['file']}),
                                     'wire_version': row.get('wire_version', 1),
                                     'review_sha256': review_sha, 'batch_id': sheet['batch_id'],
                                     'approved': review['decisions'][row['source_id']]['decision'] == 'approved'}
    return review, review_sha, [row['source_id'] for row in sheet['rows']], members


# ---------------------------------------------------------------- provider checks

def compare_wire(actual, prepared):
    """The provider's metadata equals this wire (v1 or v2 rules); any difference holds the record."""
    expected = parse(prepared.body)['metadata']
    try:
        if getattr(prepared, 'wire_version', 1) == 2:
            wire_v2.compare(actual, expected)
        else:
            compare_metadata(actual, expected)
    except (Held, KeyError, TypeError, AttributeError, ValueError):
        raise Held('metadata differs') from None


def expected_access(prepared):
    """Access as the wire sets it: v1 keeps the XML restricted, v2 makes it public (Brett, 2026-10-20)."""
    access = parse(prepared.body)['access']
    require(access in ({'record': 'public', 'files': 'restricted'}, {'record': 'public', 'files': 'public'}))
    return access


def access_matches(access, prepared):
    wanted = expected_access(prepared)
    return (isinstance(access, dict) and access.get('record') == wanted['record']
            and access.get('files') == wanted['files'] and not (access.get('embargo') or {}).get('active'))


def identity_of(data):
    parent = data.get('parent') if isinstance(data.get('parent'), dict) else {}
    return {'id': draft.identifier(data.get('id')), 'parent_id': draft.identifier(parent.get('id')),
            'owner': parent.get('access', {}).get('owned_by', {}).get('user'), 'created': data.get('created')}


def check_file_entry(entry, expected, *, completed=True):
    check(isinstance(entry, dict) and entry.get('key') == expected['key'], 'file entry key differs')
    if completed:
        check(entry.get('size') == expected['size'] and entry.get('checksum') == 'md5:' + expected['md5'],
              'file size or MD5 differs from the original')
    else:  # initialized without content: zenodo.org lists it with size 0 and no checksum (FGDC-759, 2026-10-24)
        check(not entry.get('size') and not entry.get('checksum'), 'pending file entry already has content')


def check_draft(data, prepared, record, owner, *, files_complete, status='draft', bind_since=None,
                foreign=frozenset(), compare=True, pending=frozenset()):
    """The draft as the provider holds it; binds the identity on the first validated response.

    `pending` names originals initialized but without content, listed with size 0 and no checksum;
    only `observe` passes it, so every other caller still requires the files it expects complete.
    """
    check(isinstance(data, dict) and data.get('is_published') is False and data.get('status') == status
          and data.get('pids') == {} and data.get('doi') in (None, '')
          and data.get('parent', {}).get('pids', {}) == {}
          and data.get('versions', {}).get('index') == 1, 'draft state differs')
    identity = identity_of(data)
    check(identity['owner'] == owner and identity['id'] != identity['parent_id'], 'draft owner differs')
    if record['identity'] is None:
        created = draft.instant(identity['created'])
        check(bind_since is not None and bind_since - draft.RESUME_CLOCK_SKEW <= created,
              'created time precedes the create request')
        check(not ({identity['id'], identity['parent_id']} & set(foreign)),
              'record id already belongs to another source or lane')
    else:
        check(identity == record['identity'], 'draft identity differs from the journal')
    base = '/api/records/' + identity['id'] + '/draft'
    check(data.get('links', {}).get('self') == draft.ORIGIN + base
          and data.get('links', {}).get('files') == draft.ORIGIN + base + '/files', 'draft links differ')
    if compare:  # off only for the structure of a draft about to be revised to its reviewed wire
        try:
            compare_wire(data.get('metadata'), prepared)
        except Held:
            raise RecordHold('provider metadata differs from the wire') from None
        check(access_matches(data.get('access', {}), prepared), 'access differs')
    files = data.get('files', {})
    expected = files_of(record)
    entries = files.get('entries') if isinstance(files.get('entries'), dict) else None
    pending = {f['key'] for f in expected} & set(pending)
    if files_complete == 'partial':  # some originals completed, the rest not yet (a pair between uploads)
        check(entries is not None and set(entries) - pending < {f['key'] for f in expected}, 'draft files differ')
        present = [f for f in expected if f['key'] in entries and f['key'] not in pending]
    else:
        present = expected if files_complete else []
    check(files.get('enabled') is True and entries is not None
          and set(entries) == {f['key'] for f in present} | pending
          and files.get('count') == len(present) + len(pending)
          and files.get('total_bytes') == sum(f['size'] for f in present), 'draft files differ')
    for f in present:
        check_file_entry(entries[f['key']], f)
    for f in expected:
        if f['key'] in pending:
            check_file_entry(entries[f['key']], f, completed=False)
    if files_complete is True:
        check(data.get('errors', []) == [], 'draft reports validation errors')
    elif not present:
        try:
            expected_empty_file_warning(data)
        except Held:
            raise RecordHold('draft reports an unexpected validation error') from None
    revision = data.get('revision_id')
    check(type(revision) is int and revision >= 1, 'draft revision missing')
    if status == 'draft':
        communities = data.get('parent', {}).get('communities', {})
        check(isinstance(communities, dict) and communities.get('ids', []) == []
              and 'review' not in data.get('parent', {}), 'draft already has a community or review')
    return identity, revision


def check_published(data, prepared, record, owner, communities):
    check(isinstance(data, dict) and data.get('is_published') is True and data.get('status') == 'published'
          and data.get('id') == record['identity']['id']
          and data.get('parent', {}).get('id') == record['identity']['parent_id']
          and data.get('parent', {}).get('access', {}).get('owned_by', {}).get('user') == owner
          and data.get('versions', {}).get('index') == 1, 'published record state or identity differs')
    base = '/api/records/' + record['identity']['id']
    check(data.get('links', {}).get('self') == draft.ORIGIN + base, 'published links differ')
    try:
        compare_wire(data.get('metadata'), prepared)
    except Held:
        raise RecordHold('published metadata differs from the wire') from None
    check(access_matches(data.get('access', {}), prepared), 'published access differs')
    files = data.get('files', {})
    expected = files_of(record)
    check(files.get('enabled') is True and isinstance(files.get('entries'), dict)
          and set(files['entries']) == {f['key'] for f in expected} and files.get('count') == len(expected)
          and files.get('total_bytes') == sum(f['size'] for f in expected), 'published files differ')
    for f in expected:
        check_file_entry(files['entries'][f['key']], f)
    membership = data.get('parent', {}).get('communities', {})
    check(isinstance(communities, list) and communities and communities[0] == PICES_COMMUNITY,
          'the verified PICES community is required', Held)
    check(isinstance(membership, dict) and isinstance(membership.get('ids'), list)
          and sorted(membership['ids']) == sorted(communities)
          and membership.get('default') == PICES_COMMUNITY, 'PICES membership or default differs')
    try:
        return published_pids(data)
    except Held:
        raise RecordHold('published DOI pids are incomplete') from None


def check_edit_draft(data, prepared, record, owner, communities, *, saved=False):
    """An edit draft of a published record: same identity and DOIs, this wire, the original files.

    With `prepared` None the metadata and access are not compared (a partly saved draft being rebound).
    """
    identity = record['identity']
    parent = data.get('parent', {}) if isinstance(data, dict) else {}
    check(isinstance(data, dict) and data.get('id') == identity['id'] and data.get('is_published') is True
          and data.get('status') == 'published' and parent.get('id') == identity['parent_id']
          and parent.get('access', {}).get('owned_by', {}).get('user') == owner
          and data.get('versions', {}).get('index') == 1, 'edit draft state or identity differs')
    base = '/api/records/' + identity['id'] + '/draft'
    check(data.get('links', {}).get('self') == draft.ORIGIN + base, 'edit draft links differ')
    check({'record': data.get('pids'), 'parent': parent.get('pids')} == record['pids'], 'edit draft DOI pids differ')
    if prepared is not None:
        try:
            compare_wire(data.get('metadata'), prepared)
        except Held:
            raise RecordHold('edit draft metadata differs from the ' + ('reviewed v2 wire' if saved else
                                                                        'published wire')) from None
        check(access_matches(data.get('access', {}), prepared), 'edit draft access differs')
    files = data.get('files', {})
    expected = files_of(record)
    entries = files.get('entries') if isinstance(files.get('entries'), dict) else None
    check(files.get('enabled') is True and entries is not None and set(entries) == {f['key'] for f in expected}
          and files.get('count') == len(expected) and files.get('total_bytes') == sum(f['size'] for f in expected),
          'edit draft files differ')
    for f in expected:
        check_file_entry(entries[f['key']], f)
    if saved:
        check(data.get('errors', []) == [], 'edit draft reports validation errors')
    membership = parent.get('communities', {})
    check(isinstance(membership, dict) and sorted(membership.get('ids') or []) == sorted(communities)
          and membership.get('default') == PICES_COMMUNITY, 'edit draft community differs')
    revision = data.get('revision_id')
    check(type(revision) is int and revision >= 1, 'edit draft revision missing')
    return revision


def carried_of(data):
    """What the update PUT keeps from the edit draft: its DOI pids and custom fields."""
    custom = data.get('custom_fields') or {}
    check(isinstance(data.get('pids'), dict) and isinstance(custom, dict), 'edit draft pids or custom fields differ')
    return {'pids': data['pids'], 'custom_fields': custom}


def update_body(prepared, carried):
    """The v2 wire with the record's own DOI pids and custom fields, so the update changes nothing else."""
    return encode({**parse(prepared.body), 'pids': carried['pids'], 'custom_fields': carried['custom_fields']})


# ---------------------------------------------------------------- runner

class Bulk:
    """One run of one stage; the ledger lock is held for the whole run."""

    def __init__(self, paths, transport, token, *, owner, stage, now=utc_now, clock=time.monotonic,
                 sleep=time.sleep, pace=PACE_SECONDS, captured_by='modern_bulk'):
        require(stage in ('drafts', 'publish', 'reconcile', 'update'))
        require(isinstance(token, str) and 16 <= len(token) <= 4096 and all(33 <= ord(c) <= 126 for c in token))
        require(isinstance(owner, str) and re.fullmatch('[1-9][0-9]{0,19}', owner) is not None)
        self.paths, self.transport, self.token, self.owner, self.stage = paths, transport, token, owner, stage
        self.now, self.clock, self.sleep, self.pace = now, clock, sleep, pace
        self.captured_by = captured_by
        self.inventory_pace = pace  # listing pages are paced like every other request
        self.community_ids = None
        self.last_request = None
        started = now()
        self.run_id = stage + '-' + stamp(started) + '-' + os.urandom(2).hex()
        self.ledger = {'schema_version': 1, 'kind': RUN_KIND, 'run_id': self.run_id, 'stage': stage,
                       'owner': owner, 'started_at': started.isoformat(), 'updated_at': started.isoformat(),
                       'status': 'running', 'inputs': {}, 'inventories': [], 'outcomes': {}, 'holds': [],
                       'stops': [], 'requests': 0}
        self.inventory = None
        self.inventory_at = None
        self.consecutive_holds = 0

    # ---- ledger

    def ledger_path(self):
        return bulk_root(self.paths) / 'runs' / (self.run_id + '.json')

    def save_ledger(self):
        self.ledger['updated_at'] = self.now().isoformat()
        path = self.ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path, self.ledger)

    def outcome(self, source_id, value, reason=None):
        self.ledger['outcomes'][source_id] = value
        if reason is not None:
            self.ledger['holds'].append({'source_id': source_id, 'reason': reason, 'at': self.now().isoformat()})
        self.save_ledger()

    # ---- requests

    def paced(self):
        if self.last_request is not None:
            wait = self.last_request + self.pace - self.clock()
            if wait > 0:
                self.sleep(wait)

    def retain(self, record, index, receipt, response):
        evidence = diagnostic(response, self.token)
        body = b''
        if response.complete and not evidence['credential_suppressed']:
            body = response.body
        evidence.pop('body_base64', None)
        evidence.update(request=dict(receipt), source_id=record['source_id'], run_id=self.run_id,
                        body_gzip_base64=base64.b64encode(gzip.compress(body, mtime=0)).decode())
        name = f'{index:03d}.{receipt["kind"]}.json'
        path = write_exclusive(evidence_dir(self.paths, record['source_id']) / name, evidence)
        return evidence, {'filename': name, 'sha256': sha(path.read_bytes())}

    def call(self, record, kind, method, path, expected, body=None, accept=draft.MIME):
        """Journal, pace, dispatch, retain and classify one request."""
        check(record['counts'][kind] < write_limit(record, kind), f'{kind} already spent for this record; reconcile it')
        require(not any(r.get('status') == 'uncertain' for r in record['requests']))
        record['counts'][kind] += 1
        receipt = {'index': len(record['requests']), 'kind': kind, 'method': method, 'path': path,
                   'body_sha256': sha(body) if body is not None else None, 'run_id': self.run_id,
                   'attempted_at': self.now().isoformat(), 'status': 'uncertain'}
        record['requests'].append(receipt)
        save_record(self.paths, record)  # durable before dispatch
        self.paced()
        self.ledger['requests'] += 1
        self.last_request = self.clock()  # pacing spaces request starts: at most one per PACE_SECONDS
        try:
            response = self.transport.request(method, path, body, timeout=draft.TIMEOUT, accept=accept)
        except Exception:
            raise record_stop(f'{kind} request interrupted or timed out; outcome unknown') from None
        response = normalize_response(response)
        evidence, reference = self.retain(record, receipt['index'], receipt, response)
        receipt.update(status='answered', http_status=response.status, bytes=len(response.body),
                       response_sha256=evidence['response_sha256'], evidence=reference,
                       credential_suppressed=evidence['credential_suppressed'])
        save_record(self.paths, record)
        media = response.mime.split(';', 1)[0].strip().lower() if isinstance(response.mime, str) else ''
        if not response.complete or response.status in STOP_STATUSES or media not in (draft.MIME, JSON_MEDIA):
            raise record_stop(f'{kind} answered {response.status} ({media or "no media"}, '
                              f'complete {response.complete}); stopping the run')
        check(not evidence['credential_suppressed'], f'{kind} response screened as credential-bearing')
        check(response.status == expected, f'{kind} answered {response.status}, expected {expected}')
        try:
            check(draft.response_media_type(response.mime) == accept, f'{kind} answered {media}, not {accept}')
            value = parse(response.body)
        except RecordHold:
            raise
        except Held:
            raise RecordHold(f'{kind} response is not valid JSON') from None
        check(isinstance(value, dict), f'{kind} response is not an object')
        return value

    @staticmethod
    def unspent(record, kind, path, key):
        """A file's upload or commit is sent once, or once more only when reconcile saw it absent."""
        sent = sum(r['kind'] == kind and r['path'] == path for r in record['requests'])
        again = key in record.get('resend', {}).get(kind, [])
        check(sent == 0 or (sent == 1 and again), f'{kind} of {key} was already sent; reconcile it')

    @staticmethod
    def check_listing(listing, expected, label):
        entries = listing.get('entries')
        check(isinstance(entries, list) and len(entries) == len(expected), f'{label} file listing differs')
        by_key = {e.get('key'): e for e in entries if isinstance(e, dict)}
        check(set(by_key) == {f['key'] for f in expected}, f'{label} file keys differ')
        for f in expected:
            check_file_entry(by_key[f['key']], f)
            check(by_key[f['key']].get('status') == 'completed', f'{label} file is not completed')

    def entry_hits(self, prepared, source_ids, allowed=()):
        """Inventory hits for every source id the record stands for."""
        hits = []
        for sid in source_ids:
            for hit in self.inventory_hits(prepared, allowed, source_id=sid):
                if hit not in hits:
                    hits.append(hit)
        return hits

    def advance(self, record, phase):
        record['phase'] = phase
        record['history'].append({'phase': phase, 'at': self.now().isoformat(), 'run_id': self.run_id})
        save_record(self.paths, record)

    def hold(self, record, reason):
        record['hold'] = {'stage': self.stage, 'phase': record['phase'], 'reason': reason,
                          'at': self.now().isoformat(), 'run_id': self.run_id}
        save_record(self.paths, record)

    # ---- inventory and barriers

    def refresh_inventory(self, force=False):
        if not force and self.inventory_at is not None and self.now() - self.inventory_at < INVENTORY_REFRESH:
            return
        directory = bulk_root(self.paths) / 'inventories'
        known = operator.known_records(self.paths)
        self.paced()
        path, document = operator.capture_inventory(self.transport, self.token, directory, self.captured_by,
                                                    known=known, max_bytes=INVENTORY_MAX_BYTES,
                                                    pace=self.inventory_pace,
                                                    now=lambda: self.now().replace(microsecond=0))
        self.ledger['requests'] += len(document['pages']) + len(document['details'])
        self.last_request = self.clock()
        owners = {str(r.get('owner')) for r in document['records']}
        check(owners <= {self.owner}, 'the inventory lists records of another owner; check the token and --owner',
              StopRun)
        self.inventory, self.inventory_at = document, self.now()
        self.ledger['inventories'].append({'path': str(path), 'sha256': sha(path.read_bytes()),
                                           'records': document['record_count'],
                                           'captured_at': document['captured_at']})
        self.save_ledger()

    def inventory_now(self, force=False):
        """Refresh the inventory when due; a failed capture stops the run and holds no record."""
        try:
            self.refresh_inventory(force=force)
        except StopRun:
            raise
        except Exception as error:
            reason = str(error) if isinstance(error, Held) else type(error).__name__
            raise StopRun('inventory capture held: ' + reason) from None

    def verify_community(self):
        """Read the PICES community with this token before any publication write."""
        path = '/api/communities/' + PICES_COMMUNITY
        self.paced()
        self.ledger['requests'] += 1
        try:
            response = normalize_response(self.transport.request('GET', path, None, timeout=draft.TIMEOUT))
        except Exception:
            raise StopRun('community read interrupted') from None
        self.last_request = self.clock()
        evidence = diagnostic(response, self.token)
        evidence.pop('body_base64', None)
        complete = response.complete and not evidence['credential_suppressed']
        evidence.update(request={'method': 'GET', 'path': path}, run_id=self.run_id,
                        body_gzip_base64=base64.b64encode(gzip.compress(response.body if complete else b'',
                                                                        mtime=0)).decode())
        target = write_exclusive(bulk_root(self.paths) / 'runs' / (self.run_id + '.community.json'), evidence)
        check(complete and response.status == 200
              and draft.response_media_type(response.mime) == draft.MIME, 'community read failed', StopRun)
        value = parse(response.body)
        access = value.get('access', {}) if isinstance(value, dict) else {}
        permissions = value.get('ui', {}).get('permissions', {}) if isinstance(value.get('ui'), dict) else {}
        parent = value.get('parent')
        parent_id = parent.get('id') if isinstance(parent, dict) else None
        check(value.get('id') == PICES_COMMUNITY and value.get('slug') == 'pices'
              and access.get('visibility') == 'public' and access.get('record_submission_policy') in ('open', 'closed')
              and (parent is None or isinstance(parent_id, str)), 'the PICES community identity differs', StopRun)
        check(permissions.get('can_submit_record') is True and permissions.get('can_include_directly') is True,
              'this token cannot include records in PICES directly', StopRun)
        self.community_ids = [PICES_COMMUNITY] + ([parent_id] if parent_id else [])
        self.ledger['inputs']['community'] = {
            'id': PICES_COMMUNITY, 'slug': 'pices', 'parent_id': parent_id, 'review_policy': access.get('review_policy'),
            'record_submission_policy': access.get('record_submission_policy'),
            'permissions': {k: permissions.get(k) for k in ('can_submit_record', 'can_include_directly', 'can_update')},
            'evidence': {'path': str(target), 'sha256': sha(target.read_bytes())}}
        self.save_ledger()
        return self.community_ids

    def foreign_ids(self, source_id):
        """Ids the create response must not claim: other sources' records and every legacy identity."""
        ids = set(operator.known_records(self.paths))
        for suffix, key in (('', None), ('.mutations.json', 'targets')):
            path = Path(self.paths.uploads_registry_path + suffix)
            if path.exists():
                document = json.loads(path.read_bytes())
                rows = document.get(key, {}) if key else document
                ids.update(str(row['deposition_id']) for row in rows.values()
                           if isinstance(row, dict) and row.get('deposition_id') is not None)
        record = load_record(self.paths, source_id)
        if record is not None and record.get('identity'):
            ids -= {record['identity']['id'], record['identity']['parent_id']}
        if record is not None and record.get('candidate_id'):
            ids.discard(record['candidate_id'])  # this source's own create answer
        return ids

    def inventory_hits(self, prepared, allowed=(), source_id=None):
        """Unknown owner records that may carry this source; `allowed` are reviewed false matches."""
        return inventory_hits_in(self.paths, self.inventory, prepared, allowed, source_id)

    def modern_row(self, source_id):
        journal_path = Path(self.paths.uploads_registry_path + '.modern-v1.json')
        if not journal_path.exists():
            return None
        journal, _ = draft.read_document(journal_path)
        return journal.get('targets', {}).get(source_id)

    def legacy_claims(self, source_id):
        root = draft.state_root(self.paths)
        if (root / (source_id + '.modern-create-v1.intent.json')).exists() and not legacy_released(self.paths, source_id):
            return 'modern-v1 intent'
        return self.chain_claims(source_id, ('', '.mutations.json'))

    def chain_claims(self, source_id, suffixes):
        for suffix in suffixes:
            path = Path(self.paths.uploads_registry_path + suffix)
            if path.exists():
                document = json.loads(path.read_bytes())
                rows = document.get('targets', {}) if suffix else document
                if isinstance(rows, dict) and source_id in rows:
                    return 'single-record chain entry (' + (suffix or 'legacy registry') + ')'
        return None

    # ---- stages

    def draft_member(self, member):
        """Create, upload and verify one draft; returns the outcome label."""
        sid = member['source_id']
        check(member['approved'], 'the batch review did not approve this member')
        record = load_record(self.paths, sid)
        if record is not None:
            if record['hold'] is not None:
                return 'held-earlier'
            if record['phase'] in DRAFTED + UPDATING:
                return 'already-drafted'
            if any(r.get('status') == 'uncertain' for r in record['requests']):
                self.hold(record, 'a request was interrupted before its answer was recorded; reconcile it')
                raise RecordHold('interrupted request')
        prepared = prepare_entry(self.paths, member)
        check(sha(prepared.xml) == member['source_sha256'] and sha(prepared.body) == member['wire_sha256'],
              'live preparation differs from the reviewed sheet')
        sids = source_ids_of(member)
        if record is None or record['phase'] == 'planned':
            check(not set(sids) & set(PROTECTED), 'protected source')
            check(not set(sids) & set(exclusions(self.paths)), 'excluded by a reviewed decision')
            for other in sids[1:]:
                # The second source of a pair carries no record of its own; nothing may claim it either.
                check(load_record(self.paths, other) is None and not intent_path(self.paths, other).exists()
                      and self.modern_row(other) is None and self.legacy_claims(other) is None,
                      f'{other} is already claimed by another record or lane')
            row = self.modern_row(sid)
            if row is not None and legacy_released(self.paths, sid):
                row = None  # a recorded release (FGDC-141): the bulk barrier below decides alone
            if row is not None:
                record = new_record(sid, member, 'modern-v1')
                claim = self.chain_claims(sid, ('.modern-publication-v1.json', '.modern-capture-v1.json'))
                if claim is not None:
                    self.hold(record, claim + ' exists for this source; finish it on its own route')
                    raise RecordHold(claim)
                if row.get('phase') == 'verified' and isinstance(row.get('identity'), dict):
                    record['identity'] = dict(row['identity'])
                    record['draft_revision'] = row.get('verified_revision')
                    self.advance(record, 'adopted')
                    return 'adopted'
                self.hold(record, 'modern-v1 row is not verified; use its own recovery route')
                raise RecordHold('modern-v1 row is not verified')
            if record is None:
                record = new_record(sid, member, 'bulk')
            else:  # released from an earlier barrier hold; bind it to the current review
                record.update({k: member[k] for k in ('source_sha256', 'wire_sha256', 'file', 'files', 'target',
                                                       'review_sha256', 'batch_id', 'wire_version') if k in member})
            claim = self.legacy_claims(sid)
            if claim is not None:
                self.hold(record, claim + ' exists for this source')
                raise RecordHold(claim)
            hits = self.entry_hits(prepared, sids, record.get('inventory_allowed', []))
            if hits:
                self.hold(record, 'owner inventory may already carry this source: ' + json.dumps(hits))
                raise RecordHold('inventory match')
            check(not intent_path(self.paths, sid).exists(), 'an intent exists without a created record')
            self.advance(record, 'creating')  # the record first: an intent never exists without one
        try:
            return self.continue_draft(record, prepared, self.foreign_ids(sid))
        finally:
            save_record(self.paths, record)

    def continue_draft(self, record, prepared, foreign):
        sid = record['source_id']
        expected = files_of(record)
        contents = contents_of(prepared)
        require([f['key'] for f in expected] == list(contents))
        if record['phase'] == 'creating':
            check(record['counts']['create'] < 1 + record['allowances'].get('create', 0),
                  'create already spent; reconcile it')
            for claimed in source_ids_of(record):  # a pair claims both of its sources
                if record['counts']['create'] == 0 and not intent_path(self.paths, claimed).exists():
                    write_exclusive(intent_path(self.paths, claimed), {
                        'schema_version': 1, 'kind': 'modern-bulk-intent-v1', 'source_id': claimed, 'record': sid,
                        'source_sha256': record['source_sha256'], 'wire_sha256': record['wire_sha256'],
                        'review_sha256': record['review_sha256'], 'run_id': self.run_id,
                        'at': self.now().isoformat()})
                require(intent_path(self.paths, claimed).exists())
            if record['counts']['create'] > 0:
                # An allowed re-send passes the whole barrier again on an inventory captured now.
                self.refresh_inventory(force=True)
                hits = self.entry_hits(prepared, source_ids_of(record), record.get('inventory_allowed', []))
                check(not hits, 're-sent create blocked by the owner inventory: ' + json.dumps(hits))
            sent = self.now()
            value = self.call(record, 'create', 'POST', '/api/records', 201, prepared.body)
            candidate = value.get('id')
            if isinstance(candidate, str) and re.fullmatch('[1-9][0-9]{0,19}', candidate):
                record['candidate_id'] = candidate
                save_record(self.paths, record)
            identity, revision = check_draft(value, prepared, record, self.owner, files_complete=False,
                                             bind_since=sent, foreign=foreign)
            record['identity'] = identity
            self.advance(record, 'created')
        base = '/api/records/' + record['identity']['id'] + '/draft'
        if record['phase'] == 'created':
            value = self.call(record, 'init', 'POST', base + '/files', 201,
                              encode([{'key': f['key']} for f in expected]))
            entries = value.get('entries')
            check(isinstance(entries, list) and len(entries) == len(expected)
                  and sorted(e.get('key') for e in entries if isinstance(e, dict)) == sorted(contents),
                  'file init listing differs')
            for entry in entries:
                check(entry.get('status') == 'pending', 'initialized file is not pending')
            self.advance(record, 'initialized')
        if record['phase'] == 'initialized':
            uploaded = record.setdefault('uploaded', [])
            for f in expected:
                if f['key'] in uploaded:
                    continue
                file = base + '/files/' + f['key']
                self.unspent(record, 'content', file + '/content', f['key'])
                value = self.call(record, 'content', 'PUT', file + '/content', 200, contents[f['key']])
                check(value.get('key') == f['key'], 'uploaded file key differs')
                if value.get('status') != 'completed':
                    self.unspent(record, 'commit', file + '/commit', f['key'])
                    value = self.call(record, 'commit', 'POST', file + '/commit', 200)
                check(value.get('status') == 'completed', 'upload did not complete')
                check_file_entry(value, f)
                uploaded.append(f['key'])
                save_record(self.paths, record)
            self.advance(record, 'uploaded')
        if record['phase'] == 'uploaded':
            _, revision = check_draft(self.call(record, 'get', 'GET', base, 200), prepared, record, self.owner,
                                      files_complete=True)
            self.check_listing(self.call(record, 'get', 'GET', base + '/files', 200), expected, 'draft')
            record['draft_revision'] = revision
            self.advance(record, 'draft-verified')
            return 'drafted'
        raise RecordHold(f'unexpected phase {record["phase"]} for {sid}')

    def publish_member(self, source_id, release_sha):
        record = load_record(self.paths, source_id)
        check(record is not None, 'no draft record for this source')
        if record['hold'] is not None:
            return 'held-earlier'
        if record['phase'] == 'published':
            return 'already-published'
        if any(r.get('status') == 'uncertain' for r in record['requests']):
            self.hold(record, 'a request was interrupted before its answer was recorded; reconcile it')
            raise RecordHold('interrupted request')
        check(record['phase'] in ('draft-verified', 'adopted', 'review-set', 'accepted'), 'record is not drafted')
        prepared = prepare_entry(self.paths, record)
        check(sha(prepared.xml) == record['source_sha256'] and sha(prepared.body) == record['wire_sha256'],
              'live preparation differs from the drafted record')
        try:
            return self.continue_publish(record, prepared, release_sha)
        finally:
            save_record(self.paths, record)

    def continue_publish(self, record, prepared, release_sha):
        if self.community_ids is None:
            self.verify_community()  # once per run, before its first publication request
        identity = record['identity']
        base = '/api/records/' + identity['id']
        if record['phase'] in ('draft-verified', 'adopted'):
            check_draft(self.call(record, 'get', 'GET', base + '/draft', 200), prepared, record, self.owner,
                        files_complete=True)
            record['release_sha256'] = release_sha
            body = encode({'type': 'community-submission', 'receiver': {'community': PICES_COMMUNITY}})
            value = self.call(record, 'review', 'PUT', base + '/draft/review', 200, body, accept=JSON_MEDIA)
            request_id = value.get('id')
            check(isinstance(request_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', request_id),
                  'review request id missing')
            record['request_id'] = request_id
            try:
                validate_request(value, {'identity': identity}, {'id': PICES_COMMUNITY}, request_id, created=True)
            except Held:
                raise RecordHold('review request differs from the PICES submission') from None
            record['request_status'] = value['status']
            self.advance(record, 'review-set')
        if record['phase'] == 'review-set':
            # The review PUT has no server-side compare-and-swap: read the draft again before submitting.
            reviewed = self.call(record, 'get', 'GET', base + '/draft', 200)
            check_draft(reviewed, prepared, record, self.owner, files_complete=True, status='draft_with_review')
            review = reviewed.get('parent', {}).get('review', {})
            check(isinstance(review, dict) and review.get('id') == record['request_id']
                  and review.get('receiver') == {'community': PICES_COMMUNITY}, 'the open review differs')
            value = self.call(record, 'submit', 'POST', base + '/draft/actions/submit-review', 202,
                              encode({'require_review': False}), accept=JSON_MEDIA)
            try:
                validate_request(value, {'identity': identity}, {'id': PICES_COMMUNITY}, record['request_id'])
            except Held:
                raise RecordHold('submitted request differs from the PICES submission') from None
            record['request_status'] = value['status']
            save_record(self.paths, record)
            if value['status'] != 'accepted':
                raise record_stop('the community did not include the record directly; it awaits review')
            self.advance(record, 'accepted')
        if record['phase'] == 'accepted':
            record['pids'] = check_published(self.call(record, 'get', 'GET', base, 200), prepared, record,
                                             self.owner, self.community_ids)
            # The published files endpoint serves only application/json (406 for the vendor type).
            self.check_listing(self.call(record, 'get', 'GET', base + '/files', 200, accept=JSON_MEDIA),
                               files_of(record), 'published')
            self.advance(record, 'published')
            return 'published'
        raise RecordHold(f'unexpected phase {record["phase"]}')

    def update_member(self, source_id, release_sha, member):
        """Edit one published v1 record in place to its reviewed v2 wire: same DOI, a new revision."""
        record = load_record(self.paths, source_id)
        check(record is not None, 'no record for this source')
        if record['hold'] is not None:
            return 'held-earlier'
        if record['phase'] == 'published' and record.get('wire_version', 1) == 2:
            return 'already-updated'
        if any(r.get('status') == 'uncertain' for r in record['requests']):
            self.hold(record, 'a request was interrupted before its answer was recorded; reconcile it')
            raise RecordHold('interrupted request')
        check(record['phase'] in ('published',) + UPDATING and record.get('wire_version', 1) == 1
              and isinstance(record.get('pids'), dict), 'record is not a published v1 record')
        check(member['approved'] and member.get('wire_version') == 2 and member['source_id'] == source_id
              and member['source_sha256'] == record['source_sha256'] and files_of(member) == files_of(record),
              'the v2 review does not approve this record with its original')
        current = prepare_entry(self.paths, record)
        check(sha(current.xml) == record['source_sha256'] and sha(current.body) == record['wire_sha256'],
              'live preparation differs from the published record')
        target = prepare_entry(self.paths, record, wire_version=2)
        check(sha(target.body) == member['wire_sha256'], 'live v2 preparation differs from the reviewed sheet')
        if record['phase'] == 'published':
            record['update'] = {'wire_version': 2, 'wire_sha256': member['wire_sha256'],
                                'review_sha256': member['review_sha256'], 'batch_id': member['batch_id'],
                                'release_sha256': release_sha, 'started_at': self.now().isoformat(),
                                'run_id': self.run_id, 'carried': None}
            self.advance(record, 'editing')  # durable before the edit request
        check(record.get('update', {}).get('wire_sha256') == member['wire_sha256'],
              'the update in progress targets another wire')
        try:
            return self.continue_update(record, current, target)
        finally:
            save_record(self.paths, record)

    def continue_update(self, record, current, target):
        if self.community_ids is None:
            self.verify_community()
        base = '/api/records/' + record['identity']['id']
        update = record['update']
        if record['phase'] == 'editing':
            # Opening the edit draft answers with the record as published; it must be exactly the v1 wire.
            opened = self.call(record, 'edit', 'POST', base + '/draft', 201)
            check_edit_draft(opened, current, record, self.owner, self.community_ids)
            update['carried'] = carried_of(opened)
            self.advance(record, 'edit-open')
        if record['phase'] == 'edit-open':
            check(isinstance(update.get('carried'), dict), 'the edit draft was not observed; reconcile it')
            saved = self.call(record, 'update', 'PUT', base + '/draft', 200, update_body(target, update['carried']))
            update['saved_revision'] = check_edit_draft(saved, target, record, self.owner, self.community_ids,
                                                        saved=True)
            self.advance(record, 'edit-saved')
        if record['phase'] == 'edit-saved':
            value = self.call(record, 'publish', 'POST', base + '/draft/actions/publish', 202)
            check(value.get('id') == record['identity']['id'] and value.get('is_published') is True,
                  'the publish answer names another record or no published state')
            self.advance(record, 'edit-published')
        if record['phase'] == 'edit-published':
            pids = check_published(self.call(record, 'get', 'GET', base, 200), target, record, self.owner,
                                   self.community_ids)
            check(pids == record['pids'], 'published DOI pids changed')
            self.check_listing(self.call(record, 'get', 'GET', base + '/files', 200, accept=JSON_MEDIA),
                               files_of(record), 'published')
            update['previous'] = {k: record[k] for k in ('wire_sha256', 'review_sha256', 'batch_id')} | {
                'wire_version': record.get('wire_version', 1)}
            update['completed_at'] = self.now().isoformat()
            record.update(wire_version=2, wire_sha256=update['wire_sha256'], review_sha256=update['review_sha256'],
                          batch_id=update['batch_id'])
            self.advance(record, 'published')
            return 'updated'
        raise RecordHold(f'unexpected phase {record["phase"]}')

    def run(self, items, step, *, limit=None):
        """Apply `step` to each item in order; record holds and stop on systemic failure."""
        done = 0
        try:
            for item in items:
                sid = item if isinstance(item, str) else item['source_id']
                if limit is not None and done >= limit:
                    break
                if self.stage == 'drafts':
                    self.inventory_now()
                try:
                    result = step(item)
                except StopRun as stop:
                    record = load_record(self.paths, sid)
                    if getattr(stop, 'on_record', False) and record is not None and record['hold'] is None:
                        self.hold(record, str(stop))
                    self.outcome(sid, 'stopped', str(stop))
                    raise
                except Exception as error:  # RecordHold, other closed holds, unexpected member errors
                    reason = str(error) if isinstance(error, Held) else f'{type(error).__name__}: {error}'[:300]
                    record = load_record(self.paths, sid)
                    if record is not None and record['hold'] is None:
                        self.hold(record, reason)
                    self.outcome(sid, 'held', reason)
                    self.consecutive_holds += 1
                    if self.consecutive_holds >= MAX_CONSECUTIVE_HOLDS:
                        raise StopRun(f'{MAX_CONSECUTIVE_HOLDS} consecutive record holds') from None
                    continue
                self.outcome(sid, result)
                if result in ('drafted', 'adopted', 'published', 'updated'):
                    self.consecutive_holds = 0
                    done += 1
        except StopRun as stop:
            self.ledger['status'] = 'stopped'
            self.ledger['stops'].append({'kind': 'stop', 'reason': str(stop), 'at': self.now().isoformat()})
            self.save_ledger()
            return self.summary()
        except KeyboardInterrupt:
            self.ledger['status'] = 'interrupted'
            self.save_ledger()
            raise
        self.ledger['status'] = 'complete'
        self.save_ledger()
        return self.summary()

    def summary(self):
        counts = {}
        for value in self.ledger['outcomes'].values():
            counts[value] = counts.get(value, 0) + 1
        return {'run_id': self.run_id, 'stage': self.stage, 'status': self.ledger['status'], 'counts': counts,
                'holds': self.ledger['holds'], 'stops': [s for s in self.ledger['stops'] if s['kind'] == 'stop'],
                'requests': self.ledger['requests'], 'ledger': str(self.ledger_path())}

    # ---- reconcile (GET only)

    def reconcile(self, source_id):
        """Observe a held record by GET and move its phase to what the provider shows; never writes.

        A write whose effect the provider does not show (a lost or refused request) is allowed
        exactly one more dispatch, recorded in `allowances`; the next run sends it, never this one.
        A create whose answer was lost is resolved from fresh inventories: one unknown record with
        this wire's title is read and bound; absence counts only when two inventories, ten minutes
        apart and after the create had time to be indexed, show no unknown record at all that
        could carry it. The next run re-checks the whole barrier before re-sending.
        """
        record = load_record(self.paths, source_id)
        check(record is not None and record['hold'] is not None, 'only a held record is reconciled', Held)
        prepared = prepare_entry(self.paths, record)
        require(sha(prepared.xml) == record['source_sha256'] and sha(prepared.body) == record['wire_sha256'])
        for receipt in record['requests']:
            if receipt.get('status') == 'uncertain':
                receipt['status'] = 'unanswered'
        previous = record['hold']
        refunds = []
        if record['identity'] is None:
            phase = self.reconcile_create(record, prepared)
            if phase is None:  # absence seen once; it must be seen again later
                save_record(self.paths, record)
                return {'source_id': source_id, 'phase': record['phase'], 'held': True,
                        'absence_observations': len(record['absence']), 'allowed_again': []}
            if phase == 'creating':
                refunds = ['create']
        elif record['phase'] in UPDATING:
            target = prepare_entry(self.paths, record, wire_version=2)
            require(sha(target.body) == record['update']['wire_sha256'])
            phase, refunds = self.observe_update(record, prepared, target)
        else:
            phase = self.observe(record, prepared)
            refunds = self.refunds(record, phase)
        record['hold'] = None
        record['history'].append({'reconciled_from': previous, 'observed_phase': phase, 'allowed_again': refunds,
                                  'at': self.now().isoformat(), 'run_id': self.run_id})
        self.advance(record, phase)
        return {'source_id': source_id, 'phase': phase, 'identity': record['identity'], 'allowed_again': refunds}

    def refunds(self, record, phase):
        """Allow once more each write the observed phase shows had no effect; per file for uploads."""
        granted = []

        def grant(kind, key=None):
            per = len(files_of(record)) if kind in ('content', 'commit') else 1
            check(record['allowances'].get(kind, 0) < MAX_ALLOWANCE * per,
                  f'{kind} was already allowed again; needs a separate decision')
            record['allowances'][kind] = record['allowances'].get(kind, 0) + 1
            if key is not None:
                resend = record.setdefault('resend', {}).setdefault(kind, [])
                check(key not in resend, f'{kind} of {key} was already allowed again; needs a separate decision')
                resend.append(key)
            granted.append(kind if key is None else kind + ':' + key)

        if phase in ('created', 'initialized'):
            if phase == 'created' and record['counts']['init'] >= write_limit(record, 'init'):
                grant('init')
            done = set(record.get('uploaded', [])) if phase == 'initialized' else set()
            base = '/api/records/' + record['identity']['id'] + '/draft/files/'
            for f in files_of(record):
                if f['key'] in done:
                    continue
                for kind, suffix in (('content', '/content'), ('commit', '/commit')):
                    if any(r['kind'] == kind and r['path'] == base + f['key'] + suffix for r in record['requests']):
                        grant(kind, f['key'])
        elif phase == 'draft-verified' and record['counts']['review'] >= write_limit(record, 'review'):
            grant('review')
        return granted

    def reconcile_create(self, record, prepared):
        """Bind or clear a create whose outcome is not in the journal; None while absence is unconfirmed."""
        check(record['phase'] == 'creating' and record['counts']['create'] >= 1,
              'only a spent create without an identity is resolved here', Held)
        creates = [r for r in record['requests'] if r['kind'] == 'create']
        sent = draft.instant(creates[-1]['attempted_at'])
        if record['candidate_id'] is not None:
            return self.rebind(record, prepared, creates[-1], sent)
        self.inventory_now(force=True)
        own = own_identities(self.paths)
        known = operator.known_records(self.paths)
        title = parse(prepared.body)['metadata']['title']
        core = batch.title_key(title)
        unknown = [r for r in self.inventory['records'] if str(r.get('id')) not in own]
        titled = [str(r['id']) for r in unknown if ' '.join(str(r.get('title', '')).split()) == title
                  or batch.title_key(r.get('title', '')) == core]
        if titled:
            check(len(titled) == 1, 'several unknown records carry this title; needs a separate decision', Held)
            value = self.call(record, 'get', 'GET', '/api/records/' + titled[0] + '/draft', 200)
            record['candidate_id'] = titled[0]
            identity, _ = check_draft(value, prepared, record, self.owner, files_complete=False, bind_since=sent,
                                      foreign=self.foreign_ids(record['source_id']))
            record['identity'] = identity
            return 'created'
        check(self.now() - sent >= CREATE_SETTLE, 'the lost create is too recent to judge its absence', Held)
        hits = operator.inventory_matches(unknown, record['source_id'], title, prepared.xml, known=known)
        check(not hits, 'unknown owner records could carry this source: ' + json.dumps(hits), Held)
        latest = self.ledger['inventories'][-1]
        observation = {'inventory_sha256': latest['sha256'], 'captured_at': latest['captured_at']}
        earlier = [o for o in record['absence'] if draft.instant(o['captured_at']) >= sent + CREATE_SETTLE]
        record['absence'].append(observation)
        gap = draft.instant(observation['captured_at']) - draft.instant(earlier[0]['captured_at']) if earlier else None
        if gap is None or gap < ABSENCE_GAP:
            return None
        check(record['allowances'].get('create', 0) < MAX_ALLOWANCE,
              'create was already allowed again once; needs a separate decision', Held)
        record['allowances']['create'] = record['allowances'].get('create', 0) + 1
        return 'creating'

    def rebind(self, record, prepared, receipt, sent):
        """Bind the identity from the retained 201 body of the create, as the executor's resume route does."""
        check(receipt.get('status') == 'answered' and receipt.get('http_status') == 201
              and isinstance(receipt.get('evidence'), dict), 'the create has no retained 201 answer', Held)
        path = evidence_dir(self.paths, record['source_id']) / receipt['evidence']['filename']
        evidence, evidence_sha = draft.read_document(path)
        check(evidence_sha == receipt['evidence']['sha256'] and evidence.get('credential_suppressed') is False,
              'the retained create evidence differs', Held)
        body = gzip.decompress(base64.b64decode(evidence['body_gzip_base64'], validate=True))
        check(sha(body) == receipt['response_sha256'], 'the retained create body differs', Held)
        value = parse(body)
        check(value.get('id') == record['candidate_id'], 'the retained create names another record', Held)
        identity, _ = check_draft(value, prepared, record, self.owner, files_complete=False, bind_since=sent,
                                  foreign=self.foreign_ids(record['source_id']))
        record['identity'] = identity
        return 'created'

    def observe_update(self, record, current, target):
        """Where an interrupted in-place update stands, by GET only; the phase and the writes allowed again."""
        base = '/api/records/' + record['identity']['id']
        ids = self.community_ids or self.verify_community()
        granted = []

        def again(kind):  # a spent write whose effect the provider does not show may be sent once more
            if record['counts'][kind] >= write_limit(record, kind):
                check(record['allowances'].get(kind, 0) < MAX_ALLOWANCE,
                      f'{kind} was already allowed again; needs a separate decision')
                record['allowances'][kind] = record['allowances'].get(kind, 0) + 1
                granted.append(kind)

        try:
            opened = self.call(record, 'get', 'GET', base + '/draft', 200)
        except RecordHold:
            opened = None  # no edit draft is open (404)
        if opened is not None:
            try:
                check_edit_draft(opened, target, record, self.owner, ids, saved=True)
            except RecordHold:
                check_edit_draft(opened, current, record, self.owner, ids)
                check(record['counts']['publish'] == 0,
                      'a v1 edit draft is open after the publish was sent; needs a person')
                record['update']['carried'] = carried_of(opened)
                again('update')
                return 'edit-open', granted
            again('publish')
            return 'edit-saved', granted
        published = self.call(record, 'get', 'GET', base, 200)
        try:
            pids = check_published(published, target, record, self.owner, ids)
        except RecordHold:
            pids = check_published(published, current, record, self.owner, ids)
            check(pids == record['pids'], 'published DOI pids changed')
            check(record['counts']['update'] == 0 and record['counts']['publish'] == 0,
                  'the record is still v1 and no edit draft is open after an update was sent; needs a person')
            again('edit')
            return 'editing', granted
        check(pids == record['pids'], 'published DOI pids changed')
        return 'edit-published', granted

    def revise_draft(self, source_id, member, decided_by, note):
        """A recorded decision: put the reviewed wire into this record's existing, unpublished draft.

        For a draft made before its wire was corrected (FGDC-1939, a PICES26 draft whose keyword was
        cut). The record may be unheld, or held by the publish stage because its draft still holds the
        old wire, or held because an earlier revision's answer was lost. The draft's structure
        (identity, unpublished state, files, no community or review) is checked on a GET before the one
        PUT; the PUT answer must show the reviewed wire, public files and no validation errors. A lost
        PUT whose effect the next GET does not show is sent once more. Any failure holds the record.
        """
        record = load_record(self.paths, source_id)
        reason = (record or {}).get('hold') and record['hold'].get('reason')
        transient = re.compile(r'(get|update) (request interrupted|answered 5[0-9][0-9] )')
        check(record is not None and record['phase'] in ('adopted', 'draft-verified')
              and (reason in (None, 'provider metadata differs from the wire') or transient.match(reason or ''))
              and record['counts']['review'] == 0 and record['counts']['submit'] == 0,
              'only an unpublished, unsubmitted draft, unheld or held for its old wire, is revised', Held)
        check(all(isinstance(v, str) and v.strip() for v in (decided_by, note)), 'decider and note are required', Held)
        check(member['approved'] and member['source_id'] == source_id and member['source_sha256'] == record['source_sha256']
              and member['wire_sha256'] == record['wire_sha256'] and files_of(member) == files_of(record),
              'the review does not approve this record with its wire', Held)
        prepared = prepare_entry(self.paths, record)
        check(sha(prepared.xml) == record['source_sha256'] and sha(prepared.body) == record['wire_sha256'],
              'live preparation differs from the reviewed wire', Held)
        previous = record['hold']
        for receipt in record['requests']:
            if receipt.get('status') == 'uncertain':
                receipt['status'] = 'unanswered'
        record['hold'] = None
        base = '/api/records/' + record['identity']['id'] + '/draft'
        try:
            current = self.call(record, 'get', 'GET', base, 200)
            check_draft(current, prepared, record, self.owner, files_complete=True, compare=False)
            try:
                check_draft(current, prepared, record, self.owner, files_complete=True)
                already = True  # an earlier PUT whose answer was lost did take effect
            except RecordHold:
                already = False
            if not already:
                if record['counts']['update'] >= write_limit(record, 'update'):
                    check(previous and transient.match(previous['reason'] or '')
                          and previous['reason'].startswith('update')
                          and record['allowances'].get('update', 0) < MAX_ALLOWANCE,
                          'the draft revision was already sent; needs a separate decision')
                    record['allowances']['update'] = record['allowances'].get('update', 0) + 1
                saved = self.call(record, 'update', 'PUT', base, 200, prepared.body)
                _, revision = check_draft(saved, prepared, record, self.owner, files_complete=True)
            else:
                _, revision = check_draft(current, prepared, record, self.owner, files_complete=True)
        except (Held, StopRun) as error:
            self.hold(record, str(error))
            self.ledger['holds'].append({'source_id': source_id, 'reason': str(error), 'at': self.now().isoformat()})
            self.ledger['status'] = 'stopped'
            self.save_ledger()
            raise Held('draft revision held: ' + str(error)) from None
        record['draft_revision'] = revision
        record.setdefault('revisions', []).append({'decided_by': decided_by, 'note': note, 'at': self.now().isoformat(),
                                                   'run_id': self.run_id, 'wire_sha256': record['wire_sha256'],
                                                   'revision': revision, 'previous_hold': previous})
        self.advance(record, 'draft-verified')
        self.ledger['outcomes'][source_id] = 'revised'
        return {'source_id': source_id, 'phase': 'draft-verified', 'revision': revision}

    def rebind_update(self, source_id, member, decided_by, note):
        """A recorded decision: point a held, unpublished update at a newer reviewed v2 wire; GET only.

        For a save the provider refused in part (the 2026-10-21 canary: "Unsupported value:
        MultiPolygon"). The edit draft must still be open with this record's identity, DOIs, files and
        community, the published record must still be the v1 wire, and no publish may have been sent.
        One more save is allowed; the next update run sends it and verifies the result as usual.
        """
        record = load_record(self.paths, source_id)
        check(record is not None and record['hold'] is not None and record['phase'] == 'edit-open'
              and record['counts']['publish'] == 0, 'only a held update with an open, unpublished edit is rebound', Held)
        check(all(isinstance(v, str) and v.strip() for v in (decided_by, note)), 'decider and note are required', Held)
        check(member['approved'] and member.get('wire_version') == 2 and member['source_id'] == source_id
              and member['source_sha256'] == record['source_sha256'] and files_of(member) == files_of(record)
              and member['wire_sha256'] != record['update']['wire_sha256'],
              'the review does not approve a newer v2 wire for this record', Held)
        current = prepare_entry(self.paths, record)
        require(sha(current.xml) == record['source_sha256'] and sha(current.body) == record['wire_sha256'])
        target = prepare_entry(self.paths, record, wire_version=2)
        check(sha(target.body) == member['wire_sha256'], 'live v2 preparation differs from the reviewed sheet', Held)
        for receipt in record['requests']:
            if receipt.get('status') == 'uncertain':
                receipt['status'] = 'unanswered'
        ids = self.community_ids or self.verify_community()
        base = '/api/records/' + record['identity']['id']
        opened = self.call(record, 'get', 'GET', base + '/draft', 200)
        check_edit_draft(opened, None, record, self.owner, ids)
        pids = check_published(self.call(record, 'get', 'GET', base, 200), current, record, self.owner, ids)
        check(pids == record['pids'], 'published DOI pids changed')
        check(record['allowances'].get('update', 0) < MAX_ALLOWANCE, 'update was already allowed again', Held)
        record['allowances']['update'] = record['allowances'].get('update', 0) + 1
        update = record['update']
        update.setdefault('rebound', []).append({
            'from': {k: update[k] for k in ('wire_sha256', 'review_sha256', 'batch_id')}, 'previous_hold': record['hold'],
            'decided_by': decided_by, 'note': note, 'at': self.now().isoformat(), 'run_id': self.run_id})
        update.update(wire_sha256=member['wire_sha256'], review_sha256=member['review_sha256'],
                      batch_id=member['batch_id'], carried=carried_of(opened))
        record['hold'] = None
        self.advance(record, 'edit-open')
        return {'source_id': source_id, 'phase': 'edit-open', 'allowed_again': ['update'],
                'wire_sha256': member['wire_sha256']}

    def observe(self, record, prepared):
        base = '/api/records/' + record['identity']['id']
        keys = [f['key'] for f in files_of(record)]
        try:
            value = self.call(record, 'get', 'GET', base + '/draft', 200)
        except RecordHold:
            value = None  # a published record without an open draft answers 404 here
        if value is None or value.get('is_published') is True:
            ids = self.community_ids or self.verify_community()
            record['pids'] = check_published(self.call(record, 'get', 'GET', base, 200), prepared, record,
                                             self.owner, ids)
            return 'published'
        status = value.get('status')
        check(status in ('draft', 'draft_with_review'),
              f'draft status {status}: the submission awaits community action; inspect it on Zenodo')
        files = value.get('files', {})
        entries = files.get('entries') if isinstance(files.get('entries'), dict) else {}
        pending = frozenset()
        if status == 'draft':
            # An initialized file whose content never arrived (FGDC-759: the PUT answered 502) stays listed
            # without a checksum. It is not uploaded; the file listing below says which files completed.
            pending = frozenset(k for k in keys if isinstance(entries.get(k), dict) and not entries[k].get('checksum'))
        listed = set(entries) - pending
        complete = set(keys) <= listed
        check_draft(value, prepared, record, self.owner, files_complete=True if complete else
                    ('partial' if listed else False),
                    status='draft_with_review' if status == 'draft_with_review' else 'draft', pending=pending)
        if status == 'draft_with_review':
            review = value.get('parent', {}).get('review', {})
            check(review.get('receiver') == {'community': PICES_COMMUNITY}, 'review targets another community')
            check(record['counts']['submit'] == 0,
                  'a submission was sent while the review is still open; inspect the request first')
            record['request_id'] = review.get('id', record.get('request_id'))
            return 'review-set'
        if complete:
            return 'draft-verified'
        listing = self.call(record, 'get', 'GET', base + '/draft/files', 200)
        entries = listing.get('entries') if isinstance(listing.get('entries'), list) else []
        present = {e.get('key'): e.get('status') for e in entries if isinstance(e, dict)}
        if not present:
            return 'created'
        check(set(present) == set(keys), 'only some files were initialized; needs a separate decision')
        record['uploaded'] = [k for k in keys if present[k] == 'completed']
        return 'initialized'


# ---------------------------------------------------------------- release

def releasable(record, member, action):
    """Whether a release of this action may name the record for this approved member."""
    if record is None or record['hold'] is not None or record['source_sha256'] != member['source_sha256']:
        return False
    if action == 'publish':
        return (record['phase'] in ('draft-verified', 'adopted', 'review-set', 'accepted')
                and record['wire_sha256'] == member['wire_sha256'])
    return (member.get('wire_version') == 2 and record.get('wire_version', 1) == 1
            and (record['phase'] == 'published'
                 or (record['phase'] in UPDATING and record['update']['wire_sha256'] == member['wire_sha256'])))


def build_release(paths, reviews, *, authority, instruction, instructed_at, prepared_by, now=utc_now,
                  action='publish', only=None):
    """Name every approved, unheld record of the given reviews for publication, or for its v2 update."""
    check(all(isinstance(v, str) and v.strip() for v in (authority, instruction, instructed_at, prepared_by)),
          'authority, instruction, its date and the preparer are required', Held)
    check(action in ('publish', 'update'), 'a release publishes drafts or updates published records', Held)
    listed, records = [], []
    for path in reviews:
        review, review_sha, order, members = load_review(paths, path)
        listed.append({'path': str(Path(path).resolve()), 'sha256': review_sha, 'batch_id': review['batch_id']})
        for sid in order:
            if (members[sid]['approved'] and (only is None or sid in only)
                    and releasable(load_record(paths, sid), members[sid], action)):
                records.append(sid)
    check(only is None or set(only) <= set(records), 'a named record is not releasable for this action', Held)
    check(records and len(set(records)) == len(records), 'the release would name no record', Held)
    return {'schema_version': 1, 'kind': RELEASE_KIND, 'action': action, 'authority': authority,
            'authority_type': 'human', 'instruction': instruction, 'instructed_at': instructed_at,
            'prepared_by': prepared_by, 'prepared_at': now().isoformat(), 'community': PICES_COMMUNITY,
            'reviews': listed, 'record_count': len(records), 'records': records}


def load_release(paths, path, action='publish'):
    """A release of this action (releases written before updates existed publish) and its approved members."""
    release, release_sha = draft.read_document(path)
    require(isinstance(release, dict) and release.get('kind') == RELEASE_KIND and release.get('schema_version') == 1
            and release.get('action', 'publish') == action
            and release.get('authority_type') == 'human' and release.get('community') == PICES_COMMUNITY
            and all(isinstance(release.get(k), str) and release[k].strip()
                    for k in ('authority', 'instruction', 'instructed_at', 'prepared_by'))
            and isinstance(release.get('records'), list) and release['record_count'] == len(release['records']))
    approved = {}
    for entry in release['reviews']:
        review, review_sha, order, members = load_review(paths, entry['path'])
        require(review_sha == entry['sha256'])
        for sid in order:
            if members[sid]['approved']:
                require(sid not in approved)
                approved[sid] = members[sid]
    require(set(release['records']) <= set(approved) and len(set(release['records'])) == len(release['records']))
    release_members = {sid: approved[sid] for sid in release['records']}
    return release, release_sha, release_members


def exclusions(paths):
    """Source id to its reviewed exclusion (a duplicate in the source collection, or another reason)."""
    directory = bulk_root(paths) / 'exclusions'
    found = {}
    if directory.is_dir():
        for path in sorted(directory.glob('FGDC-*.json'), key=lambda p: batch.by_number(p.stem)):
            document, _ = draft.read_document(path)
            require(isinstance(document, dict) and document.get('kind') == EXCLUSION_KIND
                    and document.get('source_id') == path.stem)
            found[path.stem] = document
        for path in sorted((directory / 'lifted').glob('FGDC-*.json')):
            lift, _ = draft.read_document(path)
            _, exclusion_sha = draft.read_document(directory / (path.stem + '.json'))
            require(isinstance(lift, dict) and lift.get('kind') == EXCLUSION_LIFT_KIND
                    and lift.get('source_id') == path.stem and lift.get('exclusion_sha256') == exclusion_sha)
            found.pop(path.stem, None)
    return found


def inventory_hits_in(paths, inventory, prepared, allowed=(), source_id=None):
    """Unknown owner records of an inventory that may carry this source; `allowed` are reviewed false matches."""
    own = own_identities(paths) | {str(i) for i in allowed}
    records = [r for r in inventory['records'] if str(r.get('id')) not in own]
    known = operator.known_records(paths)
    title = parse(prepared.body)['metadata']['title']
    hits = operator.inventory_matches(records, source_id or prepared.source_id, title, prepared.xml, known=known)
    core = batch.title_key(title)
    for r in records:
        if batch.title_key(r.get('title', '')) == core and not any(h['id'] == r.get('id') for h in hits):
            hits.append({'id': r.get('id'), 'reasons': ['core_title']})
    return hits


def legacy_paths(paths, source_id):
    require(re.fullmatch(batch.SOURCE_ID, source_id) is not None)
    return (draft.state_root(paths) / (source_id + '.modern-create-v1.intent.json'),
            bulk_root(paths) / 'legacy-releases' / (source_id + '.json'))


def legacy_released(paths, source_id):
    """Whether a recorded release covers this source's unfinished single-record claim exactly as it stands."""
    intent, path = legacy_paths(paths, source_id)
    if not path.exists():
        return False
    release, _ = draft.read_document(path)
    journal_path = Path(paths.uploads_registry_path + '.modern-v1.json')
    journal, _ = draft.read_document(journal_path)
    row = journal.get('targets', {}).get(source_id)
    require(isinstance(release, dict) and release.get('kind') == LEGACY_RELEASE_KIND
            and release.get('source_id') == source_id and isinstance(row, dict)
            and release.get('row_sha256') == sha(encode(row))
            and release.get('intent_sha256') == (sha(intent.read_bytes()) if intent.exists() else None))
    return True


def release_legacy_claim(paths, source_id, inventory_path, decided_by, authority, reason, now=utc_now):
    """Record that an unfinished single-record create left no record, so the bulk route may create the source.

    Only a create the single-record chain never bound (phase `started`, no identity, no draft
    steps) is released, and only when a recent owner inventory holds no unknown record that could
    carry the source. The single-record row and intent stay as they are; the release binds their
    hashes. The bulk route still runs its whole barrier, on a fresh inventory, before its create.
    """
    check(all(isinstance(v, str) and v.strip() for v in (decided_by, authority, reason)),
          'decider, authority and reason are required', Held)
    intent, path = legacy_paths(paths, source_id)
    journal, _ = draft.read_document(Path(paths.uploads_registry_path + '.modern-v1.json'))
    row = journal.get('targets', {}).get(source_id)
    check(isinstance(row, dict), 'no single-record row for this source', Held)
    answers = [r.get('http_status') for r in row.get('requests', []) if r.get('kind') == 'create']
    check(row.get('phase') == 'started' and row.get('identity') is None
          and row.get('untrusted_candidate_id') is None and row.get('resume_grant_sha256') is None
          and all(row.get('counts', {}).get(k, 0) == 0 for k in ('init', 'content', 'commit'))
          and not any(isinstance(a, int) and 200 <= a < 300 for a in answers),
          'only an unbound single-record create with no candidate and no 2xx answer is released', Held)
    source = Path(inventory_path)  # an owner inventory exceeds the 1 MiB document bound; the runner's own bound applies
    check(source.is_file() and not source.is_symlink() and source.stat().st_size <= INVENTORY_MAX_BYTES,
          'the inventory file is missing or too large', Held)
    raw = source.read_bytes()
    inventory, inventory_sha = parse(raw), sha(raw)
    check(isinstance(inventory, dict) and inventory.get('kind') == operator.INVENTORY_KIND
          and inventory.get('complete') is True
          and now() - draft.instant(inventory['captured_at']) <= LEGACY_RELEASE_FRESHNESS,
          'a complete owner inventory from the last 24 hours is required', Held)
    owners = {str(r.get('owner')) for r in inventory['records']}
    check(len(owners) <= 1, 'the inventory lists records of more than one owner', Held)
    hits = []
    for prepared in (member_now(paths, source_id), prepare_entry(paths, {'source_id': source_id}, 2)):
        hits += [h for h in inventory_hits_in(paths, inventory, prepared) if h not in hits]
    check(not hits, 'the owner inventory may already carry this source: ' + json.dumps(hits), Held)
    document = {'schema_version': 1, 'kind': LEGACY_RELEASE_KIND, 'source_id': source_id,
                'row_sha256': sha(encode(row)), 'row_phase': row['phase'], 'create_answers': answers,
                'untrusted_candidate_id': None,
                'intent_sha256': sha(intent.read_bytes()) if intent.exists() else None,
                'inventory': {'path': str(Path(inventory_path).resolve()), 'sha256': inventory_sha,
                              'captured_at': inventory['captured_at'], 'record_count': inventory['record_count'],
                              'owners': sorted(owners), 'hits': []},
                'decided_by': decided_by, 'authority': authority, 'reason': reason, 'decided_at': now().isoformat()}
    return write_exclusive(path, document)


def lift_exclusion(paths, source_id, decided_by, reason, now=utc_now):
    """Record that an exclusion no longer applies because its cause was repaired; the exclusion itself stays."""
    path = bulk_root(paths) / 'exclusions' / (source_id + '.json')
    check(re.fullmatch(batch.SOURCE_ID, source_id) is not None and path.exists(), 'no exclusion for this source', Held)
    check(all(isinstance(v, str) and v.strip() for v in (decided_by, reason)), 'decider and reason are required', Held)
    exclusion, exclusion_sha = draft.read_document(path)
    check(str(exclusion.get('reason', '')).startswith('held for source-text repair'),
          'only an exclusion held for source-text repair is lifted; a duplicate stays excluded', Held)
    document = {'schema_version': 1, 'kind': EXCLUSION_LIFT_KIND, 'source_id': source_id,
                'exclusion_sha256': exclusion_sha, 'exclusion_reason': exclusion.get('reason'),
                'reason': reason, 'decided_by': decided_by, 'decided_at': now().isoformat()}
    return write_exclusive(bulk_root(paths) / 'exclusions' / 'lifted' / (source_id + '.json'), document)


def exclude(paths, source_id, reason, decided_by, now=utc_now):
    """Record, once and for good, that a source is not published by this route."""
    check(re.fullmatch(batch.SOURCE_ID, source_id) is not None
          and all(isinstance(v, str) and v.strip() for v in (reason, decided_by)), 'source, reason and decider', Held)
    record = load_record(paths, source_id)
    check(record is None or (record['phase'] == 'planned' and not record['requests']),
          'a source that reached the provider cannot be excluded here', Held)
    document = {'schema_version': 1, 'kind': EXCLUSION_KIND, 'source_id': source_id, 'reason': reason,
                'decided_by': decided_by, 'decided_at': now().isoformat()}
    return write_exclusive(bulk_root(paths) / 'exclusions' / (source_id + '.json'), document)


def unhold(paths, source_id, decided_by, note, allow_inventory=(), now=utc_now):
    """Release a barrier hold on a record that never reached the provider; the next run re-checks it.

    `allow_inventory` names owner records a reviewer found to be false inventory matches for
    this source; the barrier ignores exactly those ids for this source from now on.
    """
    record = load_record(paths, source_id)
    check(record is not None and record['hold'] is not None and record['phase'] == 'planned'
          and not record['requests'] and not intent_path(paths, source_id).exists(),
          'only a held record with no provider request can be released', Held)
    check(all(isinstance(v, str) and v.strip() for v in (decided_by, note)), 'decider and note are required', Held)
    allow = sorted({str(i) for i in allow_inventory})
    check(all(re.fullmatch('[1-9][0-9]{0,19}', i) for i in allow), 'record ids are decimal strings', Held)
    record['inventory_allowed'] = sorted(set(record.get('inventory_allowed', [])) | set(allow))
    record['history'].append({'phase': 'planned', 'at': now().isoformat(), 'unheld_by': decided_by,
                              'note': note, 'previous_hold': record['hold'], 'inventory_allowed': allow})
    record['hold'] = None
    save_record(paths, record)
    return {'source_id': source_id, 'unheld': True}


# ---------------------------------------------------------------- reports

def status(paths):
    rows = batch.bulk_rows(paths)
    phases, holds = {}, []
    for sid, record in rows.items():
        key = 'held' if record['hold'] else record['phase']
        phases[key] = phases.get(key, 0) + 1
        if record['hold']:
            holds.append({'source_id': sid, 'phase': record['phase'], 'reason': record['hold']['reason']})
    return {'records': len(rows), 'phases': phases, 'holds': sorted(holds, key=lambda h: batch.by_number(h['source_id']))}


def candidates(paths):
    """Sources that prepare today and are not yet in any journal, in source order."""
    taken = set(batch.journal_phases(paths)) | set(PROTECTED) | set(exclusions(paths))
    ids = []
    for path in sorted(Path(paths.zenodo_json_dir).glob('FGDC-*.json'), key=lambda p: batch.by_number(p.stem)):
        if path.stem in taken:
            continue
        try:
            member_now(paths, path.stem)
        except Exception:
            continue
        ids.append(path.stem)
    return ids


# ---------------------------------------------------------------- command line

def transport_and_token(stage, keychain):
    """Every stage may read the Keychain item; publication and updates prompt when none is given."""
    if stage in ('publish', 'update'):
        token = draft.production_token(f'Zenodo production token ({stage}): ', keychain,
                                       action=('bulk-' + stage) if keychain else 'publish')
    else:
        token = draft.production_token('Zenodo production token: ', keychain, action='execute')
    return draft.Transport(token), token


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='action', required=True)
    plan = sub.add_parser('plan', help='Build a batch manifest and its review sheet offline')
    plan.add_argument('--batch-id', required=True)
    plan.add_argument('--owner', required=True)
    plan.add_argument('--built-by', required=True)
    plan.add_argument('--member', action='append', default=[])
    plan.add_argument('--members-file')
    plan.add_argument('--exclude', action='append', default=[], metavar='FGDC-N:reason')
    review = sub.add_parser('review', help="Record the reviewer's decisions for a sheet")
    review.add_argument('--batch-id', required=True)
    review.add_argument('--decisions', required=True, help='JSON: {"decisions": {...}, "examined": [...], "summary": "..."}')
    review.add_argument('--reviewer', required=True)
    drafts = sub.add_parser('drafts', help='Create and verify drafts for the approved members of a review')
    drafts.add_argument('--review', required=True)
    drafts.add_argument('--owner', required=True)
    drafts.add_argument('--captured-by', required=True)
    drafts.add_argument('--token-keychain', metavar='SERVICE', help=draft.KEYCHAIN_HELP)
    drafts.add_argument('--limit', type=int)
    release = sub.add_parser('release', help='Name the drafted, approved records a publish run may publish')
    release.add_argument('--review', action='append', required=True)
    release.add_argument('--name', required=True)
    release.add_argument('--authority', required=True)
    release.add_argument('--instruction', required=True)
    release.add_argument('--instructed-at', required=True)
    release.add_argument('--prepared-by', required=True)
    release.add_argument('--action', dest='release_action', choices=('publish', 'update'), default='publish')
    release.add_argument('--only', action='append', metavar='FGDC-N',
                         help='Name only these records (each must be releasable), e.g. for a canary')
    publish = sub.add_parser('publish', help='Publish the records of a release into the PICES community')
    publish.add_argument('--release', required=True)
    publish.add_argument('--owner', required=True)
    publish.add_argument('--limit', type=int)
    publish.add_argument('--token-keychain', metavar='SERVICE',
                         help='Read the token from this Keychain item (allowed by Brett on 2026-10-20); prompts otherwise')
    update = sub.add_parser('update', help='Edit the published records of an update release to their v2 wire')
    update.add_argument('--release', required=True)
    update.add_argument('--owner', required=True)
    update.add_argument('--limit', type=int)
    update.add_argument('--token-keychain', metavar='SERVICE',
                        help='Read the token from this Keychain item; prompts otherwise')
    revise = sub.add_parser('revise-draft', help='Put the reviewed wire into an existing unpublished draft (one PUT)')
    revise.add_argument('--source', required=True)
    revise.add_argument('--review', required=True, help='The review that approves the wire the record is bound to')
    revise.add_argument('--owner', required=True)
    revise.add_argument('--decided-by', required=True)
    revise.add_argument('--note', required=True)
    revise.add_argument('--token-keychain', metavar='SERVICE', help=draft.KEYCHAIN_HELP)
    legacy = sub.add_parser('release-legacy', help='Record that an unbound single-record create left no record (offline)')
    legacy.add_argument('--source', required=True)
    legacy.add_argument('--inventory', required=True, help='A complete owner inventory captured in the last 24 hours')
    legacy.add_argument('--decided-by', required=True)
    legacy.add_argument('--authority', required=True)
    legacy.add_argument('--reason', required=True)
    lift = sub.add_parser('lift-exclusion', help='Record that a repaired exclusion no longer applies (offline)')
    lift.add_argument('--source', required=True)
    lift.add_argument('--decided-by', required=True)
    lift.add_argument('--reason', required=True)
    rebind = sub.add_parser('rebind-update', help='Point a held, unpublished update at a newer reviewed v2 wire (GET only)')
    rebind.add_argument('--source', required=True)
    rebind.add_argument('--review', required=True, help='The v2 review that approves the newer wire')
    rebind.add_argument('--owner', required=True)
    rebind.add_argument('--decided-by', required=True)
    rebind.add_argument('--note', required=True)
    rebind.add_argument('--token-keychain', metavar='SERVICE', help=draft.KEYCHAIN_HELP)
    plan_v2 = sub.add_parser('plan-v2', help='Build the v2 review sheet for the approved members of a v1 review')
    plan_v2.add_argument('--base-review', required=True)
    plan_v2.add_argument('--built-by', required=True)
    plan_v2.add_argument('--suffix', default='v2', help='v2, or v2b, v2c ... when an earlier v2 sheet of the batch was superseded')
    reconcile = sub.add_parser('reconcile', help='Observe held records by GET and move their phase')
    reconcile.add_argument('--source', action='append', required=True)
    reconcile.add_argument('--owner', required=True)
    reconcile.add_argument('--token-keychain', metavar='SERVICE', help=draft.KEYCHAIN_HELP)
    pairs = sub.add_parser('plan-pairs', help='Build the review sheet for reviewed two-file pair targets offline')
    pairs.add_argument('--batch-id', required=True)
    pairs.add_argument('--built-by', required=True)
    pairs.add_argument('--targets-file', required=True, help='JSON list of pair record_target_ids (sha256:...)')
    pairs.add_argument('--reviewed-at', required=True, help='Fixed past assessment time; the wire depends on it')
    release_hold = sub.add_parser('unhold', help='Release a barrier hold on a record with no provider request')
    release_hold.add_argument('--source', required=True)
    release_hold.add_argument('--decided-by', required=True)
    release_hold.add_argument('--note', required=True)
    release_hold.add_argument('--allow-inventory-record', action='append', default=[],
                              help='Owner record id reviewed as a false inventory match for this source')
    excluded = sub.add_parser('exclude', help='Record a reviewed decision not to publish a source')
    excluded.add_argument('--source', required=True)
    excluded.add_argument('--reason', required=True)
    excluded.add_argument('--decided-by', required=True)
    sub.add_parser('status', help='Count records by phase and list holds')
    sub.add_parser('candidates', help='List sources that prepare and are in no journal')
    for child in sub.choices.values():
        child.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    try:
        paths = OutputPaths(args.output_dir, 'production')
        if args.action == 'plan':
            ids = list(args.member) + (batch.members_from_file(args.members_file) if args.members_file else [])
            manifest = batch.build_manifest(paths, ids, batch_id=args.batch_id, owner=args.owner,
                                            built_by=args.built_by,
                                            exclusions=[batch.parse_exclusion(v) for v in args.exclude])
            manifest_file = batch.write_manifest(paths, manifest)
            sheet = build_sheet(paths, manifest, sha(manifest_file.read_bytes()), args.built_by)
            path = write_exclusive(sheet_path(paths, args.batch_id), sheet)
            result = {'manifest': str(manifest_file), 'sheet': str(path), 'sheet_sha256': sha(path.read_bytes()),
                      'members': sheet['member_count'], 'flagged': len(sheet['flagged']),
                      'sample': len(sheet['sample']), 'twins': manifest['twins'], 'provider_requests': 0}
        elif args.action == 'plan-pairs':
            targets, _ = draft.read_document(args.targets_file)
            require(isinstance(targets, list) and all(isinstance(v, str) for v in targets))
            sheet = build_pair_sheet(paths, args.batch_id, targets, args.built_by, args.reviewed_at)
            path = write_exclusive(sheet_path(paths, args.batch_id), sheet)
            result = {'sheet': str(path), 'sheet_sha256': sha(path.read_bytes()), 'members': sheet['member_count'],
                      'flagged': len(sheet['flagged']), 'sample': len(sheet['sample']), 'twins': sheet['twins'],
                      'provider_requests': 0}
        elif args.action == 'plan-v2':
            sheet = build_v2_sheet(paths, args.base_review, args.built_by, suffix=args.suffix)
            path = write_exclusive(sheet_path(paths, sheet['batch_id']), sheet)
            result = {'sheet': str(path), 'sheet_sha256': sha(path.read_bytes()), 'batch_id': sheet['batch_id'],
                      'members': sheet['member_count'], 'flagged': len(sheet['flagged']),
                      'sample': len(sheet['sample']), 'skipped': sheet['skipped'], 'provider_requests': 0}
        elif args.action == 'review':
            sheet, sheet_sha = draft.read_document(sheet_path(paths, args.batch_id))
            given, _ = draft.read_document(args.decisions)
            document = build_review(sheet, sheet_sha, given['decisions'], args.reviewer, given['examined'],
                                    given.get('summary', ''))
            path = write_exclusive(review_path(paths, args.batch_id), document)
            approved = sum(v['decision'] == 'approved' for v in document['decisions'].values())
            result = {'review': str(path), 'review_sha256': sha(path.read_bytes()), 'approved': approved,
                      'held': len(document['decisions']) - approved, 'provider_requests': 0}
        elif args.action == 'release':
            document = build_release(paths, args.review, authority=args.authority, instruction=args.instruction,
                                     instructed_at=args.instructed_at, prepared_by=args.prepared_by,
                                     action=args.release_action, only=args.only)
            require(re.fullmatch(batch.BATCH_ID, args.name) is not None)
            path = write_exclusive(bulk_root(paths) / 'releases' / (args.name + '.json'), document)
            result = {'release': str(path), 'release_sha256': sha(path.read_bytes()), 'action': document['action'],
                      'records': document['record_count'], 'provider_requests': 0}
        elif args.action == 'unhold':
            with ledger_lock(paths):
                result = unhold(paths, args.source, args.decided_by, args.note, args.allow_inventory_record)
        elif args.action == 'exclude':
            with ledger_lock(paths):
                path = exclude(paths, args.source, args.reason, args.decided_by)
            result = {'exclusion': str(path), 'provider_requests': 0}
        elif args.action == 'status':
            result = status(paths)
        elif args.action == 'candidates':
            ids = candidates(paths)
            result = {'count': len(ids), 'candidates': ids}
        elif args.action == 'drafts':
            _, review_sha, order, members = load_review(paths, args.review)
            approved = [members[sid] for sid in order if members[sid]['approved']]
            require(approved)
            transport, token = transport_and_token('drafts', args.token_keychain)
            with ledger_lock(paths):
                pending = [m['source_id'] for m in approved
                           if (load_record(paths, m['source_id']) or {}).get('phase') not in DRAFTED + UPDATING]
                runner = Bulk(paths, transport, token, owner=args.owner, stage='drafts',
                              captured_by=args.captured_by)
                pairs = [m for m in approved if m.get('target')]
                require(not pairs or len(pairs) == len(approved))
                if pending and pairs:
                    rows = [{'source_id': m['source_id'], 'source_sha256': m['source_sha256'], 'target': m['target'],
                             'wire': {'title': parse(prepare_entry(paths, m).body)['metadata']['title']}}
                            for m in pairs if m['source_id'] in pending]
                    twins, used = pair_twins(paths, rows)
                    runner.ledger['inputs'] = {'review_sha256': review_sha, 'pair_twins': twins,
                                               'allowances': [a['origin'] for a in used]}
                elif pending:
                    manifest = batch.build_manifest(paths, pending, batch_id=(members[order[0]]['batch_id'] + '-'
                                                    + stamp(utc_now()))[:64].rstrip('-'),
                                                    owner=args.owner, built_by=args.captured_by)
                    manifest_file = batch.write_manifest(paths, manifest)
                    runner.ledger['inputs'] = {'review_sha256': review_sha, 'manifest': str(manifest_file),
                                               'manifest_sha256': sha(manifest_file.read_bytes())}
                result = runner.run(approved, runner.draft_member, limit=args.limit)
        elif args.action == 'release-legacy':
            with ledger_lock(paths):
                path = release_legacy_claim(paths, args.source, args.inventory, args.decided_by, args.authority,
                                            args.reason)
            result = {'release': str(path), 'provider_requests': 0}
        elif args.action == 'lift-exclusion':
            with ledger_lock(paths):
                path = lift_exclusion(paths, args.source, args.decided_by, args.reason)
            result = {'lift': str(path), 'provider_requests': 0}
        elif args.action == 'revise-draft':
            _, _, _, members = load_review(paths, args.review)
            require(args.source in members)
            transport, token = transport_and_token('drafts', args.token_keychain)
            with ledger_lock(paths):
                runner = Bulk(paths, transport, token, owner=args.owner, stage='drafts')
                result = runner.revise_draft(args.source, members[args.source], args.decided_by, args.note)
                runner.ledger['status'] = 'complete'
                runner.save_ledger()
        elif args.action == 'rebind-update':
            _, _, _, members = load_review(paths, args.review)
            require(args.source in members)
            transport, token = transport_and_token('reconcile', args.token_keychain)
            with ledger_lock(paths):
                runner = Bulk(paths, transport, token, owner=args.owner, stage='reconcile')
                result = runner.rebind_update(args.source, members[args.source], args.decided_by, args.note)
                runner.ledger['status'] = 'complete'
                runner.save_ledger()
        elif args.action == 'update':
            release, release_sha, members = load_release(paths, args.release, 'update')
            transport, token = transport_and_token('update', args.token_keychain)
            with ledger_lock(paths):
                runner = Bulk(paths, transport, token, owner=args.owner, stage='update')
                runner.ledger['inputs'] = {'release': str(Path(args.release).resolve()), 'release_sha256': release_sha}
                result = runner.run(release['records'],
                                    lambda sid: runner.update_member(sid, release_sha, members[sid]),
                                    limit=args.limit)
        elif args.action == 'publish':
            release, release_sha, _ = load_release(paths, args.release)
            transport, token = transport_and_token('publish', args.token_keychain)
            with ledger_lock(paths):
                runner = Bulk(paths, transport, token, owner=args.owner, stage='publish')
                runner.ledger['inputs'] = {'release': str(Path(args.release).resolve()), 'release_sha256': release_sha}
                result = runner.run(release['records'], lambda sid: runner.publish_member(sid, release_sha),
                                    limit=args.limit)
        else:
            transport, token = transport_and_token('reconcile', args.token_keychain)
            with ledger_lock(paths):
                runner = Bulk(paths, transport, token, owner=args.owner, stage='reconcile')
                result = {'reconciled': [runner.reconcile(sid) for sid in args.source]}
                runner.ledger['status'] = 'complete'
                runner.save_ledger()
        print(json.dumps(result, indent=1, sort_keys=True))
        return 0
    except Held as held:
        print(json.dumps({'held': True, 'reason': str(held)}))
        return 1
    except FileExistsError:
        print(json.dumps({'held': True, 'reason': 'a document with that name already exists; nothing was replaced'}))
        return 1
    except ValueError as error:  # closed holds of the preparation and operation guards
        print(json.dumps({'held': True, 'reason': str(error)[:300]}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
