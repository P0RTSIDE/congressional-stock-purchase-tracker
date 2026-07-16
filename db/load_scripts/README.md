# Load scripts

```bash
# Votes
python -m src.load_votes --congress 118 --chamber both --limit 3

# Donor profiles (OpenFEC API — organizational contributions per member)
python -m src.load_donors --cycle 2024 --limit 5

# Lobbying (LDA API — defaults to bills that have roll-call votes in DB)
python -m src.load_lobbying --year 2024 --limit-pages 50

# Overlap analysis (associational — not causal)
python -m src.run_overlap_analysis
```

See `data/DATA_NOTES.md` for source access details.