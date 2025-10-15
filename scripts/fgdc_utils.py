"""Utility helpers for working with original FGDC XML records."""

from __future__ import annotations

import os
from typing import Optional, Tuple

from scripts.path_config import OutputPaths

METADATA_ONLY_NOTE = (
    "Record is migrated FGDC metadata from the archived PICES GeoNetwork "
    "metadata catalogue; dataset is metadata-only."
)
FGDC_XML_HEADER = "Original FGDC metadata (XML):"


def _candidate_paths(base_name: str, paths: OutputPaths) -> Tuple[str, ...]:
    """Return possible filesystem locations for the FGDC XML."""
    filename = f"{base_name}.xml"
    return (
        os.path.join(paths.original_fgdc_dir, filename),
        os.path.join("FGDC", filename),
        os.path.join(paths.base, filename),
    )


def locate_fgdc_xml(base_name: str, paths: OutputPaths) -> Optional[str]:
    """Locate the FGDC XML file for a given record base name."""
    for candidate in _candidate_paths(base_name, paths):
        if os.path.exists(candidate):
            return candidate
    return None


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
    normalized = (existing_notes or "").strip()

    if normalized:
        parts.append(normalized)

    if METADATA_ONLY_NOTE not in normalized:
        parts.append(METADATA_ONLY_NOTE)

    if fgdc_xml:
        xml_block = f"{FGDC_XML_HEADER}\n\n```xml\n{fgdc_xml}\n```"
        if xml_block not in normalized:
            parts.append(xml_block)

    return "\n\n".join(part for part in parts if part).strip()
