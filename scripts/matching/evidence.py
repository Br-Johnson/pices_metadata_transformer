"""Offline external-inventory ingestion with explicit completeness and provenance.

Accepts saved HTTP snapshots or normalized exports; never fetches a repository.
HTML shells, failures and partial results cannot establish absence of duplicates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.dto import load_dto
from scripts.matching.engine import MatchCandidate, MatchingEngine
from scripts.upload_service import atomic_json


def validate_json_payload(payload, source):
    if not isinstance(payload, dict):
        raise ValueError('Expected a JSON object, not an HTML shell or unstructured response')
    if source == 'datacite':
        records = payload.get('data')
    elif source == 'crossref':
        message = payload.get('message')
        if not isinstance(message, dict):
            raise ValueError('Malformed Crossref message')
        records = message.get('items')
    elif source == 'dspace':
        embedded = payload.get('_embedded')
        result = embedded.get('searchResult') if isinstance(embedded, dict) else None
        objects = result.get('_embedded') if isinstance(result, dict) else None
        if not isinstance(objects, dict):
            raise ValueError('Malformed DSpace search containers')
        records = objects.get('objects')
    else:
        records = payload.get('records')
    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise ValueError(f'Missing or malformed {source} record collection')
    return records


def snapshot_inventory(snapshot):
    body = snapshot.get('body', '')
    serialized = body if isinstance(body, str) else json.dumps(body, sort_keys=True)
    result = {key: snapshot.get(key) for key in ('repository', 'endpoint', 'retrieved_at', 'query', 'scope')}
    result.update(response_sha256=hashlib.sha256(serialized.encode()).hexdigest(),
                  http_status=snapshot.get('http_status'), status='unchecked_unavailable',
                  inventory_complete=False, records=[])
    try:
        if not all(result.get(key) for key in ('repository', 'endpoint', 'retrieved_at', 'scope')):
            raise ValueError('Snapshot requires repository, endpoint, retrieval time and scope provenance')
        if snapshot.get('http_status') != 200:
            raise ValueError(f"HTTP {snapshot.get('http_status')}; inventory unavailable")
        format_name = snapshot.get('format', 'records')
        complete = snapshot.get('scope_complete') is True
        if format_name == 'oai':
            root = ET.fromstring(serialized)
            ns = {'oai': 'http://www.openarchives.org/OAI/2.0/', 'dc': 'http://purl.org/dc/elements/1.1/'}
            if root.tag != '{http://www.openarchives.org/OAI/2.0/}OAI-PMH':
                raise ValueError('Expected OAI-PMH XML, not an Angular/HTML application shell')
            errors = root.findall('oai:error', ns)
            if errors and any(error.get('code') != 'noRecordsMatch' for error in errors):
                raise ValueError('OAI-PMH error: ' + '; '.join(error.get('code', '') for error in errors))
            if root.find('oai:Identify', ns) is not None:
                result['status'] = 'unchecked_identify_only'
                return result
            records = []
            for record in root.findall('oai:ListRecords/oai:record', ns):
                header = record.find('oai:header', ns)
                if header is not None and header.get('status') == 'deleted':
                    continue
                titles = record.findall('.//dc:title', ns)
                identifiers = [elem.text for elem in record.findall('.//dc:identifier', ns) if elem.text]
                if not titles or not identifiers:
                    raise ValueError('OAI record missing title or persistent identifier')
                records.append({'title': titles[0].text, 'identifier': identifiers[0],
                                'identifiers': identifiers, 'creators': [elem.text for elem in record.findall('.//dc:creator', ns) if elem.text],
                                'abstract': ' '.join(elem.text or '' for elem in record.findall('.//dc:description', ns))})
            token = root.find('oai:ListRecords/oai:resumptionToken', ns)
            complete = complete and (token is None or not token.text)
            if root.find('oai:ListRecords', ns) is None and not errors:
                raise ValueError('OAI response is not a record inventory')
        else:
            if 'html' in str(snapshot.get('content_type', '')).lower():
                raise ValueError('HTML is not a metadata inventory')
            payload = json.loads(body) if isinstance(body, str) else body
            raw_records = validate_json_payload(payload, format_name)
            if format_name == 'datacite':
                from scripts.matching.datacite_adapter import DataCiteAdapter
                records = [candidate.__dict__ for candidate in (DataCiteAdapter._normalise_item(item) for item in raw_records) if candidate]
                complete = complete and isinstance(payload.get('links'), dict) and not payload['links'].get('next') and isinstance(payload.get('meta'), dict) and type(payload['meta'].get('total')) is int and payload['meta']['total'] == len(raw_records)
            elif format_name == 'crossref':
                from scripts.matching.crossref_adapter import CrossrefAdapter
                records = [candidate.__dict__ for candidate in (CrossrefAdapter._normalise_item(item) for item in raw_records) if candidate]
                total = payload['message'].get('total-results')
                complete = complete and type(total) is int and total == len(raw_records)
            elif format_name == 'dspace':
                records = []
                for obj in raw_records:
                    item = obj.get('_embedded', {}).get('indexableObject', {})
                    metadata = item.get('metadata', {})
                    identifiers = [entry.get('value') for entry in metadata.get('dc.identifier.uri', []) if entry.get('value')]
                    if not item.get('name') or not identifiers:
                        raise ValueError('DSpace search object lacks indexed title/identifier')
                    records.append({'title': item['name'], 'identifier': identifiers[0], 'identifiers': identifiers,
                                    'creators': [entry.get('value') for entry in metadata.get('dc.contributor.author', []) if entry.get('value')]})
                page = payload.get('_embedded', {}).get('searchResult', {}).get('page', {})
                total = page.get('totalElements')
                complete = complete and type(total) is int and total == len(raw_records)
            else:
                records = raw_records
            if len(records) != len(raw_records):
                raise ValueError('Inventory includes unparseable records; absence cannot be established')
        for record in records:
            if (not isinstance(record.get('title'), str) or not record['title'].strip()
                    or not isinstance(record.get('identifier'), str) or not record['identifier'].strip()
                    or not isinstance(record.get('creators', []), list)
                    or any(not isinstance(creator, str) for creator in record.get('creators', []))
                    or not isinstance(record.get('identifiers', []), list)
                    or any(not isinstance(identifier, str) for identifier in record.get('identifiers', []))
                    or record.get('abstract') is not None and not isinstance(record['abstract'], str)):
                raise ValueError('Each inventory record needs title and persistent identifier')
        result.update(records=records, inventory_complete=complete,
                      status=('checked' if complete else 'unchecked_partial'))
    except (ValueError, TypeError, AttributeError, KeyError, ET.ParseError) as exc:
        result['error'] = str(exc)
    return result


def normalize_identifier(value):
    return str(value or '').strip().casefold().removeprefix('https://doi.org/').removeprefix('http://doi.org/').removeprefix('doi:')


def review_candidates(dto, inventory):
    # Persistent identities outrank text similarity; neither implies work/version equivalence.
    original = dto.zenodo_metadata
    ids = {normalize_identifier(original.get('doi')), normalize_identifier(dto.fgdc_id)}
    ids.update(normalize_identifier(link.get('identifier')) for link in original.get('related_identifiers', [])
               if link.get('relation') in ('isAlternateIdentifier', 'isIdenticalTo'))
    ids.discard('')
    candidates = []
    for raw in inventory.get('records', []):
        candidate = MatchCandidate(source=inventory.get('repository') or 'external',
                                   identifier=raw['identifier'], title=raw['title'],
                                   creators=raw.get('creators', []), abstract=raw.get('abstract'),
                                   url=raw.get('url'), published=raw.get('published'))
        score = MatchingEngine().score_candidates(dto, [candidate])[0]
        exact = bool(ids & {normalize_identifier(value) for value in raw.get('identifiers', []) + [raw['identifier'], raw.get('source_id')]})
        if exact or score.score >= .5:
            candidates.append({'identifier': raw['identifier'], 'title': raw['title'],
                               'identifier_match': exact, 'score': score.score, 'breakdown': score.breakdown,
                               'classification': None, 'decision': 'defer',
                               'evidence': {key: inventory.get(key) for key in ('endpoint', 'retrieved_at', 'query', 'scope', 'response_sha256')}})
    status = 'candidate_matches' if candidates else ('checked_no_match' if inventory.get('inventory_complete') else inventory.get('status'))
    return {'fgdc_id': dto.fgdc_id, 'status': status, 'inventory_complete': inventory.get('inventory_complete', False),
            'candidates': candidates, 'error': inventory.get('error')}


def main():
    parser = argparse.ArgumentParser(description='Review saved external metadata snapshots offline')
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--dto-dir', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    snapshot = json.loads(Path(args.snapshot).read_text(encoding='utf-8'))
    inventory = snapshot_inventory(snapshot)
    atomic_json(args.report, {'inventory': inventory, 'reviews': [review_candidates(load_dto(str(path)), inventory)
                                                               for path in sorted(Path(args.dto_dir).glob('*.json'))]})
    if not inventory['inventory_complete']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
