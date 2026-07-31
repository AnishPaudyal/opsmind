# Architecture Decision Records

## Purpose

An Architecture Decision Record (ADR) is a durable record of a significant
technical or architectural decision, the context in which it was made, and the
consequences accepted with it. OpsMind uses ADRs to make long-lived decisions
reviewable, discoverable, and understandable after the original issue or pull
request is closed.

ADRs capture decisions that shape the system across backend, data, cloud,
machine learning, AI, security, observability, and operations. They preserve
the rationale and constraints needed for implementation, learning, onboarding,
and future reconsideration.

## When an ADR is required

Create an ADR for a significant, durable choice such as:

- Programming-language or runtime selection
- Framework selection
- Major repository, package, component, or service boundaries
- Database or storage technology
- Messaging or event architecture
- Deployment model
- Security architecture
- Significant data, ML, AI, or observability design choices
- Decisions that are difficult or expensive to reverse

## When an ADR is not required

An ADR is normally unnecessary for:

- Routine bug fixes
- Formatting changes
- Small refactors that preserve the architecture
- Dependency patch updates without design impact
- Temporary experiment notes
- Task-specific implementation details already governed by an accepted ADR

## Location and filename convention

Store ADRs at:

```text
docs/01-architecture/decisions/NNNN-short-kebab-case-title.md
```

Use four-digit sequential numbering:

```text
0000
0001
0002
...
```

The numbering and naming rules are:

- `0000` records adoption of the ADR process.
- The next technical decision is `0001`.
- Assign a number when ADR work begins.
- Never reuse a number.
- Never renumber an existing ADR.
- Retain Rejected, Deprecated, and Superseded ADRs in the repository.
- Use a concise kebab-case title in the filename.
- Coordinate parallel work before assigning a number.
- Use the highest existing ADR number to determine the next available
  sequential number.
- Document reserved but abandoned numbers instead of silently reusing them.

## Supported statuses

- **Proposed**: Under review and not yet authoritative.
- **Accepted**: Approved by the repository owner and governing related work.
- **Rejected**: Considered but explicitly not selected.
- **Deprecated**: Retained for history but no longer recommended for new work.
- **Superseded**: Replaced by a later ADR that governs the decision.

Relationship metadata may be recorded as:

```text
Supersedes: ADR-NNNN
Superseded by: ADR-NNNN
```

## Lifecycle

1. Identify a material decision.
2. Select the next available ADR number.
3. Create the ADR from [template.md](template.md).
4. Mark it Proposed during review.
5. Review it through the normal branch and pull-request workflow.
6. Mark it Accepted only when the repository owner approves the decision.
7. Retain Rejected, Deprecated, and Superseded records.
8. Update this index whenever an ADR status or relationship changes.

ADRs do not replace implementation documentation, runbooks, diagrams, or
detailed design documents. Issues describe work to perform, pull requests
review changes, and ADRs preserve the durable decision and rationale.
Contributors and AI agents must not invent material architectural conventions
when an ADR is required.

## ADR index

| Number | Title | Status | Date | Related issue |
| --- | --- | --- | --- | --- |
| [ADR-0000](0000-use-architecture-decision-records.md) | Use Architecture Decision Records | Accepted | 2026-07-31 | #6 |
| [ADR-0001](0001-select-python-toolchain.md) | Select Python Toolchain | Accepted | 2026-07-31 | #5 |
