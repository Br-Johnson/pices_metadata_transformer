"""Production-only durable write attempts; callers hold the environment ledger lock.

No transport or authority is provided here. A spent action is never replayed;
only verified readback or explicit identity reconciliation can advance its state.
The independent journal must be preserved alongside the upload registry.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Pinned retained associations, not new ownership or publication authorization.
PROTECTED = {
    'FGDC-1238': (17317855, 'c559cd8b956683c71c2fd240e583bc5817b2cf7f5bcc390955578c1e1e15aa2f'),
    'FGDC-2043': (17317851, '9fc45ede1eff08d39e06618ae4b081ba5a6244a886a1a817fb2b4640b145790d'),
    'FGDC-2057': (17317859, 'e0b48017a563544dedb618f5106e84dbeaf18ca7af1cbda83d93371cdd73736b'),
    'FGDC-2725': (17317857, 'f8c85ff810507722578d0ccf592d8dc1b1518529f7574745ff900ff5347dccdc'),
    'FGDC-2731': (17317853, '2f08555afe0c393d0c9e826d8fa3f78ddf5f5068a1575cf04218912265ec3a6c'),
}
EXCLUDED = {10042430, 15046283}
ACTIONS = {'create', 'metadata', 'artifact', 'publish'}


def doi_key(value):
    if value is None or value == '':
        return None
    if (not isinstance(value, str) or len(value) > 2048
            or not re.fullmatch(r'10\.[0-9]{4,9}/[^\s]+', value)
            or any(ord(char) < 33 for char in value)):
        raise ValueError('Invalid DOI identity')
    return value.casefold()


def preserve_identity(source_id, entry, remote=None):
    """Return the known DOI without accepting swaps or erasing absent DOI fields."""
    identifier = entry.get('deposition_id')
    if identifier is not None and (type(identifier) is not int or identifier < 1):
        raise ValueError('Invalid production record identity')
    known = entry.get('doi')
    doi_key(known)
    known = known or None
    if entry.get('environment') == 'production':
        if identifier in EXCLUDED:
            raise ValueError('Excluded production record identity')
        for sid, (record_id, source_hash) in PROTECTED.items():
            doi = f'10.5281/zenodo.{record_id}'
            if source_id == sid:
                if identifier != record_id or entry.get('source_sha256') != source_hash:
                    raise ValueError('Protected production source/record identity must be preserved')
                if known and doi_key(known) != doi_key(doi):
                    raise ValueError('Protected production DOI must be preserved')
                known = known or doi
            elif identifier == record_id or doi_key(known) == doi_key(doi):
                raise ValueError('Protected production identity belongs to another source')
    if remote is not None:
        if type(remote.get('id')) is not int or remote['id'] != identifier:
            raise ValueError('Remote record identity differs')
        metadata = remote.get('metadata', {})
        values = [remote.get('doi'), metadata.get('doi'),
                  (metadata.get('prereserve_doi') or {}).get('doi')]
        for value in values:
            if value is None or value == '':
                continue
            if not isinstance(value, str) or (known and doi_key(value) != doi_key(known)):
                raise ValueError('Remote DOI conflicts with preserved identity')
            doi_key(value)
            known = known or value
        # Also reject a protected DOI supplied by a different remote record.
        if entry.get('environment') == 'production':
            for sid, (record_id, _) in PROTECTED.items():
                if doi_key(known) == f'10.5281/zenodo.{record_id}' and source_id != sid:
                    raise ValueError('Protected production DOI belongs to another source')
    return known


def source_binding(source_id, entry):
    if entry.get('environment') != 'production' or not isinstance(source_id, str) or not source_id:
        raise ValueError('Production source binding required')
    for key in ('source_sha256', 'metadata_sha256'):
        if not isinstance(entry.get(key), str) or not re.fullmatch('[0-9a-f]{64}', entry[key]):
            raise ValueError('Complete source/payload hash binding required')
    value = {key: entry.get(key) for key in
             ('environment', 'source_sha256', 'metadata_sha256', 'artifact_contract')}
    value['source_id'] = source_id
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


class MutationJournal:
    """Independent of replaceable duplicate inventories and recoverable registries."""

    def __init__(self, paths):
        if paths.environment != 'production':
            raise ValueError('Mutation journal requires production-scoped paths')
        self.path = Path(paths.uploads_registry_path + '.mutations.json')
        self.data = (json.loads(self.path.read_text()) if self.path.exists() else
                     {'schema_version': 1, 'environment': 'production', 'targets': {}})
        if (not isinstance(self.data, dict) or type(self.data.get('schema_version')) is not int or self.data.get('schema_version') != 1
                or self.data.get('environment') != 'production'
                or not isinstance(self.data.get('targets'), dict)):
            raise ValueError('Invalid production mutation journal; preserve and reconcile')
        seen = set()
        seen_dois = set()
        for row in self.data['targets'].values():
            if (not isinstance(row, dict) or not isinstance(row.get('binding'), str)
                    or not re.fullmatch('[0-9a-f]{64}', row['binding'])
                    or not isinstance(row.get('actions'), dict) or not row['actions']):
                raise ValueError('Invalid production mutation target')
            key = doi_key(row.get('doi'))
            if key and key in seen_dois:
                raise ValueError('Shared journal DOI identity')
            if key:
                seen_dois.add(key)
            identifier = row.get('deposition_id')
            if identifier is not None:
                if type(identifier) is not int or identifier < 1 or identifier in seen:
                    raise ValueError('Invalid or shared journal record identity')
                seen.add(identifier)
            for action, receipt in row['actions'].items():
                if (action not in ACTIONS or not isinstance(receipt, dict)
                        or receipt.get('status') not in {'uncertain', 'verified'}
                        or not isinstance(receipt.get('attempted_at'), str)):
                    raise ValueError('Invalid production mutation receipt')

    def validate(self, source_id, entry, *, adopting=False):
        preserve_identity(source_id, entry)
        binding = source_binding(source_id, entry)
        row = self.data['targets'].get(source_id)
        if row is not None:
            if row['binding'] != binding:
                raise ValueError('Production mutation source/payload binding changed')
            if row.get('deposition_id') != entry.get('deposition_id'):
                if not (adopting and row.get('deposition_id') is None):
                    raise ValueError('Production mutation identity differs; reconcile')
            preserve_identity(source_id, dict(entry, doi=row.get('doi') or entry.get('doi')))
            if row.get('doi') and entry.get('doi') and doi_key(row['doi']) != doi_key(entry['doi']):
                raise ValueError('Production mutation DOI differs')
        for sid, other in self.data['targets'].items():
            if (sid != source_id and entry.get('deposition_id') is not None
                    and other.get('deposition_id') == entry['deposition_id']):
                raise ValueError('Journal record identity belongs to another source')
            if sid != source_id and entry.get('doi') and doi_key(other.get('doi')) == doi_key(entry['doi']):
                raise ValueError('Journal DOI belongs to another source')
        return row

    def _save(self):
        from scripts.upload_service import atomic_json
        atomic_json(self.path, self.data)

    def begin(self, source_id, entry, action):
        if action not in ACTIONS or (action != 'create' and not entry.get('deposition_id')):
            raise ValueError('Invalid production mutation action')
        if action == 'create' and entry.get('deposition_id') is not None:
            raise ValueError('Cannot create a replacement for a known record')
        row = self.validate(source_id, entry)
        if row is None:
            row = {'binding': source_binding(source_id, entry),
                   'deposition_id': entry.get('deposition_id'), 'doi': entry.get('doi'), 'actions': {}}
            self.data['targets'][source_id] = row
        row['doi'] = row.get('doi') or preserve_identity(source_id, entry)
        if action in row['actions']:
            raise ValueError('Production mutation already attempted; readback/reconciliation required')
        row['actions'][action] = {'status': 'uncertain', 'record_id': entry.get('deposition_id'),
                                 'attempted_at': datetime.now(timezone.utc).isoformat()}
        self._save()  # Never dispatch if file OR directory durability fails.

    def confirm(self, source_id, entry, action, remote):
        """Caller has verified the action's desired state on this exact record."""
        row = self.validate(source_id, entry, adopting=action == 'create')
        doi = preserve_identity(source_id, dict(entry, doi=(row or {}).get('doi') or entry.get('doi')), remote)
        if action == 'publish' and not doi:
            raise ValueError('Production published DOI remains unverified; reconcile')
        self.validate(source_id, dict(entry, doi=doi), adopting=action == 'create')
        if row is not None and action in row['actions']:
            row['deposition_id'], row['doi'] = entry.get('deposition_id'), doi
            row['actions'][action].update(
                status='verified', verified_at=datetime.now(timezone.utc).isoformat(),
                response_sha256=hashlib.sha256(json.dumps(remote, sort_keys=True, ensure_ascii=False,
                                                        separators=(',', ':')).encode()).hexdigest())
            self._save()
        return doi

    def adopt(self, source_id, entry):
        """Explicit offline identity recovery never replenishes spent action keys."""
        row = self.validate(source_id, entry, adopting=True)
        if row is None:
            # No retained attempt history proves that any legacy write is unspent.
            # Record uncertainty for every action; a snapshot cannot grant writes.
            row = {'binding': source_binding(source_id, entry), 'doi': entry.get('doi'),
                   'actions': {action: {
                       'status': 'uncertain',
                       'record_id': None if action == 'create' else entry['deposition_id'],
                       'attempted_at': datetime.now(timezone.utc).isoformat(),
                       'legacy_history_unknown': True} for action in sorted(ACTIONS)}}
        if row is not None:
            row = copy.deepcopy(row)
            row['deposition_id'] = entry['deposition_id']
            row['doi'] = row.get('doi') or entry.get('doi')
            self.data['targets'][source_id] = row
            self._save()
