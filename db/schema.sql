-- voting-donor-tracker schema
-- SQLite-compatible; minor syntax adjustments noted for Postgres migration.
--
-- FRAMING: Tables and views describe observed associations between voting
-- positions and financial/lobbying profiles. No column implies causation.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Reference / dimension tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS election_cycles (
    cycle_id        TEXT PRIMARY KEY,          -- e.g. '2024' (FEC two-year cycle)
    cycle_label     TEXT NOT NULL,             -- e.g. '2023-2024'
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS industry_codes (
    industry_code   TEXT PRIMARY KEY,          -- OpenSecrets Catcode
    industry_name   TEXT NOT NULL,
    sector_name     TEXT
);

CREATE TABLE IF NOT EXISTS members (
    member_id       TEXT PRIMARY KEY,          -- bioguide_id (canonical)
    bioguide_id     TEXT NOT NULL UNIQUE,
    lis_id          TEXT,                      -- Senate ID (nullable for House-only)
    crp_id          TEXT,
    fec_candidate_id TEXT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    party           TEXT,                      -- current/most recent; see member_votes.party_at_vote
    state           TEXT,
    chamber         TEXT NOT NULL CHECK (chamber IN ('house', 'senate')),
    district        TEXT,                      -- NULL for senators
    in_office       INTEGER NOT NULL DEFAULT 1 CHECK (in_office IN (0, 1)),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS organizations (
    org_id          TEXT PRIMARY KEY,
    canonical_name  TEXT NOT NULL,
    org_type        TEXT CHECK (org_type IN ('company', 'pac', 'trade_association', 'nonprofit', 'other')),
    fec_committee_id TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Fuzzy-match / manual alias registry for entity resolution
CREATE TABLE IF NOT EXISTS entity_aliases (
    alias_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id          TEXT NOT NULL REFERENCES organizations(org_id),
    alias_name      TEXT NOT NULL,
    source_system   TEXT NOT NULL,             -- 'fec', 'opensecrets', 'lda', 'manual'
    match_method    TEXT NOT NULL,             -- 'exact', 'fuzzy', 'manual'
    match_score     REAL,                      -- 0-100; NULL for exact/manual
    reviewed        INTEGER NOT NULL DEFAULT 0 CHECK (reviewed IN (0, 1)),
    UNIQUE (alias_name, source_system),
    FOREIGN KEY (org_id) REFERENCES organizations(org_id)
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id         TEXT PRIMARY KEY,          -- '{congress}-{type}-{number}' e.g. '118-hr-1'
    congress        INTEGER NOT NULL,
    bill_type       TEXT NOT NULL,             -- hr, s, hjres, etc.
    bill_number     INTEGER NOT NULL,
    title           TEXT,
    short_title     TEXT,
    primary_sponsor_id TEXT REFERENCES members(member_id),
    introduced_date DATE,
    policy_area     TEXT,
    subjects_json   TEXT,                      -- JSON array of subject strings
    source_url      TEXT,
    UNIQUE (congress, bill_type, bill_number)
);

-- ---------------------------------------------------------------------------
-- Voting fact tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS votes (
    vote_id         TEXT PRIMARY KEY,          -- e.g. 'h1-118.2023' or 's50-118.2024'
    congress        INTEGER NOT NULL,
    session         INTEGER NOT NULL,
    chamber         TEXT NOT NULL CHECK (chamber IN ('house', 'senate')),
    vote_number     INTEGER NOT NULL,
    vote_date       DATE NOT NULL,
    vote_question   TEXT,
    vote_result     TEXT,
    bill_id         TEXT REFERENCES bills(bill_id),
    source_system   TEXT NOT NULL,             -- 'congress_gov', 'senate_xml', 'unitedstates'
    source_url      TEXT,
    UNIQUE (chamber, congress, session, vote_number)
);

CREATE TABLE IF NOT EXISTS member_votes (
    member_vote_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    vote_id         TEXT NOT NULL REFERENCES votes(vote_id),
    member_id       TEXT NOT NULL REFERENCES members(member_id),
    position        TEXT NOT NULL CHECK (position IN ('yea', 'nay', 'present', 'not_voting')),
    party_at_vote   TEXT NOT NULL,             -- party label at time of vote (D/R/I/etc.)
    -- Populated by ETL from v_party_majority_by_vote + v_cross_party_flags
    party_majority_position TEXT CHECK (party_majority_position IN ('yea', 'nay', 'tie', 'unknown')),
    is_cross_party  INTEGER CHECK (is_cross_party IN (0, 1)),
    UNIQUE (vote_id, member_id)
);

-- ---------------------------------------------------------------------------
-- Campaign finance fact tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS contributions (
    contribution_id TEXT PRIMARY KEY,
    member_id       TEXT NOT NULL REFERENCES members(member_id),
    org_id          TEXT REFERENCES organizations(org_id),
    donor_org_raw   TEXT NOT NULL,             -- as reported in source
    industry_code   TEXT REFERENCES industry_codes(industry_code),
    amount          REAL NOT NULL CHECK (amount >= 0),
    contribution_date DATE,
    cycle_id        TEXT NOT NULL REFERENCES election_cycles(cycle_id),
    source_system   TEXT NOT NULL,             -- 'opensecrets', 'fec'
    source_record_id TEXT
);

-- Pre-aggregated member donor profile (top-N per cycle) — built via SQL, consumed by overlap analysis
CREATE TABLE IF NOT EXISTS member_donor_profiles (
    profile_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id       TEXT NOT NULL REFERENCES members(member_id),
    cycle_id        TEXT NOT NULL REFERENCES election_cycles(cycle_id),
    org_id          TEXT REFERENCES organizations(org_id),
    donor_org_raw   TEXT,
    industry_code   TEXT REFERENCES industry_codes(industry_code),
    total_amount    REAL NOT NULL,
    contribution_count INTEGER NOT NULL,
    rank_by_amount  INTEGER NOT NULL,          -- 1 = top donor
    top_n           INTEGER NOT NULL DEFAULT 20,
    UNIQUE (member_id, cycle_id, rank_by_amount, top_n)
);

-- ---------------------------------------------------------------------------
-- Lobbying fact tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS lobbying_records (
    lobbying_id     TEXT PRIMARY KEY,
    bill_id         TEXT REFERENCES bills(bill_id),
    org_id          TEXT REFERENCES organizations(org_id),
    org_name_raw    TEXT NOT NULL,
    registrant_name TEXT,
    position        TEXT NOT NULL CHECK (position IN ('support', 'oppose', 'monitor', 'unclear')),
    position_confidence REAL CHECK (position_confidence BETWEEN 0 AND 1),
    issue_codes     TEXT,                      -- comma-separated or JSON
    filing_id       TEXT,                      -- LDA filing UUID
    filing_date     DATE,
    cycle_id        TEXT REFERENCES election_cycles(cycle_id),
    source_system   TEXT NOT NULL DEFAULT 'lda',
    notes           TEXT                       -- why position was classified this way
);

-- ---------------------------------------------------------------------------
-- Analysis output tables (materialized from views for notebook/chart consumption)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS donor_overlap_scores (
    overlap_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    member_vote_id  INTEGER NOT NULL REFERENCES member_votes(member_vote_id),
    member_id       TEXT NOT NULL REFERENCES members(member_id),
    vote_id         TEXT NOT NULL REFERENCES votes(vote_id),
    bill_id         TEXT REFERENCES bills(bill_id),
    cycle_id        TEXT NOT NULL REFERENCES election_cycles(cycle_id),
    -- Overlap: share of member's top-N donors matching orgs lobbying on same side
    overlap_count   INTEGER NOT NULL,
    profile_size    INTEGER NOT NULL,          -- N (e.g. 20)
    overlap_score   REAL NOT NULL,             -- overlap_count / profile_size
    compared_position TEXT NOT NULL,           -- position member took on vote
    lobbying_side   TEXT NOT NULL,             -- which lobbying position bucket we matched against
    computed_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_member_votes_vote ON member_votes(vote_id);
CREATE INDEX IF NOT EXISTS idx_member_votes_member ON member_votes(member_id);
CREATE INDEX IF NOT EXISTS idx_member_votes_cross ON member_votes(is_cross_party) WHERE is_cross_party = 1;
CREATE INDEX IF NOT EXISTS idx_contributions_member_cycle ON contributions(member_id, cycle_id);
CREATE INDEX IF NOT EXISTS idx_lobbying_bill ON lobbying_records(bill_id);
CREATE INDEX IF NOT EXISTS idx_votes_bill ON votes(bill_id);
CREATE INDEX IF NOT EXISTS idx_votes_date ON votes(vote_date);
CREATE INDEX IF NOT EXISTS idx_entity_aliases_name ON entity_aliases(alias_name);

-- ---------------------------------------------------------------------------
-- SQL Views: party majority detection & cross-party flagging
-- ---------------------------------------------------------------------------

-- Map vote date to election cycle for time-aligned finance comparison
CREATE VIEW IF NOT EXISTS v_vote_cycles AS
SELECT
    v.vote_id,
    v.vote_date,
    ec.cycle_id
FROM votes v
JOIN election_cycles ec
  ON v.vote_date BETWEEN ec.start_date AND ec.end_date;

-- Party majority position per vote (yea/nay/tie/unknown)
-- Only counts yea/nay for majority; present/not_voting excluded from denominator.
CREATE VIEW IF NOT EXISTS v_party_majority_by_vote AS
WITH party_position_counts AS (
    SELECT
        mv.vote_id,
        mv.party_at_vote,
        mv.position,
        COUNT(*) AS position_count
    FROM member_votes mv
    WHERE mv.position IN ('yea', 'nay')
    GROUP BY mv.vote_id, mv.party_at_vote, mv.position
),
party_totals AS (
    SELECT
        vote_id,
        party_at_vote,
        SUM(position_count) AS party_total
    FROM party_position_counts
    GROUP BY vote_id, party_at_vote
),
ranked AS (
    SELECT
        ppc.vote_id,
        ppc.party_at_vote,
        ppc.position,
        ppc.position_count,
        ROUND(1.0 * ppc.position_count / pt.party_total, 4) AS share,
        ROW_NUMBER() OVER (
            PARTITION BY ppc.vote_id, ppc.party_at_vote
            ORDER BY ppc.position_count DESC, ppc.position ASC
        ) AS rn,
        MAX(ppc.position_count) OVER (
            PARTITION BY ppc.vote_id, ppc.party_at_vote
        ) AS max_count
    FROM party_position_counts ppc
    JOIN party_totals pt
      ON ppc.vote_id = pt.vote_id
     AND ppc.party_at_vote = pt.party_at_vote
)
SELECT
    vote_id,
    party_at_vote,
    CASE
        WHEN SUM(CASE WHEN position_count = max_count THEN 1 ELSE 0 END) > 1 THEN 'tie'
        ELSE MAX(CASE WHEN rn = 1 THEN position END)
    END AS party_majority_position,
    MAX(CASE WHEN rn = 1 THEN share END) AS majority_share
FROM ranked
GROUP BY vote_id, party_at_vote;

-- Flag cross-party votes: member position differs from own party majority
CREATE VIEW IF NOT EXISTS v_cross_party_flags AS
SELECT
    mv.member_vote_id,
    mv.vote_id,
    mv.member_id,
    mv.position,
    mv.party_at_vote,
    pm.party_majority_position,
    CASE
        WHEN pm.party_majority_position IN ('tie', 'unknown') THEN 0
        WHEN mv.position NOT IN ('yea', 'nay') THEN 0
        WHEN mv.position != pm.party_majority_position THEN 1
        ELSE 0
    END AS is_cross_party
FROM member_votes mv
LEFT JOIN v_party_majority_by_vote pm
  ON mv.vote_id = pm.vote_id
 AND mv.party_at_vote = pm.party_at_vote;

-- Member crossing rate (descriptive stat) — symmetric for all parties
CREATE VIEW IF NOT EXISTS v_member_crossing_rates AS
SELECT
    mv.member_id,
    m.full_name,
    mv.party_at_vote AS party,
    m.chamber,
    COUNT(*) AS total_votes,
    SUM(CASE WHEN cf.is_cross_party = 1 THEN 1 ELSE 0 END) AS cross_party_votes,
    ROUND(
        1.0 * SUM(CASE WHEN cf.is_cross_party = 1 THEN 1 ELSE 0 END) / COUNT(*),
        4
    ) AS crossing_rate
FROM member_votes mv
JOIN members m ON mv.member_id = m.member_id
JOIN v_cross_party_flags cf ON mv.member_vote_id = cf.member_vote_id
WHERE mv.position IN ('yea', 'nay')
GROUP BY mv.member_id, m.full_name, mv.party_at_vote, m.chamber;

-- Party-stratified crossing summary (hard requirement: report both sides)
CREATE VIEW IF NOT EXISTS v_crossing_rates_by_party AS
SELECT
    party,
    chamber,
    COUNT(DISTINCT member_id) AS member_count,
    ROUND(AVG(crossing_rate), 4) AS avg_crossing_rate,
    ROUND(MIN(crossing_rate), 4) AS min_crossing_rate,
    ROUND(MAX(crossing_rate), 4) AS max_crossing_rate
FROM v_member_crossing_rates
GROUP BY party, chamber
ORDER BY party, chamber;

-- ---------------------------------------------------------------------------
-- SQL Views: donor profile aggregation
-- ---------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_member_top_donors AS
WITH ranked AS (
    SELECT
        c.member_id,
        c.cycle_id,
        COALESCE(c.org_id, c.donor_org_raw) AS donor_key,
        c.org_id,
        c.donor_org_raw,
        c.industry_code,
        SUM(c.amount) AS total_amount,
        COUNT(*) AS contribution_count,
        ROW_NUMBER() OVER (
            PARTITION BY c.member_id, c.cycle_id
            ORDER BY SUM(c.amount) DESC
        ) AS rank_by_amount
    FROM contributions c
    GROUP BY c.member_id, c.cycle_id, COALESCE(c.org_id, c.donor_org_raw),
             c.org_id, c.donor_org_raw, c.industry_code
)
SELECT *
FROM ranked
WHERE rank_by_amount <= 20;

-- ---------------------------------------------------------------------------
-- SQL Views: donor overlap (associational comparison)
-- ---------------------------------------------------------------------------

-- For cross-party votes: overlap between member top donors and bill lobbying orgs
-- on the same side as the member's vote position.
-- NOTE: This measures association, not influence.
CREATE VIEW IF NOT EXISTS v_donor_overlap_cross_party AS
WITH cross_votes AS (
    SELECT
        mv.member_vote_id,
        mv.member_id,
        mv.vote_id,
        mv.position,
        v.bill_id,
        vc.cycle_id,
        cf.is_cross_party
    FROM member_votes mv
    JOIN votes v ON mv.vote_id = v.vote_id
    JOIN v_vote_cycles vc ON v.vote_id = vc.vote_id
    JOIN v_cross_party_flags cf ON mv.member_vote_id = cf.member_vote_id
    WHERE cf.is_cross_party = 1
      AND v.bill_id IS NOT NULL
),
member_donors AS (
    SELECT
        cv.member_vote_id,
        cv.member_id,
        cv.vote_id,
        cv.bill_id,
        cv.cycle_id,
        cv.position,
        mdp.org_id,
        mdp.donor_org_raw,
        mdp.rank_by_amount
    FROM cross_votes cv
    JOIN member_donor_profiles mdp
      ON cv.member_id = mdp.member_id
     AND cv.cycle_id = mdp.cycle_id
    WHERE mdp.rank_by_amount <= 20
),
bill_lobbying AS (
    SELECT
        lr.bill_id,
        lr.org_id,
        lr.org_name_raw,
        lr.position AS lobbying_position
    FROM lobbying_records lr
    WHERE lr.bill_id IS NOT NULL
      AND lr.position IN ('support', 'oppose')
),
overlap_detail AS (
    SELECT
        md.member_vote_id,
        md.member_id,
        md.vote_id,
        md.bill_id,
        md.cycle_id,
        md.position AS member_position,
        md.org_id AS member_donor_org_id,
        bl.org_id AS lobbying_org_id,
        bl.lobbying_position,
        CASE
            WHEN md.org_id IS NOT NULL AND bl.org_id IS NOT NULL AND md.org_id = bl.org_id THEN 1
            WHEN md.org_id IS NULL THEN 0  -- unresolved org; handled in Python fuzzy pass
            ELSE 0
        END AS is_overlap
    FROM member_donors md
    JOIN bill_lobbying bl ON md.bill_id = bl.bill_id
    -- Member voted yea → compare to lobbying 'support'; nay → 'oppose'
    WHERE (md.position = 'yea' AND bl.lobbying_position = 'support')
       OR (md.position = 'nay' AND bl.lobbying_position = 'oppose')
)
SELECT
    member_vote_id,
    member_id,
    vote_id,
    bill_id,
    cycle_id,
    member_position,
    COUNT(DISTINCT member_donor_org_id) AS profile_size,
    COUNT(DISTINCT CASE WHEN is_overlap = 1 THEN member_donor_org_id END) AS overlap_count,
    ROUND(
        1.0 * COUNT(DISTINCT CASE WHEN is_overlap = 1 THEN member_donor_org_id END)
        / NULLIF(COUNT(DISTINCT member_donor_org_id), 0),
        4
    ) AS overlap_score
FROM overlap_detail
GROUP BY member_vote_id, member_id, vote_id, bill_id, cycle_id, member_position;

-- Comparison baseline: non-crossing members on same votes
CREATE VIEW IF NOT EXISTS v_donor_overlap_non_cross_party AS
WITH non_cross AS (
    SELECT
        mv.member_vote_id,
        mv.member_id,
        mv.vote_id,
        mv.position,
        v.bill_id,
        vc.cycle_id
    FROM member_votes mv
    JOIN votes v ON mv.vote_id = v.vote_id
    JOIN v_vote_cycles vc ON v.vote_id = vc.vote_id
    JOIN v_cross_party_flags cf ON mv.member_vote_id = cf.member_vote_id
    WHERE cf.is_cross_party = 0
      AND v.bill_id IS NOT NULL
      AND mv.position IN ('yea', 'nay')
)
-- Reuse same overlap logic via parallel CTE structure (abbreviated; see overlap_analysis.py for fuzzy pass)
SELECT
    nc.member_vote_id,
    nc.member_id,
    nc.vote_id,
    nc.bill_id,
    nc.cycle_id,
    nc.position AS member_position,
    0 AS overlap_count,   -- placeholder; populated by ETL pipeline with full logic
    20 AS profile_size,
    0.0 AS overlap_score
FROM non_cross nc
WHERE 1 = 0;  -- disabled placeholder view; non-cross overlap computed in overlap_analysis.py
