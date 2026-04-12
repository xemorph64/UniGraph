# UniGRAPH Transparent Repository Audit (Code + Runtime Verified)

Date: 2026-04-12  
Workspace: /home/ojasbhalerao/Documents/Uni  
Method: direct source inspection + live runtime validation + scripted tests

## 1) Findings First (Ordered by Severity)

### F1 - Enforcement write path appears non-persistent at runtime
Observed behavior:
- POST /api/v1/enforcement/lien returned 200 with a valid lien id.
- GET /api/v1/enforcement/actions returned an empty list.
- GET /api/v1/enforcement/actions/{lien_id} returned 404.

Why this is serious:
- Maker-checker and legal action auditability cannot be trusted if actions are acknowledged but not retrievable.

Code-level risk indicator:
- Enforcement create routes swallow persistence exceptions:
  - backend/app/routers/enforcement.py contains multiple `try: await neo4j_service.create_enforcement_action(...)
    except Exception: pass` blocks.

### F2 - Graph analytics execution endpoint fails while status endpoint works
Observed behavior:
- GET /api/v1/graph-analytics/status -> 200 with populated metrics.
- POST /api/v1/graph-analytics/run -> 500 Internal Server Error (text/plain).

Why this is serious:
- Manual recovery/recompute path is broken during operations, even though read-only status is available.

### F3 - CDC ingestion verification is currently failing end-to-end
Observed behavior:
- ingestion/verify_db_ingestion.py failed: txn not observed in raw-transactions, enriched-transactions, rule-violations.
- Debezium Connect had no registered connectors (`GET /connectors` returned `[]`).
- `GET /connectors/finacle-cdc/status` returned 404.

Why this is serious:
- DB->Debezium->Kafka->Flink path is not active by default in this runtime state.

### F4 - Kafka topic durability settings are inconsistent with current topic state
Observed behavior:
- Topic describes showed replication factor 1 and min.insync.replicas 2.
- Local producer with default settings timed out (`Local: Message timed out`).
- Producer succeeded with `acks=1`.

Why this is serious:
- Producers using default `acks=all` can stall/fail in this state.

### F5 - Provider smoke script is non-conclusive by default
Observed behavior:
- scripts/provider_live_smoke.py reported PASS only because all checks were skipped (missing process env vars).
- This script reads os.environ directly and does not load .env itself.

Why this is serious:
- PASS can be misread as real provider readiness when it is only a skip-only pass.

### F6 - Frontend is mixed reality, not fully live-backed
Observed behavior:
- Dashboard/Alerts/Transaction Monitor use live backend + websocket.
- Graph Explorer/STR Generator/Copilot/Settings/TestCases are mostly local data, canned behavior, and simulated timeouts/toasts.

Why this is serious:
- Demo UX can imply production integration where none exists.

## 2) Step-by-Step Test Log (Executed)

1. Infra readiness check
Command:
```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/infra_stack_smoke.py --compose-file docker/docker-compose.yml --timeout 12 --backend-health-url http://127.0.0.1:8000/health
```
Result:
- PASS
- Kafka, Schema Registry, Debezium Connect, Neo4j, Cassandra, Redis, Vault, backend health all reachable.

2. ML service probe
Command:
```bash
curl -sS -i http://127.0.0.1:8002/api/v1/ml/health
```
Result:
- Connection failed (service not running on 8002 in current runtime).

3. Backend tests
Command:
```bash
PYTHONPATH=/home/ojasbhalerao/Documents/Uni /home/ojasbhalerao/Documents/Uni/.venv/bin/python -m pytest backend/tests -q
```
Result:
- 51 passed in 6.92s.

4. Frontend tests and build
Command:
```bash
cd frontend && npm test -- --run --reporter=dot && npm run build
```
Result:
- 1 test passed.
- Build succeeded.
- Large chunk warning present (>500 kB).

5. ML + Debezium unit tests
Command:
```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python -m pytest /home/ojasbhalerao/Documents/Uni/ml/tests/test_smoke.py /home/ojasbhalerao/Documents/Uni/ingestion/debezium/tests/test_mock_cbs_generator.py -q
```
Result:
- 4 passed.

6. Fraud detection script
Command:
```bash
PYTHONPATH=/home/ojasbhalerao/Documents/Uni /home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/test_fraud_detection.py
```
Result:
- Script completed successfully for circular, rapid-layering, dormant-awakening, and mule-network test scenarios.

7. Provider smoke
Command:
```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/provider_live_smoke.py
```
Result:
- PASS with all checks skipped (FINACLE_API_URL/FIU_IND_API_URL/NCRP_API_URL missing in process env).

8. CDC verifier
Command:
```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python ingestion/verify_db_ingestion.py --bootstrap localhost:19092 --timeout 60 --db-host localhost --db-port 5433 --db-name finacle_cbs --db-user postgres --db-password postgres
```
Result:
- FAIL: not found in all three topics (raw/enriched/rule).

9. Debezium connector status
Commands:
```bash
curl -sS http://127.0.0.1:8083/connectors
curl -sS http://127.0.0.1:8083/connectors/finacle-cdc/status
```
Result:
- `[]`
- 404 no status found.

10. Graph and enforcement runtime probes
Result:
- /api/v1/graph-analytics/status -> 200.
- /api/v1/graph-analytics/run -> 500.
- /api/v1/enforcement/lien -> 200 with lienId.
- /api/v1/enforcement/actions -> empty.
- /api/v1/enforcement/actions/{id} -> 404.

Note on interrupted remediation:
- Attempt to register Debezium connector from ingestion/debezium/connector-config.json was initiated but canceled during execution, so this run did not mutate connector state.

## 3) Architecture Map (What Exists in Code)

### A) API-driven path (currently active)

Frontend (React, Vite)
-> FastAPI backend
-> Fraud scorer (rule-first, optional ML call)
-> Neo4j persistence
-> Alerts + WebSocket push
-> Investigator flows (cases/reports/enforcement)

### B) Streaming path (implemented but not fully active in current runtime)

Postgres transactions table
-> Debezium connector
-> Kafka raw-transactions
-> Flink enrichment/anomaly jobs
-> Kafka enriched-transactions + rule-violations
-> downstream consumers (bridge/writer/backend workflows)

### C) External integration hooks

Backend services call:
- FinacleService (oauth token + account lien/freeze/hold endpoints)
- FIUIndService (mTLS STR/CTR submission + status)
- NCRPService (complaint submission/status)
- ML scoring service at ML_SERVICE_URL/api/v1/ml/score

## 4) Backend Endpoint Surface (From Routers)

Mounted prefixes are defined in backend/app/main.py.

- /api/v1/transactions
  - GET /
  - GET /{txn_id}
  - POST /ingest

- /api/v1/accounts
  - GET /{account_id}/graph
  - GET /{account_id}/profile
  - GET /{account_id}/timeline

- /api/v1/alerts
  - GET /
  - GET /{alert_id}
  - POST /{alert_id}/acknowledge
  - POST /{alert_id}/escalate
  - GET /{alert_id}/investigate

- /api/v1/cases
  - GET /
  - GET /{case_id}
  - POST /
  - PUT /{case_id}/close

- /api/v1/reports
  - GET /str
  - GET /str/{str_id}
  - POST /str/generate
  - POST /str/{str_id}/submit
  - POST /str/{str_id}/approve
  - POST /str/{str_id}/reject

- /api/v1/fraud
  - POST /score

- /api/v1/enforcement
  - GET /actions
  - GET /actions/{action_id}
  - POST /actions/{action_id}/approve
  - POST /actions/{action_id}/reject
  - POST /lien
  - POST /freeze
  - POST /hold
  - POST /ncrp-report

- /api/v1/graph-analytics
  - GET /status
  - POST /run

- /api/v1/ws
  - WS /alerts/{investigator_id}

## 5) Frontend Reality Check (Per Route)

Routes defined in frontend/src/App.tsx:

1. /
- Page: Dashboard
- Source: Live API + WebSocket (listTransactions/listAlerts/connectAlertsWebSocket)
- Verdict: Real backend data

2. /alerts
- Page: AlertsQueue
- Source: Live API + WebSocket
- Verdict: Real backend data

3. /transactions
- Page: TransactionMonitor
- Source: Live API + WebSocket for updates
- Verdict: Real backend data (with some local UI-only helper text)

4. /graph
- Page: GraphExplorer
- Source: local `@/data/*`, local timeout/toast simulation
- Verdict: Mock/static

5. /str-generator
- Page: STRGenerator
- Source: local `@/data/alerts-data`, local narrative templates, simulated submit
- Verdict: Mock/static

6. /copilot
- Page: CopilotPage
- Source: local canned responses + timeout simulation
- Verdict: Mock/static

7. /settings
- Page: SettingsPage
- Source: local state only, static status cards
- Verdict: Mock/static

Additional note:
- frontend/src/pages/TestCasesPage.tsx exists but is not routed in App.tsx.

## 6) Built vs Partial vs Missing

### Built (working components present)
- FastAPI backend with multi-domain router surface.
- Neo4j graph persistence and read flows.
- Alert websocket pipeline.
- Fraud scoring service with deterministic rules and optional ML call.
- Core frontend shell and live pages (Dashboard/Alerts/Transactions).
- Docker compose stack for local infra.
- Backend test suite coverage with passing results.

### Partial (implemented but operationally incomplete)
- Graph analytics: status reads work; manual run endpoint fails in this runtime.
- Enforcement workflows: API create succeeds but persistence/readback currently inconsistent.
- Streaming ingestion: jobs/scripts exist, but CDC runtime not active out-of-the-box due connector/state issues.
- Provider integration wrappers exist but runtime readiness is environment-dependent and not validated in this run.
- ML service integration exists, but external ML service endpoint was down in this runtime and backend used fallback scoring.

### Missing / Scaffold-only
- GraphSAGE train/evaluate/model core implementation:
  - ml/models/graphsage/train.py
  - ml/models/graphsage/model.py
  - ml/models/graphsage/evaluate.py
- Drools rule content is placeholder-level (`eval(true)` + placeholder comments) in rules/src/main/resources/rules/*.drl.
- Kubernetes manifests are scaffolding only (namespaces + kustomization overlays, no app Deployments/Services/HPA).

## 7) Contract and Documentation Drift

1. ML contract mismatch
- contracts/ml-scoring-protocol.json expects source_account/destination_account.
- ml/serving/ml_service.py expects enriched_transaction + graph_features.

2. LLM/runtime messaging drift
- README states on-prem Qwen.
- backend/app/config.py defaults to Groq provider settings.
- backend/app/services/llm_service.py uses Groq with mock fallback.

3. Rules engine claim drift
- README lists Drools rule engine.
- repository Drools rules are placeholder patterns.

4. CI workflow placement risk
- Workflows are under ci-cd/.github/workflows.
- No root .github/workflows found in this workspace snapshot.

## 8) What Is Real and Demo-Usable Today

Real and usable in local demo:
- Backend API, auth/permission layer, graph writes/reads.
- Live alert feed and websocket updates to frontend live pages.
- Fraud scoring decisions (rule-based with optional ML blend).
- Reports and case APIs (subject to endpoint-specific caveats).

Not fully real in current runtime:
- Full CDC ingestion chain activation without manual connector setup.
- Manual graph analytics run endpoint reliability.
- Enforcement action persistence integrity.
- Real external provider validation (current smoke run was skip-only).
- Full ML pipeline claims (GraphSAGE training path incomplete).

## 9) Priority Fix Plan

1. Fix enforcement persistence first
- Remove silent exception swallowing in enforcement create routes.
- Return explicit persistence errors.
- Add integration test asserting create -> list/get roundtrip.

2. Fix graph analytics run 500
- Capture and log full exception stack.
- Add health check for required GDS procedures before run.
- Add test for /graph-analytics/run success path in demo dataset.

3. Stabilize CDC ingestion bootstrap
- Ensure Debezium connector auto-registration or explicit startup script step.
- Reconcile Kafka topic RF/ISR settings with broker policy.
- Add a one-command ingestion readiness script that validates connector + topic flow.

4. Align contracts and docs with executable behavior
- Update ml-scoring-protocol.json to real request shape.
- Clarify Groq/demo fallback vs on-prem target state.
- Mark mock/static frontend pages clearly in README and UI labels.

5. Expand production readiness assets
- Add Kubernetes workload manifests.
- Move/duplicate CI workflows to repo root .github/workflows if GitHub Actions execution is required.

## 10) Bottom Line

This repository contains substantial real implementation, not just planning documents: backend flows, graph integration, live dashboard/alerts/transaction pages, and passing backend/frontend tests are present.

At the same time, key production-critical paths are currently unstable or incomplete in runtime verification, especially enforcement persistence, graph analytics run, and CDC activation defaults. The frontend is intentionally mixed (live + mock), so what users see is only partially backed by real integrations today.
