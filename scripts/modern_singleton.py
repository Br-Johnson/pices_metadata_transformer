"""Finite source-aware modern mapping; no provider or publication authority.

Only explicitly pinned organizational singleton groups are supported.
Every preparation reruns semantic assessment and preserves assembled legacy
metadata separately from the explicitly selected repository-host publisher.
"""

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from scripts.agent_qa import assess_source
from scripts.citation_creator_interpretation import source_element
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
EXTENSION = ROOT / 'docs/readiness/2026-10-05/modern_organizational_extension86.json'
EXTENSION_SHA = 'c78074384f29310e5cdc0c23dddc6b47161e516bc0222ddbbe0a36dfbc9a1dcf'
EXTENSION_POLICY = 'modern-xml-organizations86-v1'
DIRECT_PROFILE = ROOT / 'docs/readiness/2026-10-06/modern_direct_primary_organizations.json'
DIRECT_SHA = '35512b48636ae563acfc26a77c547699bba2dfe767e414e995e83079e3f3eb13'
DIRECT_POLICY = 'modern-xml-direct-organizations-v1'
EXXON_PROFILE = ROOT / 'docs/readiness/2026-10-02/exxon_citation_interpretation.json'
EXXON_SHA = 'ee49147aec99d83cf54cb7fa4e59f7e50229967af0f08f5408e97144367e99e5'
EXXON_MAPPING = ROOT / 'docs/readiness/2026-10-06/modern_exxon_singletons412.json'
EXXON_MAPPING_SHA = '5dbfeb098ee8b3bbad0e06d020c1c14c88e32363d45fab4e69a5cc961482a94f'
EXXON_POLICY = 'modern-xml-exxon412-v1'
PICES_MAPPING = ROOT / 'docs/readiness/2026-10-06/modern_pices_singletons26.json'
PICES_MAPPING_SHA = '15d5f40fe829919a0ff9d9b81bcfc6205b2cd4042a3891e4dc9e4b3595204670'
PICES_POLICY = 'modern-xml-pices26-v1'
INSTITUTION_MAPPING = ROOT / 'docs/readiness/2026-10-06/modern_institution_singletons91.json'
INSTITUTION_MAPPING_SHA = '19dd282e701bb115e256c90cac0ebaba0cfa1b49baf748dc4bf55106cc22dfd1'
INSTITUTION_POLICY = 'modern-xml-institutions91-v1'
CITATION_ORG_MAPPING = ROOT / 'docs/readiness/2026-10-06/modern_citation_organizations129.json'
CITATION_ORG_MAPPING_SHA = '8ac4f141433dbbc58513ee968942ec23d2f484949b751fa01cba6bbcc393aee3'
CITATION_ORG_REVIEW = ROOT / 'docs/readiness/2026-10-06/modern_citationorg129_independent_review.json'
CITATION_ORG_REVIEW_SHA = 'dc9033829412054b0aed2a5ec354e9133889736859a39d727aeba98e59ae88c3'
CITATION_ORG_SOURCE = ROOT / 'docs/readiness/2026-10-06/modern_citationorg129_source_review.json'
CITATION_ORG_SOURCE_SHA = 'ceeaec8fdd29b3a56dceb700d2b3c47395ec54d0755c4bc3018a01f50d359168'
CITATION_ORG_POLICY = 'modern-xml-citation-organizations129-v1'
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


def source_policy(source_id):
    """Select finite reviewed membership, never infer creator type from a name.

    Keep the original 19 evidence fields and independence from the extension.
    New sources bind both the exact mapping manifest and their creator cohort.
    """
    original = cohort()
    if source_id in {row['source_id'] for row in original['members']}:
        return original, {'schema_version': 1, 'policy': POLICY}
    extension = pinned(EXTENSION, EXTENSION_SHA)
    header = {'schema_version': 1, 'kind': 'modern-organizational-extension-v1',
              'policy': EXTENSION_POLICY, 'legacy_policy': POLICY,
              'creator_profile_sha256': PROFILE_SHA, 'source_plan_sha256': PLAN_SHA}
    require(isinstance(extension, dict) and set(extension) == set(header) | {'members'}
            and type(extension['schema_version']) is int
            and all(extension[key] == value for key, value in header.items()))
    members = extension['members']
    require(isinstance(members, list) and len(members) == 86
            and all(isinstance(row, dict) and set(row) == {'source_id', 'source_sha256', 'creator_cohort'}
                    and isinstance(row['source_id'], str) and re.fullmatch(r'FGDC-[1-9][0-9]*', row['source_id'])
                    and isinstance(row['source_sha256'], str) and re.fullmatch('[0-9a-f]{64}', row['source_sha256'])
                    and isinstance(row['creator_cohort'], str) and row['creator_cohort'] != COHORT
                    for row in members))
    ids = [row['source_id'] for row in members]
    require(len(set(ids)) == 86 and ids == sorted(ids, key=lambda sid: int(sid[5:])))
    matched = [row for row in members if row['source_id'] == source_id]
    require(len(matched) <= 1)
    if not matched:
        return direct_source_policy(source_id)
    member = matched[0]
    selected = [row for row in pinned(PROFILE, PROFILE_SHA)['cohorts']
                if row['profile'] == member['creator_cohort']]
    require(len(selected) == 1 and {'source_id': source_id, 'source_sha256': member['source_sha256']}
            in selected[0]['members'])
    return selected[0], {'schema_version': 2, 'policy': EXTENSION_POLICY,
                         'mapping_manifest_sha256': EXTENSION_SHA, 'creator_cohort': member['creator_cohort']}


def direct_source_policy(source_id):
    """Exact reviewed primary-citation credits, separate from citation426 authority.

    Default organization detection only nominated candidates. This immutable
    manifest supplies the finite independent review and full creator objects.
    """
    manifest = pinned(DIRECT_PROFILE, DIRECT_SHA)
    require(isinstance(manifest, dict) and set(manifest) == {
        'schema_version', 'kind', 'policy', 'source_plan_sha256', 'source_census_sha256',
        'review_sha256', 'member_count', 'group_count', 'groups'}
        and type(manifest['schema_version']) is int and manifest['schema_version'] == 1
        and manifest['kind'] == 'modern-direct-primary-organizations-v1'
        and manifest['policy'] == DIRECT_POLICY and manifest['source_plan_sha256'] == PLAN_SHA
        and type(manifest['member_count']) is int and manifest['member_count'] > 0
        and type(manifest['group_count']) is int and manifest['group_count'] > 0
        and isinstance(manifest['groups'], list) and len(manifest['groups']) == manifest['group_count'])
    ids, profiles, matches = [], [], []
    for group in manifest['groups']:
        require(isinstance(group, dict) and set(group) == {
            'profile', 'creators', 'primary_origin_variants', 'members'}
            and isinstance(group['profile'], str) and re.fullmatch(r'primary-origin-[0-9]{3}', group['profile'])
            and isinstance(group['creators'], list) and group['creators']
            and all(isinstance(creator, dict) and set(creator) == {'name', 'type'}
                    and isinstance(creator['name'], str) and creator['name'].strip()
                    and creator['type'] == 'Organization' for creator in group['creators'])
            and isinstance(group['primary_origin_variants'], list) and group['primary_origin_variants']
            and isinstance(group['members'], list) and group['members'])
        profiles.append(group['profile'])
        for member in group['members']:
            require(isinstance(member, dict) and set(member) == {'source_id', 'source_sha256'}
                    and isinstance(member['source_id'], str) and re.fullmatch(r'FGDC-[1-9][0-9]*', member['source_id'])
                    and isinstance(member['source_sha256'], str) and re.fullmatch('[0-9a-f]{64}', member['source_sha256']))
            ids.append(member['source_id'])
            if member['source_id'] == source_id:
                matches.append(group)
    require(len(profiles) == len(set(profiles)) and len(ids) == len(set(ids)) == manifest['member_count']
            and len(matches) <= 1)
    if not matches:
        return exxon_source_policy(source_id)
    selected = matches[0]
    return selected, {'schema_version': 3, 'policy': DIRECT_POLICY,
                      'mapping_manifest_sha256': DIRECT_SHA, 'creator_cohort': selected['profile']}


def exxon_source_policy(source_id):
    """One reviewed mixed creator projection; never split arbitrary source names."""
    manifest = pinned(EXXON_MAPPING, EXXON_MAPPING_SHA)
    profile = pinned(EXXON_PROFILE, EXXON_SHA)
    require(isinstance(manifest, dict) and set(manifest) == {
        'schema_version', 'kind', 'policy', 'profile', 'source_plan_sha256',
        'creator_profile_sha256', 'review_sha256', 'service_contract_sha256',
        'creators', 'modern_creators', 'members'}
        and type(manifest['schema_version']) is int and manifest['schema_version'] == 1
        and manifest['kind'] == 'modern-exxon-singletons-v1' and manifest['policy'] == EXXON_POLICY
        and manifest['profile'] == profile['profile']
        and manifest['source_plan_sha256'] == PLAN_SHA
        and manifest['creator_profile_sha256'] == EXXON_SHA
        and manifest['creators'] == profile['creators']
        and isinstance(manifest['members'], list) and len(manifest['members']) == 412)
    modern = manifest['modern_creators']
    require(isinstance(modern, list) and len(modern) == len(profile['creators']) == 3)
    for legacy, current in zip(profile['creators'], modern, strict=True):
        if legacy.get('type') == 'Organization':
            require(current == {'person_or_org': {'name': legacy['name'], 'type': 'organizational'}})
        else:
            require(isinstance(current, dict) and set(current) == {'person_or_org', 'affiliations'})
            person = current['person_or_org']
            require(isinstance(person, dict) and set(person) == {'type', 'family_name', 'given_name'}
                    and person['type'] == 'personal'
                    and all(isinstance(person[key], str) and person[key].strip()
                            for key in ('family_name', 'given_name'))
                    and person['family_name'] + ', ' + person['given_name'] == legacy['name']
                    and current['affiliations'] == [{'name': legacy['affiliation']}])
    original = {member['source_id']: member['source_sha256'] for member in profile['members']}
    ids = []
    for member in manifest['members']:
        require(isinstance(member, dict) and set(member) == {'source_id', 'source_sha256'}
                and isinstance(member['source_id'], str) and member['source_id'] in original
                and member['source_sha256'] == original[member['source_id']]
                and member['source_id'] not in PROTECTED)
        ids.append(member['source_id'])
    require(len(set(ids)) == 412 and ids == sorted(ids, key=lambda sid: int(sid[5:])))
    if source_id not in ids:
        return pices_source_policy(source_id)
    return manifest, {'schema_version': 4, 'policy': EXXON_POLICY,
                      'mapping_manifest_sha256': EXXON_MAPPING_SHA, 'creator_cohort': profile['profile']}


def pices_source_policy(source_id):
    """The exact 26 institutional citations receive a reviewed wire-only type.

    Keep the name-only legacy attribution intact. Neither names from titles nor
    other untyped institutions inherit this finite representation decision.
    """
    manifest = pinned(PICES_MAPPING, PICES_MAPPING_SHA)
    rows = [row for row in pinned(PROFILE, PROFILE_SHA)['cohorts']
            if row['profile'] == 'pices_literal_26']
    require(len(rows) == 1)
    profile = rows[0]
    name = 'North Pacific Marine Science Organization (PICES)'
    require(isinstance(manifest, dict) and set(manifest) == {
        'schema_version', 'kind', 'policy', 'profile', 'source_plan_sha256',
        'creator_profile_sha256', 'review_sha256', 'raw_origin',
        'creators', 'modern_creators', 'members'}
        and type(manifest['schema_version']) is int and manifest['schema_version'] == 1
        and manifest['kind'] == 'modern-pices-singletons-v1' and manifest['policy'] == PICES_POLICY
        and manifest['profile'] == profile['profile']
        and manifest['source_plan_sha256'] == PLAN_SHA
        and manifest['creator_profile_sha256'] == PROFILE_SHA
        and manifest['raw_origin'] == profile['raw_origin'] == name
        and manifest['creators'] == profile['creators'] == [{'name': name}]
        and manifest['modern_creators'] == [{'person_or_org': {'name': name, 'type': 'organizational'}}]
        and manifest['members'] == profile['members'] and len(manifest['members']) == 26)
    ids = [row['source_id'] for row in manifest['members']]
    require(len(set(ids)) == 26 and not set(ids) & set(PROTECTED))
    if source_id not in ids:
        return institution_source_policy(source_id)
    return manifest, {'schema_version': 5, 'policy': PICES_POLICY,
                      'mapping_manifest_sha256': PICES_MAPPING_SHA, 'creator_cohort': profile['profile']}


def institution_source_policy(source_id):
    """Nine reviewed literal institutional credits; keep legacy names untyped.

    This finite representation decision does not infer entities from other
    names, occupational roles, program titles or person/institution compounds.
    """
    manifest = pinned(INSTITUTION_MAPPING, INSTITUTION_MAPPING_SHA)
    require(isinstance(manifest, dict) and set(manifest) == {
        'schema_version', 'kind', 'policy', 'source_plan_sha256', 'source_census_sha256',
        'review_sha256', 'binding_review_sha256', 'member_count', 'group_count', 'groups'}
        and type(manifest['schema_version']) is int and manifest['schema_version'] == 1
        and manifest['kind'] == 'modern-institutional-singletons-v1'
        and manifest['policy'] == INSTITUTION_POLICY and manifest['source_plan_sha256'] == PLAN_SHA
        and type(manifest['member_count']) is int and manifest['member_count'] == 91
        and type(manifest['group_count']) is int and manifest['group_count'] == 9
        and isinstance(manifest['groups'], list) and len(manifest['groups']) == 9)
    ids, profiles, matches = [], [], []
    for group in manifest['groups']:
        require(isinstance(group, dict) and set(group) == {
            'profile', 'creators', 'modern_creators', 'primary_origin_variants', 'members'}
            and isinstance(group['profile'], str) and re.fullmatch(r'institution-origin-0[1-9]', group['profile'])
            and isinstance(group['creators'], list) and len(group['creators']) == 1
            and isinstance(group['creators'][0], dict) and set(group['creators'][0]) == {'name'}
            and isinstance(group['creators'][0]['name'], str) and group['creators'][0]['name'].strip()
            and group['modern_creators'] == [
                {'person_or_org': {'name': group['creators'][0]['name'], 'type': 'organizational'}}]
            and isinstance(group['primary_origin_variants'], list) and group['primary_origin_variants']
            and all(isinstance(origins, list) and len(origins) == 1
                    and isinstance(origins[0], dict)
                    and set(origins[0]) == {'tag', 'attributes', 'text', 'tail', 'children'}
                    and origins[0]['tag'] == 'origin' and origins[0]['attributes'] == {}
                    and origins[0]['children'] == [] and origins[0]['tail'] is None
                    and isinstance(origins[0]['text'], str) and origins[0]['text'].strip()
                    for origins in group['primary_origin_variants'])
            and isinstance(group['members'], list) and group['members'])
        profiles.append(group['profile'])
        for member in group['members']:
            require(isinstance(member, dict) and set(member) == {'source_id', 'source_sha256'}
                    and isinstance(member['source_id'], str) and re.fullmatch(r'FGDC-[1-9][0-9]*', member['source_id'])
                    and member['source_id'] not in PROTECTED
                    and isinstance(member['source_sha256'], str) and re.fullmatch('[0-9a-f]{64}', member['source_sha256']))
            ids.append(member['source_id'])
            if member['source_id'] == source_id:
                matches.append(group)
    require(len(profiles) == len(set(profiles)) == 9 and len(ids) == len(set(ids)) == 91 and len(matches) <= 1)
    if not matches:
        return citation_organization_source_policy(source_id)
    selected = matches[0]
    return selected, {'schema_version': 6, 'policy': INSTITUTION_POLICY,
                      'mapping_manifest_sha256': INSTITUTION_MAPPING_SHA, 'creator_cohort': selected['profile']}


def citation_organization_source_policy(source_id):
    """129 reviewed name-only arrays; preserve current profile credit and order.

    The independent finite review supplies institutional typing. No program,
    collection, occupation or other untyped credit inherits that decision.
    """
    manifest = pinned(CITATION_ORG_MAPPING, CITATION_ORG_MAPPING_SHA)
    review = pinned(CITATION_ORG_REVIEW, CITATION_ORG_REVIEW_SHA)
    source = pinned(CITATION_ORG_SOURCE, CITATION_ORG_SOURCE_SHA)
    profiles = {row['profile']: row for row in pinned(PROFILE, PROFILE_SHA)['cohorts']}
    bindings = {row['source_id']: row for row in review['verified_source_bindings']}
    expected = []
    for group in review['approved_projection_groups']:
        expected.append({
            'group': group['cluster_index'], 'creators': group['complete_legacy_creators'],
            'modern_creators': group['proposed_modern_creators'],
            'members': [dict(member, creator_cohort=bindings[member['source_id']]['creator_cohort'],
                             cohort_object_sha256=bindings[member['source_id']]['cohort_object_sha256'])
                        for member in group['members']]})
    header = {'schema_version': 1, 'kind': 'modern-citation-organizations129-v1',
              'policy': CITATION_ORG_POLICY, 'creator_profile_sha256': PROFILE_SHA,
              'source_plan_sha256': PLAN_SHA, 'source_review_sha256': CITATION_ORG_SOURCE_SHA,
              'independent_review_sha256': CITATION_ORG_REVIEW_SHA, 'member_count': 129, 'group_count': 53}
    require(isinstance(manifest, dict) and set(manifest) == set(header) | {'groups'}
            and all(type(manifest[key]) is type(value) and manifest[key] == value
                    for key, value in header.items())
            and manifest['groups'] == expected and len(expected) == 53
            and source['members'] == review['approved_members'] and len(bindings) == 129)
    members, matches = [], []
    for group in expected:
        creators = group['creators']
        require(creators and all(set(creator) == {'name'} and isinstance(creator['name'], str)
                                 and creator['name'].strip() for creator in creators)
                and group['modern_creators'] == [
                    {'person_or_org': {'name': creator['name'], 'type': 'organizational'}} for creator in creators])
        for member in group['members']:
            sid, digest = member['source_id'], member['source_sha256']
            profile = profiles[member['creator_cohort']]
            require(sid not in PROTECTED and profile['creators'] == creators
                    and sha(encode(profile)) == member['cohort_object_sha256']
                    and {'source_id': sid, 'source_sha256': digest} in profile['members'])
            members.append({'source_id': sid, 'source_sha256': digest})
            if sid == source_id:
                matches.append((group, member['creator_cohort']))
    require(len(members) == len({row['source_id'] for row in members}) == 129
            and sorted(members, key=lambda row: int(row['source_id'][5:])) == review['approved_members']
            and len(matches) == 1)
    selected, cohort_name = matches[0]
    return selected, {'schema_version': 7, 'policy': CITATION_ORG_POLICY,
                      'mapping_manifest_sha256': CITATION_ORG_MAPPING_SHA, 'creator_cohort': cohort_name}


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
    require(isinstance(meta['creators'], list) and meta['creators'])
    for creator in meta['creators']:
        require(isinstance(creator, dict) and set(creator) <= {'person_or_org', 'affiliations'})
        person = creator.get('person_or_org')
        require(isinstance(person, dict))
        keys = ({'type', 'family_name', 'given_name'} if person.get('type') == 'personal'
                else {'type', 'name'})
        require(person.get('type') in ('personal', 'organizational') and set(person) == keys
                and all(isinstance(person[key], str) and person[key].strip() for key in keys))
        if 'affiliations' in creator:
            require(isinstance(creator['affiliations'], list) and creator['affiliations']
                    and all(isinstance(value, dict) and set(value) == {'name'}
                            and isinstance(value['name'], str) and value['name'].strip()
                            for value in creator['affiliations']))


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
    selected, policy_fields = source_policy(sid)
    members = {row['source_id']: row['source_sha256'] for row in selected['members']}
    require(sid in members)
    raw_input = json_file.read_bytes()
    payload = parse(raw_input)
    policy = payload.get('artifact_policy', {})
    require(isinstance(policy, dict))
    direct = policy_fields['policy'] == DIRECT_POLICY
    exxon = policy_fields['policy'] == EXXON_POLICY
    pices = policy_fields['policy'] == PICES_POLICY
    institution = policy_fields['policy'] == INSTITUTION_POLICY
    citation_org = policy_fields['policy'] == CITATION_ORG_POLICY
    authority_sha = (INSTITUTION_MAPPING_SHA if institution else
                     (EXXON_SHA if exxon else (DIRECT_SHA if direct else PROFILE_SHA)))
    if direct or institution:
        require('creator_interpretation' not in policy)
    else:
        reference = policy.get('creator_interpretation', {})
        require(isinstance(reference, dict) and reference.get('manifest_sha256') == authority_sha)
    metadata, source_sha, artifact, _ = assess_source(json_file, paths)
    xml = (ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
    require(source_sha == sha(xml) == members[sid] and artifact is not None
            and artifact['source_id'] == sid and len(artifact['files']) == 1
            and artifact['files'][0]['sha256'] == source_sha)
    if direct or institution:
        origins = ET.fromstring(xml).findall('./idinfo/citation/citeinfo/origin')
        require(origins and [source_element(node) for node in origins] in selected['primary_origin_variants'])
    target = next(row for row in pinned(PLAN, PLAN_SHA)['targets'] if row['record_target_id'] == sid)
    require(target['source_ids'] == [sid] and target['source_semantic_status'] == 'supported'
            and target['source_sha256'] == source_sha
            and target['identity_decision']['production_record_id'] is None
            and target['identity_decision']['production_doi'] is None)
    validate_restricted_metadata(metadata)
    require(metadata['creators'] == selected['creators'])
    if exxon or pices or institution or citation_org:
        creators = selected['modern_creators']
    else:
        require(all(set(c) == {'name', 'type'} and c['type'] == 'Organization'
                    for c in selected['creators']))
        creators = [{'person_or_org': {'name': c['name'], 'type': 'organizational'}}
                    for c in metadata['creators']]
    keywords = metadata.get('keywords', [])
    require(isinstance(keywords, list) and all(isinstance(k, str) and k.strip() for k in keywords))
    legacy = encode(metadata)
    preservation = '<p>' + PRESERVATION_LABEL + '</p><pre>' + html.escape(legacy.decode()) + '</pre>'
    wire = {'metadata': {
        'resource_type': {'id': 'other'}, 'title': metadata['title'],
        'creators': creators,
        'publication_date': metadata['publication_date'], 'publisher': 'Zenodo',
        'description': metadata['description'], 'subjects': [{'subject': k} for k in keywords],
        'additional_descriptions': [{'type': {'id': 'other'}, 'description': preservation}],
    }, 'access': {'record': 'public', 'files': 'restricted'}, 'files': {'enabled': True}}
    validate_payload(wire)
    body = encode(wire)
    evidence = {**policy_fields, 'source_id': sid,
                'source_sha256': source_sha, 'prepared_input_sha256': sha(raw_input),
                'legacy_metadata_sha256': sha(legacy), 'wire_sha256': sha(body),
                'artifact_contract': artifact, 'creator_profile_sha256': authority_sha,
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
                and value.get('role') in (None, {}))
        affiliations = wanted.get('affiliations', [])
        if affiliations:
            actual_affiliations = value.get('affiliations')
            require(isinstance(actual_affiliations, list) and len(actual_affiliations) == len(affiliations))
            for actual_affiliation, affiliation in zip(actual_affiliations, affiliations, strict=True):
                require(isinstance(actual_affiliation, dict)
                        and set(actual_affiliation) <= {'name', 'identifiers'}
                        and actual_affiliation.get('name') == affiliation['name']
                        and actual_affiliation.get('identifiers') in (None, []))
        else:
            require(value.get('affiliations') in (None, []))
        person = value.get('person_or_org')
        expected_person = wanted['person_or_org']
        require(isinstance(person, dict) and person.get('identifiers') in (None, [])
                and all(person.get(key) == wanted_value for key, wanted_value in expected_person.items()))
        if expected_person['type'] == 'personal':
            require(set(person) <= {'name', 'type', 'family_name', 'given_name', 'identifiers'})
            # The pinned service derives this display from the two reviewed fields.
            if 'name' in person:
                require(person['name'] == expected_person['family_name'] + ', ' + expected_person['given_name'])
        else:
            require(set(person) <= {'name', 'type', 'identifiers'})
    descriptions = actual.get('additional_descriptions')
    require(isinstance(descriptions, list) and len(descriptions) == 1)
    value, wanted = descriptions[0], expected['additional_descriptions'][0]
    require(isinstance(value, dict) and set(value) <= {'description', 'type', 'lang'}
            and value.get('lang') in (None, {}) and value.get('description') == wanted['description'])
    vocabulary(value.get('type'), wanted['type'])
