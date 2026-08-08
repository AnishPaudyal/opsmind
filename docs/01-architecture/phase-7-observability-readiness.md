# Issue #58 — Application Observability and Readiness Design Decision

Status: Accepted design; implementation complete; final owner review pending
Governed by: Issue #58
Owner acceptance: Anish Paudyal, 2026-08-07
Accepted design candidate SHA-256: `d200954d30b1534820325ab1e5bce5cea36eaf140ac847213bc7adfd7706d92c`
Accepted review SHA-256: `aacba46e60875b8224af93395a559a3dab8f168df70328706378b9f9305edf58`
Base commit: `784c9055a393b3febd030ae8d9ce7d82fb110e4a`
Phase: 7 — testing, security, and observability hardening

## Purpose

Define the dependency-light application observability and readiness contract
before modifying runtime behavior.

This design does not authorize authentication, authorization, ADR-0006,
security implementation, cloud monitoring, deployment, or Phase 8 work.

## Pre-Implementation Architecture Evidence

The current application has one authoritative factory: `create_app()`.

That factory already owns:

- resolved application settings;
- memory versus PostgreSQL persistence selection;
- creation of the application-owned PostgreSQL engine;
- creation of repository session factories;
- repository dependency overrides;
- application lifespan disposal of the owned engine;
- API-router composition.

`GET /health` is explicitly process/liveness health and performs no downstream
dependency check.

PostgreSQL engine construction is intentionally lazy: creating the Engine does
not establish a database connection.

Application startup does not create missing database tables.

Runtime application code currently has no application request-logging
foundation. Alembic has migration logging configuration, but that is not the
runtime API observability contract.

Expected domain failures are currently translated locally in API routes into
bounded `HTTPException` responses. No application-wide request middleware or
global runtime API exception layer currently exists.

## Decision 1 — Application Integration Seam

`create_app()` remains the authoritative integration seam.

Issue #58 will not create a second database engine or a second configuration
path for readiness.

When PostgreSQL is selected, the same application-owned Engine used to construct
repository session factories will also back the readiness probe.

When memory persistence is selected, readiness performs no external I/O.

## Decision 2 — Request-ID Contract

Canonical request/response header:

`X-Request-ID`

A caller-provided identifier is accepted only when:

- exactly one `X-Request-ID` value is present;
- its length is between 1 and 64 characters;
- its first character is ASCII alphanumeric;
- every remaining character is ASCII alphanumeric, `.`, `_`, or `-`.

Equivalent validation expression:

`[A-Za-z0-9][A-Za-z0-9._-]{0,63}`

Valid caller IDs are propagated unchanged.

Absent, blank, duplicate, malformed, or oversized caller IDs are ignored and
replaced with a server-generated UUID string.

An invalid tracing header will not create a new business-API 4xx contract.

The effective request ID is stored in request scope state and emitted through
the canonical response header.

## Decision 3 — Middleware Form

Implement one small, local, pure-ASGI HTTP middleware.

The middleware:

1. passes non-HTTP scopes through unchanged;
2. resolves the effective request ID before downstream execution;
3. stores the ID in request scope state;
4. measures elapsed time with a monotonic standard-library timer;
5. intercepts `http.response.start`;
6. records the actual response status;
7. sets exactly one canonical `X-Request-ID` response header;
8. classifies the matched route after routing has occurred;
9. emits exactly one bounded request event.

No external middleware dependency is introduced.

## Decision 4 — Route Classification

Logs use the matched route template rather than the concrete request path.

Example:

`/api/v1/products/{product_id}`

not:

`/api/v1/products/98f3...`

This keeps log cardinality bounded and avoids unnecessarily recording
identifier-bearing request paths.

Requests with no matched route use:

`unmatched`

If a failure happens before routing can classify the request, use:

`unknown`

## Decision 5 — Structured Request Event

Use Python standard-library `logging`.

Dedicated logger:

`opsmind.http`

Each completed HTTP request emits one machine-parseable JSON object containing
only governed fields:

- `event`: constant `http_request`;
- `request_id`;
- `method`;
- `route`;
- `status_code`;
- `duration_ms`;
- `error_category`.

The logger must not record:

- query strings;
- request bodies;
- Authorization or authentication headers;
- database URLs;
- database passwords;
- SQL statements;
- SQL parameters;
- recommendation decision notes;
- raw exception messages;
- tracebacks in the governed request event.

The dedicated request logger is configured idempotently so repeated
`create_app()` calls do not create duplicate handlers.

## Decision 6 — Error Categories

The request event uses a bounded error-category vocabulary.

Initial categories:

- `none`;
- `client_error`;
- `dependency_unavailable`;
- `server_error`;
- `unhandled_exception`;
- `streaming_error`.

Suggested status interpretation:

- status below 400 -> `none`;
- 4xx -> `client_error`;
- readiness 503 -> `dependency_unavailable`;
- other 5xx -> `server_error`.

An exception raised before a response starts is classified as
`unhandled_exception`.

An exception after response start is classified as `streaming_error`.

No exception message is included in the governed request event.

## Decision 7 — Unexpected Exception Boundary

For an otherwise-unhandled `Exception` raised before response start:

- emit the bounded request event;
- return a generic HTTP 500 response;
- include the effective `X-Request-ID`;
- expose no internal exception, SQL, database, credential, or traceback detail.

Do not catch `BaseException`.

If the response has already started, do not attempt to replace it. Emit the
bounded `streaming_error` event and re-raise.

Existing handled FastAPI/domain error contracts remain unchanged.

## Decision 8 — Liveness Contract

`GET /health` remains unchanged in meaning and payload.

It answers only whether the API process is alive enough to answer HTTP.

It must not begin checking PostgreSQL or other external dependencies.

A PostgreSQL-configured process can therefore be:

- live; and
- not ready.

That distinction is intentional.

## Decision 9 — Readiness Route

Add one unversioned endpoint:

`GET /ready`

It reports whether the configured application dependencies are ready enough to
serve dependency-backed work.

Successful readiness returns HTTP 200.

Failed readiness returns HTTP 503.

The public response remains bounded and does not expose database URLs,
credentials, SQL, exception messages, or migration SQL.

The response identifies:

- readiness status;
- service;
- environment;
- selected persistence backend;
- bounded persistence check status.

## Decision 10 — Memory Readiness

For `PersistenceBackend.MEMORY`:

readiness is successful after application construction.

The memory readiness probe performs no external I/O.

This means memory readiness is deterministic and process-local.

## Decision 11 — PostgreSQL Readiness

For `PersistenceBackend.POSTGRESQL`, readiness uses the application-owned
SQLAlchemy Engine.

The probe occurs only when `/ready` is called.

Application construction/startup remains lazy and must not require a successful
database connection.

PostgreSQL readiness requires both:

1. successful database connectivity;
2. the database migration revision matching the application-supported Alembic
   head.

Current supported revision:

`0006_workflow_persistence`

A database that is reachable but unmigrated or at the wrong revision is not
ready because it cannot reliably serve the complete current application
contract.

Database unavailability, missing migration metadata, or revision mismatch maps
to the same bounded public `not_ready` outcome.

Internal database exception details are not returned.

## Decision 12 — Readiness Abstraction

Introduce a small application-owned readiness abstraction rather than embedding
database SQL in the route.

Proposed module:

`src/opsmind/readiness.py`

It should contain:

- a typed readiness result;
- a readiness-probe protocol or equivalent small interface;
- memory readiness implementation;
- PostgreSQL readiness implementation;
- the current supported database revision constant.

The API dependency layer exposes the application-bound readiness probe using
the same override pattern already used for repositories and clock.

## Decision 13 — Schema / Route Placement

Extend the existing health/readiness API area rather than create a new
versioned business API.

Proposed changes:

- `src/opsmind/schemas/health.py`
  - preserve `HealthResponse`;
  - add readiness response/check schema.

- `src/opsmind/api/routes/health.py`
  - preserve `/health`;
  - add unversioned `/ready`.

This avoids unnecessary router restructuring.

## Decision 14 — Observability Module

Proposed new module:

`src/opsmind/observability.py`

Responsibilities:

- request-ID constants and validation;
- request-ID generation;
- structured request-event construction;
- bounded error categorization;
- idempotent standard-library request logger configuration;
- pure-ASGI request observability middleware.

It must not contain authentication, authorization, metrics backends, tracing
collectors, AWS integration, or incident-management integration.

## Decision 15 — Testing Plan

Add focused tests before relying on the new behavior.

Observability tests must cover at least:

- generated request ID when absent;
- valid caller ID propagation;
- malformed caller ID replacement;
- duplicate request-ID replacement;
- response header on normal success;
- response header on handled 4xx/422/404 behavior;
- low-cardinality route-template logging;
- exactly one structured request event;
- expected event fields and bounded error category;
- body/header/query-string secrets absent from logs;
- unexpected pre-response exception returns safe 500 with request ID;
- unexpected exception details absent from public response and request event;
- non-HTTP scope pass-through where practical.

Readiness tests must cover at least:

- `/health` exact existing contract unchanged;
- memory `/ready` -> 200;
- PostgreSQL `/ready` -> 200 at current migrated head;
- PostgreSQL unavailable -> 503;
- PostgreSQL schema missing or wrong revision -> 503;
- readiness response contains no database/SQL detail;
- application startup remains lazy when PostgreSQL is configured;
- readiness probe uses the application-owned database boundary;
- OpenAPI documents `/ready`.

The existing combined coverage gate remains 95.00%.

## Decision 16 — Planned Runtime Files

Expected runtime changes are bounded primarily to:

- `src/opsmind/application.py`;
- `src/opsmind/api/dependencies.py`;
- `src/opsmind/api/routes/health.py`;
- `src/opsmind/schemas/health.py`;
- new `src/opsmind/observability.py`;
- new `src/opsmind/readiness.py`.

No runtime dependency change is currently justified.

## Decision 17 — Planned Tests

Expected focused test changes:

- new `tests/unit/test_observability.py`;
- new `tests/unit/test_readiness.py`;
- targeted additions to `tests/unit/test_application.py`;
- targeted additions to `tests/unit/test_health.py`;
- targeted additions to
  `tests/integration/postgresql/test_application_postgresql.py`;
- migration-state readiness coverage may reuse
  `tests/integration/postgresql/test_migrations.py` where that keeps ownership
  clearer.

Exact file ownership may be refined only when implementation evidence justifies
it.

## Decision 18 — Documentation

Create durable Issue #58 architecture/evidence documentation:

`docs/01-architecture/phase-7-observability-readiness.md`

The document will record:

- request-ID policy;
- log event schema;
- sensitive-data boundary;
- liveness versus readiness semantics;
- memory semantics;
- PostgreSQL connectivity/schema semantics;
- dependency decision;
- tests/evidence;
- residual limitations;
- owner-review state.

## Governance Handoff Result

The Phase 7A -> Issue #58 governance handoff is included in the same proposed
documentation delta as this design.

That handoff records:

- PR #57 is merged;
- Issue #56 is closed;
- canonical Phase 7A merge commit is
  `784c9055a393b3febd030ae8d9ce7d82fb110e4a`;
- Phase 7A is complete;
- Issue #58 is the active observability/readiness child;
- branch `feat/phase-7-observability-readiness` is authorized only for Issue #58;
- ADR-0006/security remains blocked;
- cloud/Phase 8 boundaries remain unchanged.

The handoff documentation and this design were repository-owner accepted and
committed before implementation began. The governed implementation is now
complete on the Issue #58 branch; final implementation acceptance and merge
remain pending.

## Owner Acceptance

Owner: Anish Paudyal
Date: 2026-08-07
Decision: Accepted; governed implementation authorized

Accepted statement:

`I accept the Issue #58 application observability and readiness pre-implementation design, including the request-ID, structured logging, liveness/readiness, PostgreSQL schema-readiness, testing, dependency, and documented Phase 7 scope boundaries, and authorize the governed Issue #58 implementation to proceed.`

This acceptance applies to design candidate
`d200954d30b1534820325ab1e5bce5cea36eaf140ac847213bc7adfd7706d92c`,
reviewed in final pre-implementation review
`aacba46e60875b8224af93395a559a3dab8f168df70328706378b9f9305edf58`.

This acceptance does not authorize ADR-0006, authentication, authorization,
trusted-principal behavior, security implementation, cloud deployment,
production monitoring infrastructure, HA/DR, Phase 8, or production-readiness
approval.

## Accepted Implementation Order

The accepted execution sequence was:

1. record repository-owner design acceptance;
2. finalize, stage, and commit the governance handoff and accepted design
   documentation;
3. implement request-ID validation and structured event primitives;
4. implement and test ASGI observability middleware;
5. implement readiness abstraction and memory semantics;
6. integrate readiness through `create_app`;
7. implement `/ready`;
8. add real-PostgreSQL readiness success/failure/schema tests;
9. run focused tests;
10. run full local quality and 95.00% combined coverage validation;
11. run PostgreSQL-backed validation with zero unintended skips;
12. review documentation and residual risks;
13. obtain separate repository-owner acceptance of the completed Issue #58
    implementation result;
14. finalize the pull request and rerun hosted CI before merge.

Steps 1 through 12 are complete. Steps 13 and 14 remain pending; this document
does not claim final owner acceptance or merge completion.

## Implementation Result

The accepted in-scope implementation is complete in two runtime checkpoints.

### HTTP observability checkpoint

Commit `511c4bf650179bc42a3667a9a10b051b2561fcae` provides bounded request-ID
validation and resolution, pure ASGI middleware, response and request-state
correlation, one seven-field structured JSON request event, low-cardinality
route templates, monotonic duration, bounded error categories, idempotent
`opsmind.http` logging, a safe unexpected pre-response `500`, and explicit
`unhandled_exception` and post-start `streaming_error` behavior.

Independent validation passed 569 tests with zero skips, included PostgreSQL
integration, and achieved approximately 95.96% combined coverage against the
95.00% gate.

### Readiness checkpoint

Commit `204c1e2961a58d8436fb7601af4a0137f55640cc` provides the typed readiness
model and protocol, immediate memory readiness, PostgreSQL connectivity and
supported-revision checks, unversioned `/ready`, bounded `200`/`503` responses,
application-owned Engine reuse, lazy startup, unchanged `/health` behavior, and
`dependency_unavailable` request-event classification for known readiness
failure.

Final PostgreSQL-backed validation passed 585 tests with zero skips and no
warnings. Ruff and strict mypy passed across 112 source files. Alembic reported
head `0006_workflow_persistence`; statement coverage was 97.54%, branch
coverage was 87.90%, combined coverage was 96.05%, and `readiness.py` was 100%
covered.

## Implementation Conformance Matrix

| Area | Accepted behavior | Result |
| --- | --- | --- |
| Request correlation | Generated ID; valid propagation; invalid or duplicate replacement; response and request-state correlation | Complete |
| Structured observability | Seven bounded JSON fields; route template or unmatched value; monotonic duration; exactly one event; sensitive data excluded | Complete |
| Safe errors | Handled categories; safe pre-start `500`; `unhandled_exception`; post-start `streaming_error`; re-raise; `BaseException` not swallowed | Complete |
| Liveness | `/health` exact process-liveness contract without dependency work | Complete |
| Readiness | `/ready` `200`/`503`; memory and PostgreSQL checks; missing/wrong/multiple revision and unavailable database handled | Complete |
| Lifecycle | Lazy startup; application-owned Engine reuse; explicit ownership preserved; no migration, repair, or secondary Engine | Complete |
| Public boundary | Bounded readiness response and request event; no database URL, credentials, SQL, revision detail, exception text, or traceback | Complete |
| Exclusions | Auth, ADR-0006, security, cloud/deployment, external telemetry, HA/DR, backup/restore, Phase 8, and production-readiness approval absent | Complete |

## Residual Limitations

The following are accepted non-blocking boundaries of this implementation:

- route classification depends on behavior pinned by the current FastAPI
  version and should be rechecked on framework upgrades;
- malformed or nonconforming downstream ASGI behavior is outside the governed
  middleware contract;
- production log collection and external telemetry remain infrastructure work;
- readiness demonstrates bounded application/backend compatibility, not
  HA/DR, production monitoring, or production readiness;
- security remains blocked pending ADR-0006.

The completed implementation still requires separate repository-owner review,
hosted pull-request validation, and merge authorization.

## Explicit Non-Goals

Issue #58 does not authorize:

- authentication;
- authorization or RBAC;
- trusted-principal behavior;
- ADR-0006;
- security implementation;
- Prometheus;
- OpenTelemetry;
- Sentry;
- structlog;
- external metrics collectors;
- distributed tracing;
- AWS resources;
- API containerization;
- cloud deployment;
- production monitoring/alerting infrastructure;
- production TLS/network architecture;
- production secret-store integration;
- HA/DR;
- backup/restore;
- external ordering;
- Phase 8 work;
- production-readiness approval.
