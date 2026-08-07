# Repository Instructions for Codex

These instructions govern AI-assisted work in the OpsMind repository.

## Current Phase

Phase 6 — decision approval, rejection, and audit history — is the Current
formal gate on canonical `main` until Issue #52 merges.

Issue #52 governs the formal Phase 6 evaluation and review on branch
`feat/phase-6-decision-review-audit-evaluation`.

The repository owner accepted the Phase 6 evaluation design and accepted the
Phase 6 review with decision `Proceed` on 2026-08-07.

Phase 6 technical and governance gates are passed. This branch is now limited to
Issue #52 finalization: documentation consistency, validation hygiene, staging,
commit, pull-request review, CI, and merge preparation.

In the merged repository state:

- Phase 6 is Complete;
- Phase 7 is Current.

Do not begin Phase 7 implementation on this branch. Phase 7 must begin through a
separate approved issue/task branch after Issue #52 is merged.

Authentication, authorization, actor verification, cryptographic audit
integrity, purchase-order execution, external ordering, Phase 7 hardening, API
containerization, AWS, deployment, and production-readiness implementation are
outside Issue #52.
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
