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

Run focused reorder-recommendation tests with:

```bash
uv run pytest -p no:cacheprovider \
  tests/unit/test_forecast_domain.py \
  tests/unit/test_stockout_domain.py \
  tests/unit/test_reorder_domain.py \
  tests/api/test_forecast.py \
  tests/api/test_stockout.py \
  tests/api/test_reorder.py
```

Reorder calculations must reuse the pure stockout-exposure result rather than
duplicating forecast, record-selection, or inventory rules. Apply `Decimal`
`ROUND_CEILING` directly to the public two-decimal shortage without a float
conversion. Preserve the complete exposure evidence, derive recommendation
status from the whole-unit result, and test exact-unit and fractional-unit
boundaries, including zero, `0.01`, `1.00`, `1.01`, `18.00`, and `18.75`.

Recommendation requests remain read-only and must not persist a forecast,
exposure, recommendation, order, or approval or mutate existing state. Use
fresh repositories or applications to verify isolation, and retain regression
coverage for forecast, exposure, product, inventory, demand, health, custom
prefixes, OpenAPI, and shared dependency injection without relying on test
order.

Run focused recommendation-review tests with:

```bash
uv run pytest -p no:cacheprovider \
  tests/unit/test_recommendation_audit_domain.py \
  tests/unit/test_recommendation_review_domain.py \
  tests/repositories/test_recommendation_workflow_repository.py \
  tests/api/test_recommendation_reviews.py
```

Recommendation reviews must store the complete actionable recommendation as
an immutable snapshot before a decision is made. Keep the workflow repository
separate from the product, inventory, and demand repository. Retrieval and
decision operations must use only stored workflow state and must never
recalculate forecast, exposure, or recommendation results.

Every stored review must have an immutable audit history. Pending histories
contain exactly sequence `1` `review_created`; terminal histories contain that
event followed by exactly one sequence `2` approval or rejection event. Test
sequence ordering explicitly when timestamps are equal, because timestamps do
not determine order.

Review state and matching event writes belong to one workflow repository
operation under one lock. Tests must cover factory or validation failure before
storage, atomic creation and terminal transitions, immutable returned tuples,
duplicate identifiers, and the absence of orphan reviews or events. Do not
introduce route-level dual writes or a separately coordinated audit repository.

Domain transitions are pure and receive decision identifiers and timestamps as
inputs. Reject naive timestamps and normalize aware timestamps to UTC. Use an
injected fixed clock in API tests. Approval and rejection are terminal;
identical normalized retries return the original decision, while changed or
opposite retries conflict without changing stored state. Audit assertions must
also prove that identical retries append no duplicate, conflicts append nothing,
and original decision and event identifiers remain unchanged. Repository tests
must exercise the full read-transition-write-and-append under one lock,
including a deterministic concurrent approve-versus-reject race with exactly
one terminal event. Do not coordinate concurrency tests with sleeps.

Use fresh workflow repositories for application isolation, and test deliberately
shared repositories separately when shared-history behavior is relevant.
History retrieval must be repeatable and read-only, access no operational
repository, and retain existing product, inventory, demand, forecast, stockout,
reorder, workflow, custom-prefix, OpenAPI, isolation, and health regressions.

The current repository and event history are process-local and nonpersistent.
Treat `decided_by` as unverified caller input: no authentication, authorization,
or role check exists. Append-only behavior applies only through supported APIs;
history is not cryptographically tamper-evident or compliance-grade, and
approval must not create an order or mutate operational state.

### PostgreSQL persistence development

PostgreSQL operational persistence follows accepted ADR-0005. The
`ProductInventoryRepository` Protocol remains the domain-facing boundary;
SQLAlchemy models stay inside
`src/opsmind/persistence/postgresql`, and immutable domain models must not import
SQLAlchemy, Psycopg, Alembic, engines, sessions, or ORM rows.

All schema changes are Alembic-first. Add and review a migration, update the
authoritative SQLAlchemy metadata, and validate both upgrade and downgrade
against real PostgreSQL. Runtime application code and test fixtures must never
call `metadata.create_all()` as a substitute for migrations.

Repository methods own their transaction boundaries. Use one short-lived
session per operation or explicit transaction, close it on success and failure,
and roll back before translating a recognized integrity violation. Translate
only known constraints into existing business errors; never expose SQL, driver
details, table or constraint names, or connection URLs to API clients. ORM
instances must be mapped to domain objects before leaving the repository.

PostgreSQL integration tests require `OPSMIND_TEST_DATABASE_URL`. The safety
gate accepts only the `postgresql+psycopg` driver, a local or loopback host, and
a database name ending in `_test` or `_testing`. Do not use
`OPSMIND_DATABASE_URL` for destructive cleanup, do not target a shared or
production-like database, and do not weaken the gate. Initialize schema through
Alembic and delete table data in dependency-safe order between tests.

Use the PostgreSQL-only Compose service for local integration work:

```bash
OPSMIND_POSTGRES_DB=opsmind_test \
OPSMIND_POSTGRES_PORT=55432 \
docker compose -p opsmind-test -f compose.postgresql.yml up -d --wait

export OPSMIND_TEST_DATABASE_URL='postgresql+psycopg://opsmind:opsmind-development-only@127.0.0.1:55432/opsmind_test'
uv run pytest -p no:cacheprovider tests/integration/postgresql
```

Concurrency tests must use barriers or other deterministic coordination, never
sleep-based timing. Every persistence change must retain memory-backend
regressions and verify PostgreSQL behavior with real PostgreSQL rather than
SQLite. Database URLs are secrets even in diagnostic paths: use synthetic local
or CI examples only and never log, snapshot, or commit real credentials.

The current persistence boundary is mixed. PostgreSQL stores products,
inventory, and demand; recommendation reviews, decisions, and audit events
remain process-local and restart-volatile. Do not describe the application as
fully durable or the audit history as PostgreSQL-backed.

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
