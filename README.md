# OpsMind - Cloud-Native Supply Chain Decision Intelligence Platform

OpsMind is a production-oriented portfolio project for building and explaining a
cloud-native supply-chain decision-intelligence platform. It is designed to
demonstrate backend engineering, data engineering, machine learning, cloud
architecture, DevOps, security, observability, and responsible AI through one
coherent product.

## Current Status

Phase 0, project definition and governance, is complete. The Phase 1 repository,
Python, quality, and CI foundations are established. Phase 2 has begun with the
reviewed FastAPI backend foundation from issue #14 and the first bounded
supply-chain business API from issue #16.

The current backend can create and retrieve products and record one in-memory
inventory position for each product. This repository does not yet contain:

- Persistence or migrations
- Authentication or authorization
- Demand history, forecasting, risk, or reorder recommendations
- Cloud infrastructure
- Deployed AWS resources
- Trained machine-learning models
- Production data

Those capabilities will be introduced only through reviewed issues and phase
gates.

## First Product Slice

The first end-to-end workflow will be:

1. Load product and demand-history data.
2. Produce a demand forecast.
3. Estimate stockout risk.
4. Generate a reorder recommendation with supporting evidence.
5. Let a user approve or reject the recommendation.
6. Record the decision and its audit history.

## Planned Technical Direction

The initial local stack is expected to use:

- Python and FastAPI
- PostgreSQL, SQLAlchemy, and Alembic
- Next.js and TypeScript
- Docker Compose
- pytest, Ruff, mypy, and frontend checks

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
- [docs/01-architecture](docs/01-architecture) contains the initial architecture
  hypothesis.
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

The API exposes an unversioned deterministic process-health endpoint and five
product and inventory operations under the configured business prefix:

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/health` | Report process health. |
| `POST` | `/api/v1/products` | Create a normalized product. |
| `GET` | `/api/v1/products` | List products in normalized-SKU order. |
| `GET` | `/api/v1/products/{product_id}` | Retrieve one product. |
| `PUT` | `/api/v1/products/{product_id}/inventory` | Set or replace inventory. |
| `GET` | `/api/v1/products/{product_id}/inventory` | Retrieve inventory. |

Application settings use the `OPSMIND_` environment-variable prefix. Supported
overrides are:

- `OPSMIND_APPLICATION_NAME`
- `OPSMIND_SERVICE_NAME`
- `OPSMIND_ENVIRONMENT` (`local`, `test`, `staging`, or `production`)
- `OPSMIND_DEBUG`
- `OPSMIND_API_V1_PREFIX`

The default service is `opsmind-api`, the default environment is `local`, debug
mode is disabled, and the default business prefix is `/api/v1`. The application
does not load a repository `.env` file implicitly.

`GET /health` reports only that the API process can serve a request. It does not
claim readiness for a database, AWS resource, external service, or product
workflow. No such dependency is configured by this foundation.

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

Products and inventory are stored only in an isolated in-memory repository for
each application instance. Restarting the process loses all product and
inventory data. There is no database, migration, authentication, demand-history,
forecasting, risk, reorder, approval, frontend, Docker, AWS, or deployment
capability in this milestone.

## Contribution Rule

All meaningful work starts with a scoped issue, is implemented on a task branch,
and is reviewed before merge. No contributor, human or automated, should merge
directly into `main` without the required review.
