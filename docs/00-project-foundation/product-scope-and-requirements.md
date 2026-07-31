# Product Scope and Requirements

Last updated: 2026-07-30

## Core Product Promise

OpsMind helps a planner understand emerging stockout risk and make a documented
reorder decision using current product data, demand history, forecast evidence,
and configurable business rules.

## First Vertical Slice

The first complete workflow is:

1. Maintain a product record and basic inventory policy.
2. Load or generate demand history.
3. Produce a demand forecast with evaluation metadata.
4. Estimate stockout risk for a defined horizon.
5. Generate a reorder recommendation and supporting factors.
6. Present the recommendation for human approval or rejection.
7. Record the decision, reason, actor, time, and source recommendation.

## Initial Functional Requirements

### Product and Demand Data

- Create, read, update, and validate product records.
- Record lead time, current inventory, service target, and reorder constraints.
- Load time-stamped demand observations from an approved sample source.
- Reject malformed data and report quality failures.

### Forecast and Risk

- Generate a reproducible baseline forecast.
- Record model or rule version, input window, horizon, and uncertainty.
- Calculate stockout risk from documented assumptions.
- Separate measured values, model estimates, and business rules.

### Recommendation and Decision

- Produce a suggested reorder quantity and timing.
- Show the major inputs and reasoning used.
- Allow approval or rejection with a reason.
- Preserve immutable decision history even when later records change.

## Initial Non-Functional Requirements

- Local startup and checks must be reproducible.
- APIs and data contracts must be versioned deliberately.
- Important operations must emit structured, correlation-friendly logs.
- Authorization and audit boundaries must be testable.
- Secrets must remain outside source control.
- Cloud resources must have explicit ownership, tagging, and budget controls.
- Model limitations and fallback behavior must be documented.

## Out of Scope for the First Vertical Slice

- Autonomous purchasing
- Multi-enterprise tenancy
- Live ERP integration
- Real-time global optimization
- Large-language-model recommendations
- High-scale streaming architecture
- Mobile applications

These may be revisited only after the core workflow is validated.

## Acceptance Standard

The vertical slice is accepted when a reviewer can run a documented scenario
from sample data through a human decision, inspect the audit record, and
understand how the recommendation was produced.
