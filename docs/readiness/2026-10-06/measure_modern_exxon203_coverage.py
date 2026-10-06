"""Guarded offline Exxon203 class-wire measurement; execute only after freeze.

Reuse pinned PR42/PR41/PR38 helpers and actual retained shard artifacts. Prepare
203 class targets twice (406 separate original files) across four shards and
compare all3262 retained singleton wires/nonruntime evidence once at original
paths. Alias source-file holds remain distinct from supported class assessment.
Only fresh /tmp output is writable; no provider/execution/release is asserted.
"""

import argparse
import hashlib
import html
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

HELPER = Path('docs/readiness/2026-10-06/measure_modern_institution91_coverage.py')
HELPER_SHA = '4c9163229ade333a2dc9a3bff1ba5725c033a302c0c343cb170459393d40b010'
INSTITUTION_VALIDATION = Path('docs/readiness/2026-10-06/modern_institution91_validation.json')
INSTITUTION_VALIDATION_SHA = 'c170ee5d9d7da6190ca2a2b97062bb1d87cad565e694959922f520d6367cf730'
INSTITUTION_ROOTS = [Path(f'/tmp/pices-institution91-shard{index}-v1') for index in range(4)]
INSTITUTION_PROFILES = Path('/workspace/pices-modern-next-citations-20261006/docs/readiness')
SOURCE_REVIEW = Path('docs/readiness/2026-10-06/modern_exxon203_source_review.json')
SOURCE_REVIEW_SHA = '51c7266a2da2d270fc52ba70e712faa27a3ffd59cd2ba7b44ff4f7dbdd3bf48d'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_helpers(repo):
    path = repo / HELPER
    assert digest(path) == HELPER_SHA
    spec = importlib.util.spec_from_file_location('frozen_institution91_measurement', path)
    institution = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(institution)
    prior, base = institution.load_helpers(repo)
    return institution, prior, base


def retained3262(repo, institution, prior, base):
    """Advance every retained binding through actual PR42 saved preparations."""
    retained, frozen, profiles, roots, _ = institution.retained3171(repo, prior, base)
    original_frozen, original_profiles = dict(frozen), dict(profiles)
    aggregate_path = repo / INSTITUTION_VALIDATION
    assert digest(aggregate_path) == INSTITUTION_VALIDATION_SHA
    aggregate = json.loads(aggregate_path.read_bytes())
    assert aggregate['status'] == 'GUARDED_INSTITUTION91_AGGREGATE_PASS'
    assert aggregate['all_shards_complete'] and aggregate['coverage'] == {
        'fresh_new_prepare_calls': 182, 'new_institutional_singletons': 91, 'paired_targets_added': 0,
        'prior_retained_singletons': 3171, 'retained_input_prepare_comparisons': 3171, 'total': 3262}
    assert aggregate['helper_sha256'] == HELPER_SHA
    assert aggregate['prior3171_validation_sha256'] == institution.PICES_VALIDATION_SHA
    assert aggregate['provider_requests'] == aggregate['provider_mutations'] == 0
    assert aggregate['source_bindings_unchanged'] and aggregate['all_saved_digests_reverified']
    proofs = {row['source_id']: row for row in aggregate['rows']}
    assert len(proofs) == len(aggregate['rows']) == 91 and not set(proofs) & set(retained)
    old_ids = set(retained)
    seen_old, seen_new, old_rows, receipts = set(), set(), [], []

    def track(path, pin):
        path = Path(path)
        assert not path.is_symlink() and path.resolve() == path
        assert any(path.is_relative_to(root) for root in INSTITUTION_ROOTS)
        assert str(path) not in frozen or frozen[str(path)] == pin
        assert digest(path) == pin
        frozen[str(path)] = pin
        return path

    assert [shard['index'] for shard in aggregate['shards']] == list(range(4))
    for shard in aggregate['shards']:
        index = shard['index']
        root = INSTITUTION_ROOTS[index]
        assert shard['root'] == str(root)
        coverage = json.loads(track(root / 'coverage.json', shard['receipt_sha256']).read_bytes())
        receipts.append(coverage)
        assert coverage['status'] == 'GUARDED_INSTITUTION_SHARD_COVERAGE_PASS'
        assert coverage['runtime_sha256'] == aggregate['runtime_sha256']
        assert coverage['helper_sha256'] == HELPER_SHA
        assert coverage['reused_helpers_sha256'] == {str(institution.HELPER): institution.HELPER_SHA,
                                                          str(prior.HELPER): prior.HELPER_SHA}
        assert coverage['guard_sha256'] == base.GUARD_SHA
        assert coverage['environment_cleared_dummy_credentials_only']
        assert coverage['source_bindings_unchanged'] and coverage['retained_paths_and_bytes_unchanged']
        assert coverage['all3171_retained_file_hashes_verified_before_and_after']
        assert coverage['original_files_verified_before_and_after'] == 4206
        assert coverage['provider_requests'] == coverage['provider_mutations'] == 0
        assert not coverage['unexpected_guard_events'] and not any(coverage['guard']['tests'].values())
        assert coverage['guard'] == shard['guard']
        assert coverage['sharding']['index'] == index and coverage['sharding']['count'] == 4
        manifest = json.loads(track(root / 'wire_artifact_manifest.json',
                                   shard['artifact_manifest_sha256']).read_bytes())
        assert coverage['wire_artifact_manifest_sha256'] == shard['artifact_manifest_sha256']
        previous_files = json.loads(track(root / 'retained_file_manifest.json',
                                         shard['retained_file_manifest_sha256']).read_bytes())
        assert coverage['retained_file_manifest_sha256'] == shard['retained_file_manifest_sha256']
        assert previous_files == {'public_baseline_files': original_frozen,
                                  'exact_public_profile_files': original_profiles}
        prepared_root = root / 'prepared'
        assert coverage['prepared_root'] == str(prepared_root)
        report = json.loads(track(prepared_root / 'classification.json',
                                  shard['classification_sha256']).read_bytes())
        assert coverage['classification_sha256'] == shard['classification_sha256']
        new, old = manifest['institution_rows'], manifest['retained3171_rows']
        expected_new = sorted(proofs, key=base.source_order)[index::4]
        expected_old = sorted(old_ids, key=base.source_order)[index::4]
        assert [row['source_id'] for row in new] == expected_new
        assert [row['source_id'] for row in old] == expected_old
        assert coverage['sharding']['assigned_new_source_ids'] == expected_new
        assert coverage['sharding']['assigned_retained_source_ids'] == expected_old
        assert len(new) == shard['new_source_count'] == (23, 23, 23, 22)[index]
        assert len(old) == shard['retained_source_count'] == (793, 793, 793, 792)[index]
        assert report['summary']['source_status_counts'] == {'supported': len(new), 'held': 0, 'failed': 0}
        assert {row['source_id'] for row in report['records']} == set(expected_new)
        old_rows.extend(old)
        for saved in old:
            sid = saved['source_id']
            assert sid not in seen_old
            seen_old.add(sid)
            original = retained[sid]
            for key, value in original.items():
                if key != 'evidence':
                    assert saved[key] == value
            path = track(root / saved['current_preparation_path'], saved['current_preparation_sha256'])
            packet = json.loads(path.read_bytes())
            assert packet['source_id'] == packet['evidence']['source_id'] == sid
            assert packet['binding'] == saved['current_binding'] == hashlib.sha256(base.encode(packet['evidence'])).hexdigest()
            assert packet['evidence']['runtime_sha256'] == aggregate['runtime_sha256']
            assert base.nonruntime(packet['evidence']) == base.nonruntime(original['evidence'])
            assert saved['nonruntime_evidence_sha256'] == hashlib.sha256(base.encode(base.nonruntime(packet['evidence']))).hexdigest()
            assert saved['wire_and_nonruntime_evidence_equal']
            original.update(evidence=packet['evidence'], binding=packet['binding'],
                            preparation_path=str(path), preparation_sha256=saved['current_preparation_sha256'])
        for saved in new:
            sid = saved['source_id']
            assert sid not in seen_new and sid not in retained
            seen_new.add(sid)
            assert proofs[sid] == saved | {'shard_index': index}
            path = track(root / saved['preparation_path'], saved['preparation_sha256'])
            packet = json.loads(path.read_bytes())
            evidence = packet['evidence']
            assert packet['source_id'] == evidence['source_id'] == sid
            assert packet['binding'] == saved['binding'] == hashlib.sha256(base.encode(evidence)).hexdigest()
            assert evidence['runtime_sha256'] == aggregate['runtime_sha256']
            assert evidence['source_sha256'] == saved['source_sha256']
            assert evidence['wire_sha256'] == saved['wire_sha256']
            input_path = track(root / saved['prepared_input_path'], saved['prepared_input_sha256'])
            assert input_path == prepared_root / 'data/zenodo_json' / (sid + '.json')
            assert evidence['prepared_input_sha256'] == saved['prepared_input_sha256']
            wire_path = track(root / saved['wire_path'], saved['wire_sha256'])
            copy_path = track(root / saved['original_copy_path'], saved['source_sha256'])
            assert copy_path == prepared_root / 'data/original_fgdc' / (sid + '.xml')
            track(root / 'sources' / (sid + '.xml'), saved['source_sha256'])
            payload = json.loads(input_path.read_bytes())
            assert packet['complete_raw_input_metadata'] == payload['metadata']
            assert packet['complete_legacy_metadata_preserved'] and packet['unchanged_repeat_equal']
            for reference in payload['artifact_policy'].values():
                if not isinstance(reference, dict) or 'manifest_path' not in reference:
                    continue
                public = Path(reference['manifest_path'])
                assert public.resolve() == public and not public.is_symlink()
                assert public.is_relative_to(INSTITUTION_PROFILES)
                relative = public.relative_to(INSTITUTION_PROFILES)
                assert str(relative) in base.PROFILE_FILES
                pin = reference['manifest_sha256']
                assert digest(public) == pin == digest(repo / 'docs/readiness' / relative)
                assert str(public) not in profiles or profiles[str(public)] == pin
                profiles[str(public)] = pin
            retained[sid] = {
                'source_id': sid, 'source_sha256': saved['source_sha256'],
                'prepared_root': str(prepared_root), 'prepared_input_path': str(input_path),
                'wire_path': str(wire_path), 'wire_sha256': saved['wire_sha256'],
                'preparation_path': str(path), 'preparation_sha256': saved['preparation_sha256'],
                'evidence': evidence, 'binding': packet['binding'],
                'raw_input_metadata_sha256': saved['raw_input_metadata_sha256']}
    assert seen_old == old_ids and seen_new == set(proofs) and len(retained) == 3262
    old_rows.sort(key=lambda row: base.source_order(row['source_id']))
    assert hashlib.sha256(base.encode(old_rows)).hexdigest() == aggregate['retained3171_comparison_rows_sha256']
    for key in ('source_bindings_before', 'runtime_sha256', 'helper_sha256', 'policy_input_bindings',
                'original_hashes', 'original_hashes_sha256'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    assert receipts[0]['original_hashes_sha256'] == aggregate['original_hashes_sha256']
    for saved in retained.values():
        payload = json.loads(Path(saved['prepared_input_path']).read_bytes())
        assert digest(Path(saved['prepared_input_path'])) == saved['evidence']['prepared_input_sha256']
        assert digest(Path(saved['wire_path'])) == saved['wire_sha256'] == saved['evidence']['wire_sha256']
        assert hashlib.sha256(base.encode(payload['metadata'])).hexdigest() == saved['raw_input_metadata_sha256']
        wire = json.loads(Path(saved['wire_path']).read_bytes())
        block = wire['metadata']['additional_descriptions'][0]['description']
        normalized = json.loads(html.unescape(block.split('<pre>', 1)[1][:-6]))
        assert hashlib.sha256(base.encode(normalized)).hexdigest() == saved['evidence']['legacy_metadata_sha256']
    return retained, frozen, profiles, [*roots, *INSTITUTION_ROOTS], receipts[0]


def measure_pairs(target_ids, selected, output, modern, mapping, fixtures, paths_class,
                  prepare_class_target, fingerprint, reviewed_at, max_bytes, originals, base):
    """Prepare both members without turning alias-file holds into source support."""
    source_ids = sorted([sid for target in target_ids for sid in selected[target]['source_ids']],
                        key=base.source_order)
    assert len(source_ids) == len(set(source_ids)) == 2 * len(target_ids)
    prepared_root = fixtures(output, ids=source_ids)
    paths = paths_class(str(prepared_root), 'production')
    report_path = prepared_root / 'classification.json'
    report = json.loads(report_path.read_bytes())
    assert len(report['records']) == len(source_ids)
    assert {row['source_id'] for row in report['records']} == set(source_ids)
    assert report['summary']['source_status_counts'] == {'supported': 0, 'held': len(source_ids), 'failed': 0}
    assert report['summary']['exact_copy_groups'] == len(target_ids)
    assert report['summary']['files_in_copy_groups'] == len(source_ids)
    pair_by_source = {sid: selected[target]['source_ids']
                      for target in target_ids for sid in selected[target]['source_ids']}
    for row in report['records']:
        assert row['source_status'] == 'held' and row['source_status_without_aliases'] == 'supported'
        assert row['exact_copy_aliases'] == pair_by_source[row['source_id']]
        assert row['hold_reasons'] == ['Exact-copy aliases require identity adjudication']
        assert row['remote_verified'] is False and row['publication_approved'] is False
    assert {path.stem for path in (output / 'sources').glob('*.xml')} == set(source_ids)
    assert {path.stem for path in Path(paths.zenodo_json_dir).glob('*.json')} == set(source_ids)
    directory = output / 'classes'
    directory.mkdir()
    rows = []
    for index, target_id in enumerate(target_ids, 1):
        started = time.monotonic()
        selected_row = selected[target_id]
        ids = selected_row['source_ids']
        payload_paths = [Path(paths.zenodo_json_dir) / (sid + '.json') for sid in ids]
        input_raw = [path.read_bytes() for path in payload_paths]
        payloads = [mapping.parse(raw) for raw in input_raw]
        current = modern.prepare(target_id, paths, reviewed_at=reviewed_at)
        repeated = modern.prepare(target_id, paths, reviewed_at=reviewed_at)
        assert current == repeated
        assert [path.read_bytes() for path in payload_paths] == input_raw
        legacy = prepare_class_target(target_id, paths, reviewed_at=reviewed_at)
        assert current.legacy_target == legacy
        assert current.record_target_id == target_id and list(current.source_ids) == ids
        assert not hasattr(current, 'source_id') and not hasattr(current, 'xml')
        assert legacy['source_semantic_status'] == 'supported'
        assert all(row['source_semantic_status'] == 'supported' and not row['hold_reasons']
                   for row in legacy['member_assessments'])
        assert legacy['production_reconciliation_status'] == 'pending'
        assert legacy['execution_status'] == 'class_execution_not_implemented'
        assert all(legacy[key] is False for key in ('upload_eligible', 'remote_verified', 'publication_approved'))
        assert all(legacy[key] is None for key in ('canonical_source_id', 'canonical_catalogue_record_id',
                                                 'canonical_provider_record_id', 'canonical_provider_doi'))
        assert isinstance(current.evidence, dict) and current.evidence['policy'] == modern.POLICY
        assert current.binding == mapping.sha(mapping.encode(current.evidence))
        assert current.evidence['runtime_sha256'] == mapping.runtime_binding()
        assert payloads[0]['metadata'] == payloads[1]['metadata']
        assert legacy['common_source_metadata_sha256'] == fingerprint(payloads[0]['metadata'])
        assert legacy['metadata_sha256'] == fingerprint(legacy['metadata'])
        contract = legacy['artifact_contract']
        assert contract['schema_version'] == 2 and contract['record_target_id'] == target_id
        assert contract['sha256'] == fingerprint({key: value for key, value in contract.items() if key != 'sha256'})
        assert len(contract['files']) == len(contract['members']) == len(current.originals) == 2
        assert contract['member_set_sha256'] == legacy['member_set_sha256'] == fingerprint(legacy['members'])
        wire = mapping.parse(current.body)
        mapping.validate_payload(wire)
        metadata = legacy['metadata']
        block = wire['metadata']['additional_descriptions'][0]['description']
        assert '<pre>' in block and block.endswith('</pre>')
        assert json.loads(html.unescape(block.split('<pre>', 1)[1][:-6])) == metadata
        for key in ('title', 'description', 'publication_date'):
            assert wire['metadata'][key] == metadata[key]
        assert wire['metadata']['subjects'] == [{'subject': value} for value in metadata.get('keywords', [])]
        assert metadata['creators'] == payloads[0]['metadata']['creators'] == selected_row['creators']
        assert wire['metadata']['creators'] == selected_row['modern_creators']
        assert metadata['access_right'] == 'restricted' and metadata['license'] == ''
        assert wire['access'] == {'record': 'public', 'files': 'restricted'} and wire['files'] == {'enabled': True}
        assert 'rights' not in wire['metadata'] and 'license' not in wire['metadata']
        mapping.compare_metadata(wire['metadata'], wire['metadata'])
        displayed = json.loads(json.dumps(wire['metadata']))
        for creator in displayed['creators']:
            person = creator['person_or_org']
            if person['type'] == 'personal':
                person['name'] = person['family_name'] + ', ' + person['given_name']
        mapping.compare_metadata(displayed, wire['metadata'])
        file_rows, expected_originals, expected_inputs = [], [], []
        for sid, path, raw_input, payload, member, item in zip(
                ids, payload_paths, input_raw, payloads, legacy['members'], contract['files'], strict=True):
            name = sid + '.xml'
            raw_xml = (mapping.ROOT / 'FGDC' / name).read_bytes()
            copy_path = Path(paths.original_fgdc_dir) / name
            assert copy_path.read_bytes() == raw_xml == (output / 'sources' / name).read_bytes()
            assert mapping.sha(raw_xml) == originals[name] == selected_row['source_sha256']
            assert member['source_id'] == sid and member['source_filename'] == name
            assert member['source_sha256'] == selected_row['source_sha256']
            assert member['payload_sha256'] == mapping.sha(raw_input)
            assert member['policy_sha256'] == fingerprint(payload['artifact_policy'])
            assert payload['artifact_policy']['creator_interpretation']['manifest_sha256'] == mapping.EXXON_SHA
            assert item['name'] == name and item['sha256'] == member['source_sha256']
            assert item['size'] == len(raw_xml) and item['md5'] == hashlib.md5(raw_xml, usedforsecurity=False).hexdigest()
            assert item['role'] == 'descriptive_metadata'
            assert len(raw_xml) <= max_bytes
            expected_originals.append((name, raw_xml))
            expected_inputs.append({
                'source_id': sid, 'source_path': str(copy_path.resolve()),
                'prepared_input_path': str(path.resolve()), 'prepared_input_sha256': mapping.sha(raw_input),
                'member': member})
            file_rows.append({
                'source_id': sid, 'name': name, 'source_sha256': member['source_sha256'],
                'size': item['size'], 'md5': item['md5'],
                'prepared_input_path': str(path.relative_to(output)), 'prepared_input_sha256': mapping.sha(raw_input),
                'original_copy_path': str(copy_path.relative_to(output)),
                'source_copy_path': str((output / 'sources' / name).relative_to(output)),
                'policy_sha256': member['policy_sha256'], 'artifact_v1_sha256': member['artifact_v1_sha256']})
        assert isinstance(current.originals, tuple) and current.originals == tuple(expected_originals)
        assert current.originals[0][1] == current.originals[1][1]
        assert len(current.body) <= max_bytes
        expected_evidence = {
            'schema_version': 1, 'kind': 'modern-content-class-preparation-v1', 'policy': modern.POLICY,
            'record_target_id': target_id, 'source_ids': ids, 'source_sha256': selected_row['source_sha256'],
            'reviewed_at': reviewed_at, 'mapping_manifest_sha256': modern.MAPPING_SHA,
            **selected_row['authority_pins'],
            'inputs': expected_inputs, 'artifact_contract': contract,
            'legacy_target_sha256': mapping.sha(mapping.encode(legacy)),
            'legacy_metadata_sha256': mapping.sha(mapping.encode(metadata)),
            'wire_sha256': mapping.sha(current.body),
            'schema_sha256': {name: pin for name, (_, pin) in mapping.SCHEMA_FILES.items()},
            'runtime_sha256': mapping.runtime_binding(),
            'production_reconciliation_status': 'pending', 'execution_status': 'class_execution_not_implemented',
            'upload_eligible': False, 'remote_verified': False, 'publication_approved': False}
        assert current.evidence == expected_evidence
        assert current.binding == mapping.sha(mapping.encode(expected_evidence))
        stem = 'XMLCLASS-' + selected_row['source_sha256']
        wire_path = directory / (stem + '.wire.json')
        legacy_path = directory / (stem + '.legacy-target.json')
        evidence_path = directory / (stem + '.preparation.json')
        with wire_path.open('xb') as stream:
            stream.write(current.body)
        base.write_json(legacy_path, legacy)
        base.write_json(evidence_path, {
            'record_target_id': target_id, 'source_ids': ids, 'binding': current.binding,
            'evidence': current.evidence, 'complete_common_source_metadata': payloads[0]['metadata'],
            'complete_legacy_class_metadata': metadata, 'complete_legacy_metadata_preserved': True,
            'both_original_files_and_policies_verified': True, 'unchanged_repeat_equal': True,
            'upload_eligible': False, 'remote_verified': False, 'publication_approved': False})
        rows.append({
            'record_target_id': target_id, 'source_ids': ids, 'source_sha256': selected_row['source_sha256'],
            'binding': current.binding, 'policy': modern.POLICY, 'members': file_rows,
            'member_set_sha256': legacy['member_set_sha256'],
            'common_source_metadata_sha256': legacy['common_source_metadata_sha256'],
            'legacy_class_metadata_sha256': legacy['metadata_sha256'],
            'artifact_contract_sha256': contract['sha256'],
            'wire_path': str(wire_path.relative_to(output)), 'wire_sha256': digest(wire_path),
            'legacy_target_path': str(legacy_path.relative_to(output)), 'legacy_target_sha256': digest(legacy_path),
            'preparation_path': str(evidence_path.relative_to(output)), 'preparation_sha256': digest(evidence_path),
            'body_bytes': len(current.body), 'original_file_count': 2, 'prepare_calls': 2,
            'source_semantic_status': 'supported', 'upload_eligible': False,
            'elapsed_seconds': time.monotonic() - started})
        if index % 10 == 0 or index == len(target_ids):
            print('NEW_EXXON_CLASS_PROGRESS', index, 'of', len(target_ids), flush=True)
    return prepared_root, report_path, report['summary']['source_status_counts'], rows


def main():
    if not __debug__:
        raise RuntimeError('Assertions must remain enabled for this measurement')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shard-index', type=int, choices=range(4), required=True)
    parser.add_argument('--shard-count', type=int, choices=(4,), default=4)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    os.environ.clear()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    institution, prior, base = load_helpers(repo)
    assert digest(repo / 'ci/run_offline_tests.py') == base.GUARD_SHA
    retained, frozen, profile_files, roots, previous_receipt = retained3262(repo, institution, prior, base)
    if (not output.is_relative_to(Path('/tmp')) or output == Path('/tmp') or output.exists()
            or output.is_relative_to(repo) or not output.parent.is_dir()
            or any(output.is_relative_to(root) for root in roots)):
        raise ValueError('Choose fresh /tmp output outside every retained baseline')
    from ci.run_offline_tests import (
        OfflineGuard,
        checkout_revision,
        clean_environment,
        source_bindings,
    )

    revision = checkout_revision(repo)
    allowed = {Path(path) for path in frozen} | {Path(path) for path in profile_files}
    for path in frozen:
        allowed.update(parent for parent in Path(path).parents if any(parent.is_relative_to(root) for root in roots))
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)
    guard = OfflineGuard(repo, output, revision)
    guard.library_files.update(allowed | {Path(__file__).resolve()})
    guard.install()
    guard.self_check()
    output.mkdir()
    started = time.monotonic()
    import scripts.logger
    scripts.logger.get_logger = lambda *args, **kwargs: Mock()
    from scripts import modern_content_class as modern
    from scripts import modern_singleton as mapping
    from scripts.artifact_contract import fingerprint
    from scripts.content_class_targets import prepare_class_target
    from scripts.modern_singleton_executor import MAX_BYTES
    from scripts.path_config import OutputPaths
    from tests.modern_singleton_fixtures import NOW, prepare_sources

    before = source_bindings(repo)
    originals = {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert len(originals) == 4206 and originals == previous_receipt['original_hashes']
    helper_sha, runtime_sha = digest(Path(__file__)), mapping.runtime_binding()
    manifest = mapping.pinned(modern.MAPPING, modern.MAPPING_SHA)
    assert manifest['policy'] == modern.POLICY
    assert digest(repo / SOURCE_REVIEW) == SOURCE_REVIEW_SHA
    review = json.loads((repo / SOURCE_REVIEW).read_bytes())
    assert review['verdict'] == 'APPROVE_FINITE_OFFLINE_PREPARATION_IMPLEMENTATION'
    authority_pins = {
        'source_review_sha256': SOURCE_REVIEW_SHA,
        'source_plan_sha256': mapping.PLAN_SHA,
        'creator_profile_sha256': mapping.EXXON_SHA,
        'creator_projection_sha256': mapping.EXXON_MAPPING_SHA,
        'service_contract_sha256': review['creator_projection']['service_contract_sha256'],
        'representation_sha256': review['input_sha256']['docs/readiness/2026-10-04/approved_alias_representation_228.json'],
        'pair_map_sha256': review['input_sha256']['docs/readiness/2026-10-04/alias456_source_to_content.json'],
        'pair_authority_sha256': review['input_sha256']['docs/readiness/2026-10-04/alias_pair_approach_authority.json']}
    assert all(manifest[key] == pin for key, pin in authority_pins.items())
    assert manifest['creators'] == review['creator_projection']['legacy_creators']
    assert manifest['modern_creators'] == review['creator_projection']['modern_creators']
    selected = {row['record_target_id']: row | {
        'creators': review['creator_projection']['legacy_creators'],
        'modern_creators': review['creator_projection']['modern_creators'], 'authority_pins': authority_pins}
        for row in review['selection']['targets']}
    assert len(selected) == len(review['selection']['targets']) == 203
    manifest_ids = [row['record_target_id'] for row in manifest['targets']]
    assert len(manifest_ids) == len(set(manifest_ids)) == 203 and set(manifest_ids) == set(selected)
    representation = mapping.pinned(repo / 'docs/readiness/2026-10-04/approved_alias_representation_228.json',
                                    authority_pins['representation_sha256'])
    assert manifest['targets'] == sorted([row for row in representation['classes']
                                         if row['record_target_id'] in selected],
                                        key=lambda row: row['record_target_id'])
    for row in manifest['targets']:
        wanted = selected[row['record_target_id']]
        assert row['source_ids'] == wanted['source_ids'] and row['source_sha256'] == wanted['source_sha256']
        assert wanted['source_paths'] == ['FGDC/' + filename for filename in row['source_filenames']]
    all_sources = [sid for row in selected.values() for sid in row['source_ids']]
    assert len(all_sources) == len(set(all_sources)) == 406 and not set(all_sources) & set(retained)
    assert mapping.sha(mapping.encode(review['selection']['targets'])) == review['selection']['targets_sha256']
    assert all(originals[sid + '.xml'] == row['source_sha256']
               for row in selected.values() for sid in row['source_ids'])
    policy_inputs = {repo / path: pin for path, pin in previous_receipt['policy_input_bindings'].items()}
    for path, pin in review['input_sha256'].items():
        actual = repo / path
        assert actual not in policy_inputs or policy_inputs[actual] == pin
        policy_inputs[actual] = pin
    policy_inputs.update({modern.MAPPING: modern.MAPPING_SHA, repo / SOURCE_REVIEW: SOURCE_REVIEW_SHA,
                          repo / INSTITUTION_VALIDATION: INSTITUTION_VALIDATION_SHA, repo / HELPER: HELPER_SHA})
    assert all(path.is_relative_to(repo) and path.resolve() == path for path in policy_inputs)
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    assert all(digest(Path(path)) == pin for path, pin in frozen.items())
    assert all(digest(Path(path)) == pin for path, pin in profile_files.items())
    all_new, all_old = sorted(selected), sorted(retained, key=base.source_order)
    target_ids, old_ids = all_new[args.shard_index::4], all_old[args.shard_index::4]
    assert len(target_ids) == (51, 51, 51, 50)[args.shard_index]
    assert len(old_ids) == (816, 816, 815, 815)[args.shard_index]
    print('EXXON_CLASS_SHARD_START', args.shard_index, 'new_targets', len(target_ids),
          'original_files', 2 * len(target_ids), 'retained', len(old_ids), flush=True)
    new_started = time.monotonic()
    prepared_root, report_path, source_counts, rows = measure_pairs(
        target_ids, selected, output, modern, mapping, prepare_sources, OutputPaths,
        prepare_class_target, fingerprint, NOW.isoformat(), MAX_BYTES, originals, base)
    new_finished = time.monotonic()
    compatibility = base.compare_retained(old_ids, retained, output, mapping, OutputPaths, MAX_BYTES, originals)
    for row in compatibility:
        row['body_bytes'] = Path(row['wire_path']).stat().st_size
        row['xml_bytes'] = (mapping.ROOT / 'FGDC' / (row['source_id'] + '.xml')).stat().st_size
    assert [row['record_target_id'] for row in rows] == target_ids
    assert [row['source_id'] for row in compatibility] == old_ids
    assert originals == {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert before == source_bindings(repo) and runtime_sha == mapping.runtime_binding()
    assert helper_sha == digest(Path(__file__))
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    assert all(digest(Path(path)) == pin for path, pin in frozen.items())
    assert all(digest(Path(path)) == pin for path, pin in profile_files.items())
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    artifact, baseline = output / 'wire_artifact_manifest.json', output / 'retained_file_manifest.json'
    base.write_json(artifact, {'exxon_class_rows': rows, 'retained3262_rows': compatibility})
    base.write_json(baseline, {'public_baseline_files': frozen, 'exact_public_profile_files': profile_files})
    receipt = output / 'coverage.json'
    base.write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_EXXON203_CLASS_SHARD_COVERAGE_PASS',
        'actual_checkout_revision': revision, 'helper_sha256': helper_sha,
        'reused_helpers_sha256': {str(HELPER): HELPER_SHA, str(institution.HELPER): institution.HELPER_SHA,
                                 str(prior.HELPER): prior.HELPER_SHA},
        'runtime_sha256': runtime_sha, 'guard_sha256': base.GUARD_SHA,
        'environment_cleared_dummy_credentials_only': True,
        'institution91_validation_sha256': INSTITUTION_VALIDATION_SHA,
        'pices26_validation_sha256': institution.PICES_VALIDATION_SHA,
        'exxon_validation_sha256': prior.EXXON_VALIDATION_SHA,
        'exxon_class_mapping_sha256': modern.MAPPING_SHA, 'source_review_sha256': SOURCE_REVIEW_SHA,
        'creator_profile_sha256': mapping.EXXON_SHA, 'policy': modern.POLICY,
        'assessment_time': NOW.isoformat(),
        'policy_input_bindings': {str(path.relative_to(repo)): pin for path, pin in policy_inputs.items()},
        'sharding': {
            'index': args.shard_index, 'count': 4,
            'assignment': 'lexical content-target IDs; numeric singleton IDs; independently ids[index::4]',
            'new_class_targets': 203, 'new_class_original_files': 406, 'retained_baseline_members': 3262,
            'sorted_new_target_ids_sha256': mapping.sha(mapping.encode(all_new)),
            'sorted_retained_ids_sha256': mapping.sha(mapping.encode(all_old)),
            'assigned_new_target_ids': target_ids,
            'assigned_new_source_ids': sorted([sid for target in target_ids for sid in selected[target]['source_ids']],
                                              key=base.source_order),
            'assigned_retained_source_ids': old_ids, 'actual_new_class_preparations': len(rows),
            'actual_new_class_prepare_calls': 2 * len(rows), 'actual_original_files': 2 * len(rows),
            'actual_retained_comparisons': len(compatibility), 'actual_retained_prepare_calls': len(compatibility),
            'all_shards_complete_claimed': False},
        'prepared_root': str(prepared_root), 'classification_sha256': digest(report_path),
        'source_file_classification_counts': source_counts,
        'class_target_assessment_counts': {'supported': len(rows), 'held': 0, 'failed': 0},
        'class_source_alias_holds_preserved': True,
        'wire_artifact_manifest_path': artifact.name, 'wire_artifact_manifest_sha256': digest(artifact),
        'retained_file_manifest_path': baseline.name, 'retained_file_manifest_sha256': digest(baseline),
        'all3262_retained_file_hashes_verified_before_and_after': True,
        'retained_file_count': len(frozen), 'exact_public_profile_file_count': len(profile_files),
        'retained_paths_and_bytes_unchanged': True, 'source_bindings_before': before, 'source_bindings_unchanged': True,
        'original_hashes': originals, 'original_hashes_sha256': mapping.sha(mapping.encode(originals)),
        'original_files_verified_before_and_after': 4206, 'guard': guard.counts,
        'unexpected_guard_events': guard.blocked_call_sites,
        'in_process_read_only_git_queries': guard.metadata_queries,
        'elapsed_seconds': {
            'new_classification_and_repeat_preparation': new_finished - new_started,
            'retained_comparisons_and_final_verification': time.monotonic() - new_finished,
            'total': time.monotonic() - started},
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Only actual assigned fresh two-member class preparation and assigned retained PR42 singleton '
                 'preparation once at exact original inputs, with identical singleton wire/nonruntime evidence. '
                 'Both class original filenames, policies, artifacts and complete common/class metadata are bound. '
                 'Alias source-file holds remain intact. Aggregate3465 wire-prepared targets representing3668 originals '
                 'and468 unmapped supported targets requires all four receipts; no class execution, adoption, '
                 'live compatibility, duplicate absence, grant, production identity, QA approval or release asserted.'})
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('EXXON_CLASS_SHARD_RESULT', json.dumps({
        'shard_index': args.shard_index, 'actual_new_class_preparations': len(rows),
        'actual_retained_comparisons': len(compatibility), 'receipt_sha256': digest(receipt), 'guard': guard.counts}),
        flush=True)


if __name__ == '__main__':
    main()
