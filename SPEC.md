# SPEC.md: UniGRAPH Liveops Updates

## 1. SPECIFY: The Intent and Invariants

### Core Objectives

The `feature/unigraph-liveops-updates` branch aims to:
1. **Finalize Transaction Dataset**: Ensure the transaction dataset contains realistic, varied transactions that properly exercise all fraud detection rules
2. **Verify Fraud Detection Pipeline**: Confirm the end-to-end flow from transaction -> fraud scoring -> alert creation -> Neo4j persistence works correctly
3. **Fix Frontend Integration**: Ensure all backend outputs are correctly displayed in the frontend (Alerts, Graph Explorer, Cases, etc.)

### System Invariants (Programmatic Graders)

| Invariant | Condition | Failure Mode |
|-----------|-----------|--------------|
| `risk_score` must be 0-100 | `0 <= risk_score <= 100` | Return 400 if out of range |
| `alert_id` must exist if `is_flagged=true` | `is_flagged == true => alert_id is not null` | Silent alert drop |
| Transaction timestamp must be valid ISO8601 | `datetime.parse(timestamp) !== NaN` | Reject with 422 |
| Account IDs cannot be empty | `from_account !== "" && to_account !== ""` | Return 422 |
| Alert status lifecycle | `OPEN -> INVESTIGATING -> ESCALATED` | Invalid status transitions |
| STR must be APPROVED before SUBMIT | `status !== "APPROVED" => 409 Conflict` | Attempt submission returns 409 |
| WebSocket connection requires valid investigator_id | `investigator_id.match(/^[\w-]+$/)` | Connection rejected |
| All persisted alerts must be queryable via `/alerts` | `get_alerts() returns all persisted alerts` | Frontend shows empty list |
| Graph Explorer must render for valid alert_id | `alert_id in URL => render graph` | "Missing alert id in URL" error |

### Win/Loss Conditions

| Scenario | Expected Outcome |
|----------|------------------|
| High-risk transaction (score >= 80) | Alert created, persisted in Neo4j, visible in frontend Alerts list |
| Medium-risk transaction (60 <= score < 80) | Alert created, visible in frontend |
| Low-risk transaction (score < 60) | No alert, transaction stored in Neo4j |
| Graph Explorer with valid alert_id | Renders investigation graph with nodes/edges |
| Demo mode + ML unavailable | Fallback to rule-based scoring, returns `model_version="unigraph-demo-v1.0"` |
| Transaction dataset contains fraud patterns | Alerts generated for: RAPID_LAYERING, STRUCTURING, DORMANT_AWAKENING, MULE_NETWORK, ROUND_TRIPPING |

---

## 2. PLAN: API Contracts and Architecture

### Boundary Definitions

```
┌─────────────┐    POST /transactions/ingest    ┌─────────────┐
│  External   │ ─────────────────────────────────▶│   Backend   │
│  Systems    │   {txn payload}                  │  FastAPI    │
└─────────────┘                                   └──────┬──────┘
                                                        │
                              ┌──────────────────────────┼──────────────────────────┐
                              ▼                          ▼                          ▼
                    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
                    │  fraud_scorer   │    │   neo4j_service  │    │  LLM Service    │
                    │  (Python)       │    │   (Neo4j)        │    │  (Groq/On-prem) │
                    └────────┬────────┘    └────────┬─────────┘    └────────┬────────┘
                             │                      │                      │
                             ▼                      ▼                      ▼
                    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
                    │  ML Service     │    │  Graph Storage   │    │  STR Narrative  │
                    │  (optional)     │    │  + Constraints   │    │  Generation     │
                    └─────────────────┘    └──────────────────┘    └─────────────────┘
                                                       │
                              ┌─────────────────────────┼──────────────────────────┐
                              ▼                         ▼                          ▼
                    ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
                    │   WebSocket     │    │  /alerts/*       │    │  /reports/str/* │
                    │  /ws/alerts/{id}│    │  Investigation  │    │  STR Workflow   │
                    └─────────────────┘    └──────────────────┘    └─────────────────┘
                                                            │
                                                            ▼
                                                   ┌─────────────────┐
                                                   │    Frontend    │
                                                   │   React/TS     │
                                                   └─────────────────┘
```

### Data Schemas

#### Transaction Ingest Request
```typescript
interface TransactionIngest {
  txn_id?: string;              // Optional, auto-generated if missing
  from_account: string;          // REQUIRED, non-empty
  to_account: string;           // REQUIRED, non-empty
  amount: number;               // REQUIRED, positive
  channel: string;              // Default: "IMPS"
  customer_id?: string;
  description?: string;         // Default: "Transfer"
  device_id?: string;
  is_dormant: boolean;          // Default: false
  device_account_count: number; // Default: 1
  velocity_1h: number;          // Default: 0
  velocity_24h: number;         // Default: 0
}
```

#### Transaction Ingest Response
```typescript
interface TransactionResponse {
  txn_id: string;
  from_account: string;
  to_account: string;
  amount: number;
  channel: string;
  timestamp: string;             // ISO8601
  risk_score: number;           // 0-100
  risk_level: string;           // "LOW"|"MEDIUM"|"HIGH"|"CRITICAL"
  recommendation: string;       // "ALLOW"|"REVIEW"|"HOLD"|"BLOCK"
  rule_violations: string[];    // e.g., ["STRUCTURING", "MULE_NETWORK"]
  is_flagged: boolean;
  alert_id?: string;            // Present if is_flagged=true
}
```

#### Alert
```typescript
interface Alert {
  id: string;                    // e.g., "ALT-XXXXXXXX"
  transaction_id: string;
  account_id: string;
  risk_score: number;
  risk_level: string;
  recommendation: string;
  shap_top3: string[];          // Top 3 SHAP explanations
  rule_flags: string[];         // Rule violations triggered
  status: string;              // "OPEN"|"INVESTIGATING"|"ESCALATED"
  created_at: string;          // ISO8601
  assigned_to?: string;
}
```

#### Investigation Response
```typescript
interface InvestigationResponse {
  alert: Alert;
  transaction?: Transaction;
  graph: {
    nodes: Array<{id: string; label: string; properties: Record<string, any>}>;
    edges: Array<{from: string; to: string; type: string}>;
  };
  investigation_note: string;   // LLM-generated summary
}
```

#### STR Generate Request/Response
```typescript
interface STRGenerateRequest {
  alert_id: string;
  case_notes?: string;
}

interface STRGenerateResponse {
  str_id: string;              // e.g., "STR-ALT-XXXXXXXX"
  narrative: string;            // LLM-generated STR draft
  status: string;              // "draft"
  alert_id: string;
  account_id: string;
  risk_score: number;
}
```

#### WebSocket Message
```typescript
interface WebSocketAlert {
  type: "ALERT_FIRED";
  alert: Alert;
}
```

---

## 3. TASKS: Execution Breakdown

### Phase A: Finalize Transaction Dataset

#### Task A.1: Audit Current Transaction Dataset
- **Test**: Run `scripts/ingest_sql_transactions.py` and verify counts
- **Impl**: Identify missing or malformed transactions in `transactions_inserts.sql` or `dataset_100_interconnected_txns.sql`
- **Acceptance**: At least 10 transactions with risk_score >= 60 (alert-generating)

#### Task A.2: Add Fraud Pattern Transactions
- **Test**: Add transactions that trigger each fraud typology:
  - RAPID_LAYERING: `velocity_1h >= 5`
  - STRUCTURING: `800000 <= amount <= 990000`
  - DORMANT_AWAKENING: `is_dormant = true` + high amount
  - MULE_NETWORK: `device_account_count > 3`
  - ROUND_TRIPPING: `from_account == to_account`
- **Impl**: Insert into `transactions_inserts.sql` with correct values
- **Acceptance**: Each typology triggers corresponding `rule_violation`

#### Task A.3: Verify Dataset INGEST -> NEO4J Flow
- **Test**: Call `/transactions/ingest` for each fraud pattern, verify response
- **Impl**: Run through all transactions, check Neo4j for persisted nodes
- **Acceptance**: All transactions persisted, fraud transactions have alerts

---

### Phase B: Verify Fraud Detection Pipeline

#### Task B.1: End-to-End Ingest -> Alert Flow
- **Test**: POST high-risk transaction, verify:
  - Response contains `alert_id`
  - Alert queryable via `GET /alerts/{alert_id}`
  - Alert appears in `GET /alerts/` list
- **Impl**: Fix any breaks in the flow
- **Acceptance**: 100% of transactions with risk_score >= 60 create alerts

#### Task B.2: Rule Violation Detection
- **Test**: Ingest transactions with known fraud signals, verify `rule_violations` array matches expected typologies
- **Impl**: Debug `fraud_scorer.py` rule matching
- **Acceptance**: Each fraud pattern triggers correct rule flag

#### Task B.3: WebSocket Alert Broadcasting
- **Test**: Ingest high-risk transaction, verify WebSocket receives `ALERT_FIRED` message
- **Impl**: Check `routers/ws.py` broadcast logic
- **Acceptance**: Frontend receives live alerts via WebSocket

#### Task B.4: Graph Persistence
- **Test**: After transaction ingest, query Neo4j for Account and Transaction nodes
- **Impl**: Verify `neo4j_service.create_transaction_node` and `upsert_account` work
- **Acceptance**: Nodes visible in Neo4j browser, linked via fund-flow edges

---

### Phase C: Fix Frontend Integration

#### Task C.1: Fix Graph Explorer "Missing alert id in URL"
- **Test**: Navigate to Graph Explorer with valid alert_id in URL
- **Impl**: Fix routing/logic in `frontend/src/pages/GraphExplorer.tsx`
- **Acceptance**: Graph renders for any alert_id in URL (not empty/missing)

#### Task C.2: Display Alerts List
- **Test**: Navigate to Alerts page, verify alerts from `/alerts` API are rendered
- **Impl**: Fix `frontend/src/pages/AlertsQueue.tsx` data binding
- **Acceptance**: List of alerts visible with correct data (id, account, risk_score, etc.)

#### Task C.3: Display Cases List
- **Test**: Navigate to Cases page, verify cases from `/cases` API are rendered
- **Impl**: Fix case display in frontend (or expose `/cases` endpoint if missing)
- **Acceptance**: Cases list populated

#### Task C.4: Connect Transaction Monitor
- **Test**: Transaction Monitor page shows transactions from `/transactions` API
- **Impl**: Fix `frontend/src/pages/TransactionMonitor.tsx`
- **Acceptance**: Transaction table populated with live data

#### Task C.5: Verify All Frontend Pages Have Data
- **Test**: Manual QA - visit each page, verify non-empty data displays
- **Impl**: Audit all pages (Dashboard, Alerts, Cases, Graph Explorer, STR Reports, Transaction Monitor)
- **Acceptance**: No "No data" or empty states for pages with backend data

#### Task C.6: Run Live Demo End-to-End
- **Test**: Execute `scripts/run_live_demo.py`, verify full chain:
  1. Ingest suspicious transaction
  2. Alert appears in frontend
  3. Graph Explorer shows investigation graph
  4. STR can be generated
  5. STR can be submitted
- **Impl**: Fix any failures in the chain
- **Acceptance**: Full demo flow completes successfully

---

### Test-Driven Task Template

For each task above, follow this pattern:
1. **Write Test First**: Create test that validates expected behavior
2. **Run Test**: Verify it fails (red)
3. **Implement Fix**: Write minimal code to make test pass
4. **Run Test**: Verify it passes (green)
5. **Refactor**: Clean up if needed

### Priority Order

1. **P0 (Blocking)**: Tasks A.1, A.2, A.3 - Transaction dataset must produce alerts
2. **P0 (Blocking)**: Tasks B.1, B.2 - Alerts must be created and persisted
3. **P1 (High)**: Tasks C.1, C.2, C.3 - Frontend shows alerts and cases
4. **P2 (Medium)**: Tasks C.4, C.5 - Frontend shows all data
5. **P2 (Medium)**: Tasks B.3, B.4 - WebSocket and graph persistence
6. **P3 (Low)**: Task C.6 - Full demo validation

---

## Current State Summary

| Component | Status | Issue |
|-----------|--------|-------|
| `/transactions/ingest` | Working | Needs fraud transactions in dataset |
| Alert Creation | Working | Depends on dataset |
| `/alerts` list | Not showing data | Frontend not rendering |
| `/alerts/{id}/investigate` | Returns "Missing alert id in URL" | Frontend routing issue |
| WebSocket | Likely working | Needs verification |
| Neo4j persistence | Likely working | Needs verification |
| Transaction dataset | Missing fraud patterns | Need to add |
| Frontend integration | Broken | Multiple display issues |
