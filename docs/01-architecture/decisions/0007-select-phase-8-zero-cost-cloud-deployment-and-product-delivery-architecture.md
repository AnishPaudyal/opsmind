# ADR-0007: Select Phase 8 Zero-Cost Cloud Deployment and Product-Delivery Architecture

- Status: Proposed
- Date: 2026-08-10
- Decision owners: Repository owner
- Related issue: #66

## Status and authority

Repository-owner acceptance is pending. This proposal authorizes no cloud
resource, identity tenant, Dockerfile, frontend, infrastructure-as-code,
workflow, dependency, migration, or runtime change. Each implementation stage
requires a separately approved issue after this ADR is accepted.

The repository owner redirected the proposal before acceptance: the Phase 8
portfolio environment must target genuine `$0` recurring infrastructure cost
under normal low-volume demonstration use. The former approximately
`$50–65/month` AWS runtime remains useful reference analysis, but is not the
proposed deployment target.

## Context

OpsMind is a hardened local FastAPI modular monolith backed by PostgreSQL. It
has a provider-neutral trusted-principal boundary, exact action permissions,
structured HTTP events, request IDs, liveness, readiness, Alembic migrations,
and a 95% combined line-and-branch coverage gate. It does not yet have an API
container, public deployment, managed database, provisioned identity provider,
frontend, infrastructure as code, or deployment pipeline.

Phase 8 must demonstrate a real browser-to-cloud-to-database product without
creating a required monthly bill. It should still teach and prove:

- a reproducible non-root OCI image and immutable release identity;
- managed PostgreSQL, controlled migrations, TLS, and connection handling;
- standards-based OAuth2/OIDC, JWT/JWKS validation, and authorization;
- a React/TypeScript dashboard on an HTTPS CDN;
- multi-provider infrastructure as code as far as providers support it;
- GitHub Actions delivery, secrets/configuration, smoke tests, and rollback;
- health, readiness, structured logging, and request-ID troubleshooting;
- an honest AWS translation and separate LocalStack skills laboratory.

The portfolio environment is not a production environment. Free-tier sleep,
resource, retention, support, and service-change constraints are accepted and
must be visible rather than disguised.

## Decision drivers

1. Required recurring infrastructure cost is `$0` at low portfolio usage.
2. A permanent free tier is acceptable; a trial, expiring database, credit, or
   student benefit is not the foundation of the decision.
3. The deployed API must preserve FastAPI, SQLAlchemy, Psycopg, Alembic, and
   Docker rather than contorting OpsMind into an unrelated runtime.
4. The first frontend remains in Phase 8.
5. Authentication stays provider-neutral inside the application and preserves
   ADR-0006.
6. Automation claims must match actual provider and free-plan capabilities.
7. Cold starts, bounded restore, and limited logs must be represented honestly.
8. AWS learning remains valuable but must not be confused with actual AWS use.
9. Later data, MLOps, and AI phases need a migration path, not premature
   infrastructure.
10. One engineer should be able to understand and operate the result.

## Free-tier classification

The selected baseline uses ongoing free offerings, not trial credit:

| Component | Selected offering | Classification and relevant limit |
| --- | --- | --- |
| Static frontend | Cloudflare Pages Free | Ongoing free plan; 500 builds/month, one concurrent build, 20-minute build limit, and Pages platform limits apply |
| API runtime | Render Free web service | Ongoing free instance; 750 free instance hours/workspace/month, idle spin-down after 15 minutes, no persistent disk, shell, scaling, private network, or one-off jobs |
| Database | Neon Free | Ongoing free plan; 100 compute-unit hours/project/month, 0.5 GB/project, scale-to-zero after five minutes, and bounded restore window |
| Identity | ZITADEL Free | Ongoing free plan; 100 daily active users and current Free-plan service limits apply |
| Source, CI, OCI | Public GitHub repository, Actions, GHCR | Standard hosted runners are free for public repositories; public package use is free under current GitHub billing terms |
| IaC state | HCP Terraform Free | Ongoing free tier with remote runs/state and up to 500 managed resources under current limits |
| AWS laboratory | LocalStack Hobby | Free personal, non-commercial plan under its license and fair-use terms; supported service APIs only |

No custom domain is required. Cloudflare `pages.dev`, Render `onrender.com`,
Neon, and ZITADEL service endpoints are sufficient. Domain registration and
any upgrade are optional and outside the `$0` baseline.

Free plans can change. Phase 8D must recheck public terms and account usage,
record the date, and stop or revise before a change could create an unexpected
charge.

### Cost guardrails

| Component | `$0` assumption | Cost or stop trigger |
| --- | --- | --- |
| Cloudflare Pages | Static SPA stays within Free build/project limits; no Pages Functions or paid domain | Excess build needs, paid Workers use, or optional domain purchase requires review |
| Render | One sleeping Free web service stays within 750 shared instance hours and included transfer/pipeline amounts | With no payment method Render suspends/disables service at relevant limits; any paid instance or supplementary billing requires owner approval |
| Neon | Demo database stays below 100 CU-hours and 0.5 GB | Exhausted allowance, more storage/compute, or longer restore retention requires a plan decision |
| ZITADEL | Portfolio usage stays below 100 DAU and within Free limits | More active users, custom paid capability, or changed Free terms requires review |
| GitHub | Repository and OCI package remain public and use standard hosted runners | Private-repository minutes/storage or paid runner/package use is outside baseline |
| HCP Terraform | One small workspace remains below 500 managed resources | Paid collaboration/governance features or higher resource count is outside baseline |
| LocalStack | Personal non-commercial Hobby use stays within fair-use terms | Commercial/shared use or an unsupported/paid service ends the Hobby design |

Payment methods are not used as permission to overrun. Where a platform can
bill supplementary usage, configure a zero/minimum spend guardrail if available,
monitor its dashboard, and prefer suspension over automatic paid continuation.
The environment's operational rule is:

```text
free-tier exhaustion
-> suspension or degraded portfolio availability
-> owner review
NOT
-> automatic paid scaling or supplementary charging
```

No component may require adding a payment method merely to keep this portfolio
environment running. Zero surprise cost has priority over availability.

## Candidate architectures

### Candidate A — Cloudflare Pages, Render, Neon, and ZITADEL

```text
Browser -> Cloudflare Pages SPA -> Render Free Docker API -> Neon PostgreSQL
               |                         ^
               +---- ZITADEL OIDC -------+
```

Cost: `$0` at bounded use. Docker and public GHCR preserve real container and
registry learning. Render fits the existing synchronous FastAPI/PostgreSQL
architecture, managed TLS, health checks, deploy hooks, logs, and recent
deployment rollback. Neon supplies durable PostgreSQL, pooling, SSL,
scale-to-zero, and pgvector. ZITADEL supplies OIDC, PKCE, project roles, JWKS,
and a Terraform provider on its Free plan.

Constraints: Render can take roughly a minute to wake after 15 idle minutes,
has ephemeral storage and no Free pre-deploy command or one-off job. Neon also
sleeps. Render Free cannot currently be represented by the official Terraform
web-service resource, but Render Blueprints can declare an image-backed Free
web service. Neon lacks a first-party Terraform provider and remains a bounded
bootstrap exception. Free-tier policy is an external risk.

### Candidate B — Cloudflare Pages, Koyeb, Neon, and ZITADEL

```text
Browser -> Cloudflare Pages SPA -> Koyeb Free container -> Neon PostgreSQL
               |                         ^
               +---- ZITADEL OIDC -------+
```

Cost: `$0` within published limits. Koyeb offers one Free instance with 512 MB
RAM, 0.1 vCPU, 2 GB ephemeral SSD, Docker deployment, scale-to-zero, managed
HTTPS, and an official Terraform provider. It generally wakes in seconds after
one hour idle, giving better cold-start behavior and IaC coverage than Render.

Constraints: the Free instance is limited to one organization, selected
regions, very small CPU, and no worker, volume, horizontal scaling, or
high-availability behavior. A valid payment method is required for the Starter
organization. The 0.1-vCPU ceiling creates more runtime and future ML risk than
Render, and it weakens the portfolio experience when builds or requests are
bursty.

### Candidate C — Cloudflare Pages/Workers, Neon, and ZITADEL

```text
Browser -> Cloudflare Pages -> Python Worker -> Neon
                 |                 ^
                 +-- ZITADEL ------+
```

Cloudflare supports Python Workers and selected packages through a
Pyodide/Wasm runtime, with a Free request/CPU allowance. This is a credible
serverless architecture for software designed for that environment.

It is rejected for OpsMind. The current synchronous FastAPI, native Psycopg,
SQLAlchemy, Alembic, and Docker architecture does not map directly to the
Workers runtime and its package/CPU constraints. Adopting it would trade away
the container objective and force a disproportionate application/data-access
redesign only to obtain hosting.

### Selection

Propose Candidate A. Render’s slow wake is a visible portfolio compromise, but
its Docker fit, resource envelope, operational surface, and future migration
path outweigh Koyeb’s stronger Terraform coverage and faster wake. Candidate B
is the documented fallback if Render changes or becomes unusable. Candidate C
is not an architecture-preserving deployment.

## Proposed actual deployment architecture

```text
                         Browser
                            |
                  OAuth2 authorization code + PKCE
                            |
             +--------------+---------------+
             |                              |
             v                              v
    Cloudflare Pages/CDN               ZITADEL Free
      React/TypeScript              OIDC issuer and roles
             |
             | HTTPS + access token
             v
       Render Free web service <--- public immutable GHCR image
       Dockerized FastAPI                  ^
             |                             |
             | TLS, pooled connection      |
             v                             |
         Neon PostgreSQL             GitHub Actions
                                      test/build/scan/
                                      migrate/deploy
```

Terraform manages Cloudflare and ZITADEL configuration where supported and
uses HCP Terraform Free for state and locking. A Render Blueprint manages the
Free API service. The initial Neon project is a bounded documented bootstrap
exception. This is a real multi-provider cloud deployment; it is not AWS.

## Container and backend runtime

Phase 8A should add one separately reviewed production-oriented API Dockerfile:

- reproducible installation from `uv.lock`;
- multi-stage or equivalently minimal build;
- non-root runtime user and no package manager at runtime;
- no credentials, local environment, tests, caches, or build tools in the final
  layer unless runtime-required;
- explicit ASGI command, bound port, graceful termination, and bounded worker
  model appropriate to the Free memory allowance;
- OCI labels and an immutable full Git commit identity;
- local container smoke test plus vulnerability scanning.

GitHub Actions, not Render, should build the image. After the existing checks,
Actions builds and scans `linux/amd64`, publishes a public GHCR artifact tagged
with the full Git SHA, and deploys that immutable identity to the image-backed
Render service. A public image avoids registry credentials at Render and is
free under current GHCR terms. Source and image remain public, and no secret
may enter a build argument or layer.

Render Free limitations are architectural facts:

- the service sleeps after 15 minutes without inbound traffic;
- waking may take approximately one minute;
- 750 instance hours are shared per workspace each month;
- its filesystem is ephemeral;
- Free has no shell, persistent disk, private network, scaling, one-off job, or
  pre-deploy command;
- outbound transfer and build-pipeline allocations remain account-level limits
  that must be monitored;
- the service is one instance and not highly available.

Application startup must not migrate. Runtime health uses `/health`; platform
readiness and post-deploy verification use `/ready`.

### Render Blueprint ownership

The official Render Terraform provider remains unsuitable for this service
because its current web-service resource does not expose the Free plan. Phase
8B therefore uses Render's native Blueprint infrastructure as code. A reviewed
root `render.yaml`, added only by a separately authorized implementation issue,
will declaratively own:

- one `type: web` service with `runtime: image` and `plan: free`;
- the stable service name and supported region;
- a public, fully qualified GHCR `image.url` pinned to a reviewed immutable Git
  SHA tag for the declared baseline release;
- `healthCheckPath: /health`;
- the required non-secret environment values, including environment, issuer,
  audience, trusted JWKS URI, exact CORS origins, and allowed algorithm;
- secret environment variable names with `sync: false`, never secret values;
- any other supported service setting that implementation evidence shows is
  required.

Blueprint validation is part of CI. The Blueprint does not manage Neon, HCP
Terraform state, Cloudflare Pages, or ZITADEL resources.

The Blueprint's initial `image.url` references an image already published by
Phase 8A. Image promotion is an operational release action, not an implicit
mutable-tag update: every deployment passes the exact immutable tag/digest to
the deploy hook. Before a later Blueprint sync, its declared `image.url` must be
reconciled through review to the currently intended immutable release so a
configuration sync cannot select a stale baseline.

One-time Render bootstrap is limited to creating/connecting the Render account
and Blueprint, granting repository access needed to sync `render.yaml`, entering
initial `sync: false` secrets, and obtaining the secret deploy hook. Later new
secret values must be added through Render's secret configuration because
Blueprint sync ignores newly introduced `sync: false` values on an existing
service. The Free service configuration itself is not described as manual.

## Cold-start and frontend behavior

Cloudflare Pages remains immediately available while Render and Neon may both
be asleep. Neon normally wakes within hundreds of milliseconds after a
connection; Render is expected to dominate the delay.

The frontend should probe public `/ready` and render `Backend waking — this
free portfolio service may take about a minute` while retrying with bounded
backoff, for example immediately and then after 2, 4, 8, and 15 seconds up to a
roughly 90-second ceiling. A non-JSON platform wake response must be handled.
After the ceiling, the UI reports `Backend unavailable` and presents the
request ID when available.

Only readiness and safe reads may be retried automatically. Mutating requests
must not be replayed without their existing idempotency contract. The design
does not weaken `/ready`: it may remain unavailable while PostgreSQL wakes or
the schema is unsupported.

## Managed PostgreSQL

Select Neon Free rather than Render Free PostgreSQL or Supabase Free.

- Neon Free does not have a 30-day database expiration. It provides PostgreSQL,
  SSL, up to 100 compute-unit hours and 0.5 GB storage per project, autoscaling,
  and scale-to-zero after five minutes.
- The application uses Neon’s pooled connection string for normal SQLAlchemy
  traffic and a direct SSL connection for controlled Alembic execution.
- SQLAlchemy and Psycopg use the standard PostgreSQL protocol; no Neon-specific
  domain or repository type is introduced.
- Phase 8B must investigate `pool_pre_ping=True`, a bounded connect timeout,
  transaction-pool compatibility, and stale connection behavior. Connection
  recycle settings are added only if measurement demonstrates need.
- `/ready` retains connectivity plus exact Alembic-revision semantics after a
  database wake.
- Neon supports `pgvector`, leaving a reasonable storage migration path for a
  separately governed Phase 11 experiment without adding vectors now.

Neon Free time travel/restore is bounded to six hours or 1 GB of changes,
whichever limit is reached first under current pricing. This is useful recovery
for a portfolio database but is not RDS-style seven-day PITR or a production
backup policy. Phase 8D should test a restore and document an optional
secret-safe logical export/import procedure. Production would require longer
retention, scheduled backups, restore objectives, monitoring, and tested DR.

Render Free PostgreSQL is rejected because it expires after 30 days. Supabase
Free is a credible PostgreSQL alternative with a larger nominal database and
pgvector, but inactive free projects may pause and free projects lack automatic
backup/PITR. Its bundled auth/storage features are unnecessary here. Neon’s
database-focused model, quick scale-to-zero wake, pooled endpoint, and bounded
restore better fit OpsMind.

Neon currently documents APIs and other IaC integrations but no first-party
Terraform provider. A community provider is not silently adopted. Account,
project, database role, and direct/pooled connection creation are a bounded
manual bootstrap, recorded in a checklist without credentials. A future
official provider can replace it through a separately reviewed import/migration.

## Identity and authorization

Select ZITADEL Free over Auth0 Free for this portfolio environment.

Both provide standards-based OIDC, authorization code with PKCE, access tokens,
JWKS, and free hosted identity. Auth0 has a mature official Terraform provider
and a 25,000-MAU Free allowance, but its current Free plan does not include
Role Management and retains tenant logs for one day. Implementing exact
read/write/decision roles through metadata or custom Actions would add manual
coupling and weak evidence.

ZITADEL Free currently includes its security features, project roles, 100 daily
active users, hosted OIDC, and an official Terraform provider. That lower user
allowance is ample for the portfolio. Self-managed identity is rejected because
password storage, recovery, abuse controls, mail delivery, patching, and
availability would materially expand risk and scope.

The Phase 8B adaptation preserves ADR-0006 and fixes the following contract.

### Token and algorithm configuration

The public SPA OIDC application uses authorization code plus PKCE with no
client secret. ZITADEL's default access-token form is opaque, which cannot be
verified through the selected local JWKS model. The future OIDC application
must therefore configure the official values:

```text
access_token_type = OIDC_TOKEN_TYPE_JWT
access_token_role_assertion = true
id_token_role_assertion = false
```

Protected OpsMind business requests carry the ZITADEL **JWT access token** as
the bearer credential. The backend never accepts an ID token as API
authorization. ID-token information may later support appropriate frontend
identity display or session UI, but the frontend is not an authorization
authority and its ID token cannot satisfy the backend bearer contract.

ZITADEL's default RS256 web-key path is selected because ADR-0006 already
allowlists RS256 and ZITADEL documents RS256 as its interoperable default. The
future verifier's algorithm allowlist contains exactly `RS256`; it never derives
an accepted algorithm from the token's untrusted `alg` header. Provisioning
must stop for design review if the selected ZITADEL environment cannot maintain
an RS256 signing key compatible with the current 2,048-bit RSA minimum.

### Audience and role assertion

The SPA authorization request includes the exact reserved audience scope:

```text
urn:zitadel:iam:org:project:id:{OPSMIND_PROJECT_ID}:aud
```

`{OPSMIND_PROJECT_ID}` is the immutable ZITADEL project ID for the OpsMind
backend resource boundary. The verifier requires that exact project ID in the
JWT access token `aud` claim. Missing, malformed, or wrong audience fails
authentication. Audience proves intended recipient, not authorization; a token
with this audience still needs an allowlisted role.

With access-token role assertion enabled, OpsMind reads only the current
project-specific claim:

```text
urn:zitadel:iam:org:project:{OPSMIND_PROJECT_ID}:roles
```

The backward-compatible unscoped role aliases are not authentication inputs.
The claim must be an object whose keys are role keys and whose values have the
documented ZITADEL organization-assignment shape. The only accepted role keys
and mappings are:

| ZITADEL project role key | OpsMind `Permission` |
| --- | --- |
| `opsmind.business.read` | `business:read` |
| `opsmind.business.write` | `business:write` |
| `opsmind.recommendation.decide` | `recommendation:decide` |

The mapping is an exact allowlist. Unknown roles grant nothing. A missing or
malformed project-specific role claim fails safely and grants no protected
access. There are no wildcards, prefix matches, implicit hierarchy, or
permission inheritance: `opsmind.business.write` does not imply
`opsmind.recommendation.decide`.

### JWKS verification contract

The future backend verifier must:

1. trust only the configured ZITADEL issuer and its configured/discovered JWKS
   endpoint;
2. require a signed JWT access token and reject opaque tokens and ID tokens;
3. verify the signature with the explicit `RS256` allowlist;
4. require the exact OpsMind project audience, expiration, and stable bounded
   subject;
5. parse only the exact project-specific role claim and apply the three-entry
   role allowlist;
6. resolve `kid` only from the trusted JWKS, using a bounded cache and one
   bounded refresh for an unknown rotated `kid`;
7. fail closed on missing configuration, discovery/JWKS failure, rotation
   failure, malformed claims, unknown key, or validation error;
8. bound token and subject values and never follow an attacker-controlled JWKS
   URL; and
9. keep token values, raw claims, keys, provider bodies, and provider exceptions
   out of client errors and governed logs.

`TrustedPrincipal` remains provider-neutral; domain and repository layers
receive no ZITADEL types.

Tenant/project bootstrap is manual because an account must exist. Terraform
can then manage project/application/API-role configuration as far as the
official provider supports it, using a narrowly scoped management credential.
Logout/redirect URIs, key rotation, malformed-token cases, outage behavior, and
the exact configured claim shape require implementation evidence before
deployment, but the token type, audience, role claim, role keys, permission
mapping, algorithm, and JWKS trust boundary are fixed by this proposal.

## Frontend and first dashboard

Phase 8C uses React, TypeScript, Vite, React Router, TanStack Query, an
OpenAPI-derived client where review proves the generator/update process, and a
restrained chart library. No SSR requirement exists, so Next.js is not selected.

Cloudflare Pages Free supplies Git integration, preview deployments, managed
HTTPS, CDN delivery, a `pages.dev` domain, custom domains if later purchased,
SPA fallback through a reviewed `_redirects` rule, and rollback to a prior
successful deployment. Static asset requests are free and unlimited under
current Pages pricing; build and project limits still apply. Pages Functions
are unnecessary and must not become an accidental backend.

The dashboard scope is:

- **Overview:** API/readiness state, inventory summary, and recommendations
  requiring attention;
- **Products:** list and detail;
- **Inventory:** current quantities and status;
- **Demand and Forecast:** demand history and transparent forecast chart;
- **Stockout:** deterministic exposure evidence;
- **Recommendations:** calculated and stored recommendations;
- **Review Queue:** pending reviews;
- **Decisions:** approve/reject only with `recommendation:decide`;
- **Audit:** trusted actor and ordered decision history;
- explicit loading, empty, error, 401, 403, backend-waking, unavailable, and
  request-ID troubleshooting states.

An `OpsMind AI` navigation location may be reserved but contains no LLM or
placeholder claims. Exact CORS allowlists contain only reviewed Pages production
and preview origins needed by the authorized environment; wildcard credentialed
CORS remains prohibited.

## CI/CD and migrations

The target pipeline evolves across separately approved stages:

```text
pull request
-> existing Python/PostgreSQL checks
-> container build and vulnerability scan
-> frontend quality when frontend exists
-> Terraform format/validate/plan
-> owner review and merge to main
-> rebuild/verify immutable image
-> publish public GHCR full-SHA image
-> one concurrency-controlled Alembic migration from GitHub Actions
-> stop on migration failure
-> trigger Render through a secret deploy hook with the exact image identity
-> wait for /ready
-> authenticated API smoke test
-> deploy immutable frontend assets to Cloudflare Pages
-> browser/full-stack smoke test
```

Image-backed Render services do not redeploy merely because a registry tag was
updated. After the immutable image is published and migration succeeds, CI must
deliberately invoke the secret deploy hook with an `imgURL` identifying the
intended public GHCR full-SHA tag or digest. All image URL components other than
the tag/digest match the Blueprint's default image URL. `latest` is prohibited.
The returned Render deploy ID, Git SHA, and image digest form the release
evidence. Rollback selects a still-available previous digest; Render does not
retain registry images on OpsMind's behalf.

GitHub Actions is selected for migrations because Render Free has no pre-deploy
command or one-off job. The migration job uses a protected GitHub environment,
one concurrency group, the Neon direct SSL URL, the reviewed repository commit,
and the locked toolchain/image. It runs exactly one `alembic upgrade head` and
does not log the URL. Failure prevents application deployment. Application
startup never creates or migrates schema.

Expand/contract migrations preserve compatibility with the previous image.
Destructive migrations require a separate decision, backup/restore evidence,
and a rollback-safe release sequence.

## Secrets and configuration

| Classification | Values | Location and rule |
| --- | --- | --- |
| Runtime secret | Neon pooled database URL | Render secret environment value bootstrapped for a Blueprint `sync: false` key; never browser, Git, log, image, or Blueprint value |
| Migration secret | Neon direct database URL | Protected GitHub environment secret; not passed to frontend or Terraform state |
| Deployment secret | Render deploy hook/API token | Protected GitHub environment secret with minimum scope; hook URL is secret |
| IaC secret | Cloudflare, ZITADEL, and HCP tokens | HCP sensitive workspace variables or protected Actions secrets; least privilege and rotation recorded |
| Public config | API URL, environment label, ZITADEL issuer/client ID/audience, redirect URI | Cloudflare Pages environment/build configuration; explicitly non-secret |
| API config | environment, exact CORS origins, issuer, audience, JWKS URI, algorithms | Render non-secret environment configuration |

No reusable secret is committed, placed in browser code, passed as a Docker
build argument, or intentionally written into Terraform resource attributes.
Terraform plans and state are treated as sensitive even when secret values are
avoided. Secret rotation and credential-revocation procedures are Phase 8D
evidence, not assumed capability.

## Terraform and state

Terraform remains preferred. Its provider ecosystem and the team’s existing
learning goal fit this bounded design; moving to OpenTofu would not solve the
provider gaps or remove a project constraint. A later licensing/governance
change can reopen that choice.

Proposed IaC layout, only after authorization:

- official Cloudflare provider for Pages project/domain/configuration that the
  provider exposes;
- official ZITADEL provider for project, applications, API roles, and grants as
  supported;
- official Render provider monitored, but **not** used to claim Free web-service
  creation while its web-service schema excludes the Free plan;
- Render-native `render.yaml` Blueprint for the complete supported Free
  image-backed service declaration;
- no unofficial Neon provider without a separate supply-chain review;
- one HCP Terraform Free workspace/environment with reviewed plans.

The success criterion is not “everything automated.” Normal repeatable
configuration is codified as far as supported. Terraform owns supported
Cloudflare and ZITADEL resources; HCP Terraform owns their remote state and run
history; Render Blueprint owns the Free API service; Alembic owns application
schema; and GitHub Actions owns image, migration, and deploy orchestration.
HCP Terraform does not claim ownership of Blueprint-managed Render configuration
or manually bootstrapped Neon resources.

Bounded bootstrap comprises the provider accounts, HCP organization/workspace
credentials, initial Render Blueprint connection and secret values, and Neon
Free project, role, and direct/pooled credentials. A versioned, secret-free
checklist records resource identifiers, validation, and teardown; no secret
values are copied into it.

HCP Terraform Free is selected over committed or CI-local state. It provides
encrypted remote state, locking/serialized runs, VCS/run history, and recovery
within the current 500-managed-resource free limit. State is never committed.
State access uses least privilege, MFA-protected account recovery, version
history/export procedures, and tested workspace recovery. If HCP terms change,
pause IaC applies and evaluate an encrypted remote alternative; do not fall back
to an unreviewed local CI state file.

## Observability

No external telemetry service is added merely to imitate CloudWatch. The
minimum deployed evidence is:

- existing seven-field structured `opsmind.http` events on stdout/stderr;
- request-ID response propagation and UI display;
- Render service/deploy log streams and current Hobby retention limits;
- `/health` process liveness and `/ready` dependency/revision readiness;
- GitHub deployment/migration logs with secret masking;
- a troubleshooting procedure correlating browser error, request ID, release
  SHA, Render event, and database status.

Render’s current Hobby log retention is seven days, and platform HTTP request
logs are not a Free/Hobby production telemetry substitute. OpsMind’s own
bounded event remains the HTTP record. This supports portfolio troubleshooting,
not production SLOs, durable audit retention, SIEM, tracing, paging, or incident
management.

## Rollback and restore

- Every API release maps to an immutable full Git SHA and GHCR image digest.
- Render Free can roll back to its recent retained successful deployments; the
  pipeline can also redeploy a prior known digest through the protected hook.
- Cloudflare Pages can roll back the production site to a prior successful
  deployment.
- `/ready` and smoke tests gate declared success.
- Application rollback assumes expand/contract database compatibility.
- Database down-migrations are never automatic. Recovery uses a forward fix,
  a separately reviewed down migration, Neon’s bounded restore window, or a
  verified logical restore as appropriate.

The free environment has no HA/DR claim, no guaranteed RTO/RPO, and no
production backup retention.

## AWS skills track

Phase 8E is separate from the deployed product. It uses Terraform’s AWS
provider and AWS CLI against LocalStack Hobby for personal, non-commercial
learning at no AWS spend. Current Hobby-supported exercises may include:

- IAM roles, policies, and trust-document structure;
- S3 buckets, object access, versioning/lifecycle concepts where supported;
- Secrets Manager metadata and synthetic secret values only;
- CloudWatch Logs groups/streams and Metrics/Alarm APIs;
- optionally SSM Parameter Store, STS, or supported messaging only when a later
  issue establishes a concrete exercise.

LocalStack Hobby requires an auth token, permits one personal sandbox, is
subject to license/fair-use terms, and is not AWS. Hobby does not currently
provide Cognito, ECS/ELB, RDS, CloudFront, IAM policy enforcement, persisted
local state, or Cloud Pods. API emulation is not cloud fidelity, security
validation, load evidence, or proof of AWS deployment. The lab uses synthetic
values, recreates ephemeral state, and must recheck the plan’s service matrix
before each bounded exercise.

## AWS translation architecture

The earlier AWS analysis remains a technically credible paid migration/reference
architecture, not an active proposal:

| Actual zero-cost deployment | Production-style AWS analogue |
| --- | --- |
| Cloudflare Pages/CDN | Private S3 origin plus CloudFront |
| Render Docker web service | ECS on Fargate behind ALB, or App Runner |
| Neon PostgreSQL | RDS PostgreSQL |
| ZITADEL OIDC | Cognito User Pools |
| Render application/deploy logs | CloudWatch Logs and deployment events |
| GHCR and GitHub Actions | ECR and an AWS deployment pipeline |
| Platform runtime secrets | Secrets Manager and SSM Parameter Store |
| HCP Terraform multi-provider state | Terraform AWS provider with reviewed remote state |

The former Candidate B—ECS/Fargate, ALB, Single-AZ RDS PostgreSQL, Cognito,
private S3/CloudFront, ECR, Secrets Manager, CloudWatch, GitHub OIDC, and
Terraform—was operationally coherent and estimated at approximately
`$50–65/month` low usage. ALB, RDS, and public IPv4 charges created unavoidable
recurring cost; production hardening would cost more. It is deferred because it
violates the current `$0` requirement, not because AWS is technically unfit.

App Runner plus RDS was simpler but had private-database/public-JWKS egress and
migration-job gaps. Lambda/API Gateway plus Aurora Serverless v2 reduced idle
compute but introduced connection/runtime adaptation and still did not provide
a reliable zero-cost baseline. AWS remains a future migration option if cost,
traffic, governance, or production requirements justify it.

## Resume and evidence language

After implementation and evidence, accurate claims may say:

> Deployed a containerized FastAPI and React application using managed
> PostgreSQL, OAuth2/OIDC, Terraform, GitHub Actions CI/CD, CDN-hosted frontend
> delivery, external migration gates, structured observability, and rollback.

After Phase 8E evidence, an additional accurate claim may say:

> Built AWS-compatible infrastructure labs with Terraform and LocalStack for
> supported IAM, S3, Secrets Manager, and CloudWatch APIs.

The project must not say “deployed OpsMind to AWS ECS/RDS/Cognito,” “production
AWS environment,” or “production-grade AWS architecture” unless those services
are actually deployed and the evidence supports the production qualifier.
Render, Neon, Cloudflare, ZITADEL, and LocalStack must be named accurately.

## Phase 8 sequence

### Phase 8A — containerization and delivery foundation

- Add the non-root, locked API Dockerfile and local smoke test.
- Add image build, scan, OCI metadata, and immutable GHCR publication evidence.
- Preserve the modular monolith and current application behavior.

Gate: separately approved issue, full local/CI checks, image review, owner merge.

### Phase 8B — zero-cost cloud backend

- Bootstrap Neon, Render, ZITADEL, and HCP accounts/resources only as approved.
- Add supported Terraform configuration, the Render Blueprint, and explicit
  Neon/account/secret bootstrap documentation.
- Adapt ADR-0006 to ZITADEL access tokens/JWKS/roles with focused security tests.
- Add exact CORS/configuration, GitHub migration gate, deployment, readiness,
  authenticated smoke, and secret handling.

Gate: separately approved issue, `$0` verification, security review, restore and
rollback evidence, owner merge.

### Phase 8C — first integrated web dashboard

- Add React/TypeScript/Vite and Cloudflare Pages.
- Implement the Overview, business workflow, decisions, audit, authorization,
  typed API integration, cold-start UX, and troubleshooting states.
- Prove one browser-to-API-to-Neon authenticated workflow.

Gate: separately approved issue, accessibility and browser/E2E evidence,
contract/CORS/security review, owner merge.

### Phase 8D — full-stack delivery hardening

- Complete CI/CD, Terraform reconciliation, migration concurrency/failure,
  rollback, restore, cold-start, secret-rotation, and full-stack smoke evidence.
- Revalidate all free-tier terms and cost triggers.
- Conduct the formal Phase 8 review.

Gate: owner `Proceed`, `Revise`, or `Stop` review. This is still not automatic
production-readiness approval.

### Phase 8E — AWS skills and translation lab

- Add separately approved LocalStack/Terraform exercises only for verified
  Hobby-supported APIs.
- Record expected AWS behavior versus emulation limitations and the paid AWS
  translation architecture.
- Keep lab state and claims separate from the deployed product.

Gate: separately approved non-commercial learning issue, reproducible lab,
truthful evidence, owner merge.

## Phase 8 success criteria

Completion must prove, not merely propose:

- a reproducible scanned non-root OCI image and immutable public release;
- a real HTTPS FastAPI deployment and Cloudflare-hosted React/TypeScript SPA;
- durable managed PostgreSQL with controlled external migration;
- OIDC PKCE login, access-token/JWKS validation, exact authorization, and
  trusted decision attribution;
- multi-provider Terraform coverage, Render Blueprint coverage, explicit
  bootstrap exceptions, and remote locked state;
- GitHub Actions test/build/publish/migrate/deploy/smoke evidence;
- secret/configuration separation and no leaked credentials;
- liveness, readiness, structured logs, request correlation, deploy evidence,
  rollback, and bounded restore evidence;
- an authenticated browser-to-API-to-database decision and audit workflow;
- measured `$0` operation within documented limits;
- separate reproducible LocalStack AWS exercises and honest claims.

## Consequences and limitations

### Positive

- The portfolio gets a real public product path without a required monthly
  infrastructure bill.
- Docker, PostgreSQL, OIDC, IaC, CI/CD, frontend, migrations, and operations
  remain genuine rather than simulated.
- Provider-neutral seams preserve migration options.
- AWS learning is retained without deceptive deployment claims.
- The chosen database offers a future pgvector path.

### Negative and accepted

- Free-tier sleep can make the first API request take roughly a minute.
- The service is single-instance, constrained, and not highly available.
- Free logs and restore history are short.
- The Terraform/Blueprint ownership boundary and Neon bootstrap introduce
  reconciliation and drift risk.
- Four hosted providers plus GitHub/HCP create more account and credential
  surfaces than one paid platform.
- Free plans can change, throttle, suspend, or require redesign.
- ZITADEL’s 100-DAU limit is sufficient only for a portfolio.

The extra provider complexity is justified only because it preserves a real
end-to-end deployment at `$0`. Phase 8D must maintain one concise runbook and a
resource inventory so one engineer can operate and tear down the environment.
If this becomes materially harder than a small paid service, owner review may
choose a bounded paid migration; it must not quietly create charges.

## Future phase boundaries

- **Phase 9:** data pipelines remain unstarted. The deployment may later expose
  data boundaries but adds no ingestion pipeline, warehouse, queue, or scheduler.
- **Phase 10:** MLOps remains unstarted. No model registry, training job,
  experiment tracker, monitoring, or promotion workflow is added.
- **Phase 11:** LLM, RAG, embeddings, vector retrieval, tool calling, and
  LangGraph remain unstarted. Neon pgvector and external HTTPS APIs offer a
  migration path, but Free Render is not promised for long-running AI work.
  Background workers, heavier compute, external LLM cost, data governance, and
  abuse controls require separate architecture decisions.
- **Phase 12:** this portfolio deployment is not production-readiness approval.

## Decision risks and review conditions

Before acceptance, the owner should confirm:

- cold-start UX is acceptable for the public portfolio;
- ZITADEL is preferred over Auth0 given current Free role-management evidence;
- Render Blueprint ownership plus minimal Render secret/account bootstrap and
  Neon manual bootstrap are acceptable despite incomplete Terraform coverage;
- public GHCR image/source exposure is acceptable;
- HCP Terraform is acceptable for state;
- the LocalStack Hobby license fits the intended personal/non-commercial lab;
- the exact `$0` triggers and provider-change stop rule are acceptable.

Implementation must stop and return to design review if a provider removes the
needed free plan, requires an unapproved card/charge, cannot satisfy the token
contract, exposes secrets through state/logs, cannot deploy the locked image,
or makes migration/readiness behavior unsafe.

## Official sources consulted

Cloudflare:

- [Pages](https://developers.cloudflare.com/pages/)
- [Pages limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/)
- [Rollbacks](https://developers.cloudflare.com/pages/configuration/rollbacks/)
- [Redirects and SPA proxying](https://developers.cloudflare.com/pages/configuration/redirects/)
- [Pages Functions pricing](https://developers.cloudflare.com/pages/functions/pricing/)
- [Terraform provider](https://developers.cloudflare.com/terraform/)

Render:

- [Free instances](https://render.com/docs/free)
- [Web services](https://render.com/docs/web-services)
- [Docker deployment](https://render.com/docs/docker)
- [Deploys and deploy hooks](https://render.com/docs/deploys)
- [Rollbacks](https://render.com/docs/rollbacks)
- [Health checks](https://render.com/docs/health-checks)
- [Logging](https://render.com/docs/logging)
- [Blueprint infrastructure as code](https://render.com/docs/infrastructure-as-code)
- [Blueprint YAML reference](https://render.com/docs/blueprint-spec)
- [Prebuilt image deployment](https://render.com/docs/deploying-an-image)
- [Deploy hooks](https://render.com/docs/deploy-hooks)
- [Terraform provider](https://render.com/docs/terraform-provider)
- [Terraform web-service resource](https://registry.terraform.io/providers/render-oss/render/latest/docs/resources/web_service)

Backend alternatives:

- [Koyeb instance types](https://www.koyeb.com/docs/reference/instances)
- [Koyeb scale-to-zero](https://www.koyeb.com/docs/run-and-scale/scale-to-zero)
- [Koyeb Terraform](https://www.koyeb.com/docs/integrations/infrastructure-as-code/terraform)
- [Python Workers](https://developers.cloudflare.com/workers/languages/python/)
- [Python Workers packages](https://developers.cloudflare.com/workers/languages/python/packages/)
- [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)

Database:

- [Neon pricing and Free limits](https://neon.com/pricing)
- [Neon scale-to-zero](https://neon.com/docs/introduction/scale-to-zero)
- [Neon connection pooling](https://neon.com/docs/connect/connection-pooling)
- [Neon Python connection guide](https://neon.com/docs/guides/python)
- [Neon AI and pgvector](https://neon.com/docs/ai/ai-concepts)
- [Supabase pricing](https://supabase.com/pricing)
- [SQLAlchemy engine configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [SQLAlchemy connection pooling](https://docs.sqlalchemy.org/en/21/core/pooling.html)

Identity:

- [ZITADEL pricing](https://zitadel.com/pricing)
- [ZITADEL recommended OAuth flows](https://zitadel.com/docs/guides/integrate/login/oidc/oauth-recommended-flows)
- [ZITADEL OIDC endpoints and JWKS](https://zitadel.com/docs/apis/openidoauth/endpoints)
- [ZITADEL web keys and signing algorithms](https://zitadel.com/docs/guides/integrate/login/oidc/webkeys)
- [ZITADEL opaque and JWT access tokens](https://zitadel.com/docs/concepts/knowledge/opaque-tokens)
- [ZITADEL audience and project-role claims](https://zitadel.com/docs/guides/integrate/retrieve-user-roles)
- [ZITADEL role scopes](https://zitadel.com/docs/apis/openidoauth/scopes)
- [ZITADEL Terraform provider](https://registry.terraform.io/providers/zitadel/zitadel/latest)
- [ZITADEL OIDC application resource](https://registry.terraform.io/providers/zitadel/zitadel/latest/docs/resources/application_oidc)
- [ZITADEL project-role resource](https://registry.terraform.io/providers/zitadel/zitadel/latest/docs/resources/project_role)
- [Auth0 pricing](https://auth0.com/pricing)
- [Auth0 SPA SDK and PKCE](https://auth0.com/docs/libraries/auth0-single-page-app-sdk)
- [Auth0 access tokens](https://auth0.com/docs/secure/tokens/access-tokens)
- [Auth0 Terraform provider](https://registry.terraform.io/providers/auth0/auth0/latest/docs)

GitHub, Terraform, and LocalStack:

- [GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [GitHub Packages billing](https://docs.github.com/en/enterprise-cloud@latest/billing/concepts/product-billing/github-packages)
- [HCP Terraform overview](https://developer.hashicorp.com/terraform/cloud-docs/overview)
- [Terraform state](https://developer.hashicorp.com/terraform/language/state)
- [LocalStack pricing](https://www.localstack.cloud/pricing)
- [LocalStack licensing plans](https://docs.localstack.cloud/aws/licensing/)
- [LocalStack IAM](https://docs.localstack.cloud/aws/services/iam/)
- [LocalStack Secrets Manager](https://docs.localstack.cloud/aws/services/secretsmanager/)
- [LocalStack CloudWatch](https://docs.localstack.cloud/aws/services/cloudwatch/)
- [LocalStack CloudWatch Logs](https://docs.localstack.cloud/aws/services/logs/)

The AWS sources and exact pricing evidence from the first proposal remain in
Git history at commit `d9364e5`. They are preserved as reference evidence, not
as the active Phase 8 target.
