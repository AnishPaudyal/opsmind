# Phase 5 Stockout and Reorder Evaluation

Status: Technical evaluation passed
Date: 2026-08-07
Governed by: Issue #50
Dataset version: `phase5-synthetic-v1`
Owner phase-gate review: Accepted — Proceed on 2026-08-07

## Purpose

Phase 5 formally evaluates the deterministic stockout-exposure and
reorder-recommendation capability that was delivered before its formal phase
gate.

This evaluation does not introduce a new forecasting model, stockout model,
reorder policy, public API, persistence model, database migration, dependency,
or architecture decision. It evaluates the existing production domain
calculations under the design accepted for Issue #50.

## Evaluation Method

The evaluator calls the existing production functions:

1. `calculate_stockout_exposure`;
2. `calculate_reorder_recommendation`.

Expected scenario outcomes are specified independently in the governed
`phase5-synthetic-v1` dataset. The evaluator does not duplicate the production
business formulas to generate its expected values.

The evaluation checks four classes of conformance:

- expected public output;
- exposure-to-recommendation evidence preservation;
- reorder rounding policy;
- status invariants.

## Governed Scenario Results

| Scenario | Exposure status | Public shortage | Reorder status | Quantity | Result |
| --- | --- | ---: | --- | ---: | --- |
| `cutoff_excludes_future_observation` | `sufficient` | 0.00 | `no_reorder_needed` | 0 | PASS |
| `exact_coverage_boundary` | `sufficient` | 0.00 | `no_reorder_needed` | 0 | PASS |
| `fractional_shortage` | `shortage_projected` | 18.75 | `reorder_recommended` | 19 | PASS |
| `large_lead_time_shortage` | `shortage_projected` | 300.00 | `reorder_recommended` | 300 | PASS |
| `negative_available_inventory` | `shortage_projected` | 5.00 | `reorder_recommended` | 5 | PASS |
| `observation_count_lookback_missing_dates` | `shortage_projected` | 5.00 | `reorder_recommended` | 5 | PASS |
| `recorded_zero_demand` | `sufficient` | 0.00 | `no_reorder_needed` | 0 | PASS |
| `small_fractional_shortage` | `shortage_projected` | 0.01 | `reorder_recommended` | 1 | PASS |
| `sufficient_buffer` | `sufficient` | 0.00 | `no_reorder_needed` | 0 | PASS |
| `whole_unit_shortage` | `shortage_projected` | 20.00 | `reorder_recommended` | 20 | PASS |
| `zero_lead_time` | `sufficient` | 0.00 | `no_reorder_needed` | 0 | PASS |

## Aggregate Result

| Measure | Result |
| --- | ---: |
| Scenarios | 11 |
| Passed scenarios | 11 |
| Failed scenarios | 0 |
| `sufficient` | 5 |
| `shortage_projected` | 6 |
| `no_reorder_needed` | 5 |
| `reorder_recommended` | 6 |
| Expected-output mismatches | 0 |
| Evidence-preservation failures | 0 |
| Rounding-invariant failures | 0 |
| Status-invariant failures | 0 |

Every governed scenario and invariant passed.

## Evidence Preservation

The evaluator verifies that the reorder recommendation preserves the exposure
evidence used to produce it, including:

- product identifier;
- forecast method;
- effective cutoff date;
- lookback requested;
- observations used;
- training start and end dates;
- average daily demand;
- lead-time days;
- on-hand quantity;
- allocated quantity;
- available inventory;
- forecasted lead-time demand;
- projected inventory balance;
- projected shortage quantity.

The evaluation recorded zero evidence-preservation failures.

## Rounding and Status Policy

The evaluated reorder policy is:

`projected_shortage_ceiling`

It applies `Decimal` `ROUND_CEILING` to the normalized public projected
shortage.

The governed boundary examples include:

- `0.00 -> 0`;
- `0.01 -> 1`;
- `18.75 -> 19`;
- `20.00 -> 20`;
- `300.00 -> 300`.

The evaluation recorded zero rounding-invariant failures and zero
status-invariant failures.

## Cutoff and Demand-Evidence Semantics

The scenario set verifies that:

- demand after the inclusive cutoff does not influence exposure;
- lookback remains based on recorded observations rather than filled calendar
  days;
- missing dates are not silently converted into zero demand;
- explicitly recorded zero demand remains valid evidence;
- zero lead time does not create artificial future demand exposure;
- negative available inventory remains visible in the evidence.

## Reproducibility

Two independent CLI runs produced byte-identical JSON and Markdown artifacts.

Reviewed SHA-256 values:

- JSON: `781f26f32f4efcf4db9d1a92edabbf306dff687fee6902bc2f04b50a43a3b429`
- Markdown: `32e19d48cd87567c699bce6a5b6affb574ceef312a4e1759a309b4eba4b7f3d5`

The raw generated artifacts remain outside version control. This document is the
durable reviewed evaluation evidence.

## Decision-Quality Limitation

**Decision-quality measurement: Not measured**

Phase 5 has no governed operational outcome dataset or optimization objective
that establishes:

- whether a real stockout occurred;
- whether a recommendation prevented a stockout;
- service-level attainment;
- lost-sales impact;
- holding-cost impact;
- supplier constraints;
- purchase-order outcomes;
- economic optimality of the recommended quantity.

Therefore this evaluation does not report or claim:

- stockout accuracy;
- recommendation accuracy;
- precision;
- recall;
- business uplift;
- service-level improvement;
- cost savings.

A passing Phase 5 result establishes deterministic policy conformance for the
governed scenarios. It does not establish real-world business optimality.

## Explicit Exclusions

Phase 5 does not add or evaluate:

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
- inventory reservation or mutation;
- recommendation approval or rejection quality;
- authentication or authorization;
- AWS or deployment;
- production readiness.

## Validation Evidence

Validation completed on 2026-08-07:

| Gate | Result |
| --- | --- |
| Focused Phase 5 + stockout + reorder tests | 68 passed |
| Ruff format check | Passed |
| Ruff lint | Passed |
| Mypy | Success across 98 source files |
| Non-PostgreSQL/default suite | 433 passed, 55 PostgreSQL-only skips, 1 known warning |
| PostgreSQL integration suite | 56 passed, 1 known warning |
| Complete PostgreSQL-backed suite | 488 passed, 0 skipped, 1 known warning |
| Alembic | `0006_workflow_persistence (head)` |
| Evaluation run reproducibility | Byte-identical |
| `git diff --check` | Passed |
| Isolated PostgreSQL cleanup | Completed |

The warning is the already-known `StarletteDeprecationWarning` emitted by the
FastAPI/Starlette test-client dependency path. It did not fail the suite and is
not introduced by Issue #50.

## Technical Conclusion

The Phase 5 technical evaluation passed.

The existing deterministic stockout-exposure and reorder-recommendation
behavior satisfies the governed scenario-conformance, evidence-preservation,
rounding, status, reproducibility, and documentation requirements evaluated
under Issue #50.

The owner accepted the Phase 5 `Proceed` decision on 2026-08-07, including
the documented absence of real-world decision-quality measurement. In the
merged Issue #50 repository state, Phase 5 is Complete. Phase 6 is the next
formal gate; this evaluation does not authorize Phase 6 work on the current
branch.
