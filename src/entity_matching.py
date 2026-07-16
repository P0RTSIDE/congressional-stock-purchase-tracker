"""Entity resolution: match member and organization names across data sources.

Organization matching is the primary challenge — the same entity may appear
with different suffixes (PAC, Corp, LLC) across FEC, OpenSecrets, and LDA.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz, process


PAC_SUFFIXES = re.compile(
    r"\b(pac|political action committee|committee|cmte|inc|corp|corporation|llc|l\.l\.c\.|co)\b\.?",
    re.IGNORECASE,
)


def normalize_org_name(name: str) -> str:
    """Normalize organization name for fuzzy comparison."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = PAC_SUFFIXES.sub("", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class MatchResult:
    query_name: str
    matched_name: str
    matched_org_id: str | None
    score: float
    method: str  # 'exact' | 'fuzzy' | 'none'


def match_organization(
    query_name: str,
    candidates: list[tuple[str, str]],  # (org_id, alias_name)
    threshold: float = 85.0,
) -> MatchResult:
    """Match a raw org name to a canonical org_id via alias list.

    Returns best match above threshold, or method='none'.
    """
    from .political_orgs import match_political_org

    political = match_political_org(query_name)
    if political:
        return MatchResult(query_name, political.canonical_name, political.org_id, 100.0, "exact")

    normalized_query = normalize_org_name(query_name)
    if not normalized_query:
        return MatchResult(query_name, "", None, 0.0, "none")

    # Exact pass on normalized names
    norm_map = {normalize_org_name(alias): (org_id, alias) for org_id, alias in candidates}
    if normalized_query in norm_map:
        org_id, alias = norm_map[normalized_query]
        return MatchResult(query_name, alias, org_id, 100.0, "exact")

    # Fuzzy pass
    choices = {normalize_org_name(alias): (org_id, alias) for org_id, alias in candidates}
    result = process.extractOne(
        normalized_query,
        list(choices.keys()),
        scorer=fuzz.token_sort_ratio,
    )
    if result is None:
        return MatchResult(query_name, "", None, 0.0, "none")

    best_norm, score, _ = result
    if score < threshold:
        return MatchResult(query_name, "", None, score, "none")

    org_id, alias = choices[best_norm]
    return MatchResult(query_name, alias, org_id, score, "fuzzy")


def bioguide_from_legislators_yaml(record: dict) -> dict[str, str]:
    """Extract crosswalk IDs from a unitedstates/congress-legislators record.

    Returns dict with keys: bioguide_id, lis_id, fec_id, opensecrets_id (when present).
    """
    ids = record.get("id", {})
    return {
        "bioguide_id": ids.get("bioguide"),
        "lis_id": ids.get("lis"),
        "fec_id": ids.get("fec"),
        "opensecrets_id": ids.get("opensecrets"),
        "govtrack_id": ids.get("govtrack"),
    }
