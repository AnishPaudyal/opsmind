"""Focused tests for the governed Phase 6 deterministic evaluator."""

from dataclasses import replace
from pathlib import Path

from opsmind.evaluation.phase6.__main__ import (
    JSON_FILENAME,
    MARKDOWN_FILENAME,
    main,
)
from opsmind.evaluation.phase6.evaluation import (
    Phase6ScenarioResult,
    evaluate_phase6,
    recommendation_signature,
)
from opsmind.evaluation.phase6.reporting import render_json, render_markdown
from opsmind.evaluation.phase6.scenarios import (
    DATASET_VERSION,
    build_phase6_dataset,
    build_recommendation,
)


def _by_name(name: str) -> Phase6ScenarioResult:
    evaluation = evaluate_phase6()
    return next(result for result in evaluation.results if result.name == name)


def test_dataset_is_named_deterministic_and_unique() -> None:
    first = build_phase6_dataset()
    second = build_phase6_dataset()

    assert DATASET_VERSION == "phase6-synthetic-v1"
    assert len(first) == 12
    assert [scenario.name for scenario in first] == [
        scenario.name for scenario in second
    ]
    assert len({scenario.name for scenario in first}) == len(first)
    assert len({scenario.ordinal for scenario in first}) == len(first)
    assert recommendation_signature(build_recommendation()) == (
        recommendation_signature(build_recommendation())
    )


def test_all_governed_scenarios_pass() -> None:
    evaluation = evaluate_phase6()

    assert evaluation.scenario_count == 12
    assert evaluation.passed_scenarios == 12
    assert evaluation.failed_scenarios == 0
    assert evaluation.approval_scenarios == 6
    assert evaluation.rejection_scenarios == 4
    assert evaluation.idempotent_retry_scenarios == 2
    assert evaluation.expected_conflict_scenarios == 4
    assert evaluation.expected_output_mismatches == 0
    assert evaluation.snapshot_preservation_failures == 0
    assert evaluation.terminal_cardinality_failures == 0
    assert evaluation.retry_idempotency_failures == 0
    assert evaluation.conflict_mutation_failures == 0
    assert evaluation.audit_order_failures == 0
    assert evaluation.memory_isolation_failures == 0


def test_approval_default_and_override_keep_recommended_quantity_distinct() -> None:
    default = _by_name("approval_uses_recommended_quantity")
    override = _by_name("approval_positive_override")

    assert default.actual_approved_quantity == 19
    assert override.actual_approved_quantity == 17
    assert default.snapshot_preserved
    assert override.snapshot_preserved


def test_rejection_preserves_terminal_shape() -> None:
    result = _by_name("rejection_normalizes_reason")

    assert result.actual_review_status == "rejected"
    assert result.actual_decision_type == "rejected"
    assert result.actual_approved_quantity is None
    assert result.actual_event_types == (
        "review_created",
        "recommendation_rejected",
    )
    assert result.terminal_cardinality_valid


def test_identical_retries_are_idempotent() -> None:
    approval = _by_name("identical_normalized_approval_retry")
    rejection = _by_name("identical_normalized_rejection_retry")

    assert approval.retry_idempotency_valid
    assert rejection.retry_idempotency_valid
    assert approval.actual_sequences == (1, 2)
    assert rejection.actual_sequences == (1, 2)


def test_changed_and_opposite_retries_conflict_without_mutation() -> None:
    names = (
        "changed_approval_retry_conflicts",
        "changed_rejection_retry_conflicts",
        "rejection_after_approval_conflicts",
        "approval_after_rejection_conflicts",
    )

    for name in names:
        result = _by_name(name)
        assert result.conflict_expected
        assert result.conflict_observed
        assert result.conflict_no_mutation_valid
        assert result.actual_sequences == (1, 2)


def test_timestamp_tie_and_memory_isolation_pass() -> None:
    ordering = _by_name("same_timestamp_sequence_ordering")
    isolation = _by_name("memory_repository_isolation")

    assert ordering.audit_order_valid
    assert ordering.actual_sequences == (1, 2)
    assert isolation.memory_isolation_valid
    assert isolation.actual_review_status == "pending_review"


def test_rendered_artifacts_are_deterministic() -> None:
    first = evaluate_phase6()
    second = evaluate_phase6()

    assert render_json(first) == render_json(second)
    assert render_markdown(first) == render_markdown(second)


def test_corrupted_expected_outcome_is_detected() -> None:
    scenarios = build_phase6_dataset()
    corrupted = replace(
        scenarios[0],
        expected=replace(scenarios[0].expected, review_status="approved"),
    )
    evaluation = evaluate_phase6((corrupted, *scenarios[1:]))

    assert evaluation.failed_scenarios == 1
    assert evaluation.expected_output_mismatches == 1


def test_reports_keep_postgresql_and_security_claim_boundaries_explicit() -> None:
    evaluation = evaluate_phase6()
    json_text = render_json(evaluation)
    markdown = render_markdown(evaluation)

    for text in (json_text, markdown):
        assert "PostgreSQL" in text
        assert "unverified" in text
        assert "authentication" in text
        assert "tamper" in text
        assert "purchase order" in text
        assert "production" in text


def test_cli_writes_artifacts_and_refuses_accidental_overwrite(
    tmp_path: Path,
) -> None:
    assert main(["--output-dir", str(tmp_path)]) == 0

    json_path = tmp_path / JSON_FILENAME
    markdown_path = tmp_path / MARKDOWN_FILENAME
    assert json_path.read_text(encoding="utf-8") == render_json(evaluate_phase6())
    assert markdown_path.read_text(encoding="utf-8") == render_markdown(
        evaluate_phase6()
    )

    assert main(["--output-dir", str(tmp_path)]) == 2
    assert main(["--output-dir", str(tmp_path), "--overwrite"]) == 0
