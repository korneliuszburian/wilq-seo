from __future__ import annotations

import json

from apps.api.wilq_api.context_compaction import compact_metric_fact_for_context
from wilq.schemas import MetricFact


def test_compact_metric_fact_context_uses_dimension_labels() -> None:
    fact = MetricFact(
        name="issue_product_count",
        value=12,
        period="test",
        source_connector="google_merchant_center",
        evidence_id="ev_metric_fact_dimension_context",
        dimensions={
            "affected_attribute": "n:unit_pricing_measure",
            "issue_type": "missing_potentially_required_attribute",
            "reporting_context": "FREE_LISTINGS",
            "resolution": "MERCHANT_ACTION",
            "severity": "NOT_IMPACTED",
        },
    )

    compact = compact_metric_fact_for_context(fact.model_dump(mode="json"))
    serialized = json.dumps(compact, ensure_ascii=False)

    assert compact["metric_label"] == "zgłoszenia problemów"
    assert compact["dimensions"]["atrybut"] == "miara ceny jednostkowej"
    assert compact["dimensions"]["problem"] == "brak potencjalnie wymaganego atrybutu"
    assert compact["dimensions"]["kontekst"] == "bezpłatne wyniki produktowe"
    assert compact["dimensions"]["rozwiązanie"] == "wymaga działania po stronie Merchant"
    assert compact["dimensions"]["status"] == "bez wpływu"
    for raw_value in (
        "issue_product_count",
        "affected_attribute",
        "missing_potentially_required_attribute",
        "FREE_LISTINGS",
        "MERCHANT_ACTION",
        "NOT_IMPACTED",
        "n:unit_pricing_measure",
    ):
        assert raw_value not in serialized


def test_compact_metric_fact_context_omits_generic_dimension_placeholders() -> None:
    fact = MetricFact(
        name="competitor_pages",
        value=123,
        period="test",
        source_connector="ahrefs",
        evidence_id="ev_metric_fact_generic_dimension_context",
        dimensions={
            "competitor_domain": "lex.pl",
            "competitor_page": "hidden-noise.example",
            "opaque_dimension": "opaque-value",
        },
    )

    compact = compact_metric_fact_for_context(fact.model_dump(mode="json"))
    serialized = json.dumps(compact, ensure_ascii=False)

    assert compact["dimensions"] == {"konkurent": "lex.pl"}
    assert "wymiar" not in serialized
    assert "wartość wymiaru do sprawdzenia" not in serialized
    assert "hidden-noise.example" not in serialized
    assert "opaque-value" not in serialized


def test_metric_fact_google_ads_dimensions_use_operator_labels() -> None:
    fact = MetricFact(
        name="campaign_cost_micros",
        value=123,
        period="test",
        source_connector="google_ads",
        evidence_id="ev_google_ads_metric_dimension_labels",
        dimensions={
            "campaign_id": "23848569273",
            "ad_group_name": "Grupa reklam 1",
            "advertising_channel_type": "PERFORMANCE_MAX",
            "campaign_status": "PAUSED",
            "search_term": "alba czeladź",
            "budget_period": "DAILY",
            "budget_status": "ENABLED",
        },
    )

    assert fact.dimension_labels["campaign_id"] == "identyfikator kampanii"
    assert fact.dimension_value_labels["campaign_id"] == (
        "dostępny w szczegółach technicznych"
    )
    assert fact.dimension_labels["ad_group_name"] == "grupa reklam"
    assert fact.dimension_value_labels["ad_group_name"] == "Grupa reklam 1"
    assert fact.dimension_value_labels["advertising_channel_type"] == "Performance Max"
    assert fact.dimension_value_labels["campaign_status"] == "wstrzymane"
    assert fact.dimension_value_labels["search_term"] == "alba czeladź"
    assert fact.dimension_value_labels["budget_period"] == "dziennie"
    assert fact.dimension_value_labels["budget_status"] == "aktywne"
    serialized = json.dumps(fact.model_dump(mode="json"), ensure_ascii=False)
    assert "wymiar" not in serialized
    assert "wartość wymiaru do sprawdzenia" not in serialized
