# Contributing to OpsMind

OpsMind uses an issue-first, review-based development workflow. The goal is to
keep product decisions, implementation, evidence, and learning connected.

## Standard Workflow

1. Create or select an issue with a clear problem, scope, and acceptance
   criteria.
2. Confirm that the work belongs in the current roadmap phase.
3. Create a short-lived branch from the default branch.
4. Make the smallest coherent change that satisfies the issue.
5. Run the relevant checks and document the results.
6. Open a pull request linked to the issue.
7. Address review findings on the same branch.
8. Merge only after the required human review.

## Branch Names

Use a descriptive prefix and short topic:

- `feature/<topic>`
- `fix/<topic>`
- `docs/<topic>`
- `chore/<topic>`
- `investigation/<topic>`

## Definition of Ready

An implementation issue is ready when it has:

- A problem statement
- An explicit in-scope and out-of-scope boundary
- Verifiable acceptance criteria
- Known dependencies
- Security, data, cost, and documentation considerations

## Definition of Done

A change is done when:

- Acceptance criteria are met.
- Relevant automated and manual checks pass.
- User-facing, operational, and architecture documentation is current.
- Security and data-handling implications were reviewed.
- The pull request explains what changed and how it was verified.
- Follow-up work is recorded in separate issues.

## Commit and Pull Request Expectations

- Keep commits focused and messages written in the imperative mood.
- Do not combine unrelated cleanup with a feature or fix.
- Include test results in the pull request.
- Call out migrations, compatibility changes, operational impact, and known
  limitations.
- Do not commit generated credentials, local environment files, build output,
  or large raw datasets.

## Documentation

Durable knowledge belongs in the repository, not only in chat history. Update
the relevant document when a decision changes product behavior, architecture,
operations, security, cost, or the learning narrative.

## Architecture Decision Records

Material technical or architectural decisions require an Architecture Decision
Record under [docs/01-architecture/decisions](docs/01-architecture/decisions/README.md).
Create and review ADRs through the normal branch and pull-request workflow,
keep them Proposed until the repository owner accepts them, and update the ADR
index whenever a record or its status changes. Accepted ADRs govern subsequent
work unless they are superseded through the documented ADR process.

## Python Quality

Synchronize the locked development environment before running Python quality
checks:

```bash
uv sync --locked --group dev
```

Verify that the lockfile remains current:

```bash
uv lock --check
```

Run the non-mutating validation commands locally:

```bash
uv run ruff format --check .
uv run ruff check --no-cache .
uv run mypy --no-incremental .
uv run pytest -p no:cacheprovider
```

The pytest command may report that no tests were collected until permanent
tests are introduced. After first-party source and tests exist, routine
coverage validation will use:

```bash
uv run pytest -p no:cacheprovider \
  --cov \
  --cov-branch \
  --cov-report=term-missing \
  --cov-report=xml
```

Source-mutating Ruff commands are explicit developer actions:

```bash
uv run ruff format .
uv run ruff check --fix .
```

`ruff check --unsafe-fixes` is not part of the standard workflow. CI will later
reproduce the non-mutating commands and become the authoritative merge gate. No
Makefile, task runner, shell wrapper, Python wrapper, or pre-commit hook is
introduced yet.

## Security

Report suspected credential exposure or sensitive-data leakage privately to the
repository owner. Do not paste secrets into an issue or pull request.
