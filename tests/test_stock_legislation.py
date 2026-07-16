"""Integration test: stock trades before controversial-bill votes."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.db_utils import SCHEMA_PATH, SCHEMA_STOCK_PATH, SEED_PATH
from src.stock_legislation_analysis import run_stock_analysis


def _init_test_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.executescript(SCHEMA_STOCK_PATH.read_text(encoding="utf-8"))
    conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def test_stock_purchase_before_controversial_vote():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = _init_test_db(db_path)

        conn.execute(
            """
            INSERT INTO controversial_bills (bill_id, controversy_tags, salience_score, source)
            VALUES ('118-hr-100', '["demo"]', 1.0, 'test')
            """
        )
        conn.execute(
            """
            INSERT INTO bill_stock_exposure (bill_id, ticker, exposure_type, confidence)
            VALUES ('118-hr-100', 'ACME', 'direct', 0.9)
            """
        )
        conn.execute(
            """
            INSERT INTO stock_transactions (
                transaction_id, member_id, member_name_raw, chamber, ticker,
                transaction_type, transaction_date, amount_min, amount_max, source_system
            ) VALUES (
                'tx_demo_1', 'B000002', 'Blake Beta', 'house', 'ACME',
                'purchase', '2023-03-20', 50001, 100000, 'test'
            )
            """
        )
        conn.commit()
        conn.close()

        prior = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(db_path)
        try:
            output = run_stock_analysis(window_days=90, write_reports=False)
        finally:
            if prior is None:
                os.environ.pop("DATABASE_PATH", None)
            else:
                os.environ["DATABASE_PATH"] = prior

        assert output["candidates_scanned"] >= 1
        assert output["signals_persisted"] >= 1
        assert output["summary"]["large_trades"] >= 1
        assert "large_purchase" in output["summary"]["by_signal_type"]
