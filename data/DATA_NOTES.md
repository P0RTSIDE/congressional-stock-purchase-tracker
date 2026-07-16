# Data Source Research & Access Notes

> **Project framing:** All data linkages in this project measure **associations** between voting behavior and financial/lobbying profiles. They do **not** establish causation, influence, or wrongdoing. See `reports/writeup.md` for the full limitations section.

Last updated: 2026-07-14

---

## Executive Summary

| Source | Primary use in this project | Access method | Rate limits | Recommended path |
|--------|----------------------------|---------------|-------------|------------------|
| **Congress.gov API** | Roll-call votes (House), bills, sponsors, members | Free API key via [api.data.gov](https://api.data.gov/signup/) | **5,000 requests/hour** per key | **Primary** for House votes + bill metadata |
| **Senate.gov XML** | Senate roll-call votes | Direct HTTP download (no key) | None documented | **Primary** for Senate votes (Congress.gov API is House-only for roll calls as of mid-2025) |
| **unitedstates/congress** | Normalized vote JSON + crosswalks | GitHub scraper or pre-built JSON | Self-throttled | **Recommended** unified vote loader for both chambers |
| **OpenSecrets Bulk Data** | Member donor/industry profiles, lobbying aggregates | Free account (educational use); manual approval | No published API rate limit (bulk download) | **Primary** for member donor profiles |
| **FEC Bulk Data** | Raw itemized contributions (SQL showcase / case studies) | Direct download (no key) | None | **Secondary** — one cycle deep-dive only |
| **OpenFEC API** | Targeted contribution lookups | Free API key | **1,000 requests/hour** (up to 7,200 on request) | Supplemental queries only |
| **LDA REST API** | Bill-specific lobbying (support/oppose via issue descriptions) | Free API key (optional) | **15 req/min** anonymous; **120 req/min** with key | **Primary** for bill-side interest mapping |
| **OpenSecrets Lobbying** | Pre-aggregated lobbying by client/org | Bulk download (same account) | N/A | **Fallback** if LDA entity matching is too noisy |

---

## 1. Roll-Call Voting Data

### ProPublica Congress API — RETIRED

- **Status:** Officially sunset **July 10, 2024**. New API keys are no longer issued.
- **Historical limits:** 5,000 requests/day when active.
- **Replacement:** Congress.gov API (Library of Congress).

**Do not build against ProPublica.** Document this migration in any portfolio narrative.

### Congress.gov API (recommended for House + bills)

| Item | Detail |
|------|--------|
| Sign-up | https://api.congress.gov/sign-up/ (uses api.data.gov umbrella key) |
| Base URL | `https://api.congress.gov/v3/` |
| Auth | Header: `X-API-Key: <key>` |
| Rate limit | **5,000 requests/hour** (increased from 1,000/hour in March 2024) |
| Format | JSON (default) or XML via `format` parameter |
| Pagination | `limit` (max 250) + `offset` |
| Docs | https://github.com/LibraryOfCongress/api.congress.gov |

**Relevant endpoints:**

```
GET /member                    # current & historical members (bioguide_id)
GET /member/{bioguideId}       # member detail + party
GET /bill/{congress}/{type}/{number}
GET /bill/{congress}/{type}/{number}/actions
GET /house-vote/{congress}/{session}/{voteNumber}
GET /house-vote/{congress}/{session}/{voteNumber}/members
```

**House roll-call votes (beta, May 2025):**

- Covers legislation-related House votes from **2023 onward** (118th Congress+).
- Member-level endpoint returns **bioguide_id** — critical for cross-dataset joins.
- Non-legislation votes (e.g., Speaker election) planned for a later phase.

**Senate roll-call votes:**

- **Not yet in Congress.gov API** as of project research date.
- Use Senate XML or `unitedstates/congress` JSON instead (see below).

### Senate.gov XML (Senate votes)

| Item | Detail |
|------|--------|
| Access | Public XML per vote; menu pages per congress/session |
| Example menu | `https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_118_2.htm` |
| Vote XML pattern | `https://www.senate.gov/legislative/LIS/roll_call_votes/vote{congress}{session}/vote_{congress}_{session}_{number}.xml` |
| Rate limits | None published; be polite (≤1 req/sec) |
| Member ID | Uses **lis_id** (Senate) vs **bioguide_id** (House/Congress.gov) |

### unitedstates/congress (unified alternative)

| Item | Detail |
|------|--------|
| Repo | https://github.com/unitedstates/congress |
| Output | JSON per vote at `data/{congress}/votes/{date}/{vote_id}/data.json` |
| Coverage | House from 1990+, Senate from 1989+ |
| IDs | Normalized vote IDs like `h1-119.2025` / `s50-112.2012` |
| Caching | Scraper caches locally; `--fast` for last 3 days only |

**Also use:** `unitedstates/congress-legislators` YAML for **bioguide_id ↔ lis_id ↔ fec_id ↔ opensecrets_id** crosswalks. This is the backbone of entity resolution.

### GovInfo / BILLSTATUS bulk (bills & sponsors)

| Item | Detail |
|------|--------|
| Access | Bulk XML/ZIP at https://www.govinfo.gov/bulkdata/BILLSTATUS |
| Auth | No key for bulk; api.data.gov key for API |
| Use | Bill titles, sponsors, cosponsors, actions, subjects |

---

## 2. Campaign Finance Data

### OpenSecrets Bulk Data (recommended for member profiles)

| Item | Detail |
|------|--------|
| Sign-up | https://www.opensecrets.org/bulk-data/signup |
| Approval | Manual review; describe project as educational/portfolio research |
| License | **Educational/non-commercial only**; credit OpenSecrets required |
| Format | Zipped CSV; pipe-delimited text fields, comma field separators |
| Docs | OpenSecrets OpenData User's Guide (data dictionaries + SQL DDL scripts) |

**Key tables for this project:**

| Table | Purpose |
|-------|---------|
| `Candidates` | CRP candidate ID ↔ FEC ID ↔ name |
| `Indivs` (Individual Contributions) | Itemized contributions with industry coding |
| `Pacs` | PAC-to-candidate flows |
| `CRP_Categories.txt` | Industry code lookup |
| `CRP_IDs.xls` | Master ID crosswalk |
| `Lobbying` tables | Client/org lobbying totals (fallback) |

**Time alignment rule:** Compare a vote in cycle *C* to contributions tagged cycle *C* (e.g., 2024 vote → 2023–2024 cycle), not lifetime totals.

**Matching challenges:**

- OpenSecrets `CRP_ID` ≠ FEC `candidate_id` ≠ `bioguide_id` — use crosswalk tables.
- Industry codes are OpenSecrets classifications, not FEC-native.
- Org names are CRP-normalized but still require fuzzy matching against LDA client names.

### FEC Bulk Data (optional deep-dive)

| Item | Detail |
|------|--------|
| Portal | https://www.fec.gov/data/browse-data/?tab=bulk-data |
| Key files | `indiv{YY}.zip` (individual contributions), `cn{YY}.zip` (candidates), `ccl{YY}.zip` (committee-candidate linkage), `itoth{YY}.zip` (committee-to-candidate) |
| Format | Pipe-delimited `.txt` |
| Size | `indiv24.zip` is **hundreds of MB to several GB** uncompressed |
| Rate limits | **None** on bulk download |
| Itemization threshold | Contributions ≥ $200 (memo items included) |

**SQL showcase path:** Load one cycle's `cn`, `cm`, `ccl`, `itoth` into normalized tables; use for one illustrative case study. Use OpenSecrets aggregates for the main overlap analysis.

### OpenFEC API (supplemental)

| Item | Detail |
|------|--------|
| Sign-up | https://api.open.fec.gov/developers/ |
| Base URL | `https://api.open.fec.gov/v1/` |
| Auth | Query param `api_key=` |
| Rate limit | **1,000/hour** default; **7,200/hour** on approval (email APIinfo@fec.gov) |
| Page size | Max 100 results per page |
| Key endpoint | `/schedules/schedule_a/` (itemized receipts) |

**Not recommended for full-session ingestion** — too many paginated calls. Use bulk data instead.

---

## 3. Lobbying & Bill-Side Interest Data

### LDA REST API (recommended)

| Item | Detail |
|------|--------|
| Register | https://lda.senate.gov/api/register/ |
| Base URL | `https://lda.senate.gov/api/v1/` |
| Auth | `Authorization: Token <key>` (optional but recommended) |
| Rate limits | **15 requests/minute** (anonymous); **120 requests/minute** (registered) |
| Docs | https://lda.senate.gov/api/redoc/v1/ |
| Migration | `lda.senate.gov` → `lda.gov` by **July 2026** — plan URL update |

**Key endpoints:**

```
GET /filings/                          # list LD-1/LD-2 filings (paginated)
GET /filings/{uuid}/                   # single filing detail
GET /contributions/                    # LD-203 contribution reports
```

**Important limitation:** The filings list endpoint returns metadata; **full lobbying activity details** (specific bills, issue codes, government entities) may require fetching individual filing records. Bill numbers appear in `lobbying_activities` nested objects when present — coverage is **incomplete** (not every bill is lobbied; not every lobbying filing names a bill).

**Position inference:** LDA does not always provide clean `support` / `oppose` labels. This project uses:

- `lobbying_activity.description` + `specific_issues` text
- `government_entities` referenced
- Issue codes (e.g., `FIN`, `HCR`) as thematic context

Store as `position` ∈ {`support`, `oppose`, `monitor`, `unclear`} with a `position_confidence` field. Default unclear rather than guessing.

### Senate bulk XML (legacy)

| Item | Detail |
|------|--------|
| URL | https://www.senate.gov/legislative/Public_Disclosure/database_download.htm |
| Format | Quarterly compressed XML (LD-1, LD-2) |
| Use | Full offline ingest if API pagination is too slow |

### House lobbying disclosure

| Item | Detail |
|------|--------|
| Portal | https://lda.gov/ (unified with Senate as of 2026 migration) |
| Note | House and Senate filings are combined in the LDA system |

### OpenSecrets Lobbying bulk (fallback)

Pre-aggregated client/registrant lobbying totals. Easier to join on org name but **loses bill-level specificity**. Use when LDA bill linkage rate is too low for a given congress.

---

## 4. Congressional Stock Disclosures (PTR)

### CongressInvests public API (primary loader)

| Item | Detail |
|------|--------|
| URL | `https://congressinfor-production.up.railway.app/trades` |
| Auth | None (free tier ~100 req/day) |
| Coverage | Aggregated House + Senate Periodic Transaction Reports |
| Loader | `python -m src.load_stock_trades` |

**Fields used:** member name, chamber, ticker, asset, transaction date, disclosure date, amount range, trade type (buy/sell).

**Member matching:** PTR filer names are fuzzy-matched to `bioguide_id` via `src/member_name_match.py` (unmatched trades retained with `member_id = NULL`).

### Official sources (authoritative, harder to parse)

| Chamber | Portal |
|---------|--------|
| House | https://disclosures-clerk.house.gov/FinancialDisclosure |
| Senate | https://efdsearch.senate.gov/search/ |

House PTRs are PDF-based; Senate EFTS provides searchable electronic forms. CongressInvests is used for MVP bulk ingest; official PDFs are the verification path for case studies.

### Stock–legislation timing analysis

**Framing:** Temporal **associations** between trades and votes on bills with curated ticker exposure — not insider trading, wrongdoing, or causal influence.

| Step | Command |
|------|---------|
| Load controversial bill catalog + ticker exposure | `python -m src.load_controversial_bills` |
| Load PTR trades | `python -m src.load_stock_trades` |
| Run timing signals | `python -m src.run_stock_analysis --window-days 90` |

**Signal types:** `purchase_before_vote`, `sale_before_vote`, `large_purchase`, `large_sale` (large = PTR bracket ≥ $50,001).

**Controversial bills:** Curated in `src/controversial_bills.py` (defense, TikTok, Social Security, energy, guns, crypto, Ukraine aid, FAA, labor, etc.). Lobbying loader auto-includes these bill IDs even without roll-call votes in DB.

**Limitations:**

- Bill→ticker mapping is illustrative, not exhaustive.
- PTR disclosure lag (up to 45 days) blurs "before vote" windows.
- Members trade for many reasons unrelated to pending legislation.
- Ticker parsing misses non-stock assets and broad funds.

---

## 5. Entity Resolution Challenges

This is the **hardest engineering problem** in the project. Document every join key and fallback.

| Entity | ID systems | Canonical key in our schema |
|--------|-----------|----------------------------|
| Members | bioguide_id, lis_id, fec_candidate_id, crp_id, govtrack_id | `members.bioguide_id` (primary) |
| Bills | congress + type + number; bill_id URI | `bills.bill_id` = `{congress}-{type}-{number}` |
| Organizations | FEC committee_id, CRP org name, LDA client_name | `organizations.org_id` + `entity_aliases` table |
| Industries | CRP Catcode, NAICS (sometimes) | `industry_code` from OpenSecrets |

**Known alias patterns:**

- `"Acme Corp"` / `"Acme Corporation"` / `"Acme Corp PAC"` / `"Acme Corporation Political Action Committee"`
- PAC contributions attributed to committee name, not parent company
- Lobbying clients listed as subsidiaries

**Approach:** `entity_aliases` table + `rapidfuzz` matching in `src/entity_matching.py`, with manual review flags for matches below confidence threshold.

---

## 6. Data Vintage & Coverage Plan

**Recommended initial scope (portfolio MVP):**

| Dimension | Scope |
|-----------|-------|
| Congress | **118th** (2023–2024) or **119th** (2025) — pick one, document choice |
| Chambers | Both House and Senate |
| Votes | All roll-call votes with bill linkage where available |
| Finance cycle | Matching 2-year cycle (e.g., 2023–2024) |
| Lobbying | Same calendar years as votes |

**Known gaps:**

- House API beta may miss some vote types before non-legislation expansion.
- Senate votes require non-API pipeline.
- LDA bill linkage is sparse for minor bills.
- OpenSecrets industry coding lags FEC by processing time.
- Independents/caucusing members: party labels vary by source and time — store `party` per vote, not just per member.

---

## 7. API Keys Checklist

Create a `.env` file (never commit) with:

```env
CONGRESS_GOV_API_KEY=       # https://api.congress.gov/sign-up/
OPENFEC_API_KEY=            # https://api.open.fec.gov/developers/ (optional)
LDA_API_KEY=                # https://lda.senate.gov/api/register/ (recommended)
CONGRESS_STOCK_API_URL=     # optional override; default CongressInvests public API
# OpenSecrets: account login, not an API key
```

---

## 8. Credits & Attribution

- Congress.gov / Library of Congress
- U.S. Senate Office of Public Records (LDA)
- Federal Election Commission
- OpenSecrets (Center for Responsive Politics) — required credit for bulk data
- unitedstates open-data projects (public domain / CC0)
