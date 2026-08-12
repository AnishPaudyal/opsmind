# Phase 8B Neon bootstrap and secret-handoff contract

## Purpose

This runbook defines the owner-controlled Neon PostgreSQL bootstrap required by
Phase 8B.

It is an operational companion to:

- `phase-8b-cloud-backend-gate.md`;
- ADR-0007; and
- the protected cloud release workflow.

Neon is a bounded manual-bootstrap exception in Phase 8B. Terraform does not
manage the Neon account, project, branch, database, role, compute, or
credentials.

## Authority boundary

The repository owns:

- the application PostgreSQL connection behavior;
- pooled runtime versus direct migration semantics;
- Alembic schema evolution;
- the protected migration-before-deploy workflow; and
- the secret names consumed by Render and GitHub Actions.

The repository owner owns:

- Neon account bootstrap;
- Free-plan and payment-state verification;
- project creation;
- region and Postgres-version selection;
- database and database-role creation;
- database credential rotation;
- retrieval and handoff of connection URLs; and
- Neon usage review.

Neon must not own application authentication. Phase 8B authentication remains
ZITADEL-backed.

Do not create a Neon API key for this bootstrap. The selected Phase 8B path uses
the Neon Console and standard PostgreSQL connection credentials only.

## Preconditions

Do not create the Neon project until all of the following are true:

1. the bounded Phase 8B implementation remains owner authorized;
2. the PostgreSQL cloud-connection hardening is reviewed;
3. the protected migration workflow exists;
4. the target Render/Neon region decision is reviewed;
5. the Neon dashboard still offers the required Free plan without a payment
   requirement;
6. no paid compute, storage, networking, support, or automatic plan upgrade is
   selected.

If the account or project flow requires payment, a paid trial, an automatic
upgrade, or a resource outside the reviewed Free baseline, stop before creating
the resource.

## Project contract

Create one Neon project with the following reviewed configuration.

| Setting | Required value |
| --- | --- |
| Plan | Free |
| Project name | `opsmind-phase-8b` |
| Cloud provider | AWS |
| Region | AWS US East 2 (Ohio), `aws-us-east-2` |
| PostgreSQL major version | 17 |
| Primary branch | One default primary branch only |
| Read replicas | None |
| Additional branches | None |
| Neon Auth | Not configured |
| Neon Data API | Not required |
| Neon API key | None |
| Paid features | None |

Do not silently accept a different default region. The backend region is
selected deliberately so the Neon database and Render API can use the reviewed
Ohio placement.

Do not create preview, development, staging, or duplicate cloud databases during
Phase 8B. Existing local PostgreSQL remains the development/test environment.

## Database and role contract

Within the primary branch, create:

- one database named `opsmind`;
- one Postgres role named `opsmind_owner`;
- make `opsmind_owner` the owner of the `opsmind` database.

Phase 8B intentionally uses this one bounded database-owner role for both:

- pooled application runtime traffic; and
- direct controlled Alembic migrations.

This is a deliberate simplicity boundary for the first portfolio deployment.
It does not claim that one shared database role is the final production
least-privilege design.

Do not use:

- the Neon account credential as an application credential;
- a Neon API key as a database credential;
- a superuser-style credential unrelated to the `opsmind` database;
- separate unreviewed migration/runtime roles;
- application-managed schema creation.

Alembic remains the only application schema authority.

## Connection-string contract

Open the Neon project **Connect** dialog and select:

- the primary branch;
- database `opsmind`; and
- role `opsmind_owner`.

Capture two connection strings for the same database and role.

### Pooled runtime connection

Enable connection pooling.

The hostname must contain the Neon pooler form:

`-pooler.`

The Neon URL is expected to have the standard PostgreSQL shape:

`postgresql://<role>:<password>@<neon-pooler-host>/opsmind?...`

The exact Neon hostname labels may vary. The reliable pooled-host contract is
that the endpoint ID contains `-pooler` and the hostname remains a Neon
PostgreSQL hostname. Do not reconstruct the host manually.

For OpsMind/SQLAlchemy, convert only the scheme to:

`postgresql+psycopg://`

Preserve the actual Neon hostname, username, password, database name, and
security query parameters.

The final pooled URL belongs only in the Render secret environment variable:

`OPSMIND_DATABASE_URL`

Do not store it in Git, Terraform, HCP Terraform, GitHub repository variables,
documentation, screenshots, issues, or chat.

### Direct migration connection

Disable connection pooling for the same branch, database, and role.

The direct hostname must not contain:

`-pooler.`

The Neon URL is expected to have the standard PostgreSQL shape:

`postgresql://<role>:<password>@<neon-direct-host>/opsmind?...`

The exact Neon hostname labels may vary. The reliable direct-host contract is
that the endpoint does not contain `-pooler` and remains a Neon PostgreSQL
hostname. Do not reconstruct the host manually.

For OpsMind/SQLAlchemy, convert only the scheme to:

`postgresql+psycopg://`

Preserve the actual Neon hostname, username, password, database name, and
security query parameters.

The final direct URL belongs only in the protected GitHub `phase-8b`
environment secret:

`OPSMIND_MIGRATION_DATABASE_URL`

Do not store the direct URL in Render.

## Required transport behavior

Both URLs must retain Neon's TLS requirement.

Do not weaken a generated Neon connection string by removing its TLS/security
query parameters.

OpsMind additionally enforces a bounded PostgreSQL connect timeout.

The runtime engine uses connection liveness checking so stale pooled
connections can be discarded after a Neon scale-to-zero wake.

The Alembic migration engine uses a direct connection and `NullPool`.

Do not run schema migrations over the pooled runtime connection.

## Secret-handoff matrix

| Value | Consumer | Storage |
| --- | --- | --- |
| Pooled `opsmind_owner` URL | Render API runtime | Render secret `OPSMIND_DATABASE_URL` |
| Direct `opsmind_owner` URL | Protected migration job | GitHub `phase-8b` environment secret `OPSMIND_MIGRATION_DATABASE_URL` |
| Neon account login | Repository owner only | Password manager / identity provider |
| Neon API key | Not used | Must not be created for Phase 8B |

The two database URLs currently derive from the same bounded role credential.
Rotating the role password therefore invalidates both URLs.

During rotation:

1. generate/reset the Neon role password;
2. retrieve a fresh pooled URL and direct URL;
3. replace both secret values in their correct stores;
4. verify direct migration connectivity;
5. verify runtime connectivity through the controlled deployment;
6. confirm the old credential no longer works.

Never paste either URL into a repository issue, pull request, chat, shell script,
tracked `.env`, Terraform file, workflow file, or documentation.

## Pre-handoff verification

Before storing either secret, verify only non-secret metadata in the Neon
dashboard:

- plan is Free;
- project is `opsmind-phase-8b`;
- PostgreSQL major version is 17;
- region is AWS US East 2 (Ohio);
- database is `opsmind`;
- role is `opsmind_owner`;
- there is one intended primary branch;
- no read replica exists;
- no paid feature is enabled.

Do not record the password or complete URL as evidence.

Safe evidence may record:

- project name;
- project ID if useful;
- region identifier;
- PostgreSQL major version;
- database name;
- role name;
- Free-plan status; and
- whether pooled/direct URL shapes were verified.

## URL-shape verification

When the owner has the two URLs locally, verify their shape without printing
their credential contents.

The runtime URL must:

- use `postgresql+psycopg`;
- target database `opsmind`;
- use role `opsmind_owner`;
- use a TLS-capable Neon PostgreSQL endpoint;
- contain `-pooler` in the hostname.

The migration URL must:

- use `postgresql+psycopg`;
- target database `opsmind`;
- use role `opsmind_owner`;
- use a TLS-capable Neon PostgreSQL endpoint;
- not contain `-pooler` in the hostname.

Both connection URLs are secrets even if only their shape is being validated.

## Migration boundary

Creating the Neon project/database does not create the OpsMind application
schema.

Do not run `create_all`, application startup migration, or manual schema SQL.

The first real schema creation is the protected release migration:

`alembic upgrade head`

executed from the exact reviewed release image against
`OPSMIND_MIGRATION_DATABASE_URL`.

A failed migration must stop the deployment.

After migration, `/ready` must verify both PostgreSQL connectivity and the exact
reviewed Alembic head before the release is declared healthy.

## Cost and usage boundary

Keep the project on the Neon Free plan.

Use one project and one primary branch only for Phase 8B.

Do not enable paid storage, paid compute, paid networking, additional paid
retention, or another plan merely to avoid a Free-tier limit.

If usage reaches a Free limit or Neon changes its plan behavior, stop and review
the Phase 8B cost gate instead of upgrading automatically.

## First live handoff sequence

The Neon portion of the first controlled deployment is:

1. owner creates the reviewed Free PostgreSQL 17 project;
2. owner creates/verifies `opsmind` and `opsmind_owner`;
3. owner retrieves the pooled and direct URLs;
4. pooled URL is stored only in Render as `OPSMIND_DATABASE_URL`;
5. direct URL is stored only in GitHub `phase-8b` as
   `OPSMIND_MIGRATION_DATABASE_URL`;
6. protected release runs Alembic against the direct URL;
7. Render runs the application against the pooled URL;
8. `/ready` proves connectivity plus exact schema revision.

This runbook does not authorize the Render service bootstrap by itself. Render
still requires the separately reviewed Blueprint and immutable GHCR digest.

## Completion evidence

Neon bootstrap is evidenced only when all of the following are true:

- one real Free project exists with the reviewed region and Postgres version;
- the `opsmind` database and bounded role exist;
- pooled and direct URL shapes are verified without leaking credentials;
- the URLs are stored in their correct secret stores;
- the direct migration succeeds;
- the application reaches the database through the pooled URL;
- `/ready` reports the exact reviewed migration revision;
- no paid Neon resource or automatic upgrade is enabled.

Until those conditions are observed, this document defines a bootstrap
procedure, not evidence that Neon has been provisioned.
