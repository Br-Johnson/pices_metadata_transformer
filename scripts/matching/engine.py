"""Shared matching utilities for bibliographic linkage workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from scripts.dto import CanonicalRecordDTO


_WHITESPACE_RE = re.compile(r"\s+")


def _normalise_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = _WHITESPACE_RE.sub(" ", value)
    return value


def _sequence_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _creator_similarity(record_creators: Sequence[str], candidate_creators: Sequence[str]) -> float:
    if not record_creators or not candidate_creators:
        return 0.0
    record_norm = {_normalise_text(name) for name in record_creators if name}
    candidate_norm = {_normalise_text(name) for name in candidate_creators if name}
    if not record_norm or not candidate_norm:
        return 0.0
    overlap = record_norm & candidate_norm
    union = record_norm | candidate_norm
    return len(overlap) / len(union)


@dataclass
class MatchCandidate:
    """Normalised external record returned by search adapters."""

    source: str
    identifier: Optional[str]
    title: str
    creators: Sequence[str] = field(default_factory=list)
    abstract: Optional[str] = None
    url: Optional[str] = None
    published: Optional[str] = None
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class MatchResult:
    """Scored bibliographic match candidate."""

    candidate: MatchCandidate
    score: float
    breakdown: Mapping[str, float]


class MatchingEngine:
    """Compute fuzzy similarity scores between records and external candidates."""

    def __init__(
        self,
        title_weight: float = 0.6,
        abstract_weight: float = 0.25,
        creator_weight: float = 0.15,
        acceptance_threshold: float = 0.8,
    ) -> None:
        self.title_weight = title_weight
        self.abstract_weight = abstract_weight
        self.creator_weight = creator_weight
        total = title_weight + abstract_weight + creator_weight
        if total == 0:
            raise ValueError("Weights must sum to a positive number")
        self.normalised_weights = (
            title_weight / total,
            abstract_weight / total,
            creator_weight / total,
        )
        self.acceptance_threshold = acceptance_threshold

    def score_candidates(
        self,
        record: CanonicalRecordDTO,
        candidates: Sequence[MatchCandidate],
    ) -> List[MatchResult]:
        """Return scored candidates sorted by highest similarity."""

        record_title = _normalise_text(record.zenodo_metadata.get("title"))
        record_description = _normalise_text(record.zenodo_metadata.get("description"))
        record_creators = [creator.get("name") for creator in record.zenodo_metadata.get("creators", [])]

        results: List[MatchResult] = []
        for candidate in candidates:
            title_score = _sequence_similarity(record_title, _normalise_text(candidate.title))
            abstract_score = _sequence_similarity(record_description, _normalise_text(candidate.abstract))
            creators_score = _creator_similarity(record_creators, candidate.creators)

            weighted_score = (
                title_score * self.normalised_weights[0]
                + abstract_score * self.normalised_weights[1]
                + creators_score * self.normalised_weights[2]
            )

            breakdown = {
                "title": round(title_score, 4),
                "abstract": round(abstract_score, 4),
                "creators": round(creators_score, 4),
            }

            results.append(
                MatchResult(
                    candidate=candidate,
                    score=round(weighted_score, 4),
                    breakdown=breakdown,
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return results

    def filter_confident(self, results: Iterable[MatchResult]) -> List[MatchResult]:
        """Return results that meet or exceed the acceptance threshold."""

        confident = [result for result in results if result.score >= self.acceptance_threshold]
        confident.sort(key=lambda item: item.score, reverse=True)
        return confident

