"""Parent-authorized continuation of one sealed owned run02 empty draft.

No create route, old-state mutation or implicit expiry extension. The separate
ledger inherits the spent create and diagnostic read. Full metadata/access and
file predicates apply after PUT; all interrupted continuations remain held.
"""

import argparse
import json
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import modern_synthetic_canary as modern
from scripts.modern_canary_errors import credential_echoed

NAMESPACE = modern.NAMESPACE + '-owned-continuation'
BEFOREIMAGE_SHA = '316073505991baeca08490de43bc3dc5f0334917c0bcee4a60abc77e2a03f662'
DIAGNOSTICS_SHA = '3ea2e9ad7da503b7ad62277258b1b0f8936f03d3712025197f68c80e672cdbf6'
CREATE_RESPONSE_SHA = '20e8f71aad83b1f045c5657288f38896ab6a5931e4b1424e22310be25729dabf'
ORIGINAL_RUNTIME = {
    'modern_synthetic_canary.py': '8b96b63ca66ec4e27546ce3980abb98cb8f5f7b696eb2c7d3f590ac7a61e9b24',
    'modern_canary_errors.py': '2f1f68bf7fee4e39099b5969e2013e1bc01f30b9edef6a2cb7f44a275fbb5bf3',
}
PRIOR_FILES = ('binding.json', 'state.json', 'journal.json', 'approval.json',
               'synthetic.xml', 'create.json', 'metadata-put.json')
STATIC_FILES = ('origin.json', 'beforeimage.json', 'read-diagnostics.json',
                'prior-binding.json', 'prior-state.json', 'prior-journal.json',
                'prior-approval.json', 'synthetic.xml', 'create.json', 'metadata-put.json')
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


def verify_origin(stage):
    origin = modern.load(stage / 'origin.json')
    original = modern.secure_stage(Path(origin['original_stage']))
    preserved = Path(origin['preserved_root'])
    modern.require(preserved.is_absolute() and preserved.is_dir() and not preserved.is_symlink()
                   and (original == preserved or preserved in original.parents)
                   and stage != preserved and preserved not in stage.parents and stage not in preserved.parents)
    modern.require(set(origin['files_sha256']) == set(PRIOR_FILES))
    for name, digest in origin['files_sha256'].items():
        modern.require(modern.sha((original / name).read_bytes()) == digest,
                       'Original failed ledger changed; no continuation')
        copied = stage / ('prior-' + name if name.endswith('.json') and name not in
                          ('create.json', 'metadata-put.json') else name)
        modern.require(modern.sha(copied.read_bytes()) == digest)
    modern.require(modern.sha((stage / 'beforeimage.json').read_bytes()) == BEFOREIMAGE_SHA
                   and modern.sha((stage / 'read-diagnostics.json').read_bytes()) == DIAGNOSTICS_SHA)
    grant = modern.load(stage / 'prior-approval.json')
    state = modern.load(stage / 'prior-state.json')
    bound = modern.load(stage / 'prior-binding.json')
    journal = modern.load(stage / 'prior-journal.json')
    modern.require(bound == state['binding'] == grant['binding']
                   and bound['namespace'] == modern.NAMESPACE
                   and bound['stage'] == str(original)
                   and bound['packet_sha256'] == modern.PACKET_SHA
                   and bound['runtime_sha256'] == ORIGINAL_RUNTIME)
    modern.require(journal == {'state_sha256': origin['files_sha256']['state.json'],
                              'counts': state['counts'], 'binding': bound}
                   and state['grant_sha256'] == origin['files_sha256']['approval.json'])
    modern.require(state['failed'] is True and state['completed'] is False
                   and state['identity'] is None and state['pending']['kind'] == 'create'
                   and state['pending']['method'] == 'POST'
                   and state['pending']['path_sha256'] == modern.sha(b'/api/records')
                   and state['counts'] == {**dict.fromkeys(modern.LIMITS, 0), 'create': 1})
    responses, attempts = state['responses'], state['attempt_diagnostics']
    modern.require(isinstance(responses, list) and len(responses) == 1
                   and responses[0]['action'] == 'create' and responses[0]['method'] == 'POST'
                   and type(responses[0]['status']) is int and responses[0]['status'] == 201
                   and responses[0]['body_complete'] is True
                   and responses[0]['body_format'] == 'json'
                   and responses[0]['body_sha256'] == CREATE_RESPONSE_SHA
                   and responses[0]['credential_echo_detected'] is False)
    modern.require(isinstance(attempts, list) and len(attempts) == 1
                   and attempts[0]['action'] == 'create' and attempts[0]['phase'] == 'identity_validation'
                   and attempts[0]['response_seen'] is True and type(attempts[0]['status']) is int
                   and attempts[0]['status'] == 201 and attempts[0]['send_call_started'] is True
                   and attempts[0]['adapter_entered'] is True
                   and attempts[0]['failure']['phase'] == 'identity_validation'
                   and attempts[0]['failure']['exception'] == 'contract')
    modern.require(grant['approved'] is True and grant['executor'] == modern.EXECUTOR
                   and grant['limits'] == modern.LIMITS and type(grant['owner']) is int
                   and grant['owner'] > 0 and grant['exclusive_namespace_confirmed'] is True
                   and grant['prior_create_allowances_permanently_spent'] is True)
    started = modern.datetime_aware(grant['started_at'])
    modern.require(modern.datetime_aware(grant['valid_until']) == started + timedelta(seconds=1800))
    for name in ('synthetic.xml', 'create.json', 'metadata-put.json'):
        modern.require((stage / name).read_bytes() == (modern.PACKET / name).read_bytes())
    return grant, state


def runtime_binding():
    return {**modern.runtime_binding(), 'modern_owned_continuation.py':
            modern.sha(Path(__file__).read_bytes())}


def binding(stage):
    verify_origin(stage)
    return {'schema_version': 1, 'namespace': NAMESPACE, 'stage': str(stage),
            'packet_sha256': modern.PACKET_SHA, 'runtime_sha256': runtime_binding(),
            'input_sha256': {name: modern.sha((stage / name).read_bytes()) for name in STATIC_FILES},
            'prior_spent_counts': {'create': 1, 'get': 1}, 'historical_get_intents': 196}


def stage_packet(stage, original_stage, beforeimage, diagnostics, token, preserved_root=None):
    """Exclusive offline staging by sole executor; no approval or provider request."""
    stage = Path(stage)
    modern.require(stage.is_absolute() and stage.name == NAMESPACE and not stage.exists())
    for path in (stage, *stage.parents):
        modern.require(not path.is_symlink())
    modern.require(isinstance(token, str) and token and token.isascii())
    original = modern.secure_stage(original_stage)
    preserved = original if preserved_root is None else Path(preserved_root)
    modern.require(preserved.is_absolute() and preserved.is_dir() and preserved.resolve() == preserved
                   and (original == preserved or preserved in original.parents)
                   and stage != preserved and preserved not in stage.parents and stage not in preserved.parents,
                   'Continuation destination must be outside the preserved original root')
    modern.packet()
    raw_image, raw_diagnostics = Path(beforeimage).read_bytes(), Path(diagnostics).read_bytes()
    modern.require(len(raw_image) <= 65536 and modern.sha(raw_image) == BEFOREIMAGE_SHA
                   and modern.sha(raw_diagnostics) == DIAGNOSTICS_SHA)
    for raw in (raw_image, raw_diagnostics):
        modern.require(token.encode() not in raw and not credential_echoed(json.loads(raw), token),
                       'Credential echo held; no private body copied')
    inputs = {'beforeimage.json': raw_image, 'read-diagnostics.json': raw_diagnostics}
    origins = {}
    for name in PRIOR_FILES:
        raw = (original / name).read_bytes()
        modern.require(token.encode() not in raw and
                       (not name.endswith('.json') or not credential_echoed(json.loads(raw), token)))
        origins[name] = modern.sha(raw)
        target = 'prior-' + name if name.endswith('.json') and name not in ('create.json', 'metadata-put.json') else name
        inputs[target] = raw
    stage.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name, raw in inputs.items():
        fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    modern.atomic(stage / 'origin.json', {'original_stage': str(original),
                                        'preserved_root': str(preserved), 'files_sha256': origins})
    prior_grant, prior_state = verify_origin(stage)
    image = modern.load(stage / 'beforeimage.json')
    modern.require(modern.record_id(image.get('id')) == prior_state['uncertain_candidate_id'])
    bound = binding(stage)
    modern.atomic(stage / 'binding.json', bound)
    state = {'binding': bound, 'grant_sha256': None,
             'counts': {**dict.fromkeys(modern.LIMITS, 0), 'create': 1, 'get': 1},
             'pending': None, 'failed': False, 'completed': False, 'retry_completed': False,
             'create_started_at': prior_state['create_started_at'],
             'create_received_at': prior_state['create_received_at'],
             'identity': None, 'uncertain_candidate_id': prior_state['uncertain_candidate_id'],
             'responses': [], 'attempt_diagnostics': [], 'controller_failure': None,
             'record_contract_diagnostics': None}
    modern.save(stage, state)
    return {'staged': True, 'provider_requests': 0, 'namespace': NAMESPACE,
            'runtime_sha256': bound['runtime_sha256'], 'counts': state['counts'],
            'original_failed_ledger_unchanged': True, 'original_expiry_retained_in_provenance':
            bool(prior_grant['valid_until'])}


def approval(stage, now, original):
    grant = modern.load(stage / 'approval.json')
    keys = {'schema_version', 'approved', 'approval_reference', 'executor', 'binding',
            'limits', 'started_at', 'valid_until', 'owner', 'known_ids', 'window_mode',
            'original_valid_until', 'existing_candidate_only', 'no_create_or_reset',
            'additional_get_limit', 'preserved_file_inventory'}
    modern.require(isinstance(grant, dict) and set(grant) == keys)
    modern.require(grant['schema_version'] == 1 and grant['approved'] is True
                   and grant['executor'] == modern.EXECUTOR and grant['binding'] == binding(stage)
                   and isinstance(grant['approval_reference'], str) and 1 <= len(grant['approval_reference']) <= 200
                   and grant['limits'] == modern.LIMITS and grant['owner'] == original['owner']
                   and type(grant['owner']) is int and grant['known_ids'] == original['known_ids']
                   and grant['existing_candidate_only'] is True and grant['no_create_or_reset'] is True
                   and type(grant['additional_get_limit']) is int and grant['additional_get_limit'] == 6
                   and grant['original_valid_until'] == original['valid_until'])
    inventory = grant['preserved_file_inventory']
    modern.require(isinstance(inventory, dict) and set(inventory) == {'count', 'sha256'}
                   and type(inventory['count']) is int and inventory['count'] == 305
                   and isinstance(inventory['sha256'], str) and modern.re.fullmatch(r'[0-9a-f]{64}', inventory['sha256']))
    started, expires = modern.datetime_aware(grant['started_at']), modern.datetime_aware(grant['valid_until'])
    modern.require(started <= now < expires <= started + timedelta(seconds=1800))
    modern.require(grant['window_mode'] in ('original_window', 'specifically_authorized_continuation_window'))
    if grant['window_mode'] == 'original_window':
        modern.require(expires <= modern.datetime_aware(original['valid_until']))
    # The second mode is an explicit parent dispatch decision bound to this ledger;
    # neither staging nor this code generates/extends an approval window.
    return grant


def metadata_diagnostics(data, expected):
    """Closed field labels/booleans only; never values, unknown keys or repr."""
    actual = data.get('metadata') if isinstance(data, dict) else None
    actual = actual if isinstance(actual, dict) else {}
    result = {}
    for name in ('title', 'publication_date', 'description', 'keywords', 'resource_type', 'creators'):
        result[name + '_present'] = name in actual
        wanted = expected['metadata'][name]
        value = actual.get(name)
        result[name + '_type'] = {str: 'string', dict: 'object', list: 'array', int: 'integer',
                                 bool: 'boolean', type(None): 'null'}.get(type(value), 'other') if name in actual else 'missing'
        if name == 'resource_type':
            matches = isinstance(value, dict) and value.get('id') == wanted['id']
        elif name == 'creators':
            item = value[0] if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict) else {}
            person = item.get('person_or_org')
            matches = (isinstance(person, dict) and all(person.get(k) == v for k, v in wanted[0]['person_or_org'].items())
                       and not item.get('affiliations') and person.get('identifiers') in (None, []))
        else:
            matches = value == wanted
        result[name + '_matches'] = bool(matches)
    access = data.get('access') if isinstance(data, dict) else None
    access = access if isinstance(access, dict) else {}
    for name in ('record', 'files'):
        result['access_' + name + '_present'] = name in access
        result['access_' + name + '_matches'] = access.get(name) == expected['access'][name]
    try:
        modern.validate_metadata(actual, expected['metadata'])
        result['metadata_contract_matches'] = True
    except (modern.Held, KeyError, TypeError, ValueError):
        result['metadata_contract_matches'] = False
    return result


class Controller(modern.Controller):
    validate_stage = staticmethod(secure_stage)

    def stage_binding(self):
        return binding(self.stage)

    def creation_grant(self):
        return self.original_grant

    def __init__(self, stage, token, transport, now=None):
        self.stage = secure_stage(stage)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.plan = modern.packet()
        self.original_grant, self.original_state = verify_origin(self.stage)
        self.grant = approval(self.stage, self.now(), self.original_grant)
        modern.require(isinstance(token, str) and token and token.isascii()
                       and all(33 <= ord(ch) <= 126 for ch in token))
        self.token, self.transport = token, transport
        self.state = modern.load(self.stage / 'state.json')
        bound = binding(self.stage)
        modern.require(modern.load(self.stage / 'binding.json') == self.state['binding'] == bound)
        modern.require(modern.load(self.stage / 'journal.json') == {
            'state_sha256': modern.sha((self.stage / 'state.json').read_bytes()),
            'counts': self.state['counts'], 'binding': bound})
        modern.require(set(self.state['counts']) == set(modern.LIMITS)
                       and all(type(v) is int and 0 <= v <= modern.LIMITS[k] for k, v in self.state['counts'].items())
                       and self.state['counts']['create'] == 1 and 1 <= self.state['counts']['get'] <= 7)
        modern.require(self.state['failed'] is False and self.state['pending'] is None,
                       'Interrupted continuation held; no replay or reset')
        modern.require(self.state['create_started_at'] == self.original_state['create_started_at']
                       and self.state['create_received_at'] == self.original_state['create_received_at'])
        self.initial, self.updated = modern.load(self.stage / 'create.json'), modern.load(self.stage / 'metadata-put.json')
        self.content, self.key = (self.stage / 'synthetic.xml').read_bytes(), self.plan['file_key']
        image = modern.load(self.stage / 'beforeimage.json')
        modern.require(token.encode() not in (self.stage / 'beforeimage.json').read_bytes()
                       and not credential_echoed(image, token))
        initial_state = deepcopy(self.state)
        self.state['identity'] = None
        identity = self.identity_fields(image)
        modern.require(identity['id'] == self.original_state['uncertain_candidate_id'])
        metadata = image.get('metadata')
        modern.require(isinstance(metadata, dict)
                       and set(metadata) <= {'publisher', 'dates', 'subjects', 'contributors', 'rights',
                                           'identifiers', 'related_identifiers', 'additional_titles',
                                           'additional_descriptions', 'languages', 'locations',
                                           'funding', 'references', 'version', 'sizes', 'formats'}
                       and all(v in (None, '', [], {}, 'Zenodo') if k == 'publisher' else
                               v in (None, '', [], {}) for k, v in metadata.items()))
        access = image.get('access')
        modern.require(isinstance(access, dict) and access.get('record') == 'public'
                       and access.get('files') in ('public', 'restricted'))
        identity['doi'] = self.doi(image, False)
        modern.require(identity['doi'] is None)
        self.state = initial_state
        digest = modern.sha((self.stage / 'approval.json').read_bytes())
        if self.state['grant_sha256'] is None:
            modern.require(self.state['counts'] == {**dict.fromkeys(modern.LIMITS, 0), 'create': 1, 'get': 1}
                           and self.state['identity'] is None and not self.state['responses'])
            self.state['grant_sha256'] = digest
            self.state['identity'] = identity
            self.state['uncertain_candidate_id'] = None
            self.persist()
        modern.require(self.state['grant_sha256'] == digest
                       and all(self.state['identity'][k] == identity[k] for k in ('id', 'parent_id', 'created')))

    def request(self, kind, *args, **kwargs):
        modern.require(kind != 'create', 'No CREATE route in owned continuation')
        if kind == 'get':
            modern.require(self.state['counts']['get'] < 7)
        return super().request(kind, *args, **kwargs)

    def record(self, data, expected, *args, **kwargs):
        self.state['record_contract_diagnostics'] = metadata_diagnostics(data, expected)
        self.persist()
        return super().record(data, expected, *args, **kwargs)

    def readback(self):
        self.record(self.request('get', 'GET', self.base(), 200), self.updated, True)
        self.acknowledge()
        listing = self.request('get', 'GET', self.base() + '/files', 200)
        modern.require(isinstance(listing, dict) and isinstance(listing.get('entries'), list)
                       and len(listing['entries']) == 1)
        self.file(listing['entries'][0], True)
        self.acknowledge()
        modern.require(self.request('get', 'GET', self.filebase() + '/content', 200, binary=True) == self.content)
        self.acknowledge()

    def run(self, retry=False):
        try:
            if retry:
                modern.require(self.state['completed'] is True and self.state['retry_completed'] is False
                               and self.state['counts']['get'] == 4)
                self.readback()
                self.state['retry_completed'] = True
                self.persist()
            else:
                modern.require(not self.state['completed'] and self.state['counts'] ==
                               {**dict.fromkeys(modern.LIMITS, 0), 'create': 1, 'get': 1})
                updated = self.request('metadata', 'PUT', self.base(), 200, deepcopy(self.updated))
                self.state['identity'] = self.record(updated, self.updated, allow_no_doi=True)
                self.acknowledge()
                if self.state['identity']['doi'] is None:
                    reserved = self.request('doi', 'POST', self.base() + '/pids/doi', 201)
                    self.state['identity'] = self.record(reserved, self.updated)
                    self.acknowledge()
                init = self.request('init', 'POST', self.base() + '/files', 201, [{'key': self.key}])
                modern.require(isinstance(init, dict) and isinstance(init.get('entries'), list) and len(init['entries']) == 1)
                self.file(init['entries'][0], False)
                self.acknowledge()
                self.file(self.request('content', 'PUT', self.filebase() + '/content', 200, self.content, binary=True), False)
                self.acknowledge()
                self.file(self.request('commit', 'POST', self.filebase() + '/commit', 200), True)
                self.acknowledge()
                self.readback()
                self.state['completed'] = True
                self.persist()
            return self.receipt()
        except BaseException as error:
            diagnostic = {'attempt': self.capture_failure(error),
                          'record_contract_diagnostics': self.state['record_contract_diagnostics']}
            raise modern.Held('Owned continuation held; no replay or reset', diagnostic) from None

    def receipt(self):
        result = super().receipt()
        result.update(namespace=NAMESPACE, runtime_sha256=runtime_binding(),
                      original_failed_ledger_unchanged=True, historical_get_intents=195 + self.state['counts']['get'],
                      additional_provider_intents=sum(self.state['counts'].values()) - 2,
                      record_contract_diagnostics=self.state['record_contract_diagnostics'])
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'execute', 'retry'))
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--original-stage', type=Path)
    parser.add_argument('--beforeimage', type=Path)
    parser.add_argument('--diagnostics', type=Path)
    parser.add_argument('--preserved-root', type=Path)
    args = parser.parse_args()
    try:
        token = os.environ.get('ZENODO_SANDBOX_TOKEN')
        if args.action == 'stage':
            modern.require(args.preserved_root is not None)
            result = stage_packet(args.stage, args.original_stage, args.beforeimage, args.diagnostics, token,
                                  args.preserved_root)
        else:
            result = modern._execute_controller(args.stage, token, Controller, args.action == 'retry')
        print(json.dumps(result, sort_keys=True))
        return 0
    except (modern.Held, OSError, ValueError, KeyError, TypeError) as error:
        result = {'completed': False, 'held': True,
                  'reason': 'Owned continuation contract held; preserve all state'}
        if type(error) is modern.Held and error.diagnostic is not None:
            result['diagnostic'] = error.diagnostic
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
