"""OpenFEC API client."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

BASE_URL = "https://api.open.fec.gov/v1"
MIN_REQUEST_INTERVAL = 0.5  # 1,000/hour default key


class OpenFECClient:
    def __init__(self, api_key: str | None = None, min_interval: float = MIN_REQUEST_INTERVAL):
        self.api_key = api_key or os.getenv("OPENFEC_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENFEC_API_KEY is required")
        self.min_interval = min_interval
        self._last_request_at = 0.0
        self.session = requests.Session()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._throttle()
        query = {"api_key": self.api_key, **(params or {})}
        response = self.session.get(f"{BASE_URL}/{path.lstrip('/')}", params=query, timeout=60)
        self._last_request_at = time.monotonic()
        if response.status_code == 429:
            time.sleep(60)
            return self.get(path, params)
        response.raise_for_status()
        return response.json()

    def paginate(self, path: str, params: dict[str, Any] | None = None, max_pages: int | None = None):
        page = 1
        params = dict(params or {})
        params.setdefault("per_page", 100)

        while True:
            data = self.get(path, {**params, "page": page})
            results = data.get("results", [])
            if not results:
                break
            yield from results

            pagination = data.get("pagination", {})
            if page >= pagination.get("pages", page):
                break
            if max_pages is not None and page >= max_pages:
                break
            page += 1

    def principal_committee_id(self, candidate_id: str, cycle: int) -> str | None:
        data = self.get(f"candidate/{candidate_id}/committees/", {"cycle": cycle})
        committees = data.get("results", [])
        principal = [c for c in committees if c.get("designation") == "P"]
        if principal:
            return principal[0]["committee_id"]
        return committees[0]["committee_id"] if committees else None
