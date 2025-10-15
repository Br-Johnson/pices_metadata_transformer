"""LLM-assisted review CLI for curator annotations."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.logger import get_logger, initialize_logger
from scripts.path_config import OutputPaths, default_log_dir

PROMPT_TEMPLATE = """You are auditing metadata for FGDC {fgdc_id}.\n\nTitle: {title}\nCreators: {creators}\nDescription: {description}\nExisting Notes: {notes}\nBibliographic Links: {links}\nFGDC Excerpt:\n{excerpt}\n\nIdentify creator/contributor anomalies, placeholder text, or bibliographic conflicts. Provide recommended remediation steps."""


def load_review_set(path: Path) -> List[Dict[str, object]]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record observations from LLM review")
    parser.add_argument("review_set", help="Input JSON produced by extract_review_set.py")
    parser.add_argument("--output-dir", default="output", help="Root output directory")
    parser.add_argument("--log-dir", default=default_log_dir("review"), help="Log directory")
    parser.add_argument("--auto", action="store_true", help="Generate placeholder observations without prompting")

    args = parser.parse_args()

    initialize_logger(args.log_dir)
    logger = get_logger()
    paths = OutputPaths(args.output_dir)

    review_path = Path(args.review_set)
    if not review_path.exists():
        raise FileNotFoundError(review_path)

    bundle = load_review_set(review_path)
    observations: Dict[str, Dict[str, object]] = {}

    for record in bundle:
        fgdc_id = record.get("fgdc_id")
        prompt = PROMPT_TEMPLATE.format(
            fgdc_id=fgdc_id,
            title=record.get("title"),
            creators=", ".join(record.get("creators") or []),
            description=record.get("description"),
            notes=record.get("notes"),
            links=", ".join(link.get("identifier", "") for link in record.get("bibliographic_links", [])),
            excerpt=record.get("fgdc_excerpt") or "(FGDC XML unavailable)",
        )

        if args.auto:
            observation_text = "AUTO: Review pending"
        else:
            print("-" * 80)
            print(prompt)
            print("Observation (press Enter for defer): ", end="", flush=True)
            observation_text = input().strip() or "DEFERRED"

        observations[fgdc_id] = {
            "prompt": prompt,
            "observation": observation_text,
        }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(paths.review_reports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"creator_anomalies_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(observations, handle, indent=2, ensure_ascii=False)

    logger.log_info(f"Recorded observations saved to {output_path}")


if __name__ == "__main__":
    main()

