"""Finite, offline representation of the 228 approved identical XML pairs.

Both original identities/files remain evidence. These targets cannot use the
legacy singleton provider, adoption or approval paths. No provider is imported
or instantiated here; preparing a target never reconciles a remote identity.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.artifact_contract import fingerprint, prepare_artifact
from scripts.content_classification import classify_content, export_content_metadata
from scripts.fgdc_utils import build_metadata_notes, load_fgdc_xml, locate_fgdc_xml

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / 'docs/readiness/2026-10-04'
REPRESENTATION_PATH = DOCS / 'approved_alias_representation_228.json'
REPRESENTATION_SHA256 = '9e45fc869b0fe03220b44734cf429129f78dc93eb9fd20bf9b802398b684dda6'
MAP_PATH = DOCS / 'alias456_source_to_content.json'
MAP_SHA256 = '9c110638bd161483727aed1b42e516fdc7a3c9d8134c97a9a70abff690750bbb'
AUTHORITY_PATH = DOCS / 'alias_pair_approach_authority.json'
AUTHORITY_SHA256 = 'ea3c0dba61ba03a330c80fc204f70ae3b88669f5ede5f22e60015b4bdb828130'
SOURCE_LEDGER_SHA256 = '4a4ef82f9da793c0a83cd58f6388991dd38f7a5f92947b2d089855b259af4e4a'
HOLD = ('Content-class operation held: production record/DOI reconciliation and '
        'reviewed class execution support are required; singleton routing is forbidden')


def _pinned(path, expected):
    try:
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Finite content-class evidence changed')
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError('Finite content-class evidence missing or invalid') from exc


def load_representation():
    """Check live evidence on every call; missing authority cannot disable a gate."""
    representation = _pinned(REPRESENTATION_PATH, REPRESENTATION_SHA256)
    mapping = _pinned(MAP_PATH, MAP_SHA256)
    _pinned(AUTHORITY_PATH, AUTHORITY_SHA256)
    classes = representation['classes']
    mapped = {group['canonical_content_id']: group for group in mapping['groups']}
    members = [sid for row in classes for sid in row['source_ids']]
    if (len(classes) != 228 or len(mapped) != 228 or len(members) != 456
            or len(set(members)) != 456):
        raise ValueError('Finite content-class membership is incomplete or overlapping')
    for row in classes:
        old = mapped[row['record_target_id']]
        if (row['record_target_id'] != 'sha256:' + row['source_sha256']
                or row['source_ids'] != sorted(old['equivalence_group_members'])
                or row['source_filenames'] != [sid + '.xml' for sid in row['source_ids']]
                or len(row['source_ids']) != 2
                or any(row[key] is not None for key in (
                    'canonical_source_id', 'canonical_catalogue_record_id',
                    'canonical_provider_record_id', 'canonical_provider_doi'))):
            raise ValueError('Finite content-class identity differs from original evidence')
    return representation


def require_singleton_operation(source_id=None, entry=None, json_file=None, paths=None):
    """Refuse protected identities from *any* binding, including renamed raw bytes.

    No caller flag, environment, approval or invented reconciliation receipt can
    activate a class. This is an operation boundary, not a source-assessment rule.
    """
    rows = load_representation()['classes']
    ids = {sid for row in rows for sid in row['source_ids']}
    hashes = {row['source_sha256'] for row in rows}
    markers = {'record_target_id', 'identity_kind', 'representation_manifest_sha256',
               'member_set_sha256', 'canonical_content_id', 'members', 'source_ids',
               'source_filenames', 'equivalence_group_members'}
    scalar_keys = {'source_id', 'fgdc_id', 'source_sha256', 'sha256', 'name',
                   'source_filename', 'source_path', 'json_file', 'fgdc_file',
                   'content_canonical_sha256', 'confirmed_fgdc_id', 'confirmed_source_sha256'}
    containers = {'artifact_contract', 'artifact_policy', 'members', 'source_ids',
                  'source_filenames', 'files', 'equivalence_group_members', 'registry_entry',
                  'upload_log_entry'}

    json_paths, source_paths, selected_ids, remote_ids = set(), set(), set(), set()

    def check_scalar(value):
        if isinstance(value, str):
            stem = Path(value).stem
            if stem in ids or value in hashes or value.startswith(('sha256:', 'XMLCLASS-')):
                raise ValueError(HOLD)

    def check_object(value):
        if isinstance(value, list):
            for item in value:
                check_object(item)
        elif isinstance(value, dict):
            if markers.intersection(value) or value.get('object_kind') in (
                    'original_fgdc_xml_content_class', 'exact_xml_content_class'):
                raise ValueError(HOLD)
            if type(value.get('deposition_id')) is int and value['deposition_id'] > 0:
                remote_ids.add(value['deposition_id'])
            for key, item in value.items():
                if (key in ('artifact_contract', 'artifact_policy') and isinstance(item, dict)
                        and item.get('schema_version') != 1):
                    raise ValueError(HOLD)
                if key in scalar_keys:
                    check_scalar(item)
                    if isinstance(item, str):
                        if key == 'json_file':
                            json_paths.add(item)
                        elif key in ('fgdc_file', 'source_path'):
                            source_paths.add(item)
                        elif key in ('source_id', 'fgdc_id', 'confirmed_fgdc_id'):
                            selected_ids.add(Path(item).stem)
                if key in containers:
                    check_object(item)
        else:
            check_scalar(value)

    check_scalar(source_id)
    if source_id is not None:
        selected_ids.add(Path(str(source_id)).stem)
    check_object(entry)
    if json_file is not None:
        json_paths.add(str(json_file))
    registry = {}
    if paths is not None:
        registry_path = Path(paths.uploads_registry_path)
        if registry_path.is_file():
            registry = json.loads(registry_path.read_bytes())
            if not isinstance(registry, dict):
                raise ValueError('Malformed selected-source registry')
    # Inspect every supplied binding AND the selected on-disk history. A caller
    # may not erase identity evidence by projecting a ledger row onto old fields.
    seen_ids, seen_json, seen_sources, seen_remote = set(), set(), set(), set()
    while (selected_ids - seen_ids or json_paths - seen_json or source_paths - seen_sources
           or remote_ids - seen_remote):
        for remote_id in sorted(remote_ids - seen_remote):
            seen_remote.add(remote_id)
            selected_ids.update(sid for sid, row in registry.items()
                                if not sid.startswith('_') and isinstance(row, dict)
                                and row.get('deposition_id') == remote_id)
        for sid in sorted(selected_ids - seen_ids):
            seen_ids.add(sid)
            check_scalar(sid)
            if sid in registry:
                if not isinstance(registry[sid], dict):
                    raise ValueError('Malformed selected-source registry entry')
                check_object(registry[sid])
            if paths is not None:
                json_paths.add(str(Path(paths.zenodo_json_dir) / (sid + '.json')))
        for candidate in sorted(json_paths - seen_json):
            seen_json.add(candidate)
            check_scalar(candidate)
            path = Path(candidate)
            selected_ids.add(path.stem)
            if path.is_file():
                check_object(json.loads(path.read_bytes()))
            if paths is not None:
                original = locate_fgdc_xml(path.stem, paths)
                if original:
                    source_paths.add(original)
        for candidate in sorted(source_paths - seen_sources):
            seen_sources.add(candidate)
            check_scalar(candidate)
            original = Path(candidate)
            selected_ids.add(original.stem)
            if original.is_file() and hashlib.sha256(original.read_bytes()).hexdigest() in hashes:
                raise ValueError(HOLD)


def preflight_inputs(paths, json_files=None):
    """Reject a selected batch before a wrapper constructs a probing client."""
    selected = (sorted(Path(paths.zenodo_json_dir).glob('*.json'))
                if json_files is None else json_files)
    for filename in selected:
        require_singleton_operation(json_file=filename, paths=paths)


def preflight_registry(paths, registry, source_ids=None):
    """Check selected successful entries; preserve unrelated historical rows."""
    for sid, entry in registry.items():
        if sid.startswith('_') or entry.get('upload_status') != 'success':
            continue
        if source_ids is None or sid in source_ids:
            require_singleton_operation(source_id=sid, entry=entry, paths=paths)


def _review_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed > datetime.now(timezone.utc):
            raise ValueError
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('Explicit timezone-aware nonfuture assessment time required') from exc


def _identity(row, reviewed_at):
    return {'schema_version': 1, 'object_kind': 'original_fgdc_xml_content_class',
            'identity_kind': 'exact_xml_content_class', **copy.deepcopy(row),
            'reviewed_at': reviewed_at,
            'representation_manifest_sha256': REPRESENTATION_SHA256,
            'identity_representation_status': 'approved',
            'production_reconciliation_status': 'pending',
            'execution_status': 'class_execution_not_implemented',
            'upload_eligible': False, 'remote_verified': False, 'publication_approved': False}


def prepare_class_target(record_target_id, paths, *, reviewed_at):
    """Prepare one local target from both actual files/policies; never choose a primary.

    Structural failures raise, so a caller emits a held row without a fabricated
    artifact. Valid artifacts with unsupported source semantics remain held.
    """
    from scripts.agent_qa import assess_source

    _review_time(reviewed_at)
    rows = load_representation()['classes']
    matches = [row for row in rows if row['record_target_id'] == record_target_id]
    if len(matches) != 1:
        raise ValueError('Target is outside the approved finite content classes')
    row = matches[0]
    target = _identity(row, reviewed_at)
    payloads, raw_files, members, assessments = [], [], [], []
    for sid, filename in zip(row['source_ids'], row['source_filenames'], strict=True):
        source = Path(paths.original_fgdc_dir) / filename
        payload_path = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw, payload_raw = source.read_bytes(), payload_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['source_sha256']:
            raise ValueError('Content-class original bytes changed')
        payload = json.loads(payload_raw)
        artifact = prepare_artifact(payload, source)
        if artifact is None:
            raise ValueError('Both members require their own reviewed XML artifact policy')
        member = {'source_id': sid, 'source_filename': filename,
                  'source_sha256': row['source_sha256'],
                  'payload_sha256': hashlib.sha256(payload_raw).hexdigest(),
                  'policy_sha256': fingerprint(payload['artifact_policy']),
                  'artifact_v1_sha256': artifact['sha256']}
        assessment = {'source_id': sid, 'source_semantic_status': 'held', 'hold_reasons': []}
        try:
            _, checked_hash, checked_artifact, _ = assess_source(str(payload_path), paths)
            if checked_hash != row['source_sha256'] or checked_artifact != artifact:
                raise ValueError('Member source changed during assessment')
            assessment['source_semantic_status'] = 'supported'
        except (ValueError, OSError) as exc:
            assessment['hold_reasons'].append(str(exc))
        if source.read_bytes() != raw or payload_path.read_bytes() != payload_raw:
            raise ValueError('Member source or payload changed during class preparation')
        members.append(member)
        assessments.append(assessment)
        payloads.append(payload)
        raw_files.append(raw)
    if raw_files[0] != raw_files[1] or payloads[0]['metadata'] != payloads[1]['metadata']:
        raise ValueError('Both complete member metadata objects and raw XML bytes must agree')
    classification = classify_content({
        'inventory_complete': True, 'reviewer': 'Codex offline class assembly; not release authority',
        'reviewed_at': reviewed_at,
        'rationale': 'Two original descriptive XML files, each bound to its own source policy',
        'files': [{'name': name, 'role': 'descriptive_metadata',
                   'evidence': 'Exact original XML bytes and validated member artifact policy'}
                  for name in row['source_filenames']]})
    contract = {'schema_version': 2, 'object_kind': 'original_fgdc_xml_content_class',
                'identity_kind': 'exact_xml_content_class', 'record_target_id': record_target_id,
                'representation_manifest_sha256': REPRESENTATION_SHA256,
                'members': members, 'member_set_sha256': fingerprint(members),
                'classification_sha256': fingerprint(classification),
                'files': [{'name': name, 'size': len(raw), 'sha256': row['source_sha256'],
                           'md5': hashlib.md5(raw, usedforsecurity=False).hexdigest(),
                           'role': 'descriptive_metadata'}
                          for name, raw in zip(row['source_filenames'], raw_files, strict=True)]}
    contract['sha256'] = fingerprint(contract)
    metadata = export_content_metadata(copy.deepcopy(payloads[0]['metadata']), classification)
    # Match singleton display-note newline handling; artifact hashes/copies still
    # bind untouched bytes from both originals, including their CRLF line endings.
    xml, _ = load_fgdc_xml(row['source_ids'][0], paths)
    metadata['notes'] = build_metadata_notes(metadata.get('notes', ''), xml)
    metadata['notes'] += ('\n\nOriginal XML content class: ' + record_target_id +
                         '. Both original source identities/files are retained: ' +
                         ', '.join(row['source_filenames']) +
                         '. The preserved XML text applies to both byte-identical originals; '
                         'no historical canonical source filename is selected. '
                         'Underlying research data are not included. Class artifact contract SHA-256: ' +
                         contract['sha256'])
    target.update(members=members, member_assessments=assessments,
                  common_source_metadata_sha256=fingerprint(payloads[0]['metadata']),
                  member_set_sha256=contract['member_set_sha256'],
                  source_semantic_status=('supported' if all(
                      item['source_semantic_status'] == 'supported' for item in assessments) else 'held'),
                  content_classification=classification, artifact_contract=contract, metadata=metadata,
                  metadata_sha256=fingerprint(metadata))
    return target


def validate_class_target(target, paths):
    """Rebuild against live evidence; a self-rehashed edited target is insufficient."""
    rebuilt = prepare_class_target(target['record_target_id'], paths, reviewed_at=target['reviewed_at'])
    if target != rebuilt:
        raise ValueError('Content-class target or current member evidence changed')
    return rebuilt


def build_target_view(paths, ledger_path, output_dir, *, reviewed_at, limit=None):
    """Write a separate target view and exact original copies in a fresh directory."""
    _review_time(reviewed_at)
    ledger = _pinned(ledger_path, SOURCE_LEDGER_SHA256)
    all_classes = load_representation()['classes']
    if limit is not None and (type(limit) is not int or not 1 <= limit <= len(all_classes)):
        raise ValueError('Target limit must be between 1 and 228 classes')
    selected = all_classes if limit is None else all_classes[:limit]
    output = Path(output_dir).resolve()
    if output.exists() or output.is_relative_to(Path(paths.zenodo_json_dir).resolve()):
        raise ValueError('Choose a fresh target directory outside legacy upload inputs')
    output.mkdir(parents=True)
    (output / 'class_payloads').mkdir()
    (output / 'originals').mkdir()
    rows, index = [], []
    for identity in selected:
        try:
            target = prepare_class_target(identity['record_target_id'], paths, reviewed_at=reviewed_at)
            for item in target['artifact_contract']['files']:
                raw = (Path(paths.original_fgdc_dir) / item['name']).read_bytes()
                if hashlib.sha256(raw).hexdigest() != item['sha256']:
                    raise ValueError('Original changed before target snapshot')
                (output / 'originals' / item['name']).write_bytes(raw)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            target = dict(_identity(identity, reviewed_at), source_semantic_status='held',
                          artifact_contract=None, hold_reasons=[str(exc)])
        name = 'XMLCLASS-' + identity['source_sha256'] + '.json'
        raw_target = (json.dumps(target, indent=2, ensure_ascii=False) + '\n').encode()
        (output / 'class_payloads' / name).write_bytes(raw_target)
        rows.append({key: target[key] for key in (
            'record_target_id', 'source_ids', 'source_sha256', 'canonical_source_id',
            'identity_representation_status', 'source_semantic_status',
            'production_reconciliation_status', 'upload_eligible', 'remote_verified',
            'publication_approved')} | {
                'payload_path': 'class_payloads/' + name,
                'payload_sha256': hashlib.sha256(raw_target).hexdigest(),
                'artifact_contract_sha256': (target.get('artifact_contract') or {}).get('sha256'),
                'member_assessments': target.get('member_assessments', []),
                'hold_reasons': target.get('hold_reasons', [])})
        index.extend({'source_id': sid, 'source_sha256': identity['source_sha256'],
                      'record_target_id': identity['record_target_id'], 'represented_by_class': True,
                      'canonical_source_id': None} for sid in identity['source_ids'])
    members = {sid for row in all_classes for sid in row['source_ids']}
    singletons = [{'record_target_id': row['source_id'], 'source_ids': [row['source_id']],
                   'source_sha256': row['source_sha256'], 'source_semantic_status': row['source_status']}
                  for row in ledger['records'] if row['source_id'] not in members]
    counts = Counter(row['source_semantic_status'] for row in rows)
    report = {'schema_version': 1, 'kind': 'offline_record_target_view', 'reviewed_at': reviewed_at,
              'source_ledger_sha256': SOURCE_LEDGER_SHA256,
              'representation_manifest_sha256': REPRESENTATION_SHA256,
              'legacy_source_ledger_changed': False, 'class_targets': rows, 'source_to_target': index,
              'summary': {'original_source_files': len(ledger['records']), 'class_targets': len(rows),
                          'represented_source_files': len(index), 'source_supported_classes': counts['supported'],
                          'source_held_classes': counts['held'], 'upload_eligible_classes': 0,
                          'complete_target_population': len(selected) == len(all_classes)}}
    if len(selected) == len(all_classes):
        total = Counter(row['source_semantic_status'] for row in singletons) + counts
        report['singleton_targets'] = singletons
        report['summary'].update(unique_record_targets=len(singletons) + len(rows),
                                 source_supported_targets=total['supported'],
                                 source_held_targets=total['held'], malformed_targets=total['failed'])
    (output / 'record_targets.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    from scripts.path_config import OutputPaths

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared-output', required=True, help='Existing source-only classification output')
    parser.add_argument('--source-ledger', required=True)
    parser.add_argument('--target-output', required=True, help='Fresh directory, outside legacy upload inputs')
    parser.add_argument('--reviewed-at', required=True)
    parser.add_argument('--limit', type=int, help='Number of whole classes, never a member-file limit')
    args = parser.parse_args()
    report = build_target_view(OutputPaths(args.prepared_output, 'sandbox'), args.source_ledger,
                               args.target_output, reviewed_at=args.reviewed_at, limit=args.limit)
    print(json.dumps(report['summary'], sort_keys=True))


if __name__ == '__main__':
    main()
