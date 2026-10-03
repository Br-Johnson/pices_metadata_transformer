"""One separately authorized synthetic Sandbox run; old run files are never read.

Only the fixed fictional packet may use this capability. Attempts are durable
before transport; failures stop permanently. Shared response projections retain
status/body fingerprints and fixed error categories, never arbitrary body text.
"""
import argparse
import contextlib
from datetime import datetime, timedelta, timezone
import fcntl
import io
import json
import logging
import os
from pathlib import Path
import shutil
import signal
from urllib.parse import quote

import requests
from scripts import synthetic_canary_controller as c
from scripts.artifact_contract import prepare_artifact
from scripts.path_config import OutputPaths
from scripts.sandbox_read_guard import SandboxInventoryGuard, credential_echoed
from scripts.upload_service import DraftUploadService, atomic_json, metadata_hash, prepare_metadata, read_json

SOURCE = 'SYNTHETIC-PICES-FRESH-20261003-01'
TITLE = 'SYNTHETIC TEST ONLY PICES FRESH 20261003 01'
SCOPE = 'synthetic_fresh_separate_run_v5'
PACKET = Path(__file__).resolve().parents[1] / 'docs/handoff/sandbox-fresh-canary-20261003-01'
PACKET_SHA = '29ca42f8abcf04e27308ccefab2c92a0364f9a511ab247f5520fa57b39bf8a32'
STATE = 'synthetic-fresh-controller.json'
JOURNAL = 'synthetic-fresh-attempt-journal.json'
EVIDENCE = 'synthetic-fresh-response-evidence.json'
LIMITS = {'get': 8, 'create': 1, 'metadata': 1, 'file': 1}
PRIOR_GETS = 190  # Parent-reported original run; never rechecked/reset here.
ERROR_PHRASES = ('internal server error', 'bad request', 'service unavailable',
                 'unexpected error', 'validation error', 'unauthorized', 'forbidden',
                 'not found', 'too many requests', 'gateway timeout', 'bad gateway')


class FreshPaths(OutputPaths):
    @property
    def safe_to_upload_path(self):
        return str(Path(self.state_dir) / 'sandbox' / 'synthetic-fresh-grant.json')

    @property
    def uploads_registry_path(self):
        return str(Path(self.state_dir) / 'sandbox' / 'synthetic-fresh-upload-ledger.json')


def packet_plan():
    raw = (PACKET / 'INVENTORY.json').read_bytes()
    c.require(c.sha(raw) == PACKET_SHA)
    for entry in json.loads(raw):
        raw_file = (PACKET / entry['path']).read_bytes()
        c.require(len(raw_file) == entry['bytes'] and c.sha(raw_file) == entry['sha256'])
    return read_json(PACKET / 'selection.json')


def checked_stage(stage):
    stage = Path(stage).resolve()
    original_root = c.RUN.resolve().parent
    c.require(stage.name == SOURCE and stage != original_root
              and stage not in original_root.parents and original_root not in stage.parents)
    return stage


def stage_packet(stage):
    """Offline, exclusive staging; an existing run is never replaced or reset."""
    stage = checked_stage(stage)
    packet_plan()
    stage.mkdir(parents=True, exist_ok=False)
    shutil.copytree(PACKET / 'data', stage / 'data')
    atomic_json(stage / 'fresh-stage-binding.json',
                {'source': SOURCE, 'run': str(stage), 'packet_sha256': PACKET_SHA})
    bindings(stage)
    return {'staged': True, 'completed': True, 'provider_requests': 0,
            'source_id': SOURCE, 'packet_sha256': PACKET_SHA}


def bindings(stage):
    stage = checked_stage(stage)
    plan = packet_plan()
    c.require(read_json(stage / 'fresh-stage-binding.json') ==
              {'source': SOURCE, 'run': str(stage), 'packet_sha256': PACKET_SHA})
    paths = FreshPaths(str(stage), 'sandbox')
    payload = Path(paths.zenodo_json_dir) / (SOURCE + '.json')
    source = Path(paths.original_fgdc_dir) / (SOURCE + '.xml')
    c.require({p.name for p in payload.parent.iterdir()} == {payload.name}
              and {p.name for p in source.parent.iterdir()} == {source.name}
              and not payload.is_symlink() and not source.is_symlink())
    c.require(c.sha(payload.read_bytes()) == plan['prepared_payload_sha256'])
    metadata, source_path, digest = prepare_metadata(str(payload), paths)
    artifact = prepare_artifact(read_json(payload), source_path)
    c.require(metadata == read_json(PACKET / 'expected-metadata.json')
              and metadata_hash(metadata) == plan['expected_metadata_sha256']
              and metadata['title'] == TITLE and plan['source_id'] == SOURCE
              and artifact == plan['artifact_contract'] and digest == plan['source_sha256']
              and len(source.read_bytes()) == plan['source_bytes'])
    return paths, payload, metadata, artifact, plan


def validate_grant(grant, paths, metadata, owner):
    c.require(isinstance(grant, dict) and type(owner) is int and owner > 0)
    started = datetime.fromisoformat(grant['started_at'])
    expires = datetime.fromisoformat(grant['valid_until'])
    expected = {'environment': 'sandbox', 'inventory_scope': SCOPE, 'inventory_complete': False,
                'owner': owner, 'run': str(Path(paths.base).resolve()), 'source': SOURCE,
                'packet_sha256': PACKET_SHA, 'limits': LIMITS,
                'prior_observed_gets_parent_reported': PRIOR_GETS,
                'original_uncertain_create': 'permanently_spent_held_not_reconciled',
                'files': [SOURCE + '.json'], 'metadata_hashes': {SOURCE + '.json': metadata_hash(metadata)},
                'started_at': grant['started_at'], 'valid_until': grant['valid_until']}
    c.require(grant == expected and started.tzinfo is not None and expires.tzinfo is not None
              and expires == started + timedelta(minutes=30) and started <= datetime.now(timezone.utc))


def prepare_grant(paths, metadata, owner):
    folder = Path(paths.state_dir) / 'sandbox'
    file = Path(paths.safe_to_upload_path)
    if not file.exists():
        c.require(not any((folder / name).exists() for name in (STATE, JOURNAL, EVIDENCE))
                  and not Path(paths.uploads_registry_path).exists())
        now = datetime.now(timezone.utc)
        atomic_json(file, {'environment': 'sandbox', 'inventory_scope': SCOPE, 'inventory_complete': False,
            'owner': owner, 'run': str(Path(paths.base).resolve()), 'source': SOURCE, 'packet_sha256': PACKET_SHA,
            'limits': LIMITS, 'prior_observed_gets_parent_reported': PRIOR_GETS,
            'original_uncertain_create': 'permanently_spent_held_not_reconciled',
            'files': [SOURCE + '.json'], 'metadata_hashes': {SOURCE + '.json': metadata_hash(metadata)},
            'started_at': now.isoformat(), 'valid_until': (now + timedelta(minutes=30)).isoformat()})
    grant = read_json(file)
    validate_grant(grant, paths, metadata, owner)
    state = read_json(folder / STATE, {})
    c.require(state.get('completed') is True or datetime.now(timezone.utc) <
              datetime.fromisoformat(grant['valid_until']))


def authorize_fresh_inventory(safe, environment, controller):
    """The fresh incomplete grant never authorizes a generic or production call."""
    c.require(type(controller) is FreshTransport and environment == 'sandbox'
              and requests.sessions.Session.send is controller.active_send
              and controller.original_send is not None and not controller.state['failed']
              and not controller.state['completed'] and controller.state['phase'] in ('upload', 'retry'))
    paths, file, metadata, artifact, plan = bindings(controller.paths.base)
    validate_grant(safe, paths, metadata, controller.owner)
    c.require(controller.metadata == metadata and controller.artifact == artifact and controller.plan == plan
              and safe['files'] == [file.name]
              and c.sha(Path(paths.safe_to_upload_path).read_bytes()) == controller.state['inventory_sha256'])


def response_projection(raw, response, method):
    """Closed vocabulary: arbitrary text/keys/values, headers and links are omitted."""
    status = response.status_code
    mime = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
    result = {'method': method, 'status': status if type(status) is int and 100 <= status <= 599 else None,
              'content_type': mime if mime in ('application/json', 'text/html', 'text/plain', 'application/xml') else 'other',
              'observed_bytes': len(raw), 'body_sha256': c.sha(raw)}
    try:
        data = json.loads(raw)
        result['body_format'] = 'json'
        result['known_error_fields'] = sorted(k for k in ('message', 'errors', 'error', 'status', 'code')
                                              if isinstance(data, dict) and k in data)
    except (ValueError, UnicodeError, RecursionError):
        result['body_format'] = 'html' if b'<' in raw[:256] else 'other'
    text = raw.decode('utf-8', errors='replace').lower()
    result['error_categories'] = [phrase for phrase in ERROR_PHRASES if phrase in text] if result['status'] and result['status'] >= 400 else []
    return result


class FreshTransport(c.SyntheticTransport):
    """Reuse the guarded transaction, with distinct source, clock and state files."""
    def __init__(self, token, owner, paths, metadata, artifact, plan):
        c.require(type(owner) is int and owner > 0)
        self.inventory_guard = SandboxInventoryGuard(token, owner, max_requests=1)
        self.token, self.owner, self.paths = token, owner, paths
        self.source, self.inventory_scope = SOURCE, SCOPE
        self.metadata, self.artifact, self.plan = metadata, artifact, plan
        self.path = Path(paths.state_dir) / 'sandbox' / STATE
        self.journal = self.path.parent / JOURNAL
        grant = read_json(paths.safe_to_upload_path)
        validate_grant(grant, paths, metadata, owner)
        self.binding = {'schema_version': 5, 'owner': owner, 'run': str(Path(paths.base).resolve()),
                        'packet': PACKET_SHA, 'inventory_scope': SCOPE, 'source': SOURCE,
                        'payload': plan['prepared_payload_sha256'], 'metadata': metadata_hash(metadata),
                        'artifact': artifact['sha256'], 'grant_sha256': c.sha(Path(paths.safe_to_upload_path).read_bytes())}
        self.state = read_json(self.path)
        ledger = read_json(paths.uploads_registry_path, {})
        c.require(isinstance(ledger, dict) and set(ledger) <= {SOURCE})
        if self.state is None:
            c.require(not ledger and not self.journal.exists() and not (self.path.parent / EVIDENCE).exists())
            self.state = {'binding': self.binding, 'counts': dict.fromkeys(LIMITS, 0), 'pre_ids': [],
                          'id': None, 'doi': None, 'bucket': None, 'created': None,
                          'failed': False, 'completed': False, 'phase': 'initial',
                          'inventory_sha256': self.binding['grant_sha256'],
                          'started_at': grant['started_at'], 'expires_at': grant['valid_until'],
                          'responses': []}
            self.save()
        c.require(self.state.get('binding') == self.binding and self.state.get('failed') is False
                  and self.state.get('started_at') == grant['started_at']
                  and self.state.get('expires_at') == grant['valid_until']
                  and self.state.get('inventory_sha256') == self.binding['grant_sha256']
                  and read_json(self.journal) == {'state_sha256': c.sha(self.path.read_bytes()), 'binding': self.binding,
                                                'counts': self.state['counts']}
                  and type(self.state.get('completed')) is bool
                  and self.state.get('phase') in ('initial', 'upload', 'download', 'retry', 'completed')
                  and set(self.state['counts']) == set(LIMITS)
                  and all(type(v) is int and 0 <= v <= LIMITS[k] for k, v in self.state['counts'].items()))
        if self.state['id'] is None:
            c.require(not ledger and not any(self.state['counts'].values()))
        else:
            c.require(type(self.state['id']) is int and self.state['id'] > 0
                      and ledger.get(SOURCE, {}).get('deposition_id') == self.state['id'])
        self.original_send = None
        self.active_send = None

    def save(self):
        super().save()
        atomic_json(self.journal, {'state_sha256': c.sha(self.path.read_bytes()),
                                  'binding': self.binding, 'counts': dict(self.state['counts'])})
        atomic_json(self.path.parent / EVIDENCE, {'source_id': SOURCE, 'packet_sha256': PACKET_SHA,
                                                 'responses': self.state['responses']})
        fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def __enter__(self):
        original = requests.sessions.Session.send
        def observed(session, request, **kwargs):
            response = original(session, request, **kwargs)
            raw = b''
            try:
                cap = 65536 if response.status_code not in (200, 201) else 12 * 1024 * 1024
                body = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    c.require(datetime.now(timezone.utc) < datetime.fromisoformat(self.state['expires_at']))
                    body.extend(chunk)
                    if len(body) > cap:
                        raw = bytes(body[:65536])
                        c.require(False, 'response_json')
                raw = bytes(body)
                c.require(datetime.now(timezone.utc) < datetime.fromisoformat(self.state['expires_at']))
                observation = response_projection(raw, response, request.method)
                try: decoded = json.loads(raw)
                except (ValueError, UnicodeError, RecursionError): decoded = None
                observation['credential_echo_detected'] = self.token.encode('ascii') in raw or credential_echoed(decoded, self.token)
                observation['body_complete'] = True
                observation['attempt_counts'] = dict(self.state['counts'])
                self.state['responses'].append(observation); self.save()
                # Cache bounded bytes for the inherited validators, never persist them.
                response._content, response._content_consumed = raw, True
                return response
            except Exception:
                observation = response_projection(raw[:65536], response, request.method)
                observation['body_complete'] = False
                observation['attempt_counts'] = dict(self.state['counts'])
                self.state['responses'].append(observation); self.save()
                try: response.close()
                except Exception: pass
                raise
        self.original_send = observed
        self.active_send = lambda session, request, **kw: self.send(session, request, **kw)
        self._previous_send = original
        requests.sessions.Session.send = self.active_send
        return self

    def __exit__(self, *_):
        requests.sessions.Session.send = self._previous_send

    def send(self, session, request, **kwargs):
        try:
            c.require(datetime.now(timezone.utc) < datetime.fromisoformat(self.state['expires_at']))
            if request.method == 'POST':
                self.state['create_started_at'] = datetime.now(timezone.utc).isoformat()
                self.save()
            response = super().send(session, request, **kwargs)
            if request.method == 'GET' and self.state['phase'] == 'upload' and self.state['id'] is None:
                records = response.json()
                seen = set()
                for item in records:
                    identifier = item.get('id')
                    c.require(type(identifier) is int and identifier > 0 and identifier not in seen, 'response_owner')
                    seen.add(identifier)
                    md = item.get('metadata', {})
                    c.require(isinstance(md, dict) and SOURCE not in json.dumps(md, sort_keys=True)
                              and md.get('title', '').strip().casefold() != TITLE.casefold(), 'response_owner')
                    files = item.get('files', [])
                    c.require(isinstance(files, list) and all(isinstance(f, dict) and SOURCE + '.xml' not in
                        [f.get(k) for k in ('filename', 'name', 'key')] for f in files), 'response_owner')
                self.state['pre_ids'] = sorted(seen); self.save()
            return response
        except Exception as exc:
            self.state['failed'] = True
            if not self.state.get('diagnostics'):
                self.state['diagnostics'] = c._exception_diagnostics(exc, 'request_prepare')
            self.state['diagnostics']['retryable'] = False
            self.save()
            raise

    def remote(self, data, creating=False):
        super().remote(data, creating=creating)
        created = datetime.fromisoformat(data.get('created', ''))
        c.require(created.tzinfo is not None, 'response_json')
        if creating:
            c.require(datetime.fromisoformat(self.state['create_started_at']) - timedelta(seconds=60) <= created
                      <= datetime.now(timezone.utc) + timedelta(seconds=60)
                      and data['files'] == [] and set(data['metadata']) <= {'prereserve_doi'}, 'response_json')
            self.state['created'] = data['created']; self.save()
        c.require(data.get('created') == self.state['created'], 'response_json')

    def receipt(self):
        return {'completed': self.state['completed'], 'failed': self.state['failed'],
                'counts': dict(self.state['counts']), 'phase': self.state['phase'],
                'diagnostics': self.state.get('diagnostics'), 'source_id': SOURCE,
                'packet_sha256': PACKET_SHA, 'inventory_scope': SCOPE, 'inventory_complete': False,
                'prior_observed_gets_parent_reported': PRIOR_GETS,
                'cumulative_gets': PRIOR_GETS + self.state['counts']['get'],
                'expires_at': self.state['expires_at'], 'responses': list(self.state['responses']),
                'original_uncertain_create': 'permanently_spent_held_not_reconciled'}


def execute(stage, owner):
    paths, file, metadata, artifact, plan = bindings(stage)
    token = c.load_zenodo_token(sandbox=True)
    c.require(token == os.environ.get('ZENODO_SANDBOX_TOKEN'))
    folder = Path(paths.state_dir) / 'sandbox'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'synthetic-fresh-controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prepare_grant(paths, metadata, owner)
        guard = FreshTransport(token, owner, paths, metadata, artifact, plan)
        if guard.state['completed']:
            entry = guard.check_ledger()
            c.require(entry.get('success') is True and entry.get('deposition_id') == guard.state['id']
                      and entry.get('doi') == guard.state['doi'] and bool(guard.state['doi'])
                      and entry.get('publish_status') == 'draft' and entry.get('upload_status') == 'success'
                      and not entry.get('needs_reconciliation'))
            return dict(guard.receipt(), cached=True, fresh_remote_check=False)
        client = None
        try:
            with guard:
                client = c.create_zenodo_client(sandbox=True)
                c.require(client.base_url == c.ORIGIN)
                client.max_retries = 0
                service = DraftUploadService(paths, 'sandbox')
                entry = service.upload(str(file), client, synthetic_controller=guard)
                c.require(entry.get('success') is True and entry.get('publish_status') == 'draft')
                remote = c.verify_remote(client, guard)
                download = remote['files'][0].get('links', {}).get('download')
                c.require(isinstance(download, str) and guard.url(download) ==
                          guard.state['bucket'] + '/' + quote(SOURCE + '.xml', safe=''), 'response_links')
                guard.state['phase'] = 'download'; guard.save()
                client.session.get(download, allow_redirects=False, timeout=(10, 30)).content
                guard.state['phase'] = 'retry'; guard.save()
                before = dict(guard.state['counts'])
                again = service.upload(str(file), client, synthetic_controller=guard)
                c.require(again.get('success') is True and again.get('deposition_id') == entry['deposition_id']
                          and again.get('doi') == entry.get('doi'))
                c.verify_remote(client, guard)
                c.require(all(guard.state['counts'][k] == before[k] for k in ('create', 'metadata', 'file')))
            client.close(); client = None
            c.require(datetime.now(timezone.utc) < datetime.fromisoformat(guard.state['expires_at']))
            guard.state.update(completed=True, phase='completed'); guard.save()
            return dict(guard.receipt(), cached=False, fresh_remote_check=True,
                        exact_readback=True, unchanged_retry=True)
        except Exception as exc:
            guard.state['failed'] = True
            if not guard.state.get('diagnostics'):
                guard.state['diagnostics'] = c._exception_diagnostics(exc, 'api_request')
            guard.state['diagnostics']['retryable'] = False
            guard.save()
            return guard.receipt()
        finally:
            if client is not None:
                try: client.close()
                except Exception: pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, type=Path, help='Separate private root whose basename is the fixed fresh source ID')
    parser.add_argument('--stage-only', action='store_true', help='Offline exclusive staging; no credentials or requests')
    parser.add_argument('--owner-file', type=Path, help='Private verified account positive integer, required for provider execution')
    args = parser.parse_args()
    receipt = {'completed': False, 'failed': True, 'status': 'setup_stopped_sanitized', 'source_id': SOURCE}
    previous = signal.getsignal(signal.SIGALRM)
    old_logging = logging.root.manager.disable
    def deadline(*_):
        raise requests.exceptions.Timeout('Synthetic fresh deadline')
    try:
        signal.signal(signal.SIGALRM, deadline); signal.alarm(1800)
        logging.disable(logging.CRITICAL)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            c.require(args.stage_only or args.owner_file is not None)
            receipt = stage_packet(args.stage) if args.stage_only else execute(args.stage, json.loads(args.owner_file.read_bytes()))
    except Exception:
        pass
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, previous); logging.disable(old_logging)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt.get('completed') else 1


if __name__ == '__main__':
    from scripts.synthetic_fresh_canary import main as canonical_main
    raise SystemExit(canonical_main())
