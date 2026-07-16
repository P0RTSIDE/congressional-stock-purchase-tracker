"""Known political/advocacy organizations and alias registry.

Includes PACs, trade associations, and advocacy groups that frequently
appear under different names across FEC, OpenSecrets, and LDA sources.
Used for entity resolution — not an exhaustive influence list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .entity_matching import normalize_org_name


@dataclass(frozen=True)
class PoliticalOrg:
    org_id: str
    canonical_name: str
    org_type: str  # pac | trade_association | nonprofit
    aliases: tuple[str, ...]


# Major political organizations with common FEC/LDA name variants.
POLITICAL_ORG_REGISTRY: tuple[PoliticalOrg, ...] = (
    PoliticalOrg(
        org_id="org_pol_aipac",
        canonical_name="American Israel Public Affairs Committee",
        org_type="trade_association",
        aliases=(
            "AIPAC",
            "AIPAC PAC",
            "AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE",
            "AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE PAC",
            "AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE (AIPAC)",
            "AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE POLITICAL ACTION COMMITTEE",
        ),
    ),
    PoliticalOrg(
        org_id="org_pol_aipac_policy",
        canonical_name="AIPAC Policy Conference",
        org_type="nonprofit",
        aliases=("AIPAC POLICY CONFERENCE",),
    ),
    PoliticalOrg(
        org_id="org_pol_nra",
        canonical_name="National Rifle Association",
        org_type="trade_association",
        aliases=(
            "NRA",
            "NRA PAC",
            "NATIONAL RIFLE ASSOCIATION",
            "NATIONAL RIFLE ASSOCIATION OF AMERICA",
            "NATIONAL RIFLE ASSOCIATION POLITICAL VICTORY FUND",
            "NRA POLITICAL VICTORY FUND",
            "NRA-ILA",
        ),
    ),
    PoliticalOrg(
        org_id="org_pol_aarp",
        canonical_name="AARP",
        org_type="nonprofit",
        aliases=("AARP", "AARP PAC", "AMERICAN ASSOCIATION OF RETIRED PERSONS"),
    ),
    PoliticalOrg(
        org_id="org_pol_afa",
        canonical_name="American Farm Bureau Federation",
        org_type="trade_association",
        aliases=("AFBF", "AMERICAN FARM BUREAU FEDERATION", "AMERICAN FARM BUREAU FEDERATION PAC"),
    ),
    PoliticalOrg(
        org_id="org_pol_adem",
        canonical_name="American Dental Political Action Committee",
        org_type="pac",
        aliases=("ADPAC", "AMERICAN DENTAL POLITICAL ACTION COMMITTEE"),
    ),
    PoliticalOrg(
        org_id="org_pol_ahip",
        canonical_name="America's Health Insurance Plans",
        org_type="trade_association",
        aliases=(
            "AHIP",
            "AMERICA'S HEALTH INSURANCE PLANS",
            "AMERICA'S HEALTH INSURANCE PLANS PAC",
        ),
    ),
    PoliticalOrg(
        org_id="org_pol_chamber",
        canonical_name="U.S. Chamber of Commerce",
        org_type="trade_association",
        aliases=(
            "US CHAMBER OF COMMERCE",
            "U.S. CHAMBER OF COMMERCE",
            "CHAMBER OF COMMERCE OF THE USA",
            "US CHAMBER OF COMMERCE PAC",
        ),
    ),
    PoliticalOrg(
        org_id="org_pol_nfib",
        canonical_name="National Federation of Independent Business",
        org_type="trade_association",
        aliases=("NFIB", "NATIONAL FEDERATION OF INDEPENDENT BUSINESS", "NFIB PAC"),
    ),
    PoliticalOrg(
        org_id="org_pol_ata",
        canonical_name="American Trucking Associations",
        org_type="trade_association",
        aliases=("ATA", "AMERICAN TRUCKING ASSOCIATIONS", "AMERICAN TRUCKING ASSOCIATIONS PAC"),
    ),
)

_POLITICAL_NORM_INDEX: dict[str, PoliticalOrg] = {}
for _org in POLITICAL_ORG_REGISTRY:
    for alias in (*_org.aliases, _org.canonical_name):
        _POLITICAL_NORM_INDEX[normalize_org_name(alias)] = _org


PAC_NAME_RE = re.compile(
    r"\b(pac|political action committee|political victory fund|victory fund|"
    r"cmte|committee)\b",
    re.IGNORECASE,
)
ADVOCACY_KEYWORDS = (
    "lobby", "advocacy", "coalition", "federation", "association", "institute",
    "council", "alliance", "union", "action fund", "policy conference",
)


def match_political_org(name: str) -> PoliticalOrg | None:
    """Return registry entry if name matches a known political organization."""
    norm = normalize_org_name(name)
    if not norm:
        return None
    if norm in _POLITICAL_NORM_INDEX:
        return _POLITICAL_NORM_INDEX[norm]
    # Substring pass for acronyms embedded in longer PAC names
    for org in POLITICAL_ORG_REGISTRY:
        for alias in org.aliases:
            alias_norm = normalize_org_name(alias)
            if len(alias_norm) >= 4 and alias_norm in norm:
                return org
    return None


def classify_org_type(name: str) -> str:
    """Classify organization type from name heuristics."""
    political = match_political_org(name)
    if political:
        return political.org_type
    upper = name.upper()
    if PAC_NAME_RE.search(upper):
        return "pac"
    if any(kw in upper.lower() for kw in ADVOCACY_KEYWORDS):
        return "trade_association"
    if "FOUNDATION" in upper or "NONPROFIT" in upper:
        return "nonprofit"
    return "company"


def is_political_org(name: str) -> bool:
    return match_political_org(name) is not None


def seed_political_orgs(conn) -> int:
    """Insert canonical political org records and aliases into the database."""
    inserted = 0
    for org in POLITICAL_ORG_REGISTRY:
        conn.execute(
            """
            INSERT INTO organizations (org_id, canonical_name, org_type)
            VALUES (?, ?, ?)
            ON CONFLICT(org_id) DO UPDATE SET
                canonical_name = excluded.canonical_name,
                org_type = excluded.org_type
            """,
            (org.org_id, org.canonical_name, org.org_type),
        )
        for alias in (*org.aliases, org.canonical_name):
            conn.execute(
                """
                INSERT INTO entity_aliases (
                    org_id, alias_name, source_system, match_method, match_score, reviewed
                ) VALUES (?, ?, 'political_registry', 'exact', 100, 1)
                ON CONFLICT(alias_name, source_system) DO UPDATE SET
                    org_id = excluded.org_id,
                    reviewed = 1
                """,
                (org.org_id, alias),
            )
            inserted += 1
    conn.commit()
    return inserted
