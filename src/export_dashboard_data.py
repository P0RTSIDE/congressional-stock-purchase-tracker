"""Export analysis results for the web dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .controversial_bills import AI_FOCUS_TAGS, CONTROVERSIAL_BILL_CATALOG
from .db_utils import PROJECT_ROOT
from .member_summary import build_member_summaries, format_vote_position, sanitize_text
from .ticker_exposure import get_ticker_context

PROCESSED = PROJECT_ROOT / "data" / "processed"
WEB_PUBLIC = PROJECT_ROOT / "web" / "public" / "data"


def _bill_context(bill_id: str | None) -> dict:
    if not bill_id or bill_id not in CONTROVERSIAL_BILL_CATALOG:
        return {"bill_id": bill_id}
    meta = CONTROVERSIAL_BILL_CATALOG[bill_id]
    return {
        "bill_id": bill_id,
        "title": meta.get("title"),
        "summary": sanitize_text(meta.get("summary")),
        "tags": meta.get("tags", []),
        "sector": meta.get("sector"),
        "salience": meta.get("salience"),
        "exposure_note": (
            "Ticker list is a curated thematic map of companies/sectors that "
            "could plausibly be affected if the bill passes or fails. "
            "This project does NOT measure actual stock price impact or prove "
            "that a specific vote moved a security."
        ),
    }


def _aggregate_bill(df: pd.DataFrame, bill_id: str) -> dict:
    subset = df[df["bill_id"] == bill_id]
    if subset.empty:
        return {}
    vote_date = subset["vote_date"].iloc[0]
    ctx = _bill_context(bill_id)
    return {
        **ctx,
        "vote_date": vote_date,
        "signal_count": len(subset),
        "member_count": subset["member_id"].nunique(),
        "ticker_count": subset["ticker"].nunique(),
    }


def export_dashboard_data() -> Path:
    summary_path = PROCESSED / "stock_legislation_summary.json"
    signals_path = PROCESSED / "stock_legislation_signals.csv"

    if not signals_path.exists():
        raise FileNotFoundError(
            f"Missing {signals_path}. Run: python -m src.run_stock_analysis"
        )

    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    df = pd.read_csv(signals_path)

    unique_trades = df.drop_duplicates(
        subset=[
            "member_id",
            "bill_id",
            "ticker",
            "transaction_date",
            "transaction_type",
            "vote_date",
        ]
    )

    bills = []
    for bill_id in unique_trades["bill_id"].dropna().unique():
        meta = _aggregate_bill(unique_trades, str(bill_id))
        if meta:
            bills.append(meta)
    bills.sort(key=lambda b: b.get("signal_count", 0), reverse=True)

    primary_bill_id = bills[0]["bill_id"] if bills else None
    primary = unique_trades[unique_trades["bill_id"] == primary_bill_id] if primary_bill_id else unique_trades

    by_member = (
        primary.groupby(["member_name", "member_id", "party_at_vote"])
        .agg(
            signals=("signal_type", "count"),
            purchases=("transaction_type", lambda s: (s == "purchase").sum()),
            sales=("transaction_type", lambda s: (s == "sale").sum()),
            large_trades=(
                "signal_type",
                lambda s: s.isin(["large_purchase", "large_sale"]).sum(),
            ),
            tickers=("ticker", lambda s: sorted(set(s))),
            min_days=("days_before_vote", "min"),
        )
        .reset_index()
        .sort_values("signals", ascending=False)
    )

    by_ticker = (
        primary.groupby("ticker")
        .agg(
            signals=("signal_type", "count"),
            purchases=("transaction_type", lambda s: (s == "purchase").sum()),
            sales=("transaction_type", lambda s: (s == "sale").sum()),
            members=("member_id", "nunique"),
        )
        .reset_index()
        .sort_values("signals", ascending=False)
    )

    timeline = (
        primary.groupby(["days_before_vote", "transaction_type"])
        .size()
        .reset_index(name="count")
    )

    scatter_cols = [
        "member_name",
        "member_id",
        "bill_id",
        "bill_title",
        "party_at_vote",
        "ticker",
        "transaction_type",
        "transaction_date",
        "vote_date",
        "days_before_vote",
        "amount_min",
        "amount_max",
        "signal_type",
    ]
    if "vote_position" in unique_trades.columns:
        scatter_cols.insert(6, "vote_position")

    scatter = unique_trades[scatter_cols].to_dict(orient="records")
    for row in scatter:
        if row.get("vote_position"):
            _, label = format_vote_position(str(row["vote_position"]))
            row["vote_position_label"] = label

    bill_ctx = _bill_context(primary_bill_id)
    sector = bill_ctx.get("sector")

    ticker_context = {}
    for ticker in unique_trades["ticker"].dropna().unique():
        raw = get_ticker_context(str(ticker), sector)
        ticker_context[str(ticker)] = {
            **raw,
            "rationale": sanitize_text(str(raw.get("rationale", ""))),
        }

    member_summaries_by_bill: dict[str, list] = {}
    for bill_id in unique_trades["bill_id"].dropna().unique():
        bill_id_str = str(bill_id)
        bill_meta = CONTROVERSIAL_BILL_CATALOG.get(bill_id_str, {})
        member_summaries_by_bill[bill_id_str] = build_member_summaries(
            unique_trades,
            bill_id_str,
            bill_meta.get("title"),
            bill_meta.get("sector"),
            ticker_context,
        )

    focus_tags = summary.get("focus_tags") or sorted(AI_FOCUS_TAGS)

    payload = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "focus_topic": "multi_bill",
        "focus_tags": focus_tags,
        "framing": sanitize_text(
            summary.get(
                "framing",
                "Temporal associations only, not evidence of wrongdoing or influence.",
            )
        ),
        "exposure_framing": sanitize_text(
            "Does this vote affect the stock? Link strength varies by bill and ticker. "
            "AI bills may map to platforms (META, GOOG), chips/cloud (NVDA, MSFT), or "
            "data-center energy (NEE, EQIX). Space/defense bills map to aerospace primes. "
            "None of this proves price impact or insider trading."
        ),
        "summary": summary.get("summary", {}),
        "bills": bills,
        "primary_bill_id": primary_bill_id,
        "bill": {
            **bill_ctx,
            "vote_date": primary["vote_date"].iloc[0] if len(primary) else None,
        },
        "ticker_context": ticker_context,
        "member_summaries_by_bill": member_summaries_by_bill,
        "by_member": by_member.to_dict(orient="records"),
        "by_ticker": by_ticker.to_dict(orient="records"),
        "timeline": timeline.to_dict(orient="records"),
        "signals": scatter,
    }

    WEB_PUBLIC.mkdir(parents=True, exist_ok=True)
    out = WEB_PUBLIC / "dashboard.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def main() -> None:
    path = export_dashboard_data()
    print(f"Exported dashboard data to {path}")


if __name__ == "__main__":
    main()
