"""One explicit corrected PUT and canonical GET on the sealed run02 draft.

Separate repair allowance; no create/PID/file route, old-stage mutation, replay or
automatic expiry extension. Only the sole provider executor stages private proof.
"""

import argparse
import json
import os
import stat
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import modern_owned_continuation as owned
from scripts import modern_synthetic_canary as modern
from scripts.modern_canary_errors import credential_echoed

NAMESPACE = modern.NAMESPACE + '-subjects-repair'
BEFOREIMAGE_SHA = '866775b60653bd5b25b1a59d9965fb070e07213a9310948f152df5d300fcee1b'
PREPARED_PUT_SHA = '4e47c3b2340483500d99ec9807fd9c90201532713b8b48e4adfe2e539fc0fb74'
PRIOR_RUNTIME = {
    'modern_synthetic_canary.py': '4865590399aa47d5a24ce52605500b5c2fcf12a4479d49cda1ec18d40566e435',
    'modern_canary_errors.py': '2f1f68bf7fee4e39099b5969e2013e1bc01f30b9edef6a2cb7f44a275fbb5bf3',
    'modern_owned_continuation.py': '5fb1b8275db0aa72f8175ad971bf8ceb1345cf240c4737e584229a603dc4c9c2',
}
LIMITS = {'metadata': 1, 'get': 1}
HISTORICAL_GET = 197
MIN_PRESERVED_FILES = 338
PRIOR_FILES = ('binding.json', 'state.json', 'journal.json', 'approval.json')
STATIC_FILES = ('origin.json', 'preserved-manifest.json', 'beforeimage197.json', 'synthetic.xml', 'create.json',
                'metadata-put.json', *(f'prior-{name}' for name in PRIOR_FILES))
FILES = modern.FILES | set(STATIC_FILES)


def secure_stage(stage):
    stage = Path(stage)
    modern.require(stage.is_absolute() and stage.name == NAMESPACE)
    for path in (stage, *stage.parents):
        modern.require(not path.is_symlink())
    modern.require(stage.is_dir() and stage.resolve() == stage and stage.stat().st_mode & 0o077 == 0)
    for path in stage.iterdir():
        modern.require(path.name in FILES and not path.is_symlink() and path.is_file()
                       and path.stat().st_nlink == 1 and path.stat().st_mode & 0o077 == 0)
    return stage


def evidence_path(path, leaf=False):
    """Private evidence files can have canonical shared, non-writable ancestors."""
    path = Path(path)
    modern.require(path.is_absolute() and path.resolve() == path)
    for ancestor in (path, *path.parents):
        modern.require(not ancestor.is_symlink())
        mode = ancestor.stat().st_mode
        if ancestor == path and leaf:
            modern.require(stat.S_ISREG(mode) and mode & 0o077 == 0 and ancestor.stat().st_nlink == 1)
        else:
            modern.require(stat.S_ISDIR(mode) and
                           (mode & 0o022 == 0 or (ancestor == Path('/tmp') and mode & stat.S_ISVTX)))
    return path


def manifest(value):
    modern.require(isinstance(value, dict) and set(value) == {'schema_version', 'files_sha256'}
                   and type(value['schema_version']) is int and value['schema_version'] == 1
                   and isinstance(value['files_sha256'], dict))
    for path, digest in value['files_sha256'].items():
        modern.require(isinstance(path, str) and str(Path(path)) == path and Path(path).is_absolute()
                       and isinstance(digest, str) and modern.re.fullmatch(r'[0-9a-f]{64}', digest))
    return value


def inventory(roots, stage, declared=None):
    """Whole evidence trees plus exact manifest leaves, never a provenance container."""
    roots = [Path(root) for root in roots]
    declared = manifest({'schema_version': 1, 'files_sha256': {}} if declared is None else declared)
    for name in declared['files_sha256']:
        path = Path(name)
        if not any(path == root or root in path.parents for root in roots):
            roots.append(path)
    modern.require(bool(roots) and len(set(roots)) == len(roots))
    result = {}
    for root in sorted(roots):
        evidence_path(root, leaf=root.is_file())
        modern.require(stage != root and stage not in root.parents and root not in stage.parents)
        modern.require(all(other == root or other not in root.parents for other in roots))
        entries = {}
        for path in sorted(root.rglob('*')) if root.is_dir() else [root]:
            evidence_path(path, leaf=path.is_file())
            if path.is_dir():
                continue
            entries[str(path.relative_to(root))] = modern.sha(path.read_bytes())
        result[str(root)] = entries
    modern.require(sum(map(len, result.values())) >= MIN_PRESERVED_FILES)
    files = inventory_files(result)
    modern.require(all(files.get(path) == digest for path, digest in declared['files_sha256'].items()),
                   'Declared preserved evidence changed; repair held')
    return result


def inventory_files(value):
    return {str(Path(root) / name): digest for root, entries in value.items() for name, digest in entries.items()}


def verify_coverage(snapshot, prior, beforeimage):
    """The immutable broad origin is ancestry; all actual stage files are evidence."""
    old_origin = modern.load(prior / 'origin.json')
    preserved = evidence_path(old_origin['preserved_root'])
    original = modern.secure_stage(Path(old_origin['original_stage']))
    modern.require(original == preserved or preserved in original.parents)
    files = inventory_files(snapshot)
    required = [*original.iterdir(), *prior.iterdir(), evidence_path(beforeimage, leaf=True)]
    modern.require(all(files.get(str(path)) == modern.sha(path.read_bytes()) for path in required),
                   'Complete original/failed stages and latest read must be preserved')


def inventory_summary(value):
    return {'count': sum(map(len, value.values())), 'sha256': modern.sha(modern.encoded(value))}


def verify_origin(stage):
    origin = modern.load(stage / 'origin.json')
    modern.require(set(origin) == {'prior_continuation', 'beforeimage197_path', 'inventory'})
    prior = owned.secure_stage(Path(origin['prior_continuation']))
    original_grant, original_state = owned.verify_origin(prior)
    roots = list(origin['inventory'])
    declared = manifest(modern.load(stage / 'preserved-manifest.json'))
    modern.require(inventory(roots, stage, declared) == origin['inventory'], 'Preserved history changed; repair held')
    beforeimage = Path(origin['beforeimage197_path'])
    verify_coverage(origin['inventory'], prior, beforeimage)
    modern.require(beforeimage.is_file() and not beforeimage.is_symlink()
                   and modern.sha(beforeimage.read_bytes()) == BEFOREIMAGE_SHA
                   and (stage / 'beforeimage197.json').read_bytes() == beforeimage.read_bytes())
    for name in PRIOR_FILES:
        modern.require((stage / ('prior-' + name)).read_bytes() == (prior / name).read_bytes())
    state = modern.load(stage / 'prior-state.json')
    bound = modern.load(stage / 'prior-binding.json')
    grant = modern.load(stage / 'prior-approval.json')
    modern.require(state['binding'] == bound == grant['binding']
                   and bound['runtime_sha256'] == PRIOR_RUNTIME and bound['stage'] == str(prior)
                   and bound['namespace'] == owned.NAMESPACE and bound['packet_sha256'] == modern.PACKET_SHA
                   and bound['input_sha256'] == {name: modern.sha((prior / name).read_bytes()) for name in owned.STATIC_FILES}
                   and bound['prior_spent_counts'] == {'create': 1, 'get': 1}
                   and bound['historical_get_intents'] == 196)
    modern.require(modern.load(stage / 'prior-journal.json') == {
        'state_sha256': modern.sha((stage / 'prior-state.json').read_bytes()),
        'counts': state['counts'], 'binding': bound})
    modern.require(state['grant_sha256'] == modern.sha((stage / 'prior-approval.json').read_bytes())
                   and grant['approved'] is True and grant['executor'] == modern.EXECUTOR
                   and grant['owner'] == original_grant['owner'] and grant['known_ids'] == original_grant['known_ids']
                   and grant['limits'] == modern.LIMITS and grant['existing_candidate_only'] is True
                   and grant['no_create_or_reset'] is True)
    modern.require(state['failed'] is True and state['completed'] is False
                   and state['counts'] == {**dict.fromkeys(modern.LIMITS, 0), 'create': 1, 'metadata': 1, 'get': 1}
                   and state['pending'] == {'kind': 'metadata', 'method': 'PUT',
                                           'path_sha256': modern.sha(('/api/records/' + modern.record_id(state['identity']['id']) + '/draft').encode())}
                   and len(state['responses']) == len(state['attempt_diagnostics']) == 1
                   and state['responses'][0]['action'] == 'metadata' and state['responses'][0]['status'] == 200
                   and state['responses'][0]['method'] == 'PUT'
                   and state['responses'][0]['body_complete'] is True
                   and state['responses'][0]['credential_echo_detected'] is False
                   and state['attempt_diagnostics'][0]['action'] == 'metadata'
                   and state['attempt_diagnostics'][0]['response_seen'] is True
                   and state['attempt_diagnostics'][0]['status'] == 200
                   and state['create_started_at'] == original_state['create_started_at']
                   and state['create_received_at'] == original_state['create_received_at'])
    modern.require(state['identity']['doi'] is None
                   and state['identity']['id'] == original_state['uncertain_candidate_id'])
    for name in ('synthetic.xml', 'create.json', 'metadata-put.json'):
        modern.require((stage / name).read_bytes() == (modern.PACKET / name).read_bytes())
    return original_grant, state


def runtime_binding():
    return {**owned.runtime_binding(), 'modern_run02_subjects_repair.py': modern.sha(Path(__file__).read_bytes())}


def binding(stage):
    verify_origin(stage)
    return {'schema_version': 1, 'namespace': NAMESPACE, 'stage': str(stage),
            'packet_sha256': modern.PACKET_SHA, 'runtime_sha256': runtime_binding(),
            'input_sha256': {name: modern.sha((stage / name).read_bytes()) for name in STATIC_FILES},
            'prepared_put_sha256': PREPARED_PUT_SHA, 'historical_get_intents': HISTORICAL_GET,
            'prior_run02_create_intents': 1, 'prior_run02_metadata_put_intents': 1}


def validate_prepared_put(prepared, token, path):
    modern.require(prepared.url == modern.ORIGIN + path
                   and prepared.headers.get('Authorization') == 'Bearer ' + token
                   and prepared.headers.get('Accept') == modern.ACCEPT
                   and prepared.method == 'PUT' and isinstance(prepared.body, bytes)
                   and len(prepared.body) == 494 and modern.sha(prepared.body) == PREPARED_PUT_SHA
                   and prepared.headers.get('Content-Type') == 'application/json'
                   and prepared.headers.get('Content-Length') == '494')


def stage_packet(stage, prior_continuation, beforeimage197, preserved_roots, token, preserved_manifest=None):
    """Sole executor offline staging only; no approval or provider request."""
    stage = Path(stage)
    modern.require(stage.is_absolute() and stage.name == NAMESPACE and not stage.exists())
    modern.require(all(not p.is_symlink() for p in (stage, *stage.parents)))
    modern.require(isinstance(token, str) and token and token.isascii())
    prior = owned.secure_stage(prior_continuation)
    owned.verify_origin(prior)
    roots = list(preserved_roots or [])
    declared = {'schema_version': 1, 'files_sha256': {}}
    if preserved_manifest is not None:
        source = evidence_path(preserved_manifest, leaf=True)
        modern.require(source.stat().st_size <= 2 * 1024 * 1024)
        declared = manifest(modern.load(source))
        if not any(source == Path(root) or Path(root) in source.parents for root in roots):
            roots.append(source)
    snapshot = inventory(roots, stage, declared)
    verify_coverage(snapshot, prior, Path(beforeimage197))
    modern.require(not Path(beforeimage197).is_symlink() and Path(beforeimage197).is_file()
                   and Path(beforeimage197).stat().st_nlink == 1)
    raw = Path(beforeimage197).read_bytes()
    modern.require(len(raw) <= 65536 and modern.sha(raw) == BEFOREIMAGE_SHA)
    inputs = {'beforeimage197.json': raw, 'preserved-manifest.json': modern.encoded(declared)}
    inputs.update({f'prior-{name}': (prior / name).read_bytes() for name in PRIOR_FILES})
    inputs.update({name: (modern.PACKET / name).read_bytes()
                   for name in ('synthetic.xml', 'create.json', 'metadata-put.json')})
    for name, value in inputs.items():
        modern.require(token.encode() not in value and
                       (not name.endswith('.json') or not credential_echoed(json.loads(value), token)))
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name, value in inputs.items():
        fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
    modern.atomic(stage / 'origin.json', {'prior_continuation': str(prior),
                                        'beforeimage197_path': str(Path(beforeimage197)), 'inventory': snapshot})
    original, spent = verify_origin(stage)
    bound = binding(stage)
    modern.atomic(stage / 'binding.json', bound)
    state = {'binding': bound, 'grant_sha256': None, 'counts': dict.fromkeys(LIMITS, 0),
             'pending': None, 'failed': False, 'completed': False, 'retry_completed': False,
             'identity': deepcopy(spent['identity']), 'create_started_at': spent['create_started_at'],
             'create_received_at': spent['create_received_at'], 'responses': [], 'attempt_diagnostics': [],
             'controller_failure': None, 'record_contract_diagnostics': None,
             'put_validated': False, 'prepared_put_verified': False}
    modern.save(stage, state)
    return {'staged': True, 'provider_requests': 0, 'runtime_sha256': runtime_binding(),
            'preserved_file_inventory': inventory_summary(snapshot), 'historical_get_intents': HISTORICAL_GET,
            'original_expired_approval_preserved': bool(original['valid_until'])}


class Controller(modern.Controller):
    validate_stage = staticmethod(secure_stage)

    def stage_binding(self):
        return binding(self.stage)

    def creation_grant(self):
        return self.original_grant

    def initialize_inputs(self, stage, token, transport, now=None):
        self.stage = secure_stage(stage)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.plan = modern.packet()
        self.original_grant, spent = verify_origin(self.stage)
        # Original owner/known IDs validate identity only; they authorize no repair.
        self.grant = self.original_grant
        modern.require(isinstance(token, str) and token and token.isascii() and all(33 <= ord(c) <= 126 for c in token))
        self.token, self.transport = token, transport
        self.state = modern.load(self.stage / 'state.json')
        modern.require(modern.load(self.stage / 'binding.json') == self.state['binding'] == binding(self.stage))
        modern.require(modern.load(self.stage / 'journal.json') == {
            'state_sha256': modern.sha((self.stage / 'state.json').read_bytes()), 'counts': self.state['counts'], 'binding': self.state['binding']})
        modern.require(self.state['counts'] == dict.fromkeys(LIMITS, 0) and self.state['pending'] is None
                       and all(type(v) is int for v in self.state['counts'].values())
                       and self.state['failed'] is False and self.state['completed'] is False
                       and self.state['put_validated'] is False and self.state['prepared_put_verified'] is False,
                       'Repair already consumed or interrupted; no reentry or replay')
        modern.require(self.state['identity'] == spent['identity']
                       and self.state['create_started_at'] == spent['create_started_at']
                       and self.state['create_received_at'] == spent['create_received_at'])
        self.initial = modern.modern_wire_payload(modern.load(self.stage / 'create.json'))
        self.updated = modern.modern_wire_payload(modern.load(self.stage / 'metadata-put.json'))
        self.content, self.key = (self.stage / 'synthetic.xml').read_bytes(), self.plan['file_key']
        image = modern.load(self.stage / 'beforeimage197.json')
        modern.require(not credential_echoed(image, token) and token.encode() not in (self.stage / 'beforeimage197.json').read_bytes())
        self.state['identity'] = None
        identity = self.identity_fields(image)
        identity['doi'] = self.doi(image, False)
        modern.require(identity == spent['identity'] and identity['doi'] is None)
        actual = image.get('metadata')
        modern.require(isinstance(actual, dict)
                       and set(actual) <= {'publisher', 'dates', 'subjects', 'contributors', 'rights',
                                           'identifiers', 'related_identifiers', 'additional_titles',
                                           'additional_descriptions', 'languages', 'locations',
                                           'funding', 'references', 'version', 'sizes', 'formats'}
                       and all(v in (None, '', 'Zenodo') if k == 'publisher' else v in (None, '', [], {}) for k, v in actual.items())
                       and image.get('access', {}).get('record') == 'public'
                       and image.get('access', {}).get('files') in (None, 'public'))
        self.state['identity'] = identity
        self.grant = None

    def __init__(self, stage, token, transport, now=None):
        self.initialize_inputs(stage, token, transport, now)
        self.grant = modern.load(self.stage / 'approval.json')
        keys = {'schema_version', 'approved', 'approval_reference', 'executor', 'binding', 'limits',
                'started_at', 'valid_until', 'owner', 'known_ids', 'existing_candidate_only',
                'no_create_or_reset', 'controlled_schema_repair', 'historical_get_intents', 'preserved_file_inventory'}
        modern.require(set(self.grant) == keys and self.grant['schema_version'] == 1
                       and self.grant['approved'] is True and self.grant['executor'] == modern.EXECUTOR
                       and self.grant['binding'] == binding(self.stage) and self.grant['limits'] == LIMITS
                       and all(type(v) is int for v in self.grant['limits'].values())
                       and isinstance(self.grant['approval_reference'], str) and 1 <= len(self.grant['approval_reference']) <= 200
                       and self.grant['owner'] == self.original_grant['owner']
                       and self.grant['known_ids'] == self.original_grant['known_ids']
                       and all(self.grant[k] is True for k in ('existing_candidate_only', 'no_create_or_reset', 'controlled_schema_repair'))
                       and self.grant['historical_get_intents'] == HISTORICAL_GET
                       and self.grant['preserved_file_inventory'] == inventory_summary(modern.load(self.stage / 'origin.json')['inventory']))
        start, expiry = map(modern.datetime_aware, (self.grant['started_at'], self.grant['valid_until']))
        modern.require(start <= self.now() < expiry <= start + timedelta(minutes=10))
        digest = modern.sha((self.stage / 'approval.json').read_bytes())
        modern.require(self.state['grant_sha256'] in (None, digest))
        self.state['grant_sha256'] = digest
        self.persist()

    def check_prepared(self, prepared):
        modern.require(prepared.url == modern.ORIGIN + self.base()
                       and prepared.headers.get('Authorization') == 'Bearer ' + self.token
                       and prepared.headers.get('Accept') == modern.ACCEPT)
        if self.state['pending']['kind'] == 'metadata':
            validate_prepared_put(prepared, self.token, self.base())
            self.state['prepared_put_verified'] = True
            self.persist()
        else:
            modern.require(prepared.method == 'GET' and prepared.body is None)

    def request(self, kind, method, path, status, body=None, binary=False):
        modern.require(self.grant is not None, 'Preflight has no action grant')
        modern.require(kind in LIMITS and not binary and path == self.base() and status == 200
                       and self.state['counts'][kind] == 0)
        if kind == 'metadata':
            modern.require(method == 'PUT' and body == self.updated and not self.state['put_validated'])
        else:
            modern.require(method == 'GET' and body is None and self.state['put_validated'] is True
                           and self.state['counts']['metadata'] == 1 and self.state['pending'] is None)
        return super().request(kind, method, path, status, body, binary)

    def record(self, data, expected, *args, **kwargs):
        self.state['record_contract_diagnostics'] = owned.metadata_diagnostics(data, expected)
        self.persist()
        identity = super().record(data, expected, allow_no_doi=True)
        modern.require(identity['doi'] is None)
        return identity

    def run(self, retry=False):
        modern.require(self.grant is not None, 'Preflight has no action grant')
        try:
            modern.require(not retry and self.state['counts'] == dict.fromkeys(LIMITS, 0))
            self.record(self.request('metadata', 'PUT', self.base(), 200, deepcopy(self.updated)), self.updated)
            modern.require(self.state['prepared_put_verified'] is True)
            self.state['put_validated'] = True
            self.acknowledge()
            self.record(self.request('get', 'GET', self.base(), 200), self.updated)
            self.acknowledge()
            verify_origin(self.stage)
            self.state['completed'] = True
            self.persist()
            return self.receipt()
        except BaseException as error:
            diagnostic = {'attempt': self.capture_failure(error),
                          'record_contract_diagnostics': self.state['record_contract_diagnostics']}
            raise modern.Held('Controlled repair held; preserve all stages, no replay', diagnostic) from None

    def receipt(self):
        result = super().receipt()
        result.update(namespace=NAMESPACE, runtime_sha256=runtime_binding(),
                      historical_get_intents=HISTORICAL_GET + self.state['counts']['get'],
                      run02_metadata_put_intents=1 + self.state['counts']['metadata'],
                      run02_create_intents=1, prepared_put_verified=self.state['prepared_put_verified'],
                      put_validated=self.state['put_validated'], all_preserved_history_unchanged=True,
                      record_contract_diagnostics=self.state['record_contract_diagnostics'])
        return result


def preflight(stage, token):
    """The same complete local checks, without a grant, ledger write or transport."""
    controller = Controller.__new__(Controller)
    controller.initialize_inputs(stage, token, None)
    with modern.requests.Session() as session:
        prepared = session.prepare_request(modern.requests.Request(
            'PUT', modern.ORIGIN + controller.base(), json=controller.updated,
            headers={'Authorization': 'Bearer ' + token, 'Accept': modern.ACCEPT}))
    validate_prepared_put(prepared, token, controller.base())
    origin = modern.load(controller.stage / 'origin.json')
    return {'preflight_complete': True, 'provider_requests': 0,
            'counts': controller.state['counts'], 'runtime_sha256': runtime_binding(),
            'binding_sha256': modern.sha((controller.stage / 'binding.json').read_bytes()),
            'preserved_file_inventory': inventory_summary(origin['inventory']),
            'declared_manifest_files': len(modern.load(controller.stage / 'preserved-manifest.json')['files_sha256']),
            'prepared_put_sha256': modern.sha(prepared.body),
            'historical_get_intents': HISTORICAL_GET, 'fresh_parent_grant_required': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'preflight', 'execute'))
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--prior-continuation', type=Path)
    parser.add_argument('--beforeimage197', type=Path)
    parser.add_argument('--preserved-root', type=Path, action='append')
    parser.add_argument('--preserved-manifest', type=Path)
    args = parser.parse_args()
    try:
        token = os.environ.get('ZENODO_SANDBOX_TOKEN')
        result = (stage_packet(args.stage, args.prior_continuation, args.beforeimage197,
                               args.preserved_root, token, args.preserved_manifest)
                  if args.action == 'stage' else preflight(args.stage, token)
                  if args.action == 'preflight' else modern._execute_controller(args.stage, token, Controller))
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException as error:
        diagnostic = error.diagnostic if isinstance(error, modern.Held) else None
        print(json.dumps({'held': True, 'no_replay': True, 'diagnostic': diagnostic}, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
