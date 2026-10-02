"""Resumable offline source-only classification using the current agent QA profile.

Does not fake upload ledgers, remote snapshots, duplicate absence or approvals.
Copies original bytes to a new task workspace; never edits original sources.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import socket
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch

from scripts.agent_qa import assess_source, _explicit_license
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, metadata_hash, read_json, prepare_metadata
from scripts.validate_zenodo import ZenodoValidator


def text(root, xpath):
    node = root.find(xpath)
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip() if node is not None else ''


def classify_collection(source_dir, output_dir, reviewed_at):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = OutputPaths(str(output), 'sandbox')
    rules = Path(__file__).parent
    # Conservative invalidation includes indirect validation/normalization helpers.
    profile_hash = metadata_hash({str(file.relative_to(rules)): hashlib.sha256(file.read_bytes()).hexdigest()
                                 for file in sorted(rules.rglob('*.py'))})
    prior = read_json(output / 'classification.json', {})
    cache = {row['source_id']: row for row in prior.get('records', [])} if prior.get('profile_sha256') == profile_hash and prior.get('reviewed_at') == reviewed_at else {}
    records, buckets = [], defaultdict(list)
    with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()), patch('scripts.validate_zenodo.get_logger', return_value=Mock()):
        transformer, validator = FGDCToZenodoTransformer(), ZenodoValidator()
        for source in sorted(Path(source_dir).glob('*.xml')):
            raw = source.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            buckets[digest].append(source.stem)
            cached = cache.get(source.stem)
            cache_valid = bool(cached and cached['source_sha256'] == digest)
            if cache_valid and cached['technical_metadata'] != 'not_constructed':
                source_copy = Path(paths.original_fgdc_dir) / source.name
                json_file = Path(paths.zenodo_json_dir) / (source.stem + '.json')
                try:
                    cache_valid = (hashlib.sha256(source_copy.read_bytes()).hexdigest() == digest
                                   and hashlib.sha256(json_file.read_bytes()).hexdigest() == cached.get('prepared_payload_sha256'))
                except OSError:
                    cache_valid = False
            if cache_valid:
                cached['source_status'] = cached.get('source_status_without_aliases', cached['source_status'])
                cached['hold_reasons'] = [reason for reason in cached['hold_reasons']
                                          if reason != 'Exact-copy aliases require identity adjudication']
                records.append(cached)
                continue
            row = {'source_id': source.stem, 'source_sha256': digest, 'source_status': 'held',
                   'technical_metadata': 'not_constructed', 'remote_verified': False,
                   'publication_approved': False, 'hold_reasons': []}
            try:
                root = ET.fromstring(raw)
            except ET.ParseError as exc:
                row.update(source_status='failed', parse_error=str(exc))
                records.append(row)
                continue
            primary_date = text(root, './idinfo/citation/citeinfo/pubdate')
            metadata_date = text(root, './metainfo/metd')
            title = text(root, './idinfo/citation/citeinfo/title')
            origins = [re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()
                       for node in root.findall('./idinfo/citation/citeinfo/origin')]
            metuc, metac = text(root, './metainfo/metuc'), text(root, './metainfo/metac')
            grant = _explicit_license(metuc)
            row.update(raw_primary_date=primary_date, raw_metadata_date=metadata_date,
                       raw_metadata_rights=metuc, raw_metadata_access=metac,
                       has_supported_xml_grant=bool(grant),
                       metadata_date_precision='day' if re.fullmatch(r'\d{8}|\d{4}-\d{2}-\d{2}', metadata_date) else 'unsupported',
                       primary_date_stratum='ambiguous_122003' if primary_date == '122003' else
                       'missing' if not primary_date else 'range_or_status' if re.search(r'Unknown|Present|thru|Planned|Unpublished|\d{4}\s*-\s*\d{4}', primary_date, re.I) else 'other',
                       origin_stratum='institutional_or_compound' if any(transformer._is_organization(name) for name in origins) else 'personal_or_unknown')
            if not grant:
                row['hold_reasons'].append('No exact XML-specific grant supported by the automatic profile')
            if metac.casefold().rstrip('.') not in ('', 'none', 'no restrictions', 'unrestricted', 'open', 'public'):
                row['hold_reasons'].append('Metadata access terms need source-backed adjudication')
            if row['metadata_date_precision'] != 'day':
                row['hold_reasons'].append('Metadata date lacks supported exact day precision')
            source_copy = Path(paths.original_fgdc_dir) / source.name
            source_copy.write_bytes(raw)
            policy = {'schema_version': 1, 'object_kind': 'original_fgdc_xml', 'resource_type': 'other',
                      'source_sha256': digest, 'date_semantics': 'source_metadata_date',
                      'reviewer': 'Codex offline source classifier; not release authority', 'reviewed_at': reviewed_at,
                      'rationale': 'Source-only classification; no live record approval',
                      'date_evidence': 'Source metainfo/metd: ' + metadata_date,
                      'rights_evidence': 'Exact source metainfo/metuc: ' + metuc + '; unresolved text is not a grant',
                      'rights_scope': 'original_fgdc_xml', 'rights_source_xpath': './metainfo/metuc', 'license': grant}
            classification = {'inventory_complete': True, 'reviewer': policy['reviewer'], 'reviewed_at': reviewed_at,
                              'rationale': 'Descriptive source XML only; no underlying data included',
                              'files': [{'name': source.name, 'role': 'descriptive_metadata', 'evidence': 'Parsed source descriptive fields'}]}
            transformer.active_decision = {'metadata': {'publication_date': metadata_date,
                'creators': [{'name': name, **({'type': 'Organization'} if transformer._is_organization(name) else {})}
                             for name in origins], 'license': grant or ''},
                'artifact_policy': policy, 'content_classification': classification}
            metadata = transformer._build_zenodo_metadata(root, str(source_copy)) if metadata_date else None
            if metadata:
                artifact_title = title + ' - FGDC XML metadata artifact'
                # The object contract/description identifies XML when the suffix would
                # push a valid source title beyond Zenodo's limit. Never truncate it.
                if len(artifact_title) > 250:
                    artifact_title = title
                abstract = text(root, './idinfo/descript/abstract') or title
                metadata.update(title=artifact_title, description=html.escape(abstract), communities=[],
                                access_right='open' if grant else 'restricted')
                row['routine_source_decisions'] = {
                    'title': 'exact source title' if artifact_title == title else 'exact source title plus artifact suffix',
                    'description': 'HTML-escaped exact source abstract, or title if abstract absent',
                    'date': 'explicit metadata creation/last-update day; not dataset publication',
                    'creators': 'primary dataset citation preserved; XML authorship not independently established'}
                if not grant:
                    metadata['access_conditions'] = 'Offline preparation only; no public release approved.'
                json_file = Path(paths.zenodo_json_dir) / (source.stem + '.json')
                atomic_json(json_file, {'metadata': metadata, 'artifact_policy': policy,
                                        'content_classification': classification})
                row['prepared_payload_sha256'] = hashlib.sha256(json_file.read_bytes()).hexdigest()
                try:
                    submitted = prepare_metadata(str(json_file), paths)[0]
                    issues, _ = validator.validate_metadata(submitted)
                    row['technical_metadata'] = 'pass' if not issues else 'held'
                    if issues:
                        row['hold_reasons'].extend(issues)
                    assessed, _, _, _ = assess_source(str(json_file), paths)
                    row.update(source_status='supported', metadata_sha256=metadata_hash(assessed))
                except (ValueError, OSError, ET.ParseError) as exc:
                    row['hold_reasons'].append(str(exc))
            else:
                row['hold_reasons'].append('Metadata artifact construction requires source/date/creator adjudication')
            records.append(row)
            if len(records) % 250 == 0:
                atomic_json(output / 'classification.json', {'profile_sha256': profile_hash, 'reviewed_at': reviewed_at, 'records': records})
                print(f'Classified {len(records)} source files', flush=True)
    groups = [aliases for aliases in buckets.values() if len(aliases) > 1]
    duplicate_sources = {sid for aliases in groups for sid in aliases}
    for row in records:
        row['source_status_without_aliases'] = row['source_status']
        row['exact_copy_aliases'] = buckets[row['source_sha256']] if row['source_id'] in duplicate_sources else []
        if row['exact_copy_aliases']:
            row['hold_reasons'] = list(dict.fromkeys(row['hold_reasons'] + ['Exact-copy aliases require identity adjudication']))
            if row['source_status'] == 'supported':
                row['source_status'] = 'held'
    counts = dict.fromkeys(('supported', 'held', 'failed'), 0)
    counts.update(Counter(row['source_status'] for row in records))
    summary = {'source_files': len(records), 'source_status_counts': counts,
               'technical_metadata_counts': dict(Counter(row['technical_metadata'] for row in records)),
               'exact_copy_groups': len(groups), 'files_in_copy_groups': len(duplicate_sources),
               'unique_raw_contents': len(buckets), 'publication_approved': 0, 'remote_verified': 0,
               'coverage': 'Every raw file hashed; strict source-only agent profile on constructed XML artifacts; no recovery or remote/API/duplicate-service assessment'}
    report = {'profile_sha256': profile_hash, 'reviewed_at': reviewed_at, 'summary': summary, 'records': records}
    atomic_json(output / 'classification.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', default='FGDC')
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--reviewed-at', default=datetime.now(timezone.utc).isoformat(), help='Repeat same run timestamp to resume unchanged evidence')
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline classification')):
        report = classify_collection(args.source_dir, args.output_dir, args.reviewed_at)
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
