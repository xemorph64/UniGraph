-- Constraints
CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT device_id_unique IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT alert_id_unique IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE;

-- Indexes
CREATE INDEX account_risk_score IF NOT EXISTS FOR (a:Account) ON (a.risk_score);
CREATE INDEX account_dormant IF NOT EXISTS FOR (a:Account) ON (a.is_dormant);
CREATE INDEX transaction_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
CREATE INDEX transaction_amount IF NOT EXISTS FOR (t:Transaction) ON (t.amount);
CREATE INDEX transaction_channel IF NOT EXISTS FOR (t:Transaction) ON (t.channel);
CREATE INDEX alert_status IF NOT EXISTS FOR (al:Alert) ON (al.status);
CREATE INDEX alert_risk_score IF NOT EXISTS FOR (al:Alert) ON (al.risk_score);