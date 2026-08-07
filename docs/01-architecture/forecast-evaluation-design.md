# Phase 4 Baseline Forecast Evaluation Design

Issue: #48
Roadmap phase: Phase 4 — Forecasting baseline and evaluation
Design status: Accepted
Design date: 2026-08-06
Accepted by: Anish Paudyal
Accepted on: 2026-08-06

## 1. Purpose

This design defines the reproducible temporal evaluation framework for OpsMind’s existing deterministic arithmetic-mean demand forecast.

The objective is to measure the existing baseline honestly before:

* introducing a more advanced forecasting model;
* claiming forecast accuracy or reliability;
* formally completing Phase 4;
* formally evaluating the downstream Phase 5 stockout and reorder capabilities.

This work evaluates the existing forecast behavior. It does not replace or redesign that behavior.

## 2. Existing Baseline

The existing forecast domain provides:

```python
calculate_simple_mean_forecast(...)
```

The function:

* is independent of HTTP transport;
* accepts immutable demand observations;
* selects eligible observations on or before an inclusive cutoff;
* uses a record-count lookback rather than a calendar-day lookback;
* includes recorded zero demand;
* leaves absent calendar dates absent;
* calculates the arithmetic mean using `Decimal`;
* multiplies the exact unrounded mean by the requested horizon;
* applies deterministic two-decimal `ROUND_HALF_UP` rounding at the public result boundary;
* returns immutable explanatory metadata;
* does not mutate or persist application state.

The evaluation framework must call this function directly. It must not reimplement the arithmetic-mean algorithm.

## 3. Decision Summary

The Phase 4 evaluation will use:

* deterministic synthetic demand-series generation;
* rolling temporal forecast origins;
* complete calendar-day target windows;
* the existing production forecast domain function;
* exact `Decimal` metric calculations;
* Mean Absolute Error;
* signed forecast bias;
* WAPE where the total actual demand denominator is nonzero;
* a standard-library command-line interface;
* JSON machine-readable output;
* Markdown human-readable output;
* generated evaluation artifacts outside version control;
* a reviewed, version-controlled evaluation report summarizing verified results.

The work will not introduce:

* a new database schema;
* persisted evaluation results;
* a new API endpoint;
* a background worker;
* third-party numerical or CLI dependencies;
* real customer, personal, confidential, or production data.

## 4. Architecture

```text
deterministic demand-series generator
                |
                v
validated chronological evaluation series
                |
                v
temporal forecast-origin generator
                |
                v
existing calculate_simple_mean_forecast(...)
                |
                v
complete future actual-demand target
                |
                v
per-window forecast comparison
                |
                v
MAE, bias, and WAPE aggregation
                |
                v
JSON result and Markdown report
```

## 5. Proposed Source Structure

```text
src/opsmind/evaluation/__init__.py
src/opsmind/evaluation/forecast.py
src/opsmind/evaluation/datasets.py
src/opsmind/evaluation/reporting.py
src/opsmind/evaluation/__main__.py
```

### `evaluation/forecast.py`

Owns:

* evaluation configuration;
* evaluation-series validation;
* temporal-origin generation;
* valid-window and excluded-window models;
* calls to the existing forecast calculation;
* future-target construction;
* per-window error calculations;
* aggregate metric calculations;
* complete evaluation-result models.

### `evaluation/datasets.py`

Owns:

* deterministic dataset-version metadata;
* stable product identifiers;
* representative synthetic demand patterns;
* deterministic observation generation;
* no random or system-time-dependent behavior.

### `evaluation/reporting.py`

Owns:

* conversion of the complete result to JSON-compatible data;
* deterministic JSON rendering;
* deterministic Markdown rendering;
* explicit representation of undefined metrics;
* stable ordering of patterns, windows, and exclusions.

### `evaluation/__main__.py`

Owns:

* standard-library `argparse` handling;
* evaluation configuration arguments;
* required output-directory selection;
* generation of JSON and Markdown artifacts;
* nonzero exit behavior for invalid configuration or output failures.

The CLI must contain no forecasting or metric logic.

## 6. Evaluation Data

### 6.1 Selected approach

Use a deterministic Python dataset generator rather than checked-in CSV files or a repository-backed production dataset.

### 6.2 Rationale

A deterministic generator:

* contains no confidential data;
* is inspectable in source control;
* avoids parsing dependencies;
* avoids accidental fixture drift;
* supports exact pattern semantics;
* remains reproducible across local development and CI;
* can version dataset behavior explicitly.

### 6.3 Required dataset metadata

The generated dataset must include:

* a stable dataset version;
* a fixed start date;
* stable UUIDs;
* stable pattern names;
* the exact generation configuration;
* deterministic chronological output.

### 6.4 Required demand patterns

The initial dataset must include:

1. stable demand;
2. upward trend;
3. downward trend;
4. weekly seasonal variation;
5. intermittent demand represented with explicit zero observations;
6. all-zero recorded demand;
7. missing calendar dates;
8. short history;
9. abrupt upward level shift.

A missing calendar date must remain different from an explicitly recorded zero.

## 7. Evaluation Configuration

The initial governed configuration is:

* lookback observations: 7;
* forecast horizon: 7 calendar days;
* minimum training observations: 7;
* forecast origins: chronological observed demand dates;
* signed-error convention: forecast minus actual;
* WAPE representation: percentage;
* public metric precision: two decimal places.

Configuration values must remain typed and validated.

Lookback, horizon, and minimum-history values must be positive integers.
Minimum training observations must not exceed lookback observations.

The initial command may permit explicit configuration overrides, but the committed evaluation report must state the exact configuration it used.

## 8. Temporal Window Generation

### 8.1 Forecast origin

Each chronological observed demand date is considered as a candidate forecast origin.

The origin date becomes the forecast’s inclusive `as_of_date`.

### 8.2 Training data

For a candidate origin:

* only observations dated on or before the origin are eligible;
* the existing forecast function performs chronological lookback selection;
* the evaluation framework must verify that the resulting training end date is not after the origin;
* a window is excluded when fewer than the configured minimum training observations were used.

### 8.3 Target data

The target interval begins one calendar day after the origin and ends on:

```text
origin + horizon_days
```

A target window is valid only when every calendar date in that interval has one observation.

This rule ensures:

* an absent date is not silently interpreted as zero;
* recorded zero demand remains valid actual demand;
* the actual target corresponds to the complete calendar horizon forecast by the existing endpoint.

The target actual quantity is the sum of the complete target interval.

### 8.4 Leakage invariant

Every valid window must satisfy:

```text
maximum training date <= forecast origin < minimum target date
```

No target observation may be included in the forecast input.

### 8.5 Stable ordering

Evaluation results must be ordered by:

1. demand-pattern name;
2. product identifier;
3. forecast-origin date.

Exclusions must use the same deterministic ordering.

## 9. Window Exclusions

Candidate windows may be excluded for explicit reasons such as:

* insufficient training observations;
* incomplete future target window;
* invalid or duplicate series data;
* no eligible forecast history;
* invalid evaluation configuration.

Expected data limitations must be represented as typed exclusions rather than swallowed exceptions.

The report must include:

* attempted-window count;
* valid-window count;
* excluded-window count;
* exclusion count by reason;
* exclusions by demand pattern.

A domain evaluation result may represent zero valid windows so its exclusions
remain inspectable. In that case:

* aggregate MAE and bias are unavailable;
* WAPE is unavailable;
* JSON represents unavailable aggregate metrics as `null`;
* Markdown explains that no valid windows were produced;
* the CLI writes the diagnostic artifacts, prints a clear error, and exits
  nonzero;
* the result cannot support Phase 4 completion.

## 10. Per-Window Result

Each valid result must include:

* dataset version;
* demand-pattern name;
* product identifier;
* forecast method;
* forecast origin;
* requested lookback;
* observations used;
* training start date;
* training end date;
* target start date;
* target end date;
* horizon days;
* forecast quantity;
* actual quantity;
* signed error;
* absolute error.

The forecast quantity used for evaluation must be the existing public `BaselineForecast.forecast_quantity`.

This measures the behavior consumers actually receive, including the established rounding boundary.

## 11. Metric Definitions

### 11.1 Signed error

```text
signed error = forecast quantity - actual quantity
```

Interpretation:

* positive: over-forecast;
* negative: under-forecast;
* zero: exact forecast.

### 11.2 Mean Absolute Error

```text
MAE = sum(absolute error) / valid window count
```

MAE is expressed in demand units over the configured forecast horizon.

### 11.3 Forecast bias

```text
bias = sum(signed error) / valid window count
```

Interpretation:

* positive aggregate bias: average over-forecasting;
* negative aggregate bias: average under-forecasting;
* zero aggregate bias does not imply low absolute error.

### 11.4 WAPE

```text
WAPE = sum(absolute error) / sum(actual quantity) * 100
```

WAPE is expressed as a percentage.

When total actual demand is zero:

* WAPE is undefined;
* it must be represented as `null` in JSON;
* it must be represented as `Not defined: total actual demand is zero` in Markdown;
* it must not be converted to zero or infinity.

### 11.5 Aggregation

Metrics must be produced for:

* all valid windows;
* each demand pattern independently.

Every valid window receives equal weight in MAE and bias.

WAPE uses aggregate absolute error and aggregate actual demand rather than an average of per-window percentages.

### 11.6 Numeric policy

All metric calculations use `Decimal`.

Public metric values use two decimal places with the existing `ROUND_HALF_UP` and signed-zero normalization policy where applicable.

Intermediate metric calculations must not use binary floating-point arithmetic.

## 12. Reporting

The command must produce:

```text
evaluation.json
evaluation.md
```

### JSON requirements

The JSON output must:

* use deterministic key and collection ordering;
* contain the complete evaluation configuration;
* contain dataset metadata;
* contain aggregate metrics;
* contain metrics by pattern;
* contain valid windows;
* contain exclusions;
* represent undefined WAPE as `null`;
* end with a newline.

### Markdown requirements

The Markdown output must summarize:

* dataset version;
* evaluation configuration;
* attempted, valid, and excluded windows;
* aggregate metrics;
* metrics by demand pattern;
* exclusions;
* baseline strengths;
* baseline weaknesses;
* implications for stockout exposure and reorder recommendations;
* explicit limitations;
* follow-up recommendations.

Generated JSON and Markdown artifacts remain outside version control.

The durable repository report must summarize the verified results and record:

* the generation command;
* the source commit;
* configuration;
* result-file checksums;
* test evidence;
* interpreted findings;
* limitations;
* follow-up decisions.

## 13. Developer Command

The initial command shape is:

```bash
uv run python -m opsmind.evaluation \
  --output-dir /tmp/opsmind-phase4-evaluation \
  --lookback-observations 7 \
  --horizon-days 7 \
  --minimum-training-observations 7
```

The command must:

* create the selected output directory when absent;
* refuse to overwrite existing result files unless `--force` is supplied;
* write only the two documented result files;
* print their paths;
* return exit status zero on success;
* return a nonzero status with a safe message on failure.

## 14. Persistence and Mutation Boundaries

Evaluation is read-only.

It must not:

* write to memory repositories;
* write to PostgreSQL;
* create or migrate database tables;
* mutate products;
* mutate inventory;
* mutate demand observations;
* create recommendation reviews;
* record approval or rejection decisions;
* append audit events.

No application repository is required for the governed synthetic evaluation.

Repository-backed evaluation may be considered in a future issue.

## 15. API Boundary

No HTTP evaluation endpoint will be introduced.

Rationale:

* Phase 4 requires reproducible engineering evidence, not a customer API;
* an API would expand the public contract before a product requirement exists;
* evaluation may involve larger reports inappropriate for the current synchronous API;
* a local developer command is easier to reproduce in CI;
* the existing production forecast endpoint remains unchanged.

## 16. Dependency Decision

No new runtime or development dependency will be added.

The implementation will use:

* `argparse`;
* `dataclasses`;
* `datetime`;
* `decimal`;
* `json`;
* `pathlib`;
* existing OpsMind domain models and forecast functions.

NumPy, pandas, scikit-learn, Typer, and Click are unnecessary for this bounded deterministic evaluation.

## 17. ADR Assessment

This issue does not require a new ADR because it does not change:

* the application’s runtime architecture;
* persistence ownership;
* schema ownership;
* an external API contract;
* cloud infrastructure;
* security boundaries;
* a major dependency;
* the established production forecast calculation.

This design document provides the durable evaluation-specific decision record.

A new ADR will be required if later work proposes:

* persisted evaluation state;
* a public evaluation API;
* distributed or background evaluation;
* a model registry;
* external experiment tracking;
* a new major numerical framework;
* production-data evaluation infrastructure.

## 18. Testing Strategy

Add focused tests for:

* dataset determinism;
* stable UUIDs and dates;
* each required demand pattern;
* duplicate and mismatched observation rejection;
* candidate-origin ordering;
* insufficient-history exclusions;
* incomplete-target exclusions;
* recorded-zero target validity;
* missing-date distinction;
* temporal leakage prevention;
* exact actual-demand sums;
* reuse of existing forecast behavior;
* signed-error convention;
* absolute-error correctness;
* MAE correctness;
* bias correctness;
* WAPE correctness;
* zero-denominator WAPE;
* aggregate and per-pattern metrics;
* deterministic JSON;
* deterministic Markdown;
* CLI argument validation;
* overwrite protection;
* successful artifact generation;
* absence of application-state mutation.

The complete existing test suite must continue to pass.

PostgreSQL integration validation will run as regression evidence, but no new PostgreSQL-specific evaluation behavior is required because this design uses synthetic, repository-independent data.

## 19. Security and Privacy

The evaluation uses only deterministic synthetic data.

It must contain no:

* personal data;
* customer data;
* company-confidential data;
* credentials;
* tokens;
* secrets;
* production identifiers.

Generated reports must not expose environment variables or local credentials.

## 20. Cost

The evaluation runs locally or in CI using a small fixed dataset.

Expected costs are limited to negligible CPU, memory, and disk use.

This issue introduces no:

* AWS cost;
* external API cost;
* managed-service cost;
* persistent storage cost.

## 21. Operational Considerations

The evaluation command is a developer and review tool, not an online production service.

It has no:

* uptime commitment;
* latency service level;
* production scheduling;
* alerting requirement;
* backup requirement;
* high-availability requirement.

Failures must be explicit and reproducible.

## 22. Limitations

This evaluation:

* measures only the deterministic synthetic dataset;
* does not prove real-world forecast accuracy;
* does not validate a learned model;
* does not model uncertainty;
* does not produce prediction intervals;
* does not estimate service-level impact;
* does not optimize safety stock;
* does not estimate supplier or ordering cost;
* does not independently validate downstream decision quality;
* does not establish production readiness.

Synthetic results may identify algorithmic strengths and weaknesses but cannot replace evaluation on governed real operational data.

## 23. Expected Baseline Findings

The design expects, but does not pre-claim, that the simple mean may:

* perform well on stable demand;
* lag systematic trends;
* smooth seasonal peaks and troughs;
* perform poorly after abrupt level shifts;
* produce difficult-to-interpret WAPE for all-zero demand;
* depend materially on lookback and horizon choices;
* require caution for intermittent demand.

These remain hypotheses until the implementation generates verified results.

## 24. Documentation Deliverables

This issue will update or create:

```text
AGENTS.md
README.md
ROADMAP.md
CHANGELOG.md
docs/01-architecture/forecast-evaluation-design.md
docs/05-evaluation/phase-4-baseline-forecast-evaluation.md
docs/09-status/current-status.md
docs/12-phase-reviews/phase-4-review.md
```

`ROADMAP.md` must not mark Phase 4 complete until the evaluation evidence and owner-accepted phase review exist.

## 25. Phase-Gate Decision

This design alone does not complete Phase 4.

Phase 4 completion requires:

* implementation;
* deterministic evaluation output;
* test and CI evidence;
* interpreted findings;
* documented limitations;
* explicit follow-up issues or accepted limitations;
* an owner-accepted Phase 4 Proceed, Revise, or Stop decision.

## 26. Alternatives Considered

### Checked-in CSV fixture

Rejected for the initial evaluation because a deterministic generator is more explicit, easier to validate, and avoids data-parsing concerns.

### Repository-backed evaluation

Deferred because the current phase requires reproducible governed evidence and does not require production-like state access.

### HTTP evaluation endpoint

Rejected because no product requirement justifies expanding the API contract.

### Persisted evaluation tables

Rejected because evaluation output is review evidence rather than operational application state.

### pandas or NumPy

Rejected because the bounded evaluation can be implemented clearly with standard-library types and exact decimal arithmetic.

### Separate implementation of the mean forecast

Rejected because duplicated calculation logic could drift from the production forecast behavior.

## 27. Design Decision

Decision: **Accepted by the repository owner; proceed with implementation.**

The design preserves the existing forecast and persistence boundaries while adding a deterministic, inspectable, and reproducible evaluation capability suitable for completing the Phase 4 gate.
