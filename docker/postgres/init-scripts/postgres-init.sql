-- UniGraph - PostgreSQL Schema for Fraud Scenarios
-- This runs on first container start

-- Create tables matching fraud_scenarios.sql
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

-- Enable CDC for Debezium
ALTER TABLE accounts REPLICA IDENTITY FULL;
ALTER TABLE transactions REPLICA IDENTITY FULL;
ALTER TABLE alerts REPLICA IDENTITY FULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender_account);
CREATE INDEX IF NOT EXISTS idx_transactions_receiver ON transactions(receiver_account);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(txn_timestamp);
CREATE INDEX IF NOT EXISTS idx_transactions_flagged ON transactions(is_flagged) WHERE is_flagged = true;
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_account ON alerts(account_id);