"""LDA (lobbying disclosure) API client."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

BASE_URL = "https://lda.senate.gov/api/v1"
MIN_REQUEST_INTERVAL = 0.5  # 120/min with API key


class LDAClient:
    def __init__(self, api_key: str | None = None, min_interval: float = MIN_REQUEST_INTERVAL):
        self.api_key = api_key or os.getenv("LDA_API_KEY", "")
        self.min_interval = min_interval
        self._last_request_at = 0.0
        self.session = requests.Session()
        if self.api_key:
            self.session.headers["Authorization"] = f"Token {self.api_key}"

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._throttle()
        response = self.session.get(f"{BASE_URL}/{path.lstrip('/')}", params=params or {}, timeout=60)
        self._last_request_at = time.monotonic()
        if response.status_code == 429:
            time.sleep(60)
            return self.get(path, params)
        response.raise_for_status()
        return response.json()

    def paginate_filings(self, params: dict[str, Any] | None = None, max_pages: int | None = None):
        page = 1
        params = dict(params or {})
        params.setdefault("page_size", 25)

        while True:
            data = self.get("filings/", {**params, "page": page})
            results = data.get("results", [])
            if not results:
                break
            yield from results

            if not data.get("next"):
                break
            if max_pages is not None and page >= max_pages:
                break
            page += 1
