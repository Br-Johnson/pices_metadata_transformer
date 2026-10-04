"""Compile a finite, nonexecutable publication plan from reviewed local evidence.

No provider client, credentials, registry discovery, grant or transport adapter.
File descriptors bind original bytes; they do not substitute for artifact policy,
prepared payload, current identity review or a durable provider execution ledger.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

D04 = 'docs/readiness/2026-10-04/'
BASE = '6825c2cda6b8932e2c053af9a76582452524dca3'
PINS = {
    'source_ledger': ('residual_targets_integrated_source_status.json', '7d5da663101ceee2228e72913ec65a8c30756325dd440a86e416c8489a1157f7'),
    'target_projection': ('residual_targets_record_target_projection.json', '8ff370c759b0e4434918364dc6d340a37adf0c7a3ef3533e1ecb99aabf4fa5fd'),
    'prior_identity': ('alias228_production_reconciliation_input.json', 'a5b34f430a3b0b3a14776987e9828b4a1cf701ce2dc2172bd4cbb472759e37e5'),
    'owner_summary': ('production_owner_inventory_parent_summary.json', 'cdb0f98655130a3bb025fa2a5c92b6c8d518602e5589027d30fdbdcab15706d8'),
    'representation': ('approved_alias_representation_228.json', '9e45fc869b0fe03220b44734cf429129f78dc93eb9fd20bf9b802398b684dda6'),
    'pair_authority': ('alias_pair_approach_authority.json', 'ea3c0dba61ba03a330c80fc204f70ae3b88669f5ede5f22e60015b4bdb828130'),
    'measurement': ('residual_targets_validation.json', 'e6b798464e1a244af26a8ad7501e527c441a185c0d28c0c0fe253476aa02f26c'),
    'remaining': ('residual_targets_remaining45.json', '3d97a03ce1343aa745b32ed374b601d5a7bdf5e9b889f4a514ff169f4f4e6bf2'),
    'resource_profile': ('finite_source_resource_access_655.json', '8aec41a5c27176c284bc0249c2619d1caa61ac1c245e986a3ba15201edfdee34'),
    'creator_profile': ('source_citation_credits_426.json', '15c654dc714849327b827363071a1da3ad7c3fa20c2c95a990d7868e75e96bd2'),
    'title_profile': ('source_display_titles_42.json', '846e8787ae141a30993611d650af84420c769347cccec155a9686736c4df5e4a'),
}
SHARED_HOLDS = [
    'prepared_payload_and_policy_binding_not_validated_by_this_plan',
    'current_provider_identity_and_conflicts_require_separate_review',
    'legacy_production_transport_compatibility_not_established_by_synthetic_controller',
    'live_canary_readback_unchanged_retry_and_release_gates_remain_separate',
    'durable_execution_state_and_bounded_action_grant_required',
]
STATE_FIELDS = {
    'record_target_id', 'source_sha256', 'environment', 'deposition_id', 'doi',
    'needs_reconciliation', 'upload_status', 'publish_status',
    'metadata_sha256', 'artifact_contract_sha256',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def rows_by_id(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), 'Duplicate evidence identity')
    return result


def _read_inputs(repo):
    documents, bindings = {}, {}
    for key, (name, expected) in PINS.items():
        relative = D04 + name
        path = (repo / relative).resolve()
        require(path.is_relative_to(repo), 'Evidence path outside repository')
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, 'Pinned evidence changed: ' + name)
        documents[key] = json.loads(raw)
        bindings[key] = {'path': relative, 'sha256': expected}
    return documents, bindings


def _originals(repo, source_rows):
    expected = {sid + '.xml' for sid in source_rows}
    root = repo / 'FGDC'
    require({p.name for p in root.glob('*.xml')} == expected, 'Original XML inventory differs')
    result = {}
    for sid, source in sorted(source_rows.items()):
        path = (root / (sid + '.xml')).resolve()
        require(path.is_relative_to(root.resolve()), 'Original XML outside source directory')
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        require(sha == source['source_sha256'], 'Original source changed: ' + sid)
        result[sid] = {'source_id': sid, 'path': 'FGDC/' + sid + '.xml',
                       'name': sid + '.xml', 'size': len(raw), 'sha256': sha,
                       'md5': hashlib.md5(raw, usedforsecurity=False).hexdigest(),
                       'role': 'descriptive_metadata'}
    return result


def validate_restart_snapshot(snapshot, expected_binding, target_rows):
    """Read only an explicitly supplied sanitized export, never discover a registry.

    This reports legacy facts conservatively. Even a complete or rehashed export
    cannot establish current provider state or make a create/retry safe.
    """
    if snapshot is None:
        return {}, None
    require(isinstance(snapshot, dict) and set(snapshot) == {
        'schema_version', 'kind', 'environment', 'publication_inputs_sha256', 'entries'},
        'Invalid sanitized restart snapshot fields')
    require(type(snapshot['schema_version']) is int and snapshot['schema_version'] == 1
            and snapshot['kind'] == 'sanitized_offline_publication_restart_snapshot'
            and snapshot['environment'] == 'production', 'Invalid restart snapshot scope')
    require(snapshot['publication_inputs_sha256'] == expected_binding,
            'Restart snapshot belongs to different publication inputs')
    require(isinstance(snapshot['entries'], list), 'Invalid restart entries')
    entries = {}
    for entry in snapshot['entries']:
        require(isinstance(entry, dict) and set(entry) == STATE_FIELDS, 'Invalid restart entry fields')
        tid = entry['record_target_id']
        require(isinstance(tid, str) and tid in target_rows and tid not in entries,
                'Unknown or duplicate restart target')
        require(entry['source_sha256'] == target_rows[tid]['source_sha256']
                and entry['environment'] == 'production', 'Restart source/environment mismatch')
        require(type(entry['needs_reconciliation']) is bool, 'Invalid reconciliation state')
        rid = entry['deposition_id']
        require(rid is None or type(rid) is int and rid > 0, 'Invalid provider identity')
        doi = entry['doi']
        require(doi is None or isinstance(doi, str) and bool(re.fullmatch(r'10\.[0-9]{4,9}/\S+', doi)),
                'Invalid DOI')
        require(entry['upload_status'] in ('pending', 'failed', 'success', 'unknown')
                and entry['publish_status'] in ('draft', 'published', 'unknown'),
                'Unsupported restart state')
        for key in ('metadata_sha256', 'artifact_contract_sha256'):
            value = entry[key]
            require(value is None or isinstance(value, str) and bool(re.fullmatch('[0-9a-f]{64}', value)),
                    'Invalid restart payload binding')
        entries[tid] = copy.deepcopy(entry)
    return entries, digest(snapshot)


def _restart_report(entry, protected, conflicting_ids, reserved_ids,
                    conflicting_dois=frozenset(), reserved_dois=frozenset()):
    if entry is None:
        return {'disposition': 'hold_missing_state_not_permission_to_create',
                'safe_to_retry': False, 'reported_entry': None}
    doi_key = (entry['doi'] or '').casefold()
    mismatch = bool(protected and (entry['deposition_id'] != protected['record_id']
                                  or doi_key != protected['doi'].casefold()))
    if doi_key in conflicting_dois:
        disposition = 'hold_provider_doi_shared_by_multiple_targets'
    elif doi_key in reserved_dois:
        disposition = 'hold_doi_reserved_for_another_source'
    elif entry['deposition_id'] in conflicting_ids:
        disposition = 'hold_provider_identity_shared_by_multiple_targets'
    elif entry['deposition_id'] in reserved_ids:
        disposition = 'hold_identity_reserved_for_another_source_or_excluded_record'
    elif mismatch:
        disposition = 'hold_conflict_with_protected_record_or_doi'
    elif entry['needs_reconciliation']:
        disposition = 'hold_uncertain_create_or_write_no_automatic_retry'
    elif entry['deposition_id'] is None:
        disposition = 'hold_missing_identity_no_create_or_retry_inferred'
    elif entry['upload_status'] == 'unknown' or entry['publish_status'] == 'unknown':
        disposition = 'hold_unknown_legacy_status_requires_reconciliation'
    elif entry['publish_status'] == 'published':
        disposition = 'preserve_reported_published_identity_no_create_or_replacement'
    elif not entry['metadata_sha256'] or not entry['artifact_contract_sha256']:
        disposition = 'hold_missing_payload_or_artifact_binding'
    elif entry['upload_status'] == 'success' and entry['publish_status'] == 'draft':
        disposition = 'reported_same_draft_requires_exact_remote_readback_before_retry'
    else:
        disposition = 'reported_partial_draft_reconcile_same_identity_and_files'
    return {'disposition': disposition, 'safe_to_retry': False,
            'reported_entry': copy.deepcopy(entry)}


def build_plan(repo, *, batch_size=10, restart_snapshot=None):
    """Return prospective batches only; executable/provider-operation fields stay false."""
    require(type(batch_size) is int and 1 <= batch_size <= 10, 'Batch size must be 1 through 10 whole targets')
    repo = Path(repo).resolve()
    documents, bindings = _read_inputs(repo)
    ledger, view = documents['source_ledger'], documents['target_projection']
    prior, summary = documents['prior_identity'], documents['owner_summary']
    sources = rows_by_id(ledger['records'], 'source_id')
    classes = rows_by_id(view['class_targets'], 'record_target_id')
    singletons = rows_by_id(view['singleton_targets'], 'record_target_id')
    targets = classes | singletons
    require(len(sources) == 4206 and len(classes) == 228 and len(singletons) == 3750
            and len(targets) == 3978, 'Finite source/target cardinality differs')
    require(view['source_ledger_sha256'] == bindings['source_ledger']['sha256'], 'Projection ledger differs')
    pairs = rows_by_id(prior['targets'], 'record_target_id')
    approved = rows_by_id(documents['representation']['classes'], 'record_target_id')
    require(set(classes) == set(pairs) == set(approved), 'Pair identities differ')
    protected = rows_by_id(prior['protected_existing_imports'], 'source_id')
    require(len(protected) == 5 and set(protected) <= set(singletons), 'Protected identities differ')
    reported_associations = {x['source_id']: int(x['record_id'])
                             for x in summary['reported_unchanged_existing_associations']}
    require(reported_associations == {sid: row['record_id'] for sid, row in protected.items()},
            'Parent-reported protected associations differ')
    coverage = summary['reported_exact_pair_candidates']
    require(coverage['pair_population'] == 228 and coverage['candidate_count'] == 0,
            'Owner summary requires a new reviewed decision adapter')
    originals = _originals(repo, sources)
    binding = digest({'evidence': bindings, 'expected_original_files': originals})
    restart, restart_hash = validate_restart_snapshot(restart_snapshot, binding, targets)
    assigned_ids = Counter(entry['deposition_id'] for entry in restart.values()
                           if entry['deposition_id'] is not None)
    conflicting_ids = {rid for rid, count in assigned_ids.items() if count > 1}
    assigned_dois = Counter(entry['doi'].casefold() for entry in restart.values() if entry['doi'])
    conflicting_dois = {doi for doi, count in assigned_dois.items() if count > 1}
    reserved_ids = {row['record_id'] for row in protected.values()} | {
        int(row['record_id']) for row in summary['excluded_from_fgdc_restoration']}
    reserved_dois = {row['doi'].casefold() for row in protected.values()}
    rows, represented = [], set()
    for tid, target in sorted(targets.items()):
        members = target['source_ids']
        is_class = tid in classes
        require(len(members) == (2 if is_class else 1) and len(set(members)) == len(members)
                and not represented.intersection(members), 'Overlapping or split target membership')
        require(all(sid in sources and sources[sid]['source_sha256'] == target['source_sha256']
                    for sid in members), 'Target source binding differs')
        represented.update(members)
        state = target['source_semantic_status']
        require(state in ('supported', 'held', 'failed'), 'Unsupported source status')
        held = None if is_class else protected.get(tid)
        holds = []
        if state != 'supported':
            holds.insert(0, 'source_' + ('malformed' if state == 'failed' else 'held'))
        artifact = {'status': 'prepared_payload_binding_pending', 'reference': None}
        if is_class:
            require(members == approved[tid]['source_ids']
                    and members == [x['source_id'] for x in pairs[tid]['members']]
                    and all(sources[sid]['source_status'] == 'held' for sid in members),
                    'Approved paired representation differs')
            require(target['upload_eligible'] is False and target['remote_verified'] is False
                    and target['publication_approved'] is False, 'Unexpected class authority')
            identity = {'decision': 'reported_zero_exact_current_owner_candidates_capture_review_pending',
                        'owner_summary_evidence': bindings['owner_summary'],
                        'current_owner_absence_independently_verified_here': False,
                        'historical_deleted_or_tombstone_absence_established': False,
                        'production_record_id': None, 'production_doi': None,
                        'canonical_source_id': None,
                        'title_hints_not_identity': copy.deepcopy(pairs[tid]['title_only_nonmatch_warnings'])}
            fresh = tid in view['class_assessment_scopes']['fresh_selected']['record_target_ids']
            artifact = {'status': 'saved_class_reference_requires_artifact_resolution_and_validation',
                        'reference': {key: target[key] for key in (
                            'payload_path', 'payload_sha256', 'artifact_contract_sha256')},
                        'assessment_scope': 'fresh_selected' if fresh else 'unchanged_historical'}
            holds.extend(['raw_owner_capture_not_supplied_to_code_lane', 'class_execution_not_implemented'])
        else:
            require(members == [tid] and state == sources[tid]['source_status'], 'Singleton status differs')
            identity = {'decision': ('preserve_known_existing_identity_pending_current_capture_review'
                                     if held else 'singleton_identity_not_assessed_by_pair_inventory'),
                        'production_record_id': held['record_id'] if held else None,
                        'production_doi': held['doi'] if held else None,
                        'historical_deleted_or_tombstone_absence_established': False}
            if held:
                holds.append('existing_record_correction_requires_review_no_replacement')
        rows.append({'record_target_id': tid, 'source_ids': list(members),
                     'source_sha256': target['source_sha256'],
                     'source_semantic_status': state,
                     'expected_original_files': [originals[sid] for sid in members],
                     'identity_decision': identity, 'artifact_binding': artifact,
                     'restart': _restart_report(restart.get(tid), held, conflicting_ids,
                                                reserved_ids - {held['record_id']} if held else reserved_ids,
                                                conflicting_dois,
                                                reserved_dois - {held['doi'].casefold()} if held else reserved_dois),
                     'execution_holds': holds, 'shared_execution_holds_apply': True,
                     'executable': False,
                     'publication_approved': False, 'upload_eligible': False, 'remote_verified': False,
                     'source_question_reference': (None if state == 'supported' else {
                         **bindings['remaining'], 'source_id': tid}),
                     'provider_actions': [], 'provider_action_grant': None})
    require(represented == set(sources), 'Incomplete original-source coverage')
    counts = Counter(row['source_semantic_status'] for row in rows)
    require(counts == {'supported': 3933, 'held': 39, 'failed': 6}, 'Target status counts differ')
    prospective = [row for row in rows if row['source_semantic_status'] == 'supported']
    supported_classes = sum(row['record_target_id'] in classes for row in prospective)
    supported_files = sum(len(row['source_ids']) for row in prospective)
    require(supported_classes == 228 and supported_files == 4161, 'Supported target/file accounting differs')
    batches = [{'batch_id': f'prospective-{i // batch_size + 1:04d}',
                'record_target_ids': [row['record_target_id'] for row in prospective[i:i + batch_size]],
                'original_file_count': sum(len(row['source_ids']) for row in prospective[i:i + batch_size]),
                'executable': False, 'provider_actions': []}
               for i in range(0, len(prospective), batch_size)]
    result = {
        'schema_version': 1, 'kind': 'nonexecutable_publication_plan',
        'source_baseline_commit': BASE, 'environment': 'production',
        'evidence': bindings, 'publication_inputs_sha256': binding,
        'restart_snapshot_canonical_sha256': restart_hash,
        'shared_execution_holds': list(SHARED_HOLDS),
        'summary': {'original_files': 4206, 'unique_targets': 3978,
                    'source_supported_targets': 3933, 'source_held_targets': 39,
                    'malformed_targets': 6, 'source_supported_singletons': 3705,
                    'source_supported_classes': supported_classes, 'prospective_original_files': supported_files,
                    'prospective_batches': len(batches), 'maximum_targets_per_batch': batch_size,
                    'executable_targets': 0, 'provider_actions': 0},
        'owner_inventory': copy.deepcopy(summary),
        'protected_existing_imports': copy.deepcopy(prior['protected_existing_imports']),
        'excluded_provider_records': copy.deepcopy(summary['excluded_from_fgdc_restoration']),
        'class_artifact_resolvers': copy.deepcopy(view['class_assessment_scopes']),
        'artifact_requirements': {
            'content_status': 'metadata_only', 'original_file_roles': 'descriptive_metadata',
            'underlying_research_data_included': False, 'new_license_inferred': False,
            'required_xml_access': 'restricted',
            'limit': 'Expected original-file hashes are not prepared payload or policy contracts. '
                     'Validate the exact current singleton v1 or paired v2 artifact, source '
                     'policy, restoration authority and complete metadata before execution.'},
        'restart_limit': 'Snapshot entries are reported legacy facts only. Missing state never '
                         'restores create allowance. Uncertain actions require reconciliation; '
                         'a same-draft hint needs exact current readback before any retry. '
                         'Published identities are preserved, never automatically replaced.',
        'integration_boundary': 'Offline planning only. Not accepted as safe_to_upload, QA, '
                                'identity adoption, execution state, grant or release evidence. '
                                'Existing live operation guards remain unchanged.',
        'targets': rows, 'prospective_batches': batches,
    }
    result['plan_sha256'] = digest(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New offline JSON file; never a live registry')
    parser.add_argument('--batch-size', type=int, default=10)
    parser.add_argument('--restart-snapshot', type=Path, help='Explicit sanitized export; never discovered automatically')
    args = parser.parse_args()
    snapshot = json.loads(args.restart_snapshot.read_bytes()) if args.restart_snapshot else None
    result = build_plan(args.repo, batch_size=args.batch_size, restart_snapshot=snapshot)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write('\n')
    print(json.dumps({'path': str(args.output), 'plan_sha256': result['plan_sha256'],
                      **result['summary']}, sort_keys=True))


if __name__ == '__main__':
    main()
