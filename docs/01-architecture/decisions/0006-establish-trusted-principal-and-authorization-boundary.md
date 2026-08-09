# ADR-0006: Establish Trusted Principal and Authorization Boundary

- Status: Accepted
- Date: 2026-08-08
- Decision owners: Anish Paudyal
- Related issues: #54, #58, #60, #62
- Related pull requests: #61
- Supersedes: None
- Superseded by: None

## Context

OpsMind exposes a versioned supply-chain decision API and unversioned
operational endpoints. The API can mutate operational data, store actionable
recommendation snapshots, approve or reject recommendations, and return ordered
audit history.

The current application has no authentication or authorization boundary. An
approval or rejection request supplies `decided_by` as ordinary request text.
The API trims and validates that the value is nonblank, but it does not verify
the actor. The value is persisted in the terminal decision and copied into the
matching audit event. A caller can therefore claim any actor identity.

Current audit behavior proves bounded application invariants: supported writes
append matching events atomically, successful events are sequence ordered, and
retries or conflicts do not create duplicate history. It does not prove who
performed an action, prevent privileged database modification, provide
cryptographic tamper evidence, or establish a compliance ledger.

The owner-accepted Phase 7 plan requires a separately accepted ADR before this
trust boundary changes. Issue #58 and PR #59 completed request correlation,
safe HTTP observability, and liveness/readiness. Security is the next governed
Phase 7 workstream, but runtime implementation remains prohibited until this
ADR is accepted.

## Problem

OpsMind needs a minimum application security boundary that:

- replaces caller-asserted decision identity with a trusted principal;
- distinguishes authentication from authorization;
- protects business reads, operational mutations, and consequential decisions
  according to their risk;
- strengthens terminal-decision audit attribution;
- works without selecting Phase 8 cloud infrastructure;
- preserves deterministic local and test construction;
- fails closed without embedding credentials or identity-provider assumptions
  in domain or repository code.

## Current security-surface inventory

### Public application surface

All routes are currently unauthenticated.

| Classification | Current operations |
| --- | --- |
| Operational | `GET /health`, `GET /ready` |
| Business reads | Product list/retrieval, inventory retrieval, demand retrieval, forecast, stockout exposure, calculated reorder recommendation, stored review retrieval, audit-history retrieval |
| Operational mutations | Product creation, inventory replacement, demand-batch insertion |
| Workflow mutation | Stored recommendation-review creation |
| Consequential decision mutation | Recommendation approval and rejection |

FastAPI also exposes OpenAPI and interactive documentation endpoints. They
describe contracts but do not return business records.

### Current identity and authorization

- No API key, session, JWT, OAuth/OIDC, external identity provider, service
  identity, role, scope, or permission is validated.
- No security dependency or middleware exists.
- Repository and domain interfaces accept an ordinary `decided_by` string.
- Approval and rejection are consequential state transitions even though they
  do not yet create orders, reserve inventory, or mutate operational data.
- Any caller can currently read or mutate every resource reachable through the
  API.
- OpsMind has no organization, tenant, ownership, or row-level access model.

## Decision drivers

- Trusted, stable terminal-decision attribution
- Explicit least-privilege authorization for consequential actions
- Protection for business data and operational mutations
- Provider independence before deployment architecture exists
- Compatibility with the FastAPI application-factory and dependency seams
- Deterministic unit, API, and PostgreSQL testing
- No hand-rolled cryptography or token parsing
- Minimal personally identifying data
- Bounded public errors and secret-safe observability
- No user database, password store, or session service without demonstrated need
- Clear migration from the existing untrusted `decided_by` contract
- Limited operational and maintenance complexity

## Considered options

### Option A — Continue without authentication

Keep accepting caller-supplied actor text and expose all operations
anonymously.

This preserves current local simplicity but does not solve actor spoofing,
protect business data, or establish a deployable decision boundary. It is
acceptable only as the current explicitly limited pre-security state.

### Option B — Application-managed shared API key

Require one shared secret for protected requests.

This is simple and can distinguish authorized traffic from anonymous traffic,
but every holder has the same identity. It provides weak individual
attribution, coarse revocation, secret-distribution and rotation burden, and no
credible basis for distinguishing ordinary writes from recommendation
decisions. It is better suited to narrow service access than human decision
audit attribution.

### Option C — External identity with application-validated bearer principal

Delegate credential issuance and identity lifecycle to an external,
provider-agnostic identity authority. The OpsMind application validates signed
bearer access tokens and maps trusted claims into a small internal principal and
permission vocabulary.

This establishes stable identity, supports explicit action authorization, does
not require an application user/password database, and can be implemented and
tested independently of Phase 8 deployment. It adds token-validation
configuration and a future reviewed runtime dependency, but keeps provider and
cloud topology outside the domain model.

### Option D — Application-managed users and cookie sessions

Add user accounts, password handling, login/logout, session persistence, and
browser-oriented CSRF protections.

This can provide individual identity, but OpsMind currently has no frontend or
user-administration requirements. It would introduce a user database, password
security, recovery, session storage, and browser security architecture that are
not justified by the API-first vertical slice.

## Decision

Adopt **Option C: external identity with an application-validated bearer
principal**, as accepted by the repository owner.

The first security implementation will:

1. validate signed bearer access tokens inside the OpsMind application against
   one configured trusted issuer and audience;
2. map validated identity and authorization claims into an immutable
   application-level `TrustedPrincipal`;
3. authorize routes through three bounded application permissions;
4. derive terminal recommendation actor identity exclusively from the trusted
   principal;
5. leave bounded operational and API-description endpoints unauthenticated;
6. fail closed when authentication is absent, invalid, or not configured for a
   protected request.

This decision is provider agnostic. It does not select an identity vendor,
cloud service, token-validation library, or deployment topology. The future
implementation must use a maintained validation library rather than implement
JOSE, signature verification, or OAuth/OIDC protocol logic directly.

## Trusted-principal contract

The application-level principal will be an immutable, slotted value with only:

- `principal_id`: a stable, nonblank, bounded identifier derived from the
  validated token subject in the configured issuer's namespace;
- `permissions`: an immutable set of supported application permissions.

The application does not require a display name, email address, profile, local
user row, password, or organization membership for the first boundary. Raw
tokens and complete claim sets must never enter domain models, repositories,
audit events, logs, errors, or response examples.

Authentication terminates in an application dependency behind a narrow
protocol. The authenticator validates the token before constructing a
principal. Domain services and repositories receive only the trusted
`principal_id` needed for a decision, not bearer credentials or provider
claims.

The validator must enforce an explicit algorithm allowlist, signature, trusted
issuer, intended audience, expiration, not-before when present, and a valid
subject. Unsigned tokens, untrusted algorithms, invalid claims, malformed
credentials, and unverifiable keys fail authentication. Unknown authorization
claims grant no permission.

Trusted public verification keys or a JWKS document are supplied through
validated authenticator configuration. The first implementation must not make
an unbounded identity-provider network request for every API request. Online
discovery, refresh, and cache policy require explicit implementation evidence;
they must not silently change application readiness or add a second
unreviewed dependency boundary.

Exactly one issuer is supported per application configuration in the first
implementation. Supporting multiple issuers, account linking, or subject
migration requires reconsideration because stable audit identity would become
ambiguous.

The first boundary is for authenticated human end-user subjects. Workload and
service principals are deferred; they must not receive
`recommendation:decide` merely because they can obtain a token.

## Authorization boundary

The internal permission vocabulary is:

- `business:read` — read business records and calculated decision evidence;
- `business:write` — create or replace operational records and create stored
  recommendation-review snapshots;
- `recommendation:decide` — approve or reject a stored recommendation.

These are application permissions, not an enterprise role hierarchy. A trusted
authentication adapter derives them from verified authorization claims. The
application never treats arbitrary caller text or an unvalidated role claim as
a permission.

| Endpoint class | Required permission |
| --- | --- |
| Product, inventory, demand, forecast, stockout, reorder, stored-review, and audit-history reads | `business:read` |
| Product creation, inventory replacement, demand insertion, and stored-review creation | `business:write` |
| Recommendation approval and rejection | `recommendation:decide` |
| `/health`, `/ready`, OpenAPI, Swagger UI, and ReDoc | None |

Permissions are checked independently. Grant provisioning is an external
identity-administration responsibility; OpsMind does not add a role or user
database. There is no tenant or row-level authorization in this decision. A
principal with a permission can perform that action across the current single
OpsMind data boundary.

Each route requires the permission listed for its action; permissions are not
implicitly cumulative. Repository reads performed inside an authorized write
or decision action are part of that action and do not create a second route-
level permission check.

`recommendation:decide` is deliberately distinct from ordinary writes because
approval and rejection create the authoritative terminal human decision and
its audit attribution. It authorizes the action response for that decision;
separate review or audit GET requests still require `business:read`.

## Operational and API-description endpoints

`GET /health` and `GET /ready` remain unauthenticated so platform probes can
operate without end-user credentials. Their existing bounded payloads reveal
no database URL, credentials, SQL, exception detail, or secret configuration.

OpenAPI, Swagger UI, and ReDoc remain unauthenticated in the first application
boundary because they contain contract metadata rather than business records
and preserve local learning ergonomics. A deployment may separately disable or
restrict them when an approved exposure policy requires it.

No operational endpoint bypass may provide access to versioned business data.

## Security error contract

- A missing, malformed, expired, unverifiable, wrong-issuer, or wrong-audience
  bearer credential returns `401 Unauthorized` with a generic bounded body and
  `WWW-Authenticate: Bearer`.
- A valid principal lacking the required permission returns `403 Forbidden`
  with a generic bounded body.
- Authentication and authorization failures retain the effective
  `X-Request-ID` and one bounded structured HTTP event.
- Public responses and governed logs must not include a token, signature,
  signing key, raw claim set, provider error, or authorization-header value.
- Existing request classification may record the failures as bounded client
  errors; adding a more specific bounded category requires separate evidence
  and is not required by this ADR.

## Decision and audit attribution

Approval and rejection request bodies will no longer accept `decided_by` as the
authoritative actor. The route will pass `TrustedPrincipal.principal_id` through
the existing workflow transaction so the terminal decision and matching audit
event persist the same trusted identifier atomically.

The existing response fields `decision.decided_by` and audit-event `actor` may
remain for compatibility, but for post-boundary terminal decisions their value
will be the validated stable principal identifier. Display names remain
non-authoritative and are not persisted in the first implementation.

Existing pre-security decision records must not be relabeled as trusted. The
repository has no production data or production migration commitment; local
development data may be recreated. If retained data must cross the boundary, a
separate migration must preserve it explicitly as legacy unverified history.

Review creation and ordinary operational mutations will be authorized but are
not retroactively added to the current recommendation audit model. Extending
audit attribution to every write is separate work. This ADR strengthens the
terminal-decision actor required by the Phase 7 gate without claiming complete
system activity auditing.

## Application and local/test boundary

`create_app()` remains the composition root. A narrow authenticator/current-
principal dependency is injected there, following existing repository, clock,
and readiness seams.

The default protected-request behavior without a configured authenticator is
deny-all. Public operational endpoints may still start and respond. Tests may
inject deterministic principals or authenticators explicitly; no environment
name, debug flag, header, or caller-supplied actor creates an implicit trusted
principal. Any fixed local/test authenticator must be explicitly constructed
and must be rejected by staging and production configuration.

Memory and PostgreSQL persistence modes use the same authentication and
authorization policy. Security is not bypassed because memory mode is selected.

## Rationale

The selected boundary solves the immediate spoofing problem without building a
second identity system inside OpsMind. A small internal principal and permission
vocabulary isolates domain and repository behavior from provider claims while
keeping consequential approval/rejection authorization explicit.

The external issuer owns credential issuance, revocation policy, and identity
lifecycle. OpsMind owns token validation, application permission mapping,
request authorization, and audit attribution. This division is usable before
Phase 8 because it does not require a particular cloud service or network
topology.

A shared API key cannot provide credible human actor attribution. An internal
user/session system would add disproportionate security and operational scope.
Continuing anonymously would leave the accepted Phase 7 trust-boundary gap
unresolved.

## Consequences

### Positive

- Terminal decisions receive stable authenticated attribution.
- Business reads, writes, and decisions have explicit authorization classes.
- The domain and repositories remain independent of bearer tokens and identity
  providers.
- No application-managed password, user, or session store is introduced.
- Local and test behavior remains deterministic through explicit injection.
- `/health` and `/ready` remain usable by platform probes.
- Existing request correlation and bounded observability remain applicable.

### Negative

- A future runtime dependency and trusted-issuer configuration are required.
- Local interactive use needs a development issuer/token or an explicitly
  constructed safe test authenticator.
- Approval/rejection request bodies change because caller-supplied `decided_by`
  is removed.
- Permission provisioning and revocation remain external operational concerns.
- Verification-key refresh and token lifetime determine how quickly issuer
  key rotation or access revocation takes effect.
- The first boundary supports one issuer and no tenant isolation.

### Neutral

- Existing workflow atomicity, idempotency, and audit ordering remain governed
  by ADR-0004.
- Authentication does not make audit storage cryptographically tamper-evident.
- Authorization does not create purchase orders or external side effects.
- Public readiness is not a production-readiness claim.

## Security and privacy implications

- Persist only the stable principal identifier required for attribution.
- Do not persist bearer tokens, full claims, email addresses, or display names.
- Treat issuer metadata, audience, and public verification keys as
  configuration; treat any client secret or private key as a secret.
- Never place credentials in source, `.env` files committed to Git, examples,
  logs, tracebacks, error bodies, or snapshots.
- Use constant, generic public authentication failures; detailed provider
  diagnostics remain bounded internal operational evidence without credential
  values.
- This boundary improves actor trust but does not establish non-repudiation,
  tamper evidence, regulatory compliance, or production security approval.

## Implementation boundaries

A separate implementation issue may add only the minimum
principal model, authentication adapter/dependency, authorization policy,
request-schema actor migration, audit attribution, configuration, OpenAPI
security scheme, and focused tests required by this decision.

The implementation must not:

- write token-validation logic or cryptography from scratch;
- pass raw tokens or claim dictionaries into domain/repository code;
- trust proxy headers without a separately authenticated proxy contract;
- authorize based on environment, debug mode, display name, or request body;
- introduce a user, organization, tenant, role, or session database;
- change workflow transaction semantics;
- add cloud identity resources or deployment architecture.

Any new security dependency requires normal dependency review, a locked version,
and explicit compatibility/security evaluation in the implementation PR.

## Testing expectations

Future implementation tests must cover:

- missing, malformed, expired, wrong-issuer, wrong-audience, bad-signature, and
  unsupported-algorithm credentials;
- valid principals with every bounded permission combination needed by the
  endpoint classes;
- `401` versus `403` behavior and `WWW-Authenticate` semantics;
- protection of all versioned business reads and mutations;
- public `/health`, `/ready`, and API-description behavior;
- authorized approval and rejection using the trusted principal identifier;
- removal or rejection of caller-supplied authoritative `decided_by`;
- identical retry and conflict behavior under trusted identity;
- matching trusted identity in decision and audit event for memory and
  PostgreSQL repositories;
- deterministic injected principals without global mutable identity state;
- OpenAPI bearer security requirements;
- `X-Request-ID` preservation and exactly-one bounded event for `401` and `403`;
- absence of tokens, claims, keys, and provider exceptions from public output
  and logs;
- full existing quality, PostgreSQL, and 95.00% combined coverage gates.

## Migration and backward compatibility

Removing `decided_by` from approval and rejection request bodies is an
intentional breaking request-contract correction before production deployment.
The implementation PR must update OpenAPI, examples, tests, and documentation
together.

The domain/repository string field and PostgreSQL columns can store the trusted
principal identifier without an immediate schema change. Existing stored actor
values remain legacy unverified data and must never be presented as
authenticated. No production database or customer data currently requires an
online migration.

If future requirements need multiple issuers, display-name history, explicit
identity provenance, tenant membership, or preservation of pre-security data,
a separately reviewed data-contract and migration decision is required.

## Risks and mitigations

- **Token acceptance is too permissive:** require signature, algorithm, issuer,
  audience, time, and subject validation through a maintained library.
- **Provider claims leak into architecture:** map verified claims immediately to
  the bounded application principal and permission enum.
- **A test bypass reaches production:** make injection explicit and reject fixed
  authenticators in staging/production.
- **Decision permission grants broad data access:** keep
  `recommendation:decide` separate; other reads still require `business:read`.
- **Legacy actor text is mistaken for trusted identity:** do not migrate or
  relabel old data without explicit provenance.
- **Authentication is overstated as tamper evidence:** preserve ADR-0004 and
  Phase 6 limitations.
- **Public probes leak infrastructure:** retain their current bounded schemas
  and regression tests.
- **Scope expands into deployment:** keep issuer/provider provisioning and
  network topology outside this ADR.

## Non-goals

- Runtime security implementation in this ADR branch
- Selecting or provisioning an identity provider
- Enterprise SSO administration
- Application-managed users, passwords, sessions, or recovery
- Organization, tenant, team, or row-level authorization
- Fine-grained ABAC or policy engines
- Service-to-service identity or workload federation
- Cloud IAM, load balancer, gateway, WAF, TLS, or network-segmentation design
- Production secret-store or key-rotation infrastructure
- Cryptographic audit signing, hash chaining, or non-repudiation
- SIEM, external monitoring, or security analytics
- Penetration-testing or vulnerability-management programs
- Compliance certification or retention policy
- Purchase-order creation, external ordering, or inventory reservation
- API containerization, AWS resources, deployment, or Phase 8
- Production-readiness approval

## Reconsideration triggers

- More than one trusted issuer must be supported.
- OpsMind introduces organizations, tenants, resource ownership, or row-level
  isolation.
- A browser frontend requires cookie sessions or backend-for-frontend behavior.
- Machine clients require a distinct service-principal boundary.
- External ordering makes approval a direct financial or inventory action.
- Regulation requires stronger identity evidence, retention, non-repudiation,
  or tamper-evident audit storage.
- Deployment architecture provides a separately governed trusted gateway that
  materially changes where token validation should terminate.

## Governed implementation sequence

1. Add the immutable trusted-principal and bounded permission model.
2. Select and lock a maintained bearer-token validation dependency.
3. Add trusted-issuer configuration and the authenticator/current-principal
   dependency at the application factory.
4. Add endpoint-class authorization dependencies and OpenAPI bearer security.
5. Remove caller-authoritative `decided_by` from decision requests and derive
   the persisted actor from the trusted principal.
6. Verify memory and PostgreSQL audit attribution and existing workflow
   invariants.
7. Add stable `401`/`403`, request-correlation, and secret-safe logging tests.
8. Run complete regression, PostgreSQL, coverage, dependency, and governance
   validation.

This sequence is governed by a separate implementation issue and does not
authorize work outside the boundaries of this ADR.

## Owner decision status

ADR-0006 is **Accepted**. On 2026-08-08, repository owner Anish Paudyal
explicitly accepted the provider-agnostic signed bearer-token boundary,
application-derived trusted principals, the `business:read`, `business:write`,
and `recommendation:decide` permissions, trusted terminal-decision attribution,
bounded `401`/`403` behavior, unauthenticated operational endpoints, and the
documented non-goals. The owner also authorized a separately governed Phase 7
security implementation to proceed.

## Implementation notes

Issue #62 implements the accepted boundary with PyJWT 2.13 and its maintained
cryptographic backend. The first implementation uses one configured PEM RSA
public key and an explicit `RS256` allowlist, avoiding a runtime identity-
provider network dependency while preserving the authenticator seam for a
separately reviewed JWKS strategy if deployment requirements later need one.

The implementation keeps the `permissions` claim deliberately bounded as a
JSON list of exact application permission strings. Unknown strings grant
nothing, malformed claims fail authentication, and the default without a
complete issuer/audience/public-key configuration denies every protected
request. No schema migration is required because the existing decision and
audit actor columns store the bounded trusted principal identifier.

The implementation remains on `feat/phase-7-security-boundary` pending
repository-owner review and merge. This note does not claim Phase 7 or
production readiness.

## References

- [ADR index](README.md)
- [ADR-0004: Co-locate Recommendation Workflow State and Audit Events](0004-co-locate-recommendation-workflow-state-and-audit-events.md)
- [Phase 7 hardening plan](../phase-7-hardening-plan.md)
- [Issue #58 observability and readiness design](../phase-7-observability-readiness.md)
- [Product scope and requirements](../../00-project-foundation/product-scope-and-requirements.md)
- [Risk, cost, security, and responsible-AI baseline](../../09-risk-cost-security/responsible-ai-baseline.md)
- [Phase 6 review](../../12-phase-reviews/phase-6-review.md)
- [Current project status](../../09-status/current-status.md)
- GitHub Issue #60: Define Phase 7 trusted-principal and authorization boundary
