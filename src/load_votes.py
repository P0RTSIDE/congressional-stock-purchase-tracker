"""Ingest roll-call votes into the database.

House: Congress.gov API (beta house-vote endpoints).
Senate: senate.gov XML (parsed from official roll-call vote files).

Usage:
    python -m src.load_votes --congress 118 --chamber both --limit 5
    python -m src.load_votes --congress 118 --chamber house --session 2
    python -m src.load_votes --congress 118 --chamber senate --session 2 --limit 10
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from src.congress_client import CongressClient
from src.db_utils import PROJECT_ROOT, get_connection, init_db
from src.legislators import LegislatorRecord, build_crosswalk, cache_legislators_json
from src.senate_votes import iter_senate_votes, normalize_position, session_year
from src.vote_analysis import sync_cross_party_flags

logger = logging.getLogger(__name__)

BILL_TYPES = {"HR", "S", "HJR", "SJR", "HCONRES", "SCONRES", "HRES", "SRES"}
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "votes"
LEG_CACHE = PROJECT_ROOT / "data" / "raw" / "legislators.json"


def make_house_vote_id(congress: int, session: int, roll_number: int) -> str:
    year = session_year(congress, session)
    return f"h{roll_number}-{congress}.{year}"


def make_bill_id(congress: int, legislation_type: str | None, legislation_number: str | int | None) -> str | None:
    if not legislation_type or legislation_number is None:
        return None
    leg_type = legislation_type.strip().upper()
    if leg_type not in BILL_TYPES:
        return None
    return f"{congress}-{leg_type.lower()}-{int(legislation_number)}"


def parse_iso_date(value: str | None) -> str | None:
    if not value:
        return None
    return value[:10]


def upsert_member(conn: sqlite3.Connection, record: LegislatorRecord) -> None:
    conn.execute(
        """
        INSERT INTO members (
            member_id, bioguide_id, lis_id, first_name, last_name, full_name,
            party, state, chamber, district, in_office, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        ON CONFLICT(member_id) DO UPDATE SET
            lis_id = COALESCE(excluded.lis_id, members.lis_id),
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            full_name = excluded.full_name,
            party = COALESCE(excluded.party, members.party),
            state = COALESCE(excluded.state, members.state),
            chamber = excluded.chamber,
            district = COALESCE(excluded.district, members.district),
            updated_at = datetime('now')
        """,
        (
            record.member_id,
            record.bioguide_id,
            record.lis_id,
            record.first_name,
            record.last_name,
            record.full_name,
            record.party,
            record.state,
            record.chamber,
            record.district,
        ),
    )


def ensure_member_from_vote(
    conn: sqlite3.Connection,
    *,
    bioguide_id: str,
    first_name: str | None,
    last_name: str | None,
    party: str | None,
    state: str | None,
    chamber: str,
    bioguide_index: dict[str, LegislatorRecord],
    lis_to_bioguide: dict[str, str],
    lis_id: str | None = None,
) -> str | None:
    """Return member_id (bioguide) or None if unresolved."""
    member_id = bioguide_id
    if not member_id and lis_id:
        member_id = lis_to_bioguide.get(lis_id)

    if not member_id:
        return None

    if member_id in bioguide_index:
        upsert_member(conn, bioguide_index[member_id])
        return member_id

    full_name = " ".join(part for part in (first_name, last_name) if part).strip() or member_id
    upsert_member(
        conn,
        LegislatorRecord(
            member_id=member_id,
            bioguide_id=member_id,
            lis_id=lis_id,
            first_name=first_name or "",
            last_name=last_name or "",
            full_name=full_name,
            party=party,
            state=state,
            chamber=chamber,
            district=None,
        ),
    )
    return member_id


def upsert_bill(conn: sqlite3.Connection, bill: dict[str, Any] | None) -> str | None:
    if not bill:
        return None
    conn.execute(
        """
        INSERT INTO bills (bill_id, congress, bill_type, bill_number, title)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(bill_id) DO UPDATE SET
            title = COALESCE(excluded.title, bills.title)
        """,
        (
            bill["bill_id"],
            bill["congress"],
            bill["bill_type"],
            bill["bill_number"],
            bill.get("title"),
        ),
    )
    return bill["bill_id"]


def upsert_vote(conn: sqlite3.Connection, vote: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO votes (
            vote_id, congress, session, chamber, vote_number, vote_date,
            vote_question, vote_result, bill_id, source_system, source_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(vote_id) DO UPDATE SET
            vote_date = excluded.vote_date,
            vote_question = excluded.vote_question,
            vote_result = excluded.vote_result,
            bill_id = COALESCE(excluded.bill_id, votes.bill_id),
            source_url = excluded.source_url
        """,
        (
            vote["vote_id"],
            vote["congress"],
            vote["session"],
            vote["chamber"],
            vote["vote_number"],
            vote["vote_date"],
            vote.get("vote_question"),
            vote.get("vote_result"),
            vote.get("bill_id"),
            vote["source_system"],
            vote.get("source_url"),
        ),
    )


def upsert_member_votes(conn: sqlite3.Connection, vote_id: str, rows: list[dict[str, Any]]) -> int:
    inserted = 0
    for row in rows:
        cursor = conn.execute(
            """
            INSERT INTO member_votes (vote_id, member_id, position, party_at_vote)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(vote_id, member_id) DO UPDATE SET
                position = excluded.position,
                party_at_vote = excluded.party_at_vote
            """,
            (vote_id, row["member_id"], row["position"], row["party_at_vote"]),
        )
        if cursor.rowcount:
            inserted += 1
    return inserted


def load_house_votes(
    conn: sqlite3.Connection,
    client: CongressClient,
    *,
    congress: int,
    session: int,
    limit: int | None = None,
    roll_numbers: list[int] | None = None,
    cache: bool = True,
    bioguide_index: dict[str, LegislatorRecord],
    lis_to_bioguide: dict[str, str],
) -> dict[str, int]:
    stats = {"votes": 0, "member_votes": 0, "skipped_members": 0, "bills": 0}
    cache_dir = RAW_DIR / "house" / str(congress) / str(session)
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)

    def load_one_roll(roll_number: int) -> None:
        nonlocal stats
        vote_id = make_house_vote_id(congress, session, roll_number)

        detail = client.get_house_vote(congress, session, roll_number).get(
            "houseRollCallVote", {}
        )
        members = client.get_house_vote_members(congress, session, roll_number)

        if cache:
            (cache_dir / f"{roll_number}_summary.json").write_text(
                json.dumps(detail, indent=2), encoding="utf-8"
            )
            (cache_dir / f"{roll_number}_members.json").write_text(
                json.dumps(members, indent=2), encoding="utf-8"
            )

        bill_id = make_bill_id(
            congress,
            detail.get("legislationType"),
            detail.get("legislationNumber"),
        )
        if bill_id:
            upsert_bill(
                conn,
                {
                    "bill_id": bill_id,
                    "congress": congress,
                    "bill_type": detail["legislationType"].lower(),
                    "bill_number": int(detail["legislationNumber"]),
                    "title": None,
                },
            )
            stats["bills"] += 1

        upsert_vote(
            conn,
            {
                "vote_id": vote_id,
                "congress": congress,
                "session": session,
                "chamber": "house",
                "vote_number": roll_number,
                "vote_date": parse_iso_date(detail.get("startDate")) or date.today().isoformat(),
                "vote_question": detail.get("voteQuestion"),
                "vote_result": detail.get("result"),
                "bill_id": bill_id,
                "source_system": "congress_gov",
                "source_url": detail.get("sourceDataURL") or detail.get("url"),
            },
        )
        stats["votes"] += 1

        member_rows = []
        for member in members:
            bioguide = member.get("bioguideID")
            member_id = ensure_member_from_vote(
                conn,
                bioguide_id=bioguide,
                first_name=member.get("firstName"),
                last_name=member.get("lastName"),
                party=member.get("voteParty"),
                state=member.get("voteState"),
                chamber="house",
                bioguide_index=bioguide_index,
                lis_to_bioguide=lis_to_bioguide,
            )
            if not member_id:
                stats["skipped_members"] += 1
                continue
            member_rows.append(
                {
                    "member_id": member_id,
                    "position": normalize_position(member.get("voteCast", "")),
                    "party_at_vote": member.get("voteParty") or "UNK",
                }
            )

        stats["member_votes"] += upsert_member_votes(conn, vote_id, member_rows)
        conn.commit()
        logger.info("Loaded House vote %s (%s member positions)", vote_id, len(member_rows))

    if roll_numbers:
        for roll_number in roll_numbers:
            load_one_roll(roll_number)
        return stats

    for idx, summary in enumerate(client.list_house_votes(congress, session)):
        if limit is not None and idx >= limit:
            break

        roll_number = summary["rollCallNumber"]
        vote_id = make_house_vote_id(congress, session, roll_number)

        if cache:
            summary_path = cache_dir / f"{roll_number}_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        detail = client.get_house_vote(congress, session, roll_number).get("houseRollCallVote", summary)
        members = client.get_house_vote_members(congress, session, roll_number)

        if cache:
            members_path = cache_dir / f"{roll_number}_members.json"
            members_path.write_text(json.dumps(members, indent=2), encoding="utf-8")

        bill_id = make_bill_id(
            congress,
            detail.get("legislationType"),
            detail.get("legislationNumber"),
        )
        if bill_id:
            upsert_bill(
                conn,
                {
                    "bill_id": bill_id,
                    "congress": congress,
                    "bill_type": detail["legislationType"].lower(),
                    "bill_number": int(detail["legislationNumber"]),
                    "title": None,
                },
            )
            stats["bills"] += 1

        upsert_vote(
            conn,
            {
                "vote_id": vote_id,
                "congress": congress,
                "session": session,
                "chamber": "house",
                "vote_number": roll_number,
                "vote_date": parse_iso_date(detail.get("startDate")) or date.today().isoformat(),
                "vote_question": detail.get("voteQuestion"),
                "vote_result": detail.get("result"),
                "bill_id": bill_id,
                "source_system": "congress_gov",
                "source_url": detail.get("sourceDataURL") or detail.get("url"),
            },
        )
        stats["votes"] += 1

        member_rows = []
        for member in members:
            bioguide = member.get("bioguideID")
            member_id = ensure_member_from_vote(
                conn,
                bioguide_id=bioguide,
                first_name=member.get("firstName"),
                last_name=member.get("lastName"),
                party=member.get("voteParty"),
                state=member.get("voteState"),
                chamber="house",
                bioguide_index=bioguide_index,
                lis_to_bioguide=lis_to_bioguide,
            )
            if not member_id:
                stats["skipped_members"] += 1
                continue
            member_rows.append(
                {
                    "member_id": member_id,
                    "position": normalize_position(member.get("voteCast", "")),
                    "party_at_vote": member.get("voteParty") or "UNK",
                }
            )

        stats["member_votes"] += upsert_member_votes(conn, vote_id, member_rows)
        conn.commit()
        logger.info("Loaded House vote %s (%s member positions)", vote_id, len(member_rows))

    return stats


def load_senate_votes(
    conn: sqlite3.Connection,
    *,
    congress: int,
    session: int,
    limit: int | None = None,
    cache: bool = True,
    bioguide_index: dict[str, LegislatorRecord],
    lis_to_bioguide: dict[str, str],
    pause_seconds: float = 0.5,
) -> dict[str, int]:
    stats = {"votes": 0, "member_votes": 0, "skipped_members": 0, "bills": 0}
    cache_dir = RAW_DIR / "senate" / str(congress) / str(session)
    if cache:
        cache_dir.mkdir(parents=True, exist_ok=True)

    for idx, parsed in enumerate(
        iter_senate_votes(congress, session, limit=limit, pause_seconds=pause_seconds)
    ):
        vote_id = parsed["vote_id"]
        if cache:
            (cache_dir / f"{parsed['vote_number']}.json").write_text(
                json.dumps(parsed, indent=2),
                encoding="utf-8",
            )

        bill_id = None
        if parsed.get("bill"):
            bill_id = upsert_bill(conn, parsed["bill"])
            if bill_id:
                stats["bills"] += 1

        upsert_vote(
            conn,
            {
                "vote_id": vote_id,
                "congress": parsed["congress"],
                "session": parsed["session"],
                "chamber": "senate",
                "vote_number": parsed["vote_number"],
                "vote_date": parsed["vote_date"],
                "vote_question": parsed.get("vote_question"),
                "vote_result": parsed.get("vote_result"),
                "bill_id": bill_id,
                "source_system": "senate_xml",
                "source_url": parsed.get("source_url"),
            },
        )
        stats["votes"] += 1

        member_rows = []
        for member in parsed["members"]:
            member_id = ensure_member_from_vote(
                conn,
                bioguide_id="",
                lis_id=member.get("lis_id"),
                first_name=member.get("first_name"),
                last_name=member.get("last_name"),
                party=member.get("party"),
                state=member.get("state"),
                chamber="senate",
                bioguide_index=bioguide_index,
                lis_to_bioguide=lis_to_bioguide,
            )
            if not member_id:
                stats["skipped_members"] += 1
                continue
            member_rows.append(
                {
                    "member_id": member_id,
                    "position": member["position"],
                    "party_at_vote": member.get("party") or "UNK",
                }
            )

        stats["member_votes"] += upsert_member_votes(conn, vote_id, member_rows)
        conn.commit()
        logger.info(
            "Loaded Senate vote %s (%s member positions)",
            vote_id,
            len(member_rows),
        )

    return stats


def load_votes(
    *,
    congress: int,
    chamber: str = "both",
    sessions: list[int] | None = None,
    limit: int | None = None,
    roll_numbers: list[int] | None = None,
    cache: bool = True,
    init_if_missing: bool = True,
) -> dict[str, Any]:
    if init_if_missing:
        init_db()

    if sessions is None:
        sessions = [1, 2]

    entries = cache_legislators_json(LEG_CACHE)
    bioguide_index, lis_to_bioguide = build_crosswalk(entries)

    conn = get_connection()
    totals = {"house": {}, "senate": {}}
    try:
        if chamber in ("house", "both"):
            client = CongressClient()
            for session in sessions:
                logger.info("Loading House votes for %s Congress, session %s", congress, session)
                totals["house"][session] = load_house_votes(
                    conn,
                    client,
                    congress=congress,
                    session=session,
                    limit=limit,
                    roll_numbers=roll_numbers,
                    cache=cache,
                    bioguide_index=bioguide_index,
                    lis_to_bioguide=lis_to_bioguide,
                )

        if chamber in ("senate", "both"):
            for session in sessions:
                logger.info("Loading Senate votes for %s Congress, session %s", congress, session)
                totals["senate"][session] = load_senate_votes(
                    conn,
                    congress=congress,
                    session=session,
                    limit=limit,
                    cache=cache,
                    bioguide_index=bioguide_index,
                    lis_to_bioguide=lis_to_bioguide,
                )

        updated = sync_cross_party_flags(conn)
        logger.info("Synced cross-party flags for %s member-vote rows", updated)
    finally:
        conn.close()

    return totals


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Load congressional roll-call votes")
    parser.add_argument("--congress", type=int, required=True, help="Congress number (e.g. 118)")
    parser.add_argument(
        "--chamber",
        choices=["house", "senate", "both"],
        default="both",
        help="Chamber to load",
    )
    parser.add_argument(
        "--session",
        type=int,
        action="append",
        dest="sessions",
        help="Session number (1 or 2). Repeatable. Default: both sessions.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max votes per chamber/session (for testing)")
    parser.add_argument(
        "--rolls",
        type=int,
        action="append",
        dest="roll_numbers",
        help="Load specific House roll-call numbers only (repeatable). Use with --session.",
    )
    parser.add_argument("--no-cache", action="store_true", help="Do not write raw API/XML cache files")
    parser.add_argument("--no-init", action="store_true", help="Skip schema init if DB missing")
    args = parser.parse_args()

    totals = load_votes(
        congress=args.congress,
        chamber=args.chamber,
        sessions=args.sessions,
        limit=args.limit,
        roll_numbers=args.roll_numbers,
        cache=not args.no_cache,
        init_if_missing=not args.no_init,
    )
    print(json.dumps(totals, indent=2))


if __name__ == "__main__":
    main()
