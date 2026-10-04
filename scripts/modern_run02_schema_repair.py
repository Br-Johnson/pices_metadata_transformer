"""One complete-schema PUT/GET after the permanently spent subjects repair.

The separate parent-bound ledger preserves all357 historical entries and permits
only the same sealed synthetic draft. No create/PID/files/publish/delete/replay.
"""

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import modern_draft_schema as schema
from scripts import modern_owned_continuation as owned
from scripts import modern_run02_subjects_repair as prior
from scripts import modern_synthetic_canary as modern
from scripts.modern_canary_errors import credential_echoed

NAMESPACE = modern.NAMESPACE + '-schema-repair'
PREPARED_PUT_SHA = '71830ca80356953b8654dd0e589eeff15b1b46c08c313b98372936c85c09da7a'
PRIOR_RUNTIME = {
    'modern_run02_subjects_repair.py': '085cefe5ff18b6c5c06d9d7598f267ec19c6bfe6a6a0953588c3477d7c7f46e2',
    'modern_synthetic_canary.py': '9d3c27b6b2d31f59b054971108f0a8abb87e5a069eae56fed94498323d3237cd',
    'modern_owned_continuation.py': 'bb559985ce97fdf855d3995981fa290a958910a9d5f7721a02a83de999163090',
    'modern_canary_errors.py': 'f6393fde1dddb6e2c751e7ab8d8ec18261d55c93bf29603e531117f0c361aa54',
}
MIN_PRESERVED_FILES = 357
LIMITS = {'metadata': 1, 'get': 1}
PRIOR_FILES = ('binding.json', 'state.json', 'journal.json', 'approval.json')
STATIC_FILES = ('origin.json', 'preserved-manifest.json', 'beforeimage197.json',
                'synthetic.xml', 'create.json', 'metadata-put.json',
                *(f'spent-{name}' for name in PRIOR_FILES))
FILES = modern.FILES | set(STATIC_FILES)


def secure_stage(stage):
    stage = Path(stage)
    modern.require(stage.is_absolute() and stage.name == NAMESPACE and stage.resolve() == stage)
    for path in (stage, *stage.parents):
        modern.require(not path.is_symlink())
    modern.require(stage.is_dir() and stage.stat().st_mode & 0o077 == 0)
    for path in stage.iterdir():
        modern.require(path.name in FILES and not path.is_symlink() and path.is_file()
                       and path.stat().st_nlink == 1 and path.stat().st_mode & 0o077 == 0)
    return stage


def verify_spent(stage):
    """Exact immutable failed PUT2, not a reset or a current canonical read."""
    stage = prior.secure_stage(stage)
    original, spent_owned = prior.verify_origin(stage)
    bound = modern.load(stage / 'binding.json')
    state = modern.load(stage / 'state.json')
    grant = modern.load(stage / 'approval.json')
    modern.require(bound == state['binding'] == grant['binding']
                   and bound['runtime_sha256'] == PRIOR_RUNTIME and bound['stage'] == str(stage)
                   and bound['schema_version'] == 1 and bound['namespace'] == prior.NAMESPACE
                   and bound['packet_sha256'] == modern.PACKET_SHA
                   and bound['input_sha256'] == {name: modern.sha((stage / name).read_bytes()) for name in prior.STATIC_FILES}
                   and bound['prepared_put_sha256'] == prior.PREPARED_PUT_SHA
                   and bound['historical_get_intents'] == 197
                   and bound['prior_run02_create_intents'] == bound['prior_run02_metadata_put_intents'] == 1)
    modern.require(modern.load(stage / 'journal.json') == {
        'state_sha256': modern.sha((stage / 'state.json').read_bytes()), 'counts': state['counts'], 'binding': bound})
    modern.require(state['grant_sha256'] == modern.sha((stage / 'approval.json').read_bytes())
                   and grant['approved'] is True and grant['executor'] == modern.EXECUTOR
                   and grant['owner'] == original['owner'] and grant['known_ids'] == original['known_ids']
                   and grant['limits'] == LIMITS and grant['existing_candidate_only'] is True
                   and grant['no_create_or_reset'] is True and grant['controlled_schema_repair'] is True
                   and grant['historical_get_intents'] == 197
                   and grant['preserved_file_inventory'] == prior.inventory_summary(modern.load(stage / 'origin.json')['inventory']))
    start, expiry = map(modern.datetime_aware, (grant['started_at'], grant['valid_until']))
    modern.require(start < expiry <= start + timedelta(minutes=10))
    modern.require(state['failed'] is True and state['completed'] is False
                   and state['counts'] == {'metadata': 1, 'get': 0}
                   and all(type(v) is int for v in state['counts'].values())
                   and state['prepared_put_verified'] is True and state['put_validated'] is False
                   and state['identity'] == spent_owned['identity'] and state['identity']['doi'] is None
                   and state['create_started_at'] == spent_owned['create_started_at']
                   and state['create_received_at'] == spent_owned['create_received_at']
                   and state['pending'] == {'kind': 'metadata', 'method': 'PUT',
                       'path_sha256': modern.sha(('/api/records/' + modern.record_id(state['identity']['id']) + '/draft').encode())}
                   and len(state['responses']) == len(state['attempt_diagnostics']) == 1)
    response, attempt = state['responses'][0], state['attempt_diagnostics'][0]
    flags = response.get('validation_errors', {})
    modern.require(response['action'] == 'metadata' and response['method'] == 'PUT'
                   and response['status'] == 200 and response['body_complete'] is True
                   and response['credential_echo_detected'] is False
                   and attempt['action'] == 'metadata' and attempt['response_seen'] is True
                   and attempt['status'] == 200 and flags.get('errors_present') is True
                   and flags.get('errors_type') == 'array' and flags.get('errors_shape_supported') is True
                   and flags.get('errors_count') == 2 and flags.get('metadata_publisher_error_present') is True
                   and flags.get('unknown_error_field_present') is True)
    # These flags came from PUT2. GET197 remains an earlier identity anchor.
    diagnostics = state['record_contract_diagnostics']
    modern.require(isinstance(diagnostics, dict)
                   and all(diagnostics.get(name + '_present') is False
                           for name in ('title', 'publication_date', 'description', 'subjects', 'resource_type', 'creators'))
                   and diagnostics.get('access_files_matches') is False)
    return original, state


def verify_origin(stage):
    origin = modern.load(stage / 'origin.json')
    modern.require(set(origin) == {'prior_repair', 'manifest_source', 'inventory'})
    old = prior.secure_stage(Path(origin['prior_repair']))
    original, spent = verify_spent(old)
    declared = prior.manifest(modern.load(stage / 'preserved-manifest.json'))
    modern.require(len(declared['files_sha256']) >= MIN_PRESERVED_FILES,
                   'Complete357 historical evidence manifest required')
    snapshot = prior.inventory(list(origin['inventory']), stage, declared)
    modern.require(snapshot == origin['inventory'], 'Preserved history changed; no schema repair')
    verify_manifest_coverage(snapshot, declared, origin['manifest_source'])
    files = prior.inventory_files(snapshot)
    modern.require(stage != old and stage not in old.parents and old not in stage.parents
                   and all(files.get(str(path)) == modern.sha(path.read_bytes()) for path in old.iterdir()))
    old_origin = modern.load(old / 'origin.json')
    prior.verify_coverage(snapshot, Path(old_origin['prior_continuation']),
                          Path(old_origin['beforeimage197_path']), stage)
    for name in PRIOR_FILES:
        modern.require((stage / ('spent-' + name)).read_bytes() == (old / name).read_bytes())
    modern.require((stage / 'beforeimage197.json').read_bytes() == (old / 'beforeimage197.json').read_bytes())
    for name in ('synthetic.xml', 'create.json', 'metadata-put.json'):
        modern.require((stage / name).read_bytes() == (modern.PACKET / name).read_bytes())
    return original, spent


def verify_manifest_coverage(snapshot, declared, source):
    """Every retained evidence byte has a previous expected hash, not a new baseline."""
    source = prior.evidence_path(source, leaf=True)
    modern.require(modern.load(source) == declared)
    files = prior.inventory_files(snapshot)
    modern.require(set(files) <= set(declared['files_sha256']) | {str(source)},
                   'Every retained evidence file must be in the sealed expected manifest')


def runtime_binding():
    return {**prior.runtime_binding(),
            'modern_draft_schema.py': modern.sha(Path(schema.__file__).read_bytes()),
            'modern_run02_schema_repair.py': modern.sha(Path(__file__).read_bytes())}


def binding(stage):
    verify_origin(stage)
    return {'schema_version': 1, 'namespace': NAMESPACE, 'stage': str(stage),
            'packet_sha256': modern.PACKET_SHA, 'runtime_sha256': runtime_binding(),
            'schema_sha256': schema.schema_binding(),
            'input_sha256': {name: modern.sha((stage / name).read_bytes()) for name in STATIC_FILES},
            'prepared_put_sha256': PREPARED_PUT_SHA, 'historical_get_intents': 197,
            'prior_run02_create_intents': 1, 'prior_run02_metadata_put_intents': 2,
            'exact_missing_upload_warning_only': True}


def validate_prepared_put(prepared, token, path):
    modern.require(prepared.url == modern.ORIGIN + path and prepared.method == 'PUT'
                   and prepared.headers.get('Authorization') == 'Bearer ' + token
                   and prepared.headers.get('Accept') == modern.ACCEPT
                   and prepared.headers.get('Content-Type') == 'application/json'
                   and prepared.headers.get('Content-Length') == '517'
                   and isinstance(prepared.body, bytes) and len(prepared.body) == 517
                   and modern.sha(prepared.body) == PREPARED_PUT_SHA)
    schema.validate_payload(json.loads(prepared.body))


def stage_packet(stage, previous_repair, preserved_roots, token, preserved_manifest):
    """Read sealed history and stage offline; never read/mint an action grant."""
    stage = Path(stage)
    modern.require(stage.is_absolute() and stage.resolve() == stage
                   and stage.name == NAMESPACE and not stage.exists())
    modern.require(all(not path.is_symlink() for path in (stage, *stage.parents)))
    modern.require(isinstance(token, str) and token and token.isascii())
    old = prior.secure_stage(previous_repair)
    verify_spent(old)
    source = prior.evidence_path(preserved_manifest, leaf=True)
    modern.require(source.stat().st_size <= 2 * 1024 * 1024)
    declared = prior.manifest(modern.load(source))
    modern.require(len(declared['files_sha256']) >= MIN_PRESERVED_FILES)
    roots = list(preserved_roots or [])
    if not any(source == Path(root) or Path(root) in source.parents for root in roots):
        roots.append(source)
    snapshot = prior.inventory(roots, stage, declared)
    verify_manifest_coverage(snapshot, declared, source)
    files = prior.inventory_files(snapshot)
    modern.require(stage != old and stage not in old.parents and old not in stage.parents
                   and all(files.get(str(path)) == modern.sha(path.read_bytes()) for path in old.iterdir()))
    old_origin = modern.load(old / 'origin.json')
    prior.verify_coverage(snapshot, Path(old_origin['prior_continuation']),
                          Path(old_origin['beforeimage197_path']), stage)
    inputs = {'preserved-manifest.json': modern.encoded(declared),
              'beforeimage197.json': (old / 'beforeimage197.json').read_bytes()}
    inputs.update({f'spent-{name}': (old / name).read_bytes() for name in PRIOR_FILES})
    inputs.update({name: (modern.PACKET / name).read_bytes()
                   for name in ('synthetic.xml', 'create.json', 'metadata-put.json')})
    schema.synthetic_payload(modern.load(modern.PACKET / 'metadata-put.json'))
    for name, raw in inputs.items():
        modern.require(token.encode() not in raw and
                       (not name.endswith('.json') or not credential_echoed(json.loads(raw), token)))
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name, raw in inputs.items():
        fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    modern.atomic(stage / 'origin.json', {'prior_repair': str(old), 'manifest_source': str(source), 'inventory': snapshot})
    _, spent = verify_origin(stage)
    bound = binding(stage)
    modern.atomic(stage / 'binding.json', bound)
    modern.save(stage, {'binding': bound, 'grant_sha256': None, 'counts': dict.fromkeys(LIMITS, 0),
                       'pending': None, 'failed': False, 'completed': False, 'retry_completed': False,
                       'identity': deepcopy(spent['identity']), 'create_started_at': spent['create_started_at'],
                       'create_received_at': spent['create_received_at'], 'responses': [], 'attempt_diagnostics': [],
                       'controller_failure': None, 'record_contract_diagnostics': None,
                       'put_validated': False, 'prepared_put_verified': False, 'accepted_empty_file_warnings': 0})
    return {'staged': True, 'provider_requests': 0, 'runtime_sha256': runtime_binding(),
            'schema_sha256': schema.schema_binding(), 'preserved_file_inventory': prior.inventory_summary(snapshot),
            'historical_get_intents': 197, 'prior_run02_metadata_put_intents': 2}


class Controller(prior.Controller):
    validate_stage = staticmethod(secure_stage)
    creation_grant = prior.Controller.creation_grant
    request = prior.Controller.request

    def stage_binding(self):
        return binding(self.stage)

    def initialize_inputs(self, stage, token, transport, now=None):
        self.stage = secure_stage(stage)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.plan = modern.packet()
        self.original_grant, spent = verify_origin(self.stage)
        self.grant = self.original_grant
        modern.require(isinstance(token, str) and token and token.isascii() and all(33 <= ord(c) <= 126 for c in token))
        self.token, self.transport = token, transport
        for name in STATIC_FILES:
            raw = (self.stage / name).read_bytes()
            modern.require(token.encode() not in raw and
                           (not name.endswith('.json') or not credential_echoed(json.loads(raw), token)))
        self.state = modern.load(self.stage / 'state.json')
        modern.require(modern.load(self.stage / 'binding.json') == self.state['binding'] == binding(self.stage))
        modern.require(modern.load(self.stage / 'journal.json') == {
            'state_sha256': modern.sha((self.stage / 'state.json').read_bytes()), 'counts': self.state['counts'], 'binding': self.state['binding']})
        modern.require(self.state['counts'] == dict.fromkeys(LIMITS, 0) and self.state['pending'] is None
                       and all(type(v) is int for v in self.state['counts'].values())
                       and self.state['failed'] is False and self.state['completed'] is False
                       and self.state['put_validated'] is False and self.state['prepared_put_verified'] is False
                       and self.state['accepted_empty_file_warnings'] == 0,
                       'Schema repair consumed or interrupted; no reentry')
        modern.require(self.state['identity'] == spent['identity']
                       and self.state['create_started_at'] == spent['create_started_at']
                       and self.state['create_received_at'] == spent['create_received_at'])
        self.initial = schema.synthetic_payload(modern.load(self.stage / 'create.json'))
        self.updated = schema.synthetic_payload(modern.load(self.stage / 'metadata-put.json'))
        self.content, self.key = (self.stage / 'synthetic.xml').read_bytes(), self.plan['file_key']
        image = modern.load(self.stage / 'beforeimage197.json')
        self.state['identity'] = None
        identity = self.identity_fields(image)
        identity['doi'] = self.doi(image, False)
        modern.require(identity == spent['identity'] and identity['doi'] is None)
        self.state['identity'] = identity
        self.grant = None

    def __init__(self, stage, token, transport, now=None):
        self.initialize_inputs(stage, token, transport, now)
        self.grant = modern.load(self.stage / 'approval.json')
        keys = {'schema_version', 'approved', 'approval_reference', 'executor', 'binding', 'limits',
                'started_at', 'valid_until', 'owner', 'known_ids', 'existing_candidate_only', 'no_create_or_reset',
                'controlled_full_schema_repair', 'allow_exact_missing_upload_warning',
                'historical_get_intents', 'preserved_file_inventory'}
        modern.require(set(self.grant) == keys and self.grant['schema_version'] == 1
                       and self.grant['approved'] is True and self.grant['executor'] == modern.EXECUTOR
                       and self.grant['binding'] == binding(self.stage) and self.grant['limits'] == LIMITS
                       and all(type(v) is int for v in self.grant['limits'].values())
                       and isinstance(self.grant['approval_reference'], str) and 1 <= len(self.grant['approval_reference']) <= 200
                       and self.grant['owner'] == self.original_grant['owner']
                       and self.grant['known_ids'] == self.original_grant['known_ids']
                       and all(self.grant[k] is True for k in ('existing_candidate_only', 'no_create_or_reset',
                                                             'controlled_full_schema_repair', 'allow_exact_missing_upload_warning'))
                       and self.grant['historical_get_intents'] == 197
                       and self.grant['preserved_file_inventory'] == prior.inventory_summary(modern.load(self.stage / 'origin.json')['inventory']))
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

    def record(self, data, expected, *args, **kwargs):
        diagnostics = owned.metadata_diagnostics(data, expected)
        actual = data.get('metadata') if isinstance(data, dict) else None
        diagnostics['publisher_present'] = isinstance(actual, dict) and 'publisher' in actual
        diagnostics['publisher_matches'] = isinstance(actual, dict) and actual.get('publisher') == schema.PUBLISHER
        self.state['record_contract_diagnostics'] = diagnostics
        self.persist()
        modern.require(diagnostics['publisher_matches'])
        warning = schema.expected_empty_file_warning(data)
        checked = deepcopy(data)
        checked.pop('errors', None)
        identity = modern.Controller.record(self, checked, expected, allow_no_doi=True)
        modern.require(identity['doi'] is None)
        # Full metadata/access, same owner/draft, zero files and absent DOI have
        # now passed. Only this ledger accepts the exact source-backed warning.
        if warning:
            self.state['accepted_empty_file_warnings'] += 1
            self.persist()
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
            raise modern.Held('Complete-schema repair held; preserve every stage, no replay', diagnostic) from None

    def receipt(self):
        result = modern.Controller.receipt(self)
        result.update(namespace=NAMESPACE, runtime_sha256=runtime_binding(), schema_sha256=schema.schema_binding(),
                      historical_get_intents=197 + self.state['counts']['get'],
                      run02_metadata_put_intents=2 + self.state['counts']['metadata'], run02_create_intents=1,
                      prepared_put_verified=self.state['prepared_put_verified'], put_validated=self.state['put_validated'],
                      all_preserved_history_unchanged=True, publication_ready=False,
                      accepted_empty_file_warnings=self.state['accepted_empty_file_warnings'],
                      record_contract_diagnostics=self.state['record_contract_diagnostics'])
        return result


def preflight(stage, token):
    controller = Controller.__new__(Controller)
    controller.initialize_inputs(stage, token, None)
    with modern.requests.Session() as session:
        prepared = session.prepare_request(modern.requests.Request(
            'PUT', modern.ORIGIN + controller.base(), json=controller.updated,
            headers={'Authorization': 'Bearer ' + token, 'Accept': modern.ACCEPT}))
    validate_prepared_put(prepared, token, controller.base())
    return {'preflight_complete': True, 'local_schema_valid': True, 'provider_requests': 0,
            'counts': controller.state['counts'], 'runtime_sha256': runtime_binding(),
            'schema_sha256': schema.schema_binding(),
            'binding_sha256': modern.sha((controller.stage / 'binding.json').read_bytes()),
            'preserved_file_inventory': prior.inventory_summary(modern.load(controller.stage / 'origin.json')['inventory']),
            'declared_manifest_files': len(modern.load(controller.stage / 'preserved-manifest.json')['files_sha256']),
            'prepared_put_bytes': len(prepared.body), 'prepared_put_sha256': modern.sha(prepared.body),
            'historical_get_intents': 197, 'prior_run02_metadata_put_intents': 2,
            'fresh_parent_grant_required': True, 'exact_missing_upload_warning_policy_required': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'preflight', 'execute'))
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--previous-repair', type=Path)
    parser.add_argument('--preserved-root', type=Path, action='append')
    parser.add_argument('--preserved-manifest', type=Path)
    args = parser.parse_args()
    try:
        token = os.environ.get('ZENODO_SANDBOX_TOKEN')
        result = (stage_packet(args.stage, args.previous_repair, args.preserved_root, token, args.preserved_manifest)
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
