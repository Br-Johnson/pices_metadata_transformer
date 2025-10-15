"""Prepare DTO summaries for LLM-assisted curator review."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dto import load_dto
from scripts.fgdc_utils import load_fgdc_xml
from scripts.logger import get_logger, initialize_logger
from scripts.path_config import OutputPaths, default_log_dir


def summarise_record(dto_path: Path, paths: OutputPaths) -> Dict[str, object]:
    dto = load_dto(str(dto_path))
    fgdc_content, fgdc_path = load_fgdc_xml(dto.fgdc_id, paths)
    fgdc_excerpt = None
    if fgdc_content:
        fgdc_excerpt = fgdc_content[:800]

    creators = [creator.get("name") for creator in dto.zenodo_metadata.get("creators", []) if creator.get("name")]
    anomalies = dto.quality.enhanced_metrics.get("anomalies")

    return {
        "fgdc_id": dto.fgdc_id,
        "title": dto.zenodo_metadata.get("title"),
        "description": dto.zenodo_metadata.get("description"),
        "creators": creators,
        "keywords": dto.zenodo_metadata.get("keywords", []),
        "publisher": dto.zenodo_metadata.get("publisher"),
        "bibliographic_links": [link.to_json() for link in dto.bibliographic_links],
        "quality": dto.quality.to_json(),
        "fgdc_excerpt": fgdc_excerpt,
        "fgdc_path": fgdc_path,
        "notes": dto.zenodo_metadata.get("notes"),
        "anomalies": anomalies,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate review set for LLM QA")
    parser.add_argument("--dto-dir", default="output/data/dto", help="Directory containing DTO files")
    parser.add_argument("--limit", type=int, help="Limit number of records")
    parser.add_argument("--log-dir", default=default_log_dir("review"), help="Log directory")
    parser.add_argument("--output", help="Override output path")

    args = parser.parse_args()

    initialize_logger(args.log_dir)
    logger = get_logger()
    paths = OutputPaths("output")

    dto_dir = Path(args.dto_dir)
    dto_files = sorted(dto_dir.glob("*.json"))
    if args.limit is not None:
        dto_files = dto_files[: args.limit]

    summaries: List[Dict[str, object]] = []
    for dto_file in dto_files:
        summaries.append(summarise_record(dto_file, paths))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(paths.review_reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = output_dir / f"creator_anomalies_input_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2, ensure_ascii=False)

    logger.log_info(f"Review set written to {output_path}")


if __name__ == "__main__":
    main()

