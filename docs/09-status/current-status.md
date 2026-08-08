# OpsMind Current Status

This document is the detailed authority for the current project state. The
[roadmap](../../ROADMAP.md) defines phase order and gates; architecture and
phase-review documents preserve the decisions and evidence that established
earlier states.

- Status date: 2026-08-08
- Current formal gate: Phase 7 — testing, security, and observability hardening
- Active workstream: Issue #58 — application observability and readiness
- Issue #58 result: implementation and local validation complete; final
  repository-owner review, hosted pull-request validation, and merge pending

## Canonical Phase Status

| Phase | Focus | Formal status | Current finding |
| --- | --- | --- | --- |
| 0 | Project definition, scope, governance, and readiness | Complete | Owner-accepted review |
| 1 | Repository and local development foundation | Complete | Delivered and retrospectively reviewed |
| 2 | Product data and transactional backend | Complete | Delivered and retrospectively reviewed |
| 3 | Web workflow for product and demand operations | Complete | Delivered and retrospectively reviewed |
| 4 | Forecasting baseline and evaluation | Complete | Owner-accepted Proceed review under Issue #48 |
| 5 | Stockout risk and reorder recommendations | Complete | Owner-accepted Proceed review under Issue #50 |
| 6 | Decision approval, rejection, and audit history | Complete | Owner-accepted Proceed review under Issue #52 |
| 7 | Testing, security, and observability hardening | Current | Phase 7A complete; Issue #58 awaiting final review and merge |
| 8–12 | Cloud, pipelines, MLOps, advanced AI, and production readiness | Planned | Not formally opened |

Implementation delivery and formal phase completion remain separate. Phases 5
and 6 were partly delivered ahead of their gates, but their later
repository-owner-accepted reviews completed those phases.

## Current Product and Architecture

OpsMind currently provides a packaged FastAPI modular monolith with:

- product, inventory, demand-history, forecast, stockout-exposure, reorder,
  recommendation-review, and audit-history APIs under the configured versioned
  business prefix;
- UUID product identifiers, normalized SKUs, atomic demand batches, and
  deterministic domain calculations;
- immutable recommendation/evidence snapshots, one-way review decisions, and
  ordered audit history;
- isolated, restart-volatile memory repositories;
- shared, restart-durable PostgreSQL operational and workflow repositories;
- SQLAlchemy, Psycopg, Alembic, and migration head
  `0006_workflow_persistence`;
- an application factory that owns application-created resources while
  preserving caller ownership for explicit injections;
- deterministic Phase 4, Phase 5, and Phase 6 evaluation evidence.

ADRs 0000 through 0005 are Accepted. ADR-0006 has not been created or accepted;
trusted-principal and security implementation therefore remain blocked.

## Phase 7 Progress

The repository owner accepted the Phase 7 hardening plan under Issue #54.

### Phase 7A — testing and coverage hardening

Phase 7A is complete. Issue #56 is closed and PR #57 merged as canonical commit
`784c9055a393b3febd030ae8d9ce7d82fb110e4a`. The accepted regression gate is
95.00% combined line-and-branch coverage. The work also removed the previously
observed Starlette `TestClient` deprecation warning. See
[Phase 7A testing and coverage hardening](../01-architecture/phase-7-testing-coverage-hardening.md).

### Issue #58 — observability and readiness

The repository owner accepted the Issue #58 pre-implementation design on
2026-08-07. The implementation is complete on
`feat/phase-7-observability-readiness`; final owner review, hosted checks, and
merge remain pending. This is not a claim that Issue #58 is closed or that
Phase 7 is complete.

#### HTTP observability checkpoint

Commit `511c4bf650179bc42a3667a9a10b051b2561fcae` implements:

- bounded caller request-ID validation and server-generated replacement;
- pure ASGI middleware with request-state and response-header correlation;
- one machine-parseable, seven-field JSON event per HTTP request;
- low-cardinality matched route templates and a bounded unmatched route value;
- monotonic request duration and bounded error categories;
- idempotent `opsmind.http` logger configuration;
- safe unexpected pre-response `500` handling with `unhandled_exception`;
- post-response-start `streaming_error` logging and re-raising.

Its independent validation passed 569 tests with zero skips, included
PostgreSQL integration, and achieved approximately 95.96% combined coverage,
above the 95.00% gate.

#### Readiness checkpoint

Commit `204c1e2961a58d8436fb7601af4a0137f55640cc` implements:

- immutable, typed, bounded readiness results and a readiness protocol;
- immediate, no-I/O memory readiness;
- PostgreSQL connectivity and exact supported-revision readiness using the
  application-owned Engine;
- an unversioned `GET /ready` endpoint with bounded `200`/`503` responses;
- lazy startup, no automatic migration or schema repair, and no secondary
  Engine;
- unchanged `/health` process-liveness behavior;
- `dependency_unavailable` request-event classification for known readiness
  failure.

Its final PostgreSQL-backed validation passed 585 tests with zero skips and no
warnings. Ruff and strict mypy passed across 112 source files, Alembic reported
head `0006_workflow_persistence`, statement coverage was 97.54%, branch
coverage was 87.90%, combined coverage was 96.05%, and `readiness.py` was fully
covered.

The accepted design, implementation matrix, evidence, and residual limitations
are recorded in
[Phase 7 observability and readiness](../01-architecture/phase-7-observability-readiness.md).

## Issue #58 Implementation Matrix

| Area | Accepted behavior | Result |
| --- | --- | --- |
| Request correlation | Generated ID; valid propagation; malformed, duplicate, blank, or oversized replacement; response and request-state correlation | Complete |
| Structured event | Exactly seven bounded fields in machine-parseable JSON | Complete |
| Route classification | Matched template or bounded unmatched value; no concrete high-cardinality path | Complete |
| Timing | Monotonic non-negative duration | Complete |
| Event count | Exactly one governed request event | Complete |
| Privacy | No query, body, credentials, SQL, raw exception, or traceback in governed output | Complete |
| Handled errors | Bounded client, server, and dependency-unavailable categories | Complete |
| Unexpected errors | Safe pre-start `500`; `unhandled_exception`; post-start `streaming_error`; exception re-raise; no `BaseException` swallowing | Complete |
| Liveness | `/health` exact contract and no dependency probe | Complete |
| Readiness | Unversioned `/ready`, bounded `200`/`503`, memory and PostgreSQL checks | Complete |
| PostgreSQL schema | Connectivity plus exact `0006_workflow_persistence`; missing, wrong, multiple, or unavailable state is not ready | Complete |
| Lifecycle | Lazy startup; app-owned Engine reuse; explicit-resource ownership preserved; no migration or repair | Complete |
| OpenAPI | `/ready` documented; `/api/v1/ready` absent | Complete |
| Scope exclusions | Security, cloud, deployment, external telemetry, HA/DR, backup/restore, and Phase 8 absent | Complete |

## Validation and Repository Controls

The current repository requires:

- locked dependency synchronization and lock verification with `uv`;
- Ruff formatting and linting;
- strict mypy;
- pytest with the 95.00% combined line-and-branch coverage gate;
- PostgreSQL 17 integration tests when database behavior is in scope;
- repository-governance, Markdown, link, and secret-pattern checks;
- pull-request review before merge.

Local and CI destructive PostgreSQL fixtures require a loopback host and a
database name ending in `_test` or `_testing`. Runtime application code does not
create or migrate tables; Alembic remains the schema owner.

## Security, Privacy, Operations, and Cost

Current safeguards include environment-supplied PostgreSQL credentials,
secret-aware settings, ignored local environment files, pinned GitHub Actions,
read-only workflow permissions, bounded request/readiness output, and human
pull-request review.

Current limitations include:

- no authentication, authorization, RBAC, or verified reviewer identity;
- caller-supplied and unverified actor strings;
- no cryptographic signatures, hash chaining, tamper-evident audit store, or
  compliance-ledger guarantee;
- no production database, network-security posture, secret rotation, backup,
  restore, replication, or high availability;
- no production log collection, monitoring, alerting, service-level objectives,
  or incident-response system;
- no API container, AWS infrastructure, cloud deployment, or
  production-readiness approval.

No AWS resources or managed production services exist. Tests and evaluations
use synthetic or controlled data; no production, customer, personal, or
regulated data is required.

## Issue #58 Residual Limitations

These limitations are non-blocking for the accepted Issue #58 scope:

- route classification relies on FastAPI behavior pinned by the current
  dependency set and should be rechecked on framework upgrades;
- malformed or nonconforming downstream ASGI behavior is outside the governed
  middleware contract;
- production log collection and external telemetry backends remain future
  infrastructure work;
- readiness proves bounded local application/backend compatibility, not HA/DR,
  monitoring coverage, or production readiness;
- security remains intentionally blocked pending ADR-0006.

## Historical Evidence

Historical implementation and phase-review documents remain authoritative for
the state they record, but they are not the current-state authority. In
particular, earlier statements that memory was the only repository, that Phases
5 or 6 were gate pending, or that the Starlette warning was unresolved describe
earlier milestones.

Accepted phase reviews are stored under
[`docs/12-phase-reviews`](../12-phase-reviews), and durable evaluation evidence
is stored under [`docs/05-evaluation`](../05-evaluation).

## Next Permitted Work

The immediate work is final review, hosted validation, and repository-owner
merge authorization for Issue #58. Do not treat implementation completion as
owner acceptance or merge completion.

After Issue #58 is accepted and merged, synchronize and clean its feature
branch. Only then may separately governed ADR-0006 security-boundary work be
prepared. Authentication, authorization, trusted-principal behavior, Phase 8,
deployment, and production-readiness work remain unauthorized.
