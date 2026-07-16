"""Senate roll-call vote ingestion from senate.gov XML."""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

VOTE_MENU_URL = "https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_{congress}_{session}.htm"
VOTE_XML_URL = (
    "https://www.senate.gov/legislative/LIS/roll_call_votes/"
    "vote{congress}{session}/vote_{congress}_{session}_{vote_number:05d}.xml"
)

VOTE_LINK_RE = re.compile(
    r'href="(/legislative/LIS/roll_call_votes/vote\d+/vote_(\d+)_(\d+)_(\d+)\.htm)"',
    re.IGNORECASE,
)

BILL_TYPE_MAP = {
    "H.R.": "hr",
    "HR": "hr",
    "S.": "s",
    "S": "s",
    "H.J.Res.": "hjres",
    "H.J.RES.": "hjres",
    "S.J.Res.": "sjres",
    "S.J.RES.": "sjres",
    "H.Con.Res.": "hconres",
    "S.Con.Res.": "sconres",
    "H.Res.": "hres",
    "S.Res.": "sres",
}


@dataclass
class SenateVoteRef:
    congress: int
    session: int
    vote_number: int
    result: str | None
    question: str | None
    issue: str | None


def session_year(congress: int, session: int) -> int:
    return (congress - 1) * 2 + 1789 + (session - 1)


def make_senate_vote_id(congress: int, session: int, vote_number: int, congress_year: int | None = None) -> str:
    year = congress_year or session_year(congress, session)
    return f"s{vote_number}-{congress}.{year}"


def normalize_position(vote_cast: str) -> str:
    value = (vote_cast or "").strip().lower()
    mapping = {
        "yea": "yea",
        "yes": "yea",
        "aye": "yea",
        "nay": "nay",
        "no": "nay",
        "present": "present",
        "not voting": "not_voting",
        "absent": "not_voting",
    }
    return mapping.get(value, "not_voting")


def parse_bill_from_document(doc: ET.Element | None, congress: int) -> dict[str, Any] | None:
    if doc is None:
        return None
    doc_type = (doc.findtext("document_type") or "").strip()
    doc_number = (doc.findtext("document_number") or "").strip()
    if not doc_type or not doc_number:
        return None

    bill_type = BILL_TYPE_MAP.get(doc_type.upper().replace(" ", ""), BILL_TYPE_MAP.get(doc_type, doc_type.lower()))
    if not bill_type:
        bill_type = doc_type.lower().replace(".", "").replace(" ", "")
    try:
        bill_number = int(doc_number)
    except ValueError:
        return None

    return {
        "bill_id": f"{congress}-{bill_type}-{bill_number}",
        "congress": congress,
        "bill_type": bill_type,
        "bill_number": bill_number,
        "title": doc.findtext("document_title"),
    }


def parse_senate_vote_xml(xml_text: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    congress = int(root.findtext("congress", "0"))
    session = int(root.findtext("session", "0"))
    vote_number = int(root.findtext("vote_number", "0"))
    congress_year = int(root.findtext("congress_year", "0") or session_year(congress, session))

    vote_date_raw = root.findtext("vote_date", "")
    vote_date = _parse_senate_date(vote_date_raw)

    bill = parse_bill_from_document(root.find("document"), congress)

    members = []
    for member in root.findall("./members/member"):
        lis_id = (member.findtext("lis_member_id") or "").strip()
        members.append(
            {
                "lis_id": lis_id,
                "first_name": member.findtext("first_name"),
                "last_name": member.findtext("last_name"),
                "full_name": member.findtext("member_full"),
                "party": (member.findtext("party") or "").strip(),
                "state": (member.findtext("state") or "").strip(),
                "position": normalize_position(member.findtext("vote_cast", "")),
            }
        )

    return {
        "vote_id": make_senate_vote_id(congress, session, vote_number, congress_year),
        "congress": congress,
        "session": session,
        "chamber": "senate",
        "vote_number": vote_number,
        "vote_date": vote_date,
        "vote_question": root.findtext("question") or root.findtext("vote_question_text"),
        "vote_result": root.findtext("vote_result") or root.findtext("vote_result_text"),
        "bill": bill,
        "members": members,
        "source_url": VOTE_XML_URL.format(
            congress=congress, session=session, vote_number=vote_number
        ),
    }


def _parse_senate_date(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return datetime.utcnow().date().isoformat()
    for fmt in (
        "%B %d, %Y,  %I:%M %p",
        "%B %d, %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw.split(",")[0] if "," in raw else raw


def fetch_vote_menu(congress: int, session: int, timeout: int = 60) -> str:
    url = VOTE_MENU_URL.format(congress=congress, session=session)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_vote_menu(html: str) -> list[SenateVoteRef]:
    votes: list[SenateVoteRef] = []
    seen: set[tuple[int, int, int]] = set()
    for match in VOTE_LINK_RE.finditer(html):
        congress = int(match.group(2))
        session = int(match.group(3))
        vote_number = int(match.group(4))
        key = (congress, session, vote_number)
        if key in seen:
            continue
        seen.add(key)
        votes.append(
            SenateVoteRef(
                congress=congress,
                session=session,
                vote_number=vote_number,
                result=None,
                question=None,
                issue=None,
            )
        )
    return sorted(votes, key=lambda v: v.vote_number)


def fetch_senate_vote_xml(congress: int, session: int, vote_number: int, timeout: int = 60) -> str:
    url = VOTE_XML_URL.format(congress=congress, session=session, vote_number=vote_number)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text


def iter_senate_votes(
    congress: int,
    session: int,
    *,
    limit: int | None = None,
    pause_seconds: float = 0.5,
):
    """Yield parsed Senate votes for a congress/session."""
    menu_html = fetch_vote_menu(congress, session)
    refs = parse_vote_menu(menu_html)
    if limit is not None:
        refs = refs[-limit:]  # most recent votes (highest roll numbers)

    for ref in refs:
        xml_text = fetch_senate_vote_xml(ref.congress, ref.session, ref.vote_number)
        time.sleep(pause_seconds)
        yield parse_senate_vote_xml(xml_text)
