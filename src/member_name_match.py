"""Match congressional PTR filer names to bioguide_id."""

from __future__ import annotations

import sqlite3

from rapidfuzz import fuzz, process

from .legislators import LegislatorRecord, build_crosswalk, cache_legislators_json
from .db_utils import PROJECT_ROOT

LEG_CACHE = PROJECT_ROOT / "data" / "raw" / "legislators.json"

_name_index: dict[str, str] | None = None
_bioguide_index: dict[str, LegislatorRecord] | None = None


def _load_indexes() -> tuple[dict[str, str], dict[str, LegislatorRecord]]:
    global _name_index, _bioguide_index
    if _name_index is None or _bioguide_index is None:
        entries = cache_legislators_json(LEG_CACHE)
        bioguide_index, _ = build_crosswalk(entries)
        name_index: dict[str, str] = {}
        for member_id, record in bioguide_index.items():
            name_index[record.full_name.lower()] = member_id
            name_index[f"{record.first_name} {record.last_name}".lower()] = member_id
            name_index[f"{record.last_name}, {record.first_name}".lower()] = member_id
        _name_index = name_index
        _bioguide_index = bioguide_index
    return _name_index, _bioguide_index


def get_name_index() -> dict[str, str]:
    index, _ = _load_indexes()
    return index


def get_legislator_record(bioguide_id: str) -> LegislatorRecord | None:
    _, bioguide_index = _load_indexes()
    return bioguide_index.get(bioguide_id)


def match_member_name(raw_name: str, threshold: float = 88.0) -> str | None:
    """Return bioguide_id for a PTR filer name, or None."""
    if not raw_name:
        return None
    index = get_name_index()
    clean = raw_name.strip().lower()
    if clean in index:
        return index[clean]

    choices = list(index.keys())
    result = process.extractOne(clean, choices, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return index[result[0]]
    return None


def upsert_member_record(conn: sqlite3.Connection, record: LegislatorRecord) -> None:
    conn.execute(
        """
        INSERT INTO members (
            member_id, bioguide_id, lis_id, first_name, last_name, full_name,
            party, state, chamber, district, in_office, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        ON CONFLICT(member_id) DO UPDATE SET
            full_name = excluded.full_name,
            chamber = excluded.chamber,
            updated_at = datetime('now')
        """,
        (
            record.member_id,
            record.bioguide_id,
            record.lis_id,
            record.first_name,
            record.last_name,
            record.full_name,
            record.party,
            record.state,
            record.chamber,
            record.district,
        ),
    )


def resolve_member_id(conn: sqlite3.Connection, raw_name: str, threshold: float = 88.0) -> str | None:
    """Match PTR name, ensure member row exists, return bioguide_id."""
    member_id = match_member_name(raw_name, threshold=threshold)
    if not member_id:
        return None
    record = get_legislator_record(member_id)
    if record:
        upsert_member_record(conn, record)
    return member_id
