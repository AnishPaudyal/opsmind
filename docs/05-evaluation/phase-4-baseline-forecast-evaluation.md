# Phase 4 Baseline Forecast Evaluation

Evaluation date: 2026-08-06
Governed by: Issue #48
Owner acceptance: 2026-08-06
Design:
`docs/01-architecture/forecast-evaluation-design.md`
Dataset version: `phase4-synthetic-v1`

## Purpose

This report records the durable, reviewed evidence for OpsMind's
deterministic arithmetic-mean demand forecast. It evaluates the existing
production domain calculation without adding another forecast
implementation, mutating application state, or exposing an evaluation HTTP
endpoint.

The report supports the Phase 4 gate. It does not establish real-world
accuracy, production readiness, downstream decision quality, or superiority
over candidate forecasting models.

## Reproduction Command

```bash
uv run python -m opsmind.evaluation       --output-dir /tmp/opsmind-phase4-evaluation       --lookback-observations 7       --horizon-days 7       --minimum-training-observations 7
```

The command writes:

* `evaluation.json` — complete machine-readable evidence;
* `evaluation.md` — generated human-readable evidence.

Generated artifacts remain outside version control. This document preserves
the reviewed method, measurements, checksums, interpretation, and limitations.

## Evaluation Configuration

| Setting | Value |
| --- | --- |
| Lookback | 7 recorded observations |
| Forecast horizon | 7 calendar days |
| Minimum training history | 7 observations |
| Forecast method | `simple_mean` |
| Signed error | forecast minus actual |
| Numeric policy | exact `Decimal`, published to two decimals with `ROUND_HALF_UP` |
| Missing dates | missing, never silently interpreted as zero |
| Recorded zeros | valid demand observations |
| Target eligibility | every calendar date in the future horizon must be present |
| Forecast origins | chronological observed dates |
| Randomness | none |

## Dataset

The deterministic generator creates nine fixed product series:

1. stable demand;
2. upward trend;
3. downward trend;
4. weekly seasonality;
5. intermittent demand with recorded zeros;
6. all-zero demand;
7. missing calendar dates;
8. short history;
9. abrupt upward level shift.

Product UUIDs, dates, quantities, pattern order, and dataset version are
stable and locked by tests. No production, customer, personal, or regulated
data is used.

## Temporal Method

Each observed date is considered as a candidate forecast origin.

Training evidence:

* includes only observations whose date is on or before the origin;
* selects the most recent requested number of observations;
* must contain the configured minimum training history.

Target evidence:

* begins one calendar day after the origin;
* ends exactly seven calendar days after the origin;
* is accepted only when every date in that interval is observed.

The enforced leakage invariant is:

```text
maximum training date <= forecast origin < minimum target date
```

A missing target date excludes the window. It is not converted to zero.

## Metrics

### Mean Absolute Error

```text
MAE = sum(abs(forecast - actual)) / valid windows
```

MAE measures average absolute seven-day quantity error.

### Forecast Bias

```text
bias = sum(forecast - actual) / valid windows
```

Negative bias means under-forecasting. Positive bias means
over-forecasting.

### WAPE

```text
WAPE = sum(abs(forecast - actual)) / sum(actual) * 100
```

WAPE is aggregated from totals rather than averaged from per-window
percentages. It is undefined when total actual demand is zero.

## Aggregate Results

| Attempted windows | Valid windows | Excluded windows | MAE | Bias | WAPE |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 288 | 161 | 127 | 11.26 | -4.57 | 17.51% |

Supporting totals:

| Total forecast | Total actual | Total signed error | Total absolute error |
| ---: | ---: | ---: | ---: |
| 9617.00 | 10352.00 | -735.00 | 1813.00 |

## Results by Pattern

| Pattern | Valid windows | MAE | Bias | WAPE |
| --- | ---: | ---: | ---: | ---: |
| `abrupt_upward_level_shift` | 22 | 33.41 | -33.41 | 38.18% |
| `all_zero` | 22 | 0.00 | 0.00 | Undefined |
| `downward_trend` | 22 | 24.50 | 24.50 | 23.33% |
| `intermittent` | 22 | 0.00 | 0.00 | 0.00% |
| `missing_calendar_dates` | 7 | 0.00 | 0.00 | 0.00% |
| `short_history` | 0 | Unavailable | Unavailable | Unavailable |
| `stable` | 22 | 0.00 | 0.00 | 0.00% |
| `upward_trend` | 22 | 24.50 | -24.50 | 23.33% |
| `weekly_seasonal` | 22 | 0.00 | 0.00 | 0.00% |

## Exclusions

| Reason | Count |
| --- | ---: |
| `incomplete_target_window` | 73 |
| `insufficient_training_observations` | 54 |

The missing-date pattern generated 20 incomplete-target exclusions, compared
with seven for each complete 35-day pattern. The short-history pattern
generated no valid window.

## Findings

### Demonstrated strengths

* Stable demand is forecast exactly.
* Recorded all-zero demand is handled without division-by-zero
  misrepresentation; WAPE remains undefined.
* The controlled weekly pattern is exact because both the lookback and
  horizon cover one complete seven-day cycle.
* The controlled intermittent pattern is exact for the same alignment
  reason.
* Missing dates are not silently imputed.

### Demonstrated weaknesses

* Upward trend is under-forecast by 24.50 units per valid window on average.
* Downward trend is over-forecast by 24.50 units per valid window on average.
* The abrupt upward level shift is the weakest tested pattern, with MAE
  33.41, bias -33.41, and WAPE 38.18%.
* A short series cannot support the selected configuration.
* Missing calendar dates sharply reduce evaluable evidence.

### Downstream implication

Stockout exposure and reorder recommendations reuse this forecast evidence.
Negative forecast bias can understate projected demand; positive bias can
overstate it. This evaluation does not independently measure downstream
stockout or reorder decision quality.

## Reproducibility Evidence

Two clean runs produced byte-identical JSON and Markdown artifacts.

| Artifact | SHA-256 |
| --- | --- |
| `evaluation.json` | `2494c13ad484fa9845dc65ac8d3f39924d394ebe67bcbd8fcf495af4a66e51d0` |
| `evaluation.md` | `791614bdcbc11958c7e8c544c0b7f6a40d2f9cf1efc978e6eacba229abb5583e` |

Validation recorded:

* 18 focused evaluation tests passed;
* Ruff formatting passed;
* Ruff linting passed;
* mypy passed across 92 source files;
* 56 PostgreSQL integration tests passed;
* 464 tests passed with the isolated PostgreSQL test database configured;
* zero tests skipped in the final full suite;
* one known Starlette TestClient/httpx deprecation warning remained;
* Alembic remained at `0006_workflow_persistence (head)`.

## Security, Privacy, Cost, and Operations

* No production or personal data is used.
* No network service, database write, or API mutation is required by the
  evaluation.
* No new third-party dependency is introduced.
* No cloud resource or persistent infrastructure cost is created.
* Output directories are explicit and protected from accidental overwrite.
* Generated evidence is deterministic and suitable for local or CI
  comparison.
* None of this establishes a production monitoring or model-governance
  system.

## Limitations

* Synthetic results do not prove real-world forecast accuracy.
* Pattern definitions are intentionally controlled and limited.
* Exact weekly and intermittent results depend on alignment between the
  seven-observation lookback, seven-day horizon, and seven-day pattern.
* No uncertainty, confidence interval, or probabilistic forecast is
  produced.
* No model selection, hyperparameter search, or learned model is evaluated.
* No operational data drift, correction, deletion, or late-arrival process
  is evaluated.
* No stockout or reorder decision-quality metric is included.
* No production-readiness claim is supported.

## Recommendation

Preserve the simple mean as a transparent reference baseline.

The repository owner accepted the Phase 4 Proceed decision on 2026-08-06 with
the explicit condition that these synthetic measurements are reference evidence
only. Any real-world accuracy claim requires a separately governed operational
dataset, temporal evaluation, and review. Future candidate forecasts should be
compared on the same governed windows and metrics or on a reviewed successor
methodology.
