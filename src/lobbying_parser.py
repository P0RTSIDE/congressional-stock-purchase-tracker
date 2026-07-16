"""Parse LDA lobbying activities into bill-linked records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .cycles import congress_for_year
from .entity_matching import normalize_org_name

BILL_PATTERN = re.compile(
    r"(?P<type>H\.?\s*R\.?|S\.?\s*J\.?\s*Res\.?|H\.?\s*J\.?\s*Res\.?"
    r"|H\.?\s*Con\.?\s*Res\.?|S\.?\s*Con\.?\s*Res\.?|H\.?\s*Res\.?|S\.?\s*Res\.?|S\.?)"
    r"\s*(?P<num>\d+)",
    re.IGNORECASE,
)

TYPE_MAP = {
    "hr": "hr",
    "h.r.": "hr",
    "h r": "hr",
    "s": "s",
    "s.": "s",
    "hjres": "hjres",
    "h.j.res.": "hjres",
    "sjres": "sjres",
    "s.j.res.": "sjres",
    "hconres": "hconres",
    "h.con.res.": "hconres",
    "sconres": "sconres",
    "s.con.res.": "sconres",
    "hres": "hres",
    "h.res.": "hres",
    "sres": "sres",
    "s.res.": "sres",
}

SUPPORT_TERMS = ("support", "favor", "enactment", "passage", "advocate", "promote", "backing")
OPPOSE_TERMS = ("oppose", "opposition", "against", "block", "prevent", "reject", "defeat")
MONITOR_TERMS = ("monitor", "track", "watch", "awareness")


@dataclass
class ParsedLobbyingRecord:
    lobbying_id: str
    bill_id: str
    org_name_raw: str
    registrant_name: str | None
    position: str
    position_confidence: float
    issue_codes: str | None
    filing_id: str
    filing_date: str | None
    cycle_id: str
    notes: str | None


def _normalize_bill_type(raw: str) -> str | None:
    key = re.sub(r"\s+", "", raw.lower())
    key = key.replace(".", "")
    return TYPE_MAP.get(key) or TYPE_MAP.get(raw.lower().strip(), None)


def extract_bill_refs(text: str, congress: int) -> list[str]:
    bills: list[str] = []
    seen: set[str] = set()
    for match in BILL_PATTERN.finditer(text or ""):
        bill_type = _normalize_bill_type(match.group("type"))
        if not bill_type:
            continue
        bill_id = f"{congress}-{bill_type}-{int(match.group('num'))}"
        if bill_id not in seen:
            seen.add(bill_id)
            bills.append(bill_id)
    return bills


def classify_position(description: str) -> tuple[str, float, str]:
    """Return (position, confidence, notes). Neutral classification only."""
    text = (description or "").lower()
    if not text:
        return "unclear", 0.2, "empty description"

    support_hits = [term for term in SUPPORT_TERMS if term in text]
    oppose_hits = [term for term in OPPOSE_TERMS if term in text]
    monitor_hits = [term for term in MONITOR_TERMS if term in text]

    if support_hits and not oppose_hits:
        return "support", 0.75, f"keywords: {', '.join(support_hits)}"
    if oppose_hits and not support_hits:
        return "oppose", 0.75, f"keywords: {', '.join(oppose_hits)}"
    if support_hits and oppose_hits:
        return "unclear", 0.4, "mixed support/oppose keywords"
    if monitor_hits:
        return "monitor", 0.6, f"keywords: {', '.join(monitor_hits)}"
    return "unclear", 0.3, "no position keywords; bill reference only"


def org_id_for_name(name: str) -> str:
    digest = hashlib.md5(normalize_org_name(name).encode("utf-8")).hexdigest()[:12]
    return f"org_{digest}"


def parse_filing(
    filing: dict,
    *,
    target_bills: set[str] | None = None,
) -> list[ParsedLobbyingRecord]:
    filing_id = filing.get("filing_uuid") or filing.get("id")
    filing_year = int(filing.get("filing_year") or 0)
    congress = congress_for_year(filing_year)
    cycle_id = str(filing_year if filing_year % 2 == 0 else filing_year + 1)

    client = filing.get("client") or {}
    client_name = client.get("name") or "Unknown client"
    registrant = (filing.get("registrant") or {}).get("name")
    filing_date = (filing.get("dt_posted") or "")[:10] or None

    records: list[ParsedLobbyingRecord] = []
    for activity in filing.get("lobbying_activities") or []:
        description = activity.get("description") or ""
        issue_code = activity.get("general_issue_code")
        bill_ids = extract_bill_refs(description, congress)
        if not bill_ids:
            continue

        position, confidence, notes = classify_position(description)
        for bill_id in bill_ids:
            if target_bills is not None and bill_id not in target_bills:
                continue
            lobbying_id = hashlib.md5(
                f"{filing_id}|{bill_id}|{client_name}|{issue_code}|{description}".encode("utf-8")
            ).hexdigest()
            records.append(
                ParsedLobbyingRecord(
                    lobbying_id=lobbying_id,
                    bill_id=bill_id,
                    org_name_raw=client_name,
                    registrant_name=registrant,
                    position=position,
                    position_confidence=confidence,
                    issue_codes=issue_code,
                    filing_id=filing_id,
                    filing_date=filing_date,
                    cycle_id=cycle_id,
                    notes=notes,
                )
            )
    return records
