"""Curator review CLI for bibliographic match candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from scripts.logger import get_logger, initialize_logger
from scripts.path_config import OutputPaths, default_log_dir


Decision = Dict[str, object]


def load_candidates(path: Path) -> List[Dict[str, object]]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def prompt_user(fgdc_id: str, candidate: Dict[str, object]) -> str:
    print("-" * 72)
    print(f"FGDC ID: {fgdc_id}")
    print(f"Source: {candidate.get('source')} | Score: {candidate.get('score')}")
    print(f"Identifier: {candidate.get('identifier')}")
    print(f"Title: {candidate.get('title')}")
    print(f"URL: {candidate.get('url')}")
    print(f"Breakdown: {candidate.get('breakdown')}")
    print("Decision? [a]ccept / [r]eject / [d]efer: ", end="", flush=True)
    while True:
        choice = input().strip().lower() or "d"
        if choice in {"a", "r", "d"}:
            return {"a": "accept", "r": "reject", "d": "defer"}[choice]
        print("Please enter a, r, or d: ", end="", flush=True)


def auto_decide(candidate: Dict[str, object], threshold: float) -> str:
    score = float(candidate.get("score", 0.0))
    return "accept" if score >= threshold else "defer"


def main() -> None:
    parser = argparse.ArgumentParser(description="Review bibliographic match candidates")
    parser.add_argument("candidates", help="Path to candidates JSON produced by bibliographic_linkage.py")
    parser.add_argument("--output-dir", default="output", help="Root output directory")
    parser.add_argument("--log-dir", default=default_log_dir("bibliography_review"), help="Directory for log files")
    parser.add_argument("--auto-accept", action="store_true", help="Automatically accept matches above threshold")
    parser.add_argument("--threshold", type=float, default=0.85, help="Threshold for auto-accept decisions")

    args = parser.parse_args()

    initialize_logger(args.log_dir)
    logger = get_logger()
    paths = OutputPaths(args.output_dir)

    candidate_path = Path(args.candidates)
    if not candidate_path.exists():
        raise FileNotFoundError(candidate_path)

    candidates = load_candidates(candidate_path)
    decisions: Dict[str, List[Decision]] = {}

    for record in candidates:
        fgdc_id = record.get("fgdc_id")
        record_decisions: List[Decision] = []
        for candidate in record.get("candidates", []):
            if args.auto_accept:
                decision = auto_decide(candidate, args.threshold)
            else:
                decision = prompt_user(fgdc_id, candidate)
            record_decisions.append(
                {
                    "source": candidate.get("source"),
                    "identifier": candidate.get("identifier"),
                    "title": candidate.get("title"),
                    "url": candidate.get("url"),
                    "confidence": candidate.get("confidence"),
                    "relation": candidate.get("relation"),
                    "breakdown": candidate.get("breakdown"),
                    "decision": decision,
                    "notes": None,
                }
            )
        decisions[fgdc_id] = record_decisions

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = Path(paths.duplicates_reports_dir) / f"bibliographic_decisions_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(decisions, handle, indent=2, ensure_ascii=False)

    logger.log_info(f"Curator decisions saved to {output_path}")


if __name__ == "__main__":
    main()

