# UniGRAPH Process Finalization Plan (Discussion First)

Status: Draft v0.1 (not final)
Owner: Ojas
Last updated: 2026-04-15

Purpose:
This document is the single source of truth to stop ad-hoc fixes and lock a stable, phase-wise process.
We will finalize this only after back-and-forth decisions are captured below.

---

## 1) Back-and-Forth Discussion Log (Must Complete First)

How to use:
1. We answer one block at a time.
2. We do not move to the next phase until decisions are written here.
3. Every decision needs an owner and a done-by date.

### Round 1: Outcomes and Constraints

| Topic | Question | Your Decision | Owner | Date |
|---|---|---|---|---|
| Primary goal | Rank top 3 goals (stability, latency, 1000 tx/sec, explainability, maintainability, demo reliability, deployment readiness) | TBD | TBD | TBD |
| Non-negotiables | What must never be broken while fixing others? | TBD | TBD | TBD |
| Scope boundary | What is in scope now, and explicitly out of scope for this cycle? | TBD | TBD | TBD |
| Deadline | Is there a hard date for a stable release candidate? | TBD | TBD | TBD |
| Risk tolerance | Prefer fast iteration with some breakage, or slower hardening with strict gates? | TBD | TBD | TBD |

### Round 2: Architecture and Cleanup Decisions

| Topic | Question | Your Decision | Owner | Date |
|---|---|---|---|---|
| Canonical path | Confirm single ingest path to optimize first (CDC -> Kafka -> Flink -> bridge -> backend -> Neo4j) | TBD | TBD | TBD |
| Deprecations | Which duplicate scripts/jobs/endpoints should be removed now? | TBD | TBD | TBD |
| Docs policy | Keep only essential docs and auto-generated runbooks? | TBD | TBD | TBD |
| Feature flags | Which high-throughput flags stay permanent vs temporary? | TBD | TBD | TBD |
| Alert policy | Keep alerts on in throughput tests, or disable for clean baseline? | TBD | TBD | TBD |

### Round 3: Quality Gates

| Topic | Question | Your Decision | Owner | Date |
|---|---|---|---|---|
| Perf gate | Target throughput and latency gate for pass/fail (for example p95 <= X ms at Y tx/sec) | TBD | TBD | TBD |
| Reliability gate | What pass criteria are required (for example 0 data loss, retry budget, no partials)? | TBD | TBD | TBD |
| Test gate | Minimum test suite before merge (unit, integration, e2e, smoke)? | TBD | TBD | TBD |
| Rollback gate | What rollback path must be validated each release? | TBD | TBD | TBD |
| Observability gate | Required dashboards and alerts before sign-off? | TBD | TBD | TBD |

### Final Lock

When all rows above are filled, mark:
- Decision freeze approved: [ ]
- Process finalization approved: [ ]
- Scope freeze approved: [ ]

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

## 5) Open Decisions (Current)

1. Final target definition: is the hard target 1000 tx/sec sustained with p95 under what threshold?
2. Throughput mode policy: benchmark-only or production-safe mode?
3. Alert generation policy during perf tests: on or off?
4. Primary benchmark command set to declare pass/fail.
5. Exact list of components to deprecate in this cycle.
