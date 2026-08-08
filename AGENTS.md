# Repository Instructions for Codex

These instructions govern AI-assisted work in the OpsMind repository.

## Current Phase

Phase 7 — testing, security, and observability hardening — is the Current formal
gate on canonical `main`.

The repository owner accepted the Phase 7 hardening plan under Issue #54.
Issue #56 is the active first child workstream on branch
`test/phase-7-testing-coverage-hardening`.

This branch is authorized only for Phase 7A testing and coverage hardening,
including:

- reproducible statement/branch coverage evidence;
- risk-based test-gap analysis;
- focused regression tests for meaningful uncovered behavior;
- TestClient warning resolution or bounded disposition;
- an evidence-based coverage-gate decision;
- testing/coverage documentation and CI updates justified by that decision.

Do not implement on this branch:

- authentication or authorization behavior;
- ADR-0006 or trusted-principal implementation;
- request/correlation-ID middleware;
- application logging or readiness behavior;
- observability runtime dependencies;
- AWS, API containerization, cloud deployment, production monitoring/alerting,
  HA/DR, production secret-store integration, external ordering, or Phase 8 work.

After the Phase 7A workstream is accepted and merged, the accepted Phase 7
sequence continues with observability/readiness, then ADR-0006, then security
implementation only after ADR-0006 owner acceptance, and finally the integrated
Phase 7 evaluation/review.
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
