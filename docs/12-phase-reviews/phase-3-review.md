# Phase 3 Retrospective Review and Readiness Assessment

Review date: 2026-08-04
Review type: Retrospective phase-gate review
Governed by: Issue #46
Reconciliation basis:
`docs/00-project-foundation/roadmap-phase-reconciliation.md`

## Outcome

Overall result: **Passed**

Decision: **Proceed — retrospective**

The delivered web workflow for product, inventory, and demand operations
satisfies the Phase 3 exit criteria.

Upon acceptance and merge of this review through Issue #46, Phase 3 is formally
complete.

This retrospective decision completes the missing governance gate before
Phase 4. It does not by itself authorize Phase 4 implementation until the full
Issue #46 documentation reconciliation is reviewed and merged.

## Review Scope

This review evaluates work delivered primarily through:

* FastAPI backend foundation: Issue #14 / PR #15;
* product and inventory API: Issue #16 / PR #17;
* demand-history API: Issue #18 / PR #19;
* PostgreSQL operational persistence: Issue #32 / PR #33;
* PostgreSQL persistence status finalization: Issue #34 / PR #35.

It also considers:

* ADR-0003: Select Backend Application Structure;
* ADR-0005: Use SQLAlchemy and Alembic for PostgreSQL Persistence;
* Alembic revision `0005_operational_data`;
* the shared `ProductInventoryRepository` contract;
* supported in-memory operational behavior;
* supported PostgreSQL operational behavior;
* local and CI API, repository, and PostgreSQL validation.

This review evaluates the operational web workflow through demand history. It
does not evaluate:

* forecast accuracy or forecast evaluation;
* stockout or reorder decision quality;
* recommendation approval and rejection;
* recommendation audit history;
* recommendation-workflow persistence;
* authentication or authorization;
* deployment or production readiness.

## Exit-Criteria Assessment

| Exit criterion                                                                      | Result                   | Evidence                                                                                                              |
| ----------------------------------------------------------------------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| Product, inventory, and demand operations are exposed through stable HTTP contracts | Passed                   | Issues #16 and #18 delivered versioned product, inventory, and demand routes under the configured business API prefix |
| Validation and business conflicts do not expose storage details                     | Passed                   | Public validation and conflict responses remain expressed through established application and business errors         |
| Demand batches are atomic                                                           | Passed                   | A duplicate-date conflict stores none of the failed batch and preserves prior state                                   |
| Source data is retrievable deterministically                                        | Passed                   | Product listing is deterministic and demand results are chronological with inclusive date filtering                   |
| Operational state supports isolated memory and durable PostgreSQL modes             | Passed                   | The in-memory repository remains supported while PostgreSQL provides sharing and restart durability                   |
| API behavior remains consistent across supported persistence implementations        | Passed                   | Both repository implementations satisfy the shared operational contract and preserve public behavior                  |
| A Phase 3 review records an accepted decision                                       | Pending owner acceptance | Satisfied when this review is reviewed and merged through Issue #46                                                   |

## Delivered Capabilities

Phase 3 delivered the operational web workflow for:

* product creation;
* deterministic product listing;
* product retrieval by UUID;
* current-inventory replacement;
* current-inventory retrieval;
* calculated available inventory;
* negative available inventory representing shortage;
* nonempty daily demand-batch ingestion;
* atomic demand-batch validation and persistence;
* chronological demand-history retrieval;
* optional inclusive demand start-date filtering;
* optional inclusive demand end-date filtering;
* valid zero-demand observations;
* rejection of negative demand quantities;
* stable versioned HTTP business routes;
* domain-level validation and conflict responses;
* shared operational repository contracts;
* isolated in-memory execution;
* durable PostgreSQL execution;
* shared PostgreSQL state across application instances;
* operational state that survives application restart.

## HTTP Contract Evidence

The business workflow is exposed beneath the configured versioned API prefix.

Product operations include:

* create a product;
* list products in deterministic order;
* retrieve an existing product;
* return the documented response for an unknown product.

Inventory operations include:

* set or replace the current inventory position for an existing product;
* retrieve the current inventory position;
* calculate available inventory as on-hand quantity minus allocated quantity;
* preserve a negative available quantity as shortage evidence.

Demand operations include:

* submit a nonempty batch of dated daily observations;
* validate the entire batch before successful storage;
* reject duplicate observations for the same product and date;
* retrieve observations chronologically;
* filter observations by an optional inclusive start date;
* filter observations by an optional inclusive end date;
* preserve recorded zero-demand observations;
* reject negative quantities.

These contracts expose business and validation behavior without requiring
clients to understand the active repository implementation.

## Atomicity and Determinism Evidence

Demand ingestion is atomic.

When any observation in a submitted batch conflicts with existing demand:

* none of the failed batch is stored;
* previously stored observations remain unchanged;
* the conflict is returned through the established business-error behavior.

Deterministic retrieval is supported through:

* deterministic product listing;
* chronological demand ordering;
* inclusive start-date filtering;
* inclusive end-date filtering;
* stable UUID-based product retrieval;
* preserved zero-demand observations;
* explicit distinction between a missing calendar date and a recorded zero.

The workflow does not silently create missing demand dates or reinterpret a
missing observation as zero demand.

## Persistence-Mode Evidence

### In-memory mode

The supported in-memory operational repository provides:

* isolated application state;
* deterministic behavior for local development and tests;
* no dependency on an external database;
* restart-volatile state;
* no sharing between independent application instances.

### PostgreSQL mode

The supported PostgreSQL operational repository provides:

* product persistence;
* current-inventory persistence;
* daily demand-observation persistence;
* shared state between applications using the same database;
* state that survives application restart;
* explicit transaction boundaries;
* rollback on failed writes;
* database constraint enforcement;
* Alembic-owned schema migration.

PostgreSQL is selected explicitly through the configured database URL. Runtime
application code does not create or migrate tables.

The memory and PostgreSQL modes intentionally differ in durability and sharing,
but they preserve the established public operational API behavior.

## Architecture Evidence

ADR-0003 records the modular FastAPI backend structure that separates:

* application construction;
* settings;
* routers;
* schemas;
* domain and service behavior;
* repository contracts;
* repository implementations;
* tests.

ADR-0005 records the PostgreSQL persistence approach:

* SQLAlchemy 2.x;
* Psycopg 3;
* synchronous sessions;
* Alembic-only schema ownership;
* explicit transaction boundaries;
* domain and ORM separation;
* real PostgreSQL integration testing;
* phased persistence adoption.

Migration `0005_operational_data` provides the operational schema for:

* products;
* current inventory positions;
* daily demand observations.

The database schema includes deterministic keys, constraints, uniqueness rules,
and indexes that support the documented workflow invariants.

## Validation Evidence

Phase 3 validation includes:

* product API tests;
* inventory API tests;
* demand API tests;
* request-validation tests;
* unknown-product behavior tests;
* duplicate-product conflict tests;
* inventory replacement tests;
* available-inventory calculation tests;
* negative-availability tests;
* empty demand-batch rejection tests;
* duplicate-date conflict tests;
* atomic demand-batch tests;
* chronological retrieval tests;
* inclusive start-date tests;
* inclusive end-date tests;
* combined date-range tests;
* zero-demand tests;
* negative-demand rejection tests;
* repository-contract tests;
* in-memory repository tests;
* PostgreSQL repository integration tests;
* cross-application shared-state tests;
* restart-durability tests;
* transaction rollback tests;
* database constraint tests;
* Alembic migration application in CI;
* repository-governance checks;
* Python-quality checks.

PostgreSQL-specific tests use a real PostgreSQL 17 service in local and CI
validation rather than substituting SQLite behavior.

## Documentation Evidence

Phase 3 documentation includes or is supported by:

* public product API documentation;
* public inventory API documentation;
* public demand-history API documentation;
* validation and conflict behavior;
* memory-repository behavior;
* PostgreSQL repository configuration;
* database URL guidance;
* Alembic migration guidance;
* local PostgreSQL test safeguards;
* CI PostgreSQL service configuration;
* ADR-0003;
* ADR-0005;
* migration `0005_operational_data`;
* historical issue and pull-request records;
* the accepted roadmap-phase reconciliation.

Issue #46 corrects the historical phase headings and current-state summaries
without deleting the chronology of when the memory-only and PostgreSQL
capabilities were introduced.

## Security and Privacy Findings

* No production, customer, personal, or regulated data is required.
* Test data is synthetic or controlled.
* PostgreSQL credentials remain environment supplied.
* Database URLs use secret-aware application settings.
* Credentials are not committed to the repository.
* Destructive PostgreSQL tests restrict acceptable hosts and database names.
* Public errors do not expose raw storage exceptions.
* No authentication or role-based authorization protects the operational API.
* No production network, encryption, access-control, or compliance posture is
  established.

Result: **Acceptable for Phase 3**

## Cost Findings

* No AWS infrastructure is created.
* No managed or production database is provisioned.
* Local PostgreSQL and the GitHub Actions PostgreSQL service are the evidenced
  database environments.
* No persistent production infrastructure cost is incurred.
* No production load, capacity, or scaling cost estimate is justified.

Result: **Acceptable for Phase 3**

## Data Findings

* Products are identified with UUIDs.
* Inventory represents the latest operational position rather than a complete
  movement ledger.
* Available inventory may be negative.
* Demand observations are keyed by product and calendar date.
* Recorded zero demand is distinct from a missing observation.
* Demand history is returned chronologically.
* Date-range filters are inclusive.
* Demand batches are atomic.
* Database constraints protect structural invariants.
* Backup, retention, archival, correction, and deletion policies remain
  undefined.

Result: **Acceptable for Phase 3**

## Operational Findings

* Memory mode supports isolated local and test execution.
* Memory state is lost on restart and is not shared between applications.
* PostgreSQL mode supports shared state and restart durability.
* Alembic must be applied before PostgreSQL-backed application use.
* Runtime startup does not create or migrate tables.
* Failed PostgreSQL writes roll back through explicit transaction handling.
* Local and CI PostgreSQL integration testing is evidenced.
* There is no production database service.
* There are no backups, replicas, high-availability controls, monitoring,
  alerting, service-level objectives, or incident-response procedures.

Result: **Acceptable for Phase 3**

## Unresolved Risks

* The operational API has no authentication or authorization.
* There is no request-rate limiting or abuse protection.
* There is no production database provisioning or capacity plan.
* There is no backup, restore, replication, or disaster-recovery procedure.
* There is no production monitoring or alerting.
* There is no production secret-management and rotation workflow.
* Inventory is current-state replacement, not an immutable movement history.
* Demand correction and deletion workflows are not implemented.
* Data-retention and archival policies are undefined.
* PostgreSQL integration evidence does not establish production readiness.
* API stability is governed by tests and review but is not associated with a
  released semantic-versioning policy.

These risks do not block retrospective Phase 3 completion.

## Conditions Carried Forward

* Preserve stable versioned business routes.
* Preserve storage-independent public behavior.
* Preserve atomic demand-batch ingestion.
* Preserve chronological demand retrieval.
* Preserve inclusive date filtering.
* Preserve recorded zero demand as distinct from missing dates.
* Preserve isolated in-memory execution.
* Preserve PostgreSQL sharing and restart durability.
* Keep Alembic as the sole schema owner.
* Keep database credentials environment supplied and uncommitted.
* Require real PostgreSQL tests for PostgreSQL-specific behavior.
* Keep destructive-test database safeguards intact.
* Do not describe local or CI PostgreSQL evidence as production readiness.
* Record material API or persistence changes through governed issues, tests,
  ADRs, and migrations as applicable.

## Deferred Work

The following work is outside Phase 3:

* formal forecast-baseline evaluation;
* temporal backtesting;
* forecast-error metrics and measured forecast quality;
* stockout and reorder decision-quality evaluation;
* Phase 5 formal completion;
* recommendation approval and audit Phase 6 completion;
* authentication and role-based authorization;
* inventory movement history;
* demand correction and deletion workflows;
* production database provisioning;
* backups, replication, and high availability;
* API containerization;
* AWS infrastructure and deployment;
* production monitoring and incident response.

Later implementation has delivered forecasting, stockout, reorder,
recommendation-review, audit, and workflow-persistence capabilities. Those
capabilities are mapped to later phases and do not alter this Phase 3 decision.

## Decision

**Proceed — retrospective**

The Phase 3 product, inventory, and demand web workflow is accepted as
sufficient for the governed transition into Phase 4.

Phase 3 becomes formally Complete when this review and the associated Issue #46
documentation corrections are accepted and merged.

After the full Issue #46 documentation-reconciliation pull request is reviewed
and merged, Phase 4 — Forecasting baseline and evaluation — becomes the current
permitted implementation phase.

This decision does not mark Phase 4 complete and does not authorize Phase 5,
Phase 6, Docker, AWS, deployment, or production-readiness work.
