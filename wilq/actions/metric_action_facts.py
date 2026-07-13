from __future__ import annotations

from collections.abc import Callable, Iterable

from wilq.actions.metric_utils import latest_metric_facts_by_identity
from wilq.schemas import MetricFact
from wilq.storage.metric_store import DuckDbMetricStore


def load_action_metric_facts(
    *,
    store: DuckDbMetricStore,
    connector_ids: Iterable[str],
    limits: dict[str, int],
    latest_google_ads_facts: Callable[[], list[MetricFact]],
    is_probe_only_fact: Callable[[MetricFact], bool],
) -> list[MetricFact]:
    """Read the bounded, latest metric batch used by ActionObject inventory."""
    connector_ids = tuple(connector_ids)
    facts_by_connector = store.list_latest_metric_facts_by_connector_limits(
        {connector_id: limits.get(connector_id, 500) for connector_id in connector_ids}
    )
    google_ads_facts = latest_google_ads_facts()
    if google_ads_facts:
        facts_by_connector["google_ads"] = google_ads_facts

    facts = [
        fact
        for connector_id in connector_ids
        for fact in facts_by_connector.get(connector_id, [])
        if not is_probe_only_fact(fact)
    ]
    return latest_metric_facts_by_identity(facts)
