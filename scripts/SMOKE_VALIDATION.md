# Smoke Validation Guide

## 1) Live Provider Smoke (Staging)

This checks connectivity/auth for Finacle, FIU-IND, and NCRP.

### Required environment variables

- `FINACLE_API_URL`
- `FINACLE_CLIENT_ID`
- `FINACLE_CLIENT_SECRET`
- `FIU_IND_API_URL`
- `FIU_IND_MTLS_CERT_PATH`
- `FIU_IND_MTLS_KEY_PATH`
- `NCRP_API_URL`
- `NCRP_API_KEY`

Optional:

- `FIU_REFERENCE_ID` (if provided, script calls FIU submission-status endpoint)
- `NCRP_HEALTH_URL` (defaults to `<NCRP_API_URL>/api/v1/health`)

### Run

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" scripts/provider_live_smoke.py --timeout 20
```

The script exits with code `1` on any failed non-skipped check.

## 2) Infra Stack Smoke (Local)

This validates docker-compose stack state and probes Kafka, Schema Registry, Debezium, Neo4j, Cassandra, Redis, and Vault endpoints.

### Start stack

```powershell
docker compose -f docker/docker-compose.yml up -d
```

### Run

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" scripts/infra_stack_smoke.py --compose-file docker/docker-compose.yml --timeout 12
```

Optional backend health probe:

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" scripts/infra_stack_smoke.py --compose-file docker/docker-compose.yml --backend-health-url http://localhost:8000/health
```

### Teardown

```powershell
docker compose -f docker/docker-compose.yml down -v
```

## 3) GitHub Actions Workflows

- `ci-cd/.github/workflows/staging-live-provider-smoke.yml`
- `ci-cd/.github/workflows/infra-stack-smoke.yml`

Both are manual (`workflow_dispatch`) and intended for controlled validation runs.

## 4) Demo Data Cleanup (Neo4j)

If this environment was ever seeded with `scripts/demo_seeder.py`, remove known demo entities:

```powershell
& "c:/vs code/UniGRAPH2/.venv/Scripts/python.exe" scripts/cleanup_demo_graph_data.py --uri bolt://localhost:7687 --user neo4j --password unigraph_dev
```
