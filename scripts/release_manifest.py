"""Separate explicit publication release from record-level human or agent QA.

Offline preparation never approves a release. Production publishing validates
exact QA-manifest and selected record bindings before any client operation.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from scripts.upload_service import atomic_json, metadata_hash, read_json


def record_binding(record):
    return {key: record.get(key) for key in ('fgdc_id', 'deposition_id', 'source_sha256',
                                            'metadata_sha256', 'artifact_contract')}


def prepare_release(qa_manifest, source_ids=None):
    if (not isinstance(qa_manifest, dict) or qa_manifest.get('environment') != 'production'
            or qa_manifest.get('schema_version') not in (1, 2)
            or not isinstance(qa_manifest.get('records'), list)):
        raise ValueError('Versioned production QA manifest required')
    selected = set(source_ids) if source_ids is not None else None
    records = [record for record in qa_manifest['records'] if record.get('qa', {}).get('approved') is True
               and (selected is None or record.get('fgdc_id') in selected)]
    if not records or (selected is not None and {row.get('fgdc_id') for row in records} != selected):
        raise ValueError('Release selection must identify QA-approved records')
    if len({row.get('fgdc_id') for row in records}) != len(records):
        raise ValueError('Release source identities must be unique')
    return {'schema_version': 1, 'environment': 'production',
            'qa_manifest_sha256': metadata_hash(qa_manifest),
            'prepared_at': datetime.now(timezone.utc).isoformat(),
            'release': {'approved': False, 'authority_type': 'human', 'authority': '',
                        'authorized_at': '', 'rationale': ''},
            'records': [record_binding(row) for row in records]}


def validate_release(release_manifest, qa_manifest, fgdc_id, entry):
    release = release_manifest.get('release', {}) if isinstance(release_manifest, dict) else {}
    if (not isinstance(release_manifest, dict) or release_manifest.get('schema_version') != 1
            or release_manifest.get('environment') != 'production' or entry.get('environment') != 'production'
            or release_manifest.get('qa_manifest_sha256') != metadata_hash(qa_manifest)
            or release.get('approved') is not True or release.get('authority_type') != 'human'
            or any(not isinstance(release.get(key), str) or not release[key].strip()
                   for key in ('authority', 'authorized_at', 'rationale'))):
        raise ValueError('Separate explicit human publication release required for this exact QA manifest')
    rows = release_manifest.get('records')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Release selection is malformed')
    matches = [row for row in rows if row.get('fgdc_id') == fgdc_id]
    if len(matches) != 1 or matches[0] != record_binding(dict(entry, fgdc_id=fgdc_id)):
        raise ValueError('Record is outside the exact authorized release selection')
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description='Prepare an unapproved production release; never publish')
    parser.add_argument('--qa-manifest', required=True)
    parser.add_argument('--release-manifest', required=True)
    parser.add_argument('--fgdc-id', action='append', help='Repeat to select exact approved source IDs')
    args = parser.parse_args()
    if Path(args.release_manifest).exists():
        raise ValueError('Choose a new path to preserve release history')
    atomic_json(args.release_manifest, prepare_release(read_json(args.qa_manifest), args.fgdc_id))


if __name__ == '__main__':
    main()
