"""Resolve canonical FGDC bytes, rejecting conflicting copies without rewriting them."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from scripts.path_config import OutputPaths

LEGACY_METADATA_ONLY_NOTE = (
    "Record is migrated FGDC metadata from the archived PICES GeoNetwork "
    "metadata catalogue; dataset is metadata-only."
)
MIGRATION_NOTE = (
    "Record includes migrated FGDC metadata from the archived PICES GeoNetwork "
    "metadata catalogue; deposited research-data availability is classified separately."
)
FGDC_XML_HEADER = "Original FGDC metadata (XML):"


def _candidate_paths(base_name: str, paths: OutputPaths) -> Tuple[str, ...]:
    """Return possible filesystem locations for the FGDC XML."""
    filename = f"{base_name}.xml"
    return (
        os.path.join("FGDC", filename),
        os.path.join(paths.original_fgdc_dir, filename),
        os.path.join(paths.base, filename),
    )


def locate_fgdc_xml(base_name: str, paths: OutputPaths) -> Optional[str]:
    """Prefer FGDC/, with byte-identical copies or compatible fallback only."""
    present = [candidate for candidate in dict.fromkeys(_candidate_paths(base_name, paths))
               if os.path.lexists(candidate)]
    if not present:
        return None
    original = None
    for candidate in present:
        if not os.path.isfile(candidate):
            raise ValueError(f"Ambiguous FGDC source candidate is not a file: {candidate}")
        raw = Path(candidate).read_bytes()  # An unreadable present copy cannot establish agreement.
        if original is not None and raw != original:
            raise ValueError(f"Conflicting FGDC sources for {base_name}; copies must match original bytes")
        original = raw
    return present[0]


def load_fgdc_xml(base_name: str, paths: OutputPaths) -> Tuple[Optional[str], Optional[str]]:
    """Load the FGDC XML content and return it with the resolved path."""
    fgdc_path = locate_fgdc_xml(base_name, paths)
    if not fgdc_path:
        return None, None

    with open(fgdc_path, "r", encoding="utf-8") as fh:
        content = fh.read().strip()
    return content, fgdc_path


def build_metadata_notes(existing_notes: str, fgdc_xml: Optional[str]) -> str:
    """Return a consolidated notes field with metadata-only context and FGDC XML."""
    parts = []
    normalized = (existing_notes or "").replace(LEGACY_METADATA_ONLY_NOTE, "").strip()

    if normalized:
        parts.append(normalized)

    if MIGRATION_NOTE not in normalized:
        parts.append(MIGRATION_NOTE)

    if fgdc_xml:
        xml_block = f"{FGDC_XML_HEADER}\n\n```xml\n{fgdc_xml}\n```"
        if xml_block not in normalized:
            parts.append(xml_block)

    return "\n\n".join(part for part in parts if part).strip()
