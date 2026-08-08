# Repository Instructions for Codex

These instructions govern AI-assisted work in the OpsMind repository.

## Current Phase

Phase 7 — testing, security, and observability hardening — is the Current formal
gate on canonical `main`.

The repository owner accepted the Phase 7 hardening plan under Issue #54.

Phase 7A testing and coverage hardening is complete:

- Issue #56 is closed;
- PR #57 is merged;
- canonical merge commit is
  `784c9055a393b3febd030ae8d9ce7d82fb110e4a`;
- the merged tree exactly matches the reviewed final Phase 7A tree
  `4f592917107dcc2c07ae1d23ecd1cc63ad6729d4`;
- the accepted 95.00% combined line-and-branch coverage regression gate remains
  in force.

Issue #58 observability/readiness is complete:

- PR #59 was squash-merged as
  `f12082db31359a734b012867267de970cabcfa1a`;
- Issue #58 is closed;
- the canonical merge tree exactly matches the reviewed feature tree;
- post-merge Python-quality and repository-governance checks passed.

Issue #60 is the active Phase 7 security-boundary investigation on branch
`docs/adr-0006-security-boundary`.

This branch is authorized only for:

- the Proposed ADR-0006 trusted-principal and authorization decision;
- minimal governance/current-state documentation;
- documentation validation and pull-request preparation.

Do not begin on this branch:

- authentication or authorization behavior;
- trusted-principal or ADR-0006 implementation;
- security implementation;
- AWS or cloud deployment;
- API containerization;
- production monitoring/alerting infrastructure;
- external metrics or tracing backends;
- HA/DR;
- backup/restore;
- production secret-store integration;
- external ordering;
- Phase 8 work;
- production-readiness approval.

Security implementation remains blocked until ADR-0006 is explicitly accepted
by the repository owner and a separate implementation issue is authorized. The
accepted Phase 7 sequence then continues with security implementation and the
integrated Phase 7 evaluation/review.
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
