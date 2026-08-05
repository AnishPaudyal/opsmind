# Roadmap Phase Reconciliation

Investigation issue: #44
Investigation date: 2026-08-04
Repository baseline: `d832fba`
Status: Accepted by repository owner
Owner decision date: 2026-08-04

## 1. Purpose

This investigation reconciles OpsMind's original phase-gated roadmap with the implementation history merged through PR #43.

The repository has delivered substantially more capability than the roadmap status table and several status documents currently acknowledge. The goal is not to rewrite Git history or pretend that implementation occurred in a different order. The goal is to establish one truthful mapping between:

* the roadmap's intended capability phases;
* merged issues and pull requests;
* architecture decisions;
* Alembic migrations;
* automated validation;
* current limitations;
* the next phase that governance permits.

## 2. Investigation Decision

Decision: **Revise**

Use a hybrid reconciliation:

1. Preserve the original Phase 0 through Phase 12 capability structure.
2. Preserve the actual chronological issue, pull-request, ADR, migration, and commit history.
3. Map completed work retrospectively to the roadmap phase whose capability it primarily supports.
4. Permit one pull request or decision to support more than one roadmap phase when the work crosses capability boundaries.
5. Record that some later-phase capabilities were implemented before earlier phase gates were formally reviewed.
6. Do not mark a phase formally complete until its exit criteria and phase review are recorded.
7. Pause new application-code, deployment, Docker, and AWS work until the documentation reconciliation and required retrospective reviews are merged.

This approach avoids both undesirable alternatives:

* leaving documentation materially inconsistent with verified behavior; or
* rewriting the roadmap so extensively that it no longer records the project's original intended sequence.

## 3. Evidence Baseline

The merged history through PR #43 includes:

* repository governance and documentation foundations;
* accepted ADR governance;
* a packaged Python and FastAPI backend;
* local and CI quality tooling;
* product, inventory, and demand APIs;
* a deterministic baseline demand forecast;
* deterministic stockout exposure;
* deterministic reorder recommendations;
* recommendation approval and rejection;
* ordered recommendation audit history;
* PostgreSQL operational persistence;
* PostgreSQL recommendation-workflow persistence;
* application-level PostgreSQL repository selection and lifecycle ownership.

The persistence layer includes:

* migration `0005_operational_data`;
* migration `0006_workflow_persistence`;
* SQLAlchemy and Psycopg-backed repositories;
* Alembic-only schema ownership;
* PostgreSQL restart-durability and shared-state tests.

The current automated test collection contains 446 tests.

Only `docs/12-phase-reviews/phase-0-review.md` currently exists. Therefore, only Phase 0 has a formally recorded phase-review decision.

## 4. Canonical Phase Mapping

### Phase 0 — Project definition, scope, governance, and readiness

Formal status: **Complete**

Primary evidence:

* repository governance foundation;
* project charter and competency documentation;
* development-governance rules;
* documentation and learning system;
* initial architecture hypothesis;
* risk, cost, security, and responsible-AI baseline;
* `docs/12-phase-reviews/phase-0-review.md`.

Decision:

Phase 0 remains complete with no historical remapping required.

### Phase 1 — Repository and local development foundation

Implementation status: **Delivered; retrospective review required**

Primary issues and pull requests:

* ADR system: PR #7;
* Python project foundation: PR #8;
* Python quality toolchain: PR #11;
* Python-quality CI: PR #13.

Primary decisions:

* ADR-0000: Use Architecture Decision Records;
* ADR-0001: Select Python Toolchain;
* ADR-0002: Select Python Quality and Testing Toolchain.

Proposed exit criteria:

* repository governance is merged;
* local prerequisites and setup are documented;
* Python version and dependency management are reproducible;
* formatting, linting, type checking, and testing run locally;
* equivalent quality checks run in CI;
* secret-prevention and dependency-management practices exist;
* the first backend implementation issue is approved.

Finding:

The implementation evidence satisfies these criteria, but no Phase 1 review exists.

Required action:

Create `docs/12-phase-reviews/phase-1-review.md` and record a retrospective Proceed, Revise, or Stop decision.

### Phase 2 — Product data and transactional backend

Implementation status: **Delivered; retrospective review required**

Primary issues and pull requests:

* FastAPI backend foundation: Issue #14 / PR #15;
* product and inventory API: Issue #16 / PR #17;
* PostgreSQL operational persistence: Issue #32 / PR #33;
* PostgreSQL persistence status finalization: Issue #34 / PR #35.

Primary decisions and migrations:

* ADR-0003: Select Backend Application Structure;
* ADR-0005: Use SQLAlchemy and Alembic for PostgreSQL Persistence;
* migration `0005_operational_data`.

Proposed exit criteria:

* the application has a reviewed modular backend structure;
* product and inventory contracts are implemented;
* repository interfaces keep domain and API behavior independent from storage;
* an in-memory implementation remains available for isolated execution;
* PostgreSQL provides durable product and inventory storage;
* Alembic owns schema creation and migration;
* transaction, rollback, constraint, and restart behavior are tested;
* runtime code does not create tables directly.

Finding:

The implementation evidence satisfies the proposed capability criteria, but no Phase 2 review exists.

Required action:

Create `docs/12-phase-reviews/phase-2-review.md` and record a retrospective phase decision.

### Phase 3 — Web workflow for product and demand operations

Implementation status: **Delivered; retrospective review required**

Primary issues and pull requests:

* FastAPI backend foundation: Issue #14 / PR #15;
* product and inventory API: Issue #16 / PR #17;
* demand-history API: Issue #18 / PR #19;
* PostgreSQL operational persistence: Issue #32 / PR #33.

Primary evidence:

* versioned business routes;
* product creation, listing, and retrieval;
* inventory replacement and retrieval;
* atomic demand-batch ingestion;
* chronological demand retrieval and inclusive filtering;
* shared operational repository contracts;
* durable PostgreSQL product, inventory, and demand behavior;
* preserved isolated in-memory behavior.

Proposed exit criteria:

* product, inventory, and demand operations are exposed through stable HTTP contracts;
* validation and business conflicts do not leak storage details;
* demand batches are atomic;
* source data is retrievable deterministically;
* operational state can run in isolated memory or durable PostgreSQL modes;
* API behavior remains consistent across persistence implementations.

Finding:

The implementation evidence satisfies the proposed capability criteria, but no Phase 3 review exists.

Required action:

Create `docs/12-phase-reviews/phase-3-review.md` and record a retrospective phase decision.

### Phase 4 — Forecasting baseline and evaluation

Recommended formal status after reconciliation: **Current**

Until the documentation corrections and retrospective Phase 1–3 reviews are
accepted and merged, the repository's existing formal roadmap status remains
unchanged.

Delivered evidence:

* Issue #20 / PR #21 implemented the deterministic arithmetic-mean forecast;
* forecasts preserve cutoff, lookback, zero-demand, missing-date, rounding, and evidence behavior;
* forecast behavior has automated API and domain tests.

Missing evidence:

* no formal baseline evaluation dataset;
* no temporal backtesting procedure;
* no comparison metric such as MAE, RMSE, WAPE, bias, or service-level impact;
* no measured forecast accuracy;
* no evaluation findings by demand pattern;
* no documented proceed, revise, or stop decision for the baseline.

Decision:

Phase 4 is the next permitted implementation phase after the documentation-reconciliation work and retrospective Phase 1–3 reviews are merged.

The existing baseline implementation does not by itself satisfy the roadmap phrase “forecasting baseline and evaluation.”

### Phase 5 — Stockout risk and reorder recommendations

Implementation status: **Delivered ahead of its formal gate; review deferred**

Primary issues and pull requests:

* stockout exposure: Issue #22 / PR #23;
* reorder recommendation: Issue #24 / PR #25.

Delivered evidence:

* deterministic lead-time demand exposure;
* projected inventory balance and shortage;
* deterministic reorder quantity using the documented ceiling policy;
* preserved recommendation evidence;
* automated domain and API tests.

Limitations:

* the current exposure is not a calibrated probability;
* it is not a learned risk model;
* it has no measured decision-quality evaluation;
* it has no service-level, safety-stock, supplier, pack-size, or cost optimization.

Decision:

Do not erase or downgrade the delivered implementation. Record it as early Phase 5 delivery.

Do not mark Phase 5 formally complete until:

1. Phase 4 is closed;
2. Phase 5 exit criteria are approved;
3. the delivered deterministic approach is reviewed against those criteria;
4. any required evaluation or explicitly accepted limitations are recorded.

### Phase 6 — Decision approval, rejection, and audit history

Implementation status: **Delivered ahead of its formal gate; review deferred**

Primary issues and pull requests:

* recommendation review workflow: Issue #26 / PR #27;
* recommendation audit history: Issue #28 / PR #29;
* ADR-0004 acceptance: Issue #30 / PR #31;
* workflow-persistence design: Issue #36 / PR #37;
* workflow schema: Issue #38 / PR #39;
* PostgreSQL workflow repository: Issue #40 / PR #41;
* application integration: Issue #42 / PR #43.

Primary decisions and migrations:

* ADR-0004: Co-locate Recommendation Workflow State and Audit Events;
* ADR-0005: Use SQLAlchemy and Alembic for PostgreSQL Persistence;
* migration `0006_workflow_persistence`.

Delivered evidence:

* immutable recommendation snapshots;
* pending, approved, and rejected states;
* normalized idempotent terminal retries;
* conflict handling for changed or opposite retries;
* ordered creation and terminal-decision events;
* atomic review, decision, and event persistence;
* concurrent-decision protection;
* PostgreSQL sharing and restart durability;
* isolated memory behavior;
* application-owned engine disposal and explicit-injection ownership preservation.

Limitations:

* `decided_by` remains caller supplied and unverified;
* there is no authentication or role-based authorization;
* audit events are not cryptographically tamper-evident;
* approval does not create a purchase order or external business action;
* the system is not a compliance ledger.

Decision:

Record this as early Phase 6 delivery.

Do not mark Phase 6 formally complete until Phase 4 and Phase 5 gates are reconciled and a Phase 6 review determines whether the delivered behavior and accepted limitations satisfy its approved exit criteria.

### Phase 7 — Testing, security, and observability hardening

Formal status: **Planned**

Existing quality and integration testing supports earlier phases, but Phase 7-specific security and observability hardening has not been formally scoped or approved.

Phase 7 must not become current merely because extensive tests already exist.

### Phases 8–12

Formal status: **Planned**

No phase should be advanced based only on exploratory documentation or dependency presence.

In particular:

* there is no API container;
* there is no AWS deployment;
* there is no production database;
* there is no production monitoring or alerting;
* there is no production backup, replication, or high-availability evidence;
* there is no governed model lifecycle;
* there is no advanced-AI production capability;
* there is no production-readiness approval.

## 5. Required Documentation Corrections

A follow-up documentation task must update the following files.

### `ROADMAP.md`

* Keep the original Phase 0–12 capability structure.
* Replace the stale status table.
* Distinguish formal phase status from implementation delivered ahead of a gate.
* Add explicit exit criteria for Phases 2–6.
* Mark Phase 4 as Current only after retrospective Phase 1–3 reviews are accepted.
* Keep Phases 7–12 Planned.
* Document that early implementation does not automatically equal formal phase completion.

### `docs/09-status/current-status.md`

* Preserve historical issue and PR records.
* Correct headings that incorrectly group forecasting, stockout, reorder, approval, and audit work entirely under Phase 2.
* Add the workflow-persistence work delivered through PRs #35, #37, #39, #41, and #43.
* Correct claims that PostgreSQL workflow state remains process-local, restart-volatile, or isolated across application instances.
* Preserve memory-backend isolation as an intentional supported behavior.
* Record the current application-level repository-selection and engine-ownership rules.

### `CHANGELOG.md`

* Move implemented application services out of “Not Yet Implemented.”
* Move implemented database schema and migrations out of “Not Yet Implemented.”
* Add the implemented backend, decision workflow, audit history, and PostgreSQL persistence capabilities under `Unreleased`.
* Keep AWS infrastructure, user interface, authentication, production deployment, and advanced AI under “Not Yet Implemented.”

### `README.md`

* Correct current-status summaries that describe workflow history as universally process-local.
* Explain memory and PostgreSQL behavior separately.
* Correct restart and cross-application durability language.
* Preserve warnings about unverified actors, missing authorization, absent external ordering, and non-compliance-grade audit history.
* Do not claim production readiness.

### Phase-review documents

Create retrospective reviews for:

* `docs/12-phase-reviews/phase-1-review.md`;
* `docs/12-phase-reviews/phase-2-review.md`;
* `docs/12-phase-reviews/phase-3-review.md`.

Each review must include:

* delivered capabilities;
* validation evidence;
* documentation evidence;
* security, cost, data, and operational findings;
* unresolved risks;
* deferred work;
* a Proceed, Revise, or Stop decision.

Do not create a passing Phase 4, Phase 5, or Phase 6 review until its formal gate is evaluated.

## 6. Explicitly Stale or Contradictory Claims

The follow-up task must correct, without deleting historical context, claims that currently imply:

* Phase 1 is still the active implementation phase;
* all Phases 2–6 remain wholly planned;
* workflow storage is always process-local;
* workflow state is always lost on restart;
* workflow state is never shared across application instances;
* workflow persistence does not exist;
* database schema and migrations do not exist;
* application services do not exist.

Historical sections may retain descriptions of what was true at the time of an earlier PR, but they must be clearly labeled as historical rather than current behavior.

## 7. Security, Cost, Data, and Operational Findings

### Security

* No credentials or private data are required for this documentation investigation.
* PostgreSQL secrets remain environment supplied.
* Actors remain unauthenticated and unverified.
* No authorization or tamper-evidence claim is justified.

### Cost

* No cloud resources are created.
* Local PostgreSQL and GitHub-hosted CI remain the only evidenced infrastructure.
* No production cost estimate is yet justified.

### Data

* Tests use synthetic or controlled test data.
* No production or regulated data is introduced.

### Operations

* Local and CI migrations are evidenced.
* Durable local PostgreSQL behavior is evidenced.
* Deployment, backups, replication, high availability, observability, and incident response remain unimplemented.

## 8. Deferred Risks and Follow-up Work

* missing retrospective Phase 1–3 reviews;
* missing Phase 4 evaluation design and results;
* undefined Phase 5 and Phase 6 formal exit criteria until the roadmap correction is accepted;
* caller-supplied reviewer identity;
* no authorization;
* no tamper-evident audit history;
* no external ordering integration;
* no deployment or production operations;
* known Starlette TestClient/httpx deprecation warning;
* no production-readiness evidence.

## 9. Proceed, Revise, or Stop Decision

Decision: **Revise**

The implementation itself does not need to be reverted.

The governance and status documentation must be revised before further implementation begins.

Proceed with a bounded documentation-correction task that:

1. updates the roadmap and status documents;
2. adds explicit Phase 2–6 exit criteria;
3. creates retrospective Phase 1–3 reviews;
4. records Phase 4 as the next current capability phase;
5. records Phase 5 and Phase 6 as delivered early but not yet formally closed;
6. leaves Phases 7–12 planned.

## 10. Next Permitted Phase

After the documentation corrections and retrospective Phase 1–3 reviews are reviewed and merged:

**Proceed to Phase 4 — Forecasting baseline and evaluation.**

The next application implementation issue should focus on defining and validating a reproducible baseline forecast-evaluation method.

Do not begin:

* Phase 7 hardening as a substitute for missing Phase 4 evaluation;
* Docker API packaging;
* AWS resources;
* cloud deployment;
* production-readiness claims.

## 11. Issue #44 Completion Criteria

Issue #44 is complete when:

* this reconciliation document is reviewed;
* the repository owner accepts or revises the hybrid mapping;
* the Proceed, Revise, or Stop decision is explicit;
* the next permitted phase is explicit;
* a separate documentation-correction task is ready to be opened;
* no application code, schema, migration, Docker, deployment, or AWS change is included.
