# OpsMind Current Status

Status basis: implementation merged through PR #43
Governance basis:
`docs/00-project-foundation/roadmap-phase-reconciliation.md`
Documentation reconciliation: Issue #46

This document describes the repository state established when the Issue #46
documentation reconciliation and retrospective Phase 1–3 reviews are accepted
and merged.

Historical implementation descriptions remain useful evidence, but current
behavior is determined by the latest merged implementation rather than by an
earlier memory-only milestone.

## Canonical Phase Status

| Phase | Focus                                                                     | Formal status | Current finding                                    |
| ----- | ------------------------------------------------------------------------- | ------------- | -------------------------------------------------- |
| 0     | Project definition, scope, governance, and readiness                      | Complete      | Phase 0 review accepted                            |
| 1     | Repository and local development foundation                               | Complete      | Delivered and retrospectively reviewed             |
| 2     | Product data and transactional backend                                    | Complete      | Delivered and retrospectively reviewed             |
| 3     | Web workflow for product and demand operations                            | Complete      | Delivered and retrospectively reviewed             |
| 4     | Forecasting baseline and evaluation                                       | Current       | Baseline delivered; evaluation remains             |
| 5     | Stockout risk and reorder recommendations                                 | Gate pending  | Deterministic capability delivered early           |
| 6     | Decision approval, rejection, and audit history                           | Gate pending  | Workflow and PostgreSQL durability delivered early |
| 7–12  | Hardening, cloud, pipelines, MLOps, advanced AI, and production readiness | Planned       | Not formally opened                                |

Implementation delivery and formal phase completion are separate. Phases 5 and
6 contain working capability but have not passed their formal gates.

## Repository and Development Foundation

Phase 1 established:

* repository governance;
* contributor and automated-agent boundaries;
* Architecture Decision Records;
* the packaged Python project;
* dependency locking with `uv`;
* Ruff formatting and linting;
* mypy static type checking;
* pytest and pytest-cov;
* Python-quality continuous integration;
* repository-governance validation;
* pull-request review before merge.

The foundation includes:

* `pyproject.toml`;
* `.python-version`;
* `uv.lock`;
* the packaged `src/opsmind` layout;
* application and test layouts;
* pinned GitHub Actions;
* read-only workflow permissions.

ADR-0000, ADR-0001, and ADR-0002 record the accepted ADR, Python, and
quality-toolchain decisions.

Pre-commit remains deferred. Coverage is collected without a minimum percentage
gate.

## Phase 2 — Product Data and Transactional Backend

Phase 2 delivered the reviewed FastAPI backend and operational persistence
foundation.

### Backend structure

Issue #14 and PR #15 delivered:

* the FastAPI application factory;
* typed settings;
* modular routing;
* dependency-injection boundaries;
* separate schemas, services, repositories, and tests;
* the unversioned `GET /health` process-health endpoint;
* the configured versioned business API prefix.

ADR-0003 records the accepted modular-monolith backend structure.

### Product and inventory behavior

Issue #16 and PR #17 delivered:

* product creation;
* deterministic product listing;
* product retrieval by UUID;
* current-inventory replacement;
* current-inventory retrieval;
* available inventory calculated as on-hand minus allocated quantity;
* negative available inventory preserved as shortage evidence.

The initial PR #17 implementation used isolated in-memory storage. That remains
a supported mode, but it is no longer the only persistence mode.

### Operational persistence

Issue #32 and PR #33 delivered PostgreSQL persistence for:

* products;
* current inventory positions;
* daily demand observations.

PR #35 finalized the operational-persistence status and documentation.

ADR-0005 records the accepted use of:

* SQLAlchemy 2.x;
* Psycopg 3;
* synchronous sessions;
* Alembic migrations;
* explicit transaction boundaries;
* domain and ORM separation;
* real PostgreSQL integration tests;
* phased persistence adoption.

Migration `0005_operational_data` creates the operational schema.

Runtime application code does not create or migrate tables.

PostgreSQL-backed applications using the same database:

* share product, inventory, and demand state;
* retain that state across application restart.

The in-memory operational repository remains available for isolated execution.

## Phase 3 — Product and Demand Web Workflow

Phase 3 delivered stable HTTP operations for product, inventory, and demand
data.

### Product and inventory routes

The configured versioned API supports:

* product creation;
* deterministic product listing;
* product retrieval;
* inventory replacement;
* inventory retrieval.

Public business behavior remains independent of whether the active repository
uses memory or PostgreSQL.

### Demand-history routes

Issue #18 and PR #19 delivered:

* nonempty daily demand-batch ingestion;
* whole-batch validation;
* atomic storage;
* duplicate product-date conflict handling;
* chronological demand retrieval;
* optional inclusive start-date filtering;
* optional inclusive end-date filtering;
* valid zero-demand observations;
* rejection of negative demand quantities.

The original PR #19 implementation was memory-only. After PR #33, demand uses
the same supported operational persistence selection as product and inventory.

In memory mode, state remains isolated and restart-volatile.

In PostgreSQL mode, product, inventory, and demand state is shared between
applications using the same database and survives application restart.

## Phase 4 — Forecasting Baseline and Evaluation

Phase 4 is the current permitted implementation phase after Issue #46 merges.

Issue #20 and PR #21 delivered a deterministic arithmetic-mean forecast that:

* reads chronological demand observations;
* supports an observation-count lookback;
* supports a requested horizon;
* supports an optional inclusive cutoff;
* uses the latest stored demand date when no cutoff is supplied;
* preserves recorded zero demand;
* leaves missing calendar dates missing;
* uses exact decimal arithmetic;
* rounds published values to two decimal places with `ROUND_HALF_UP`;
* returns the selected evidence and effective calculation inputs.

Forecasts are calculated on demand and are not persisted.

The baseline does not yet satisfy the evaluation portion of Phase 4. Missing
work includes:

* an approved evaluation dataset or generation method;
* temporal backtesting;
* forecast-error metrics;
* measured baseline accuracy;
* findings by demand pattern;
* an accepted Phase 4 decision.

The baseline does not currently model:

* trend;
* seasonality;
* intermittent-demand structure;
* uncertainty;
* calibrated prediction intervals.

## Phase 5 — Stockout Risk and Reorder Recommendations

Phase 5 capability was delivered ahead of its formal gate.

### Deterministic stockout exposure

Issue #22 and PR #23 delivered:

* lead-time demand exposure;
* projected inventory balance;
* projected shortage;
* `sufficient` and `shortage_projected` statuses;
* deterministic evidence derived from the baseline forecast.

This is not:

* a calibrated stockout probability;
* a learned risk model;
* a measured decision-quality model.

### Deterministic reorder recommendation

Issue #24 and PR #25 delivered:

* a read-only recommendation endpoint;
* preservation of forecast and exposure evidence;
* the `projected_shortage_ceiling` policy;
* whole-unit recommendations using `ROUND_CEILING`;
* `no_reorder_needed` and `reorder_recommended` outcomes.

Recommendations do not:

* create purchase orders;
* select suppliers;
* reserve inventory;
* mutate inventory;
* optimize cost, pack size, safety stock, or service level.

Phase 5 remains gate pending until Phase 4 is complete and the delivered
deterministic behavior is formally evaluated against the Phase 5 criteria.

## Phase 6 — Decision Review and Audit History

Phase 6 capability was delivered ahead of its formal gate.

### Recommendation review workflow

Issue #26 and PR #27 delivered:

* storage of actionable positive recommendations;
* server-generated recommendation-review UUIDs;
* timezone-aware UTC creation timestamps;
* immutable recommendation and evidence snapshots;
* initial `pending_review` state;
* one terminal `approved` or `rejected` state;
* normalized idempotent retries;
* conflict handling for changed or opposite retries;
* concurrent-decision protection;
* separately recorded recommended and approved quantities;
* required rejection reasons.

The workflow does not recalculate forecast, exposure, or recommendation evidence
during retrieval or decision handling.

### Ordered audit history

Issue #28 and PR #29 delivered:

* automatic `review_created` events;
* terminal approval or rejection events;
* sequence-based deterministic ordering;
* immutable retrieval through supported APIs;
* no duplicate terminal event for an identical normalized retry;
* no event append for a conflicting retry.

ADR-0004 records the decision to keep workflow state and its matching audit
event within one atomic repository transaction boundary.

The original PR #27 and PR #29 implementations used a process-local in-memory
workflow repository. That remains a supported mode, but it is no longer the
only implementation.

### PostgreSQL workflow-persistence design

Issue #34 and PR #35 finalized the operational-persistence status.

Issue #36 and PR #37 documented the PostgreSQL recommendation-workflow
persistence design and transaction requirements.

The design preserves:

* immutable recommendation snapshots;
* one terminal decision;
* idempotent normalized retries;
* conflict behavior;
* atomic review, decision, and event persistence;
* deterministic audit-event ordering;
* repository-interface independence.

### PostgreSQL workflow schema

Issue #38 and PR #39 added migration `0006_workflow_persistence`.

The migration extends `0005_operational_data` with the recommendation-workflow
schema required for:

* review aggregates;
* immutable recommendation evidence;
* approval and rejection data;
* ordered audit events;
* documented relational constraints.

Alembic remains the sole schema owner.

### PostgreSQL workflow repository

Issue #40 and PR #41 delivered the PostgreSQL recommendation-workflow
repository.

The repository preserves:

* atomic aggregate and event changes;
* idempotent retry behavior;
* conflict handling;
* concurrent terminal-decision protection;
* ordered audit retrieval;
* PostgreSQL sharing;
* restart durability.

### Application integration

Issue #42 and PR #43 integrated PostgreSQL workflow persistence into application
construction.

The application supports coordinated repository selection for:

* operational product, inventory, and demand state;
* recommendation workflow and audit state.

When the application creates PostgreSQL infrastructure, it owns and disposes
that infrastructure through the application lifecycle.

When repositories or related resources are explicitly injected, caller
ownership is preserved and the application does not take ownership of those
external resources.

Phase 6 remains gate pending. Delivered implementation is not equivalent to an
accepted Phase 6 review.

## Persistence Modes

| Behavior                                  | In-memory mode | PostgreSQL mode                          |
| ----------------------------------------- | -------------- | ---------------------------------------- |
| Product, inventory, and demand storage    | Supported      | Supported                                |
| Recommendation workflow and audit storage | Supported      | Supported                                |
| Shared between independent applications   | No             | Yes, when using the same database        |
| Survives application restart              | No             | Yes                                      |
| External database required                | No             | Yes                                      |
| Schema ownership                          | Not applicable | Alembic                                  |
| Suitable for isolated tests               | Yes            | Yes, with controlled PostgreSQL fixtures |
| Production readiness established          | No             | No                                       |

Memory behavior is intentionally isolated and restart-volatile.

PostgreSQL behavior is evidenced through local and CI integration tests for
sharing and restart durability. This evidence does not establish a production
database or production-readiness posture.

## Validation Status

The accepted reconciliation recorded 446 collected tests through PR #43.

The validation surface includes:

* application-construction tests;
* configuration tests;
* product API tests;
* inventory API tests;
* demand API tests;
* forecast API and domain tests;
* stockout API and domain tests;
* reorder API and domain tests;
* recommendation-review tests;
* audit-history tests;
* operational repository-contract tests;
* in-memory repository tests;
* PostgreSQL operational repository tests;
* PostgreSQL workflow-schema tests;
* PostgreSQL workflow-constraint tests;
* PostgreSQL workflow-repository tests;
* application-level PostgreSQL integration tests;
* migration tests;
* cross-application sharing tests;
* restart-durability tests;
* concurrency tests;
* transaction and rollback tests.

Local and CI PostgreSQL integration tests use PostgreSQL 17.

Destructive local fixtures require:

* `OPSMIND_TEST_DATABASE_URL`;
* a loopback database host;
* a database name ending in `_test` or `_testing`.

Repository-governance and Python-quality checks remain required.

A known Starlette TestClient/httpx deprecation warning remains unresolved.

## Security and Privacy Status

Current safeguards include:

* environment-supplied PostgreSQL credentials;
* secret-aware database settings;
* ignored local environment files;
* read-only CI permissions;
* pinned external GitHub Actions;
* controlled destructive-test database requirements;
* domain-level translation of expected storage conflicts;
* human pull-request review.

Current limitations include:

* no user authentication;
* no role-based authorization;
* caller-supplied and unverified `decided_by`;
* no proof that an audit actor is authentic;
* no cryptographic signatures;
* no hash chaining;
* no tamper-evident audit storage;
* no compliance-ledger guarantee;
* no production network or database-security posture.

No production, customer, personal, or regulated data is required for the
implemented tests.

## Cost Status

* No AWS resources exist.
* No managed production database exists.
* Local PostgreSQL and GitHub-hosted CI are the evidenced infrastructure.
* No production capacity or cost estimate is justified.
* No production cost-control system exists.

## Data Status

* Tests use synthetic or controlled data.
* Products use UUID identifiers.
* Inventory represents the latest current position, not a movement ledger.
* Available inventory may be negative.
* Demand observations are keyed by product and calendar date.
* Recorded zero demand remains distinct from a missing observation.
* Demand batches are atomic.
* Recommendation snapshots preserve decision evidence.
* Audit events use deterministic sequence ordering.
* Backup, retention, archival, correction, and deletion policies remain
  undefined.

## Operational Status

Evidenced:

* reproducible local setup;
* pull-request CI;
* Alembic migration execution;
* local and CI PostgreSQL integration tests;
* explicit transaction boundaries;
* rollback behavior;
* shared PostgreSQL state;
* restart durability;
* application-owned resource cleanup;
* preservation of explicit-injection ownership.

Not implemented or approved:

* API containerization;
* AWS deployment;
* production database provisioning;
* backups;
* restore procedures;
* replication;
* high availability;
* monitoring;
* alerting;
* service-level objectives;
* incident response;
* production secret rotation;
* production-readiness approval.

## Historical Delivery Record

The implementation history remains chronological:

* PR #7 — Architecture Decision Record system;
* PR #8 — Python project foundation;
* PR #11 — Python quality toolchain;
* PR #13 — Python-quality CI;
* PR #15 — FastAPI backend foundation;
* PR #17 — product and inventory API;
* PR #19 — demand-history API;
* PR #21 — baseline demand forecast;
* PR #23 — deterministic stockout exposure;
* PR #25 — deterministic reorder recommendation;
* PR #27 — recommendation-review workflow;
* PR #29 — recommendation audit history;
* PR #31 — ADR-0004 acceptance;
* PR #33 — PostgreSQL operational persistence;
* PR #35 — PostgreSQL persistence status finalization;
* PR #37 — PostgreSQL workflow-persistence design;
* PR #39 — PostgreSQL workflow schema;
* PR #41 — PostgreSQL recommendation-workflow repository;
* PR #43 — application integration of PostgreSQL workflow persistence;
* PR #45 — accepted roadmap-phase reconciliation.

Historical memory-only descriptions remain accurate for the point in history at
which their associated PR merged. They must not be interpreted as the current
limit of supported behavior after PR #43.

## Current Limitations

OpsMind currently has no:

* formal forecast-baseline evaluation;
* measured forecast accuracy;
* calibrated stockout probability;
* learned stockout model;
* supplier optimization;
* cost optimization;
* safety-stock optimization;
* purchase-order creation;
* external ordering integration;
* authenticated reviewer identity;
* authorization;
* tamper-evident audit ledger;
* frontend user interface;
* API container;
* AWS infrastructure;
* cloud deployment;
* production database;
* backups or high availability;
* production observability;
* governed model lifecycle;
* advanced-AI production capability;
* production-readiness approval.

## Next Permitted Work

After the Issue #46 documentation reconciliation is accepted and merged, the
next permitted implementation work is:

**Phase 4 — Forecasting baseline and evaluation**

The next implementation issue should define and validate a reproducible
forecast-evaluation method.

Do not begin Phase 5 or Phase 6 formal completion, Phase 7 hardening, Docker,
AWS, deployment, or production-readiness work as a substitute for the missing
Phase 4 evaluation.
