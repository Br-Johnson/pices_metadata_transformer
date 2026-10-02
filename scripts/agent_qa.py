"""Conservative offline, source-backed record QA. No service calls or publication.

Agent assessment is not a release authorization or independent program review.
Unsupported semantics remain held, rather than being inferred from a successful upload.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from scripts.artifact_contract import prepare_artifact, assert_artifact_binding, validate_files
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.path_config import OutputPaths
from scripts.qa_manifest import QA_CHECKS
from scripts.upload_service import (assert_environment, atomic_json, expected_host,
                                    metadata_hash, prepare_metadata, read_json,
                                    validate_deposition_response, validate_registry_identities)
from scripts.validate_zenodo import ZenodoValidator
from scripts.verify_uploads import compare_metadata
from scripts.matching.evidence import snapshot_inventory
from scripts.rehosting_authority import validate_authority, validate_restricted_metadata
from scripts.source_access_interpretation import validate_interpretation


def _text(root, path):
    node = root.find(path)
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip() if node is not None else ''


def _explicit_license(text):
    """Recognize a complete explicit grant label; free prose needs adjudication."""
    text = text.strip()
    if not re.fullmatch(r'(?:CC0|CC[- ]BY(?:[- ](?:NC|ND|SA)){0,2}[- ]+[1-4]\.0|'
                        r'https://creativecommons\.org/(?:licenses/[a-z-]+/[1-4]\.0/|publicdomain/zero/1\.0/))',
                        text, re.IGNORECASE):
        return None
    return FGDCToZenodoTransformer()._detect_license(text, 'offline agent QA')


def _citation_organization(name, transformer):
    """Recognize the reviewed citation name without changing contact formatting."""
    return name == 'Washington Sea Grant Program' or transformer._is_organization(name)


def _timestamp(value):
    if not isinstance(value, str) or not value:
        raise ValueError('Evidence timestamp is missing or malformed')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError('Evidence timestamp must be timezone-aware and not in the future')
    if datetime.now(timezone.utc) - stamp > timedelta(hours=24):
        raise ValueError('Saved repository response is stale; maximum evidence age is 24 hours')
    return stamp


def assess_source(json_file, paths):
    """Source-only profile assessment; no remote identity, duplicate or release approval."""
    metadata, source_path, source_hash = prepare_metadata(json_file, paths)
    payload = read_json(json_file)
    artifact = prepare_artifact(payload, source_path)
    issues, _ = ZenodoValidator().validate_metadata(metadata)
    if issues:
        raise ValueError('Invalid transformed metadata: ' + '; '.join(issues))
    root = ET.parse(source_path).getroot()
    title = _text(root, './idinfo/citation/citeinfo/title') or _text(root, './title')
    abstract = _text(root, './idinfo/descript/abstract') or title
    visible_description = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', metadata.get('description', ''))))
    allowed_titles = (title, title + ' - FGDC XML metadata artifact') if artifact else (title,)
    if not title or metadata.get('title') not in allowed_titles or not abstract or abstract not in visible_description:
        raise ValueError('Source title/description fidelity is not supported')
    origins = root.findall('./idinfo/citation/citeinfo/origin')
    if not origins:
        raise ValueError('Citation creators missing; contacts are not proven authors')
    names = [re.sub(r'\s+', ' ', ''.join(node.itertext())).strip() for node in origins]
    # Do not split ambiguous lists, initials, mixed XML or infer a creator from contacts.
    transformer = FGDCToZenodoTransformer()
    expected = []
    for node, name in zip(origins, names):
        # The reviewed institutional name is not a surname in a comma-separated
        # institution/person compound; keep appended identities for adjudication.
        if name.startswith('Washington Sea Grant Program') and name != 'Washington Sea Grant Program':
            raise ValueError('Creator semantics are ambiguous')
        organization = _citation_organization(name, transformer)
        if (list(node) or not name or '\n' in ''.join(node.itertext()) or ';' in name
                or (organization and re.search(r',\s*[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:of|and)\b', name))
                or (not organization and not re.fullmatch(r"[A-Za-z][A-Za-z' -]+, [A-Za-z][A-Za-z' -]+", name))):
            raise ValueError('Creator semantics are ambiguous')
        expected.append({'name': name, **({'type': 'Organization'} if organization else {})})
    if compare_metadata({'creators': expected}, {'creators': metadata.get('creators')}):
        raise ValueError('Creator order/name/type differs from primary citation')
    interpreted_access = False
    if artifact:
        policy = payload['artifact_policy']
        authority = policy.get('rehosting_authority')
        if (policy.get('rights_scope') != 'original_fgdc_xml'
                or policy.get('rights_source_xpath') != './metainfo/metuc'
                or policy.get('date_semantics') != 'source_metadata_date'):
            raise ValueError('XML-specific source-backed rights/date policy is required')
        grant = _text(root, './metainfo/metuc')
        prefix = 'Original FGDC XML metadata: '
        # FGDC metuc is metadata-use constraints; useconst is the underlying resource's rights.
        license_id = _explicit_license(grant[len(prefix):] if grant.startswith(prefix) else grant)
        if authority is not None:
            validate_authority(authority, Path(source_path).stem, source_hash)
            validate_restricted_metadata(metadata)
            if policy.get('license') not in ('', None):
                raise ValueError('Rehosting attestation cannot grant a policy license')
        elif policy.get('license') != license_id:
            raise ValueError('XML policy license differs from explicit XML grant')
        date_text = _text(root, './metainfo/metd')
        access_constraints = _text(root, './metainfo/metac')
        if policy.get('source_access_interpretation') is not None:
            if authority is None:
                raise ValueError('Access interpretation requires separate rehosting authority')
            validate_interpretation(policy['source_access_interpretation'], Path(source_path).stem,
                                    source_hash, root, policy.get('reviewed_at'))
            interpreted_access = True
    else:
        authority = None
        license_id = _explicit_license(_text(root, './idinfo/useconst'))
        date_text = _text(root, './idinfo/citation/citeinfo/pubdate')
        access_constraints = _text(root, './idinfo/accconst')
    if not interpreted_access and access_constraints.strip().casefold().rstrip('.') not in ('', 'none', 'no restrictions', 'unrestricted', 'open', 'public'):
        raise ValueError('Contradictory or unsupported source access constraints require adjudication')
    if authority is None and (not license_id or license_id != metadata.get('license')):
        raise ValueError('Unknown or unsupported source rights; no inferred grant')
    if authority is None and metadata.get('access_right') != 'open':
        raise ValueError('Restricted/embargoed rights need separate adjudication')
    if not re.fullmatch(r'\d{8}|\d{4}-\d{2}-\d{2}', date_text):
        raise ValueError('Exact source-backed date required; ambiguous precision is held')
    normalized_date = transformer._normalize_date(date_text, 'offline agent QA')
    if not normalized_date or normalized_date != metadata.get('publication_date'):
        raise ValueError('Date differs from explicit source date or is unsupported')
    # Relations cannot be inferred: this automated slice supports no outgoing relations.
    if metadata.get('related_identifiers'):
        raise ValueError('Relations require explicit record-level adjudication')
    return metadata, source_hash, artifact, title


def assess(entry, paths, snapshot_path, duplicate_path):
    """Return reproducible evidence only when every source-backed check succeeds."""
    assert_environment(entry, paths.environment)
    if entry.get('upload_status') != 'success' or entry.get('needs_reconciliation'):
        raise ValueError('Successful reconciled draft required')
    metadata, source_path, source_hash = prepare_metadata(entry['json_file'], paths)
    payload = read_json(entry['json_file'])
    artifact = prepare_artifact(payload, source_path)
    assert_artifact_binding(entry, artifact)
    if source_hash != entry.get('source_sha256') or metadata_hash(metadata) != entry.get('metadata_sha256'):
        raise ValueError('Source or metadata differs from uploaded ledger binding')
    registry = read_json(paths.uploads_registry_path, {})
    if any(key != Path(entry['json_file']).stem and not key.startswith('_')
           and other.get('source_sha256') == source_hash for key, other in registry.items()):
        raise ValueError('Another local source identity shares these exact source bytes; duplicate adjudication required')
    checked_metadata, checked_hash, checked_artifact, title = assess_source(entry['json_file'], paths)
    if checked_metadata != metadata or checked_hash != source_hash or checked_artifact != artifact:
        raise ValueError('Source changed during assessment')
    snapshot = read_json(snapshot_path)
    if not isinstance(snapshot, dict):
        raise ValueError('Saved remote snapshot must be an object')
    endpoint = urlparse(snapshot.get('endpoint', ''))
    identifier = entry['deposition_id']
    if (snapshot.get('http_status') != 200 or endpoint.scheme != 'https'
            or endpoint.hostname != expected_host(paths.environment)
            or endpoint.path.rstrip('/') != f'/api/deposit/depositions/{identifier}'
            or endpoint.query or endpoint.fragment):
        raise ValueError('Saved remote snapshot endpoint/status differs from approved identity')
    _timestamp(snapshot.get('retrieved_at', ''))
    remote = validate_deposition_response(snapshot.get('body'), identifier)
    if remote['state'] not in ('unsubmitted', 'inprogress') or remote.get('submitted'):
        raise ValueError('Saved snapshot must identify an unpublished draft')
    validate_files(remote['files'], artifact)
    if compare_metadata(metadata, remote['metadata']):
        raise ValueError('Saved remote metadata differs from uploaded source-backed payload')
    duplicate = read_json(duplicate_path)
    if (not isinstance(duplicate, dict) or duplicate.get('schema_version') != 1 or duplicate.get('status') != 'checked_no_match'
            or duplicate.get('inventory_complete') is not True
            or duplicate.get('environment') != paths.environment
            or duplicate.get('fgdc_id') != Path(entry['json_file']).stem
            or duplicate.get('source_sha256') != source_hash
            or duplicate.get('metadata_sha256') != metadata_hash(metadata)
            or duplicate.get('candidates') != [] or not duplicate.get('scope')
            or not isinstance(duplicate.get('evidence'), list) or not duplicate['evidence']):
        raise ValueError('Complete source/payload-scoped duplicate evidence is required')
    _timestamp(duplicate.get('checked_at', ''))
    if not isinstance(duplicate.get('valid_until'), str):
        raise ValueError('Duplicate evidence expiry is missing or malformed')
    expires = datetime.fromisoformat(duplicate['valid_until'].replace('Z', '+00:00'))
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
        raise ValueError('Duplicate evidence is expired')
    for proof in duplicate['evidence']:
        if (not isinstance(proof, dict) or proof.get('status') != 'checked_no_match'
                or proof.get('inventory_complete') is not True or not proof.get('endpoint')
                or not proof.get('scope') or not re.fullmatch(r'[0-9a-f]{64}', proof.get('response_sha256', ''))):
            raise ValueError('Malformed or incomplete duplicate evidence')
        raw_snapshot = proof.get('snapshot')
        if not isinstance(raw_snapshot, dict) or raw_snapshot.get('format') not in ('oai', 'datacite', 'crossref', 'dspace'):
            raise ValueError('Duplicate evidence needs a recognized raw repository response')
        inventory = snapshot_inventory(raw_snapshot)
        if (not inventory['inventory_complete'] or inventory['records']
                or inventory['response_sha256'] != proof['response_sha256']
                or inventory['endpoint'] != proof['endpoint'] or inventory['scope'] != proof['scope']
                or raw_snapshot.get('query') != title):
            raise ValueError('Raw duplicate response is incomplete, not empty, or wrongly scoped')
        _timestamp(raw_snapshot.get('retrieved_at', ''))
    # HEAD alone does not describe rules executing from an uncommitted working tree.
    rules = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
             for name in ('agent_qa.py', 'qa_manifest.py', 'rehosting_authority.py', 'source_access_interpretation.py')}
    return {'checks': dict.fromkeys(QA_CHECKS, True), 'rules_sha256': rules, 'source_sha256': source_hash,
            'metadata_sha256': metadata_hash(metadata), 'artifact_contract': artifact,
            'remote_snapshot': {'path': str(Path(snapshot_path).resolve()), 'sha256': metadata_hash(snapshot),
                                'endpoint': snapshot['endpoint'], 'retrieved_at': snapshot['retrieved_at']},
            'duplicate_snapshot': {'path': str(Path(duplicate_path).resolve()), 'sha256': metadata_hash(duplicate)},
            'scope': 'Strict source-backed record checks; no independent program review or publication authority'}


def validate_agent_evidence(record, entry, paths):
    if record.get('fgdc_id') != Path(entry['json_file']).stem:
        raise ValueError('QA source identity differs from payload source filename')
    evidence = record.get('agent_evidence', {})
    current = assess(entry, paths, evidence.get('remote_snapshot', {}).get('path', ''),
                     evidence.get('duplicate_snapshot', {}).get('path', ''))
    if evidence != current or record.get('qa', {}).get('evidence') != [metadata_hash(current)]:
        raise ValueError('Agent source/snapshot evidence is stale or altered')


def build_manifest(paths, inputs, reviewer, run_id, revision=None):
    if not reviewer or not run_id:
        raise ValueError('Honest agent identity and run ID required')
    registry = read_json(paths.uploads_registry_path, {})
    if not isinstance(registry, dict) or any(not isinstance(entry, dict) for entry in registry.values()):
        raise ValueError('Malformed upload registry; no approvals produced')
    manifest = {'schema_version': 2, 'environment': paths.environment,
                'source_revision': revision or subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1], text=True).strip(),
                'prepared_at': datetime.now(timezone.utc).isoformat(), 'records': []}
    for fgdc_id, entry in sorted(registry.items()):
        if fgdc_id.startswith('_') or entry.get('upload_status') != 'success':
            continue
        manifest['records'].append({
            'fgdc_id': fgdc_id, **{key: entry.get(key) for key in
            ('deposition_id', 'source_sha256', 'metadata_sha256', 'artifact_contract')},
            'qa': {'approved': False, 'checks': dict.fromkeys(QA_CHECKS, False)},
            'duplicate_review': {'status': 'pending', 'classification': None, 'rationale': '', 'evidence': []}})
    if not manifest['records']:
        raise ValueError('No successful draft records to assess')
    manifest['program_review'] = {name: {'status': 'pending', 'evidence': []}
                                  for name in ('independent_review', 'risk_stratified_spotcheck')}
    identity_error = None
    try:
        validate_registry_identities(registry)
    except ValueError as exc:
        identity_error = str(exc)
    for record in manifest['records']:
        record['qa'].update(reviewer_type='agent', reviewer=reviewer, run_id=run_id,
                            review_revision=manifest['source_revision'], reviewed_at=datetime.now(timezone.utc).isoformat(),
                            rationale='Conservative offline source-backed assessment', evidence=[])
        try:
            if identity_error:
                raise ValueError(identity_error)
            if Path(registry[record['fgdc_id']]['json_file']).stem != record['fgdc_id']:
                raise ValueError('Ledger source identity differs from payload filename')
            item = inputs[record['fgdc_id']]
            evidence = assess(registry[record['fgdc_id']], paths, item['remote_snapshot'], item['duplicate_snapshot'])
            record['agent_evidence'] = evidence
            record['qa'].update(approved=True, checks=evidence['checks'], evidence=[metadata_hash(evidence)])
            record['duplicate_review'] = {'status': 'reviewed', 'classification': 'checked_no_match',
                                          'rationale': 'Complete scoped saved evidence; no matching candidates',
                                          'reviewer_type': 'agent', 'evidence': [evidence['duplicate_snapshot']]}
        except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
            record['qa']['approved'] = False
            record['hold_reasons'] = [str(exc)]
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='output')
    parser.add_argument('--production', action='store_true')
    parser.add_argument('--inputs', required=True, help='JSON mapping FGDC IDs to saved remote/duplicate snapshots')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--reviewer', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if Path(args.manifest).exists():
        raise ValueError('Preserve prior QA evidence; choose a new manifest path')
    manifest = build_manifest(OutputPaths(args.output, 'production' if args.production else 'sandbox'),
                              read_json(args.inputs), args.reviewer, args.run_id)
    atomic_json(args.manifest, manifest)


if __name__ == '__main__':
    main()
