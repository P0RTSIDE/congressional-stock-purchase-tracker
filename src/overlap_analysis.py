"""Donor overlap comparison for cross-party votes.

Computes associational overlap between a member's top donors and organizations
lobbying on the bill in the direction the member voted. This is NOT a causal measure.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .db_utils import PROJECT_ROOT, get_connection
from .entity_matching import match_organization
from .political_orgs import is_political_org, match_political_org, seed_political_orgs

logger = logging.getLogger(__name__)

REPORTS_DIR = PROJECT_ROOT / "reports" / "figures"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


@dataclass
class OverlapResult:
    member_vote_id: int
    member_id: str
    member_name: str
    vote_id: str
    bill_id: str | None
    cycle_id: str
    is_cross_party: bool
    party_at_vote: str
    member_position: str
    overlap_count: int
    profile_size: int
    overlap_score: float
    lobbying_side: str
    matched_orgs: list[str] = field(default_factory=list)
    political_org_matches: list[str] = field(default_factory=list)


def lobbying_side_for_vote(position: str) -> str:
    return "support" if position == "yea" else "oppose"


def load_alias_candidates(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT org_id, alias_name
        FROM entity_aliases
        ORDER BY reviewed DESC, match_score DESC
        """
    ).fetchall()
    return [(row["org_id"], row["alias_name"]) for row in rows]


def resolve_name_to_org_id(name: str, candidates: list[tuple[str, str]], threshold: float) -> str | None:
    political = match_political_org(name)
    if political:
        return political.org_id
    result = match_organization(name, candidates, threshold)
    return result.matched_org_id


def compute_overlap_score(
    member_donors: list[str],
    lobbying_orgs: list[str],
    candidates: list[tuple[str, str]],
    threshold: float = 85.0,
) -> tuple[int, int, float, list[str], list[str]]:
    """Compute overlap between donor names and lobbying org names.

    Returns (overlap_count, profile_size, overlap_score, matched_canonical_names, political_matches).
    """
    profile_size = len(member_donors)
    if profile_size == 0:
        return 0, 0, 0.0, [], []

    donor_org_ids: dict[str, str] = {}
    for donor in member_donors:
        org_id = resolve_name_to_org_id(donor, candidates, threshold)
        if org_id:
            donor_org_ids[org_id] = donor

    lobby_org_ids: dict[str, str] = {}
    for lobby_org in lobbying_orgs:
        org_id = resolve_name_to_org_id(lobby_org, candidates, threshold)
        if org_id:
            lobby_org_ids[org_id] = lobby_org

    overlap_ids = set(donor_org_ids) & set(lobby_org_ids)
    matched_names = sorted({donor_org_ids[i] for i in overlap_ids})
    political_matches = sorted(
        {
            name
            for oid in overlap_ids
            for name in (donor_org_ids.get(oid), lobby_org_ids.get(oid))
            if name and is_political_org(name)
        }
    )

    overlap_count = len(overlap_ids)
    score = round(overlap_count / profile_size, 4) if profile_size else 0.0
    return overlap_count, profile_size, score, matched_names, political_matches


def fetch_member_votes(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            mv.member_vote_id,
            mv.member_id,
            mv.vote_id,
            mv.position,
            mv.party_at_vote,
            mv.is_cross_party,
            v.bill_id,
            vc.cycle_id,
            m.full_name
        FROM member_votes mv
        JOIN votes v ON mv.vote_id = v.vote_id
        JOIN v_vote_cycles vc ON v.vote_id = vc.vote_id
        JOIN members m ON m.member_id = mv.member_id
        WHERE v.bill_id IS NOT NULL
          AND mv.position IN ('yea', 'nay')
        """
    ).fetchall()


def fetch_member_donors(
    conn: sqlite3.Connection,
    member_id: str,
    cycle_id: str,
    top_n: int,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT donor_org_raw
        FROM member_donor_profiles
        WHERE member_id = ? AND cycle_id = ? AND rank_by_amount <= ?
        ORDER BY rank_by_amount
        """,
        (member_id, cycle_id, top_n),
    ).fetchall()
    return [row["donor_org_raw"] for row in rows if row["donor_org_raw"]]


def fetch_bill_lobbying_orgs(
    conn: sqlite3.Connection,
    bill_id: str,
    lobbying_side: str,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT org_name_raw
        FROM lobbying_records
        WHERE bill_id = ?
          AND position = ?
        """,
        (bill_id, lobbying_side),
    ).fetchall()
    return [row["org_name_raw"] for row in rows]


def analyze_overlaps(
    conn: sqlite3.Connection,
    *,
    top_n: int = 20,
    threshold: float = 85.0,
) -> list[OverlapResult]:
    seed_political_orgs(conn)
    candidates = load_alias_candidates(conn)
    results: list[OverlapResult] = []

    for row in fetch_member_votes(conn):
        lobbying_side = lobbying_side_for_vote(row["position"])
        donors = fetch_member_donors(conn, row["member_id"], row["cycle_id"], top_n)
        lobby_orgs = fetch_bill_lobbying_orgs(conn, row["bill_id"], lobbying_side)

        overlap_count, profile_size, score, matched, political = compute_overlap_score(
            donors, lobby_orgs, candidates, threshold
        )

        results.append(
            OverlapResult(
                member_vote_id=row["member_vote_id"],
                member_id=row["member_id"],
                member_name=row["full_name"],
                vote_id=row["vote_id"],
                bill_id=row["bill_id"],
                cycle_id=row["cycle_id"],
                is_cross_party=bool(row["is_cross_party"]),
                party_at_vote=row["party_at_vote"],
                member_position=row["position"],
                overlap_count=overlap_count,
                profile_size=profile_size,
                overlap_score=score,
                lobbying_side=lobbying_side,
                matched_orgs=matched,
                political_org_matches=political,
            )
        )
    return results


def materialize_overlap_scores(conn: sqlite3.Connection, results: list[OverlapResult]) -> int:
    conn.execute("DELETE FROM donor_overlap_scores")
    for r in results:
        conn.execute(
            """
            INSERT INTO donor_overlap_scores (
                member_vote_id, member_id, vote_id, bill_id, cycle_id,
                overlap_count, profile_size, overlap_score,
                compared_position, lobbying_side
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r.member_vote_id,
                r.member_id,
                r.vote_id,
                r.bill_id,
                r.cycle_id,
                r.overlap_count,
                r.profile_size,
                r.overlap_score,
                r.member_position,
                r.lobbying_side,
            ),
        )
    conn.commit()
    return len(results)


def compare_cross_vs_non_cross(
    overlap_df: pd.DataFrame,
    party_col: str = "party_at_vote",
) -> pd.DataFrame:
    """Descriptive comparison of overlap_score distributions.

    Always stratify by party — symmetric reporting is a hard requirement.
    """
    if overlap_df.empty:
        return pd.DataFrame(
            columns=[
                "is_cross_party",
                party_col,
                "n",
                "mean_overlap_score",
                "median_overlap_score",
                "std_overlap_score",
            ]
        )
    summary = (
        overlap_df.groupby(["is_cross_party", party_col])["overlap_score"]
        .agg(["count", "mean", "median", "std"])
        .reset_index()
    )
    summary.columns = [
        "is_cross_party",
        party_col,
        "n",
        "mean_overlap_score",
        "median_overlap_score",
        "std_overlap_score",
    ]
    return summary


def political_org_overlap_report(results: list[OverlapResult]) -> pd.DataFrame:
    """Rows where overlap involves a known political/advocacy organization."""
    rows = []
    for r in results:
        if not r.political_org_matches:
            continue
        rows.append(
            {
                "member_name": r.member_name,
                "party": r.party_at_vote,
                "is_cross_party": r.is_cross_party,
                "bill_id": r.bill_id,
                "vote_id": r.vote_id,
                "overlap_score": r.overlap_score,
                "political_orgs": ", ".join(r.political_org_matches),
                "all_matched_orgs": ", ".join(r.matched_orgs),
            }
        )
    return pd.DataFrame(rows)


def run_overlap_analysis(
    *,
    top_n: int = 20,
    threshold: float = 85.0,
    write_reports: bool = True,
) -> dict:
    conn = get_connection()
    try:
        results = analyze_overlaps(conn, top_n=top_n, threshold=threshold)
        materialize_overlap_scores(conn, results)

        df = pd.DataFrame(
            [
                {
                    "member_vote_id": r.member_vote_id,
                    "member_id": r.member_id,
                    "member_name": r.member_name,
                    "vote_id": r.vote_id,
                    "bill_id": r.bill_id,
                    "cycle_id": r.cycle_id,
                    "is_cross_party": r.is_cross_party,
                    "party_at_vote": r.party_at_vote,
                    "member_position": r.member_position,
                    "overlap_count": r.overlap_count,
                    "profile_size": r.profile_size,
                    "overlap_score": r.overlap_score,
                    "lobbying_side": r.lobbying_side,
                    "matched_orgs": "; ".join(r.matched_orgs),
                    "political_org_matches": "; ".join(r.political_org_matches),
                }
                for r in results
            ]
        )

        summary = compare_cross_vs_non_cross(df)
        summary = summary.fillna(0)
        political = political_org_overlap_report(results)

        cross_with_overlap = df[(df["is_cross_party"]) & (df["overlap_score"] > 0)]
        output = {
            "total_member_votes_analyzed": len(results),
            "cross_party_votes": int(df["is_cross_party"].sum()),
            "votes_with_any_overlap": int((df["overlap_score"] > 0).sum()),
            "cross_party_with_overlap": len(cross_with_overlap),
            "political_org_overlap_count": len(political),
            "party_summary": summary.to_dict(orient="records"),
            "top_cross_party_overlaps": (
                cross_with_overlap.sort_values("overlap_score", ascending=False)
                .head(10)[
                    [
                        "member_name",
                        "party_at_vote",
                        "bill_id",
                        "overlap_score",
                        "matched_orgs",
                        "political_org_matches",
                    ]
                ]
                .to_dict(orient="records")
            ),
            "political_org_overlaps": political.to_dict(orient="records"),
        }

        if write_reports:
            PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(PROCESSED_DIR / "overlap_scores.csv", index=False)
            summary.to_csv(PROCESSED_DIR / "overlap_summary_by_party.csv", index=False)
            if not political.empty:
                political.to_csv(PROCESSED_DIR / "political_org_overlaps.csv", index=False)
            (PROCESSED_DIR / "overlap_analysis.json").write_text(
                json.dumps(output, indent=2),
                encoding="utf-8",
            )

        return output
    finally:
        conn.close()
