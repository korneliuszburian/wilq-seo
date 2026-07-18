from wilq.briefing.ads_diagnostics import _search_term_metric_rows
from wilq.schemas import MetricFact


def test_search_term_contract_exposes_resolved_landing_lineage_without_raw_url() -> None:
    dimensions = {
        "campaign_id": "campaign-1",
        "campaign_name": "Ekologus Search",
        "ad_group_id": "ad-group-1",
        "ad_group_name": "BDO",
        "search_term": "bdo sprawozdanie",
        "landing_mapping_status": "resolved",
        "landing_identity_sha256": "a" * 64,
    }
    facts = [
        MetricFact(
            name=name,
            value=value,
            period="last_30_days",
            source_connector="google_ads",
            evidence_id="ev_ads_landing",
            dimensions=dimensions,
        )
        for name, value in (
            ("search_term_clicks", 4),
            ("search_term_impressions", 40),
            ("search_term_cost_micros", 1_000_000),
            ("search_term_conversions", 0.0),
            ("search_term_conversion_value", 0.0),
        )
    ]

    row = _search_term_metric_rows(facts)[0]

    assert row.landing_mapping_status == "resolved"
    assert row.landing_identity_sha256 == "a" * 64
    assert not hasattr(row, "landing_url")
