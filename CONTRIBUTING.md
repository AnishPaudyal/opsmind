# Contributing to OpsMind

OpsMind uses an issue-first, review-based development workflow. The goal is to
keep product decisions, implementation, evidence, and learning connected.

## Standard Workflow

1. Create or select an issue with a clear problem, scope, and acceptance
   criteria.
2. Confirm that the work belongs in the current roadmap phase.
3. Create a short-lived branch from the default branch.
4. Make the smallest coherent change that satisfies the issue.
5. Run the relevant checks and document the results.
6. Open a pull request linked to the issue.
7. Address review findings on the same branch.
8. Merge only after the required human review.

## Branch Names

Use a descriptive prefix and short topic:

- `feature/<topic>`
- `fix/<topic>`
- `docs/<topic>`
- `chore/<topic>`
- `investigation/<topic>`

## Definition of Ready

An implementation issue is ready when it has:

- A problem statement
- An explicit in-scope and out-of-scope boundary
- Verifiable acceptance criteria
- Known dependencies
- Security, data, cost, and documentation considerations

## Definition of Done

A change is done when:

- Acceptance criteria are met.
- Relevant automated and manual checks pass.
- User-facing, operational, and architecture documentation is current.
- Security and data-handling implications were reviewed.
- The pull request explains what changed and how it was verified.
- Follow-up work is recorded in separate issues.

## Commit and Pull Request Expectations

- Keep commits focused and messages written in the imperative mood.
- Do not combine unrelated cleanup with a feature or fix.
- Include test results in the pull request.
- Call out migrations, compatibility changes, operational impact, and known
  limitations.
- Do not commit generated credentials, local environment files, build output,
  or large raw datasets.

## Documentation

Durable knowledge belongs in the repository, not only in chat history. Update
the relevant document when a decision changes product behavior, architecture,
operations, security, cost, or the learning narrative.

## Architecture Decision Records

Material technical or architectural decisions require an Architecture Decision
Record under [docs/01-architecture/decisions](docs/01-architecture/decisions/README.md).
Create and review ADRs through the normal branch and pull-request workflow,
keep them Proposed until the repository owner accepts them, and update the ADR
index whenever a record or its status changes. Accepted ADRs govern subsequent
work unless they are superseded through the documented ADR process.

## Python Quality

Synchronize the locked development environment before running Python quality
checks:

```bash
uv sync --locked --group dev
```

Verify that the lockfile remains current:

```bash
uv lock --check
```

Run the non-mutating validation commands locally:

```bash
uv run ruff format --check .
uv run ruff check --no-cache .
uv run mypy --no-incremental .
uv run pytest -p no:cacheprovider
```

The repository contains first-party source and tests, so pytest and coverage are
required. Routine coverage validation uses:

```bash
uv run pytest -p no:cacheprovider \
  --cov=opsmind \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml
```

Source-mutating Ruff commands are explicit developer actions:

```bash
uv run ruff format .
uv run ruff check --fix .
```

`ruff check --unsafe-fixes` is not part of the standard workflow. No Makefile,
task runner, shell wrapper, Python wrapper, or pre-commit hook is introduced
yet.

### Backend development

The packaged FastAPI application uses the `src/opsmind` layout. Start it locally
through the locked project environment:

```bash
uv run uvicorn opsmind.main:app --reload
```

The application reads typed settings from environment variables prefixed with
`OPSMIND_`; do not commit local credentials or `.env` files. The unversioned
`GET /health` route is process health only. Add versioned routes under the
configured `/api/v1` prefix only when an approved issue introduces a real
business capability.

Validate distribution packaging with a fresh temporary output directory:

```bash
uv build --out-dir /tmp/opsmind-build
```

Build output is generated evidence and must not be committed. Material changes
to the framework, packaging, configuration boundary, or route architecture
require ADR review.

Product and inventory tests can be run directly while developing the first
business API:

```bash
uv run pytest -p no:cacheprovider \
  tests/unit/test_product_domain.py \
  tests/unit/test_inventory_domain.py \
  tests/unit/test_memory_repository.py \
  tests/api/test_products.py
```

Tests must construct their own repository or application instance, must not
depend on test execution order, and must not share mutable business state. The
current repository boundary is deliberately in memory: it is isolated per
application instance and loses all data on process restart. Database behavior
and database-backed test fixtures remain outside this milestone.

Run focused demand-history tests with:

```bash
uv run pytest -p no:cacheprovider \
  tests/unit/test_demand_domain.py \
  tests/unit/test_demand_repository.py \
  tests/api/test_demand.py
```

Demand tests must verify that a conflicting batch stores no partial data, that
responses and repository results remain chronological, and that date filters
are inclusive. Construct fresh repositories or applications so demand state is
isolated, and never rely on test execution order. Demand remains part of the
same process-local in-memory repository as products and inventory; persistence
and database-backed fixtures remain future work.

Run focused baseline-forecast tests with:

```bash
uv run pytest -p no:cacheprovider \
  tests/unit/test_forecast_domain.py \
  tests/api/test_forecast.py
```

Forecast calculations belong in the pure domain layer and must remain
independent of FastAPI, Pydantic, repository implementations, external models,
and the system clock. Tests must preserve exact decimal arithmetic until final
two-decimal `ROUND_HALF_UP` quantization, prevent future observations from
crossing the effective cutoff, count records rather than calendar days, and
distinguish a recorded zero from a missing date. Forecast requests are
read-only: product, inventory, and demand state must remain unchanged.

Construct a fresh repository or application for each forecast test. Tests must
remain deterministic, order-independent, and isolated, while regression checks
continue to cover product, inventory, demand, health, custom-prefix, OpenAPI,
and shared dependency-injection behavior. Forecast source history remains
process-local and nonpersistent.

Run focused stockout-exposure tests with:

```bash
uv run pytest -p no:cacheprovider \
  tests/unit/test_forecast_domain.py \
  tests/unit/test_stockout_domain.py \
  tests/api/test_forecast.py \
  tests/api/test_stockout.py
```

Stockout calculations must reuse the pure forecast domain's exact simple-mean
statistics rather than duplicating selection rules or using the displayed
rounded average. Preserve product lead time as the exposure horizon, current
available inventory even when negative, inclusive cutoffs, recorded zeroes,
and missing dates. Do not introduce probability or reorder semantics.

Quantize public analytical values independently to two decimals with
`ROUND_HALF_UP`, normalize negative zero, and derive shortage and status from
the normalized public balance. Exposure requests remain read-only and must not
persist results or mutate product, inventory, or demand state.

Use fresh repositories or applications for exposure tests. Regression coverage
must keep the forecast response exact and continue to validate all existing
routes, custom prefixes, OpenAPI, shared dependency injection, and application
isolation without relying on test order.

### Continuous integration

The [Python-quality workflow](.github/workflows/python-quality.yml) reproduces
the approved non-mutating local Python checks for pull requests targeting
`main` and pushes to `main`. It is an authoritative pull-request gate.

Run the currently applicable checks locally before pushing:

```bash
uv sync --locked --group dev
uv lock --check
uv run ruff format --check .
uv run ruff check --no-cache .
```

mypy and pytest are mandatory because tracked first-party source and standard
pytest tests now exist. The workflow's empty-code detection selects those real
paths, so it no longer uses its temporary no-code notices for this repository
state.

The governance workflow validates repository policy and document hygiene, while
the Python-quality workflow validates the locked Python environment and quality
contract. Pre-commit remains deferred. Future application and integration tests
may require separate jobs or workflows when databases, services, secrets,
matrices, or longer runtimes are introduced.

## Security

Report suspected credential exposure or sensitive-data leakage privately to the
repository owner. Do not paste secrets into an issue or pull request.
