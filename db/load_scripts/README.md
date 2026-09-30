# Load scripts

Votes:

```bash
python -m src.load_votes --congress 118 --chamber both --limit 3
```

Donor profiles from the OpenFEC API (organizational contributions per member):

```bash
python -m src.load_donors --cycle 2024 --limit 5
```

Lobbying disclosures from the LDA API. The default set is bills that already have roll-call votes in the database:

```bash
python -m src.load_lobbying --year 2024 --limit-pages 50
```

Overlap scores. The score is an association, not a causal estimate:

```bash
python -m src.run_overlap_analysis
```

Source access, rate limits, and name matching: `data/DATA_NOTES.md`.
