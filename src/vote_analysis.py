"""Roll-call vote analysis: party-majority detection and cross-party flagging.

SQL views (v_party_majority_by_vote, v_cross_party_flags) handle the core logic.
This module provides Python helpers for API ingestion and post-load updates.
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

Position = Literal["yea", "nay", "present", "not_voting"]
PartyMajority = Literal["yea", "nay", "tie", "unknown"]


def compute_party_majority(
    positions: list[tuple[str, Position]],
) -> dict[str, PartyMajority]:
    """Compute majority position per party from a list of (party, position) tuples.

    Used during ETL before SQL views are populated. Mirrors v_party_majority_by_vote logic.
    """
    by_party: dict[str, Counter] = {}
    for party, position in positions:
        if position not in ("yea", "nay"):
            continue
        by_party.setdefault(party, Counter())[position] += 1

    result: dict[str, PartyMajority] = {}
    for party, counts in by_party.items():
        if not counts:
            result[party] = "unknown"
            continue
        top = counts.most_common(2)
        if len(top) > 1 and top[0][1] == top[1][1]:
            result[party] = "tie"
        else:
            result[party] = top[0][0]  # type: ignore[assignment]
    return result


def is_cross_party_vote(
    member_position: Position,
    party: str,
    party_majorities: dict[str, PartyMajority],
) -> bool:
    """Return True if member voted against their party's majority position."""
    majority = party_majorities.get(party, "unknown")
    if majority in ("tie", "unknown"):
        return False
    if member_position not in ("yea", "nay"):
        return False
    return member_position != majority


def sync_cross_party_flags(conn) -> int:
    """Update member_votes.party_majority_position and is_cross_party from SQL views."""
    sql = """
    UPDATE member_votes
    SET
        party_majority_position = (
            SELECT party_majority_position
            FROM v_party_majority_by_vote pm
            WHERE pm.vote_id = member_votes.vote_id
              AND pm.party_at_vote = member_votes.party_at_vote
        ),
        is_cross_party = (
            SELECT is_cross_party
            FROM v_cross_party_flags cf
            WHERE cf.member_vote_id = member_votes.member_vote_id
        )
    """
    cursor = conn.execute(sql)
    conn.commit()
    return cursor.rowcount
