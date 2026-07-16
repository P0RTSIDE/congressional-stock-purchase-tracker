"""Generate member pre-vote narrative summaries for the dashboard."""

from __future__ import annotations

import re

from .ticker_exposure import get_ticker_context

_EM_DASH = "\u2014"
_EN_DASH = "\u2013"


def format_vote_position(position: str | None) -> tuple[str, str]:
    """Return raw key and neutral display label for a roll-call position."""
    if not position:
        return ("", "Not available")
    raw = str(position).strip().lower()
    labels = {
        "yea": "Yea",
        "nay": "Nay",
        "present": "Present",
        "not_voting": "Did not vote",
    }
    return (raw, labels.get(raw, raw.replace("_", " ").title()))


def sanitize_text(text: str | None) -> str:
    """Replace em/en dashes with plain punctuation for UI copy."""
    if not text:
        return ""
    cleaned = text.replace(_EM_DASH, ", ").replace(_EN_DASH, " to ")
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def format_amount_range(
    amount_min: float | int | None,
    amount_max: float | int | None,
) -> str:
    hi = amount_max if amount_max is not None else amount_min
    lo = amount_min if amount_min is not None else amount_max
    if hi is None and lo is None:
        return "amount not disclosed"
    if hi is not None and hi >= 50001:
        return "$50,001 to $100,000+"
    if hi is not None and hi >= 15001:
        return "$15,001 to $50,000"
    if lo is not None and lo >= 15001:
        return "$15,001 to $50,000"
    return "$1,001 to $15,000"


AFFECTS_LABELS = {
    "plausible_direct": "Strong link",
    "possible_indirect": "Some connection",
    "weak_thematic": "Loose connection",
    "unlikely_direct": "Weak connection",
    "unclear": "Unclear connection",
}

LINK_STRENGTH_ORDER = {
    "plausible_direct": 4,
    "possible_indirect": 3,
    "weak_thematic": 2,
    "unlikely_direct": 1,
    "unclear": 0,
}


def _plain_exposure_explanation(
    ticker: str,
    exposure_key: str,
    rationale: str,
) -> str:
    """Rewrite exposure notes in plain language for end users."""
    lead = {
        "plausible_direct": f"{ticker} is closely tied to what this bill would change.",
        "possible_indirect": f"{ticker} could be affected indirectly if this bill passes or fails.",
        "weak_thematic": f"{ticker} sits in a related industry, but the tie to this bill is loose.",
        "unlikely_direct": f"{ticker} is only loosely mapped to this bill.",
        "unclear": f"{ticker} is on our watch list for this bill, but the link is not well defined.",
    }.get(exposure_key, f"{ticker} may relate to this bill in some way.")

    detail = rationale.strip()
    if not detail:
        return lead

    detail = detail[0].upper() + detail[1:] if len(detail) > 1 else detail
    if detail.endswith("."):
        return f"{lead} {detail}"
    return f"{lead} {detail}."


def _trade_line(
    ticker: str,
    transaction_type: str,
    amount_label: str,
    days_before_vote: int,
    exposure_label: str,
    plain_explanation: str,
) -> str:
    action = "bought" if transaction_type == "purchase" else "sold"
    return (
        f"{action.upper()} {ticker} ({amount_label}, {days_before_vote} days before vote). "
        f"Bill link: {exposure_label}. {plain_explanation}"
    )


def build_member_summaries(
    df,
    bill_id: str,
    bill_title: str | None,
    bill_sector: str | None,
    ticker_context: dict[str, dict],
) -> list[dict]:
    """Build per-member pre-vote summaries for one bill."""
    subset = df[df["bill_id"] == bill_id]
    if subset.empty:
        return []

    deduped = subset.drop_duplicates(
        subset=[
            "member_id",
            "ticker",
            "transaction_date",
            "transaction_type",
        ]
    )

    summaries: list[dict] = []
    grouped = deduped.groupby(["member_id", "member_name", "party_at_vote"], sort=False)

    for (member_id, member_name, party), group in grouped:
        trades = []
        trade_lines: list[str] = []
        purchases = 0
        sales = 0
        large_trades = 0
        min_days = int(group["days_before_vote"].min())
        vote_raw, vote_label = format_vote_position(
            group["vote_position"].iloc[0] if "vote_position" in group.columns else None
        )

        for _, row in group.iterrows():
            ticker = str(row["ticker"])
            ctx = ticker_context.get(ticker) or get_ticker_context(ticker, bill_sector)
            exposure_key = ctx.get("affects_stock", "unclear")
            exposure_label = AFFECTS_LABELS.get(exposure_key, "Unclear connection")
            confidence_pct = int(round(float(ctx.get("confidence", 0.4)) * 100))
            rationale = sanitize_text(str(ctx.get("rationale", "")))
            plain_explanation = sanitize_text(
                _plain_exposure_explanation(ticker, exposure_key, rationale)
            )
            amount_label = format_amount_range(row.get("amount_min"), row.get("amount_max"))
            tx_type = str(row["transaction_type"])
            days = int(row["days_before_vote"])

            if tx_type == "purchase":
                purchases += 1
            else:
                sales += 1
            if (row.get("amount_max") or 0) >= 50001:
                large_trades += 1

            trade = {
                "ticker": ticker,
                "transaction_type": tx_type,
                "transaction_date": str(row["transaction_date"]),
                "amount_label": amount_label,
                "days_before_vote": days,
                "exposure_label": exposure_label,
                "exposure_confidence": confidence_pct,
                "exposure_key": exposure_key,
                "exposure_rationale": rationale,
                "exposure_plain": plain_explanation,
            }
            trades.append(trade)

        trades.sort(
            key=lambda t: (
                -LINK_STRENGTH_ORDER.get(t["exposure_key"], 0),
                -t["exposure_confidence"],
                t["days_before_vote"],
            )
        )

        for trade in trades:
            trade.pop("exposure_key", None)
            trade_lines.append(
                _trade_line(
                    trade["ticker"],
                    trade["transaction_type"],
                    trade["amount_label"],
                    trade["days_before_vote"],
                    trade["exposure_label"],
                    trade["exposure_plain"],
                )
            )

        bill_label = bill_title or bill_id
        vote_clause = (
            f" Recorded roll-call position on this vote: {vote_label}."
            if vote_label != "Not available"
            else ""
        )
        overview = (
            f"{member_name} ({party}) disclosed {len(trades)} mapped pre-vote trade"
            f"{'s' if len(trades) != 1 else ''} within 365 days of the roll call on "
            f"{bill_label}.{vote_clause} Closest trade activity was {min_days} days before "
            f"the vote ({purchases} purchase{'s' if purchases != 1 else ''}, "
            f"{sales} sale{'s' if sales != 1 else ''}"
            f"{f', {large_trades} at $50k+' if large_trades else ''}). "
            f"These are timing overlaps only. They do not prove the member traded because "
            f"of this bill or that the vote moved any stock price."
        )

        summaries.append(
            {
                "member_id": str(member_id),
                "member_name": str(member_name),
                "party_at_vote": str(party),
                "vote_position": vote_raw,
                "vote_position_label": vote_label,
                "trade_count": len(trades),
                "purchases": purchases,
                "sales": sales,
                "large_trades": large_trades,
                "min_days_before_vote": min_days,
                "overview": sanitize_text(overview),
                "trades": trades,
                "trade_details": [sanitize_text(line) for line in trade_lines],
            }
        )

    summaries.sort(key=lambda s: (s["trade_count"], -s["min_days_before_vote"]), reverse=True)
    return summaries
