# Risk, Cost, Security, and Responsible-AI Baseline

Last updated: 2026-07-30

## Security Baseline

- Use least-privilege access for people, workloads, and automation.
- Keep credentials in approved secret stores or local ignored environment files.
- Use synthetic or explicitly approved sample data.
- Validate input at trust boundaries.
- Preserve authorization and audit evidence for decisions.
- Review dependencies and container images before release.
- Do not expose cloud resources publicly without a documented requirement and
  review.

## Cost Baseline

- No AWS resource is created before the cloud phase is approved.
- Cloud resources must have an owner, purpose, environment, and cost tag.
- Budgets and alerts must exist before nontrivial workloads are deployed.
- Prefer bounded experiments and automatic shutdown for learning environments.
- Record material cost assumptions in architecture decisions and phase reviews.
- Delete unused resources through reviewed, recoverable procedures.

## Responsible-AI Baseline

- Model output is decision support, not autonomous authority.
- Users must be able to distinguish observed facts, estimates, rules, and
  generated explanations.
- Recommendations must include relevant evidence, uncertainty, and limitations.
- A human approves or rejects consequential reorder actions.
- Decisions, reasons, model versions, and major inputs must be auditable.
- Evaluation must include failure cases and data-quality degradation.
- The system must define fallback behavior when a model or supporting service is
  unavailable.

## Initial Risk Register

| Risk | Initial control |
| --- | --- |
| Scope expands into disconnected demos | Phase gates and vertical-slice roadmap |
| Credentials enter source control | Ignore rules, review checklist, repository checks |
| Cloud experimentation creates surprise cost | No early resources, budgets, tagging, shutdown |
| Synthetic results are presented as production proof | Explicit status and evidence language |
| Model output is trusted without context | Uncertainty, explanations, human approval, audit |
| Documentation diverges from behavior | Definition of done and phase reviews |
| Technology choices add unnecessary operations | Entry conditions and alternatives review |

## Incident Rule

Suspected credential or sensitive-data exposure takes priority over feature
work. Stop propagation, preserve necessary evidence, rotate affected
credentials, assess impact, and document the corrective action without exposing
the secret again.
