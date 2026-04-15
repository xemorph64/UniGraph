# UniGRAPH Process Finalization Plan (Discussion First)

Status: Finalized v1.0 (implementation in progress)
Owner: Ojas
Last updated: 2026-04-15

Purpose:
This document is the single source of truth to stop ad-hoc fixes and lock a stable, phase-wise process.
All decision rows below are locked and implementation must follow them.

---

## 1) Back-and-Forth Discussion Log (Must Complete First)

How to use:
1. We answer one block at a time.
2. We do not move to the next phase until decisions are written here.
3. Every decision needs an owner and a done-by date.

### Round 1: Outcomes and Constraints

| Topic | Question | Your Decision | Owner | Date |
|---|---|---|---|---|
| Primary goal | Rank top 3 goals (stability, latency, 1000 tx/sec, explainability, maintainability, demo reliability, deployment readiness) | 1) Fraud-detection correctness, 2) Low-latency E2E performance, 3) Stability and reliability | Ojas | 2026-04-15 |
| Non-negotiables | What must never be broken while fixing others? | Ingestion -> graph database -> rules + machine learning evaluation -> display on frontend | Ojas | 2026-04-15 |
| Scope boundary | What is in scope now, and explicitly out of scope for this cycle? | In scope: full CDC -> Kafka -> Flink -> bridge -> backend -> Neo4j -> frontend path with strict ML+rules, latency/recall gates, observability, rollback drill. Out of scope: new model architecture changes, UI redesign, Kubernetes production rollout. | Ojas | 2026-04-15 |
| Deadline | Is there a hard date for a stable release candidate? | Today | Ojas | 2026-04-15 |
| Risk tolerance | Prefer fast iteration with some breakage, or slower hardening with strict gates? | Slower hardening with strict gates (end-to-end working, no in-between process skipped) | Ojas | 2026-04-15 |

### Round 2: Architecture and Cleanup Decisions

| Topic | Question | Your Decision | Owner | Date |
|---|---|---|---|---|
| Canonical path | Confirm single ingest path to optimize first (CDC(Debezium) -> Kafka -> Flink -> bridge -> backend -> Neo4j) | Yes. Full workflow is mandatory with both ML and rules evaluation included. | Ojas | 2026-04-15 |
| Deprecations | Which duplicate scripts/jobs/endpoints should be removed now? | Deprecate scripts/ingest_sql_transactions.py, scripts/seed_graph.py, scripts/sync_550.py with integrity checks before removal. | Ojas | 2026-04-15 |
| Docs policy | Keep only essential docs and auto-generated runbooks? | Yes. Keep canonical runbook and archive non-canonical docs. | Ojas | 2026-04-15 |
| Feature flags | Which high-throughput flags stay permanent vs temporary? | High-throughput flags are benchmark-only. Release validation must disable throughput shortcuts and require ML. | Ojas | 2026-04-15 |
| Alert policy | Keep alerts on in throughput tests, or disable for clean baseline? | Keep alerts on. Fraudulent transaction detection is the core feature. | Ojas | 2026-04-15 |

### Round 3: Quality Gates

| Topic | Question | Your Decision | Owner | Date |
|---|---|---|---|---|
| Perf gate | Target throughput and latency gate for pass/fail (for example p95 <= X ms at Y tx/sec) | End-to-end p95 <= 300ms and p99 <= 600ms at 5k tx/sec sustained for 10 minutes. | Ojas | 2026-04-15 |
| Reliability gate | What pass criteria are required (for example 0 data loss, retry budget, no partials)? | No data loss/partials, no orphan graph entities, and both ML+rules executed per transaction in release-validation profile. | Ojas | 2026-04-15 |
| Test gate | Minimum test suite before merge (unit, integration, e2e, smoke)? | E2E is mandatory, with targeted unit tests for strict profile behavior. | Ojas | 2026-04-15 |
| Rollback gate | What rollback path must be validated each release? | One-command revert to last known stable compose tag plus post-rollback data integrity check. | Ojas | 2026-04-15 |
| Observability gate | Required dashboards and alerts before sign-off? | Mandatory: p95/p99 latency and error alerts, Kafka/Flink lag visibility, ML scoring-mode/fallback metric, and per-run end-to-end trace artifact. | Ojas | 2026-04-15 |

### Final Lock

When all rows above are filled, mark:
- Decision freeze approved: [x]
- Process finalization approved: [x]
- Scope freeze approved: [x]

---

## 2) Phase-Wise Execution Plan (To Run After Decision Freeze)

Note: Each phase has strict entry and exit criteria to prevent "fix one, break ten" behavior.

## Phase 0 - Baseline and Freeze

Goal:
Create a reproducible baseline and freeze changing requirements.

Steps:
1. Capture current architecture and active runtime path.
2. Snapshot current benchmark numbers for ingest and full pipeline.
3. Freeze scope with explicit in-scope and out-of-scope list.
4. Freeze branch strategy and merge policy.

Deliverables:
- Baseline metrics file (throughput, p50/p95/p99, error rate).
- Scope freeze section completed in this document.
- Risk register initialized.

Exit criteria:
- Everyone agrees on target metrics and constraints.
- No unresolved scope decisions.

## Phase 1 - Cleanup and Simplification

Goal:
Remove dead code paths, duplicate scripts, and stale docs.

Steps:
1. Inventory duplicate runtime paths and overlapping scripts.
2. Remove or deprecate non-canonical code paths.
3. Remove obsolete docs and keep one canonical runbook.
4. Add a quick integrity check to ensure no critical path is removed.

Deliverables:
- Deleted/replaced asset list with reason.
- Canonical path map.
- Updated minimal docs.

Exit criteria:
- No duplicate runtime entrypoints for the same responsibility.
- All core commands are documented and tested once.

## Phase 2 - Contract Hardening

Goal:
Stabilize interfaces so schema and parsing changes do not ripple unpredictably.

Steps:
1. Define strict contracts for Kafka event fields and backend ingest payloads.
2. Add compatibility handling only where mandatory and document it.
3. Add validation at boundaries (bridge, API, scorer input).
4. Version contracts and enforce compatibility checks.

Deliverables:
- Contract definitions and validation rules.
- Error handling matrix for malformed and missing fields.

Exit criteria:
- No unvalidated payload enters core scoring/persistence path.
- Contract changes require explicit version update.

## Phase 3 - Reliability First

Goal:
Stop cascading failures with deterministic recovery and retries.

Steps:
1. Define retry policies, timeout budgets, and backpressure behavior.
2. Add idempotency guarantees for ingest and write operations.
3. Add startup/readiness sequencing checks for Kafka, Flink, backend, Neo4j.
4. Run failure injection tests (service down, lag spikes, restart loops).

Deliverables:
- Retry/backpressure policy file.
- Failure playbook and recovery runbook.

Exit criteria:
- Recovery from known failures is automated or one-command.
- No manual multi-step firefight needed for common incidents.

## Phase 4 - Performance Optimization

Goal:
Reach agreed throughput and latency targets without sacrificing reliability.

Steps:
1. Profile and remove top bottlenecks in scoring and persistence.
2. Tune batch size, concurrency, and worker counts with controlled experiments.
3. Separate throughput profile from full-fidelity profile using clear flags.
4. Validate sustained load, not only burst load.

Deliverables:
- Performance experiment matrix and chosen operating point.
- Benchmark report with confidence runs.

Exit criteria:
- Meets agreed perf gate and reliability gate simultaneously.
- Results reproducible with one benchmark command set.

## Phase 5 - Verification and Release Control

Goal:
Prevent regressions and keep the system stable after release.

Steps:
1. Define mandatory CI checks and branch protections.
2. Lock test pyramid minimums (unit, integration, e2e).
3. Add release checklist and rollback drill.
4. Add post-release monitoring and ownership rotation.

Deliverables:
- CI gate list.
- Release and rollback checklist.
- Monitoring ownership map.

Exit criteria:
- Every merge passes required gates.
- Rollback tested and documented.

---

## 3) Anti-Chaos Rules (Always On)

1. No fix without a reproducible failing case.
2. No optimization without baseline and after-metric.
3. No new path until old duplicate path is removed or explicitly retained.
4. No schema change without contract versioning.
5. No merge if reliability gate fails, even if throughput improves.

---

## 4) Weekly Cadence

1. Monday: choose one phase focus and lock it.
2. Mid-week: review metrics and blocker burn-down.
3. Friday: decide promote, hold, or rollback.

Meeting outputs each week:
- What changed
- What broke
- Why it broke
- What prevents recurrence

---

## 5) Closed Decisions (Locked 2026-04-15)

1. Hard target: end-to-end p95 <= 300ms and p99 <= 600ms at 5k tx/sec sustained for 10 minutes.
2. Throughput mode policy: benchmark-only, never used as release sign-off evidence.
3. Alert generation policy during perf tests: alerts remain enabled.
4. Primary pass/fail path: CDC path (Postgres -> Debezium -> Kafka -> Flink -> bridge -> backend -> Neo4j -> frontend).
5. Deprecation list this cycle: scripts/ingest_sql_transactions.py, scripts/seed_graph.py, scripts/sync_550.py.
6. Dataset policy: do not use dataset_550.sql or dataset_550_normal_txns.sql for active validation; use dataset_100_interconnected_txns.sql and dataset_200_interconnected_txns.sql.
