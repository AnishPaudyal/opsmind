# Phase 4 Forecasting Baseline and Evaluation Review

Review date: 2026-08-06
Review type: Phase-gate review
Governed by: Issue #48
Owner acceptance: Anish Paudyal, 2026-08-06
Design:
`docs/01-architecture/forecast-evaluation-design.md`
Evidence:
`docs/05-evaluation/phase-4-baseline-forecast-evaluation.md`

## Outcome

Overall result: **Passed**

Decision: **Proceed**

The deterministic forecast baseline and its governed synthetic evaluation
satisfy the Phase 4 exit criteria. The repository owner accepted this review
and the Proceed decision on 2026-08-06. Phase 4 is Complete in the merged
repository state.

This decision accepts the simple mean as a transparent reference baseline.
It does not claim real-world accuracy, production model quality, stockout or
reorder decision quality, deployment readiness, or production readiness.

## Review Scope

This review evaluates:

* the existing arithmetic-mean forecast delivered through Issue #20 / PR #21;
* the accepted Issue #48 evaluation design;
* deterministic dataset version `phase4-synthetic-v1`;
* temporal window construction and leakage prevention;
* MAE, forecast bias, and WAPE;
* deterministic JSON and Markdown reporting;
* CLI behavior and artifact overwrite protection;
* exact measured results and limitations;
* local, full-suite, and PostgreSQL regression evidence.

It does not evaluate:

* a learned or probabilistic forecast model;
* production or customer data;
* real-world forecast accuracy;
* stockout or reorder decision quality;
* model monitoring or drift detection;
* MLOps or model lifecycle;
* API containerization, AWS, or deployment;
* production readiness.

## Exit-Criteria Assessment

| Exit criterion | Result | Evidence |
| --- | --- | --- |
| Deterministic forecast baseline remains reproducible | Passed | Evaluation invokes the existing `calculate_simple_mean_forecast` implementation and exact measurements are locked by tests |
| Approved dataset or deterministic generator is documented | Passed | Accepted design and dataset version `phase4-synthetic-v1` define fixed UUIDs, dates, patterns, quantities, and ordering |
| Temporal evaluation prevents future leakage | Passed | Training dates are on or before the origin and complete target dates begin after it; invariants are directly tested |
| Approved forecast-error metric is implemented and explained | Passed | MAE, signed forecast bias, and WAPE are implemented with exact decimal aggregation and documented denominator behavior |
| Baseline results are measured and reproducible | Passed | 161 valid windows produced MAE 11.26, bias -4.57, WAPE 17.51%; two runs were byte-identical |
| Limitations are documented | Passed | Trend, level-shift, seasonality alignment, intermittency, missing dates, short history, uncertainty, and decision-use limits are explicit |
| Findings produce a follow-up or accepted decision | Passed | Owner-accepted Proceed decision preserves the simple mean as a reference and requires separate governance before real-world claims |
| Phase 4 review records an accepted decision | Passed | Repository owner accepted this review and the Proceed decision on 2026-08-06 |

## Delivered Capabilities

* deterministic evaluation package under `src/opsmind/evaluation`;
* fixed synthetic dataset generator;
* nine documented demand patterns;
* chronological forecast-origin generation;
* complete target-window validation;
* explicit exclusion reasons;
* production forecast reuse;
* exact per-window errors;
* aggregate and per-pattern metrics;
* explicit undefined-WAPE behavior;
* explicit zero-valid-window behavior;
* deterministic JSON and Markdown reports;
* overwrite-safe CLI;
* durable evaluation design and report;
* focused methodology, reporting, and CLI tests.

## Measured Evidence

| Measure | Result |
| --- | ---: |
| Attempted windows | 288 |
| Valid windows | 161 |
| Excluded windows | 127 |
| Aggregate MAE | 11.26 |
| Aggregate bias | -4.57 |
| Aggregate WAPE | 17.51% |
| Total forecast quantity | 9617.00 |
| Total actual quantity | 10352.00 |
| Total signed error | -735.00 |
| Total absolute error | 1813.00 |

The most material weakness was the abrupt upward level shift: MAE 33.41,
bias -33.41, and WAPE 38.18%. Upward trend was under-forecast; downward
trend was over-forecast. Exact results for controlled weekly and intermittent
patterns are configuration-alignment findings, not general model-quality
claims.

## Validation Evidence

* 18 focused evaluation tests passed.
* Dataset identity, dates, counts, and pattern semantics are locked.
* Exact aggregate and per-pattern measurements are locked.
* Leakage prevention, recorded-zero handling, missing-date behavior, and
  short-history exclusions are tested.
* JSON and Markdown outputs are deterministic.
* Zero-valid-window evaluation writes diagnostics and exits nonzero.
* Ruff formatting and linting passed.
* mypy passed across 92 source files.
* 56 real PostgreSQL integration tests passed.
* The full suite passed 464 tests with zero skips.
* Alembic remained at `0006_workflow_persistence (head)`.
* The isolated PostgreSQL container, network, and volume were removed after
  validation.
* One known Starlette TestClient/httpx deprecation warning remains.

## Documentation Evidence

Phase 4 documentation includes:

* accepted evaluation design;
* durable measured evaluation report;
* README reproduction command and interpretation;
* roadmap status and gate language;
* current-status evidence and limitations;
* changelog entries;
* this proposed review.

No new ADR is required because Issue #48 does not change the public API,
persistence schema, deployment architecture, security boundary, or major
dependency set.

## Security and Privacy Findings

* Synthetic data only.
* No production, customer, personal, or regulated data.
* No secret or credential required by evaluation execution.
* No network access or application mutation.
* Output is written only to an explicit local directory.
* Existing PostgreSQL test credentials remain development-only and
  environment supplied.
* Evaluation evidence does not establish an authenticated or authorized
  product workflow.

Result: **Acceptable for Phase 4**

## Cost Findings

* No AWS or managed infrastructure.
* No new dependency or hosted evaluation service.
* Local execution only.
* Temporary PostgreSQL validation resources were removed after the test run.
* No production cost estimate is justified.

Result: **Acceptable for Phase 4**

## Data Findings

* Dataset construction is deterministic and versioned.
* Recorded zeros remain distinct from missing dates.
* Missing target dates exclude windows.
* Every accepted target window contains all required calendar dates.
* Short history produces no valid evidence under the selected configuration.
* Synthetic data cannot support real-world accuracy claims.
* No data-retention, operational correction, late-arrival, or drift process
  is established.

Result: **Acceptable for Phase 4**

## Operational Findings

* Evaluation remains outside the HTTP request path.
* No repository or database mutation occurs.
* Generated artifacts are protected from accidental overwrite.
* Zero-valid-window runs fail the CLI while retaining diagnostics.
* Exact artifact checksums support reproducibility review.
* No production evaluation scheduler, monitoring, alerting, or model registry
  exists.

Result: **Acceptable for Phase 4**

## Unresolved Risks

* Synthetic results may not transfer to operational demand.
* The baseline reacts slowly to trend and abrupt level shifts.
* Aligned weekly results may overstate performance on irregular seasonality.
* Intermittent-demand success is specific to the controlled repeating
  pattern and selected horizon.
* No uncertainty estimate or prediction interval exists.
* No downstream stockout or reorder decision-quality evaluation exists.
* No governed operational dataset has been approved.
* No model drift, retraining, registry, or production monitoring exists.
* The known Starlette TestClient/httpx warning remains.

These risks do not block Phase 4 completion because the phase establishes a
reproducible reference baseline and its limitations rather than approving a
production forecasting model.

## Conditions Carried Forward

* Preserve the simple mean as a transparent comparison baseline.
* Preserve temporal no-leakage evaluation.
* Preserve recorded zero demand as distinct from missing dates.
* Preserve exact decimal aggregation and explicit rounding.
* Keep undefined WAPE explicit when actual demand totals zero.
* Keep zero-valid-window evidence invalid for phase completion.
* Require separate governance before introducing real operational data.
* Compare future forecast candidates against this method or a reviewed
  successor.
* Do not infer stockout or reorder decision quality from forecast metrics.
* Do not claim production model quality or readiness.

## Deferred Work

* governed operational forecast dataset;
* real-world temporal forecast validation;
* probabilistic forecasts or prediction intervals;
* learned forecast models;
* downstream stockout and reorder decision-quality evaluation;
* Phase 5 formal review;
* Phase 6 formal review;
* model monitoring, drift detection, and retraining;
* MLOps and model registry;
* API containerization;
* AWS infrastructure and deployment;
* production readiness.

## Decision

**Proceed**

The repository owner accepted the Phase 4 deterministic forecast baseline and
evaluation review on 2026-08-06. Phase 4 is Complete in the merged repository
state.

Phase 5 becomes the next formal gate after the associated pull request merges.
This decision does not mark Phase 5 or Phase 6 complete and does not authorize
Phase 7, deployment, AWS, or production-readiness claims.
