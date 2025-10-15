"""Adapter for querying Crossref for bibliographic matches."""

from __future__ import annotations

import time
from typing import List, Optional, Sequence

import requests

from scripts.logger import get_logger

from .engine import MatchCandidate


class CrossrefAdapter:
    BASE_URL = "https://api.crossref.org/works"

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        rows: int = 20,
        pause_seconds: float = 1.0,
    ) -> None:
        self.session = session or requests.Session()
        self.rows = max(1, min(rows, 100))
        self.pause_seconds = max(0.1, pause_seconds)
        self.logger = get_logger()

    def search(
        self,
        title: str,
        creators: Sequence[str],
        abstract: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> List[MatchCandidate]:
        params = {
            "query.bibliographic": title,
            "rows": self.rows,
        }
        if cursor:
            params["cursor"] = cursor

        self.logger.log_info(
            f"Crossref search title='{title[:60]}' rows={self.rows} cursor={'yes' if cursor else 'no'}"
        )

        response = self.session.get(self.BASE_URL, params=params, timeout=30)
        if response.status_code == 429:
            self.logger.log_info(
                f"Crossref rate limit encountered; sleeping {self.pause_seconds} seconds"
            )
            time.sleep(self.pause_seconds)
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        payload = response.json()
        items = payload.get("message", {}).get("items", [])
        matches = [self._normalise_item(item) for item in items]
        return [match for match in matches if match is not None]

    @staticmethod
    def _normalise_item(item: dict) -> Optional[MatchCandidate]:
        title_list = item.get("title") or []
        title = title_list[0] if title_list else None
        if not title:
            return None

        creators = []
        for author in item.get("author", []) or []:
            name_parts = [author.get("given"), author.get("family")]
            creators.append(" ".join(part for part in name_parts if part))

        abstract = item.get("abstract")
        doi = item.get("DOI")
        url = item.get("URL")
        published = None
        if "published-print" in item:
            date_parts = item["published-print"].get("date-parts")
            if date_parts:
                published = "-".join(str(p) for p in date_parts[0])
        elif "created" in item:
            date_parts = item["created"].get("date-parts")
            if date_parts:
                published = "-".join(str(p) for p in date_parts[0])

        return MatchCandidate(
            source="crossref",
            identifier=f"https://doi.org/{doi}" if doi else url,
            title=title,
            creators=creators,
            abstract=abstract,
            url=url,
            published=published,
            extra={"raw": item},
        )

