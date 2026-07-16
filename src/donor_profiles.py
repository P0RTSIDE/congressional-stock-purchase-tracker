"""Donor and industry profile aggregation per member per election cycle.

Profiles should be time-aligned: a 2024 vote compares against the 2023-2024 cycle,
not lifetime contribution totals.
"""

from __future__ import annotations


def build_top_donor_profile_sql(top_n: int = 20) -> str:
    """Return SQL to materialize member_donor_profiles from contributions."""
    return f"""
    INSERT OR REPLACE INTO member_donor_profiles (
        member_id, cycle_id, org_id, donor_org_raw, industry_code,
        total_amount, contribution_count, rank_by_amount, top_n
    )
    SELECT
        member_id,
        cycle_id,
        org_id,
        donor_org_raw,
        industry_code,
        total_amount,
        contribution_count,
        rank_by_amount,
        {top_n} AS top_n
    FROM v_member_top_donors
    WHERE rank_by_amount <= {top_n}
    """


def cycle_for_vote_date(vote_date: str, cycles: list[dict]) -> str | None:
    """Map a vote date (ISO string) to an election cycle_id."""
    for cycle in cycles:
        if cycle["start_date"] <= vote_date <= cycle["end_date"]:
            return cycle["cycle_id"]
    return None
