# Phase 8B Review — Zero-Cost Cloud Backend Operational Closeout

Status: Accepted
Review date: 2026-08-13
Governed by: Issue #70
Technical result: Passed
Formal decision: Complete — owner accepted
Owner acceptance: Anish Paudyal, 2026-08-13

## Review Scope

This review closes the bounded Phase 8B zero-cost cloud-backend work governed by
accepted [ADR-0007](../01-architecture/decisions/0007-select-phase-8-zero-cost-cloud-deployment-and-product-delivery-architecture.md)
and the [Phase 8B gate](../01-architecture/phase-8b-cloud-backend-gate.md). It
evaluates:

- provider-neutral ZITADEL JWT/JWKS authentication;
- Neon Free PostgreSQL runtime and migration connectivity;
- HCP Terraform state and run control for supported ZITADEL resources;
- public immutable GHCR publication;
- the Render Blueprint and Free image-backed API service;
- the protected migration-before-deploy release and live smoke evidence;
- secret, ownership, cost, and operational boundaries.

It does not review or complete the Phase 8C frontend, Cloudflare Pages, Phase 8D
hardening, Phase 8E LocalStack, the complete Phase 8 gate, or production
readiness.

## Canonical Repository Evidence

| Workstream | Canonical result |
| --- | --- |
| Phase 8B repository foundation | PR #72 squash-merged as `c52dfedc2ce4019b64dd1e0333f28cbef77b8a82` |
| Render Blueprint and validation | PR #75 squash-merged as `ba2b4284e24d3a440e58bce4d6337a9ad008eade` |
| First controlled cloud release | GitHub Actions Cloud release run #1, run ID `31738097577`, succeeded |
| Governing issue | Issue #70 remains open until this closeout merges with `Closes #70` |

Canonical repository `main` is
`ba2b4284e24d3a440e58bce4d6337a9ad008eade`. The first application image was
published before the Blueprint follow-up, so its application revision is
`1f7de97e593182bd79ff767de220532b8301acff`. These identities are intentionally
different: the later canonical repository SHA must not be reported as the
deployed application revision.

## First Controlled Release Evidence

| Evidence | Verified result |
| --- | --- |
| Approved GitHub environment | `phase-8b` |
| Application revision | `1f7de97e593182bd79ff767de220532b8301acff` |
| Public SHA tag | `ghcr.io/anishpaudyal/opsmind:1f7de97e593182bd79ff767de220532b8301acff` |
| Immutable deployed image | `ghcr.io/anishpaudyal/opsmind@sha256:1b3470e14704640e21f2ccf8bc93d779f732ec888950b9a19ddd0478b9f1be5d` |
| Migration | Success |
| Render deploy | `dep-d9v2si8n74is73ctnfig` |
| Health | Success on attempt 1 |
| Readiness | Success on attempt 1 |
| Unauthenticated protected route | 401 |
| Authenticated read-only route | 200 |
| Final revision attestation | Success |

The release used the direct Neon SSL connection for the protected Alembic
migration, selected the exact immutable digest for Render, and then performed
bounded availability and authentication smoke checks. Application startup did
not create or migrate the schema.

## Live Provider Evidence

### Render and GHCR

- Blueprint: `opsmind-phase-8b` (`exs-d9v2h467bikc73e4ruog`)
- Blueprint mode: manual synchronization
- Blueprint commit: `ba2b4284e24d3a440e58bce4d6337a9ad008eade`
- Service: `opsmind-api` (`srv-d9v2kdid0e5s73egn4ug`)
- Public URL: `https://opsmind-api-ru63.onrender.com`
- Shape: exactly one Free Ohio image-backed web service
- Health path: `/health`
- Live health document: service `opsmind-api`, environment `production`, status
  `ok`
- Registry: public GHCR package, allowing anonymous Render pull without a
  registry credential

The Blueprint controls stable service shape. It does not contain a database,
disk, worker, cron service, migration hook, registry credential, or secret
value.

### Neon

- Plan: Free
- Cloud and region: AWS US East 2 / Ohio
- PostgreSQL: 17
- Runtime connection: pooled SSL
- Migration connection: separate direct SSL
- Schema creation: protected Alembic migration
- Startup migration: absent

The owner-controlled Neon account, project, database, role, and connection
bootstrap remain a documented manual boundary. No database credential is
recorded in this review.

### ZITADEL and HCP Terraform

- ZITADEL contains the OpsMind project, three exact application roles, public
  User Agent SPA metadata, and the bounded `opsmind-release-smoke` identity.
- The exact roles remain `opsmind.business.read`, `opsmind.business.write`, and
  `opsmind.recommendation.decide`.
- The release-smoke identity retains only `opsmind.business.read`.
- HCP Terraform owns the supported ZITADEL Terraform state and run history.
- The owner-bootstrap identity and provider credential remain outside Terraform
  ownership.
- Terraform did not create or store the release-smoke private key.

The authenticated 200 smoke proves the live JWT/JWKS and read-role path for the
bounded smoke identity. It does not establish application-managed identity,
tenant administration, or enterprise identity governance.

## Completion-Criteria Assessment

| Criterion | Result | Evidence |
| --- | --- | --- |
| Real Free PostgreSQL with separated pooled/direct TLS paths | Passed | Neon PostgreSQL 17 runtime and protected migration connectivity |
| Controlled migration reaches the supported schema | Passed | Cloud release migration success and first-attempt readiness success |
| Real ZITADEL JWT resolves through bounded JWKS | Passed | Authenticated read-only smoke returned 200 |
| Exact three-role authorization model | Passed | Terraform-managed role inventory and regression coverage |
| Public immutable image publication | Passed | Full-SHA tag and retained SHA-256 digest |
| One Render Free image service runs the exact digest | Passed | Blueprint/service inventory and deploy ID |
| Health and readiness satisfy the bounded contract | Passed | Both succeeded on attempt 1 |
| Anonymous protected route fails closed | Passed | 401 smoke result |
| Least-privilege authenticated read succeeds | Passed | 200 smoke result |
| Migration precedes deployment | Passed | Protected workflow ordering and migration result |
| Release identity is attested | Passed | Final application-revision attestation succeeded |
| Secrets remain outside repository evidence | Passed | Only names, public identifiers, and redacted authority boundaries are documented |
| Phase 8C and production claims remain excluded | Passed | No frontend, Cloudflare deployment, or production-readiness claim |

## Architecture Ownership

| Resource or action | Authority |
| --- | --- |
| Supported ZITADEL project, roles, application, and smoke-identity metadata | Terraform through HCP Terraform |
| ZITADEL instance, organization, provider bootstrap identity, and credentials | Owner-controlled bootstrap |
| Neon account, project, database, role, and connection bootstrap | Owner/manual boundary |
| PostgreSQL schema and revision | Alembic |
| Render stable service shape | Root `render.yaml` and Render Blueprint |
| Render secret values and deploy hook | Owner through Render dashboard |
| Image build, scan, tag, and digest publication | GitHub Actions and GHCR |
| Migration, exact-digest deploy, health/readiness, and authentication smoke | Protected GitHub Actions cloud release |
| Future browser application and Cloudflare delivery | Phase 8C, not started |

No second authority is claimed for any row. Terraform does not own Render or
Neon, the Blueprint does not migrate the database, and application startup does
not own schema changes.

## Security and Secret Closeout

After the authenticated smoke succeeded, the owner deleted the downloaded
local ZITADEL smoke-key JSON artifact and cleared the clipboard. The cloud
ZITADEL smoke credential and corresponding protected GitHub environment secret
remain intentionally active for future controlled releases.

No database URL, database password, deploy-hook URL, private key, JWT profile
JSON, access token, GitHub secret value, or HCP sensitive value is present in
this review or the repository closeout.

## Validation Evidence

The repository-controlled Phase 8B foundation passed Container quality, Python
quality, Terraform quality, and Repository checks on canonical `main`. PR #75
also passed those four hosted checks plus the HCP Terraform commit status. The
first controlled Cloud release succeeded end to end.

The documentation closeout reran the locked repository validation contract:

- Render Blueprint official-schema validation: Passed;
- required-file, empty-Markdown, link, and secret-pattern checks: Passed;
- `uv lock --check`: Passed;
- Ruff formatting and linting: Passed;
- strict mypy: Passed;
- complete PostgreSQL-backed pytest and 95.00% combined coverage gate: Passed;
- `git diff --check`: Passed.

## Residual Limitations

Phase 8B completion does not establish:

- production readiness or a production security approval;
- high availability, disaster recovery, backup objectives, or a production
  SLA;
- production monitoring, alerting, on-call, or incident response;
- production-scale load, concurrency, endurance, or capacity validation;
- multi-tenant identity, application-managed users/sessions, or enterprise
  identity governance;
- frontend implementation or Cloudflare Pages deployment;
- Phase 8C, Phase 8D, Phase 8E, or complete Phase 8 completion;
- forecast accuracy on governed real-world data or any advanced ML capability;
- purchase-order execution or external ordering;
- AWS production deployment or completed LocalStack learning exercises;
- enterprise security, privacy, regulatory, or compliance certification.

Render and Neon Free services may sleep, have bounded resources and service
limits, and provide no production availability promise. Free-tier terms can
change.
The inherited Debian vulnerability disclosure remains active: 19 High and 4
Critical findings were present at the reviewed scan, none was fixable, and no
Python/application High or Critical finding was reported. Future releases must
rescan and remediate when upstream fixes become available.

The retained immutable digest provides a rollback identity, but this first live
closeout does not claim a destructive failure exercise, production recovery
objective, or HA/DR validation. Those operational concerns remain Phase 8D or
production-readiness work.

## Owner Decision

**Complete — accepted**

Owner: Anish Paudyal
Date: 2026-08-13
Decision: Complete — accepted

Accepted statement:

> “I accept the Phase 8B review, including the documented security,
> operational, free-tier, and production-readiness limitations, and approve the
> Complete decision under Issue #70.”

The owner accepts the documented Phase 8B security, operational, free-tier,
and production-readiness limitations.

The repository implementation, provider bootstrap, protected cloud release,
live service evidence, security cleanup, and durable limitations satisfy the
bounded Issue #70 completion criteria. Phase 8B is Complete, and merge of this
pull request may close Issue #70.

Phase 8 overall remains Current. This decision does not authorize Phase 8C or
any additional cloud mutation. Phase 8C remains not started and requires its
own owner-authorized issue and gate.
