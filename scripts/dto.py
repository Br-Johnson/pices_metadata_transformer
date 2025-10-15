"""Canonical record data-transfer objects used across the pipeline.

This module defines lightweight dataclasses that capture the normalized
representation of a transformed record.  By keeping the DTO close to the
Zenodo JSON structure we avoid bespoke dictionaries scattered across the
codebase and provide a single place to document invariants such as
"publisher must always be PICES".  The DTO objects are intentionally
serialisable so they can be written to disk for regression testing and
downstream JSON-LD generation.

The classes here are intentionally conservative – they only model fields
that are required by the current pipeline.  Optional metadata is stored in
`extra_metadata` so the DTO remains forward compatible when new Zenodo
attributes are introduced.  This keeps the codebase parsimonious without
losing fidelity of the source metadata.
"""

from __future__ import annotations

import json

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Attachment:
    """Represents a file that should accompany the Zenodo deposition."""

    path: str
    description: str
    file_type: str

    def to_json(self) -> Dict[str, Any]:
        """Return a JSON serialisable representation of the attachment."""

        return {
            "path": self.path,
            "description": self.description,
            "type": self.file_type,
        }


@dataclass(frozen=True)
class BibliographicLink:
    """Represents a normalised link to an external bibliographic system."""

    source: str
    identifier: str
    relation: str
    confidence: float
    status: str = "proposed"
    title: Optional[str] = None
    url: Optional[str] = None
    scheme: Optional[str] = None
    notes: Optional[str] = None

    def to_related_identifier(self) -> Dict[str, Any]:
        """Return a Zenodo `related_identifiers` compatible payload."""

        payload: Dict[str, Any] = {
            "relation": self.relation,
            "identifier": self.identifier,
            "resource_type": "dataset",
        }
        if self.scheme:
            payload["scheme"] = self.scheme
        if self.notes:
            payload["description"] = self.notes
        return payload

    def to_json(self) -> Dict[str, Any]:
        """Serialise the bibliographic link for DTO persistence."""

        result = asdict(self)
        return result


@dataclass(frozen=True)
class QualitySnapshot:
    """Aggregated quality metrics captured during transformation."""

    character_analysis: Mapping[str, Any] = field(default_factory=dict)
    enhanced_metrics: Mapping[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        """Serialise the quality snapshot."""

        return {
            "character_analysis": dict(self.character_analysis),
            "enhanced_metrics": dict(self.enhanced_metrics),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "QualitySnapshot":
        return cls(
            character_analysis=payload.get("character_analysis", {}),
            enhanced_metrics=payload.get("enhanced_metrics", {}),
        )


@dataclass
class CanonicalRecordDTO:
    """Canonical record representation shared by all downstream systems."""

    fgdc_id: str
    source_path: str
    zenodo_metadata: MutableMapping[str, Any]
    attachments: Tuple[Attachment, ...] = field(default_factory=tuple)
    bibliographic_links: Tuple[BibliographicLink, ...] = field(default_factory=tuple)
    quality: QualitySnapshot = field(default_factory=QualitySnapshot)
    audit_trail: MutableMapping[str, Any] = field(default_factory=dict)
    extra_metadata: MutableMapping[str, Any] = field(default_factory=dict)

    PICES_PUBLISHER = "North Pacific Marine Science Organization"

    def __post_init__(self) -> None:
        """Enforce invariants that keep downstream consumers consistent."""

        publisher = self.zenodo_metadata.get("publisher")
        if publisher and publisher != self.PICES_PUBLISHER:
            self.zenodo_metadata["imprint_publisher"] = publisher
        self.zenodo_metadata["publisher"] = self.PICES_PUBLISHER

    # ------------------------------------------------------------------ helpers
    @property
    def related_identifiers(self) -> List[Dict[str, Any]]:
        """Return normalised related identifiers for Zenodo payloads."""

        identifiers: List[Dict[str, Any]] = []
        for link in self.bibliographic_links:
            identifiers.append(link.to_related_identifier())
        return identifiers

    def copy(self, **overrides: Any) -> "CanonicalRecordDTO":
        """Return a shallow clone with optional field overrides."""

        payload: Dict[str, Any] = {
            "fgdc_id": self.fgdc_id,
            "source_path": self.source_path,
            "zenodo_metadata": dict(self.zenodo_metadata),
            "attachments": self.attachments,
            "bibliographic_links": self.bibliographic_links,
            "quality": self.quality,
            "audit_trail": dict(self.audit_trail),
            "extra_metadata": dict(self.extra_metadata),
        }
        payload.update(overrides)
        return CanonicalRecordDTO(**payload)

    def with_attachments(self, attachments: Sequence[Attachment]) -> "CanonicalRecordDTO":
        """Return a clone with updated attachments."""

        return self.copy(attachments=tuple(attachments))

    def with_bibliographic_links(self, links: Iterable[BibliographicLink]) -> "CanonicalRecordDTO":
        """Return a clone with updated bibliographic links."""

        return self.copy(bibliographic_links=tuple(links))

    def with_audit_event(
        self,
        stage: str,
        event: Mapping[str, Any],
    ) -> "CanonicalRecordDTO":
        """Return a clone with an audit event appended for the supplied stage."""

        audit_trail = dict(self.audit_trail)
        stage_events = list(audit_trail.get(stage) or [])
        stage_events.append(dict(event))
        audit_trail[stage] = stage_events
        return self.copy(audit_trail=audit_trail)

    def to_json(self) -> Dict[str, Any]:
        """Serialise the DTO to a JSON compatible structure."""

        return {
            "fgdc_id": self.fgdc_id,
            "source_path": self.source_path,
            "zenodo_metadata": dict(self.zenodo_metadata),
            "attachments": [attachment.to_json() for attachment in self.attachments],
            "bibliographic_links": [link.to_json() for link in self.bibliographic_links],
            "quality": self.quality.to_json(),
            "audit_trail": dict(self.audit_trail),
            "extra_metadata": dict(self.extra_metadata),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "CanonicalRecordDTO":
        attachments = [
            Attachment(
                path=item.get("path", ""),
                description=item.get("description", ""),
                file_type=item.get("type", ""),
            )
            for item in payload.get("attachments", [])
        ]
        links = [
            BibliographicLink(
                source=item.get("source", ""),
                identifier=item.get("identifier", ""),
                relation=item.get("relation", "isAlternativeIdentifierOf"),
                confidence=float(item.get("confidence", 0.0)),
                status=item.get("status", "proposed"),
                title=item.get("title"),
                url=item.get("url"),
                scheme=item.get("scheme"),
                notes=item.get("notes"),
            )
            for item in payload.get("bibliographic_links", [])
        ]
        quality = QualitySnapshot.from_json(payload.get("quality", {}))
        return cls(
            fgdc_id=payload.get("fgdc_id", ""),
            source_path=payload.get("source_path", ""),
            zenodo_metadata=dict(payload.get("zenodo_metadata", {})),
            attachments=tuple(attachments),
            bibliographic_links=tuple(links),
            quality=quality,
            audit_trail=dict(payload.get("audit_trail", {})),
            extra_metadata=dict(payload.get("extra_metadata", {})),
        )


def _normalise_fgdc_id(source_path: str) -> str:
    base = source_path.rsplit("/", 1)[-1]
    if base.lower().endswith(".xml"):
        base = base[:-4]
    return base


def build_canonical_dto(
    source_path: str,
    zenodo_metadata: Mapping[str, Any],
    character_analysis: Optional[Mapping[str, Any]] = None,
    enhanced_metrics: Optional[Mapping[str, Any]] = None,
    attachments: Optional[Iterable[Mapping[str, Any]]] = None,
    bibliographic_links: Optional[Iterable[BibliographicLink]] = None,
    audit_trail: Optional[Mapping[str, Any]] = None,
    extra_metadata: Optional[Mapping[str, Any]] = None,
) -> CanonicalRecordDTO:
    """Construct the canonical DTO from raw transformation artefacts."""

    fgdc_id = _normalise_fgdc_id(source_path)
    attachment_objs = []
    if attachments:
        for attachment in attachments:
            if not attachment:
                continue
            attachment_objs.append(
                Attachment(
                    path=str(attachment.get("path", "")),
                    description=str(attachment.get("description", "")),
                    file_type=str(attachment.get("type", "")),
                )
            )

    quality = QualitySnapshot(
        character_analysis=character_analysis or {},
        enhanced_metrics=enhanced_metrics or {},
    )

    dto = CanonicalRecordDTO(
        fgdc_id=fgdc_id,
        source_path=source_path,
        zenodo_metadata=dict(zenodo_metadata),
        attachments=tuple(attachment_objs),
        bibliographic_links=tuple(bibliographic_links or ()),
        quality=quality,
        audit_trail=dict(audit_trail or {}),
        extra_metadata=dict(extra_metadata or {}),
    )
    return dto


def merge_related_identifiers(
    metadata: MutableMapping[str, Any],
    related_identifiers: Sequence[Dict[str, Any]],
) -> None:
    """Merge related identifiers into the Zenodo metadata in-place."""

    existing: List[Dict[str, Any]] = list(metadata.get("related_identifiers") or [])
    identifier_set = {
        (item.get("identifier"), item.get("relation")) for item in existing
    }
    for identifier in related_identifiers:
        key = (identifier.get("identifier"), identifier.get("relation"))
        if key in identifier_set:
            continue
        existing.append(identifier)
        identifier_set.add(key)
    metadata["related_identifiers"] = existing


def load_dto(path: str) -> CanonicalRecordDTO:
    """Load a DTO JSON file from disk."""

    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return CanonicalRecordDTO.from_json(payload)


def save_dto(path: str, dto: CanonicalRecordDTO) -> None:
    """Persist a DTO to disk with deterministic formatting."""

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(dto.to_json(), handle, indent=2, ensure_ascii=False)

