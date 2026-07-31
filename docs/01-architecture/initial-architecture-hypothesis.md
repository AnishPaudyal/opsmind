# Initial Architecture Hypothesis

Last updated: 2026-07-30

This document is a starting hypothesis, not an implemented-system description.
It will be refined before application scaffolding begins.

## Local Architecture

The first implementation is expected to contain:

- A Next.js web application for planner workflows
- A FastAPI service for product, forecast, risk, recommendation, and decision APIs
- PostgreSQL for transactional and audit data
- Background processing only when synchronous work no longer meets a measured
  requirement
- Docker Compose for a reproducible local environment

## Primary Data Flow

`web client -> API -> transactional data -> forecast and risk logic ->
recommendation -> human decision -> audit record`

## Initial Boundaries

- Product and demand records are authoritative inputs.
- Forecast outputs are versioned estimates, not facts.
- Reorder recommendations combine measured data, forecast output, and explicit
  business rules.
- Human decisions are stored separately from recommendations.
- Audit records retain the evidence needed to reconstruct a decision.

## Cloud Direction

After local validation, a reviewed AWS design may map the system to:

- Managed networking and identity controls
- Container hosting for web and API workloads
- Managed PostgreSQL
- Object storage for approved datasets and artifacts
- Centralized logs, metrics, traces, and alerts
- Managed secret storage
- Infrastructure as code and controlled deployment workflows

Exact AWS services will be selected during the cloud-design phase based on cost,
security, operations, and learning value.

## Key Architecture Questions

- Which actions require synchronous responses?
- What audit data must remain immutable?
- How will authorization separate planners, reviewers, and operators?
- What forecast latency and data volume justify background processing?
- How will model and rule versions be tied to recommendations?
- What recovery objectives are justified for a portfolio environment?

## Constraint

No architecture diagram or document should imply that a planned component is
already implemented, deployed, secured, or production-ready.
