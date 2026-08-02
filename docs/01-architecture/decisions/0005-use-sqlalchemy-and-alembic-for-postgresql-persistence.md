# ADR-0005: Use SQLAlchemy and Alembic for PostgreSQL Persistence

- Status: Proposed
- Date: 2026-08-02
- Decision owners: Anish Paudyal
- Related issues: #32
- Related pull requests: The pull request implementing issue #32
- Supersedes: None
- Superseded by: None

## Context

OpsMind's product, inventory, and demand source data is currently held by an
application-instance-local in-memory repository. That repository is useful for
isolated tests and temporary development, but it loses data on restart and
cannot share operational state across application processes. Forecast,
stockout-exposure, reorder, and stored-review creation all read this source data
through the existing `ProductInventoryRepository` Protocol.

Issue #32 introduces the first durable-data boundary without changing the
domain-facing repository contract or the public HTTP contracts. The current
application and routes are synchronous. Recommendation reviews, decisions, and
audit events use a separate process-local repository governed by ADR-0004 and
are intentionally outside this first persistence milestone.

## Decision drivers

- Durable product, inventory, and demand state
- Shared operational truth across application instances
- PostgreSQL constraints and transaction semantics
- Compatibility with the synchronous FastAPI and repository design
- Explicit separation between immutable domain models and database models
- Deterministic, reviewable schema migrations
- Real-database integration confidence
- Safe error translation and secret handling
- A bounded migration path for the existing in-memory application
- Preservation of ADR-0004's future atomic workflow-history requirement

## Considered options

1. **Raw Psycopg SQL.** This provides direct PostgreSQL access and few layers,
   but would require repetitive typed row mapping, statement construction, and
   migration coordination as the schema grows.
2. **Synchronous SQLAlchemy 2.x with Psycopg 3 and Alembic.** This provides
   typed statement APIs, explicit ORM mappings, PostgreSQL dialect support,
   transaction control, and a mature migration system while preserving the
   synchronous repository contract.
3. **Async SQLAlchemy.** This can support high-concurrency asynchronous I/O,
   but would force async engines, sessions, repository methods, routes, and test
   fixtures without an established requirement.
4. **SQLite integration tests.** These are easy to run, but SQLite does not
   reproduce PostgreSQL UUID, constraint, transaction, locking, or upsert
   behavior and could give false confidence.
5. **Migrate operational and workflow repositories together.** This could
   remove the mixed-persistence period, but it would combine two transaction
   models and substantially expand issue #32 beyond its operational-data scope.

## Decision

OpsMind will use PostgreSQL for durable shared operational data, SQLAlchemy 2.x
synchronous APIs with Psycopg 3 for database access, and Alembic as the sole
schema-migration mechanism.

The first PostgreSQL repository persists only:

1. Products
2. Current inventory positions
3. Daily demand observations

The existing `ProductInventoryRepository` remains the domain-facing boundary.
The PostgreSQL adapter accepts and returns existing immutable domain objects;
SQLAlchemy rows remain internal to the persistence package and are converted by
explicit typed mapping helpers. Domain modules do not import SQLAlchemy,
Psycopg, Alembic, sessions, engines, or ORM models.

Synchronous sessions match the current synchronous application and repository
design. One short-lived session owns each repository operation or explicitly
defined transaction. Writes commit completely or roll back, and failed sessions
are closed. Runtime code never creates schema through `metadata.create_all()`;
Alembic owns upgrades and downgrades.

The schema uses one authoritative SQLAlchemy metadata object with deterministic
names for primary keys, foreign keys, unique constraints, check constraints,
and indexes. Product foreign keys use restrictive deletion behavior because no
product-deletion API exists.

Integration tests use a real, dedicated PostgreSQL database. Destructive test
setup rejects URLs unless the host is local or loopback and the database name
ends in `_test` or `_testing`. SQLite is not used as a compatibility substitute.

The in-memory operational repository remains available and is the temporary
default during the phased migration. Explicit repository injection continues
to override backend selection. This preserves isolated unit tests and existing
startup behavior while PostgreSQL is selected deliberately through typed
configuration.

Persistence is intentionally split into two milestones:

1. Operational products, inventory, and demand
2. Recommendation reviews, decisions, and audit events

The second milestone must preserve ADR-0004 by storing workflow state and its
matching audit event in one PostgreSQL transaction. Merely storing those records
in separate tables would not satisfy the accepted atomicity requirement.

## Rationale

PostgreSQL supplies the durable relational constraints, transactional writes,
concurrent uniqueness, and shared state needed by OpsMind's operational source
data. SQLAlchemy provides a typed, testable adapter without coupling the domain
or HTTP schemas to ORM objects. Alembic makes schema history explicit and
repeatable across local development, CI, and future deployments.

Keeping the repository synchronous avoids a broad architectural conversion
that is unrelated to the current product need. Keeping workflow persistence
separate lets this issue validate operational transactions and migrations while
retaining ADR-0004 as an explicit requirement for the next persistence step.

## Consequences

### Positive

- Operational source data survives application restart.
- Applications using the same database observe shared products, inventory, and
  demand.
- Database constraints protect canonical SKU and product/date uniqueness.
- Inventory upsert and demand-batch transactions handle concurrent writes.
- Existing domain, repository, API, forecast, exposure, and reorder contracts
  remain stable.
- Alembic provides a single auditable schema history.
- Memory-backed tests and isolated development remain available.
- Real PostgreSQL tests validate behavior that SQLite cannot represent.

### Negative

- Developers and CI now require PostgreSQL for integration validation.
- SQLAlchemy, Psycopg, and Alembic add dependency and upgrade maintenance.
- Connection lifecycle, migrations, transaction rollback, and database test
  cleanup become ongoing operational responsibilities.
- The application temporarily has mixed durability.
- Local Compose volumes consume disk and require explicit lifecycle management.

### Neutral

- The migration-phase default remains `memory`.
- Forecasts, stockout results, and calculated reorder results remain computed
  on demand and unpersisted.
- Recommendation reviews, decisions, and audit events remain process-local,
  restart-volatile, and cross-worker isolated.
- PostgreSQL does not add authentication, deployment, backup, replication, or
  production-readiness guarantees.

## Security, operations, cost, and learning impact

- **Security:** Database URLs are secret values, are not stored in Alembic
  configuration, and must not appear in logs, validation output, HTTP errors,
  or documentation using real values. SQLAlchemy uses parameterized statements.
- **Operations:** Schema changes require Alembic. Application-owned engines are
  disposed during shutdown. Local data remains in a named Compose volume until
  that volume is explicitly deleted.
- **Cost:** Local and GitHub-hosted PostgreSQL use existing development and CI
  capacity. A future managed PostgreSQL deployment will require a separate cost,
  security, backup, availability, and networking decision.
- **Learning:** The design demonstrates repository adapters, relational
  constraints, migrations, transaction rollback, concurrency, and explicit
  domain/ORM mapping without hiding the mixed-persistence tradeoff.

## Risks and mitigations

- **ORM models leak across boundaries:** keep them under the PostgreSQL package
  and return only explicit domain mappings.
- **Migration and metadata drift:** test constraints and upgrade/downgrade
  behavior against real PostgreSQL and use the same metadata in Alembic.
- **Failed transactions poison later work:** roll back before translating known
  conflicts and create a new session per operation.
- **Demand batches partially persist:** insert the complete batch in one
  transaction and roll back the transaction on any conflict.
- **Concurrent writes bypass application checks:** rely on PostgreSQL unique
  constraints and an inventory upsert as the final integrity boundary.
- **Secrets appear in diagnostics:** use secret-wrapped settings, hidden SQL
  parameters, generic configuration messages, and client-safe API errors.
- **Tests damage the wrong database:** require a dedicated test variable, local
  host, and explicit `_test` or `_testing` database suffix before cleanup.
- **Mixed persistence is overstated:** document that workflow and audit history
  remain volatile until the next milestone.

## Mixed-persistence limitation

With PostgreSQL selected, products, inventory, and demand are durable and
shared. Recommendation reviews, decisions, and audit events are still stored in
one in-memory repository per application instance. Restarting an application
therefore retains operational data but loses its workflow state and history.
Multiple application workers share operational source data but do not share
reviews or audit events.

This is not complete application durability, a durable approval system, a
cross-worker workflow, or a compliance-grade audit ledger.

## Migration path

1. Keep `memory` as the default and select PostgreSQL explicitly.
2. Apply Alembic revision `0005_operational_data` before PostgreSQL-backed
   application traffic.
3. Validate operational persistence, restart durability, shared state,
   concurrency, and analytical regressions.
4. Review and accept or reject this ADR through the repository-owner process.
5. In a separate issue, model recommendation reviews and audit events in
   PostgreSQL while preserving ADR-0004 through one database transaction.
6. Reconsider the default backend only after all required persistence and
   operational safeguards are approved.

## Validation

Validate with locked dependency synchronization; Ruff; strict mypy; memory-only
tests; migration upgrade, downgrade, and idempotence tests; real-PostgreSQL
repository, concurrency, restart, shared-application, and analytical tests;
reverse-order execution; coverage; Compose validation; governance, links,
secret patterns, protected-file hashes, and generated-artifact review.

## Reconsideration triggers

- The application requires async-only database dependencies or measured async
  throughput benefits.
- The repository contract no longer represents required transactional work.
- Recommendation workflow and audit persistence is introduced.
- PostgreSQL deployment, backup, replication, pooling, or high availability is
  designed.
- Multi-tenancy, row-level security, or data-retention requirements emerge.
- A different persistence technology demonstrates a concrete product benefit.

## Implementation notes

- ADR-0005 remains Proposed until the repository owner explicitly accepts it.
- The initial revision identifier is `0005_operational_data`.
- PostgreSQL 17 is the pinned major line for local Compose and CI.
- No production database, deployment manifest, API container, or cloud resource
  is introduced by issue #32.

## References

- [ADR-0000: Use Architecture Decision Records](0000-use-architecture-decision-records.md)
- [ADR-0003: Select Backend Application Structure](0003-select-backend-application-structure.md)
- [ADR-0004: Co-locate Recommendation Workflow State and Audit Events](0004-co-locate-recommendation-workflow-state-and-audit-events.md)
- [Architecture Decision Record index](README.md)
- [Repository README](../../../README.md)
- [Contribution guide](../../../CONTRIBUTING.md)
- [Current project status](../../09-status/current-status.md)
- GitHub issue #32: Implement PostgreSQL operational data persistence
