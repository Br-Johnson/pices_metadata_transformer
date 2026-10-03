"""Propose byte-group review identities without changing source or provider state.

Consumes the frozen source-only preparation and committed public evidence.
Every original ID, payload hash and derived artifact/submission fingerprint is
retained. A review representative is not an approved canonical provider record.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.artifact_contract import prepare_artifact  # noqa: E402
from scripts.upload_service import prepare_metadata  # noqa: E402

CHECKPOINT = '0188b1f93c459d2427c10d9f1964966289f8576c'
REPORT_SHA256 = 'f6b68ea0bbc328bd44f6bba06a9b504c8b438c232fc10dcc868d628e2867ec91'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return digest(canonical(value).encode())


def differences(left, right, pointer=''):
    if type(left) is not type(right):
        return [pointer]
    if isinstance(left, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            part = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            result.extend(differences(left[key], right[key], part) if key in left and key in right else [part])
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [pointer]
        return [part for i, pair in enumerate(zip(left, right))
                for part in differences(*pair, pointer + '/' + str(i))]
    return [] if left == right else [pointer]


def source_number(source_id):
    match = re.fullmatch(r'FGDC-(\d+)', source_id)
    assert match, source_id
    return int(match[1])


def text(root, path):
    node = root.find(path)
    return ''.join(node.itertext()) if node is not None else ''


def reconcile(prepared):
    report_raw = (prepared / 'classification.json').read_bytes()
    assert digest(report_raw) == REPORT_SHA256, 'Unexpected source preparation checkpoint'
    report = json.loads(report_raw)
    assert report['summary']['source_status_counts'] == {'supported': 2138, 'held': 2062, 'failed': 6}
    rows = {row['source_id']: row for row in report['records']}
    assert len(rows) == len(report['records']) == 4206
    assert {p.stem for p in (ROOT / 'FGDC').glob('*.xml')} == set(rows)
    buckets = defaultdict(list)
    for sid, row in rows.items():
        raw = (ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        assert digest(raw) == row['source_sha256'], sid
        buckets[row['source_sha256']].append(sid)
    raw_groups = [{'source_sha256': sha, 'source_ids': sorted(ids)}
                  for sha, ids in sorted(buckets.items()) if len(ids) > 1]
    assert len(raw_groups) == 228 and all(len(group['source_ids']) == 2 for group in raw_groups)
    assert fingerprint(raw_groups) == '798863f69fbcc965f17e21c53e807c8961dfd86c9aeb5139fba07f0160ae7f33'
    proposal_path = ROOT / 'docs/readiness/2026-10-01/five_imports_correction_proposal.json'
    public_path = ROOT / 'docs/readiness/2026-10-01/public_source_associations.json'
    proposal_raw, public_raw = proposal_path.read_bytes(), public_path.read_bytes()
    proposal, public = json.loads(proposal_raw), json.loads(public_raw)
    protections = sorted([{key: rec[key] for key in
                          ('source_id', 'source_sha256', 'record_id', 'doi', 'association_status')}
                          for rec in proposal['records']], key=lambda item: item['source_id'])
    for protection in protections:
        assert rows[protection['source_id']]['source_sha256'] == protection['source_sha256']
    assert fingerprint(protections) == 'd6c4aabc801945ccf6edc0221ca87b026777a479db98ed63837252d6829680ed'
    paths = SimpleNamespace(original_fgdc_dir=str(prepared / 'data/original_fgdc'), base=str(prepared))
    alias_map, groups, member_proofs, submission_proofs = {}, [], [], []
    pre_alias_counts, technical_counts, reason_groups = Counter(), Counter(), Counter()
    for raw_group in raw_groups:
        sha, ids = raw_group['source_sha256'], raw_group['source_ids']
        originals = [(ROOT / 'FGDC' / (sid + '.xml')).read_bytes() for sid in ids]
        assert originals[0] == originals[1]
        assert abs(source_number(ids[0]) - source_number(ids[1])) == 228
        candidate = min(ids, key=source_number)
        group_id = 'fgdc-xml-sha256:' + sha
        payloads, contracts, submitted, roots = [], [], [], []
        for sid, raw in zip(ids, originals):
            row = rows[sid]
            assert row['source_status'] == 'held' and row['exact_copy_aliases'] == ids
            copied = prepared / 'data/original_fgdc' / (sid + '.xml')
            assert copied.read_bytes() == raw
            payload_path = prepared / 'data/zenodo_json' / (sid + '.json')
            payload_raw = payload_path.read_bytes()
            assert digest(payload_raw) == row['prepared_payload_sha256']
            payload = json.loads(payload_raw)
            contract = prepare_artifact(payload, copied)
            metadata, _, source_sha = prepare_metadata(str(payload_path), paths)
            assert source_sha == sha
            raw_metadata_sha = fingerprint(payload['metadata'])
            metadata_sha = fingerprint(metadata)
            if row.get('metadata_sha256') is not None:
                assert row['metadata_sha256'] == metadata_sha
            proof = {'source_id': sid, 'source_sha256': sha,
                     'prepared_payload_sha256': digest(payload_raw),
                     'metadata_sha256': raw_metadata_sha,
                     'artifact_policy_sha256': fingerprint(payload['artifact_policy']),
                     'content_classification_sha256': fingerprint(payload['content_classification'])}
            member_proofs.append(proof)
            submission_proofs.append({'source_id': sid, 'source_sha256': sha,
                                     'artifact_contract_sha256': contract['sha256'],
                                     'submitted_metadata_sha256': metadata_sha})
            alias_map[sid] = {'candidate_canonical_group_id': group_id,
                              'candidate_review_representative_source_id': candidate,
                              'source_sha256': sha, 'original_filename': sid + '.xml',
                              'prepared_payload_sha256': digest(payload_raw),
                              'prepared_metadata_sha256': raw_metadata_sha,
                              'artifact_contract_sha256': contract['sha256'],
                              'submitted_metadata_sha256': metadata_sha,
                              'source_status': 'held',
                              'source_status_without_aliases': row['source_status_without_aliases'],
                              'hold_reasons': row['hold_reasons'],
                              'canonical_provider_record_id': None, 'canonical_provider_doi': None}
            pre_alias_counts[row['source_status_without_aliases']] += 1
            technical_counts[row['technical_metadata']] += 1
            payloads.append(payload)
            contracts.append(contract)
            submitted.append(metadata)
            roots.append(ET.fromstring(raw))
        assert payloads[0]['metadata'] == payloads[1]['metadata']
        assert payloads[0]['artifact_policy'] == payloads[1]['artifact_policy']
        assert differences(payloads[0], payloads[1]) == ['/content_classification/files/0/name']
        assert differences(contracts[0], contracts[1]) == [
            '/classification_sha256', '/files/0/name', '/sha256', '/source_id']
        assert differences(submitted[0], submitted[1]) == ['/notes']
        shared_file = [{key: contract['files'][0][key] for key in ('sha256', 'md5', 'size', 'role')}
                       for contract in contracts]
        assert shared_file[0] == shared_file[1]
        reasons = sorted(set(reason for sid in ids for reason in rows[sid]['hold_reasons']
                             if reason != 'Exact-copy aliases require identity adjudication'))
        reason_groups[tuple(reasons)] += 1
        title = text(roots[0], './idinfo/citation/citeinfo/title')
        abstract = text(roots[0], './idinfo/descript/abstract')
        title_warnings = []
        for protection in protections:
            protected_root = ET.parse(ROOT / 'FGDC' / (protection['source_id'] + '.xml')).getroot()
            if title == text(protected_root, './idinfo/citation/citeinfo/title'):
                assert sha != protection['source_sha256']
                assert ' '.join(abstract.split()) != ' '.join(text(protected_root, './idinfo/descript/abstract').split())
                title_warnings.append({**protection, 'comparison': 'title_only; different source bytes and abstract; do not inherit record ID/DOI'})
        procite_matches = re.findall(r'Reference Procite #(\d+)', abstract)
        groups.append({'candidate_canonical_group_id': group_id, 'source_sha256': sha,
                       'member_source_ids': ids, 'candidate_review_representative_source_id': candidate,
                       'representative_basis': 'Smallest numeric FGDC ID for stable review display only; no evidence of historical priority or ownership.',
                       'prepared_metadata_identical': True, 'artifact_policy_identical': True,
                       'prepared_payload_difference_json_pointers': ['/content_classification/files/0/name'],
                       'artifact_contract_difference_json_pointers': ['/classification_sha256', '/files/0/name', '/sha256', '/source_id'],
                       'submitted_metadata_difference_json_pointers': ['/notes'],
                       'prepared_metadata_sha256': fingerprint(payloads[0]['metadata']),
                       'shared_xml_file': shared_file[0], 'title': title,
                       'literal_procite_references': procite_matches,
                       'non_alias_hold_reasons': reasons,
                       'title_only_protected_record_warnings': title_warnings,
                       'canonical_provider_record_id': None, 'canonical_provider_doi': None,
                       'unresolved': ['Current production source-to-record crosswalk and ownership are unverified.',
                                      'Identical XML cannot establish a primary catalogue ID or authorize collapsing source/provider records.']
                                     + (['Independent source holds also remain.'] if reasons else [])})
    alias_map = dict(sorted(alias_map.items()))
    member_proofs.sort(key=lambda item: item['source_id'])
    submission_proofs.sort(key=lambda item: item['source_id'])
    assert len(alias_map) == 456 and not set(alias_map).intersection(p['source_id'] for p in protections)
    assert pre_alias_counts == {'supported': 408, 'held': 48}
    assert technical_counts == {'pass': 450, 'held': 6}
    assert sum(bool(group['title_only_protected_record_warnings']) for group in groups) == 2
    return {'schema_version': 1, 'analysis_only': True, 'eligibility_delta': 0,
            'source_checkpoint': CHECKPOINT, 'classification_sha256': REPORT_SHA256,
            'source_summary_unchanged': report['summary'],
            'candidate_identity_policy': 'Neutral original-XML SHA-256 byte group; retain every member source ID, filename, payload and artifact fingerprint. No dataset/record merger or canonical provider identity is selected.',
            'source_alias_to_candidate_canonical': alias_map, 'groups': groups,
            'summary': {'groups': 228, 'alias_identities': 456, 'prepared_metadata_equal_groups': 228,
                        'prepared_metadata_meaningfully_different_groups': 0,
                        'submitted_metadata_different_fingerprint_groups': 228,
                        'source_status_without_aliases': dict(pre_alias_counts),
                        'technical_metadata': dict(technical_counts), 'retained_direct_production_alias_associations': 0,
                        'title_only_protected_record_collision_groups': 2,
                        'non_alias_reason_partitions': [{'reasons': list(key), 'groups': count, 'identities': 2 * count}
                                                       for key, count in sorted(reason_groups.items(), key=lambda item: (-item[1], item[0]))]},
            'exact_copy_groups_sha256': fingerprint(raw_groups),
            'alias_member_proof_sha256': fingerprint(member_proofs),
            'derived_artifact_submission_proof_sha256': fingerprint(submission_proofs),
            'retained_historical_production_protections': protections,
            'retained_public_association_history': public['records'],
            'public_protection_list_sha256': fingerprint(protections),
            'public_evidence_files': {str(proposal_path.relative_to(ROOT)): digest(proposal_raw),
                                      str(public_path.relative_to(ROOT)): digest(public_raw)},
            'excluded_unrelated_record_id': 10042430,
            'preservation': 'Read-only reconciliation; original IDs/bytes, prepared payload hashes, public evidence history and all holds remain unchanged.',
            'provider_requests': 0, 'provider_writes': 0, 'publication_approvals': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.prepared), indent=2, ensure_ascii=False))
