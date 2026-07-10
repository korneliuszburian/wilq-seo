"""Compatibility contract for the public WILQ schema facade."""

from wilq.schemas import (
    ActionObject,
    ConnectorRefreshRun,
    KnowledgeDecisionBinding,
    MetricFact,
    Opportunity,
)
from wilq.schemas.actions import ActionObject as DomainActionObject
from wilq.schemas.core import (
    ConnectorRefreshRun as CoreConnectorRefreshRun,
)
from wilq.schemas.core import MetricFact as CoreMetricFact
from wilq.schemas.core import Opportunity as CoreOpportunity


def test_schema_package_reexports_core_models_without_changing_public_imports() -> None:
    assert ConnectorRefreshRun is CoreConnectorRefreshRun
    assert MetricFact is CoreMetricFact
    assert Opportunity is CoreOpportunity
    assert ActionObject is DomainActionObject


def test_schema_package_preserves_the_active_content_workflow_route_label() -> None:
    binding = KnowledgeDecisionBinding(
        id="content_workflow",
        title="Treści",
        status="ready",
        route="/content-workflow",
        summary="Aktualna przestrzeń pracy.",
        next_step="Otwórz decyzję treści.",
    )

    assert binding.route_label == "Treści"
