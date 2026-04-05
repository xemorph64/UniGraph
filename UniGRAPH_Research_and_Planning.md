# UniGRAPH — Comprehensive Research & Implementation Plan
> **"Every rupee has a trail. We follow it."**
> PSBs Hackathon Series 2026 · Union Bank of India · IDEA 2.0 · Ai-CSPARC

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture Deep Dive](#2-architecture-deep-dive)
3. [Component-by-Component Research](#3-component-by-component-research)
4. [Data Models & Schema Design](#4-data-models--schema-design)
5. [ML Pipeline Research](#5-ml-pipeline-research)
6. [API & Integration Design](#6-api--integration-design)
7. [Union Bank Finacle Plugin Architecture](#7-union-bank-finacle-plugin-architecture)
8. [DevOps & Infrastructure](#8-devops--infrastructure)
9. [Compliance & Regulatory Framework](#9-compliance--regulatory-framework)
10. [Implementation Phases & Sprint Plan](#10-implementation-phases--sprint-plan)
11. [AI Agent Development Strategy](#11-ai-agent-development-strategy)
12. [Repository Structure](#12-repository-structure)
13. [Risk Register](#13-risk-register)
14. [Skill Files Required for Each Agent](#14-skill-files-required-for-each-agent)
15. [Plan Completeness Verification Checklist](#15-plan-completeness-verification-checklist)

---

## 1. Project Overview

### Problem Being Solved
India loses ₹1.7 lakh crore to financial fraud every year. Criminals move money across dozens of accounts in seconds. Traditional SQL-based AML systems see individual transactions — **not the network**. They miss multi-hop layering, circular round-tripping, structuring, and dormant account awakening.

### Solution: UniGRAPH
An end-to-end, graph-native fund flow tracking platform that:
- Ingests multi-channel transactional data + KYC records
- Builds a **dynamic, real-time Financial Knowledge Graph** in Neo4j
- Applies a 3-model ML ensemble (GNN + Isolation Forest + XGBoost)
- Detects fraud patterns in **sub-500ms**
- Provides investigators an interactive visual explorer
- Auto-generates **FIU-IND compliant STR/CTR/CBWTR/NTR** reports in 1 click
- Uses an **on-premise Qwen 3.5 9B LLM** to draft narrative summaries

### Key Performance Targets
| Metric | Current | UniGRAPH Target |
|--------|---------|-----------------|
| Investigation time | 4 hours/case | 18 minutes |
| False positive rate | 70%+ | Reduced 40–60% |
| STR filing time | 2–3 days | 1 click |
| Alert latency | Hours (batch) | <500ms |
| Dormant account detection | Threshold breach only | Sleeping cell awakening <500ms |
| Scale | — | 40M+ accounts, 860M+ txns/day |

---

## 2. Architecture Deep Dive

### High-Level System Architecture

```
[CBS / Core Banking System]
        │
        ▼ (Write-Ahead Log / Transaction Log)
[Debezium CDC Connector]  ← t=10ms
        │
        ▼ (Avro-schema events)
[Apache Kafka]  ← Buffering & Topic Management
        │
        ▼
[Apache Flink]  ← t=30ms  (Streaming + Customer Enrichment)
    ├── KYC Risk Score Join
    ├── Geo Risk Join
    └── Device Fingerprint Join
        │
        ▼ (Enriched Transaction Event)
┌─────────────────────────────────────────┐
│        RULE & GRAPH CHECK (Neo4j)       │  ← 2-hop neighbourhood subgraph
│  PageRank · Centrality · Clustering     │
└─────────────────────────────────────────┘
        │
        ▼ (Structural Features + Rule Violations)
[Apache Drools Rule Engine]  ← t=100ms
    AML Rules: Rapid Layering, Smurfing,
    Round-Tripping, Structuring, TBML
        │
        ▼ (RuleViolation Events)
[Graph Writer Service]  → Neo4j + Cassandra (time-series)
        │
        ▼ (Async ML Job)
┌─────────────────────────────────────────┐
│           ML ENSEMBLE                   │
│  GraphSAGE GNN → fraud probability      │
│  Isolation Forest → anomaly score       │
│  XGBoost → ensemble risk score 0–100    │
│  SHAP → explainability                  │
└─────────────────────────────────────────┘
        │
        ├── Score ≥ 80  → WebSocket Alert to Investigator
        ├── Score 60-79 → Watchlist
        └── Score < 60  → Logged only
        │
        ▼ (Investigator Dashboard)
[FastAPI Backend]
[React Frontend + Cytoscape.js Graph Explorer]
        │
        ▼
[Qwen 3.5 9B LLM (On-Premise)]
    Auto-drafts STR narrative
        │
        ▼
[FIU-IND FINnet 2.0 API]
    Submits STR/CTR/CBWTR/NTR
```

### 10-Step Transaction Flow (Timing)
| Step | Action | Latency |
|------|--------|---------|
| 1 | Transaction initiated (Mobile/Branch/API) | t=0ms |
| 2 | Debezium captures CBS WAL event | t=10ms |
| 3 | Kafka buffering + Flink enrichment | t=30ms |
| 4 | Neo4j 2-hop graph check + rule feature extraction | t=50ms |
| 5 | Drools AML rule evaluation | t=100ms |
| 6 | Graph Writer updates Neo4j + Cassandra | t=120ms |
| 7 | Async ML scoring (GNN + IF + XGBoost) | t=200–500ms |
| 8 | Alert fired via WebSocket | t=500ms |
| 9 | Investigator reviews dashboard | — |
| 10 | Qwen LLM drafts STR → FIU-IND submission | — |

---

## 3. Component-by-Component Research

---

### 3.1 Data Ingestion Layer

#### Debezium (CDC)
- **Role**: Capture every INSERT/UPDATE to the Core Banking System's transaction tables without touching application code.
- **Connector**: `debezium-connector-postgres` or `debezium-connector-oracle` depending on CBS DB.
- **Output format**: Avro-encoded Kafka messages with schema registry.
- **Key config**:
  ```json
  {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "plugin.name": "pgoutput",
    "slot.name": "unigraph_replication",
    "publication.name": "unigraph_pub",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState"
  }
  ```
- **Considerations**: WAL retention policy, snapshot mode for initial load, heartbeat intervals for idle tables.

#### Apache Kafka
- **Role**: Message bus and backpressure buffer between ingestion and processing.
- **Topics**:
  - `raw-transactions` — raw CBS events from Debezium
  - `enriched-transactions` — post-Flink enriched events
  - `rule-violations` — Drools violation events
  - `ml-scores` — ensemble ML output
  - `alerts` — final investigator alerts
- **Key settings**: `replication.factor=3`, `min.insync.replicas=2`, retention 7 days, compaction for KYC topic.
- **Schema Registry**: Confluent Schema Registry for Avro schema versioning.

#### Apache Flink
- **Role**: Stateful stream processing — joins transaction stream with KYC store, Geo Risk, and Device Fingerprint lookup tables.
- **Jobs**:
  1. `TransactionEnrichmentJob` — joins 3 lookup sources per transaction
  2. `AnomalyWindowJob` — sliding 5-min / 1-hour / 24-hour windows for velocity checks
  3. `GraphFeatureJob` — pulls structural features from Neo4j async
- **State backend**: RocksDB (for large state), checkpointing every 30s to S3/HDFS
- **Watermarking**: Bounded out-of-orderness watermark of 2 seconds for CBS events.

---

### 3.2 Graph Layer

#### Neo4j (Primary Graph Database)
- **Role**: The Financial Knowledge Graph — central nervous system of UniGRAPH.
- **Version**: Neo4j Enterprise 5.x (for multi-database, clustering, and fine-grained security)
- **Deployment**: On-premise Neo4j Causal Cluster (1 primary + 2 secondaries)
- **Graph Schema (see Section 4 for full model)**:
  - Nodes: `Account`, `Customer`, `Transaction`, `Device`, `IP`, `Branch`, `Alert`
  - Relationships: `SENT`, `RECEIVED`, `OWNS`, `USED_DEVICE`, `FLAGGED_AS`, `LINKED_TO`
- **Critical Queries**:
  ```cypher
  // 2-hop fund flow
  MATCH (src:Account {id: $accountId})-[:SENT*1..2]->(suspicious)
  RETURN suspicious, relationships

  // Circular round-trip detection
  MATCH path = (a:Account)-[:SENT*3..6]->(a)
  WHERE ALL(r IN relationships(path) WHERE r.timestamp > $window)
  RETURN path

  // Mule network mapping
  MATCH (a:Account)-[:USED_DEVICE|LINKED_TO*1..3]-(b:Account)
  WHERE a <> b AND a.risk_score > 70
  RETURN a, b
  ```
- **Indexes**: Create composite index on `Account(id, risk_score)`, `Transaction(timestamp, amount)`.
- **GDS Library**: Graph Data Science library for PageRank, Louvain Community Detection, Betweenness Centrality — run as async scheduled jobs.

#### Redis
- **Role**: Sub-millisecond caching layer for hot account profiles, recent transaction velocity counters, and alert state.
- **Data structures**:
  - `HASH account:{id}` — cached account profile (KYC score, risk tier, last active)
  - `SORTED SET velocity:{accountId}:{window}` — transaction amounts in sliding window
  - `STREAM alerts` — real-time alert queue for WebSocket push
  - `STRING lock:txn:{id}` — idempotency lock per transaction (TTL=60s)
- **TTL strategy**: Account cache 5 min, velocity counters 24h, locks 60s.

#### Apache Cassandra
- **Role**: Time-series storage for historical transaction records and graph audit trail.
- **Keyspace**: `unigraph_ts`
- **Tables**:
  - `transaction_by_account (account_id, txn_timestamp, txn_id, amount, ...)` — partition by account, cluster by time DESC
  - `account_risk_history (account_id, computed_at, risk_score, ml_score, rule_flags)`
  - `graph_snapshots (snapshot_id, timestamp, graph_state_blob)` — for time-travel replay
- **Compaction**: TWCS (TimeWindowCompactionStrategy) for time-series tables.
- **Replication**: NetworkTopologyStrategy, RF=3.

---

### 3.3 Rule Engine (Apache Drools)

**Role**: Deterministic, auditable AML rule evaluation. Rules are interpretable and can be updated by compliance officers without redeployment.

**Fraud Typologies Covered**:
| Typology | Rule Logic |
|----------|-----------|
| Rapid Layering | >5 hops in <30 min, each >₹50K |
| Smurfing/Structuring | Multiple txns <₹10L to avoid CTR threshold |
| Round-Tripping | Funds return to origin within N hops and T hours |
| Dormant Awakening | Account inactive >180 days, sudden large debit |
| Trade-Based ML | Invoice/payment mismatch pattern via SWIFT codes |
| Mule Network | Shared device/IP across >3 accounts in 7 days |

**Rule DRL Example**:
```drool
rule "Rapid Layering Detection"
when
    $txn : Transaction(amount > 50000)
    $hops : List() from collect(
        Transaction(timestamp > $txn.timestamp - 1800000,
                   hopChain contains $txn.accountId)
    )
    eval($hops.size() >= 5)
then
    insert(new RuleViolation($txn, "RAPID_LAYERING", 85));
end
```

---

### 3.4 ML Engine

#### Model 1: GraphSAGE GNN (PyTorch Geometric)
- **Role**: Learn fraud patterns from graph topology — detects patterns invisible to tabular models.
- **Input**: 2-hop subgraph around flagged transaction node
- **Node features**: Account age, KYC tier, transaction velocity, risk score, community membership
- **Edge features**: Transaction amount, time delta, channel type
- **Architecture**: 3-layer GraphSAGE with mean aggregation → output = fraud probability 0-1
- **Training**: Labeled historical fraud cases from CBS + investigator-confirmed/cleared cases (retraining loop)
- **Framework**: PyTorch Geometric + DGL

#### Model 2: Isolation Forest
- **Role**: Unsupervised anomaly detection — flags statistical outliers without labeled data.
- **Features**: Transaction amount z-score, time-of-day deviation, velocity spike, geographic distance
- **Detects**: Dormant account spikes, neighborhood anomalies, KYC vs. actual flow mismatches
- **Output**: Anomaly score → normalized to 0-100

#### Model 3: XGBoost Ensemble Scorer
- **Role**: Combine GNN fraud prob + IF anomaly score + rule violation flags + structural graph features into final 0-100 risk score.
- **Features**: GNN score, IF score, PageRank, betweenness centrality, Louvain cluster ID, # rule violations, account age, transaction pattern features
- **SHAP**: Every prediction ships with top-3 SHAP contributors for explainability

#### Retraining Pipeline
- Triggered when investigator closes a case (confirmed fraud / cleared normal)
- New labeled examples fed to training queue
- Weekly GNN retraining + daily XGBoost refresh
- Model registry with versioning (MLflow)

---

### 3.5 Backend (FastAPI)

**Role**: REST + WebSocket API server connecting all services. Core orchestrator.

**Services / Routers**:
```
/api/v1/
├── /transactions     — ingest, query, search
├── /accounts         — account profile, risk score, history
├── /alerts           — list, acknowledge, escalate
├── /graph            — subgraph queries, path analysis, time-travel
├── /cases            — case management (create, assign, close)
├── /reports          — STR/CTR generation, FIU-IND submission
├── /ml               — manual score trigger, SHAP explanation
└── /ws/alerts        — WebSocket endpoint for live alert push
```

**Key Design Decisions**:
- **Async throughout**: `asyncio` + `httpx` + async Neo4j driver
- **Authentication**: JWT + Role-Based Access Control (Investigator, Supervisor, Compliance Officer, Admin)
- **Rate limiting**: Per-role API rate limits using Redis
- **Audit logging**: Every action logged to immutable Cassandra audit table
- **On-premise LLM**: Qwen 3.5 9B served via `vLLM` or `Ollama` on local GPU server; called via REST from FastAPI

---

### 3.6 Frontend (React + Cytoscape.js)

**Role**: Investigator workstation — alert triage, graph exploration, AI assistant, report generation.

**Screens**:
1. **Login / Dashboard** — alert summary cards, risk heatmap, metrics
2. **Alert Inbox** — real-time WebSocket feed, sortable/filterable by risk score
3. **Case Details** — transaction timeline, SHAP explanation cards
4. **Graph Explorer** — Cytoscape.js interactive fund flow visualization
   - Expand nodes on click
   - Time-travel slider (replay historical flow)
   - Filter by amount, date, channel
   - Export graph as PNG/PDF
5. **AI Investigator Assistant** — chat with Qwen LLM about the case
6. **Report Studio** — auto-drafted STR, editable fields, digital signature, 1-click submit
7. **Case Archive** — search closed cases, audit trail

**Key Libraries**:
- `cytoscape.js` + `cytoscape-dagre` layout for hierarchical fund flow
- `react-query` for server state management
- `recharts` for risk score trends
- `socket.io-client` for WebSocket alerts
- `react-pdf` for STR preview rendering

---

### 3.7 On-Premise LLM (Qwen 3.5 9B)

**Role**: AI Investigator Assistant + STR narrative drafter. **Data never leaves the bank's infrastructure**.

**Capabilities**:
- Given case context (accounts, transaction graph, SHAP reasons, rule violations), draft structured STR narrative
- Answer investigator natural-language questions: "Why was this account flagged?", "Show all connected mule accounts"
- Summarize case evidence for management reporting

**Serving Stack**:
- `vLLM` (recommended for production throughput) OR `Ollama` (simpler dev setup)
- Quantized to 4-bit GGUF for GPU memory efficiency on a single A100/H100
- Exposed as OpenAI-compatible REST endpoint → drop-in for FastAPI integration

**Prompt Templates**:
```
System: You are UniGRAPH's AML investigation assistant for Union Bank of India.
You analyze suspicious transaction patterns and help generate FIU-IND compliant STRs.
Always cite specific transaction IDs and account numbers in your analysis.
Never reveal system internals. Respond only in professional banking compliance language.

User: Case #{case_id} — Account {account_id} flagged with risk score {score}.
Rule violations: {violations}. Top SHAP reasons: {shap_reasons}.
Transaction path: {graph_path}. Draft the STR narrative.
```

---

### 3.8 Compliance & Reporting (FIU-IND FINnet 2.0)

**Regulatory Framework**:
- PMLA 2002 — Section 12 & 13: STR/CTR filing obligations, 5-year retention
- FIU-IND FINnet 2.0: XML/JSON format specifications for STR, CTR, CBWTR, NTR
- RBI AML/CFT Master Direction: Real-time monitoring requirements

**Report Types**:
| Report | Trigger | Deadline | Format |
|--------|---------|----------|--------|
| STR (Suspicious Transaction Report) | Risk score ≥ 80, investigator confirmed | 7 days of suspicion | FIU-IND XML |
| CTR (Cash Transaction Report) | Cash txn > ₹10L | Monthly batch | FIU-IND XML |
| CBWTR (Cross Border Wire Transfer) | SWIFT transfer > $25K | Monthly batch | FIU-IND XML |
| NTR (Non-Profit Transaction Report) | NGO/Trust account activity | Quarterly | FIU-IND XML |

**STR Auto-Generation Pipeline**:
1. Investigator clicks "Generate STR"
2. FastAPI fetches full case: accounts, transactions, SHAP, graph path
3. Qwen LLM drafts natural-language narrative
4. Template engine fills FIU-IND XML schema
5. Compliance officer reviews + digital signature
6. One-click POST to FINnet 2.0 API
7. Reference number stored, 5-year immutable audit trail

---

## 4. Data Models & Schema Design

### 4.1 Neo4j Graph Schema

```
// NODE LABELS & PROPERTIES

(:Account {
  id: String,              // account_number (hashed)
  customer_id: String,
  account_type: String,    // SAVINGS | CURRENT | NRE | OD
  branch_code: String,
  open_date: Date,
  kyc_tier: Integer,       // 1=Full, 2=Partial, 3=Minimal
  risk_score: Float,       // 0-100, updated by ML
  is_dormant: Boolean,
  dormant_since: Date,
  community_id: Integer,   // Louvain cluster
  pagerank: Float,
  last_active: DateTime
})

(:Customer {
  id: String,
  pan: String,             // encrypted
  aadhaar_hash: String,    // one-way hash
  name_encrypted: String,
  dob: Date,
  pep_flag: Boolean,       // Politically Exposed Person
  sanction_flag: Boolean,
  kyc_verified: Boolean,
  occupation_code: String
})

(:Transaction {
  id: String,              // UUID
  amount: Float,
  currency: String,
  channel: String,         // NEFT|RTGS|IMPS|UPI|CASH|SWIFT
  timestamp: DateTime,
  from_account: String,
  to_account: String,
  description: String,
  device_id: String,
  ip_address: String,      // hashed
  geo_lat: Float,
  geo_lon: Float,
  risk_score: Float,       // ML ensemble score
  rule_violations: [String],
  is_flagged: Boolean,
  alert_id: String
})

(:Device {
  id: String,              // device fingerprint hash
  device_type: String,
  os_version: String,
  first_seen: DateTime,
  account_count: Integer   // # accounts using this device
})

(:Alert {
  id: String,
  transaction_id: String,
  risk_score: Float,
  shap_top3: [String],
  rule_flags: [String],
  status: String,          // OPEN|INVESTIGATING|CLOSED_FRAUD|CLOSED_NORMAL
  assigned_to: String,
  created_at: DateTime,
  closed_at: DateTime
})

// RELATIONSHIP TYPES
(:Account)-[:SENT {amount, timestamp, txn_id}]->(:Account)
(:Account)-[:RECEIVED {amount, timestamp, txn_id}]->(:Account)
(:Customer)-[:OWNS]->(:Account)
(:Account)-[:USED_DEVICE {last_used}]->(:Device)
(:Device)-[:SHARED_BY]->(:Account)
(:Transaction)-[:FLAGGED_AS]->(:Alert)
(:Account)-[:LINKED_TO {reason, confidence}]->(:Account)
```

### 4.2 Cassandra Schema

```cql
CREATE TABLE transaction_by_account (
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

CREATE TABLE account_risk_history (
    account_id TEXT,
    computed_at TIMESTAMP,
    risk_score FLOAT,
    ml_score FLOAT,
    rule_flags LIST<TEXT>,
    community_id INT,
    pagerank FLOAT,
    PRIMARY KEY (account_id, computed_at)
) WITH CLUSTERING ORDER BY (computed_at DESC);
```

### 4.3 Kafka Topic Schema (Avro)

```json
// enriched-transactions topic
{
  "type": "record",
  "name": "EnrichedTransaction",
  "fields": [
    {"name": "txn_id", "type": "string"},
    {"name": "from_account", "type": "string"},
    {"name": "to_account", "type": "string"},
    {"name": "amount", "type": "double"},
    {"name": "timestamp", "type": "long"},
    {"name": "channel", "type": "string"},
    {"name": "kyc_risk_score", "type": "float"},
    {"name": "geo_risk_score", "type": "float"},
    {"name": "device_fingerprint", "type": "string"},
    {"name": "device_risk_flag", "type": "boolean"}
  ]
}
```

---

## 5. ML Pipeline Research

### 5.1 Training Data Strategy

**Labeled data sources**:
- Historical confirmed fraud cases from CBS (anonymized)
- RBI/FIU-IND public typology datasets
- Synthetic fraud generation using SMOTE for class imbalance
- Investigator feedback loop (closed cases)

**Class imbalance handling**:
- Expected fraud rate: ~0.1–0.5% of transactions
- Strategy: SMOTE on tabular features + graph-level oversampling
- Loss function: Focal loss for GNN training (γ=2 for fraud class)

### 5.2 Feature Engineering

**Graph Features (from Neo4j GDS)**:
- PageRank score (account influence in network)
- Betweenness centrality (account acts as bridge)
- Louvain community ID (cluster membership)
- Clustering coefficient (local connectivity)
- In-degree / out-degree in 24h window
- Shortest path to known fraud node

**Transaction Features**:
- Amount z-score (vs account historical mean)
- Velocity: # transactions in 1h, 6h, 24h windows
- Time-of-day encoding (cyclical sin/cos)
- Geographic distance from account's home branch
- Channel switch pattern (IMPS → UPI → NEFT in rapid succession)
- Counterparty risk score

### 5.3 SHAP Explainability

Every XGBoost prediction generates SHAP values. The top-3 contributors are:
1. Stored with the Alert record in Neo4j
2. Rendered as human-readable cards in the UI ("This account sent 8 transactions in 47 minutes")
3. Included verbatim in the STR narrative drafted by Qwen LLM
4. Used as evidence in FIU-IND compliance submission

### 5.4 Continuous Learning Loop

```
Investigator closes case
        │
        ▼
Label written to training_queue (Kafka topic)
        │
        ▼
Weekly batch: retrain GNN (PyTorch Geometric)
Daily batch:  refresh XGBoost + IF models
        │
        ▼
Model validation on held-out test set
If AUC > threshold → promote to production
MLflow model registry tracks version history
        │
        ▼
A/B shadow mode for 24h before full cutover
```

---

## 6. API & Integration Design

### 6.1 Core REST Endpoints

```
POST /api/v1/transactions/ingest        # Manual ingest (for testing)
GET  /api/v1/transactions/{id}          # Get transaction details + SHAP
GET  /api/v1/accounts/{id}/graph        # Get N-hop subgraph JSON for Cytoscape
GET  /api/v1/accounts/{id}/timeline     # Historical risk score timeline
GET  /api/v1/alerts                     # Paginated alert list (with filters)
POST /api/v1/alerts/{id}/acknowledge    # Investigator takes ownership
POST /api/v1/cases                      # Create investigation case
PUT  /api/v1/cases/{id}/close           # Close + label for retraining
POST /api/v1/reports/str/generate       # Generate STR draft
POST /api/v1/reports/str/{id}/submit    # Submit to FIU-IND FINnet 2.0
GET  /api/v1/graph/path?from=&to=       # Fund flow path between accounts
GET  /api/v1/graph/timetravel?at=       # Historical graph state at timestamp
WS   /api/v1/ws/alerts                  # WebSocket live alert stream
```

### 6.2 WebSocket Protocol

```json
// Server → Client (new alert)
{
  "type": "ALERT_FIRED",
  "alert_id": "ALT-2026-00123",
  "risk_score": 87,
  "account_id": "ACC-XXXX",
  "shap_summary": "High velocity + shared device with known fraud",
  "timestamp": "2026-04-05T14:23:01Z"
}

// Client → Server (acknowledge)
{
  "type": "ACKNOWLEDGE",
  "alert_id": "ALT-2026-00123",
  "investigator_id": "INV-042"
}
```

### 6.3 FIU-IND FINnet 2.0 Integration

```
Endpoint: POST https://finnet.fiu.gov.in/api/v2/str/submit
Auth: Mutual TLS (client certificate issued to bank)
Format: XML (FIU-IND schema) wrapped in JSON envelope
Response: {"reference_id": "STR2026XXXX", "status": "ACCEPTED"}
```

**STR XML Schema key fields**:
- `<ReportingEntity>` — Union Bank IFSC + FIU registration
- `<SubjectAccount>` — flagged account details (encrypted PAN/Aadhaar)
- `<TransactionDetails>` — list of suspicious transactions
- `<SuspicionReason>` — Qwen-drafted narrative (max 4000 chars)
- `<InvestigatorDeclaration>` — digital signature

---

## 7. Union Bank Finacle Plugin Architecture

### 7.1 Union Bank CBS Context

Union Bank of India uses **Infosys Finacle Core Banking System v10.2.x** (currently migrating to v10.2.25). This dictates the integration approach.

**Finacle Integration Ecosystem:**
| Component | Purpose | UniGRAPH Usage |
|-----------|---------|----------------|
| Finacle API Connect | BIAN-inspired REST APIs | Account/customer data queries |
| Finacle Event Hub | Kafka-based business events | Real-time transaction ingestion |
| Finacle API Hub | API orchestration & transformation | Request/response routing |
| Finacle Digital Engagement Suite | Digital banking layer | Channel-specific fraud scoring |

### 7.2 Plugin Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Union Bank of India Infrastructure              │
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐  │
│  │   Finacle    │     │        Finacle API Connect        │  │
│  │   CBS v10    │────▶│  ┌─────────┐  ┌───────────────┐  │  │
│  │  (Core DB)   │     │  │API Hub  │  │  Event Hub    │  │  │
│  └──────────────┘     │  │(REST)   │  │  (Kafka)      │  │  │
│                       └──────┬───┘  └───────┬───────┘  │  │
│                              │               │          │  │
│                    ┌─────────▼───────────────▼──────┐   │  │
│                    │     UniGRAPH Plugin Layer      │   │  │
│                    │  ┌──────────────────────────┐  │   │  │
│                    │  │  API Gateway (Kong)      │  │   │  │
│                    │  │  - OAuth 2.0 / mTLS      │  │   │  │
│                    │  │  - Rate limiting         │  │   │  │
│                    │  │  - IP whitelisting       │  │   │  │
│                    │  └────────────┬─────────────┘  │   │  │
│                    │               │                │   │  │
│                    │  ┌────────────▼─────────────┐  │   │  │
│                    │  │  UniGRAPH Fraud Engine   │  │   │  │
│                    │  │  - Real-time scoring     │  │   │  │
│                    │  │  - Graph analysis        │  │   │  │
│                    │  │  - ML ensemble           │  │   │  │
│                    │  └────────────┬─────────────┘  │   │  │
│                    └───────────────┼────────────────┘   │  │
│                                    │                     │  │
│                    ┌───────────────▼────────────────┐   │  │
│                    │  Action Enforcement Layer      │   │  │
│                    │  - POST /lien (mark lien)      │───┼──┘
│                    │  - POST /freeze (freeze acct)  │───┘
│                    │  - POST /hold (hold txn)       │
│                    └────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Real-Time Scoring API Contract

**Inbound: CBS → UniGRAPH (during payment processing)**
```
POST /api/v1/fraud/score
Headers:
  Authorization: Bearer <JWT>
  X-Request-ID: <UUID>
  X-Idempotency-Key: <UUID>
  
{
  "transactionId": "TXN-2026-UBI-00012345",
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
  "location": { "lat": 19.0760, "lon": 72.8777 },
  "referenceNumber": "REF123456789",
  "callbackUrl": "https://finacle.uboi.in/api/v1/fraud/decision"
}
```

**Outbound: UniGRAPH → CBS (scoring decision)**
```json
{
  "transactionId": "TXN-2026-UBI-00012345",
  "riskScore": 87,
  "riskLevel": "HIGH",
  "recommendation": "HOLD",
  "decisionLatencyMs": 142,
  "reasons": [
    "mule_account_match",
    "unusual_velocity_8txns_47min",
    "graph_cluster_anomaly_score_0.87",
    "shared_device_with_known_fraud"
  ],
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
  "modelVersion": "unigraph-v2.3.1"
}
```

**Recommendation Values:**
| Value | Action | Description |
|-------|--------|-------------|
| `ALLOW` | Process normally | Risk score < 60 |
| `REVIEW` | Flag for post-facto review | Risk score 60-79 |
| `HOLD` | Hold transaction for manual review | Risk score 80-89 |
| `BLOCK` | Reject transaction | Risk score ≥ 90 or known fraud pattern |

### 7.4 Action Enforcement APIs (UniGRAPH → Finacle)

```
POST /api/v1/enforcement/lien
{
  "accountId": "UBI30100012345678",
  "reason": "SUSPECTED_FRAUD",
  "alertId": "ALT-2026-00123",
  "amount": 75000.00,
  "initiatedBy": "UNIGRAPH_AUTO",
  "requiresMakerChecker": true
}

POST /api/v1/enforcement/freeze
{
  "accountId": "UBI30100012345678",
  "reason": "CONFIRMED_FRAUD",
  "caseId": "CASE-2026-00456",
  "initiatedBy": "INV-042",
  "requiresMakerChecker": true
}

POST /api/v1/enforcement/ncrp-report
{
  "complaintId": "NCRP-2026-XXXXX",
  "accountId": "UBI30100012345678",
  "action": "AUTO_LIEN_AND_FREEZE",
  "evidence": { ... }
}
```

### 7.5 NCRP/I4C Integration

RBI mandates real-time API integration with the National Cyber Crime Reporting Portal:
- Automated complaint intake from NCRP
- Auto lien marking on reported accounts
- Freeze trigger within "Golden Hour" (< 4 hours)
- Investigation initiation workflow
- Status reporting back to NCRP

### 7.6 MuleHunter.AI Compatibility

RBI's MuleHunter.AI is live in 26+ banks. UniGRAPH must:
- Accept mule account lists from MuleHunter.AI as input
- Cross-reference detected accounts with MuleHunter database
- Share anonymized fraud patterns back to RBI
- Support RBI's network analytics requirements for mule detection

### 7.7 Plugin Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| OAuth 2.0 / OIDC | Finacle API Connect token-based auth |
| mTLS | Service-to-service between Finacle ↔ UniGRAPH |
| IP Whitelisting | Only Finacle API Gateway IPs allowed |
| RBAC | Least privilege + Maker-Checker for all admin |
| MFA | Mandatory for all human access to UniGRAPH |
| DLP | Data Loss Prevention on all data flows |
| SIEM Integration | All logs → Union Bank's SOC (24×7) |
| VAPT | CERT-In empanelled auditor certification |
| Data Localization | 100% India-based infrastructure |
| HSM Integration | Cryptographic key management via bank HSM |

---

## 8. DevOps & Infrastructure

### 8.1 CI/CD Pipeline

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Code Push  │───▶│  Build &     │───▶│  Security    │───▶│  Deploy to   │
│  (Git)      │    │  Test        │    │  Scanning    │    │  Staging     │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                │
                   ┌──────────────┐    ┌──────────────┐         │
                   │  Production  │◀───│  CAB Approval│◀────────┘
                   │  Deploy      │    │  Gate        │
                   └──────────────┘    └──────────────┘
```

**Pipeline Components:**
| Stage | Tool | Purpose |
|-------|------|---------|
| Build | GitHub Actions / GitLab CI | Multi-stage Docker builds |
| SAST | SonarQube + Semgrep | Static code analysis |
| DAST | OWASP ZAP | Runtime security testing |
| Container Scan | Trivy / Grype | CVE detection in images |
| SBOM | Syft + CycloneDX | Software Bill of Materials |
| Image Signing | Cosign / Sigstore | Supply chain integrity |
| Artifact Registry | Harbor / Nexus | Versioned, scanned images |
| GitOps | ArgoCD | Declarative K8s deployment |
| DORA Metrics | Built-in | Deployment frequency, MTTR, etc. |

### 8.2 Monitoring & Observability Stack

```
┌─────────────────────────────────────────────────────────┐
│                  Observability Stack                     │
│                                                          │
│  Metrics:        Prometheus + Grafana                    │
│  Logs:           Loki + Grafana (or ELK/OpenSearch)     │
│  Traces:         Jaeger / Tempo (OpenTelemetry)         │
│  Alerts:         AlertManager → PagerDuty/OpsGenie      │
│  Synthetics:     Blackbox exporter + k6                 │
│  SLOs:           Error budgets per service              │
│                                                          │
│  Service-Specific Monitors:                              │
│  ├── Kafka:      kafka_exporter, consumer lag, URP      │
│  ├── Neo4j:      Query latency, page cache, cluster     │
│  ├── Cassandra:  nodetool metrics, compaction, latency  │
│  ├── Redis:      Memory, eviction, replication lag      │
│  ├── Flink:      Checkpoint, backpressure, watermark    │
│  └── Debezium:   Connector status, lag, schema registry │
└─────────────────────────────────────────────────────────┘
```

**SLO Targets:**
| Service | SLO | Error Budget |
|---------|-----|--------------|
| Fraud Scoring API | 99.95% availability, <200ms P99 | 21.6 min/month downtime |
| Alert WebSocket | 99.9% delivery rate | 43.2 min/month |
| ML Scoring | 99.5% within 500ms | 3.6 hours/month |
| Graph Queries | 99% within 100ms | 7.2 hours/month |
| STR Generation | 99% within 10s | 7.2 hours/month |

### 8.3 Disaster Recovery & Backup

| Component | Backup Strategy | RPO | RTO |
|-----------|----------------|-----|-----|
| Neo4j | `neo4j-admin backup` hourly + off-site | 1 hour | 15 min |
| Cassandra | Medusa incremental snapshots to S3 | 15 min | 30 min |
| Redis | RDB + AOF, Redis Sentinel across AZs | 5 min | 5 min |
| Kafka | MirrorMaker 2 cross-region replication | 0 (sync) | 10 min |
| ML Models | MLflow registry + artifact backup | N/A | 5 min |
| Config | Git repo (single source of truth) | 0 | 5 min |

**DR Runbooks Required:**
1. Neo4j cluster failover
2. Cassandra node recovery
3. Kafka cluster failover
4. Full site failover to DR DC
5. Model rollback procedure
6. Data corruption recovery

### 8.4 Production Deployment Architecture

**Move from Docker Compose (dev) to Kubernetes (prod):**

```
┌──────────────────────────────────────────────────────────┐
│              Kubernetes Cluster (On-Premise)              │
│                                                           │
│  Ingress:    NGINX Ingress Controller + WAF              │
│  Mesh:       Istio (mTLS, traffic splitting, circuit brk)│
│  Gateway:    Kong API Gateway                             │
│                                                           │
│  Namespaces:                                              │
│  ├── unigraph-ingestion   (Debezium, Flink, Kafka)       │
│  ├── unigraph-graph       (Neo4j cluster, Redis)         │
│  ├── unigraph-ml          (ML serving, GNN, XGBoost)     │
│  ├── unigraph-backend     (FastAPI, Drools)              │
│  ├── unigraph-frontend    (React static + API)           │
│  ├── unigraph-llm         (Qwen vLLM/Ollama)             │
│  ├── unigraph-monitoring  (Prometheus, Grafana, Loki)   │
│  └── unigraph-compliance  (FIU-IND, STR templates)       │
│                                                           │
│  Storage:    Persistent Volumes (Ceph/Rook for on-prem)  │
│  Secrets:    HashiCorp Vault (HA cluster)                 │
│  Registry:   Harbor (internal container registry)         │
└──────────────────────────────────────────────────────────┘
```

### 8.5 Secret Management

| Secret Type | Storage | Rotation |
|-------------|---------|----------|
| DB Credentials | HashiCorp Vault | 30 days |
| API Keys | Vault + external-secrets-operator | 90 days |
| TLS Certificates | cert-manager + Vault PKI | 90 days |
| Kafka SASL | Vault | 30 days |
| JWT Signing Key | HSM-backed Vault transit | 180 days |
| LLM API Keys | Vault | 90 days |
| FIU-IND mTLS Certs | HSM | Per FIU-IND policy |

### 8.6 Database Migration Strategy

| Database | Tool | Strategy |
|----------|------|----------|
| Neo4j | Liquigraph | Versioned Cypher migrations, CI dry-run |
| Cassandra | Custom migration runner | Expand/contract pattern, zero-downtime |
| Redis | Application-level | Cache invalidation on schema change |
| Kafka Schema | Schema Registry | BACKWARD compatibility, DLQ for failures |

### 8.7 Deployment Strategy

| Strategy | Service | Details |
|----------|---------|---------|
| Blue-Green | FastAPI, React | Full environment swap, instant rollback |
| Canary | ML Models | 1% → 5% → 25% → 50% → 100% with metric gates |
| Rolling | Kafka Consumers | Consumer group migration with dual-read |
| Feature Flags | All services | Unleash/OpenFeature for gradual rollout |

**Canary Promotion Gates:**
- Error rate < 0.1%
- P99 latency < 200ms
- No increase in false positive rate > 5%
- No degradation in fairness metrics

### 8.8 Network Security Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Network Segmentation                 │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │  DMZ Zone   │  │  App Zone   │  │  Data Zone   │ │
│  │             │  │             │  │              │ │
│  │ - API GW    │──│ - FastAPI   │──│ - Neo4j      │ │
│  │ - React CDN │  │ - Flink     │  │ - Cassandra  │ │
│  │ - WAF       │  │ - Drools    │  │ - Redis      │ │
│  │             │  │ - ML Serve  │  │ - Kafka      │ │
│  └─────────────┘  └─────────────┘  └──────────────┘ │
│                                                       │
│  Network Policies: Zero-trust, pod-to-pod mTLS       │
│  Egress: Whitelist only (FIU-IND, NCRP endpoints)    │
│  DNS: Internal CoreDNS, no external resolution       │
└──────────────────────────────────────────────────────┘
```

### 8.9 Audit Trail & Compliance Logging

| Log Type | Storage | Retention | Integrity |
|----------|---------|-----------|-----------|
| API Access Logs | Loki/Splunk | 7 years | Cryptographic signing |
| Database Audit | Immutable Cassandra table | 7 years | Append-only, no DELETE |
| ML Decision Logs | ELK + MLflow | Model lifecycle + 3 years | Hash-chained |
| LLM Prompt/Response | Encrypted S3 | 5 years | Tamper-evident |
| Drools Rule Changes | Git + audit table | Permanent | Git history |
| SIEM Events | Bank's SIEM (Splunk/QRadar) | 7 years | Per PCI-DSS Req 10 |

**Data Lineage:** OpenLineage + Marquez for tracking: CBS → Debezium → Kafka → Flink → Neo4j/Cassandra → ML → Alerts

---

## 9. Compliance & Regulatory Framework

### 9.1 RBI FREE-AI Framework (August 2025) — CRITICAL

The RBI's **Framework for Responsible and Ethical Enablement of Artificial Intelligence** is the primary regulatory document for UniGRAPH.

**7 Sutras (Guiding Principles):**
1. Trust is the Foundation
2. People First
3. Innovation over Restraint
4. Fairness and Equity
5. Accountability
6. Understandable by Design
7. Safety, Resilience and Sustainability

**Implementation Requirements:**
| Pillar | UniGRAPH Requirement |
|--------|---------------------|
| Infrastructure | India-based deployment, trustworthy data platforms |
| Policy | Board-approved AI policy per Annex V template |
| Capacity | AI literacy for investigators and compliance officers |
| Governance | AI-specific decision governance, human-in-the-loop |
| Protection | Consumer notification when AI is used, enhanced cybersecurity |
| Assurance | AI audit framework, model validation, BCP for AI degradation |

### 9.2 DPDPA 2023 Compliance

| Requirement | Implementation |
|-------------|----------------|
| Lawful basis | Consent OR legitimate use for each data point |
| Consent standards | English + 1 of 22 scheduled languages, affirmative action |
| Data Principal Rights | Access, correction, erasure, grievance, nomination |
| Security safeguards | Field-level encryption, access controls, audit logs |
| Breach notification | Notify Data Protection Board + affected individuals |
| Data erasure | Erase when purpose complete (unless PMLA retention applies) |
| SDF obligations | DPO appointment, DPIA, periodic data audits |
| Processor contracts | Third-party AI vendors must comply with DPDPA |

### 9.3 CERT-In Requirements

| Requirement | Implementation |
|-------------|----------------|
| 6-hour reporting | Automated incident detection → CERT-In notification |
| Log retention | 180 days minimum for all system logs |
| Cybersecurity audits | CERT-In empanelled auditor, annual schedule |
| Nodal officer | Designated CERT-In point of contact |
| CSIRT-FIN | Participate in financial sector threat intelligence sharing |

### 9.4 Model Risk Management

| Component | Implementation |
|-----------|----------------|
| Independent validation | Pre-deployment + annual third-party audit |
| Model lifecycle governance | Approval → Testing → Deployment → Change control |
| Model documentation | MCP (Model Context Protocol), inputs, outputs, preprocessing |
| Bias/fairness testing | Quarterly testing across demographics, geography |
| Drift monitoring | PSI > 0.2 triggers investigation, > 0.25 triggers retraining |
| Stress testing | Scenario analysis for systemic/operational resilience |
| Dataset retention | Training data retained for auditability (5+ years) |
| Reproducible pipelines | Seed management, config versioning, deterministic builds |

### 9.5 Audit Framework

| Audit Type | Frequency | Scope |
|------------|-----------|-------|
| Internal AI Audit | Quarterly | Model bias, degradation, unexplained behavior |
| Concurrent Audit | Real-time | AI-driven fraud detection decisions |
| External Audit | Annual | Third-party CERT-In empanelled auditor |
| RBI Supervision | As scheduled | On-site/off-site AI compliance review |
| VAPT | Semi-annual | CERT-In empanelled security testing |

**Audit Trail Requirements:**
- Complete trail: inputs → model version → output → human override
- Drools rule change history with versioning
- LLM prompt/response logging for STR generation
- ML model version, training data snapshot, metrics at time of each prediction

### 9.6 Incident Response Integration

**Unified Incident Response Plan:**
| Regulator | Timeline | Format |
|-----------|----------|--------|
| CERT-In | 6 hours | CERT-In incident form |
| RBI | 2-6 hours | RBI cyber incident format |
| DPDPA | As soon as practicable | Data Protection Board notification |
| FIU-IND | Per STR/CTR deadlines | FINnet 2.0 XML |
| NCRP/I4C | Immediate (Golden Hour) | NCRP API |

**AI-Specific Incident Categories:**
- Model degradation (sudden drop in precision/recall)
- False positive spike (>2x baseline)
- Adversarial attack on ML model
- Data poisoning attempt
- LLM hallucination in STR narrative
- Graph database corruption

### 9.7 Customer Transparency & Grievance

| Requirement | Implementation |
|-------------|----------------|
| AI disclosure | Privacy policy disclosure of AI-based fraud monitoring |
| Explainability | Human-readable rationale for every fraud flag |
| Human escalation | Option to request human review of AI decisions |
| Grievance channel | Dedicated AI-related complaint mechanism |
| RBI Ombudsman | Integration with RBI Integrated Ombudsman Scheme |
| TAT | Defined resolution timelines for AI-related grievances |
| Feedback loop | Grievance data → model retraining for bias reduction |

### 9.8 Data Retention Policy

| Data Category | Retention Period | Regulatory Basis |
|---------------|-----------------|------------------|
| Transaction records | 5 years | PMLA 2002 Section 12 |
| STR/CTR reports | 5 years | PMLA 2002 |
| System logs | 180 days minimum | CERT-In |
| API access logs | 7 years | PCI-DSS + banking norms |
| ML training data | Model lifecycle + 3 years | Model risk management |
| ML model artifacts | Permanent (versioned) | Audit requirements |
| LLM prompts/responses | 5 years | AI audit requirements |
| Customer personal data | Until purpose complete | DPDPA 2023 (conflicts with PMLA — legal review needed) |

---

## 10. Implementation Phases & Sprint Plan

### Phase 0: Compliance & Foundation (Weeks 0–2)
**Goal**: Regulatory alignment, infrastructure blueprint, Finacle integration setup

| Week | Tasks |
|------|-------|
| 0 | Board AI policy draft (FREE-AI Annex V), DPDPA data mapping, CERT-In nodal officer designation |
| 1 | Finacle API Connect sandbox access, Finacle Event Hub Kafka topic subscription setup, OAuth 2.0 / mTLS configuration |
| 2 | Repo setup, Docker Compose (dev), Kubernetes manifests (prod), Harbor registry, Vault deployment, CI/CD pipeline |

**Deliverable**: Compliance framework documented, Finacle integration channel established, CI/CD running.

### Phase 1: Data Pipeline + Graph Skeleton (Weeks 3–5)
**Goal**: Data flowing from Finacle → Kafka → Flink → Neo4j

| Week | Tasks |
|------|-------|
| 3 | Debezium CDC connector to Finacle DB (or mock CBS data generator for dev), Kafka topics + Schema Registry, Avro schemas |
| 4 | Flink enrichment job (mock KYC/Geo/Device stores), write enriched events to Neo4j, graph schema + indexes |
| 5 | Initial Cypher queries (2-hop, circular, mule), Drools rule engine setup with 3 core rules, Redis caching layer |

**Deliverable**: Transaction data flows from mock CBS → Kafka → Flink → Neo4j in real-time. Graph queries operational.

### Phase 2: ML Core (Weeks 6–8)
**Goal**: Working ML ensemble with SHAP, feature store, drift detection

| Week | Tasks |
|------|-------|
| 6 | Synthetic fraud dataset generation, feature store setup (Feast), GraphSAGE GNN training, baseline evaluation |
| 7 | Isolation Forest + XGBoost ensemble, SHAP + GNNExplainer integration, MLflow registry, fairness testing |
| 8 | ML scoring microservice (FastAPI), integration with graph pipeline, drift detection (PSI monitoring), shadow mode setup |

**Deliverable**: Every transaction gets 0-100 risk score with SHAP explanation. Shadow mode running alongside pipeline.

### Phase 3: Backend, Alerts & Plugin APIs (Weeks 9–12)
**Goal**: Full FastAPI backend + WebSocket alerts + Finacle plugin APIs

| Week | Tasks |
|------|-------|
| 9 | FastAPI project scaffolding, JWT + RBAC auth, all REST endpoints, Finacle fraud scoring API (`POST /fraud/score`) |
| 10 | Case management APIs, WebSocket alert stream, Redis pub/sub, enforcement APIs (lien, freeze, hold) |
| 11 | Qwen 3.5 9B setup (vLLM on-prem), LLM API wrapper, STR narrative generation endpoint, prompt templates |
| 12 | NCRP/I4C integration, MuleHunter.AI cross-reference API, audit logging pipeline, SIEM integration |

**Deliverable**: Backend API fully operational. Finacle plugin APIs ready. LLM connected. NCRP integration working.

### Phase 4: Frontend (Weeks 13–15)
**Goal**: Full investigator UI

| Week | Tasks |
|------|-------|
| 13 | React project setup, Dashboard + Alert Inbox + SHAP cards UI, real-time WebSocket feed |
| 14 | Cytoscape.js graph explorer, time-travel slider, node expansion, fund flow visualization |
| 15 | Report Studio (STR editor), AI chat assistant panel, case archive, maker-checker approval UI |

**Deliverable**: Investigators can receive alerts, investigate via graph, chat with AI, generate STR with maker-checker.

### Phase 5: Compliance, Hardening & UAT (Weeks 16–18)
**Goal**: FIU-IND integration + production hardening + UAT

| Week | Tasks |
|------|-------|
| 16 | FIU-IND FINnet 2.0 API integration, STR/CTR/CBWTR XML template engine, digital signature, DPDPA consent management |
| 17 | End-to-end load testing (860M txn/day simulation), VAPT by CERT-In auditor, DR failover testing, chaos engineering |
| 18 | UAT with Union Bank fraud investigation team, model validation by independent validator, Board AI policy sign-off |

**Deliverable**: Production-ready system. STR submission to FIU-IND working. UAT passed. Board AI policy approved.

### Phase 6: Production Rollout (Weeks 19–20)
**Goal**: Gradual production deployment with canary

| Week | Tasks |
|------|-------|
| 19 | Blue-green deployment of backend/frontend, canary ML deployment (1% → 5% → 25%), shadow-to-production comparison |
| 20 | Full cutover, monitoring dashboards live, incident response playbooks tested, handover to Union Bank ops team |

**Deliverable**: UniGRAPH live in production on Union Bank infrastructure.

---

## 11. AI Agent Development Strategy

Since development will be done using **AI agents**, here is how to structure agent tasks for maximum effectiveness:

### Agent Architecture Recommendation

Use a **multi-agent parallel development** approach with specialized agents:

```
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                    │
│   Reads this plan, breaks work into agent tasks,        │
│   tracks completion, resolves conflicts                 │
└─────────┬───────────┬──────────┬──────────┬────────────┘
          │           │          │          │
    ┌─────▼──┐  ┌─────▼──┐ ┌────▼───┐ ┌────▼────┐
    │INFRA   │  │ML      │ │BACKEND │ │FRONTEND │
    │AGENT   │  │AGENT   │ │AGENT   │ │AGENT    │
    │        │  │        │ │        │ │         │
    │Kafka   │  │GNN     │ │FastAPI │ │React    │
    │Neo4j   │  │XGBoost │ │REST API│ │Cytoscape│
    │Flink   │  │SHAP    │ │WebSocket│ │LLM Chat │
    │Drools  │  │MLflow  │ │Auth    │ │Reports  │
    └────────┘  └────────┘ └────────┘ └─────────┘
```

### Agent Task Templates

**For Infrastructure Agent**:
```
Task: Set up Docker Compose for UniGRAPH data pipeline.
Services needed: zookeeper, kafka (3 brokers), schema-registry,
debezium-connect, flink-jobmanager, flink-taskmanager,
neo4j enterprise, redis, cassandra.
Output: docker-compose.yml + init scripts + health checks.
Reference: /repo/docs/architecture.md section 3.1
```

**For ML Agent**:
```
Task: Implement GraphSAGE GNN for fraud detection.
Framework: PyTorch Geometric
Input: 2-hop subgraph from Neo4j (JSON adjacency)
Output: fraud_probability (float 0-1) + node embeddings
Training data: /data/synthetic_fraud_dataset.csv
Target: AUC > 0.92 on test set
Include: SHAP wrapper, MLflow experiment tracking
```

**For Backend Agent**:
```
Task: Implement FastAPI endpoint POST /api/v1/reports/str/generate
Logic:
  1. Fetch case details from Neo4j (account, transactions, alerts)
  2. Call Qwen LLM with STR prompt template
  3. Parse LLM response, fill FIU-IND XML template
  4. Return draft STR as JSON
Auth: Require role=COMPLIANCE_OFFICER
Tests: pytest with mock Neo4j + mock LLM
```

**For Frontend Agent**:
```
Task: Build Cytoscape.js graph explorer component in React.
Props: { caseId: string, initialGraph: GraphData }
Features:
  - Render nodes (Account, Transaction) with color by risk score
  - Click node → expand 1 hop via /api/v1/accounts/{id}/graph
  - Time-travel slider → fetch historical state
  - Right-click menu: "Flag as Suspicious", "Add Note"
  - Export as PNG button
Styling: follow UniGRAPH design system (dark theme, risk colors)
```

### Key Agent Instructions for All Tasks
1. Always write tests alongside code (pytest / vitest)
2. Never hardcode credentials — use environment variables from `.env`
3. All DB operations must use async drivers
4. Log every important operation with structured JSON logging (Pydantic)
5. Document every function with docstrings + type hints
6. Follow the existing code style in the repo before generating new code

### 8.1 Context Window Management

**Codebase Chunking Strategy:**
- Agents receive context via **dependency-graph-based retrieval**, not file dumps
- Maximum context: 80% of available window, 20% reserved for reasoning
- Priority order: (1) Interface contracts/OpenAPI specs, (2) Type definitions, (3) Related functions, (4) Test files, (5) Config files

**RAG for Codebase:**
- Build a code index (file → symbols → dependencies graph) before agent work begins
- Agents query the index for relevant context rather than reading entire files
- Use file-level summaries for navigation, function-level code for implementation

**Token Budget per Agent Task:**
| Task Type | Max Context | Reserved for Output |
|-----------|-------------|---------------------|
| Single file edit | 50% | 50% |
| Multi-file feature | 70% | 30% |
| Architecture design | 60% | 40% |
| Bug fix | 40% | 60% |

### 8.2 Inter-Agent Communication & Dependency Management

**Artifact Handoff Protocol:**
```
Agent A completes → Writes artifact to /artifacts/<agent>/<artifact-name>
                  → Updates /artifacts/registry.json with version + hash
                  → Orchestrator validates artifact against contract
                  → Orchestrator notifies dependent agents
```

**Dependency Graph (Execution Order):**
```
Week 0-2:  Orchestrator Agent (compliance docs, repo structure, CI/CD)
            │
Week 3-5:  Infra Agent (Docker, K8s, Kafka, Neo4j, Vault)  ← parallel → Compliance Agent (DPDPA mappings)
            │
Week 6-8:  ML Agent (GNN, XGBoost, SHAP, feature store)   ← parallel → Data Agent (synthetic data)
            │
Week 9-12: Backend Agent (FastAPI, plugin APIs, enforcement) ← depends on Infra + ML interfaces
            │
Week 13-15: Frontend Agent (React, Cytoscape) ← depends on Backend OpenAPI spec
            │
Week 16-18: Integration Agent (FIU-IND, NCRP, MuleHunter) + Testing Agent (E2E, load)
            │
Week 19-20: Orchestrator Agent (canary rollout, monitoring, handover)
```

**Interface Contract Registry (`/contracts/`):**
- `fraud-scoring-api.yaml` — OpenAPI spec for `POST /fraud/score`
- `enforcement-api.yaml` — OpenAPI spec for lien/freeze/hold
- `kafka-schemas/` — Avro schemas for all topics
- `neo4j-schema.json` — Graph node/relationship definitions
- `ml-scoring-protocol.json` — Input/output format for ML service

### 8.3 Code Review Process Between Agents

**Cross-Agent Review Assignments:**
| Agent's Output | Reviewed By | Focus Areas |
|----------------|-------------|-------------|
| Infra Agent (Docker/K8s) | Backend Agent | Service connectivity, env vars, health checks |
| ML Agent (models) | Backend Agent | API integration, error handling, latency |
| Backend Agent (APIs) | Infra Agent | Resource usage, scaling, security |
| Frontend Agent (UI) | Backend Agent | API contract compliance, error states |
| All agents | Orchestrator Agent | Code quality, test coverage, compliance |

**Automated Quality Gates (pre-merge):**
- Linting: ruff (Python), ESLint (TypeScript), hadolint (Docker)
- Type checking: mypy (Python), tsc --noEmit (TypeScript)
- Security: Bandit (Python), Semgrep (all), Trivy (containers)
- Test coverage: >80% for new code, >70% overall
- Performance: API response <200ms, graph query <50ms (benchmarked in CI)

**Human-in-the-Loop Review Points:**
- All database schema changes
- All ML model deployments
- All security-related code (auth, encryption, access control)
- All compliance report generation code
- All Finacle integration code

### 8.4 Integration Testing Strategy

**Contract Testing:**
- Pact tests between Frontend ↔ Backend API
- Schema Registry compatibility tests for Kafka topics
- OpenAPI spec validation for all REST endpoints

**End-to-End Test Scenarios:**
1. Transaction ingestion → Graph update → ML scoring → Alert fired → WebSocket delivery
2. Alert acknowledgment → Case creation → STR generation → FIU-IND submission
3. Finacle payment event → Fraud score → HOLD decision → Lien marking → Release
4. NCRP complaint → Auto lien → Investigation → Case closure → Model retraining

**Mock Service Strategy:**
| Agent | Mocks Needed | Implementation |
|-------|-------------|----------------|
| Frontend | All Backend APIs | MSW (Mock Service Worker) |
| Backend | Finacle CBS, Neo4j, ML service | Testcontainers |
| ML Agent | Neo4j graph data, labeled fraud data | Synthetic graph generator |
| Infra Agent | External services (FIU-IND, NCRP) | WireMock |

### 8.5 Conflict Resolution Protocol

**File Ownership Matrix:**
| File/Directory | Owner Agent | Shared With |
|----------------|-------------|-------------|
| `docker-compose.yml` | Infra Agent | Backend Agent (review only) |
| `docker/*.Dockerfile` | Infra Agent | Each service's agent |
| `backend/app/main.py` | Backend Agent | — |
| `backend/app/routers/*` | Backend Agent | — |
| `ml/models/*` | ML Agent | — |
| `frontend/src/components/*` | Frontend Agent | — |
| `contracts/*` | Orchestrator Agent | All agents |
| `docker/init-scripts/*` | Infra Agent | Backend, ML agents |
| `.github/workflows/*` | Orchestrator Agent | All agents |
| `.env.example` | Infra Agent | All agents |

**Conflict Resolution Rules:**
1. If two agents modify the same file → Orchestrator resolves using the owning agent's version as base
2. Shared config files → Orchestrator merges, agents submit PRs with descriptions
3. Contract files → Only Orchestrator Agent can modify
4. Pre-commit hook detects overlapping edits → blocks merge, notifies orchestrator

### 8.6 Branching Strategy

```
main (protected)
├── develop
│   ├── agent/infra/docker-setup
│   ├── agent/infra/k8s-manifests
│   ├── agent/ml/graphsage-model
│   ├── agent/ml/xgboost-ensemble
│   ├── agent/backend/fraud-scoring-api
│   ├── agent/backend/enforcement-apis
│   ├── agent/frontend/graph-explorer
│   └── agent/frontend/dashboard
├── release/v1.0.0
└── hotfix/*
```

**Branch Protection Rules:**
- `main`: Require 2 approvals, all CI checks pass, signed commits
- `develop`: Require 1 approval, all CI checks pass
- Agent branches: Auto-delete after merge

**PR Template for Agent Submissions:**
```
## Agent: [name]
## Task: [description]
## Files Changed: [list]
## Tests Added: [count, coverage %]
## Dependencies: [new packages]
## Breaking Changes: [yes/no + description]
## Manual Testing: [steps performed]
```

### 8.7 Progressive Disclosure of Requirements

**Context Loading Sequence for Each Agent:**
1. **Phase 1**: Architecture overview + this planning document
2. **Phase 2**: Interface contracts + data models relevant to their task
3. **Phase 3**: Specific task requirements with acceptance criteria
4. **Phase 4**: Code context (relevant files, dependencies)
5. **Phase 5**: Implementation with iterative feedback loops

**Complexity Ramping:**
- Start agents on simpler tasks (CRUD endpoints, basic Dockerfiles)
- Progress to complex tasks (graph queries, ML pipelines, real-time streaming)
- Each completed task builds context for the next

### 8.8 Quality Gates & Acceptance Criteria

**Definition of Done per Agent Type:**

| Agent Type | Acceptance Criteria |
|------------|-------------------|
| Infra Agent | All services healthy, health checks passing, monitoring dashboards populated |
| ML Agent | AUC > 0.92, fairness metrics within bounds, SHAP explanations generated, drift detection active |
| Backend Agent | All endpoints tested, <200ms P99, auth working, audit logging active, OpenAPI spec valid |
| Frontend Agent | All screens functional, WebSocket connected, graph renders, responsive, accessibility score >90 |
| Compliance Agent | All report templates valid XML, FIU-IND schema validated, DPDPA consent flow working |

**Automated Quality Checks:**
- SAST: Bandit + Semgrep, zero critical/high findings
- Container scan: Trivy, zero critical CVEs
- Dependency audit: No unapproved packages, all licenses compatible
- Performance: k6 load tests pass in CI
- Security: OWASP ZAP baseline scan, no high findings

### 8.9 Hallucination Prevention

**Library Validation:**
- All imports must exist in the project's `requirements.txt` / `package.json`
- Agent must cite documentation URL for any non-standard library usage
- Pre-commit hook validates import existence

**API Existence Verification:**
- Agent must use documented API methods only (Neo4j driver, FastAPI decorators, etc.)
- Generated code must pass type checking (mypy, tsc)
- Integration tests verify API calls against real/mock services

**Reference Documentation Requirement:**
- For non-trivial implementations, agent must include comment citing source
- Example: `# Source: https://neo4j.com/docs/cypher-manual/current/patterns/`

### 8.10 Rollback Strategy

**Automated Rollback Triggers:**
| Trigger | Action |
|---------|--------|
| Error rate > 1% for 5 minutes | Auto-rollback to previous version |
| P99 latency > 500ms for 10 minutes | Auto-scale + alert, rollback if persists |
| ML false positive rate > 2x baseline | Switch to shadow mode, alert ML team |
| Database migration failure | Auto-rollback migration, restore from backup |
| Health check failure (3 consecutive) | Remove from service, alert ops |

**Rollback Runbook:**
1. Identify affected service and version
2. `kubectl rollout undo deployment/<name> -n <namespace>`
3. Verify health checks pass
4. Run integration test suite
5. Document incident, update runbook

### 8.11 Documentation Generation

**Auto-Generated Documentation:**
- OpenAPI/Swagger specs from FastAPI (auto-generated on build)
- Architecture Decision Records (ADRs) for significant design choices
- Changelog from commit messages (conventional commits)
- Code coverage reports (published to CI artifacts)

**Agent Documentation Requirements:**
- Every new module: README with purpose, usage, dependencies
- Every API endpoint: OpenAPI docstring with request/response examples
- Every ML model: Model card with training data, metrics, limitations
- Every config file: Comment explaining purpose and valid values

### 8.12 Checkpoint & Milestone Tracking

**Milestone Gates:**
| Gate | Criteria | Blocked Agents |
|------|----------|----------------|
| Infra Ready | All Docker services healthy, K8s manifests validated | Backend, ML, Frontend |
| Contracts Signed | All OpenAPI specs reviewed, Avro schemas registered | Backend, Frontend |
| ML Baseline | GNN AUC > 0.90, XGBoost integrated | Backend (ML endpoints) |
| API Complete | All endpoints tested, auth working | Frontend |
| E2E Passing | All integration scenarios green | All agents |

**Progress Metrics:**
- Tasks completed / total tasks per phase
- Test coverage trend
- CI pass rate
- Open PR count per agent
- Blocker count and age

---

## 12. Repository Structure

```
unigraph/
├── docker/
│   ├── docker-compose.yml          # Full stack local dev
│   ├── docker-compose.prod.yml     # Production overrides
│   └── init-scripts/               # Kafka topics, Neo4j schema, Cassandra keyspaces
│
├── kubernetes/                     # NEW: Production K8s manifests
│   ├── base/                       # Kustomize base
│   ├── overlays/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── production/
│   ├── namespaces/
│   ├── helm/                       # Helm charts for complex deployments
│   └── istio/                      # Service mesh configs
│
├── contracts/                      # NEW: Interface contracts
│   ├── fraud-scoring-api.yaml      # OpenAPI spec
│   ├── enforcement-api.yaml
│   ├── kafka-schemas/              # Avro schemas
│   ├── neo4j-schema.json
│   └── ml-scoring-protocol.json
│
├── ingestion/
│   ├── debezium/
│   │   └── connector-config.json
│   ├── flink/
│   │   ├── jobs/
│   │   │   ├── TransactionEnrichmentJob.java
│   │   │   ├── AnomalyWindowJob.java
│   │   │   └── GraphFeatureJob.java
│   │   └── Dockerfile
│   └── kafka/
│       └── schemas/                # Avro schemas
│
├── graph/
│   ├── schema/
│   │   ├── nodes.cypher
│   │   ├── relationships.cypher
│   │   └── indexes.cypher
│   ├── queries/
│   │   ├── fraud_patterns.cypher
│   │   └── investigation.cypher
│   └── gds/
│       └── analytics_jobs.cypher   # PageRank, Louvain, etc.
│
├── rules/
│   ├── src/main/resources/rules/
│   │   ├── rapid_layering.drl
│   │   ├── structuring.drl
│   │   ├── round_tripping.drl
│   │   ├── dormant_awakening.drl
│   │   └── mule_network.drl
│   └── pom.xml
│
├── ml/
│   ├── data/
│   │   ├── synthetic_generator.py
│   │   └── feature_engineering.py
│   ├── features/                   # NEW: Feature store
│   │   ├── feast_repo/
│   │   └── feature_definitions.yaml
│   ├── models/
│   │   ├── graphsage/
│   │   │   ├── model.py
│   │   │   ├── train.py
│   │   │   └── evaluate.py
│   │   ├── isolation_forest/
│   │   │   └── model.py
│   │   └── xgboost_ensemble/
│   │       ├── model.py
│   │       └── shap_explainer.py
│   ├── serving/
│   │   └── ml_service.py           # FastAPI ML scoring service
│   ├── monitoring/                 # NEW: ML monitoring
│   │   ├── drift_detection.py
│   │   ├── fairness_tests.py
│   │   └── performance_dashboard.py
│   └── mlflow/
│       └── experiments/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/                 # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── transactions.py
│   │   │   ├── accounts.py
│   │   │   ├── alerts.py
│   │   │   ├── cases.py
│   │   │   ├── reports.py
│   │   │   ├── ws.py
│   │   │   ├── fraud_scoring.py    # NEW: Finacle plugin API
│   │   │   └── enforcement.py      # NEW: Lien/freeze/hold APIs
│   │   ├── services/
│   │   │   ├── neo4j_service.py
│   │   │   ├── cassandra_service.py
│   │   │   ├── redis_service.py
│   │   │   ├── llm_service.py      # Qwen 3.5 9B wrapper
│   │   │   ├── fiu_ind_service.py  # FINnet 2.0 integration
│   │   │   ├── finacle_service.py  # NEW: Finacle API Connect client
│   │   │   └── ncrp_service.py     # NEW: NCRP/I4C integration
│   │   └── auth/
│   │       └── jwt_rbac.py
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/
│   │   │   ├── AlertInbox/
│   │   │   ├── GraphExplorer/      # Cytoscape.js
│   │   │   ├── CaseDetails/
│   │   │   ├── AIAssistant/
│   │   │   └── ReportStudio/
│   │   ├── services/               # API clients
│   │   ├── hooks/                  # React Query hooks
│   │   └── store/                  # Zustand state
│   ├── package.json
│   └── vite.config.ts
│
├── llm/
│   ├── prompt_templates/
│   │   ├── str_narrative.txt
│   │   ├── case_summary.txt
│   │   └── investigator_chat.txt
│   └── ollama/
│       └── Modelfile
│
├── compliance/
│   ├── templates/
│   │   ├── str_template.xml
│   │   ├── ctr_template.xml
│   │   └── cbwtr_template.xml
│   ├── fiu_ind_client.py
│   ├── dpdpa/                      # NEW: DPDPA compliance
│   │   ├── consent_manager.py
│   │   └── data_retention.py
│   └── audit/                      # NEW: Audit framework
│       ├── audit_logger.py
│       └── model_audit.py
│
├── monitoring/                     # NEW: Observability
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   └── dashboards/
│   ├── loki/
│   │   └── loki-config.yml
│   └── alerts/
│       └── alertmanager.yml
│
├── ci-cd/                          # NEW: Pipeline definitions
│   ├── .github/workflows/
│   │   ├── build.yml
│   │   ├── test.yml
│   │   ├── security-scan.yml
│   │   ├── deploy-staging.yml
│   │   └── deploy-production.yml
│   └── scripts/
│       ├── scan-containers.sh
│       └── generate-sbom.sh
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   ├── aml_rulebook.md
│   ├── finacle_integration.md     # NEW
│   ├── compliance_framework.md    # NEW
│   ├── agent_workflow.md          # NEW
│   └── adr/                       # NEW: Architecture Decision Records
│
├── artifacts/                      # NEW: Agent artifact handoff
│   ├── registry.json
│   ├── infra/
│   ├── ml/
│   ├── backend/
│   └── frontend/
│
└── scripts/
    ├── seed_graph.py               # Load synthetic data into Neo4j
    ├── simulate_transactions.py    # Load test transaction generator
    ├── generate_str_report.py      # Test STR generation
    ├── dr-failover-test.sh         # NEW: DR testing
    └── load-test.sh                # NEW: k6 load test runner
```

---

## 13. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Neo4j performance on 40M+ nodes | Medium | High | Proper indexing, connection pooling, GDS job scheduling off-peak |
| Flink state backend OOM | Medium | High | RocksDB backend, tune managed memory, incremental checkpointing |
| Qwen LLM hallucinating STR content | Medium | Critical | Output validation schema, human review mandatory before submission |
| Debezium WAL lag on peak load | Low | High | Monitor `lag_in_milliseconds` metric, size Kafka partitions correctly |
| FIU-IND API downtime | Low | Medium | Queue STRs locally, retry with exponential backoff |
| GraphSAGE false positives | Medium | Medium | SHAP explainability + investigator feedback loop reduces over time |
| Data privacy (PAN/Aadhaar) | High | Critical | Field-level encryption, on-premise only, no cloud egress |
| Drools rule conflicts | Low | Medium | Rule unit testing suite, conflict detection in KIE Workbench |
| Finacle API version mismatch | Medium | High | Contract testing, versioned API specs, sandbox testing before integration |
| RBI FREE-AI non-compliance | Medium | Critical | Map all 26 recommendations, Board AI policy, quarterly audits |
| DPDPA consent violation | Medium | Critical (₹250Cr penalty) | Consent manager, data mapping, DPIA, erasure workflows |
| CERT-In reporting delay | Low | Critical | Automated incident detection → 6-hour notification pipeline |
| ML model adversarial attack | Low | Critical | Adversarial robustness testing, input validation, anomaly detection on features |
| Agent-generated code conflicts | High | Medium | File ownership matrix, orchestrator resolution, pre-commit overlap detection |
| Agent hallucination in critical code | Medium | High | Import validation, type checking, integration tests, documentation citations |
| Context window overflow for agents | High | Medium | RAG-based code retrieval, token budget allocation, dependency-graph chunking |
| Integration test failures across agents | High | High | Contract testing, mock services, E2E scenarios, staging environment |
| Kubernetes complexity for bank ops | Medium | Medium | Helm charts, runbooks, training, gradual K8s adoption with Docker Compose dev |
| Model drift in production | Medium | High | PSI monitoring, automated retraining triggers, shadow mode before promotion |
| Data localization breach | Low | Critical | 100% India-based infra, egress filtering, data flow audit |
| Maker-checker bypass | Low | Critical | Enforced at API level, audit trail, RBAC with dual authorization |
| GPU resource unavailability for GNN | Medium | Medium | CPU fallback path, embedding caching, batch precomputation |
| Synthetic data not representative | High | Medium | Domain expert validation, fidelity metrics, gradual real data replacement |
| Cold start for new accounts | High | Medium | Rule-based fallback for accounts <30 days, KYC risk score weighting |

---

## 11. Skill Files Required for Each Agent

This section maps every development agent to the SKILL.md files it needs to perform its tasks optimally.

### Infrastructure Agent
- **Skills needed**: Docker, Kafka, Neo4j, Cassandra, Redis, Flink config
- **Skill files**:
  - `/mnt/skills/public/pdf-reading/SKILL.md` — to read any vendor docs uploaded as PDFs
  - No specific public skill file exists for infra tooling — agent should work from Docker/Kafka/Neo4j official docs directly

### ML Agent
- **Skills needed**: Python ML, PyTorch Geometric, scikit-learn, SHAP, MLflow
- **Skill files**:
  - `/mnt/skills/public/xlsx/SKILL.md` — for reading/writing ML experiment result spreadsheets
  - `/mnt/skills/public/pdf-reading/SKILL.md` — for reading research papers on GNN fraud detection

### Backend Agent (FastAPI)
- **Skills needed**: Python async, FastAPI, Pydantic, Neo4j driver, REST API design
- **Skill files**:
  - `/mnt/skills/public/product-self-knowledge/SKILL.md` — for using the Claude/Anthropic API correctly if building any AI-powered backend features

### Frontend Agent (React)
- **Skills needed**: React, TypeScript, Cytoscape.js, Tailwind, WebSockets
- **Skill files**:
  - `/mnt/skills/public/frontend-design/SKILL.md` — **CRITICAL**: Read before building any UI component to ensure production-grade, distinctive design quality

### Documentation & Report Agent
- **Skills needed**: Technical writing, Word docs, compliance PDFs, presentations
- **Skill files**:
  - `/mnt/skills/public/docx/SKILL.md` — for generating Word documents (architecture docs, API reference)
  - `/mnt/skills/public/pdf/SKILL.md` — for generating PDF reports and compliance docs
  - `/mnt/skills/public/pptx/SKILL.md` — for generating presentation slides (demo deck)

### Data Analysis Agent
- **Skills needed**: Data exploration, CSV/XLSX analysis, feature analysis
- **Skill files**:
  - `/mnt/skills/public/xlsx/SKILL.md` — for working with transaction data spreadsheets
  - `/mnt/skills/public/file-reading/SKILL.md` — **READ FIRST** to determine correct strategy for any uploaded file type

### Compliance & STR Agent
- **Skills needed**: XML template generation, FIU-IND schema, PDF generation
- **Skill files**:
  - `/mnt/skills/public/pdf/SKILL.md` — for generating court-ready PDF evidence packages
  - `/mnt/skills/public/docx/SKILL.md` — for STR Word document drafts

---

## Quick Reference: Tech Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + TypeScript | 18+ |
| UI Library | Tailwind CSS + shadcn/ui | — |
| Graph Viz | Cytoscape.js | 3.x |
| Backend | FastAPI (Python) | 0.110+ |
| Streaming | Apache Kafka | 3.6+ |
| CDC | Debezium | 2.5+ |
| Stream Proc | Apache Flink | 1.18+ |
| Graph DB | Neo4j Enterprise | 5.x |
| Cache | Redis | 7.x |
| Time-Series | Apache Cassandra | 4.x |
| Rule Engine | Apache Drools | 9.x |
| GNN | PyTorch Geometric | 2.x |
| Ensemble | XGBoost + scikit-learn | 2.x |
| Explainability | SHAP | 0.44+ |
| Model Registry | MLflow | 2.x |
| On-Prem LLM | Qwen 3.5 9B via vLLM/Ollama | — |
| Compliance | FIU-IND FINnet 2.0 API | — |
| Auth | JWT + RBAC | — |

---

## 15. Plan Completeness Verification Checklist

### Architecture & Design
- [x] High-level system architecture with timing
- [x] 10-step transaction flow with latency targets
- [x] Component-by-component research (8 components)
- [x] Neo4j graph schema (nodes, relationships, indexes, queries)
- [x] Cassandra time-series schema
- [x] Kafka topic schema (Avro)
- [x] Redis caching strategy
- [x] Finacle CBS integration architecture
- [x] Plugin API contracts (scoring, enforcement, NCRP)
- [x] Network security architecture (DMZ, App, Data zones)
- [x] Kubernetes production deployment design

### Data Pipeline
- [x] Debezium CDC configuration
- [x] Kafka topics + Schema Registry
- [x] Flink enrichment jobs (3 jobs defined)
- [x] Graph writer service
- [x] Data quality checks
- [x] Schema evolution strategy

### ML Pipeline
- [x] GraphSAGE GNN architecture + training
- [x] Isolation Forest anomaly detection
- [x] XGBoost ensemble scoring
- [x] SHAP explainability
- [x] GNNExplainer for graph interpretability
- [x] Feature store (Feast)
- [x] Data drift detection (PSI monitoring)
- [x] Fairness/bias testing
- [x] Model registry (MLflow)
- [x] Shadow mode deployment
- [x] Canary rollout strategy
- [x] Model rollback procedure
- [x] Continuous learning loop
- [x] Training data strategy (SMOTE, focal loss)
- [x] GPU resource planning

### Backend & APIs
- [x] FastAPI REST endpoints (12+ endpoints)
- [x] WebSocket alert stream
- [x] JWT + RBAC authentication
- [x] Finacle fraud scoring API (`POST /fraud/score`)
- [x] Enforcement APIs (lien, freeze, hold)
- [x] NCRP/I4C integration
- [x] MuleHunter.AI cross-reference
- [x] Rate limiting
- [x] Audit logging

### Frontend
- [x] 7 screens defined with features
- [x] Cytoscape.js graph explorer
- [x] Time-travel slider
- [x] AI chat assistant
- [x] Report Studio (STR editor)
- [x] Maker-checker UI
- [x] Real-time WebSocket feed

### LLM Integration
- [x] Qwen 3.5 9B on-premise setup
- [x] vLLM/Ollama serving
- [x] STR narrative prompt templates
- [x] Investigator chat prompts
- [x] Output validation schema
- [x] LLM prompt/response logging

### Compliance & Regulatory
- [x] RBI FREE-AI Framework (7 Sutras, 26 recommendations)
- [x] DPDPA 2023 compliance (consent, erasure, SDF)
- [x] CERT-In 6-hour reporting
- [x] FIU-IND FINnet 2.0 integration
- [x] STR/CTR/CBWTR/NTR report types
- [x] PMLA 2002 retention
- [x] Model risk management framework
- [x] AI audit framework (internal, concurrent, external)
- [x] Incident response plan (unified across regulators)
- [x] Customer transparency & grievance
- [x] Data retention policy
- [x] Board AI policy requirement
- [x] NCRP/I4C integration
- [x] MuleHunter.AI compatibility
- [x] Data localization (100% India)

### DevOps & Infrastructure
- [x] CI/CD pipeline (build, test, scan, deploy)
- [x] SAST/DAST/Container scanning
- [x] SBOM generation
- [x] GitOps (ArgoCD)
- [x] Monitoring (Prometheus + Grafana)
- [x] Logging (Loki/ELK)
- [x] Tracing (Jaeger/Tempo)
- [x] Alerting (AlertManager → PagerDuty)
- [x] SLOs + error budgets
- [x] Disaster recovery (RPO/RTO per component)
- [x] Backup strategy
- [x] DR runbooks
- [x] Secret management (HashiCorp Vault)
- [x] Database migration strategy
- [x] Blue-green + canary deployment
- [x] Feature flags (Unleash)
- [x] Network segmentation (zero-trust)
- [x] mTLS between services

### AI Agent Workflow
- [x] Multi-agent architecture (6 agents)
- [x] Context window management (RAG, chunking, token budget)
- [x] Inter-agent communication (artifact handoff, contracts)
- [x] Dependency graph (execution order)
- [x] Cross-agent code review
- [x] Integration testing strategy
- [x] Conflict resolution (file ownership matrix)
- [x] Branching strategy
- [x] Progressive disclosure of requirements
- [x] Quality gates & acceptance criteria
- [x] Hallucination prevention
- [x] Rollback strategy
- [x] Documentation generation
- [x] Checkpoint & milestone tracking
- [x] PR templates for agents

### Testing
- [x] Unit testing (pytest, vitest)
- [x] Contract testing (Pact)
- [x] Integration testing (Testcontainers)
- [x] E2E test scenarios (4 defined)
- [x] Load testing (k6)
- [x] DR failover testing
- [x] VAPT (CERT-In auditor)
- [x] Chaos engineering
- [x] Mock service strategy

### Documentation
- [x] Architecture docs
- [x] API reference
- [x] AML rulebook
- [x] Finacle integration guide
- [x] Compliance framework
- [x] Agent workflow guide
- [x] Architecture Decision Records (ADRs)
- [x] Model cards
- [x] Runbooks

### Remaining Items (To Be Addressed During Implementation)
- [ ] Finacle v10.2.25 sandbox access and API documentation (requires Union Bank engagement)
- [ ] FIU-IND FINnet 2.0 API credentials and test environment (requires FIU-IND registration)
- [ ] Union Bank's SIEM integration details (requires bank SOC team engagement)
- [ ] HSM integration specifics (requires bank crypto team engagement)
- [ ] Board AI policy template customization (requires legal/compliance team)
- [ ] Real historical fraud data from CBS (requires data sharing agreement)
- [ ] GPU hardware procurement for on-premise Qwen LLM + GNN inference
- [ ] Union Bank brand guidelines for frontend theming
- [ ] Exact Finacle Event Hub Kafka topic names and schemas
- [ ] CERT-In empanelled auditor engagement
- [ ] Independent ML model validator engagement

---

*Document prepared for Team "Beyond Just Programming" — PSBs Hackathon IDEA 2.0, April 2026.*
*Project: UniGRAPH — AI-Powered Fund Tracking for Fraud Detection at Union Bank of India.*
