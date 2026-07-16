"""Integration test: AIPAC and other political orgs resolve across donor/lobbying overlap."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db_utils import SCHEMA_PATH, SEED_PATH
from src.overlap_analysis import run_overlap_analysis


def _init_test_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def test_aipac_overlap_detected():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = _init_test_db(db_path)
        conn.execute(
            """
            INSERT INTO organizations (org_id, canonical_name, org_type)
            VALUES ('org_pol_aipac', 'American Israel Public Affairs Committee', 'trade_association')
            """
        )
        # Blake Beta: cross-party nay + AIPAC donor + AIPAC lobbying oppose on same bill
        conn.execute(
            """
            INSERT INTO member_donor_profiles (
                member_id, cycle_id, org_id, donor_org_raw,
                total_amount, contribution_count, rank_by_amount, top_n
            ) VALUES (
                'B000002', '2024', 'org_pol_aipac',
                'AMERICAN ISRAEL PUBLIC AFFAIRS COMMITTEE PAC',
                5000, 1, 3, 20
            )
            """
        )
        conn.execute(
            """
            INSERT INTO lobbying_records (
                lobbying_id, bill_id, org_id, org_name_raw, registrant_name,
                position, position_confidence, cycle_id, source_system, notes
            ) VALUES (
                'lob_aipac_demo', '118-hr-100', 'org_pol_aipac',
                'American Israel Public Affairs Committee', 'Demo Registrant',
                'oppose', 0.8, '2024', 'test', 'demo oppose keyword'
            )
            """
        )
        conn.commit()
        conn.close()

        import os

        prior = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(db_path)
        try:
            output = run_overlap_analysis(write_reports=False)
        finally:
            if prior is None:
                os.environ.pop("DATABASE_PATH", None)
            else:
                os.environ["DATABASE_PATH"] = prior

        assert output["votes_with_any_overlap"] >= 1
        assert output["political_org_overlap_count"] >= 1
        assert any(
            "AIPAC" in str(row.get("political_orgs", "")).upper()
            or "ISRAEL" in str(row.get("political_orgs", "")).upper()
            for row in output["political_org_overlaps"]
        )


if __name__ == "__main__":
    test_aipac_overlap_detected()
    print("AIPAC overlap integration test passed.")
