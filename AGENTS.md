# Repository Instructions for Codex

These instructions govern AI-assisted work in the OpsMind repository.

## Current Phase

Phase 7 — testing, security, and observability hardening — is the Current formal
gate on canonical `main`.

The repository owner accepted the Phase 7 hardening plan under Issue #54.

The repository owner accepted the Phase 7A testing and coverage hardening result
under Issue #56 on 2026-08-07, including the 95.00% combined coverage gate,
documented residual-risk treatment, and Phase 7 boundaries.

PR #57 is approved for finalization and merge preparation.

The reviewed Phase 7A feature commit
`2d8425d243e8237046b403b060faa4f8e0cb3b6d` passed both required GitHub-hosted
pull-request checks before owner acceptance.

This branch is now limited to Issue #56 finalization:

- durable owner-acceptance documentation;
- validation and diff hygiene;
- staging and commit verification;
- pull-request CI revalidation;
- merge preparation.

Any acceptance/finalization commit must pass the required GitHub CI again before
merge.

Do not begin on this branch:

- observability/readiness implementation;
- ADR-0006 or trusted-principal implementation;
- authentication or authorization behavior;
- request/correlation-ID middleware;
- AWS or cloud deployment;
- production monitoring/alerting;
- HA/DR;
- production secret-store integration;
- external ordering;
- Phase 8 work.

After PR #57 is revalidated and merged, the accepted Phase 7 sequence continues
with observability/readiness through a separately governed issue/task branch,
then ADR-0006, then security implementation only after ADR-0006 repository-owner
acceptance, and finally the integrated Phase 7 evaluation/review.
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
