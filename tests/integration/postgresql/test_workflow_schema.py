"""Real-PostgreSQL recommendation-workflow schema tests."""

from collections.abc import Iterable, Mapping

from alembic import command
from alembic.config import Config
from sqlalchemy import DateTime, Numeric, inspect
from sqlalchemy.engine import Engine

OPERATIONAL_TABLES = {
    "products",
    "inventory_positions",
    "demand_observations",
}
WORKFLOW_TABLES = {
    "recommendation_reviews",
    "recommendation_decisions",
    "recommendation_audit_events",
}

REVIEW_CHECK_CONSTRAINTS = {
    "ck_recommendation_reviews_allocated_quantity_nonnegative",
    "ck_recommendation_reviews_available_inventory_consistent",
    "ck_recommendation_reviews_average_daily_demand_nonnegative",
    "ck_recommendation_reviews_forecast_lead_time_demand_nonnegative",
    "ck_recommendation_reviews_forecast_method_supported",
    "ck_recommendation_reviews_lead_time_days_nonnegative",
    "ck_recommendation_reviews_lookback_observations_positive",
    "ck_recommendation_reviews_observations_used_positive",
    "ck_recommendation_reviews_observations_within_lookback",
    "ck_recommendation_reviews_on_hand_quantity_nonnegative",
    "ck_recommendation_reviews_projected_shortage_quantity_positive",
    "ck_recommendation_reviews_recommendation_policy_supported",
    "ck_recommendation_reviews_recommendation_status_actionable",
    "ck_recommendation_reviews_recommended_quantity_positive",
    "ck_recommendation_reviews_review_decision_shape",
    "ck_recommendation_reviews_review_status_supported",
    "ck_recommendation_reviews_training_date_order",
    "ck_recommendation_reviews_unit_of_measure_nonblank",
}

DECISION_CHECK_CONSTRAINTS = {
    "ck_recommendation_decisions_decided_by_nonblank",
    "ck_recommendation_decisions_decision_shape",
    "ck_recommendation_decisions_decision_type_supported",
    "ck_recommendation_decisions_note_optional_nonblank",
}

AUDIT_CHECK_CONSTRAINTS = {
    "ck_recommendation_audit_events_actor_optional_nonblank",
    "ck_recommendation_audit_events_event_shape",
    "ck_recommendation_audit_events_event_type_supported",
    "ck_recommendation_audit_events_note_optional_nonblank",
    "ck_recommendation_audit_events_recommended_quantity_positive",
    "ck_recommendation_audit_events_review_status_supported",
    "ck_recommendation_audit_events_sequence_number_positive",
}


def _constraint_names(
    items: Iterable[Mapping[str, object]],
) -> set[str]:
    """Return all non-null reflected constraint names."""
    return {name for item in items if isinstance((name := item.get("name")), str)}


def test_workflow_migration_creates_expected_tables(
    postgresql_engine: Engine,
) -> None:
    """Alembic head contains all three workflow tables."""
    table_names = set(inspect(postgresql_engine).get_table_names())

    assert WORKFLOW_TABLES <= table_names


def test_workflow_tables_have_expected_primary_keys(
    postgresql_engine: Engine,
) -> None:
    """Each workflow table has its deterministic primary-key name."""
    inspector = inspect(postgresql_engine)

    assert (
        inspector.get_pk_constraint("recommendation_reviews")["name"]
        == "pk_recommendation_reviews"
    )
    assert (
        inspector.get_pk_constraint("recommendation_decisions")["name"]
        == "pk_recommendation_decisions"
    )
    assert (
        inspector.get_pk_constraint("recommendation_audit_events")["name"]
        == "pk_recommendation_audit_events"
    )


def test_workflow_foreign_keys_match_aggregate_relationships(
    postgresql_engine: Engine,
) -> None:
    """Reflected foreign keys match the approved workflow design."""
    inspector = inspect(postgresql_engine)

    assert _constraint_names(inspector.get_foreign_keys("recommendation_reviews")) == {
        "fk_recommendation_reviews_product_id_products",
        "fk_recommendation_reviews_decision_pair",
    }
    assert _constraint_names(
        inspector.get_foreign_keys("recommendation_decisions")
    ) == {
        "fk_recommendation_decisions_review",
    }
    assert _constraint_names(
        inspector.get_foreign_keys("recommendation_audit_events")
    ) == {
        "fk_recommendation_audit_events_decision_pair",
        "fk_recommendation_audit_events_review",
    }


def test_workflow_unique_constraints_enforce_cardinality(
    postgresql_engine: Engine,
) -> None:
    """Unique constraints enforce one decision and ordered audit history."""
    inspector = inspect(postgresql_engine)

    assert _constraint_names(
        inspector.get_unique_constraints("recommendation_decisions")
    ) == {
        "uq_recommendation_decisions_recommendation_id",
        "uq_recommendation_decisions_recommendation_id_decision_id",
    }
    assert _constraint_names(
        inspector.get_unique_constraints("recommendation_audit_events")
    ) == {
        "uq_recommendation_audit_events_decision_id",
        "uq_recommendation_audit_events_recommendation_id",
    }


def test_workflow_check_constraints_match_domain_shapes(
    postgresql_engine: Engine,
) -> None:
    """Database checks protect review, decision, and event invariants."""
    inspector = inspect(postgresql_engine)

    assert (
        _constraint_names(inspector.get_check_constraints("recommendation_reviews"))
        == REVIEW_CHECK_CONSTRAINTS
    )
    assert (
        _constraint_names(inspector.get_check_constraints("recommendation_decisions"))
        == DECISION_CHECK_CONSTRAINTS
    )
    assert (
        _constraint_names(
            inspector.get_check_constraints("recommendation_audit_events")
        )
        == AUDIT_CHECK_CONSTRAINTS
    )


def test_review_product_lookup_index_exists(
    postgresql_engine: Engine,
) -> None:
    """Product-based workflow lookups have one explicit index."""
    index_names = _constraint_names(
        inspect(postgresql_engine).get_indexes("recommendation_reviews")
    )

    assert "ix_recommendation_reviews_product_id" in index_names


def test_workflow_decimal_and_timestamp_types_preserve_domain_values(
    postgresql_engine: Engine,
) -> None:
    """Decimals remain unconstrained and timestamps remain timezone-aware."""
    inspector = inspect(postgresql_engine)

    review_columns = {
        column["name"]: column
        for column in inspector.get_columns("recommendation_reviews")
    }
    decision_columns = {
        column["name"]: column
        for column in inspector.get_columns("recommendation_decisions")
    }
    audit_columns = {
        column["name"]: column
        for column in inspector.get_columns("recommendation_audit_events")
    }

    for column_name in (
        "average_daily_demand",
        "forecasted_lead_time_demand",
        "projected_inventory_balance",
        "projected_shortage_quantity",
    ):
        column_type = review_columns[column_name]["type"]
        assert isinstance(column_type, Numeric)
        assert column_type.precision is None
        assert column_type.scale is None

    for column in (
        review_columns["created_at"],
        decision_columns["decided_at"],
        audit_columns["occurred_at"],
    ):
        column_type = column["type"]
        assert isinstance(column_type, DateTime)
        assert column_type.timezone is True


def test_downgrade_to_operational_revision_removes_only_workflow_tables(
    postgresql_engine: Engine,
    alembic_config: Config,
) -> None:
    """Revision 0005 retains operational tables but not workflow tables."""
    try:
        command.downgrade(alembic_config, "0005_operational_data")
        table_names = set(inspect(postgresql_engine).get_table_names())

        assert OPERATIONAL_TABLES <= table_names
        assert WORKFLOW_TABLES.isdisjoint(table_names)

        command.upgrade(alembic_config, "head")
        restored_names = set(inspect(postgresql_engine).get_table_names())

        assert OPERATIONAL_TABLES <= restored_names
        assert WORKFLOW_TABLES <= restored_names
    finally:
        command.upgrade(alembic_config, "head")
