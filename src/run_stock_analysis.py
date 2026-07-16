"""Run stock–legislation timing analysis.

Associational comparison only — not evidence of insider trading or influence.

Usage:
    python -m src.run_stock_analysis
    python -m src.run_stock_analysis --window-days 60 --all-exposure-bills
"""

from __future__ import annotations

import argparse
import json
import logging

from src.controversial_bills import AI_FOCUS_TAGS
from src.stock_legislation_analysis import run_stock_analysis

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Analyze PTR stock trades before votes on controversial bills (associational)"
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=365,
        help="Days before vote to scan for trades (default: 365)",
    )
    parser.add_argument(
        "--all-topics",
        action="store_true",
        help="Include all controversial bills (default: AI/environment/society focus only)",
    )
    parser.add_argument(
        "--all-exposure-bills",
        action="store_true",
        help="Include all bills with stock exposure mappings, not only controversial catalog",
    )
    parser.add_argument("--no-reports", action="store_true", help="Skip writing CSV/JSON reports")
    args = parser.parse_args()

    focus = None if args.all_topics else AI_FOCUS_TAGS
    logger.info(
        "Running stock–legislation timing analysis (window=%s days, focus=%s). "
        "Framing: associational signal only.",
        args.window_days,
        "all" if focus is None else "ai/environment/society",
    )
    output = run_stock_analysis(
        window_days=args.window_days,
        controversial_only=not args.all_exposure_bills,
        focus_tags=focus,
        write_reports=not args.no_reports,
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
