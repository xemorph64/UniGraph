# UniGRAPH — 3-Person Parallel Implementation Plan

> **Mode**: Agentic Coding — Every detail planned upfront. Humans only review & accept.
> **Team**: 3 developers working in parallel on vertical slices.
> **Integration**: Continuous via contracts, not deferred to the end.

---

## Table of Contents

0. [Current Implementation Status (P1/P2/P3)](#current-implementation-status-p1p2p3)
1. [Integration Strategy](#1-integration-strategy)
2. [Person 1: Data & Infrastructure Lead](#2-person-1-data--infrastructure-lead)
3. [Person 2: ML & Analytics Lead](#3-person-2-ml--analytics-lead)
4. [Person 3: Application & Integration Lead](#4-person-3-application--integration-lead)
5. [Contract Registry (Shared by All)](#5-contract-registry-shared-by-all)
6. [Weekly Integration Cadence](#6-weekly-integration-cadence)
7. [Git Workflow & CODEOWNERS](#7-git-workflow--codeowners)
8. [Definition of Done](#8-definition-of-done)

---

## Current Implementation Status (P1/P2/P3)

Status date: 2026-04-10

### P1: Data & Infrastructure Lead

✅ Completed:
- Flink runtime image updated to Java 17 for both jobmanager and taskmanager in `docker/docker-compose.yml`
- All 12 services defined in docker-compose.yml (zookeeper, kafka-1/2/3, schema-registry, postgres, debezium-connect, flink-jobmanager, flink-taskmanager, neo4j, redis, cassandra, vault)
- Init scripts created: `kafka-topics.sh`, `neo4j-schema.cypher`, `cassandra-init.cql`, `postgres-init.sql`
- Debezium connector config exists at `ingestion/debezium/connector-config.json`
- Mock CBS generator exists at `ingestion/debezium/mock-cbs-generator.py`
- Flink jobs exist: `TransactionEnrichmentJob.java`, `AnomalyWindowJob.java`
- Drools rules created: `rapid_layering.drl`, `structuring.drl`, `dormant_awakening.drl`, `round_tripping.drl`, `mule_network.drl`

### P2: ML & Analytics Lead

✅ Completed:
- `ml/requirements.txt` matches spec
- `ml/data/synthetic_generator.py` - SyntheticFraudGenerator implemented
- `ml/data/feature_engineering.py` - FeatureEngineer implemented
- `ml/models/graphsage/` - GraphSAGE model, train, evaluate
- `ml/models/xgboost_ensemble/` - XGBoost ensemble, SHAP explainer, train
- `ml/models/isolation_forest/` - Isolation Forest model
- `ml/serving/ml_service.py` - FastAPI ML scoring service
- **Test 1 verified**: synthetic data generator produces (1010, 30) with 1000 normal + 10 fraud

### P3: Application & Integration Lead

✅ Completed:
- `backend/requirements.txt`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/auth/jwt_rbac.py`
- `backend/app/routers/` - all routers implemented (transactions, accounts, alerts, cases, reports, ws, fraud_scoring, enforcement)
- `backend/app/services/` - all services implemented (neo4j_service, llm_service, finacle_service, fiu_ind_service, ncrp_service)
- `frontend/package.json`
- `frontend/src/App.tsx` - Dashboard, Alerts, Graph Explorer, Cases views
- `frontend/src/services/api.ts`, `frontend/src/store/authStore.ts`
- LLM configured for Groq API (llama-3.1-70b-versatile)

## Refined Agent Prompts (Safe Update Mode)

### P1 Agent Prompt (Refined)

> "Read `/UniGRAPH_3_Person_Implementation_Plan.md` Section 2. Implement Phase 1 (Foundation) by aligning existing files to spec without destructive overwrite: update `docker/docker-compose.yml` (12 services), `docker/init-scripts/` (`kafka-topics.sh`, `neo4j-schema.cypher`, `cassandra-init.cql`), `ci-cd/.github/workflows/build.yml`, and `.env.example`. Preserve valid existing repository changes and only modify deltas required by Section 2. After each file group, run the verification commands from Section 2.3 Test 5 (Docker Compose Health). If Docker daemon is unavailable, capture the exact blocker and continue with all non-daemon checks."

### P2 Agent Prompt (Refined)

> "Read `/UniGRAPH_3_Person_Implementation_Plan.md` Section 3. Implement Phase 1 (Foundation) by updating existing files to match spec: `ml/requirements.txt`, `ml/data/synthetic_generator.py` (all fraud type generators), and `ml/data/feature_engineering.py`. Do not overwrite unrelated logic that already satisfies the spec. After implementation, run Section 3.3 Tests 1-2 and verify outputs match expected shape and values. Report any mismatch with exact observed output."

### P3 Agent Prompt (Refined)

> "Read `/UniGRAPH_3_Person_Implementation_Plan.md` Section 4. Implement Phase 1 (Foundation) by updating existing files to match spec: `backend/requirements.txt`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/auth/jwt_rbac.py`, `frontend/package.json`, `frontend/src/services/api.ts`, and `frontend/src/store/authStore.ts`. Preserve existing compatible code and only change gaps versus spec. After implementation, run Section 4.3 Tests 1-2 and verify outputs match expected responses."

---

## 1. Integration Strategy

### Core Principle: Contract-First, Mock-Everything, Integrate-Continuously

Each person owns a **vertical slice** — from their layer's bottom to top. They never wait for another person because:

1. **All contracts are written in Week 0** — OpenAPI specs, Avro schemas, Neo4j schema, ML protocol
2. **Every dependency is mocked** — using the exact contract shape
3. **Integration tests run weekly** — swapping mocks for real services one at a time

### Shared Contract Registry (`/contracts/`)

| Contract File | Purpose | Owned By | Consumed By |
|---------------|---------|----------|-------------|
| `fraud-scoring-api.yaml` | `POST /api/v1/fraud/score` request/response | P1+P3 | P3 (implements), Finacle (calls) |
| `enforcement-api.yaml` | Lien/freeze/hold request/response | P1+P3 | P3 (implements), Finacle (calls) |
| `kafka-schemas/enriched-transaction.avsc` | Flink → Neo4j/ML event | P1 | P2 (consumes for ML), P3 (consumes for alerts) |
| `kafka-schemas/ml-score.avsc` | ML → Backend scoring event | P2 | P3 (consumes for alerts/dashboard) |
| `kafka-schemas/rule-violation.avsc` | Drools → Backend violation event | P1 | P3 (consumes for case creation) |
| `kafka-schemas/alert.avsc` | Final alert event | P3 | P1 (infrastructure validation) |
| `neo4j-schema.json` | Graph nodes, relationships, properties | P1 | P2 (reads graph features), P3 (reads for UI) |
| `ml-scoring-protocol.json` | ML service input/output format | P2 | P3 (calls ML service), P1 (pipes data to ML) |
| `backend-api.yaml` | All REST + WebSocket endpoints | P3 | P1 (health checks), P2 (ML service hooks) |

### Mock Strategy Per Person

| Person | Mocks | Tool |
|--------|-------|------|
| P1 | CBS data source, ML service responses, Finacle callback | Python scripts, HTTP mock server |
| P2 | Neo4j graph data, Kafka enriched transactions, Backend callback | Synthetic graph generator, local Kafka, HTTP mock |
| P3 | Neo4j, Kafka, ML service, Finacle, FIU-IND, NCRP | Testcontainers, MSW (frontend), HTTP mocks |

---

## 2. Person 1: Data & Infrastructure Lead

### 2.1 Domain Scope

Everything from data ingestion to graph storage to DevOps backbone.

**You own these directories (no one else touches them):**
```
docker/
kubernetes/
ci-cd/
ingestion/
graph/
rules/
monitoring/
scripts/
.env.example
```

### 2.2 File-by-File Implementation Plan

#### Phase 1: Foundation (Week 0-1)

##### `docker/docker-compose.yml`
**Purpose**: Full local dev stack — one command to start everything.

**Services to define** (exact names, ports, images):

| Service | Image | Port | Health Check |
|---------|-------|------|-------------|
| `zookeeper` | `confluentinc/cp-zookeeper:7.5.0` | 2181 | `echo ruok \| nc localhost 2181` |
| `kafka-1` | `confluentinc/cp-kafka:7.5.0` | 9092 | `kafka-broker-api-versions --bootstrap-server localhost:9092` |
| `kafka-2` | `confluentinc/cp-kafka:7.5.0` | 9093 | same |
| `kafka-3` | `confluentinc/cp-kafka:7.5.0` | 9094 | same |
| `schema-registry` | `confluentinc/cp-schema-registry:7.5.0` | 8081 | `curl -f http://localhost:8081/subjects` |
| `debezium-connect` | `debezium/connect:2.5` | 8083 | `curl -f http://localhost:8083/connectors` |
| `flink-jobmanager` | `flink:1.18-scala_2.12-java17` | 8081 | `curl -f http://localhost:8081/overview` |
| `flink-taskmanager` | `flink:1.18-scala_2.12-java17` | — | depends on jobmanager |
| `neo4j` | `neo4j:5.15-enterprise` | 7474 (HTTP), 7687 (Bolt) | `cypher-shell -u neo4j -p unigraph_dev "RETURN 1"` |
| `redis` | `redis:7-alpine` | 6379 | `redis-cli ping` |
| `cassandra` | `cassandra:4.1` | 9042 | `cqlsh -e "DESCRIBE KEYSPACES"` |
| `vault` | `hashicorp/vault:1.15` | 8200 | `vault status` |

**Networks**: `unigraph-network` (bridge)
**Volumes**: `neo4j_data`, `cassandra_data`, `kafka_data_1`, `kafka_data_2`, `kafka_data_3`, `redis_data`, `vault_data`

##### `docker/.env`
```env
NEO4J_AUTH=neo4j/unigraph_dev
NEO4J_PLUGINS=["apoc","graph-data-science"]
KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka-1:9092
REDIS_URL=redis://redis:6379/0
CASSANDRA_CONTACT_POINTS=cassandra
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=root
```

##### `docker/init-scripts/kafka-topics.sh`
**Purpose**: Create all Kafka topics on first startup.

```bash
#!/bin/bash
KAFKA_BOOTSTRAP=kafka-1:9092

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic raw-transactions \
  --partitions 12 --replication-factor 3 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic enriched-transactions \
  --partitions 12 --replication-factor 3 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic rule-violations \
  --partitions 6 --replication-factor 3 \
  --config retention.ms=259200000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic ml-scores \
  --partitions 12 --replication-factor 3 \
  --config retention.ms=259200000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic alerts \
  --partitions 6 --replication-factor 3 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic training-queue \
  --partitions 3 --replication-factor 3 \
  --config retention.ms=2592000000
```

##### `docker/init-scripts/neo4j-schema.cypher`
**Purpose**: Initialize Neo4j constraints, indexes, and GDS projections.

```cypher
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
```

##### `docker/init-scripts/cassandra-init.cql`
**Purpose**: Create Cassandra keyspaces and tables.

```cql
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
```

##### `ci-cd/.github/workflows/build.yml`
**Purpose**: Run on every push to any branch.

```yaml
name: Build & Test

on:
  push:
    branches: ['**']
  pull_request:
    branches: [develop, main]

jobs:
  lint-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff mypy
      - run: ruff check ingestion/ graph/ rules/ ml/ backend/ compliance/
      - run: mypy ml/ backend/ --ignore-missing-imports

  lint-typescript:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npx eslint src/ --max-warnings 0
      - run: cd frontend && npx tsc --noEmit

  test-python:
    runs-on: ubuntu-latest
    services:
      redis: { image: redis:7-alpine, ports: ['6379:6379'] }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt pytest pytest-asyncio
      - run: pytest backend/tests/ ml/tests/ --cov=backend --cov=ml --cov-report=xml

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm test -- --coverage

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with: { scan-type: 'fs', scan-ref: '.', format: 'sarif' }
      - run: pip install bandit semgrep
      - run: bandit -r backend/ ml/ -f json -o bandit-report.json
      - run: semgrep scan --config auto --json -o semgrep-report.json

  docker-build:
    runs-on: ubuntu-latest
    needs: [lint-python, lint-typescript, security-scan]
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker/docker-compose.yml build
```

##### `ci-cd/.github/workflows/deploy-staging.yml`
**Purpose**: Deploy to staging on merge to `develop`.

```yaml
name: Deploy to Staging

on:
  push:
    branches: [develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-kubectl@v3
      - run: kubectl apply -k kubernetes/overlays/staging/
      - run: kubectl rollout status deployment/unigraph-backend -n unigraph-staging --timeout=300s
      - run: kubectl rollout status deployment/unigraph-frontend -n unigraph-staging --timeout=300s
```

##### `.env.example`
```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=unigraph_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Cassandra
CASSANDRA_CONTACT_POINTS=localhost
CASSANDRA_KEYSPACE=unigraph_ts

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SCHEMA_REGISTRY_URL=http://localhost:8081

# Vault
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=root

# JWT
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=30

# ML Service
ML_SERVICE_URL=http://localhost:8002

# LLM
LLM_URL=http://localhost:11434
LLM_MODEL=qwen3.5:9b

# Finacle
FINACLE_API_URL=https://finacle-sandbox.uboi.in/api/v1
FINACLE_CLIENT_ID=
FINACLE_CLIENT_SECRET=
FINACLE_MTLS_CERT_PATH=
FINACLE_MTLS_KEY_PATH=

# FIU-IND
FIU_IND_API_URL=https://finnet.fiu.gov.in/api/v2
FIU_IND_MTLS_CERT_PATH=

# NCRP
NCRP_API_URL=https://cybercrime.gov.in/api/v1
NCRP_API_KEY=

# App
APP_ENV=development
APP_DEBUG=true
APP_CORS_ORIGINS=http://localhost:5173
```

#### Phase 2: Data Pipeline (Week 2-3)

##### `ingestion/debezium/connector-config.json`
**Purpose**: Configure Debezium to capture CBS transaction events.

```json
{
  "name": "unigraph-cbs-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "plugin.name": "pgoutput",
    "slot.name": "unigraph_replication",
    "publication.name": "unigraph_pub",
    "database.hostname": "cbs-db.internal",
    "database.port": "5432",
    "database.user": "debezium_reader",
    "database.password": "${DEBEZIUM_DB_PASSWORD}",
    "database.dbname": "finacle_cbs",
    "database.server.name": "cbs",
    "table.include.list": "public.transactions,public.accounts,public.customers",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "key.converter": "io.confluent.connect.avro.AvroConverter",
    "key.converter.schema.registry.url": "http://schema-registry:8081",
    "value.converter": "io.confluent.connect.avro.AvroConverter",
    "value.converter.schema.registry.url": "http://schema-registry:8081",
    "topic.prefix": "cbs",
    "heartbeat.interval.ms": "10000",
    "snapshot.mode": "initial",
    "tombstones.on.delete": "false"
  }
}
```

##### `ingestion/debezium/mock-cbs-generator.py`
**Purpose**: Generate synthetic CBS transaction events when real Debezium is unavailable.

**Function signatures**:
```python
def generate_transaction(
    txn_id: str,
    from_account: str,
    to_account: str,
    amount: float,
    channel: str,
    timestamp: str,
    customer_id: str,
    device_fingerprint: str,
    ip_address: str,
    location: dict
) -> dict:
    """Generate a single mock CBS transaction event matching Debezium output format."""

def generate_fraud_scenario_rapid_layering(num_hops: int = 6) -> list[dict]:
    """Generate a chain of 6 rapid transactions (<30 min, each >50K)."""

def generate_fraud_scenario_structuring(num_txns: int = 12) -> list[dict]:
    """Generate 12 transactions just below 10L CTR threshold."""

def generate_fraud_scenario_dormant_awakening() -> list[dict]:
    """Generate a sudden large debit from a dormant account."""

def generate_normal_transactions(count: int = 100) -> list[dict]:
    """Generate realistic normal transaction patterns."""

def publish_to_kafka(events: list[dict], topic: str = "raw-transactions"):
    """Publish events to Kafka topic."""
```

##### `ingestion/flink/jobs/TransactionEnrichmentJob.java`
**Purpose**: Flink job that joins raw transactions with KYC, Geo Risk, and Device stores.

**Class structure**:
```java
public class TransactionEnrichmentJob {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.enableCheckpointing(30000);
        env.setStateBackend(new EmbeddedRocksDBStateBackend());

        // Source: raw-transactions Kafka topic
        FlinkKafkaConsumer<RawTransaction> source = new FlinkKafkaConsumer<>(
            "raw-transactions",
            new AvroDeserializationSchema<>(RawTransaction.class),
            kafkaProps
        );

        // Lookup tables (broadcast state)
        DataStream<KYCRiskScore> kycStream = env.addSource(new KYCLookupSource());
        DataStream<GeoRiskScore> geoStream = env.addSource(new GeoRiskLookupSource());
        DataStream<DeviceRiskFlag> deviceStream = env.addSource(new DeviceRiskLookupSource());

        // Enrichment logic
        DataStream<EnrichedTransaction> enriched = rawTxnStream
            .keyBy(RawTransaction::getFromAccount)
            .connect(kycStream.broadcast())
            .process(new KYCEnrichmentFunction())
            .keyBy(EnrichedTransaction::getFromAccount)
            .connect(geoStream.broadcast())
            .process(new GeoEnrichmentFunction())
            .connect(deviceStream.broadcast())
            .process(new DeviceEnrichmentFunction());

        // Sink: enriched-transactions Kafka topic
        enriched.addSink(new FlinkKafkaProducer<>(
            "enriched-transactions",
            new AvroSerializationSchema<>(EnrichedTransaction.class),
            kafkaProps
        ));

        env.execute("TransactionEnrichmentJob");
    }
}
```

##### `ingestion/flink/jobs/AnomalyWindowJob.java`
**Purpose**: Sliding window velocity checks.

5-minute, 1-hour, 24-hour sliding windows. Count transactions per account per window. Flag if velocity exceeds threshold. Output: velocity metrics to enriched stream.

#### Phase 3: Graph + Rules (Week 4-5)

##### `graph/schema/nodes.cypher`
```cypher
-- Account node creation (called by Graph Writer Service)
CREATE (a:Account {
    id: $account_id,
    customer_id: $customer_id,
    account_type: $account_type,
    branch_code: $branch_code,
    open_date: date($open_date),
    kyc_tier: $kyc_tier,
    risk_score: 0.0,
    is_dormant: false,
    community_id: 0,
    pagerank: 0.0,
    last_active: datetime($last_active)
})

-- Customer node
CREATE (c:Customer {
    id: $customer_id,
    pan: $pan_encrypted,
    aadhaar_hash: $aadhaar_hash,
    name_encrypted: $name_encrypted,
    dob: date($dob),
    pep_flag: false,
    sanction_flag: false,
    kyc_verified: true,
    occupation_code: $occupation_code
})

-- Transaction node
CREATE (t:Transaction {
    id: $txn_id,
    amount: $amount,
    currency: $currency,
    channel: $channel,
    timestamp: datetime($timestamp),
    description: $description,
    device_id: $device_fingerprint,
    ip_address: $ip_hash,
    geo_lat: $geo_lat,
    geo_lon: $geo_lon,
    risk_score: 0.0,
    rule_violations: [],
    is_flagged: false,
    alert_id: null
})

-- Device node
CREATE (d:Device {
    id: $device_id,
    device_type: $device_type,
    os_version: $os_version,
    first_seen: datetime($first_seen),
    account_count: 1
})
```

##### `graph/schema/relationships.cypher`
```cypher
-- Customer owns Account
MATCH (c:Customer {id: $customer_id}), (a:Account {id: $account_id})
CREATE (c)-[:OWNS]->(a)

-- Account sent to Account (transaction relationship)
MATCH (src:Account {id: $from_account}), (dst:Account {id: $to_account})
CREATE (src)-[:SENT {
    amount: $amount,
    timestamp: datetime($timestamp),
    txn_id: $txn_id,
    channel: $channel
}]->(dst)

-- Account used Device
MATCH (a:Account {id: $account_id}), (d:Device {id: $device_id})
MERGE (a)-[r:USED_DEVICE]->(d)
ON CREATE SET r.last_used = datetime($timestamp)
ON MATCH SET r.last_used = datetime($timestamp)

-- Device shared by accounts (mule detection)
MATCH (d:Device {id: $device_id})<-[:USED_DEVICE]-(a:Account)
WITH d, count(a) as account_count
WHERE account_count > 3
MATCH (a1:Account)-[:USED_DEVICE]->(d)<-[:USED_DEVICE]-(a2:Account)
WHERE a1 <> a2
MERGE (a1)-[:LINKED_TO {reason: 'shared_device', confidence: 0.8}]->(a2)
```

##### `graph/schema/indexes.cypher`
```cypher
-- Additional GDS projection
CALL gds.graph.project(
    'unigraph',
    {
        Account: {
            properties: ['risk_score', 'kyc_tier', 'is_dormant', 'community_id']
        }
    },
    {
        SENT: {
            properties: ['amount', 'timestamp'],
            orientation: 'NATURAL'
        },
        LINKED_TO: {
            properties: ['confidence'],
            orientation: 'NATURAL'
        }
    }
)
```

##### `graph/queries/fraud_patterns.cypher`
```cypher
-- 2-hop fund flow from an account
MATCH path = (src:Account {id: $account_id})-[:SENT*1..2]->(suspicious)
WHERE ALL(r IN relationships(path) WHERE r.timestamp > datetime($window_start))
RETURN path,
       reduce(total = 0, r IN relationships(path) | total + r.amount) as total_flow,
       length(path) as hops

-- Circular round-trip detection (3-6 hops, within time window)
MATCH path = (a:Account)-[:SENT*3..6]->(a)
WHERE ALL(r IN relationships(path) WHERE r.timestamp > datetime($window_start))
  AND length(path) >= 3
RETURN path,
       reduce(total = 0, r IN relationships(path) | total + r.amount) as round_trip_amount,
       length(path) as cycle_length
ORDER BY cycle_length ASC

-- Mule network: shared device across >3 accounts in 7 days
MATCH (a:Account)-[:USED_DEVICE]->(d:Device)<-[:USED_DEVICE]-(b:Account)
WHERE a <> b
  AND d.first_seen > datetime($window_start)
WITH a, b, d, count(DISTINCT b) as shared_accounts
WHERE shared_accounts >= 3
RETURN a.id as account_a, b.id as account_b, d.id as device, shared_accounts
ORDER BY shared_accounts DESC

-- Dormant account awakening
MATCH (a:Account {is_dormant: true})
WHERE a.dormant_since < datetime($cutoff_date)
MATCH (a)-[r:SENT]->(b:Account)
WHERE r.timestamp > a.dormant_since
RETURN a.id, r.amount, r.timestamp, b.id
ORDER BY r.amount DESC

-- Rapid layering: >5 hops in <30 min
MATCH path = (start:Account)-[:SENT*5..10]->(end:Account)
WHERE duration.between(
    head(relationships(path)).timestamp,
    last(relationships(path)).timestamp
).minutes < 30
RETURN path,
       reduce(total = 0, r IN relationships(path) | total + r.amount) as total_amount,
       length(path) as hop_count
ORDER BY hop_count DESC
```

##### `graph/queries/investigation.cypher`
```cypher
-- Get N-hop subgraph for Cytoscape visualization
MATCH path = (center:Account {id: $account_id})-[*1..$hops]-(neighbor)
WHERE ALL(r IN relationships(path) WHERE r.timestamp > datetime($window_start))
RETURN nodes(path) as nodes, relationships(path) as relationships

-- Transaction timeline for an account
MATCH (a:Account {id: $account_id})-[r:SENT|RECEIVED]->(other)
RETURN r.txn_id as txn_id,
       r.amount as amount,
       r.timestamp as timestamp,
       r.channel as channel,
       other.id as counterparty,
       type(r) as direction
ORDER BY r.timestamp DESC
LIMIT 100

-- Find path between two accounts
MATCH path = shortestPath(
    (a:Account {id: $from_account})-[:SENT*1..6]-(b:Account {id: $to_account})
)
RETURN path, length(path) as hops
```

##### `graph/gds/analytics_jobs.cypher`
```cypher
-- PageRank (run daily)
CALL gds.pageRank.write('unigraph', {
    writeProperty: 'pagerank',
    maxIterations: 20,
    dampingFactor: 0.85
}) YIELD nodePropertiesWritten, ranIterations;

-- Louvain Community Detection (run weekly)
CALL gds.louvain.write('unigraph', {
    writeProperty: 'community_id',
    maxIterations: 10,
    tolerance: 0.0001
}) YIELD communityCount, ranIterations, modularities;

-- Betweenness Centrality (run weekly)
CALL gds.betweenness.write('unigraph', {
    writeProperty: 'betweenness_centrality'
}) YIELD centralityDistribution;
```

##### `graph/services/graph_writer.py`
**Purpose**: Python service that consumes enriched transactions from Kafka and writes to Neo4j + Cassandra.

```python
class GraphWriterService:
    def __init__(self, neo4j_driver, cassandra_session, redis_client):
        self.neo4j = neo4j_driver
        self.cassandra = cassandra_session
        self.redis = redis_client

    async def process_enriched_transaction(self, txn: EnrichedTransaction):
        """Process a single enriched transaction:
        1. Ensure Account nodes exist (upsert)
        2. Create Transaction node
        3. Create SENT relationship
        4. Update velocity counters in Redis
        5. Write to Cassandra time-series
        6. Trigger rule engine evaluation
        """

    async def _ensure_account_exists(self, account_id: str, customer_id: str):
        """Upsert Account node in Neo4j."""

    async def _create_transaction(self, txn: EnrichedTransaction):
        """Create Transaction node + SENT relationship."""

    async def _update_redis_velocity(self, account_id: str, amount: float, timestamp: int):
        """Update sorted set velocity counters."""

    async def _write_cassandra(self, txn: EnrichedTransaction):
        """Write to transaction_by_account table."""
```

##### `rules/` — Apache Drools Setup

##### `rules/pom.xml`
```xml
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>io.unigraph</groupId>
    <artifactId>unigraph-rules</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    <dependencies>
        <dependency>
            <groupId>org.drools</groupId>
            <artifactId>drools-core</artifactId>
            <version>9.44.0.Final</version>
        </dependency>
        <dependency>
            <groupId>org.drools</groupId>
            <artifactId>drools-compiler</artifactId>
            <version>9.44.0.Final</version>
        </dependency>
    </dependencies>
</project>
```

##### `rules/src/main/resources/rules/rapid_layering.drl`
```drool
package io.unigraph.rules

import io.unigraph.rules.EnrichedTransaction
import io.unigraph.rules.RuleViolation
import java.util.List
import java.util.ArrayList

global List<RuleViolation> violations

rule "Rapid Layering Detection"
    salience 100
when
    $txn : EnrichedTransaction(amount > 50000)
    $chain : List(size >= 5) from collect(
        EnrichedTransaction(
            from_account == $txn.from_account || to_account == $txn.from_account,
            timestamp > $txn.timestamp - 1800000,
            this != $txn
        )
    )
then
    RuleViolation v = new RuleViolation();
    v.setViolationId("RV-LAYER-" + $txn.getTxnId());
    v.setTxnId($txn.getTxnId());
    v.setAccountId($txn.getFromAccount());
    v.setRuleName("RAPID_LAYERING");
    v.setSeverity("HIGH");
    v.setRiskScore(85);
    v.setDetails("Account involved in " + $chain.size() + " transactions within 30 minutes");
    v.setTimestamp(System.currentTimeMillis());
    violations.add(v);
end
```

##### `rules/src/main/resources/rules/structuring.drl`
```drool
package io.unigraph.rules

import io.unigraph.rules.EnrichedTransaction
import io.unigraph.rules.RuleViolation
import java.util.List

global List<RuleViolation> violations

rule "Structuring / Smurfing Detection"
    salience 90
when
    $txn : EnrichedTransaction(amount < 1000000, amount > 500000)
    $count : Number(intValue >= 3) from accumulate(
        EnrichedTransaction(
            from_account == $txn.from_account,
            amount < 1000000,
            amount > 500000,
            timestamp > $txn.timestamp - 86400000,
            this != $txn
        ),
        count(1)
    )
then
    RuleViolation v = new RuleViolation();
    v.setViolationId("RV-STRUCT-" + $txn.getTxnId());
    v.setTxnId($txn.getTxnId());
    v.setAccountId($txn.getFromAccount());
    v.setRuleName("STRUCTURING");
    v.setSeverity("HIGH");
    v.setRiskScore(80);
    v.setDetails("Multiple transactions below CTR threshold in 24h");
    v.setTimestamp(System.currentTimeMillis());
    violations.add(v);
end
```

##### `rules/src/main/resources/rules/dormant_awakening.drl`
```drool
package io.unigraph.rules

import io.unigraph.rules.EnrichedTransaction
import io.unigraph.rules.RuleViolation
import java.util.List

global List<RuleViolation> violations

rule "Dormant Account Awakening"
    salience 95
when
    $txn : EnrichedTransaction(amount > 100000)
    eval($txn.getFromAccount().isDormant() == true)
    eval($txn.getFromAccount().getDormantDays() > 180)
then
    RuleViolation v = new RuleViolation();
    v.setViolationId("RV-DORM-" + $txn.getTxnId());
    v.setTxnId($txn.getTxnId());
    v.setAccountId($txn.getFromAccount().getId());
    v.setRuleName("DORMANT_AWAKENING");
    v.setSeverity("CRITICAL");
    v.setRiskScore(90);
    v.setDetails("Dormant account (" + $txn.getFromAccount().getDormantDays() + " days) sudden large transaction");
    v.setTimestamp(System.currentTimeMillis());
    violations.add(v);
end
```

##### `rules/src/main/resources/rules/round_tripping.drl`
```drool
package io.unigraph.rules

import io.unigraph.rules.EnrichedTransaction
import io.unigraph.rules.RuleViolation
import java.util.List

global List<RuleViolation> violations

rule "Round-Tripping Detection"
    salience 85
when
    $txn : EnrichedTransaction()
    eval($txn.getGraphPath().containsCycle($txn.getFromAccount(), 3, 6))
    eval($txn.getGraphPath().getCycleDurationHours() < 24)
then
    RuleViolation v = new RuleViolation();
    v.setViolationId("RV-ROUND-" + $txn.getTxnId());
    v.setTxnId($txn.getTxnId());
    v.setAccountId($txn.getFromAccount());
    v.setRuleName("ROUND_TRIPPING");
    v.setSeverity("HIGH");
    v.setRiskScore(82);
    v.setDetails("Funds returned to origin within " + $txn.getGraphPath().getCycleDurationHours() + " hours via " + $txn.getGraphPath().getCycleLength() + " hops");
    v.setTimestamp(System.currentTimeMillis());
    violations.add(v);
end
```

##### `rules/src/main/resources/rules/mule_network.drl`
```drool
package io.unigraph.rules

import io.unigraph.rules.EnrichedTransaction
import io.unigraph.rules.RuleViolation
import java.util.List

global List<RuleViolation> violations

rule "Mule Network Detection"
    salience 80
when
    $txn : EnrichedTransaction(deviceRiskFlag == true)
    eval($txn.getDeviceAccountCount() > 3)
then
    RuleViolation v = new RuleViolation();
    v.setViolationId("RV-MULE-" + $txn.getTxnId());
    v.setTxnId($txn.getTxnId());
    v.setAccountId($txn.getFromAccount());
    v.setRuleName("MULE_NETWORK");
    v.setSeverity("CRITICAL");
    v.setRiskScore(88);
    v.setDetails("Device shared across " + $txn.getDeviceAccountCount() + " accounts");
    v.setTimestamp(System.currentTimeMillis());
    violations.add(v);
end
```

#### Phase 4: Production Infrastructure (Week 6-8)

##### `kubernetes/base/kustomization.yaml`
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespaces.yaml
  - neo4j/statefulset.yaml
  - neo4j/service.yaml
  - redis/deployment.yaml
  - redis/service.yaml
  - cassandra/statefulset.yaml
  - cassandra/service.yaml
  - kafka/statefulset.yaml
  - kafka/service.yaml
  - backend/deployment.yaml
  - backend/service.yaml
  - backend/ingress.yaml
  - frontend/deployment.yaml
  - frontend/service.yaml
  - ml/deployment.yaml
  - ml/service.yaml
  - network-policies.yaml
```

##### `kubernetes/base/namespaces.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: unigraph-ingestion
  labels: { istio-injection: enabled }
---
apiVersion: v1
kind: Namespace
metadata:
  name: unigraph-graph
  labels: { istio-injection: enabled }
---
apiVersion: v1
kind: Namespace
metadata:
  name: unigraph-ml
  labels: { istio-injection: enabled }
---
apiVersion: v1
kind: Namespace
metadata:
  name: unigraph-backend
  labels: { istio-injection: enabled }
---
apiVersion: v1
kind: Namespace
metadata:
  name: unigraph-frontend
  labels: { istio-injection: enabled }
---
apiVersion: v1
kind: Namespace
metadata:
  name: unigraph-monitoring
  labels: { istio-injection: enabled }
```

##### `kubernetes/overlays/dev/kustomization.yaml`
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
  - ../../base
namespace: unigraph-dev
patches:
  - target:
      kind: Deployment
      name: unigraph-backend
    patch: |
      - op: replace
        path: /spec/replicas
        value: 1
  - target:
      kind: Deployment
      name: unigraph-ml
    patch: |
      - op: replace
        path: /spec/replicas
        value: 1
```

##### `kubernetes/overlays/production/kustomization.yaml`
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
  - ../../base
namespace: unigraph-production
patches:
  - target:
      kind: Deployment
      name: unigraph-backend
    patch: |
      - op: replace
        path: /spec/replicas
        value: 4
  - target:
      kind: Deployment
      name: unigraph-ml
    patch: |
      - op: replace
        path: /spec/replicas
        value: 3
```

##### `kubernetes/istio/virtual-service.yaml`
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: unigraph-backend
  namespace: unigraph-backend
spec:
  hosts:
    - unigraph-backend.unigraph.svc.cluster.local
  http:
    - route:
        - destination:
            host: unigraph-backend
            port:
              number: 8000
          weight: 100
      timeout: 200ms
      retries:
        attempts: 3
        perTryTimeout: 100ms
        retryOn: 5xx,reset,connect-failure
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: unigraph-ml
  namespace: unigraph-ml
spec:
  hosts:
    - unigraph-ml.unigraph.svc.cluster.local
  http:
    - route:
        - destination:
            host: unigraph-ml
            port:
              number: 8002
          weight: 100
      timeout: 500ms
      retries:
        attempts: 2
        perTryTimeout: 250ms
        retryOn: 5xx,reset
```

##### `kubernetes/istio/destination-rule.yaml`
```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: unigraph-backend
  namespace: unigraph-backend
spec:
  host: unigraph-backend
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        h2UpgradePolicy: DEFAULT
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

##### `monitoring/prometheus/prometheus.yml`
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-exporter:9308']

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'cassandra'
    static_configs:
      - targets: ['cassandra-exporter:5556']

  - job_name: 'flink'
    static_configs:
      - targets: ['flink-jobmanager:8081']

  - job_name: 'backend'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['unigraph-backend:8000']

  - job_name: 'ml-service'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['unigraph-ml:8002']
```

##### `monitoring/alerts/alertmanager.yml`
```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'pagerduty-critical'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
    - match:
        severity: warning
      receiver: 'slack-warnings'

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
  - name: 'slack-warnings'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#unigraph-alerts'
```

##### `monitoring/alerts/rules.yml`
```yaml
groups:
  - name: unigraph-critical
    rules:
      - alert: FraudScoringAPISlow
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job="backend",path="/api/v1/fraud/score"}[5m])) > 0.2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Fraud scoring API P99 latency > 200ms"

      - alert: KafkaConsumerLag
        expr: kafka_consumer_group_lag > 10000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Kafka consumer lag > 10000"

      - alert: Neo4jQuerySlow
        expr: histogram_quantile(0.95, rate(neo4j_query_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Neo4j query P95 latency > 100ms"

      - alert: MLScoringErrorRate
        expr: rate(ml_scoring_errors_total[5m]) / rate(ml_scoring_requests_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "ML scoring error rate > 1%"

      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage > 85%"
```

##### `scripts/seed_graph.py`
**Purpose**: Populate Neo4j with synthetic graph data for testing.

```python
def seed_graph(num_accounts: int = 1000, num_transactions: int = 10000, fraud_ratio: float = 0.02):
    """
    Create synthetic graph with:
    - num_accounts Account nodes + Customer nodes
    - num_transactions SENT relationships
    - Inject fraud_ratio of transactions as fraud patterns
    - Create device sharing patterns for mule detection
    """

def create_normal_cluster(accounts: list, density: float = 0.1):
    """Create a cluster of normal accounts with random transactions."""

def create_fraud_ring(accounts: list, cycle_length: int = 5):
    """Create a circular fraud ring."""

def create_mule_hub(device_id: str, accounts: list):
    """Create a mule hub: one device used by many accounts."""

def create_dormant_account(account_id: str, dormant_days: int = 200):
    """Create an account that was dormant then suddenly active."""
```

##### `scripts/simulate_transactions.py`
**Purpose**: Generate live transaction stream for load testing.

```python
def simulate_transactions(
    rate_per_second: float = 100,
    duration_seconds: int = 3600,
    kafka_topic: str = "raw-transactions",
    fraud_injection_rate: float = 0.02
):
    """
    Publish transactions to Kafka at specified rate.
    Inject fraud patterns at fraud_injection_rate.
    """
```

##### `scripts/dr-failover-test.sh`
```bash
#!/bin/bash
# DR Failover Test Script
echo "=== DR Failover Test ==="
echo "1. Testing Neo4j primary failover..."
kubectl delete pod neo4j-primary-0 -n unigraph-graph
sleep 30
kubectl exec neo4j-secondary-0 -n unigraph-graph -- cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"
echo "2. Testing Kafka broker loss..."
kubectl delete pod kafka-2 -n unigraph-ingestion
sleep 30
kafka-topics --describe --bootstrap-server kafka-0:9092 --topic enriched-transactions
echo "3. Testing Cassandra node recovery..."
kubectl delete pod cassandra-2 -n unigraph-graph
sleep 60
cqlsh cassandra-0 -e "SELECT count(*) FROM unigraph_ts.transaction_by_account"
echo "=== DR Test Complete ==="
```

### 2.3 Sample Input/Output for Independent Testing

#### Test 1: Mock CBS to Kafka to Neo4j Pipeline

**Input** (run `python ingestion/debezium/mock-cbs-generator.py`):
```python
{
    "txn_id": "TXN-2026-00001",
    "from_account": "ACC-001",
    "to_account": "ACC-002",
    "amount": 75000.00,
    "currency": "INR",
    "channel": "IMPS",
    "timestamp": 1712329381234,
    "customer_id": "CUST-001",
    "device_fingerprint": "dev_fp_abc123",
    "ip_address": "sha256:1a2b3c...",
    "geo_lat": 19.0760,
    "geo_lon": 72.8777,
    "reference_number": "REF123456789",
    "description": "Payment for services"
}
```

**Expected Neo4j state after processing**:
```cypher
MATCH (a:Account {id: "ACC-001"}) RETURN a;
-- Expected: Account node with id="ACC-001", risk_score=0.0

MATCH (a:Account {id: "ACC-002"}) RETURN a;
-- Expected: Account node with id="ACC-002", risk_score=0.0

MATCH (a:Account {id: "ACC-001"})-[r:SENT]->(b:Account {id: "ACC-002"})
RETURN r.amount, r.channel, r.timestamp;
-- Expected: amount=75000.00, channel="IMPS"
```

**Expected Cassandra state**:
```cql
SELECT * FROM unigraph_ts.transaction_by_account
WHERE account_id = 'ACC-001' LIMIT 1;
-- Expected: row with txn_id, amount=75000.00, channel="IMPS"
```

#### Test 2: Fraud Scenario - Rapid Layering

**Input** (run `python ingestion/debezium/mock-cbs-generator.py --scenario rapid_layering`):
```
Generates 6 transactions in 25 minutes, each >50K:
ACC-010 to ACC-011 (75K, t=0)
ACC-011 to ACC-012 (74K, t=5min)
ACC-012 to ACC-013 (73K, t=10min)
ACC-013 to ACC-014 (72K, t=15min)
ACC-014 to ACC-015 (71K, t=20min)
ACC-015 to ACC-016 (70K, t=25min)
```

**Expected Drools output** (published to `rule-violations` Kafka topic):
```json
{
    "violation_id": "RV-LAYER-TXN-2026-00010",
    "txn_id": "TXN-2026-00010",
    "account_id": "ACC-010",
    "rule_name": "RAPID_LAYERING",
    "severity": "HIGH",
    "risk_score": 85,
    "details": "Account involved in 6 transactions within 25 minutes",
    "timestamp": 1712330881234
}
```

**Expected Neo4j query result** (run rapid layering query):
```
path: ACC-010 -> ACC-011 -> ACC-012 -> ACC-013 -> ACC-014 -> ACC-015 -> ACC-016
total_flow: 435000.00
hops: 6
```

#### Test 3: Fraud Scenario - Mule Network

**Input**: Create 5 accounts all using the same device `dev_mule_001`, then generate transactions between them.

**Expected Neo4j query result** (run mule network query):
```
account_a: ACC-020, account_b: ACC-021, device: dev_mule_001, shared_accounts: 5
account_a: ACC-020, account_b: ACC-022, device: dev_mule_001, shared_accounts: 5
... (all pairs)
```

**Expected Drools output**:
```json
{
    "violation_id": "RV-MULE-TXN-2026-00020",
    "txn_id": "TXN-2026-00020",
    "account_id": "ACC-020",
    "rule_name": "MULE_NETWORK",
    "severity": "CRITICAL",
    "risk_score": 88,
    "details": "Device shared across 5 accounts",
    "timestamp": 1712331481234
}
```

#### Test 4: GDS Analytics

**Input**: Run `graph/gds/analytics_jobs.cypher` on a graph with 1000 accounts and 10000 transactions.

**Expected output**:
```
PageRank: nodePropertiesWritten=1000, ranIterations=12
Louvain: communityCount=47, ranIterations=8, modularities=[0.62]
Betweenness: centralityDistribution={p99: 0.045, p50: 0.002}
```

#### Test 5: Docker Compose Health

**Command**: `docker compose -f docker/docker-compose.yml up -d && docker compose ps`

**Expected**: All 12 services showing `healthy` or `running` status.

**Verification**:
```bash
curl -f http://localhost:8081/subjects                    # Schema Registry
curl -f http://localhost:8083/connectors                   # Debezium
curl -f http://localhost:7474                              # Neo4j Browser
redis-cli ping                                              # PONG
cqlsh -e "DESCRIBE KEYSPACES"                              # unigraph_ts
kafka-topics --list --bootstrap-server localhost:9092      # 6 topics
```

---

## 3. Person 2: ML & Analytics Lead

### 3.1 Domain Scope

The entire ML pipeline — from feature engineering to model training to serving to monitoring.

**You own these directories (no one else touches them):**
```
ml/
```

### 3.2 File-by-File Implementation Plan

#### Phase 1: Foundation (Week 0-1)

##### `ml/requirements.txt`
```
torch>=2.1.0
torch-geometric>=2.4.0
dgl>=2.0.0
scikit-learn>=1.3.0
xgboost>=2.0.0
shap>=0.44.0
mlflow>=2.9.0
feast>=0.36.0
numpy>=1.24.0
pandas>=2.1.0
fastapi>=0.110.0
uvicorn>=0.24.0
pydantic>=2.5.0
confluent-kafka>=2.3.0
neo4j>=5.15.0
prometheus-client>=0.19.0
imbalanced-learn>=0.12.0
optuna>=3.5.0
```

##### `ml/data/synthetic_generator.py`
**Purpose**: Generate realistic synthetic fraud dataset with class imbalance.

```python
class SyntheticFraudGenerator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def generate_dataset(
        self,
        num_normal: int = 50000,
        num_fraud: int = 250,
        num_accounts: int = 5000,
        date_range_days: int = 90
    ) -> pd.DataFrame:
        """
        Generate synthetic transaction dataset with:
        - num_normal normal transactions
        - num_fraud fraud transactions (0.5% ratio)
        - Realistic account behaviors
        - Temporal patterns (business hours, weekends)
        Returns DataFrame with columns matching feature engineering spec.
        """

    def _generate_normal_transactions(self, num: int, accounts: list) -> pd.DataFrame:
        """Normal transactions: salary credits, bill payments, peer transfers."""

    def _generate_fraud_layering(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: rapid layering — multiple hops in short time."""

    def _generate_fraud_structuring(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: structuring — amounts just below CTR threshold."""

    def _generate_fraud_round_trip(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: round-tripping — funds return to origin."""

    def _generate_fraud_dormant(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: dormant account awakening."""

    def _generate_fraud_mule(self, num: int, accounts: list) -> pd.DataFrame:
        """Fraud type: mule network — shared device/IP."""

    def apply_smote(self, df: pd.DataFrame, target_col: str = 'is_fraud') -> pd.DataFrame:
        """Apply SMOTE to balance classes for tabular features."""

    def save_dataset(self, df: pd.DataFrame, path: str):
        """Save to CSV + metadata JSON."""
```

**Output DataFrame columns**:
```
txn_id, from_account, to_account, amount, channel, timestamp,
is_fraud, fraud_type, customer_age, account_age_days, kyc_tier,
avg_monthly_balance, transaction_count_30d, avg_txn_amount,
std_txn_amount, max_txn_amount, min_txn_amount,
hour_of_day, day_of_week, is_weekend, is_holiday,
geo_distance_from_home, device_risk_flag, device_account_count,
counterparty_risk_score, is_international, channel_switch_count
```

##### `ml/data/feature_engineering.py`
**Purpose**: Transform raw transactions into ML features.

```python
class FeatureEngineer:
    def __init__(self, neo4j_driver, redis_client):
        self.neo4j = neo4j_driver
        self.redis = redis_client

    def extract_transaction_features(self, txn: dict) -> dict:
        """Extract per-transaction features."""
        return {
            'amount_zscore': self._amount_zscore(txn),
            'velocity_1h': self._velocity(txn, window_hours=1),
            'velocity_6h': self._velocity(txn, window_hours=6),
            'velocity_24h': self._velocity(txn, window_hours=24),
            'hour_sin': np.sin(2 * np.pi * txn['hour'] / 24),
            'hour_cos': np.cos(2 * np.pi * txn['hour'] / 24),
            'day_sin': np.sin(2 * np.pi * txn['day_of_week'] / 7),
            'day_cos': np.cos(2 * np.pi * txn['day_of_week'] / 7),
            'geo_distance': self._geo_distance(txn),
            'channel_switch_count': self._channel_switches(txn),
            'counterparty_risk': self._counterparty_risk(txn),
            'amount_to_avg_ratio': txn['amount'] / self._avg_amount(txn),
            'is_round_amount': self._is_round_amount(txn['amount']),
            'time_since_last_txn': self._time_since_last(txn),
        }

    def extract_graph_features(self, account_id: str) -> dict:
        """Extract graph-based features from Neo4j GDS."""
        return {
            'pagerank': self._get_pagerank(account_id),
            'betweenness_centrality': self._get_betweenness(account_id),
            'community_id': self._get_community(account_id),
            'clustering_coefficient': self._get_clustering(account_id),
            'in_degree_24h': self._in_degree(account_id, hours=24),
            'out_degree_24h': self._out_degree(account_id, hours=24),
            'shortest_path_to_fraud': self._shortest_path_to_known_fraud(account_id),
            'community_risk_score': self._community_risk(account_id),
            'neighbor_fraud_ratio': self._neighbor_fraud_ratio(account_id),
        }

    def extract_account_features(self, account_id: str) -> dict:
        """Extract account-level features."""
        return {
            'account_age_days': self._account_age(account_id),
            'kyc_tier': self._kyc_tier(account_id),
            'is_dormant': self._is_dormant(account_id),
            'dormant_days': self._dormant_days(account_id),
            'avg_monthly_balance': self._avg_balance(account_id),
            'transaction_count_30d': self._txn_count_30d(account_id),
            'unique_counterparties_30d': self._unique_counterparties(account_id),
            'avg_txn_amount_30d': self._avg_txn_amount(account_id),
            'std_txn_amount_30d': self._std_txn_amount(account_id),
            'max_txn_amount_30d': self._max_txn_amount(account_id),
            'device_count_30d': self._device_count(account_id),
            'ip_count_30d': self._ip_count(account_id),
        }

    def build_feature_vector(self, txn: dict) -> dict:
        """Combine all feature types into single vector for ML."""
        account_id = txn['from_account']
        features = {}
        features.update(self.extract_transaction_features(txn))
        features.update(self.extract_graph_features(account_id))
        features.update(self.extract_account_features(account_id))
        return features
```

#### Phase 2: Model Training (Week 2-4)

##### `ml/models/graphsage/model.py`
**Purpose**: GraphSAGE GNN for fraud detection.

```python
class GraphSAGEFraudDetector(nn.Module):
    def __init__(
        self,
        in_features: int = 32,
        hidden_dim: int = 128,
        out_features: int = 64,
        num_layers: int = 3,
        dropout: float = 0.3,
        aggregation: str = 'mean'
    ):
        super().__init__()
        # 3-layer GraphSAGE with mean aggregation
        # Output: fraud probability (0-1)

    def forward(self, x, edge_index, edge_attr) -> torch.Tensor:
        """
        Args:
            x: Node features [num_nodes, in_features]
            edge_index: Graph connectivity [2, num_edges]
            edge_attr: Edge features [num_edges, edge_feature_dim]
        Returns:
            fraud_probability [num_nodes, 1]
        """

    def get_embeddings(self, x, edge_index, edge_attr) -> torch.Tensor:
        """Return node embeddings for downstream use."""

    def train_model(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        num_epochs: int = 50,
        lr: float = 0.001,
        weight_decay: float = 1e-5
    ) -> dict:
        """
        Training loop with:
        - Focal loss (gamma=2) for class imbalance
        - Early stopping on validation AUC
        - Learning rate scheduling
        Returns training metrics dict.
        """
```

##### `ml/models/graphsage/train.py`
**Purpose**: Training script for GraphSAGE model.

```python
def train_graphsage(
    data_path: str,
    neo4j_uri: str,
    output_dir: str,
    config: dict
):
    """
    1. Load graph data from Neo4j (2-hop subgraphs around labeled nodes)
    2. Build PyG Data objects
    3. Split train/val/test (70/15/15, stratified by fraud label)
    4. Train GraphSAGE model
    5. Evaluate: AUC, Precision, Recall, F1, AP
    6. Save model + metadata to output_dir
    7. Log to MLflow
    """

def load_graph_data(neo4j_uri: str, account_ids: list, label_col: str) -> Data:
    """Load 2-hop subgraphs from Neo4j as PyG Data object."""

def create_dataloaders(data: Data, batch_size: int = 256) -> tuple:
    """Create train/val/test DataLoaders with NeighborSampler."""

def evaluate_model(model: nn.Module, loader: DataLoader) -> dict:
    """Evaluate model and return metrics dict."""
```

##### `ml/models/graphsage/evaluate.py`
**Purpose**: Evaluation metrics and visualization.

```python
def compute_metrics(y_true, y_pred_proba, threshold: float = 0.5) -> dict:
    """Compute AUC, Precision, Recall, F1, AP, Confusion Matrix."""

def plot_roc_curve(y_true, y_pred_proba, save_path: str):
    """Plot and save ROC curve."""

def plot_precision_recall_curve(y_true, y_pred_proba, save_path: str):
    """Plot and save PR curve."""

def plot_confusion_matrix(y_true, y_pred, save_path: str):
    """Plot and save confusion matrix."""

def generate_model_card(metrics: dict, training_config: dict) -> dict:
    """Generate model card with all metadata."""
```

##### `ml/models/isolation_forest/model.py`
**Purpose**: Isolation Forest for unsupervised anomaly detection.

```python
class IsolationForestDetector:
    def __init__(
        self,
        n_estimators: int = 200,
        contamination: float = 0.005,
        max_samples: str = 'auto',
        random_state: int = 42
    ):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            max_samples=max_samples,
            random_state=random_state
        )

    def fit(self, X: np.ndarray):
        """Fit on normal transaction features."""

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return -1 for anomaly, 1 for normal."""

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Return anomaly scores (lower = more anomalous)."""

    def score_to_0_100(self, scores: np.ndarray) -> np.ndarray:
        """Convert anomaly scores to 0-100 scale for ensemble."""
```

##### `ml/models/xgboost_ensemble/model.py`
**Purpose**: XGBoost ensemble combining all signals.

```python
class XGBoostEnsembleScorer:
    def __init__(
        self,
        n_estimators: int = 500,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        scale_pos_weight: float = 200,
        random_state: int = 42
    ):
        self.model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            scale_pos_weight=scale_pos_weight,
            eval_metric='auc',
            random_state=random_state,
            use_label_encoder=False
        )

    def prepare_features(
        self,
        gnn_score: float,
        if_score: float,
        graph_features: dict,
        transaction_features: dict,
        account_features: dict,
        rule_violations: list
    ) -> np.ndarray:
        """
        Combine all inputs into feature vector:
        [gnn_score, if_score, pagerank, betweenness, community_id,
         num_rule_violations, account_age_days, kyc_tier,
         velocity_1h, velocity_24h, amount_zscore,
         channel_switch_count, device_risk_flag, ...]
        """

    def train(self, X: np.ndarray, y: np.ndarray):
        """Train on labeled data with early stopping."""

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return fraud probability 0-1."""

    def predict_risk_score(self, X: np.ndarray) -> int:
        """Return risk score 0-100."""

    def get_shap_values(self, X: np.ndarray) -> tuple:
        """Return SHAP values and summary for explainability."""
```

##### `ml/models/xgboost_ensemble/shap_explainer.py`
**Purpose**: SHAP explainability wrapper.

```python
class SHAPExplainer:
    def __init__(self, model: xgb.XGBClassifier, X_train: np.ndarray):
        self.explainer = shap.TreeExplainer(model, X_train)

    def explain(self, X: np.ndarray, feature_names: list[str]) -> list[dict]:
        """
        For each sample, return:
        {
            "risk_score": 87,
            "shap_top3": [
                "velocity_1h: +0.32",
                "shared_device_risk: +0.28",
                "amount_zscore: +0.15"
            ],
            "shap_all": {"feature_name": shap_value, ...},
            "base_value": 0.05
        }
        """

    def get_feature_importance(self) -> dict:
        """Return global feature importance ranking."""

    def plot_waterfall(self, shap_values, feature_names, save_path: str):
        """Generate SHAP waterfall plot for a single prediction."""

    def plot_summary(self, shap_values, feature_names, save_path: str):
        """Generate SHAP summary plot for all features."""
```

#### Phase 3: ML Serving (Week 5-6)

##### `ml/serving/ml_service.py`
**Purpose**: FastAPI microservice for real-time ML scoring.

```python
app = FastAPI(title="UniGRAPH ML Scoring Service", version="1.0.0")

class MLScoringService:
    def __init__(self):
        self.gnn_model = None
        self.if_model = None
        self.xgb_model = None
        self.shap_explainer = None
        self.feature_engineer = None
        self.model_version = "unigraph-v1.0.0"

    async def load_models(self, model_dir: str):
        """Load all models from disk."""

    async def score_transaction(self, enriched_txn: dict, graph_features: dict) -> dict:
        """
        Full scoring pipeline:
        1. Extract features
        2. Run GraphSAGE GNN
        3. Run Isolation Forest
        4. Run XGBoost ensemble
        5. Generate SHAP explanation
        6. Return structured result
        """

ml_service = MLScoringService()

@app.on_event("startup")
async def startup():
    await ml_service.load_models(os.getenv("MODEL_DIR", "/models"))

@app.post("/api/v1/ml/score")
async def score(request: MLScoringRequest) -> MLScoringResponse:
    """Score a single transaction."""
    result = await ml_service.score_transaction(
        request.enriched_transaction,
        request.graph_features
    )
    return MLScoringResponse(**result)

@app.post("/api/v1/ml/score/batch")
async def score_batch(request: BatchScoringRequest) -> BatchScoringResponse:
    """Score multiple transactions."""

@app.get("/api/v1/ml/health")
async def health():
    return {"status": "healthy", "model_version": ml_service.model_version}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""

# Pydantic models for request/response
class MLScoringRequest(BaseModel):
    enriched_transaction: dict
    graph_features: dict

class MLScoringResponse(BaseModel):
    txn_id: str
    gnn_fraud_probability: float
    if_anomaly_score: float
    xgboost_risk_score: int
    shap_top3: list[str]
    model_version: str
    scoring_latency_ms: float
    timestamp: str
```

##### `ml/serving/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY ml/serving/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml/ ./ml/

ARG MODEL_URL
RUN mkdir -p /models

EXPOSE 8002

CMD ["uvicorn", "ml.serving.ml_service:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
```

#### Phase 4: Monitoring & Integration (Week 7-8)

##### `ml/monitoring/drift_detection.py`
**Purpose**: Population Stability Index monitoring.

```python
class DriftDetector:
    def __init__(self, reference_data: pd.DataFrame, psi_threshold: float = 0.2):
        self.reference = reference_data
        self.psi_threshold = psi_threshold

    def compute_psi(self, current_data: pd.DataFrame, feature: str) -> float:
        """Compute PSI for a single feature."""

    def detect_drift(self, current_data: pd.DataFrame) -> dict:
        """
        Check all features for drift.
        Returns: {
            "drift_detected": bool,
            "features_drifted": ["feature1", "feature2"],
            "psi_scores": {"feature1": 0.25, "feature2": 0.31},
            "severity": "HIGH" if PSI > 0.25 else "MEDIUM"
        }
        """

    def alert_if_drifted(self, results: dict):
        """Send alert if drift detected (Prometheus metric + log)."""
```

##### `ml/monitoring/fairness_tests.py`
**Purpose**: Bias testing across demographics.

```python
class FairnessTester:
    def __init__(self, model, test_data: pd.DataFrame):
        self.model = model
        self.data = test_data

    def test_demographic_parity(self, protected_attribute: str) -> dict:
        """Check if fraud rate differs across groups."""

    def test_equalized_odds(self, protected_attribute: str) -> dict:
        """Check if TPR/FPR differs across groups."""

    def test_predictive_parity(self, protected_attribute: str) -> dict:
        """Check if PPV differs across groups."""

    def run_all_tests(self) -> dict:
        """Run all fairness tests and return report."""
```

##### `ml/features/feast_repo/feature_store.yaml`
```yaml
project: unigraph
registry: data/registry.db
provider: local
online_store:
    type: redis
    connection_string: localhost:6379
offline_store:
    type: file
entity_key_serialization_version: 2
```

##### `ml/features/feast_repo/features.py`
```python
from feast import Entity, Feature, FeatureView, FileSource, ValueType

account = Entity(name="account_id", value_type=ValueType.STRING)
customer = Entity(name="customer_id", value_type=ValueType.STRING)

account_features = FeatureView(
    name="account_features",
    entities=["account_id"],
    ttl=Duration(days=1),
    features=[
        Feature(name="account_age_days", dtype=ValueType.INT32),
        Feature(name="kyc_tier", dtype=ValueType.INT32),
        Feature(name="is_dormant", dtype=ValueType.BOOL),
        Feature(name="avg_monthly_balance", dtype=ValueType.FLOAT),
        Feature(name="transaction_count_30d", dtype=ValueType.INT32),
        Feature(name="avg_txn_amount_30d", dtype=ValueType.FLOAT),
        Feature(name="std_txn_amount_30d", dtype=ValueType.FLOAT),
    ],
    online=True,
    batch_source=FileSource(...),
)

transaction_features = FeatureView(
    name="transaction_features",
    entities=["account_id"],
    ttl=Duration(hours=24),
    features=[
        Feature(name="velocity_1h", dtype=ValueType.INT32),
        Feature(name="velocity_24h", dtype=ValueType.INT32),
        Feature(name="amount_zscore", dtype=ValueType.FLOAT),
        Feature(name="channel_switch_count", dtype=ValueType.INT32),
    ],
    online=True,
    batch_source=FileSource(...),
)

graph_features = FeatureView(
    name="graph_features",
    entities=["account_id"],
    ttl=Duration(hours=6),
    features=[
        Feature(name="pagerank", dtype=ValueType.FLOAT),
        Feature(name="betweenness_centrality", dtype=ValueType.FLOAT),
        Feature(name="community_id", dtype=ValueType.INT32),
        Feature(name="clustering_coefficient", dtype=ValueType.FLOAT),
    ],
    online=True,
    batch_source=FileSource(...),
)
```

### 3.3 Sample Input/Output for Independent Testing

#### Test 1: Synthetic Data Generation

**Command**: `python -c "from ml.data.synthetic_generator import SyntheticFraudGenerator; g = SyntheticFraudGenerator(); df = g.generate_dataset(num_normal=1000, num_fraud=10); print(df.shape); print(df['is_fraud'].value_counts())"`

**Expected output**:
```
(1010, 30)
is_fraud
0    1000
1      10
Name: count, dtype: int64
```

#### Test 2: Feature Engineering

**Input**:
```python
from ml.data.feature_engineering import FeatureEngineer
fe = FeatureEngineer(neo4j_driver, redis_client)
txn = {
    'txn_id': 'TXN-TEST-001',
    'from_account': 'ACC-001',
    'to_account': 'ACC-002',
    'amount': 75000.00,
    'channel': 'IMPS',
    'timestamp': '2026-04-05T14:23:01Z',
    'hour': 14,
    'day_of_week': 1,
    'geo_lat': 19.0760,
    'geo_lon': 72.8777
}
features = fe.build_feature_vector(txn)
print(len(features), list(features.keys())[:5])
```

**Expected output**:
```
28 ['amount_zscore', 'velocity_1h', 'velocity_6h', 'velocity_24h', 'hour_sin']
```

#### Test 3: GraphSAGE Training

**Command**: `python ml/models/graphsage/train.py --data-path data/synthetic --output-dir models/graphsage-v1 --epochs 30`

**Expected output**:
```
Epoch 1/30: train_loss=0.654, val_auc=0.712
Epoch 5/30: train_loss=0.423, val_auc=0.834
Epoch 10/30: train_loss=0.312, val_auc=0.891
Epoch 15/30: train_loss=0.267, val_auc=0.912
Epoch 20/30: train_loss=0.245, val_auc=0.921
Epoch 25/30: train_loss=0.238, val_auc=0.925
Epoch 30/30: train_loss=0.235, val_auc=0.927

Final Metrics:
  AUC: 0.927
  Precision: 0.891
  Recall: 0.845
  F1: 0.867
  Average Precision: 0.873

Model saved to models/graphsage-v1/
MLflow run: abc123def456
```

#### Test 4: Isolation Forest

**Input**:
```python
from ml.models.isolation_forest.model import IsolationForestDetector
if_model = IsolationForestDetector(n_estimators=200, contamination=0.005)
if_model.fit(X_normal)
scores = if_model.score_samples(X_mixed)
print(f"Normal mean score: {scores[:100].mean():.4f}")
print(f"Fraud mean score: {scores[100:].mean():.4f}")
```

**Expected output**:
```
Normal mean score: 0.4523
Fraud mean score: -0.1234
```

#### Test 5: XGBoost Ensemble

**Input**:
```python
from ml.models.xgboost_ensemble.model import XGBoostEnsembleScorer
xgb = XGBoostEnsembleScorer()
xgb.train(X_train, y_train)

features = xgb.prepare_features(
    gnn_score=0.87,
    if_score=0.72,
    graph_features={'pagerank': 0.045, 'betweenness': 0.023, 'community_id': 1423},
    transaction_features={'velocity_1h': 8, 'amount_zscore': 3.2},
    account_features={'account_age_days': 45, 'kyc_tier': 1},
    rule_violations=['RAPID_LAYERING']
)
risk_score = xgb.predict_risk_score(features)
print(f"Risk Score: {risk_score}")
```

**Expected output**:
```
Risk Score: 87
```

#### Test 6: SHAP Explanation

**Input**:
```python
from ml.models.xgboost_ensemble.shap_explainer import SHAPExplainer
explainer = SHAPExplainer(xgb.model, X_train)
result = explainer.explain(features, feature_names=feature_names_list)
print(result)
```

**Expected output**:
```json
{
    "risk_score": 87,
    "shap_top3": [
        "velocity_1h: +0.32",
        "shared_device_risk: +0.28",
        "amount_zscore: +0.15"
    ],
    "shap_all": {
        "velocity_1h": 0.32,
        "shared_device_risk": 0.28,
        "amount_zscore": 0.15,
        "gnn_score": 0.12,
        "account_age_days": -0.05,
        "kyc_tier": -0.03
    },
    "base_value": 0.05
}
```

#### Test 7: ML Scoring Service

**Start service**: `uvicorn ml.serving.ml_service:app --host 0.0.0.0 --port 8002`

**Request**:
```bash
curl -X POST http://localhost:8002/api/v1/ml/score \
  -H "Content-Type: application/json" \
  -d '{
    "enriched_transaction": {
        "txn_id": "TXN-TEST-001",
        "from_account": "ACC-001",
        "to_account": "ACC-002",
        "amount": 75000.00,
        "channel": "IMPS",
        "timestamp": 1712329381234,
        "kyc_risk_score": 0.3,
        "kyc_tier": 1,
        "geo_risk_score": 0.1,
        "device_risk_flag": true,
        "device_account_count": 5,
        "velocity_1h": 8,
        "velocity_24h": 15,
        "amount_zscore": 3.2
    },
    "graph_features": {
        "pagerank": 0.045,
        "betweenness_centrality": 0.023,
        "community_id": 1423,
        "clustering_coefficient": 0.12,
        "in_degree_24h": 3,
        "out_degree_24h": 8,
        "shortest_path_to_fraud": 2,
        "community_risk_score": 0.87,
        "neighbor_fraud_ratio": 0.4
    }
  }'
```

**Expected response**:
```json
{
    "txn_id": "TXN-TEST-001",
    "gnn_fraud_probability": 0.87,
    "if_anomaly_score": 0.72,
    "xgboost_risk_score": 87,
    "shap_top3": [
        "velocity_1h: +0.32",
        "shared_device_risk: +0.28",
        "amount_zscore: +0.15"
    ],
    "model_version": "unigraph-v1.0.0",
    "scoring_latency_ms": 142,
    "timestamp": "2026-04-05T14:23:01.234Z"
}
```

**Expected latency**: <500ms (P99)

#### Test 8: Drift Detection

**Input**:
```python
from ml.monitoring.drift_detection import DriftDetector
detector = DriftDetector(reference_data=X_train, psi_threshold=0.2)
results = detector.detect_drift(X_current_week)
print(results)
```

**Expected output (no drift)**:
```json
{
    "drift_detected": false,
    "features_drifted": [],
    "psi_scores": {"velocity_1h": 0.08, "amount_zscore": 0.12},
    "severity": "NONE"
}
```

**Expected output (drift)**:
```json
{
    "drift_detected": true,
    "features_drifted": ["velocity_1h", "amount_zscore"],
    "psi_scores": {"velocity_1h": 0.31, "amount_zscore": 0.28},
    "severity": "HIGH"
}
```

#### Test 9: Fairness Testing

**Input**:
```python
from ml.monitoring.fairness_tests import FairnessTester
tester = FairnessTester(xgb.model, test_data)
report = tester.run_all_tests()
print(report)
```

**Expected output**:
```json
{
    "demographic_parity": {
        "passed": true,
        "max_difference": 0.03,
        "threshold": 0.05,
        "details": {"urban": 0.012, "rural": 0.015, "metro": 0.011}
    },
    "equalized_odds": {
        "passed": true,
        "tpr_difference": 0.02,
        "fpr_difference": 0.01
    },
    "predictive_parity": {
        "passed": true,
        "ppv_difference": 0.04
    },
    "overall": "PASS"
}
```

---

## 4. Person 3: Application & Integration Lead

### 4.1 Domain Scope

Everything the user interacts with — backend APIs, frontend UI, Finacle integration, LLM, compliance reporting.

**You own these directories (no one else touches them):**
```
backend/
frontend/
llm/
compliance/
contracts/
```

### 4.2 File-by-File Implementation Plan

#### Phase 1: Foundation (Week 0-1)

##### `backend/requirements.txt`
```
fastapi>=0.110.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
neo4j>=5.15.0
cassandra-driver>=3.28.0
redis>=5.0.0
httpx>=0.25.0
websockets>=12.0
prometheus-fastapi-instrumentator>=6.1.0
structlog>=23.2.0
confluent-kafka>=2.3.0
python-dotenv>=1.0.0
lxml>=4.9.0
jinja2>=3.1.0
```

##### `backend/app/config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_CORS_ORIGINS: str = "http://localhost:5173"
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "unigraph_dev"
    REDIS_URL: str = "redis://localhost:6379/0"
    CASSANDRA_CONTACT_POINTS: str = "localhost"
    CASSANDRA_KEYSPACE: str = "unigraph_ts"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_SCHEMA_REGISTRY_URL: str = "http://localhost:8081"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 30
    ML_SERVICE_URL: str = "http://localhost:8002"
    LLM_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen3.5:9b"
    FINACLE_API_URL: str = ""
    FINACLE_CLIENT_ID: str = ""
    FINACLE_CLIENT_SECRET: str = ""
    FIU_IND_API_URL: str = ""
    NCRP_API_URL: str = ""
    NCRP_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

##### `backend/app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from .config import settings
from .routers import transactions, accounts, alerts, cases, reports, ws, fraud_scoring, enforcement

app = FastAPI(
    title="UniGRAPH Backend API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(ws.router, prefix="/api/v1", tags=["websocket"])
app.include_router(fraud_scoring.router, prefix="/api/v1/fraud", tags=["fraud-scoring"])
app.include_router(enforcement.router, prefix="/api/v1/enforcement", tags=["enforcement"])

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}
```

##### `backend/app/auth/jwt_rbac.py`
**Purpose**: JWT authentication with role-based access control.

```python
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from ..config import settings

class User(BaseModel):
    user_id: str
    username: str
    role: str  # INVESTIGATOR, SUPERVISOR, COMPLIANCE_OFFICER, ADMIN

class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: datetime

security = HTTPBearer()

ROLE_PERMISSIONS = {
    "INVESTIGATOR": ["read:alerts", "read:cases", "write:cases", "read:graph", "read:transactions"],
    "SUPERVISOR": ["read:alerts", "read:cases", "write:cases", "read:graph", "read:transactions", "approve:str", "read:reports"],
    "COMPLIANCE_OFFICER": ["read:alerts", "read:cases", "write:cases", "read:graph", "read:transactions", "approve:str", "read:reports", "write:reports", "submit:str"],
    "ADMIN": ["*"]
}

def create_access_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload = {"sub": user.user_id, "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    payload = decode_token(credentials.credentials)
    return User(user_id=payload.sub, username=payload.sub, role=payload.role)

def require_permission(permission: str):
    def checker(user: User = Depends(get_current_user)):
        user_perms = ROLE_PERMISSIONS.get(user.role, [])
        if "*" not in user_perms and permission not in user_perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker
```

#### Phase 2: Backend APIs (Week 2-4)

##### `backend/app/routers/transactions.py`
```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()

class TransactionResponse(BaseModel):
    txn_id: str
    from_account: str
    to_account: str
    amount: float
    currency: str
    channel: str
    timestamp: str
    risk_score: Optional[float]
    rule_violations: list[str]
    is_flagged: bool
    alert_id: Optional[str]

@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(
    txn_id: str,
    user: User = Depends(require_permission("read:transactions"))
):
    """Get transaction details with SHAP explanation."""

@router.get("/")
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    account_id: Optional[str] = None,
    channel: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    flagged_only: bool = False,
    user: User = Depends(require_permission("read:transactions"))
):
    """List transactions with pagination and filters."""

@router.post("/ingest")
async def ingest_transaction(
    txn: dict,
    user: User = Depends(require_permission("write:transactions"))
):
    """Manually ingest a transaction (for testing)."""
```

##### `backend/app/routers/accounts.py`
```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()

class AccountProfile(BaseModel):
    id: str
    customer_id: str
    account_type: str
    branch_code: str
    open_date: str
    kyc_tier: int
    risk_score: float
    is_dormant: bool
    community_id: int
    pagerank: float
    last_active: str

class SubgraphResponse(BaseModel):
    nodes: list[dict]
    relationships: list[dict]

@router.get("/{account_id}/profile", response_model=AccountProfile)
async def get_account_profile(
    account_id: str,
    user: User = Depends(require_permission("read:accounts"))
):
    """Get account profile with current risk score."""

@router.get("/{account_id}/graph")
async def get_account_subgraph(
    account_id: str,
    hops: int = Query(2, ge=1, le=4),
    window_start: Optional[str] = None,
    user: User = Depends(require_permission("read:graph"))
):
    """Get N-hop subgraph for Cytoscape visualization."""

@router.get("/{account_id}/timeline")
async def get_account_timeline(
    account_id: str,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(require_permission("read:accounts"))
):
    """Get historical risk score timeline from Cassandra."""
```

##### `backend/app/routers/alerts.py`
```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()

class AlertResponse(BaseModel):
    alert_id: str
    txn_id: str
    account_id: str
    risk_score: int
    risk_level: str
    recommendation: str
    shap_summary: str
    rule_flags: list[str]
    status: str
    created_at: str
    assigned_to: Optional[str]

@router.get("/")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    min_risk_score: Optional[int] = None,
    account_id: Optional[str] = None,
    user: User = Depends(require_permission("read:alerts"))
):
    """List alerts with pagination and filters."""

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user: User = Depends(require_permission("write:alerts"))
):
    """Investigator takes ownership of alert."""

@router.post("/{alert_id}/escalate")
async def escalate_alert(
    alert_id: str,
    reason: str,
    user: User = Depends(require_permission("write:alerts"))
):
    """Escalate alert to supervisor."""
```

##### `backend/app/routers/cases.py`
```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()

class CaseCreate(BaseModel):
    alert_id: str
    title: str
    description: str
    priority: str = "MEDIUM"

class CaseResponse(BaseModel):
    case_id: str
    alert_id: str
    title: str
    description: str
    priority: str
    status: str
    assigned_to: str
    created_at: str
    closed_at: Optional[str]
    labels: list[str]

class CaseClose(BaseModel):
    outcome: str
    notes: str

@router.post("/", response_model=CaseResponse)
async def create_case(
    case: CaseCreate,
    user: User = Depends(require_permission("write:cases"))
):
    """Create investigation case from alert."""

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    user: User = Depends(require_permission("read:cases"))
):
    """Get case details."""

@router.put("/{case_id}/close", response_model=CaseResponse)
async def close_case(
    case_id: str,
    close_data: CaseClose,
    user: User = Depends(require_permission("write:cases"))
):
    """Close case and label for ML retraining."""

@router.get("/")
async def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    user: User = Depends(require_permission("read:cases"))
):
    """List cases with pagination."""
```

##### `backend/app/routers/reports.py`
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()

class STRGenerateRequest(BaseModel):
    case_id: str

class STRGenerateResponse(BaseModel):
    case_id: str
    str_draft: str
    xml_preview: str
    shap_summary: str
    transaction_summary: str
    generated_at: str

class STRSubmitRequest(BaseModel):
    case_id: str
    edited_narrative: str
    digital_signature: str

@router.post("/str/generate", response_model=STRGenerateResponse)
async def generate_str(
    request: STRGenerateRequest,
    user: User = Depends(require_permission("write:reports"))
):
    """Generate STR draft with LLM narrative."""

@router.post("/str/{case_id}/submit")
async def submit_str(
    case_id: str,
    request: STRSubmitRequest,
    user: User = Depends(require_permission("submit:str"))
):
    """Submit STR to FIU-IND with maker-checker."""
```

##### `backend/app/routers/ws.py`
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, investigator_id: str):
        await websocket.accept()
        self.active_connections[investigator_id] = websocket

    def disconnect(self, investigator_id: str):
        self.active_connections.pop(investigator_id, None)

    async def broadcast_alert(self, alert_data: dict):
        message = json.dumps({"type": "ALERT_FIRED", **alert_data})
        for ws in self.active_connections.values():
            await ws.send_text(message)

    async def send_personal(self, investigator_id: str, message: dict):
        ws = self.active_connections.get(investigator_id)
        if ws:
            await ws.send_text(json.dumps(message))

manager = ConnectionManager()

@router.websocket("/ws/alerts/{investigator_id}")
async def websocket_alerts(websocket: WebSocket, investigator_id: str):
    """WebSocket endpoint for live alert stream."""
    await manager.connect(websocket, investigator_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ACKNOWLEDGE":
                await handle_acknowledgment(message, investigator_id)
    except WebSocketDisconnect:
        manager.disconnect(investigator_id)
```

##### `backend/app/routers/fraud_scoring.py`
**Purpose**: Finacle plugin API — the critical <200ms SLA endpoint.

```python
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import time

router = APIRouter()

class FraudScoreRequest(BaseModel):
    transactionId: str
    channel: str
    sourceAccount: str
    destinationAccount: str
    amount: float
    currency: str
    timestamp: str
    customerId: str
    beneficiaryName: str
    deviceFingerprint: str
    ipAddress: str
    location: dict
    referenceNumber: str
    callbackUrl: Optional[str] = None

class FraudScoreResponse(BaseModel):
    transactionId: str
    riskScore: int
    riskLevel: str
    recommendation: str
    decisionLatencyMs: float
    reasons: list[str]
    graphEvidence: dict
    shapTopContributors: list[str]
    alertId: Optional[str]
    modelVersion: str

@router.post("/score", response_model=FraudScoreResponse)
async def score_fraud(
    request: FraudScoreRequest,
    x_request_id: str = Header(...),
    x_idempotency_key: str = Header(...)
):
    """
    Real-time fraud scoring for Finacle payment processing.
    SLA: <200ms P99 latency.
    """
    start_time = time.time()

    # 1. Idempotency check
    cached = await redis.get(f"idempotent:{x_idempotency_key}")
    if cached:
        return FraudScoreResponse(**json.loads(cached))

    # 2. Graph features (async, <50ms)
    graph_features = await neo4j_service.get_account_features(request.sourceAccount)

    # 3. ML scoring (async, <100ms)
    ml_result = await ml_service.score(request, graph_features)

    # 4. Rule evaluation (async, <30ms)
    rule_violations = await drools_service.evaluate(request, graph_features)

    # 5. Combine and determine recommendation
    risk_score = ml_result['xgboost_risk_score']
    recommendation = determine_recommendation(risk_score, rule_violations)

    elapsed = (time.time() - start_time) * 1000

    response = FraudScoreResponse(
        transactionId=request.transactionId,
        riskScore=risk_score,
        riskLevel=risk_score_to_level(risk_score),
        recommendation=recommendation,
        decisionLatencyMs=elapsed,
        reasons=generate_reasons(ml_result, rule_violations),
        graphEvidence=graph_features,
        shapTopContributors=ml_result['shap_top3'],
        alertId=generate_alert_id() if risk_score >= 80 else None,
        modelVersion=ml_result['model_version']
    )

    # 6. Cache for idempotency
    await redis.setex(f"idempotent:{x_idempotency_key}", 60, response.json())

    # 7. If HIGH risk, fire alert
    if risk_score >= 80:
        await manager.broadcast_alert({
            "alert_id": response.alertId,
            "risk_score": risk_score,
            "account_id": request.sourceAccount,
            "shap_summary": ", ".join(response.shapTopContributors),
            "timestamp": request.timestamp
        })

    return response

def determine_recommendation(risk_score: int, rule_violations: list) -> str:
    if risk_score >= 90 or any(v.severity == "CRITICAL" for v in rule_violations):
        return "BLOCK"
    elif risk_score >= 80:
        return "HOLD"
    elif risk_score >= 60:
        return "REVIEW"
    else:
        return "ALLOW"

def risk_score_to_level(score: int) -> str:
    if score >= 90: return "CRITICAL"
    elif score >= 80: return "HIGH"
    elif score >= 60: return "MEDIUM"
    else: return "LOW"
```

##### `backend/app/routers/enforcement.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth.jwt_rbac import require_permission, User

router = APIRouter()

class LienRequest(BaseModel):
    accountId: str
    reason: str
    alertId: str
    amount: float
    initiatedBy: str
    requiresMakerChecker: bool = True

class FreezeRequest(BaseModel):
    accountId: str
    reason: str
    caseId: str
    initiatedBy: str
    requiresMakerChecker: bool = True

class NCRPReportRequest(BaseModel):
    complaintId: str
    accountId: str
    action: str
    evidence: dict

@router.post("/lien")
async def mark_lien(
    request: LienRequest,
    user: User = Depends(require_permission("write:enforcement"))
):
    """Mark lien on account via Finacle API."""

@router.post("/freeze")
async def freeze_account(
    request: FreezeRequest,
    user: User = Depends(require_permission("write:enforcement"))
):
    """Freeze account via Finacle API."""

@router.post("/ncrp-report")
async def submit_ncrp_report(
    request: NCRPReportRequest,
    user: User = Depends(require_permission("write:enforcement"))
):
    """Submit NCRP/I4C report for auto-lien and freeze."""
```

##### `backend/app/services/neo4j_service.py`
```python
from neo4j import AsyncGraphDatabase
from typing import Optional

class Neo4jService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def get_account(self, account_id: str) -> Optional[dict]:
        """Get account node by ID."""

    async def get_subgraph(self, account_id: str, hops: int = 2, window_start: str = None) -> dict:
        """Get N-hop subgraph for visualization."""

    async def get_account_features(self, account_id: str) -> dict:
        """Get graph features for ML scoring."""

    async def get_transaction_timeline(self, account_id: str, days: int = 30) -> list[dict]:
        """Get transaction history for an account."""

    async def create_alert(self, alert_data: dict) -> str:
        """Create Alert node and link to Transaction."""

    async def update_account_risk(self, account_id: str, risk_score: float):
        """Update account risk_score property."""

    async def close(self):
        await self.driver.close()
```

##### `backend/app/services/llm_service.py`
```python
import httpx
from typing import Optional

class LLMService:
    def __init__(self, llm_url: str, model: str):
        self.base_url = llm_url
        self.model = model

    async def generate_str_narrative(
        self,
        case_id: str,
        account_id: str,
        risk_score: int,
        violations: list[str],
        shap_reasons: list[str],
        graph_path: str,
        transaction_summary: str
    ) -> str:
        """Call Qwen LLM to draft STR narrative. Max 4000 chars."""

    async def chat(self, messages: list[dict], context: Optional[dict] = None) -> str:
        """Investigator chat with LLM about a case."""

    async def summarize_case(self, case_data: dict) -> str:
        """Generate executive summary for management reporting."""
```

##### `backend/app/services/finacle_service.py`
```python
import httpx
from typing import Optional

class FinacleService:
    def __init__(self, api_url: str, client_id: str, client_secret: str):
        self.base_url = api_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None

    async def _get_token(self) -> str:
        """Get OAuth 2.0 access token from Finacle."""

    async def mark_lien(self, account_id: str, amount: float, reason: str) -> dict:
        """POST to Finacle lien API."""

    async def freeze_account(self, account_id: str, reason: str, case_id: str) -> dict:
        """POST to Finacle freeze API."""

    async def get_account_details(self, account_id: str) -> dict:
        """GET from Finacle account API."""

    async def hold_transaction(self, txn_id: str, reason: str) -> dict:
        """POST to Finacle hold API."""
```

##### `backend/app/services/fiu_ind_service.py`
```python
import httpx

class FIUIndService:
    def __init__(self, api_url: str, mtls_cert_path: str, mtls_key_path: str):
        self.base_url = api_url
        self.mtls_cert_path = mtls_cert_path
        self.mtls_key_path = mtls_key_path

    async def submit_str(self, str_xml: str, digital_signature: str) -> dict:
        """POST to FIU-IND FINnet 2.0 API."""

    async def submit_ctr(self, ctr_xml: str) -> dict:
        """Submit Cash Transaction Report."""

    async def get_submission_status(self, reference_id: str) -> dict:
        """Check status of a previous submission."""
```

##### `backend/app/services/ncrp_service.py`
```python
import httpx

class NCRPService:
    def __init__(self, api_url: str, api_key: str):
        self.base_url = api_url
        self.api_key = api_key

    async def submit_complaint(self, complaint_data: dict) -> dict:
        """Submit complaint to NCRP/I4C portal."""

    async def auto_lien(self, complaint_id: str, account_id: str) -> dict:
        """Auto-mark lien on NCRP-reported account."""

    async def report_status(self, complaint_id: str, status: str) -> dict:
        """Report investigation status back to NCRP."""
```

#### Phase 3: Frontend (Week 5-7)

##### `frontend/package.json`
```json
{
  "name": "unigraph-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src/ --ext .ts,.tsx",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.12.0",
    "cytoscape": "^3.28.0",
    "cytoscape-dagre": "^2.5.0",
    "react-cytoscapejs": "^2.0.0",
    "socket.io-client": "^4.7.0",
    "recharts": "^2.10.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0",
    "lucide-react": "^0.294.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@types/cytoscape": "^3.21.0",
    "@types/cytoscape-dagre": "^2.3.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "eslint": "^8.55.0",
    "@typescript-eslint/eslint-plugin": "^6.14.0",
    "vitest": "^1.0.0"
  }
}
```

##### `frontend/src/services/api.ts`
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('jwt_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const transactionsApi = {
  list: (params: any) => api.get('/transactions/', { params }),
  get: (id: string) => api.get(`/transactions/${id}`),
};

export const alertsApi = {
  list: (params: any) => api.get('/alerts/', { params }),
  acknowledge: (id: string) => api.post(`/alerts/${id}/acknowledge`),
  escalate: (id: string, reason: string) => api.post(`/alerts/${id}/escalate`, { reason }),
};

export const casesApi = {
  list: (params: any) => api.get('/cases/', { params }),
  create: (data: any) => api.post('/cases/', data),
  get: (id: string) => api.get(`/cases/${id}`),
  close: (id: string, data: any) => api.put(`/cases/${id}/close`, data),
};

export const accountsApi = {
  profile: (id: string) => api.get(`/accounts/${id}/profile`),
  subgraph: (id: string, params: any) => api.get(`/accounts/${id}/graph`, { params }),
  timeline: (id: string, days: number) => api.get(`/accounts/${id}/timeline`, { params: { days } }),
};

export const reportsApi = {
  generateSTR: (caseId: string) => api.post('/reports/str/generate', { case_id: caseId }),
  submitSTR: (caseId: string, data: any) => api.post(`/reports/str/${caseId}/submit`, data),
};

export const fraudScoringApi = {
  score: (data: any, headers: any) => api.post('/fraud/score', data, { headers }),
};

export default api;
```

##### `frontend/src/store/authStore.ts`
```typescript
import { create } from 'zustand';

interface AuthState {
  user: { user_id: string; username: string; role: string } | null;
  token: string | null;
  login: (token: string, user: any) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  hasPermission: (permission: string) => boolean;
}

const ROLE_PERMISSIONS: Record<string, string[]> = {
  INVESTIGATOR: ['read:alerts', 'read:cases', 'write:cases', 'read:graph', 'read:transactions'],
  SUPERVISOR: ['read:alerts', 'read:cases', 'write:cases', 'read:graph', 'read:transactions', 'approve:str', 'read:reports'],
  COMPLIANCE_OFFICER: ['read:alerts', 'read:cases', 'write:cases', 'read:graph', 'read:transactions', 'approve:str', 'read:reports', 'write:reports', 'submit:str'],
  ADMIN: ['*'],
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  login: (token, user) => {
    localStorage.setItem('jwt_token', token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem('jwt_token');
    set({ token: null, user: null });
  },
  isAuthenticated: () => !!get().token,
  hasPermission: (permission) => {
    const { user } = get();
    if (!user) return false;
    const perms = ROLE_PERMISSIONS[user.role] || [];
    return perms.includes('*') || perms.includes(permission);
  },
}));
```

##### `frontend/src/components/Dashboard/Dashboard.tsx`
**Components to build**:
- `AlertSummaryCards` — OPEN, INVESTIGATING, CLOSED_FRAUD counts
- `RiskHeatmap` — branch-wise risk distribution
- `MetricsChart` — alert rate, false positive rate over time
- `RecentAlerts` — last 10 alerts with risk score badges
- `QuickStats` — total transactions today, avg risk score, top fraud type

##### `frontend/src/components/AlertInbox/AlertInbox.tsx`
**Components to build**:
- `AlertTable` — sortable, filterable table with columns: alert_id, risk_score, account_id, shap_summary, status, created_at
- `AlertFilters` — filter by status, risk score range, account ID
- `AlertDetail` — slide-out panel with full alert details
- `WebSocketListener` — connects to `/ws/alerts/{investigator_id}`, shows toast on new alert

##### `frontend/src/components/GraphExplorer/GraphExplorer.tsx`
**Components to build**:
- `CytoscapeGraph` — renders nodes (Account, Transaction) with color by risk score
- `NodeExpansion` — click node to fetch 1-hop via `/accounts/{id}/graph`
- `TimeTravelSlider` — slider to select historical timestamp
- `FilterPanel` — filter by amount range, date range, channel type
- `ExportButton` — export graph as PNG
- `NodeContextMenu` — right-click: "Flag as Suspicious", "Add Note", "View Details"
- `Legend` — node/relationship type legend with risk color coding

**Node styling**:
```typescript
const nodeStyle = (node: any) => ({
  label: node.data('id'),
  'background-color': riskColor(node.data('risk_score')),
  'border-width': node.data('is_flagged') ? 3 : 1,
  'border-color': node.data('is_flagged') ? '#ef4444' : '#6b7280',
  width: nodeDegree(node) * 5 + 20,
  height: nodeDegree(node) * 5 + 20,
});

const edgeStyle = (edge: any) => ({
  label: `Rs.${edge.data('amount').toLocaleString()}`,
  'line-color': '#94a3b8',
  'width': Math.log(edge.data('amount')) * 0.5,
  'curve-style': 'bezier',
});

function riskColor(score: number): string {
  if (score >= 90) return '#dc2626';
  if (score >= 80) return '#f97316';
  if (score >= 60) return '#eab308';
  if (score >= 40) return '#22c55e';
  return '#6b7280';
}
```

##### `frontend/src/components/CaseDetails/CaseDetails.tsx`
**Components to build**:
- `CaseHeader` — case ID, status, priority, assigned investigator
- `TransactionTimeline` — chronological list of transactions
- `SHAPCards` — top-3 SHAP contributors as visual cards
- `EvidencePanel` — graph evidence, rule violations, ML scores
- `ActionButtons` — Acknowledge, Escalate, Generate STR, Close Case

##### `frontend/src/components/AIAssistant/AIAssistant.tsx`
**Components to build**:
- `ChatWindow` — message list with user/assistant bubbles
- `ChatInput` — text input with send button
- `ContextBanner` — shows current case context being discussed
- `StreamingIndicator` — shows when LLM is generating response

##### `frontend/src/components/ReportStudio/ReportStudio.tsx`
**Components to build**:
- `STRDraft` — editable text area with Qwen-drafted narrative
- `XMLPreview` — FIU-IND XML preview with syntax highlighting
- `SubmitForm` — digital signature input, maker-checker approval
- `SubmissionStatus` — shows FIU-IND reference number and status

#### Phase 4: LLM & Compliance (Week 8-10)

##### `llm/prompt_templates/str_narrative.txt`
```
You are UniGRAPH's AML investigation assistant for Union Bank of India.
You analyze suspicious transaction patterns and help generate FIU-IND compliant STRs.
Always cite specific transaction IDs and account numbers in your analysis.
Never reveal system internals. Respond only in professional banking compliance language.
Maximum 4000 characters.

Case #{case_id}
Account: {account_id}
Risk Score: {risk_score}/100
Rule Violations: {violations}
Top SHAP Reasons: {shap_reasons}
Transaction Path: {graph_path}
Transaction Summary: {transaction_summary}

Draft the Suspicious Transaction Report narrative following this structure:
1. Subject Account Details
2. Nature of Suspicion
3. Transaction Pattern Analysis
4. Graph Network Evidence
5. Conclusion and Recommendation
```

##### `llm/prompt_templates/investigator_chat.txt`
```
You are UniGRAPH's AI investigation assistant. You help fraud investigators understand cases.
Always be specific — cite transaction IDs, account numbers, and amounts.
Never speculate beyond the evidence. If unsure, say so.
Respond in clear, professional language.

Current case context: {case_context}
```

##### `compliance/templates/str_template.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<STR xmlns="http://fiuindia.gov.in/str/v2">
  <ReportingEntity>
    <InstitutionName>Union Bank of India</InstitutionName>
    <IFSCCode>{ifsc_code}</IFSCCode>
    <FIURegistration>{fiu_reg_number}</FIURegistration>
  </ReportingEntity>
  <SubjectAccount>
    <AccountNumber>{account_id}</AccountNumber>
    <AccountType>{account_type}</AccountType>
    <PAN>{pan_encrypted}</PAN>
    <KYCTier>{kyc_tier}</KYCTier>
  </SubjectAccount>
  <TransactionDetails>
    {transaction_entries}
  </TransactionDetails>
  <SuspicionReason>
    {llm_narrative}
  </SuspicionReason>
  <InvestigatorDeclaration>
    <InvestigatorID>{investigator_id}</InvestigatorID>
    <DigitalSignature>{digital_signature}</DigitalSignature>
    <Timestamp>{timestamp}</Timestamp>
  </InvestigatorDeclaration>
</STR>
```

##### `compliance/fiu_ind_client.py`
```python
class FIUIndClient:
    def __init__(self, api_url: str, mtls_cert: str, mtls_key: str):
        self.base_url = api_url
        self.mtls_cert = mtls_cert
        self.mtls_key = mtls_key

    async def submit_str(self, str_xml: str, signature: str) -> dict:
        """Submit STR to FIU-IND FINnet 2.0 API."""

    async def submit_ctr(self, ctr_xml: str) -> dict:
        """Submit CTR to FIU-IND."""

    async def get_status(self, reference_id: str) -> dict:
        """Check submission status."""
```

##### `compliance/dpdda/consent_manager.py`
```python
class ConsentManager:
    def record_consent(self, customer_id: str, purpose: str, consent_text: str) -> str:
        """Record customer consent for data processing."""

    def verify_consent(self, customer_id: str, purpose: str) -> bool:
        """Verify active consent exists for purpose."""

    def withdraw_consent(self, customer_id: str, purpose: str):
        """Withdraw consent and trigger data erasure workflow."""
```

##### `compliance/audit/audit_logger.py`
```python
class AuditLogger:
    def __init__(self, cassandra_session):
        self.cassandra = cassandra_session

    async def log(self, entity_type: str, entity_id: str, action: str, actor: str, details: dict):
        """Write immutable audit log entry to Cassandra."""
```

### 4.3 Sample Input/Output for Independent Testing

#### Test 1: Backend Health Check

**Command**: `curl http://localhost:8000/health`

**Expected response**:
```json
{"status": "healthy", "version": "1.0.0"}
```

#### Test 2: JWT Auth Flow

**Input**:
```python
from backend.app.auth.jwt_rbac import create_access_token, User, decode_token

user = User(user_id="INV-001", username="investigator1", role="INVESTIGATOR")
token = create_access_token(user)
payload = decode_token(token)
print(payload)
```

**Expected output**:
```
TokenPayload(sub='INV-001', role='INVESTIGATOR', exp=datetime(...))
```

#### Test 3: Fraud Scoring API

**Start backend**: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/fraud/score \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: req-test-001" \
  -H "X-Idempotency-Key: idem-test-001" \
  -d '{
    "transactionId": "TXN-2026-00001",
    "channel": "UPI",
    "sourceAccount": "UBI30100012345678",
    "destinationAccount": "HDFC50100098765432",
    "amount": 75000.00,
    "currency": "INR",
    "timestamp": "2026-04-05T14:23:01.234Z",
    "customerId": "CUST-UBI-0045678",
    "beneficiaryName": "encrypted:AES256:...",
    "deviceFingerprint": "sha256:...",
    "ipAddress": "sha256:...",
    "location": {"lat": 19.0760, "lon": 72.8777},
    "referenceNumber": "REF123456789"
  }'
```

**Expected response** (with mocked ML service):
```json
{
    "transactionId": "TXN-2026-00001",
    "riskScore": 87,
    "riskLevel": "HIGH",
    "recommendation": "HOLD",
    "decisionLatencyMs": 142,
    "reasons": ["mule_account_match", "unusual_velocity_8txns_47min", "graph_cluster_anomaly_score_0.87"],
    "graphEvidence": {
        "connectedSuspiciousNodes": 5,
        "clusterRiskScore": 0.87,
        "pathToKnownFraudster": 2,
        "communityId": 1423
    },
    "shapTopContributors": [
        "velocity_1h: +0.32",
        "shared_device_risk: +0.28",
        "amount_zscore: +0.15"
    ],
    "alertId": "ALT-2026-00123",
    "modelVersion": "unigraph-v1.0.0"
}
```

**Expected latency**: <200ms (P99)

#### Test 4: WebSocket Alert Stream

**Connect**: `ws://localhost:8000/api/v1/ws/alerts/INV-001`

**Expected server message** (when alert fires):
```json
{
    "type": "ALERT_FIRED",
    "alert_id": "ALT-2026-00123",
    "risk_score": 87,
    "account_id": "UBI30100012345678",
    "shap_summary": "High velocity + shared device with known fraud",
    "timestamp": "2026-04-05T14:23:01Z"
}
```

**Client acknowledgment**:
```json
{
    "type": "ACKNOWLEDGE",
    "alert_id": "ALT-2026-00123",
    "investigator_id": "INV-001"
}
```

#### Test 5: STR Generation

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/reports/str/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"case_id": "CASE-2026-00456"}'
```

**Expected response**:
```json
{
    "case_id": "CASE-2026-00456",
    "str_draft": "Subject Account UBI30100012345678 was flagged with risk score 87...",
    "xml_preview": "<?xml version=\"1.0\"?><STR>...</STR>",
    "shap_summary": "velocity_1h: +0.32, shared_device_risk: +0.28",
    "transaction_summary": "8 transactions in 47 minutes totaling Rs.585,000",
    "generated_at": "2026-04-05T14:30:00Z"
}
```

#### Test 6: Neo4j Service

**Input**:
```python
from backend.app.services.neo4j_service import Neo4jService
svc = Neo4jService("bolt://localhost:7687", "neo4j", "unigraph_dev")
profile = await svc.get_account("ACC-001")
print(profile)
```

**Expected output**:
```json
{
    "id": "ACC-001",
    "customer_id": "CUST-001",
    "account_type": "SAVINGS",
    "branch_code": "UBI0001234",
    "open_date": "2024-01-15",
    "kyc_tier": 1,
    "risk_score": 0.0,
    "is_dormant": false,
    "community_id": 1423,
    "pagerank": 0.045,
    "last_active": "2026-04-05T14:23:01Z"
}
```

#### Test 7: Frontend Dashboard

**Start frontend**: `cd frontend && npm run dev`

**Expected**: Dashboard loads at http://localhost:5173 with:
- Alert summary cards showing counts (mock data)
- Risk heatmap (mock data)
- Recent alerts table (mock data)
- All charts rendering without errors

#### Test 8: Graph Explorer

**Expected behavior**:
1. Graph renders with nodes colored by risk score
2. Click any node expands 1-hop neighborhood
3. Time-travel slider changes graph state
4. Right-click shows context menu
5. Export PNG downloads the graph
6. Legend shows node/relationship types

#### Test 9: LLM Service

**Start Ollama**: `ollama run qwen3.5:9b`

**Request**:
```python
from backend.app.services.llm_service import LLMService
llm = LLMService("http://localhost:11434", "qwen3.5:9b")
narrative = await llm.generate_str_narrative(
    case_id="CASE-2026-00456",
    account_id="UBI30100012345678",
    risk_score=87,
    violations=["RAPID_LAYERING", "MULE_NETWORK"],
    shap_reasons=["velocity_1h: +0.32", "shared_device_risk: +0.28"],
    graph_path="ACC-001 -> ACC-002 -> ACC-003 -> ACC-004",
    transaction_summary="8 transactions in 47 minutes"
)
print(f"Narrative length: {len(narrative)} chars")
assert len(narrative) <= 4000
```

**Expected**: STR narrative under 4000 characters, professional banking language, cites specific transaction IDs.

---

## 5. Contract Registry (Shared by All)

### 5.1 Kafka Topic Contracts

These Avro schemas are the single source of truth. P1 creates them, P2 and P3 consume them. No one changes them without all 3 agreeing.

**Topic: raw-transactions**
- Producer: P1 (Debezium / mock CBS generator)
- Consumers: P1 (Flink enrichment)
- Schema file: `ingestion/kafka/schemas/raw-transaction.avsc`

**Topic: enriched-transactions**
- Producer: P1 (Flink enrichment job)
- Consumers: P2 (ML scoring), P3 (graph writer trigger)
- Schema file: `ingestion/kafka/schemas/enriched-transaction.avsc`

**Topic: rule-violations**
- Producer: P1 (Drools rule engine)
- Consumers: P3 (alert creation, case management)
- Schema file: `ingestion/kafka/schemas/rule-violation.avsc`

**Topic: ml-scores**
- Producer: P2 (ML scoring service)
- Consumers: P3 (alert generation, dashboard)
- Schema file: `ingestion/kafka/schemas/ml-score.avsc`

**Topic: alerts**
- Producer: P3 (backend alert service)
- Consumers: P3 (WebSocket push), P1 (monitoring validation)
- Schema file: `ingestion/kafka/schemas/alert.avsc`

**Topic: training-queue**
- Producer: P3 (case close with label)
- Consumers: P2 (model retraining pipeline)
- Schema file: To be defined when retraining is implemented

### 5.2 REST API Contracts

**ML Scoring API** (P2 implements, P3 calls):
```
POST /api/v1/ml/score
Content-Type: application/json

Request:
{
  "enriched_transaction": { ...enriched txn fields... },
  "graph_features": { ...graph feature fields... }
}

Response (200):
{
  "txn_id": "string",
  "gnn_fraud_probability": 0.87,
  "if_anomaly_score": 0.72,
  "xgboost_risk_score": 87,
  "shap_top3": ["velocity_1h: +0.32", "shared_device_risk: +0.28", "amount_zscore: +0.15"],
  "model_version": "unigraph-v1.0.0",
  "scoring_latency_ms": 142,
  "timestamp": "2026-04-05T14:23:01.234Z"
}
```

**Fraud Scoring API** (P3 implements, Finacle calls):
```
POST /api/v1/fraud/score
Headers: X-Request-ID, X-Idempotency-Key
Content-Type: application/json

Request:
{
  "transactionId": "string",
  "channel": "UPI|IMPS|NEFT|RTGS",
  "sourceAccount": "string",
  "destinationAccount": "string",
  "amount": 75000.00,
  "currency": "INR",
  "timestamp": "ISO8601",
  "customerId": "string",
  "beneficiaryName": "string",
  "deviceFingerprint": "string",
  "ipAddress": "string",
  "location": {"lat": 19.0760, "lon": 72.8777},
  "referenceNumber": "string",
  "callbackUrl": "string (optional)"
}

Response (200):
{
  "transactionId": "string",
  "riskScore": 87,
  "riskLevel": "CRITICAL|HIGH|MEDIUM|LOW",
  "recommendation": "ALLOW|REVIEW|HOLD|BLOCK",
  "decisionLatencyMs": 142,
  "reasons": ["string"],
  "graphEvidence": {"connectedSuspiciousNodes": 5, "clusterRiskScore": 0.87},
  "shapTopContributors": ["string"],
  "alertId": "ALT-2026-00123 (null if score < 80)",
  "modelVersion": "unigraph-v1.0.0"
}
```

### 5.3 Neo4j Schema Contract

**Node Labels**: Account, Customer, Transaction, Device, Alert

**Relationship Types**: SENT, RECEIVED, OWNS, USED_DEVICE, SHARED_BY, FLAGGED_AS, LINKED_TO

**Key Properties per Node**:
- Account: id (unique), customer_id, account_type, branch_code, open_date, kyc_tier, risk_score, is_dormant, community_id, pagerank, last_active
- Customer: id (unique), pan (encrypted), aadhaar_hash, name_encrypted, dob, pep_flag, sanction_flag, kyc_verified, occupation_code
- Transaction: id (unique), amount, currency, channel, timestamp, description, device_id, ip_address, geo_lat, geo_lon, risk_score, rule_violations, is_flagged, alert_id
- Device: id (unique), device_type, os_version, first_seen, account_count
- Alert: id (unique), transaction_id, risk_score, shap_top3, rule_flags, status, assigned_to, created_at, closed_at

### 5.4 Contract Change Process

1. Any person proposes a change by editing the schema file
2. All 3 must review and approve the change
3. Update the version in the schema file header
4. Run contract tests to verify backward compatibility
5. If breaking change: all consumers must update before producer deploys

---

## 6. Weekly Integration Cadence

| Week | Milestone | What Gets Integrated | Who Validates |
|------|-----------|---------------------|---------------|
| 1 | Contracts Signed | All OpenAPI specs, Avro schemas, Neo4j schema written and agreed | All 3 |
| 2 | Infra Running | Docker Compose starts all 12 services healthy | P1 runs, P2+P3 verify |
| 3 | Pipeline Flow | Mock CBS -> Kafka -> Flink -> Neo4j (mock data flowing) | P1 demos, P2+P3 query Neo4j |
| 4 | ML Baseline | P2 trains GNN on synthetic data, AUC > 0.90 | P2 demos, P1 validates data flow |
| 5 | Backend Connected | P3 backend connects to real Neo4j, real Redis, real Cassandra | P3 demos, P1 validates connections |
| 6 | ML Service Live | P2 ML scoring API serves real predictions, P3 backend calls it | P2+P3 integration test |
| 7 | Frontend Connected | P3 frontend connects to real backend APIs, WebSocket works | P3 demos, all 3 test UI |
| 8 | End-to-End | Full pipeline: mock CBS -> Kafka -> Flink -> Neo4j -> ML -> Backend -> WebSocket -> Frontend | All 3 run E2E test |
| 9 | Rules + Alerts | P1 Drools rules fire, P3 creates alerts from violations | P1+P3 integration test |
| 10 | Full System | LLM generates STRs, enforcement APIs work, all screens functional | All 3 run full demo |

### Integration Test Checklist (Run Every Friday)

- [ ] Docker Compose: all services healthy
- [ ] Kafka: all 6 topics exist, messages flowing
- [ ] Neo4j: graph queries return results
- [ ] ML Service: scoring API returns risk score + SHAP
- [ ] Backend: all REST endpoints respond with correct status codes
- [ ] Frontend: all pages load, no console errors
- [ ] WebSocket: alerts received in real-time
- [ ] Auth: JWT login, RBAC permissions enforced
- [ ] E2E scenario: single transaction flows through entire pipeline

---

## 7. Git Workflow & CODEOWNERS

### 7.1 Branch Structure

```
main (protected, requires 2 approvals)
├── develop
│   ├── p1/infra/docker-setup
│   ├── p1/infra/kafka-topics
│   ├── p1/infra/neo4j-schema
│   ├── p1/infra/k8s-manifests
│   ├── p1/infra/monitoring
│   ├── p2/ml/synthetic-data
│   ├── p2/ml/graphsage-training
│   ├── p2/ml/xgboost-ensemble
│   ├── p2/ml/ml-serving
│   ├── p2/ml/monitoring
│   ├── p3/backend/auth-rbac
│   ├── p3/backend/rest-endpoints
│   ├── p3/backend/enforcement-apis
│   ├── p3/backend/llm-integration
│   ├── p3/frontend/dashboard
│   ├── p3/frontend/graph-explorer
│   ├── p3/frontend/report-studio
│   └── p3/compliance/fiu-ind
```

### 7.2 CODEOWNERS File

```
# Root config
* @p1 @p2 @p3

# Person 1 owns
/docker/ @p1
/kubernetes/ @p1
/ci-cd/ @p1
/ingestion/ @p1
/graph/ @p1
/rules/ @p1
/monitoring/ @p1
/scripts/ @p1
/.env.example @p1

# Person 2 owns
/ml/ @p2

# Person 3 owns
/backend/ @p3
/frontend/ @p3
/llm/ @p3
/compliance/ @p3
/contracts/ @p3

# Shared (requires all 3)
/contracts/kafka-schemas/ @p1 @p2 @p3
```

### 7.3 Branch Rules

- Each person works on their own branch prefix (`p1/`, `p2/`, `p3/`)
- No one touches another person's directory (enforced by CODEOWNERS)
- PRs to `develop` require review from at least one other person
- `main` requires all 3 to approve
- Squash merge all feature branches to `develop`
- Release branches: `release/v1.0.0` cut from `develop` when all E2E tests pass

### 7.4 PR Template

```markdown
## Person: [P1/P2/P3]
## Task: [brief description]
## Files Changed: [list]
## Tests Added: [count]
## Dependencies: [new packages added]
## Breaking Changes: [yes/no + description]
## Manual Testing: [steps performed]
## Contract Changes: [yes/no - if yes, list changed contracts]
```

---

## 8. Definition of Done

### 8.1 Per Person

**Person 1 (Infrastructure) is done when:**
- [ ] Docker Compose starts all 12 services with one command
- [ ] All services pass health checks
- [ ] Kafka has all 6 topics created
- [ ] Neo4j schema initialized with constraints and indexes
- [ ] Cassandra keyspaces and tables created
- [ ] Debezium connector configured (or mock generator working)
- [ ] Flink enrichment job running
- [ ] Drools rules executing and publishing violations
- [ ] Graph Writer writing to Neo4j + Cassandra
- [ ] Kubernetes manifests validated
- [ ] Monitoring dashboards populated
- [ ] CI/CD pipeline green

**Person 2 (ML) is done when:**
- [ ] Synthetic data generator produces realistic data with correct class imbalance
- [ ] GraphSAGE GNN trained with AUC > 0.90
- [ ] Isolation Forest detecting anomalies
- [ ] XGBoost ensemble scoring 0-100 with SHAP
- [ ] ML scoring API responding < 500ms P99
- [ ] Model registry tracking versions in MLflow
- [ ] Drift detection alerting on PSI > 0.2
- [ ] Fairness tests passing (demographic parity, equalized odds)
- [ ] Feature store (Feast) configured and serving

**Person 3 (Application) is done when:**
- [ ] All REST endpoints responding with correct status codes
- [ ] JWT auth + RBAC working
- [ ] Fraud scoring API < 200ms P99
- [ ] WebSocket delivering alerts in real-time
- [ ] Case management CRUD working
- [ ] STR generation with LLM narrative
- [ ] Frontend dashboard loading with real data
- [ ] Graph Explorer rendering and interactive
- [ ] Alert Inbox with WebSocket feed
- [ ] Report Studio with XML preview
- [ ] AI Assistant chat working
- [ ] Enforcement APIs (lien, freeze) implemented
- [ ] FIU-IND XML templates valid

### 8.2 System-Wide (All 3)

- [ ] End-to-end: mock CBS -> Kafka -> Flink -> Neo4j -> ML -> Backend -> WebSocket -> Frontend
- [ ] All integration tests passing
- [ ] Load testing: 100 txn/sec sustained
- [ ] Security scan: zero critical/high findings
- [ ] All contracts validated
- [ ] Demo ready: full scenario from transaction to STR generation

---

*Document prepared for 3-person parallel development team.*
*Mode: Agentic Coding — every detail planned upfront. Humans review and accept only.*
*Reference: See UniGRAPH_Research_and_Planning.md for full architecture and compliance details.*
