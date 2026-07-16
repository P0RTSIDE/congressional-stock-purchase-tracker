"""Load member donor profiles via OpenFEC API.

Aggregates organizational contributions to each member's principal campaign
committee for a given cycle, then materializes member_donor_profiles.

Usage:
    python -m src.load_donors --cycle 2024 --limit 5
    python -m src.load_donors --cycle 2024
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.cycles import ensure_election_cycles
from src.db_utils import PROJECT_ROOT, get_connection, init_db
from src.legislators import cache_legislators_json
from src.openfec_client import OpenFECClient
from src.org_utils import upsert_organization

logger = logging.getLogger(__name__)

LEG_CACHE = PROJECT_ROOT / "data" / "raw" / "legislators.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "donors"


def pick_fec_candidate_id(entry: dict[str, Any]) -> str | None:
    ids = entry.get("id", {})
    fec = ids.get("fec")
    if not fec:
        return None
    if isinstance(fec, list):
        return fec[0] if fec else None
    return fec


def sync_member_fec_ids(conn: sqlite3.Connection) -> int:
    entries = cache_legislators_json(LEG_CACHE)
    updated = 0
    for entry in entries:
        bioguide = entry.get("id", {}).get("bioguide")
        fec_id = pick_fec_candidate_id(entry)
        if not bioguide or not fec_id:
            continue
        cursor = conn.execute(
            """
            UPDATE members
            SET fec_candidate_id = ?, updated_at = datetime('now')
            WHERE member_id = ?
            """,
            (fec_id, bioguide),
        )
        updated += cursor.rowcount
    conn.commit()
    return updated


def get_target_members(conn: sqlite3.Connection, limit: int | None = None) -> list[sqlite3.Row]:
    sql = """
        SELECT DISTINCT m.member_id, m.full_name, m.fec_candidate_id, m.chamber
        FROM members m
        JOIN member_votes mv ON mv.member_id = m.member_id
        WHERE m.fec_candidate_id IS NOT NULL
        ORDER BY m.full_name
    """
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def aggregate_committee_contributions(
    client: OpenFECClient,
    committee_id: str,
    cycle: int,
    *,
    max_pages: int = 15,
) -> dict[str, dict[str, Any]]:
    """Aggregate organizational contributions by contributor_name."""
    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"amount": 0.0, "count": 0, "dates": []}
    )

    for record in client.paginate(
        "schedules/schedule_a/",
        {
            "committee_id": committee_id,
            "two_year_transaction_period": cycle,
            "is_individual": "false",
            "sort": "-contribution_receipt_date",
        },
        max_pages=max_pages,
    ):
        name = (record.get("contributor_name") or "").strip()
        amount = record.get("contribution_receipt_amount") or 0.0
        if not name or not amount:
            continue
        totals[name]["amount"] += float(amount)
        totals[name]["count"] += 1
        if record.get("contribution_receipt_date"):
            totals[name]["dates"].append(record["contribution_receipt_date"])

    return totals


def load_member_donors(
    conn: sqlite3.Connection,
    client: OpenFECClient,
    *,
    cycle: int,
    member_limit: int | None = None,
    max_pages: int = 15,
    top_n: int = 20,
    cache: bool = True,
) -> dict[str, int]:
    ensure_election_cycles(conn, [str(cycle)])
    cycle_id = str(cycle)
    stats = {
        "members_processed": 0,
        "members_skipped": 0,
        "contributions": 0,
        "profiles": 0,
    }

    if cache:
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    members = get_target_members(conn, member_limit)
    for member in members:
        fec_id = member["fec_candidate_id"]
        committee_id = client.principal_committee_id(fec_id, cycle)
        if not committee_id:
            stats["members_skipped"] += 1
            logger.warning("No committee for %s (%s)", member["full_name"], fec_id)
            continue

        aggregated = aggregate_committee_contributions(
            client, committee_id, cycle, max_pages=max_pages
        )
        if cache:
            cache_path = RAW_DIR / f"{member['member_id']}_{cycle}.json"
            cache_path.write_text(json.dumps(aggregated, indent=2), encoding="utf-8")

        ranked = sorted(aggregated.items(), key=lambda kv: kv[1]["amount"], reverse=True)[:top_n]

        # Replace existing cycle rows for this member
        conn.execute(
            "DELETE FROM contributions WHERE member_id = ? AND cycle_id = ? AND source_system = 'openfec'",
            (member["member_id"], cycle_id),
        )
        conn.execute(
            "DELETE FROM member_donor_profiles WHERE member_id = ? AND cycle_id = ?",
            (member["member_id"], cycle_id),
        )

        for rank, (donor_name, meta) in enumerate(ranked, start=1):
            org_id = upsert_organization(conn, donor_name, source_system="openfec")
            contribution_id = hashlib.md5(
                f"{member['member_id']}|{cycle_id}|{donor_name}".encode("utf-8")
            ).hexdigest()
            conn.execute(
                """
                INSERT INTO contributions (
                    contribution_id, member_id, org_id, donor_org_raw,
                    amount, contribution_date, cycle_id, source_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'openfec')
                """,
                (
                    contribution_id,
                    member["member_id"],
                    org_id,
                    donor_name,
                    meta["amount"],
                    meta["dates"][0] if meta["dates"] else None,
                    cycle_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO member_donor_profiles (
                    member_id, cycle_id, org_id, donor_org_raw,
                    total_amount, contribution_count, rank_by_amount, top_n
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    member["member_id"],
                    cycle_id,
                    org_id,
                    donor_name,
                    meta["amount"],
                    meta["count"],
                    rank,
                    top_n,
                ),
            )
            stats["contributions"] += 1
            stats["profiles"] += 1

        stats["members_processed"] += 1
        conn.commit()
        logger.info(
            "Loaded %s top donors for %s",
            len(ranked),
            member["full_name"],
        )

    return stats


def load_donors(
    *,
    cycle: int = 2024,
    member_limit: int | None = None,
    max_pages: int = 15,
    top_n: int = 20,
    cache: bool = True,
    init_if_missing: bool = True,
) -> dict[str, int]:
    if init_if_missing:
        init_db()

    conn = get_connection()
    client = OpenFECClient()
    try:
        sync_member_fec_ids(conn)
        return load_member_donors(
            conn,
            client,
            cycle=cycle,
            member_limit=member_limit,
            max_pages=max_pages,
            top_n=top_n,
            cache=cache,
        )
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load donor profiles from OpenFEC")
    parser.add_argument("--cycle", type=int, default=2024)
    parser.add_argument("--limit", type=int, default=None, help="Max members to process")
    parser.add_argument("--max-pages", type=int, default=15, help="OpenFEC pages per member committee")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-init", action="store_true")
    args = parser.parse_args()

    stats = load_donors(
        cycle=args.cycle,
        member_limit=args.limit,
        max_pages=args.max_pages,
        top_n=args.top_n,
        cache=not args.no_cache,
        init_if_missing=not args.no_init,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
