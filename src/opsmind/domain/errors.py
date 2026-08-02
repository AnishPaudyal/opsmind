"""Typed errors for OpsMind business operations."""

from datetime import date
from uuid import UUID


class DuplicateSkuError(Exception):
    """A product already uses the normalized SKU."""

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(sku)


class ProductNotFoundError(Exception):
    """The requested product does not exist."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(str(product_id))


class InventoryNotFoundError(Exception):
    """The product exists but has no inventory position."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(str(product_id))


class DuplicateDemandDateError(Exception):
    """Demand already exists for a product and calendar date."""

    def __init__(self, product_id: UUID, demand_date: date) -> None:
        self.product_id = product_id
        self.demand_date = demand_date
        super().__init__(f"{product_id}:{demand_date.isoformat()}")


class InsufficientDemandHistoryError(Exception):
    """No eligible demand exists for a requested forecast."""

    def __init__(
        self,
        product_id: UUID,
        effective_cutoff: date | None,
    ) -> None:
        self.product_id = product_id
        self.effective_cutoff = effective_cutoff
        if effective_cutoff is None:
            message = (
                "At least one demand observation is required to calculate a "
                f"forecast for product '{product_id}'."
            )
        else:
            message = (
                f"No demand observations are available for product '{product_id}' "
                f"on or before '{effective_cutoff.isoformat()}'."
            )
        super().__init__(message)


class NoActionableReorderRecommendationError(Exception):
    """The calculated recommendation cannot enter human review."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(
            f"Product '{product_id}' has no actionable reorder recommendation."
        )


class RecommendationReviewNotFoundError(Exception):
    """The requested stored recommendation review does not exist."""

    def __init__(self, recommendation_id: UUID) -> None:
        self.recommendation_id = recommendation_id
        super().__init__(str(recommendation_id))


class DuplicateRecommendationReviewError(Exception):
    """A stored recommendation already uses the generated identifier."""

    def __init__(self, recommendation_id: UUID) -> None:
        self.recommendation_id = recommendation_id
        super().__init__(str(recommendation_id))


class RecommendationReviewConflictError(Exception):
    """A requested decision conflicts with the terminal stored decision."""
