// Constraints and indexes for graph model bootstrapping.

CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT device_id_unique IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT alert_id_unique IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE;

CREATE INDEX account_risk_score IF NOT EXISTS FOR (a:Account) ON (a.risk_score);
CREATE INDEX account_last_active IF NOT EXISTS FOR (a:Account) ON (a.last_active);
CREATE INDEX transaction_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
CREATE INDEX transaction_amount IF NOT EXISTS FOR (t:Transaction) ON (t.amount);
CREATE INDEX alert_status IF NOT EXISTS FOR (al:Alert) ON (al.status);
