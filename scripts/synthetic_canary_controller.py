"""Frozen synthetic-only sandbox controller; durable attempt caps and no implicit retry.

The original run and ledger are mandatory. Every transport is guarded; returned
links are inert except the one checked bucket/file. Shared receipts omit private
IDs, owners, URLs, credentials, response bodies and arbitrary exception text.
"""
import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import signal
from urllib.parse import urlsplit, quote
from uuid import UUID

import requests
from scripts.artifact_contract import prepare_artifact, validate_files
from scripts.path_config import OutputPaths
from scripts.sandbox_read_guard import SandboxInventoryGuard
from scripts.upload_service import (DraftUploadService, atomic_json, read_json,
                                    prepare_metadata, metadata_hash, require_inventory)
from scripts.verify_uploads import compare_metadata
from scripts.zenodo_api import create_zenodo_client, load_zenodo_token, ZenodoAPIError, _exception_diagnostics

ORIGIN = 'https://sandbox.zenodo.org'
SOURCE = 'SYNTHETIC-PICES-9379FD8-20261002'
RUN = Path('/workspace/pices-sandbox-run-9379fd8-20261002/synthetic')
PACKET = Path(__file__).resolve().parents[1] / 'docs/handoff/sandbox-canary-20261002'
INVENTORY_SHA = '428559c7a8e81e84c22627b0add1230797b92013f87152e2ee3024b56af30fd1'


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


def inventory(stage, owner):
    """One bounded full-checker run, accounting for the three prior observed GETs."""
    from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
    paths, file, metadata, artifact, plan = bindings(stage)
    token = load_zenodo_token(sandbox=True)
    require(token == os.environ.get('ZENODO_SANDBOX_TOKEN'))
    folder = Path(paths.state_dir) / 'sandbox'
    folder.mkdir(parents=True, exist_ok=True)
    state_file = folder / 'synthetic-inventory-controller.json'
    with (folder / 'synthetic-controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not state_file.exists())  # A stopped/successful inventory is never silently rerun.
        require(not (folder / 'synthetic-controller.json').exists() and
                not read_json(paths.uploads_registry_path, {}))
        guard = SandboxInventoryGuard(token, owner, max_requests=237)
        state = {'completed': False, 'failed': False, 'get_attempts': 0,
                 'prior_observed_gets': 3, 'maximum_new_gets': 237,
                 'owner': owner, 'packet': INVENTORY_SHA}
        def save():
            atomic_json(state_file, state)
            fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
        save()
        original = requests.sessions.Session.send
        checker = None
        def counted(session, request, **kwargs):
            require(state['get_attempts'] < 237)
            state['get_attempts'] += 1; save()
            return original(session, request, **kwargs)
        try:
            requests.sessions.Session.send = counted
            with guard:
                checker = PreUploadDuplicateChecker(sandbox=True, output_dir=str(stage),
                                                    allow_replacements=False, canary_plan=None)
                checker.client.max_retries = 0
                summary = checker.check_all_files()
                require(not summary['check_errors'] and not summary['duplicate_files'] and
                        summary['safe_to_upload_files'] == [file.name])
                require(any(o['owner_validated'] for o in guard.receipt()['observations']), 'response_owner')
                checker.generate_upload_list()
            checker.client.close(); checker = None
            state.update(completed=True,
                         safe_sha256=sha(Path(paths.safe_to_upload_path).read_bytes()),
                         retained_sha256=sha(Path(paths.already_uploaded_path).read_bytes()))
        except Exception as exc:
            state['failed'] = True
            state['diagnostics'] = _exception_diagnostics(exc, 'api_request')
            state['diagnostics']['retryable'] = False
        finally:
            requests.sessions.Session.send = original
            if checker is not None:
                try: checker.client.close()
                except Exception: pass
            save()
        return {'mode': 'inventory', 'completed': state['completed'], 'failed': state['failed'],
                'get_attempts': state['get_attempts'], 'prior_observed_gets': 3,
                'diagnostics': state.get('diagnostics'), 'guard': guard.receipt(),
                'packet_sha256': INVENTORY_SHA}


class SyntheticTransport:
    """Transport boundary used only by the complete controller below."""
    def __init__(self, token, owner, paths, metadata, artifact, plan):
        require(type(owner) is int and owner > 0)
        self.inventory_guard = SandboxInventoryGuard(token, owner, max_requests=1)
        self.token, self.owner, self.paths = token, owner, paths
        self.metadata, self.artifact, self.plan = metadata, artifact, plan
        self.path = Path(paths.state_dir) / 'sandbox' / 'synthetic-controller.json'
        self.binding = {'schema_version': 1, 'owner': owner, 'run': str(RUN.resolve()),
                        'packet': INVENTORY_SHA, 'payload': plan['prepared_payload_sha256'],
                        'metadata': metadata_hash(metadata), 'artifact': artifact['sha256']}
        self.state = read_json(self.path)
        ledger = read_json(paths.uploads_registry_path, {})
        require(set(ledger) <= {SOURCE})
        if self.state is None:
            require(not ledger)  # Never reconstruct lost controls around a prior attempt.
            inventory_state = read_json(self.path.parent / 'synthetic-inventory-controller.json', {})
            require(inventory_state.get('completed') is True and inventory_state.get('failed') is False
                    and inventory_state.get('owner') == owner and inventory_state.get('packet') == INVENTORY_SHA
                    and inventory_state.get('safe_sha256') == sha(Path(paths.safe_to_upload_path).read_bytes())
                    and inventory_state.get('retained_sha256') == sha(Path(paths.already_uploaded_path).read_bytes()))
            safe = read_json(paths.safe_to_upload_path)
            require_inventory(safe, 'sandbox')
            require(safe['files'] == [SOURCE + '.json'] and
                    safe['metadata_hashes'].get(SOURCE + '.json') == metadata_hash(metadata))
            prior = read_json(paths.already_uploaded_path)
            require(prior['environment'] == 'sandbox' and prior['community'] == 'pices')
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
        requests.sessions.Session.send = lambda session, request, **kw: self.send(session, request, **kw)
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
                require_inventory(read_json(self.paths.safe_to_upload_path), 'sandbox')
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
                entry = service.upload(str(file), client)
                require(entry.get('success') is True and entry.get('publish_status') == 'draft')
                remote = verify_remote(client, guard)
                download = remote['files'][0].get('links', {}).get('download')
                require(isinstance(download, str) and guard.url(download) ==
                        guard.state['bucket'] + '/' + quote(SOURCE + '.xml', safe=''), 'response_links')
                guard.state['phase'] = 'download'; guard.save()
                client.session.get(download, allow_redirects=False, timeout=(10, 30)).content
                guard.state['phase'] = 'retry'; guard.save()
                before = dict(guard.state['counts'])
                again = service.upload(str(file), client)
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
    parser.add_argument('--inventory-only', action='store_true', help='One complete read-only checker run, at most 237 new GETs, then pause')
    args = parser.parse_args()
    previous = signal.getsignal(signal.SIGALRM)
    old_logging = logging.root.manager.disable
    receipt = {'completed': False, 'failed': True, 'status': 'setup_stopped_sanitized'}
    def deadline(*_):
        raise requests.exceptions.Timeout('Synthetic deadline')
    try:
        signal.signal(signal.SIGALRM, deadline); signal.alarm(300)
        logging.disable(logging.CRITICAL)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            operation = inventory if args.inventory_only else execute
            receipt = operation(RUN, json.loads(args.owner_file.read_bytes()))
    except Exception:
        pass
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, previous); logging.disable(old_logging)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt.get('completed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
