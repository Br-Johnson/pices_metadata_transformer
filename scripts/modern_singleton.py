"""Finite source-aware modern mapping; no provider or publication authority.

Only the reviewed 19 NCDC/NESDIS/NOAA singleton XML artifacts are supported.
Every preparation reruns semantic assessment and preserves assembled legacy
metadata separately from the explicitly selected repository-host publisher.
"""

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from scripts.agent_qa import assess_source
from scripts.content_class_targets import require_singleton_operation
from scripts.modern_draft_schema import SCHEMA_FILES, SCHEMAS
from scripts.production_mutations import PROTECTED
from scripts.rehosting_authority import validate_restricted_metadata

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'docs/readiness/2026-10-04/source_citation_credits_426.json'
PROFILE_SHA = '15c654dc714849327b827363071a1da3ad7c3fa20c2c95a990d7868e75e96bd2'
PLAN = ROOT / 'docs/readiness/2026-10-04/publication_plan.json'
PLAN_SHA = '39d2894d518fa5a10d87cc784ce40064e6757529f23219eea153f25805f506ad'
COHORT = 'ncdc_nesdis_noaa_literal_19'
POLICY = 'modern-xml-ncdc19-v1'
PRESERVATION_LABEL = (
    'Legacy assembled metadata, preserved without field loss. Publisher values in this '
    'block are legacy mapping values, not independently source-attested publishers. '
    'The current publisher Zenodo identifies the repository hosting this restored XML '
    'artifact. Its publication date is the approved source metadata date, not the date '
    'of hosting on Zenodo. Underlying dataset citation and access conditions remain '
    'source evidence; no new license is granted.'
)


class Held(ValueError):
    """Closed diagnostic; never expose transport errors or provider text."""


def require(condition):
    if not condition:
        raise Held('Modern singleton held; preserve evidence and spent attempts')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: require(False))


def pinned(path, digest):
    raw = path.read_bytes()
    require(sha(raw) == digest)
    return parse(raw)


def cohort():
    rows = [row for row in pinned(PROFILE, PROFILE_SHA)['cohorts'] if row['profile'] == COHORT]
    require(len(rows) == 1 and len(rows[0]['members']) == 19)
    return rows[0]


def runtime_binding():
    # Include indirect transformation, authority, identity and transport helpers.
    return sha(encode({p.name: sha(p.read_bytes()) for p in sorted((ROOT / 'scripts').glob('*.py'))}))


def validate_payload(payload):
    registry = Registry()
    for name, (uri, digest) in SCHEMA_FILES.items():
        registry = registry.with_resource(uri, Resource(pinned(SCHEMAS / name, digest), DRAFT7))
    validator = Draft7Validator({'$ref': 'local://records/record-v6.0.0.json'}, registry=registry)
    require(validator.is_valid(payload))
    # Service schema requirements and finite policy supplement the permissive storage schema.
    require(set(payload) == {'metadata', 'access', 'files'}
            and payload['access'] == {'record': 'public', 'files': 'restricted'}
            and payload['files'] == {'enabled': True})
    meta = payload['metadata']
    require(set(meta) == {'resource_type', 'creators', 'title', 'publication_date', 'publisher',
                         'description', 'subjects', 'additional_descriptions'}
            and meta['resource_type'] == {'id': 'other'} and meta['publisher'] == 'Zenodo'
            and all(isinstance(meta[key], str) and meta[key] for key in
                    ('title', 'description', 'publication_date')))


@dataclass(frozen=True)
class Prepared:
    source_id: str
    body: bytes
    xml: bytes
    evidence: dict
    binding: str


def prepare(json_file, paths):
    """Fresh semantic assessment, exact original and independently pinned cohort.

    Prepared input retains its existing artifact/authority profiles. Changing it,
    its paths, any policy, a schema, or runtime invalidates the execution binding.
    """
    json_file = Path(json_file)
    sid = json_file.stem
    require(re.fullmatch(r'FGDC-[1-9][0-9]*', sid) is not None and sid not in PROTECTED)
    require_singleton_operation(source_id=sid, json_file=json_file, paths=paths)
    selected = cohort()
    members = {row['source_id']: row['source_sha256'] for row in selected['members']}
    require(sid in members)
    raw_input = json_file.read_bytes()
    payload = parse(raw_input)
    reference = payload.get('artifact_policy', {}).get('creator_interpretation', {})
    require(reference.get('manifest_sha256') == PROFILE_SHA)
    metadata, source_sha, artifact, _ = assess_source(json_file, paths)
    xml = (ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
    require(source_sha == sha(xml) == members[sid] and artifact is not None
            and artifact['source_id'] == sid and len(artifact['files']) == 1
            and artifact['files'][0]['sha256'] == source_sha)
    target = next(row for row in pinned(PLAN, PLAN_SHA)['targets'] if row['record_target_id'] == sid)
    require(target['source_ids'] == [sid] and target['source_semantic_status'] == 'supported'
            and target['source_sha256'] == source_sha
            and target['identity_decision']['production_record_id'] is None
            and target['identity_decision']['production_doi'] is None)
    validate_restricted_metadata(metadata)
    require(metadata['creators'] == selected['creators']
            and all(set(c) == {'name', 'type'} and c['type'] == 'Organization'
                    for c in selected['creators']))
    keywords = metadata.get('keywords', [])
    require(isinstance(keywords, list) and all(isinstance(k, str) and k.strip() for k in keywords))
    legacy = encode(metadata)
    preservation = '<p>' + PRESERVATION_LABEL + '</p><pre>' + html.escape(legacy.decode()) + '</pre>'
    wire = {'metadata': {
        'resource_type': {'id': 'other'}, 'title': metadata['title'],
        'creators': [{'person_or_org': {'name': c['name'], 'type': 'organizational'}}
                     for c in metadata['creators']],
        'publication_date': metadata['publication_date'], 'publisher': 'Zenodo',
        'description': metadata['description'], 'subjects': [{'subject': k} for k in keywords],
        'additional_descriptions': [{'type': {'id': 'other'}, 'description': preservation}],
    }, 'access': {'record': 'public', 'files': 'restricted'}, 'files': {'enabled': True}}
    validate_payload(wire)
    body = encode(wire)
    evidence = {'schema_version': 1, 'policy': POLICY, 'source_id': sid,
                'source_sha256': source_sha, 'prepared_input_sha256': sha(raw_input),
                'legacy_metadata_sha256': sha(legacy), 'wire_sha256': sha(body),
                'artifact_contract': artifact, 'creator_profile_sha256': PROFILE_SHA,
                'source_plan_sha256': PLAN_SHA, 'runtime_sha256': runtime_binding(),
                'schema_sha256': {name: digest for name, (_, digest) in SCHEMA_FILES.items()}}
    return Prepared(sid, body, xml, evidence, sha(encode(evidence)))


def compare_metadata(actual, expected):
    """Accept only known empty defaults and vocabulary display labels; no HTML repair."""
    require(isinstance(actual, dict))
    defaults = {'dates', 'contributors', 'rights', 'identifiers', 'related_identifiers',
                'additional_titles', 'languages', 'locations', 'funding', 'references',
                'version', 'sizes', 'formats'}
    require(set(actual) <= set(expected) | defaults)
    require(all(actual[k] in (None, '', [], {}) for k in set(actual) - set(expected)))
    for key in ('title', 'publisher', 'publication_date', 'description', 'subjects'):
        require(actual.get(key) == expected[key])
    def vocabulary(value, wanted):
        require(isinstance(value, dict) and value.get('id') == wanted['id']
                and set(value) <= {'id', 'title'})
    vocabulary(actual.get('resource_type'), expected['resource_type'])
    creators = actual.get('creators')
    require(isinstance(creators, list) and len(creators) == len(expected['creators']))
    for value, wanted in zip(creators, expected['creators'], strict=True):
        require(isinstance(value, dict) and set(value) <= {'person_or_org', 'affiliations', 'role'}
                and value.get('affiliations') in (None, []) and value.get('role') in (None, {}))
        person = value.get('person_or_org')
        require(isinstance(person, dict) and set(person) <= {'name', 'type', 'identifiers'}
                and person.get('identifiers') in (None, [])
                and all(person.get(k) == v for k, v in wanted['person_or_org'].items()))
    descriptions = actual.get('additional_descriptions')
    require(isinstance(descriptions, list) and len(descriptions) == 1)
    value, wanted = descriptions[0], expected['additional_descriptions'][0]
    require(isinstance(value, dict) and set(value) <= {'description', 'type', 'lang'}
            and value.get('lang') in (None, {}) and value.get('description') == wanted['description'])
    vocabulary(value.get('type'), wanted['type'])
