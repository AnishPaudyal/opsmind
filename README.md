# OpsMind - Cloud-Native Supply Chain Decision Intelligence Platform

OpsMind is a production-oriented portfolio project for building and explaining a
cloud-native supply-chain decision-intelligence platform. It is designed to
demonstrate backend engineering, data engineering, machine learning, cloud
architecture, DevOps, security, observability, and responsible AI through one
coherent product.

## Current Status

Phases 0 through 4 are complete. The repository owner accepted the Phase 4
forecasting-baseline and evaluation review under Issue #48 on 2026-08-06.
Phase 5, stockout risk and reorder recommendations, is Current. Capabilities
associated with Phases 5 and 6 were delivered ahead of their formal gates and
are not yet formally complete.

The current backend can create and retrieve products, store current inventory,
and ingest and retrieve daily demand history through either an isolated memory
backend or an explicitly selected PostgreSQL backend. It can calculate a
transparent arithmetic-mean demand forecast, deterministic stockout exposure,
and a whole-unit reorder recommendation on request.

Actionable recommendations can be stored as immutable snapshots for approval or
rejection with ordered audit-event history. Memory mode keeps operational and
workflow state isolated and restart-volatile. PostgreSQL mode makes both forms
of state durable across application restart and shared by applications using
the same database.

This repository does not yet contain:

- Real-world forecast validation on governed operational data
- Probabilistic forecasts, prediction intervals, or trained forecast models
- Authentication, authorization, or verified reviewer identity
- Calibrated stockout probability or a trained stockout model
- Purchase-order creation or external ordering integration
- A frontend user interface or containerized API
- AWS infrastructure or cloud deployment
- A production database, production data, or production-readiness approval

Those capabilities require reviewed issues and their applicable phase gates.

## First Product Slice

The first end-to-end workflow is:

1. Load product and demand-history data.
2. Produce a demand forecast.
3. Calculate deterministic stockout exposure.
4. Generate a reorder recommendation with supporting evidence.
5. Let a user approve or reject the recommendation.
6. Record the decision and its audit history.

## Technical Direction

The current implemented local stack uses:

- Python and FastAPI
- PostgreSQL, SQLAlchemy, and Alembic
- pytest, Ruff, mypy, and PostgreSQL integration tests

Docker Compose is used only to run local PostgreSQL; it does not containerize
the OpsMind API. Next.js and TypeScript remain a later product direction, and no
frontend is currently implemented.

Later phases may introduce AWS services, infrastructure as code, event
streaming, analytical pipelines, MLOps, and retrieval-augmented AI. Each
addition must be justified by a concrete product or learning requirement.

## Repository Guide

- [AGENTS.md](AGENTS.md) contains instructions for Codex and other AI-assisted
  contributors.
- [CONTRIBUTING.md](CONTRIBUTING.md) defines the development workflow.
- [ROADMAP.md](ROADMAP.md) defines phase order and exit criteria.
- [docs/00-project-foundation](docs/00-project-foundation) contains the project
  charter, scope, competency plan, governance model, and technology principles.
- [docs/01-architecture](docs/01-architecture) contains architecture and
  evaluation-design records.
- [docs/05-evaluation](docs/05-evaluation) contains durable, reviewed evaluation
  evidence.
- [docs/09-risk-cost-security](docs/09-risk-cost-security) contains the risk,
  cost, security, and responsible-AI baseline.
- [docs/12-phase-reviews](docs/12-phase-reviews) records phase reviews.

## Local Python setup

Install `uv` using an [officially supported installation
method](https://docs.astral.sh/uv/getting-started/installation/), then verify the
installation:

```bash
uv --version
```

Install or confirm the supported Python 3.13 interpreter:

```bash
uv python install 3.13
```

Synchronize the repository environment from the committed lockfile:

```bash
uv sync --locked
```

Run repository Python commands through the project environment:

```bash
uv run python --version
```

OpsMind supports Python 3.13. The local environment is `.venv`, which must
never be committed. Do not install OpsMind dependencies into Miniconda base,
Homebrew Python, or `/usr/bin/python3`. Bare `python` and `python3` may resolve
to unrelated interpreters, so prefer `uv run` for repository commands.

## FastAPI backend

The packaged backend lives under `src/opsmind`. Start the local ASGI application
with:

```bash
uv run uvicorn opsmind.main:app --reload
```

The API exposes an unversioned deterministic process-health endpoint and
fifteen product, inventory, demand, forecast, exposure, recommendation, review,
and audit-history operations under the configured business prefix:

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/health` | Report process health. |
| `POST` | `/api/v1/products` | Create a normalized product. |
| `GET` | `/api/v1/products` | List products in normalized-SKU order. |
| `GET` | `/api/v1/products/{product_id}` | Retrieve one product. |
| `PUT` | `/api/v1/products/{product_id}/inventory` | Set or replace inventory. |
| `GET` | `/api/v1/products/{product_id}/inventory` | Retrieve inventory. |
| `POST` | `/api/v1/products/{product_id}/demand` | Atomically add daily demand. |
| `GET` | `/api/v1/products/{product_id}/demand` | Retrieve daily demand. |
| `GET` | `/api/v1/products/{product_id}/forecast` | Calculate a baseline demand forecast. |
| `GET` | `/api/v1/products/{product_id}/stockout-exposure` | Calculate deterministic lead-time exposure. |
| `GET` | `/api/v1/products/{product_id}/reorder-recommendation` | Calculate a whole-unit reorder recommendation. |
| `POST` | `/api/v1/products/{product_id}/reorder-recommendations` | Store one actionable recommendation snapshot for review. |
| `GET` | `/api/v1/reorder-recommendations/{recommendation_id}` | Retrieve a stored recommendation review. |
| `POST` | `/api/v1/reorder-recommendations/{recommendation_id}/approve` | Approve a pending recommendation. |
| `POST` | `/api/v1/reorder-recommendations/{recommendation_id}/reject` | Reject a pending recommendation. |
| `GET` | `/api/v1/reorder-recommendations/{recommendation_id}/audit-events` | Retrieve ordered workflow history. |

Application settings use the `OPSMIND_` environment-variable prefix. Supported
overrides are:

- `OPSMIND_APPLICATION_NAME`
- `OPSMIND_SERVICE_NAME`
- `OPSMIND_ENVIRONMENT` (`local`, `test`, `staging`, or `production`)
- `OPSMIND_DEBUG`
- `OPSMIND_API_V1_PREFIX`
- `OPSMIND_PERSISTENCE_BACKEND` (`memory` or `postgresql`)
- `OPSMIND_DATABASE_URL` (required only for `postgresql`)

The default service is `opsmind-api`, the default environment is `local`, debug
mode is disabled, and the default business prefix is `/api/v1`. The application
does not load a repository `.env` file implicitly.

`GET /health` reports only that the API process can serve a request. It does not
claim readiness for a database, AWS resource, external service, or product
workflow. PostgreSQL backend selection does not change this process-health
contract and no readiness endpoint is introduced.

### Persistence backends

The migration-phase default remains `memory`. Each memory-backed application
has isolated operational and recommendation-workflow repositories. Products,
inventory, demand, reviews, decisions, and audit events are lost when the
process stops and are not shared with independent applications.

Select PostgreSQL explicitly to make those persisted operational and workflow
resources durable and shared:

```bash
export OPSMIND_PERSISTENCE_BACKEND=postgresql
export OPSMIND_DATABASE_URL='postgresql+psycopg://opsmind:opsmind-development-only@127.0.0.1:5432/opsmind'
```

The URL must use the `postgresql+psycopg` SQLAlchemy driver form. Treat every
database URL as a secret: provide it through the environment or a governed
secret manager, never commit a real value, and never paste it into logs, issues,
screenshots, or support output. The application does not load `.env`
automatically. An explicitly injected repository still takes precedence over
backend selection.

When the application creates the PostgreSQL engine and session factory, it
shares them for the application lifespan and disposes the engine during
application shutdown. Explicitly injected repositories and related resources
remain caller owned.

The current persistence behavior is:

```text
Memory selected:
products / inventory / demand
recommendation reviews / decisions / audit events
-> isolated, restart-volatile, and not shared between applications

PostgreSQL selected:
products / inventory / demand
recommendation reviews / decisions / audit events
-> durable across restart and shared through the same database
```

Forecasts, stockout exposure, and calculated reorder recommendations remain
read-only calculations and are not persisted. PostgreSQL stores their
operational inputs and the stored review workflow, including decisions and
audit events. PostgreSQL selection does not provide production readiness.

#### Start and migrate local PostgreSQL

The Compose file runs PostgreSQL 17 only; it does not containerize OpsMind:

```bash
docker compose -f compose.postgresql.yml up -d --wait
docker compose -f compose.postgresql.yml ps
```

Apply the schema before starting a PostgreSQL-backed application:

```bash
export OPSMIND_DATABASE_URL='postgresql+psycopg://opsmind:opsmind-development-only@127.0.0.1:5432/opsmind'
uv run alembic upgrade head
uv run alembic current
export OPSMIND_PERSISTENCE_BACKEND=postgresql
uv run uvicorn opsmind.main:app --reload
```

Alembic revision `0005_operational_data` creates products, inventory positions,
and demand observations. Revision `0006_workflow_persistence` creates the
recommendation-review, decision, evidence, and audit-event schema.

Runtime startup never creates or migrates tables. Foreign keys are restrictive,
available inventory remains derived, and schema changes must use reviewed
Alembic revisions.

Stopping Compose preserves the named data volume:

```bash
docker compose -f compose.postgresql.yml down
```

Deleting the volume permanently destroys the local development database:

```bash
docker compose -f compose.postgresql.yml down --volumes
```

That destructive command is also the local reset procedure. Start the service
again and reapply `alembic upgrade head` afterward.

#### Run PostgreSQL integration tests

Use a separate Compose project, port, volume, and database whose name ends in
`_test`:

```bash
OPSMIND_POSTGRES_DB=opsmind_test \
OPSMIND_POSTGRES_PORT=55432 \
docker compose -p opsmind-test -f compose.postgresql.yml up -d --wait

export OPSMIND_TEST_DATABASE_URL='postgresql+psycopg://opsmind:opsmind-development-only@127.0.0.1:55432/opsmind_test'
uv run pytest -p no:cacheprovider tests/integration/postgresql
```

The integration fixture refuses destructive setup when the variable is absent,
the host is not local or loopback, or the database name does not end in `_test`
or `_testing`. It initializes schema through Alembic and never uses the normal
application URL for cleanup. With no test URL, integration tests skip clearly
while memory and unit tests still run.

Migration downgrade validation is allowed only against this disposable test
database:

```bash
export OPSMIND_DATABASE_URL="$OPSMIND_TEST_DATABASE_URL"
uv run alembic downgrade base
uv run alembic upgrade head
```

Stop the test service without deleting data using `docker compose -p
opsmind-test -f compose.postgresql.yml down`. Add `--volumes` only when the
dedicated test data may be permanently deleted.

For troubleshooting, use `docker compose -f compose.postgresql.yml ps`, the
PostgreSQL health status, and Alembic's revision output. Do not print the
database URL. Confirm that the selected port is free, the database name is
correct, and migrations reached head before investigating application code.

### Product and inventory example

With the local server running, interactive OpenAPI documentation is available
at `http://127.0.0.1:8000/docs`. A product can also be created with a synthetic
request:

```bash
curl --fail-with-body \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "sku": " sensor-001 ",
    "name": "Temperature Sensor",
    "unit_of_measure": "each",
    "lead_time_days": 14,
    "is_active": true
  }' \
  http://127.0.0.1:8000/api/v1/products
```

The API generates the UUID and returns the normalized SKU:

```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "sku": "SENSOR-001",
  "name": "Temperature Sensor",
  "unit_of_measure": "each",
  "lead_time_days": 14,
  "is_active": true
}
```

Use the returned UUID to set inventory:

```bash
curl --fail-with-body \
  --request PUT \
  --header 'Content-Type: application/json' \
  --data '{"on_hand_quantity": 100, "allocated_quantity": 35}' \
  http://127.0.0.1:8000/api/v1/products/00000000-0000-0000-0000-000000000001/inventory
```

Inventory uses three quantities: on-hand is the physical quantity present,
allocated is the quantity already committed to demand, and available is
calculated as on-hand minus allocated. Available quantity may be negative; a
negative value represents a shortage and is not clamped to zero.

With the default memory backend, products and inventory remain isolated per
application and are lost on restart. With PostgreSQL explicitly selected and
migrated, they persist across restarts and are shared by applications using the
same database. Neither backend adds authentication, stockout probability,
ordering, frontend, AWS, or deployment capability.

### Demand history

Demand history records the non-negative quantity observed for one product on
one calendar date. It uses daily granularity, accepts zero as valid demand, and
allows only one observation per product/date combination. Demand is the
historical input for the baseline forecast described below.

Submit one or more observations as an atomic batch using the UUID returned when
the product was created:

```bash
curl --fail-with-body \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "observations": [
      {"demand_date": "2026-07-03", "quantity": 9},
      {"demand_date": "2026-07-01", "quantity": 12},
      {"demand_date": "2026-07-02", "quantity": 18}
    ]
  }' \
  http://127.0.0.1:8000/api/v1/products/00000000-0000-0000-0000-000000000001/demand
```

The response is chronological even when the request is not:

```json
[
  {
    "product_id": "00000000-0000-0000-0000-000000000001",
    "demand_date": "2026-07-01",
    "quantity": 12
  },
  {
    "product_id": "00000000-0000-0000-0000-000000000001",
    "demand_date": "2026-07-02",
    "quantity": 18
  },
  {
    "product_id": "00000000-0000-0000-0000-000000000001",
    "demand_date": "2026-07-03",
    "quantity": 9
  }
]
```

If any submitted date is repeated within the batch or already exists for that
product, the entire request returns HTTP 409 and stores nothing from the failed
batch. Retrieve complete history or apply inclusive date bounds:

```bash
curl --fail-with-body \
  'http://127.0.0.1:8000/api/v1/products/00000000-0000-0000-0000-000000000001/demand?start_date=2026-07-01&end_date=2026-07-03'
```

Swagger UI at `http://127.0.0.1:8000/docs` documents both demand operations and
their schemas. Demand uses the same selected operational repository as products
and inventory. It is restart-volatile with memory and durable with PostgreSQL.
Ingestion pipelines and model training remain outside this milestone.

### Baseline demand forecast

The baseline forecast is a transparent reference calculation that averages the
most recent eligible demand observations and projects that exact average across
a requested horizon:

```text
exact average = sum(selected quantities) / observations used
exact forecast = exact average * horizon days
```

A simple baseline comes before complex models so future forecasting work can be
compared with a deterministic, explainable reference. The endpoint calculates
the result on demand and never stores a forecast or changes product, inventory,
or demand state:

```text
GET /api/v1/products/{product_id}/forecast
```

| Query parameter | Default | Bounds | Meaning |
| --- | --- | --- | --- |
| `lookback_observations` | `7` | 1–365 | Most recent eligible records to select. |
| `horizon_days` | `7` | 1–365 | Days covered by the projected quantity. |
| `as_of_date` | latest demand date | Optional date | Inclusive cutoff for eligible history. |

Lookback counts recorded observations, not elapsed calendar days. A recorded
zero is real demand and remains in the calculation; a missing date remains
missing and is never imputed as zero. When an explicit cutoff is supplied,
later observations are excluded to prevent future-data leakage. Without a
cutoff, the latest stored demand date becomes the effective cutoff—no system
clock is used.

For the July 1–4 quantities `12, 18, 9, 0`, request a seven-day forecast with:

```bash
curl --fail-with-body \
  'http://127.0.0.1:8000/api/v1/products/00000000-0000-0000-0000-000000000001/forecast?lookback_observations=4&horizon_days=7&as_of_date=2026-07-04'
```

The explanatory response identifies the selected window and calculation:

```json
{
  "product_id": "00000000-0000-0000-0000-000000000001",
  "method": "simple_mean",
  "as_of_date": "2026-07-04",
  "lookback_observations_requested": 4,
  "observations_used": 4,
  "training_start_date": "2026-07-01",
  "training_end_date": "2026-07-04",
  "average_daily_demand": 9.75,
  "horizon_days": 7,
  "forecast_quantity": 68.25
}
```

Average and forecast values use exact standard-library decimal arithmetic.
Each is independently rounded to two decimal places with `ROUND_HALF_UP` only
at the result boundary. The horizon forecast is calculated from the unrounded
exact mean, not the displayed average: demand `1, 0, 0` displays an average of
`0.33`, while its three-day forecast is correctly `1.00`, not `0.99`.

An existing product without eligible history returns HTTP 422; a missing
product returns HTTP 404. Swagger UI at `http://127.0.0.1:8000/docs` documents
the response metadata and parameter constraints.

This baseline uses source demand through the selected operational repository.
PostgreSQL-backed history survives restart; memory-backed history does not. The simple mean does not
model trend, seasonality, intermittent demand, or uncertainty; it supplies no
confidence interval and is not production-grade machine learning. Phase 4 now
measures this baseline on deterministic synthetic temporal windows, but those
results do not establish real-world accuracy. The deterministic exposure and
recommendation calculations below use this baseline.

### Reproducible baseline evaluation

Run the governed Phase 4 evaluation separately from the HTTP API:

```bash
uv run python -m opsmind.evaluation \
  --output-dir /tmp/opsmind-phase4-evaluation \
  --lookback-observations 7 \
  --horizon-days 7 \
  --minimum-training-observations 7
```

The command uses deterministic synthetic demand series, chronological forecast
origins, complete future target windows, and the existing
`calculate_simple_mean_forecast` domain implementation. It writes only
`evaluation.json` and `evaluation.md` to the selected output directory and
refuses to overwrite existing artifacts unless `--force` is supplied.

The accepted configuration produced 161 valid windows from 288 attempts. The
aggregate results were MAE `11.26`, forecast bias `-4.57`, and WAPE `17.51%`.
The simple mean was exact for the controlled stable, all-zero, weekly-cycle,
and aligned intermittent patterns. It under-forecast upward trend and an abrupt
upward level shift, and over-forecast downward trend. Missing calendar dates
reduced evaluable windows rather than being silently interpreted as zero.

These are synthetic reference measurements, not real-world accuracy,
production-readiness, or downstream decision-quality claims. The durable
method, findings, checksums, exclusions, and limitations are recorded in
[the Phase 4 baseline evaluation report](docs/05-evaluation/phase-4-baseline-forecast-evaluation.md).

### Deterministic stockout exposure

Stockout exposure answers whether currently available inventory covers the
baseline demand expected during a product's replenishment lead time. It is an
explainable arithmetic comparison, not a probability, calibrated risk score,
confidence rating, or reorder recommendation:

```text
available inventory = on-hand quantity - allocated quantity
exact lead-time demand = exact average daily demand * product lead-time days
projected balance = available inventory - exact lead-time demand
projected shortage = max(-public projected balance, 0.00)
```

Calculate exposure on demand with:

```text
GET /api/v1/products/{product_id}/stockout-exposure
```

| Query parameter | Default | Bounds | Meaning |
| --- | --- | --- | --- |
| `lookback_observations` | `7` | 1–365 | Most recent eligible demand records to select. |
| `as_of_date` | latest demand date | Optional date | Inclusive cutoff for eligible history. |

Clients do not supply a forecast horizon. The product's authoritative
`lead_time_days` defines it, including zero and values greater than 365. An
exposure request retrieves the product, inventory, and demand through the same
injected repository used by the existing business routes.

The result has one of two deterministic statuses:

- `sufficient` when the public projected balance is zero or positive.
- `shortage_projected` when the public projected balance is negative.

Exact equality is sufficient. Negative available inventory is preserved rather
than clamped. For a zero-lead-time product, lead-time demand is `0.00`, so the
projected balance is the current available inventory.

For a product with a five-day lead time, 60 on hand, 10 allocated, and the
July 1–4 demand quantities `12, 18, 9, 0`, request:

```bash
curl --fail-with-body \
  'http://127.0.0.1:8000/api/v1/products/00000000-0000-0000-0000-000000000001/stockout-exposure?lookback_observations=4&as_of_date=2026-07-04'
```

The average is `9.75`, lead-time demand is `48.75`, available inventory is
`50`, and the response reports a sufficient balance of `1.25`:

```json
{
  "product_id": "00000000-0000-0000-0000-000000000001",
  "forecast_method": "simple_mean",
  "as_of_date": "2026-07-04",
  "lookback_observations_requested": 4,
  "observations_used": 4,
  "training_start_date": "2026-07-01",
  "training_end_date": "2026-07-04",
  "average_daily_demand": 9.75,
  "lead_time_days": 5,
  "on_hand_quantity": 60,
  "allocated_quantity": 10,
  "available_inventory": 50,
  "forecasted_lead_time_demand": 48.75,
  "projected_inventory_balance": 1.25,
  "projected_shortage_quantity": 0.0,
  "status": "sufficient"
}
```

Exposure reuses the forecast domain's chronological record selection,
inclusive cutoff, zero-demand preservation, and missing-date behavior. Later
observations cannot cross an explicit cutoff. The latest stored demand date is
the default cutoff, so no system clock affects the result.

Lead-time demand is calculated from the exact unrounded mean. Analytical values
are independently rounded to two decimal places using `ROUND_HALF_UP` at the
public boundary. A balance that quantizes to negative zero is normalized to
`0.00`; shortage is then `0.00` and status is `sufficient`, keeping all public
fields consistent.

A missing product or missing inventory position returns HTTP 404. An existing
product without eligible demand returns HTTP 422. Swagger UI at
`http://127.0.0.1:8000/docs` documents the schema and validation constraints.

The operation is read-only: it stores no exposure or forecast and changes no
product, inventory, or demand state. Its operational inputs follow the active
persistence backend: memory is isolated and restart-volatile, while PostgreSQL
is shared and restart-durable.

The operation provides no stockout probability, uncertainty interval,
safety-stock optimization, or measured forecast accuracy. The deterministic
recommendation below uses its public shortage as the recommendation boundary.

### Deterministic reorder recommendation

A reorder recommendation converts the public projected shortage from the
stockout-exposure calculation into a whole-unit proposal. Exposure is the
evidence, the recommendation is an unapproved calculation, and the stored
review workflow described below is a separate capability:

```text
recommended reorder quantity = ceiling(public projected shortage quantity)
```

Calculate the recommendation on demand with:

```text
GET /api/v1/products/{product_id}/reorder-recommendation
```

| Query parameter | Default | Bounds | Meaning |
| --- | --- | --- | --- |
| `lookback_observations` | `7` | 1–365 | Most recent eligible demand records to select. |
| `as_of_date` | latest demand date | Optional date | Inclusive cutoff for eligible history. |

The sole policy is `projected_shortage_ceiling`. It applies standard-library
`Decimal` `ROUND_CEILING` directly to the two-decimal public shortage; it never
converts the value through binary floating point before rounding. A shortage of
`0.00` recommends `0` units, `0.01` recommends `1`, `1.00` recommends `1`,
`1.01` recommends `2`, `18.00` recommends `18`, and `18.75` recommends `19`.
Nearest-integer rounding is not used because it could round a positive
fractional shortage down and leave part of the shortage uncovered. The public
shortage is intentionally authoritative, so the recommendation does not
recalculate or round from a hidden exact balance.

For the same five-day product and July 1–4 demand quantities, reducing on-hand
inventory to 40 with 10 allocated produces a public shortage of `18.75`:

```bash
curl --fail-with-body \
  'http://127.0.0.1:8000/api/v1/products/00000000-0000-0000-0000-000000000001/reorder-recommendation?lookback_observations=4&as_of_date=2026-07-04'
```

The response preserves the complete exposure evidence and adds only the
recommendation policy, whole-unit quantity, unit of measure, and status:

```json
{
  "product_id": "00000000-0000-0000-0000-000000000001",
  "forecast_method": "simple_mean",
  "as_of_date": "2026-07-04",
  "lookback_observations_requested": 4,
  "observations_used": 4,
  "training_start_date": "2026-07-01",
  "training_end_date": "2026-07-04",
  "average_daily_demand": 9.75,
  "lead_time_days": 5,
  "on_hand_quantity": 40,
  "allocated_quantity": 10,
  "available_inventory": 30,
  "forecasted_lead_time_demand": 48.75,
  "projected_inventory_balance": -18.75,
  "projected_shortage_quantity": 18.75,
  "recommendation_policy": "projected_shortage_ceiling",
  "recommended_reorder_quantity": 19,
  "unit_of_measure": "each",
  "recommendation_status": "reorder_recommended"
}
```

Zero recommended units use `no_reorder_needed`; a positive whole-unit result
uses `reorder_recommended`. A missing product or inventory position returns
HTTP 404, and an existing product without eligible demand returns HTTP 422.
The route shares the exposure endpoint's cutoff, chronological selection,
record-count lookback, recorded-zero, missing-date, negative-inventory,
zero-lead-time, and custom-prefix behavior.

The calculated operation remains read-only and nonpersistent. It stores no
forecast, exposure, recommendation, order, or approval and does not mutate
product, inventory, or demand state. It does not select suppliers, prices,
pack sizes, minimum order quantities, safety stock, service levels,
probabilities, or confidence. The bounded stored-review workflow below is a
separate capability.

### Stored reorder recommendation review

An actionable calculated recommendation can be captured as an immutable
snapshot before human review:

```text
POST /api/v1/products/{product_id}/reorder-recommendations
```

Creation supports the same optional inclusive `as_of_date` and the same
`lookback_observations` default of `7` with bounds from 1 through 365. It reads
product, inventory, and demand through the existing repository, invokes the
existing stockout and reorder domain calculations, and stores only a result
whose status is `reorder_recommended` with a positive whole-unit quantity. A
current `no_reorder_needed` result returns HTTP 409 and creates no review.

The server assigns a UUID and a timezone-aware UTC creation time. The response
contains the complete original recommendation evidence under `recommendation`,
a `pending_review` status, and no decision. A product can have multiple separate
snapshots; each represents the inputs and calculation at its own creation time.
Later inventory or demand changes do not alter, refresh, or invalidate an
existing snapshot.

Retrieve a snapshot and its current state without recalculation:

```text
GET /api/v1/reorder-recommendations/{recommendation_id}
```

The only workflow transitions are:

```text
pending_review -> approved
pending_review -> rejected
```

Both terminal states are final in this milestone. Approve a recommendation
with:

```bash
curl --fail-with-body \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "decided_by": "Anish Paudyal",
    "approved_quantity": 24,
    "note": "Physical ordering occurs in case packs of six."
  }' \
  http://127.0.0.1:8000/api/v1/reorder-recommendations/00000000-0000-0000-0000-000000000101/approve
```

`approved_quantity` is optional and defaults to the stored recommended
quantity. A different positive approved quantity records the human decision
without changing the original recommendation. `decided_by` is required and
trimmed; an optional blank note becomes `null`.

Reject a recommendation with:

```bash
curl --fail-with-body \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "decided_by": "Anish Paudyal",
    "reason": "Inbound inventory is already scheduled."
  }' \
  http://127.0.0.1:8000/api/v1/reorder-recommendations/00000000-0000-0000-0000-000000000101/reject
```

A rejection requires a nonblank reason and never has an approved quantity.
Workflow timestamps reject naive datetimes and normalize aware datetimes to
UTC. The application supplies time through a narrow clock boundary so tests do
not depend on the system clock.

An identical normalized retry returns the existing terminal review with its
original decision UUID and timestamp. A changed retry or the opposite decision
returns HTTP 409 and leaves state unchanged. Each full read-transition-write is
serialized by the workflow repository, so concurrent approval and rejection
cannot both win.

Review storage uses the selected recommendation-workflow repository. Memory
mode is thread-safe within one process but is isolated and restart-volatile.
PostgreSQL mode shares reviews and decisions through the selected database and
preserves them across application restart.

Retrieval, approval, and rejection read the stored workflow object only; they
do not recalculate forecast, exposure, or recommendation values and do not
mutate product, inventory, or demand.

The `decided_by` value is caller supplied and unverified. There is no
authentication, authorization, role check, or trusted user identity. The stored
snapshot, current aggregate, and ordered event history are useful workflow
evidence, but they do not prove who performed an action. Approval does not
create a purchase order, reserve or change inventory, select a supplier, or
initiate any external action.

### Recommendation audit history

Every stored review has an immutable, append-only event stream available at:

```text
GET /api/v1/reorder-recommendations/{recommendation_id}/audit-events
```

The stream records exactly three supported event types:

- `review_created`
- `recommendation_approved`
- `recommendation_rejected`

Sequence numbers are local to one recommendation. Sequence `1` is always the
creation event. A successful first approval or rejection appends sequence `2`.
Sequence, rather than timestamp, defines order because an injected fixed clock
can legitimately give creation and decision events the same time.

Events are generated automatically by successful workflow writes. The selected
workflow repository stores current review state and its event tuple within one
atomic repository transaction boundary.

Memory mode enforces this boundary under one repository lock. PostgreSQL mode
enforces it through one database transaction. Review creation and its creation
event therefore succeed together, and a terminal state change and matching
terminal event succeed together. HTTP routes never perform independent state
and event writes.

An identical normalized approval or rejection retry returns the original
decision and appends no duplicate event. A changed or opposite retry returns
HTTP 409 and appends nothing. Clients cannot create, update, delete, reorder, or
correct events directly.

Retrieve a review's history with:

```bash
curl --fail-with-body \
  http://127.0.0.1:8000/api/v1/reorder-recommendations/00000000-0000-0000-0000-000000000101/audit-events
```

An approved history keeps the original system recommendation separate from the
human-approved quantity:

```json
{
  "recommendation_id": "00000000-0000-0000-0000-000000000101",
  "events": [
    {
      "sequence_number": 1,
      "event_type": "review_created",
      "review_status": "pending_review",
      "recommended_reorder_quantity": 19,
      "approved_quantity": null
    },
    {
      "sequence_number": 2,
      "event_type": "recommendation_approved",
      "review_status": "approved",
      "actor": "Anish Paudyal",
      "recommended_reorder_quantity": 19,
      "approved_quantity": 24
    }
  ]
}
```

The actual response also includes event, recommendation, and decision UUIDs;
aware UTC timestamps; and explicit nullable actor, decision, quantity, and note
fields. Swagger UI documents the complete response schema and 200, 404, and 422
behavior.

The immutable recommendation snapshot preserves calculation evidence, the
review aggregate answers the current state, and audit events record the two
successful workflow facts in order. The aggregate remains the current-state
source of truth; events are not replayed to rebuild it, so this is audited state
storage rather than full event sourcing.

In memory mode, history is lost on restart and is not shared between
applications. In PostgreSQL mode, history is durable across application restart
and shared by applications using the same database.

The actor remains caller supplied, unauthenticated, unverified, and potentially
spoofable. Events are not cryptographically signed, hash chained, tamper
evident, externally published, or protected from privileged direct storage
modification. This is not a production compliance ledger.

## Contribution Rule

All meaningful work starts with a scoped issue, is implemented on a task branch,
and is reviewed before merge. No contributor, human or automated, should merge
directly into `main` without the required review.

## Phase 5 Evaluation Status

Phase 5 has an owner-accepted `Proceed` decision under Issue #50. The governed
`phase5-synthetic-v1` evaluation exercises 11 deterministic stockout/reorder
scenarios covering cutoff behavior, observation-count lookback, recorded zero
demand, negative available inventory, zero lead time, shortage boundaries, and
whole-unit `ROUND_CEILING` recommendations.

All 11 scenarios passed with zero expected-output, evidence-preservation,
rounding, or status-invariant failures. Two independent evaluation runs were
byte-identical, and the complete PostgreSQL-backed repository suite passed 488
tests with zero skips.

This establishes deterministic policy conformance for the governed scenarios.
It does **not** establish calibrated stockout probability, learned risk,
real-world recommendation accuracy, economic optimality, service-level
improvement, or cost savings. See
`docs/05-evaluation/phase-5-stockout-reorder-evaluation.md` and
`docs/12-phase-reviews/phase-5-review.md` for the governed evidence and accepted
limitations.
