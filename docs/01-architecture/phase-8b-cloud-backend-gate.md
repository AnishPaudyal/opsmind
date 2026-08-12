# Phase 8B Zero-Cost Cloud Backend Implementation Gate

## Gate status

Phase 8A completed through PR #69 as canonical commit
`631b8a2d1c9696b374f2b96b0295190bbca4a3bf`. Its canonical tree exactly
matches the reviewed feature tree, Issue #68 is closed, and Repository checks,
Python quality, and Container quality all passed on `main`.

[Issue #70](https://github.com/AnishPaudyal/opsmind/issues/70) is the bounded
Phase 8B implementation workstream governed by accepted
[ADR-0007](decisions/0007-select-phase-8-zero-cost-cloud-deployment-and-product-delivery-architecture.md).
The repository owner subsequently authorized the bounded Phase 8B
implementation. Repository implementation is now in progress under that
authority.

This document remains the governing scope, ownership, cost, secret, and stop
contract. Authorization does not extend to Phase 8C frontend/Cloudflare work,
Phase 8D hardening, Phase 8E LocalStack, production-readiness claims, or later
phases.

## Current authorization boundary

The authorized Phase 8B repository work may implement the bounded package
defined below. Owner-controlled account signup, credential creation, HCP
Terraform apply approval, Render authorization, protected-environment approval,
GHCR visibility changes, and live deployment remain explicit human actions
performed only at their documented point in the bootstrap sequence.

The current state is:

`IMPLEMENTATION AUTHORIZED — REPOSITORY WORK IN PROGRESS — LIVE CLOUD BOOTSTRAP NOT STARTED`

## Bounded implementation scope after approval

Phase 8B may implement:

- one Neon Free PostgreSQL project with pooled TLS application traffic and a
  direct TLS Alembic path;
- one ZITADEL Free project, a public User Agent application, the exact three
  OpsMind project roles, and a dedicated least-privilege smoke identity;
- provider-neutral JWKS-backed RS256 verification behind the existing
  `Authenticator` and `TrustedPrincipal` boundaries;
- immutable `linux/amd64` image publication to public GHCR by full Git SHA and
  digest;
- one Render Blueprint-controlled Free image web service, explicit immutable
  deployment, cold-start-aware health/readiness polling, and authenticated
  smoke validation;
- an owner-approved HCP Terraform Free organization/workspace for remote state,
  reviewed runs, and only provider-supported ZITADEL backend resources;
- controlled migration-before-deploy automation, tests, operations evidence,
  cost guards, and minimum durable documentation.

It may not implement or create a frontend, Cloudflare resource, Render or Neon
paid service, Render Postgres, application-managed identity, tenant model,
automatic startup migration, automatic downgrade, mutable `latest` deployment,
LocalStack/AWS resource, Phase 8C–8E capability, production-readiness claim,
Phase 9 data work, MLOps, LLM, RAG, or LangGraph capability.

## Ordered human and account bootstrap inventory

Issue #70 has owner authorization for the bounded Phase 8B implementation.
Perform these owner-controlled steps only in the documented order and only
after the corresponding repository prerequisite exists. The order prevents
credentials or resources from being created before their consumer and
authority are known.

1. **GitHub owner controls**
   - Confirm the repository remains public and Actions is enabled.
   - Create a protected `phase-8b` deployment environment restricted to
     `main`; configure the repository owner as required reviewer and disallow
     bypass if the available plan permits it.
   - After the first workflow publication creates the package, explicitly make
     the GHCR package public and confirm it remains linked to this repository.
   - No PAT is expected: the repository `GITHUB_TOKEN` with `contents: read`
     and `packages: write` is sufficient for publication.
2. **Neon owner bootstrap**
   - Create or sign in to a Neon account and complete email/identity checks.
     The current Free plan advertises no credit card requirement.
   - Manually create one Free PostgreSQL 17 project in the region selected for
     the backend. Manual creation is the accepted Neon bootstrap exception;
     no Terraform provider or API key is required for this slice.
   - Create the bounded OpsMind database/role configuration and capture two
     SQLAlchemy/Psycopg URLs: pooled runtime and direct migration. Codex cannot
     infer or retrieve these credentials without owner-authorized console/API
     access.
   - Follow `phase-8b-neon-bootstrap.md` for the exact project, region,
     database/role, pooled/direct URL, and secret-handoff contract.
3. **ZITADEL owner bootstrap**
   - Create or sign in to one ZITADEL Cloud Free instance and complete email,
     CAPTCHA, and administrator bootstrap. The current Free plan is `$0` with
     one instance and 100 daily active users; the official pricing page does
     not establish a universal payment-card requirement, so the owner must
     confirm the signup screen before continuing.
   - Manually create the bootstrap organization boundary and a narrowly
     authorized Terraform service account/key. Terraform will manage the
     Phase 8B project, roles, and applications after bootstrap.
   - Approve placeholder local and eventual Phase 8C redirect/logout origins.
     Phase 8B must not create the frontend or Cloudflare resources.
4. **HCP Terraform owner bootstrap**
   - Create or sign in to a free HCP Terraform account, verify email, and
     create the organization.
   - Authorize the HCP Terraform GitHub App for this repository only.
   - Create the backend workspace manually and connect its working directory
     after Terraform files are reviewed. This small control-plane exception
     avoids circularly managing the workspace that stores its own state.
   - Store the ZITADEL provider credential as a sensitive workspace variable.
     A separate HCP API token is not required for the selected VCS-driven
     workflow.
   - Follow `phase-8b-hcp-terraform-bootstrap.md` for the exact workspace,
     variable, speculative-plan, and manual-apply contract.
5. **Render owner bootstrap**
   - Create or sign in to a Render Hobby workspace and connect GitHub only to
     this repository.
   - Confirm no payment method is attached. Current Render behavior suspends
     services instead of charging when unbilled usage limits are exceeded.
   - After the reviewed Blueprint exists, authorize its initial synchronization
     to create the one Free image service. Render will then produce the secret
     deploy-hook URL and public service URL.
   - Set Render secret environment values through its dashboard; Codex cannot
     obtain them automatically without separately authorized account access.
6. **Secret handoff and first controlled release**
   - Place each secret only in the storage named below; never paste values into
     issues, pull requests, chat, logs, screenshots, Terraform source, or
     Blueprint YAML.
   - Verify all dashboards still show Free/Hobby and zero paid resources before
     allowing the protected release job to run.

## Secret inventory

| Secret | Producer | Consumer and storage | GitHub | Render | Terraform state | Rotation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Neon pooled runtime URL | Neon | Render secret environment variable `OPSMIND_DATABASE_URL` | No | Yes | Never | Rotate the database-role password, replace the Render secret, deploy, then revoke the old credential. |
| Neon direct migration URL | Neon | GitHub `phase-8b` environment secret `OPSMIND_MIGRATION_DATABASE_URL` | Yes | No | Never | Rotate the migration credential, replace the environment secret, validate migration access, then revoke the old credential. |
| Render deploy-hook URL | Render | GitHub `phase-8b` environment secret `RENDER_DEPLOY_HOOK_URL` | Yes | Render endpoint | Never | Regenerate the hook in Render and replace the GitHub secret before disabling the old hook. |
| ZITADEL Terraform service-account key | ZITADEL bootstrap | Sensitive HCP Terraform workspace variable | No | No | Must not be written by a resource or output; verify plans/state | Create a replacement key, update the sensitive variable, verify a plan, then revoke the old key. |
| ZITADEL smoke service-account key | ZITADEL/Terraform | GitHub `phase-8b` environment secret used only to request a short-lived read-only smoke token | Yes | No | The generated private key must not enter state; use an owner-generated/imported credential | Replace the key and GitHub secret, verify token issuance, then revoke the old key. |

The ephemeral `GITHUB_TOKEN` is generated by GitHub and receives only
`contents: read` and `packages: write`; it is not a stored project secret. A
public GHCR package requires no Render registry credential. The public SPA has
no client secret. HCP Terraform uses the VCS integration, so no HCP token is
stored in GitHub. The Render API is not required when the bounded secret deploy
hook is used.

Public configuration includes the ZITADEL issuer, JWKS URL, project ID/audience,
role-claim name, public SPA client ID, approved redirect origins, Render service
URL, GitHub repository, and GHCR image path. Public does not mean mutable:
issuer, JWKS host, audience, and role-claim configuration remain reviewed trust
inputs.

## ZITADEL implementation contract

The future SPA is a ZITADEL **User Agent/public client** using Authorization
Code with PKCE S256. It has no browser client secret. Implicit flow is disabled.
Phase 8B may configure placeholder localhost and future reviewed redirect/logout
URIs but does not implement the SPA.

The access-token contract is:

- JWT bearer access tokens only; opaque tokens fail closed;
- RS256 only, with a required trusted `kid`;
- exact configured issuer and exact OpsMind project audience;
- required `exp`, `iat`, `jti`, and bounded stable string `sub`; requiring
  `jti` follows ZITADEL's published claims matrix and distinguishes JWT access
  tokens from ID tokens, which must be rejected as API bearer credentials;
- exact project-specific role claim
  `urn:zitadel:iam:org:project:{project_id}:roles`;
- no user-profile, organization-domain, email, or other token fields enter the
  `TrustedPrincipal` boundary.

Create exactly these project roles with no hierarchy:

| ZITADEL project role | OpsMind permission |
| --- | --- |
| `opsmind.business.read` | `business:read` |
| `opsmind.business.write` | `business:write` |
| `opsmind.recommendation.decide` | `recommendation:decide` |

The adapter reads only exact role-name keys from the project-specific claim.
Missing or malformed claims grant no permissions; unknown roles grant nothing.
No role implies another role. A valid but unauthorized principal receives the
existing generic 403, while any credential-validation failure retains the
generic 401.

## JWKS adaptation design

ADR-0006 remains authoritative:

```text
static configured RSA public key ─┐
                                  ├─ provider adapter ─ Authenticator
trusted configured ZITADEL JWKS ──┘                      ↓
                                                   TrustedPrincipal
```

The static public-key path remains supported for deterministic local tests and
provider-neutral deployments. JWKS mode adds reviewed settings for the exact
HTTPS JWKS URL and ZITADEL project ID and makes it mutually exclusive with the
static key. The URL is configuration-controlled, must be HTTPS, and must match
the trusted issuer host; token claims and headers can never select a host or
discovery endpoint.

PyJWT 2.13.0 already provides `PyJWKClient`, a five-minute JWK-set cache,
configurable timeout, `kid` lookup, and exactly one forced refresh after a
cache miss. No new HTTP dependency is justified. The implementation should
wrap that facility to enforce:

- a five-second network timeout;
- a 300-second JWK-set lifetime and bounded response size;
- no indefinite per-key cache;
- one network refresh after an unknown `kid`, then fail closed;
- RS256 and minimum RSA-key-strength checks after resolution;
- generic authentication failure without token, provider, key, URL, claim, or
  exception leakage.

The current synchronous FastAPI authentication dependency already executes
outside the event loop. Tests use an injected fake resolver/transport and
fixed JWKS documents; ordinary unit tests never call ZITADEL. Tests must cover
cache hit/expiry, rotation, one refresh, timeout, malformed documents,
untrusted URLs, unknown `kid`, wrong algorithm, undersized keys, ID and opaque
tokens, wrong issuer/audience, and exact role mapping.

## Neon connection contract

- Application traffic uses the Neon **pooled** hostname and
  `postgresql+psycopg` URL with `sslmode=require`, channel binding when supplied
  by Neon, and `connect_timeout=10`.
- Alembic uses the **direct** hostname with the same TLS requirements and
  `connect_timeout=10`. Neon explicitly recommends direct connections for ORM
  migrations.
- The existing application engine already uses `pool_pre_ping=True`; retain it
  to discard stale connections after Neon scale-to-zero wake.
- The existing Alembic engine uses `NullPool`; retain it for the one controlled
  migration job.
- Do not add speculative pool recycling. Measure real wake/reconnect behavior
  first.
- Render receives only the pooled URL. The protected migration job receives
  only the direct URL and maps it to `OPSMIND_DATABASE_URL` for the existing
  Alembic command.

Neon Free currently scales idle compute to zero after five minutes. `/health`
must remain independent and return 200 while `/ready` performs its existing
bounded connectivity and exact Alembic-head check. Database wake or failure
therefore produces bounded 503 readiness rather than a false liveness failure.

## Render runtime and cold-start contract

The Render service is an image-backed public web service using `runtime: image`,
`plan: free`, the Phase 8A `linux/amd64` image, the image's Uvicorn command, and
the platform `PORT`. Render terminates public TLS. `/health` is the service
health path; `/ready` remains the post-deploy dependency gate.

Render Free currently spins a service down after 15 idle minutes and documents
about one minute to wake. The release smoke contract is deliberately wider:

1. Trigger the exact immutable image through the secret deploy hook.
2. Poll `/health` every five seconds for at most 180 seconds (36 attempts).
3. After health succeeds, poll `/ready` every five seconds for at most another
   180 seconds.
4. Perform one unauthenticated business GET expecting 401 and one authenticated
   read-only GET with a 30-second request timeout.
5. Fail the release on a terminal Render deploy failure, exhausted polling
   budget, wrong response, or request-ID/log leakage; never hide a failure with
   an unbounded retry.

The browser-facing “backend waking” experience belongs to Phase 8C. Phase 8B
only records the backend timings and preserves a contract that Phase 8C can
present accurately.

## Migration and release ordering

```text
main and all quality checks green
→ build linux/amd64 once
→ comprehensive vulnerability report and fixable High/Critical gate
→ publish full-Git-SHA tag to GHCR and capture digest
→ owner-approved GitHub deployment environment
→ run `alembic upgrade head` against the direct Neon TLS URL
→ trigger Render with the exact GHCR digest
→ `/health`
→ `/ready`
→ unauthenticated 401
→ authenticated read-only smoke
→ record deployed SHA/digest and evidence
```

Migration intentionally precedes the new service. Every Phase 8B and future
schema change must therefore be expand/contract compatible with the currently
running application. Do not drop or repurpose data required by the old image
before the new image is verified. There is no automatic startup migration and
no automatic down-migration. A migration failure stops deployment before the
Render hook is called.

## GHCR package and release identity

- Build once for `linux/amd64`, scan that image, and push it with the full Git
  SHA tag.
- Capture and deploy the immutable registry digest; never depend on `latest`.
- Use workflow permissions `contents: read` and `packages: write` only for the
  publication job. No PAT or registry password is planned.
- Publish from this repository so GHCR links the package automatically, then
  have the owner make the first package public. Public GHCR pulls are anonymous,
  so Render receives no registry credential.
- Retain the deployed digest and at least the two prior known-good digests.
  Never delete an active or rollback image. Render re-pulls images and cannot
  roll back if the registry digest has been removed.
- Record full SHA, manifest digest, scan evidence, migration result, Render
  deployment identity, and smoke result. A tag is a lookup aid; the digest is
  the release identity.

GitHub currently states that public packages and Container registry storage
and bandwidth are free, and that standard hosted runners are free for public
repositories. Reverify these policies on every implementation/release review.

## Render Blueprint and release ownership

The future `render.yaml` owns only stable service configuration:

- service name and `type: web`;
- `runtime: image` and a public GHCR repository/image reference;
- `plan: free` and one reviewed region;
- `/health` health-check path;
- environment key names and `sync: false` secret placeholders;
- the default Docker image command and runtime `PORT` behavior.

Image-backed services do not support Git auto-deploy. The Blueprint must not run
Alembic as `preDeployCommand`; migration belongs to the protected release job.
GitHub Actions alone selects each release digest and calls the Render deploy
hook with `imgURL` set to that exact identity. Manual “latest” deployment is
not an authority. The Blueprint may bootstrap the service with one reviewed
digest, while subsequent release identity and rollback are recorded deployment
events.

## Resource ownership matrix

| Resource or configuration | Terraform | Render Blueprint | Alembic | GitHub Actions | Manual bootstrap |
| --- | --- | --- | --- | --- | --- |
| ZITADEL Cloud instance and bootstrap organization/admin | No | No | No | No | Owner |
| ZITADEL Terraform service account/key | No; consumed as sensitive provider input | No | No | No | Owner |
| ZITADEL OpsMind project, three roles, public SPA app, smoke identity metadata | Authoritative, subject to provider support verified during implementation | No | No | Plan only through HCP VCS run | Bootstrap credential/approval only |
| ZITADEL smoke private key | Must not be generated into state | No | No | Consumes GitHub environment secret | Owner-generated key handoff |
| HCP Terraform account, organization, VCS connection, workspace | No self-management | No | No | No HCP token | Owner control-plane bootstrap |
| Terraform state and run history | HCP Terraform authoritative | No | No | No | Owner approves applies |
| Neon project, database, role, compute, pooled/direct URLs | No provider selected for Phase 8B | No | No | Migration consumes direct URL | Owner Neon bootstrap |
| PostgreSQL schema and revision | No | No | Authoritative | Runs reviewed upgrade | No |
| Render account and GitHub connection | No | No | No | No | Owner |
| Render service shape, Free plan, region, health path, env-key declarations | No | Authoritative | No | Blueprint validation only | Initial Blueprint authorization |
| Secret values in Render | No | Placeholder keys only | No | No | Owner/dashboard handoff |
| API image build, scan, full-SHA tag, digest publication | No | No | No | Authoritative | Owner makes first package public |
| Migration, immutable Render deploy, health/readiness/auth smoke | No | No | Schema step only | Authoritative protected release | Owner environment approval |
| Cloudflare/frontend resources | Not Phase 8B | No | No | No | Not started |

Normal operation has one authority per row. Terraform must not manage the
Render service, Neon bootstrap, database schema, or release image. The Blueprint
must not run migrations. GitHub Actions must not invent infrastructure outside
the reviewed authorities.

## Current zero-cost verification

Verified against current official documentation on 2026-08-10:

| Service | Current free behavior | Cost guard and risk |
| --- | --- | --- |
| Neon | Free is `$0`, no credit card required, 100 CU-hours and 0.5 GB per project, scale-to-zero, and 5 GB monthly public transfer | Use one project, monitor storage/compute/transfer, and accept suspension rather than upgrade. Do not enable a paid plan. |
| ZITADEL Cloud | Free is `$0`, one instance, 100 daily active users, one administrator, and 5,000 management API requests | Portfolio traffic must stay below limits. Confirm signup/payment prompts and do not select Pro or a custom domain. |
| Render | Free web service, 750 monthly instance hours, idle spin-down after 15 minutes, approximately one-minute wake, and ephemeral filesystem | Keep the workspace without a payment method so overage suspends services/builds instead of billing. Monitor 5 GB Hobby outbound bandwidth and pipeline limits. No persistent disk or paid instance. |
| HCP Terraform | Free remote state, remote runs, and VCS integration for up to 500 managed resources; one concurrent run | Use one small workspace, owners-only free access, and no paid plan. State can contain sensitive resource data even when UI values are marked sensitive. |
| GitHub Actions/GHCR | Standard hosted runners are free for public repositories; public packages and Container registry storage/bandwidth are currently free | Keep the repository/package public, avoid larger runners and unnecessary artifacts, set zero-spend/fail-closed budgets where available, and recheck policy before release. |

Free services are portfolio evidence, not production SLAs. Limits and pricing
can change. If any signup requires a payment method, any plan would auto-upgrade,
or any expected resource is no longer free, stop before account/resource
creation and return to the owner gate.

## Measurable Phase 8B completion criteria

Phase 8B is complete only when all of the following are evidenced:

- one real Neon Free database exists; pooled runtime and direct migration
  connections require TLS and remain separated by secret storage;
- controlled `alembic upgrade head` succeeds against the direct URL and the
  application reports the exact reviewed revision through `/ready`;
- a real ZITADEL RS256 JWT access token resolves through the trusted JWKS path;
- all three exact project roles map one-to-one to the three OpsMind permissions;
- missing/malformed role claims, unknown roles, ID tokens, opaque tokens,
  invalid signatures, unknown `kid`, timeout, expired tokens, and wrong
  issuer/audience fail closed without secret/provider leakage;
- the reviewed `linux/amd64` image is scanned and published to public GHCR with
  a full-SHA tag and retained digest;
- Render Free runs that exact digest with no registry credential, `/health` and
  `/ready` succeed within the bounded cold-start contract, and logs preserve
  request IDs without credentials or principal data;
- unauthenticated business access returns 401 and the dedicated read-only smoke
  identity completes an authenticated GET;
- migration-before-deploy compatibility, failed-migration stop behavior, and
  rollback to a retained digest are verified;
- all existing Python, PostgreSQL, coverage, governance, container, link,
  secret-pattern, and IaC validation passes;
- current `$0` plan/usage evidence, human bootstrap, secrets, rotations,
  limitations, and exact deployed identity are documented;
- no frontend, Cloudflare, LocalStack/AWS, Phase 8C–8E, later-phase, or
  production-readiness capability is claimed.

## Implementation risks and required owner interaction

| Risk | Mitigation | Owner interaction |
| --- | --- | --- |
| Account signup, email verification, CAPTCHA, regional or payment prompts | Stop on unexpected paid requirement; record exact current plan | Required for every provider account |
| GitHub environment and first-package visibility | Protected `main` environment; public package after first workflow publish | Required |
| Neon pooled/direct URL confusion or credential leakage | Distinct secret names/stores, TLS/query validation, redacted diagnostics | Owner supplies URLs without exposing them in chat/logs |
| Neon scale-to-zero plus Render cold start | Existing `pool_pre_ping`, bounded connect timeout, explicit 180-second polls | Review observed timings |
| ZITADEL bootstrap credential has broad authority | One narrowly scoped service account, HCP sensitive variable, key rotation | Owner creates/rotates bootstrap key |
| JWKS timeout or key rotation | Trusted URL, five-second timeout, bounded cache, one refresh, fail closed | Approve issuer/JWKS/project IDs |
| ID token accepted accidentally | Require JWT access-token-only claims including `jti`; explicit negative tests | Review real token evidence |
| Render GitHub/Blueprint authorization and deploy-hook leakage | Repository-only GitHub grant; protected secret; hook regeneration | Required |
| Migration before deploy breaks current image | Expand/contract migrations; migration failure blocks deploy | Approve protected release |
| GHCR package is private or digest deleted | Owner makes it public; retain deployed plus two rollback digests | Required after first publish and during retention review |
| HCP state exposes provider/resource values | Avoid key-generating resources/outputs; inspect plan/state; least access | Owner approves workspace and applies |
| Free-tier exhaustion or pricing change | No payment method where possible; usage monitoring; suspension over overage | Confirm dashboards before each release |

Codex can implement repository code, deterministic fake-JWKS tests,
Terraform/Blueprint/workflow source, validation, and documentation after
authorization. The owner must perform or explicitly authorize account signup,
email/CAPTCHA flows, GitHub/Render/HCP application connections, service-account
key creation, protected-environment approval, first GHCR visibility change,
secret entry, and any cloud apply/deploy.

## Official sources reviewed

- [Neon pricing](https://neon.com/pricing)
- [Neon connection pooling](https://neon.com/docs/connect/connection-pooling)
- [Neon compute scale-to-zero](https://neon.com/docs/manage/endpoints/)
- [ZITADEL pricing](https://zitadel.com/pricing)
- [ZITADEL application types and token settings](https://zitadel.com/docs/guides/manage/console/applications-overview)
- [ZITADEL token claims](https://zitadel.com/docs/apis/openidoauth/claims)
- [ZITADEL Terraform provider guide](https://zitadel.com/docs/guides/manage/terraform-provider)
- [PyJWT `PyJWKClient`](https://pyjwt.readthedocs.io/en/stable/api.html)
- [Render Free limitations](https://render.com/docs/free)
- [Render prebuilt-image deployment](https://render.com/docs/deploying-an-image)
- [Render Blueprint specification](https://render.com/docs/blueprint-spec)
- [Render deploy hooks](https://render.com/docs/deploy-hooks)
- [HCP Terraform Free features](https://developer.hashicorp.com/terraform/cloud-docs/overview)
- [HCP Terraform GitHub App connection](https://developer.hashicorp.com/terraform/cloud-docs/vcs/github-app)
- [GitHub Container registry permissions](https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages)
- [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages)
- [GitHub-hosted public runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [GitHub deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)

## Current stop boundary

Phase 8B repository implementation now exists under Issue #70, including the
backend trust adaptation, cloud connection hardening, immutable release
workflow source, ZITADEL Terraform source, Terraform quality validation, and
bootstrap documentation.

No live Neon, Render, ZITADEL, or HCP Terraform Phase 8B resource, GHCR package,
Render Blueprint, cloud credential, or deployment is claimed by this
repository state. Do not claim Phase 8B complete until the measurable
completion criteria above are evidenced. Phase 8C–8E and later-phase work
remain outside this authorization.
