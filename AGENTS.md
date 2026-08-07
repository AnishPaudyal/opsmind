# Repository Instructions for Codex

These instructions govern AI-assisted work in the OpsMind repository.

## Current Phase

The repository owner accepted the Phase 4 forecasting-baseline and evaluation
review under Issue #48 on 2026-08-06. This branch is limited to finalizing that
accepted Issue #48 work and preparing it for review and merge.

Phase 4 is Complete in the merged repository state. Phase 5, stockout risk and
reorder recommendations, becomes the next formal phase after the Issue #48 pull
request merges.

Do not begin Phase 5 implementation on this branch. Phase 5 work must start
through a separately approved issue and task branch. Phase 6 formal completion,
Phase 7 hardening, API containerization, AWS, deployment, and
production-readiness work remain outside the current authorization.

## Required Context

Before starting work:

1. Read `README.md`, `ROADMAP.md`, and the relevant issue.
2. Read the documentation for the affected phase or subsystem.
3. Check the working tree and preserve changes that are outside the task.
4. State assumptions when the issue leaves a material decision open.

## Work Rules

- Keep changes within the issue's stated scope.
- Prefer the repository's existing patterns over new abstractions.
- Add tests in proportion to behavioral risk.
- Update durable documentation when behavior, architecture, operations, or
  decisions change.
- Use example or synthetic data only unless an issue explicitly approves a
  governed data source.
- Keep generated artifacts and local environment files out of version control.
- Never store secrets in source, documentation, fixtures, logs, or screenshots.

## Git and Review

- Use a short-lived branch associated with one issue.
- Use clear, focused commits.
- Run the relevant checks before requesting review.
- Include validation evidence and documentation impact in the pull request.
- Do not rewrite shared history.
- Do not push directly to `main` after the initial empty-repository bootstrap.
- Do not merge a pull request. Final merge authority remains with the repository
  owner.

## Architecture and Dependency Changes

Architecture, security boundaries, data contracts, cloud services, and major
dependencies require:

- A stated problem and acceptance criteria
- Alternatives considered
- Cost, security, operations, and learning impact
- A durable decision record when the choice has long-term consequences

## Architecture Decision Records

Before making a material architectural decision, contributors and AI agents
must:

- Check the [ADR index](docs/01-architecture/decisions/README.md) for an
  existing governing decision.
- Create or update an ADR when a material decision is not already governed.
- Follow the documented numbering, naming, status, and lifecycle conventions.
- Avoid silently inventing architectural conventions or assumptions.
- Preserve repository-owner approval for accepting or superseding an ADR.

## Completion Standard

A task is complete only when:

- Acceptance criteria are satisfied.
- Relevant checks pass.
- Documentation is accurate.
- No secret or private data is introduced.
- Deferred work is recorded rather than hidden in vague TODO comments.
