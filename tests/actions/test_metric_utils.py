from datetime import UTC, datetime

from wilq.actions.localo.visibility import localo_action_metric_facts
from wilq.actions.metric_utils import facts_by_connector, latest_metric_facts_by_identity
from wilq.schemas import (
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    MetricFact,
)


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


def test_localo_action_metric_facts_falls_back_to_latest_completed_vendor_read() -> None:
    probe = _fact(value=1, collected_at=None, connector="localo", dimensions={})
    probe.name = "access_token_present"
    value_fact = _fact(value=12, collected_at="2026-07-12T10:00:00", connector="localo")
    run = ConnectorRefreshRun(
        id="refresh_localo_completed",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        vendor_data_collected=True,
        summary="Localo odczyt zakończony.",
        evidence_ids=["ev_localo_latest"],
    )

    result = localo_action_metric_facts(
        facts=[probe],
        refresh_runs=[run],
        metric_facts_by_evidence_ids=lambda evidence_ids: (
            [value_fact] if evidence_ids == ["ev_localo_latest"] else []
        ),
        is_probe_only_fact=lambda fact: fact.name == "access_token_present",
    )

    assert result == [value_fact]
