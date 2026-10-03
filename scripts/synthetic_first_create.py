"""Sealed synthetic first-create evidence; no provider request or scan.

This deliberately narrower scope is authorized by the parent for an unused
synthetic create only. A negative indexed title search never reconciles a POST.
Historical evidence is immutable; the new runtime clock starts in execute().
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import synthetic_canary_controller as c
from scripts.upload_service import atomic_json, metadata_hash, read_json

FAILED_STATE_SHA = '158b34452cb43d102457bd6f700e3bd8bc0aabb7dd0412ba7d65a6e71116f23f'
FAILURE_RECEIPT = 'synthetic-owned-recovery-failure-receipt.json'
FAILURE_RECEIPT_SHA = 'b0d5826cc12866dde84ae92428ac9a82341dc0925b6969bee6892f7743a50d1b'
# Exact parent-provided hashes of the already completed diagnostics. These files
# stay at the original run root; no copy, provider read or new receipt is needed.
PINNED_DIAGNOSTICS = {
    'diagnostic-page101-limit-receipt.json': '8134aa13052e97ebd11a3a50380fe597b00cf4d028d364f0232758ed0a129227',
    'diagnostic-scoped-title-search-receipt.json': 'cbdb5267fa65be3ca0073d39045bb1d26611b6f7b40bf580702fd1eff31ba230',
}


def evidence_binding(folder, metadata, owner):
    """Recheck retained bytes locally, retaining all 185 observed reads."""
    c.require(c.sha((folder / c.RECOVERY_STATE).read_bytes()) == FAILED_STATE_SHA)
    prior = read_json(folder / c.RECOVERY_STATE)
    c.require(prior.get('schema_version') == 3 and prior.get('inventory_scope') == c.RECOVERY_SCOPE
              and prior.get('owner') == owner and prior.get('packet') == c.INVENTORY_SHA
              and prior.get('failed') is True and prior.get('completed') is False
              and prior.get('resume_allowed') is False and prior.get('get_attempts') == 102
              and prior.get('prior_observed_gets') == 80 and prior.get('next_page') == 101
              and prior.get('maximum_cumulative_gets') == 305 and len(prior.get('pages', [])) == 100)
    started, expired = datetime.fromisoformat(prior['started_at']), datetime.fromisoformat(prior['expires_at'])
    c.require(started.tzinfo is not None and expired == started + timedelta(minutes=30))
    old_binding = c.recovery_binding(folder, metadata, owner)
    c.require(prior.get('recovery_binding') == old_binding)
    receipt_file = folder / FAILURE_RECEIPT
    c.require(c.sha(receipt_file.read_bytes()) == FAILURE_RECEIPT_SHA)
    receipt = read_json(receipt_file)
    guard = receipt.get('guard', {})
    observations = guard.get('observations', [])
    c.require(receipt.get('failed') is True and receipt.get('completed') is False
              and receipt.get('get_attempts') == 102 and receipt.get('cumulative_inventory_gets') == 182
              and receipt.get('verified_pages') == 100 and receipt.get('next_page') == 101
              and receipt.get('diagnostics', {}).get('status') == 400
              and guard.get('transport_attempts') == 102 and guard.get('writes_performed') == 0
              and guard.get('community_pages') == 0 and len(observations) == 102
              and observations[-1].get('status') == 400)
    c.require(all(o.get('status') == 200 and all(o.get(k) is True for k in
              ('request_prepared', 'transport_entered', 'response_received', 'status_validated',
               'json_validated', 'owner_validated', 'links_validated', 'completed'))
              for o in observations[:-1]))
    pages = folder / c.RECOVERY_PAGES
    c.require({p.name for p in pages.iterdir()} == {f'page-{n:03d}.json' for n in range(1, 101)})
    seen, hashes = set(), {}
    for index, saved in enumerate(prior['pages'], 1):
        path = pages / f'page-{index:03d}.json'
        raw = path.read_bytes(); records = json.loads(raw)
        c.require(saved.get('page') == index and saved.get('count') == 100 and len(records) == 100
                  and saved.get('sha256') == c.sha(raw)
                  and saved.get('response_sha256') == observations[index].get('sha256'))
        c.check_owned_page(records, metadata, owner, seen)
        hashes[path.name] = c.sha(raw)
    c.require(len(seen) == 10000 and prior.get('ids') == sorted(seen))
    diagnostics = {}
    c.require(len(PINNED_DIAGNOSTICS) >= 2)
    for name, digest in PINNED_DIAGNOSTICS.items():
        c.require(c.valid_sha(digest))
        raw = (folder.parents[2] / name).read_bytes()
        c.require(c.sha(raw) == digest and isinstance(json.loads(raw), dict))
        diagnostics[name] = digest
    return {'failed_state_sha256': FAILED_STATE_SHA, 'failure_receipt_sha256': FAILURE_RECEIPT_SHA,
            'prior_recovery_binding': old_binding, 'retained_page_sha256': hashes,
            'diagnostic_receipt_sha256': diagnostics,
            'prior_read_counts': {'before_recovery':80, 'recovery':102, 'page_101_diagnostic':1,
                                  'scoped_diagnostics':2, 'total':185},
            'accepted_diagnostic_result': {'completed_at':'2026-10-03T03:16:38Z',
                'positive_control_status':200, 'positive_control_items':6,
                'own_title_status':200, 'own_title_items':0},
            'proof':'sealed_unused_first_create_with_title_candidate_evidence'}, sorted(seen)


def validate_grant(grant, paths, metadata, owner, evidence):
    c.require(isinstance(grant, dict) and grant.get('environment') == 'sandbox'
              and grant.get('inventory_scope') == c.FIRST_CREATE_SCOPE
              and grant.get('inventory_complete') is False and grant.get('owner') == owner
              and grant.get('packet') == c.INVENTORY_SHA and grant.get('evidence_binding') == evidence
              and grant.get('files') == [c.SOURCE + '.json']
              and grant.get('metadata_hashes') == {c.SOURCE + '.json':metadata_hash(metadata)}
              and grant.get('known_ids_sha256') == c.sha(Path(paths.already_uploaded_path).read_bytes()))
    started, expires = datetime.fromisoformat(grant['started_at']), datetime.fromisoformat(grant['valid_until'])
    c.require(started.tzinfo is not None and expires.tzinfo is not None
              and expires == started + timedelta(minutes=30) and started <= datetime.now(timezone.utc))
    retained = read_json(paths.already_uploaded_path)
    c.require(retained.get('inventory_scope') == c.FIRST_CREATE_SCOPE
              and retained.get('inventory_complete') is False and retained.get('environment') == 'sandbox'
              and retained.get('total_records') == 10000 and len(retained.get('records', [])) == 10000)
    expected_ids = read_json(Path(paths.state_dir) / 'sandbox' / c.RECOVERY_STATE)['ids']
    c.require([item.get('id') for item in retained['records']] == expected_ids)


def prepare_grant(paths, metadata, owner):
    """Only provider execute may create this separate durable 30-minute grant."""
    folder = Path(paths.state_dir) / 'sandbox'
    evidence, ids = evidence_binding(folder, metadata, owner)
    state_file = folder / 'synthetic-controller.json'
    grant_file, ids_file = Path(paths.safe_to_upload_path), Path(paths.already_uploaded_path)
    if not grant_file.exists():
        c.require(not ids_file.exists() and not state_file.exists() and not read_json(paths.uploads_registry_path, {}))
        now = datetime.now(timezone.utc)
        atomic_json(ids_file, {'environment':'sandbox', 'inventory_scope':c.FIRST_CREATE_SCOPE,
            'inventory_complete':False, 'total_records':len(ids), 'records':[{'id':i} for i in ids]})
        atomic_json(grant_file, {'environment':'sandbox', 'inventory_scope':c.FIRST_CREATE_SCOPE,
            'inventory_complete':False, 'owner':owner, 'packet':c.INVENTORY_SHA,
            'started_at':now.isoformat(), 'valid_until':(now+timedelta(minutes=30)).isoformat(),
            'files':[c.SOURCE+'.json'], 'metadata_hashes':{c.SOURCE+'.json':metadata_hash(metadata)},
            'known_ids_sha256':c.sha(ids_file.read_bytes()), 'evidence_binding':evidence})
        # Persist both new directory entries before the controller can send.
        import os
        fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    grant = read_json(grant_file)
    validate_grant(grant, paths, metadata, owner, evidence)
    state = read_json(state_file, {})
    c.require(state.get('completed') is True or datetime.now(timezone.utc) < datetime.fromisoformat(grant['valid_until']))
