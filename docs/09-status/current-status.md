# OpsMind Current Status

This document is the detailed authority for the current project state. The
[roadmap](../../ROADMAP.md) defines phase order and gates; architecture and
phase-review documents preserve the decisions and evidence that established
earlier states.

- Status date: 2026-08-10
- Current formal gate: Phase 8 — containerization and delivery foundation
- Active workstream: Issue #68 Phase 8A containerization implementation review
- Issue #64 result: complete; PR #65 merged and Issue #64 closed
- Issue #58 result: complete; PR #59 merged and Issue #58 closed
- ADR-0006 result: accepted and merged through PR #61; Issue #60 closed
- Issue #62 result: complete; PR #63 merged and Issue #62 closed
- ADR-0007 result: Accepted by the repository owner on 2026-08-10
- Issue #66 result: complete; PR #67 merged and Issue #66 closed
- Issue #68 result: implementation prepared on its bounded branch; owner review
  and merge pending

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
| 7 | Testing, security, and observability hardening | Complete | Owner accepted Proceed under Issue #64 on 2026-08-09 |
| 8 | Cloud deployment and product delivery | Current | ADR-0007 Accepted; Phase 8A implementation under Issue #68 |
| 9–12 | Data pipelines, MLOps, advanced AI, and production readiness | Planned | Not formally opened |

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
- fail-closed RS256 bearer authentication with bounded trusted principals and
  explicit read, write, and recommendation-decision permissions;
- trusted terminal-decision and audit-event actor attribution;
- deterministic Phase 4, Phase 5, and Phase 6 evaluation evidence.

ADRs 0000 through 0007 are Accepted. On 2026-08-08, the repository owner accepted ADR-0006 and
authorized a separately governed Phase 7 security implementation.

PR #61 squash-merged the accepted ADR as
`3e8b0a78344cc0164a35c268fa119d9c5321de50`. Its canonical tree exactly matched
the reviewed acceptance tree, post-merge workflows passed, and design Issue
#60 was closed after implementation Issue #62 was created.

## Phase 7 Progress

The repository owner accepted the Phase 7 hardening plan under Issue #54. All
four governed technical workstreams are merged. On 2026-08-09, the owner
accepted the integrated review under Issue #64 with a formal `Proceed` decision.
PR #65 merged the accepted record as
`984826a9fc1c16c0a7a1a30006cad120f301cd8d`; Phase 7 is Complete.

### Phase 7A — testing and coverage hardening

Phase 7A is complete. Issue #56 is closed and PR #57 merged as canonical commit
`784c9055a393b3febd030ae8d9ce7d82fb110e4a`. The accepted regression gate is
95.00% combined line-and-branch coverage. The work also removed the previously
observed Starlette `TestClient` deprecation warning. See
[Phase 7A testing and coverage hardening](../01-architecture/phase-7-testing-coverage-hardening.md).

### Issue #58 — observability and readiness

The repository owner accepted the Issue #58 pre-implementation design on
2026-08-07. PR #59 was squash-merged into canonical `main` on 2026-08-08 as
`f12082db31359a734b012867267de970cabcfa1a`, and Issue #58 closed automatically.
The merge tree exactly matched the reviewed feature tree. Both post-merge
Python-quality and repository-governance workflows passed. Issue #58 is
complete and contributes to the accepted integrated Phase 7 gate.

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
read-only workflow permissions, bounded request/readiness output, signed bearer
validation, action permissions, trusted terminal-decision attribution, and
human pull-request review.

Current limitations include:

- no provisioned production identity provider, credential lifecycle, or key
  rotation service;
- no application user/session database, tenant boundary, row-level policy, or
  enterprise RBAC/ABAC;
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

### Issue #62 — ADR-0006 security implementation

Issue #60 governed the ADR-0006 decision and closed after PR #61 merged the
accepted record. Issue #62 implements a
provider-agnostic, application-validated bearer principal with three bounded
permissions: `business:read`, `business:write`, and
`recommendation:decide`. It requires deriving terminal decision and audit actor
identity from the trusted principal rather than caller-supplied `decided_by`,
while keeping `/health` and `/ready` unauthenticated and bounded.

The implementation uses PyJWT with the `crypto` extra and one configured RS256
public key with an enforced 2,048-bit RSA minimum. It validates one issuer, one
strict audience, required expiration, optional `nbf`, a bounded stable subject,
and a strict list-valued permissions claim. Missing configuration denies every
protected request. Public probes and API-description endpoints remain public.
PR #63 was squash-merged on 2026-08-09 as
`575fd03eab2ebf5dc221ae1d52e44802ddaf7970`; Issue #62 closed automatically.
The canonical merge tree exactly matches the reviewed feature tree, and both
post-merge workflows passed. Final PostgreSQL-backed validation passed 648 tests
with zero skips or warnings, 97.65% statement coverage, 88.72% branch coverage,
and 96.25% combined coverage.

### Issue #64 — integrated Phase 7 review

The integrated review maps the accepted 20 Phase 7 exit criteria across Phase
7A testing, Issue #58 observability/readiness, accepted ADR-0006, and Issue #62
security. Criteria 1–19 pass with canonical evidence. On 2026-08-09, the
repository owner accepted `Proceed`, satisfying criterion 20 and authorizing
Phase 8 design/planning. PR #65 squash-merged the review on 2026-08-09 as
`984826a9fc1c16c0a7a1a30006cad120f301cd8d`; Issue #64 closed automatically.
Its canonical tree `8f8cb3e8da65b9768f26b0e0166a0c9f3d873afa` exactly matches the
reviewed acceptance tree. Post-merge Repository checks run `31345098172` and
Python quality run `31345098175` passed. The durable review is
[Phase 7 Review](../12-phase-reviews/phase-7-review.md).

## Phase 8 Architecture and Phase 8A Delivery Foundation

Issue #66 established the accepted
[ADR-0007](../01-architecture/decisions/0007-select-phase-8-zero-cost-cloud-deployment-and-product-delivery-architecture.md)
after comparing three current architectures using official sources. It defines a real
portfolio environment targeting `$0` recurring infrastructure cost at bounded
usage:

- a reproducible non-root API image built by GitHub Actions, scanned, and
  published to public GHCR with an immutable Git identity;
- a Render Blueprint-managed Free image-backed FastAPI service with managed
  HTTPS, explicit cold-start UX, health/readiness checks, deliberate immutable
  image deploys, and bounded rollback;
- Neon Free PostgreSQL with pooled application traffic, direct controlled
  Alembic migration, scale-to-zero, SSL, bounded restore, and a future pgvector
  path;
- ZITADEL Free authorization code plus PKCE, RS256 JWT access tokens, exact
  OpsMind audience and project-role claims, bounded JWKS validation, and exact
  role-to-permission mapping under ADR-0006;
- a React/TypeScript/Vite dashboard hosted on Cloudflare Pages Free;
- Terraform for supported Cloudflare and ZITADEL resources, HCP Terraform Free
  state, Render-native Blueprint IaC for the Free API service, and an explicit
  Neon bootstrap exception where no first-party Terraform provider exists;
- existing structured application logs plus Render deploy/log evidence and
  request-ID troubleshooting;
- a separate LocalStack Hobby AWS skills track and an honest AWS translation
  architecture, neither represented as actual AWS deployment.

The former approximately `$50–65/month` ECS/Fargate, ALB, RDS PostgreSQL,
Cognito, ECR, S3/CloudFront, and CloudWatch proposal remains preserved as a
technically credible paid AWS reference and future migration option. It is not
the active implementation target because it violates the owner’s `$0`
recurring-cost requirement.

The repository owner accepted ADR-0007 on 2026-08-10. PR #67 squash-merged the
accepted record as `733f405ef89c38a2b09b95587bdbd77b938ee853`, its canonical
tree exactly matched the accepted design tree, both post-merge workflows
passed, and Issue #66 closed.

Issue #68 is the bounded Phase 8A implementation. Its review branch adds:

- a digest-pinned official Python 3.13 slim multi-stage image built with pinned
  `uv` and the committed lockfile;
- a non-editable installed OpsMind package with production dependencies only;
- numeric non-root execution, a read-only-compatible runtime, no additional
  Linux capabilities, and one signal-aware Uvicorn worker;
- runtime `PORT` selection, `/health` Docker liveness, and unchanged `/ready`
  dependency semantics;
- explicit external Alembic migration support without startup migration or
  schema creation;
- disposable memory and PostgreSQL 17 container validation covering migration,
  readiness, authentication, image contents, metadata, and graceful shutdown;
- build-only `linux/amd64` container CI with a repeat-build functional check.

The existing PostgreSQL-only developer Compose definition and its normal data
volume remain unchanged. The Phase 8A validator uses separate, uniquely named,
disposable resources. Phase 8A does not publish an image or introduce a cloud
service, deployment, secret, dependency, migration, application behavior,
frontend, infrastructure as code, or production-readiness claim.

Local Phase 8A evidence passed two explicit `linux/amd64` builds on Apple
Silicon, the complete disposable memory/PostgreSQL contract, and the repeat
memory contract. The runtime image measured 64.90 MiB through Docker. The full
PostgreSQL-backed Python gate passed 648 tests with zero skips or warnings and
96.25% combined line-and-branch coverage. Digest-pinned Trivy 0.72.0, using a
database updated at `2026-08-10T18:43:54Z`, reported zero fixed high or critical
findings. Hosted pull-request checks remain pending until the branch is pushed
and its pull request is opened.

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
- Issue #58 itself did not add security; the separate accepted ADR-0006 boundary
  is implemented under Issue #62 without changing readiness semantics.

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

The immediate permitted work is repository-owner review of Issue #68 and its
Phase 8A pull request. Phase 8A remains incomplete until that pull request is
accepted and merged.

Phase 8B–8E, cloud resource creation, frontend implementation, deployment,
identity-provider configuration, Terraform/HCP Terraform, Render Blueprint,
LocalStack, and production-readiness work remain unauthorized pending their
documented gates.
Phase 9 data pipelines, Phase 10 MLOps, and Phase 11 LLM/RAG/LangGraph work
remain Planned.
