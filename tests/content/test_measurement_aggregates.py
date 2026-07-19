from __future__ import annotations

from datetime import UTC, datetime

from wilq.content.measurement import evidence as measurement_evidence
from wilq.content.measurement.aggregates import (
    aggregate_exact_page_metric_facts,
    compare_exact_page_metric_periods,
)
from wilq.schemas import MetricFact


def _fact(
    *,
    connector: str,
    name: str,
    value: float,
    dimensions: dict[str, str],
    period: str = "2026-01-01/2026-01-28",
    evidence_id: str = "ev_refresh_period",
) -> MetricFact:
    return MetricFact(
        name=name,
        value=value,
        period=period,
        source_connector=connector,
        evidence_id=evidence_id,
        dimensions=dimensions,
        collected_at=datetime(2026, 1, 29, tzinfo=UTC),
    )


def test_aggregates_exact_period_gsc_and_ga4_detail_rows() -> None:
    url = "https://www.ekologus.pl/bdo/"
    facts = [
        _fact(
            connector="google_search_console",
            name="clicks",
            value=3,
            dimensions={"page": url, "query": "bdo"},
        ),
        _fact(
            connector="google_search_console",
            name="clicks",
            value=1,
            dimensions={"page": url, "query": "bdo dla kogo"},
        ),
        _fact(
            connector="google_search_console",
            name="impressions",
            value=100,
            dimensions={"page": url, "query": "bdo"},
        ),
        _fact(
            connector="google_search_console",
            name="impressions",
            value=20,
            dimensions={"page": url, "query": "bdo dla kogo"},
        ),
        _fact(
            connector="google_analytics_4",
            name="sessions",
            value=10,
            dimensions={"landing_page": url, "source": "google"},
        ),
        _fact(
            connector="google_analytics_4",
            name="sessions",
            value=5,
            dimensions={"landing_page": url, "source": "direct"},
        ),
        _fact(
            connector="google_analytics_4",
            name="engaged_sessions",
            value=6,
            dimensions={"landing_page": url, "source": "google"},
        ),
        _fact(
            connector="google_analytics_4",
            name="engaged_sessions",
            value=3,
            dimensions={"landing_page": url, "source": "direct"},
        ),
    ]

    result = aggregate_exact_page_metric_facts(facts, content_url=url)
    values = {(fact.source_connector, fact.name): fact.value for fact in result.facts}

    assert values[("google_search_console", "clicks")] == 4
    assert values[("google_search_console", "impressions")] == 120
    assert values[("google_analytics_4", "sessions")] == 15
    assert values[("google_analytics_4", "engaged_sessions")] == 9
    assert values[("google_analytics_4", "engagement_rate")] == 0.6
    assert next(
        fact
        for fact in result.facts
        if fact.source_connector == "google_analytics_4"
        and fact.name == "engagement_rate"
    ).unit == "ratio"
    assert result.exclusions == []


def test_comparison_requires_two_complete_periods_and_preserves_evidence() -> None:
    url = "https://www.ekologus.pl/bdo/"
    facts = []
    for period, evidence, clicks, impressions in [
        ("2026-01-01/2026-01-07", "ev_baseline", 2, 40),
        ("2026-01-08/2026-01-14", "ev_observation", 4, 80),
    ]:
        facts.extend(
            [
                _fact(
                    connector="google_search_console",
                    name="clicks",
                    value=clicks,
                    dimensions={"page": url, "query": "bdo"},
                    period=period,
                    evidence_id=evidence,
                ),
                _fact(
                    connector="google_search_console",
                    name="impressions",
                    value=impressions,
                    dimensions={"page": url, "query": "bdo"},
                    period=period,
                    evidence_id=evidence,
                ),
            ]
        )

    comparison = compare_exact_page_metric_periods(facts, content_url=url)
    gsc = next(item for item in comparison if item.source_connector == "google_search_console")
    assert gsc.status == "available"
    assert gsc.baseline_period == "2026-01-01/2026-01-07"
    assert gsc.comparison_period == "2026-01-08/2026-01-14"
    assert gsc.evidence_ids == ["ev_baseline", "ev_observation"]

    one_period = compare_exact_page_metric_periods(facts[:2], content_url=url)
    assert (
        next(
            item for item in one_period if item.source_connector == "google_search_console"
        ).status
        == "not_available"
    )


def test_aggregator_excludes_wrong_period_and_mixed_lineage() -> None:
    url = "https://www.ekologus.pl/bdo/"
    result = aggregate_exact_page_metric_facts(
        [
            _fact(
                connector="google_search_console",
                name="clicks",
                value=1,
                dimensions={"page": url, "query": "bdo"},
                period="connector_refresh",
            ),
            _fact(
                connector="google_search_console",
                name="impressions",
                value=1,
                dimensions={"page": url, "query": "bdo"},
                evidence_id="ev_other_refresh",
            ),
            _fact(
                connector="google_search_console",
                name="clicks",
                value=1,
                dimensions={"page": url, "query": "bdo dla kogo"},
                evidence_id="ev_third_refresh",
            ),
            _fact(
                connector="google_search_console",
                name="unexpected_metric",
                value=1,
                dimensions={"page": url, "query": "bdo"},
            ),
        ],
        content_url=url,
    )

    assert all(fact.name != "ctr" for fact in result.facts)
    assert {item.code for item in result.exclusions} == {
        "wrong_period",
        "ambiguous_source_lineage",
        "unrecognized_detail_metric",
    }


def test_aggregator_deduplicates_row_exclusions_and_preserves_evidence() -> None:
    url = "https://www.ekologus.pl/bdo/"
    result = aggregate_exact_page_metric_facts(
        [
            _fact(
                connector="google_search_console",
                name="clicks",
                value=1,
                dimensions={"page": url, "query": "bdo"},
                period="connector_refresh",
                evidence_id="ev_old_a",
            ),
            _fact(
                connector="google_search_console",
                name="clicks",
                value=2,
                dimensions={"page": url, "query": "bdo dla kogo"},
                period="connector_refresh",
                evidence_id="ev_old_a",
            ),
            _fact(
                connector="google_search_console",
                name="clicks",
                value=3,
                dimensions={"page": url, "query": "bdo odpady"},
                period="connector_refresh",
                evidence_id="ev_old_b",
            ),
        ],
        content_url=url,
    )

    assert len(result.exclusions) == 1
    assert result.exclusions[0].code == "wrong_period"
    assert result.exclusions[0].evidence_ids == ["ev_old_a", "ev_old_b"]


def test_repeated_period_prefers_newest_refresh_lineage() -> None:
    url = "https://www.ekologus.pl/bdo/"
    old = datetime(2026, 1, 29, tzinfo=UTC)
    new = datetime(2026, 1, 30, tzinfo=UTC)
    facts = [
        _fact(
            connector="google_search_console",
            name=name,
            value=value,
            dimensions={"page": url, "query": "bdo"},
            evidence_id=evidence_id,
        ).model_copy(update={"collected_at": collected_at})
        for name, value, evidence_id, collected_at in [
            ("clicks", 1, "ev_old", old),
            ("impressions", 10, "ev_old", old),
            ("clicks", 2, "ev_new", new),
            ("impressions", 20, "ev_new", new),
        ]
    ]

    result = aggregate_exact_page_metric_facts(facts, content_url=url)

    assert {(fact.name, fact.value, fact.evidence_id) for fact in result.facts} >= {
        ("clicks", 2.0, "ev_new"),
        ("impressions", 20.0, "ev_new"),
    }
    assert not any(item.code == "ambiguous_source_lineage" for item in result.exclusions)


def test_repeated_period_without_collection_timestamps_stays_ambiguous() -> None:
    url = "https://www.ekologus.pl/bdo/"
    facts = [
        _fact(
            connector="google_search_console",
            name=name,
            value=value,
            dimensions={"page": url, "query": "bdo"},
            evidence_id=evidence_id,
        ).model_copy(update={"collected_at": None})
        for evidence_id in ("ev_legacy_a", "ev_legacy_b")
        for name, value in (("clicks", 1), ("impressions", 10))
    ]

    result = aggregate_exact_page_metric_facts(facts, content_url=url)

    assert result.facts == []
    assert [item.code for item in result.exclusions] == ["ambiguous_source_lineage"]
    assert result.exclusions[0].evidence_ids == ["ev_legacy_a", "ev_legacy_b"]


def test_ratio_aggregation_excludes_non_numeric_numerator() -> None:
    url = "https://www.ekologus.pl/bdo/"
    facts = [
        _fact(
            connector="google_search_console",
            name="clicks",
            value=1,
            dimensions={"page": url, "query": "bdo"},
        ),
        _fact(
            connector="google_search_console",
            name="impressions",
            value=10,
            dimensions={"page": url, "query": "bdo"},
        ),
    ]
    facts[0] = facts[0].model_copy(update={"value": "unknown"})

    result = aggregate_exact_page_metric_facts(facts, content_url=url)

    assert all(fact.name != "ctr" for fact in result.facts)
    assert {item.code for item in result.exclusions} == {
        "insufficient_values",
        "missing_denominator",
    }


def test_loader_returns_server_owned_aggregate_and_typed_exclusions(
    monkeypatch,
) -> None:
    url = "https://www.ekologus.pl/bdo/"
    facts = [
        _fact(
            connector="google_search_console",
            name="clicks",
            value=3,
            dimensions={"page": url, "query": "bdo"},
        ),
        _fact(
            connector="google_search_console",
            name="impressions",
            value=100,
            dimensions={"page": url, "query": "bdo"},
        ),
    ]

    class Store:
        def list_metric_facts_for_content_url(self, *_args, **_kwargs):
            return facts

    monkeypatch.setattr(measurement_evidence, "metric_store", lambda: Store())
    result = measurement_evidence.load_content_measurement_evidence(url)

    assert {(fact.name, fact.value) for fact in result.facts} >= {
        ("clicks", 3.0),
        ("impressions", 100.0),
        ("ctr", 0.03),
    }
    assert result.exclusions == []
