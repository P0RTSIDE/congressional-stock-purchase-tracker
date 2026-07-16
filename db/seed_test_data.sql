-- Seed data for end-to-end pipeline smoke test
-- Synthetic members/votes/contributions/lobbying — NOT real congressional data.
-- Purpose: validate schema, views, and join logic before scaling to live sources.

INSERT INTO election_cycles (cycle_id, cycle_label, start_date, end_date) VALUES
    ('2024', '2023-2024', '2023-01-03', '2024-12-31');

INSERT INTO industry_codes (industry_code, industry_name, sector_name) VALUES
    ('A01', 'Agribusiness', 'Agriculture'),
    ('F03', 'Commercial Banks', 'Finance'),
    ('H01', 'Health Services/HMOs', 'Health');

INSERT INTO members (member_id, bioguide_id, first_name, last_name, full_name, party, state, chamber, district) VALUES
    ('A000001', 'A000001', 'Alex', 'Alpha', 'Alex Alpha', 'D', 'CA', 'house', '12'),
    ('B000002', 'B000002', 'Blake', 'Beta', 'Blake Beta', 'D', 'CA', 'house', '07'),
    ('C000003', 'C000003', 'Casey', 'Gamma', 'Casey Gamma', 'R', 'TX', 'house', '14'),
    ('D000004', 'D000004', 'Dana', 'Delta', 'Dana Delta', 'R', 'TX', 'house', '03'),
    ('E000005', 'E000005', 'Evan', 'Epsilon', 'Evan Epsilon', 'D', 'CA', 'house', '02'),
    ('F000006', 'F000006', 'Finn', 'Foxtrot', 'Finn Foxtrot', 'R', 'TX', 'house', '08');

INSERT INTO organizations (org_id, canonical_name, org_type) VALUES
    ('org_agri_co', 'Heartland Agri Co', 'company'),
    ('org_bank_pa', 'Metro Bank PAC', 'pac'),
    ('org_health_sys', 'National Health System', 'company');

INSERT INTO entity_aliases (org_id, alias_name, source_system, match_method, match_score, reviewed) VALUES
    ('org_agri_co', 'Heartland Agri Co', 'opensecrets', 'exact', 100, 1),
    ('org_agri_co', 'Heartland Agri Company', 'lda', 'fuzzy', 92.5, 1),
    ('org_bank_pa', 'Metro Bank PAC', 'opensecrets', 'exact', 100, 1),
    ('org_health_sys', 'National Health System', 'opensecrets', 'exact', 100, 1),
    ('org_health_sys', 'National Health System Inc', 'lda', 'fuzzy', 95.0, 1);

INSERT INTO bills (bill_id, congress, bill_type, bill_number, title, primary_sponsor_id, introduced_date, policy_area) VALUES
    ('118-hr-100', 118, 'hr', 100, 'Agriculture Subsidy Reform Act', 'A000001', '2023-03-15', 'Agriculture'),
    ('118-hr-200', 118, 'hr', 200, 'Banking Transparency Act', 'C000003', '2023-06-01', 'Finance');

INSERT INTO votes (vote_id, congress, session, chamber, vote_number, vote_date, vote_question, vote_result, bill_id, source_system) VALUES
    ('h10-118.2023', 118, 1, 'house', 10, '2023-04-01', 'On Passage', 'Passed', '118-hr-100', 'seed'),
    ('h20-118.2023', 118, 1, 'house', 20, '2023-07-15', 'On Passage', 'Failed', '118-hr-200', 'seed');

-- Vote 10: D majority yea (2-1), R majority nay (2-0). Blake Beta (D) crosses to nay.
INSERT INTO member_votes (vote_id, member_id, position, party_at_vote) VALUES
    ('h10-118.2023', 'A000001', 'yea', 'D'),
    ('h10-118.2023', 'B000002', 'nay', 'D'),
    ('h10-118.2023', 'E000005', 'yea', 'D'),
    ('h10-118.2023', 'C000003', 'nay', 'R'),
    ('h10-118.2023', 'D000004', 'nay', 'R'),
    ('h10-118.2023', 'F000006', 'nay', 'R');

-- Vote 20: D majority nay (3-0), R majority yea (2-1). Dana Delta (R) crosses to nay.
INSERT INTO member_votes (vote_id, member_id, position, party_at_vote) VALUES
    ('h20-118.2023', 'A000001', 'nay', 'D'),
    ('h20-118.2023', 'B000002', 'nay', 'D'),
    ('h20-118.2023', 'E000005', 'nay', 'D'),
    ('h20-118.2023', 'C000003', 'yea', 'R'),
    ('h20-118.2023', 'D000004', 'nay', 'R'),
    ('h20-118.2023', 'F000006', 'yea', 'R');

-- Contributions: Blake Beta has agribusiness donor; Dana Delta has health donor
INSERT INTO contributions (contribution_id, member_id, org_id, donor_org_raw, industry_code, amount, contribution_date, cycle_id, source_system) VALUES
    ('c001', 'B000002', 'org_agri_co', 'Heartland Agri Co', 'A01', 5000, '2023-05-01', '2024', 'seed'),
    ('c002', 'B000002', 'org_bank_pa', 'Metro Bank PAC', 'F03', 2500, '2023-08-01', '2024', 'seed'),
    ('c003', 'D000004', 'org_health_sys', 'National Health System', 'H01', 7500, '2023-09-01', '2024', 'seed'),
    ('c004', 'C000003', 'org_bank_pa', 'Metro Bank PAC', 'F03', 10000, '2023-06-15', '2024', 'seed');

INSERT INTO member_donor_profiles (member_id, cycle_id, org_id, donor_org_raw, industry_code, total_amount, contribution_count, rank_by_amount, top_n) VALUES
    ('B000002', '2024', 'org_agri_co', 'Heartland Agri Co', 'A01', 5000, 1, 1, 20),
    ('B000002', '2024', 'org_bank_pa', 'Metro Bank PAC', 'F03', 2500, 1, 2, 20),
    ('D000004', '2024', 'org_health_sys', 'National Health System', 'H01', 7500, 1, 1, 20),
    ('C000003', '2024', 'org_bank_pa', 'Metro Bank PAC', 'F03', 10000, 1, 1, 20);

-- Lobbying: HR-100 has agribusiness lobbying FOR (support); HR-200 has bank support, health oppose
INSERT INTO lobbying_records (lobbying_id, bill_id, org_id, org_name_raw, position, position_confidence, cycle_id, source_system) VALUES
    ('l001', '118-hr-100', 'org_agri_co', 'Heartland Agri Company', 'support', 0.9, '2024', 'seed'),
    ('l002', '118-hr-200', 'org_bank_pa', 'Metro Bank PAC', 'support', 0.95, '2024', 'seed'),
    ('l003', '118-hr-200', 'org_health_sys', 'National Health System Inc', 'oppose', 0.85, '2024', 'seed');

-- Populate party majority + cross-party flags from views
UPDATE member_votes
SET
    party_majority_position = (
        SELECT party_majority_position
        FROM v_party_majority_by_vote pm
        WHERE pm.vote_id = member_votes.vote_id
          AND pm.party_at_vote = member_votes.party_at_vote
    ),
    is_cross_party = (
        SELECT is_cross_party
        FROM v_cross_party_flags cf
        WHERE cf.member_vote_id = member_votes.member_vote_id
    );
