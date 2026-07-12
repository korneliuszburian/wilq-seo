from datetime import UTC, datetime

from wilq.actions.metric_utils import facts_by_connector, latest_metric_facts_by_identity
from wilq.schemas import MetricFact


def _fact(
    *,
    value: int,
    collected_at: str | None,
    connector: str = "google_ads",
    dimensions: dict[str, str] | None = None,
) -> MetricFact:
    return MetricFact(
        name="clicks",
        value=value,
        period="30d",
        source_connector=connector,
        evidence_id=f"ev_{value}",
        dimensions=dimensions or {"campaign_name": "Ekologus"},
        collected_at=(
            datetime.fromisoformat(collected_at).replace(tzinfo=UTC)
            if collected_at
            else None
        ),
    )


def test_latest_metric_facts_deduplicate_identity_and_sort_by_collection_time() -> None:
    facts = [
        _fact(value=10, collected_at="2026-07-11T10:00:00"),
        _fact(value=20, collected_at="2026-07-12T10:00:00"),
        _fact(
            value=30,
            collected_at="2026-07-12T09:00:00",
            dimensions={"campaign_name": "Inna kampania"},
        ),
        _fact(value=40, collected_at=None, connector="ga4"),
    ]

    latest = latest_metric_facts_by_identity(facts)

    assert [(fact.value, fact.source_connector) for fact in latest] == [
        (20, "google_ads"),
        (30, "google_ads"),
        (40, "ga4"),
    ]


def test_facts_by_connector_preserves_input_order_within_groups() -> None:
    facts = [
        _fact(value=1, collected_at=None, connector="gsc"),
        _fact(value=2, collected_at=None, connector="ga4"),
        _fact(value=3, collected_at=None, connector="gsc"),
    ]

    grouped = facts_by_connector(facts)

    assert [fact.value for fact in grouped["gsc"]] == [1, 3]
    assert [fact.value for fact in grouped["ga4"]] == [2]
