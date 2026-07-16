"""Load bill-specific lobbying records from the LDA API.

Usage:
    python -m src.load_lobbying --year 2024 --limit-pages 10
    python -m src.load_lobbying --year 2024 --all-bills
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from pathlib import Path

from src.controversial_bills import all_controversial_bill_ids
from src.cycles import ensure_election_cycles
from src.db_utils import PROJECT_ROOT, get_connection, init_db
from src.lda_client import LDAClient
from src.lobbying_parser import parse_filing
from src.org_utils import upsert_organization

logger = logging.getLogger(__name__)
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "lobbying"


def ensure_bill_stub(conn: sqlite3.Connection, bill_id: str) -> None:
    parts = bill_id.split("-")
    if len(parts) != 3:
        return
    congress, bill_type, bill_number = parts
    conn.execute(
        """
        INSERT INTO bills (bill_id, congress, bill_type, bill_number)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(bill_id) DO NOTHING
        """,
        (bill_id, int(congress), bill_type, int(bill_number)),
    )


def get_target_bills(conn: sqlite3.Connection, *, include_controversial: bool = True) -> set[str]:
    rows = conn.execute(
        "SELECT DISTINCT bill_id FROM votes WHERE bill_id IS NOT NULL"
    ).fetchall()
    bills = {row["bill_id"] for row in rows}
    if include_controversial:
        bills.update(all_controversial_bill_ids())
        for bill_id in all_controversial_bill_ids():
            ensure_bill_stub(conn, bill_id)
    return bills


def upsert_lobbying_record(conn: sqlite3.Connection, record) -> None:
    org_id = upsert_organization(conn, record.org_name_raw, source_system="lda")
    ensure_bill_stub(conn, record.bill_id)
    conn.execute(
        """
        INSERT INTO lobbying_records (
            lobbying_id, bill_id, org_id, org_name_raw, registrant_name,
            position, position_confidence, issue_codes, filing_id,
            filing_date, cycle_id, source_system, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'lda', ?)
        ON CONFLICT(lobbying_id) DO UPDATE SET
            position = excluded.position,
            position_confidence = excluded.position_confidence,
            notes = excluded.notes
        """,
        (
            record.lobbying_id,
            record.bill_id,
            org_id,
            record.org_name_raw,
            record.registrant_name,
            record.position,
            record.position_confidence,
            record.issue_codes,
            record.filing_id,
            record.filing_date,
            record.cycle_id,
            record.notes,
        ),
    )


def load_lobbying(
    *,
    year: int = 2024,
    limit_pages: int | None = None,
    only_voted_bills: bool = True,
    cache: bool = True,
    init_if_missing: bool = True,
) -> dict[str, int]:
    if init_if_missing:
        init_db()

    cycle_id = str(year if year % 2 == 0 else year + 1)
    conn = get_connection()
    client = LDAClient()
    stats = {"filings_scanned": 0, "records_loaded": 0, "bills_matched": 0}

    if cache:
        (RAW_DIR / str(year)).mkdir(parents=True, exist_ok=True)

    try:
        ensure_election_cycles(conn, [cycle_id])
        target_bills = get_target_bills(conn) if only_voted_bills else None
        if only_voted_bills:
            logger.info("Filtering to %s bills with roll-call votes in DB", len(target_bills))
            if not target_bills:
                logger.warning("No bills in votes table — run vote loader first or pass --all-bills")

        matched_bills: set[str] = set()
        for filing in client.paginate_filings({"filing_year": year}, max_pages=limit_pages):
            stats["filings_scanned"] += 1
            if cache and stats["filings_scanned"] <= 50:
                fid = filing.get("filing_uuid", "unknown")
                (RAW_DIR / str(year) / f"{fid}.json").write_text(
                    json.dumps(filing, indent=2),
                    encoding="utf-8",
                )

            records = parse_filing(filing, target_bills=target_bills)
            for record in records:
                upsert_lobbying_record(conn, record)
                stats["records_loaded"] += 1
                matched_bills.add(record.bill_id)

            if stats["filings_scanned"] % 25 == 0:
                conn.commit()
                logger.info(
                    "Scanned %s filings, loaded %s lobbying records",
                    stats["filings_scanned"],
                    stats["records_loaded"],
                )

        conn.commit()
        stats["bills_matched"] = len(matched_bills)
    finally:
        conn.close()

    return stats


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load LDA lobbying records")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--limit-pages", type=int, default=None, help="Max API pages to scan")
    parser.add_argument(
        "--all-bills",
        action="store_true",
        help="Load all bill references (default: only bills with votes in DB)",
    )
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-init", action="store_true")
    args = parser.parse_args()

    stats = load_lobbying(
        year=args.year,
        limit_pages=args.limit_pages,
        only_voted_bills=not args.all_bills,
        cache=not args.no_cache,
        init_if_missing=not args.no_init,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
