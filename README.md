# UniGRAPH — AI-Powered Fund Flow Tracking & Fraud Detection

> **"Every rupee has a trail. We follow it."**

An end-to-end, graph-native fund flow tracking platform designed as a pluggable module for **Union Bank of India's Finacle Core Banking System**. Built for PSBs Hackathon IDEA 2.0 by Team "Beyond Just Programming".

---

## What It Does

- Ingests real-time transactional data from CBS via Debezium CDC + Kafka
- Builds a **dynamic Financial Knowledge Graph** in Neo4j
- Applies a **live ML scoring service** with fallback linear models, and uses GraphSAGE/IF/XGBoost artifacts when available
- Detects fraud patterns in **sub-500ms**
- Provides investigators an **interactive graph explorer** with time-travel
- Auto-generates **FIU-IND compliant STR/CTR/CBWTR/NTR** reports in 1 click
- Uses configurable LLM providers (Groq by default, on-prem models supported) to draft investigation narratives

## Key Targets

| Metric | Current | UniGRAPH Target |
|--------|---------|-----------------|
| Investigation time | 4 hours/case | 18 minutes |
| False positive rate | 70%+ | Reduced 40-60% |
| STR filing time | 2-3 days | 1 click |
| Alert latency | Hours (batch) | <500ms |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Cytoscape.js |
| Backend | FastAPI (Python) + WebSocket |
| Streaming | Apache Kafka + Debezium + Flink |
| Graph DB | Neo4j Enterprise 5.x |
| Time-Series | Apache Cassandra 4.x |
| Cache | Redis 7.x |
| Rule Engine | Python rule evaluator (`backend/app/services/rule_evaluator.py`) |
| ML | FastAPI ML scoring service + fallback models; GraphSAGE/XGBoost/IF when artifacts exist |
| LLM | Configurable provider (Groq default, on-prem compatible) |
| Infra | Docker Compose (dev) + Kubernetes (prod) |
| CI/CD | GitHub Actions + ArgoCD + Trivy + SonarQube |

## Team

| Role | Person | Branch Prefix |
|------|--------|---------------|
| Data & Infrastructure Lead | P1 | `p1/` |
| ML & Analytics Lead | P2 | `p2/` |
| Application & Integration Lead | P3 | `p3/` |

## Getting Started

Use the runtime docs below for setup and operations.

```bash
# Clone
git clone <repo-url>
cd unigraph

# Start full dev stack (infrastructure + services)
docker compose -f docker/docker-compose.yml up -d

# Run backend locally (only if you are not already running backend in compose)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Run frontend
cd frontend && npm install && npm run dev
```

Note: Avoid running multiple backend instances on the same port (`8000`). If runtime checks look stale, verify the active process on `:8000` and restart the intended backend process.

## ML Dependency Profile (GPU Default)

- `ml-service` uses `ml/serving/requirements.txt` by default. This keeps GPU-capable dependencies (Torch + XGBoost) enabled.
- First-time image builds can take several minutes because large CUDA/NCCL wheels are downloaded.

If you want a faster CPU-only local build, switch the requirements profile at build time:

```bash
ML_SERVING_REQUIREMENTS=requirements.cpu.txt docker compose -f docker/docker-compose.yml build ml-service
docker compose -f docker/docker-compose.yml up -d ml-service
```

If `ML_SERVING_REQUIREMENTS` is not set, the default GPU profile is used.

## High Throughput Profile

For aggressive ingest targets (for example, approaching 1000 transactions/sec), use the throughput profile below.

1. Backend scoring profile (in `.env`):

```bash
HIGH_THROUGHPUT_MODE=true
HIGH_THROUGHPUT_RULE_ONLY=true
HIGH_THROUGHPUT_SKIP_GRAPH_FEATURES=true
SCORER_ENABLE_GRAPH_SUBGRAPH=false
SCORER_ML_TIMEOUT_SECONDS=1.5
```

2. Start backend with multiple workers (example):

```bash
cd backend
PYTHONPATH=.. uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

3. Start the stream bridge with high concurrency:

```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python ingestion/neo4j_writer.py \
	--bootstrap-servers localhost:19092 \
	--backend-url http://localhost:8000/api/v1 \
	--ingest-workers 128 \
	--max-inflight 8000 \
	--ingest-batch-size 200 \
	--ingest-batch-wait-ms 20 \
	--disable-rule-reingest \
	--http-timeout-seconds 8
```

4. Benchmark stream throughput and backend ingest throughput:

```bash
/home/ojasbhalerao/Documents/Uni/.venv/bin/python ingestion/benchmark_ingestion.py --bootstrap localhost:19092 --count 10000 --timeout 240 --profile optimized
/home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/benchmark_backend_ingest.py --url http://localhost:8000/api/v1/transactions/ingest --count 10000 --concurrency 256 --timeout 8
/home/ojasbhalerao/Documents/Uni/.venv/bin/python scripts/benchmark_backend_ingest.py --url http://localhost:8000/api/v1/transactions/ingest/batch --count 20000 --batch-size 200 --concurrency 32 --timeout 8
```

The batch endpoint (`/api/v1/transactions/ingest/batch`) is intended for high-throughput ingestion paths and can significantly outperform single-request ingest under load.

## Documentation

- **End-to-End Runtime Flow**: `END_TO_END_PIPELINE_MAP.md` — File-to-file system flow from ingestion to frontend
- **Research & Architecture**: `UniGRAPH_Research_and_Planning.md` — Full blueprint with compliance, Finacle integration, risk register
- **SQL Dataset Structure**: `UniGRAPH_SQL_Transaction_Dataset_Structure.md` — Transaction schema and field semantics
- **Smoke Validation**: `scripts/SMOKE_VALIDATION.md` — Live provider checks and infra stack readiness checks
- **Live Demo Runner**: `scripts/run_live_demo.py` — Deterministic ingest -> alert -> investigate -> STR generate/submit validation

## Validation Workflows

- `ci-cd/.github/workflows/staging-live-provider-smoke.yml` — Manual live provider connectivity/auth smoke (staging)
- `ci-cd/.github/workflows/infra-stack-smoke.yml` — Manual docker-compose infra readiness smoke
- `ci-cd/BRANCH_PROTECTION_REQUIRED_CHECKS.md` — Required checks to enforce in GitHub branch protection settings

## Non-Demo Mode

- Backend defaults now run with `DEMO_MODE=false` and `DEMO_SEED_ON_STARTUP=false`.
- In non-demo mode, startup validates provider configuration and fails fast if required values are missing.
- Demo reset route `/api/v1/demo/reset` is disabled in non-demo mode.

If you previously seeded demo entities in Neo4j, clean them with one command:

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" scripts/cleanup_demo_graph_data.py --uri bolt://localhost:7687 --user neo4j --password unigraph_dev
```

## Compliance

Built to comply with:
- RBI FREE-AI Framework (Aug 2025)
- DPDPA 2023
- CERT-In 6-hour reporting
- FIU-IND FINnet 2.0
- PMLA 2002
- NCRP/I4C Golden Hour mandates

---

*Internal use only. Not for public distribution.*
