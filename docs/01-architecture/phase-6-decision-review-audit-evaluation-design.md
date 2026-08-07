# Phase 6 Decision Review and Audit Evaluation Design

Status: Accepted
Date: 2026-08-07
Governed by: Issue #52
Owner acceptance: Anish Paudyal, 2026-08-07

## Purpose

Phase 6 formally evaluates the already-delivered recommendation-review,
terminal-decision, audit-history, PostgreSQL workflow-persistence, and
application-lifecycle behavior.

This design is an evaluation and governance plan. It does not authorize a new
decision workflow, authentication system, authorization model, compliance
ledger, purchasing integration, deployment system, or Phase 7 implementation.

## Gate Context

Phase 5 is Complete in the merged repository state.

Phase 6 is the Current formal gate.

The following Phase 6 capabilities were delivered before the formal gate:

- recommendation-review creation;
- immutable recommendation/evidence snapshots;
- initial `pending_review` state;
- terminal approval or rejection;
- separately recorded recommended and approved quantities;
- normalized idempotent retries;
- conflict handling for changed and opposite retries;
- ordered audit-event history;
- memory-repository concurrency protection;
- PostgreSQL workflow schema and repository;
- PostgreSQL row-lock concurrency protection;
- PostgreSQL sharing and restart durability;
- application-level PostgreSQL repository coordination and lifecycle ownership.

Early delivery is not equivalent to formal phase completion. Issue #52 must
evaluate this behavior against the accepted Phase 6 exit criteria.

## Existing Architecture Reused

Phase 6 evaluation reuses the architecture already governed by:

- ADR-0004: Co-locate Recommendation Workflow State and Audit Events;
- ADR-0005: Use SQLAlchemy and Alembic for PostgreSQL Persistence;
- the accepted PostgreSQL recommendation-workflow persistence design;
- Alembic revision `0006_workflow_persistence`;
- the `RecommendationWorkflowRepository` protocol;
- the in-memory workflow repository;
- the PostgreSQL workflow repository;
- the existing application factory and dependency-injection boundaries.

No new ADR is required for this evaluation design because it does not change a
public API, persistence schema, transaction boundary, security boundary,
dependency choice, deployment architecture, or ownership model.

If implementation discovers that one of those architectural boundaries must
change, work must stop and the change must be separately reviewed before it is
implemented.

## Inspection Findings

Repository inspection under Issue #52 established that:

1. Review and decision domain objects are frozen and slotted.
2. Only actionable positive reorder recommendations can create reviews.
3. New reviews begin in `pending_review` with no decision.
4. Approval and rejection create immutable terminal review values rather than
   mutating the original review object.
5. Identical normalized retries return the previously stored terminal state.
6. Changed or opposite retries raise a typed conflict.
7. Audit history begins with sequence 1 `review_created`.
8. A successful terminal transition adds exactly one sequence 2 terminal event.
9. Memory-mode workflow writes are protected by one `RLock`.
10. PostgreSQL terminal transitions lock the review row with `FOR UPDATE`.
11. PostgreSQL persists decision, review status/linkage, and terminal audit
    event in one session transaction.
12. PostgreSQL code rolls back SQLAlchemy failures before re-raising them.
13. Audit retrieval orders by authoritative `sequence_number`.
14. PostgreSQL schema tests verify relational, uniqueness, and event-shape
    constraints.
15. Existing PostgreSQL integration tests exercise retry, conflict, concurrency,
    shared-state, and restart behavior.
16. Application tests cover shared session-factory construction and engine
    disposal/ownership behavior.
17. Existing focused Phase 6 domain/repository/API/mapping tests pass.

The inspection baseline was:

- 106 focused tests passed;
- 1 known non-blocking Starlette/FastAPI TestClient deprecation warning;
- no worktree changes after inspection.

## Evaluation Principle

Phase 6 has two materially different evidence types:

1. **Deterministic workflow-policy conformance**
2. **Backend and lifecycle integration guarantees**

They must not be conflated.

A deterministic in-process evaluator can prove stable workflow-policy behavior
for governed fixtures. It cannot, by itself, prove PostgreSQL transaction
atomicity, row locking, cross-application sharing, restart durability, or
resource lifecycle behavior.

Therefore Phase 6 uses a layered evidence model.

## Evidence Layer A — Deterministic Workflow Conformance

Add a small deterministic evaluator under:

```text
src/opsmind/evaluation/phase6/
├── __init__.py
├── __main__.py
├── scenarios.py
├── evaluation.py
└── reporting.py
```

The evaluator must reuse the existing production domain and in-memory workflow
repository. It must not duplicate the transition rules.

The governed dataset identifier is:

`phase6-synthetic-v1`

All identifiers and timestamps are fixed constants. The evaluator must not use
the system clock, randomness, environment-dependent ordering, or generated
UUIDs in governed output.

### Canonical fixture

Use one fixed actionable `ReorderRecommendation` snapshot with:

- fixed recommendation UUID;
- fixed product UUID;
- fixed unit of measure;
- deterministic forecast method;
- fixed cutoff and training dates;
- fixed evidence fields;
- recommended reorder quantity `19`.

The evaluator is testing Phase 6 workflow behavior, not recalculating Phase 4 or
Phase 5 arithmetic. The recommendation fixture is therefore an explicit,
governed input.

The complete recommendation/evidence snapshot must be represented in a stable
signature so transitions can prove that Phase 6 preserves it unchanged.

## Governed Scenario Families

The deterministic evaluator must cover at least the following scenarios.

### 1. Pending review creation

Create one actionable review.

Expected:

- status `pending_review`;
- decision absent;
- one `review_created` audit event;
- audit sequence `(1,)`;
- recommendation/evidence snapshot unchanged.

### 2. Approval using recommended quantity

Approve a pending review without supplying an override quantity.

Expected:

- status `approved`;
- approved quantity equals recommended quantity `19`;
- recommendation remains unchanged;
- audit sequence `(1, 2)`;
- second event is `recommendation_approved`.

### 3. Approval with explicit positive override

Approve with a fixed positive override different from `19`.

Expected:

- recommended quantity remains `19`;
- approved quantity equals the explicit override;
- the recommendation snapshot is unchanged;
- terminal audit evidence records the approved quantity.

This proves recommended quantity and approved quantity are distinct facts.

### 4. Rejection with normalized reason

Reject a pending review using actor/reason strings with surrounding whitespace.

Expected:

- status `rejected`;
- approved quantity absent;
- normalized nonblank reason preserved as the decision note;
- second event is `recommendation_rejected`.

### 5. Identical normalized approval retry

Retry an existing approval with:

- a new candidate decision UUID;
- a new candidate event UUID;
- a different candidate timestamp;
- semantically identical normalized actor, quantity, and note.

Expected:

- stored review remains unchanged;
- original decision identity/time remain authoritative;
- history remains exactly two events;
- no candidate retry identity is appended.

### 6. Changed approval retry

Retry an approved review with changed actor, quantity, or note.

Expected:

- typed conflict;
- stored review unchanged;
- stored audit history unchanged.

### 7. Identical normalized rejection retry

Retry an existing rejection with new candidate IDs/time but the same normalized
actor and reason.

Expected:

- original terminal review remains authoritative;
- history remains exactly two events;
- no duplicate terminal event.

### 8. Changed rejection retry

Retry a rejected review with a changed actor or reason.

Expected:

- typed conflict;
- review and history remain unchanged.

### 9. Rejection after approval

Attempt rejection after a successful approval.

Expected:

- typed conflict;
- approval remains authoritative;
- no additional event.

### 10. Approval after rejection

Attempt approval after a successful rejection.

Expected:

- typed conflict;
- rejection remains authoritative;
- no additional event.

### 11. Same-timestamp authoritative ordering

Use equal creation and decision timestamps.

Expected:

- ordering remains sequence `(1, 2)`;
- timestamp ties do not reorder history.

### 12. Memory isolation and restart volatility

Create state in one in-memory repository and construct a separate repository.

Expected:

- first repository retains its workflow;
- second repository cannot retrieve it.

This is the governed representation of supported memory isolation and
restart-volatility semantics.

## Independent Expected Outcomes

The evaluator must not use the production transition implementation as the
source of expected outcomes.

Each scenario definition must independently declare the public result it
expects, such as:

- expected final review status;
- expected decision type;
- expected recommended quantity;
- expected approved quantity;
- expected event count;
- expected sequence numbers;
- expected event types;
- whether a conflict is expected;
- whether the pre-transition review/history must remain unchanged.

Production functions and repositories execute the scenario. The scenario
definition supplies the oracle.

## Deterministic Conformance Invariants

Every governed run evaluates these invariants where applicable.

### Snapshot preservation

The recommendation and supporting evidence stored at review creation must remain
exactly unchanged through:

- retrieval;
- approval;
- rejection;
- identical retries;
- failed changed retries;
- failed opposite retries.

### Pending-state invariant

A new review must have:

- `pending_review` status;
- no terminal decision;
- exactly one sequence-1 creation event.

### Terminal-cardinality invariant

A terminal workflow must contain:

- exactly one terminal decision;
- exactly one terminal audit event;
- exactly two total audit events.

### Status/decision alignment

- `approved` review -> approved decision -> approval event.
- `rejected` review -> rejected decision -> rejection event.
- `pending_review` -> no decision -> creation event only.

### Retry-idempotency invariant

A normalized identical retry must not change:

- authoritative decision UUID;
- authoritative decision timestamp;
- review content;
- event count;
- event UUIDs;
- event order.

### Conflict-no-mutation invariant

A changed or opposite terminal retry must:

- raise the expected conflict;
- leave the authoritative review unchanged;
- leave history unchanged.

### Audit-order invariant

Audit `sequence_number` must be contiguous and authoritative:

- pending: `(1,)`;
- terminal: `(1, 2)`.

Equal timestamps must not affect order.

### Memory-isolation invariant

Independent in-memory repository instances must not share workflow state.

## Deterministic Evaluation Output

The CLI is:

```bash
uv run python -m opsmind.evaluation.phase6   --output-dir /tmp/opsmind-phase6-evaluation
```

It writes:

```text
phase6-evaluation.json
phase6-evaluation.md
```

The CLI must:

- refuse accidental overwrite unless the repository's existing evaluation
  convention explicitly permits it;
- use stable output ordering;
- exit `0` when all governed scenarios pass;
- exit nonzero when a scenario or invariant fails;
- avoid embedding run timestamps or machine-specific paths in governed output.

The JSON and Markdown artifacts from two independent runs must be byte-identical.

## Deterministic Evaluation Summary

The durable summary must include:

- dataset version;
- scenario count;
- passed scenarios;
- failed scenarios;
- approval scenarios;
- rejection scenarios;
- idempotent retry scenarios;
- expected conflict scenarios;
- snapshot-preservation failures;
- terminal-cardinality failures;
- retry-idempotency failures;
- conflict-mutation failures;
- audit-order failures;
- memory-isolation failures;
- per-scenario result and evidence.

A successful deterministic governed run requires every failure count to be zero.

## Evidence Layer B — PostgreSQL Integration

PostgreSQL claims must come from real PostgreSQL integration tests, not from the
in-process evaluator.

At minimum, the Phase 6 validation matrix must execute and record evidence from:

```text
tests/integration/postgresql/test_workflow_schema.py
tests/integration/postgresql/test_workflow_constraints.py
tests/integration/postgresql/test_workflow_repository.py
tests/integration/postgresql/test_application_postgresql.py
```

The durable Phase 6 report must map individual Phase 6 exit criteria to the
specific integration behaviors that prove them.

### PostgreSQL schema and relational constraints

Evidence must cover:

- workflow tables and expected columns;
- supported review and decision states;
- decision-shape constraints;
- event-shape constraints;
- positive quantity constraints;
- creation-event sequence requirements;
- terminal-event sequence requirements;
- review/decision linkage;
- event/review linkage;
- uniqueness enforcing one authoritative decision/event identity and ordered
  per-review history.

### PostgreSQL transaction atomicity

Evidence must establish that review state, decision state, and the matching
terminal audit event do not become partially authoritative.

Before adding new tests, inspect the exact existing repository integration test
bodies.

If the existing suite directly forces a failure after part of a terminal
transition has been prepared and proves rollback leaves the prior workflow
unchanged, reuse that evidence.

If that direct failure-path evidence does not exist, add one narrowly scoped
PostgreSQL integration test that forces a terminal persistence failure and proves:

- the review remains pending;
- no terminal decision becomes authoritative;
- no terminal audit event is appended;
- a subsequent valid terminal transition can still succeed.

Do not alter production transaction behavior merely to make this test easier.

### PostgreSQL idempotency and conflict behavior

Evidence must cover:

- identical approval retry changes nothing;
- identical rejection retry changes nothing;
- changed approval retry conflicts without mutation;
- changed rejection retry conflicts without mutation;
- rejection after approval conflicts without mutation;
- approval after rejection conflicts without mutation.

### PostgreSQL concurrency

Use the existing real PostgreSQL one-winner test as the governed concurrency
evidence.

Required result:

- one concurrent terminal transition wins;
- one conflicting terminal transition loses;
- one authoritative terminal decision remains;
- one sequence-2 terminal audit event remains;
- history remains `(1, 2)`.

Do not generalize this result into a claim about arbitrary distributed systems,
all transaction isolation levels, or production-scale concurrency.

### PostgreSQL sharing and restart durability

Use application-level real PostgreSQL integration tests to establish:

- workflow state is visible through a later application instance using the same
  database;
- approved workflows survive application restart;
- rejected workflows survive application restart;
- audit history survives restart;
- identical retries remain idempotent after restart;
- conflicting retries remain non-mutating after restart.

This evidence is for the supported PostgreSQL configuration used by the test
suite. It is not a backup, HA, disaster-recovery, or production-availability
claim.

## Evidence Layer C — Application Ownership and Lifecycle

The Phase 6 validation matrix must explicitly include application-factory tests
covering PostgreSQL repository construction and lifecycle behavior.

Evidence must establish that:

- when the application creates PostgreSQL infrastructure, the operational and
  workflow repositories use the intended shared application-created session
  factory;
- application-owned engine infrastructure is disposed during application
  shutdown;
- explicitly injected repositories/resources remain caller-owned;
- application shutdown does not dispose resources it does not own.

No ownership claim beyond the tested application-factory behavior is allowed.

## Evidence Layer D — Security and Compliance Limitations

The durable Phase 6 report and review must explicitly retain these limitations:

- `decided_by` is caller supplied;
- `decided_by` is unverified;
- there is no user authentication;
- there is no role-based authorization;
- there is no verified reviewer identity;
- audit actor identity can be spoofed by a caller;
- audit events are not cryptographically signed;
- audit events are not hash chained;
- storage is not tamper-evident;
- there is no compliance-ledger guarantee;
- there is no approved retention/compliance policy;
- approval does not create a purchase order;
- approval does not perform an external business action;
- approval does not reserve or mutate inventory;
- there is no Phase 7 security-hardening claim;
- there is no deployment or production-readiness claim.

A successful Phase 6 review does not erase these limitations.

## Claims We May Make After a Passing Gate

If all governed evidence passes, Phase 6 may claim:

- deterministic review-state transition conformance;
- immutable recommendation/evidence preservation through supported workflow
  operations;
- normalized retry idempotency;
- conflict-without-mutation behavior;
- deterministic sequence-based audit ordering;
- one-winner behavior in the governed memory and PostgreSQL concurrency tests;
- atomic workflow persistence for the specifically tested PostgreSQL
  transaction behaviors;
- supported PostgreSQL sharing and restart durability demonstrated by the
  integration suite;
- supported memory isolation and restart volatility;
- tested application resource-ownership behavior.

## Claims We Must Not Make

Phase 6 must not claim:

- authenticated reviewer identity;
- authorized reviewer roles;
- non-repudiation;
- cryptographic integrity;
- tamper-proof or tamper-evident storage;
- compliance certification;
- regulatory ledger status;
- exactly-once distributed processing;
- arbitrary distributed-system correctness;
- disaster recovery;
- backup or replication guarantees;
- high availability;
- production-scale concurrency;
- purchase-order execution;
- inventory mutation;
- external ordering;
- production security;
- production readiness.

## Test Strategy

### Focused deterministic evaluator tests

Add focused tests for:

- dataset determinism and unique scenario names/IDs;
- all governed scenario outcomes;
- snapshot preservation;
- approved-vs-recommended quantity distinction;
- approval retry idempotency;
- rejection retry idempotency;
- changed retry conflict behavior;
- opposite retry conflict behavior;
- timestamp-tie sequence ordering;
- memory isolation;
- report determinism;
- CLI output and overwrite behavior;
- evaluator detection of a corrupted expected outcome.

### Existing Phase 6 tests

Re-run existing:

```text
tests/unit/test_recommendation_review_domain.py
tests/unit/test_recommendation_audit_domain.py
tests/repositories/test_recommendation_workflow_repository.py
tests/api/test_recommendation_reviews.py
tests/unit/test_postgresql_workflow_mappings.py
tests/unit/test_application.py
```

### Real PostgreSQL validation

Use the repository's isolated test database procedure and run:

```text
tests/integration/postgresql/test_workflow_schema.py
tests/integration/postgresql/test_workflow_constraints.py
tests/integration/postgresql/test_workflow_repository.py
tests/integration/postgresql/test_application_postgresql.py
```

Then run the complete PostgreSQL integration suite and complete
PostgreSQL-backed repository suite.

### Repository-wide gates

Run:

- Ruff format;
- Ruff lint;
- mypy;
- full test suite;
- `git diff --check`;
- two independent Phase 6 evaluator runs;
- byte comparison of JSON artifacts;
- byte comparison of Markdown artifacts;
- SHA-256 of reviewed artifacts;
- documentation consistency checks.

## Evaluation Evidence Classification

The final report must label evidence by source:

- **Deterministic evaluator** — policy and memory-mode conformance.
- **Domain/repository/API tests** — contract and transition behavior.
- **PostgreSQL schema/constraint tests** — relational integrity.
- **PostgreSQL repository tests** — transaction, retry, conflict, ordering, and
  concurrency behavior.
- **PostgreSQL application tests** — sharing and restart durability.
- **Application unit tests** — infrastructure ownership and disposal.
- **Documentation review** — explicit security/compliance limitations.

This prevents one evidence type from being overstated as proving another.

## Durable Evidence

After implementation and validation, create:

```text
docs/05-evaluation/phase-6-decision-review-audit-evaluation.md
```

It must record:

- design status and owner acceptance;
- dataset version;
- deterministic scenario results;
- invariant results;
- reproducibility hashes;
- exact focused-test results;
- exact PostgreSQL integration-test results;
- exact full-suite results;
- Alembic revision;
- concurrency result;
- restart/durability result;
- ownership/disposal result;
- security/compliance limitations;
- known warnings;
- interpretation boundaries.

Raw generated evaluation artifacts remain outside version control.

## Phase 6 Review

After the technical evidence is complete, create:

```text
docs/12-phase-reviews/phase-6-review.md
```

The initial review must remain `Proposed`.

It must map every Phase 6 exit criterion to explicit evidence.

The owner must choose:

- `Proceed`;
- `Revise`; or
- `Stop`.

Phase 6 must not be marked Complete until the review is owner accepted.

Phase 7 must not be marked Current in canonical repository status until the
accepted Phase 6 change is merged.

## Architecture Decision Assessment

No new ADR is proposed.

The evaluation is intentionally verifying ADR-0004 and ADR-0005 behavior rather
than changing those decisions.

A new ADR becomes necessary only if Issue #52 discovers a need to change, for
example:

- workflow/audit transaction ownership;
- state-machine semantics;
- persistence technology;
- public workflow API;
- actor/security boundary;
- audit-integrity model;
- application resource ownership.

## Owner Acceptance

The repository owner accepted this design on 2026-08-07 and approved implementation under Issue #52.

Accepted statement:

`I accept the Phase 6 decision review and audit evaluation design and approve implementation under Issue #52.`
