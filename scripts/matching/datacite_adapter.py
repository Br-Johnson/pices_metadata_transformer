"""Adapter for querying the DataCite REST API for potential duplicates."""

from __future__ import annotations

import time
from typing import List, Optional, Sequence

import requests

from scripts.logger import get_logger

from .engine import MatchCandidate


class DataCiteAdapter:
    """Query the DataCite API while respecting rate limits and paging."""

    BASE_URL = "https://api.datacite.org/works"

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        rows: int = 25,
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
        """Search DataCite for works similar to the provided metadata."""

        params = {
            "query": self._build_query(title, creators, abstract),
            "page[size]": self.rows,
        }
        if cursor:
            params["page[cursor]"] = cursor

        self.logger.log_info(
            f"DataCite search title='{title[:60]}' rows={self.rows} cursor={'yes' if cursor else 'no'}"
        )

        response = self.session.get(self.BASE_URL, params=params, timeout=30)
        if response.status_code == 429:
            self.logger.log_info(
                f"DataCite rate limit encountered; sleeping {self.pause_seconds} seconds"
            )
            time.sleep(self.pause_seconds)
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        payload = response.json()
        data = payload.get("data", [])
        matches = [self._normalise_item(item) for item in data]
        return [match for match in matches if match is not None]

    @staticmethod
    def _build_query(title: str, creators: Sequence[str], abstract: Optional[str]) -> str:
        parts: List[str] = []
        title = title or ""
        parts.append(f"title:\"{title}\"")
        for creator in creators:
            if creator:
                parts.append(f"creator.name:\"{creator}\"")
        if abstract:
            parts.append(abstract[:120])
        return " ".join(parts)

    @staticmethod
    def _normalise_item(item: dict) -> Optional[MatchCandidate]:
        attributes = item.get("attributes") or {}
        titles = attributes.get("titles") or []
        title = titles[0].get("title") if titles else None
        if not title:
            return None

        creators = [creator.get("name") for creator in attributes.get("creators") or [] if creator.get("name")]
        descriptions = attributes.get("descriptions") or []
        description = None
        if descriptions:
            description = descriptions[0].get("description")
        identifier = attributes.get("doi") or item.get("id")
        url = attributes.get("url")
        published = attributes.get("published") or attributes.get("publicationYear")

        return MatchCandidate(
            source="datacite",
            identifier=identifier,
            title=title,
            creators=creators,
            abstract=description,
            url=url,
            published=str(published) if published else None,
            extra={"raw": attributes},
        )

