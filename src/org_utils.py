"""Shared organization upsert and resolution utilities."""

from __future__ import annotations

import sqlite3

from .lobbying_parser import org_id_for_name
from .political_orgs import classify_org_type, match_political_org


def resolve_org_id(name: str) -> tuple[str, str, str]:
    """Return (org_id, canonical_name, org_type) for a raw organization name."""
    clean = name.strip()
    political = match_political_org(clean)
    if political:
        return political.org_id, political.canonical_name, political.org_type
    return org_id_for_name(clean), clean, classify_org_type(clean)


def upsert_organization(
    conn: sqlite3.Connection,
    org_name: str,
    *,
    source_system: str = "openfec",
) -> str:
    org_id, canonical_name, org_type = resolve_org_id(org_name)
    conn.execute(
        """
        INSERT INTO organizations (org_id, canonical_name, org_type)
        VALUES (?, ?, ?)
        ON CONFLICT(org_id) DO UPDATE SET
            org_type = COALESCE(excluded.org_type, organizations.org_type)
        """,
        (org_id, canonical_name, org_type),
    )
    conn.execute(
        """
        INSERT INTO entity_aliases (org_id, alias_name, source_system, match_method, match_score, reviewed)
        VALUES (?, ?, ?, 'exact', 100, 0)
        ON CONFLICT(alias_name, source_system) DO NOTHING
        """,
        (org_id, org_name.strip(), source_system),
    )
    return org_id
