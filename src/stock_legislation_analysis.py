"""Stock–legislation timing analysis (associational only).

Flags temporal associations between PTR stock trades and roll-call votes on
bills with curated stock exposure mappings. Does NOT assert insider trading,
wrongdoing, or causal influence.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .controversial_bills import AI_FOCUS_TAGS, bills_matching_tags
from .db_utils import PROJECT_ROOT, SCHEMA_STOCK_PATH, get_connection

logger = logging.getLogger(__name__)

REPORTS_DIR = PROJECT_ROOT / "reports" / "figures"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# PTR disclosure brackets: $15,001+ = above lowest tier; $50,001+ = "large"
LARGE_TRADE_MIN = 50_001
SUBSTANTIAL_TRADE_MIN = 15_001

SIGNAL_QUERY = """
SELECT
    mv.member_vote_id,
    mv.member_id,
    m.full_name AS member_name,
    mv.vote_id,
    v.bill_id,
    b.title AS bill_title,
    cb.controversy_tags,
    st.transaction_id,
    st.ticker,
    st.transaction_type,
    st.transaction_date,
    v.vote_date,
    CAST(julianday(v.vote_date) - julianday(st.transaction_date) AS INTEGER) AS days_before_vote,
    bse.exposure_type,
    st.amount_min,
    st.amount_max,
    COALESCE(mv.is_cross_party, cf.is_cross_party, 0) AS is_cross_party,
    mv.party_at_vote,
    mv.position AS vote_position
FROM member_votes mv
JOIN votes v ON mv.vote_id = v.vote_id
JOIN members m ON mv.member_id = m.member_id
JOIN bill_stock_exposure bse ON bse.bill_id = v.bill_id
JOIN stock_transactions st ON st.member_id = mv.member_id
    AND st.ticker IS NOT NULL
    AND bse.ticker IS NOT NULL
    AND UPPER(st.ticker) = UPPER(bse.ticker)
LEFT JOIN controversial_bills cb ON cb.bill_id = v.bill_id
LEFT JOIN v_cross_party_flags cf ON cf.member_vote_id = mv.member_vote_id
JOIN bills b ON b.bill_id = v.bill_id
WHERE v.bill_id IS NOT NULL
  AND st.transaction_date <= v.vote_date
  AND st.transaction_date >= date(v.vote_date, ?)
  AND cb.bill_id IS NOT NULL
"""


@dataclass
class StockSignal:
    member_vote_id: int
    member_id: str
    member_name: str
    vote_id: str
    bill_id: str
    bill_title: str | None
    transaction_id: str
    ticker: str | None
    transaction_type: str
    transaction_date: str
    vote_date: str
    days_before_vote: int
    exposure_type: str | None
    signal_types: list[str] = field(default_factory=list)
    is_cross_party: bool = False
    party_at_vote: str = ""
    vote_position: str = ""
    amount_min: float | None = None
    amount_max: float | None = None


def ensure_stock_schema(conn: sqlite3.Connection) -> None:
    if SCHEMA_STOCK_PATH.exists():
        conn.executescript(SCHEMA_STOCK_PATH.read_text(encoding="utf-8"))
        conn.commit()


def _is_large_trade(amount_min: float | None, amount_max: float | None) -> bool:
    if amount_max is not None and amount_max >= LARGE_TRADE_MIN:
        return True
    if amount_min is not None and amount_min >= LARGE_TRADE_MIN:
        return True
    return False


def _is_substantial_trade(amount_min: float | None, amount_max: float | None) -> bool:
    if _is_large_trade(amount_min, amount_max):
        return True
    if amount_max is not None and amount_max >= SUBSTANTIAL_TRADE_MIN:
        return True
    if amount_min is not None and amount_min >= SUBSTANTIAL_TRADE_MIN:
        return True
    return False


def classify_signal_types(
    transaction_type: str,
    amount_min: float | None,
    amount_max: float | None,
) -> list[str]:
    signals: list[str] = []
    tx = (transaction_type or "").lower()
    if tx == "purchase":
        signals.append("purchase_before_vote")
        if _is_large_trade(amount_min, amount_max):
            signals.append("large_purchase")
    elif tx == "sale":
        signals.append("sale_before_vote")
        if _is_large_trade(amount_min, amount_max):
            signals.append("large_sale")
    return signals


def fetch_candidate_rows(
    conn: sqlite3.Connection,
    *,
    window_days: int = 90,
    controversial_only: bool = True,
    focus_tags: set[str] | frozenset[str] | None = None,
) -> list[sqlite3.Row]:
    window_param = f"-{window_days} days"
    query = SIGNAL_QUERY
    if not controversial_only:
        query = query.replace("  AND cb.bill_id IS NOT NULL\n", "")

    rows = conn.execute(query, (window_param,)).fetchall()
    if not focus_tags:
        return rows

    allowed_bills = set(bills_matching_tags(focus_tags))
    return [row for row in rows if row["bill_id"] in allowed_bills]


def build_signals(rows: list[sqlite3.Row]) -> list[StockSignal]:
    signals: list[StockSignal] = []
    for row in rows:
        types = classify_signal_types(
            row["transaction_type"],
            row["amount_min"],
            row["amount_max"],
        )
        if not types:
            continue
        signals.append(
            StockSignal(
                member_vote_id=row["member_vote_id"],
                member_id=row["member_id"],
                member_name=row["member_name"],
                vote_id=row["vote_id"],
                bill_id=row["bill_id"],
                bill_title=row["bill_title"],
                transaction_id=row["transaction_id"],
                ticker=row["ticker"],
                transaction_type=row["transaction_type"],
                transaction_date=row["transaction_date"],
                vote_date=row["vote_date"],
                days_before_vote=row["days_before_vote"],
                exposure_type=row["exposure_type"],
                signal_types=types,
                is_cross_party=bool(row["is_cross_party"]),
                party_at_vote=row["party_at_vote"] or "",
                vote_position=(row["vote_position"] or "").lower(),
                amount_min=row["amount_min"],
                amount_max=row["amount_max"],
            )
        )
    return signals


def persist_signals(conn: sqlite3.Connection, signals: list[StockSignal]) -> int:
    conn.execute("DELETE FROM stock_legislation_signals")
    inserted = 0
    for sig in signals:
        for signal_type in sig.signal_types:
            conn.execute(
                """
                INSERT INTO stock_legislation_signals (
                    member_vote_id, member_id, vote_id, bill_id, transaction_id,
                    ticker, transaction_type, transaction_date, vote_date,
                    days_before_vote, exposure_type, signal_type,
                    is_cross_party, party_at_vote, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sig.member_vote_id,
                    sig.member_id,
                    sig.vote_id,
                    sig.bill_id,
                    sig.transaction_id,
                    sig.ticker,
                    sig.transaction_type,
                    sig.transaction_date,
                    sig.vote_date,
                    sig.days_before_vote,
                    sig.exposure_type,
                    signal_type,
                    int(sig.is_cross_party),
                    sig.party_at_vote,
                    "Associational timing signal only, not evidence of wrongdoing.",
                ),
            )
            inserted += 1
    conn.commit()
    return inserted


def summarize_signals(signals: list[StockSignal]) -> dict:
    if not signals:
        return {
            "total_signals": 0,
            "unique_members": 0,
            "unique_bills": 0,
            "by_signal_type": {},
            "cross_party": {"count": 0, "pct": 0.0},
            "non_cross_party": {"count": 0, "pct": 0.0},
            "by_party": {},
            "large_trades": 0,
        }

    df = pd.DataFrame(
        [
            {
                "member_id": s.member_id,
                "bill_id": s.bill_id,
                "signal_type": st,
                "is_cross_party": s.is_cross_party,
                "party_at_vote": s.party_at_vote,
                "is_large": "large_purchase" in s.signal_types or "large_sale" in s.signal_types,
            }
            for s in signals
            for st in s.signal_types
        ]
    )

    cross = int(df["is_cross_party"].sum())
    non_cross = len(df) - cross
    total = len(df)

    by_party = (
        df.groupby("party_at_vote")
        .size()
        .sort_values(ascending=False)
        .to_dict()
    )

    return {
        "total_signals": total,
        "unique_members": int(df["member_id"].nunique()),
        "unique_bills": int(df["bill_id"].nunique()),
        "by_signal_type": df.groupby("signal_type").size().to_dict(),
        "cross_party": {
            "count": cross,
            "pct": round(100.0 * cross / total, 2) if total else 0.0,
        },
        "non_cross_party": {
            "count": non_cross,
            "pct": round(100.0 * non_cross / total, 2) if total else 0.0,
        },
        "by_party": by_party,
        "large_trades": int(df["is_large"].sum()),
    }


def export_report_files(signals: list[StockSignal], summary: dict) -> dict[str, str]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for sig in signals:
        for st in sig.signal_types:
            rows.append(
                {
                    "member_name": sig.member_name,
                    "member_id": sig.member_id,
                    "bill_id": sig.bill_id,
                    "bill_title": sig.bill_title,
                    "ticker": sig.ticker,
                    "transaction_type": sig.transaction_type,
                    "transaction_date": sig.transaction_date,
                    "vote_date": sig.vote_date,
                    "days_before_vote": sig.days_before_vote,
                    "signal_type": st,
                    "is_cross_party": sig.is_cross_party,
                    "party_at_vote": sig.party_at_vote,
                    "vote_position": sig.vote_position,
                    "amount_min": sig.amount_min,
                    "amount_max": sig.amount_max,
                }
            )

    paths: dict[str, str] = {}
    if rows:
        df = pd.DataFrame(rows)
        csv_path = PROCESSED_DIR / "stock_legislation_signals.csv"
        df.to_csv(csv_path, index=False)
        paths["signals_csv"] = str(csv_path)

    summary_path = PROCESSED_DIR / "stock_legislation_summary.json"
    payload = {
        "framing": (
            "Temporal associations between PTR trades and legislative votes. "
            "Not evidence of insider trading, influence, or wrongdoing."
        ),
        "summary": summary,
        "signal_count": len(rows),
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    paths["summary_json"] = str(summary_path)
    return paths


def run_stock_analysis(
    *,
    window_days: int = 90,
    controversial_only: bool = True,
    focus_tags: set[str] | frozenset[str] | None = None,
    write_reports: bool = True,
) -> dict:
    conn = get_connection()
    try:
        ensure_stock_schema(conn)
        rows = fetch_candidate_rows(
            conn,
            window_days=window_days,
            controversial_only=controversial_only,
            focus_tags=focus_tags,
        )
        signals = build_signals(rows)
        inserted = persist_signals(conn, signals)
        summary = summarize_signals(signals)

        output: dict = {
            "candidates_scanned": len(rows),
            "signals_persisted": inserted,
            "summary": summary,
            "focus_tags": sorted(focus_tags) if focus_tags else None,
            "framing": (
                "Associational timing analysis only. Members may trade for many "
                "reasons unrelated to pending legislation; disclosure lag and "
                "imperfect bill-to-ticker mapping add further uncertainty."
            ),
        }

        if write_reports:
            output["reports"] = export_report_files(signals, summary)

        return output
    finally:
        conn.close()
