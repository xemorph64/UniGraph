CREATE KEYSPACE IF NOT EXISTS unigraph_ts
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE unigraph_ts;

CREATE TABLE IF NOT EXISTS transaction_by_account (
    account_id TEXT,
    txn_timestamp TIMESTAMP,
    txn_id UUID,
    amount DECIMAL,
    channel TEXT,
    counterparty_id TEXT,
    risk_score FLOAT,
    rule_flags LIST<TEXT>,
    ml_score FLOAT,
    PRIMARY KEY (account_id, txn_timestamp)
) WITH CLUSTERING ORDER BY (txn_timestamp DESC)
  AND compaction = {'class': 'TimeWindowCompactionStrategy',
                    'compaction_window_size': 1, 'compaction_window_unit': 'DAYS'};

CREATE TABLE IF NOT EXISTS account_risk_history (
    account_id TEXT,
    computed_at TIMESTAMP,
    risk_score FLOAT,
    ml_score FLOAT,
    rule_flags LIST<TEXT>,
    community_id INT,
    pagerank FLOAT,
    PRIMARY KEY (account_id, computed_at)
) WITH CLUSTERING ORDER BY (computed_at DESC);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id UUID,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT,
    actor TEXT,
    timestamp TIMESTAMP,
    details TEXT,
    PRIMARY KEY (entity_type, timestamp, log_id)
) WITH CLUSTERING ORDER BY (timestamp DESC);