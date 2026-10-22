"""Offline modern metadata for reviewed exact-content pairs.

Two pinned pair policies: the 203 Exxon pairs (`POLICY`, published) and the 25
non-Exxon pairs (`NONEXXON_POLICY`: 24 organizational credits and the Food Habits
personal pair, ADR 0015). Two source identities, filenames and policies remain
distinct even when bytes match. No singleton identity alias, transport, grant,
execution or release is provided. Every preparation rebuilds both source
assessments and the v2 target, and every policy re-derives its membership from
the pinned reviews instead of trusting its own manifest.
"""

import hashlib
import html
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from scripts import content_class_targets as classes
from scripts import modern_singleton as singleton
from scripts.artifact_contract import fingerprint
from scripts.modern_singleton import encode, parse, pinned, require, sha, source_element
from scripts.production_mutations import PROTECTED
from scripts.rehosting_authority import validate_restricted_metadata

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / 'docs/readiness/2026-10-06/modern_exxon_pairs203.json'
MAPPING_SHA = '19686d6204a2d42e42dbef735313693e2a47553ec135f674c6e7c235a82ffa58'
POLICY = 'modern-xml-exxon-pairs203-v1'
REVIEW = MAPPING.parent / 'modern_exxon203_source_review.json'
REVIEW_SHA = '51c7266a2da2d270fc52ba70e712faa27a3ffd59cd2ba7b44ff4f7dbdd3bf48d'
SERVICE = MAPPING.parent / 'modern_exxon_creator_contract.json'
SERVICE_SHA = 'e320207b7feda481d7466eaa28e021d64ce24ce7e25f442e0f33e164fe9d88ab'

# The 25 non-Exxon pairs (ADR 0015): the manifest is derived from, and checked against, the
# archived pair source review and the Food Habits literal-parts supplement.
REVIEWS = ROOT / 'docs/readiness/2026-10-06/next_source_review'
NONEXXON_MAPPING = ROOT / 'docs/readiness/2026-10-22/modern_nonexxon_pairs25.json'
NONEXXON_MAPPING_SHA = 'a561055aa20864a6e2bb362c410f6b345c48ffef94e093feea64a75427e9b84b'
NONEXXON_POLICY = 'modern-xml-nonexxon-pairs25-v1'
NONEXXON_KIND = 'modern-nonexxon-content-classes-v1'
NONEXXON_REVIEW = REVIEWS / 'pices-nonexxon25-pair-source-review.json'
NONEXXON_REVIEW_SHA = '455b5e015eca7f93e96b1a75ecd0a1998adaaa6ee37a38a512c18f2f913c7d94'
NONEXXON_REVIEW_KIND = 'remaining_nonexxon25_pairs_source_only_modern_creator_review'
FOODHABITS_SUPPLEMENT = REVIEWS / 'pices-foodhabits-pair-literal-parts-supplement.json'
FOODHABITS_SUPPLEMENT_SHA = 'ee723d4a262238dd72223e87f17f552b3e25aad41f92faa071c330cecd75b97a'
FOODHABITS_SUPPLEMENT_VERDICT = 'APPROVE_EXACT_COMPLETE_TWO_PERSON_VECTOR_AS_FINITE_CONTEXTUAL_NAME_PARTS_INFERENCE'
FOODHABITS_BINDINGS = REVIEWS / 'pices-foodhabits-pair-current-source-bindings.json'
FOODHABITS_BINDINGS_SHA = 'b353004cd8c4328d51db32cec4dbbfed092d6f97d715b1f1cb65460d21bea9db'
ORGANIZATIONAL_VERDICT = 'approve_finite_organizational_pair_projection'
# How a prepared input bound its legacy creators: a literal primary origin carries no
# creator_interpretation; the creator426 and Exxon821 cohorts carry their manifest digest.
LITERAL_PRIMARY, CREATOR426, EXXON821 = 'literal_default_primary', 'creator426', 'exxon821'
IDENTITY_FIELDS = ('canonical_source_id', 'production_record_id', 'production_doi')


def planned_target(row):
    """The pinned publication-plan target of a pair: supported, both files, no production identity."""
    planned = [plan for plan in pinned(singleton.PLAN, singleton.PLAN_SHA)['targets']
               if plan['record_target_id'] == row['record_target_id']]
    require(len(planned) == 1)
    plan = planned[0]
    require(plan['source_ids'] == row['source_ids'] and plan['source_sha256'] == row['source_sha256']
            and plan['source_semantic_status'] == 'supported'
            and all(plan['identity_decision'][key] is None for key in IDENTITY_FIELDS))
    return plan


def source_policy(record_target_id):
    """Finite paired authority is separate from the 412-singleton admission set."""
    manifest = pinned(MAPPING, MAPPING_SHA)
    profile = pinned(singleton.EXXON_PROFILE, singleton.EXXON_SHA)
    projection = pinned(singleton.EXXON_MAPPING, singleton.EXXON_MAPPING_SHA)
    pinned(REVIEW, REVIEW_SHA)
    pinned(SERVICE, SERVICE_SHA)
    representation = classes.load_representation()
    members = {row['source_id']: row['source_sha256'] for row in profile['members']}
    expected = sorted([row for row in representation['classes'] if all(
        members.get(sid) == row['source_sha256'] for sid in row['source_ids'])],
        key=lambda row: row['record_target_id'])
    header = {
        'schema_version': 1, 'kind': 'modern-exxon-content-classes-v1', 'policy': POLICY,
        'profile': profile['profile'], 'creators': profile['creators'],
        'modern_creators': projection['modern_creators'],
        'source_review_sha256': REVIEW_SHA, 'service_contract_sha256': SERVICE_SHA,
        'source_plan_sha256': singleton.PLAN_SHA, 'creator_profile_sha256': singleton.EXXON_SHA,
        'creator_projection_sha256': singleton.EXXON_MAPPING_SHA,
        'representation_sha256': classes.REPRESENTATION_SHA256,
        'pair_map_sha256': classes.MAP_SHA256, 'pair_authority_sha256': classes.AUTHORITY_SHA256,
    }
    require(isinstance(manifest, dict) and set(manifest) == set(header) | {'targets'}
            and type(manifest['schema_version']) is int
            and all(manifest[key] == value for key, value in header.items())
            and projection['creators'] == profile['creators']
            and projection['creator_profile_sha256'] == singleton.EXXON_SHA
            and projection['service_contract_sha256'] == SERVICE_SHA
            and manifest['targets'] == expected and len(expected) == 203)
    selected = [row for row in expected if row['record_target_id'] == record_target_id]
    require(len(selected) == 1 and not set(selected[0]['source_ids']) & set(PROTECTED))
    row = selected[0]
    return manifest, row, planned_target(row)


def reviewed_groups():
    """The 25 non-Exxon pairs as the pinned reviews approve them, derived without the manifest.

    The 24 organizational pairs are approved by the pair source review with their exact
    legacy creator object and modern organizational creator. The Food Habits pair was held
    there for its personal name parts; the later literal-parts supplement approves its exact
    two-person vector and supersedes only that hold. Returns the groups (one reviewed creator
    array each), the representation rows of the targets, and each source's reviewed primary
    origin elements.
    """
    review = pinned(NONEXXON_REVIEW, NONEXXON_REVIEW_SHA)
    supplement = pinned(FOODHABITS_SUPPLEMENT, FOODHABITS_SUPPLEMENT_SHA)
    bindings = pinned(FOODHABITS_BINDINGS, FOODHABITS_BINDINGS_SHA)
    rows = {row['record_target_id']: row for row in classes.load_representation()['classes']}
    require(review['kind'] == NONEXXON_REVIEW_KIND and len(review['pairs']) == 25
            and supplement['verdict'] == FOODHABITS_SUPPLEMENT_VERDICT
            and supplement['complete_modern_projection_approved_for_source_review'] is True
            and supplement['remaining_limits']['source_boundary_hold_for_this_exact_vector'] is False
            and supplement['existing_pair_review']['sha256'] == NONEXXON_REVIEW_SHA
            and supplement['source_binding_receipt']['sha256'] == FOODHABITS_BINDINGS_SHA
            and supplement['publication_plan_sha256'] == singleton.PLAN_SHA
            and bindings['record_target_id'] == supplement['record_target_id']
            and bindings['complete_current_legacy_creators'] == supplement['complete_current_legacy_creators'])
    groups, targets, origins = {}, [], {}
    for pair in review['pairs']:
        target_id, members = pair['record_target_id'], pair['members']
        row = rows[target_id]
        require(row['source_ids'] == [m['source_id'] for m in members]
                and all(m['source_sha256'] == row['source_sha256'] for m in members)
                and pair['both_original_files_byte_identical'] is True
                and pair['both_current_full_legacy_creator_arrays_equal'] is True
                and [s['source_id'] for s in pair['sources']] == row['source_ids']
                and all(s['source_sha256'] == row['source_sha256'] for s in pair['sources']))
        if pair['verdict'] == ORGANIZATIONAL_VERDICT:
            require(pair['actual_blocker'] is None and pair['proposed_modern_creators'])
            creators, modern, authority = (pair['full_current_legacy_creator_objects'],
                                           pair['proposed_modern_creators'], LITERAL_PRIMARY)
            reviewed_by = NONEXXON_REVIEW.name
        else:
            require(target_id == supplement['record_target_id'] and pair['proposed_modern_creators'] is None
                    and supplement['complete_current_legacy_creators'] == pair['full_current_legacy_creator_objects']
                    and supplement['full_current_creator426_cohort']['members'] == members
                    and [r['source_id'] for r in supplement['source_rows']] == row['source_ids']
                    and all(r['sha256'] == row['source_sha256'] for r in supplement['source_rows']))
            creators, modern, authority = (supplement['complete_current_legacy_creators'],
                                           supplement['approved_complete_modern_creators'], CREATOR426)
            reviewed_by = FOODHABITS_SUPPLEMENT.name
        group = groups.setdefault(pair['group_id'], {
            'group_id': pair['group_id'], 'review': reviewed_by, 'creator_authority': authority,
            'creators': creators, 'modern_creators': modern, 'record_target_ids': []})
        require(group == {**group, 'review': reviewed_by, 'creator_authority': authority,
                          'creators': creators, 'modern_creators': modern})
        group['record_target_ids'].append(target_id)
        targets.append(row)
        for source in pair['sources']:
            origins[source['source_id']] = source['ordered_primary_origin_elements']
    for group in groups.values():
        group['record_target_ids'].sort()
    targets.sort(key=lambda row: row['record_target_id'])
    ids = [sid for row in targets for sid in row['source_ids']]
    require(len(targets) == 25 and len(groups) == 5 and len(set(ids)) == len(ids) == len(origins) == 50)
    return [groups[key] for key in sorted(groups)], targets, origins


def nonexxon_source_policy(record_target_id):
    """The second finite pair policy; its manifest must equal what the pinned reviews derive."""
    manifest = pinned(NONEXXON_MAPPING, NONEXXON_MAPPING_SHA)
    exxon = pinned(MAPPING, MAPPING_SHA)
    groups, expected, origins = reviewed_groups()
    header = {
        'schema_version': 1, 'kind': NONEXXON_KIND, 'policy': NONEXXON_POLICY,
        'source_review_sha256': NONEXXON_REVIEW_SHA,
        'foodhabits_supplement_sha256': FOODHABITS_SUPPLEMENT_SHA,
        'foodhabits_bindings_sha256': FOODHABITS_BINDINGS_SHA,
        'source_plan_sha256': singleton.PLAN_SHA, 'creator_profile_sha256': singleton.PROFILE_SHA,
        'representation_sha256': classes.REPRESENTATION_SHA256,
        'pair_map_sha256': classes.MAP_SHA256, 'pair_authority_sha256': classes.AUTHORITY_SHA256,
    }
    require(isinstance(manifest, dict) and set(manifest) == set(header) | {'groups', 'targets'}
            and type(manifest['schema_version']) is int
            and all(manifest[key] == value for key, value in header.items())
            and manifest['groups'] == groups and manifest['targets'] == expected
            and not ({row['record_target_id'] for row in expected}
                     & {row['record_target_id'] for row in exxon['targets']}))
    selected = [row for row in expected if row['record_target_id'] == record_target_id]
    require(len(selected) == 1 and not set(selected[0]['source_ids']) & set(PROTECTED))
    row = selected[0]
    group = [g for g in groups if record_target_id in g['record_target_ids']]
    require(len(group) == 1)
    return manifest, row, planned_target(row), group[0], {sid: origins[sid] for sid in row['source_ids']}


@dataclass(frozen=True)
class PairRule:
    """What one pinned policy binds for one pair: its identity, plan, creators and evidence pins."""
    policy: str
    row: dict
    plan: dict
    creators: list           # the exact legacy creator array both prepared inputs must carry
    modern_creators: list    # the reviewed creators the wire sends
    creator_authority: str   # how the prepared inputs bound those creators
    origins: dict            # source id -> reviewed primary origin elements; empty when the review binds none
    pins: dict               # the policy's evidence fields


def pair_rule(record_target_id):
    """Select the one pinned policy that admits this pair; the two memberships never overlap."""
    exxon_ids = {row['record_target_id'] for row in pinned(MAPPING, MAPPING_SHA)['targets']}
    other_ids = {row['record_target_id'] for row in pinned(NONEXXON_MAPPING, NONEXXON_MAPPING_SHA)['targets']}
    require(not exxon_ids & other_ids and record_target_id in exxon_ids | other_ids)
    common = {'source_plan_sha256': singleton.PLAN_SHA, 'representation_sha256': classes.REPRESENTATION_SHA256,
              'pair_map_sha256': classes.MAP_SHA256, 'pair_authority_sha256': classes.AUTHORITY_SHA256}
    if record_target_id in exxon_ids:
        manifest, row, plan = source_policy(record_target_id)
        return PairRule(POLICY, row, plan, manifest['creators'], manifest['modern_creators'], EXXON821, {}, {
            **common, 'mapping_manifest_sha256': MAPPING_SHA, 'source_review_sha256': REVIEW_SHA,
            'creator_profile_sha256': singleton.EXXON_SHA, 'creator_projection_sha256': singleton.EXXON_MAPPING_SHA,
            'service_contract_sha256': SERVICE_SHA})
    _, row, plan, group, origins = nonexxon_source_policy(record_target_id)
    return PairRule(NONEXXON_POLICY, row, plan, group['creators'], group['modern_creators'],
                    group['creator_authority'], origins, {
                        **common, 'mapping_manifest_sha256': NONEXXON_MAPPING_SHA,
                        'source_review_sha256': NONEXXON_REVIEW_SHA,
                        'foodhabits_supplement_sha256': FOODHABITS_SUPPLEMENT_SHA,
                        'foodhabits_bindings_sha256': FOODHABITS_BINDINGS_SHA,
                        'creator_profile_sha256': singleton.PROFILE_SHA,
                        'group_id': group['group_id'], 'creator_authority': group['creator_authority']})


def check_creator_binding(rule, policy):
    """The prepared input bound its legacy creators the way the policy's review did."""
    require(isinstance(policy, dict))
    reference = policy.get('creator_interpretation')
    if rule.creator_authority == LITERAL_PRIMARY:
        require('creator_interpretation' not in policy)
    else:
        expected = singleton.EXXON_SHA if rule.creator_authority == EXXON821 else singleton.PROFILE_SHA
        require(isinstance(reference, dict) and reference.get('manifest_sha256') == expected)


@dataclass(frozen=True)
class PreparedClass:
    record_target_id: str
    source_ids: tuple[str, str]
    body: bytes
    originals: tuple[tuple[str, bytes], tuple[str, bytes]]
    legacy_target: dict
    evidence: dict
    binding: str


def prepare(record_target_id, paths, *, reviewed_at):
    """Return a source-bound wire proposal; a supported source is not a grant.

    The caller supplies a fixed explicit assessment time and existing prepared
    inputs. No saved target, single preferred member or renamed copy is accepted.
    """
    rule = pair_rule(record_target_id)
    row, plan = rule.row, rule.plan
    target = classes.prepare_class_target(record_target_id, paths, reviewed_at=reviewed_at)
    require(target['source_semantic_status'] == 'supported'
            and all(item['source_semantic_status'] == 'supported'
                    for item in target['member_assessments'])
            and all(target[key] == value for key, value in row.items())
            and target['production_reconciliation_status'] == 'pending'
            and target['execution_status'] == 'class_execution_not_implemented'
            and all(target[key] is False for key in
                    ('upload_eligible', 'remote_verified', 'publication_approved')))
    originals, inputs = [], []
    contract = target['artifact_contract']
    require(contract['schema_version'] == 2 and len(contract['files']) == len(target['members']) == 2
            and contract['sha256'] == fingerprint({k: v for k, v in contract.items() if k != 'sha256'}))
    for sid, filename, member, file in zip(row['source_ids'], row['source_filenames'],
                                         target['members'], contract['files'], strict=True):
        source = Path(paths.original_fgdc_dir) / filename
        path = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw, payload_raw = source.read_bytes(), path.read_bytes()
        payload = parse(payload_raw)
        check_creator_binding(rule, payload.get('artifact_policy', {}))
        require(payload['metadata']['creators'] == rule.creators
                and fingerprint(payload['metadata']) == target['common_source_metadata_sha256']
                and member['source_id'] == sid and member['source_filename'] == filename
                and member['source_sha256'] == sha(raw) == row['source_sha256']
                and member['payload_sha256'] == sha(payload_raw)
                and member['policy_sha256'] == fingerprint(payload['artifact_policy'])
                and raw == (ROOT / 'FGDC' / filename).read_bytes())
        if sid in rule.origins:  # the review read exactly these primary origin elements
            origins = ET.fromstring(raw).findall('./idinfo/citation/citeinfo/origin')
            require([source_element(node) for node in origins] == rule.origins[sid])
        descriptor = {'name': filename, 'size': len(raw), 'sha256': sha(raw),
                      'md5': hashlib.md5(raw, usedforsecurity=False).hexdigest(),
                      'role': 'descriptive_metadata'}
        require(file == descriptor and dict(descriptor, source_id=sid, path='FGDC/' + filename)
                in plan['expected_original_files'])
        originals.append((filename, raw))
        inputs.append({'source_id': sid, 'source_path': str(source.resolve()),
                       'prepared_input_path': str(path.resolve()), 'prepared_input_sha256': sha(payload_raw),
                       'member': member})
    require(len(plan['expected_original_files']) == 2 and originals[0][1] == originals[1][1])
    metadata = target['metadata']
    validate_restricted_metadata(metadata)
    require(metadata['creators'] == rule.creators)
    keywords = metadata.get('keywords', [])
    require(isinstance(keywords, list) and all(isinstance(k, str) and k.strip() for k in keywords))
    legacy = encode(metadata)
    preservation = '<p>' + singleton.PRESERVATION_LABEL + '</p><pre>' + html.escape(legacy.decode()) + '</pre>'
    wire = {'metadata': {
        'resource_type': {'id': 'other'}, 'title': metadata['title'],
        'creators': rule.modern_creators,
        'publication_date': metadata['publication_date'], 'publisher': 'Zenodo',
        'description': metadata['description'], 'subjects': [{'subject': k} for k in keywords],
        'additional_descriptions': [{'type': {'id': 'other'}, 'description': preservation}],
    }, 'access': {'record': 'public', 'files': 'restricted'}, 'files': {'enabled': True}}
    singleton.validate_payload(wire)
    body = encode(wire)
    evidence = {
        'schema_version': 1, 'kind': 'modern-content-class-preparation-v1', 'policy': rule.policy,
        'record_target_id': record_target_id, 'source_ids': row['source_ids'],
        'source_sha256': row['source_sha256'], 'reviewed_at': reviewed_at, **rule.pins,
        'inputs': inputs, 'artifact_contract': contract, 'legacy_target_sha256': sha(encode(target)),
        'legacy_metadata_sha256': sha(legacy), 'wire_sha256': sha(body),
        'schema_sha256': {name: digest for name, (_, digest) in singleton.SCHEMA_FILES.items()},
        'runtime_sha256': singleton.runtime_binding(),
        'production_reconciliation_status': 'pending', 'execution_status': 'class_execution_not_implemented',
        'upload_eligible': False, 'remote_verified': False, 'publication_approved': False,
    }
    return PreparedClass(record_target_id, tuple(row['source_ids']), body, tuple(originals),
                         target, evidence, sha(encode(evidence)))


def validate_prepared(prepared, paths):
    """Self-rehashing an edited wire/target/inventory never establishes validity."""
    require(type(prepared) is PreparedClass)
    rebuilt = prepare(prepared.record_target_id, paths, reviewed_at=prepared.evidence['reviewed_at'])
    require(prepared == rebuilt)
    return rebuilt
