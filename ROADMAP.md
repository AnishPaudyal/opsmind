# OpsMind Roadmap

The roadmap is phase-gated. A later phase may be explored, but implementation
should not bypass the exit criteria of the current phase.

## Phase Status

| Phase | Focus | Status |
| --- | --- | --- |
| 0 | Project definition, scope, governance, and readiness | Complete |
| 1 | Repository and local development foundation | Current |
| 2 | Product data and transactional backend | Planned |
| 3 | Web workflow for product and demand operations | Planned |
| 4 | Forecasting baseline and evaluation | Planned |
| 5 | Stockout risk and reorder recommendations | Planned |
| 6 | Decision approval, rejection, and audit history | Planned |
| 7 | Testing, security, and observability hardening | Planned |
| 8 | AWS foundation and first cloud deployment | Planned |
| 9 | Data engineering and analytical pipelines | Planned |
| 10 | MLOps and model lifecycle | Planned |
| 11 | Advanced AI, retrieval, and event-driven capabilities | Planned |
| 12 | Production-readiness review and portfolio packaging | Planned |

## Phase 1 Exit Criteria

Phase 1 is complete when:

- Repository governance is merged.
- Local development prerequisites and setup are documented.
- The initial application architecture is reviewed.
- Quality checks can run consistently.
- Secret prevention and dependency-management practices are established.
- The first implementation issue is ready and approved.

## First Vertical Slice

Phases 2 through 6 will build one coherent workflow:

`product data -> demand history -> forecast -> stockout risk -> reorder
recommendation -> approval or rejection -> audit record`

## Phase-Gate Rule

Each phase review must record:

- Delivered capabilities
- Validation evidence
- Documentation changes
- Security, cost, and operational findings
- Deferred risks and follow-up issues
- A clear proceed, revise, or stop decision
