# Analysis stages

The study is implemented as Python modules under `src/`. This folder is the stage index for that pipeline.

| Stage | What it covers | Where it runs |
| --- | --- | --- |
| 01 | Roll-call votes | `python -m src.load_votes` |
| 02 | Donor profiles | `python -m src.load_donors` |
| 03 | LDA lobbying on those bills | `python -m src.load_lobbying` |
| 04 | Organization and member name matching | `src/entity_matching.py` |
| 05 | Crossing rates and party-stratified summaries | `src/vote_analysis.py` |
| 06 | Donor overlap on cross-party votes | `python -m src.run_overlap_analysis` |
| Stock | PTR trades near controversial-bill votes | `python -m src.load_stock_trades`, `python -m src.run_stock_analysis` |

Schema and views: `db/schema.sql`. Limitations: `reports/writeup.md`.
