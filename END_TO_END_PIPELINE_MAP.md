# UniGRAPH End-to-End Pipeline Map (Dataset Input to Frontend Output)

## 1) Scope and Intent

This document maps the runtime data path step by step, file to file, from dataset input to UI output.

It covers both active ingestion modes present in this repo:

1. Direct replay mode (SQL scenarios -> backend ingest API), which is the clearest deterministic validation path.
2. CDC streaming mode (Postgres -> Debezium -> Kafka -> Flink -> bridge -> backend ingest API).

It also maps the post-alert investigation and STR workflow that surfaces in the frontend.

---

## 2) Top-Level Architecture (What Actually Runs Where)

Infrastructure stack (Docker Compose):

- docker/docker-compose.yml
- docker/init-scripts/kafka-topics.sh
- docker/init-scripts/register-debezium-connector.sh
- docker/init-scripts/postgres-init.sql
- ingestion/debezium/connector-config.json

Application services (typically run separately from compose in local dev):

- Backend API: backend/app/main.py
- ML scoring service: ml/serving/ml_service.py
- Frontend app: frontend/src/main.tsx -> frontend/src/App.tsx

Important operational detail:

- docker/docker-compose.yml provisions infra and streaming components.
- Backend and frontend are not defined as services in this compose file and are typically started separately.

---

## 3) Input Datasets and Shapes

### 3.1 Scenario SQL (active datasets)

Primary files:

- fraud_scenarios.sql
- dataset_100_interconnected_txns.sql

Key table shapes in active use:

- fraud_scenarios.sql: accounts, transactions, alerts
- dataset_100_interconnected_txns.sql: transactions_input

The active SQL paths cover both deterministic scenario replay and input-schema replay through the backend ingest API.

### 3.2 Legacy wide synthetic dataset status

Legacy wide-schema transaction artifacts were removed from the active runtime path during repository cleanup.

Use the active SQL datasets above for ingestion, validation, and frontend verification flows.

---

## 4) Pipeline A: Direct Replay Path (Dataset -> Backend -> Neo4j -> Frontend)

This is the most direct and deterministic end-to-end path used for scenario validation.

### Step A1: Parse SQL and derive ingest features

Files:

- scripts/ingest_fraud_scenarios.py
- fraud_scenarios.sql

What happens:

1. The script parses accounts, transactions, and expected alerts from fraud_scenarios.sql.
2. It computes stream-like enrichment fields per transaction:
   - velocity_1h
   - velocity_24h
   - device_account_count
   - is_dormant
   - round-trip marker in description when a short circular path is detected
3. It builds payloads for backend ingest endpoint.

Output payload shape produced by script:

- txn_id
- from_account
- to_account
- amount
- channel
- customer_id
- description
- device_id
- is_dormant
- device_account_count
- velocity_1h
- velocity_24h

### Step A2: Ingest transaction through backend API

Files:

- backend/app/routers/transactions.py

Endpoint:

- POST /api/v1/transactions/ingest

What happens:

1. Request is validated via TransactionIngest model.
2. Backend sets defaults:
   - txn_id if missing
   - timestamp
   - device_id fallback
3. Backend calls fraud scoring pipeline.

### Step A3: Rule + ML scoring

Files:

- backend/app/services/fraud_scorer.py
- backend/app/services/rule_evaluator.py
- ml/serving/ml_service.py
- contracts/ml-scoring-protocol.json

What happens:

1. rule_evaluator.py computes deterministic rule violations and base risk contributions.
2. fraud_scorer.py fetches graph features from Neo4j for the sender account:
   - connected suspicious neighbors
   - community risk score
   - pagerank
   - betweenness
3. fraud_scorer.py calls ML service endpoint:
   - POST /api/v1/ml/score
4. If ML is available:
   - Blend ML score with rule-based score.
   - Preserve a rule floor for alert-worthy deterministic patterns.
5. If ML is unavailable:
   - Fallback to rule-only scoring.
6. risk_level and recommendation are derived from risk_score thresholds.
7. primary_fraud_type is selected from rule_violations using priority order.

### Step A4: Persist graph entities and relationships

Files:

- backend/app/services/neo4j_service.py

What happens:

1. Upsert source and destination accounts.
2. Create or update Transaction node with:
   - amount, channel, timestamp
   - from_account, to_account
   - risk_score, rule_violations, primary_fraud_type
   - is_flagged, description, device_id
3. Create or merge SENT relationship between accounts with amount, timestamp, channel.

### Step A5: Conditional alert creation and live push

Files:

- backend/app/routers/transactions.py
- backend/app/services/fraud_scorer.py
- backend/app/services/neo4j_service.py
- backend/app/routers/ws.py

What happens:

1. If risk_score >= 60, backend creates Alert node.
2. Backend broadcasts websocket message of type ALERT_FIRED.

Websocket endpoint:

- /api/v1/ws/alerts/{investigator_id}

### Step A6: Frontend reads and renders live data

Files:

- frontend/src/lib/unigraph-api.ts
- frontend/src/App.tsx
- frontend/src/components/AppLayout.tsx
- frontend/src/pages/Dashboard.tsx
- frontend/src/pages/AlertsQueue.tsx
- frontend/src/pages/TransactionMonitor.tsx
- frontend/src/pages/TestCasesPage.tsx

What happens:

1. Polling adapters call:
   - GET /api/v1/transactions
   - GET /api/v1/alerts
2. Websocket subscription listens for ALERT_FIRED and prepends incoming alerts.
3. UI mapping logic converts backend objects to page-specific cards/tables.
4. Results appear in:
   - Dashboard KPI + live feed + charts
   - Alerts queue cards
   - Transaction monitor table
   - Pipeline status page

---

## 5) Pipeline B: CDC Streaming Path (Postgres CDC -> Kafka -> Flink -> Backend -> Neo4j -> Frontend)

### Step B1: Source transaction insert/update in Postgres

Files:

- docker/init-scripts/postgres-init.sql
- ingestion/verify_db_ingestion.py

What happens:

1. public.transactions table is created in Postgres.
2. PostgreSQL publication unigraph_pub is created for CDC.
3. Inserts/updates to this table become Debezium source events.

### Step B2: Debezium captures CDC and routes to Kafka raw topic

Files:

- ingestion/debezium/connector-config.json
- docker/init-scripts/register-debezium-connector.sh

What happens:

1. Debezium Postgres connector reads public.transactions changes.
2. ExtractNewRecordState unwraps CDC envelope.
3. RegexRouter routes topic to raw-transactions.

### Step B3: Flink enrichment stage

Files:

- ingestion/flink/jobs/TransactionEnrichmentJob.java

Topic flow:

- raw-transactions -> enriched-transactions

What happens:

1. Job consumes raw-transactions.
2. Wraps each event with deterministic enrichment metadata:
   - ingest_ts
   - pipeline_version
   - event_uid
3. Emits enriched payload to enriched-transactions.

### Step B4: Flink anomaly window stage

Files:

- ingestion/flink/jobs/AnomalyWindowJob.java

Topic flow:

- enriched-transactions -> rule-violations

What happens:

1. Job parses event payload, including Debezium-style after records.
2. Keys by account and applies sliding windows.
3. Emits flagged velocity violations when thresholds are crossed.
4. Emits immediate high-value violation for amount >= 300000.

### Step B5: Bridge Flink outputs into backend ingest

Files:

- ingestion/neo4j_writer.py

What happens:

1. Consumes enriched-transactions and rule-violations.
2. Maintains short-lived rule signals by account.
3. Builds backend ingest payload from enriched event.
4. Calls backend:
   - POST /api/v1/transactions/ingest
5. Optionally re-ingests cached transactions when new rule-violation signals arrive to raise velocity features.
6. Optional flag can trigger STR draft generation for new alerts.

At this point, flow converges with Pipeline A (backend scoring, Neo4j persistence, websocket broadcast, frontend rendering).

---

## 6) Investigation and STR Workflow (Alert -> Graph -> STR -> Submission)

### Step C1: Investigation payload assembly

Files:

- backend/app/routers/alerts.py
- backend/app/services/neo4j_service.py
- backend/app/services/llm_service.py
- frontend/src/pages/GraphExplorer.tsx
- frontend/src/components/LiveGraph.tsx

Endpoint:

- GET /api/v1/alerts/{alert_id}/investigate?hops=2

What happens:

1. Fetch alert by id.
2. Fetch linked transaction.
3. Build account-centered N-hop graph subgraph.
4. Generate investigator note via LLM service.
5. Frontend GraphExplorer renders summary + graph + reasons.

### Step C2: STR draft generation

Files:

- backend/app/routers/reports.py
- backend/app/services/neo4j_service.py
- backend/app/services/llm_service.py
- frontend/src/pages/STRGenerator.tsx

Endpoint:

- POST /api/v1/reports/str/generate

What happens:

1. Backend collects alert + subgraph context.
2. LLM generates narrative.
3. STRReport node is created/updated in Neo4j with DRAFT status.
4. Frontend loads narrative and editable preview.

### Step C3: STR approval and submit

Files:

- backend/app/routers/reports.py
- backend/app/auth/jwt_rbac.py
- backend/app/services/fiu_ind_service.py
- backend/app/services/neo4j_service.py

Endpoints:

- POST /api/v1/reports/str/{str_id}/approve
- POST /api/v1/reports/str/{str_id}/reject
- POST /api/v1/reports/str/{str_id}/submit

What happens:

1. In non-demo mode, submit requires APPROVED status.
2. If FIU integration config exists, provider submission is attempted.
3. Neo4j STRReport status/reference_id/submitted_at are persisted.

---

## 7) Enforcement and Case Workflow (Ancillary to Frontend Output)

Files:

- backend/app/routers/enforcement.py
- backend/app/services/finacle_service.py
- backend/app/services/ncrp_service.py
- backend/app/services/neo4j_service.py
- backend/app/routers/cases.py

What happens:

1. Maker initiates lien/freeze/hold/NCRP report action.
2. Action is persisted as EnforcementAction node.
3. Checker approves/rejects via maker-checker endpoints.
4. Provider calls run when integration config is present.
5. Status transitions are persisted and retrievable via list/get endpoints.

---

## 8) Frontend Route-to-Data Map (Where Pipeline Ends on Screen)

Routing root:

- frontend/src/App.tsx

Route output mapping:

1. / (Dashboard)
   - Source: listTransactions, listAlerts, websocket alerts
   - Files: frontend/src/pages/Dashboard.tsx

2. /alerts (Alerts Queue)
   - Source: listAlerts + getTransaction lookups + websocket
   - Files: frontend/src/pages/AlertsQueue.tsx

3. /transactions (Transaction Monitor)
   - Source: listTransactions + websocket-triggered getTransaction
   - Files: frontend/src/pages/TransactionMonitor.tsx

4. /graph (Graph Explorer)
   - Source: investigateAlert
   - Files: frontend/src/pages/GraphExplorer.tsx, frontend/src/components/LiveGraph.tsx

5. /str-generator (STR Generator)
   - Source: listAlerts, listTransactions, listStrReports, generateStrReport, submitStrReport
   - Files: frontend/src/pages/STRGenerator.tsx

6. /copilot (Investigator Copilot)
   - Source: listAlerts, listTransactions, listStrReports, investigateAlert
   - Files: frontend/src/pages/CopilotPage.tsx

7. /pipeline-status
   - Source: getBackendHealth, listTransactions, listAlerts
   - Files: frontend/src/pages/TestCasesPage.tsx

8. /settings
   - Source: getBackendHealth, getGraphAnalyticsStatus, getMlHealth, listAlerts plus localStorage
   - Files: frontend/src/pages/SettingsPage.tsx

Adapter and websocket implementation:

- frontend/src/lib/unigraph-api.ts

---

## 9) Contract and Schema Anchors

Contracts:

- contracts/fraud-scoring-api.yaml
- contracts/enforcement-api.yaml
- contracts/ml-scoring-protocol.json
- contracts/neo4j-schema.json

Runtime schema in Neo4j:

- backend/app/services/neo4j_service.py (initialize_schema)

This defines constraints/indexes for Account, Transaction, Alert, Case, STRReport, EnforcementAction.

---

## 10) Real Runtime vs Legacy/Utility Paths

### Primary runtime paths for dataset-to-frontend validation

- scripts/ingest_fraud_scenarios.py -> backend ingest API -> Neo4j -> frontend
- or CDC/Flink path ending in ingestion/neo4j_writer.py -> backend ingest API -> Neo4j -> frontend

### Legacy or compatibility utilities (still present)

- scripts/ingest_sql_transactions.py (legacy guard requires --allow-legacy)
- scripts/simulate_transactions.py (legacy guard requires --allow-legacy)

Note: older wide-schema verification artifacts were removed from the current repository state.

---

## 11) End-to-End Sequence Summaries

### Sequence 1: Deterministic scenario replay

fraud_scenarios.sql
-> scripts/ingest_fraud_scenarios.py
-> POST /api/v1/transactions/ingest
-> fraud_scorer + rule_evaluator + ML service
-> neo4j_service transaction/account persistence
-> alert creation when risk >= 60
-> websocket ALERT_FIRED
-> frontend pages refresh/push-update

### Sequence 2: CDC streaming path

Postgres public.transactions
-> Debezium connector
-> Kafka raw-transactions
-> Flink TransactionEnrichmentJob
-> Kafka enriched-transactions
-> Flink AnomalyWindowJob
-> Kafka rule-violations
-> ingestion/neo4j_writer.py
-> POST /api/v1/transactions/ingest
-> same downstream path as Sequence 1

---

## 12) Validation Scripts Tied to the Pipeline

- scripts/ingest_fraud_scenarios.py
- ingestion/verify_db_ingestion.py
- ingestion/verify_e2e_ingestion.py
- scripts/run_live_demo.py

These scripts validate different slices of the same end-to-end pipeline.

---

## 13) Practical Conclusion

From dataset input to frontend output, the core application convergence point is always:

- backend/app/routers/transactions.py POST /ingest

All upstream sources (SQL replay or CDC/Flink streaming bridge) are normalized into that ingest payload shape, and all downstream user-visible outputs are driven from Neo4j-backed API reads plus websocket alerts consumed by frontend/src/lib/unigraph-api.ts.
