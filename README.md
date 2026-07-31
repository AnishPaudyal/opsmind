# OpsMind - Cloud-Native Supply Chain Decision Intelligence Platform

OpsMind is a production-oriented portfolio project for building and explaining a
cloud-native supply-chain decision-intelligence platform. It is designed to
demonstrate backend engineering, data engineering, machine learning, cloud
architecture, DevOps, security, observability, and responsible AI through one
coherent product.

## Current Status

Phase 0, project definition and governance, is complete. The Phase 1 repository,
Python, quality, and CI foundations are established. Phase 2 has begun with the
reviewed FastAPI backend foundation from issue #14.

The backend foundation is deliberately narrow. This repository does not yet
contain:

- Supply-chain business endpoints
- Persistence or migrations
- Authentication or authorization
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

## FastAPI backend foundation

The packaged backend lives under `src/opsmind`. Start the local ASGI application
with:

```bash
uv run uvicorn opsmind.main:app --reload
```

The initial API exposes one deterministic process-health endpoint:

```text
GET /health
```

Application settings use the `OPSMIND_` environment-variable prefix. Supported
overrides are:

- `OPSMIND_APPLICATION_NAME`
- `OPSMIND_SERVICE_NAME`
- `OPSMIND_ENVIRONMENT` (`local`, `test`, `staging`, or `production`)
- `OPSMIND_DEBUG`
- `OPSMIND_API_V1_PREFIX`

The default service is `opsmind-api`, the default environment is `local`, debug
mode is disabled, and `/api/v1` is reserved for a future real business API. The
application does not load a repository `.env` file implicitly.

`GET /health` reports only that the API process can serve a request. It does not
claim readiness for a database, AWS resource, external service, or product
workflow. No such dependency is configured by this foundation.

## Contribution Rule

All meaningful work starts with a scoped issue, is implemented on a task branch,
and is reviewed before merge. No contributor, human or automated, should merge
directly into `main` without the required review.
