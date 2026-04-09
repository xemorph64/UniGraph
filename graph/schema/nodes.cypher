// Node definitions are expressed through merge patterns used by ingestion services.
// This file provides idempotent seed node examples and documentation queries.

MERGE (:Account {id: 'ACC-SEED-001'})
  ON CREATE SET created_at = datetime();

MERGE (:Customer {id: 'CUST-SEED-001'})
  ON CREATE SET created_at = datetime();

MERGE (:Transaction {id: 'TXN-SEED-001'})
  ON CREATE SET created_at = datetime(), amount = 1000.0, channel = 'UPI';

MERGE (:Device {id: 'DEV-SEED-001'})
  ON CREATE SET created_at = datetime();

MERGE (:IP {ip_address: 'IP-SEED-001'})
  ON CREATE SET last_seen = datetime();

MERGE (:Alert {id: 'ALERT-SEED-001'})
  ON CREATE SET created_at = datetime(), status = 'OPEN';
