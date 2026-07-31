# Technology Selection Principles

Last updated: 2026-07-30

## Decision Principles

Technology is selected to solve a defined problem and produce useful learning
evidence. A tool is not justified only because it is popular or appears in a job
description.

Prefer choices that:

- Support the current vertical slice.
- Can be run and understood locally.
- Have strong documentation and ecosystem support.
- Make testing, security, and operations practical.
- Transfer to relevant job environments.
- Can be replaced without rewriting unrelated parts of the product.

## Initial Direction

| Need | Initial direction | Reason |
| --- | --- | --- |
| Backend API | Python and FastAPI | Strong typing and validation with ML/data alignment |
| Transactional data | PostgreSQL | Mature relational constraints and broad AWS path |
| Data access | SQLAlchemy and Alembic | Explicit models and reproducible migrations |
| Web workflow | Next.js and TypeScript | Typed full-stack UI ecosystem |
| Local environment | Docker Compose | Reproducible service orchestration |
| Backend quality | pytest, Ruff, mypy | Fast feedback across behavior, style, and types |
| Cloud target | AWS | Direct alignment with project and certification goals |
| Infrastructure | Terraform, subject to review | Portable, reviewable infrastructure as code |

## Deferred Technologies

The following are intentionally deferred until a concrete requirement appears:

- Kafka or Kinesis for event streaming
- Spark or AWS Glue for distributed processing
- dbt for analytical transformations
- MLflow or a managed equivalent for model lifecycle
- Kubernetes for orchestration
- Vector databases and retrieval-augmented generation
- Agent frameworks and automated decision execution

## Entry Conditions for a New Technology

A proposal should explain:

- The problem it solves now
- Simpler alternatives considered
- Operational and security burden
- Cost implications
- Exit or replacement strategy
- The evidence that will show whether the choice worked
