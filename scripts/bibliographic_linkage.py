"""Bibliographic linkage orchestration script.

This script queries external registries (DataCite and Crossref) for records
that resemble the transformed FGDC metadata.  It stores match candidates for
curator review, applies previously accepted decisions, and emits linkage
metrics for monitoring dashboards.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dto import (
    BibliographicLink,
    CanonicalRecordDTO,
    load_dto,
    merge_related_identifiers,
    save_dto,
)
from scripts.logger import get_logger, initialize_logger
from scripts.matching.crossref_adapter import CrossrefAdapter
from scripts.matching.datacite_adapter import DataCiteAdapter
from scripts.matching.engine import MatchCandidate, MatchResult, MatchingEngine
from scripts.path_config import OutputPaths, default_log_dir


def iter_dto_files(dto_dir: Path, limit: Optional[int]) -> Iterable[Path]:
    files = sorted(dto_dir.glob("*.json"))
    if limit is not None:
        files = files[:limit]
    for path in files:
        yield path


def build_candidates(
    dto: CanonicalRecordDTO,
    engine: MatchingEngine,
    adapters: Dict[str, object],
) -> List[MatchResult]:
    title = dto.zenodo_metadata.get("title", "")
    abstract = dto.zenodo_metadata.get("description")
    creators = [creator.get("name") for creator in dto.zenodo_metadata.get("creators", [])]

    candidates: List[MatchCandidate] = []
    for name, adapter in adapters.items():
        try:
            if hasattr(adapter, "search"):
                adapter_candidates = adapter.search(title, creators, abstract)
            else:
                adapter_candidates = []
        except Exception as exc:  # pragma: no cover - defensive logging
            get_logger().log_info(f"Adapter {name} failed: {exc}")
            adapter_candidates = []
        candidates.extend(adapter_candidates)

    scored = engine.score_candidates(dto, candidates)
    return scored


def write_candidates_report(
    output_path: Path,
    results: List[Dict[str, object]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)


def write_metrics(
    output_path: Path,
    generated_at: str,
    results: List[Dict[str, object]],
    threshold: float,
) -> None:
    counters = Counter()
    confident_records = 0
    for record in results:
        for candidate in record["candidates"]:
            counters[candidate["source"]] += 1
            if candidate["score"] >= threshold:
                confident_records += 1

    metrics = {
        "generated_at": generated_at,
        "records_evaluated": len(results),
        "total_candidates": sum(counters.values()),
        "sources": dict(counters),
        "above_threshold": confident_records,
        "threshold": threshold,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, ensure_ascii=False)


def _load_decisions(decision_path: Path) -> Dict[str, List[Dict[str, object]]]:
    if not decision_path.exists():
        return {}
    with open(decision_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_decisions(
    dto_path: Path,
    dto: CanonicalRecordDTO,
    decisions: List[Dict[str, object]],
    paths: OutputPaths,
    applied_at: Optional[str] = None,
) -> CanonicalRecordDTO:
    accepted_links: List[BibliographicLink] = []
    for decision in decisions:
        if decision.get("decision") != "accept":
            continue
        link = BibliographicLink(
            source=decision.get("source", ""),
            identifier=decision.get("identifier", ""),
            relation=decision.get("relation", "isAlternativeIdentifierOf"),
            confidence=float(decision.get("confidence", 0.0)),
            status="accepted",
            title=decision.get("title"),
            url=decision.get("url"),
            scheme=decision.get("scheme"),
            notes=decision.get("notes"),
        )
        accepted_links.append(link)

    if not accepted_links:
        return dto

    dto = dto.with_bibliographic_links(tuple(accepted_links))
    merge_related_identifiers(dto.zenodo_metadata, dto.related_identifiers)

    # Append provenance note
    note = (
        "Bibliographic linkage: "
        + "; ".join(
            f"{link.source}:{link.identifier} (score {link.confidence:.2f})"
            for link in accepted_links
        )
    )
    existing_notes = dto.zenodo_metadata.get("notes") or ""
    if existing_notes:
        existing_notes = existing_notes.strip() + "\n"
    dto.zenodo_metadata["notes"] = existing_notes + note

    audit_event = {
        "applied_at": applied_at,
        "accepted_links": [link.to_json() for link in accepted_links],
    }
    dto = dto.with_audit_event("bibliographic_linkage", audit_event)

    save_dto(str(dto_path), dto)

    zenodo_path = Path(paths.zenodo_json_dir) / f"{dto.fgdc_id}.json"
    if zenodo_path.exists():
        with open(zenodo_path, "r", encoding="utf-8") as handle:
            zenodo_payload = json.load(handle)
        metadata = zenodo_payload.get("metadata", {})
        merge_related_identifiers(metadata, dto.related_identifiers)
        metadata["notes"] = dto.zenodo_metadata.get("notes")
        zenodo_payload["metadata"] = metadata
        with open(zenodo_path, "w", encoding="utf-8") as handle:
            json.dump(zenodo_payload, handle, indent=2, ensure_ascii=False)

    return dto


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bibliographic linkage checks")
    parser.add_argument("--dto-dir", default="output/data/dto", help="Directory containing DTO JSON files")
    parser.add_argument("--output-dir", default="output", help="Root output directory")
    parser.add_argument("--limit", type=int, help="Limit number of DTO files to process")
    parser.add_argument("--skip-datacite", action="store_true", help="Skip DataCite queries")
    parser.add_argument("--skip-crossref", action="store_true", help="Skip Crossref queries")
    parser.add_argument("--log-dir", default=default_log_dir("bibliography"), help="Directory for log files")
    parser.add_argument("--decisions", help="Path to curator decision JSON to apply")
    parser.add_argument("--threshold", type=float, default=0.82, help="Acceptance threshold for confident matches")

    args = parser.parse_args()

    initialize_logger(args.log_dir)
    logger = get_logger()
    paths = OutputPaths(args.output_dir)

    dto_dir = Path(args.dto_dir)
    if not dto_dir.exists():
        raise FileNotFoundError(f"DTO directory does not exist: {dto_dir}")

    adapters: Dict[str, object] = {}
    if not args.skip_datacite:
        adapters["datacite"] = DataCiteAdapter()
    if not args.skip_crossref:
        adapters["crossref"] = CrossrefAdapter()

    engine = MatchingEngine(acceptance_threshold=args.threshold)

    results: List[Dict[str, object]] = []
    dto_cache: Dict[str, Tuple[Path, CanonicalRecordDTO]] = {}

    for dto_path in iter_dto_files(dto_dir, args.limit):
        dto = load_dto(str(dto_path))
        dto_cache[dto.fgdc_id] = (dto_path, dto)
        scored = build_candidates(dto, engine, adapters)
        candidates_payload: List[Dict[str, object]] = []
        for result in scored:
            candidate = result.candidate
            candidates_payload.append(
                {
                    "source": candidate.source,
                    "identifier": candidate.identifier,
                    "title": candidate.title,
                    "url": candidate.url,
                    "score": result.score,
                    "breakdown": result.breakdown,
                    "confidence": result.score,
                    "relation": "isAlternativeIdentifierOf",
                }
            )

        results.append(
            {
                "fgdc_id": dto.fgdc_id,
                "zenodo_title": dto.zenodo_metadata.get("title"),
                "candidates": candidates_payload,
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    candidates_path = (
        Path(paths.duplicates_reports_dir)
        / f"bibliographic_candidates_{timestamp}.json"
    )
    write_candidates_report(candidates_path, results)

    metrics_path = (
        Path(paths.metrics_reports_dir) / f"bibliographic_metrics_{timestamp}.json"
    )
    write_metrics(metrics_path, timestamp, results, engine.acceptance_threshold)

    logger.log_info(
        f"Bibliographic linkage completed for {len(results)} records; candidates saved to {candidates_path}"
    )

    decisions_path = Path(args.decisions) if args.decisions else None
    if decisions_path:
        decisions = _load_decisions(decisions_path)
        applied_at = datetime.now(timezone.utc).isoformat()
        for fgdc_id, decision_items in decisions.items():
            cached = dto_cache.get(fgdc_id)
            if not cached:
                continue
            dto_path, dto = cached
            updated = apply_decisions(dto_path, dto, decision_items, paths, applied_at=applied_at)
            dto_cache[fgdc_id] = (dto_path, updated)
        logger.log_info(
            f"Applied curator decisions from {decisions_path}"
        )


if __name__ == "__main__":
    main()

