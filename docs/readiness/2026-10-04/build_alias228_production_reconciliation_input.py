#!/usr/bin/env python3
"""Prepare finite offline reconciliation inputs; never infer remote absence or grants.

Reads only the explicit committed public evidence allowlist below. No network,
credential, provider client, private registry, environment or subprocess access.
Frozen semantic counts describe the PR28 baseline; subsequent source corrections
must retain their own ledger and must not overwrite this evidence history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

BASE_COMMIT = '173a4b0613e915b2915ae815b01f9f8823f2ced8'
OWNER = '01a0fed7-bf71-7384-95fd-3434599df03f'
D04 = 'docs/readiness/2026-10-04/'
D03 = 'docs/readiness/2026-10-03/'
D01 = 'docs/readiness/2026-10-01/'
PINS = {
    D04 + 'approved_alias_representation_228.json': '9e45fc869b0fe03220b44734cf429129f78dc93eb9fd20bf9b802398b684dda6',
    D04 + 'alias456_source_to_content.json': '9c110638bd161483727aed1b42e516fdc7a3c9d8134c97a9a70abff690750bbb',
    D04 + 'alias228_record_targets.json': 'fd9bcba857c5d9816f44bbca0ac4c826c10527f64a7e6330468ee2fe814981d4',
    D04 + 'residual_evidence15_integrated_source_status.json': '4a4ef82f9da793c0a83cd58f6388991dd38f7a5f92947b2d089855b259af4e4a',
    D03 + 'source_alias_candidates.json': 'd1b5aae5446e230d86fd4a91b6385548b8d6c4fa93a3b98a0ccc26fc731f22d5',
    D01 + 'public_source_associations.json': 'ff22622eb0b396dc52a5af4c66e6eedc56b8d2b4b4dd2421d69d4ca38322a2ad',
    D03 + 'production_source_identity_review_3.json': 'eb4e3d9c14e31564c4c83aed7a3cfdcd9200cfec1fc36bf6fda66c7ce7a1bb51',
    D03 + 'production_identity_adjudication.md': '4d65315e4bf232fdc121aebc2a601cf69dec433be812c644dcc039c7ade0f6db',
    D04 + 'alias456_canonical_evidence_review.json': '14094d058d55d136160ce68e05995a22079161263b65ceaa91a5220428c74d13',
    D01 + 'five_imports_correction_proposal.json': 'd2e5875ea809aabd4565480799c23930f943e24d659af042697ea25e645b49f3',
    D01 + 'production_readiness_plan.md': '412261898d88e974829b7fb82193881913004bc6d5b03e9d7d61f65f902466d6',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(data.encode()).hexdigest()


def unique_rows(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), f'duplicate {key}')
    return result


def build(repo):
    documents = {}
    inventory = []
    for relative, expected in sorted(PINS.items()):
        path = repo / relative
        require(path.resolve().is_relative_to(repo.resolve()), 'input outside repository')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected, f'changed evidence: {relative}')
        inventory.append({'path': relative, 'sha256': expected, 'bytes': len(data)})
        if relative.endswith('.json'):
            documents[relative] = json.loads(data)
    representation = documents[D04 + 'approved_alias_representation_228.json']
    mapping = documents[D04 + 'alias456_source_to_content.json']
    view = documents[D04 + 'alias228_record_targets.json']
    ledger = documents[D04 + 'residual_evidence15_integrated_source_status.json']
    history = documents[D03 + 'source_alias_candidates.json']
    review = documents[D03 + 'production_source_identity_review_3.json']
    require(representation['provider_operations_authorized'] is False, 'unexpected authority')
    require(view['source_ledger_sha256'] == PINS[D04 + 'residual_evidence15_integrated_source_status.json'], 'ledger mismatch')
    require(view['representation_manifest_sha256'] == PINS[D04 + 'approved_alias_representation_228.json'], 'representation mismatch')
    groups = unique_rows(mapping['groups'], 'canonical_content_id')
    sources = unique_rows(mapping['source_to_content'], 'source_id')
    ledger_rows = unique_rows(ledger['records'], 'source_id')
    targets = unique_rows(view['class_targets'], 'record_target_id')
    approved = unique_rows(representation['classes'], 'record_target_id')
    require(len(groups) == len(targets) == len(approved) == 228, 'class cardinality')
    require(len(sources) == 456 and len(ledger_rows) == 4206, 'source cardinality')
    require(set(groups) == set(targets) == set(approved), 'class set mismatch')
    protected = []
    reviewed = unique_rows(review['records'], 'record_id')
    snapshot_path = D01 + 'five_imports_correction_proposal.json'
    snapshots = unique_rows(documents[snapshot_path]['records'], 'record_id')
    for old in history['retained_historical_production_protections']:
        row = dict(old)
        row['historical_association_status'] = row.pop('association_status')
        row['evidence_path'] = D03 + 'source_alias_candidates.json'
        row['preservation_required'] = True
        row['current_owner_or_remote_state_verified'] = False
        if row['record_id'] in reviewed:
            latest = reviewed[row['record_id']]
            require(all(row[k] == latest[k] for k in ('source_id', 'source_sha256', 'record_id', 'doi')), 'retained identity conflict')
            row['subsequent_identity_decision'] = latest['decision']
            row['subsequent_identity_review_path'] = D03 + 'production_source_identity_review_3.json'
        require(row['source_id'] not in sources, 'unexpected retained pair association requires review')
        require(ledger_rows[row['source_id']]['source_sha256'] == row['source_sha256'], 'retained source binding')
        snapshot = snapshots[row['record_id']]
        require(all(row[key] == snapshot[key] for key in ('source_id', 'source_sha256', 'doi')),
                'historical snapshot association differs')
        retained = {key: snapshot[key] for key in (
            'public_snapshot_provenance', 'current_public_fields', 'public_files')}
        row['historical_public_snapshot'] = {
            'source_evidence_path': snapshot_path,
            'source_record_id': row['record_id'],
            'captured_fields': retained,
            'captured_fields_canonical_sha256': canonical_digest(retained),
            'meaning': 'Exact retained public metadata/file snapshot at its recorded capture time; '
                       'not current freshness, ownership, complete owner inventory or file-absence proof.'}
        protected.append(row)
    require(len(protected) == 5, 'retained protection cardinality')
    rows = []
    seen_members = set()
    for target_id in sorted(approved):
        item = approved[target_id]
        group = groups[target_id]
        target = targets[target_id]
        members = item['source_ids']
        sha = item['source_sha256']
        require(target_id == f'sha256:{sha}', 'target identity')
        require(len(members) == 2 and members == sorted(members), 'pair members')
        require(not seen_members.intersection(members), 'overlapping pairs')
        seen_members.update(members)
        require(members == group['equivalence_group_members'] == target['source_ids'], 'member mismatch')
        require(sha == group['content_canonical_sha256'] == target['source_sha256'], 'raw hash mismatch')
        require(item['source_filenames'] == [f'{sid}.xml' for sid in members], 'filename mismatch')
        require(all(item[field] is None for field in ('canonical_source_id', 'canonical_catalogue_record_id', 'canonical_provider_record_id', 'canonical_provider_doi')), 'unexpected canonical selection')
        require(target['upload_eligible'] is False and target['remote_verified'] is False and target['publication_approved'] is False, 'unexpected target authority')
        member_rows = []
        for sid in members:
            require(sources[sid]['source_sha256'] == sha == ledger_rows[sid]['source_sha256'], 'member source binding')
            require(sources[sid]['canonical_content_id'] == target_id, 'member class mismatch')
            member_rows.append({'source_id': sid, 'source_path': sources[sid]['source_path'],
                                'original_filename': f'{sid}.xml', 'raw_xml_sha256': sha,
                                'legacy_source_status': ledger_rows[sid]['source_status']})
        # This finite adapter examines only explicit source-ID/hash crosswalks.
        # A title, bibliography citation or underlying-dataset DOI is never a match.
        candidates = []
        for record in protected:
            reasons = []
            if record['source_id'] in members:
                reasons.append('exact_captured_source_id')
            if record['source_sha256'] == sha:
                reasons.append('exact_captured_source_content_sha256')
            if reasons:
                candidates.append({'record_id': record['record_id'], 'doi': record['doi'],
                                   'matched_evidence': reasons, 'review_required': True,
                                   'evidence_path': record['evidence_path']})
        require(not candidates, 'new candidate requires an explicit reviewed evidence adapter')
        warnings = group['historical_title_collision_warnings']
        rows.append({
            'record_target_id': target_id, 'raw_xml_sha256': sha,
            'members': member_rows, 'source_semantic_status_at_frozen_baseline': target['source_semantic_status'],
            'member_assessments_at_frozen_baseline': target['member_assessments'],
            'exact_captured_production_candidates': candidates,
            'title_only_nonmatch_warnings': warnings,
            'search_hints_not_identity_proof': {
                'historical_title': group['historical_title_from_frozen_alias_review'],
                'historical_procite_literals': group['historical_literal_procite_references'],
                'limit': 'Search hints only. ProCite is a historical bibliography row, not a provider identity; zero is reused.'},
            'reconciliation_status': 'unresolved_no_exact_match_in_allowed_captured_evidence',
            'production_record_id': None, 'production_doi': None, 'canonical_source_id': None,
            'fresh_read_only_evidence_requirements': ['complete_owner_scope_inventory', 'source_identity_candidate_readback', 'current_ownership_versions_files', 'preserve_conflicts_and_protected_records'],
            'remote_absence_established': False, 'upload_eligible': False,
            'provider_action_grant': None,
        })
    require(seen_members == set(sources), 'member coverage')
    require(sum(bool(row['title_only_nonmatch_warnings']) for row in rows) == 2, 'collision coverage')
    return {
        'schema_version': 1,
        'kind': 'offline_production_identity_reconciliation_input',
        'status': 'PREPARATION_ONLY_NO_REMOTE_DECISIONS_OR_ACTION_GRANTS',
        'frozen_source_baseline_commit': BASE_COMMIT,
        'scope': 'All 228 approved identical-pair targets, both 456 original source identities retained. Committed captured public evidence only; no live calls or private files.',
        'counts_at_frozen_baseline': {
            'original_source_files': len(ledger_rows),
            'legacy_source_file_statuses': ledger['integrated_counts'],
            'unique_record_targets': view['summary']['unique_record_targets'],
            'unique_record_target_statuses': {
                'supported': view['summary']['source_supported_targets'],
                'held': view['summary']['source_held_targets'],
                'malformed': view['summary']['malformed_targets']},
            'pair_targets': 228, 'pair_source_files': 456,
            'pair_semantic_statuses': dict(sorted(Counter(row['source_semantic_status_at_frozen_baseline'] for row in rows).items())),
            'exact_captured_pair_production_candidates': 0,
            'unresolved_pair_targets': 228, 'upload_eligible_pair_targets': 0,
            'title_only_protected_record_collisions': 2,
        },
        'evidence_inventory': inventory,
        'evidence_inventory_canonical_sha256': canonical_digest(inventory),
        'captured_evidence_coverage': {
            'complete_authenticated_owner_inventory_available': False,
            'raw_current_production_export_available_in_allowlist': False,
            'current_record_metadata_file_version_or_ownership_readback_available': False,
            'public_record_ids_in_historical_associations': [15046283, 17317851, 17317853, 17317855, 17317857, 17317859],
            'reader_reported_export_limit': review['evidence_limits']['library_status'],
            'capture_dates': 'Five historical public snapshots retain exact 2026-10-01 endpoint, retrieval timestamp, HTTP status and captured metadata/file fields in protected_existing_imports. Current freshness, ownership and inventory completeness remain unverified.',
            'absence_limit': 'Zero captured exact matches means no proven local match; it is not remote absence, a complete duplicate check, or permission to create.',
        },
        'protected_existing_imports': sorted(protected, key=lambda row: row['record_id']),
        'unrelated_records': [
            {'record_id': 10042430, 'disposition': 'explicitly_excluded_poster', 'doi': None},
            {'record_id': 15046283, 'disposition': 'preserve_unrelated_wellbeing_record_do_not_attach_to_pairs', 'doi': None},
        ],
        'evidence_requirement_definitions': {
            'complete_owner_scope_inventory': {
                'scope': 'One shared, complete current read-only owner inventory covering records and drafts, relevant versions and community/account scope; preserve pagination, totals, query parameters, timestamps, endpoint and terminal-completeness receipts.',
                'limit': 'Community-only public search is incomplete owner evidence. Do not guess API filter support; verified filtering or a complete finite inventory is needed. Missing pages or inaccessible scopes remain gaps.'},
            'source_identity_candidate_readback': {
                'scope': 'For each pair, compare both exact FGDC IDs/filenames and raw XML SHA-256 against actual captured metadata notes/identifiers and source-file evidence. Preserve literal fields, record IDs/DOIs, response byte hashes and source evidence references for every candidate.',
                'limit': 'Filename or metadata ID is a candidate requiring provenance review. Actual matching bytes establish shared content, not unique record priority. Title and research DOI never establish provider identity. Remote checksums of another algorithm are not compared as SHA-256.'},
            'current_ownership_versions_files': {
                'scope': 'For any candidate, capture controlled ownership, current record/version/concept identifiers, current DOI fields, draft/published/deleted state and complete file names/sizes/checksum algorithms, with read-only exact-source byte evidence where available.',
                'limit': 'Omitted or inaccessible files are unknown, not absent. Historical evidence does not establish current state or authorize correction.'},
            'preserve_conflicts_and_protected_records': {
                'scope': 'Retain every matching or competing existing record/DOI, including multiple matches. Require explicit same-work/version/subset and disposition review before selecting a correction target. Keep five protected imports and both distinct title-collision pairs separate.',
                'limit': 'No automatic deletion, merge, canonical priority, new DOI, create grant or replacement follows from this input.'},
        },
        'sole_provider_executor': OWNER,
        'provider_stage_dispatched': False,
        'provider_requests': 0, 'provider_writes': 0, 'private_file_reads': 0,
        'production_credentials_required_here': False,
        'targets': rows,
        'targets_canonical_sha256': canonical_digest(rows),
        'integration_boundary': 'Documentation/preparation artifact only; not consumed by upload, QA, release, reconciliation adoption or provider transport. It cannot clear existing class guards.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.repo)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write('\n')
    print(json.dumps({'output': str(args.output), 'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(), 'targets': len(result['targets'])}, sort_keys=True))


if __name__ == '__main__':
    main()
