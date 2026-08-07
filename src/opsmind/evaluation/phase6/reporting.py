"""Stable JSON and Markdown reporting for the Phase 6 evaluator."""

import json
from dataclasses import asdict

from opsmind.evaluation.phase6.evaluation import Phase6Evaluation

EVALUATION_TYPE = "deterministic workflow-policy conformance"
GOVERNED_BY = "Issue #52"

LIMITATIONS = (
    "decided_by is caller supplied and unverified",
    "no user authentication",
    "no role-based authorization",
    "no verified reviewer identity",
    "audit actor identity may be spoofed by a caller",
    "audit events are not cryptographically signed",
    "audit events are not hash chained",
    "storage is not tamper-evident",
    "no compliance-ledger guarantee",
    "no approved retention/compliance policy",
    "approval does not create a purchase order",
    "approval does not perform an external business action",
    "approval does not reserve or mutate inventory",
    "no Phase 7 security-hardening claim",
    "no deployment or production-readiness claim",
)

POSTGRESQL_EVIDENCE_NOTE = (
    "PostgreSQL atomicity, row-lock concurrency, sharing, and restart durability "
    "are validated separately by real PostgreSQL integration tests; this "
    "deterministic evaluator does not claim to prove those backend guarantees."
)


def render_json(evaluation: Phase6Evaluation) -> str:
    """Render stable machine-readable Phase 6 evidence."""
    payload = {
        "dataset_version": evaluation.dataset_version,
        "evaluation_type": EVALUATION_TYPE,
        "governed_by": GOVERNED_BY,
        "summary": {
            "scenario_count": evaluation.scenario_count,
            "passed_scenarios": evaluation.passed_scenarios,
            "failed_scenarios": evaluation.failed_scenarios,
            "approval_scenarios": evaluation.approval_scenarios,
            "rejection_scenarios": evaluation.rejection_scenarios,
            "idempotent_retry_scenarios": evaluation.idempotent_retry_scenarios,
            "expected_conflict_scenarios": evaluation.expected_conflict_scenarios,
            "expected_output_mismatches": evaluation.expected_output_mismatches,
            "snapshot_preservation_failures": (
                evaluation.snapshot_preservation_failures
            ),
            "terminal_cardinality_failures": (evaluation.terminal_cardinality_failures),
            "retry_idempotency_failures": evaluation.retry_idempotency_failures,
            "conflict_mutation_failures": evaluation.conflict_mutation_failures,
            "audit_order_failures": evaluation.audit_order_failures,
            "memory_isolation_failures": evaluation.memory_isolation_failures,
        },
        "scenarios": [asdict(result) for result in evaluation.results],
        "postgresql_evidence_note": POSTGRESQL_EVIDENCE_NOTE,
        "limitations": list(LIMITATIONS),
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _display(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, tuple):
        return ", ".join(str(item) for item in value)
    return str(value)


def render_markdown(evaluation: Phase6Evaluation) -> str:
    """Render stable human-readable Phase 6 evidence."""
    lines = [
        "# Phase 6 Deterministic Workflow Evaluation",
        "",
        f"- Dataset: `{evaluation.dataset_version}`",
        f"- Evaluation type: {EVALUATION_TYPE}",
        f"- Governed by: {GOVERNED_BY}",
        "",
        "## Summary",
        "",
        f"- Scenarios: {evaluation.scenario_count}",
        f"- Passed: {evaluation.passed_scenarios}",
        f"- Failed: {evaluation.failed_scenarios}",
        f"- Approval outcomes: {evaluation.approval_scenarios}",
        f"- Rejection outcomes: {evaluation.rejection_scenarios}",
        f"- Idempotent retry scenarios: {evaluation.idempotent_retry_scenarios}",
        f"- Expected conflict scenarios: {evaluation.expected_conflict_scenarios}",
        f"- Expected-output mismatches: {evaluation.expected_output_mismatches}",
        (
            "- Snapshot-preservation failures: "
            f"{evaluation.snapshot_preservation_failures}"
        ),
        (
            "- Terminal-cardinality failures: "
            f"{evaluation.terminal_cardinality_failures}"
        ),
        f"- Retry-idempotency failures: {evaluation.retry_idempotency_failures}",
        f"- Conflict-mutation failures: {evaluation.conflict_mutation_failures}",
        f"- Audit-order failures: {evaluation.audit_order_failures}",
        f"- Memory-isolation failures: {evaluation.memory_isolation_failures}",
        "",
        "## Scenario Results",
        "",
        (
            "| Scenario | Final status | Decision | Approved qty | Events | "
            "Sequences | Conflict | Result |"
        ),
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]

    for result in evaluation.results:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{result.name}`",
                    f"`{result.actual_review_status}`",
                    _display(result.actual_decision_type),
                    _display(result.actual_approved_quantity),
                    "<br>".join(result.actual_event_types),
                    ", ".join(str(item) for item in result.actual_sequences),
                    "yes" if result.conflict_observed else "no",
                    "PASS" if result.passed else "FAIL",
                )
            )
            + " |"
        )

    lines.extend(
        (
            "",
            "## Evidence Boundary",
            "",
            POSTGRESQL_EVIDENCE_NOTE,
            "",
            "## Explicit Limitations",
            "",
        )
    )
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.extend(
        (
            "",
            "## Interpretation",
            "",
            (
                "A passing run establishes deterministic workflow-policy conformance "
                "for the governed synthetic scenarios. It does not establish "
                "authentication, authorization, cryptographic integrity, compliance "
                "certification, distributed exactly-once processing, disaster "
                "recovery, high availability, production-scale concurrency, "
                "external ordering, or production readiness."
            ),
            "",
        )
    )
    return "\n".join(lines)
