"""Database utilities for voting-donor-tracker."""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "voting_donor_tracker.db"
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
SCHEMA_STOCK_PATH = PROJECT_ROOT / "db" / "schema_stock.sql"
SEED_PATH = PROJECT_ROOT / "db" / "seed_test_data.sql"


def get_db_path() -> Path:
    env_path = os.getenv("DATABASE_PATH")
    if env_path:
        p = Path(env_path)
        return p if p.is_absolute() else PROJECT_ROOT / p
    return DEFAULT_DB_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> Path:
    """Create database and apply schema."""
    path = db_path or get_db_path()
    conn = get_connection(path)
    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        if SCHEMA_STOCK_PATH.exists():
            conn.executescript(SCHEMA_STOCK_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    return path


def seed_db(db_path: Path | None = None) -> None:
    """Load synthetic test data for pipeline validation."""
    conn = get_connection(db_path)
    try:
        seed_sql = SEED_PATH.read_text(encoding="utf-8")
        conn.executescript(seed_sql)
        conn.commit()
    finally:
        conn.close()


def run_query(sql: str, db_path: Path | None = None) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Database utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize schema")
    sub.add_parser("seed", help="Load seed test data")
    query_parser = sub.add_parser("query", help="Run a SQL query")
    query_parser.add_argument("sql", help="SQL to execute")

    args = parser.parse_args()
    if args.command == "init":
        path = init_db()
        print(f"Initialized database at {path}")
    elif args.command == "seed":
        seed_db()
        print("Seed data loaded.")
    elif args.command == "query":
        rows = run_query(args.sql)
        for row in rows:
            print(dict(row))


if __name__ == "__main__":
    main()
