"""Import an explicitly reviewed draft identity from a saved deposition response.

Offline only. Does not delete, create, update or publish remote records. The
operator must establish ownership and source identity before running this tool.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from scripts.artifact_contract import prepare_artifact, validate_files
from scripts.content_class_targets import require_singleton_operation
from scripts.path_config import OutputPaths
from scripts.production_mutations import MutationJournal, preserve_identity
from scripts.upload_service import (
    atomic_json,
    expected_host,
    ledger_lock,
    metadata_hash,
    prepare_metadata,
    read_json,
    validate_deposition_response,
    validate_registry_identities,
)


def reconcile(paths, fgdc_id, snapshot, reviewer, rationale):
    require_singleton_operation(source_id=fgdc_id, entry=snapshot,
                                json_file=Path(paths.zenodo_json_dir) / (fgdc_id + '.json'), paths=paths)
    if not reviewer or not rationale or snapshot.get('confirmed_fgdc_id') != fgdc_id:
        raise ValueError('Explicit reviewer, rationale and confirmed source identity required')
    endpoint = urlparse(snapshot.get('endpoint', ''))
    record = snapshot.get('body')
    if (snapshot.get('http_status') != 200 or not snapshot.get('retrieved_at')
            or endpoint.scheme != 'https' or endpoint.hostname != expected_host(paths.environment)
            or not isinstance(record, dict) or not isinstance(record.get('id'), int)
            or endpoint.path.rstrip('/') != f"/api/deposit/depositions/{record['id']}"):
        raise ValueError('Verified environment-matched deposition response required')
    validate_deposition_response(record, record['id'])
    if record['state'] not in ('unsubmitted', 'inprogress') or record.get('submitted'):
        raise ValueError('Only an unpublished draft may be reconciled for upload resume')
    json_file = str(Path(paths.zenodo_json_dir) / f'{fgdc_id}.json')
    metadata, source_path, source_hash = prepare_metadata(json_file, paths)
    artifact = prepare_artifact(read_json(json_file), source_path)
    validate_files(record['files'], artifact, allow_missing=True)
    digest = metadata_hash(metadata)
    if snapshot.get('confirmed_metadata_sha256') != digest or snapshot.get('confirmed_source_sha256') != source_hash:
        raise ValueError('Human source correlation does not match current source/payload hashes')
    remote_title = record.get('metadata', {}).get('title')
    if remote_title and remote_title != metadata.get('title'):
        raise ValueError('Remote title conflicts with confirmed source identity')
    with ledger_lock(paths):
        registry = read_json(paths.uploads_registry_path, {})
        existing = registry.get(fgdc_id, {})
        require_singleton_operation(source_id=fgdc_id, entry=existing, json_file=json_file, paths=paths)
        if existing.get('deposition_id') and existing['deposition_id'] != record['id']:
            raise ValueError('Existing draft ID differs; resolve conflict manually')
        registry[fgdc_id] = dict(existing, environment=paths.environment,
            json_file=json_file, fgdc_file=source_path, metadata=metadata,
            metadata_sha256=digest, source_sha256=source_hash, deposition_id=record['id'],
            artifact_contract=artifact,
            zenodo_url=f'https://{endpoint.hostname}/deposit/{record["id"]}',
            needs_reconciliation=False, upload_status='pending', success=False, publish_status='draft',
            reconciliation={'reviewer': reviewer, 'rationale': rationale, 'endpoint': snapshot['endpoint'],
                            'retrieved_at': snapshot['retrieved_at'],
                            'reviewed_at': datetime.now(timezone.utc).isoformat(),
                            'response_sha256': metadata_hash(record)})
        registry[fgdc_id]['doi'] = preserve_identity(fgdc_id, registry[fgdc_id], record)
        validate_registry_identities(registry)
        if paths.environment == 'production':
            MutationJournal(paths).adopt(fgdc_id, registry[fgdc_id])
        atomic_json(paths.uploads_registry_path, registry)
    return registry[fgdc_id]


def main():
    parser = argparse.ArgumentParser(description='Offline human-reviewed draft reconciliation')
    parser.add_argument('--output', default='output')
    parser.add_argument('--production', action='store_true')
    parser.add_argument('--fgdc-id', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--reviewer', required=True)
    parser.add_argument('--rationale', required=True)
    args = parser.parse_args()
    reconcile(OutputPaths(args.output, 'production' if args.production else 'sandbox'), args.fgdc_id,
              read_json(args.snapshot), args.reviewer, args.rationale)


if __name__ == '__main__':
    main()
