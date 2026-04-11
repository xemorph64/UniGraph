# UniGraph: Single-Person Implementation Plan
## AI-Powered Fraud Detection System for FinTech Hackathon

---

## 1. The "Plugin" Positioning

**What we are building:** An AI Middleware that plugs into an existing CBS (Core Banking System) as a sidecar. It intercepts transactions, analyzes the money trail using Graph Neural Networks, and provides investigators with a visual "Money Flow" tool + LLM-generated compliance reports.

**Who we compete against:** Teams building basic ML classifiers on static CSVs.

**Our unfair advantage:**
- Graph-based detection (finds mule networks, circular flows)
- Real-time streaming pipeline
- Interactive visual investigation tool
- Auto-generated regulatory reports (STR/CTR)

---

## 2. Tech Stack (Simplified for Single Person)

| Layer | Technology | Purpose |
|-------|------------|---------|
| Data Stream | Python `asyncio` generator + `aiokafka` | Simulate CBS transactions at high speed |
| Processing | FastAPI (async) | Real-time ingestion and orchestration |
| Graph DB | Neo4j (via `neo4j` driver) | Store accounts, transactions, relationships |
| Cache/Queue | Redis | Velocity counters, pub/sub for live updates |
| ML Models | XGBoost + Isolation Forest + Graph Features | Ensemble scoring with SHAP explainability |
| LLM | Groq API (llama-3.1-70b) | Generate investigation narratives |
| UI | React + Vite + Cytoscape.js | Real-time ticker + graph explorer |

**Removed from original plan:**
- Apache Kafka (use Redis pub/sub instead for simplicity)
- Apache Flink (use Python async processing)
- Kubernetes (use Docker Compose)
- Drools (encode rules in Python)

---

## 3. Implementation Phases (Priority Order)

### Phase 1: Foundation (Day 1)
**Goal:** Get the data pipeline flowing end-to-end.

- [ ] **1.1** Set up `docker-compose.yml` with: Neo4j, Redis, PostgreSQL (optional)
- [ ] **1.2** Create `backend/app/`
  - `main.py` with FastAPI + WebSocket support
  - `config.py` for environment variables
- [ ] **1.3** Write `ingestion/simulator.py`:
  - Generate realistic transaction events
  - Inject fraud scenarios: Rapid Layering, Structuring, Mule Network
  - Publish to Redis pub/sub channel `transactions`
- [ ] **1.4** Create `backend/app/consumers/transaction_consumer.py`:
  - Subscribe to Redis `transactions`
  - Upsert Account/Transaction nodes in Neo4j
  - Compute basic velocity (5-min window) in Redis

**Deliverable:** Dashboard showing live incoming transactions.

---

### Phase 2: Graph Intelligence (Day 2)
**Goal:** Extract graph features and detect patterns.

- [ ] **2.1** Write `graph/features.py`:
  - Compute PageRank, Degree Centrality, Community ID (Louvain) via Neo4j GDS
  - Store as node properties
- [ ] **2.2** Write `graph/patterns.py`:
  - Cypher queries for: 2-hop circular flow, shared device (mule), dormant awakening
- [ ] **2.3** Write `ml/models/isolation_forest.py`:
  - Train on transaction amount, velocity, time_of_day
  - Return anomaly score (0-1)
- [ ] **2.4** Write `ml/models/xgboost_ensemble.py`:
  - Combine: Amount, Velocity, Isolation Score, Graph Features
  - Output probability + SHAP values

**Deliverable:** API endpoint `/api/v1/fraud/score` returning `{probability, shap_values, graph_evidence}`.

---

### Phase 3: The "Killer" UI (Day 3)
**Goal:** Make it look like an enterprise product.

- [ ] **3.1** Update `frontend/src/pages/Dashboard.tsx`:
  - Real-time ticker using WebSocket (`ws://localhost:8000/ws`)
  - Green/Red color coding
  - Live counter: Total Processed, Flagged, Cleared
- [ ] **3.2** Update `frontend/src/pages/GraphExplorer.tsx`:
  - Fetch 2-hop neighborhood from Neo4j
  - Render using Cytoscape.js
  - Highlight fraudulent paths in red
- [ ] **3.3** Update `frontend/src/pages/Alerts.tsx`:
  - Show list of flagged transactions
  - Expandable cards showing SHAP explainability
  - "Why flagged?" explanation text

**Deliverable:** Interactive dashboard that updates in real-time.

---

### Phase 4: The LLM Report Generator (Day 4)
**Goal:** Auto-generate regulatory reports.

- [ ] **4.1** Write `backend/app/services/llm_service.py`:
  - Prompt engineering: Input = SHAP values + Graph Path + Rule Flags
  - Output = Formatted STR (Suspicious Transaction Report)
- [ ] **4.2** Add "Generate Report" button in frontend
  - Call `/api/v1/reports/generate` with alert_id
  - Stream response from LLM

**Deliverable:** One-click generation of auditor-ready reports.

---

### Phase 5: Demo Polish (Day 5)
**Goal:** Flawless live presentation.

- [ ] **5.1** Create `scripts/demo_runner.py`:
  - Pre-loads Neo4j with "Demo Data" (known fraud patterns)
  - Starts the simulator at high speed
  - Triggers specific scenarios on demand
- [ ] **5.2** Prepare 3 test cases:
  1. **Clean Transaction**: Normal salary payment (0.02% risk)
  2. **Structuring**: 3x transactions of ₹9.5L in 1 hour (CTR evasion)
  3. **Mule Network**: Account receiving from 5 different people, sending to 1
- [ ] **5.3** Rehearse the demo flow:
  - Start services → Show ticker → Trigger Test Case 2 → Click alert → Show graph → Generate report

---

## 4. Directory Structure

```
UniGraph/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry + WebSocket
│   │   ├── config.py            # Environment config
│   │   ├── routers/             # API endpoints
│   │   ├── services/            # Neo4j, LLM, scoring
│   │   └── consumers/           # Redis consumers
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # Dashboard, Alerts, GraphExplorer
│   │   ├── components/          # RealTimeTicker, TransactionCard
│   │   └── services/            # API client
│   └── package.json
├── ml/
│   ├── models/                  # XGBoost, Isolation Forest
│   ├── data/                   # Synthetic generator
│   └── serving/                # ML scoring service
├── graph/
│   ├── schema/                  # Cypher initialization
│   ├── features/                # PageRank, Louvain, Pattern detection
│   └── queries/                 # Investigation queries
├── ingestion/
│   └── simulator.py             # CBS transaction generator
├── docker/
│   └── docker-compose.yml       # Neo4j, Redis, Backend, Frontend
└── scripts/
    ├── demo_runner.py           # One-command demo
    └── seed_demo_data.py        # Load fraud patterns
```

---

## 5. Key API Contracts

### POST /api/v1/fraud/score
**Input:**
```json
{
  "transaction_id": "TXN-12345",
  "from_account": "ACC-9876",
  "to_account": "ACC-5432",
  "amount": 950000,
  "channel": "IMPS",
  "timestamp": "2026-04-11T10:30:00Z"
}
```

**Output:**
```json
{
  "transaction_id": "TXN-12345",
  "probability": 0.94,
  "risk_level": "CRITICAL",
  "shap_values": {
    "amount": 0.32,
    "velocity_1h": 0.28,
    "graph_neighborhood": 0.25,
    "dormant_awakening": 0.09
  },
  "graph_evidence": {
    "pattern": "STRUCTURING",
    "hops": 3,
    "total_flow": 2850000
  },
  "explanation": "Transaction flagged due to structuring pattern (3 transactions near CTR threshold in 1 hour)"
}
```

### WebSocket /ws/stream
**Message:**
```json
{
  "type": "transaction",
  "data": {
    "transaction_id": "TXN-12345",
    "from_account": "ACC-9876",
    "amount": 950000,
    "risk_level": "CRITICAL",
    "timestamp": "2026-04-11T10:30:00Z"
  }
}
```

---

## 6. "God Mode" Strategy (Risk Mitigation)

Since this is a complex system running on limited hardware, prepare for failures:

1. **Pre-seeded Neo4j:** Before the demo, run `scripts/seed_demo_data.py` to load known fraud patterns.
2. **Fallback LLM:** If local Ollama is slow, use Groq API (set `LLM_PROVIDER=groq` in `.env`).
3. **Static Demo Mode:** If the live stream fails, switch the UI to "Playback Mode" showing pre-recorded transactions.

---

## 7. Success Metrics (What Judges Will See)

| Metric | Target |
|--------|--------|
| Demo Start Time | < 30 seconds |
| Prediction Latency | < 500ms per transaction |
| Fraud Detection Rate | > 95% on test cases |
| UI Responsiveness | Real-time updates (no refresh) |
| Report Generation | < 5 seconds |

---

## 8. Quick Start Commands

```bash
# Start everything
docker compose -f docker/docker-compose.yml up -d

# Seed demo data
python scripts/seed_demo_data.py

# Start backend
cd backend && uvicorn app.main:app --reload

# Start frontend
cd frontend && npm run dev

# Run transaction simulator
python ingestion/simulator.py
```

---

*Plan created: 2026-04-11*
*Branch: single-person-refactor*