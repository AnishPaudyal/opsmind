# OpsMind - Cloud-Native Supply Chain Decision Intelligence Platform

OpsMind is a production-oriented portfolio project for building and explaining a
cloud-native supply-chain decision-intelligence platform. It is designed to
demonstrate backend engineering, data engineering, machine learning, cloud
architecture, DevOps, security, observability, and responsible AI through one
coherent product.

## Current Status

Phase 0, project definition and governance, is complete. The repository is now
in Phase 1, repository and development foundation.

This repository does not yet contain:

- Application code
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

## Contribution Rule

All meaningful work starts with a scoped issue, is implemented on a task branch,
and is reviewed before merge. No contributor, human or automated, should merge
directly into `main` without the required review.
