"""Load legislator crosswalks from unitedstates/congress-legislators."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

CURRENT_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
HISTORICAL_URL = "https://unitedstates.github.io/congress-legislators/legislators-historical.json"


@dataclass
class LegislatorRecord:
    member_id: str
    bioguide_id: str
    lis_id: str | None
    first_name: str
    last_name: str
    full_name: str
    party: str | None
    state: str | None
    chamber: str
    district: str | None


def _normalize_party(party: str | None) -> str | None:
    if not party:
        return None
    party = party.strip()
    mapping = {
        "Democrat": "D",
        "Republican": "R",
        "Independent": "I",
        "Libertarian": "L",
        "D": "D",
        "R": "R",
        "I": "I",
    }
    return mapping.get(party, party[:1].upper() if party else None)


def _term_chamber(term_type: str) -> str:
    return "senate" if term_type == "sen" else "house"


def _pick_term(terms: list[dict[str, Any]], on_date: date | None = None) -> dict[str, Any] | None:
    if not terms:
        return None
    if on_date is None:
        return terms[-1]

    for term in reversed(terms):
        start = term.get("start")
        end = term.get("end")
        if not start:
            continue
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end) if end else date.max
        if start_d <= on_date <= end_d:
            return term
    return terms[-1]


def _record_from_entry(entry: dict[str, Any], on_date: date | None = None) -> LegislatorRecord | None:
    ids = entry.get("id", {})
    bioguide = ids.get("bioguide")
    if not bioguide:
        return None

    name = entry.get("name", {})
    first_name = name.get("first") or ""
    last_name = name.get("last") or ""
    full_name = name.get("official_full") or f"{first_name} {last_name}".strip()

    term = _pick_term(entry.get("terms", []), on_date)
    if not term:
        return None

    return LegislatorRecord(
        member_id=bioguide,
        bioguide_id=bioguide,
        lis_id=ids.get("lis"),
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        party=_normalize_party(term.get("party")),
        state=term.get("state"),
        chamber=_term_chamber(term.get("type", "rep")),
        district=str(term["district"]) if term.get("district") is not None else None,
    )


def download_legislators() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for url in (CURRENT_URL, HISTORICAL_URL):
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        records.extend(response.json())
    return records


def build_crosswalk(
    entries: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, LegislatorRecord], dict[str, str]]:
    """Return (bioguide_index, lis_to_bioguide)."""
    if entries is None:
        entries = download_legislators()

    bioguide_index: dict[str, LegislatorRecord] = {}
    lis_to_bioguide: dict[str, str] = {}

    for entry in entries:
        record = _record_from_entry(entry)
        if not record:
            continue
        bioguide_index[record.bioguide_id] = record
        if record.lis_id:
            lis_to_bioguide[record.lis_id] = record.bioguide_id

    return bioguide_index, lis_to_bioguide


def cache_legislators_json(cache_path) -> list[dict[str, Any]]:
    """Download and cache legislators JSON; reuse cache when present."""
    from pathlib import Path

    path = Path(cache_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    records = download_legislators()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    return records
