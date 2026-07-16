"""Load congressional stock trades (PTR data)."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sqlite3
from pathlib import Path

from src.db_utils import PROJECT_ROOT, SCHEMA_STOCK_PATH, get_connection, init_db
from src.member_name_match import match_member_name, resolve_member_id
from src.stock_client import StockTradesClient

logger = logging.getLogger(__name__)
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "stock_trades"


def ensure_stock_schema(conn: sqlite3.Connection) -> None:
    if SCHEMA_STOCK_PATH.exists():
        conn.executescript(SCHEMA_STOCK_PATH.read_text(encoding="utf-8"))
        conn.commit()


def parse_amount_range(amount_raw: str) -> tuple[float | None, float | None]:
    if not amount_raw:
        return None, None
    nums = re.findall(r"\$?([\d,]+)", amount_raw.replace("\n", " "))
    values = [float(n.replace(",", "")) for n in nums if n]
    if not values:
        return None, None
    if len(values) >= 2:
        return min(values[0], values[1]), max(values[0], values[1])
    return values[0], values[0]


def normalize_trade_type(raw: str) -> str:
    value = (raw or "").strip().lower()
    if value in ("buy", "purchase"):
        return "purchase"
    if value in ("sell", "sale"):
        return "sale"
    if value == "exchange":
        return "exchange"
    return "other"


def normalize_chamber(raw: str) -> str | None:
    value = (raw or "").strip().lower()
    if value == "house":
        return "house"
    if value == "senate":
        return "senate"
    return None


def upsert_trade(conn: sqlite3.Connection, trade: dict) -> str | None:
    member_name = trade.get("member", "").strip()
    if not member_name:
        return None

    member_id = resolve_member_id(conn, member_name)
    ticker = (trade.get("ticker") or "").strip().upper() or None
    tx_date = (trade.get("tx_date") or "")[:10]
    if not tx_date:
        return None

    amount_min, amount_max = parse_amount_range(trade.get("amount", ""))
    tx_type = normalize_trade_type(trade.get("trade_type", ""))
    transaction_id = hashlib.md5(
        f"{member_name}|{ticker}|{tx_date}|{tx_type}|{trade.get('asset','')}".encode("utf-8")
    ).hexdigest()

    conn.execute(
        """
        INSERT INTO stock_transactions (
            transaction_id, member_id, member_name_raw, chamber, ticker, asset_name,
            transaction_type, transaction_date, disclosed_date, amount_min, amount_max,
            amount_raw, source_system, source_url, ptr_year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'congressinvests', ?, ?)
        ON CONFLICT(transaction_id) DO UPDATE SET
            member_id = COALESCE(excluded.member_id, stock_transactions.member_id),
            disclosed_date = COALESCE(excluded.disclosed_date, stock_transactions.disclosed_date)
        """,
        (
            transaction_id,
            member_id,
            member_name,
            normalize_chamber(trade.get("chamber", "")),
            ticker,
            trade.get("asset"),
            tx_type,
            tx_date,
            (trade.get("disclosed") or "")[:10] or None,
            amount_min,
            amount_max,
            trade.get("amount"),
            trade.get("link"),
            int(tx_date[:4]) if tx_date else None,
        ),
    )
    return transaction_id


def load_stock_trades(
    *,
    max_pages: int = 30,
    cache: bool = True,
    init_if_missing: bool = True,
) -> dict[str, int]:
    if init_if_missing:
        init_db()

    client = StockTradesClient()
    conn = get_connection()
    stats = {"trades_loaded": 0, "members_matched": 0, "unmatched_members": 0}

    if cache:
        RAW_DIR.mkdir(parents=True, exist_ok=True)

    try:
        ensure_stock_schema(conn)
        matched_members: set[str] = set()
        batch: list[dict] = []

        for trade in client.paginate_trades(page_size=200, max_pages=max_pages):
            batch.append(trade)
            tid = upsert_trade(conn, trade)
            if tid:
                stats["trades_loaded"] += 1
                if trade.get("member"):
                    mid = resolve_member_id(conn, trade["member"])
                    if mid:
                        matched_members.add(mid)

            if len(batch) >= 500:
                conn.commit()
                batch.clear()

        conn.commit()
        stats["members_matched"] = len(matched_members)

        if cache:
            (RAW_DIR / "trades_snapshot.json").write_text(
                json.dumps({"count": stats["trades_loaded"]}, indent=2),
                encoding="utf-8",
            )
    finally:
        conn.close()

    return stats


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load congressional stock trades (PTR)")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--no-init", action="store_true")
    args = parser.parse_args()

    stats = load_stock_trades(
        max_pages=args.max_pages,
        cache=not args.no_cache,
        init_if_missing=not args.no_init,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
