# Legislative Voting Pattern + Donor Overlap Tracker

A portfolio data-engineering project that joins congressional roll-call votes, campaign finance profiles, and lobbying disclosures to examine **associations** between cross-party voting and donor overlap — not causation or influence.

## Framing (read first)

This repository is built around a deliberate methodological stance:

- Outputs describe **observed associations** ("donor overlap," "financial alignment").
- The pipeline **cannot distinguish** donor selection (giving to aligned candidates) from donor influence (donations changing votes).
- Analysis is **symmetric by construction** — the same logic applies to Democratic and Republican crossing members.
- Avoid accusatory framing in code, comments, and reports.

See `reports/writeup.md` for the full limitations section (structured **before** any findings).

## Data sources

| Source | Role | Status |
|--------|------|--------|
| [Congress.gov API](https://api.congress.gov/) | House votes, bills, members | Active (House roll calls in beta) |
| Senate.gov XML / [unitedstates/congress](https://github.com/unitedstates/congress) | Senate votes | Active |
| [OpenSecrets Bulk Data](https://www.opensecrets.org/bulk-data) | Member donor/industry profiles | Requires free educational account |
| [FEC Bulk Data](https://www.fec.gov/data/browse-data/?tab=bulk-data) | Optional raw SQL deep-dive | Active |
| [LDA REST API](https://lda.senate.gov/api/) | Bill-specific lobbying | Active (migrating to lda.gov) |
| [CongressInvests API](https://congressinfor-production.up.railway.app) | Congressional PTR stock trades | Active (free, no key) |

**ProPublica Congress API is retired (July 2024).** Do not use it.

Full access details, rate limits, and matching notes: `data/DATA_NOTES.md`.

## Quick start

```bash
# 1. Clone and install
cd voting-donor-tracker
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Configure API keys (copy and fill in)
copy .env.example .env

# 3. Initialize database and load votes (requires CONGRESS_GOV_API_KEY in .env for House)
python -m src.db_utils init
python -m src.load_votes --congress 118 --chamber both --limit 3

# 4. Verify views
python -m src.db_utils query "SELECT * FROM v_cross_party_flags WHERE is_cross_party = 1"
python -m src.db_utils query "SELECT * FROM v_donor_overlap_cross_party"

# 5. Stock activity + controversial bills (associational timing analysis)
python -m src.load_controversial_bills
python -m src.load_stock_trades --max-pages 10
python -m src.run_stock_analysis --window-days 90

# 6. Web dashboard (visualization)
python -m src.export_dashboard_data
cd web && npm install && npm run dev
```

## Project structure

```
voting-donor-tracker/
├── data/
│   ├── raw/                  # downloaded source files (gitignored)
│   ├── processed/              # cleaned parquet/csv exports
│   └── DATA_NOTES.md         # source research & access documentation
├── db/
│   ├── schema.sql            # normalized schema + SQL views
│   ├── seed_test_data.sql    # synthetic end-to-end test
│   └── load_scripts/         # per-source loaders
├── notebooks/                # staged analysis notebooks
├── src/                      # Python modules
├── reports/
│   ├── writeup.md            # findings (limitations first)
│   └── figures/
├── requirements.txt
└── README.md
```

## Methodology pipeline

1. **Vote matrix** — build member-by-bill positions; SQL views flag party-majority dissent (`v_cross_party_flags`).
2. **Donor profiles** — aggregate top-N orgs/industries per member per cycle (time-aligned).
3. **Bill-side interests** — map lobbying orgs to bills with position labels.
4. **Overlap analysis** — compare crossing members' donor profiles to bill lobbying lists; contrast with non-crossing members on same votes.
5. **Stock–legislation timing** — flag PTR purchases/sales on bill-exposed tickers within N days before controversial-bill votes; compare cross-party vs. non-cross-party members (associational only).
6. **Robustness** — stratify by party, topic, and overlap specificity.

## SQL-first design

Heavy joins and aggregations live in `db/schema.sql` views:

- `v_party_majority_by_vote` — party majority position per roll call
- `v_cross_party_flags` — dissent flag per member-vote
- `v_member_crossing_rates` — descriptive crossing rate
- `v_donor_overlap_cross_party` — associational overlap score

Python/pandas is used for visualization, fuzzy entity matching, and statistical summaries.

## API keys

| Key | Sign-up | Required? |
|-----|---------|-----------|
| `CONGRESS_GOV_API_KEY` | https://api.congress.gov/sign-up/ | Yes (House votes + bills) |
| `LDA_API_KEY` | https://lda.senate.gov/api/register/ | Recommended (120 req/min vs 15) |
| `OPENFEC_API_KEY` | https://api.open.fec.gov/developers/ | Optional |
| OpenSecrets bulk | https://www.opensecrets.org/bulk-data/signup | Yes (manual approval) |

## Development order

1. ✅ Research data sources → `data/DATA_NOTES.md`
2. ✅ Design SQL schema → `db/schema.sql`
3. ✅ Seed end-to-end test → `db/seed_test_data.sql`
4. ⬜ Implement loaders (`db/load_scripts/`, notebooks 01–03)
   - ✅ Votes: `python -m src.load_votes`
   - ✅ Donors: `python -m src.load_donors` (OpenFEC API)
   - ✅ Lobbying: `python -m src.load_lobbying` (LDA API)
   - ✅ Stock trades: `python -m src.load_stock_trades` (CongressInvests API)
   - ✅ Controversial bills: `python -m src.load_controversial_bills`
   - ✅ Stock timing analysis: `python -m src.run_stock_analysis`
5. ⬜ Entity resolution (`src/entity_matching.py`, notebook 04)
6. ⬜ Scale to one full congressional session
7. ⬜ Analysis notebooks 05–06 + `reports/writeup.md`

## License & attribution

Code: MIT (see LICENSE if added).

Data: Credit Congress.gov, FEC, OpenSecrets, and LDA sources per their terms. OpenSecrets bulk data is educational-use only.
