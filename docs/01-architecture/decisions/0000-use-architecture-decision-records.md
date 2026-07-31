# ADR-0000: Use Architecture Decision Records

- Status: Accepted
- Date: 2026-07-31
- Decision owners: Anish Paudyal
- Related issues: #6
- Related pull requests: The pull request implementing issue #6
- Supersedes: None
- Superseded by: None

## Context

OpsMind is intended to be a long-lived, learning-focused, and
production-oriented system. Its planned scope includes backend engineering,
data systems, cloud architecture, machine learning, AI, security, and
operational decisions. These areas will produce choices whose rationale must
remain understandable as the repository and its contributors evolve.

Issues and pull requests organize work and review changes, but alone they may
not preserve why an option was chosen, which alternatives were rejected, which
constraints mattered, what consequences were accepted, or when a decision
should be revisited. OpsMind needs a durable, low-overhead record that remains
close to the implementation and available throughout the project lifecycle.

## Decision drivers

- Version-controlled history
- Reviewability
- Low operational overhead
- Offline availability
- Durability
- Discoverability
- Traceability to issues and pull requests
- Learning and interview value
- Onboarding value
- Auditability
- Compatibility with the repository workflow

## Considered options

1. **No formal decision records.** This minimizes process but loses durable
   rationale and makes repeated or inconsistent decisions more likely.
2. **Decisions recorded only in issues and pull requests.** This provides
   discussion history but scatters authoritative rationale across transient
   work records and review threads.
3. **Decisions recorded only in general architecture documents.** This keeps
   architecture content together but makes decision status, alternatives,
   consequences, and supersession harder to track consistently.
4. **External decision-management software.** This could add specialized
   search or reporting, but introduces cost, account dependencies, operational
   overhead, and separation from repository history.
5. **Repository-managed Markdown ADRs.** This keeps decisions versioned,
   reviewable, linkable, offline, and close to related implementation with
   minimal tooling.

## Decision

OpsMind will maintain Markdown Architecture Decision Records under:

```text
docs/01-architecture/decisions/
```

ADRs will follow the numbering, naming, status, lifecycle, retention, and index
rules documented in the [ADR process index](README.md).

## Rationale

Repository-managed Markdown ADRs are version controlled, reviewed through pull
requests, stored beside the implementation, and available offline. They have
low cost and low tool complexity, are easy to link from issues and technical
documents, and provide durable evidence for learning, interviews, onboarding,
and audits. This approach fits the repository's existing issue-first,
review-based workflow without adding an external system.

## Consequences

### Positive

- Design rationale remains preserved with repository history.
- Reviews can evaluate alternatives and consequences, not only implementation.
- New contributors can understand why the system has its current shape.
- Reconsideration triggers make future review more explicit.
- Project storytelling and interview evidence become stronger.
- AI-assisted work gains a consistent source of governing decisions.

### Negative

- Authors and reviewers take on additional process and maintenance.
- ADRs can become stale if related changes do not update them.
- Parallel work must coordinate number assignment.
- The process may be overused for minor decisions that do not need an ADR.

### Neutral

- ADRs supplement rather than replace other documentation.
- Rejected and superseded records remain visible as historical evidence.
- ADR acceptance and supersession continue to require human judgment.

## Risks and mitigations

- **Stale ADRs:** Review related ADRs whenever architecture changes.
- **Excessive process:** Require ADRs only for material decisions.
- **Duplicate numbers:** Inspect the index and coordinate before creation.
- **Documentation drift:** Update ADR status and references in the same pull
  request as material changes.
- **AI-generated unsupported assumptions:** Require evidence and human review
  before acceptance.

## Validation

The ADR process is validated when ADR `0000`, the template, and the process
index exist; governance documents link to the system; the next material
decision can use ADR `0001`; and all repository checks pass.

## Reconsideration triggers

- The repository becomes a large multi-team monorepo.
- ADR volume becomes difficult to navigate.
- Automated ADR tooling becomes necessary.
- External compliance mandates another system.
- Markdown-based records no longer meet search, reporting, or governance needs.

## Implementation notes

- ADR `0001` is reserved for the Python toolchain decision in issue #5 after
  issue #6 is merged.
- Issue #5 remains blocked until this ADR system is merged.
- ADRs must follow the normal branch, review, and pull-request workflow.

## References

- [Repository instructions](../../../AGENTS.md)
- [Contribution guide](../../../CONTRIBUTING.md)
- [Development governance](../../00-project-foundation/development-governance.md)
- [Documentation and learning system](../../00-project-foundation/documentation-and-learning-system.md)
- [Initial architecture hypothesis](../initial-architecture-hypothesis.md)
