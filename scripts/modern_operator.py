"""Operator toolkit for the finite modern production chain.

Purpose: capture the owner's current record inventory through the production
transport, and mint the reviewed create grant and duplicate proof that the
draft executor requires, so records move one at a time without hand-written
JSON. Invariants: bounded listing and detail GETs, no retries or redirects, no
token in any output, grants never longer than 600 seconds, exclusive output
files, rollback of a half-minted pair, and no provider write. Assumptions: the
executor's preparation, state root and authorize() contract are the source of
truth; any inventory match for the source, or a record whose files cannot be
seen, refuses minting and leaves adjudication to a reviewer. The legacy
listing's coverage of RDM drafts is not proven; drafts created by this chain
are known through the journal, which the executor checks before every write.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import modern_singleton_executor as draft
from scripts.modern_response_evidence import sensitive
from scripts.modern_singleton import Held, encode, parse, prepare, require, sha
from scripts.path_config import OutputPaths
from scripts.production_mutations import EXCLUDED, PROTECTED

LIST_PATH = '/api/deposit/depositions'
PAGE_SIZE = 50
MAX_PAGES = 100
MAX_DETAILS = 25
PACE_SECONDS = 0.5
INVENTORY_KIND = 'modern-owner-inventory-v1'
INVENTORY_MAX_AGE = timedelta(minutes=50)
SOURCE_MENTION = re.compile(r'(?<![A-Za-z0-9])FGDC[-_\s]*0*([1-9][0-9]*)(?![0-9])', re.IGNORECASE)
HEX_LITERAL = re.compile(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])')
HELD = '{"held":true,"instruction":"Preserve all evidence; nothing was written to the provider"}'


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def listing_path(page):
    require(type(page) is int and page >= 1)
    return f'{LIST_PATH}?page={page}&size={PAGE_SIZE}&sort=mostrecent&all_versions=true'


def detail_path(record_id):
    require(isinstance(record_id, str) and re.fullmatch('[1-9][0-9]{0,19}', record_id) is not None)
    return LIST_PATH + '/' + record_id


def write_exclusive(path, raw):
    """Exclusive, mode 0600, fsynced raw bytes; existing files are never replaced."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def summarize(record, detail=None):
    """Keep what duplicate matching needs: names, checksums, sizes, owner, mentions, digests."""
    require(isinstance(record, dict) and type(record.get('id')) is int and record['id'] > 0)
    require(detail is None or (isinstance(detail, dict) and detail.get('id') == record['id']))
    files = record.get('files') if isinstance(record.get('files'), list) else []
    source = 'listing' if files else 'none'
    if not files and detail is not None:
        files = detail.get('files') if isinstance(detail.get('files'), list) else []
        source = 'detail' if files else 'none'
    text = json.dumps(record, sort_keys=True) + ('' if detail is None else json.dumps(detail, sort_keys=True))
    entries = []
    for item in files:
        require(isinstance(item, dict))
        checksum = str(item.get('checksum') or '').lower()
        entries.append({'name': str(item.get('filename') or item.get('key') or ''),
                        'md5': checksum[4:] if checksum.startswith('md5:') else checksum,
                        'size': item.get('filesize', item.get('size'))})
    metadata = record.get('metadata') if isinstance(record.get('metadata'), dict) else {}
    return {'id': str(record['id']), 'owner': record.get('owner'),
            'title': ' '.join(str(record.get('title') or metadata.get('title') or '').split()),
            'files': entries, 'files_source': source,
            'mentions': sorted({'FGDC-' + str(int(found)) for found in SOURCE_MENTION.findall(text)}),
            'sha256_literals': sorted(set(HEX_LITERAL.findall(text.lower()))),
            'doi': record.get('doi'), 'state': record.get('state'), 'submitted': record.get('submitted')}


def fetch_json(transport, token, path):
    """One bounded GET; a hold names the stage and status but never the body."""
    response = draft.normalize_response(
        transport.request('GET', path, None, timeout=draft.TIMEOUT, accept='application/json'))
    media = draft.response_media_type(response.mime) if isinstance(response.mime, str) and response.mime else ''
    if not (response.complete and response.status == 200 and media == 'application/json'):
        raise Held(f'inventory fetch held at {path}: status {response.status}, media {media or "none"}, '
                   f'complete {response.complete}')
    if sensitive(response.body, token):
        raise Held(f'inventory fetch held at {path}: response screened as credential-bearing; not retained')
    return response.body, parse(response.body)


def capture_inventory(transport, token, evidence_dir, captured_by, *, max_pages=MAX_PAGES,
                      max_details=MAX_DETAILS, now=utc_now, pace=PACE_SECONDS):
    """GET the owner's listing until an empty page, then details for records that list no files.

    Raw responses are retained as `.partial` files until the capture completes,
    so an interrupted capture never looks like an inventory.
    """
    require(isinstance(captured_by, str) and captured_by.strip()
            and 1 <= max_pages <= MAX_PAGES and 0 <= max_details <= MAX_DETAILS)
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    started = now()
    stamp = started.strftime('%Y%m%dT%H%M%SZ') + '-' + os.urandom(3).hex()
    retained = []

    def retain(name, raw):
        final = evidence_dir / name
        require(not final.exists())
        temp = evidence_dir / (name + '.partial')
        write_exclusive(temp, raw)
        retained.append((temp, final))

    pages, items = [], []
    for page in range(1, max_pages + 1):
        path = listing_path(page)
        if page > 1 and pace:
            time.sleep(pace)
        raw, listing = fetch_json(transport, token, path)
        require(isinstance(listing, list) and len(listing) <= PAGE_SIZE
                and all(isinstance(i, dict) and type(i.get('id')) is int and i['id'] > 0 for i in listing))
        name = f'inventory-{stamp}.page-{page}.json'
        retain(name, raw)
        pages.append({'page': page, 'path': path, 'http_status': 200, 'count': len(listing),
                      'response_sha256': sha(raw), 'raw': name})
        items.extend(listing)
        if not listing:
            break
    else:
        raise Held('Inventory exceeded the page bound; it is not complete')
    require(len({item['id'] for item in items}) == len(items))
    missing = [item for item in items if not (isinstance(item.get('files'), list) and item['files'])]
    require(len(missing) <= max_details)
    details, detail_by_id = [], {}
    for item in missing:
        record_id = str(item['id'])
        if pace:
            time.sleep(pace)
        raw, detail = fetch_json(transport, token, detail_path(record_id))
        require(isinstance(detail, dict) and detail.get('id') == item['id'])
        name = f'inventory-{stamp}.detail-{record_id}.json'
        retain(name, raw)
        details.append({'id': record_id, 'path': detail_path(record_id), 'response_sha256': sha(raw), 'raw': name})
        detail_by_id[item['id']] = detail
    records = [summarize(item, detail_by_id.get(item['id'])) for item in items]
    document = {'schema_version': 1, 'kind': INVENTORY_KIND, 'origin': draft.ORIGIN,
                'captured_by': captured_by, 'captured_at': started.isoformat(),
                'completed_at': now().isoformat(), 'page_size': PAGE_SIZE,
                'pages': pages, 'details': details, 'complete': True,
                'record_count': len(records), 'records': records}
    if len(encode(document)) > draft.MAX_BYTES:
        raise Held('inventory summary exceeds the 1 MiB document bound; receipts stay partial')
    for temp, final in retained:
        os.link(temp, final)  # fails rather than replacing an existing receipt
        os.unlink(temp)
    out = evidence_dir / f'inventory-{stamp}.json'
    draft.permanent_intent(out, document)
    return out, document


def known_records(paths, extra=()):
    """Records whose files need no listing evidence: protected, excluded, or created by this chain."""
    known = {str(value[0]) for value in PROTECTED.values()} | {str(i) for i in EXCLUDED} | {str(i) for i in extra}
    journal_path = Path(paths.uploads_registry_path + '.modern-v1.json')
    if journal_path.exists():
        journal, _ = draft.read_document(journal_path)
        for row in journal.get('targets', {}).values():
            if not isinstance(row, dict):
                continue
            if isinstance(row.get('identity'), dict):
                known.update(str(row['identity'].get(key)) for key in ('id', 'parent_id'))
            if row.get('untrusted_candidate_id') is not None:
                known.add(str(row['untrusted_candidate_id']))
    return known


def inventory_matches(records, source_id, title, xml, known=frozenset()):
    """Every owned record that could already carry this source; any hit refuses minting."""
    key = ' '.join(title.casefold().split())
    md5 = hashlib.md5(xml, usedforsecurity=False).hexdigest()
    digest = sha(xml)
    file_name = (source_id + '.xml').casefold()
    hits = []
    for record in records:
        reasons = []
        files = record.get('files', [])
        if ' '.join(str(record.get('title', '')).casefold().split()) == key:
            reasons.append('title')
        if any(str(item.get('name', '')).casefold() == file_name for item in files):
            reasons.append('file')
        if any(str(item.get('md5', '')).lower() == md5 for item in files):
            reasons.append('md5')
        if digest in record.get('sha256_literals', []):
            reasons.append('sha256')
        if source_id in record.get('mentions', []):
            reasons.append('source_id')
        if record.get('files_source') == 'none' and str(record.get('id')) not in known:
            reasons.append('files_unverified')
        if reasons:
            hits.append({'id': record.get('id'), 'reasons': reasons})
    return hits


def rebuild_records(inventory_path, inventory):
    """Re-derive the summary from the hashed raw receipts; an edited summary cannot pass."""
    items, details = [], {}
    for index, page in enumerate(inventory['pages'], start=1):
        raw = (inventory_path.parent / page['raw']).read_bytes()
        require(page.get('page') == index and sha(raw) == page['response_sha256'])
        listing = parse(raw)
        require(isinstance(listing, list) and len(listing) == page.get('count'))
        items.extend(listing)
    for receipt in inventory['details']:
        raw = (inventory_path.parent / receipt['raw']).read_bytes()
        require(sha(raw) == receipt['response_sha256'])
        detail = parse(raw)
        require(isinstance(detail, dict) and str(detail.get('id')) == receipt.get('id'))
        details[detail['id']] = detail
    return [summarize(item, details.get(item['id'])) for item in items]


def source_already_attempted(paths, source_id):
    root = draft.state_root(paths)
    if (root / (source_id + '.modern-create-v1.intent.json')).exists():
        return True
    for suffix, key in (('.modern-v1.json', 'targets'), ('.mutations.json', 'targets'), ('', None)):
        path = Path(paths.uploads_registry_path + suffix)
        if path.exists():
            document = draft.read_document(path)[0]
            rows = document.get(key, {}) if key else document
            if isinstance(rows, dict) and source_id in rows:
                return True
    return False


def mint_create(json_file, paths, inventory_path, owner, reviewer, canary_receipt_sha256,
                grant_out, proof_out, *, window=600, now=utc_now, known=()):
    """Write the duplicate proof and create grant, then prove the executor accepts them."""
    prepared = prepare(json_file, paths)
    root = draft.state_root(paths)
    require(not source_already_attempted(paths, prepared.source_id))
    journal_path = Path(paths.uploads_registry_path + '.modern-v1.json')
    history = journal_path.read_bytes() if journal_path.exists() else b'{}'
    inventory_path = Path(inventory_path)
    inventory, inventory_sha = draft.read_document(inventory_path)
    require(isinstance(inventory, dict) and inventory.get('kind') == INVENTORY_KIND
            and inventory.get('complete') is True and inventory.get('origin') == draft.ORIGIN
            and isinstance(inventory.get('records'), list) and isinstance(inventory.get('pages'), list)
            and isinstance(inventory.get('details'), list) and inventory['pages']
            and inventory['pages'][-1].get('count') == 0
            and inventory.get('record_count') == len(inventory['records']))
    require(rebuild_records(inventory_path, inventory) == inventory['records'])
    captured = draft.instant(inventory['captured_at'])
    start = now()
    require(timedelta(0) <= start - captured <= INVENTORY_MAX_AGE and type(window) is int and 0 < window <= 600)
    require(isinstance(reviewer, str) and reviewer.strip())
    draft.digest(canary_receipt_sha256)
    require(isinstance(owner, str) and re.fullmatch('[1-9][0-9]{0,19}', owner) is not None)
    records = inventory['records']
    require(records and all(str(record.get('owner')) == owner for record in records)
            and all(set(record) == set(summarize({'id': 1})) for record in records))
    title = parse(prepared.body)['metadata']['title']
    hits = inventory_matches(records, prepared.source_id, title, prepared.xml, known_records(paths, known))
    if hits:
        raise Held('Inventory holds candidate records for this source: ' + json.dumps(hits, sort_keys=True))
    proof = {'schema_version': 1, 'origin': draft.ORIGIN, 'owner': owner, 'binding': prepared.binding,
             'state_root': str(root), 'complete': True, 'history_reconciled': True,
             'checked_at': captured.isoformat(), 'expires_at': (captured + timedelta(hours=1)).isoformat(),
             'matched_record_ids': [], 'matched_dois': [], 'inventory_sha256': inventory_sha,
             'history_sha256': sha(history), 'reviewed_by': reviewer}
    grant = {'schema_version': 1, 'approved': True, 'executor': draft.EXECUTOR, 'origin': draft.ORIGIN,
             'binding': prepared.binding, 'state_root': str(root), 'owner': owner, 'limits': dict(draft.LIMITS),
             'started_at': start.isoformat(), 'expires_at': (start + timedelta(seconds=window)).isoformat(),
             'duplicate_proof_sha256': None, 'reviewed_by': reviewer, 'token_scope': 'deposit:write',
             'draft_only': True, 'canary_receipt_sha256': canary_receipt_sha256}
    require(not Path(proof_out).exists() and not Path(grant_out).exists())
    try:
        draft.permanent_intent(proof_out, proof)
        grant['duplicate_proof_sha256'] = sha(Path(proof_out).read_bytes())
        draft.permanent_intent(grant_out, grant)
        # The executor's own contract is the final word on what was minted.
        draft.authorize(prepared, paths, grant_out, proof_out, start)
    except BaseException:
        for path in (Path(proof_out), Path(grant_out)):
            path.unlink(missing_ok=True)
        raise
    return {'source_id': prepared.source_id, 'binding': prepared.binding, 'title': title,
            'inventory_sha256': inventory_sha, 'inventory_records': len(records),
            'grant_sha256': sha(Path(grant_out).read_bytes()), 'proof_sha256': grant['duplicate_proof_sha256'],
            'window_ends': grant['expires_at'], 'provider_requests': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    inventory = sub.add_parser('inventory', help='Capture the owner inventory with bounded listing GETs')
    inventory.add_argument('--evidence-dir', required=True)
    inventory.add_argument('--captured-by', required=True)
    inventory.add_argument('--max-pages', type=int, default=MAX_PAGES)
    inventory.add_argument('--max-details', type=int, default=MAX_DETAILS)
    inventory.add_argument('--token-keychain', metavar='SERVICE', help=draft.KEYCHAIN_HELP)
    mint = sub.add_parser('mint-create', help='Mint the create grant and duplicate proof offline')
    for key in ('json-file', 'output-dir', 'inventory', 'owner', 'reviewer', 'canary-receipt-sha256',
                'grant-out', 'proof-out'):
        mint.add_argument('--' + key, required=True)
    mint.add_argument('--window-seconds', type=int, default=600)
    mint.add_argument('--known-record', action='append', default=[],
                      help='Record ID whose files were verified another way; repeatable')
    args = parser.parse_args()
    try:
        if args.action == 'inventory':
            try:
                token = draft.production_token('Production token (memory only; deposit:write): ',
                                               args.token_keychain, action='inventory')
            except BaseException:
                print(draft.TOKEN_HELD)
                return 1
            out, document = capture_inventory(draft.Transport(token), token, args.evidence_dir, args.captured_by,
                                              max_pages=args.max_pages, max_details=args.max_details)
            result = {'inventory': str(out), 'inventory_sha256': sha(out.read_bytes()),
                      'record_count': document['record_count'], 'pages': len(document['pages']),
                      'details': len(document['details']),
                      'provider_requests': len(document['pages']) + len(document['details']),
                      'provider_mutations': 0}
        else:
            paths = OutputPaths(args.output_dir, 'production')
            result = mint_create(args.json_file, paths, args.inventory, args.owner, args.reviewer,
                                 args.canary_receipt_sha256, args.grant_out, args.proof_out,
                                 window=args.window_seconds, known=args.known_record)
        print(encode(result).decode())
        return 0
    except Held as held:
        print(json.dumps({'held': True, 'reason': str(held)}))
        return 1
    except FileExistsError:
        print(json.dumps({'held': True, 'reason': 'an output file already exists; choose new output names'}))
        return 1
    except BaseException:
        print(HELD)
        return 1


if __name__ == '__main__':
    sys.exit(main())
