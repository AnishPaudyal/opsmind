# Phase 5 Stockout and Reorder Evaluation Design

Status: Accepted
Date: 2026-08-07
Governed by: Issue #50
Owner acceptance: Anish Paudyal, 2026-08-07
Phase: 5 — Stockout Risk and Reorder Recommendations

## Purpose

Formally evaluate the already-delivered deterministic stockout-exposure and
reorder-recommendation behavior against the Phase 5 exit criteria.

This design does not introduce a new stockout model or recommendation policy.
It defines a reproducible scenario-conformance evaluation around the existing
domain behavior.

## Existing Behavior Under Evaluation

The evaluation must reuse:

- `calculate_stockout_exposure`;
- `calculate_reorder_recommendation`;
- the existing simple-mean demand statistics used by stockout exposure;
- the existing `projected_shortage_ceiling` reorder policy.

The evaluator must not reimplement the business formulas independently.

## Phase 5 Exit Criteria Addressed

The evaluation must provide evidence that:

1. stockout exposure uses documented and reproducible evidence;
2. reorder recommendations preserve the evidence used to produce them;
3. quantity and rounding policies are explicit and tested;
4. deterministic behavior is distinguished from probability, calibrated risk,
   or learned prediction;
5. decision-quality evaluation is completed or its absence is explicitly
   accepted with documented limitations;
6. supplier, cost, pack-size, safety-stock, service-level, and ordering
   exclusions remain explicit;
7. a Phase 5 review can record a Proceed, Revise, or Stop decision.

## Evaluation Type

The Phase 5 evaluation is a deterministic **scenario-conformance evaluation**.

It measures whether the implementation follows its documented arithmetic and
policy rules across governed synthetic scenarios.

It does not measure real-world business optimality.

## Dataset Version

The deterministic scenario dataset version is:

`phase5-synthetic-v1`

The dataset must contain no randomness, wall-clock dependence, external
services, or mutable external state.

Scenario identifiers, dates, quantities, lead times, demand observations, and
expected public outcomes must be fixed.

## Governed Scenario Families

The initial scenario set must include at least:

### 1. Sufficient buffer

Purpose:

- verify positive projected inventory balance;
- verify `sufficient`;
- verify zero public shortage;
- verify `no_reorder_needed`;
- verify recommended quantity zero.

### 2. Exact coverage boundary

Purpose:

- verify a public projected balance of exactly `0.00`;
- verify exact zero remains `sufficient`;
- verify no reorder is proposed.

### 3. Fractional shortage

Purpose:

- verify a positive fractional public shortage;
- verify `shortage_projected`;
- verify `ROUND_CEILING` produces the next whole unit.

Canonical example:

`18.75 -> 19`

### 4. Whole-unit shortage

Purpose:

- verify an integral public shortage remains unchanged by whole-unit ceiling.

Canonical example:

`20.00 -> 20`

### 5. Small fractional shortage

Purpose:

- verify any positive public shortage below one unit still produces one unit.

Canonical example:

`0.01 -> 1`

### 6. Negative available inventory

Purpose:

- verify allocated quantity may exceed on-hand quantity;
- preserve negative available inventory as evidence;
- verify the resulting deterministic shortage remains explainable.

### 7. Zero lead time

Purpose:

- verify zero lead time produces zero lead-time demand;
- verify no artificial future exposure is created.

### 8. Recorded zero demand

Purpose:

- verify explicitly recorded zero demand remains valid evidence;
- distinguish recorded zeros from missing calendar dates.

### 9. Cutoff excludes future observation

Purpose:

- verify demand after the inclusive `as_of_date` does not influence exposure or
  recommendation evidence.

### 10. Observation-count lookback with missing calendar dates

Purpose:

- verify lookback remains based on recorded observations rather than filled
  calendar days;
- preserve missing-date semantics inherited from the forecast baseline.

### 11. Large lead-time shortage

Purpose:

- verify mechanically consistent behavior at a larger deterministic exposure;
- ensure the evaluator does not assume only small recommendation quantities.

## Expected Outputs

Each scenario must define expected public values independently of the production
functions being evaluated.

Expected values may include:

- effective `as_of_date`;
- observations used;
- training start date;
- training end date;
- average daily demand;
- lead-time days;
- available inventory;
- forecasted lead-time demand;
- projected inventory balance;
- projected shortage quantity;
- stockout exposure status;
- recommendation policy;
- recommendation status;
- recommended reorder quantity.

The expected result must not be calculated by calling the same production
function whose output it is validating.

## Core Invariants

### Evidence preservation

The recommendation must preserve the exposure evidence used to produce it.

At minimum, these values must match exactly between exposure and recommendation:

- product identifier;
- forecast method;
- effective cutoff;
- requested lookback;
- observations used;
- training start date;
- training end date;
- average daily demand;
- lead-time days;
- on-hand quantity;
- allocated quantity;
- available inventory;
- forecasted lead-time demand;
- projected inventory balance;
- projected shortage quantity.

### Exposure status

If:

`projected_inventory_balance >= 0.00`

then:

- status must be `sufficient`;
- projected shortage must be `0.00`.

If:

`projected_inventory_balance < 0.00`

then:

- status must be `shortage_projected`;
- projected shortage must be positive.

The evaluator validates the documented public behavior, including public
two-decimal normalization.

### Reorder quantity

For the sole Phase 5 policy:

`projected_shortage_ceiling`

the recommendation quantity must equal:

`ROUND_CEILING(projected_shortage_quantity)`

where the input is the public normalized projected shortage.

### Recommendation status

If public projected shortage is `0.00`:

- recommended quantity must be `0`;
- status must be `no_reorder_needed`.

If public projected shortage is positive:

- recommended quantity must be positive;
- status must be `reorder_recommended`.

## Evaluation Result

The evaluator must report:

- dataset version;
- scenario count;
- passed scenario count;
- failed scenario count;
- count of `sufficient` results;
- count of `shortage_projected` results;
- count of `no_reorder_needed` results;
- count of `reorder_recommended` results;
- expected-output mismatch count;
- evidence-preservation failure count;
- rounding-invariant failure count;
- status-invariant failure count;
- scenario-level results.

A successful governed run requires every failure count to be zero.

## Decision-Quality Limitation

Phase 5 does not have a governed operational outcome dataset containing realized
business outcomes such as:

- whether a real stockout occurred;
- whether a recommendation prevented a stockout;
- service-level attainment;
- lost-sales impact;
- holding-cost impact;
- supplier constraints;
- purchase-order outcomes;
- economic optimality of the recommended quantity.

Therefore this phase must not invent or report metrics such as:

- stockout accuracy;
- recommendation accuracy;
- precision;
- recall;
- business uplift;
- service-level improvement;
- cost savings.

The Phase 5 report must record:

**Decision-quality measurement: Not measured**

with the reason that no governed operational outcome labels or optimization
objective exist in Phase 5 scope.

The roadmap explicitly allows this absence to be accepted when documented as a
limitation.

## Explicit Non-Goals and Exclusions

This evaluation does not add or evaluate:

- calibrated stockout probability;
- learned stockout prediction;
- probabilistic forecasting;
- safety-stock optimization;
- service-level optimization;
- supplier selection;
- supplier lead-time optimization;
- supplier reliability;
- cost optimization;
- pack-size optimization;
- minimum-order quantities;
- purchase-order creation;
- external ordering;
- reservation or mutation of inventory;
- recommendation approval or rejection quality;
- authentication or authorization;
- AWS or deployment;
- production readiness.

## Implementation Shape

Use a dedicated Phase 5 evaluation subpackage:

```text
src/opsmind/evaluation/phase5/
├── __init__.py
├── __main__.py
├── scenarios.py
├── evaluation.py
└── reporting.py
```

Add focused tests under:

```text
tests/unit/test_phase5_evaluation.py
```

The Phase 4 evaluation package must remain behaviorally unchanged.

## CLI

The intended command is:

```bash
uv run python -m opsmind.evaluation.phase5 \
  --output-dir /tmp/opsmind-phase5-evaluation
```

The evaluator should emit:

```text
phase5-evaluation.json
phase5-evaluation.md
```

Outputs must be deterministic and overwrite-safe, following the successful
Phase 4 evaluation pattern.

## Durable Evidence

The reviewed Phase 5 report should be committed under:

`docs/05-evaluation/phase-5-stockout-reorder-evaluation.md`

Raw generated temporary artifacts should remain outside version control.

## Phase Review

The Phase 5 review should be created under:

`docs/12-phase-reviews/phase-5-review.md`

Before owner acceptance it must remain explicitly proposed.

A proposed technical pass must not mark Phase 5 Complete before owner acceptance
and merge.

## Validation Plan

At minimum:

1. focused Phase 5 evaluator tests;
2. existing stockout-domain tests;
3. existing reorder-domain tests;
4. relevant stockout API tests;
5. relevant reorder API tests;
6. Ruff formatting;
7. Ruff lint;
8. mypy;
9. complete test suite;
10. PostgreSQL integration suite;
11. two independent Phase 5 evaluation runs compared byte-for-byte;
12. stable SHA-256 values recorded for reviewed artifacts;
13. `git diff --check`;
14. documentation link and terminology checks.

## Architecture Decision

No new ADR is required.

The work does not change:

- public API contracts;
- persistence architecture;
- database schema;
- dependency architecture;
- security boundaries;
- deployment architecture;
- forecast implementation;
- stockout implementation;
- reorder policy.

It adds governed evaluation around already accepted behavior.

## Owner Acceptance

The repository owner accepted this design on 2026-08-07 and approved
implementation under Issue #50.

Accepted statement:

`I accept the Phase 5 stockout and reorder evaluation design and approve implementation under Issue #50.`
