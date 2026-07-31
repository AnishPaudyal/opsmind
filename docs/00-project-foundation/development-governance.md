# Development Governance

Last updated: 2026-07-30

## Governance Objective

The development system should make scope, decisions, evidence, and responsibility
visible without creating process that is heavier than the project.

## Authority and Sources of Truth

Use the following order when instructions conflict:

1. Repository security and contribution rules
2. Approved roadmap and phase review
3. Accepted architecture decision records
4. The linked issue and its acceptance criteria
5. Pull-request discussion
6. Temporary chat or working notes

Durable decisions must move from chat into the repository.

## Work Hierarchy

- Roadmap phases define sequence and readiness.
- Milestones group outcomes within a phase.
- Issues define reviewable units of work.
- Pull requests implement one coherent issue or tightly related issue set.
- Decision records preserve long-lived technical choices.

## Change Workflow

`issue -> readiness review -> branch -> implementation -> validation -> pull
request -> review -> merge -> documentation and phase evidence`

## Review Requirements

Human review is required before merge. Additional scrutiny is required for:

- Authentication or authorization changes
- Data deletion, retention, or migration
- Cloud permissions and public exposure
- Model behavior affecting recommendations
- Major dependencies or architecture boundaries
- History-rewriting Git operations

## AI-Assisted Development

Codex may:

- Inspect the repository and linked issue.
- Implement scoped changes.
- Run checks and report evidence.
- Prepare commits, push task branches, and open pull requests when authorized.
- Respond to review feedback on the same branch.

Codex may not:

- Merge into `main`.
- Introduce unapproved scope.
- Store credentials or private data.
- Treat chat statements as a substitute for durable project documentation.
- Claim tests, deployments, or controls that were not actually verified.

## Phase Gates

A phase review records one of three outcomes:

- Proceed: exit criteria are satisfied.
- Revise: targeted work remains before proceeding.
- Stop: assumptions or constraints require a roadmap change.

Application implementation and AWS work remain closed until their corresponding
phase gates are approved.
