"""Read-only observations for the single spent FGDC-141 modern create.

No create, adoption, upload, publish, delete, redirects or automatic continuation.
A legacy inventory never proves modern absence. All original evidence is immutable.
Provider dispatch requires separately reviewed actual evidence and a fresh grant.
"""

import argparse
import base64
import getpass
import platform
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import modern_publication as publication
from scripts import modern_singleton_executor as draft
from scripts.modern_draft_schema import expected_empty_file_warning
from scripts.modern_response_evidence import normalize_response, sensitive
from scripts.modern_singleton import (
    Held,
    Prepared,
    compare_metadata,
    encode,
    parse,
    prepare,
    require,
    sha,
)
from scripts.path_config import OutputPaths
from scripts.production_mutations import EXCLUDED, PROTECTED
from scripts.upload_service import atomic_json, ledger_lock

SOURCE_ID = 'FGDC-141'
LIMITS = {'get': 240, 'pages': 200}
KIND = 'modern-unknown-create-observations-v1'
LIST_BASE = '/api/deposit/depositions'


def positive_id(value):
    require(isinstance(value, str) and re.fullmatch('[1-9][0-9]{0,19}', value))
    return value


def immutable_bytes(path, *, optional=False):
    path = Path(path).absolute()
    require(path == path.resolve() and all(not p.is_symlink() for p in (path, *path.parents)))
    if optional and not path.exists():
        return None
    require(path.is_file() and path.stat().st_size <= draft.MAX_BYTES)
    value = path.read_bytes()
    require(len(value) <= draft.MAX_BYTES)
    return value


def failed_context(json_file, paths, documents):
    """Require actual retained submitted bytes, never substitute new wire output."""
    require(set(documents) == {'preparation', 'submitted_wire', 'original_grant', 'original_proof',
                               'parent_packet', 'owner_proof', 'network_recovery_proof'})
    prepared = prepare(json_file, paths)
    require(prepared.source_id == SOURCE_ID)
    root = draft.state_root(paths)
    state = {
        'failed_journal': Path(paths.uploads_registry_path + '.modern-v1.json'),
        'create_intent': root / (SOURCE_ID + '.modern-create-v1.intent.json'),
        'legacy_registry': Path(paths.uploads_registry_path),
        'legacy_mutations': Path(paths.uploads_registry_path + '.mutations.json'),
    }
    all_paths = {**{k: Path(v) for k, v in documents.items()}, **state,
                 'prepared_input': Path(json_file)}
    before = {k: immutable_bytes(p, optional=k in ('legacy_registry', 'legacy_mutations'))
              for k, p in all_paths.items()}
    packet, journal, intent = (parse(before[k]) for k in ('preparation', 'failed_journal', 'create_intent'))
    require(set(packet) == {'binding', 'evidence', 'provider_requests'}
            and type(packet['provider_requests']) is int and packet['provider_requests'] == 0)
    approved_runtimes = (prepared.evidence['runtime_sha256'], publication.PR34_RUNTIME,
                         publication.PR35_RUNTIME, publication.PR36_RUNTIME, publication.PR37_RUNTIME,
                         publication.PR38_RUNTIME, publication.PR39_RUNTIME, publication.PR40_RUNTIME,
                         publication.PR41_RUNTIME, publication.PR42_RUNTIME, publication.PR43_RUNTIME,
                         publication.PR44_RUNTIME, publication.PR45_RUNTIME, publication.PR46_RUNTIME)
    evidence = packet['evidence']
    require(isinstance(evidence, dict) and evidence.get('runtime_sha256') in approved_runtimes
            and evidence == dict(prepared.evidence, runtime_sha256=evidence['runtime_sha256'])
            and packet['binding'] == sha(encode(evidence)))
    wire = before['submitted_wire']
    require(wire == prepared.body and sha(wire) == evidence['wire_sha256'])
    old = Prepared(SOURCE_ID, wire, prepared.xml, evidence, packet['binding'])
    require(set(journal) == {'schema_version', 'kind', 'targets'} and type(journal['schema_version']) is int and journal['schema_version'] == 1
            and journal['kind'] == 'modern-production-draft-attempts'
            and isinstance(journal['targets'], dict))
    row = journal['targets'].get(SOURCE_ID)
    require(isinstance(row, dict) and row.get('phase') == 'started' and row.get('identity') is None
            and row.get('untrusted_candidate_id') is None
            and row.get('binding') == old.binding
            and row.get('counts') == {'get': 0, 'create': 1, 'init': 0, 'content': 0, 'commit': 0}
            and all(type(v) is int for v in row['counts'].values())
            and isinstance(row.get('requests'), list) and len(row['requests']) == 1)
    request = row['requests'][0]
    require(isinstance(request, dict)
            and tuple(request.get(k) for k in ('kind', 'method', 'path', 'body_sha256', 'status'))
            == ('create', 'POST', '/api/records', sha(wire), 'uncertain')
            and type(request.get('http_status')) is int and request['http_status'] == 403)
    attempted = draft.instant(request.get('attempted_at'))
    old_grant, old_grant_sha = draft.authorize(old, paths, documents['original_grant'],
                                               documents['original_proof'], attempted)
    require(row.get('grant_sha256') == old_grant_sha and row.get('intent_sha256') == sha(before['create_intent'])
            and intent == {'schema_version': 1, 'binding': old.binding,
                           'grant_sha256': old_grant_sha, 'state_root': str(root)})
    # Opaque parent/owner/network packets are bound to the actual reviewed bytes;
    # their authenticity requires independent review, not invented JSON fields.
    require(all(isinstance(parse(before[k]), dict) and parse(before[k])
                for k in ('parent_packet', 'owner_proof', 'network_recovery_proof')))
    other_ids = set(str(i) for i in EXCLUDED | {v[0] for v in PROTECTED.values()})
    for role in ('legacy_registry', 'legacy_mutations'):
        data = parse(before[role]) if before[role] is not None else {}
        require(isinstance(data, dict))
        rows = data.get('targets', {}) if role == 'legacy_mutations' else data
        require(isinstance(rows, dict) and SOURCE_ID not in rows)
        for value in rows.values():
            if isinstance(value, dict) and value.get('deposition_id') is not None:
                other_ids.add(str(value['deposition_id']))
    for sid, value in journal['targets'].items():
        if sid == SOURCE_ID:
            continue
        require(isinstance(value, dict))
        if value.get('untrusted_candidate_id') is not None:
            other_ids.add(str(value['untrusted_candidate_id']))
        if isinstance(value.get('identity'), dict):
            other_ids.update(str(value['identity'].get(k)) for k in ('id', 'parent_id'))
    binding = {'source_id': SOURCE_ID, 'source_sha256': sha(prepared.xml), 'wire_sha256': sha(wire),
               'original_preparation_binding': old.binding, 'runtime_sha256': prepared.evidence['runtime_sha256'],
               'current_preparation_binding': prepared.binding,
               'state_root': str(root), 'owner': old_grant['owner'], 'failed_row_sha256': sha(encode(row)),
               'files': {k: sha(v) if v is not None else None for k, v in before.items()}}
    return {'prepared': old, 'current_prepared': prepared, 'binding': binding, 'binding_sha256': sha(encode(binding)),
            'paths': all_paths, 'before': before, 'original_grant': old_grant,
            'attempted_at': attempted, 'root': root, 'other_ids': other_ids}


def authorize(context, grant, now):
    require(set(grant) == {'schema_version', 'kind', 'approved', 'executor', 'origin', 'binding',
                           'limits', 'started_at', 'expires_at', 'reviewed_by', 'clock_skew_seconds',
                           'candidate_scope', 'read_only', 'no_create_replay', 'token_scope'})
    require(type(grant['schema_version']) is int and grant['schema_version'] == 1
            and grant['kind'] == 'modern-unknown-create-read-grant-v1'
            and grant['approved'] is True and grant['executor'] == draft.EXECUTOR
            and grant['origin'] == draft.ORIGIN and grant['binding'] == context['binding']
            and grant['limits'] == LIMITS and all(type(v) is int for v in grant['limits'].values())
            and grant['read_only'] is True and grant['no_create_replay'] is True
            and grant['candidate_scope'] == 'all_returned_owned_ids_including_protected_read_only'
            and grant['token_scope'] == 'deposit:write'
            and isinstance(grant['reviewed_by'], str) and grant['reviewed_by'].strip()
            and type(grant['clock_skew_seconds']) is int and 0 <= grant['clock_skew_seconds'] <= 60)
    start, end = draft.instant(grant['started_at']), draft.instant(grant['expires_at'])
    require(context['attempted_at'] <= start <= now < end and 0 < (end - start).total_seconds() <= 600)


def candidate_checks(data, candidate_id, context, skew_seconds):
    """A pure body comparison; even exact agreement never adopts an identity."""
    if not isinstance(data, dict):
        return {'modern_object': False}
    parent = data.get('parent') if isinstance(data.get('parent'), dict) else {}
    ownership = parent.get('access', {}).get('owned_by', {}) if isinstance(parent.get('access'), dict) else {}
    if not isinstance(ownership, dict):
        ownership = {}
    files = data.get('files') if isinstance(data.get('files'), dict) else {}
    checks = {
        'record_id': data.get('id') == candidate_id,
        'owner': ownership.get('user') == context['binding']['owner'],
        'draft_without_pid': data.get('is_published') is False and data.get('status') == 'draft'
            and data.get('pids') == {} and parent.get('pids', {}) == {} and data.get('doi') in (None, ''),
        'empty_files': files.get('enabled') is True and files.get('entries') == {}
            and type(files.get('count')) is int and files['count'] == 0
            and type(files.get('total_bytes')) is int and files['total_bytes'] == 0,
        'access': isinstance(data.get('access'), dict) and data['access'].get('record') == 'public'
            and data['access'].get('files') == 'restricted',
        'first_version': isinstance(data.get('versions'), dict)
            and type(data['versions'].get('index')) is int and data['versions']['index'] == 1,
        'no_existing_review': data.get('review') in (None, {}) and parent.get('review') in (None, {}),
        'revision': type(data.get('revision_id')) is int and data['revision_id'] >= 1,
        'links': isinstance(data.get('links'), dict)
            and data['links'].get('self') == draft.ORIGIN + '/api/records/' + candidate_id + '/draft'
            and data['links'].get('files') == draft.ORIGIN + '/api/records/' + candidate_id + '/draft/files',
    }
    try:
        parent_id = positive_id(parent.get('id'))
        competing_claims = set().union(*(claims for rid, claims in context.get('listed_claims', {}).items()
                                         if rid != candidate_id))
        checks['distinct_unclaimed_identity'] = (parent_id != candidate_id
            and not ({parent_id, candidate_id} & (context['other_ids'] | competing_claims)))
    except ValueError:
        checks['distinct_unclaimed_identity'] = False
    try:
        created = draft.instant(data.get('created'))
        skew = timedelta(seconds=skew_seconds)
        # attempted_at precedes fsync and transport dispatch. The original grant
        # expiry is a conservative bound, not an observed response timestamp.
        checks['conservative_attempt_window'] = (context['attempted_at'] - skew
            <= created <= draft.instant(context['original_grant']['expires_at']) + skew)
    except (ValueError, TypeError):
        checks['conservative_attempt_window'] = False
    try:
        compare_metadata(data.get('metadata'), parse(context['prepared'].body)['metadata'])
        checks['exact_original_metadata'] = True
    except (ValueError, TypeError, KeyError):
        checks['exact_original_metadata'] = False
    try:
        expected_empty_file_warning(data)
        checks['expected_empty_file_warning'] = True
    except (ValueError, TypeError, KeyError):
        checks['expected_empty_file_warning'] = False
    return checks


class Runner:
    def __init__(self, json_file, paths, documents, grant_path, token, transport=None, now=None):
        self.json_file, self.paths = Path(json_file), paths
        self.context = failed_context(json_file, paths, documents)
        self.grant_path = Path(grant_path)
        self.grant_raw = immutable_bytes(self.grant_path)
        self.grant, self.grant_sha = parse(self.grant_raw), sha(self.grant_raw)
        self.now = now or (lambda: datetime.now(timezone.utc))
        authorize(self.context, self.grant, self.now())
        require(isinstance(token, str) and 16 <= len(token) <= 4096
                and all(33 <= ord(c) <= 126 for c in token))
        require(not any(sensitive(raw, token) for raw in
                        (self.context['prepared'].body, self.context['prepared'].xml, self.grant_raw,
                         *(v for v in self.context['before'].values() if v is not None))))
        self.token = token
        self.transport = transport or draft.Transport(token)
        self.root = self.context['root']
        self.journal_path = self.root / (SOURCE_ID + '.modern-unknown-create-v1.json')
        self.intent_path = self.root / (SOURCE_ID + '.modern-unknown-create-v1.intent.json')
        self.deadline = time.monotonic() + 600
        self.journal = None

    def current(self):
        require(immutable_bytes(self.grant_path) == self.grant_raw)
        for role, path in self.context['paths'].items():
            require(immutable_bytes(path, optional=role in ('legacy_registry', 'legacy_mutations'))
                    == self.context['before'][role])
        current = prepare(self.json_file, self.paths)
        require(current == self.context['current_prepared'])
        authorize(self.context, self.grant, self.now())
        require(time.monotonic() < self.deadline)

    def save(self):
        # Only short references/checks enter this bounded journal. Raw captures
        # are separate exclusive files; no historical journal is modified.
        import json
        require(len((json.dumps(self.journal, indent=2, ensure_ascii=False) + '\n').encode()) <= draft.MAX_BYTES)
        atomic_json(self.journal_path, self.journal)

    def summarize(self):
        observations = self.journal['observations']
        observed = {row['record_id'] for row in observations}
        self.journal['unobserved_ids'] = [rid for rid in self.journal['listed_ids'] if rid not in observed]
        self.journal['exact_body_candidates'] = [row['record_id'] for row in observations
                                                  if row['exact_body_candidate']]
        # Every failed comparison/404 remains unresolved, never ruled absent.
        self.journal['unresolved_ids'] = [row['record_id'] for row in observations
                                           if not row['exact_body_candidate']] + self.journal['unobserved_ids']
        self.journal['multiple_exact_candidates'] = len(self.journal['exact_body_candidates']) > 1
        self.journal['observation_complete'] = (self.journal['legacy_terminal_observed']
            and self.journal['first_page_repeat_consistent'] and not self.journal['unobserved_ids'])

    @staticmethod
    def page_path(page):
        require(type(page) is int and 1 <= page <= LIMITS['pages'])
        return LIST_BASE + f'?page={page}&size=100&sort=mostrecent&all_versions=true'

    def get(self, path, *, page=None, repeat=False, candidate_id=None):
        self.current()
        require(self.journal is not None and self.journal['phase'] == 'started')
        if candidate_id is not None:
            require(page is None and not repeat and candidate_id in self.journal['listed_ids']
                    and path == '/api/records/' + positive_id(candidate_id) + '/draft')
            accept = draft.MIME
        else:
            require(path == self.page_path(page) and (not repeat or page == 1))
            if not repeat:
                require(page == self.journal['counts']['pages'] + 1)
                require(self.journal['counts']['pages'] < LIMITS['pages'])
                self.journal['counts']['pages'] += 1
            accept = 'application/json'
        require(self.journal['counts']['get'] < LIMITS['get'])
        self.journal['counts']['get'] += 1
        receipt = {'kind': 'get', 'method': 'GET', 'path': path, 'body_sha256': None,
                   'attempted_at': self.now().isoformat(), 'status': 'uncertain'}
        self.journal['requests'].append(receipt)
        self.save()
        self.current()
        remaining = min(draft.TIMEOUT, self.deadline - time.monotonic(),
                        (draft.instant(self.grant['expires_at']) - self.now()).total_seconds())
        require(remaining > 0)
        try:
            response = normalize_response(self.transport.request('GET', path, None,
                                                                  timeout=remaining, accept=accept))
        except Exception:
            raise Held('Read-only observation interrupted; GET attempt remains spent') from None
        evidence = draft.retain_response(self.journal_path, SOURCE_ID, self.grant_sha,
                                         len(self.journal['requests']) - 1, receipt, response,
                                         self.token, self.save)
        require(response.complete and not evidence['credential_suppressed'])
        # This cap counts received bodies. Base64 sidecars use up to 4/3 of
        # those bytes plus bounded JSON/diagnostic overhead, not 240MiB on disk.
        self.journal['received_body_bytes'] += len(response.body)
        require(self.journal['received_body_bytes'] <= LIMITS['get'] * draft.MAX_BYTES)
        if candidate_id is not None and response.status == 404:
            self.current()
            self.save()
            return None, receipt['response_sha256']
        require(response.status == 200 and draft.response_media_type(response.mime) == accept)
        # Full safe successful bodies, including >64KiB inventories, are retained
        # independently of bounded diagnostic previews before parsing/acceptance.
        raw_name = (self.journal_path.name + '.' + self.grant_sha + '.'
                    + str(len(self.journal['requests']) - 1) + '.raw.json')
        raw_packet = {'method': 'GET', 'path': path, 'http_status': response.status,
                      'content_type': response.mime, 'received_at': self.now().isoformat(),
                      'body_base64': base64.b64encode(response.body).decode(),
                      'response_sha256': sha(response.body)}
        draft.permanent_intent(self.root / raw_name, raw_packet)
        receipt['raw_evidence'] = {'filename': raw_name, 'sha256': sha(encode(raw_packet))}
        self.save()
        self.current()
        return parse(response.body), sha(response.body)

    def run(self):
        with ledger_lock(self.paths):
            self.current()
            # One canonical barrier per failed source. A new grant/recovery ID or
            # lost journal cannot reopen it. Explicit continuation is not added.
            require(not self.journal_path.exists() and not self.journal_path.is_symlink()
                    and not self.intent_path.exists() and not self.intent_path.is_symlink())
            intent = {'schema_version': 1, 'kind': KIND, 'binding_sha256': self.context['binding_sha256'],
                      'grant_sha256': self.grant_sha, 'state_root': str(self.root)}
            draft.permanent_intent(self.intent_path, intent)
            self.journal = {'schema_version': 1, 'kind': KIND, 'phase': 'started',
                            'binding': self.context['binding'], 'grant_sha256': self.grant_sha,
                            'intent_sha256': sha(encode(intent)), 'counts': {'get': 0, 'pages': 0},
                            'requests': [], 'received_body_bytes': 0, 'listed_ids': [], 'observations': [],
                            'unobserved_ids': [], 'unresolved_ids': [], 'exact_body_candidates': [],
                            'multiple_exact_candidates': False, 'observation_complete': False,
                            'legacy_terminal_observed': False, 'first_page_repeat_consistent': False,
                            'original_create_spent': True, 'replay_authorized': False,
                            'identity_adoption_authorized': False, 'modern_inventory_coverage_proven': False,
                            'provider_mutation_authorized': False, 'modern_create_outcome': 'unresolved'}
            self.save()
            try:
                self.context['listed_claims'] = {}
                for page in range(1, LIMITS['pages'] + 1):
                    data, body_sha = self.get(self.page_path(page), page=page)
                    require(isinstance(data, list) and len(data) <= 100)
                    if page == 1:
                        self.journal['first_page_sha256'] = body_sha
                    if not data:
                        self.journal['legacy_terminal_observed'] = True
                        self.save()
                        break
                    for item in data:
                        require(isinstance(item, dict) and type(item.get('id')) is int
                                and item['id'] > 0 and len(str(item['id'])) <= 20
                                and type(item.get('owner')) is int
                                and str(item['owner']) == self.context['binding']['owner'])
                        rid = str(item['id'])
                        require(rid not in self.journal['listed_ids'])
                        self.journal['listed_ids'].append(rid)
                        claims = {rid}
                        if item.get('record_id') is not None:
                            require(type(item['record_id']) is int)
                            claims.add(positive_id(str(item['record_id'])))
                        if item.get('conceptrecid') is not None:
                            claims.add(positive_id(item['conceptrecid']))
                        self.context['listed_claims'][rid] = claims
                    self.save()
                require(self.journal['legacy_terminal_observed'])
                # Observe every returned ID, including fileless/unknown/old rows.
                # Title, timestamps or missing descriptors never veto a candidate.
                for rid in self.journal['listed_ids']:
                    if self.journal['counts']['get'] >= LIMITS['get'] - 1:
                        break  # Reserve the final page-1 repeat; report all unobserved IDs.
                    data, body_sha = self.get('/api/records/' + rid + '/draft', candidate_id=rid)
                    checks = ({'draft_endpoint_available': False} if data is None else
                              candidate_checks(data, rid, self.context, self.grant['clock_skew_seconds']))
                    self.journal['observations'].append({'record_id': rid, 'response_sha256': body_sha,
                                                         'parent_id': data.get('parent', {}).get('id')
                                                         if isinstance(data, dict) and isinstance(data.get('parent'), dict) else None,
                                                         'checks': checks, 'exact_body_candidate': all(checks.values())})
                    # Shared modern parent claims make both observations
                    # indeterminate even if no legacy concept ID was supplied.
                    parent_id = self.journal['observations'][-1]['parent_id']
                    if isinstance(parent_id, str):
                        same_parent = [row for row in self.journal['observations'] if row['parent_id'] == parent_id]
                        if len(same_parent) > 1:
                            for row in same_parent:
                                row['checks']['distinct_unclaimed_identity'] = False
                                row['exact_body_candidate'] = False
                    self.summarize()
                    self.save()
                _, repeated_sha = self.get(self.page_path(1), page=1, repeat=True)
                require(repeated_sha == self.journal['first_page_sha256'])
                self.journal['first_page_repeat_consistent'] = True
                self.summarize()
                self.current()
                self.journal['phase'] = ('held' if self.journal['unresolved_ids']
                    or self.journal['multiple_exact_candidates'] or not self.journal['observation_complete'] else 'captured')
                if self.journal['phase'] == 'held':
                    self.journal['hold_reason'] = 'Observation incomplete or candidates unresolved; no create outcome established'
                self.journal['scope'] = 'Bounded legacy-owned observations; modern absence and causality unproven'
                self.save()
                return self.journal
            except Exception:
                self.summarize()
                self.journal['phase'] = 'held'
                self.journal['hold_reason'] = 'Observation incomplete; retain original create and all spent GET attempts'
                self.save()
                raise Held('Read-only observations held; original create and GET attempts remain spent') from None


def main():
    parser = argparse.ArgumentParser(description='Bounded GET-only observations for spent FGDC-141 create')
    parser.add_argument('action', choices=('preflight', 'observe'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--json-file', required=True, type=Path)
    for role in ('preparation', 'submitted_wire', 'original_grant', 'original_proof',
                 'parent_packet', 'owner_proof', 'network_recovery_proof'):
        parser.add_argument('--' + role.replace('_', '-'), required=True, type=Path)
    parser.add_argument('--grant', type=Path)
    args = parser.parse_args()
    paths = OutputPaths(str(args.output), 'production')
    documents = {role: getattr(args, role) for role in ('preparation', 'submitted_wire', 'original_grant',
                 'original_proof', 'parent_packet', 'owner_proof', 'network_recovery_proof')}
    try:
        context = failed_context(args.json_file, paths, documents)
        if args.action == 'preflight':
            print(encode({'binding': context['binding'], 'binding_sha256': context['binding_sha256'],
                          'limits': LIMITS, 'provider_requests': 0, 'approved': False,
                          'replay_authorized': False, 'modern_create_outcome': 'unresolved'}).decode())
            return
        require(args.grant is not None and platform.system() == 'Darwin' and sys.stdin.isatty())
        grant, _ = draft.read_document(args.grant)
        authorize(context, grant, datetime.now(timezone.utc))
        token = getpass.getpass('Production token for bounded GET-only observation: ')
        runner = Runner(args.json_file, paths, documents, args.grant, token)
        result = runner.run()
        print(encode({'phase': result['phase'], 'counts': result['counts'],
                      'exact_body_candidates': result.get('exact_body_candidates', []),
                      'unobserved_ids': result.get('unobserved_ids', []),
                      'unresolved_ids': result.get('unresolved_ids', []),
                      'multiple_exact_candidates': result.get('multiple_exact_candidates', False),
                      'observation_complete': result.get('observation_complete', False),
                      'modern_create_outcome': 'unresolved', 'replay_authorized': False,
                      'identity_adoption_authorized': False}).decode())
        if result['phase'] == 'held':
            raise SystemExit(2)
    except BaseException:
        print('Read-only observations held; preserve original create and all spent GET attempts', file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == '__main__':
    main()
