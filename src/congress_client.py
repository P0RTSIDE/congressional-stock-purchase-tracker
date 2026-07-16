"""Congress.gov API client with pagination and rate limiting."""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

BASE_URL = "https://api.congress.gov/v3"
DEFAULT_LIMIT = 250
# Congress.gov allows 5,000/hour; stay under ~1 req/sec for safety.
MIN_REQUEST_INTERVAL = 1.0


class CongressClient:
    def __init__(self, api_key: str | None = None, min_interval: float = MIN_REQUEST_INTERVAL):
        self.api_key = api_key or os.getenv("CONGRESS_GOV_API_KEY") or "DEMO_KEY"
        self.min_interval = min_interval
        self._last_request_at = 0.0
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": self.api_key})

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._throttle()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        response = self.session.get(url, params={"format": "json", **(params or {})}, timeout=60)
        self._last_request_at = time.monotonic()
        if response.status_code == 429:
            time.sleep(60)
            return self.get(path, params)
        response.raise_for_status()
        return response.json()

    def paginate(self, path: str, results_key: str, params: dict[str, Any] | None = None):
        """Yield all items across paginated Congress.gov list endpoints."""
        offset = 0
        params = dict(params or {})
        params.setdefault("limit", DEFAULT_LIMIT)

        while True:
            page = self.get(path, {**params, "offset": offset})
            items = page.get(results_key, [])
            if not items:
                break
            yield from items

            pagination = page.get("pagination", {})
            count = pagination.get("count")
            if count is None or offset + len(items) >= count:
                break
            next_url = pagination.get("next")
            if next_url:
                parsed = urlparse(next_url)
                next_offset = parse_qs(parsed.query).get("offset", [None])[0]
                offset = int(next_offset) if next_offset is not None else offset + len(items)
            else:
                offset += len(items)

    def list_house_votes(self, congress: int, session: int):
        return self.paginate(
            f"house-vote/{congress}/{session}",
            "houseRollCallVotes",
        )

    def get_house_vote(self, congress: int, session: int, roll_number: int) -> dict[str, Any]:
        return self.get(f"house-vote/{congress}/{session}/{roll_number}")

    def get_house_vote_members(self, congress: int, session: int, roll_number: int) -> list[dict[str, Any]]:
        data = self.get(
            f"house-vote/{congress}/{session}/{roll_number}/members",
            {"limit": DEFAULT_LIMIT},
        )
        members = data.get("houseRollCallVoteMemberVotes", {}).get("results", [])
        if members:
            return members

        # Some responses may not paginate; fetch additional pages if needed.
        all_members = list(members)
        pagination = data.get("pagination", {})
        count = pagination.get("count", len(all_members))
        offset = len(all_members)
        while offset < count:
            page = self.get(
                f"house-vote/{congress}/{session}/{roll_number}/members",
                {"limit": DEFAULT_LIMIT, "offset": offset},
            )
            batch = page.get("houseRollCallVoteMemberVotes", {}).get("results", [])
            if not batch:
                break
            all_members.extend(batch)
            offset += len(batch)
        return all_members
