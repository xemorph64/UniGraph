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

See the implementation plan for detailed setup instructions.

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

## Documentation

- **Implementation Plan**: `UniGRAPH_3_Person_Implementation_Plan.md` — Master guide for all 3 developers
- **Research & Architecture**: `UniGRAPH_Research_and_Planning.md` — Full blueprint with compliance, Finacle integration, risk register
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
