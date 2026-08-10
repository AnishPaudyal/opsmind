# ADR-0007: Select Phase 8 AWS Deployment and Product-Delivery Architecture

- Status: Proposed
- Date: 2026-08-09
- Decision owners: Anish Paudyal
- Related issues: #64, #66
- Related pull requests: Pending
- Supersedes: None
- Superseded by: None

## Owner-decision status

Repository-owner acceptance is pending. This proposal authorizes no AWS
resource, deployment code, container definition, frontend code, dependency,
workflow, or runtime change. Phase 8 implementation remains blocked until the
repository owner accepts this ADR and the accepted record is merged.

## Context

The owner-accepted Phase 7 review records `Proceed` and completes the testing,
observability, readiness, security, and architecture-hardening gate. OpsMind is
now a deployable-shaped application, but it is not deployed and is not
production ready.

The next governed question is:

> How should OpsMind move from a local FastAPI/PostgreSQL application to a
> secure, low-cost, reproducible AWS-hosted product foundation while adding the
> first real integrated web dashboard?

This is a durable architecture decision because runtime, database, network,
identity, frontend, release, and infrastructure-as-code choices will shape
multiple implementation issues and recurring operating cost.

## Current application inventory

Canonical `main` currently provides:

- Python 3.13 with a locked `uv` environment;
- a FastAPI/Uvicorn modular monolith entered through `opsmind.main:app` and
  composed by `create_app()`;
- typed `OPSMIND_` environment settings;
- synchronous SQLAlchemy and Psycopg access to PostgreSQL;
- Alembic-owned schema at `0006_workflow_persistence` with no runtime migration
  or repair;
- public, unversioned `/health` process liveness;
- public, unversioned `/ready` dependency and exact-schema readiness;
- bounded seven-field JSON request events from `opsmind.http` on stderr;
- application-validated RS256 bearer tokens for one issuer and audience;
- one statically configured RSA public verification key;
- protected product, inventory, demand, forecast, stockout, reorder,
  recommendation-review, decision, and audit APIs;
- isolated memory mode and durable PostgreSQL mode.

The repository has no API Dockerfile, frontend, infrastructure as code,
deployment workflow, AWS SDK dependency, AWS resource, managed identity
provider, online JWKS refresh, production secret store, cloud logging, backup
policy, or production-readiness approval.

Cloud deployment must preserve the modular monolith, the application factory,
repository boundaries, external migration ownership, bounded operational
contracts, structured log schema, and accepted ADR-0006 trust boundary.

## Phase 8 objectives

Phase 8 should establish a path to:

- run the FastAPI API from an immutable OCI image;
- persist state in managed PostgreSQL;
- execute one controlled migration before a release depends on new schema;
- expose bounded `/health` and `/ready` through HTTPS;
- authenticate a real browser user and authorize protected API actions;
- keep secrets out of Git and use short-lived GitHub-to-AWS credentials;
- collect the existing structured logs and basic operational signals;
- reproduce the environment from reviewed infrastructure as code;
- deploy automatically with smoke evidence and a bounded rollback path;
- deliver a real integrated dashboard over current APIs;
- operate one low-usage development/portfolio environment at a visible cost.

Completing these objectives would demonstrate a credible cloud product
foundation. It would not by itself establish production readiness, HA/DR,
compliance, or proven scale.

## Decision drivers

- Fit with the existing long-running FastAPI/SQLAlchemy/PostgreSQL process
- Controlled Alembic migration and readiness behavior
- Private database access without an unnecessarily expensive NAT Gateway
- Low, understandable portfolio-environment cost
- Reproducibility and rollback evidence
- Industry-relevant container, network, IAM, and release learning
- Provider-agnostic application identity under ADR-0006
- A simple static dashboard that leaves FastAPI as backend authority
- Future data, ML, and LLM extensibility without premature distribution
- Operability by one engineer
- No premature Kubernetes, microservices, or production-scale topology

## Cost assumptions

Estimates use current public prices researched on 2026-08-09 and assume:

- US East (N. Virginia), 730 hours per month;
- one low-traffic development/portfolio environment;
- one continuously running API task where applicable;
- one small Single-AZ database or a scale-to-zero serverless database;
- 20 GB initial relational storage;
- low log, request, image, and static-site volume;
- one hosted zone when a custom domain is used;
- no promotional account credits;
- current service free allowances only where explicitly stated.

Taxes, domain registration, internet data transfer, SMS/email, large log
queries, enhanced image scanning, extra backups, and traffic-driven scaling are
excluded. Estimates are planning ranges, not billing guarantees. The AWS
Pricing Calculator must be rerun before implementation and cost reviewed after
the first month.

Current official price-list evidence includes:

- Fargate Linux/x86: `$0.04048` per vCPU-hour and `$0.004445` per GB-hour;
- RDS PostgreSQL Single-AZ `db.t4g.micro`: `$0.016` per hour;
- RDS PostgreSQL gp3 storage: `$0.115` per GB-month;
- Aurora Serverless v2 PostgreSQL: `$0.12` per ACU-hour, plus storage and I/O;
- ALB: `$0.0225` per hour plus `$0.008` per LCU-hour;
- public IPv4: `$0.005` per address-hour;
- NAT Gateway: `$0.045` per hour plus `$0.045` per GB and public IPv4;
- App Runner: `$0.007` per provisioned GB-hour and `$0.064` per active
  vCPU-hour in the listed US regions;
- ECR private storage: `$0.10` per GB-month;
- Secrets Manager: `$0.40` per secret-month plus API calls;
- Route 53: `$0.50` per hosted zone-month for the first 25 zones;
- Cognito Lite and Essentials: 10,000 direct/social monthly active users in
  the ongoing free tier;
- Amplify Hosting beyond its allowance: `$0.01` per standard build minute,
  `$0.023` per stored GB-month, and `$0.15` per served GB.

## Candidate architectures

### Candidate A — App Runner, RDS PostgreSQL, and managed static hosting

```text
Browser -> CloudFront/static frontend -> App Runner -> RDS PostgreSQL
                      |                    |
                    Cognito          VPC connector
```

App Runner supplies a managed HTTPS service, image deployment, request scaling,
and low idle compute cost. It is the simplest container runtime considered and
fits the existing Uvicorn process without an ASGI adapter.

The private-database path is the decisive limitation. App Runner reaches RDS
through a VPC connector in private subnets. AWS documents that all application
outbound traffic then follows that VPC and loses public-internet access. The
future Cognito JWKS refresh path is public, so a complete design needs NAT or
another supported egress path. App Runner also has no equally natural one-off
release task for Alembic; adding ECS only for migrations weakens its simplicity.

Strengths:

- smallest runtime-management surface;
- built-in service URL, TLS, scaling, and managed image pull/log transport;
- direct container fit and useful managed-service learning;
- low cost when static-key operation needs no public egress.

Weaknesses:

- private RDS plus public JWKS egress introduces a NAT cost or a design gap;
- controlled one-off migrations need a separate mechanism;
- less control over deployment health and rollback than the ECS proposal;
- lower container/network learning value for the project portfolio.

Low-usage estimate:

- approximately `$22–38/month` before NAT, dominated by RDS and App Runner;
- approximately `$58–75/month` when one NAT Gateway and its IPv4 are required;
- variable logs, data transfer, DNS, and active CPU are additional.

Future fit: acceptable for the current API but less convenient for separate
data/ML jobs and the explicit migration gate. It remains the fallback if owner
priority shifts decisively toward minimum runtime operations and the egress
problem is solved without making the database public.

### Candidate B — ECS on Fargate, ALB, RDS PostgreSQL, and S3/CloudFront

```text
                         +-> Cognito
                         |
Browser -> CloudFront SPA+-> ALB (HTTPS) -> ECS/Fargate -> RDS PostgreSQL
                                             |             (private)
                                             +-> CloudWatch Logs
GitHub OIDC -> ECR -> migration task -> ECS service deployment
```

One small Fargate task runs in a public subnet with a public IPv4 address for
outbound ECR, Secrets Manager, CloudWatch, and future Cognito JWKS access. Its
security group accepts application traffic only from the ALB security group;
direct internet ingress is denied. RDS remains non-public in private database
subnets and permits port 5432 only from the application/migration task security
group.

This is intentionally a cost-aware first environment, not the generic
production pattern of private tasks behind NAT. A single public task address is
about `$3.65/month`; one NAT plus its address is about `$36.50/month` before
data. Private Fargate tasks with NAT or interface endpoints become a future
hardening option when availability, scale, or compliance justifies them.

Strengths:

- direct container and PostgreSQL fit;
- native one-off Fargate migration task from the same immutable image;
- explicit task, execution, deployment, network, and secret boundaries;
- ALB readiness checks and ECS deployment circuit-breaker rollback;
- strong industry and portfolio relevance without Kubernetes;
- natural future path for separately governed worker or ML tasks.

Weaknesses:

- ALB and public IPv4 charges dominate low-traffic compute cost;
- more IAM, VPC, task-definition, and release configuration than App Runner;
- the first environment has one API task and Single-AZ RDS, so it is not HA;
- a task public address increases exposure surface even though its security
  group denies direct ingress.

Low-usage estimate:

- Fargate 0.25 vCPU/0.5 GB x86 task: about `$9.01/month`;
- task public IPv4: about `$3.65/month`;
- ALB base: about `$16.43/month`, plus low LCU usage;
- two ALB public IPv4 addresses: about `$7.30/month`;
- `db.t4g.micro`: about `$11.68/month`;
- 20 GB gp3: about `$2.30/month`;
- ECR, one secret, DNS, frontend, logs, and alarms: approximately `$2–12`;
- expected total: approximately `$50–65/month`, excluding domain registration
  and traffic spikes.

Future fit: strongest of the candidates. Later data/ML/LLM work can add bounded
tasks or services without splitting the current modular monolith prematurely.

### Candidate C — API Gateway, Lambda, Aurora Serverless v2, and static hosting

```text
Browser -> CloudFront SPA -> API Gateway -> Lambda -> Aurora Serverless v2
                  |                         |
                Cognito                VPC/JWKS egress
```

Lambda and HTTP API can be inexpensive at low request volume, and compatible
Aurora PostgreSQL versions can scale Serverless v2 capacity to zero. This is
not a drop-in deployment for current OpsMind. It needs an ASGI-to-Lambda adapter
or runtime integration, careful SQLAlchemy connection handling, a VPC egress
answer for JWKS, and a separate migration mechanism. Database resume latency
also interacts with `/ready`, smoke tests, and user experience.

Strengths:

- near-zero request compute at very low use within applicable allowances;
- automatic request scaling;
- Aurora Serverless v2 can auto-pause on supported versions;
- useful event-driven learning.

Weaknesses:

- changes the current request/runtime lifecycle and adds an adapter;
- burst concurrency can multiply PostgreSQL connections or require RDS Proxy;
- cold database resume can make readiness temporarily fail;
- migrations, rollback, streaming behavior, and existing error middleware need
  new evidence;
- NAT, proxy, and Aurora choices can erase the headline compute savings;
- weaker fit for later containerized data/ML workloads.

Low-usage estimate:

- approximately `$5–25/month` when Lambda/API traffic is within low-use
  allowances and Aurora actually spends substantial time paused;
- RDS Proxy, NAT, longer database activity, logs, or nonzero minimum ACUs can
  materially increase the total;
- this range is more workload-sensitive than Candidates A or B.

Future fit: viable for a purpose-designed serverless API, but the current
FastAPI/PostgreSQL application would pay material migration complexity for an
unproven traffic pattern.

## Decision

Propose **Candidate B: ECS on Fargate behind an Application Load Balancer, RDS
PostgreSQL, a React/TypeScript/Vite SPA in private S3 through CloudFront,
Cognito user-pool authentication, and Terraform** for the first Phase 8
development/portfolio environment.

The explicit first implementation is:

| Concern | Proposed choice |
| --- | --- |
| Region | US East (N. Virginia), configurable rather than embedded in application code |
| API artifact | Minimal Linux/x86_64 OCI image, Python 3.13, non-root user, locked production dependencies |
| Registry | Private ECR repository; immutable Git-SHA tags and retention policy |
| API runtime | ECS service on Fargate, one 0.25-vCPU/0.5-GB task initially |
| Ingress | Internet-facing ALB with HTTPS and HTTP-to-HTTPS redirect |
| Database | RDS PostgreSQL Single-AZ `db.t4g.micro`, 20 GB encrypted gp3 |
| Frontend | React, TypeScript, Vite, React Router, TanStack Query, and a restrained reviewed chart library |
| Frontend hosting | Private S3 origin through CloudFront Origin Access Control |
| Identity | Cognito user pool using authorization code with PKCE; no SPA client secret |
| Network | Two public subnets and two private DB subnets across two AZs; no NAT Gateway initially |
| Secrets | One Secrets Manager database secret; least-privilege task retrieval |
| Non-secret config | ECS environment values or SSM `String` parameters where independent lifecycle is useful |
| Logs | Existing stdout/stderr through ECS `awslogs` to CloudWatch Logs |
| CI/CD identity | GitHub Actions OIDC to narrowly scoped AWS roles |
| Migration | One-off Fargate task running `alembic upgrade head` before service deployment |
| IaC | Terraform with versioned encrypted S3 state and native S3 lockfile |
| Environment | Local development plus one AWS `dev`/portfolio environment |
| Backup | Seven-day automated RDS backups/PITR, final snapshots, and scheduled restore verification |
| Domain/TLS | ACM-managed certificates; stable frontend/API hostnames when a domain is available |

The AWS resource environment is named `dev`, but the application sets
`OPSMIND_ENVIRONMENT=staging`, which is the existing non-local, non-production
enum value. Phase 8 does not add a new application environment solely to mirror
an infrastructure label.

Why not App Runner: its managed simplicity is offset by private-RDS/public-JWKS
egress and migration-job problems. Adding NAT and a second execution mechanism
removes its cost and simplicity advantage.

Why not Lambda: the current application is a long-running ASGI and SQLAlchemy
service with explicit readiness and migration semantics. Lambda introduces an
adapter, connection/cold-start concerns, and different failure evidence without
a demonstrated scaling need.

Why not Kubernetes: one modular-monolith API, one database, one SPA, and one
engineer do not justify cluster, ingress-controller, workload-identity, or
upgrade complexity.

## Container and image design

Phase 8A should add one API Dockerfile only after this ADR is accepted. It must:

- use a pinned, reviewed Python 3.13 runtime base and deterministic `uv`-locked
  installation;
- install runtime dependencies only and copy the packaged application;
- run as a numeric non-root user with a read-only application tree;
- expose only the application port and run Uvicorn for
  `opsmind.main:app` without development reload;
- preserve environment-only configuration and stdout/stderr logging;
- include no credential, token, private key, `.env`, test data, or build cache;
- support local build and health/readiness smoke tests on Apple Silicon while
  producing the explicitly selected x86_64 deployment image;
- use multi-stage construction, a `.dockerignore`, and a small runtime image;
- tag ECR images by full Git commit SHA, never deploy mutable `latest`, and
  retain a bounded number of prior deployable images;
- produce an SBOM and use ECR basic scanning initially; enhanced continuous
  scanning is a later cost/need decision.

ARM Fargate is cheaper at current rates and Python supports it, but the first
image remains x86_64 to match hosted CI and reduce cross-build uncertainty.
Reconsider ARM after the full image, cryptography, Psycopg, and PostgreSQL test
gate runs natively for that architecture.

## PostgreSQL and migration architecture

RDS PostgreSQL is proposed because it directly matches SQLAlchemy, Psycopg, and
Alembic without an engine or repository redesign. The first database is:

- Single-AZ `db.t4g.micro` with 20 GB gp3 and storage autoscaling bounded by a
  reviewed maximum;
- encrypted at rest with an AWS-managed key initially;
- non-public in a DB subnet group spanning two AZs;
- protected by a database security group accepting 5432 only from the API and
  migration task security group;
- configured for seven days of automated backups and point-in-time recovery;
- protected from accidental deletion, with an explicit final snapshot on
  governed teardown;
- monitored for CPU, free storage, connections, and availability.

Single-AZ is a deliberate cost choice for the one dev environment, not an HA
claim. Multi-AZ, larger instances, read replicas, RDS Proxy, cross-region
copies, and advanced Performance Insights are future production-hardening
choices driven by observed need.

Aurora PostgreSQL/Serverless v2 is not proposed. Its scale-to-zero capability is
credible for intermittent development, but version eligibility, pause/resume
latency, ACU/I/O billing, connection behavior, and readiness interactions add
complexity. RDS PostgreSQL provides the smallest predictable architecture for
the current workload.

Application startup continues not to migrate. A deployment runs exactly one
standalone Fargate task from the candidate image with the same database secret
and network security group:

```text
build immutable image
-> start migration task: alembic upgrade head
-> require exit code 0
-> register/deploy API task definition
-> require ALB /ready success
-> run authenticated smoke tests
```

A failed migration blocks the release. Schema changes must use expand/contract
compatibility so the previous image remains deployable. Routine rollback means
redeploying the previous immutable task definition; it does not automatically
run `alembic downgrade`. A failed destructive migration requires the separately
reviewed restore procedure, not an improvised down migration.

## Network, ingress, TLS, and domain design

The first VPC contains two public subnets and two private database subnets in
two Availability Zones:

```text
Internet
   |
ALB in public subnets (443; 80 redirect)
   |
task SG -> one Fargate task in a public subnet with public egress
   |
private VPC address
   |
RDS in private DB subnets, publicly_accessible = false
```

Security-group rules are source based:

- ALB: inbound 443 from clients and 80 only for redirect; outbound only to the
  task application port;
- task: inbound application port only from the ALB security group; outbound
  5432 only to the database security group and 443 for required AWS/IdP
  endpoints;
- database: inbound 5432 only from the task security group; no public route or
  public address.

The task's public IPv4 address exists only to avoid a `$36.50/month` NAT
baseline for one low-volume task. It does not authorize direct inbound traffic.
The ALB reaches the task inside the VPC and its security group blocks other
sources. Public task placement must be revisited for a production-like
environment, multiple tasks, stricter egress control, or compliance needs.

The ALB target-group health check uses `/ready`; container/process health can
use `/health`. Because AWS documents that ALB target groups fail open when all
targets are unhealthy, readiness is a routing and deployment signal, not an
access-control boundary. The ECS deployment circuit breaker, CloudWatch alarms,
and post-deploy smoke test remain required.

TLS terminates with non-exportable ACM public certificates, which currently
have no certificate charge on integrated ALB and CloudFront services. HTTP
redirects to HTTPS. A custom domain is recommended once available:

- `app.<domain>` for CloudFront;
- `api.<domain>` for the ALB.

Route 53 is proposed for DNS when the owner supplies a domain. Domain
registration is excluded from the cost estimate. Until then, CloudFront and ALB
service domains can support infrastructure smoke tests, but stable Cognito
callback and CORS origins must be explicit. CORS allows only the exact deployed
frontend origin and intentional local development origins; it never uses
credentialed wildcard origins.

## Secrets and non-secret configuration

The boundary is:

| Classification | Examples | Proposed storage |
| --- | --- | --- |
| Secret | PostgreSQL username/password and full connection URL | One Secrets Manager secret injected by the ECS execution role |
| Non-secret | service/environment name, API prefix, AWS Region, issuer, audience, JWKS URI, algorithm, CORS origins | Reviewed task environment or SSM `String` parameters |
| Public integrity-sensitive material | RSA public key or JWKS metadata | Validated configuration/cache, never treated as credential material |
| Browser-public configuration | API base URL, Cognito issuer/client ID, redirect URI | Vite build/runtime configuration; no secret client key |

Secrets never enter Git, image layers, Terraform state values, GitHub
repository secrets, command output, logs, or frontend assets. Terraform may
create secret containers and IAM references but must not embed secret values.
The first full database URL is supplied through a documented, non-echoing
Secrets Manager bootstrap step outside Terraform; that explicit prerequisite
is reviewable and must never print the value. A future move to RDS-managed
credentials or component settings requires separate application evidence.
Secret rotation restarts the ECS task because injected environment values do
not update a running task automatically.

## GitHub-to-AWS identity and CI/CD

GitHub Actions uses OIDC federation, not long-lived AWS access keys. AWS IAM
trust conditions must bind the role to this repository and the intended branch,
tag, or protected GitHub environment. The workflow grants `id-token: write`
only to jobs that assume an AWS role and keeps `contents: read` otherwise.

Separate least-privilege roles are proposed:

- a plan/read role for reviewed Terraform plans and state reads;
- an image role for ECR authentication and immutable image push;
- a deployment role for the one environment, migration task, ECS service,
  frontend bucket/invalidation, and narrowly scoped Terraform apply.

If one role is used initially to reduce bootstrap complexity, its policy must
still be resource scoped and split when permissions or environments expand.
GitHub environment protection gates deployment from canonical `main`.

The future release pipeline is:

```text
pull request
-> locked Python and frontend quality/security checks
-> merge main
-> OIDC role
-> build/test/SBOM/scan immutable image
-> push Git-SHA image to ECR
-> Terraform plan/apply when infrastructure changed
-> one-off Alembic migration task
-> ECS rolling deployment with circuit-breaker rollback
-> /health and /ready smoke
-> authenticated business-read smoke
-> deploy immutable frontend assets and invalidate changed entry assets
-> record release evidence
```

Pinned third-party actions, least permissions, concurrency control, artifact
provenance, and failure-safe logs are implementation acceptance criteria. A
deployment failure keeps or restores the previous completed task definition.
Database rollback follows the expand/contract and restore rules above.

## Cloud observability and operational baseline

The existing `opsmind.http` event remains the application request event. The
ECS `awslogs` driver forwards container stdout/stderr to a CloudWatch log group
with a 30-day dev retention. CloudWatch Logs Insights can query the JSON fields,
including request ID, route template, status, duration, and bounded error
category. Tokens, claims, principal IDs, bodies, SQL, and traceback content
remain excluded from the governed event.

Initial alarms remain small and actionable:

- ALB unhealthy target or sustained 5xx;
- ECS deployment failure or running task count below desired;
- RDS CPU, connection, free-storage, and availability thresholds;
- application log evidence for sustained dependency unavailability;
- AWS Budget/cost threshold for the one environment.

Alarm destinations and on-call maturity are not claimed. OpenTelemetry,
external tracing, SIEM, formal SLOs, and an incident-management platform remain
future work. Retention and query volume receive a cost review after the first
month.

## Backup, restore, and rollback baseline

- RDS automated backup retention: seven days with PITR.
- Manual final snapshot before a governed environment destroy.
- Restore verification: at least quarterly for a retained environment and
  before any production-readiness claim.
- Immutable image tags and retained prior task definitions.
- ECS circuit-breaker rollback to the last completed application deployment.
- Forward-compatible migrations; no automatic downgrade.
- Frontend assets versioned by build, with the prior release redeployable.
- Terraform state encrypted, versioned, and locked; state recovery tested
  before relying on it for production governance.

This is a development baseline, not advanced disaster recovery. RTO, RPO,
cross-region backup, multi-AZ failover, restore automation, and game days remain
future production-readiness decisions.

## Identity provider and key rotation

### Options

**Cognito user pools** provide an AWS-managed OAuth/OIDC issuer, hosted login,
JWT access tokens, JWKS discovery/rotation, authorization-code PKCE support,
and an ongoing low-MAU allowance. They integrate naturally with the selected
AWS environment but add user-pool and claim-provisioning configuration.

**Auth0 or another external OIDC provider** can offer strong developer
ergonomics and remains compatible with ADR-0006. It adds another vendor,
billing boundary, and operational surface without a demonstrated need for the
first AWS-focused portfolio environment.

**Static/manual tokens** can support a narrow infrastructure smoke test but do
not provide a credible user login, revocation, key rotation, or integrated
dashboard flow. They are not an acceptable final Phase 8 authentication path.

### Proposal

Use one Cognito user pool with a public SPA client and authorization code plus
PKCE. The frontend obtains an access token and sends it only in the
`Authorization: Bearer` header. It never puts a token in a URL. Access and ID
tokens are not stored in `localStorage`; the first client keeps tokens in
memory, uses a reviewed OIDC library, and accepts reauthentication rather than
introducing a browser-held long-lived secret. A later persistent-session or
backend-for-frontend decision requires separate threat review.

ADR-0006 remains provider agnostic and authoritative. Cognito integration
requires an explicit application implementation item because the current
authenticator accepts one static PEM key and a list-valued `permissions` claim.
The Phase 8 implementation must:

- discover or configure one trusted JWKS URI;
- cache keys by `kid`, refresh them with bounded timeouts and frequency, and
  retain fail-closed issuer/audience/algorithm validation;
- map reviewed Cognito resource-server scopes or claims into only
  `business:read`, `business:write`, and `recommendation:decide`;
- preserve application-scoped injection and deterministic offline tests;
- define whether cached-key refresh affects readiness without adding an
  unbounded IdP request to every API request;
- preserve stable Cognito `sub` as the terminal decision/audit principal ID.

Grant administration remains external. OpsMind still does not add passwords,
local users, organizations, tenants, or row-level authorization.

## Frontend architecture

### Technology choice

Use a client-rendered React/TypeScript application built with Vite. The product
is an authenticated, interaction-heavy dashboard whose current data authority
is FastAPI; it has no search-indexing, public-content, server rendering, or
server-action requirement. Next.js can statically export an SPA, but its server
and rendering model adds concepts without current value. Reconsider Next.js if
public SEO content, per-request server rendering, or a backend-for-frontend
becomes a real requirement.

The proposed client structure uses:

- React and TypeScript;
- Vite build/dev tooling;
- React Router for client routes;
- TanStack Query for remote server state, cache invalidation, and request
  lifecycle;
- generated TypeScript types from the committed/reviewed FastAPI OpenAPI
  contract, with a thin handwritten transport/auth/error layer;
- one reviewed, restrained chart library for demand and forecast series;
- feature-oriented components and accessible design primitives.

Generated code is build evidence, not the contract authority, unless a later
issue deliberately commits it. CI detects OpenAPI/client drift. Frontend state
does not duplicate backend business rules.

### Hosting choice

Use a private S3 bucket through CloudFront Origin Access Control. This provides
static hosting, HTTPS, caching, explicit AWS/IaC learning, and very low usage
cost without a frontend server. The bucket is not a public website endpoint.
CloudFront serves the SPA entry fallback, immutable hashed assets, and an ACM
certificate when a custom domain is available.

Amplify Hosting is a credible simpler alternative with managed Git builds,
previews, HTTPS, and a low free allowance. It is not proposed because the
selected GitHub OIDC pipeline and Terraform already own release automation;
S3/CloudFront keeps deployment and caching explicit and avoids a second CI
control plane. Reconsider Amplify if branch previews become more valuable than
infrastructure transparency.

### Browser/API contract

- The API base URL is non-secret environment configuration.
- CORS permits exact frontend and intentional local origins only.
- The OIDC library performs authorization code plus PKCE.
- The request layer attaches the in-memory access token as a bearer header.
- `401` clears the invalid session and starts reauthentication.
- `403` renders an authorized-identity/insufficient-permission state.
- Decision controls may be hidden or disabled by known scopes for usability,
  but FastAPI remains authoritative.
- Response `X-Request-ID` appears in bounded troubleshooting errors and can be
  correlated with CloudWatch logs.
- Loading, empty, stale, unavailable, and validation states are explicit.
- `/health` and `/ready` remain public and unversioned; a dashboard readiness
  indicator must not expose internal details.

## First dashboard scope

The Phase 8C dashboard is a real client, not a mock. Its first screens are:

1. **Overview** — service readiness, product count, inventory/stockout
   attention, and recommendation-review summary.
2. **Products** — list and product detail.
3. **Inventory** — current on-hand, allocated, and available quantities,
   preserving negative availability.
4. **Demand and forecast** — chronological demand observations and the bounded
   baseline forecast visualization.
5. **Stockout exposure** — current deterministic exposure evidence.
6. **Reorder recommendations** — recommendation calculation and stored snapshot
   details.
7. **Review queue** — pending stored recommendations.
8. **Decision** — approve or reject only for a principal with
   `recommendation:decide`.
9. **Audit** — ordered trusted decision history.

Current product, inventory, demand, forecast, stockout, reorder, individual
review, decision, and audit endpoints supply most screens. The API does not yet
list stored recommendation reviews, so a review queue cannot be implemented
honestly from current contracts. Phase 8C must open a separately scoped API
contract issue for a bounded review-list/pending filter if the queue remains in
the accepted first slice. An overview aggregation endpoint is optional only if
measured client fan-out becomes excessive; it is not invented preemptively.

Visual direction is a professional, restrained, desktop-first responsive
operations dashboard: clear hierarchy, dense but readable tables, accessible
status and risk treatments, and charts only where they aid decisions. Reserve
a future navigation area named `OpsMind AI`, but add no chatbot, copilot, or AI
behavior in Phase 8.

## First end-to-end full-stack slice

The accepted implementation should eventually prove that a user can:

1. open the CloudFront-hosted dashboard over HTTPS;
2. sign in through Cognito authorization code plus PKCE;
3. load real products from the deployed FastAPI API;
4. inspect inventory, demand, forecast, stockout, and reorder evidence;
5. store a recommendation review;
6. approve or reject it only with `recommendation:decide`;
7. retrieve audit history whose actor equals the trusted Cognito subject;
8. correlate a displayed request ID with the bounded CloudWatch event;
9. observe that data persists across API task replacement.

This proves one authenticated product workflow. It does not prove production
scale, tenant isolation, advanced forecast quality, or external ordering.

## Infrastructure-as-code decision

### Terraform

Terraform provides declarative plans, reviewable state transitions, broad AWS
coverage, strong industry relevance, and portable IaC learning. Its state and
provider lifecycle add operational responsibility. The proposed backend uses
an encrypted, versioned S3 bucket and native S3 lockfile (`use_lockfile = true`);
HashiCorp now marks DynamoDB locking deprecated. Backend bootstrap must be a
small, documented, repeatable prerequisite rather than hidden console work.

### AWS CDK

CDK would let the project use Python or TypeScript abstractions and synthesizes
CloudFormation templates. It is credible and AWS-native, but adds construct,
bootstrap, synthesis, and generated-template layers. The convenience is not
enough to outweigh Terraform's direct plan/state learning for this portfolio.

### Raw CloudFormation

CloudFormation is the underlying AWS-native stack model and avoids a third-party
state engine. For this multi-service design, verbose templates and intrinsic
functions create more maintenance cost than learning value.

### Proposal

Use Terraform, pinned by version constraints, with format, validate, plan, and
security/static checks added during Phase 8B. Separate reusable modules only
where actual repetition appears. One environment uses one explicit state path;
workspaces do not stand in for deliberate future environment isolation.

## Implementation sequence

### Phase 8A — cloud packaging foundation

- Add the reviewed API Dockerfile and ignore rules.
- Prove locked, non-root, secret-free x86_64 image construction.
- Run local `/health`, `/ready`, security, logging, and PostgreSQL container
  smoke tests.
- Document image metadata, SBOM, scanning, and immutable tagging.
- Define validated cloud configuration without provisioning resources.

Gate: owner-reviewed image design and complete local quality/coverage evidence.

### Phase 8B — AWS backend foundation

- Add Terraform state bootstrap documentation and reviewed IaC.
- Define VPC/subnets/routes/security groups without NAT.
- Define ECR, RDS, Secrets Manager reference, ECS/Fargate, ALB, ACM, Route 53
  options, CloudWatch, backups, and budget controls.
- Add GitHub OIDC roles and pinned plan/deploy workflows.
- Add the one-off migration task, ECS deployment circuit breaker, readiness,
  authenticated smoke, and rollback evidence.
- Implement separately reviewed Cognito JWKS/scope integration under ADR-0006.

Gate: reproducible backend environment, private database, HTTPS, migration,
readiness, authentication, logs, rollback, backup, and cost evidence.

### Phase 8C — first integrated frontend

- Scaffold React/TypeScript/Vite with frontend quality and accessibility gates.
- Integrate Cognito PKCE, in-memory tokens, typed OpenAPI contracts, exact CORS,
  and bounded error/request-ID behavior.
- Implement the defined dashboard screens against real APIs.
- Add the bounded review-list API only through a separately approved issue.
- Deploy immutable assets to private S3/CloudFront.

Gate: real local and cloud API data, permission-aware decisions, audit actor,
responsive UI, and frontend/backend contract evidence.

### Phase 8D — cloud full-stack integration

- Run the complete authenticated browser workflow.
- Prove persistence across task replacement and schema compatibility.
- Exercise failed deployment rollback and a non-destructive restore check.
- Verify logs, alarms, cost, no hidden snowflake steps, and teardown/runbook
  accuracy.
- Perform the formal Phase 8 review.

Gate: owner `Proceed`, `Revise`, or `Stop` review. Phase 8 completion still does
not automatically mean production ready.

Each phase segment requires its own approved issue. Acceptance of this ADR is
not blanket implementation authorization.

## Phase 8 success criteria

- All resources are reproducible from reviewed Terraform plus a documented
  state bootstrap.
- GitHub deployment uses short-lived OIDC credentials and no long-lived AWS
  access keys.
- The API runs as one non-root immutable Git-SHA image.
- Managed PostgreSQL persists operational and workflow state.
- RDS has no public endpoint and only task-scoped database ingress.
- Alembic runs once outside application startup and failure blocks release.
- `/health` remains process liveness and `/ready` proves database/revision
  compatibility.
- Frontend and API use HTTPS with exact CORS.
- Protected routes accept only validated issuer/audience/signature and mapped
  permissions with bounded JWKS caching/rotation.
- CloudWatch contains the existing bounded structured events searchable by
  request ID.
- The real dashboard reads and mutates real API data with complete loading,
  error, and permission states.
- Approval/rejection uses the trusted principal and audit history preserves the
  same actor end to end.
- Build, migration, deployment, readiness, authenticated smoke, and frontend
  release are automated and reviewable.
- Previous application/frontend artifacts remain redeployable.
- Backup retention is enabled and restore evidence exists.
- Actual first-month cost is recorded and compared with this estimate.
- Normal deploy and teardown contain no undocumented console-only step.
- No production-readiness, HA, compliance, or model-quality claim exceeds the
  evidence.

## Consequences

### Positive

- OpsMind gains a concrete AWS and first-frontend path without changing its
  modular-monolith authority.
- Migration, readiness, identity, logging, and rollback boundaries remain
  explicit.
- The architecture develops relevant ECS, RDS, VPC, IAM, OIDC, Terraform,
  CloudFront, and browser-integration skills.
- One environment and no NAT bound initial complexity and cost.
- Later tasks can support data/ML workloads without premature Kubernetes.

### Negative

- Approximately `$50–65/month` is meaningful for a low-traffic portfolio
  environment.
- ALB and three public IPv4 addresses cost more than the API compute.
- Public-subnet task placement is a conscious non-production compromise.
- Cognito JWKS and scope mapping require new security implementation evidence.
- Terraform state bootstrap and IAM roles add operational responsibility.
- The frontend introduces a separate TypeScript dependency and quality surface.

### Neutral

- RDS is Single-AZ and the ECS service has one task initially.
- Cognito is the first provider, while the application principal remains
  provider agnostic.
- S3/CloudFront is selected over Amplify; both remain viable static hosts.
- The current product API remains authoritative; one real review-list gap is
  explicitly deferred to a separate API issue.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Idle cloud cost | One environment, smallest credible resources, no NAT, budget alarm, monthly review, explicit teardown |
| Public task address | ALB-only ingress security group, narrow egress, no SSH, no credentials in image, future private-task trigger |
| Database exposure | Non-public RDS, private subnets, task-SG-only 5432, encrypted secret and storage |
| IAM overreach | GitHub OIDC, repository/branch conditions, protected environment, resource-scoped roles, no static keys |
| Migration failure | One migration task, block release, expand/contract schemas, no startup migration, restore procedure |
| Broken rollback | Immutable images/task definitions, circuit breaker, readiness/smoke, backward-compatible schema |
| Cognito/provider coupling | ADR-0006 principal/permission seam, standard OIDC/JWKS, no provider types in domain/repositories |
| JWKS outage/rotation | Bounded cached keys, `kid` refresh, timeouts, stale-key policy under explicit tests, fail closed |
| Browser token theft | Authorization code PKCE, memory-only tokens, no URL/localStorage token, CSP/XSS controls, backend authority |
| CORS widening | Exact deployed/local origins; no credentialed wildcard |
| Frontend/backend drift | OpenAPI-derived types and CI contract-drift check |
| Hidden cloud snowflake | Terraform, scripted migration/deploy/smoke, documented state bootstrap |
| Backup illusion | PITR plus recurring restore verification; no DR claim |
| Local/cloud divergence | Same image, lockfile, config model, PostgreSQL migrations, and smoke contracts |

## Explicit non-goals and future production hardening

The first Phase 8 implementation does not include or claim:

- multiple always-on environments;
- multi-AZ RDS or multiple API tasks;
- private ECS tasks with NAT/endpoints;
- multi-region, advanced DR, formal RTO/RPO, chaos testing, or HA approval;
- Kubernetes or microservices;
- enterprise SSO administration, application users, organizations, tenants, or
  row-level policy;
- WAF policy maturity, SIEM, SOC, penetration testing, formal SLO/error budget,
  or incident-response maturity;
- production secret rotation automation;
- advanced autoscaling or performance qualification;
- forecast-model expansion, supplier/order integration, or product redesign;
- production-readiness approval.

Production hardening may later add multiple tasks across AZs, Multi-AZ RDS,
private task subnets with justified egress, stronger egress controls, WAF,
cross-region backups, restore automation, SLOs, and a second environment. Those
changes require evidence and governance rather than being implied here.

## Future data, MLOps, and AI seam

Phase boundaries remain:

```text
Phase 9  -> governed data pipelines and analytical data foundations
Phase 10 -> MLOps, training, registry, evaluation, and model lifecycle
Phase 11 -> LLM integration, RAG, embeddings/vector retrieval, tool calling,
            LangGraph, and governed AI workflows
Phase 12 -> production-readiness review and portfolio packaging
```

The ECS/VPC/IAM/container foundation can later host separately governed batch
tasks or services. The dashboard reserves an `OpsMind AI` navigation seam, but
Phase 8 adds no model, LLM, RAG, vector store, tool, agent, or LangGraph code.
The application remains a modular monolith until evidence justifies another
boundary.

## Critical design review

The proposal was challenged against the Issue #66 review questions:

- The NAT Gateway was removed because its idle cost exceeds the one-task public
  IPv4 compromise.
- ALB cost remains justified by stable HTTPS, health routing, deployment
  integration, and industry learning, but it is the largest avoidable runtime
  cost and a reconsideration trigger.
- RDS is the smallest predictable direct PostgreSQL fit; Aurora is not selected
  for novelty.
- The database is private and security-group scoped.
- Secret and non-secret configuration are separated.
- GitHub uses short-lived OIDC credentials.
- Migrations remain outside startup and block release on failure.
- `/ready` is a target/deployment signal with ALB fail-open behavior documented.
- Rollback and backup limitations are explicit.
- Cognito requires bounded JWKS and scope-mapping implementation; it is not
  assumed compatible without work.
- Tokens avoid URLs and local storage; exact CORS is required.
- React/Vite avoids an unnecessary frontend server.
- The dashboard uses current APIs and identifies the one genuine queue-list gap.
- One engineer can operate one environment without Kubernetes or microservices.
- Later data/ML/AI tasks fit without beginning Phases 9–11.

No remaining issue invalidates owner review. Acceptance is still pending.

## Validation

If accepted, each implementation segment must validate in proportion to risk:

- unchanged locked Python quality, strict mypy, and the 95.00% combined
  coverage gate;
- real PostgreSQL migration, repository, rollback, and restart evidence;
- container non-root, secret, architecture, SBOM, and vulnerability checks;
- Terraform format, validate, plan, policy/security checks, and drift review;
- IAM trust/policy review with no long-lived GitHub AWS keys;
- database non-public network assertions;
- Cognito/JWKS rotation, outage, timeout, issuer, audience, scope, and cache
  tests under ADR-0006;
- exact CORS and browser token-handling tests;
- deployed `/health`, `/ready`, authenticated API, decision, audit, persistence,
  log-correlation, rollback, backup/restore, and cost smoke evidence;
- documentation and repository-governance checks.

## Reconsideration triggers

Revisit this decision if:

- the environment costs materially more than the stated range;
- ALB or public IPv4 cost outweighs its learning/operational value;
- a safe App Runner egress/migration design becomes materially simpler;
- sustained traffic, concurrency, availability, or compliance needs require
  multiple tasks, Multi-AZ database, RDS Proxy, private tasks, or stronger
  network controls;
- Cognito cannot produce a stable subject and safely mapped authorization
  claims under ADR-0006;
- a browser session requirement justifies a backend-for-frontend;
- frontend SEO or server rendering becomes a real product requirement;
- data/ML workloads need a separately governed execution plane;
- a second environment or production-readiness review begins.

## References

Repository:

- [OpsMind roadmap](../../../ROADMAP.md)
- [Current status](../../09-status/current-status.md)
- [Phase 7 review](../../12-phase-reviews/phase-7-review.md)
- [ADR-0003: Backend application structure](0003-select-backend-application-structure.md)
- [ADR-0005: PostgreSQL persistence](0005-use-sqlalchemy-and-alembic-for-postgresql-persistence.md)
- [ADR-0006: Trusted principal and authorization](0006-establish-trusted-principal-and-authorization-boundary.md)

AWS architecture, security, and operations:

- [AWS App Runner VPC egress](https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html)
- [ECS Fargate task networking](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html)
- [ECS standalone tasks](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/standalone-tasks.html)
- [ECS deployment circuit breaker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html)
- [ALB target health checks](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html)
- [ECS logs to CloudWatch](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html)
- [CloudFront Origin Access Control for S3](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [RDS in a VPC](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html)
- [RDS automated backups and PITR](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [Aurora Serverless v2 behavior](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.how-it-works.html)
- [ECS Secrets Manager injection](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html)
- [SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS IAM OIDC federation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_oidc.html)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect)
- [Cognito security and PKCE](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-security-best-practices.html)
- [Cognito JWKS endpoints](https://docs.aws.amazon.com/cognito/latest/developerguide/federation-endpoints.html)
- [Cognito JWT verification and rotation](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html)
- [ACM pricing](https://aws.amazon.com/certificate-manager/pricing/)

Official pricing evidence:

- [AWS Fargate pricing](https://aws.amazon.com/fargate/pricing/)
- [AWS ECS public price list, us-east-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/us-east-1/index.json)
- [Elastic Load Balancing pricing](https://aws.amazon.com/elasticloadbalancing/pricing/)
- [VPC, NAT, and public IPv4 pricing](https://aws.amazon.com/vpc/pricing/)
- [App Runner pricing](https://aws.amazon.com/apprunner/pricing/)
- [RDS PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/)
- [AWS RDS public price list, us-east-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/us-east-1/index.json)
- [Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [API Gateway pricing](https://aws.amazon.com/api-gateway/pricing/)
- [ECR pricing](https://aws.amazon.com/ecr/pricing/)
- [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/)
- [Route 53 pricing](https://aws.amazon.com/route53/pricing/)
- [CloudFront pricing](https://aws.amazon.com/cloudfront/pricing/)
- [Amplify Hosting pricing](https://aws.amazon.com/amplify/pricing/)
- [Cognito pricing](https://aws.amazon.com/cognito/pricing/)

Frontend and infrastructure as code:

- [React application guidance](https://react.dev/learn/creating-a-react-app)
- [Next.js static export](https://nextjs.org/docs/app/guides/static-exports)
- [Terraform S3 backend and native locking](https://developer.hashicorp.com/terraform/language/backend/s3)
- [AWS CDK synthesis](https://docs.aws.amazon.com/cdk/v2/guide/ref-cli-cmd-synth.html)
- [AWS CloudFormation](https://docs.aws.amazon.com/cloudformation/)
