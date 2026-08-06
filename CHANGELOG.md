# Changelog

All notable changes to OpsMind will be documented in this file.

The project follows the principles of Keep a Changelog. Versioning will begin
when the first application release is defined.

## Unreleased

### Added

* Repository governance, contribution rules, and automated-agent boundaries.
* Phase-based roadmap and phase-review process.
* GitHub issue and pull-request templates.
* Repository-governance validation workflow.
* Architecture Decision Record process.
* Accepted ADRs 0000 through 0005.
* Reproducible Python project using `uv`, `.python-version`, `pyproject.toml`,
  and `uv.lock`.
* Ruff formatting and linting, mypy static type checking, pytest, pytest-cov,
  and Python-quality continuous integration.
* Packaged FastAPI modular-monolith application foundation.
* Typed application settings and dependency-injection boundaries.
* Unversioned process-health endpoint.
* Versioned product, inventory, and demand business APIs.
* Product creation, deterministic listing, and UUID retrieval.
* Current-inventory replacement and retrieval.
* Atomic demand-batch ingestion.
* Chronological demand retrieval with inclusive date filtering.
* Deterministic arithmetic-mean demand forecast.
* Deterministic stockout exposure.
* Deterministic reorder recommendations.
* Recommendation approval and rejection workflow.
* Immutable recommendation and evidence snapshots.
* Normalized idempotent terminal-decision retries.
* Conflict and concurrent-decision protection.
* Ordered recommendation audit-event history.
* Supported in-memory operational and recommendation-workflow repositories.
* SQLAlchemy and Psycopg PostgreSQL persistence.
* Alembic migration `0005_operational_data` for products, inventory positions,
  and demand observations.
* Alembic migration `0006_workflow_persistence` for recommendation reviews,
  decisions, evidence, and audit events.
* PostgreSQL operational persistence shared between applications using the
  same database.
* PostgreSQL recommendation-workflow and audit persistence.
* PostgreSQL restart durability.
* Application-level coordinated operational and workflow repository selection.
* Application ownership and disposal of application-created PostgreSQL
  infrastructure.
* Preservation of caller ownership for explicitly injected repositories and
  related resources.
* Local and CI PostgreSQL 17 integration testing.
* Transaction, rollback, constraint, sharing, restart-durability, concurrency,
  and migration validation.
* Accepted roadmap-phase reconciliation through PR #45.
* Retrospective Phase 1, Phase 2, and Phase 3 reviews.

### Changed

* Reconciled the formal roadmap with implementation merged through PR #43.
* Recorded Phases 1 through 3 as retrospectively complete.
* Recorded Phase 4, forecasting baseline and evaluation, as Current.
* Recorded Phase 5 and Phase 6 capabilities as delivered ahead of their formal
  gates rather than formally complete.
* Distinguished implementation delivery from formal phase completion.
* Distinguished isolated, restart-volatile memory behavior from shared,
  restart-durable PostgreSQL behavior.
* Preserved historical memory-only descriptions while labeling them as
  historical rather than current universal behavior.
* Clarified that Alembic exclusively owns PostgreSQL schema creation and
  migration.
* Clarified application-created versus explicitly injected PostgreSQL resource
  ownership.

### Not Yet Implemented

* Formal forecast-baseline evaluation and temporal backtesting.
* Measured forecast accuracy and approved forecast-error metrics.
* Formal Phase 5 and Phase 6 completion.
* Calibrated stockout probability or learned stockout model.
* Supplier, pack-size, safety-stock, service-level, and cost optimization.
* Purchase-order creation or external ordering integration.
* User authentication.
* Role-based authorization.
* Verified recommendation-reviewer identity.
* Cryptographically signed, hash-chained, or tamper-evident audit history.
* Compliance-ledger guarantees.
* Frontend user interface.
* API containerization.
* AWS infrastructure.
* Cloud deployment.
* Production database provisioning.
* Backup, restore, replication, or high availability.
* Production monitoring, alerting, service-level objectives, or incident
  response.
* Production secret-management and rotation workflow.
* Governed model lifecycle.
* Trained machine-learning or advanced-AI production capabilities.
* Production-readiness approval.
