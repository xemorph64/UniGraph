-- ============================================================
-- UniGraph AI — Fraudulent Transaction Test Data
-- PSBs Hackathon Series 2026 | IDEA 2.0
-- Team: Beyond Just Programming | Union Bank of India
-- ============================================================
-- 5 Fraud Scenarios:
--   1. Round-Tripping
--   2. Structuring / Smurfing
--   3. Dormant Account Awakening
--   4. Rapid Layering
--   5. Mule Account Network
-- ============================================================

-- ============================================================
-- SCHEMA SETUP
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    account_id        VARCHAR(20) PRIMARY KEY,
    customer_name     VARCHAR(100),
    account_type      VARCHAR(20),
    kyc_tier          INTEGER,
    risk_score        DECIMAL(5,2),
    is_dormant        BOOLEAN DEFAULT FALSE,
    last_active       TIMESTAMP,
    account_age_days  INTEGER,
    balance           DECIMAL(15,2),
    branch_code       VARCHAR(10),
    ifsc_code         VARCHAR(15),
    pep_flag          BOOLEAN DEFAULT FALSE,
    sanction_flag     BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id            VARCHAR(30) PRIMARY KEY,
    sender_account    VARCHAR(20) REFERENCES accounts(account_id),
    receiver_account  VARCHAR(20) REFERENCES accounts(account_id),
    amount            DECIMAL(15,2),
    channel           VARCHAR(10),
    txn_timestamp     TIMESTAMP,
    device_id         VARCHAR(30),
    ip_address        VARCHAR(20),
    geo_lat           DECIMAL(9,6),
    geo_lon           DECIMAL(9,6),
    utr_number        VARCHAR(30),
    narration         VARCHAR(200),
    status            VARCHAR(20) DEFAULT 'SUCCESS',
    is_flagged        BOOLEAN DEFAULT FALSE,
    fraud_flag_type   VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id          VARCHAR(20) PRIMARY KEY,
    txn_id            VARCHAR(30) REFERENCES transactions(txn_id),
    account_id        VARCHAR(20) REFERENCES accounts(account_id),
    fraud_type        VARCHAR(50),
    ensemble_score    DECIMAL(5,2),
    drools_score      DECIMAL(5,2),
    gnn_score         DECIMAL(5,2),
    isolation_score   DECIMAL(5,2),
    alert_timestamp   TIMESTAMP,
    status            VARCHAR(20) DEFAULT 'OPEN',
    pmla_citation     VARCHAR(100),
    fatf_typology     VARCHAR(100)
);

-- ============================================================
-- CLEAN UP PREVIOUS TEST DATA
-- ============================================================

DELETE FROM alerts;
DELETE FROM transactions;
DELETE FROM accounts;

-- ============================================================
-- SCENARIO 1 — ROUND-TRIPPING
-- ₹4,80,000 cycled across 3 accounts and returns to origin
-- Accounts: Mumbai → Delhi → Pune → Mumbai
-- Channel: RTGS → NEFT → UPI
-- Time window: 4 hours
-- Detection: Johnson's Algorithm — cycle detected
-- ============================================================

INSERT INTO accounts VALUES
('ACC-RT-MUM-001', 'Rajan Shah',         'CURRENT', 2, 45.00, FALSE, NOW() - INTERVAL '30 days',  365, 850000.00,  'MUM-001', 'UBIN0504100', FALSE, FALSE),
('ACC-RT-DEL-002', 'Delhi Enterprises',  'CURRENT', 1, 55.00, FALSE, NOW() - INTERVAL '15 days',  280, 200000.00,  'DEL-002', 'UBIN0601200', FALSE, FALSE),
('ACC-RT-PUN-003', 'Pune Trading Co.',   'CURRENT', 1, 60.00, FALSE, NOW() - INTERVAL '10 days',  190, 150000.00,  'PUN-003', 'UBIN0701300', FALSE, FALSE);

INSERT INTO transactions VALUES
('TXN-RT-001', 'ACC-RT-MUM-001', 'ACC-RT-DEL-002', 480000.00, 'RTGS', NOW() - INTERVAL '4 hours',  'DEV-MUM-9912', '103.45.67.89',  19.0760, 72.8777, 'UBOI260108001', 'Payment for goods',         'SUCCESS', FALSE, NULL),
('TXN-RT-002', 'ACC-RT-DEL-002', 'ACC-RT-PUN-003', 475000.00, 'NEFT', NOW() - INTERVAL '2 hours',  'DEV-DEL-4421', '103.78.23.11',  28.6139, 77.2090, 'UBOI260108002', 'Transfer of funds',         'SUCCESS', FALSE, NULL),
('TXN-RT-003', 'ACC-RT-PUN-003', 'ACC-RT-MUM-001', 470000.00, 'UPI',  NOW() - INTERVAL '30 minutes','DEV-PUN-7734', '103.12.89.45', 18.5204, 73.8567, 'UBOI260108003', 'Service fee settlement',    'SUCCESS', FALSE, NULL);

INSERT INTO alerts VALUES
('ALT-2024-0847', 'TXN-RT-003', 'ACC-RT-MUM-001', 'Round-Tripping', 87.00, 82.00, 91.00, 79.00, NOW(), 'OPEN', 'PMLA Section 12 — STR Obligation', 'FATF ML-Layering-003');

-- ============================================================
-- SCENARIO 2 — STRUCTURING / SMURFING
-- 7 deposits of ₹49,000 each into same account within 24 hours
-- All deposits just below ₹50,000 reporting threshold
-- Channel: UPI across multiple senders
-- Detection: Sliding window aggregation — structuring signal
-- ============================================================

INSERT INTO accounts VALUES
('ACC-ST-RECV-001', 'Priya Merchants Ltd', 'SAVINGS', 1, 70.00, FALSE, NOW() - INTERVAL '5 days',   60,  50000.00, 'MUM-002', 'UBIN0504200', FALSE, FALSE),
('ACC-ST-SND-001',  'Arjun Patil',         'SAVINGS', 2, 20.00, FALSE, NOW() - INTERVAL '90 days',  400, 100000.00, 'MUM-003', 'UBIN0504300', FALSE, FALSE),
('ACC-ST-SND-002',  'Kavita Sharma',       'SAVINGS', 2, 20.00, FALSE, NOW() - INTERVAL '80 days',  380, 100000.00, 'MUM-004', 'UBIN0504400', FALSE, FALSE),
('ACC-ST-SND-003',  'Suresh Nair',         'SAVINGS', 2, 20.00, FALSE, NOW() - INTERVAL '70 days',  360, 100000.00, 'MUM-005', 'UBIN0504500', FALSE, FALSE),
('ACC-ST-SND-004',  'Vikram Gupta',        'SAVINGS', 2, 20.00, FALSE, NOW() - INTERVAL '60 days',  340, 100000.00, 'MUM-006', 'UBIN0504600', FALSE, FALSE),
('ACC-ST-SND-005',  'Meena Joshi',         'SAVINGS', 2, 20.00, FALSE, NOW() - INTERVAL '50 days',  320, 100000.00, 'MUM-007', 'UBIN0504700', FALSE, FALSE),
('ACC-ST-SND-006',  'Ankit Verma',         'SAVINGS', 2, 20.00, FALSE, NOW() - INTERVAL '40 days',  300, 100000.00, 'MUM-008', 'UBIN0504800', FALSE, FALSE),
('ACC-ST-SND-007',  'Deepa Singh',         'SAVINGS', 2, 20.00, FALSE, NOW() - INTERVAL '30 days',  280, 100000.00, 'MUM-009', 'UBIN0504900', FALSE, FALSE);

INSERT INTO transactions VALUES
('TXN-ST-001', 'ACC-ST-SND-001', 'ACC-ST-RECV-001', 49000.00, 'UPI', NOW() - INTERVAL '23 hours', 'DEV-SND-001', '103.11.22.33', 19.0760, 72.8777, 'UBOI260108011', 'Personal transfer', 'SUCCESS', FALSE, NULL),
('TXN-ST-002', 'ACC-ST-SND-002', 'ACC-ST-RECV-001', 49000.00, 'UPI', NOW() - INTERVAL '20 hours', 'DEV-SND-002', '103.22.33.44', 19.0760, 72.8777, 'UBOI260108012', 'Personal transfer', 'SUCCESS', FALSE, NULL),
('TXN-ST-003', 'ACC-ST-SND-003', 'ACC-ST-RECV-001', 49000.00, 'UPI', NOW() - INTERVAL '17 hours', 'DEV-SND-003', '103.33.44.55', 19.0760, 72.8777, 'UBOI260108013', 'Personal transfer', 'SUCCESS', FALSE, NULL),
('TXN-ST-004', 'ACC-ST-SND-004', 'ACC-ST-RECV-001', 49000.00, 'UPI', NOW() - INTERVAL '14 hours', 'DEV-SND-004', '103.44.55.66', 19.0760, 72.8777, 'UBOI260108014', 'Personal transfer', 'SUCCESS', FALSE, NULL),
('TXN-ST-005', 'ACC-ST-SND-005', 'ACC-ST-RECV-001', 49000.00, 'UPI', NOW() - INTERVAL '10 hours', 'DEV-SND-005', '103.55.66.77', 19.0760, 72.8777, 'UBOI260108015', 'Personal transfer', 'SUCCESS', FALSE, NULL),
('TXN-ST-006', 'ACC-ST-SND-006', 'ACC-ST-RECV-001', 49000.00, 'UPI', NOW() - INTERVAL '6 hours',  'DEV-SND-006', '103.66.77.88', 19.0760, 72.8777, 'UBOI260108016', 'Personal transfer', 'SUCCESS', FALSE, NULL),
('TXN-ST-007', 'ACC-ST-SND-007', 'ACC-ST-RECV-001', 49000.00, 'UPI', NOW() - INTERVAL '2 hours',  'DEV-SND-007', '103.77.88.99', 19.0760, 72.8777, 'UBOI260108017', 'Personal transfer', 'SUCCESS', FALSE, NULL);

INSERT INTO alerts VALUES
('ALT-2024-0848', 'TXN-ST-007', 'ACC-ST-RECV-001', 'Structuring', 84.00, 88.00, 82.00, 78.00, NOW(), 'OPEN', 'PMLA Section 12 — CTR Threshold', 'FATF Typology: Structuring');

-- ============================================================
-- SCENARIO 3 — DORMANT ACCOUNT AWAKENING
-- Account inactive for 240 days suddenly receives ₹12,00,000
-- Then immediately sends 90% out within 45 minutes
-- Channel: RTGS in, UPI out
-- Detection: DARS pre-transaction scoring
-- ============================================================

INSERT INTO accounts VALUES
('ACC-DA-DORM-001', 'Sanjay Traders',     'SAVINGS', 2, 88.00, TRUE,  NOW() - INTERVAL '240 days', 800, 1500.00,    'PUN-010', 'UBIN0701000', FALSE, FALSE),
('ACC-DA-SRC-001',  'Global Imports Ltd', 'CURRENT', 2, 30.00, FALSE, NOW() - INTERVAL '20 days',  500, 5000000.00, 'MUM-011', 'UBIN0504110', FALSE, FALSE),
('ACC-DA-DST-001',  'Hawala Exports',     'CURRENT', 1, 75.00, FALSE, NOW() - INTERVAL '10 days',   45, 100000.00,  'DEL-012', 'UBIN0601210', FALSE, FALSE);

INSERT INTO transactions VALUES
('TXN-DA-001', 'ACC-DA-SRC-001',  'ACC-DA-DORM-001', 1200000.00, 'RTGS', NOW() - INTERVAL '1 hour',      'DEV-SRC-001', '103.88.99.10', 19.0760, 72.8777, 'UBOI260108021', 'Business settlement',    'SUCCESS', FALSE, NULL),
('TXN-DA-002', 'ACC-DA-DORM-001', 'ACC-DA-DST-001',  1080000.00, 'UPI',  NOW() - INTERVAL '15 minutes',  'DEV-NEW-999', '103.99.10.11', 19.0761, 72.8778, 'UBOI260108022', 'Vendor payment',         'SUCCESS', FALSE, NULL);

INSERT INTO alerts VALUES
('ALT-2024-0849', 'TXN-DA-001', 'ACC-DA-DORM-001', 'Dormant Account Awakening', 91.00, 90.00, 93.00, 88.00, NOW(), 'OPEN', 'PMLA Section 12 — STR Obligation', 'FATF Typology: Placement');

-- ============================================================
-- SCENARIO 4 — RAPID LAYERING
-- ₹8,00,000 moves through 5 accounts in 4 hours
-- Each hop within 80 minutes of previous
-- Channels: NEFT, RTGS, IMPS, UPI, NEFT
-- Detection: BFS traversal — 5-hop chain detected
-- ============================================================

INSERT INTO accounts VALUES
('ACC-LA-001', 'Anand Exports',      'CURRENT', 2, 50.00, FALSE, NOW() - INTERVAL '30 days',  150, 1000000.00, 'MUM-020', 'UBIN0504200', FALSE, FALSE),
('ACC-LA-002', 'Shell Company A',    'CURRENT', 1, 65.00, FALSE, NOW() - INTERVAL '20 days',   90, 200000.00,  'DEL-021', 'UBIN0601211', FALSE, FALSE),
('ACC-LA-003', 'Shell Company B',    'CURRENT', 1, 65.00, FALSE, NOW() - INTERVAL '15 days',   60, 150000.00,  'PUN-022', 'UBIN0701311', FALSE, FALSE),
('ACC-LA-004', 'Shell Company C',    'CURRENT', 1, 65.00, FALSE, NOW() - INTERVAL '10 days',   45, 100000.00,  'BAN-023', 'UBIN0801411', FALSE, FALSE),
('ACC-LA-005', 'Final Destination',  'SAVINGS', 1, 80.00, FALSE, NOW() - INTERVAL '5 days',    30,  50000.00,  'HYD-024', 'UBIN0901511', FALSE, FALSE);

INSERT INTO transactions VALUES
('TXN-LA-001', 'ACC-LA-001', 'ACC-LA-002', 800000.00, 'NEFT', NOW() - INTERVAL '4 hours',      'DEV-LA-001', '103.11.11.11', 19.0760, 72.8777, 'UBOI260108031', 'Trade payment',    'SUCCESS', FALSE, NULL),
('TXN-LA-002', 'ACC-LA-002', 'ACC-LA-003', 795000.00, 'RTGS', NOW() - INTERVAL '3 hours',      'DEV-LA-002', '103.22.22.22', 28.6139, 77.2090, 'UBOI260108032', 'Service charge',   'SUCCESS', FALSE, NULL),
('TXN-LA-003', 'ACC-LA-003', 'ACC-LA-004', 790000.00, 'IMPS', NOW() - INTERVAL '2 hours',      'DEV-LA-003', '103.33.33.33', 18.5204, 73.8567, 'UBOI260108033', 'Vendor payment',   'SUCCESS', FALSE, NULL),
('TXN-LA-004', 'ACC-LA-004', 'ACC-LA-005', 785000.00, 'UPI',  NOW() - INTERVAL '1 hour',       'DEV-LA-004', '103.44.44.44', 12.9716, 77.5946, 'UBOI260108034', 'Commission fee',   'SUCCESS', FALSE, NULL),
('TXN-LA-005', 'ACC-LA-005', 'ACC-LA-001', 780000.00, 'NEFT', NOW() - INTERVAL '30 minutes',   'DEV-LA-005', '103.55.55.55', 17.3850, 78.4867, 'UBOI260108035', 'Refund transfer',  'SUCCESS', FALSE, NULL);

INSERT INTO alerts VALUES
('ALT-2024-0850', 'TXN-LA-005', 'ACC-LA-001', 'Rapid Layering', 89.00, 85.00, 93.00, 82.00, NOW(), 'OPEN', 'PMLA Section 12 — STR Obligation', 'FATF ML-Layering-003');

-- ============================================================
-- SCENARIO 5 — MULE ACCOUNT NETWORK
-- Hub account receives from 5 senders within 30 minutes
-- Immediately forwards 90% to 3 destination accounts
-- All intermediate accounts opened within 60 days
-- Shared device detected across 2 accounts
-- Detection: WCC algorithm — mule cluster identified
-- ============================================================

INSERT INTO accounts VALUES
('ACC-MU-HUB-001', 'Rajesh Mule Hub',    'SAVINGS', 1, 85.00, FALSE, NOW() - INTERVAL '3 days',   35,  5000.00,   'MUM-030', 'UBIN0504300', FALSE, FALSE),
('ACC-MU-SND-001', 'Sender Alpha',       'SAVINGS', 2, 25.00, FALSE, NOW() - INTERVAL '90 days',  400, 300000.00,  'MUM-031', 'UBIN0504310', FALSE, FALSE),
('ACC-MU-SND-002', 'Sender Beta',        'SAVINGS', 2, 25.00, FALSE, NOW() - INTERVAL '85 days',  380, 300000.00,  'MUM-032', 'UBIN0504320', FALSE, FALSE),
('ACC-MU-SND-003', 'Sender Gamma',       'SAVINGS', 2, 25.00, FALSE, NOW() - INTERVAL '80 days',  360, 300000.00,  'MUM-033', 'UBIN0504330', FALSE, FALSE),
('ACC-MU-SND-004', 'Sender Delta',       'SAVINGS', 2, 25.00, FALSE, NOW() - INTERVAL '75 days',  340, 300000.00,  'MUM-034', 'UBIN0504340', FALSE, FALSE),
('ACC-MU-SND-005', 'Sender Epsilon',     'SAVINGS', 2, 25.00, FALSE, NOW() - INTERVAL '70 days',  320, 300000.00,  'MUM-035', 'UBIN0504350', FALSE, FALSE),
('ACC-MU-DST-001', 'Crypto Exchange A',  'CURRENT', 1, 90.00, FALSE, NOW() - INTERVAL '2 days',   20,  10000.00,  'DEL-036', 'UBIN0601236', FALSE, FALSE),
('ACC-MU-DST-002', 'Hawala Network B',   'CURRENT', 1, 90.00, FALSE, NOW() - INTERVAL '2 days',   18,  10000.00,  'PUN-037', 'UBIN0701337', FALSE, FALSE),
('ACC-MU-DST-003', 'Shell Final C',      'CURRENT', 1, 90.00, FALSE, NOW() - INTERVAL '2 days',   15,  10000.00,  'BAN-038', 'UBIN0801438', FALSE, FALSE);

INSERT INTO transactions VALUES
('TXN-MU-IN-001', 'ACC-MU-SND-001', 'ACC-MU-HUB-001', 200000.00, 'UPI',  NOW() - INTERVAL '30 minutes', 'DEV-SHARED-X1', '103.99.11.22', 19.0760, 72.8777, 'UBOI260108041', 'Payment',         'SUCCESS', FALSE, NULL),
('TXN-MU-IN-002', 'ACC-MU-SND-002', 'ACC-MU-HUB-001', 200000.00, 'UPI',  NOW() - INTERVAL '25 minutes', 'DEV-SHARED-X2', '103.99.11.23', 19.0760, 72.8777, 'UBOI260108042', 'Payment',         'SUCCESS', FALSE, NULL),
('TXN-MU-IN-003', 'ACC-MU-SND-003', 'ACC-MU-HUB-001', 200000.00, 'NEFT', NOW() - INTERVAL '20 minutes', 'DEV-SHARED-X3', '103.99.11.24', 19.0760, 72.8777, 'UBOI260108043', 'Payment',         'SUCCESS', FALSE, NULL),
('TXN-MU-IN-004', 'ACC-MU-SND-004', 'ACC-MU-HUB-001', 200000.00, 'IMPS', NOW() - INTERVAL '15 minutes', 'DEV-SHARED-X4', '103.99.11.25', 19.0760, 72.8777, 'UBOI260108044', 'Payment',         'SUCCESS', FALSE, NULL),
('TXN-MU-IN-005', 'ACC-MU-SND-005', 'ACC-MU-HUB-001', 200000.00, 'UPI',  NOW() - INTERVAL '10 minutes', 'DEV-SHARED-X1', '103.99.11.22', 19.0760, 72.8777, 'UBOI260108045', 'Payment',         'SUCCESS', FALSE, NULL),
('TXN-MU-OUT-001','ACC-MU-HUB-001', 'ACC-MU-DST-001',  300000.00, 'RTGS', NOW() - INTERVAL '5 minutes',  'DEV-SHARED-X1', '103.99.11.22', 19.0760, 72.8777, 'UBOI260108046', 'Vendor settlement','SUCCESS', FALSE, NULL),
('TXN-MU-OUT-002','ACC-MU-HUB-001', 'ACC-MU-DST-002',  300000.00, 'NEFT', NOW() - INTERVAL '4 minutes',  'DEV-SHARED-X1', '103.99.11.22', 19.0760, 72.8777, 'UBOI260108047', 'Vendor settlement','SUCCESS', FALSE, NULL),
('TXN-MU-OUT-003','ACC-MU-HUB-001', 'ACC-MU-DST-003',  280000.00, 'UPI',  NOW() - INTERVAL '3 minutes',  'DEV-SHARED-X1', '103.99.11.22', 19.0760, 72.8777, 'UBOI260108048', 'Vendor settlement','SUCCESS', FALSE, NULL);

INSERT INTO alerts VALUES
('ALT-2024-0852', 'TXN-MU-OUT-003', 'ACC-MU-HUB-001', 'Mule Account Network', 93.00, 88.00, 96.00, 86.00, NOW(), 'OPEN', 'PMLA Section 12 — STR Obligation', 'FATF Typology: Integration');

-- ============================================================
-- VERIFICATION QUERIES
-- Run these after inserting to confirm data is correct
-- ============================================================

-- Check all 5 scenarios loaded
SELECT 'TOTAL ALERTS'       AS check_name, COUNT(*) AS count FROM alerts
UNION ALL
SELECT 'TOTAL TRANSACTIONS' AS check_name, COUNT(*) AS count FROM transactions
UNION ALL
SELECT 'TOTAL ACCOUNTS'     AS check_name, COUNT(*) AS count FROM accounts;

-- Scenario 1: Detect round-trip (money returning to origin)
SELECT 'SCENARIO 1 - Round-Tripping' AS scenario,
       t1.sender_account AS origin,
       t1.receiver_account AS hop1,
       t2.receiver_account AS hop2,
       t3.receiver_account AS returns_to,
       t1.amount AS amount_sent,
       t3.amount AS amount_returned,
       EXTRACT(EPOCH FROM (t3.txn_timestamp - t1.txn_timestamp))/3600 AS hours_elapsed
FROM transactions t1
JOIN transactions t2 ON t1.receiver_account = t2.sender_account
JOIN transactions t3 ON t2.receiver_account = t3.sender_account
WHERE t3.receiver_account = t1.sender_account
  AND t3.txn_timestamp - t1.txn_timestamp < INTERVAL '24 hours';

-- Scenario 2: Detect structuring (multiple deposits just below threshold)
SELECT 'SCENARIO 2 - Structuring' AS scenario,
       receiver_account,
       COUNT(*)           AS deposit_count,
       SUM(amount)        AS total_amount,
       MIN(amount)        AS min_deposit,
       MAX(amount)        AS max_deposit,
       MIN(txn_timestamp) AS first_deposit,
       MAX(txn_timestamp) AS last_deposit
FROM transactions
WHERE amount >= 40000 AND amount < 50000
  AND txn_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY receiver_account
HAVING COUNT(*) >= 3;

-- Scenario 3: Detect dormant account awakening
SELECT 'SCENARIO 3 - Dormant Awakening' AS scenario,
       a.account_id,
       a.customer_name,
       a.last_active,
       t.amount,
       t.channel,
       t.txn_timestamp,
       EXTRACT(DAY FROM (t.txn_timestamp - a.last_active)) AS days_dormant
FROM accounts a
JOIN transactions t ON a.account_id = t.receiver_account
WHERE a.is_dormant = TRUE
   OR a.last_active < NOW() - INTERVAL '90 days'
HAVING EXTRACT(DAY FROM (t.txn_timestamp - a.last_active)) > 90;

-- Scenario 4: Detect layering chain (5 hops)
WITH RECURSIVE layering_chain AS (
    SELECT txn_id, sender_account, receiver_account, amount, txn_timestamp, 1 AS hop,
           ARRAY[sender_account] AS path
    FROM transactions
    WHERE sender_account = 'ACC-LA-001'

    UNION ALL

    SELECT t.txn_id, t.sender_account, t.receiver_account, t.amount, t.txn_timestamp,
           lc.hop + 1,
           lc.path || t.sender_account
    FROM transactions t
    JOIN layering_chain lc ON t.sender_account = lc.receiver_account
    WHERE lc.hop < 5
      AND NOT t.sender_account = ANY(lc.path)
      AND t.txn_timestamp - lc.txn_timestamp < INTERVAL '2 hours'
)
SELECT 'SCENARIO 4 - Rapid Layering' AS scenario,
       MAX(hop) AS total_hops,
       MIN(amount) AS final_amount,
       COUNT(*) AS chain_length
FROM layering_chain;

-- Scenario 5: Detect mule account (hub receives many, forwards most)
SELECT 'SCENARIO 5 - Mule Network' AS scenario,
       hub.account_id,
       hub.customer_name,
       COUNT(DISTINCT t_in.sender_account)   AS unique_senders,
       COUNT(DISTINCT t_out.receiver_account) AS unique_receivers,
       SUM(t_in.amount)  AS total_received,
       SUM(t_out.amount) AS total_forwarded,
       ROUND((SUM(t_out.amount) / SUM(t_in.amount) * 100), 2) AS forward_pct
FROM accounts hub
JOIN transactions t_in  ON hub.account_id = t_in.receiver_account
JOIN transactions t_out ON hub.account_id = t_out.sender_account
WHERE t_out.txn_timestamp - t_in.txn_timestamp < INTERVAL '2 hours'
GROUP BY hub.account_id, hub.customer_name
HAVING COUNT(DISTINCT t_in.sender_account) >= 3
   AND COUNT(DISTINCT t_out.receiver_account) >= 2
   AND (SUM(t_out.amount) / SUM(t_in.amount)) >= 0.80;
