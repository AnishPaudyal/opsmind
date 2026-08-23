# Repository Instructions for Codex

These instructions govern AI-assisted work in the OpsMind repository.

## Current Phase

Phase 8 — cloud deployment and product delivery — is the Current formal gate.

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

The repository owner accepted ADR-0006 on 2026-08-08. PR #61 was squash-merged
as `3e8b0a78344cc0164a35c268fa119d9c5321de50`, Issue #60 is closed, and the
accepted tree exactly matches the reviewed ADR branch tree.

Issue #62 security implementation is complete:

- PR #63 was squash-merged as
  `575fd03eab2ebf5dc221ae1d52e44802ddaf7970`;
- Issue #62 is closed;
- the canonical merge tree exactly matches the reviewed feature tree;
- post-merge Python-quality and repository-governance checks passed.

The repository owner accepted the integrated Phase 7 `Proceed` review on
2026-08-09. PR #65 was squash-merged as
`984826a9fc1c16c0a7a1a30006cad120f301cd8d`, Issue #64 is closed, the canonical
tree exactly matches the reviewed acceptance tree, and both post-merge
workflows passed. Phase 7 is Complete.

The repository owner accepted ADR-0007 on 2026-08-10. PR #67 was squash-merged
as `733f405ef89c38a2b09b95587bdbd77b938ee853`, Issue #66 is closed, and the
canonical tree exactly matches the accepted design tree.

Issue #68 Phase 8A containerization is complete. PR #69 was squash-merged as
`631b8a2d1c9696b374f2b96b0295190bbca4a3bf`, Issue #68 is closed, the
canonical tree exactly matches the reviewed feature tree, and all three
post-merge workflows passed.

Issue #70 Phase 8B zero-cost cloud backend is complete. PR #72 merged the
repository-controlled foundation as
`c52dfedc2ce4019b64dd1e0333f28cbef77b8a82`; PR #75 merged the reviewed Render
Blueprint as `ba2b4284e24d3a440e58bce4d6337a9ad008eade`; and Cloud release run
`31738097577` successfully published, migrated, deployed, and smoke-tested the
immutable application image for revision
`1f7de97e593182bd79ff767de220532b8301acff`. PR #76 merged the accepted
operational closeout as `77b4f1d8981fe998fe55a8bf6e3dea2f99e02dfd`, and Issue
#70 is closed.

The repository owner accepted the Issue #77 Phase 8C authenticated frontend
and full-stack product gate on 2026-08-13. PR #79 merged Batch 1 as
`3a49eedc7e842998a49ec2c4393096973d828f11`, and PR #80 merged Batch 2 as
`a3fc7b2c6ae19d07acb8e63baf1b87784dd1a47d`. Batch 1 and Batch 2 are
Complete. The repository owner authorized Batch 3 on 2026-08-16 and authorized
Substep 1 for credential-free Cloudflare Terraform, CI, runbook,
security-header, and repository preparation. PR #82 squash-merged that
foundation as `7526f6eab78ef685669b3246e4a4487a83d1c331`, so Substep 1 is
Complete. Substep 2 completed its Cloudflare Free, repository-scoped GitHub
App, least-privilege token, HCP workspace, and credentialed plan verification.
Substep 3 is Complete. Its first apply failed safely before project creation
with Cloudflare error `8000066`; PR #84 corrected the equal `fail_open`
contract, and the corrected apply created exactly one dormant Pages project.
The provider origin is `https://opsmind-app.pages.dev`, but no Pages deployment
exists, and a later HCP plan verified no drift. Issue #77 remains open;
PR #86 merged the repository-only Substep 4 exact-origin packet as
`18d29c92dd0070faad8038c88d159d533ad353e8`. HCP run
`run-UXDXd9rKDhe74ocK` verified the source as zero additions, one in-place SPA
change, and zero destroys or replacements, but remains unapplied at Pending
confirmation. Substep 4 is Complete. The owner has authorized only the
repository grant preparation for Substep 5; the human operator has not been
created or selected, its public user ID is not in HCP, and no operator grant is
live. Substeps 6–8 remain unauthorized.
Continuing an established Phase 8B release still requires the documented
owner-controlled environment approval and secret boundaries.

Do not begin without separate authorization:

- Render, Neon, ZITADEL, HCP Terraform, GHCR, Cloudflare, AWS, or other cloud
  resource creation/configuration;
- credentials, account connections, identity-provider provisioning, or secret
  storage;
- a cloud-release dispatch, HCP Terraform apply, migration, deployment, or
  `render.yaml` addition;
- application-managed users, sessions, organizations, or tenants;
- Phase 8C Batch 3 Substep 5 owner/operator, HCP variable, plan/apply, or live
  grant work; Substeps 6–8; live frontend delivery; LocalStack; Phase 8D–8E; or
  production-readiness work;
- Phase 9 data pipelines, Phase 10 MLOps, or Phase 11 LLM/RAG/LangGraph work.

Phase 8B and Phase 8C Batches 1 and 2 are Complete, but Phase 8 remains
Current. The Phase 8C gate is Accepted, Phase 8C is not Complete, and Batch 3
Substeps 1 through 4 are Complete. Substep 5 is In Progress only for its
reviewed repository operator-grant preparation; do not begin its owner/HCP/live
work, Substeps 6–8, or any broader live-provider mutation until their separate
owner authorizations exist.

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
