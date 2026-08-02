# ADR-0004: Co-locate Recommendation Workflow State and Audit Events

- Status: Proposed
- Date: 2026-08-01
- Decision owners: Anish Paudyal
- Related issues: #28
- Related pull requests: The pull request implementing issue #28
- Supersedes: None
- Superseded by: None

## Context

OpsMind stores an immutable reorder-recommendation snapshot and its current
review state in a process-local workflow repository. Issue #28 adds an ordered
history containing a creation event and, when a terminal decision succeeds, an
approval or rejection event.

The central consistency requirement is:

```text
workflow state change + matching audit event append
-> both succeed together or neither succeeds
```

A review without its corresponding event, or a terminal event without the
matching terminal review state, would make both current-state and historical
answers unreliable. The current implementation has no database transaction,
so the in-memory boundary and lock must preserve this invariant.

## Decision drivers

- Atomic consistency between current review state and audit history
- Preservation of the existing pure transition functions
- Deterministic append-only ordering
- Compatibility with idempotent terminal retries
- Per-application isolation
- Clear migration to transactional persistence
- Minimal operational and dependency complexity
- Explicit security and audit limitations
- Reviewability and learning value

## Considered options

1. **Keep only the current review aggregate.** This answers the current state
   but cannot provide an ordered history of creation and terminal decisions.
2. **Perform route-level dual writes.** A route could update the workflow and
   then append through another boundary, but a failure between writes could
   leave state and history inconsistent. Routes would also own business
   consistency that belongs below HTTP orchestration.
3. **Create an independently coordinated audit repository.** This separates
   storage concerns superficially, but two in-memory repositories have no
   shared transaction and could succeed or fail independently.
4. **Co-locate review state and immutable audit streams in the existing
   workflow repository.** One process-local lock can protect validation,
   transition, event construction, and both storage updates.
5. **Adopt full event sourcing.** Events could become the source of truth and
   rebuild aggregates through replay, but replay, projections, versioning, and
   event migration are unnecessary for the bounded two-step workflow.
6. **Introduce PostgreSQL immediately.** A database transaction would provide
   durable atomicity, but persistence, migrations, deployment, and operational
   design are outside issue #28.

## Decision

The existing `RecommendationWorkflowRepository` owns both current review state
and each review's immutable ordered audit-event tuple.

- Review creation, approval, rejection, and their matching event append occur
  inside one repository operation under one process-local lock.
- Routes provide candidate review, decision, and event identifiers but do not
  perform independent state and event writes.
- Pure review-transition functions continue to own state rules.
- Pure audit-event factories derive event facts only from the immutable review
  aggregate and receive UUIDs and timestamps as inputs.
- Audit events remain separate frozen, slotted domain objects rather than
  becoming mutable fields inside the review aggregate.
- Sequence numbers are local to a recommendation and are authoritative for
  ordering; timestamps are evidence but may be equal.
- Successful first writes append one event. Identical terminal retries append
  nothing, and conflicts append nothing.
- The read API exposes history only. No supported event create, update, delete,
  correction, replay, or publication operation exists.

This is audited state storage, not event sourcing. The current review aggregate
remains the source of truth for current state; the event stream is not replayed
to construct it.

## Rationale

The consistency rule can be enforced without a new dependency by keeping the
two related in-memory structures behind the existing workflow boundary and its
`RLock`. Event construction occurs before prepared state is committed, so a
validation or factory failure changes neither structure. A successful terminal
transition replaces the immutable review and appends a new immutable tuple
while the lock excludes competing writers.

Separate event domain objects preserve append-only historical facts without
making the current aggregate responsible for storing a mutable collection.
Keeping transition and event factories pure makes the rules deterministic,
directly testable, and reusable by a future persistence adapter.

## Consequences

### Positive

- Current state and history remain mutually consistent through supported APIs.
- One lock provides deterministic process-local atomicity and concurrency.
- Immutable tuples prevent callers from mutating stored event order or content.
- Idempotent retries retain original decision and event identity.
- HTTP routes remain thin and existing review responses remain compatible.
- No dependency, cloud resource, or additional service is introduced.
- The boundary maps naturally to a later relational transaction.

### Negative

- The workflow repository now owns two related in-memory structures and must
  validate their consistency.
- Every workflow write must supply a candidate event identifier even when an
  identical retry ultimately ignores it.
- Process-local atomicity does not survive crashes and does not coordinate
  multiple workers.
- Direct memory inspection or mutation could bypass supported append-only APIs.

### Neutral

- Actor values remain caller supplied, unverified, and potentially spoofable.
- History is lost on process restart.
- The stream contains only successful creation and terminal-transition facts.
- Recommendation calculation and operational source data remain unchanged.

## Security, operations, cost, and learning impact

- **Security:** Events contain no credentials, request headers, IP addresses,
  authentication claims, or private infrastructure data. They do not prove an
  actor's identity.
- **Operations:** History is isolated per application process, is not shared
  across workers, and has no backup, retention, recovery, or external delivery.
- **Cost:** The implementation adds only bounded in-process memory use and no
  service, database, queue, or cloud cost.
- **Learning:** The boundary demonstrates atomic consistency and append-only
  modeling while keeping the limitations of in-memory coordination explicit.

## Risks and mitigations

- **State changes without an event:** construct and validate the event before
  committing prepared review and history state under the lock.
- **Duplicate events on retry:** detect unchanged aggregate identity and return
  the stored review before constructing or appending an event.
- **Conflicts append history:** let pure transitions raise before event creation
  or storage preparation.
- **Timestamp ties reorder history:** order exclusively by contiguous sequence
  numbers starting at one.
- **Mutable history leaks:** store and return tuples of frozen event objects.
- **History is overstated as compliance evidence:** document that it is not
  durable, cryptographically signed, hash chained, tamper-evident, or certified.
- **Repository responsibility grows:** keep audit behavior limited to this
  workflow and reconsider the boundary when transactional persistence arrives.

## PostgreSQL migration considerations

A later PostgreSQL adapter can store review aggregates and audit events in
separate tables while preserving the same repository boundary. One database
transaction should lock or version the review row, apply the transition, insert
the next per-review sequence, validate uniqueness, and commit both changes.
Recommended constraints include a unique event ID and a unique
`(recommendation_id, sequence_number)` pair.

Migration must define how existing process-local records are handled; the
current data is intentionally ephemeral and has no durable source to migrate.
Multi-worker consistency, retention, authorization, actor identity, and
tamper-evidence require separate reviewed decisions. Event replay is not
required merely to adopt transactional storage.

## Validation

Validate with direct invariant and factory tests; repository creation,
transition, failure, retry, conflict, isolation, ordering, and deterministic
concurrency tests; API and OpenAPI tests; normal and reverse-order complete
suites; strict typing; Ruff; coverage; governance checks; protected-file hash
comparison; and artifact review.

## Reconsideration triggers

- Workflow state becomes durable in PostgreSQL or another transactional store.
- Multiple application workers must share review state and history.
- Authentication or authorization introduces trusted actor identities.
- Compliance requirements demand retention, access controls, tamper evidence,
  signatures, hash chains, or independently governed audit storage.
- Workflows gain reopening, reversal, or more than one terminal decision.
- Events must be published externally or consumed asynchronously.
- Rebuilding current state through event replay becomes a demonstrated need.

## Implementation notes

- Event streams contain sequence 1 for creation and sequence 2 for the one
  successful terminal decision.
- Failed attempts, reads, conflicts, and retries are not events.
- The existing application factory continues to inject one workflow repository
  per application instance; no new dependency-injection mechanism is needed.
- ADR-0004 remains Proposed until the repository owner explicitly accepts it
  through review.

## References

- [ADR-0000: Use Architecture Decision Records](0000-use-architecture-decision-records.md)
- [ADR-0003: Select Backend Application Structure](0003-select-backend-application-structure.md)
- [Architecture Decision Record index](README.md)
- [Repository README](../../../README.md)
- [Contribution guide](../../../CONTRIBUTING.md)
- [Current project status](../../09-status/current-status.md)
- GitHub issue #28: Implement append-only recommendation audit history API
