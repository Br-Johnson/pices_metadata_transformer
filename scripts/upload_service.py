"""Canonical draft upload and durable environment-scoped recovery state.

No network is performed at import. CLI callers provide a client explicitly.
An uncertain create is never retried automatically; recovery needs a verified ID.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import fcntl

from scripts.fgdc_utils import build_metadata_notes, load_fgdc_xml
from scripts.validate_zenodo import ZenodoValidator


def metadata_hash(metadata: dict) -> str:
    return hashlib.sha256(json.dumps(metadata, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)  # Corrupt state must not silently become empty.


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def ledger_lock(paths):
    # One writer per environment, including concurrent CLI entry points.
    with open(paths.uploads_registry_path + ".lock", "a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def expected_host(environment):
    return "sandbox.zenodo.org" if environment == "sandbox" else "zenodo.org"


def assert_environment(entry, environment):
    if entry.get("environment") != environment:
        raise ValueError("Record environment is missing or mismatched; reconcile legacy state first")
    if urlparse(entry.get("zenodo_url", "")).hostname != expected_host(environment):
        raise ValueError("Record URL does not match selected environment")
    if entry.get('deposition_id'):
        if not isinstance(entry['deposition_id'], int) or entry['deposition_id'] < 1:
            raise ValueError('Invalid deposition ID')
        if urlparse(entry['zenodo_url']).path.rstrip('/') != f"/deposit/{entry['deposition_id']}":
            raise ValueError('Record URL and deposition ID disagree')


def require_inventory(safe, environment):
    if not isinstance(safe, dict) or safe.get('environment') != environment or not safe.get('inventory_complete'):
        raise ValueError('Complete environment-scoped duplicate inventory required before upload')
    try:
        expires = datetime.fromisoformat(safe['valid_until'])
        if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
            raise ValueError('Duplicate inventory expired; refresh before upload')
    except (KeyError, TypeError) as exc:
        raise ValueError('Duplicate inventory requires a validity window') from exc


def prepare_metadata(json_file, paths):
    payload = read_json(json_file)
    if not isinstance(payload, dict) or not isinstance(payload.get("metadata"), dict):
        raise ValueError("JSON file requires a metadata object")
    metadata = dict(payload["metadata"])
    base = Path(json_file).stem
    xml, xml_path = load_fgdc_xml(base, paths)
    if not xml:
        raise ValueError("Original FGDC XML required for source fidelity")
    metadata["notes"] = build_metadata_notes(metadata.get("notes", ""), xml)
    return metadata, xml_path, hashlib.sha256(Path(xml_path).read_bytes()).hexdigest()


class DraftUploadService:
    """Shared by batch and compatibility single-file upload entry points."""

    def __init__(self, paths, environment):
        if paths.environment != environment:
            raise ValueError("Upload state must be scoped to its environment")
        self.paths, self.environment = paths, environment

    def pending_files(self, limit=None):
        registry = read_json(self.paths.uploads_registry_path, {})
        safe = read_json(self.paths.safe_to_upload_path)
        require_inventory(safe, self.environment)
        fingerprints = safe.get("metadata_hashes", {})
        pending = []
        for json_file in sorted(Path(self.paths.zenodo_json_dir).glob("*.json")):
            metadata, _, _ = prepare_metadata(str(json_file), self.paths)
            digest = metadata_hash(metadata)
            entry = registry.get(json_file.stem, {})
            if entry:
                assert_environment(entry, self.environment)
                if entry.get("needs_reconciliation"):
                    raise ValueError(f"{json_file.stem}: uncertain creation requires reconciliation")
                if entry.get("metadata_sha256") != digest:
                    raise ValueError(f"{json_file.stem}: metadata changed after draft creation; review before replacing")
                if entry.get("upload_status") == "success":
                    continue
                if entry.get("deposition_id"):
                    pending.append(str(json_file))
                    continue  # Resume the same known draft, even if inventory now lists it.
            if json_file.name in safe.get("files", []):
                if fingerprints.get(json_file.name) != digest:
                    raise ValueError(f"{json_file.name}: stale duplicate-check payload")
                pending.append(str(json_file))
        return pending[:limit] if limit is not None else pending

    def upload(self, json_file, client):
        metadata, xml_path, source_hash = prepare_metadata(json_file, self.paths)
        digest = metadata_hash(metadata)
        base = Path(json_file).stem
        if urlparse(client.base_url).hostname != expected_host(self.environment):
            raise ValueError("Client host mismatch")
        # Validate the actual payload after XML notes assembly, before creating anything.
        issues, warnings = ZenodoValidator().validate_metadata(metadata)
        if issues:
            raise ValueError("Invalid metadata: " + "; ".join(issues))
        with ledger_lock(self.paths):
            registry = read_json(self.paths.uploads_registry_path, {})
            previous = registry.get(base, {})
            if previous:
                assert_environment(previous, self.environment)
                if previous.get("needs_reconciliation"):
                    raise ValueError("Uncertain creation requires reconciliation before retry")
                if previous.get("metadata_sha256") != digest:
                    raise ValueError("Metadata changed; existing draft must be reviewed before updating")
                if previous.get("upload_status") == "success":
                    return dict(previous, success=True, json_file=json_file, metadata=metadata)
            else:
                safe = read_json(self.paths.safe_to_upload_path, {})
                require_inventory(safe, self.environment)
                if (safe.get("environment") != self.environment or not safe.get("inventory_complete")
                        or json_file and Path(json_file).name not in safe.get("files", [])
                        or safe.get("metadata_hashes", {}).get(Path(json_file).name) != digest):
                    raise ValueError("Fresh complete duplicate check required for this payload")
            entry = dict(previous, json_file=str(json_file), metadata=metadata,
                         metadata_sha256=digest, source_sha256=source_hash,
                         fgdc_file=xml_path, environment=self.environment,
                         timestamp=datetime.now(timezone.utc).isoformat(),
                         upload_status="pending", success=False,
                         zenodo_url=previous.get("zenodo_url", client.base_url + "/deposit/"))

            def save():
                registry[base] = entry
                atomic_json(self.paths.uploads_registry_path, registry)

            try:
                if not entry.get("deposition_id"):
                    entry["needs_reconciliation"] = True
                    save()  # A crash/lost response from POST must not cause another POST.
                    deposition = client.create_deposition()
                    entry["deposition_id"] = deposition["id"]
                    entry["zenodo_url"] = f"{client.base_url}/deposit/{deposition['id']}"
                    entry["needs_reconciliation"] = False
                    save()  # Persist remote ID before metadata update.
                updated = client.update_deposition_metadata(entry["deposition_id"], metadata,
                                                            files={"enabled": False})
                entry.update(success=True, upload_status="success", publish_status="draft",
                             doi=updated.get("metadata", {}).get("prereserve_doi", {}).get("doi"))
                entry.pop("error", None)
            except Exception as exc:
                entry.update(error=str(exc), upload_status="failed", success=False)
            save()
            return entry
