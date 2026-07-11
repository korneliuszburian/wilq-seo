"""API contract proof for source-backed platform trap rule packs."""

from tests._contract_support.api_client import client


def test_platform_trap_packs_have_typed_lineage_and_safety_contracts() -> None:
    sources_response = client.get("/api/expert/sources")
    assert sources_response.status_code == 200
    sources = {source["id"]: source for source in sources_response.json()}
    expected_sources = {
        "src_google_ads_api_docs",
        "src_ga4_data_api_docs",
        "src_google_merchant_center_docs",
        "src_google_search_console_docs",
        "src_wordpress_rest_docs",
    }
    assert expected_sources.issubset(sources)

    rules_response = client.get("/api/expert/rules")
    assert rules_response.status_code == 200
    rules = {rule["id"]: rule for rule in rules_response.json()}
    trap_ids = {
        "ads_platform_traps_v1",
        "ga4_platform_traps_v1",
        "merchant_platform_traps_v1",
        "gsc_platform_traps_v1",
        "wordpress_platform_traps_v1",
    }
    assert trap_ids.issubset(rules)
    for rule_id in trap_ids:
        rule = rules[rule_id]
        trap = rule["platform_trap"]
        assert trap["constraints"]
        assert trap["safe_next_steps"]
        assert rule["source_ids"]
        assert rule["condition"]
        assert rule["required_connectors"]
        assert rule["required_metrics"]
        assert rule["minimum_window"]
        assert rule["false_positive_checks"]
        assert rule["blocked_states"]
        assert rule["recommendation_template"]
        assert rule["forbidden_conclusions"]
        assert rule["safety_level"] in {"low", "medium", "high"}
        assert rule["eval_case_ids"]

    ads = rules["ads_platform_traps_v1"]
    assert ads["source_ids"] == ["src_google_ads_api_docs"]
    assert ads["required_connectors"] == ["google_ads"]
    assert ads["required_metrics"] == ["campaign_metrics", "search_term_metrics"]
    assert ads["safety_level"] == "high"
    assert rules["wordpress_platform_traps_v1"]["source_ids"] == [
        "src_wordpress_rest_docs"
    ]

    summaries_response = client.get("/api/expert/rule-summaries")
    assert summaries_response.status_code == 200
    summaries = {summary["id"]: summary for summary in summaries_response.json()}
    assert summaries["ads_platform_traps_v1"]["blocked_states"] == ads["blocked_states"]
    assert summaries["ads_platform_traps_v1"]["safety_level"] == "high"

