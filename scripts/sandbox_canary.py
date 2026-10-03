"""Pinned three-source sandbox-only legacy duplicate exception, never release authority."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

PLAN_SHA256 = '7d6ca76c371d1e9d78a3e99d92df00dd672ae4731a7d4f0b4b4528df1c83a389'
MARKER_PREFIX = 'pices-sandbox-canary:'


class SandboxCanary:
    def __init__(self, plan_path, environment):
        if environment != 'sandbox':
            raise ValueError('Canary duplicate exception is sandbox-only')
        self.path = Path(plan_path)
        raw = self.path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
            raise ValueError('Canary plan does not match reviewed pinned evidence')
        self.plan = json.loads(raw)
        self.binding = {'plan_sha256': PLAN_SHA256, 'run_namespace': self.plan['run_namespace']}

    def authorize(self, json_file, paths):
        from scripts.upload_service import prepare_metadata, metadata_hash
        if paths.environment != 'sandbox':
            raise ValueError('Canary paths must be sandbox-only')
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != PLAN_SHA256:
            raise ValueError('Canary plan changed after loading')
        path = Path(json_file)
        expected = self.plan['sources'].get(path.stem)
        if (not expected or path.name != path.stem + '.json'
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected['payload_sha256']):
            raise ValueError('Canary source or payload is outside the exact plan')
        metadata, _, source_hash = prepare_metadata(str(path), paths)
        if (source_hash != expected['source_sha256']
                or metadata_hash(metadata) != expected['metadata_sha256']
                or self.plan['marker'] not in metadata.get('keywords', [])):
            raise ValueError('Canary source/metadata/namespace binding changed')
        return metadata

    def registry(self, registry):
        if registry and registry.get('_sandbox_canary') != self.binding:
            raise ValueError('Canary ledger belongs to another plan/run or lacks binding')
        entries = {key: value for key, value in registry.items() if not key.startswith('_')}
        if set(entries) - set(self.plan['sources']) or len(entries) > self.plan['maximum_new_drafts']:
            raise ValueError('Canary ledger exceeds the exact selected source set')
        for sid, entry in entries.items():
            expected = self.plan['sources'][sid]
            if (entry.get('source_sha256') != expected['source_sha256']
                    or entry.get('metadata_sha256') != expected['metadata_sha256']):
                raise ValueError('Canary ledger source/payload binding changed')

    def check_inventory(self, json_file, paths, inventory, registry):
        from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
        self.registry(registry)
        metadata = self.authorize(json_file, paths)
        if not inventory.get('inventory_complete') or not isinstance(inventory.get('records'), list):
            raise ValueError('Canary requires complete live inventory')
        # DOI/identity matches are never waived, even alongside an old title match.
        if PreUploadDuplicateChecker._identifiers(metadata) & inventory.get('identifiers', set()):
            raise ValueError('Canary exception does not waive identifier collisions')
        title = metadata['title'].strip().casefold()
        if inventory.get('title_to_record', {}).get(title, {}).get('state') == 'local_candidate':
            raise ValueError('Canary exception does not waive in-batch collisions')
        expected_entry = registry.get(Path(json_file).stem, {})
        historical_ids = []
        for record in inventory['records']:
            md = record.get('metadata', {})
            keywords = md.get('keywords', [])
            if not isinstance(keywords, list):
                raise ValueError('Malformed inventory keywords')
            own = self.plan['marker'] in keywords
            if own:
                owners = [entry for key, entry in registry.items() if not key.startswith('_')
                          and entry.get('deposition_id') == record.get('id')]
                if len(owners) != 1:
                    raise ValueError('Own-run remote draft requires its original ledger; reconcile')
            if md.get('title', '').strip().casefold() != title:
                continue
            if own and expected_entry.get('deposition_id') == record.get('id'):
                if record.get('state') == 'done' or record.get('submitted') is True:
                    raise ValueError('Own-run canary unexpectedly published')
                continue
            if any(str(word).startswith(MARKER_PREFIX) for word in keywords):
                raise ValueError('Canary namespace collision is not a historical duplicate')
            try:
                created = datetime.fromisoformat(record['created'].replace('Z', '+00:00'))
                cutoff = datetime.fromisoformat(self.plan['legacy_created_before'])
                if created.tzinfo is None or created >= cutoff:
                    raise ValueError('Not a historical duplicate')
            except (KeyError, AttributeError, TypeError, ValueError):
                raise ValueError('Canary duplicate requires a verified historical creation time') from None
            if type(record.get('id')) is not int or record['id'] < 1:
                raise ValueError('Historical duplicate has invalid identity')
            historical_ids.append(record['id'])
        return historical_ids


def require_canary_context(canary, safe, registry):
    """Prevent a saved sandbox exception being consumed by a generic/production caller."""
    safe_binding = safe.get('sandbox_canary') if isinstance(safe, dict) else None
    ledger_binding = registry.get('_sandbox_canary')
    if canary is None:
        if safe_binding is not None or ledger_binding is not None:
            raise ValueError('Explicit sandbox canary plan required for exception state')
        return
    canary.registry(registry)
    if ledger_binding != canary.binding:
        raise ValueError('Initialized canary ledger missing; reconcile before new creates')
    if safe_binding != canary.binding:
        raise ValueError('Canary requires a fresh plan-bound inventory')
