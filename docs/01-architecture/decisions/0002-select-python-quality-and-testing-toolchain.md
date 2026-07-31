# ADR-0002: Select Python Quality and Testing Toolchain

- Status: Proposed
- Date: 2026-07-31
- Decision owners: Anish Paudyal
- Related issues: #9, #10
- Related pull requests: The pull request implementing issue #10
- Supersedes: None
- Superseded by: None

## Context

OpsMind now has a reproducible Python 3.13 foundation, but no application code
exists yet. Formatting, linting, type checking, testing, and coverage must be
selected before application development begins so that the first implementation
work starts with a consistent quality baseline.

The repository uses `uv`, a committed `uv.lock`, and one root Python project.
The selected tools must support Python 3.13, native Apple Silicon development,
future backend and API work, and future data and machine-learning work without
selecting an application or test layout prematurely.

## Decision drivers

- Python 3.13 compatibility
- Native Apple Silicon compatibility
- Reproducibility through `uv.lock`
- Fast local feedback
- Configuration simplicity
- Diagnostic quality
- IDE integration
- CI suitability
- Backend and API suitability
- Data and ML suitability
- Maintenance burden
- Minimal tool overlap
- Learning and interview relevance

## Considered options

1. **Ruff, mypy, pytest, and pytest-cov.** This provides fast formatting,
   linting, import sorting, strict static typing, an extensible test runner, and
   integrated coverage with little responsibility overlap.
2. **Black, isort, Flake8, mypy, pytest, and pytest-cov.** This is mature and
   familiar, but uses three tools where Ruff can provide a coherent formatter,
   import sorter, and linter with less configuration and maintenance.
3. **Ruff, Pyright, pytest, and pytest-cov.** Pyright provides strong performance
   and editor integration, but mypy is more directly aligned with the selected
   Python-only project foundation and its learning goals.
4. **Ruff without a dedicated type checker.** This minimizes tooling but cannot
   enforce the strict first-party typing discipline required for future code.
5. **Standard-library `unittest`.** This avoids a third-party test runner but
   offers less concise test authoring, fixture support, and plugin integration
   than pytest.
6. **Direct coverage.py invocation.** This is capable and remains the underlying
   coverage engine, but pytest-cov provides a simpler test-and-coverage command
   contract.
7. **Separate `lint`, `type`, and `test` dependency groups.** This could reduce
   installation scope for specialized jobs, but adds synchronization and CI
   complexity before the repository has code large enough to benefit.
8. **Deferring the quality baseline.** This avoids immediate maintenance but
   allows inconsistent conventions and untyped code to accumulate from the
   beginning of application development.

## Decision

- Ruff is the formatter and linter, and it handles import sorting.
- mypy is the static type checker.
- pytest is the primary test runner.
- pytest-cov, backed by coverage.py, provides coverage integration.
- Ruff, mypy, pytest, and pytest-cov are direct development dependencies in one
  `dev` dependency group.
- Ruff and mypy target Python 3.13.
- Future first-party production code is strict-typed by default.
- Type-checking exceptions must be narrow, documented, and evidence-based.
- Global `ignore_missing_imports` is prohibited.
- Branch coverage begins with the first application code.
- No arbitrary coverage percentage is established before a meaningful baseline
  exists.
- Direct `uv` commands are documented initially; no Makefile, task runner, or
  wrapper scripts are introduced.
- CI will later reproduce the non-mutating local commands and become the
  authoritative merge gate.
- Pre-commit is deferred until application code and Python-quality CI exist.

## Rationale

The selected composition establishes complementary responsibilities without
duplicating formatters, import sorters, or lint frontends. Ruff gives rapid,
consistent feedback through a single formatter and linter; mypy establishes an
independent strict-typing boundary; and pytest plus pytest-cov supplies a common
test and branch-coverage workflow. All are compatible with the repository's
Python 3.13 and native Apple Silicon foundation and can run locally and in CI
from the same locked dependency group.

The alternatives either increase tool overlap and maintenance, weaken typing or
testing capabilities, split a small baseline unnecessarily, or defer safeguards
until inconsistencies are more expensive to correct.

## Consequences

### Positive

- Formatting is consistent before application code is introduced.
- Lint and import checks provide fast feedback.
- Strict typing establishes early type-safety discipline.
- Testing and coverage tooling are reproducible.
- Tool configuration resides in one `pyproject.toml` file.
- Direct tools reside in one locked development group.
- Local and future CI commands remain aligned.
- Formatter and linter overlap is reduced compared with separate tools.

### Negative

- Contributors must install the locked development environment.
- Strict mypy may require future narrow exceptions or stubs.
- Ruff cannot load arbitrary Flake8 plugins.
- The lockfile and configuration require maintenance.
- Coverage configuration may need refinement after a source layout exists.

### Neutral

- Tool patch versions are fixed by `uv.lock`.
- No source or test layout is selected.
- No coverage percentage is selected.
- CI and pre-commit remain separate future work.

## Risks and mitigations

- **A required Ruff plugin is unavailable:** reconsider the tool composition if
  the needed rule cannot be expressed through Ruff's supported rules.
- **mypy conflicts with a future dependency:** use stubs or narrow exceptions,
  then reconsider the checker if the incompatibility becomes systemic.
- **Strict typing creates excessive friction:** measure the friction and adjust
  narrow rules rather than disabling typing globally.
- **Coverage becomes a vanity metric:** combine measured coverage with
  risk-based tests and review of meaningful behavior.
- **Tools differ between local and CI:** use locked dependencies and identical
  non-mutating commands.
- **Generated caches or reports are committed:** maintain minimal ignore rules
  and verify Git tracking during validation.
- **Pre-commit duplicates CI or slows commits:** defer it until a measured
  benefit justifies the additional workflow.

## Validation

The decision is validated through locked installation with `uv`, tool-version
checks, successful configuration parsing, and a temporary typed module and
pytest test stored outside the repository. Ruff formatting and lint checks,
mypy strict validation, pytest execution, and pytest-cov branch-coverage
collection must pass against that fixture. Synchronization must be idempotent,
repository checks must pass, and no permanent application or test files may be
introduced.

## Reconsideration triggers

- A required Ruff plugin or rule is unavailable.
- mypy performance or ecosystem compatibility becomes materially problematic.
- Pyright or another checker demonstrates a repository-wide benefit.
- The Python minor-version policy changes.
- Data or ML dependencies introduce incompatible native or typing constraints.
- The repository becomes a workspace or monorepo.
- CI runtime justifies dependency-group or job separation.
- A task runner becomes valuable because command orchestration is repeatedly
  duplicated.

## Implementation notes

- No application directory is selected.
- No test directory is selected.
- No framework plugin is installed.
- No async-test plugin is installed.
- No application-specific lint suppression is introduced.
- CI implementation is a separate issue.
- Pre-commit implementation is deferred.
- Exact versions are determined by `uv.lock`.

## References

- [ADR-0000: Use Architecture Decision Records](0000-use-architecture-decision-records.md)
- [ADR-0001: Select Python Toolchain](0001-select-python-toolchain.md)
- [Architecture Decision Record index](README.md)
- [Contribution guide](../../../CONTRIBUTING.md)
- [Python project configuration](../../../pyproject.toml)
- [Current project status](../../09-status/current-status.md)
- GitHub issue #9: Investigate Python quality and testing standards
- GitHub issue #10: Establish Python quality and testing toolchain
