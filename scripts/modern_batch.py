"""Batch manifests for the modern singleton chain: finite membership, twins and exclusions.

Purpose: build and validate `modern-batch-v1` manifests (ADR 0012) offline. A manifest
pins, per member, the preparation binding the executor demands, so one batch grant can
cover many records without weakening the per-record contract.
Invariants: members are distinct prepared singletons under one runtime; byte-identical
sources never share a batch or follow an attempted twin; equal or contained core titles
need a reviewed allowance (from the command line or the allowance registry under the
state root); validation re-derives every member, the attempted set and every twin from
the live preparation and journal, so any drift holds.
Assumptions: prepared inputs exist under the output root for every member and every
journal row; the original XML lives under the repository's FGDC directory; nothing here
makes a provider request.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts import modern_singleton_executor as draft
from scripts.modern_singleton import (
    ROOT,
    Held,
    canonical_text,
    encode,
    parse,
    prepare,
    require,
    runtime_binding,
    sha,
)
from scripts.path_config import OutputPaths

MANIFEST_KIND = 'modern-batch-v1'
ALLOWANCE_KIND = 'modern-twin-allowance-v1'
STAGES = ('drafts',)
BATCH_ID = r'[a-z0-9][a-z0-9-]{2,63}'
SOURCE_ID = r'FGDC-[1-9][0-9]*'
MAX_MEMBERS = 250
CONTAINMENT_MIN = 40  # a shorter contained title is a weak signal, not a twin
ARTIFACT_SUFFIX = ' - FGDC XML metadata artifact'  # appended to every artifact title by collection_qa
MEMBER_KEYS = {'index', 'source_id', 'policy', 'schema_version', 'source_sha256', 'wire_sha256',
               'binding', 'title_key', 'journal_phase'}
ALLOWANCE_KEYS = {'sources', 'allowed_by', 'note', 'origin'}
REGISTRY_KEYS = {'schema_version', 'kind', 'sources', 'allowed_by', 'note', 'decided_at'}
EXCLUSION_KEYS = {'source_id', 'reason'}
MANIFEST_KEYS = {'schema_version', 'kind', 'batch_id', 'stage', 'origin', 'owner', 'state_root', 'built_at',
                 'built_by', 'runtime_sha256', 'member_count', 'members', 'membership_sha256',
                 'attempted_count', 'attempted_sha256', 'twins', 'allowances', 'exclusions'}


def utc_now():
    return datetime.now(timezone.utc)


def by_number(source_id):
    return int(source_id[5:])


def title_key(title):
    """Case-folded, whitespace-normalised core title in the provider's stored form.

    The constant artifact suffix is dropped so one source's core title can be found
    inside another's; the inventory matcher keeps it because it looks for exact copies.
    """
    text = canonical_text(str(title))
    if text.endswith(ARTIFACT_SUFFIX):
        text = text[:-len(ARTIFACT_SUFFIX)]
    return ' '.join(text.casefold().split())


def batches_dir(paths):
    return draft.state_root(paths) / 'batches'


def manifest_path(paths, batch_id):
    return batches_dir(paths) / (batch_id + '.manifest.json')


def allowances_dir(paths):
    return batches_dir(paths) / 'allowances'


def journal_phases(paths):
    """Source id to phase for every row of the modern journal; empty when there is none."""
    journal_path = Path(paths.uploads_registry_path + '.modern-v1.json')
    if not journal_path.exists():
        return {}
    journal, _ = draft.read_document(journal_path)
    require(isinstance(journal.get('targets'), dict))
    phases = {}
    for source_id, row in journal['targets'].items():
        require(isinstance(row, dict) and re.fullmatch(SOURCE_ID, source_id) is not None
                and isinstance(row.get('phase'), str))
        phases[source_id] = row['phase']
    return phases


def prepared_input(paths, source_id):
    path = Path(paths.zenodo_json_dir) / (source_id + '.json')
    require(re.fullmatch(SOURCE_ID, source_id) is not None and path.is_file())
    return path


def member_facts(source_id, paths, phases):
    """What a batch pins for one source: its live preparation binding and the twin keys."""
    prepared = prepare(str(prepared_input(paths, source_id)), paths)
    require(prepared.source_id == source_id)
    evidence = prepared.evidence
    return {'source_id': source_id, 'policy': evidence['policy'], 'schema_version': evidence['schema_version'],
            'source_sha256': evidence['source_sha256'], 'wire_sha256': evidence['wire_sha256'],
            'binding': prepared.binding,
            'title_key': title_key(parse(prepared.body)['metadata']['title']),
            'journal_phase': phases.get(source_id)}


def attempted_facts(paths, phases, members):
    """Twin keys of every journal source outside the batch; a row without its input holds."""
    facts = []
    for source_id in sorted(set(phases) - set(members), key=by_number):
        document, _ = draft.read_document(prepared_input(paths, source_id))
        require(isinstance(document, dict) and isinstance(document.get('metadata'), dict))
        title = document['metadata'].get('title')
        require(isinstance(title, str) and title.strip())
        xml_path = ROOT / 'FGDC' / (source_id + '.xml')
        require(xml_path.is_file())
        facts.append({'source_id': source_id, 'source_sha256': sha(xml_path.read_bytes()),
                      'title_key': title_key(title)})
    return facts


def attempted_sha256(attempted):
    return sha(encode([fact['source_id'] for fact in attempted]))


def twin_findings(facts, others=()):
    """Pairs that may describe one record: identical sources (hard) or shared titles (soft).

    Pairs inside `facts` and between `facts` and `others` are compared; pairs inside
    `others` (the attempted sources) are not this batch's concern.
    """
    findings = []
    others = list(others)
    for position, left in enumerate(facts):
        for right in facts[position + 1:] + others:
            pair = sorted((left['source_id'], right['source_id']), key=by_number)
            if left['source_sha256'] == right['source_sha256']:
                findings.append({'pair': pair, 'kind': 'identical_source', 'hard': True})
            elif left['title_key'] == right['title_key']:
                findings.append({'pair': pair, 'kind': 'same_title', 'hard': False})
            else:
                shorter, longer = sorted((left['title_key'], right['title_key']), key=len)
                if len(shorter) >= CONTAINMENT_MIN and shorter in longer:
                    findings.append({'pair': pair, 'kind': 'title_contained', 'hard': False})
    return findings


def normalise_allowance(entry, origin):
    """One reviewed decision that the named sources are distinct records despite their titles."""
    require(isinstance(entry, dict) and {'sources', 'allowed_by', 'note'} <= set(entry) <= ALLOWANCE_KEYS)
    sources = entry['sources']
    require(isinstance(sources, list) and len(sources) >= 2 and len(set(sources)) == len(sources)
            and all(isinstance(sid, str) and re.fullmatch(SOURCE_ID, sid) for sid in sources)
            and sources == sorted(sources, key=by_number)
            and isinstance(entry['allowed_by'], str) and entry['allowed_by'].strip()
            and isinstance(entry['note'], str))
    origin = entry.get('origin', origin)
    require(isinstance(origin, str) and origin.strip())
    return {'sources': list(sources), 'allowed_by': entry['allowed_by'], 'note': entry['note'], 'origin': origin}


def allowance_pairs(allowance):
    sources = allowance['sources']
    return {tuple(sorted((left, right), key=by_number))
            for position, left in enumerate(sources) for right in sources[position + 1:]}


def load_registry(paths):
    """Every reviewed allowance recorded under the state root, by file name."""
    directory = allowances_dir(paths)
    if not directory.is_dir():
        return []
    entries = []
    for path in sorted(directory.glob('*.json')):
        document, _ = draft.read_document(path)
        require(isinstance(document, dict) and set(document) == REGISTRY_KEYS
                and type(document['schema_version']) is int and document['schema_version'] == 1
                and document['kind'] == ALLOWANCE_KIND)
        draft.instant(document['decided_at'])
        entries.append(normalise_allowance({k: document[k] for k in ('sources', 'allowed_by', 'note')},
                                           'registry:' + path.name))
    return entries


def record_allowance(paths, name, sources, allowed_by, note, now=utc_now):
    """Write one reviewed allowance to the registry; an existing name is never replaced."""
    require(isinstance(name, str) and re.fullmatch(BATCH_ID, name) is not None)
    entry = normalise_allowance({'sources': sorted(sources, key=by_number), 'allowed_by': allowed_by, 'note': note},
                                'registry:' + name + '.json')
    document = {'schema_version': 1, 'kind': ALLOWANCE_KIND, 'sources': entry['sources'],
                'allowed_by': entry['allowed_by'], 'note': entry['note'], 'decided_at': now().isoformat()}
    directory = allowances_dir(paths)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + '.json')
    draft.permanent_intent(path, document)
    return path


def resolve_twins(member_facts_list, attempted, required, optional=()):
    """Hard twins hold; soft twins need an allowance; a required allowance must match a twin.

    `required` allowances come from the command line or a manifest being re-validated and
    must each cover at least one twin of this batch; `optional` ones are the registry, which
    may name sources this batch never meets. Returns the twins and the allowances used.
    """
    relevant = twin_findings(member_facts_list, attempted)
    members = {fact['source_id'] for fact in member_facts_list}
    known = members | {fact['source_id'] for fact in attempted}
    hard = [finding['pair'] for finding in relevant if finding['hard']]
    if hard:
        raise Held('Identical sources in or against the batch: ' + json.dumps(hard))
    soft = {tuple(finding['pair']) for finding in relevant if not finding['hard']}
    used, covered = [], set()
    for allowance in list(required):
        require(set(allowance['sources']) <= known)
        matched = allowance_pairs(allowance) & soft
        if not matched:
            raise Held('Allowance matches no twin of this batch: ' + json.dumps(allowance['sources']))
        used.append(allowance)
        covered |= matched
    for allowance in list(optional):
        matched = allowance_pairs(allowance) & soft
        if matched:
            used.append(allowance)
            covered |= matched
    unallowed = sorted(soft - covered)
    if unallowed:
        raise Held('Title twins without a reviewed allowance: ' + json.dumps(unallowed))
    twins = [{'pair': list(finding['pair']), 'kind': finding['kind']} for finding in relevant]
    return twins, used


def check_exclusions(exclusions, ids):
    exclusions = list(exclusions)
    require(all(isinstance(e, dict) and set(e) == EXCLUSION_KEYS and isinstance(e['source_id'], str)
                and re.fullmatch(SOURCE_ID, e['source_id']) and isinstance(e['reason'], str) and e['reason'].strip()
                for e in exclusions))
    excluded = {e['source_id'] for e in exclusions}
    require(len(excluded) == len(exclusions) and not (excluded & set(ids)))
    return exclusions


def check_header(batch_id, stage, owner, built_by):
    require(isinstance(batch_id, str) and re.fullmatch(BATCH_ID, batch_id) is not None and stage in STAGES
            and isinstance(owner, str) and re.fullmatch('[1-9][0-9]{0,19}', owner) is not None
            and isinstance(built_by, str) and built_by.strip())


def build_manifest(paths, source_ids, *, batch_id, owner, built_by, stage='drafts', allowances=(),
                   exclusions=(), now=utc_now, registry=True):
    """Assemble the manifest offline; every member binding is the live preparation's."""
    check_header(batch_id, stage, owner, built_by)
    ids = list(source_ids)
    require(0 < len(ids) <= MAX_MEMBERS and len(set(ids)) == len(ids)
            and all(isinstance(sid, str) and re.fullmatch(SOURCE_ID, sid) for sid in ids))
    exclusions = check_exclusions(exclusions, ids)
    phases = journal_phases(paths)
    facts = [member_facts(sid, paths, phases) for sid in ids]
    attempted = attempted_facts(paths, phases, ids)
    # A command-line decision is recorded as such; only the registry confers registry provenance.
    required = [normalise_allowance({k: v for k, v in entry.items() if k != 'origin'}, 'cli') for entry in allowances]
    twins, used = resolve_twins(facts, attempted, required, load_registry(paths) if registry else [])
    members = [dict(fact, index=index) for index, fact in enumerate(facts)]
    require(all(set(member) == MEMBER_KEYS for member in members))
    return {'schema_version': 1, 'kind': MANIFEST_KIND, 'batch_id': batch_id, 'stage': stage,
            'origin': draft.ORIGIN, 'owner': owner, 'state_root': str(draft.state_root(paths)),
            'built_at': now().isoformat(), 'built_by': built_by, 'runtime_sha256': runtime_binding(),
            'member_count': len(members), 'members': members,
            'membership_sha256': membership_sha256(members),
            'attempted_count': len(attempted), 'attempted_sha256': attempted_sha256(attempted),
            'twins': twins, 'allowances': used, 'exclusions': exclusions}


def membership_sha256(members):
    return sha(encode([[member['source_id'], member['binding']] for member in members]))


def write_manifest(paths, document):
    """Exclusive write under the state root; an existing manifest is never replaced."""
    path = manifest_path(paths, document['batch_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    draft.permanent_intent(path, document)
    return path


def validate_manifest(path, paths):
    """Re-derive members, the attempted set and the twins; any drift or runtime change holds."""
    document, document_sha = draft.read_document(path)
    require(isinstance(document, dict) and set(document) == MANIFEST_KEYS
            and type(document['schema_version']) is int and document['schema_version'] == 1
            and document['kind'] == MANIFEST_KIND and document['origin'] == draft.ORIGIN
            and document['state_root'] == str(draft.state_root(paths))
            and document['runtime_sha256'] == runtime_binding()
            and isinstance(document['members'], list) and document['members']
            and len(document['members']) <= MAX_MEMBERS
            and document['member_count'] == len(document['members'])
            and isinstance(document['twins'], list) and isinstance(document['allowances'], list))
    check_header(document['batch_id'], document['stage'], document['owner'], document['built_by'])
    draft.instant(document['built_at'])
    ids = [member['source_id'] for member in document['members'] if isinstance(member, dict)]
    require(len(ids) == len(document['members']) and len(set(ids)) == len(ids))
    check_exclusions(document['exclusions'], ids)
    phases = journal_phases(paths)
    facts = []
    for index, member in enumerate(document['members']):
        require(set(member) == MEMBER_KEYS and member['index'] == index)
        live = member_facts(member['source_id'], paths, phases)
        require({k: v for k, v in member.items() if k not in ('journal_phase', 'index')}
                == {k: v for k, v in live.items() if k != 'journal_phase'})
        facts.append(live)
    require(document['membership_sha256'] == membership_sha256(document['members']))
    attempted = attempted_facts(paths, phases, ids)
    require(document['attempted_count'] == len(attempted)
            and document['attempted_sha256'] == attempted_sha256(attempted))
    required = [normalise_allowance(entry, 'manifest') for entry in document['allowances']]
    twins, used = resolve_twins(facts, attempted, required)
    require(twins == document['twins'] and used == required)
    return document, document_sha


def parse_sources(value):
    sources = value.split(',')
    require(len(sources) >= 2 and all(re.fullmatch(SOURCE_ID, sid) for sid in sources)
            and len(set(sources)) == len(sources))
    return sorted(sources, key=by_number)


def parse_exclusion(value):
    source_id, _, reason = value.partition(':')
    require(re.fullmatch(SOURCE_ID, source_id) is not None and reason.strip())
    return {'source_id': source_id, 'reason': reason.strip()}


def members_from_file(path):
    document, _ = draft.read_document(path)
    rows = document['members'] if isinstance(document, dict) else document
    require(isinstance(rows, list))
    return [row['source_id'] if isinstance(row, dict) else row for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    build = sub.add_parser('build', help='Build a batch manifest offline')
    build.add_argument('--output-dir', required=True)
    build.add_argument('--batch-id', required=True)
    build.add_argument('--owner', required=True)
    build.add_argument('--built-by', required=True)
    build.add_argument('--stage', default='drafts', choices=STAGES)
    build.add_argument('--member', action='append', default=[], help='Source id; repeatable')
    build.add_argument('--members-file', help='JSON list of ids, or a policy list with members[].source_id')
    build.add_argument('--allow', action='append', default=[], metavar='FGDC-A,FGDC-B[,FGDC-C]',
                       help='Reviewed title-twin allowance for this build only; needs --allowed-by')
    build.add_argument('--allowed-by', default='', help='Who decided the --allow entries and where')
    build.add_argument('--allow-note', default='', help='Note recorded with every --allow entry')
    build.add_argument('--exclude', action='append', default=[], metavar='FGDC-N:reason',
                       help='Source deferred from this batch with its reason')
    validate = sub.add_parser('validate', help='Re-derive a manifest against the live preparation and journal')
    validate.add_argument('--output-dir', required=True)
    validate.add_argument('--manifest', required=True)
    allow = sub.add_parser('allow', help='Record a reviewed twin allowance in the registry')
    allow.add_argument('--output-dir', required=True)
    allow.add_argument('--name', required=True, help='Registry entry name, e.g. cccc-workshop-1997')
    allow.add_argument('--sources', required=True, metavar='FGDC-A,FGDC-B[,FGDC-C]')
    allow.add_argument('--allowed-by', required=True)
    allow.add_argument('--note', required=True)
    args = parser.parse_args()
    try:
        paths = OutputPaths(args.output_dir, 'production')
        if args.action == 'build':
            ids = list(args.member) + (members_from_file(args.members_file) if args.members_file else [])
            require(not args.allow or args.allowed_by.strip())
            allowances = [{'sources': parse_sources(v), 'allowed_by': args.allowed_by, 'note': args.allow_note}
                          for v in args.allow]
            document = build_manifest(paths, ids, batch_id=args.batch_id, owner=args.owner,
                                      built_by=args.built_by, stage=args.stage, allowances=allowances,
                                      exclusions=[parse_exclusion(v) for v in args.exclude])
            path = write_manifest(paths, document)
            result = {'manifest': str(path), 'manifest_sha256': sha(path.read_bytes()),
                      'membership_sha256': document['membership_sha256'], 'member_count': document['member_count'],
                      'attempted_count': document['attempted_count'], 'twins': document['twins'],
                      'allowances_used': [a['origin'] for a in document['allowances']],
                      'journal_phases': {m['source_id']: m['journal_phase'] for m in document['members']
                                         if m['journal_phase']},
                      'provider_requests': 0}
        elif args.action == 'validate':
            document, document_sha = validate_manifest(args.manifest, paths)
            result = {'manifest_sha256': document_sha, 'membership_sha256': document['membership_sha256'],
                      'member_count': document['member_count'], 'attempted_count': document['attempted_count'],
                      'valid': True, 'provider_requests': 0}
        else:
            path = record_allowance(paths, args.name, parse_sources(args.sources), args.allowed_by, args.note)
            result = {'allowance': str(path), 'allowance_sha256': sha(path.read_bytes()), 'provider_requests': 0}
        print(encode(result).decode())
        return 0
    except Held as held:
        print(json.dumps({'held': True, 'reason': str(held)}))
        return 1
    except FileExistsError:
        print(json.dumps({'held': True, 'reason': 'a document with that name already exists; nothing was replaced'}))
        return 1
    except BaseException:
        print(json.dumps({'held': True, 'reason': 'Modern batch manifest held; nothing was written'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
