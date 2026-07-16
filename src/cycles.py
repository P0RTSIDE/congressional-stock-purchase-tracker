"""Election cycle helpers."""

from __future__ import annotations

import sqlite3

# FEC two-year cycles used as cycle_id (even year ending the cycle).
CYCLE_DEFS: dict[str, dict[str, str]] = {
    "2022": {"cycle_label": "2021-2022", "start_date": "2021-01-03", "end_date": "2022-12-31"},
    "2024": {"cycle_label": "2023-2024", "start_date": "2023-01-03", "end_date": "2024-12-31"},
    "2026": {"cycle_label": "2025-2026", "start_date": "2025-01-03", "end_date": "2026-12-31"},
}


def congress_for_year(year: int) -> int:
    """Map calendar year to Congress number (118th for 2023-2024)."""
    return (year - 1787) // 2


def ensure_election_cycles(conn: sqlite3.Connection, cycle_ids: list[str] | None = None) -> None:
    targets = cycle_ids or list(CYCLE_DEFS.keys())
    for cycle_id in targets:
        meta = CYCLE_DEFS.get(cycle_id)
        if not meta:
            continue
        conn.execute(
            """
            INSERT INTO election_cycles (cycle_id, cycle_label, start_date, end_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cycle_id) DO NOTHING
            """,
            (cycle_id, meta["cycle_label"], meta["start_date"], meta["end_date"]),
        )
    conn.commit()
