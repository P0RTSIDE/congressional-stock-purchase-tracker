# Legislative Voting Pattern + Donor Overlap Tracker

## Limitations (read before results)

This analysis examines **associations** between cross-party voting and overlap in financial/lobbying profiles. It does **not** establish causation, legal wrongdoing, or the direction of influence.

### 1. Selection vs. influence (central confound)

The largest interpretive limitation is that **donors often give to candidates who already agree with them** (selection), not because a donation changed a legislator's vote (influence). This project's design **cannot distinguish** these mechanisms. A high donor-overlap score on a cross-party vote may reflect:

- A member crossing because their donor-aligned constituency or ideology already favored that position, or
- Coincidental overlap in a complex bill with many interested parties, or
- Entity-matching false positives across differently named PACs and subsidiaries.

Any finding below is a **signal worth further investigation**, not evidence of influence.

### 2. Data coverage gaps

- **House votes** via Congress.gov API are in beta (118th Congress+, legislation-related votes first).
- **Senate votes** require a separate XML/scraper pipeline.
- **Lobbying disclosures** do not cover every bill; bill-specific linkage is incomplete.
- **Campaign finance** itemization starts at $200; smaller donations are invisible.
- **Entity resolution** across FEC, OpenSecrets, and LDA is approximate — fuzzy matching introduces error.

### 3. Entity-matching imprecision

Organization names differ across sources (`Acme Corp` vs `Acme Corp PAC` vs `Acme Corporation Political Action Committee`). We normalize and fuzzy-match with a documented threshold, but matches below manual review remain uncertain.

### 4. Symmetric methodology

The pipeline applies **identical logic** to Democratic and Republican crossing members. Party-stratified results are reported side by side without editorial ranking of which party shows higher overlap.

### 5. No ideological or district controls (MVP)

The MVP comparison is descriptive: crossing members vs. non-crossing members on the same votes. A rigorous extension would match on ideology (e.g., DW-NOMINATE), district partisanship (Cook PVI), and committee membership. Even with matching, results remain associational.

### 6. Stock–legislation timing (associational extension)

A separate module flags **temporal associations** between congressional PTR stock trades and roll-call votes on **controversial bills** with curated ticker exposure mappings. This is **not** evidence of insider trading or influence.

**Additional limitations:**

- Bill→ticker exposure maps are illustrative; many bills affect sectors diffusely.
- PTR disclosure can lag transaction dates by weeks, compressing apparent "before vote" windows.
- Members may trade for portfolio, estate, or unrelated reasons.
- Name matching and ticker normalization introduce false positives/negatives.

Signals are stratified by party and cross-party status for symmetric comparison.

---

## Research question

When a member votes against their party's majority position, is there **greater overlap** between that member's top campaign donors and the organizations lobbying on the bill in the direction of the member's vote — compared to members who did not cross?

## Data sources

See `data/DATA_NOTES.md` for access methods, rate limits, and vintage.

| Source | Use |
|--------|-----|
| Congress.gov API + Senate XML | Roll-call votes, bill metadata |
| OpenSecrets bulk | Member donor/industry profiles |
| LDA REST API | Bill-specific lobbying organizations |
| CongressInvests API | Congressional PTR stock trades |
| unitedstates/congress-legislators | ID crosswalks |

## Methodology summary

1. Compute party-majority position per roll-call vote (SQL: `v_party_majority_by_vote`).
2. Flag member-votes where position ≠ own-party majority (`v_cross_party_flags`).
3. Build time-aligned top-N donor profiles per member per cycle.
4. Map lobbying organizations to bills with position labels (support/oppose/monitor/unclear).
5. Compute overlap score = |member top donors ∩ bill lobbying orgs on member's side| / N.
6. Compare overlap distributions for crossing vs. non-crossing members, **stratified by party**.
7. *(Stock extension)* Flag PTR trades on bill-exposed tickers within N days before controversial-bill votes; compare signal rates for cross-party vs. non-cross-party voters (`python -m src.run_stock_analysis`).

## Findings

> _Not yet populated — run notebooks 05–06 after loading a full congressional session._

### Aggregate (placeholder)

| Party | Crossing members (n) | Mean overlap score (cross) | Mean overlap score (non-cross) |
|-------|---------------------|---------------------------|-------------------------------|
| D | — | — | — |
| R | — | — | — |

### Illustrative case studies (placeholder)

Select 2–3 well-documented cross-party votes with high and low overlap scores to make the methodology concrete for readers.

## Robustness checks (planned)

- Topic stratification: agriculture votes with agribusiness donors vs. unrelated topics.
- Sensitivity to top-N (10 vs 20 vs 50 donors).
- Fuzzy match threshold sensitivity.
- Cycle alignment verification.

## Conclusion

_This section will summarize associational patterns observed, reiterate that selection vs. influence cannot be resolved here, and outline what additional data or methods would be needed for stronger inference._

## References & attribution

- Congress.gov / Library of Congress
- Federal Election Commission
- OpenSecrets (Center for Responsive Politics)
- U.S. Senate Lobbying Disclosure Act database
