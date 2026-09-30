# Congressional Voting, Donor Overlap, and Stock Timing

Joins House and Senate roll-call votes, campaign finance profiles, lobbying disclosures, and periodic transaction reports. The question is descriptive: where cross-party votes line up with shared donors or with stock trades on bill-exposed tickers.

The pipeline cannot separate donor selection (giving to candidates who already agree) from donor influence (a gift changing a vote). The same rules run for Democratic and Republican members. Outputs use association language: donor overlap, financial alignment, timing overlap. They are not findings of causation, influence, or legal wrongdoing.

Limitations are written out in `reports/writeup.md` ahead of any results.

## Data sources

| Source | Role | Status |
| --- | --- | --- |
| [Congress.gov API](https://api.congress.gov/) | House votes, bills, members | Active (House roll calls in beta) |
| Senate.gov XML / [unitedstates/congress](https://github.com/unitedstates/congress) | Senate votes | Active |
| [OpenSecrets bulk data](https://www.opensecrets.org/bulk-data) | Member donor and industry profiles | Free educational account |
| [FEC bulk data](https://www.fec.gov/data/browse-data/?tab=bulk-data) | Optional raw finance tables | Active |
| [LDA API](https://lda.senate.gov/api/) | Bill-level lobbying disclosures | Active (moving to lda.gov) |
| [CongressInvests API](https://congressinfor-production.up.railway.app) | Congressional stock trades (PTRs) | Active, no key |

The ProPublica Congress API was retired in July 2024 and is not used.

Access notes, rate limits, and name-matching rules: `data/DATA_NOTES.md`.

## Method

1. **Vote matrix.** Member-by-bill positions. SQL views flag votes against the party majority (`v_cross_party_flags`).
2. **Donor profiles.** Top organizations and industries per member per cycle, aligned to that cycle (`src/load_donors.py`, OpenFEC).
3. **Bill-side interests.** Lobbying organizations linked to bills, with position labels (`src/load_lobbying.py`, LDA).
4. **Overlap.** Donor profiles of members who crossed their party are compared with the lobbying list on the same bills, and with members who did not cross (`src/run_overlap_analysis.py`).
5. **Names.** Organization strings differ across FEC, OpenSecrets, and LDA (PAC, Corp, LLC). `src/entity_matching.py` normalizes suffixes and fuzzy-matches with a documented threshold.
6. **Stock timing.** PTR purchases and sales on tickers tied to controversial bills, inside a window before the roll call. Cross-party members are compared with other members on the same votes (`src/run_stock_analysis.py`). This is a timing overlap, not an insider-trading test.
7. **Checks.** Results can be split by party, topic, and how specific the overlap is. The MVP comparison does not control for DW-NOMINATE, district lean, or committee seat.

Heavy joins live in `db/schema.sql`:

- `v_party_majority_by_vote`: party majority position on a roll call
- `v_cross_party_flags`: dissent flag per member and vote
- `v_member_crossing_rates`: crossing rate
- `v_donor_overlap_cross_party`: overlap score

Python is used for export, fuzzy matching, and the charts.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows, activate with `.venv\Scripts\activate` and copy the env file with `copy .env.example .env`.

```bash
python -m src.db_utils init
python -m src.load_votes --congress 118 --chamber both --limit 3
python -m src.db_utils query "SELECT * FROM v_cross_party_flags WHERE is_cross_party = 1"
python -m src.db_utils query "SELECT * FROM v_donor_overlap_cross_party"
python -m src.load_controversial_bills
python -m src.load_stock_trades --max-pages 10
python -m src.run_stock_analysis --window-days 90
python -m src.export_dashboard_data
cd web && npm install && npm run dev
```

`--limit 3` is a short vote pull. Omit it for a wider load. House votes need `CONGRESS_GOV_API_KEY` in `.env`.

The Vite dashboard in `web/` charts the exported JSON. Vercel builds that app from the repo root (`vercel.json` sets the install and build commands to the `web` folder).

Per-source commands and the overlap run are also listed in `db/load_scripts/README.md`. Stage names and the matching Python modules are in `notebooks/README.md`.

## API keys

| Key | Sign-up | Needed for |
| --- | --- | --- |
| `CONGRESS_GOV_API_KEY` | https://api.congress.gov/sign-up/ | House votes and bills |
| `LDA_API_KEY` | https://lda.senate.gov/api/register/ | Higher LDA rate limit (120 requests per minute, otherwise 15) |
| `OPENFEC_API_KEY` | https://api.open.fec.gov/developers/ | Optional OpenFEC access |
| OpenSecrets bulk | https://www.opensecrets.org/bulk-data/signup | Donor bulk files (manual approval) |

## Repository layout

```
data/          raw downloads (gitignored), processed exports, DATA_NOTES.md
db/            schema.sql, seed data, load_scripts/
notebooks/     stage index
src/           clients, loaders, matching, overlap, stock timing, dashboard export
reports/       writeup.md and figures
web/           Vite dashboard
```

## License

No license file is included with this repository. Credit Congress.gov, FEC, OpenSecrets, and LDA under their own terms. OpenSecrets bulk data is for educational use.
