# Phase 7 Testing, Security, and Observability Hardening Plan

Status: Accepted
Date: 2026-08-07
Governed by: Issue #54
Owner acceptance: Anish Paudyal, 2026-08-07
Implementation authorization: Granted only for separately governed child workstreams after Issue #54 merges

## Purpose

Phase 7 hardens the already-delivered OpsMind vertical slice without expanding
into Phase 8 cloud deployment or later production-readiness work.

This plan defines the formal scope, workstream boundaries, decision gates, and
exit criteria for:

1. testing and coverage hardening;
2. application observability and readiness;
3. authentication and authorization;
4. final Phase 7 evaluation and review.

Phase 7 implementation must not begin until this plan is accepted by the
repository owner.

## Evidence Base

The plan is based on canonical `main` at:

`4f7e07b054953d9fd654c8867e2a595e33c81c57`

and the Phase 7 inspections completed after Phase 6 merged.

Inspection evidence established that:

- Phase 7 is the canonical Current phase;
- earlier phases already provide extensive unit, API, repository, migration,
  PostgreSQL, rollback, concurrency, restart, and lifecycle testing;
- statement/branch coverage is collected but no minimum percentage is governed;
- the existing quality ADR intentionally rejected arbitrary coverage percentages
  before a meaningful baseline existed;
- `/health` is process/liveness health only and intentionally does not check
  downstream dependencies;
- there is no application readiness contract;
- there is no runtime request/correlation-ID facility;
- there is no application request logging, latency, or error-correlation
  infrastructure;
- there is no runtime metrics, tracing, or external observability dependency;
- the application dependency boundary currently supplies settings,
  repositories, and the workflow clock, but no trusted principal or
  authorization policy;
- approval/rejection request schemas accept caller-supplied `decided_by`;
- public decision and audit schemas explicitly describe actor identity as
  unverified;
- the current OpenAPI regression contract deliberately excludes authentication,
  authorization, and correlation-ID fields;
- no security/identity dependency has been selected;
- the current security baseline requires least privilege, protected credentials,
  trust-boundary validation, and authorization/audit evidence.

## Governing Principles

### 1. Harden by risk, not by tool count

Phase 7 must not add technologies merely because they are commonly associated
with security or observability.

Every dependency, middleware layer, security mechanism, and quality gate must
have a documented purpose and testable outcome.

### 2. Preserve the existing vertical slice

Phase 7 must harden:

`product -> demand -> forecast -> stockout -> reorder -> review -> decision -> audit`

It must not add purchase orders, supplier integrations, external ordering,
inventory mutation from approval, or unrelated product capabilities.

### 3. Separate application hardening from cloud operations

Application-level security, readiness, correlation, and logging belong here.

AWS services, production monitoring/alerting infrastructure, API
containerization, cloud deployment, HA/DR, and production network architecture
do not.

### 4. Security architecture precedes security implementation

Authentication and authorization change the system trust boundary.

A separately reviewed ADR-0006 is required before trusted-identity
implementation begins.

### 5. Evidence precedes a numerical coverage gate

Phase 7 must measure the actual statement and branch-coverage baseline first.

A percentage threshold may be adopted only if it is justified from the measured
baseline and risk review. A threshold must not be selected for cosmetic reasons.

## Workstream A — Testing and Coverage Hardening

### Goal

Convert the mature existing test suite into an explicit Phase 7 quality
baseline and close risk-significant coverage gaps.

### Required work

1. Run reproducible statement and branch coverage against the complete supported
   test suite.
2. Record:
   - total statement coverage;
   - total branch coverage;
   - per-module coverage;
   - missing lines/branches;
   - excluded or unmeasured code, if any.
3. Review uncovered behavior by risk.
4. Prioritize critical paths involving:
   - trust-boundary validation;
   - authentication/authorization once introduced;
   - recommendation approval/rejection;
   - error handling;
   - observability middleware;
   - readiness behavior;
   - secret-safe configuration behavior.
5. Decide whether a minimum coverage threshold should be adopted.
6. If a threshold is adopted:
   - explain why the value is appropriate;
   - apply it to the repository quality workflow;
   - ensure it is reproducible locally and in CI.
7. If no threshold is adopted:
   - record the rationale;
   - define the alternative Phase 7 regression-quality guard.
8. Resolve the known Starlette/TestClient deprecation warning if a safe,
   compatible repository-owned change is available.
9. Otherwise record a bounded disposition with evidence and follow-up condition.

### Not required

Phase 7 does not require increasing the test count for its own sake.

No test should be added solely to raise a percentage without protecting
meaningful behavior.

## Workstream B — Application Observability and Readiness

### Goal

Create a dependency-light application observability foundation that can later
integrate with cloud monitoring without coupling Phase 7 to Phase 8.

### Initial design direction

Prefer standard Python and FastAPI capabilities first.

Do not add Prometheus, OpenTelemetry, Sentry, structlog, or another
observability dependency unless a separately reviewed design shows concrete
value that the standard library cannot reasonably provide.

### Required behavior

1. Every normal application request receives an application correlation/request
   identifier.
2. The identifier has a deterministic propagation contract:
   - server-generated when absent;
   - caller-provided values accepted only under a documented validation policy;
   - one canonical response header exposes the effective identifier.
3. Runtime request logging records structured, machine-parseable fields for at
   least:
   - correlation/request ID;
   - HTTP method;
   - route/path classification;
   - response status;
   - request duration;
   - bounded error category where applicable.
4. Logs must not expose:
   - database passwords;
   - full database URLs containing credentials;
   - authentication secrets;
   - authorization credentials;
   - request bodies containing sensitive decision notes by default.
5. Error logging must correlate a failure with the request identifier without
   returning internal exception/SQL/database details to callers.
6. Existing `/health` behavior remains process/liveness health.
7. A distinct readiness contract represents whether configured application
   dependencies are ready enough to serve dependency-backed work.
8. Memory and PostgreSQL readiness semantics must be explicit.
9. Readiness must not be documented as:
   - HA evidence;
   - backup/restore evidence;
   - production monitoring;
   - full production-readiness approval.
10. Observability behavior must have automated success and failure-path tests.

### Metrics/tracing boundary

Application request logs and readiness are the required Phase 7 baseline.

A dedicated metrics or tracing library is optional and requires explicit
evidence-based approval.

## Workstream C — Security Boundary

### Goal

Replace caller-asserted decision identity with an accepted trusted-principal
boundary and explicitly authorize consequential actions.

### ADR-0006 requirement

Before security implementation begins, ADR-0006 must evaluate and decide:

1. authentication mechanism;
2. principal representation;
3. authorization model;
4. protected endpoint classification;
5. application dependency-injection boundary;
6. audit actor derivation;
7. authentication/authorization failure semantics;
8. OpenAPI/security-scheme implications;
9. configuration and secret handling;
10. testing strategy;
11. supported environments;
12. explicit non-goals and production limitations.

### Alternatives that ADR-0006 must consider

At minimum, compare appropriate variants of:

- static/API-key authentication;
- signed token/JWT authentication;
- OAuth2/OIDC-style external identity;
- session/cookie authentication, if applicable;
- deliberately limited local/test identity mechanisms.

The ADR must not select a mechanism merely because FastAPI supports it or
because it is common.

### Required security behavior after ADR acceptance

1. Consequential recommendation approval and rejection require an authenticated
   principal under the accepted design.
2. Authorization for approval/rejection is explicit and tested.
3. Other mutating endpoints are deliberately classified:
   - protected;
   - authenticated but broadly authorized;
   - intentionally public for the current learning boundary.
4. Trusted decision actor identity comes from the authenticated principal.
5. `decided_by` must no longer be the authoritative caller-supplied identity for
   trusted terminal decisions.
6. Any retained caller-supplied display/note field must be clearly distinct from
   authenticated identity.
7. Audit events persist the trusted actor identity defined by the accepted ADR.
8. Authentication and authorization failures have stable public semantics.
9. Secrets/credentials are hidden from:
   - settings representations;
   - logs;
   - errors;
   - OpenAPI examples unless intentionally safe.
10. Security tests cover:
    - missing credentials;
    - malformed credentials;
    - invalid credentials;
    - authenticated but unauthorized principals;
    - authorized approval;
    - authorized rejection;
    - actor/audit identity derivation;
    - secret-safe logging/error behavior.

## Workstream D — Phase 7 Evaluation and Review

### Goal

Evaluate the accepted testing, observability, readiness, and security behavior
as one formal Phase 7 gate.

### Required evidence

The final Phase 7 evaluation must include:

- reproducible coverage evidence;
- risk-based uncovered-path review;
- coverage-gate decision;
- warning disposition;
- accepted ADR-0006;
- authentication tests;
- authorization tests;
- trusted-actor audit tests;
- correlation/request-ID tests;
- structured logging tests;
- readiness tests;
- real PostgreSQL regression evidence;
- complete quality suite;
- documentation consistency;
- explicit limitations.

The final review must record an owner decision:

`Proceed`, `Revise`, or `Stop`.

## Phase 7 Exit Criteria

Phase 7 is complete only when all of the following are satisfied.

### Testing

1. Current statement and branch coverage are measured reproducibly.
2. Critical uncovered paths are reviewed by risk.
3. Any numerical coverage threshold is evidence-based and documented, or the
   owner accepts a documented alternative quality guard.
4. Phase 7 security and observability behavior has automated regression
   coverage.
5. The known TestClient warning is resolved or formally dispositioned.

### Security

6. ADR-0006 is accepted before the trusted security boundary is implemented.
7. Protected operations require the accepted authenticated principal.
8. Approval/rejection actor identity comes from the trusted principal rather
   than caller-supplied `decided_by`.
9. Authorization for consequential recommendation decisions is explicit and
   tested.
10. Other mutating endpoints are deliberately classified and documented.
11. Authentication/authorization failures use stable public semantics.
12. Security credentials and configured secrets are not leaked through normal
    public errors, representations, or application logs.

### Observability and readiness

13. Requests have deterministic correlation/request identifiers with documented
    propagation rules.
14. Runtime logging provides safe request correlation, outcome, latency, and
    bounded error evidence.
15. `/health` remains process/liveness health.
16. A distinct readiness contract represents supported dependency readiness.
17. Important observability and readiness failure paths are tested.

### Scope and governance

18. No unsupported production/cloud/security claims are introduced.
19. AWS, cloud deployment, API containerization, HA/DR, production monitoring
    infrastructure, production secret-store integration, external ordering, and
    production-readiness approval remain excluded unless separately governed.
20. A final Phase 7 review records an owner-accepted `Proceed`, `Revise`, or
    `Stop` decision.

## Proposed Work Order

Subject to owner acceptance, use this order:

1. testing/coverage baseline and hardening;
2. observability/readiness design and implementation;
3. ADR-0006 security-boundary decision;
4. security implementation after ADR-0006 acceptance;
5. Phase 7 integrated evaluation and review.

Rationale:

- coverage measurement gives an objective starting baseline;
- observability can be implemented without prejudging authentication technology;
- security receives its own explicit architecture decision;
- final evaluation verifies the combined hardened application.

The owner may revise this order before implementation.

## Child-Issue Boundaries

After this plan is accepted, open separate child issues.

Expected issue classes:

### Testing child

May modify:

- coverage configuration;
- CI quality commands;
- focused regression tests;
- warning-related tooling/tests;
- testing documentation.

Must not introduce authentication or observability runtime behavior.

### Observability child

May modify:

- request middleware;
- correlation/request-ID behavior;
- logging configuration;
- readiness route/service/dependencies;
- observability tests and documentation.

Must not introduce authentication/authorization or cloud monitoring.

### Security ADR child

Documentation/ADR only.

Must not implement the selected security mechanism before owner acceptance.

### Security implementation child

May begin only after ADR-0006 is accepted.

Must remain inside the accepted ADR boundary.

### Evaluation child

May evaluate and document accepted Phase 7 behavior.

Must not silently add new product/security/observability scope.

## Architecture-Decision Policy

This Phase 7 plan itself is not an ADR.

ADR-0006 is mandatory because the authentication/authorization design changes a
system trust boundary.

A separate observability ADR is not currently required if Phase 7 uses:

- Python standard logging;
- local FastAPI middleware;
- an application-defined request-ID contract;
- an application-defined readiness contract;
- no major runtime dependency.

If observability work proposes a major dependency, external collector,
distributed tracing architecture, or externally visible metrics contract, stop
and review whether an ADR is required.

A coverage threshold does not require an ADR unless it materially changes the
repository quality architecture beyond the accepted testing toolchain.

## Explicit Non-Goals

Phase 7 does not implement or approve:

- AWS resources;
- cloud deployment;
- API containerization;
- Kubernetes/ECS/EKS;
- production load balancing;
- production TLS/network architecture;
- production monitoring/alerting infrastructure;
- PagerDuty or incident-management integration;
- production secret-store integration or rotation infrastructure;
- backup/restore;
- replication;
- high availability;
- disaster recovery;
- production-scale performance claims;
- production-scale concurrency claims;
- purchase orders;
- supplier integrations;
- external ordering;
- automatic inventory mutation from approval;
- compliance certification;
- production-readiness approval.

## Definition of Done for Issue #54

Issue #54 is complete when:

1. this plan is reviewed;
2. the repository owner accepts or revises the plan;
3. the testing, observability, security-ADR, security-implementation, and final
   evaluation boundaries are unambiguous;
4. Phase 7 exit criteria are explicit;
5. the coverage policy is explicit;
6. the observability dependency policy is explicit;
7. ADR-0006 is explicitly required before security implementation;
8. the next permitted child issue is explicit;
9. no Phase 7 implementation is included in this scope issue.

## Owner Acceptance

Owner: Anish Paudyal
Date: 2026-08-07
Decision: Accepted

Accepted statement:

`I accept the Phase 7 testing, security, and observability hardening plan under Issue #54 and approve opening the governed child workstreams.`

The owner accepts the Phase 7 workstream boundaries, exit criteria, coverage
policy, observability dependency policy, ADR-0006 requirement, proposed work
order, and explicit non-goals documented in this plan.

This acceptance authorizes opening and executing the governed Phase 7 child
workstreams after the Issue #54 scope change is merged.

It does not authorize Phase 7 implementation on
`docs/phase-7-hardening-scope`.

Security implementation remains separately blocked until ADR-0006 is reviewed
and owner accepted.

## Acceptance Gate

The repository owner has accepted this plan. Governed child workstreams may begin
after the Issue #54 scope change is merged, each through its own approved
issue/task branch.

Security implementation remains blocked until ADR-0006 is separately
reviewed and owner accepted.
