"""Load controversial bills and stock exposure mappings."""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3

from src.congress_client import CongressClient
from src.controversial_bills import CONTROVERSIAL_BILL_CATALOG
from src.db_utils import SCHEMA_STOCK_PATH, get_connection, init_db

logger = logging.getLogger(__name__)


def ensure_stock_schema(conn: sqlite3.Connection) -> None:
    if SCHEMA_STOCK_PATH.exists():
        conn.executescript(SCHEMA_STOCK_PATH.read_text(encoding="utf-8"))
        conn.commit()


def parse_bill_id(bill_id: str) -> tuple[int, str, int]:
    congress, bill_type, bill_number = bill_id.split("-")
    return int(congress), bill_type, int(bill_number)


def upsert_controversial_bill(conn: sqlite3.Connection, bill_id: str, meta: dict) -> None:
    congress, bill_type, bill_number = parse_bill_id(bill_id)
    title = meta.get("title")
    conn.execute(
        """
        INSERT INTO bills (bill_id, congress, bill_type, bill_number, title, policy_area)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(bill_id) DO UPDATE SET
            title = COALESCE(excluded.title, bills.title),
            policy_area = COALESCE(excluded.policy_area, bills.policy_area)
        """,
        (bill_id, congress, bill_type, bill_number, title, meta.get("sector")),
    )
    conn.execute(
        """
        INSERT INTO controversial_bills (bill_id, controversy_tags, salience_score, notes, source)
        VALUES (?, ?, ?, ?, 'curated')
        ON CONFLICT(bill_id) DO UPDATE SET
            controversy_tags = excluded.controversy_tags,
            salience_score = excluded.salience_score
        """,
        (
            bill_id,
            json.dumps(meta.get("tags", [])),
            meta.get("salience", 1.0),
            title,
        ),
    )
    for ticker in meta.get("tickers", []):
        conn.execute(
            """
            INSERT INTO bill_stock_exposure (
                bill_id, ticker, sector, exposure_type, confidence, notes
            ) VALUES (?, ?, ?, 'direct', 0.7, ?)
            ON CONFLICT(bill_id, ticker, company_name, sector) DO NOTHING
            """,
            (bill_id, ticker.upper(), meta.get("sector"), f"curated exposure for {bill_id}"),
        )
    if meta.get("sector"):
        conn.execute(
            """
            INSERT INTO bill_stock_exposure (
                bill_id, ticker, company_name, sector, exposure_type, confidence, notes
            ) VALUES (?, NULL, NULL, ?, 'sector', 0.4, ?)
            ON CONFLICT(bill_id, ticker, company_name, sector) DO NOTHING
            """,
            (bill_id, meta.get("sector"), f"sector-level exposure for {bill_id}"),
        )


def enrich_from_congress_gov(conn: sqlite3.Connection, client: CongressClient) -> int:
    updated = 0
    for bill_id in CONTROVERSIAL_BILL_CATALOG:
        congress, bill_type, bill_number = parse_bill_id(bill_id)
        try:
            data = client.get(f"bill/{congress}/{bill_type}/{bill_number}")
            bill = data.get("bill", {})
            title = bill.get("title") or bill.get("shortTitle")
            if title:
                conn.execute(
                    "UPDATE bills SET title = ? WHERE bill_id = ?",
                    (title, bill_id),
                )
                updated += 1
        except Exception as exc:
            logger.warning("Congress.gov lookup failed for %s: %s", bill_id, exc)
    conn.commit()
    return updated


def load_controversial_bills(
    *,
    enrich_metadata: bool = True,
    init_if_missing: bool = True,
) -> dict[str, int]:
    if init_if_missing:
        init_db()

    conn = get_connection()
    try:
        ensure_stock_schema(conn)
        for bill_id, meta in CONTROVERSIAL_BILL_CATALOG.items():
            upsert_controversial_bill(conn, bill_id, meta)
        conn.commit()

        enriched = 0
        if enrich_metadata:
            client = CongressClient()
            enriched = enrich_from_congress_gov(conn, client)

        return {
            "bills_loaded": len(CONTROVERSIAL_BILL_CATALOG),
            "metadata_enriched": enriched,
        }
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load controversial bill catalog")
    parser.add_argument("--no-enrich", action="store_true")
    parser.add_argument("--no-init", action="store_true")
    args = parser.parse_args()

    stats = load_controversial_bills(
        enrich_metadata=not args.no_enrich,
        init_if_missing=not args.no_init,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
