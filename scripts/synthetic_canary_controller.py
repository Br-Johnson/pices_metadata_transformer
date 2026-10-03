"""Frozen synthetic-only sandbox controller; durable attempt caps and no implicit retry.

The original run and ledger are mandatory. Every transport is guarded; returned
links are inert except the one checked bucket/file. Shared receipts omit private
IDs, owners, URLs, credentials, response bodies and arbitrary exception text.
"""
import argparse
from datetime import datetime, timezone, timedelta
import contextlib
import fcntl
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import signal
from urllib.parse import urlsplit, quote, parse_qsl
from uuid import UUID

import requests
from scripts.artifact_contract import prepare_artifact, validate_files
from scripts.path_config import OutputPaths
from scripts.sandbox_read_guard import SandboxInventoryGuard, credential_echoed
from scripts.upload_service import (DraftUploadService, atomic_json, read_json,
                                    prepare_metadata, metadata_hash, require_inventory)
from scripts.verify_uploads import compare_metadata
from scripts.zenodo_api import create_zenodo_client, load_zenodo_token, ZenodoAPIError, _exception_diagnostics

ORIGIN = 'https://sandbox.zenodo.org'
SOURCE = 'SYNTHETIC-PICES-9379FD8-20261002'
RUN = Path('/workspace/pices-sandbox-run-9379fd8-20261002/synthetic')
PACKET = Path(__file__).resolve().parents[1] / 'docs/handoff/sandbox-canary-20261002'
INVENTORY_SHA = '428559c7a8e81e84c22627b0add1230797b92013f87152e2ee3024b56af30fd1'
OWNED_SCOPE = 'synthetic_owned_namespace_pages_v2'
OWNED_STATE = 'synthetic-owned-pages-controller.json'
RECOVERY_SCOPE = 'synthetic_owned_namespace_recovery_v3'
RECOVERY_STATE = 'synthetic-owned-recovery-controller.json'
RECOVERY_PAGES = 'synthetic-owned-recovery-pages'
RECOVERY_RECEIPT = 'synthetic-owned-pages-failure-receipt.json'
RECOVERY_DIAGNOSTIC = 'synthetic-owned-page-63-diagnostic-receipt.json'
COMPATIBILITY_COMMIT = '58bbf0d501cda9244804734d52a1d425d47bd0c3'
COMPATIBILITY_RECEIPT_SHA = '65efffe3c461e620323b01f2f7ee34cadd31b61f13e92f72d2a63a3c04616f3c'


def require(ok, stage='request_prepare'):
    if not ok:
        raise ZenodoAPIError('Synthetic controller stopped', stage=stage, exception_type='ValueError')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bindings(stage):
    require(Path(stage).resolve() == RUN.resolve())
    raw = (PACKET / 'INVENTORY.json').read_bytes()
    require(sha(raw) == INVENTORY_SHA)
    for entry in json.loads(raw):
        data = (PACKET / entry['path']).read_bytes()
        require(len(data) == entry['bytes'] and sha(data) == entry['sha256'])
    plan = read_json(PACKET / 'selection.json')['synthetic']
    paths = OutputPaths(str(stage), 'sandbox')
    file = Path(paths.zenodo_json_dir) / (SOURCE + '.json')
    require({p.name for p in Path(paths.zenodo_json_dir).glob('*.json')} == {file.name})
    require(sha(file.read_bytes()) == plan['prepared_payload_sha256'])
    metadata, source, digest = prepare_metadata(str(file), paths)
    artifact = prepare_artifact(read_json(file), source)
    require(metadata == read_json(PACKET / plan['expected_metadata_file']))
    require(metadata_hash(metadata) == plan['expected_metadata_sha256'])
    require(artifact == plan['artifact_contract'] and digest == plan['source_sha256'])
    raw_source = Path(source).read_bytes()
    require(len(raw_source) == plan['source_bytes'] and sha(raw_source) == digest)
    return paths, file, metadata, artifact, plan


def check_owned_page(records, metadata, owner, seen):
    require(isinstance(records, list) and len(records) <= 100, 'response_json')
    for item in records:
        require(isinstance(item, dict) and type(item.get('id')) is int and item['id'] > 0
                and item['id'] not in seen and type(item.get('owner')) is int and item['owner'] == owner,
                'response_owner')
        md, files = item.get('metadata'), item.get('files')
        require(isinstance(md, dict) and isinstance(files, list), 'response_json')
        # Historical empty drafts can have no title. Check every supplied
        # identity field without requiring unrelated drafts to be complete.
        title = md.get('title', '')
        require(isinstance(title, str), 'response_json')
        same_run = title.strip().casefold() == metadata['title'].strip().casefold()
        same_run |= SOURCE in json.dumps(md, sort_keys=True)
        for remote_file in files:
            require(isinstance(remote_file, dict), 'response_json')
            names = [remote_file[k] for k in ('filename', 'name', 'key') if k in remote_file]
            require(names and all(isinstance(name, str) and bool(name) for name in names), 'response_json')
            same_run |= SOURCE + '.xml' in names
        require(not same_run, 'response_owner')
        seen.add(item['id'])


def legacy_receipt_hashes(folder, owner):
    """Only the previously reviewed read-only failures may precede this run."""
    hashes = {}
    for name, attempts in [('synthetic-inventory-controller.json', 2),
                           ('synthetic-owned-inventory-controller.json', 10)]:
        path = folder / name
        if path.exists():
            prior = read_json(path)
            require(prior.get('completed') is False and prior.get('failed') is True
                    and prior.get('get_attempts') == attempts and prior.get('owner') == owner
                    and prior.get('packet') == INVENTORY_SHA)
            if attempts == 2:
                require(prior.get('diagnostics', {}).get('status') == 400)
            else:
                diagnostics = prior.get('diagnostics', {})
                require(prior.get('inventory_scope') == 'synthetic_owned_namespace_only_v1'
                        and prior.get('prior_observed_gets') == 5 and prior.get('maximum_new_gets') == 10
                        and diagnostics.get('stage') == 'request_prepare'
                        and diagnostics.get('exception_type') == 'ValueError'
                        and diagnostics.get('status') is None and diagnostics.get('retryable') is False)
            hashes[name] = sha(path.read_bytes())
    return hashes


def valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(ch in '0123456789abcdef' for ch in value)


def recovery_binding(folder, metadata, owner):
    """Validate exact retained v2 failure; old pages never supply scan credit."""
    require(type(owner) is int and owner > 0)
    compatibility = PACKET.parents[1] / 'readiness/2026-10-03/synthetic_empty_draft_compatibility_validation.json'
    require(sha(compatibility.read_bytes()) == COMPATIBILITY_RECEIPT_SHA)
    state_file, receipt_file = folder / OWNED_STATE, folder / RECOVERY_RECEIPT
    prior, receipt = read_json(state_file, {}), read_json(receipt_file, {})
    require(isinstance(prior, dict) and isinstance(receipt, dict))
    require(prior.get('schema_version') == 2 and prior.get('inventory_scope') == OWNED_SCOPE
            and prior.get('completed') is False and prior.get('failed') is True
            and prior.get('resume_allowed') is False and prior.get('owner') == owner
            and prior.get('packet') == INVENTORY_SHA
            and type(prior.get('get_attempts')) is int and prior['get_attempts'] == 64
            and prior.get('prior_observed_gets') == 15 and prior.get('maximum_new_gets') == 225
            and prior.get('maximum_pages') == 200 and prior.get('page_size') == 100
            and prior.get('next_page') == 63)
    diagnostics = prior.get('diagnostics', {})
    require(diagnostics.get('stage') == 'response_json' and diagnostics.get('exception_type') == 'ValueError'
            and diagnostics.get('status') is None and diagnostics.get('retryable') is False)
    started, expires = datetime.fromisoformat(prior['started_at']), datetime.fromisoformat(prior['expires_at'])
    # The original may have expired. Its lifetime is checked, never extended.
    require(started.tzinfo is not None and expires.tzinfo is not None
            and expires == started + timedelta(minutes=30))
    require(prior.get('previous_attempt_hashes') == legacy_receipt_hashes(folder, owner)
            and prior.get('resumes') == [] and isinstance(prior.get('failures'), list)
            and len(prior['failures']) == 1 and prior['failures'][0] ==
                {'get_attempts':64, 'verified_pages':62, 'diagnostics':diagnostics})
    require(receipt.get('mode') == 'inventory' and receipt.get('inventory_scope') == OWNED_SCOPE
            and receipt.get('completed') is False and receipt.get('failed') is True
            and receipt.get('resume_allowed') is False and receipt.get('verified_pages') == 62
            and receipt.get('next_page') == 63 and receipt.get('get_attempts') == 64
            and receipt.get('prior_observed_gets') == 15 and receipt.get('cumulative_inventory_gets') == 79
            and receipt.get('maximum_new_gets') == 225 and receipt.get('packet_sha256') == INVENTORY_SHA
            and receipt.get('diagnostics') == diagnostics)
    guard = receipt.get('guard', {})
    require(isinstance(guard, dict) and guard.get('transport_attempts') == 64
            and guard.get('owned_pages') == 64 and guard.get('community_pages') == 0
            and guard.get('writes_performed') == 0 and isinstance(guard.get('observations'), list)
            and len(guard['observations']) == 64)
    for index, observation in enumerate(guard['observations']):
        require(isinstance(observation, dict) and observation.get('status') == 200
                and all(observation.get(key) is True for key in ('request_prepared', 'transport_entered',
                    'response_received', 'status_validated', 'json_validated', 'owner_validated',
                    'links_validated', 'completed'))
                and 'diagnostics' not in observation and 'failure_code' not in observation
                and valid_sha(observation.get('sha256'))
                and type(observation.get('bytes')) is int and 0 < observation['bytes'] <= 12*1024*1024
                and type(observation.get('owned_items')) is int and observation['owned_items'] > 0
                and (index == 0 or observation['owned_items'] == 100))
    require(isinstance(prior.get('pages'), list) and len(prior['pages']) == 62)
    pages_dir = folder / 'synthetic-owned-pages'
    expected = {'page-%03d.json' % page for page in range(1, 63)}
    require(pages_dir.is_dir() and {p.name for p in pages_dir.iterdir()} == expected)
    seen, page_hashes = set(), {}
    for index, saved in enumerate(prior['pages'], 1):
        page_file = pages_dir / ('page-%03d.json' % index)
        raw = page_file.read_bytes(); records = json.loads(raw)
        require(saved.get('page') == index and saved.get('count') == 100
                and saved.get('sha256') == sha(raw)
                and saved.get('response_sha256') == guard['observations'][index]['sha256'])
        check_owned_page(records, metadata, owner, seen)
        require(len(records) == 100)
        page_hashes[page_file.name] = sha(raw)
    require(len(seen) == 6200 and prior.get('ids') == sorted(seen))
    failed_response = guard['observations'][-1]['sha256']
    diagnostic_file = folder / RECOVERY_DIAGNOSTIC
    diagnostic_hash = None
    if diagnostic_file.exists():
        raw = diagnostic_file.read_bytes(); data = json.loads(raw)
        # A retained diagnostic may have a tool-specific envelope. Hash its
        # complete bytes and require the exact failed response hash as a value.
        pending, found = [data], False
        while pending:
            item = pending.pop()
            if isinstance(item, str): found |= item == failed_response
            elif isinstance(item, dict): pending.extend(item.values())
            elif isinstance(item, list): pending.extend(item)
        require(found)
        diagnostic_hash = sha(raw)
    return {'compatibility_commit':COMPATIBILITY_COMMIT,
            'compatibility_receipt_sha256':COMPATIBILITY_RECEIPT_SHA,
            'failed_state_sha256':sha(state_file.read_bytes()),
            'failed_receipt_sha256':sha(receipt_file.read_bytes()),
            'failed_response_sha256':failed_response, 'old_page_sha256':page_hashes,
            'old_legacy_receipt_sha256':prior['previous_attempt_hashes'],
            'diagnostic_receipt_sha256':diagnostic_hash,
            'prior_read_counts':{'earlier':15, 'v2':64, 'diagnostic':1, 'total':80}}


def inventory(stage, owner, *, resume=False, recovery=False):
    """One bounded owned scan. Resume replays every page; no snapshot is assumed."""
    paths, file, metadata, artifact, plan = bindings(stage)
    token = load_zenodo_token(sandbox=True)
    require(token == os.environ.get('ZENODO_SANDBOX_TOKEN'))
    folder = Path(paths.state_dir) / 'sandbox'
    folder.mkdir(parents=True, exist_ok=True)
    scope = RECOVERY_SCOPE if recovery else OWNED_SCOPE
    prior_gets = 80 if recovery else 15
    schema = 3 if recovery else 2
    state_file = folder / (RECOVERY_STATE if recovery else OWNED_STATE)
    pages_dir = folder / (RECOVERY_PAGES if recovery else 'synthetic-owned-pages')
    with (folder / 'synthetic-controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (folder / 'synthetic-controller.json').exists() and
                not read_json(paths.uploads_registry_path, {}))
        require(recovery or not (folder / RECOVERY_STATE).exists())
        prior_hashes = legacy_receipt_hashes(folder, owner)
        recovery_evidence = recovery_binding(folder, metadata, owner) if recovery else None
        state = read_json(state_file)
        if state is None:
            require(not resume and not pages_dir.exists())
            now = datetime.now(timezone.utc)
            state = {'schema_version': schema, 'completed': False, 'failed': False, 'resume_allowed': True,
                     'get_attempts': 0, 'prior_observed_gets': prior_gets, 'maximum_new_gets': 225,
                     'maximum_pages': 200, 'page_size': 100,
                     'inventory_scope': scope, 'owner': owner, 'packet': INVENTORY_SHA,
                     'previous_attempt_hashes': prior_hashes, 'started_at': now.isoformat(),
                     'expires_at': (now + timedelta(minutes=30)).isoformat(),
                     'pages': [], 'next_page': 1, 'ids': [], 'failures': [], 'resumes': []}
            if recovery:
                state.update(recovery_binding=recovery_evidence, maximum_cumulative_gets=305)
        else:
            require(resume and state.get('completed') is False and state.get('resume_allowed') is True)
            require(state.get('schema_version') == schema and type(state.get('failed')) is bool
                    and state.get('owner') == owner and state.get('packet') == INVENTORY_SHA
                    and state.get('inventory_scope') == scope
                    and state.get('previous_attempt_hashes') == prior_hashes
                    and state.get('prior_observed_gets') == prior_gets and state.get('maximum_new_gets') == 225
                    and state.get('maximum_pages') == 200 and state.get('page_size') == 100)
            if recovery:
                require(state.get('recovery_binding') == recovery_evidence
                        and state.get('maximum_cumulative_gets') == 305)
        require(type(state.get('get_attempts')) is int and 0 <= state['get_attempts'] < 225)
        require(isinstance(state.get('pages'), list) and len(state['pages']) <= 200
                and type(state.get('next_page')) is int and state['next_page'] == len(state['pages']) + 1
                and isinstance(state.get('failures'), list) and isinstance(state.get('resumes'), list))
        started = datetime.fromisoformat(state['started_at'])
        expires = datetime.fromisoformat(state['expires_at'])
        require(started.tzinfo is not None and expires.tzinfo is not None
                and expires == started + timedelta(minutes=30)
                and started <= datetime.now(timezone.utc) < expires)
        seen = set()
        terminal = False
        expected_files = set()
        # A partial checkpoint is evidence, not a remotely valid snapshot.
        # Verify it locally, then replay from page one under the remaining budget.
        for index, saved in enumerate(state['pages'], 1):
            require(saved['page'] == index and not terminal)
            page_name = 'page-%03d.json' % index
            expected_files.add(page_name)
            raw = (pages_dir / page_name).read_bytes()
            require(sha(raw) == saved['sha256'])
            records = json.loads(raw)
            check_owned_page(records, metadata, owner, seen)
            require(len(records) == saved['count'])
            terminal = len(records) < 100
        require(sorted(seen) == state['ids'] and state['get_attempts'] >= len(state['pages']))
        minimum_replay_gets = 1 + len(state['pages']) + (0 if terminal else 1)
        require(225 - state['get_attempts'] >= minimum_replay_gets)
        require((not pages_dir.exists() and not expected_files) or
                (pages_dir.is_dir() and {p.name for p in pages_dir.iterdir()} == expected_files))
        def save():
            atomic_json(state_file, state)
            fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
        if resume:
            # Failed diagnostics stay in the immutable failure history. A resume
            # must be dispatched explicitly, and never renews the clock or counts.
            state['resumes'].append({'at': datetime.now(timezone.utc).isoformat(),
                                     'get_attempts': state['get_attempts']})
        state.update(failed=False, resume_allowed=True)
        save()
        incomplete = {'environment': 'sandbox', 'inventory_scope': scope,
                      'inventory_complete': False, 'files': [], 'metadata_hashes': {}}
        atomic_json(paths.safe_to_upload_path, incomplete)
        guard = SandboxInventoryGuard(token, owner, max_requests=225 - state['get_attempts'])
        original = requests.sessions.Session.send
        client = None
        def counted(session, request, **kwargs):
            parsed = urlsplit(request.url)
            require(request.method == 'GET' and parsed.path == '/api/deposit/depositions')
            pairs = parse_qsl(parsed.query, keep_blank_values=True)
            require((active_page is None and not pairs) or (active_page is not None and len(pairs) == 2 and dict(pairs) ==
                    {'page': str(active_page), 'size': '100'}))
            require(state['get_attempts'] < 225 and datetime.now(timezone.utc) < expires)
            state['get_attempts'] += 1; save()
            return original(session, request, **kwargs)
        active_page = None
        try:
            requests.sessions.Session.send = counted
            with guard:
                client = create_zenodo_client(sandbox=True)
                require(client.base_url == ORIGIN)
                client.max_retries = 0
                require(guard.receipt()['observations'][-1]['owner_validated'], 'response_owner')
                seen = set()
                for page in range(1, 201):
                    active_page = page
                    response = client._make_request('GET', 'deposit/depositions',
                        params={'page': page, 'size': 100}, allow_redirects=False)
                    records = response.json()
                    check_owned_page(records, metadata, owner, seen)
                    page_file = pages_dir / ('page-%03d.json' % page)
                    if page <= len(state['pages']):
                        # Revalidate all retained content/order, not just an
                        # unpaged constructor anchor that could miss later drift.
                        require(records == read_json(page_file), 'response_json')
                    else:
                        require(not page_file.exists())
                        atomic_json(page_file, records)
                        fd = os.open(pages_dir, os.O_RDONLY | os.O_DIRECTORY)
                        try: os.fsync(fd)
                        finally: os.close(fd)
                        state['pages'].append({'page': page, 'count': len(records),
                            'sha256': sha(page_file.read_bytes()),
                            'response_sha256': guard.receipt()['observations'][-1]['sha256']})
                        state['next_page'] = page + 1; state['ids'] = sorted(seen); save()
                    if len(records) < 100:
                        break
                else:
                    require(False)  # 200 full pages do not prove completion.
                require(seen, 'response_owner')
            client.close(); client = None
            require(datetime.now(timezone.utc) < expires)
            if recovery:
                require(recovery_binding(folder, metadata, owner) == recovery_evidence)
            atomic_json(paths.already_uploaded_path, {'environment': 'sandbox', 'inventory_scope': scope,
                        'total_records': len(seen), 'records': [{'id': i} for i in sorted(seen)],
                        'checkpoint_pages': state['pages'], 'check_date': datetime.now(timezone.utc).isoformat()})
            atomic_json(paths.safe_to_upload_path, {'environment': 'sandbox', 'inventory_scope': scope,
                        'inventory_complete': True, 'files': [file.name],
                        'checked_at': datetime.now(timezone.utc).isoformat(), 'valid_until': state['expires_at'],
                        'metadata_hashes': {file.name: metadata_hash(metadata)}})
            state.update(completed=True, resume_allowed=False, owned_count=len(seen),
                         safe_sha256=sha(Path(paths.safe_to_upload_path).read_bytes()),
                         retained_sha256=sha(Path(paths.already_uploaded_path).read_bytes()))
        except Exception as exc:
            diagnostics = _exception_diagnostics(exc, 'api_request')
            diagnostics['retryable'] = False  # No automatic request retry.
            state.update(completed=False, failed=True, diagnostics=diagnostics)
            state['failures'].append({'get_attempts': state['get_attempts'],
                                     'verified_pages': len(state['pages']), 'diagnostics': diagnostics})
            state['resume_allowed'] = (diagnostics['stage'] == 'transport' and diagnostics['status'] is None
                and diagnostics['exception_type'] in ('ConnectionError', 'Timeout', 'ReadTimeout', 'ConnectTimeout')
                and 225 - state['get_attempts'] >= 1 + len(state['pages']) +
                    (0 if state['pages'] and state['pages'][-1]['count'] < 100 else 1)
                and datetime.now(timezone.utc) < expires)
            atomic_json(paths.safe_to_upload_path, incomplete)
        finally:
            requests.sessions.Session.send = original
            if client is not None:
                try: client.close()
                except Exception: pass
            save()
        result = {'mode': 'inventory', 'inventory_scope': scope,
                'completed': state['completed'], 'failed': state['failed'],
                'resume_allowed': state['resume_allowed'], 'verified_pages': len(state['pages']),
                'next_page': state['next_page'], 'get_attempts': state['get_attempts'], 'prior_observed_gets': prior_gets,
                'cumulative_inventory_gets': prior_gets + state['get_attempts'], 'maximum_new_gets': 225,
                'owned_count': state.get('owned_count'),
                'diagnostics': state.get('diagnostics') if state['failed'] else None,
                'guard': guard.receipt(), 'packet_sha256': INVENTORY_SHA}
        if recovery:
            result.update(maximum_cumulative_gets=305, compatibility_commit=COMPATIBILITY_COMMIT,
                          failed_receipt_sha256=recovery_evidence['failed_receipt_sha256'])
        return result


def authorize_scoped_inventory(safe, environment, controller):
    """A reduced-scope grant is usable only inside this exact active controller."""
    require(type(controller) is SyntheticTransport and environment == 'sandbox')
    require(safe.get('inventory_scope') == controller.inventory_scope and
            requests.sessions.Session.send is controller.active_send and
            controller.original_send is not None and not controller.state['failed'] and
            not controller.state['completed'] and controller.state['phase'] in ('upload', 'retry'))
    paths, file, metadata, artifact, plan = bindings(RUN)
    require(str(Path(controller.paths.base).resolve()) == str(RUN.resolve()) and
            controller.metadata == metadata and controller.artifact == artifact and controller.plan == plan)
    require(safe['files'] == [file.name] and safe['metadata_hashes'].get(file.name) == metadata_hash(metadata)
            and sha(Path(paths.safe_to_upload_path).read_bytes()) == controller.state['inventory_sha256'])


class SyntheticTransport:
    """Transport boundary used only by the complete controller below."""
    def __init__(self, token, owner, paths, metadata, artifact, plan):
        require(type(owner) is int and owner > 0)
        self.inventory_guard = SandboxInventoryGuard(token, owner, max_requests=1)
        self.token, self.owner, self.paths = token, owner, paths
        self.metadata, self.artifact, self.plan = metadata, artifact, plan
        self.path = Path(paths.state_dir) / 'sandbox' / 'synthetic-controller.json'
        safe = read_json(paths.safe_to_upload_path, {})
        self.inventory_scope = safe.get('inventory_scope')
        require(self.inventory_scope in (OWNED_SCOPE, RECOVERY_SCOPE))
        self.binding = {'schema_version': 1, 'owner': owner, 'run': str(RUN.resolve()),
                        'packet': INVENTORY_SHA, 'inventory_scope': self.inventory_scope, 'payload': plan['prepared_payload_sha256'],
                        'metadata': metadata_hash(metadata), 'artifact': artifact['sha256']}
        recovery_evidence = None
        if self.inventory_scope == RECOVERY_SCOPE:
            recovery_evidence = recovery_binding(self.path.parent, metadata, owner)
            self.binding['recovery_binding_sha256'] = sha(json.dumps(recovery_evidence, sort_keys=True).encode())
        self.state = read_json(self.path)
        ledger = read_json(paths.uploads_registry_path, {})
        require(set(ledger) <= {SOURCE})
        if self.state is None:
            require(not ledger)  # Never reconstruct lost controls around a prior attempt.
            inventory_state = read_json(self.path.parent / (RECOVERY_STATE if self.inventory_scope == RECOVERY_SCOPE else OWNED_STATE), {})
            require(inventory_state.get('inventory_scope') == self.inventory_scope
                    and inventory_state.get('completed') is True and inventory_state.get('failed') is False
                    and inventory_state.get('owner') == owner and inventory_state.get('packet') == INVENTORY_SHA
                    and inventory_state.get('safe_sha256') == sha(Path(paths.safe_to_upload_path).read_bytes())
                    and inventory_state.get('retained_sha256') == sha(Path(paths.already_uploaded_path).read_bytes()))
            if self.inventory_scope == RECOVERY_SCOPE:
                require(inventory_state.get('schema_version') == 3
                        and inventory_state.get('prior_observed_gets') == 80
                        and inventory_state.get('maximum_new_gets') == 225
                        and inventory_state.get('maximum_cumulative_gets') == 305
                        and inventory_state.get('recovery_binding') == recovery_evidence)
            safe = read_json(paths.safe_to_upload_path)
            # Validate freshness locally before the transport context exists.
            # Generic callers must never receive this scope-free copy.
            require_inventory({k: v for k, v in safe.items() if k != 'inventory_scope'}, 'sandbox')
            require(safe.get('inventory_scope') == self.inventory_scope and safe['files'] == [SOURCE + '.json'] and
                    safe['metadata_hashes'].get(SOURCE + '.json') == metadata_hash(metadata))
            prior = read_json(paths.already_uploaded_path)
            require(prior['environment'] == 'sandbox' and prior.get('inventory_scope') == self.inventory_scope)
            require(prior['total_records'] == len(prior['records']))
            ids = [r['id'] for r in prior['records']]
            require(all(type(i) is int and i > 0 for i in ids))
            self.state = {'binding': self.binding, 'counts': {'get': 0, 'create': 0, 'metadata': 0, 'file': 0},
                          'pre_ids': sorted(set(ids)), 'id': None, 'doi': None, 'bucket': None,
                          'failed': False, 'completed': False, 'phase': 'initial',
                          'inventory_sha256': sha(Path(paths.safe_to_upload_path).read_bytes())}
            self.save()
        require(self.state.get('binding') == self.binding and self.state.get('failed') is False)
        require(type(self.state.get('completed')) is bool and self.state.get('phase') in
                ('initial', 'upload', 'download', 'retry', 'completed'))
        require(self.state.get('id') is None or
                (type(self.state['id']) is int and self.state['id'] > 0))
        require(set(self.state['counts']) == {'get', 'create', 'metadata', 'file'})
        require(all(type(v) is int and 0 <= v <= (8 if k == 'get' else 1)
                    for k, v in self.state['counts'].items()))
        if self.state.get('id') is not None:
            require(ledger.get(SOURCE, {}).get('deposition_id') == self.state['id'])
        else:
            require(not ledger and not any(self.state['counts'].values()))
        self.original_send = None
        self.active_send = None

    def save(self):
        atomic_json(self.path, self.state)
        # Persist the directory entry as well as atomic_json's file fsync.
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def receipt(self):
        saved = self.state.get('diagnostics')
        diagnostics = None
        if isinstance(saved, dict):
            diagnostics = ZenodoAPIError('Synthetic stopped', **{
                k: saved[k] for k in ('stage', 'exception_type', 'status', 'attempt') if k in saved
            }).diagnostics
        return {'completed': self.state['completed'], 'failed': self.state['failed'],
                'counts': dict(self.state['counts']), 'phase': self.state['phase'],
                'diagnostics': diagnostics, 'packet_sha256': INVENTORY_SHA}

    def __enter__(self):
        self.original_send = requests.sessions.Session.send
        self.active_send = lambda session, request, **kw: self.send(session, request, **kw)
        requests.sessions.Session.send = self.active_send
        return self

    def __exit__(self, *_):
        requests.sessions.Session.send = self.original_send

    def url(self, value):
        p = urlsplit(value)
        require(p.scheme == 'https' and p.netloc in ('sandbox.zenodo.org', 'sandbox.zenodo.org:443')
                and p.port in (None, 443) and p.username is None and p.password is None
                and not p.query and not p.fragment)
        return p.path

    def remote(self, data, creating=False):
        require(not credential_echoed(data, self.token), 'response_json')
        require(isinstance(data, dict) and type(data.get('id')) is int and data['id'] > 0, 'response_json')
        if creating:
            require(data['id'] not in self.state['pre_ids'], 'response_owner')
            self.state['id'] = data['id']
            self.save()  # ID durable even if a later response check stops the run.
        require(data['id'] == self.state['id'] and type(data.get('owner')) is int
                and data['owner'] == self.owner, 'response_owner')
        require(data.get('submitted') is False and data.get('state') == 'unsubmitted', 'response_owner')
        require(isinstance(data.get('metadata'), dict) and isinstance(data.get('files'), list), 'response_json')
        validate_files(data['files'], self.artifact, allow_missing=True)
        doi = data['metadata'].get('prereserve_doi', {}).get('doi')
        if self.state['doi'] is not None:
            require(doi == self.state['doi'], 'response_json')
        if doi is not None:
            require(isinstance(doi, str) and bool(doi), 'response_json')
            require(self.state['doi'] in (None, doi), 'response_json')
            self.state['doi'] = doi
        bucket = data.get('links', {}).get('bucket')
        require(isinstance(bucket, str), 'response_links')
        path = self.url(bucket)
        parts = path.split('/')
        require(len(parts) == 4 and parts[:3] == ['', 'api', 'files'], 'response_links')
        require(str(UUID(parts[-1])) == parts[-1], 'response_links')
        require(self.state['bucket'] in (None, path), 'response_links')
        self.state['bucket'] = path
        self.save()

    def check_ledger(self):
        entry = read_json(self.paths.uploads_registry_path, {}).get(SOURCE, {})
        require(entry.get('environment') == 'sandbox' and
                entry.get('source_sha256') == self.plan['source_sha256'] and
                entry.get('metadata_sha256') == metadata_hash(self.metadata) and
                entry.get('artifact_contract') == self.artifact)
        return entry

    def send(self, session, request, **kwargs):
        response = None
        stage, status = 'request_prepare', None
        try:
            require(not self.state['failed'] and not self.state['completed'])
            path = self.url(request.url)
            require(request.headers.get('Authorization') == 'Bearer ' + self.token)
            method = request.method
            deposition = '/api/deposit/depositions'
            target = deposition + '/' + str(self.state['id'])
            file_path = (self.state['bucket'] or '') + '/' + quote(SOURCE + '.xml', safe='')
            constructor = method == 'GET' and path == deposition and self.state['phase'] == 'initial'
            download = method == 'GET' and path == file_path and self.state['phase'] == 'download'
            if constructor or download or (method == 'GET' and self.state['id'] and path == target):
                kind = 'get'
            elif method == 'POST' and path == deposition and self.state['id'] is None:
                require(self.state['phase'] == 'upload' and json.loads(request.body) == {})
                require(sha(Path(self.paths.safe_to_upload_path).read_bytes()) == self.state['inventory_sha256'])
                require_inventory(read_json(self.paths.safe_to_upload_path), 'sandbox', synthetic_controller=self)
                entry = self.check_ledger()
                require(entry.get('needs_reconciliation') is True and not entry.get('deposition_id'))
                kind = 'create'
            elif method == 'PUT' and self.state['phase'] == 'upload' and self.state['id']:
                entry = self.check_ledger()
                require(entry.get('deposition_id') == self.state['id'] and not entry.get('needs_reconciliation'))
                if path == target:
                    require(json.loads(request.body) == {'metadata': self.metadata})
                    kind = 'metadata'
                elif path == file_path:
                    stream = request.body
                    pos = stream.tell(); raw = stream.read(self.plan['source_bytes'] + 1); stream.seek(pos)
                    require(len(raw) == self.plan['source_bytes'] and sha(raw) == self.plan['source_sha256'])
                    kind = 'file'
                else:
                    require(False)
            else:
                require(False)
            require(self.state['counts'][kind] < (8 if kind == 'get' else 1))
            self.state['counts'][kind] += 1
            self.save()  # Attempt consumes allowance before entering transport.
            kwargs.update(allow_redirects=False, timeout=(10, 30), stream=True)
            stage = 'transport'
            if constructor:
                response = self.inventory_guard.send(self.original_send, session, request, **kwargs)
                require(self.inventory_guard.receipt()['observations'][-1]['owner_validated'], 'response_owner')
                self.state['phase'] = 'upload'; self.save()
                return response
            response = self.original_send(session, request, **kwargs)
            status = response.status_code
            stage = 'response_status'
            require(status in ((201,) if kind == 'create' else (200, 201) if kind == 'file' else (200,)), stage)
            stage = 'response_json'
            chunks, size = [], 0
            cap = self.plan['source_bytes'] if download else 12 * 1024 * 1024
            for chunk in response.iter_content(chunk_size=min(cap + 1, 65536)):
                size += len(chunk); require(size <= cap, stage); chunks.append(chunk)
            raw = b''.join(chunks)
            require(self.token.encode('ascii') not in raw, stage)
            if download:
                require(size == self.plan['source_bytes'] and sha(raw) == self.plan['source_sha256'], stage)
            elif kind != 'file':
                self.remote(json.loads(raw), creating=kind == 'create')
            else:
                data = json.loads(raw)
                require(not credential_echoed(data, self.token), stage)
                require(isinstance(data, dict), stage)
            response._content, response._content_consumed = raw, True
            return response
        except Exception as exc:
            self.state['failed'] = True
            diagnostics = _exception_diagnostics(exc, stage)
            diagnostics['status'] = status if type(status) is int else diagnostics['status']
            diagnostics['retryable'] = False
            self.state['diagnostics'] = diagnostics
            self.save()
            raise ZenodoAPIError('Synthetic controller stopped', **diagnostics) from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    if not self.state['failed']:
                        self.state['failed'] = True
                        self.state['diagnostics'] = {'stage': 'response_cleanup', 'exception_type': 'unknown',
                                                     'status': status, 'retryable': False, 'attempt': 1}
                    self.save()
                    raise ZenodoAPIError('Synthetic cleanup stopped', **self.state['diagnostics']) from None


def verify_remote(client, guard):
    remote = client.get_deposition(guard.state['id'])
    require(not compare_metadata(guard.metadata, remote['metadata']), 'response_json')
    validate_files(remote['files'], guard.artifact)
    require(isinstance(guard.state['doi'], str) and bool(guard.state['doi']), 'response_json')
    require(remote['metadata'].get('prereserve_doi', {}).get('doi') == guard.state['doi'], 'response_json')
    return remote


def execute(stage, owner):
    paths, file, metadata, artifact, plan = bindings(stage)
    token = load_zenodo_token(sandbox=True)
    require(token == os.environ.get('ZENODO_SANDBOX_TOKEN'))
    lock_path = Path(paths.state_dir) / 'sandbox' / 'synthetic-controller.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard = SyntheticTransport(token, owner, paths, metadata, artifact, plan)
        if guard.state['completed']:
            entry = guard.check_ledger()
            require(entry.get('success') is True and entry.get('deposition_id') == guard.state['id']
                    and entry.get('doi') == guard.state['doi'] and bool(guard.state['doi'])
                    and entry.get('publish_status') == 'draft' and entry.get('upload_status') == 'success'
                    and not entry.get('needs_reconciliation'))
            return dict(guard.receipt(), cached=True, fresh_remote_check=False)
        client = None
        try:
            with guard:
                client = create_zenodo_client(sandbox=True)
                require(client.base_url == ORIGIN)
                client.max_retries = 0
                service = DraftUploadService(paths, 'sandbox')
                entry = service.upload(str(file), client, synthetic_controller=guard)
                require(entry.get('success') is True and entry.get('publish_status') == 'draft')
                remote = verify_remote(client, guard)
                download = remote['files'][0].get('links', {}).get('download')
                require(isinstance(download, str) and guard.url(download) ==
                        guard.state['bucket'] + '/' + quote(SOURCE + '.xml', safe=''), 'response_links')
                guard.state['phase'] = 'download'; guard.save()
                client.session.get(download, allow_redirects=False, timeout=(10, 30)).content
                guard.state['phase'] = 'retry'; guard.save()
                before = dict(guard.state['counts'])
                again = service.upload(str(file), client, synthetic_controller=guard)
                require(again.get('success') is True and again.get('deposition_id') == entry['deposition_id']
                        and again.get('doi') == entry.get('doi'))
                verify_remote(client, guard)
                require(all(guard.state['counts'][k] == before[k] for k in ('create', 'metadata', 'file')))
            client.close(); client = None
            guard.state.update(completed=True, phase='completed'); guard.save()
            return dict(guard.receipt(), cached=False, fresh_remote_check=True,
                        exact_readback=True, unchanged_retry=True)
        except Exception as exc:
            guard.state['failed'] = True
            if not guard.state.get('diagnostics'):
                guard.state['diagnostics'] = _exception_diagnostics(exc, 'api_request')
            guard.state['diagnostics']['retryable'] = False
            guard.save()
            return guard.receipt()
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-file', required=True, type=Path, help='Private JSON positive integer from verified account provenance')
    parser.add_argument('--inventory-only', action='store_true', help='Checkpointed owned scan, up to 200 pages and 225 new GETs, then pause')
    parser.add_argument('--resume-inventory', action='store_true', help='Explicitly resume only eligible retained checkpoints')
    parser.add_argument('--recover-inventory', action='store_true', help='Explicit new v3 scan:225 additional GETs plus80 preserved, new30-minute lifetime')
    args = parser.parse_args()
    previous = signal.getsignal(signal.SIGALRM)
    old_logging = logging.root.manager.disable
    receipt = {'completed': False, 'failed': True, 'status': 'setup_stopped_sanitized'}
    def deadline(*_):
        raise requests.exceptions.Timeout('Synthetic deadline')
    try:
        signal.signal(signal.SIGALRM, deadline); signal.alarm(1800 if args.inventory_only else 300)
        logging.disable(logging.CRITICAL)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            require(not args.resume_inventory or args.inventory_only)
            require(not args.recover_inventory or args.inventory_only)
            owner = json.loads(args.owner_file.read_bytes())
            receipt = (inventory(RUN, owner, resume=args.resume_inventory, recovery=args.recover_inventory)
                       if args.inventory_only else execute(RUN, owner))
    except Exception:
        pass
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, previous); logging.disable(old_logging)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt.get('completed') else 1


if __name__ == '__main__':
    # Keep capability class identity canonical when invoked with python -m.
    from scripts.synthetic_canary_controller import main as canonical_main
    raise SystemExit(canonical_main())
