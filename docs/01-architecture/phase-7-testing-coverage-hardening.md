# Phase 7A Testing and Coverage Hardening

Status: Implemented and final validation passed on Issue #56 branch; owner review pending
Date: 2026-08-07
Governed by: Issue #56
Canonical base: `c010c4047f849f57444d31b72213a48c80ea5f28`

## Purpose

This workstream establishes a reproducible testing and coverage baseline, reviews uncovered behavior by risk, hardens consequential gaps, resolves the known TestClient dependency warning, and introduces an evidence-based coverage regression gate.

It does not implement authentication, authorization, observability, readiness, AWS, cloud deployment, or Phase 8 behavior.

## Measured progression

| State | Tests | Statement coverage | Branch coverage | Combined coverage |
| --- | ---: | ---: | ---: | ---: |
| Untouched Phase 7A baseline | 499 | 96.34% | 82.96% | 94.31% |
| After domain-invariant hardening | 503 | 97.02% | 86.73% | 95.45% |
| Final hardened state | 511 | 97.42% | 87.83% | 95.96% |

The combined values use the same Coverage.py model as the repository's branch-enabled report: executable statements and branch destinations both contribute execution opportunities.

## Risk-based hardening

The workstream deliberately prioritized consequential gaps instead of attempting to maximize every module's percentage.

Added regression coverage includes:

- recommendation audit-event invariants;
- recommendation decision and review invariants;
- API duplicate-creation conflict translation;
- API decision-value error translation;
- PostgreSQL detection of non-contiguous audit history;
- PostgreSQL detection of incomplete terminal history;
- PostgreSQL detection of review/audit quantity drift;
- PostgreSQL detection of pending-review/terminal-event inconsistency;
- PostgreSQL detection of terminal audit timestamp drift.

After hardening:

- recommendation-review API: 100% line and branch coverage;
- recommendation audit domain: 100% line and branch coverage;
- recommendation review domain: 100% line and branch coverage;
- PostgreSQL workflow repository: 94.29% line and 96.67% branch coverage.

Remaining uncovered behavior is not treated as automatically defective. Evaluation-support paths, defensive branches constrained by database invariants, and other lower-risk paths remain subject to future risk-based review rather than coverage-percentage chasing.

## TestClient warning disposition

The development-only direct dependency changed from `httpx` to `httpx2`.

OpsMind does not directly import either package; API and PostgreSQL application tests continue to use FastAPI/Starlette `TestClient`.

The previously observed Starlette deprecation warning is absent from focused and complete test runs after the dependency change.

## Coverage regression gate

The proposed Phase 7A numerical gate is:

**95.00% combined coverage with branch measurement enabled.**

Rationale:

1. The untouched baseline was approximately 94.31% combined.
2. Risk-based Batch 1 increased the result to approximately 95.45%.
3. Final persistence/API hardening increased it to approximately 95.96%.
4. A 95% floor therefore rejects the pre-hardening posture.
5. It preserves approximately 0.96 percentage points of headroom below the final hardened result.
6. A 96% floor would exceed the measured 95.96% result and would therefore be an unjustified rounding-based threshold.
7. Critical workflow confidence is additionally protected by explicit regression tests rather than allowing unrelated high-coverage modules to substitute for consequential behavior.

The standard coverage command and Python-quality CI use `--cov-fail-under=95`.

Coverage reporting uses two decimal places to make the actual result visible.

## CI policy

Python-quality CI remains the authoritative merge gate.

Its test step now runs the complete pytest suite with:

- `--cov=opsmind`;
- branch measurement;
- terminal missing-line reporting;
- XML reporting;
- `--cov-fail-under=95`.

No new coverage service, external quality platform, or CI dependency is introduced.

## Evidence

Final hardened validation:

- 511 tests passed;
- zero unintended skips;
- Ruff formatting passed;
- Ruff lint passed;
- strict mypy passed for 107 source files;
- PostgreSQL migration head: `0006_workflow_persistence`;
- statement coverage: 97.42%;
- branch coverage: 87.83%;
- combined coverage: approximately 95.96%;
- no Starlette TestClient deprecation warning observed.

Final hardened coverage-measurement hashes:

- terminal/coverage log: `cd61486fdec0046cb42a2255cf8324754d0c91bb1c01507bb8d9354496444296`
- coverage XML: `92229d0152cbdf78d8a0b059998f242f6b7e00f04bf413a74fc8ef1aaba01276`
- coverage data: `70240cbf728cd40d952a634205746cdb5f42350f6e2822bf1ba8b56b701616af`

Final CI-equivalent validation also passed after the coverage policy and CI gate were applied:

- 511 tests passed;
- required combined coverage of 95.00% was satisfied at 95.96%;
- Ruff formatting and linting passed;
- strict mypy passed for 107 source files;
- PostgreSQL migrations reached `0006_workflow_persistence`;
- no Starlette TestClient deprecation warning was observed;
- PostgreSQL test resources were removed after validation.

Final CI-equivalent validation artifact:

- terminal log: `/tmp/opsmind-phase7a-final-ci-equivalent.txt`
- SHA-256: `c6a73f5354eb88401ad08bb8d6f73ba98a0a83e9de31ace625f03e1d6c3246b5`

## Remaining Phase 7 boundaries

This workstream does not authorize or implement:

- authenticated principals;
- authorization or RBAC;
- ADR-0006;
- request/correlation-ID middleware;
- runtime observability;
- readiness probes;
- AWS or cloud deployment;
- production monitoring or alerting;
- HA/DR;
- external ordering;
- production-readiness approval.

Those remain governed by the accepted Phase 7 sequence.

## Acceptance

Technical implementation and final CI-equivalent validation are complete. Pull-request review and repository-owner acceptance remain pending under Issue #56.
