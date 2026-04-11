# UniGRAPH Transparent Repository Audit (Code-Verified)

Date: 2026-04-11
Scope: `C:/vs code/UniGRAPH2` only
Method: direct source inspection + IDE diagnostics (`get_errors`), no assumptions from planning docs

## 1) Direct correction to earlier misread

I previously overstated ML completeness. The corrected, code-backed status is:

- `ml/serving/ml_service.py` is implemented and runnable.
- `ml/models/graphsage/train.py` is scaffold only (`NotImplementedError`).
- `ml/models/graphsage/evaluate.py` is scaffold only (`NotImplementedError`).
- `ml/models/graphsage/model.py` defines the class but core methods are unimplemented (`NotImplementedError`).

So: online scoring service exists, but GraphSAGE training/evaluation/model-forward training path is not implemented.

## 2) Architecture observed in code (not vision)

### Runtime flow that is actually implemented

1. Transaction enters backend via `POST /api/v1/transactions/ingest` in `backend/app/routers/transactions.py`.
2. Backend fraud scoring runs in `backend/app/services/fraud_scorer.py`.
3. Backend attempts ML call to `ML_SERVICE_URL/api/v1/ml/score`; if unavailable, it falls back to deterministic rules.
4. Account and transaction graph entities are written to Neo4j via `backend/app/services/neo4j_service.py`.
5. Alerts are created for high-risk scores and pushed over WebSocket via `backend/app/routers/ws.py`.
6. Investigation endpoint (`/alerts/{id}/investigate`) returns alert + subgraph + LLM note.
7. STR generation/submission endpoints are present in `backend/app/routers/reports.py`.
8. Enforcement maker-checker endpoints are present in `backend/app/routers/enforcement.py`.

### Streaming/ingestion implementation status

- Flink jobs are implemented in:
  - `ingestion/flink/jobs/TransactionEnrichmentJob.java`
  - `ingestion/flink/jobs/AnomalyWindowJob.java`
- E2E and DB ingestion verification scripts are implemented:
  - `ingestion/verify_e2e_ingestion.py`
  - `ingestion/verify_db_ingestion.py`
- Kafka producer/CDC mock generator and tests are implemented:
  - `ingestion/debezium/mock-cbs-generator.py`
  - `ingestion/debezium/tests/test_mock_cbs_generator.py`

### Frontend status in this repo

- This repo currently has a single primary app surface (dashboard route):
  - `frontend/src/App.tsx`
  - `frontend/src/main.tsx`
- It is wired to live backend endpoints and websocket alerts through `frontend/src/services/api.ts`.

## 3) What is built vs partial vs missing

## Built (code exists and is wired)

- Backend API composition and routing (`backend/app/main.py`)
- Neo4j persistence and graph query service (`backend/app/services/neo4j_service.py`)
- Fraud scoring pipeline with rules + ML-service call fallback (`backend/app/services/fraud_scorer.py`)
- LLM service integration path (Groq + mock fallback) (`backend/app/services/llm_service.py`)
- Alerts websocket push (`backend/app/routers/ws.py`)
- STR lifecycle endpoints including approve/reject and submit (`backend/app/routers/reports.py`)
- Enforcement lifecycle endpoints including approve/reject (`backend/app/routers/enforcement.py`)
- Timeline service with Cassandra primary + Neo4j fallback (`backend/app/services/timeline_service.py`)
- Flink ingestion jobs and packaging (`ingestion/flink/pom.xml`, jobs/*.java)
- Docker Compose local infra stack for core dependencies (`docker/docker-compose.yml`)
- Provider and infra smoke scripts (`scripts/provider_live_smoke.py`, `scripts/infra_stack_smoke.py`)
- Backend test suite for approval/enforcement/workflow routes (`backend/tests/*`)

## Partially built (implemented, but not production-complete)

- ML serving is operational but primarily fallback-first in absence of trained artifacts:
  - `ml/serving/ml_service.py` can train simple fallback linear models from local CSV/SQL.
  - Real model loading is conditional on model files existing.
- Graph analytics exists in backend (`run_gds_analytics`) but depends on Neo4j GDS plugin and runtime data shape.
- External provider integrations (Finacle/FIU/NCRP) are HTTP wrappers but minimal hardening:
  - basic request/response handling only, limited resilience patterns.
- CI/CD workflows exist under `ci-cd/.github/workflows/*`, but deployment jobs include scaffold/placeholder steps.
- Kubernetes overlays exist, but manifests are skeletal (mostly namespace/base references).

## Not built or scaffold-only

- GraphSAGE training/evaluation/model training loops:
  - `ml/models/graphsage/train.py`
  - `ml/models/graphsage/evaluate.py`
  - `ml/models/graphsage/model.py`
- Drools rule engine execution path is not implemented end-to-end:
  - rules are placeholders in `rules/src/main/resources/rules/*.drl`
  - no Java rule execution service in `rules/src/main/java` (directory absent)
- Compliance pack is placeholder-level:
  - `compliance/README.md` says placeholder bootstrap
- Kubernetes production workload manifests are not present (Deployments/Services/HPA/etc).
- Contract alignment is incomplete (see section 4).

## 4) Code-vs-doc drift and interface drift

### Documentation drift

- README claims on-prem Qwen usage, but runtime code uses Groq settings by default:
  - docs: `README.md`
  - code: `backend/app/services/llm_service.py`, `backend/app/config.py`
- README claims full 3-model ML ensemble; code currently supports this only if model artifacts are present, otherwise fallback linear/rule path dominates.

### API/contract drift

- `contracts/ml-scoring-protocol.json` request fields (`source_account`, `destination_account`) do not match actual ML service request shape (`enriched_transaction` object) in `ml/serving/ml_service.py`.
- OpenAPI docs are high-level and not fully synchronized with all backend route payload details.

### CI/CD structure drift

- Workflows are inside `ci-cd/.github/workflows`.
- GitHub Actions natively expects `.github/workflows` at repository root.
- If not mirrored/symlinked in repo root, these workflows will not run automatically in GitHub.

## 5) Operational risks found

1. Non-demo startup can fail hard by default unless provider credentials are present.
   - `backend/app/config.py` has `DEMO_MODE = False` default.
   - `backend/app/main.py` enforces provider config in non-demo mode.

2. Frontend auth redirect points to `/login`, but this repo frontend routes only `/` and `/dashboard`.
   - `frontend/src/services/api.ts` redirects to `/login` on 401.
   - `frontend/src/main.tsx` does not define `/login` route.

3. Flink code uses deprecated Kafka APIs.
   - IDE diagnostics flag deprecated `FlinkKafkaConsumer`/`FlinkKafkaProducer` usage in job files.
   - Works today but increases upgrade risk.

4. Rules engine mismatch.
   - Fraud typologies are enforced in Python heuristics (`fraud_scorer.py`), while Drools rules are placeholders.

5. Kubernetes readiness gap.
   - Base/overlays mostly namespace wiring without app deployments.

## 6) What is demonstrably runnable now

With dependencies available, this repository supports a real local demo path:

- Backend API with graph-backed alerting and investigations.
- Frontend dashboard pulling live alerts and websocket events.
- Streaming ingestion scripts/jobs for Kafka/Flink pipeline.
- STR and enforcement API flows (with demo/provider-conditional behavior).

## 7) Maturity snapshot (evidence-based)

- API/domain workflow maturity: Medium-High
- Streaming ingestion maturity: Medium
- ML training/MLOps maturity: Low-Medium
- Rule engine maturity: Low
- Kubernetes/prod deployment maturity: Low
- Compliance artifact maturity: Low
- End-to-end local demo maturity: Medium-High

## 8) Priority fixes (ordered)

1. Implement GraphSAGE model/train/evaluate modules or explicitly remove training claims.
2. Replace placeholder Drools rules with executable rule service or de-scope Drools from architecture.
3. Add missing frontend auth route/workflow (or remove hard redirect to `/login`).
4. Align contracts with actual backend/ML payload schemas.
5. Move/duplicate CI workflows to repo-root `.github/workflows` for real automation.
6. Add Kubernetes Deployments/Services/ConfigMaps/Secrets/HPA manifests for backend/frontend/ml components.
7. Add production-grade provider client resilience (retry policy, timeout tiers, typed error mapping, audit-safe logging).

## 9) Bottom line

This is not a fake repository and not just slides. Significant working code exists for backend domain flows, graph operations, streaming jobs, and live UI integration.

But it is also not fully production-complete. The largest gap is between platform claims (full ML + rule engine + production deployment posture) and what is currently implemented end-to-end in executable code.
