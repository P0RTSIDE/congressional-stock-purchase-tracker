# Notebooks (run in order)

| Notebook | Purpose |
|----------|---------|
| `01_load_votes.ipynb` | Ingest roll-call votes — or use `python -m src.load_votes` CLI |
| `02_load_campaign_finance.ipynb` | Donor profiles — or use `python -m src.load_donors` |
| `03_load_lobbying_bill_data.ipynb` | LDA lobbying — or use `python -m src.load_lobbying` |
| `04_entity_resolution.ipynb` | Build entity_aliases; validate crosswalks |
| `05_crossparty_vote_analysis.ipynb` | Crossing rates; party-stratified summaries |
| `06_donor_overlap_analysis.ipynb` | Overlap scores — or use `python -m src.run_overlap_analysis` |

Create these notebooks as you implement each pipeline stage.
