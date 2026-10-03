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

from scripts.agent_qa import assess_source, _explicit_license, _citation_organization
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, metadata_hash, read_json, prepare_metadata
from scripts.validate_zenodo import ZenodoValidator
from scripts.source_access_interpretation import validate_interpretation, CONTRIBUTOR_WORDING
from scripts.citation_creator_interpretation import validate_creator_interpretation
from scripts.source_link_interpretation import validate_source_link_interpretation, apply_source_link_interpretation
from scripts.source_title_interpretation import (validate_source_title_interpretation,
    apply_source_title_interpretation)
from scripts.dataset_access_interpretation import (validate_dataset_access_interpretation,
    dataset_access_member_ids, REGISTRATION_WORDING)


def text(root, xpath):
    node = root.find(xpath)
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip() if node is not None else ''


def classify_collection(source_dir, output_dir, reviewed_at, authority_manifest=None, access_interpretation_manifest=None, creator_interpretation_manifest=None, dataset_access_interpretation_manifest=None, contributor_access_interpretation_manifest=None, collective_creator_interpretation_manifest=None, institution_creator_interpretation_manifest=None, source_link_interpretation_manifest=None, source_title_interpretation_manifest=None):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = OutputPaths(str(output), 'sandbox')
    rules = Path(__file__).parent
    # Conservative invalidation includes indirect validation/normalization helpers.
    authority_reference = ({'manifest_path': str(authority_manifest),
                            'manifest_sha256': hashlib.sha256(Path(authority_manifest).read_bytes()).hexdigest()}
                           if authority_manifest else None)
    access_reference = None
    if access_interpretation_manifest:
        try:
            access_digest = hashlib.sha256(Path(access_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            access_digest = None  # Missing evidence is a source hold, not an exception to the rule.
        access_reference = {'manifest_path': str(access_interpretation_manifest), 'manifest_sha256': access_digest}
    contributor_reference = None
    if contributor_access_interpretation_manifest:
        try:
            contributor_digest = hashlib.sha256(Path(contributor_access_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            contributor_digest = None
        contributor_reference = {'manifest_path': str(contributor_access_interpretation_manifest),
                                 'manifest_sha256': contributor_digest}
    creator_reference = None
    if creator_interpretation_manifest:
        try:
            creator_digest = hashlib.sha256(Path(creator_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            creator_digest = None
        creator_reference = {'manifest_path': str(creator_interpretation_manifest), 'manifest_sha256': creator_digest}
    collective_reference = None
    if collective_creator_interpretation_manifest:
        try:
            collective_digest = hashlib.sha256(Path(collective_creator_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            collective_digest = None
        collective_reference = {'manifest_path': str(collective_creator_interpretation_manifest),
                                'manifest_sha256': collective_digest}
    institution_reference = None
    if institution_creator_interpretation_manifest:
        try:
            institution_digest = hashlib.sha256(Path(institution_creator_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            institution_digest = None
        institution_reference = {'manifest_path': str(institution_creator_interpretation_manifest),
                                 'manifest_sha256': institution_digest}
    dataset_access_reference = None
    source_link_reference = None
    if source_link_interpretation_manifest:
        try:
            link_digest = hashlib.sha256(Path(source_link_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            link_digest = None
        source_link_reference = {'manifest_path': str(source_link_interpretation_manifest),
                                 'manifest_sha256': link_digest}
    if dataset_access_interpretation_manifest:
        try:
            dataset_access_digest = hashlib.sha256(Path(dataset_access_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            dataset_access_digest = None
        dataset_access_reference = {'manifest_path': str(dataset_access_interpretation_manifest),
                                    'manifest_sha256': dataset_access_digest}
    title_reference = None
    if source_title_interpretation_manifest:
        try:
            title_digest = hashlib.sha256(Path(source_title_interpretation_manifest).read_bytes()).hexdigest()
        except OSError:
            title_digest = None
        title_reference = {'manifest_path': str(source_title_interpretation_manifest),
                           'manifest_sha256': title_digest}
    dataset_access_members = dataset_access_member_ids(dataset_access_reference) if dataset_access_reference else frozenset()
    profile_hash = metadata_hash({'rules': {str(file.relative_to(rules)): hashlib.sha256(file.read_bytes()).hexdigest()
                                 for file in sorted(rules.rglob('*.py'))},
                                 'authority_reference': authority_reference, 'access_reference': access_reference,
                                 'creator_reference': creator_reference, 'collective_reference': collective_reference,
                                 'institution_reference': institution_reference,
                                 'source_link_reference': source_link_reference,
                                 'source_title_reference': title_reference,
                                 'contributor_reference': contributor_reference,
                                 'dataset_access_reference': dataset_access_reference})
    prior = read_json(output / 'classification.json', {})
    cache = {row['source_id']: row for row in prior.get('records', [])} if prior.get('profile_sha256') == profile_hash and prior.get('reviewed_at') == reviewed_at else {}
    records, buckets = [], defaultdict(list)
    with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()), patch('scripts.validate_zenodo.get_logger', return_value=Mock()):
        transformer, validator = FGDCToZenodoTransformer(), ZenodoValidator()
        for source in sorted(Path(source_dir).glob('*.xml')):
            raw = source.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            buckets[digest].append(source.stem)
            source_copy = Path(paths.original_fgdc_dir) / source.name
            json_file = Path(paths.zenodo_json_dir) / (source.stem + '.json')
            cached = cache.get(source.stem)
            cache_valid = bool(cached and cached.get('source_sha256') == digest)
            if cache_valid:
                try:
                    cache_valid = (hashlib.sha256(source_copy.read_bytes()).hexdigest() == digest
                                   and hashlib.sha256(json_file.read_bytes()).hexdigest() == cached.get('prepared_payload_sha256'))
                except OSError:
                    cache_valid = False
            # Only reuse verified construction bytes. Cached semantic verdicts,
            # provenance and release flags are derived evidence, never authority.
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
            interpreted_creators = None
            creator_preservation_notes = []
            selected_creator_reference = None
            legacy_reference = collective_reference if origins == ['DFO Staff'] else creator_reference
            for reference in (institution_reference, legacy_reference):
                if reference is None:
                    continue
                try:
                    creator_result = validate_creator_interpretation(reference, source.stem, digest, root, True)
                    interpreted_creators = creator_result['creators']
                    creator_preservation_notes = creator_result['preservation_notes']
                    selected_creator_reference = reference
                    row.pop('creator_interpretation_diagnostic', None)
                    break
                except ValueError as exc:
                    # Outside this pinned cohort, retain the conservative default.
                    row['creator_interpretation_diagnostic'] = str(exc)
            if institution_reference or legacy_reference:
                row['creator_interpretation'] = 'source_primary_citation_attribution' if interpreted_creators else 'not_established'
            interpreted_link = None
            if source_link_reference:
                try:
                    interpreted_link = validate_source_link_interpretation(source_link_reference, source.stem, digest, root)
                except ValueError as exc:
                    row['source_link_interpretation_diagnostic'] = str(exc)
                row['source_link_interpretation'] = 'SOURCE_BACKED' if interpreted_link else 'not_established'
            interpreted_title = None
            if title_reference:
                try:
                    interpreted_title = validate_source_title_interpretation(title_reference, source.stem, digest, root)
                except ValueError as exc:
                    row['source_title_interpretation_diagnostic'] = str(exc)
                row['source_title_interpretation'] = 'SOURCE_BACKED' if interpreted_title else 'not_established'
            metuc, metac = text(root, './metainfo/metuc'), text(root, './metainfo/metac')
            grant = _explicit_license(metuc)
            authority = None
            if authority_reference:
                from scripts.rehosting_authority import validate_authority
                try:
                    authority = validate_authority(authority_reference, source.stem, digest)
                except (ValueError, OSError) as exc:
                    row['hold_reasons'].append(str(exc))
            row['rehosting_authority'] = 'USER_ATTESTED' if authority else 'not_established'
            row['new_reuse_license'] = 'not_granted_by_rehosting_attestation'
            if authority:
                grant = None  # Restoration authority never assigns or imports a license.
            interpreted_access = None
            selected_access_reference = (access_reference if metac == 'Contact Source.' else
                                         contributor_reference if metac == CONTRIBUTOR_WORDING else None)
            if selected_access_reference:
                try:
                    if not authority:
                        raise ValueError('Access interpretation requires separate rehosting authority')
                    interpreted_access = validate_interpretation(selected_access_reference, source.stem, digest, root, reviewed_at)
                except ValueError as exc:
                    row['hold_reasons'].append(str(exc))
                row['source_access_interpretation'] = 'USER_ATTESTED' if interpreted_access else 'not_established'
            interpreted_dataset_access = None
            if dataset_access_reference and (metac == REGISTRATION_WORDING or source.stem in dataset_access_members):
                try:
                    if not authority:
                        raise ValueError('Dataset access interpretation requires separate rehosting authority')
                    if interpreted_access:
                        raise ValueError('Conflicting access interpretations require separate adjudication')
                    interpreted_dataset_access = validate_dataset_access_interpretation(
                        dataset_access_reference, source.stem, digest, root)
                except ValueError as exc:
                    row['hold_reasons'].append(str(exc))
                row['dataset_access_interpretation'] = 'SOURCE_BACKED' if interpreted_dataset_access else 'not_established'
            row.update(raw_primary_date=primary_date, raw_metadata_date=metadata_date,
                       raw_metadata_rights=metuc, raw_metadata_access=metac,
                       has_supported_xml_grant=bool(grant),
                       metadata_date_precision='day' if re.fullmatch(r'\d{8}|\d{4}-\d{2}-\d{2}', metadata_date) else 'unsupported',
                       primary_date_stratum='ambiguous_122003' if primary_date == '122003' else
                       'missing' if not primary_date else 'range_or_status' if re.search(r'Unknown|Present|thru|Planned|Unpublished|\d{4}\s*-\s*\d{4}', primary_date, re.I) else 'other',
                       origin_stratum='institutional_or_compound' if any(_citation_organization(name, transformer) for name in origins) else 'personal_or_unknown')
            if not grant and not authority:
                row['hold_reasons'].append('No exact XML-specific grant supported by the automatic profile')
            if not interpreted_access and not interpreted_dataset_access and metac.casefold().rstrip('.') not in ('', 'none', 'no restrictions', 'unrestricted', 'open', 'public'):
                row['hold_reasons'].append('Metadata access terms need source-backed adjudication')
            if row['metadata_date_precision'] != 'day':
                row['hold_reasons'].append('Metadata date lacks supported exact day precision')
            policy = {'schema_version': 1, 'object_kind': 'original_fgdc_xml', 'resource_type': 'other',
                      'source_sha256': digest, 'date_semantics': 'source_metadata_date',
                      'reviewer': 'Codex offline source classifier; not release authority', 'reviewed_at': reviewed_at,
                      'rationale': 'Source-only classification; no live record approval',
                      'date_evidence': 'Source metainfo/metd: ' + metadata_date,
                      'rights_evidence': 'Exact source metainfo/metuc: ' + metuc + '; unresolved text is not a grant',
                      'rights_scope': 'original_fgdc_xml', 'rights_source_xpath': './metainfo/metuc', 'license': grant}
            if authority:
                policy['rehosting_authority'] = authority_reference
                policy['rights_evidence'] = ('Brett user-attested historical GeoNetwork restoration authority; '
                                             'not an independently verified agreement or new license. '
                                             'Original source constraints preserved: ' + metuc)
            if interpreted_access:
                policy['source_access_interpretation'] = selected_access_reference
            if interpreted_dataset_access:
                policy['dataset_access_interpretation'] = dataset_access_reference
            if interpreted_creators:
                policy['creator_interpretation'] = selected_creator_reference
            if interpreted_link:
                policy['source_link_interpretation'] = source_link_reference
            if interpreted_title:
                policy['source_title_interpretation'] = title_reference
            classification = {'inventory_complete': True, 'reviewer': policy['reviewer'], 'reviewed_at': reviewed_at,
                              'rationale': 'Descriptive source XML only; no underlying data included',
                              'files': [{'name': source.name, 'role': 'descriptive_metadata', 'evidence': 'Parsed source descriptive fields'}]}
            if cache_valid:
                cached_payload = read_json(json_file)
                # A matching editable payload hash cannot select dataset rights
                # or discard the collection's current attested XML policy.
                cache_valid = (isinstance(cached_payload, dict)
                               and isinstance(cached_payload.get('metadata'), dict)
                               and cached_payload.get('artifact_policy') == policy
                               and cached_payload.get('content_classification') == classification)
            if not cache_valid:
                source_copy.write_bytes(raw)
            transformer.active_decision = {'metadata': {'publication_date': metadata_date,
                'creators': interpreted_creators or [{'name': name, **({'type': 'Organization'} if _citation_organization(name, transformer) else {})}
                             for name in origins], 'license': grant or ''},
                'artifact_policy': policy, 'content_classification': classification}
            metadata = (cached_payload['metadata'] if cache_valid else
                        transformer._build_zenodo_metadata(root, str(source_copy))) if metadata_date else None
            if metadata:
                artifact_title = title + ' - FGDC XML metadata artifact'
                # The object contract/description identifies XML when the suffix would
                # push a valid source title beyond Zenodo's limit. Never truncate it.
                if len(artifact_title) > 250:
                    artifact_title = title
                abstract = text(root, './idinfo/descript/abstract') or title
                row['routine_source_decisions'] = {
                    'title': 'reviewed source display title with complete original preservation' if interpreted_title else
                             'exact source title' if artifact_title == title else 'exact source title plus artifact suffix',
                    'description': 'HTML-escaped exact source abstract, or title if abstract absent',
                    'date': 'explicit metadata creation/last-update day; not dataset publication',
                    'creators': 'primary dataset citation preserved; XML authorship not independently established'}
                if not cache_valid:
                    metadata.update(title=artifact_title, description=html.escape(abstract), communities=[],
                                    access_right='open' if grant else 'restricted')
                    if creator_preservation_notes:
                        metadata['notes'] += ''.join('\n' + note for note in creator_preservation_notes)
                    elif (interpreted_creators and selected_creator_reference == institution_reference
                            and [creator['name'] for creator in interpreted_creators] != origins):
                        # Exact reviewed joint credits retain the unparsed source
                        # citation alongside the corrected creator list.
                        metadata['notes'] += '\nOriginal primary citation origin: ' + root.find(
                            './idinfo/citation/citeinfo/origin').text
                    if not grant:
                        if authority:
                            from scripts.rehosting_authority import AUTHORITY_ACCESS_CONDITIONS
                            metadata['access_conditions'] = AUTHORITY_ACCESS_CONDITIONS
                            metadata['notes'] += ('\nSource dataset citation originators are preserved for attribution; '
                                                  'XML authorship is not independently established.')
                        else:
                            metadata['access_conditions'] = 'Offline preparation only; no public release approved.'
                    if interpreted_link:
                        try:
                            metadata = apply_source_link_interpretation(interpreted_link, metadata)
                        except ValueError as exc:
                            row['hold_reasons'].append(str(exc))
                    if interpreted_title:
                        try:
                            metadata = apply_source_title_interpretation(interpreted_title, metadata)
                        except ValueError as exc:
                            row['hold_reasons'].append(str(exc))
                    atomic_json(json_file, {'metadata': metadata, 'artifact_policy': policy,
                                            'content_classification': classification})
                row['prepared_payload_sha256'] = hashlib.sha256(json_file.read_bytes()).hexdigest()
                try:
                    submitted = prepare_metadata(str(json_file), paths)[0]
                    issues, _ = validator.validate_metadata(submitted)
                    row['technical_metadata'] = 'pass' if not issues else 'held'
                    if issues:
                        row['hold_reasons'].extend(issues)
                    if authority_reference and not authority:
                        raise ValueError('Requested rehosting authority does not cover this exact source')
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
               'rehosting_authority_counts': dict(Counter(row.get('rehosting_authority', 'parse_failed') for row in records)),
               'coverage': 'Every raw file hashed; strict source-only agent profile on constructed XML artifacts; no recovery or remote/API/duplicate-service assessment'}
    report = {'profile_sha256': profile_hash, 'reviewed_at': reviewed_at, 'summary': summary, 'records': records}
    atomic_json(output / 'classification.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', default='FGDC')
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--authority-manifest', help='Source-hash-bound user attestation; grants rehosting, never a new license')
    parser.add_argument('--access-interpretation-manifest', help='Exact Contact Source. dataset-acquisition interpretation; no license or release grant')
    parser.add_argument('--contributor-access-interpretation-manifest', help='Exact source-bound Contributor or Source attestation; no license or release grant')
    parser.add_argument('--creator-interpretation-manifest', help='Pinned Exxon primary citation attribution; no XML authorship or rights grant')
    parser.add_argument('--dataset-access-interpretation-manifest', help='Pinned finite source-backed data acquisition meaning; no authority or license grant')
    parser.add_argument('--collective-creator-interpretation-manifest', help='Pinned literal DFO Staff collective citation; no person, affiliation or institutional type inference')
    parser.add_argument('--institution-creator-interpretation-manifest', help='Pinned institution/program or reviewed joint/collection citation profile; exact full creator objects')
    parser.add_argument('--source-link-interpretation-manifest', help='Pinned historical shared dataset linkage preservation; no XML identity or replacement relation')
    parser.add_argument('--source-title-interpretation-manifest', help='Pinned eight source display titles with full original context and complete before/after metadata')
    parser.add_argument('--reviewed-at', default=datetime.now(timezone.utc).isoformat(), help='Repeat same run timestamp to resume unchanged evidence')
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline classification')):
        report = classify_collection(args.source_dir, args.output_dir, args.reviewed_at, args.authority_manifest,
                                     args.access_interpretation_manifest, args.creator_interpretation_manifest,
                                     args.dataset_access_interpretation_manifest, args.contributor_access_interpretation_manifest,
                                     args.collective_creator_interpretation_manifest,
                                     args.institution_creator_interpretation_manifest,
                                     args.source_link_interpretation_manifest,
                                     args.source_title_interpretation_manifest)
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
