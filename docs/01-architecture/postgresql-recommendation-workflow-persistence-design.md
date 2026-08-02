# PostgreSQL Recommendation Workflow Persistence Design

## Status

- Design issue: #36
- Governing decisions: ADR-0004 and ADR-0005
- Implementation status: Not implemented
- Scope: Recommendation reviews, terminal decisions, and audit events

## Objective

Persist recommendation-review workflow state and append-only audit history in
PostgreSQL while preserving the existing domain behavior, repository Protocol,
HTTP contracts, idempotent retries, and ADR-0004 atomicity requirement.

The central invariant is:

```text
workflow state change + matching audit event append
→ both commit together or neither commits
```

This design introduces durable audited state storage. It does not introduce
event sourcing. The current review aggregate remains the source of truth for
current state, and audit events are not replayed to rebuild it.

## Existing behavior to preserve

The existing `RecommendationWorkflowRepository` exposes five operations:

- `create_review`
- `get_review`
- `list_audit_events`
- `approve_review`
- `reject_review`

HTTP routes generate candidate identifiers and timestamps, but one repository
operation owns each atomic workflow write.

The pure domain functions remain authoritative for business behavior:

- `create_recommendation_review`
- `approve_recommendation`
- `reject_recommendation`
- `create_review_created_audit_event`
- `create_review_decision_audit_event`

An identical terminal retry returns the original stored review and preserves the
original decision identifier, event identifier, and decision timestamp. Changed
or opposite decisions raise `RecommendationReviewConflictError` and append
nothing.

## Persistence boundaries

PostgreSQL workflow persistence uses three tables:

1. `recommendation_reviews`
2. `recommendation_decisions`
3. `recommendation_audit_events`

SQLAlchemy rows remain internal to `opsmind.persistence.postgresql`. Repository
methods accept and return immutable domain objects. Domain modules must not
import SQLAlchemy, Psycopg, Alembic, engines, sessions, or ORM rows.

## Recommendation reviews

`recommendation_reviews` stores the immutable recommendation snapshot and the
current review status.

### Columns

- `recommendation_id`: UUID primary key
- `product_id`: UUID foreign key to `products.id`
- `unit_of_measure`: nonblank text
- `recommendation_policy`: text
- `recommendation_status`: text
- `forecast_method`: text
- `as_of_date`: date
- `lookback_observations_requested`: positive integer
- `observations_used`: positive integer
- `training_start_date`: date
- `training_end_date`: date
- `average_daily_demand`: numeric
- `lead_time_days`: nonnegative integer
- `on_hand_quantity`: nonnegative integer
- `allocated_quantity`: nonnegative integer
- `available_inventory`: integer
- `forecasted_lead_time_demand`: nonnegative numeric
- `projected_inventory_balance`: numeric
- `projected_shortage_quantity`: positive numeric
- `recommended_reorder_quantity`: positive integer
- `review_status`: `pending_review`, `approved`, or `rejected`
- `created_at`: timezone-aware timestamp
- `decision_id`: nullable UUID

PostgreSQL unconstrained `NUMERIC` is used for domain `Decimal` values so the
persistence adapter does not impose an unverified precision or scale.

### Constraints

- Product deletion is restrictive.
- `unit_of_measure` must be nonblank.
- Only actionable `reorder_recommended` snapshots may be stored.
- `lookback_observations_requested` must be positive.
- `observations_used` must be positive.
- `observations_used` cannot exceed `lookback_observations_requested`.
- `training_end_date` cannot precede `training_start_date`.
- `average_daily_demand` must be nonnegative.
- `lead_time_days` must be nonnegative.
- `on_hand_quantity` and `allocated_quantity` must be nonnegative.
- `available_inventory` must equal `on_hand_quantity -
  allocated_quantity`.
- `forecasted_lead_time_demand` must be nonnegative.
- `projected_shortage_quantity` must be positive.
- `recommended_reorder_quantity` must be positive.
- Pending reviews must have a null `decision_id`.
- Approved and rejected reviews must have a non-null `decision_id`.
- `(recommendation_id, decision_id)` references the matching decision pair.

The repository reconstructs `ReorderRecommendationReview` after reads so domain
constructors additionally verify that terminal review status matches the stored
decision type.

## Recommendation decisions

`recommendation_decisions` stores one immutable terminal decision per review.

### Columns

- `decision_id`: UUID primary key
- `recommendation_id`: UUID foreign key to `recommendation_reviews`
- `decision_type`: `approved` or `rejected`
- `decided_by`: nonblank text
- `decided_at`: timezone-aware timestamp
- `approved_quantity`: nullable integer
- `note`: nullable text

### Constraints

- `recommendation_id` is unique, allowing at most one decision per review.
- `(recommendation_id, decision_id)` is unique for same-review foreign-key
  references.
- Approved decisions require a positive `approved_quantity`.
- Approved decisions may have a null note.
- Rejected decisions require `approved_quantity` to be null.
- Rejected decisions require a nonblank note.

The rejection reason continues to be stored as the decision note so the
existing domain and API contracts remain unchanged.

## Recommendation audit events

`recommendation_audit_events` stores immutable, append-only workflow facts.

### Columns

- `event_id`: UUID primary key
- `recommendation_id`: UUID foreign key to `recommendation_reviews`
- `sequence_number`: positive integer
- `event_type`: `review_created`, `recommendation_approved`, or
  `recommendation_rejected`
- `occurred_at`: timezone-aware timestamp
- `review_status`: recorded workflow status
- `decision_id`: nullable UUID
- `actor`: nullable text
- `recommended_reorder_quantity`: positive integer
- `approved_quantity`: nullable integer
- `note`: nullable text

### Constraints

- `(recommendation_id, sequence_number)` is unique.
- `decision_id` is unique when present.
- `(recommendation_id, decision_id)` references the matching decision pair.
- `review_created` uses sequence 1 and contains no decision fields.
- `recommendation_approved` uses sequence 2, records approved status, and
  requires decision linkage, actor, and positive approved quantity.
- `recommendation_rejected` uses sequence 2, records rejected status, and
  requires decision linkage, actor, and nonblank note while approved quantity
  remains null.

Sequence number is authoritative for ordering. Timestamps are retained as
evidence but may be equal.

No repository operation updates or deletes audit events.

## Review creation transaction

Review creation executes inside one short-lived SQLAlchemy session and one
database transaction:

```text
construct valid pending review
→ construct sequence-1 review_created event
→ insert recommendation review
→ insert creation event
→ flush
→ commit
```

A duplicate review identifier is translated to
`DuplicateRecommendationReviewError`.

Any domain, mapping, constraint, flush, or commit failure rolls back both rows.
A committed review therefore cannot exist without its creation event.

## Terminal-decision transaction

Approval and rejection use the same transaction structure:

```text
begin transaction
→ SELECT review row FOR UPDATE
→ return typed not-found error when absent
→ load matching decision when present
→ load audit history in sequence order
→ reconstruct and validate immutable domain state
→ call the pure domain transition
```

### First terminal decision

When the pure transition returns a new terminal review:

```text
construct immutable decision
→ construct sequence-2 decision event
→ insert decision row
→ update review status and decision pointer
→ insert audit event
→ flush
→ commit
```

All three mutations commit together or roll back together.

### Identical retry

When the pure transition returns the original stored review:

```text
insert nothing
→ update nothing
→ append nothing
→ ignore candidate decision ID
→ ignore candidate event ID
→ ignore candidate timestamp
→ return the original stored review
```

### Conflict

When the pure transition raises `RecommendationReviewConflictError`:

```text
roll back
→ preserve stored review
→ preserve stored decision
→ preserve audit history
```

## Concurrency

Terminal operations acquire a row-level lock with
`SELECT ... FOR UPDATE`.

When approval and rejection race for the same pending review:

```text
first transaction locks the review
→ second transaction waits
→ first commits one terminal state and sequence-2 event
→ second reads the terminal state
→ second becomes an identical retry or a conflict
```

Exactly one conflicting approval/rejection pair can succeed.

The default PostgreSQL transaction isolation level plus the row lock is
sufficient because each operation transitions one review aggregate. This design
does not require table locks, advisory locks, distributed locks, Redis locks, or
serializable isolation.

Lock acquisition is always scoped to one review row, avoiding inconsistent
multi-row lock ordering.

## Read behavior

`get_review`:

- Opens a short-lived session.
- Loads the review and optional decision.
- Reconstructs immutable domain objects.
- Returns a detached domain review.
- Raises `RecommendationReviewNotFoundError` when absent.

`list_audit_events`:

- Verifies that the review exists.
- Loads events ordered by `sequence_number`.
- Reconstructs immutable domain events.
- Validates the review/history relationship.
- Returns a tuple.
- Performs no recalculation or mutation.

Operational product, inventory, and demand data are not accessed during stored
review or audit retrieval.

## Error translation

Known persistence outcomes map to existing domain errors:

- Duplicate review primary key:
  `DuplicateRecommendationReviewError`
- Missing review:
  `RecommendationReviewNotFoundError`
- Changed or opposite terminal decision:
  `RecommendationReviewConflictError`

Unexpected integrity violations after locking and domain validation indicate a
persistence invariant failure rather than an ordinary client conflict. They
must roll back and surface as internal failures without exposing SQL, database
URLs, parameters, or credentials.

## Application integration

Explicit repository injection continues to take precedence over backend
selection.

When no explicit repository is supplied:

```text
memory backend
→ in-memory operational repository
→ in-memory workflow repository

PostgreSQL backend
→ PostgreSQL operational repository
→ PostgreSQL workflow repository
```

The application creates one owned PostgreSQL engine and one shared
`SessionFactory` when either default PostgreSQL repository is required. Both
repositories receive that factory. The application disposes the engine once
during shutdown.

Separate repository operations still use separate short-lived sessions and
transactions.

## Migration

The implementation migration will use:

```text
revision = 0006_workflow_persistence
down_revision = 0005_operational_data
```

Upgrade order:

1. Create `recommendation_reviews` without its decision composite foreign key.
2. Create `recommendation_decisions`.
3. Add the matching review-to-decision composite foreign key.
4. Create `recommendation_audit_events`.
5. Create required indexes.

Downgrade order:

1. Drop `recommendation_audit_events`.
2. Drop the review-to-decision composite foreign key.
3. Drop `recommendation_decisions`.
4. Drop `recommendation_reviews`.

There is no process-local workflow data migration. Existing in-memory records
are intentionally ephemeral and have no durable source.

## Testing requirements

The PostgreSQL implementation must run against a real dedicated PostgreSQL test
database and reproduce the existing repository and API behavior.

Required coverage includes:

- Review and creation-event atomicity
- Duplicate review rollback
- Retrieval after application restart
- Shared state across application instances
- Approval and approval-event atomicity
- Rejection and rejection-event atomicity
- Identical approval retry
- Identical rejection retry
- Changed approval conflict
- Changed rejection conflict
- Opposite-decision conflict
- Event-construction or flush failure rollback
- Sequence ordering when timestamps are equal
- Exactly one winner for concurrent approval and rejection
- Immutable tuple audit responses
- Missing-review error translation
- Stored snapshots remaining unchanged after operational-data changes
- Migration upgrade, downgrade, re-upgrade, and metadata alignment
- Memory backend regression coverage

## Security and operational limitations

This design does not add authentication or authorization. `decided_by` remains
caller supplied and does not prove identity.

Audit events are not cryptographically signed, hash chained, independently
governed, or compliance certified.

This design does not introduce:

- Purchase-order creation
- Inventory mutation during approval
- Event publication
- Message queues
- Frontend behavior
- LLM integration
- Database deployment
- Backups
- Replication
- High availability
- Multi-tenancy
- Row-level security

## Implementation sequence

The implementation should be divided into focused pull requests:

1. SQLAlchemy models, mapping helpers, and Alembic migration
2. PostgreSQL creation, retrieval, and audit-history repository methods
3. PostgreSQL approval and rejection transaction methods
4. Application integration, concurrency tests, and documentation cleanup

Each pull request must preserve the existing Protocol and public API contracts.
