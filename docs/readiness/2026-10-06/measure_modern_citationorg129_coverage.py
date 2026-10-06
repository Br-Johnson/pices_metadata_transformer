"""Guarded finite citation-organizations129 measurement; run only after freeze.

Freshly classify all129
selected sources and prepare twice. Compare each of the
3262 saved singleton preparations and203 saved class preparations once at exact
PR43 input paths. Preserve complete wire/legacy/nonruntime evidence and both
class originals. Only fresh /tmp output is writable; no provider claim is made.
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
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

HELPER = Path('docs/readiness/2026-10-06/measure_modern_exxon203_coverage.py')
HELPER_SHA = '8d4be3e8b484f0abc6e94074bf2cfea6e64f2d88dcb4c27ccabddd6b05ddd830'
PRIOR_VALIDATION = Path('docs/readiness/2026-10-06/modern_exxon203_validation.json')
PRIOR_VALIDATION_SHA = '49460d21fefe455fc3036a198704ae0587d5b7f453b408b7cc679601abcf21b4'
PRIOR_ROOTS = [Path(f'/tmp/pices-exxon203-shard{index}-v1') for index in range(4)]
PRIOR_PROFILES = Path('/workspace/pices-modern-exxon-pairs203-20261006/docs/readiness')
SOURCE_REVIEW = Path('docs/readiness/2026-10-06/modern_citationorg129_source_review.json')
SOURCE_REVIEW_SHA = 'ceeaec8fdd29b3a56dceb700d2b3c47395ec54d0755c4bc3018a01f50d359168'
INDEPENDENT_REVIEW = Path('docs/readiness/2026-10-06/modern_citationorg129_independent_review.json')
INDEPENDENT_REVIEW_SHA = 'dc9033829412054b0aed2a5ec354e9133889736859a39d727aeba98e59ae88c3'
MAPPING_SHA = '8ac4f141433dbbc58513ee968942ec23d2f484949b751fa01cba6bbcc393aee3'
DRAFT_ONLY = False  # Exact input pins integrated; independent review and code freeze precede execution.
STALE_CREATOR_IDS = {'FGDC-' + str(n) for n in (2552, 3951, 3952, 3953, 3954, 3956,
                                              3957, 3961, 3966, 3967, 3968, 3969)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_helpers(repo):
    path = repo / HELPER
    assert digest(path) == HELPER_SHA
    spec = importlib.util.spec_from_file_location('frozen_exxon203_measurement', path)
    exxon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exxon)
    institution, prior, base = exxon.load_helpers(repo)
    return exxon, institution, prior, base


def retained3465(repo, exxon, institution, prior, base):
    """Advance all singleton bindings through PR43; retain real paired inputs."""
    singles, frozen, profiles, roots, _ = exxon.retained3262(repo, institution, prior, base)
    original_frozen, original_profiles = dict(frozen), dict(profiles)
    aggregate_path = repo / PRIOR_VALIDATION
    assert digest(aggregate_path) == PRIOR_VALIDATION_SHA
    aggregate = json.loads(aggregate_path.read_bytes())
    assert aggregate['status'] == 'GUARDED_EXXON203_CLASS_AGGREGATE_PASS'
    assert aggregate['helper_sha256'] == HELPER_SHA and aggregate['all_shards_complete']
    assert aggregate['prior3262_validation_sha256'] == exxon.INSTITUTION_VALIDATION_SHA
    assert aggregate['all_saved_digests_reverified'] and aggregate['source_bindings_unchanged']
    assert aggregate['provider_requests'] == aggregate['provider_mutations'] == 0
    assert aggregate['coverage'] == {
        'fresh_new_class_prepare_calls': 406, 'new_class_execution_enabled': False,
        'new_class_original_files': 406, 'new_exxon_class_targets': 203,
        'prior_retained_singletons': 3262, 'retained_input_prepare_comparisons': 3262,
        'total_represented_originals': 3668, 'total_wire_prepared_targets': 3465}
    assert aggregate['source_status_unchanged'] == {
        'malformed_targets': 6, 'source_held_targets': 39, 'source_promotions': 0,
        'supported_pair_targets': 228, 'supported_singletons': 3705, 'supported_targets': 3933}
    proofs = {row['record_target_id']: row for row in aggregate['rows']}
    assert len(proofs) == len(aggregate['rows']) == 203
    class_manifest_path = repo / 'docs/readiness/2026-10-06/modern_exxon_pairs203.json'
    assert digest(class_manifest_path) == aggregate['mapping_manifest_sha256']
    targets = {row['record_target_id']: row for row in json.loads(class_manifest_path.read_bytes())['targets']}
    assert set(targets) == set(proofs)
    all_old, all_classes = sorted(singles, key=base.source_order), sorted(targets)
    classes, seen_old, old_rows, receipts = {}, set(), [], []

    def track(path, pin):
        path = Path(path)
        assert not path.is_symlink() and path.resolve() == path
        assert any(path.is_relative_to(root) for root in PRIOR_ROOTS)
        assert str(path) not in frozen or frozen[str(path)] == pin
        assert digest(path) == pin
        frozen[str(path)] = pin
        return path

    assert [shard['index'] for shard in aggregate['shards']] == list(range(4))
    for shard in aggregate['shards']:
        index, root = shard['index'], PRIOR_ROOTS[shard['index']]
        assert shard['root'] == str(root)
        coverage = json.loads(track(root / 'coverage.json', shard['receipt_sha256']).read_bytes())
        receipts.append(coverage)
        assert coverage['status'] == 'GUARDED_EXXON203_CLASS_SHARD_COVERAGE_PASS'
        assert coverage['runtime_sha256'] == aggregate['runtime_sha256']
        assert coverage['helper_sha256'] == HELPER_SHA and coverage['guard_sha256'] == base.GUARD_SHA
        assert coverage['environment_cleared_dummy_credentials_only']
        assert coverage['source_bindings_unchanged'] and coverage['retained_paths_and_bytes_unchanged']
        assert coverage['all3262_retained_file_hashes_verified_before_and_after']
        assert coverage['original_files_verified_before_and_after'] == 4206
        assert coverage['provider_requests'] == coverage['provider_mutations'] == 0
        assert not coverage['unexpected_guard_events'] and not any(coverage['guard']['tests'].values())
        assert coverage['guard'] == shard['guard']
        assert coverage['sharding']['index'] == index and coverage['sharding']['count'] == 4
        artifact = json.loads(track(root / 'wire_artifact_manifest.json',
                                   shard['artifact_manifest_sha256']).read_bytes())
        assert coverage['wire_artifact_manifest_sha256'] == shard['artifact_manifest_sha256']
        files = json.loads(track(root / 'retained_file_manifest.json',
                                shard['retained_file_manifest_sha256']).read_bytes())
        assert coverage['retained_file_manifest_sha256'] == shard['retained_file_manifest_sha256']
        assert files == {'public_baseline_files': original_frozen, 'exact_public_profile_files': original_profiles}
        prepared_root = root / 'prepared'
        assert coverage['prepared_root'] == str(prepared_root)
        report = json.loads(track(prepared_root / 'classification.json', shard['classification_sha256']).read_bytes())
        assert coverage['classification_sha256'] == shard['classification_sha256']
        rows, old = artifact['exxon_class_rows'], artifact['retained3262_rows']
        wanted_old, wanted_classes = all_old[index::4], all_classes[index::4]
        assert [row['source_id'] for row in old] == wanted_old
        assert [row['record_target_id'] for row in rows] == wanted_classes
        assert coverage['sharding']['assigned_retained_source_ids'] == wanted_old
        assert coverage['sharding']['assigned_new_target_ids'] == wanted_classes
        assert len(old) == shard['retained_source_count'] == (816, 816, 815, 815)[index]
        assert len(rows) == shard['new_class_count'] == (51, 51, 51, 50)[index]
        wanted_sources = sorted([sid for tid in wanted_classes for sid in targets[tid]['source_ids']],
                                key=base.source_order)
        assert coverage['sharding']['assigned_new_source_ids'] == wanted_sources
        assert {row['source_id'] for row in report['records']} == set(wanted_sources)
        assert report['summary']['source_status_counts'] == {'supported': 0, 'held': len(wanted_sources), 'failed': 0}
        assert coverage['class_source_alias_holds_preserved']
        assert coverage['class_target_assessment_counts'] == {'supported': len(rows), 'held': 0, 'failed': 0}
        for source in report['records']:
            assert source['source_status'] == 'held' and source['source_status_without_aliases'] == 'supported'
            assert source['hold_reasons'] == ['Exact-copy aliases require identity adjudication']
        old_rows.extend(old)
        for saved in old:
            sid = saved['source_id']
            assert sid not in seen_old
            seen_old.add(sid)
            original = singles[sid]
            assert all(saved[key] == value for key, value in original.items() if key != 'evidence')
            path = track(root / saved['current_preparation_path'], saved['current_preparation_sha256'])
            packet = json.loads(path.read_bytes())
            assert packet['source_id'] == packet['evidence']['source_id'] == sid
            assert packet['binding'] == saved['current_binding'] == hashlib.sha256(base.encode(packet['evidence'])).hexdigest()
            assert packet['evidence']['runtime_sha256'] == aggregate['runtime_sha256']
            assert base.nonruntime(packet['evidence']) == base.nonruntime(original['evidence'])
            assert saved['wire_and_nonruntime_evidence_equal']
            assert saved['nonruntime_evidence_sha256'] == hashlib.sha256(base.encode(base.nonruntime(packet['evidence']))).hexdigest()
            original.update(evidence=packet['evidence'], binding=packet['binding'],
                            preparation_path=str(path), preparation_sha256=saved['current_preparation_sha256'])
        for saved in rows:
            tid = saved['record_target_id']
            assert tid not in classes and proofs[tid] == saved | {'shard_index': index}
            target = targets[tid]
            assert saved['source_ids'] == target['source_ids']
            assert saved['source_sha256'] == target['source_sha256']
            packet_path = track(root / saved['preparation_path'], saved['preparation_sha256'])
            packet = json.loads(packet_path.read_bytes())
            evidence = packet['evidence']
            assert packet['binding'] == saved['binding'] == hashlib.sha256(base.encode(evidence)).hexdigest()
            assert packet['record_target_id'] == evidence['record_target_id'] == tid
            assert packet['source_ids'] == evidence['source_ids'] == saved['source_ids']
            assert evidence['runtime_sha256'] == aggregate['runtime_sha256']
            assert evidence['reviewed_at'] == coverage['assessment_time'] == '2026-10-05T18:00:00+00:00'
            wire_path = track(root / saved['wire_path'], saved['wire_sha256'])
            legacy_path = track(root / saved['legacy_target_path'], saved['legacy_target_sha256'])
            legacy = json.loads(legacy_path.read_bytes())
            assert evidence['legacy_target_sha256'] == hashlib.sha256(base.encode(legacy)).hexdigest()
            assert evidence['wire_sha256'] == saved['wire_sha256']
            assert legacy['metadata'] == packet['complete_legacy_class_metadata']
            assert packet['complete_legacy_metadata_preserved'] and packet['both_original_files_and_policies_verified']
            assert packet['unchanged_repeat_equal'] and saved['prepare_calls'] == 2
            assert all(packet[key] is False and legacy[key] is False and evidence[key] is False
                       for key in ('upload_eligible', 'remote_verified', 'publication_approved'))
            wire = json.loads(wire_path.read_bytes())
            preserved = wire['metadata']['additional_descriptions'][0]['description']
            assert json.loads(html.unescape(preserved.split('<pre>', 1)[1][:-6])) == legacy['metadata']
            assert evidence['legacy_metadata_sha256'] == hashlib.sha256(base.encode(legacy['metadata'])).hexdigest()
            assert evidence['artifact_contract'] == legacy['artifact_contract']
            assert evidence['artifact_contract']['sha256'] == saved['artifact_contract_sha256']
            members = []
            for member, item in zip(saved['members'], evidence['inputs'], strict=True):
                sid = member['source_id']
                assert sid not in singles and sid in target['source_ids']
                assert member['source_sha256'] == target['source_sha256'] == digest(repo / 'FGDC' / (sid + '.xml'))
                inp = track(root / member['prepared_input_path'], member['prepared_input_sha256'])
                original = track(root / member['original_copy_path'], member['source_sha256'])
                source_copy = track(root / member['source_copy_path'], member['source_sha256'])
                assert inp == prepared_root / 'data/zenodo_json' / (sid + '.json')
                assert original == prepared_root / 'data/original_fgdc' / (sid + '.xml')
                assert item['prepared_input_path'] == str(inp) and item['source_path'] == str(original)
                assert item['prepared_input_sha256'] == member['prepared_input_sha256']
                assert original.read_bytes() == source_copy.read_bytes() == (repo / 'FGDC' / (sid + '.xml')).read_bytes()
                payload = json.loads(inp.read_bytes())
                assert payload['metadata'] == packet['complete_common_source_metadata']
                for reference in payload['artifact_policy'].values():
                    if not isinstance(reference, dict) or 'manifest_path' not in reference:
                        continue
                    public = Path(reference['manifest_path'])
                    assert public.resolve() == public and not public.is_symlink() and public.is_relative_to(PRIOR_PROFILES)
                    relative = public.relative_to(PRIOR_PROFILES)
                    assert str(relative) in (base.PROFILE_FILES |
                                             {'2026-10-02/exxon_citation_interpretation.json'})
                    pin = reference['manifest_sha256']
                    assert digest(public) == pin == digest(repo / 'docs/readiness' / relative)
                    assert str(public) not in profiles or profiles[str(public)] == pin
                    profiles[str(public)] = pin
                members.append(member | {'prepared_input_path': str(inp), 'original_copy_path': str(original),
                                         'source_copy_path': str(source_copy)})
            assert [member['source_id'] for member in members] == saved['source_ids'] and len(members) == 2
            classes[tid] = {
                'record_target_id': tid, 'source_ids': saved['source_ids'], 'source_sha256': saved['source_sha256'],
                'prepared_root': str(prepared_root), 'reviewed_at': evidence['reviewed_at'],
                'wire_path': str(wire_path), 'wire_sha256': saved['wire_sha256'],
                'legacy_target_path': str(legacy_path), 'legacy_target_sha256': saved['legacy_target_sha256'],
                'preparation_path': str(packet_path), 'preparation_sha256': saved['preparation_sha256'],
                'binding': packet['binding'], 'evidence': evidence, 'members': members}
    assert seen_old == set(singles) and len(singles) == 3262 and set(classes) == set(proofs)
    assert len({sid for row in classes.values() for sid in row['source_ids']}) == 406
    old_rows.sort(key=lambda row: base.source_order(row['source_id']))
    assert hashlib.sha256(base.encode(old_rows)).hexdigest() == aggregate['retained3262_comparison_rows_sha256']
    for key in ('source_bindings_before', 'runtime_sha256', 'helper_sha256', 'policy_input_bindings',
                'original_hashes', 'original_hashes_sha256', 'assessment_time'):
        assert all(receipt[key] == receipts[0][key] for receipt in receipts)
    assert receipts[0]['original_hashes_sha256'] == aggregate['original_hashes_sha256']
    return singles, classes, frozen, profiles, [*roots, *PRIOR_ROOTS], receipts[0]


def measure_new(ids, members, groups, bindings, output, mapping, fixtures, paths_class,
                assess, max_bytes, originals, base):
    """Every input is freshly classified, including the12 stale historical rows."""
    prepared_root = fixtures(output, ids=ids)
    paths = paths_class(str(prepared_root), 'production')
    report_path = prepared_root / 'classification.json'
    report = json.loads(report_path.read_bytes())
    assert len(report['records']) == len(ids) and {row['source_id'] for row in report['records']} == set(ids)
    assert report['summary']['source_status_counts'] == {'supported': len(ids), 'held': 0, 'failed': 0}
    assert {path.stem for path in (output / 'sources').glob('*.xml')} == set(ids)
    assert {path.stem for path in Path(paths.zenodo_json_dir).glob('*.json')} == set(ids)
    directory = output / 'citationorg'
    directory.mkdir()
    rows = []
    for index, sid in enumerate(ids, 1):
        started = time.monotonic()
        group, member = groups[sid], members[sid]
        json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
        raw = json_file.read_bytes()
        payload = mapping.parse(raw)
        raw_metadata = payload['metadata']
        current, repeated = mapping.prepare(json_file, paths), mapping.prepare(json_file, paths)
        assert current == repeated and raw == json_file.read_bytes()
        metadata, source_sha, artifact, _ = assess(json_file, paths)
        assert raw_metadata['creators'] == metadata['creators'] == group['creators']
        assert payload['artifact_policy']['creator_interpretation']['manifest_sha256'] == mapping.PROFILE_SHA
        assert current.evidence['schema_version'] == 7 and current.evidence['policy'] == mapping.CITATION_ORG_POLICY
        assert current.evidence['mapping_manifest_sha256'] == mapping.CITATION_ORG_MAPPING_SHA == MAPPING_SHA
        assert current.evidence['creator_profile_sha256'] == mapping.PROFILE_SHA
        assert current.evidence['creator_cohort'] == member['creator_cohort']
        assert current.evidence['artifact_contract'] == artifact
        assert current.binding == mapping.sha(mapping.encode(current.evidence))
        assert len(current.body) <= max_bytes and len(current.xml) <= max_bytes
        wire = base.check_preservation(mapping, current, metadata)
        assert wire['metadata']['creators'] == group['modern_creators']
        original = (mapping.ROOT / 'FGDC' / (sid + '.xml')).read_bytes()
        root = ET.fromstring(original)
        assert mapping.sha(mapping.encode(mapping.source_element(root))) == bindings[sid]['source_root_sha256']
        copy_path = Path(paths.original_fgdc_dir) / (sid + '.xml')
        assert current.xml == original == copy_path.read_bytes() == (output / 'sources' / (sid + '.xml')).read_bytes()
        assert mapping.sha(original) == source_sha == member['source_sha256'] == originals[sid + '.xml']
        wire_path, evidence_path = directory / (sid + '.wire.json'), directory / (sid + '.preparation.json')
        with wire_path.open('xb') as stream:
            stream.write(current.body)
        base.write_json(evidence_path, {
            'source_id': sid, 'binding': current.binding, 'evidence': current.evidence,
            'complete_raw_input_metadata': raw_metadata, 'complete_legacy_metadata': metadata,
            'complete_legacy_metadata_preserved': True, 'exact_creators_date_access_and_rights': True,
            'fresh_source_assessment_true': True, 'exact_source_root_verified': True,
            'unchanged_repeat_equal': True})
        rows.append({
            'source_id': sid, 'source_sha256': source_sha, 'binding': current.binding,
            'policy': current.evidence['policy'], 'creator_cohort': member['creator_cohort'],
            'prepared_input_path': str(json_file.relative_to(output)), 'prepared_input_sha256': mapping.sha(raw),
            'raw_input_metadata_sha256': mapping.sha(mapping.encode(raw_metadata)),
            'normalized_legacy_metadata_sha256': current.evidence['legacy_metadata_sha256'],
            'original_copy_path': str(copy_path.relative_to(output)),
            'wire_path': str(wire_path.relative_to(output)), 'wire_sha256': digest(wire_path),
            'preparation_path': str(evidence_path.relative_to(output)), 'preparation_sha256': digest(evidence_path),
            'body_bytes': len(current.body), 'xml_bytes': len(current.xml), 'prepare_calls': 2,
            'fresh_source_assessment_true': True, 'elapsed_seconds': time.monotonic() - started})
        if index % 10 == 0 or index == len(ids):
            print('NEW_CITATIONORG_PROGRESS', index, 'of', len(ids), flush=True)
    return prepared_root, report_path, rows


def compare_retained_classes(ids, retained, output, modern, mapping, paths_class, max_bytes, originals, base):
    class RetainedPaths(paths_class):
        def _prepare_dir(self, new_path, legacy_path=None, migrate_patterns=None):
            assert Path(new_path).is_dir()
            return new_path

        def _prepare_file(self, new_path, legacy_path=None):
            assert Path(new_path).parent.is_dir()
            return new_path

    directory = output / 'retained_classes'
    directory.mkdir()
    paths_by_root, rows = {}, []
    for index, tid in enumerate(ids, 1):
        prior = retained[tid]
        root = prior['prepared_root']
        if root not in paths_by_root:
            paths_by_root[root] = RetainedPaths(root, 'production')
        current = modern.prepare(tid, paths_by_root[root], reviewed_at=prior['reviewed_at'])
        assert current.record_target_id == tid and list(current.source_ids) == prior['source_ids']
        assert current.body == Path(prior['wire_path']).read_bytes()
        assert current.legacy_target == json.loads(Path(prior['legacy_target_path']).read_bytes())
        assert base.nonruntime(current.evidence) == base.nonruntime(prior['evidence'])
        assert current.binding == mapping.sha(mapping.encode(current.evidence))
        assert len(current.body) <= max_bytes
        assert len(current.originals) == len(prior['members']) == 2
        for (filename, raw), member in zip(current.originals, prior['members'], strict=True):
            assert filename == member['name'] == member['source_id'] + '.xml'
            assert raw == Path(member['original_copy_path']).read_bytes() == Path(member['source_copy_path']).read_bytes()
            assert raw == (mapping.ROOT / 'FGDC' / filename).read_bytes()
            assert mapping.sha(raw) == member['source_sha256'] == prior['source_sha256'] == originals[filename]
            assert len(raw) == member['size'] and len(raw) <= max_bytes
            assert digest(member['prepared_input_path']) == member['prepared_input_sha256']
        evidence_path = directory / ('XMLCLASS-' + tid.split(':')[1] + '.preparation.json')
        base.write_json(evidence_path, {'record_target_id': tid, 'source_ids': list(current.source_ids),
                                       'binding': current.binding, 'evidence': current.evidence})
        rows.append({key: value for key, value in prior.items() if key != 'evidence'} | {
            'current_binding': current.binding, 'current_preparation_path': str(evidence_path.relative_to(output)),
            'current_preparation_sha256': digest(evidence_path), 'wire_legacy_and_nonruntime_evidence_equal': True,
            'nonruntime_evidence_sha256': mapping.sha(mapping.encode(base.nonruntime(current.evidence))),
            'current_prepare_calls': 1})
        if index % 10 == 0 or index == len(ids):
            print('RETAINED_CLASS_PROGRESS', index, 'of', len(ids), flush=True)
    return rows


def main():
    if DRAFT_ONLY or not all(
            len(pin) == 64 and all(char in '0123456789abcdef' for char in pin)
            for pin in (SOURCE_REVIEW_SHA, INDEPENDENT_REVIEW_SHA, MAPPING_SHA)):
        raise RuntimeError('Nonexecutable draft: freeze reviewed129 manifest/source pins and helper before enabling')
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
    exxon, institution, prior, base = load_helpers(repo)
    assert digest(repo / 'ci/run_offline_tests.py') == base.GUARD_SHA
    retained, classes, frozen, profile_files, roots, previous_receipt = retained3465(repo, exxon, institution, prior, base)
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
    from scripts.agent_qa import assess_source
    from scripts.modern_singleton_executor import MAX_BYTES
    from scripts.path_config import OutputPaths
    from tests.modern_singleton_fixtures import NOW, prepare_sources

    before = source_bindings(repo)
    originals = {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert len(originals) == 4206 and originals == previous_receipt['original_hashes']
    assert NOW.isoformat() == previous_receipt['assessment_time']
    helper_sha, runtime_sha = digest(Path(__file__)), mapping.runtime_binding()
    manifest = mapping.pinned(mapping.CITATION_ORG_MAPPING, mapping.CITATION_ORG_MAPPING_SHA)
    assert mapping.CITATION_ORG_MAPPING_SHA == MAPPING_SHA
    assert manifest['policy'] == mapping.CITATION_ORG_POLICY == 'modern-xml-citation-organizations129-v1'
    assert manifest['schema_version'] == 1 and manifest['kind'] == 'modern-citation-organizations129-v1'
    assert manifest['member_count'] == 129 and manifest['group_count'] == len(manifest['groups']) == 53
    assert manifest['source_plan_sha256'] == mapping.PLAN_SHA
    assert manifest['creator_profile_sha256'] == mapping.PROFILE_SHA
    assert manifest['source_review_sha256'] == SOURCE_REVIEW_SHA
    assert manifest['independent_review_sha256'] == INDEPENDENT_REVIEW_SHA
    assert digest(repo / SOURCE_REVIEW) == SOURCE_REVIEW_SHA and digest(repo / INDEPENDENT_REVIEW) == INDEPENDENT_REVIEW_SHA
    review = json.loads((repo / SOURCE_REVIEW).read_bytes())
    independent = json.loads((repo / INDEPENDENT_REVIEW).read_bytes())
    assert independent['verdict'] == 'APPROVE_EXACT_FINITE_WIRE_PROJECTION_WITH_PRESERVATION_CONDITIONS'
    assert not independent['held_from_proposed129'] and not independent['material_findings']
    assert review['members'] == independent['approved_members']
    assert mapping.sha(mapping.encode(review['members'])) == review['membership_sha256'] == independent['approved_membership_sha256']
    assert set(review['selected_historical_creator_mismatches']) == STALE_CREATOR_IDS
    source_rows = {row['source_id']: row for row in review['source_rows']}
    bindings = {row['source_id']: row for row in independent['verified_source_bindings']}
    assert len(bindings) == len(source_rows) == len(independent['verified_source_bindings']) == 129
    assert mapping.sha(mapping.encode(independent['verified_source_bindings'])) == independent['verified_source_bindings_sha256']
    groups = {member['source_id']: group for group in manifest['groups'] for member in group['members']}
    all_members = [member for group in manifest['groups'] for member in group['members']]
    members = {member['source_id']: member for member in all_members}
    assert len(members) == len(all_members) == 129 and set(members) == set(bindings) == set(source_rows)
    assert not set(members) & set(retained)
    assert not set(members) & {sid for row in classes.values() for sid in row['source_ids']}
    projections = {row['cluster_index']: row for row in independent['approved_projection_groups']}
    profiles = {row['profile']: row for row in mapping.pinned(mapping.PROFILE, mapping.PROFILE_SHA)['cohorts']}
    plan = {row['record_target_id']: row for row in mapping.pinned(mapping.PLAN, mapping.PLAN_SHA)['targets']}
    assert len(projections) == len(manifest['groups']) == 53
    for group in manifest['groups']:
        approved = projections[group['group']]
        assert group['creators'] == approved['complete_legacy_creators']
        assert group['modern_creators'] == approved['proposed_modern_creators']
        assert [{'source_id': row['source_id'], 'source_sha256': row['source_sha256']} for row in group['members']] == approved['members']
        assert mapping.sha(mapping.encode(group['creators'])) == approved['complete_legacy_creators_sha256']
        assert mapping.sha(mapping.encode(group['modern_creators'])) == approved['proposed_modern_creators_sha256']
        for member in group['members']:
            sid = member['source_id']
            assert originals[sid + '.xml'] == member['source_sha256'] == bindings[sid]['source_sha256']
            assert member['creator_cohort'] == bindings[sid]['creator_cohort']
            cohort = profiles[member['creator_cohort']]
            assert mapping.sha(mapping.encode(cohort)) == member['cohort_object_sha256'] == bindings[sid]['cohort_object_sha256']
            assert cohort['creators'] == group['creators'] == source_rows[sid]['complete_legacy_creators']
            assert plan[sid]['source_ids'] == [sid] and plan[sid]['source_semantic_status'] == 'supported'
            assert plan[sid]['source_sha256'] == member['source_sha256']
            assert mapping.sha(mapping.encode(plan[sid])) == source_rows[sid]['source_plan_target_sha256']
    policy_inputs = {repo / path: pin for path, pin in previous_receipt['policy_input_bindings'].items()}
    policy_inputs.update({mapping.CITATION_ORG_MAPPING: MAPPING_SHA, repo / SOURCE_REVIEW: SOURCE_REVIEW_SHA,
                          repo / INDEPENDENT_REVIEW: INDEPENDENT_REVIEW_SHA,
                          repo / PRIOR_VALIDATION: PRIOR_VALIDATION_SHA, repo / HELPER: HELPER_SHA})
    assert all(path.is_relative_to(repo) and path.resolve() == path for path in policy_inputs)
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    assert all(digest(path) == pin for path, pin in frozen.items())
    assert all(digest(path) == pin for path, pin in profile_files.items())
    all_new, all_old, all_classes = sorted(members, key=base.source_order), sorted(retained, key=base.source_order), sorted(classes)
    new_ids, old_ids, class_ids = all_new[args.shard_index::4], all_old[args.shard_index::4], all_classes[args.shard_index::4]
    assert len(new_ids) == (33, 32, 32, 32)[args.shard_index] and len(old_ids) == (816, 816, 815, 815)[args.shard_index]
    assert len(class_ids) == (51, 51, 51, 50)[args.shard_index]
    print('CITATIONORG_SHARD_START', args.shard_index, 'new', len(new_ids), 'retained', len(old_ids),
          'retained_classes', len(class_ids), flush=True)
    prepared_root, report_path, rows = measure_new(new_ids, members, groups, bindings, output, mapping, prepare_sources,
                                                 OutputPaths, assess_source, MAX_BYTES, originals, base)
    new_finished = time.monotonic()
    compatibility = base.compare_retained(old_ids, retained, output, mapping, OutputPaths, MAX_BYTES, originals)
    for row in compatibility:
        row['body_bytes'] = Path(row['wire_path']).stat().st_size
        row['xml_bytes'] = (mapping.ROOT / 'FGDC' / (row['source_id'] + '.xml')).stat().st_size
    class_comparisons = compare_retained_classes(class_ids, classes, output, modern, mapping,
                                                OutputPaths, MAX_BYTES, originals, base)
    assert [row['source_id'] for row in rows] == new_ids
    assert [row['source_id'] for row in compatibility] == old_ids
    assert [row['record_target_id'] for row in class_comparisons] == class_ids
    assert originals == {path.name: digest(path) for path in sorted((repo / 'FGDC').glob('*.xml'))}
    assert before == source_bindings(repo) and runtime_sha == mapping.runtime_binding()
    assert helper_sha == digest(Path(__file__))
    assert all(digest(path) == pin for path, pin in policy_inputs.items())
    assert all(digest(path) == pin for path, pin in frozen.items())
    assert all(digest(path) == pin for path, pin in profile_files.items())
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    artifact, baseline = output / 'wire_artifact_manifest.json', output / 'retained_file_manifest.json'
    base.write_json(artifact, {'citationorg_rows': rows, 'retained3262_rows': compatibility,
                               'retained203_class_rows': class_comparisons})
    base.write_json(baseline, {'public_baseline_files': frozen, 'exact_public_profile_files': profile_files})
    receipt = output / 'coverage.json'
    base.write_json(receipt, {
        'schema_version': 1, 'status': 'GUARDED_CITATIONORG129_SHARD_COVERAGE_PASS',
        'actual_checkout_revision': revision, 'helper_sha256': helper_sha,
        'reused_helpers_sha256': {str(HELPER): HELPER_SHA, str(exxon.HELPER): exxon.HELPER_SHA,
                                 str(institution.HELPER): institution.HELPER_SHA, str(prior.HELPER): prior.HELPER_SHA},
        'runtime_sha256': runtime_sha, 'guard_sha256': base.GUARD_SHA,
        'environment_cleared_dummy_credentials_only': True,
        'prior3465_validation_sha256': PRIOR_VALIDATION_SHA,
        'mapping_manifest_sha256': MAPPING_SHA, 'source_review_sha256': SOURCE_REVIEW_SHA,
        'independent_review_sha256': INDEPENDENT_REVIEW_SHA,
        'creator_profile_sha256': mapping.PROFILE_SHA, 'policy': mapping.CITATION_ORG_POLICY,
        'evidence_schema_version': 7, 'assessment_time': NOW.isoformat(),
        'policy_input_bindings': {str(path.relative_to(repo)): pin for path, pin in policy_inputs.items()},
        'sharding': {
            'index': args.shard_index, 'count': 4,
            'assignment': 'numeric singleton IDs and lexical class IDs, independently ids[index::4]',
            'new_manifest_members': 129, 'retained_baseline_members': 3262, 'retained_baseline_classes': 203,
            'sorted_new_ids_sha256': mapping.sha(mapping.encode(all_new)),
            'sorted_retained_ids_sha256': mapping.sha(mapping.encode(all_old)),
            'sorted_retained_class_ids_sha256': mapping.sha(mapping.encode(all_classes)),
            'assigned_new_source_ids': new_ids, 'assigned_retained_source_ids': old_ids,
            'assigned_retained_class_ids': class_ids, 'actual_new_preparations': len(rows),
            'actual_new_prepare_calls': len(rows) * 2, 'actual_retained_comparisons': len(compatibility),
            'actual_retained_prepare_calls': len(compatibility), 'actual_retained_class_comparisons': len(class_comparisons),
            'actual_retained_class_prepare_calls': len(class_comparisons), 'all_shards_complete_claimed': False},
        'prepared_root': str(prepared_root), 'classification_sha256': digest(report_path),
        'classification_counts': {'supported': len(rows), 'held': 0, 'failed': 0},
        'fresh_classification_including_historical_creator_mismatches': True,
        'historical_creator_mismatch_ids': sorted(STALE_CREATOR_IDS, key=base.source_order),
        'retained_class_alias_holds_preserved': True,
        'source_status_unchanged': {'supported_targets': 3933, 'supported_singletons': 3705,
                                  'supported_pair_targets': 228, 'source_held_targets': 39,
                                  'malformed_targets': 6, 'source_promotions': 0},
        'wire_artifact_manifest_path': artifact.name, 'wire_artifact_manifest_sha256': digest(artifact),
        'retained_file_manifest_path': baseline.name, 'retained_file_manifest_sha256': digest(baseline),
        'all3465_retained_file_hashes_verified_before_and_after': True,
        'retained_file_count': len(frozen), 'exact_public_profile_file_count': len(profile_files),
        'retained_paths_and_bytes_unchanged': True, 'source_bindings_before': before, 'source_bindings_unchanged': True,
        'original_hashes': originals, 'original_hashes_sha256': mapping.sha(mapping.encode(originals)),
        'original_files_verified_before_and_after': 4206, 'guard': guard.counts,
        'unexpected_guard_events': guard.blocked_call_sites,
        'in_process_read_only_git_queries': guard.metadata_queries,
        'elapsed_seconds': {'new_classification_and_repeat_preparation': new_finished - started,
                            'retained_comparisons_and_final_verification': time.monotonic() - new_finished,
                            'total': time.monotonic() - started},
        'provider_requests': 0, 'provider_mutations': 0,
        'scope': 'Only assigned fresh classification/repeat singleton preparation and assigned retained PR43 '
                 'singleton/class preparation once at exact original inputs. Identical prior wires, full class '
                 'legacy targets, both class originals and nonruntime evidence are verified. All129 new inputs '
                 'are freshly classified, including12 stale historical creator inputs. Aggregate3391 singletons '
                 '+203 classes=3594 wire-prepared targets/3797 original XML requires all four receipts. '
                 'No class execution, live compatibility, duplicate absence, grant, production identity, '
                 'QA approval, community acceptance or release is asserted.'})
    assert not guard.blocked_call_sites and not any(guard.counts['tests'].values())
    print('CITATIONORG_SHARD_RESULT', json.dumps({
        'shard_index': args.shard_index, 'actual_new_preparations': len(rows),
        'actual_retained_comparisons': len(compatibility), 'actual_retained_class_comparisons': len(class_comparisons),
        'receipt_sha256': digest(receipt), 'guard': guard.counts}), flush=True)


if __name__ == '__main__':
    main()
