"""Prepare and validate evidence-bound record QA for exact drafts and payloads.

Preparing a manifest is offline and does not approve or publish records.
Reviewers explicitly fill the approval and duplicate-adjudication fields.
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from scripts.path_config import OutputPaths
from scripts.upload_service import assert_environment, atomic_json, metadata_hash, prepare_metadata, read_json
from scripts.artifact_contract import prepare_artifact, assert_artifact_binding, validate_files


QA_CHECKS = ('source_fidelity', 'dates', 'creators', 'rights', 'relations', 'metadata_only')
CLASSIFICATIONS = ('same_work', 'alternate_version', 'derived_subset', 'different_dataset',
                   'checked_no_match', 'waived_unavailable')


def approved_population_hash(manifest):
    """Bind program review to exact approved identities, without a circular manifest hash."""
    population = [{key: record.get(key) for key in
                   ('fgdc_id', 'deposition_id', 'source_sha256', 'metadata_sha256',
                    'artifact_contract', 'agent_evidence', 'qa', 'duplicate_review')}
                  for record in manifest.get('records', []) if record.get('qa', {}).get('approved') is True]
    return metadata_hash({'source_revision': manifest.get('source_revision'),
                          'records': sorted(population, key=lambda item: item['fgdc_id'])})


def validate_program_review(manifest):
    """Schema 2 requires independent process review and risk-stratified spot checks.

    This is a program gate, not a claim that every source received independent review.
    Publication callers enforce it separately from record-level assessment.
    """
    if manifest.get('schema_version') != 2:
        return
    digest = approved_population_hash(manifest)
    approved = {row['fgdc_id'] for row in manifest.get('records', []) if row.get('qa', {}).get('approved') is True}
    if not approved:
        raise ValueError('Program review requires an approved record population')
    for name in ('independent_review', 'risk_stratified_spotcheck'):
        review = manifest.get('program_review', {}).get(name, {})
        if (review.get('status') != 'reviewed' or review.get('reviewer_type') not in ('human', 'agent')
                or review.get('population_sha256') != digest
                or any(not isinstance(review.get(key), str) or not review[key].strip()
                       for key in ('reviewer', 'reviewed_at', 'rationale'))
                or not isinstance(review.get('evidence'), list) or not review['evidence']
                or any(not isinstance(item, dict) or not item.get('scope') or not item.get('reference')
                       for item in review['evidence'])):
            raise ValueError(f'Program {name} evidence is missing or stale')
        if name == 'risk_stratified_spotcheck':
            sample = review.get('sampled_ids')
            if (not isinstance(sample, list) or not sample or len(set(sample)) != len(sample)
                    or not set(sample).issubset(approved) or not review.get('risk_strata')):
                raise ValueError('Risk-stratified spotcheck needs an explicit sample and strata')
        elif review['reviewer'] in {row.get('qa', {}).get('reviewer') for row in manifest['records']
                                   if row.get('qa', {}).get('approved') is True}:
            raise ValueError('Independent program review must identify a separate assessor')


def prepare_manifest(paths):
    registry = read_json(paths.uploads_registry_path, {})
    records = []
    for fgdc_id, entry in sorted(registry.items()):
        if fgdc_id.startswith('_') or entry.get('upload_status') != 'success':
            continue
        assert_environment(entry, paths.environment)
        metadata, source_path, source_hash = prepare_metadata(entry['json_file'], paths)
        artifact = prepare_artifact(read_json(entry['json_file']), source_path)
        assert_artifact_binding(entry, artifact)
        if metadata_hash(metadata) != entry.get('metadata_sha256') or source_hash != entry.get('source_sha256'):
            raise ValueError(f'{fgdc_id}: draft/source payload changed; reconcile before QA')
        records.append({
            'fgdc_id': fgdc_id, 'deposition_id': entry['deposition_id'],
            'metadata_sha256': entry['metadata_sha256'], 'source_sha256': entry['source_sha256'],
            'artifact_contract': artifact,
            'duplicate_review': {'status': 'pending', 'classification': None, 'rationale': '', 'evidence': []},
            'qa': {'approved': False, 'reviewer': '', 'reviewed_at': '', 'rationale': '',
                   'checks': {check: False for check in QA_CHECKS}},
        })
    if not records:
        raise ValueError('No successful drafts available for QA')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1], text=True).strip()
    return {'schema_version': 1, 'environment': paths.environment, 'source_revision': revision,
            'prepared_at': datetime.now(timezone.utc).isoformat(), 'records': records}


def validate_approval(manifest, fgdc_id, entry, paths, remote_metadata=None, remote_files=None):
    assert_environment(entry, paths.environment)
    if (not manifest or manifest.get('schema_version') not in (1, 2)
            or manifest.get('environment') != paths.environment or not manifest.get('source_revision')):
        raise ValueError('A versioned environment-matched QA manifest is required')
    matches = [record for record in manifest.get('records', []) if record.get('fgdc_id') == fgdc_id]
    if len(matches) != 1:
        raise ValueError(f'{fgdc_id}: exactly one QA record required')
    record = matches[0]
    metadata, source_path, source_hash = prepare_metadata(entry['json_file'], paths)
    artifact = prepare_artifact(read_json(entry['json_file']), source_path)
    assert_artifact_binding(entry, artifact)
    if record.get('artifact_contract') != artifact:
        raise ValueError('QA artifact approval is stale or missing')
    if (record.get('deposition_id') != entry.get('deposition_id')
            or record.get('metadata_sha256') != entry.get('metadata_sha256')
            or record.get('metadata_sha256') != metadata_hash(metadata)
            or record.get('source_sha256') != source_hash
            or source_hash != entry.get('source_sha256')):
        raise ValueError('QA approval is stale or identifies a different draft')
    qa = record.get('qa', {})
    if manifest['schema_version'] == 1 and qa.get('reviewer_type', 'human') != 'human':
        raise ValueError('Historical schema 1 approval requires human review')
    if manifest['schema_version'] == 2:
        if (qa.get('reviewer_type') not in ('human', 'agent') or not qa.get('run_id')
                or qa.get('review_revision') != manifest['source_revision'] or not qa.get('evidence')):
            raise ValueError('Schema 2 reviewer provenance is required')
        if qa['reviewer_type'] == 'agent':
            from scripts.agent_qa import validate_agent_evidence
            validate_agent_evidence(record, entry, paths)
    if (qa.get('approved') is not True or not qa.get('reviewer') or not qa.get('reviewed_at')
            or not qa.get('rationale') or any(qa.get('checks', {}).get(key) is not True for key in QA_CHECKS)):
        raise ValueError('Record QA approval and all checks are required')
    duplicate = record.get('duplicate_review', {})
    if (duplicate.get('status') != 'reviewed' or duplicate.get('classification') not in CLASSIFICATIONS
            or not duplicate.get('rationale') or not duplicate.get('evidence')):
        raise ValueError('Duplicate evidence and recorded adjudication are required')
    if duplicate['classification'] == 'same_work' and duplicate.get('action') != 'publish_metadata_reference':
        raise ValueError('Same-work duplicate needs an explicit referential publication decision')
    if remote_metadata is not None:
        from scripts.verify_uploads import compare_metadata
        if compare_metadata(metadata, remote_metadata):
            raise ValueError('Remote draft differs from the QA-approved payload')
    if remote_files is not None:
        validate_files(remote_files, artifact)
    return record


def main():
    parser = argparse.ArgumentParser(description='Prepare pending offline QA; schema 1 uses human review, agent_qa emits evidence-bound schema 2')
    parser.add_argument('--output', default='output')
    parser.add_argument('--production', action='store_true')
    parser.add_argument('--manifest', required=True, help='New manifest path; existing files are never overwritten')
    args = parser.parse_args()
    if Path(args.manifest).exists():
        raise ValueError('Choose a new manifest path to preserve review history')
    paths = OutputPaths(args.output, 'production' if args.production else 'sandbox')
    atomic_json(args.manifest, prepare_manifest(paths))


if __name__ == '__main__':
    main()
