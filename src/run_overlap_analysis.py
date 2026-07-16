"""Run donor-overlap analysis and write reports.

Associational comparison only — not evidence of influence or wrongdoing.

Usage:
    python -m src.run_overlap_analysis
    python -m src.run_overlap_analysis --top-n 20 --threshold 85
"""

from __future__ import annotations

import argparse
import json
import logging

from src.overlap_analysis import run_overlap_analysis

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Compute donor-lobbying overlap scores (associational analysis)"
    )
    parser.add_argument("--top-n", type=int, default=20, help="Top-N donors per member profile")
    parser.add_argument("--threshold", type=float, default=85.0, help="Fuzzy match threshold (0-100)")
    parser.add_argument("--no-reports", action="store_true", help="Skip writing CSV/JSON reports")
    args = parser.parse_args()

    logger.info(
        "Running overlap analysis (top_n=%s, threshold=%s). "
        "Framing: associational signal only.",
        args.top_n,
        args.threshold,
    )
    output = run_overlap_analysis(
        top_n=args.top_n,
        threshold=args.threshold,
        write_reports=not args.no_reports,
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
