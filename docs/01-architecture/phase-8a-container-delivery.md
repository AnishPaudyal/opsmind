# Phase 8A Container Delivery Foundation

## Scope and authority

Issue #68 implements only the Phase 8A container boundary authorized by
[ADR-0007](decisions/0007-select-phase-8-zero-cost-cloud-deployment-and-product-delivery-architecture.md).
It packages the existing FastAPI application for local and CI review. It does
not publish an image, deploy a service, create cloud resources, or begin Phase
8B–8E.

## Image contract

The root `Dockerfile` uses digest-pinned, multi-architecture references for the
official Python 3.13 slim image and the project-pinned `uv` 0.11.28 image. A
builder stage performs `uv sync --locked --no-dev --no-editable`; only the
resulting virtual environment, Alembic configuration, and migration tree enter
the runtime stage.

The runtime contract is:

- installed OpsMind package rather than a source-tree or host-path dependency;
- production dependencies only; no tests, dev tools, compiler, `uv`, source
  tree, local virtual environment, VCS metadata, or local configuration;
- numeric user/group `10001:10001`, `/app` working directory, and port `8000`
  by default;
- one Uvicorn worker with no reload or nested process manager;
- shell expansion only for `${PORT:-8000}`, followed by `exec` so Uvicorn is
  PID 1 and receives `SIGTERM` directly;
- Docker `HEALTHCHECK` against unversioned `/health`; dependency readiness stays
  on unversioned `/ready`;
- OCI source, version, description, title, and full Git-revision labels;
- no startup migration, schema creation, data persistence, or bundled secret.

The image remains compatible with a platform-supplied `PORT` without a rebuild.
Its filesystem may be run read-only with a small disposable `/tmp` tmpfs. All
durable state remains in the selected PostgreSQL service.

## Build and inspect

Use the full reviewed Git identity. Phase 8A validates `linux/amd64` explicitly,
including through emulation on Apple Silicon:

```bash
revision="$(git rev-parse HEAD)"
docker build --pull --platform linux/amd64 \
  --build-arg "VCS_REF=${revision}" \
  --tag opsmind-api:phase8a .
docker image inspect opsmind-api:phase8a
docker history --no-trunc opsmind-api:phase8a
```

`VCS_REF` is non-secret provenance metadata. Do not pass database URLs, signing
material, tokens, or any other secret as a build argument.

## Runtime configuration

The image preserves the existing `OPSMIND_` settings contract. Supply runtime
values through the process environment or a later governed secret manager.
Never bake them into the image or command history. Relevant values include:

- `OPSMIND_ENVIRONMENT`;
- `OPSMIND_PERSISTENCE_BACKEND`;
- `OPSMIND_DATABASE_URL` when PostgreSQL is selected;
- `OPSMIND_AUTH_ISSUER`, `OPSMIND_AUTH_AUDIENCE`, and
  `OPSMIND_AUTH_PUBLIC_KEY` together for signed bearer authentication;
- `OPSMIND_AUTH_ALGORITHM=RS256`;
- `PORT`, defaulting to `8000` at the container boundary.

Unconfigured authentication remains fail-closed for every business route.
`/health`, `/ready`, and API-description endpoints retain their accepted public
behavior.

## Database migration boundary

Application startup never migrates. Run Alembic as a separate, controlled job
using the same reviewed image and runtime database URL before starting or
promoting an application instance:

```bash
docker run --rm \
  --env OPSMIND_DATABASE_URL \
  opsmind-api:phase8a \
  alembic upgrade head
```

An application pointed at reachable but unmigrated PostgreSQL starts and keeps
`/health` at `200`, while `/ready` returns the bounded `503` response. After an
external `alembic upgrade head`, `/ready` returns `200` at the supported
revision `0006_workflow_persistence`.

## Disposable validation

The validation harness uses uniquely named containers and a dedicated Docker
network. It does not use the normal `compose.postgresql.yml` project or its
named volume:

```bash
python3 scripts/validate_container.py --image opsmind-api:phase8a
```

It proves:

- `linux/amd64` image metadata, full revision label, bounded contents, installed
  package, and absence of development tools;
- numeric non-root Uvicorn PID 1 with a read-only root filesystem, dropped
  capabilities, `no-new-privileges`, and graceful `SIGTERM` shutdown;
- exact memory `/health` and `/ready` behavior;
- PostgreSQL 17 startup, unmigrated `503`, absence of implicit schema creation,
  separate Alembic migration, and migrated `200` readiness;
- fail-closed unauthenticated `401` and a short-lived synthetic authenticated
  business read;
- absence of secret/configuration markers from image history;
- final compressed image size as reported by Docker.

Build a second tag from the same tree and run `--mode memory` to verify
functional repeatability without asserting byte-identical digests. Image bytes
may legitimately differ because upstream image metadata and build tooling can
encode timestamps; the locked application dependency graph and observed
runtime behavior are the governed reproducibility boundary.

If Docker Scout is available, record its version and vulnerability-database
timestamp and scan the locally built image. A scan is evidence at one point in
time, not a claim that the image will remain vulnerability-free.

The 2026-08-10 local review found Docker Scout 1.18.3 installed, but Scout
required a Docker ID login and no credential workflow was introduced. The
fallback scan used digest-pinned Trivy 0.72.0 in a disposable container. Its
database was updated at `2026-08-10T18:43:54Z` and downloaded at
`2026-08-10T20:02:30Z`; it reported zero fixed high or critical findings for
the Debian 13.6 and Python package surfaces. The cache volume was removed after
capturing the evidence.

## Compose and CI decisions

`compose.postgresql.yml` remains the single PostgreSQL developer-service
definition. Adding an API service there would mix a persistent normal developer
resource with a destructive smoke lifecycle, so Phase 8A deliberately leaves it
unchanged.

The `Container quality` workflow builds `linux/amd64`, runs the full disposable
contract, runs digest-pinned Trivy against fixed high/critical findings, builds
a second tag, and runs the memory equivalence check. It has read-only repository
permission and does not log into a registry, publish an image, deploy, migrate
any shared database, or use cloud credentials.

## Limitations and deferred work

Phase 8A is container-delivery evidence only. It does not establish public
availability, HTTPS, production data protection, high availability, backup or
restore, external monitoring, identity-provider integration, production secret
management, registry publication, rollback, or production readiness.

Render, Neon, ZITADEL, Cloudflare, Terraform/HCP Terraform, Render Blueprint,
GHCR publication, the frontend, LocalStack, and all Phase 8B–8E implementation
remain gated future work.
