# ADR-0001: Select Python Toolchain

- Status: Accepted
- Date: 2026-07-31
- Decision owners: Anish Paudyal
- Related issues: #2, #3, #4, #5
- Related pull requests: The pull request implementing issue #5
- Supersedes: None
- Superseded by: None

## Context

OpsMind needs a reproducible Python foundation for local development and future
continuous integration without altering unrelated or system-managed Python
installations. The development machine is an Apple M4 using native `arm64`, but
several Python distributions are available: `python` resolves to Miniconda,
`python3` resolves first to Homebrew, and Xcode Command Line Tools also provides
Python. Bare `python`, `python3`, and `python3.13` commands therefore do not form
a reproducible project contract.

Homebrew-managed `uv 0.11.28` is installed. A `uv`-managed CPython 3.13.14
interpreter is also installed and has been verified as a native `arm64`
executable. The repository requires repeatable local and future CI setup while
keeping OpsMind isolated from Miniconda base, Homebrew-managed Python, and
system-managed interpreters.

## Decision drivers

- Reproducibility
- Interpreter isolation
- Apple Silicon compatibility
- Local and CI consistency
- Deterministic dependency locking
- Clear developer onboarding
- Low tool complexity
- Future FastAPI, data, ML, and AI compatibility
- Avoidance of system and Conda environment pollution
- Maintainability

## Considered options

1. **`uv` with managed CPython 3.13.** Centralizes interpreter discovery,
   environment synchronization, dependency management, locking, and command
   execution while providing a native Apple Silicon interpreter isolated from
   other installations.
2. **Miniconda.** Provides capable environment management and is common in data
   and ML work, but using the existing base environment would couple OpsMind to
   unrelated packages and user configuration. A separate Conda workflow would
   also duplicate the selected dependency-management responsibilities.
3. **Homebrew-managed Python.** Provides a native Apple Silicon build and easy
   local installation, but Homebrew upgrades can change the interpreter outside
   the repository workflow and make CI parity less direct.
4. **Xcode Command Line Tools Python.** Is already present, but is controlled by
   operating-system developer tooling and is not an appropriate project runtime
   or dependency target.
5. **Standard-library `venv` plus `pip`.** Uses familiar built-in tools, but
   requires separate interpreter provisioning and additional conventions or
   tools for deterministic locking and synchronization.
6. **Poetry.** Offers dependency management, locking, and packaging workflows,
   but adds a packaging-oriented tool when the initial root project is
   intentionally non-packaged and still requires an interpreter strategy.
7. **Python 3.12.** Has broad current ecosystem support, but would not use the
   approved, verified 3.13 toolchain and would shorten the useful lifetime of
   the initial version constraint.
8. **Python 3.14.** Is newer, but adopting it before the future FastAPI, data,
   ML, and AI dependency set is selected would create avoidable compatibility
   risk without a demonstrated project benefit.
9. **A packaged Python project from the beginning.** Would establish import and
   distribution structure early, but would prematurely select an application
   layout and build configuration before those decisions are in scope.

No claim is made that every future dependency has already been validated on
Python 3.13. Compatibility will be checked as dependencies are proposed.

## Decision

OpsMind will use `uv` for Python discovery, environment synchronization,
dependency management, locking, and command execution. The repository will use
`uv`-managed CPython 3.13 and declare supported Python as `>=3.13,<3.14`.

The project will use a repository-local `.venv`, commit `.python-version` and
`uv.lock`, and keep the initial root project non-packaged with
`[tool.uv] package = false`. OpsMind dependencies must not be installed into
Miniconda base, Homebrew Python, or Xcode Python. Contributors should prefer
`uv run` and other project-aware `uv` commands over ambiguous bare Python
commands. Future CI will use the same Python minor version.

## Rationale

The selected approach provides one low-complexity workflow for interpreter
selection, isolated environments, deterministic dependency locking, and command
execution. It uses a verified native Apple Silicon runtime, avoids coupling the
project to machine-specific PATH order, and can be reproduced in CI. Python
3.13 balances a current supported runtime with a deliberate requirement to
validate future framework, data, ML, and AI dependencies before adoption. A
non-packaged root avoids committing to a source or distribution layout before
application architecture is approved.

## Consequences

### Positive

- Interpreter selection is reproducible.
- The committed lockfile provides deterministic dependency state.
- The project remains isolated from unrelated Python installations.
- Local execution uses a native Apple Silicon runtime.
- Onboarding and future CI parity are simpler.
- Python tooling is centralized in `uv`.

### Negative

- The project gains an additional reliance on `uv`.
- `uv.lock` must remain synchronized with project metadata.
- Contributors must install `uv`.
- Python 3.13 compatibility must be validated when dependencies are selected.

### Neutral

- `.venv` is local and uncommitted.
- Exact Python patch versions may advance while the supported minor remains
  3.13.
- The project can become packaged later.

## Risks and mitigations

- **A required dependency lacks Python 3.13 support:** Validate dependencies
  before adoption and reconsider this ADR if required.
- **PATH selects the wrong interpreter:** Use project-aware `uv` commands.
- **`.venv` is accidentally committed:** Enforce `.gitignore` coverage and
  repository validation.
- **The lockfile drifts:** Require lockfile checks in future CI.
- **Local and CI versions diverge:** Use the same Python minor constraint and
  lockfile in both environments.
- **Python 3.14 is adopted prematurely:** Upgrade only after ecosystem
  validation demonstrates a concrete benefit.

## Validation

The decision is validated by `pyproject.toml`, `.python-version`, `uv.lock`, a
`uv`-created `.venv`, direct interpreter-provenance checks, idempotent
synchronization, repository checks, and confirmation that no application
dependencies were added.

## Reconsideration triggers

- A required dependency lacks Python 3.13 support.
- CI or deployment runtime requirements change.
- Python 3.14 support is validated and offers a concrete benefit.
- The repository becomes a Python workspace or monorepo.
- The project requires packaging, distribution, or console entry points.
- A different tool demonstrably improves reproducibility or security.

## Implementation notes

- The initial project version is `0.1.0`.
- The initial root project is non-packaged.
- No application source layout is selected by this ADR.
- No runtime or development dependencies are selected by this ADR.
- Backend framework, testing, linting, and packaging decisions remain future
  work.

## References

- [ADR-0000: Use Architecture Decision Records](0000-use-architecture-decision-records.md)
- [ADR index](README.md)
- [Repository README](../../../README.md)
- [Contribution guide](../../../CONTRIBUTING.md)
- [Roadmap](../../../ROADMAP.md)
- [Current project status](../../09-status/current-status.md)
