-- Stock disclosure + controversial bill extensions
-- FRAMING: Temporal associations between PTR trades and legislative events.
-- NOT evidence of insider trading, wrongdoing, or causal influence.

-- ---------------------------------------------------------------------------
-- Controversial / high-salience bills (curated + tagged)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS controversial_bills (
    bill_id         TEXT PRIMARY KEY REFERENCES bills(bill_id),
    controversy_tags TEXT NOT NULL,           -- JSON array: defense, tech, healthcare, etc.
    salience_score  REAL DEFAULT 1.0,         -- descriptive weight for reporting
    notes           TEXT,
    source          TEXT NOT NULL DEFAULT 'curated'
);

-- Bill exposure: which tickers/sectors may be materially affected
CREATE TABLE IF NOT EXISTS bill_stock_exposure (
    exposure_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id         TEXT NOT NULL REFERENCES bills(bill_id),
    ticker          TEXT,                      -- e.g. LMT, NULL if sector-only
    company_name    TEXT,
    sector          TEXT,
    exposure_type   TEXT NOT NULL CHECK (exposure_type IN ('direct', 'sector', 'supply_chain')),
    confidence      REAL DEFAULT 0.5,
    notes           TEXT,
    UNIQUE (bill_id, ticker, company_name, sector)
);

-- ---------------------------------------------------------------------------
-- Periodic Transaction Reports (PTR) / stock trades
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS stock_transactions (
    transaction_id  TEXT PRIMARY KEY,
    member_id       TEXT REFERENCES members(member_id),
    member_name_raw TEXT NOT NULL,
    chamber         TEXT CHECK (chamber IN ('house', 'senate')),
    ticker          TEXT,
    asset_name      TEXT,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'sale', 'exchange', 'other')),
    transaction_date DATE NOT NULL,
    disclosed_date  DATE,
    amount_min      REAL,
    amount_max      REAL,
    amount_raw      TEXT,
    source_system   TEXT NOT NULL,
    source_url      TEXT,
    ptr_year        INTEGER
);

-- ---------------------------------------------------------------------------
-- Analysis output: stock activity timing vs legislation
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS stock_legislation_signals (
    signal_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    member_vote_id  INTEGER REFERENCES member_votes(member_vote_id),
    member_id       TEXT NOT NULL REFERENCES members(member_id),
    vote_id         TEXT NOT NULL REFERENCES votes(vote_id),
    bill_id         TEXT NOT NULL REFERENCES bills(bill_id),
    transaction_id  TEXT NOT NULL REFERENCES stock_transactions(transaction_id),
    ticker          TEXT,
    transaction_type TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    vote_date       DATE NOT NULL,
    days_before_vote INTEGER NOT NULL,
    exposure_type   TEXT,
    signal_type     TEXT NOT NULL CHECK (signal_type IN (
        'purchase_before_vote', 'sale_before_vote', 'large_purchase', 'large_sale'
    )),
    is_cross_party  INTEGER,
    party_at_vote   TEXT,
    -- Associational flag only
    notes           TEXT,
    computed_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_stock_tx_member_date ON stock_transactions(member_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_stock_tx_ticker ON stock_transactions(ticker);
CREATE INDEX IF NOT EXISTS idx_bill_exposure_bill ON bill_stock_exposure(bill_id);
CREATE INDEX IF NOT EXISTS idx_stock_signals_bill ON stock_legislation_signals(bill_id);
