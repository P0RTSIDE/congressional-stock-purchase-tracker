"""Congressional stock trade data client.

Primary: CongressInvests public API (aggregated House + Senate PTRs).
Official sources: disclosures-clerk.house.gov, efts.senate.gov (see DATA_NOTES.md).
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

DEFAULT_BASE_URL = os.getenv(
    "CONGRESS_STOCK_API_URL",
    "https://congressinfor-production.up.railway.app",
)
MIN_INTERVAL = 1.0


class StockTradesClient:
    def __init__(self, base_url: str | None = None, min_interval: float = MIN_INTERVAL):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.min_interval = min_interval
        self._last_request_at = 0.0
        self.session = requests.Session()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._throttle()
        response = self.session.get(
            f"{self.base_url}/{path.lstrip('/')}",
            params=params or {},
            timeout=60,
        )
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response.json()

    def list_trades(self, *, limit: int = 200, offset: int = 0) -> dict[str, Any]:
        return self.get("trades", {"limit": limit, "offset": offset})

    def trades_by_ticker(self, ticker: str, *, chamber: str | None = None) -> dict[str, Any]:
        params = {}
        if chamber:
            params["chamber"] = chamber
        return self.get(f"trades/{ticker.upper()}", params)

    def paginate_trades(self, *, page_size: int = 200, max_pages: int | None = None):
        offset = 0
        pages = 0
        while True:
            data = self.list_trades(limit=page_size, offset=offset)
            trades = data.get("trades", [])
            if not trades:
                break
            yield from trades
            if not data.get("has_more"):
                break
            offset += len(trades)
            pages += 1
            if max_pages is not None and pages >= max_pages:
                break
