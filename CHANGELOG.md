# Changelog

All notable changes to OpsMind will be documented in this file.

The project follows the principles of Keep a Changelog. Versioning will begin
when the first application release is defined.

## Unreleased

### Phase 8 deployment and product-delivery design

- Proposed ADR-0007 with three current AWS architecture/cost candidates and a
  cost-aware ECS/Fargate, RDS PostgreSQL, Cognito, React/Vite, CloudFront, and
  Terraform recommendation.
- Defined the first integrated dashboard, authenticated full-stack slice,
  Phase 8A–8D gates, and explicit Phase 9–11 deferrals without implementing or
  provisioning anything.

### Phase 7 observability and readiness

- Added bounded request-ID propagation, structured HTTP request events, and a
  safe unexpected-error boundary.
- Added unversioned application readiness with memory and PostgreSQL
  connectivity/schema-revision semantics while preserving `/health` as process
  liveness.
- Recorded the completed Issue #58 implementation and validation evidence for
  final repository-owner review.

### Phase 7 trusted-principal security

- Added fail-closed signed bearer authentication with a bounded trusted
  principal and explicit business-read, business-write, and
  recommendation-decision permissions.
- Protected business routes while preserving unauthenticated health,
  readiness, and API-documentation surfaces.
- Replaced caller-controlled recommendation decision attribution with the
  authenticated principal identifier for both decisions and audit events.
- Added bounded 401/403 contracts and OpenAPI bearer-security documentation
  without expanding the governed HTTP event fields.

### Phase 7 integrated review

- Recorded the complete testing, observability, readiness, security, and
  architecture evidence against all 20 accepted Phase 7 exit criteria.
- Recorded the repository-owner-accepted `Proceed` decision with explicit
  infrastructure, product, security, and production limitations.

### Phase 6 decision-review and audit evaluation

- Added the accepted Phase 6 decision-review/audit evaluation design.
- Added deterministic `phase6-synthetic-v1` workflow-policy evaluation with
  12/12 governed scenarios passing.
- Recorded direct PostgreSQL rollback, concurrency, sharing, restart-durability,
  and application resource-ownership evidence.
- Validated 117 focused tests, 41 targeted Phase 6 PostgreSQL tests, 56 complete
  PostgreSQL integration tests, and 499 complete PostgreSQL-backed tests with
  zero skips.
- Recorded byte-identical Phase 6 evaluation artifacts and stable SHA-256
  evidence.
- Recorded the owner-accepted Phase 6 `Proceed` review under Issue #52.
- Prepared merged-state governance so Phase 6 is Complete and Phase 7 becomes
  Current after the Issue #52 pull request merges.
- Kept authentication, authorization, actor verification, cryptographic audit
  integrity, compliance guarantees, external ordering, deployment, and
  production-readiness work outside Phase 6.


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
* Deterministic Phase 4 synthetic demand dataset with nine governed patterns.
* Temporal baseline-forecast evaluation with explicit no-leakage windows.
* MAE, signed forecast bias, and WAPE evaluation metrics.
* Deterministic JSON and Markdown evaluation reporting.
* `python -m opsmind.evaluation` developer command with overwrite protection.
* Durable Phase 4 evaluation design, measured report, and proposed phase review.
* Deterministic stockout exposure.
* Deterministic reorder recommendations.
* Governed Phase 5 deterministic stockout/reorder scenario-conformance
  evaluation with reproducible JSON and Markdown evidence.
* Owner-accepted Phase 5 `Proceed` review under Issue #50, including explicit
  acceptance of the documented decision-quality limitations.
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
* Recorded Phase 4, forecasting baseline and evaluation, as Complete after
  repository-owner acceptance of the Issue #48 Proceed decision.
* Recorded Phase 5, stockout risk and reorder recommendations, as Current.
* Recorded Phase 6 capability as delivered ahead of its formal gate rather than
  formally complete.
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

* Real-world forecast validation on governed operational data.
* Probabilistic forecasting, prediction intervals, or trained forecast models.
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
