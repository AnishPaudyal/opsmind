# OpsMind Roadmap

The roadmap is phase-gated. Implementation may explore or deliver capability
associated with a later phase, but early delivery does not make that phase
formally complete.

A phase is complete only when:

* its exit criteria are satisfied;
* its validation and limitations are documented;
* its phase review records a Proceed, Revise, or Stop decision;
* the repository owner accepts that review.

The accepted phase mapping and historical reconciliation are recorded in
[Roadmap Phase Reconciliation](docs/00-project-foundation/roadmap-phase-reconciliation.md).

## Phase Status

| Phase | Focus                                                 | Formal status | Implementation note                                                 |
| ----- | ----------------------------------------------------- | ------------- | ------------------------------------------------------------------- |
| 0     | Project definition, scope, governance, and readiness  | Complete      | Reviewed in `phase-0-review.md`                                     |
| 1     | Repository and local development foundation           | Complete      | Delivered and retrospectively reviewed                              |
| 2     | Product data and transactional backend                | Complete      | Delivered and retrospectively reviewed                              |
| 3     | Web workflow for product and demand operations        | Complete      | Delivered and retrospectively reviewed                              |
| 4     | Forecasting baseline and evaluation                   | Complete      | Owner-accepted Phase 4 review under Issue #48                       |
| 5     | Stockout risk and reorder recommendations             | Complete      | Owner-accepted Phase 5 review under Issue #50                       |
| 6     | Decision approval, rejection, and audit history       | Complete      | Owner-accepted Phase 6 review under Issue #52                       |
| 7     | Testing, security, and observability hardening        | Complete      | Owner-accepted Phase 7 review merged through PR #65                 |
| 8     | Cloud deployment and first product delivery             | Current       | Phase 8A and Phase 8B Complete; Phase 8C not started               |
| 9     | Data engineering and analytical pipelines             | Planned       | Not started                                                         |
| 10    | MLOps and model lifecycle                             | Planned       | Not started                                                         |
| 11    | Advanced AI, retrieval, and event-driven capabilities | Planned       | LLM, RAG, tool calling, and LangGraph not started                   |
| 12    | Production-readiness review and portfolio packaging   | Planned       | No production-readiness approval exists                             |

## Status Meanings

* **Complete**: exit criteria and an accepted phase review are recorded.
* **Current**: this is the active governed phase; its accepted issue boundary
  determines whether design, implementation, or review work is permitted.
* **Gate pending**: relevant implementation exists, but preceding gates, exit
  criteria, or the phase review are incomplete.
* **Planned**: the phase has not been formally opened.

Implementation status and formal phase status are intentionally separate. A
merged capability is evidence for a phase review; it is not a substitute for
that review.

## First Vertical Slice

Phases 2 through 6 form one coherent workflow:

`product data -> demand history -> forecast -> stockout risk -> reorder
recommendation -> approval or rejection -> audit record`

Parts of Phases 5 and 6 were delivered before the formal Phase 4 evaluation
gate was completed. Their later owner-accepted reviews completed both gates;
the early-delivery history remains relevant without changing their current
Complete status.

## Phase 1 Exit Criteria

Phase 1 is complete when:

* repository governance is merged;
* local development prerequisites and setup are documented;
* Python version and dependency management are reproducible;
* formatting, linting, type checking, and testing run consistently;
* equivalent quality checks run in CI;
* secret-prevention and dependency-management practices are established;
* the first backend implementation issue is ready and approved;
* a Phase 1 review records an accepted decision.

## Phase 2 Exit Criteria

Phase 2 is complete when:

* the application has a reviewed modular backend structure;
* product and inventory contracts are implemented;
* repository interfaces separate domain and API behavior from storage details;
* an isolated in-memory repository remains available;
* PostgreSQL provides durable product and inventory persistence;
* Alembic owns schema creation and migration;
* runtime application code does not create or migrate tables;
* transaction, rollback, constraint, sharing, and restart behavior are tested;
* a Phase 2 review records an accepted decision.

## Phase 3 Exit Criteria

Phase 3 is complete when:

* product, inventory, and demand operations are exposed through stable HTTP
  contracts;
* validation and business conflicts do not expose storage implementation
  details;
* demand batches are stored atomically;
* demand history is returned chronologically with deterministic filtering;
* operational state supports isolated memory and durable PostgreSQL modes;
* API behavior remains consistent across supported persistence backends;
* a Phase 3 review records an accepted decision.

## Phase 4 Exit Criteria

Phase 4 is complete when:

* the deterministic forecast baseline remains reproducible;
* an approved evaluation dataset or deterministic dataset-generation method is
  documented;
* temporal evaluation prevents future observations from leaking into training
  inputs;
* at least one approved forecast-error metric is implemented and explained;
* baseline results are measured and reproducible;
* limitations for trend, seasonality, intermittent demand, uncertainty, and
  decision use are documented;
* evaluation findings produce explicit follow-up issues or an accepted decision;
* a Phase 4 review records an accepted Proceed, Revise, or Stop decision.

Issue #48 implements the evaluation portion with deterministic synthetic data,
temporal no-leakage windows, MAE, bias, WAPE, and reproducible reports. The
repository owner accepted the Phase 4 Proceed decision on 2026-08-06, completing
the Phase 4 gate in the merged repository state.

## Phase 5 Exit Criteria

The owner accepted the Phase 5 `Proceed` decision under Issue #50 on
2026-08-07. Phase 5 is Complete.

Phase 5 is complete when:

* stockout exposure uses documented and reproducible evidence;
* reorder recommendations preserve the evidence used to produce them;
* quantity and rounding policies are explicit and tested;
* deterministic behavior is distinguished from probability, calibrated risk,
  or learned prediction;
* decision-quality evaluation is completed or its absence is explicitly
  accepted with documented limitations;
* supplier, cost, pack-size, safety-stock, service-level, and ordering
  exclusions remain explicit unless separately implemented;
* a Phase 5 review records an accepted Proceed, Revise, or Stop decision.

The deterministic stockout-exposure and reorder-recommendation APIs were
delivered ahead of the formal gate. Issue #50 evaluated the governed
deterministic behavior, recorded reproducible evidence, documented the
decision-quality limitation, and received an owner-accepted `Proceed` decision
on 2026-08-07. In the merged repository state, Phase 5 is Complete.

## Phase 6 Exit Criteria

Phase 6 cannot complete before Phase 5.

Phase 6 is complete when:

* actionable recommendation snapshots are immutable after creation;
* each review begins pending and permits only one terminal approval or
  rejection;
* normalized retries are idempotent;
* changed or opposite terminal retries conflict without mutating state;
* review state, terminal decisions, and matching audit events share one atomic
  transaction boundary;
* audit events have deterministic ordering;
* supported PostgreSQL state is shared and survives application restart;
* supported memory state remains isolated and restart-volatile;
* application-created PostgreSQL repositories share application-owned
  infrastructure without taking ownership of explicitly injected resources;
* authentication, authorization, actor verification, tamper evidence, external
  ordering, and compliance limitations remain explicit;
* a Phase 6 review records an accepted Proceed, Revise, or Stop decision.

The review workflow, ordered audit history, PostgreSQL schema, PostgreSQL
repository, and application integration are delivered. The repository owner
accepted the Phase 6 `Proceed` review under Issue #52 on 2026-08-07, completing
the Phase 6 gate.

## Phase-Gate Rule

Each phase review must record:

* delivered capabilities;
* validation evidence;
* documentation changes;
* security, privacy, cost, data, and operational findings;
* deferred risks and follow-up issues;
* a clear Proceed, Revise, or Stop decision.

Work must not claim deployment, security, model quality, compliance, or
production readiness beyond the evidence actually reviewed.

## Current Direction

**Phase 8 — Cloud deployment and product delivery** is Current. Phase 8A
containerization completed through PR #69. Phase 8B zero-cost cloud backend is
Complete: the repository foundation, owner-controlled cloud bootstrap, Render
Blueprint, immutable GHCR publication, protected migration and deployment, and
live health/readiness/authentication smoke evidence are recorded under Issue
#70 and the Phase 8B review. Phase 8C has not started.

Phase 7A testing and coverage hardening, Issue #58 observability/readiness, and
the accepted ADR-0006 security implementation are complete and merged. Issue
#64 integrates that evidence, and the repository owner accepted its `Proceed`
decision on 2026-08-09. PR #65 merged the accepted review, completing Phase 7.

The repository owner accepted ADR-0007 on 2026-08-10. It defines a genuine
zero-recurring-cost portfolio deployment and first integrated frontend
architecture. AWS remains a reference translation and separate LocalStack
skills track, not a deployment claim. Phase 8A API containerization is merged.
The Phase 8B gate defines the backend account, identity, database, registry,
deployment, secret, and IaC boundaries. Its completed evidence includes the
backend trust adaptation, PostgreSQL cloud hardening, ZITADEL/HCP Terraform,
Neon persistence, the reviewed Render Blueprint, public immutable GHCR release,
and protected migration/deploy/smoke orchestration. Frontend, Phase 8C–8E work,
and production-readiness approval remain subject to their documented gates.
Phase 9 data, Phase 10 MLOps, and Phase 11 LLM/RAG/LangGraph remain Planned.

Detailed current evidence and next-work boundaries live in
[Current Status](docs/09-status/current-status.md).
