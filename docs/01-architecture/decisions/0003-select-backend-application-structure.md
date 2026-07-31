# ADR-0003: Select Backend Application Structure

- Status: Accepted
- Date: 2026-07-31
- Decision owners: Anish Paudyal
- Related issues: #14
- Related pull requests: The pull request implementing issue #14
- Supersedes: None
- Superseded by: None

## Context

OpsMind completed its repository, Python, quality, and continuous-integration
foundations without selecting or creating application code. Phase 2 now needs a
small backend foundation that can support the first product slice while keeping
business logic, persistence, cloud services, authentication, and data systems
outside this decision.

The first application boundary must work with the accepted Python 3.13 and `uv`
toolchain, the accepted Ruff, mypy, pytest, and pytest-cov quality contract, and
the existing Python-quality CI workflow. It must also establish configuration,
application construction, routing, health reporting, packaging, and test
boundaries that future issues can extend without pretending downstream systems
already exist.

## Decision drivers

- Python 3.13 compatibility
- Reproducibility through `uv.lock`
- Native Apple Silicon and GitHub-hosted CI compatibility
- Fast local development and deterministic tests
- Strict typing and clear dependency-injection boundaries
- Explicit environment configuration without repository-local secret files
- OpenAPI support for an API-first product
- A package layout that can be built and installed independently
- Minimal runtime dependencies and operational surface area
- Suitability for future supply-chain, data-science, and ML-backed APIs
- Separation of process health from future dependency readiness
- Low maintenance complexity for the first application milestone

## Considered options

1. **FastAPI with Pydantic Settings and Uvicorn.** This supplies typed API
   contracts, OpenAPI generation, dependency injection, validated environment
   settings, and a small ASGI runtime that fits the accepted Python toolchain.
2. **Flask with separate schema and settings libraries.** Flask is mature and
   flexible, but matching the selected typing, validation, and OpenAPI baseline
   would require more integration choices and dependencies.
3. **Django with Django REST Framework.** This offers a comprehensive web and
   persistence framework, but introduces application, ORM, administration, and
   configuration conventions beyond the bounded backend foundation.
4. **Starlette directly.** This provides the underlying ASGI primitives with a
   smaller framework layer, but would require more manual API validation,
   dependency injection, and schema composition.
5. **Litestar.** This is a capable typed ASGI framework, but FastAPI has the
   stronger fit with the repository's learning goals, expected ecosystem, and
   future data and ML service integration.
6. **A single-module FastAPI application.** This would minimize initial files,
   but it would mix construction, configuration, routes, and public schemas at
   the first durable application boundary.
7. **A package-first `src/opsmind` layout with an application factory.** This
   makes imports and builds independent of the checkout root and lets tests bind
   one explicit settings instance without global mutation.
8. **Deferring application code.** This avoids immediate framework maintenance,
   but Phase 2 cannot begin its API and product work without a reviewed backend
   boundary.

## Decision

- FastAPI is the backend API framework.
- Pydantic Settings owns typed environment-backed configuration.
- Uvicorn is the direct ASGI runtime.
- HTTPX is a development-only dependency used by FastAPI's synchronous
  `TestClient`.
- The project becomes a packaged application using the `uv_build` backend and
  its default `src/opsmind` package discovery.
- The build requirement is bounded to `uv_build>=0.11.28,<0.12`, matching the
  repository's pinned `uv` minor line.
- `src/opsmind/application.py` owns the `create_app` application factory, and
  `src/opsmind/main.py` exposes the module-level ASGI application.
- Settings use the `OPSMIND_` environment prefix and are cached once per
  process, with an explicit typed reset function for tests.
- Supported environments are `local`, `test`, `staging`, and `production`.
- The root router exposes only an unversioned `GET /health` process-health
  endpoint in this issue.
- `/api/v1` is reserved in configuration but remains unrouted until a real
  versioned business capability exists.
- Health responses expose only status, service name, and environment; they do
  not claim database, cloud, or external-service readiness.
- Synchronous pytest tests validate the application factory, settings behavior,
  health HTTP contract, and OpenAPI contract.

## Rationale

FastAPI provides a cohesive typed API surface on top of Starlette and Pydantic
without requiring the broader conventions of a full-stack framework. Pydantic
Settings keeps validation and environment parsing consistent with the API's
data model, while Uvicorn provides the minimal direct runtime needed to run the
ASGI application. Installing each dependency without extras keeps optional
servers, reloaders, cloud integrations, and protocol extensions out of the
baseline.

The package-first `src` layout follows the uv build backend's default discovery
rules and prevents tests from succeeding only because the repository root is on
the import path. An application factory accepts explicit settings for
deterministic construction, while a narrow dependency provider ensures route
handlers observe the same resolved instance. The health endpoint is deliberately
process-only so future readiness checks can be designed with real dependencies
and operational requirements.

## Consequences

### Positive

- The repository has a runnable, typed, documented HTTP application boundary.
- Local imports, distribution builds, and isolated wheel installs share one
  package layout.
- Configuration defaults and overrides are validated and testable.
- OpenAPI documents the first public response contract automatically.
- Runtime dependencies remain small and explicitly separated from test tooling.
- Future routers and versioned endpoints can be added without restructuring the
  application factory.
- Existing CI automatically begins running real mypy and pytest validation.

### Negative

- The repository now owns framework, validation, server, build-backend, and HTTP
  client dependency maintenance.
- Process-global settings caching requires explicit reset discipline in tests
  that exercise default configuration.
- The application factory uses a narrow FastAPI dependency override to bind its
  resolved settings instance.
- The package layout introduces more modules than a single-file prototype.

### Neutral

- ADR-0003 was accepted by the repository owner during PR #15 review.
- `/api/v1` is configured but intentionally has no endpoint.
- No database, queue, cloud service, UI, ML model, or business API is selected.
- No readiness or liveness split is introduced yet.
- No coverage percentage gate is established.

## Risks and mitigations

- **Framework dependencies become incompatible:** retain the locked resolver
  result, run Python 3.13 validation locally and in CI, and review upgrades as
  focused dependency changes.
- **Ambient environment variables make tests nondeterministic:** use explicit
  test settings, clear relevant variables for default-setting tests, and reset
  the cached provider when its behavior is under test.
- **Health is mistaken for dependency readiness:** document it as deterministic
  process health and exclude all downstream-system claims from its response.
- **Global mutable settings leak across application instances:** resolve one
  instance in the factory and bind that exact instance through a scoped provider.
- **The source tree builds differently from an installed wheel:** inspect source
  and wheel contents and validate imports and health behavior in an isolated
  environment installed only from the built wheel and its dependencies.
- **Optional extras expand the runtime surface:** keep direct requirements free
  of extras and add optional capabilities only through reviewed issues.
- **Secrets are committed as configuration examples:** document variable names
  and synthetic values only; do not configure `.env` loading or commit secret
  material.

## Validation

Validate the decision with locked synchronization; lock freshness; Ruff format
and lint checks; strict mypy; synchronous pytest; and branch-coverage reporting
for `opsmind`. Confirm exact HTTP status, content type, response body, settings
defaults and overrides, invalid typed values, cache reset behavior, route
composition, and the OpenAPI schema.

Build both source and wheel distributions into a temporary output directory,
inspect their contents, and install the wheel with dependencies into a separate
temporary Python 3.13 environment. From outside the repository, verify imports,
application construction, and `/health`. Run the existing governance workflows,
relative-link validation, secret-pattern checks, artifact checks, and diff scope
checks without changing either workflow.

## Reconsideration triggers

- FastAPI, Pydantic, or Uvicorn no longer supports the accepted Python version.
- The service needs async integration-test fixtures or async-only dependencies.
- Real downstream services require distinct liveness and readiness semantics.
- Multiple deployable Python services require a workspace or package split.
- A settings source beyond environment variables becomes operationally required.
- Native extension modules require a build backend beyond pure-Python `uv_build`.
- Versioned business endpoints expose a routing constraint not handled by the
  reserved `/api/v1` prefix.
- Authentication, authorization, or public API lifecycle requirements change
  the application boundary.

## Implementation notes

- Keep `src/opsmind/__init__.py` present before synchronizing the packaged
  project.
- Use the uv build backend's default `src/opsmind` discovery; do not configure a
  custom package root.
- Do not load a `.env` file implicitly.
- Do not add optional dependency extras.
- Keep HTTPX in the existing `dev` dependency group.
- Keep the module-level ASGI application as `opsmind.main:app`.
- Keep health synchronous and deterministic until real readiness requirements
  exist.
- Preserve the accepted Ruff, mypy, pytest, and pytest-cov versions and settings.
- Treat database, business endpoint, Docker, frontend, AWS, CI redesign, and
  pre-commit work as separate issues.

## References

- [ADR-0000: Use Architecture Decision Records](0000-use-architecture-decision-records.md)
- [ADR-0001: Select Python Toolchain](0001-select-python-toolchain.md)
- [ADR-0002: Select Python Quality and Testing Toolchain](0002-select-python-quality-and-testing-toolchain.md)
- [Architecture Decision Record index](README.md)
- [Contribution guide](../../../CONTRIBUTING.md)
- [Python project configuration](../../../pyproject.toml)
- [Current project status](../../09-status/current-status.md)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Pydantic Settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Uvicorn documentation](https://www.uvicorn.org/)
- [uv build-backend documentation](https://docs.astral.sh/uv/concepts/build-backend/)
- GitHub issue #14: Establish FastAPI backend foundation
