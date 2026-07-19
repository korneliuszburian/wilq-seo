"""Social, demand-gen, knowledge and workflow context API tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from apps.api.wilq_api.context_daily import compact_content_knowledge_card_for_operator_context
from apps.api.wilq_api.context_knowledge import content_knowledge_cards_for_skill
from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from wilq.actions.social import social_draft_actions
from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import (
    AdsCampaignMetricRow,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    DemandGenLandingQualityRow,
    MetricFact,
)
from wilq.social.history import SOCIAL_HISTORY_INVENTORY_FILE_ENV, social_history_input_example
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store
from wilq.workflows.models import Workflow, _workflow_run_status_label
from wilq.workflows.registry import _risk_label as _workflow_risk_label
from wilq.workflows.registry import _status_label as _workflow_status_label


def test_expert_rules_are_loaded_from_structured_files() -> None:
    response = client.get("/api/expert/rules")
    assert response.status_code == 200
    rules = response.json()
    rule_ids = {rule["id"] for rule in rules}
    assert "ads_search_terms_v1" in rule_ids
    search_terms_rule = next(rule for rule in rules if rule["id"] == "ads_search_terms_v1")
    assert search_terms_rule["domain"] == "ads"
    assert search_terms_rule["requires_evidence"] is True
    assert "evidence_ids" in search_terms_rule["required_inputs"]
    assert search_terms_rule["source_path"].startswith("wilq/expert/")
    assert search_terms_rule["source_ids"] == ["src_google_ads_api_docs"]


def test_expert_knowledge_sources_link_to_structured_rules() -> None:
    response = client.get("/api/expert/sources")
    assert response.status_code == 200
    sources = response.json()
    source_by_id = {source["id"]: source for source in sources}

    assert "src_google_ads_api_docs" in source_by_id
    assert "src_google_merchant_center_docs" in source_by_id
    assert "src_ga4_data_api_docs" in source_by_id
    assert "src_google_search_console_docs" in source_by_id
    assert "src_wordpress_rest_docs" in source_by_id

    ads_source = source_by_id["src_google_ads_api_docs"]
    assert ads_source["domain"] == "ads"
    assert ads_source["knowledge_type"] == "platform_trap"
    assert ads_source["source_type"] == "official_platform_doc"
    assert ads_source["license_status"] == "commit_safe"
    assert ads_source["trust_level"] == "high"
    assert "ads_search_terms_v1" in ads_source["linked_rule_ids"]
    assert "ads_platform_traps_v1" in ads_source["linked_rule_ids"]
    assert "automatic_vendor_write" in ads_source["forbidden_usage"]
    assert all("/home/" not in source["source_reference"] for source in sources)
    assert all(source["linked_rule_ids"] for source in sources)

    summaries_response = client.get("/api/expert/rule-summaries")
    assert summaries_response.status_code == 200
    summaries = summaries_response.json()
    search_terms_summary = next(
        summary for summary in summaries if summary["id"] == "ads_search_terms_v1"
    )
    assert search_terms_summary["source_ids"] == ["src_google_ads_api_docs"]

    rules_response = client.get("/api/expert/rules")
    assert rules_response.status_code == 200
    rules_by_id = {rule["id"]: rule for rule in rules_response.json()}
    trap_ids = {
        "ads_platform_traps_v1",
        "ga4_platform_traps_v1",
        "merchant_platform_traps_v1",
        "gsc_platform_traps_v1",
        "wordpress_platform_traps_v1",
    }
    assert trap_ids.issubset(rules_by_id)
    assert all(rules_by_id[rule_id]["platform_trap"]["constraints"] for rule_id in trap_ids)
    assert all(rules_by_id[rule_id]["platform_trap"]["safe_next_steps"] for rule_id in trap_ids)
    assert rules_by_id["wordpress_platform_traps_v1"]["source_ids"] == [
        "src_wordpress_rest_docs"
    ]


def test_knowledge_taxonomy_separates_client_truth_from_expert_rules() -> None:
    response = client.get("/api/knowledge/taxonomy")
    assert response.status_code == 200
    taxonomy = response.json()
    entries = {entry["id"]: entry for entry in taxonomy}

    assert set(entries) == {
        "client_truth",
        "expert_operating",
        "platform_trap",
        "workspace_memory",
        "observed_outcome",
    }
    assert entries["client_truth"]["owned_by"] == "source_fact_compiler"
    assert entries["expert_operating"]["owned_by"] == "expert_rule_compiler"
    assert entries["platform_trap"]["owned_by"] == "platform_rule_pack"
    assert entries["workspace_memory"]["owned_by"] == "workspace_dossier"
    assert entries["observed_outcome"]["owned_by"] == "measurement_loop"
    assert any(
        "diagnostic thresholds" in forbidden
        for forbidden in entries["client_truth"]["forbidden_usage"]
    )
    assert any(
        record.startswith("expert_rule:")
        for record in entries["expert_operating"]["example_records"]
    )


def test_expert_capabilities_are_available_through_api() -> None:
    response = client.get("/api/expert/capabilities")
    assert response.status_code == 200
    capabilities = response.json()
    capability_ids = {capability["id"] for capability in capabilities}
    assert "ads_daily_check" in capability_ids
    assert "ads_custom_segments" in capability_ids
    assert all(capability["requires_evidence"] for capability in capabilities)


def test_daily_context_pack_excludes_social_draft_action_objects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    all_action_ids = {action["id"] for action in actions_response.json()}
    assert "act_prepare_linkedin_social_drafts" in all_action_ids
    assert "act_prepare_facebook_social_drafts" in all_action_ids

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    daily_action_ids = {action["id"] for action in context_payload["active_action_objects"]}

    assert {
        "act_review_merchant_feed_issues",
        "act_review_ga4_tracking_quality",
        "act_prepare_content_refresh_queue",
    }.issubset(daily_action_ids)
    assert "act_prepare_linkedin_social_drafts" not in daily_action_ids
    assert "act_prepare_facebook_social_drafts" not in daily_action_ids


def test_social_context_pack_keeps_explicit_social_draft_action_objects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-social-publisher"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    social_action_ids = {action["id"] for action in context_payload["active_action_objects"]}

    assert "act_prepare_linkedin_social_drafts" in social_action_ids
    assert "act_prepare_facebook_social_drafts" in social_action_ids
    assert social_action_ids == {
        "act_prepare_linkedin_social_drafts",
        "act_prepare_facebook_social_drafts",
    }


def test_social_context_pack_exposes_review_only_draft_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv(SOCIAL_HISTORY_INVENTORY_FILE_ENV, raising=False)
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-social-publisher"},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()

    social_context = context_payload["social_draft_context"]
    assert social_context["mode"] == "review_only"
    assert social_context["publish_allowed"] is False
    assert social_context["missing_publish_access"] == {
        "linkedin": ["LINKEDIN_ORGANIZATION_ID", "LINKEDIN_ACCESS_TOKEN"],
        "facebook": ["FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_ACCESS_TOKEN"],
    }
    assert "missing_publish_permissions" not in social_context
    assert social_context["draft_action_ids"] == [
        "act_prepare_facebook_social_drafts",
        "act_prepare_linkedin_social_drafts",
    ]
    assert social_context["source_inputs"]
    assert "candidate_inputs" not in social_context
    assert {
        "source_connector",
        "metric_name",
        "value",
        "context_summary",
        "evidence_id",
    }.issubset(social_context["source_inputs"][0])
    assert "no_publishing_without_connector_credentials" in social_context["draft_constraints"]
    assert "require_social_history_duplicate_review" in social_context["draft_constraints"]
    assert "opublikowanie posta" in social_context["blocked_claims"]
    assert "wzrost skuteczności social" in social_context["blocked_claims"]
    assert "brak powtórzeń historycznych postów" in social_context["blocked_claims"]
    assert "przychód" in social_context["blocked_claims"]
    assert "wzrost konwersji" in social_context["blocked_claims"]
    assert social_context["historical_social_inventory_status"] == "missing"
    assert (
        social_context["historical_social_inventory_status_label"]
        == "brak spisu historycznych postów LinkedIn/Facebook"
    )
    assert social_context["duplicate_risk_status"] == "blocked_until_social_history_review"
    assert (
        social_context["duplicate_risk_status_label"]
        == "nie oceniono ryzyka powtórzenia treści social"
    )
    assert social_context["required_history_sources"] == ["linkedin", "facebook"]
    assert social_context["missing_history_evidence"] == [
        "linkedin_historical_posts",
        "facebook_historical_posts",
    ]
    assert social_context["history_audit_endpoint"] == ("/api/social/history-inventory/audit")
    assert social_context["history_audit_contract"] == "social_history_inventory_v1"
    history_inventory = social_context["social_history_inventory"]
    assert history_inventory["contract"] == "social_history_inventory_v1"
    assert history_inventory["read_only"] is True
    assert history_inventory["status"] == "missing"
    assert history_inventory["duplicate_risk_status"] == "blocked_until_social_history_review"
    assert history_inventory["required_sources"] == ["linkedin", "facebook"]
    assert history_inventory["missing_evidence_ids"] == [
        "linkedin_historical_posts",
        "facebook_historical_posts",
    ]
    assert {source["channel"] for source in history_inventory["sources"]} == {
        "linkedin",
        "facebook",
    }
    assert all(
        source["safe_collection_mode"] == "metadata_only" for source in history_inventory["sources"]
    )
    assert all(source["raw_post_body_allowed"] is False for source in history_inventory["sources"])
    assert history_inventory["discovery_seeds"] == [
        {
            "id": "social_history_seed_ekologus_linkedin_posts",
            "channel": "linkedin",
            "source_type": "public_posts_url",
            "source_url": (
                "https://www.linkedin.com/company/"
                "ekologus-esg-eko-audyt-ochrona-srodowiska-dokumentacje-"
                "srodowiskowe-szkolenia-sorbenty/posts/?feedView=all"
            ),
            "status": "seeded_not_collected",
            "safe_collection_mode": "metadata_only",
            "raw_post_body_allowed": False,
            "required_review": True,
            "operator_note": (
                "Publiczny adres postów LinkedIn Ekologus jest tylko punktem startowym "
                "discovery. WILQ nie traktuje go jako gotowej historii postów, dopóki "
                "metadata-only inventory nie zostanie zebrane i sprawdzone."
            ),
        },
        {
            "id": "social_history_seed_ekologus_facebook_posts",
            "channel": "facebook",
            "source_type": "public_posts_url",
            "source_url": "https://www.facebook.com/ekologus/?locale=pl_PL",
            "status": "seeded_not_collected",
            "safe_collection_mode": "metadata_only",
            "raw_post_body_allowed": False,
            "required_review": True,
            "operator_note": (
                "Publiczny adres strony Facebook Ekologus jest tylko punktem startowym "
                "discovery. WILQ nie traktuje go jako gotowej historii postów, dopóki "
                "metadata-only inventory nie zostanie zebrane i sprawdzone."
            ),
        },
    ]
    assert {source["connector_access_status"] for source in history_inventory["sources"]} == {
        "missing_credentials"
    }
    assert "credential_status" not in history_inventory["sources"][0]
    assert {
        "channel",
        "published_at",
        "topic",
        "service",
        "claim",
        "cta",
        "format",
        "post_url_or_id",
        "source_evidence_id",
    }.issubset(history_inventory["sources"][0]["required_metadata_fields"])
    input_template = history_inventory["input_template"]
    assert input_template["contract"] == "social_history_inventory_v1"
    assert {item["channel"] for item in input_template["items"]} == {
        "linkedin",
        "facebook",
    }
    assert "metadata-only" in input_template["_instruction"]
    serialized_input_template = json.dumps(input_template, ensure_ascii=False)
    assert "raw_post_body" not in serialized_input_template
    assert "comments" not in serialized_input_template
    assert "twierdzenie że temat jest nowy bez historii postów" in history_inventory["blocked_uses"]
    assert "claim i CTA" in " ".join(history_inventory["dedupe_requirements"])
    assert "braku powtórzeń" in social_context["operator_next_step"]
    old_post_publish_claim = "post " + "published"
    old_social_growth_claim = "social performance " + "up" + "lift"
    assert old_post_publish_claim not in social_context["blocked_claims"]
    assert old_social_growth_claim not in social_context["blocked_claims"]
    serialized_social_context = json.dumps(social_context, ensure_ascii=False)
    assert "candidate_inputs" not in serialized_social_context
    assert "availability_updated" not in serialized_social_context
    assert "FREE_LISTINGS" not in serialized_social_context
    assert "MERCHANT_ACTION" not in serialized_social_context
    assert "n:availability" not in serialized_social_context
    assert (
        context_payload["marketing_brief"]["context_pack_compaction"]["sections_compacted"] is True
    )
    assert context_payload["tactical_queue"]["context_pack_compaction"]["items_compacted"] is True
    assert (
        context_payload["tactical_queue"]["context_pack_compaction"]["metric_facts_removed"] is True
    )
    assert len(json.dumps(context_payload, ensure_ascii=False).encode()) < 140_000


def test_social_context_pack_uses_review_ready_history_inventory_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    history_file = tmp_path / "social-history.json"
    history_file.write_text(
        json.dumps(social_history_input_example(), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setenv(SOCIAL_HISTORY_INVENTORY_FILE_ENV, str(history_file))

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-social-publisher"},
    )

    assert context_response.status_code == 200
    social_context = context_response.json()["social_draft_context"]
    assert social_context["publish_allowed"] is False
    assert social_context["historical_social_inventory_status"] == "review_ready"
    assert social_context["historical_social_inventory_status_label"] == (
        "spis historii social gotowy do oceny"
    )
    assert social_context["duplicate_risk_status"] == ("blocked_until_social_history_review")
    assert social_context["missing_history_evidence"] == []
    inventory = social_context["social_history_inventory"]
    assert inventory["metadata_source_configured"] is True
    assert inventory["metadata_source_status"] == "review_ready"
    assert inventory["input_template"]["contract"] == "social_history_inventory_v1"
    assert inventory["item_count"] == 2
    assert inventory["channel_counts"] == {"facebook": 1, "linkedin": 1}
    assert inventory["import_errors"] == []
    assert {source["inventory_status"] for source in inventory["sources"]} == {"review_ready"}
    assert "brak powtórzeń historycznych postów" in social_context["blocked_claims"]


def test_social_draft_actions_exclude_dev_site_inventory_inputs() -> None:
    actions = social_draft_actions(
        [
            MetricFact(
                name="clicks",
                value=4,
                period="connector_refresh",
                source_connector="google_search_console",
                evidence_id="ev_gsc_social_candidate",
                dimensions={
                    "query": "ekologus bielsko",
                    "page": "https://www.ekologus.pl/",
                },
            ),
            MetricFact(
                name="content_object_seen",
                value=1,
                period="connector_refresh",
                source_connector="wordpress_ekologus",
                evidence_id="ev_wordpress_dev_site_candidate",
                dimensions={
                    "content_url": "https://ekologus.dev.proudsite.pl/",
                    "site_kind": "primary",
                    "status": "publish",
                },
            ),
        ]
    )

    linkedin_action = actions["act_prepare_linkedin_social_drafts"]
    source_inputs = linkedin_action.payload["source_inputs"]
    serialized_inputs = json.dumps(source_inputs, ensure_ascii=False)

    assert source_inputs
    assert "candidate_inputs" not in linkedin_action.payload
    assert "ev_gsc_social_candidate" in linkedin_action.evidence_ids
    assert "ev_wordpress_dev_site_candidate" not in linkedin_action.evidence_ids
    assert "ekologus.dev.proudsite.pl" not in serialized_inputs


def test_codex_context_pack_scopes_demand_gen_payload() -> None:
    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-demand-gen-operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-demand-gen-operator"
    assert "ads_diagnostics" in data
    assert "ga4_diagnostics" in data
    assert "demand_gen_readiness" in data
    assert "merchant_diagnostics" not in data
    assert "command_center" not in data
    assert set(data["context_scope"]["source_connectors"]) == {
        "google_ads",
        "google_analytics_4",
    }
    assert [action["id"] for action in data["active_action_objects"]] == [
        "act_review_demand_gen_readiness"
    ]
    assert data["active_action_objects"][0]["action_plan"]["apply_status_label"] == (
        "zablokowane do sprawdzenia"
    )
    assert data["ads_diagnostics"]["action_ids"] == []
    readiness = data["demand_gen_readiness"]
    assert readiness["status"] == "blocked"
    assert readiness["title"].startswith("Demand Gen:")
    assert readiness["metric_tiles"]["kampanie Ads"] == readiness["campaign_rows_evaluated"]
    assert readiness["metric_tiles"]["braki"] == len(readiness["missing_read_contracts"])
    assert readiness["action_ids"] == ["act_review_demand_gen_readiness"]
    assert readiness["payload_preview"][0]["preview_contract"] == (
        "demand_gen_readiness_review_preview_v1"
    )
    assert readiness["payload_preview"][0]["api_mutation_ready"] is False
    assert readiness["source_connectors"] == ["google_ads", "google_analytics_4"]
    assert readiness["source_connector_labels"] == ["Google Ads", "GA4"]
    assert (
        "dowód" in readiness["evidence_summary_label"]
        or "dowod" in readiness["evidence_summary_label"]
    )
    assert isinstance(readiness["campaign_rows_evaluated"], int)
    assert isinstance(readiness["campaign_channel_counts"], dict)
    assert isinstance(readiness["demand_gen_campaign_rows"], list)
    campaign_rows = data["ads_diagnostics"]["campaign_read_contract"]["campaign_rows"]
    if campaign_rows:
        assert any(row.get("advertising_channel_type") for row in campaign_rows)
        assert readiness["campaign_rows_evaluated"] >= len(campaign_rows)
        assert readiness["campaign_channel_counts"]
        assert "demand_gen_campaign_rows" in readiness["available_read_contracts"]
        assert "demand_gen_campaign_rows" not in readiness["missing_read_contracts"]
    assert "demand_gen_asset_group_rows" not in readiness["missing_read_contracts"]
    assert isinstance(readiness["demand_gen_ad_group_ad_rows"], list)
    assert isinstance(readiness["demand_gen_creative_asset_rows"], list)
    if "demand_gen_ad_group_ad_rows" in readiness["available_read_contracts"]:
        assert "demand_gen_ad_group_ad_rows" not in readiness["missing_read_contracts"]
    else:
        assert "demand_gen_ad_group_ad_rows" in readiness["missing_read_contracts"]
    if "demand_gen_creative_asset_rows" in readiness["available_read_contracts"]:
        assert "demand_gen_creative_asset_rows" not in readiness["missing_read_contracts"]
    else:
        assert "demand_gen_creative_asset_rows" in readiness["missing_read_contracts"]
    assert "demand_gen_readiness_review_action_object" in readiness["available_read_contracts"]
    assert "demand_gen_action_object" not in readiness["missing_read_contracts"]
    assert "rekomendacja uruchomienia Demand Gen" in readiness["blocked_claims"]
    assert "sections" not in data["ga4_diagnostics"]
    assert '"metric_facts":' not in json.dumps(data["ga4_diagnostics"])
    assert (
        data["ga4_diagnostics"]["context_pack_compaction"]["full_endpoint"]
        == "/api/ga4/diagnostics"
    )
    assert data["ads_diagnostics"]["context_pack_compaction"]["metric_facts_removed"] is True
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000


def test_codex_context_pack_scopes_demand_gen_without_full_ga4_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_full_ga4_builder(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Demand Gen context must not build full GA4 diagnostics")

    monkeypatch.setattr(
        "apps.api.wilq_api.context_skill.build_ga4_diagnostics",
        fail_full_ga4_builder,
    )

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-demand-gen-operator"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "demand_gen_readiness" in data
    assert (
        data["ga4_diagnostics"]["context_pack_compaction"]["full_endpoint"]
        == "/api/ga4/diagnostics"
    )


def test_demand_gen_diagnostics_exposes_honest_readiness_contract() -> None:
    response = client.get("/api/demand-gen/diagnostics")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["title"].startswith("Demand Gen:")
    assert data["metric_tiles"]["kampanie Ads"] == data["campaign_rows_evaluated"]
    assert data["metric_tiles"]["braki"] == len(data["missing_read_contracts"])
    assert data["source_connectors"] == ["google_ads", "google_analytics_4"]
    assert data["source_connector_labels"] == ["Google Ads", "GA4"]
    assert "dowód" in data["evidence_summary_label"] or "dowod" in data["evidence_summary_label"]
    assert data["action_ids"] == ["act_review_demand_gen_readiness"]
    assert data["payload_preview"][0]["preview_contract"] == (
        "demand_gen_readiness_review_preview_v1"
    )
    assert data["payload_preview"][0]["apply_allowed"] is False
    assert data["payload_preview"][0]["destructive"] is False
    assert isinstance(data["campaign_rows_evaluated"], int)
    assert isinstance(data["campaign_channel_counts"], dict)
    assert isinstance(data["demand_gen_campaign_rows"], list)
    if data["campaign_rows_evaluated"] > 0:
        assert "demand_gen_campaign_rows" in data["available_read_contracts"]
        assert "demand_gen_campaign_rows" not in data["missing_read_contracts"]
    assert "demand_gen_asset_group_rows" not in data["missing_read_contracts"]
    assert isinstance(data["demand_gen_ad_group_ad_rows"], list)
    assert isinstance(data["demand_gen_creative_asset_rows"], list)
    if "demand_gen_ad_group_ad_rows" in data["available_read_contracts"]:
        assert "demand_gen_ad_group_ad_rows" not in data["missing_read_contracts"]
    else:
        assert "demand_gen_ad_group_ad_rows" in data["missing_read_contracts"]
    if "demand_gen_creative_asset_rows" in data["available_read_contracts"]:
        assert "demand_gen_creative_asset_rows" not in data["missing_read_contracts"]
    else:
        assert "demand_gen_creative_asset_rows" in data["missing_read_contracts"]
    assert isinstance(data["demand_gen_landing_quality_rows"], list)
    assert isinstance(data["demand_gen_campaign_mode_review_rows"], list)
    assert "demand_gen_landing_quality_by_campaign" not in data["missing_read_contracts"]
    assert "demand_gen_campaign_mode_review" not in data["missing_read_contracts"]
    assert "demand_gen_readiness_review_action_object" in data["available_read_contracts"]
    assert "demand_gen_action_object" not in data["missing_read_contracts"]
    assert "rekomendacja uruchomienia Demand Gen" in data["blocked_claims"]


def test_demand_gen_diagnostics_does_not_require_full_ga4_builder() -> None:
    response = client.get("/api/demand-gen/diagnostics")

    assert response.status_code == 200
    assert response.json()["source_connectors"] == ["google_ads", "google_analytics_4"]


def test_demand_gen_diagnostics_uses_empty_read_ad_and_asset_contracts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "demand_gen.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "demand_gen.duckdb"))
    run = ConnectorRefreshRun(
        id="refresh_google_ads_demand_gen_empty_read",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_ads_demand_gen_empty_read"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "demand_gen_ad_group_ad_status": "ready",
            "demand_gen_ad_group_ad_row_count": 0,
            "demand_gen_asset_reference_count": 0,
            "demand_gen_creative_asset_status": "ready",
            "demand_gen_creative_asset_row_count": 0,
            "demand_gen_creative_asset_impressions": 0,
        },
        summary="Google Ads Demand Gen empty-read proof seed.",
    )
    ga4_run = ConnectorRefreshRun(
        id="refresh_google_analytics_4_demand_gen_landing_read",
        connector_id="google_analytics_4",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_google_analytics_4_demand_gen_landing_read"],
        external_call_attempted=True,
        vendor_data_collected=True,
        summary="GA4 Demand Gen landing quality seed.",
    )
    local_state_store().save_connector_refresh_run(run)
    local_state_store().save_connector_refresh_run(ga4_run)
    metric_store().save_connector_refresh_metrics(
        run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=12,
                dimensions={
                    "campaign_id": "103",
                    "campaign_name": "Demand Gen Test",
                    "campaign_status": "PAUSED",
                    "advertising_channel_type": "DEMAND_GEN",
                },
            ),
            VendorMetricFact(
                name="demand_gen_ad_available",
                value=1,
                dimensions={
                    "campaign_id": "103",
                    "campaign_name": "Demand Gen Test",
                    "campaign_status": "PAUSED",
                    "advertising_channel_type": "DEMAND_GEN",
                    "ad_group_id": "203",
                    "ad_group_name": "DG grupa",
                    "ad_id": "803",
                    "ad_type": "DEMAND_GEN_MULTI_ASSET_AD",
                    "ad_status": "PAUSED",
                },
                period="demand_gen_ad_inventory",
            ),
            VendorMetricFact(
                name="demand_gen_ad_asset_reference_count",
                value=4,
                dimensions={
                    "campaign_id": "103",
                    "campaign_name": "Demand Gen Test",
                    "campaign_status": "PAUSED",
                    "advertising_channel_type": "DEMAND_GEN",
                    "ad_group_id": "203",
                    "ad_group_name": "DG grupa",
                    "ad_id": "803",
                    "ad_type": "DEMAND_GEN_MULTI_ASSET_AD",
                    "ad_status": "PAUSED",
                },
                period="demand_gen_ad_inventory",
            ),
            VendorMetricFact(
                name="demand_gen_creative_asset_impressions",
                value=44,
                dimensions={
                    "asset_id": "901",
                    "asset_type": "DEMAND_GEN_CAROUSEL_CARD",
                    "field_type": "DEMAND_GEN_CAROUSEL_CARD",
                },
                period="demand_gen_creative_asset",
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        ga4_run,
        detailed_facts=[
            VendorMetricFact(
                name="active_users",
                value=18,
                dimensions={
                    "landing_page": "/dg-test/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Demand Gen Test",
                },
                period="ga4_landing_source_campaign",
            ),
            VendorMetricFact(
                name="sessions",
                value=24,
                dimensions={
                    "landing_page": "/dg-test/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Demand Gen Test",
                },
                period="ga4_landing_source_campaign",
            ),
            VendorMetricFact(
                name="engagement_rate",
                value=0.75,
                dimensions={
                    "landing_page": "/dg-test/",
                    "source_medium": "google / cpc",
                    "campaign_name": "Demand Gen Test",
                },
                period="ga4_landing_source_campaign",
            ),
        ],
    )

    response = client.get("/api/demand-gen/diagnostics")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert "demand_gen_ad_group_ad_rows" in data["available_read_contracts"]
    assert "demand_gen_creative_asset_rows" in data["available_read_contracts"]
    assert "demand_gen_ad_group_ad_rows" not in data["missing_read_contracts"]
    assert "demand_gen_asset_group_rows" not in data["missing_read_contracts"]
    assert "demand_gen_creative_asset_rows" not in data["missing_read_contracts"]
    assert "demand_gen_landing_quality_by_campaign" in data["available_read_contracts"]
    assert "demand_gen_campaign_mode_review" in data["available_read_contracts"]
    assert "demand_gen_landing_quality_by_campaign" not in data["missing_read_contracts"]
    assert "demand_gen_campaign_mode_review" not in data["missing_read_contracts"]
    assert data["metric_tiles"]["reklamy Demand Gen"] == 1
    assert data["metric_tiles"]["kreacje Demand Gen"] == 1
    assert data["metric_tiles"]["strony wejścia Demand Gen"] == 1
    assert data["metric_tiles"]["kontrola trybu"] == 1
    assert len(data["demand_gen_ad_group_ad_rows"]) == 1
    assert len(data["demand_gen_creative_asset_rows"]) == 1
    assert len(data["demand_gen_landing_quality_rows"]) == 1
    assert len(data["demand_gen_campaign_mode_review_rows"]) == 1
    assert data["demand_gen_ad_group_ad_rows"][0]["ad_id"] == "803"
    assert data["demand_gen_ad_group_ad_rows"][0]["asset_reference_count"] == 4
    assert data["demand_gen_creative_asset_rows"][0]["asset_id"] == "901"
    assert data["demand_gen_creative_asset_rows"][0]["impressions"] == 44
    assert data["demand_gen_landing_quality_rows"][0]["campaign_name"] == "Demand Gen Test"
    assert data["demand_gen_landing_quality_rows"][0]["landing_page"] == "/dg-test/"
    assert data["demand_gen_landing_quality_rows"][0]["landing_page_label"] == "/dg-test/"
    assert data["demand_gen_landing_quality_rows"][0]["source_medium_label"] == ("google / cpc")
    assert data["demand_gen_landing_quality_rows"][0]["active_users"] == 18
    assert data["demand_gen_landing_quality_rows"][0]["active_users_label"] == "18"
    assert data["demand_gen_landing_quality_rows"][0]["sessions"] == 24
    assert data["demand_gen_landing_quality_rows"][0]["sessions_label"] == "24"
    assert data["demand_gen_landing_quality_rows"][0]["engagement_rate"] == 0.75
    assert data["demand_gen_landing_quality_rows"][0]["engagement_rate_label"] == "75%"
    assert data["demand_gen_campaign_mode_review_rows"][0]["campaign_name"] == ("Demand Gen Test")
    assert data["demand_gen_campaign_rows"][0]["advertising_channel_type_label"] == ("Demand Gen")
    assert data["demand_gen_campaign_rows"][0]["campaign_status_label"] == "wstrzymana"
    assert data["demand_gen_campaign_rows"][0]["clicks_label"] == "12"
    assert data["demand_gen_campaign_rows"][0]["impressions_label"] == (
        "brak odczytu wyświetleń Ads"
    )
    assert data["demand_gen_campaign_rows"][0]["cost_label"] == "brak odczytu kosztu Ads"
    assert data["demand_gen_campaign_rows"][0]["conversions_label"] == (
        "brak odczytu konwersji Ads"
    )
    assert data["demand_gen_campaign_rows"][0]["evidence_summary_label"] == ("1 dowód źródłowy")
    assert data["demand_gen_ad_group_ad_rows"][0]["evidence_summary_label"] == ("1 dowód źródłowy")
    assert data["demand_gen_creative_asset_rows"][0]["evidence_summary_label"] == (
        "1 dowód źródłowy"
    )
    assert data["demand_gen_landing_quality_rows"][0]["evidence_summary_label"] == (
        "1 dowód źródłowy"
    )
    campaign_mode_review_row = data["demand_gen_campaign_mode_review_rows"][0]
    assert "transition_candidate" not in campaign_mode_review_row
    assert campaign_mode_review_row["advertising_channel_type_label"] == "Demand Gen"
    assert campaign_mode_review_row["campaign_status_label"] == "wstrzymana"
    assert campaign_mode_review_row["review_required"] is False
    assert campaign_mode_review_row["review_status_label"] == "bez zmiany trybu"
    assert campaign_mode_review_row["evidence_summary_label"] == "1 dowód źródłowy"
    assert "already_demand_gen" in campaign_mode_review_row["reason"]
    preview = data["payload_preview"][0]
    assert preview["demand_gen_ad_group_ad_row_count"] == 1
    assert preview["demand_gen_creative_asset_row_count"] == 1
    assert preview["demand_gen_landing_quality_row_count"] == 1
    assert preview["demand_gen_campaign_mode_review_row_count"] == 1
    assert preview["apply_allowed"] is False
    assert "rekomendacja uruchomienia Demand Gen" in data["blocked_claims"]


def test_demand_gen_metric_rows_expose_self_defending_labels() -> None:
    campaign_row = AdsCampaignMetricRow(
        campaign_name="Demand Gen Test",
        evidence_ids=["ev_ads_demand_gen"],
    )
    assert campaign_row.clicks_label == "brak odczytu kliknięć Ads"
    assert campaign_row.impressions_label == "brak odczytu wyświetleń Ads"
    assert campaign_row.cost_label == "brak odczytu kosztu Ads"
    assert campaign_row.conversions_label == "brak odczytu konwersji Ads"
    assert campaign_row.conversion_value_label == "brak odczytu wartości konwersji Ads"

    labeled_campaign_row = AdsCampaignMetricRow(
        campaign_name="Demand Gen Test",
        clicks=1200,
        impressions=34567,
        cost_micros=12345678,
        conversions=2.5,
        conversion_value=320.25,
        evidence_ids=["ev_ads_demand_gen"],
    )
    assert labeled_campaign_row.clicks_label == "1 200"
    assert labeled_campaign_row.impressions_label == "34 567"
    assert labeled_campaign_row.cost_label == "12,35 jedn. konta"
    assert labeled_campaign_row.conversions_label == "2,5"
    assert labeled_campaign_row.conversion_value_label == "320,25"

    landing_row = DemandGenLandingQualityRow(
        campaign_name="Demand Gen Test",
        landing_page="/oferta/",
        evidence_ids=["ev_ga4_demand_gen"],
    )
    assert landing_row.active_users_label == "brak odczytu aktywnych użytkowników GA4"
    assert landing_row.sessions_label == "brak odczytu sesji GA4"
    assert landing_row.engagement_rate_label == "brak odczytu zaangażowania GA4"

    labeled_landing_row = DemandGenLandingQualityRow(
        campaign_name="Demand Gen Test",
        landing_page="/oferta/",
        active_users=20,
        sessions=30,
        engagement_rate=0.125,
        evidence_ids=["ev_ga4_demand_gen"],
    )
    assert labeled_landing_row.active_users_label == "20"
    assert labeled_landing_row.sessions_label == "30"
    assert labeled_landing_row.engagement_rate_label == "12,5%"


def test_demand_gen_readiness_uses_ads_summary_view(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.api.wilq_api import context_demand_gen

    requested_views: list[str] = []

    class FakeAdsDiagnostics:
        def model_dump(self, *, mode: str) -> dict[str, Any]:
            assert mode == "json"
            return {}

    def fake_build_ads_diagnostics(*, view: str = "full") -> FakeAdsDiagnostics:
        requested_views.append(view)
        return FakeAdsDiagnostics()

    monkeypatch.setattr(context_demand_gen, "_demand_gen_google_ads_metric_facts", lambda: [])
    monkeypatch.setattr(context_demand_gen, "_demand_gen_ga4_metric_facts", lambda: [])
    monkeypatch.setattr(context_demand_gen, "build_ads_diagnostics", fake_build_ads_diagnostics)
    monkeypatch.setattr(
        context_demand_gen,
        "_readiness_contract",
        lambda ads, ga4, demand_gen_facts, ga4_facts: "demand_gen_contract",
    )

    assert context_demand_gen.build_readiness_contract() == "demand_gen_contract"
    assert requested_views == ["summary"]


def test_demand_gen_zero_campaign_next_step_is_operator_specific() -> None:
    from apps.api.wilq_api import context_demand_gen

    contract = context_demand_gen._readiness_contract(
        {
            "campaign_read_contract": {
                "campaign_rows": [
                    {"campaign_name": "Search", "advertising_channel_type": "SEARCH"},
                    {
                        "campaign_name": "Performance Max",
                        "advertising_channel_type": "PERFORMANCE_MAX",
                    },
                ]
            },
            "evidence_ids": ["ev_ads"],
        },
        {"evidence_ids": ["ev_ga4"]},
        [],
        [],
    )

    assert contract.status == "blocked"
    assert contract.metric_tiles["kampanie Demand Gen"] == 0
    assert "nie oceniaj jeszcze jakości kreacji ani ruchu" in contract.next_step.lower()
    assert "0 kampanii Demand Gen/Discovery" in contract.next_step
    assert contract.action_ids == ["act_review_demand_gen_readiness"]
    assert "act_" not in contract.next_step


def test_demand_gen_review_action_is_validate_only_and_scoped() -> None:
    response = client.get("/api/actions/act_review_demand_gen_readiness")

    assert response.status_code == 200
    action = response.json()
    assert action["connector"] == "google_ads"
    assert action["mode"] == "prepare"
    assert action["payload"]["action_type"] == "google_ads_demand_gen_readiness_review"
    assert action["payload"]["preview_contract"] == "demand_gen_readiness_review_preview_v1"
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False
    assert action["payload"]["payload_preview"][0]["api_mutation_ready"] is False
    assert "rekomendacja uruchomienia Demand Gen" in action["payload"]["blocked_claims"]
    assert action["preview_cards"]
    preview_card = action["preview_cards"][0]
    assert preview_card["kind"] == "google_ads_demand_gen_readiness_review"
    assert preview_card["title_label"] == "Gotowość Demand Gen do sprawdzenia"
    preview_rows = {row["label"]: row["value"] for row in preview_card["rows"]}
    assert "Kanały kampanii" in preview_rows
    assert "PERFORMANCE_MAX" not in str(preview_card)
    assert "UNKNOWN" not in str(preview_card)

    validation = client.post(
        "/api/actions/act_review_demand_gen_readiness/validate",
        json={},
    )

    assert validation.status_code == 200
    assert validation.json()["valid"] is True


def test_codex_context_pack_includes_expert_rule_summaries() -> None:
    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert response.status_code == 200
    data = response.json()
    rule_ids = {rule["id"] for rule in data["expert_rule_summaries"]}
    assert "ads_principles_v1" in rule_ids
    assert data["expert_capabilities"]
    assert all(capability["required_inputs"] == [] for capability in data["expert_capabilities"])
    assert all(
        isinstance(capability["required_inputs_total"], int)
        for capability in data["expert_capabilities"]
    )
    assert "required_mapping" not in json.dumps(data["expert_capabilities"])


def test_knowledge_playbooks_are_machine_readable_and_evidence_gated() -> None:
    response = client.get("/api/knowledge/playbooks")
    assert response.status_code == 200
    playbooks = response.json()
    families = {playbook["family"] for playbook in playbooks}
    assert {
        "google_ads_search_playbook",
        "google_ads_budget_review_playbook",
        "google_ads_demand_gen_playbook",
        "google_ads_pmax_playbook",
        "google_ads_negative_keywords_playbook",
        "google_ads_custom_segments_playbook",
        "gsc_seo_content_playbook",
        "ahrefs_content_gap_playbook",
        "localo_local_seo_playbook",
        "ga4_behavior_diagnostics_playbook",
        "merchant_feed_optimization_playbook",
        "linkedin_content_playbook",
        "facebook_content_playbook",
        "wordpress_content_refresh_playbook",
    }.issubset(families)
    assert all("evidence_ids" in playbook["required_evidence"] for playbook in playbooks)
    assert all(playbook["maps_to_opportunity_types"] for playbook in playbooks)
    assert all(playbook["maps_to_action_types"] for playbook in playbooks)
    search_playbook = next(
        playbook for playbook in playbooks if playbook["id"] == "google_ads_search_playbook"
    )
    assert search_playbook["display_title"] == "Diagnostyka wyszukiwanych haseł Google Ads"
    assert search_playbook["card_type_label"] == "wzorzec Ads"
    assert search_playbook["source_type_label"] == "zasada pracy"
    assert search_playbook["required_evidence_summary_label"] == "4 wymagane dowody"
    assert search_playbook["mapped_action_type_summary_label"] == "3 typy akcji do sprawdzenia"


def test_knowledge_compiler_produces_lineage_preserving_card_types() -> None:
    response = client.post("/api/knowledge/condense")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    card_types = {card["card_type"] for card in result["cards"]}
    assert {
        "service_card",
        "content_card",
        "keyword_cluster_card",
        "campaign_card",
        "voice_rule",
        "ads_pattern_card",
        "negative_keyword_pattern_card",
        "competitor_card",
        "local_visibility_card",
        "social_pattern_card",
    }.issubset(card_types)
    assert all(card["source_lineage"] for card in result["cards"])
    assert all(card["source_url_or_path"] for card in result["cards"])
    cards_by_id = {card["id"]: card for card in result["cards"]}
    assert cards_by_id["card_goal_001_rules"]["display_title"] == "Zakaz wymyślania metryk"
    assert cards_by_id["card_goal_001_rules"]["card_type_label"] == "reguła głosu"
    assert cards_by_id["card_goal_001_rules"]["source_type_label"] == "reguła projektu"
    assert "dowodach i źródłach danych" in cards_by_id["card_goal_001_rules"]["summary"]
    assert "evidence IDs" not in cards_by_id["card_goal_001_rules"]["summary"]


def test_codex_context_pack_includes_compiled_knowledge_cards() -> None:
    response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert response.status_code == 200
    data = response.json()
    card_ids = {card["id"] for card in data["knowledge_card_summaries"]}
    assert "card_google_ads_search_playbook" in card_ids
    assert "card_google_ads_budget_review_playbook" in card_ids
    assert "card_goal_001_rules" in card_ids
    evidence_ids = {item["id"] for item in data["evidence_summaries"]}
    assert "ev_connector_google_ads_status" in evidence_ids


def test_content_context_uses_real_ekologus_source_fact_cards() -> None:
    cards = content_knowledge_cards_for_skill("wilq-content-operator")
    card_ids = {card.id for card in cards}

    assert "ekologus_service_bdo_reporting" in card_ids
    assert "ekologus_service_environmental_consulting_outsourcing" in card_ids

    bdo = next(card for card in cards if card.id == "ekologus_service_bdo_reporting")
    compact = compact_content_knowledge_card_for_operator_context(bdo)
    assert compact["summary"]
    assert compact["source_fact_ids"]
    assert compact["evidence_ids"]
    assert compact["source_lineage"]
    assert compact["lifecycle_status"] == "approved_current"
    assert compact["forbidden_claims"]
    assert any(card.source_material_ids for card in cards)


def test_knowledge_operating_map_binds_sources_to_decisions() -> None:
    response = client.get("/api/knowledge/operating-map")
    assert response.status_code == 200
    data = response.json()
    assert data["source_card_count"] >= 10
    assert data["playbook_count"] >= 10
    assert data["expert_rule_count"] >= 10
    assert data["blocked_binding_summary_label"]
    assert data["missing_contract_summary_label"]
    assert data["blocked_claim_count_summary_label"]
    binding_by_id = {binding["id"]: binding for binding in data["bindings"]}

    daily = binding_by_id["knowledge_daily_command"]
    assert daily["route"] == "/command-center"
    assert daily["route_label"] == "Centrum pracy"
    assert daily["status"] == "ready"
    assert daily["status_label"] in {"gotowe", "gotowe z blokadami"}
    assert daily["risk_label"] in {"niskie ryzyko", "średnie ryzyko"}
    assert daily["skill_id"] == "wilq-daily-command"
    assert daily["knowledge_card_ids"] == ["card_goal_001_rules"]
    assert daily["metric_tiles"]["decyzje"] >= 1
    assert daily["metric_tiles"]["blokady"] >= 0
    assert daily["evidence_ids"]
    assert daily["evidence_summary_label"]
    assert daily["source_connector_labels"]
    assert daily["source_connector_summary_label"]
    assert daily["action_summary_label"]
    assert daily["knowledge_summary_label"]
    assert daily["required_evidence_summary_label"]
    assert daily["missing_contract_summary_label"]
    assert daily["missing_contract_detail_label"]
    assert daily["has_missing_contracts"] is False
    assert daily["source_lineage_summary_label"]
    assert "blocked_claim_labels" in daily
    assert "blocked_claim_count_summary_label" in daily
    assert isinstance(daily["has_blocked_claims"], bool)
    assert "missing_contract_labels" in daily
    visible_blocked_claims = [
        claim
        for binding in data["bindings"]
        for claim in [
            *binding.get("blocked_claims", []),
            *binding.get("blocked_claim_labels", []),
        ]
    ]
    assert "blokada do sprawdzenia" not in visible_blocked_claims

    ads = binding_by_id["knowledge_ads_daily_check"]
    assert ads["route"] == "/ads-doctor"
    assert ads["route_label"] == "Google Ads"
    assert ads["status_label"] == "gotowe"
    assert ads["risk_label"] in {"niskie ryzyko", "średnie ryzyko", "wysokie ryzyko"}
    assert ads["skill_id"] == "wilq-ads-doctor"
    assert "card_google_ads_search_playbook" in ads["knowledge_card_ids"]
    assert "google_ads_search_playbook" in ads["playbook_ids"]
    assert "ads_search_terms_v1" in ads["expert_rule_ids"]
    assert "search_terms" in ads["required_evidence"]
    assert ads["action_ids"]
    assert ads["source_connector_summary_label"] == "Google Ads"
    assert "akcj" in ads["action_summary_label"]
    assert "wiedzy" in ads["knowledge_summary_label"]
    assert "dow" in ads["required_evidence_summary_label"]
    assert "ślad" in ads["source_lineage_summary_label"]

    localo = binding_by_id["knowledge_localo_visibility_review"]
    assert localo["status"] == "blocked"
    assert localo["status_label"] == "zablokowane"
    assert localo["route_label"] == "Localo"
    assert "local_ranking_rows" in localo["missing_contracts"]
    assert "lokalne pozycje" in localo["missing_contract_labels"]
    assert localo["missing_contract_summary_label"]
    assert localo["missing_contract_detail_label"]
    assert localo["has_missing_contracts"] is True
    assert "card_localo_local_seo_playbook" in localo["knowledge_card_ids"]


def test_demand_gen_readiness_uses_operator_summary_labels() -> None:
    response = client.get("/api/demand-gen/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert data["evidence_summary_label"]
    assert data["action_summary_label"]
    assert all(label for label in data["campaign_channel_labels"].values())
    assert "PERFORMANCE_MAX" not in data["campaign_channel_labels"].values()


def test_workflows_are_decision_backed_operator_contracts() -> None:
    response = client.get("/api/workflows")
    assert response.status_code == 200
    workflows = response.json()
    workflow_by_id = {workflow["id"]: workflow for workflow in workflows}

    daily_command = workflow_by_id["daily_command"]
    assert daily_command["label"] == "Plan dnia WILQ"
    assert daily_command["route"] == "/command-center"
    assert daily_command["route_label"] == "Centrum pracy"
    assert daily_command["status_label"] in {"gotowe", "gotowe z blokadami", "zablokowane"}
    assert daily_command["risk_label"] in {"niskie ryzyko", "średnie ryzyko"}
    assert daily_command["skill_id"] == "wilq-daily-command"
    assert daily_command["metric_tiles"]["decyzje"] >= 1
    assert daily_command["source_connectors"]
    assert daily_command["source_connector_labels"]
    assert daily_command["source_connector_summary_label"]
    assert daily_command["evidence_ids"]
    assert daily_command["evidence_summary_label"]
    assert daily_command["action_summary_label"]
    assert daily_command["blocked_claim_summary_label"]
    assert daily_command["missing_contract_summary_label"]
    assert daily_command["missing_contract_detail_label"]

    ads_daily = workflow_by_id["ads_daily_check"]
    assert ads_daily["label"] == "Ocena Ads"
    assert ads_daily["route"] == "/ads-doctor"
    assert ads_daily["route_label"] == "Google Ads"
    assert ads_daily["status_label"] in {"gotowe", "zablokowane"}
    assert ads_daily["skill_id"] == "wilq-ads-doctor"
    assert "kampanie" in ads_daily["metric_tiles"]
    assert any(value >= 1 for value in ads_daily["metric_tiles"].values())
    assert "act_prepare_ads_campaign_review_queue" in ads_daily["action_ids"]

    localo = workflow_by_id["localo_visibility_review"]
    assert localo["label"] == "Widoczność lokalna Localo"
    assert localo["status"] == "blocked"
    assert localo["status_label"] == "zablokowane"
    assert localo["route"] == "/localo"
    assert localo["route_label"] == "Localo"
    assert localo["source_connector_labels"] == ["Localo"]
    assert localo["source_connector_summary_label"] == "Localo"
    assert "local_ranking_rows" in localo["missing_contracts"]
    assert "lokalne pozycje" in localo["missing_contract_labels"]
    assert localo["missing_contract_summary_label"] == "3 brakujące zakresy danych"
    assert "lokalne pozycje" in localo["missing_contract_detail_label"]
    assert localo["blocked_claim_labels"]
    assert localo["blocked_claim_summary_label"] == "2 zablokowane obietnice"

    serialized = json.dumps(workflows, ensure_ascii=False)
    assert "Workflow definition runs against WILQ API" not in serialized
    assert "Fetch WILQ API context" not in serialized
    assert "Ads daily check" not in serialized
    assert "Merchant feed review" not in serialized
    assert "GSC content doctor" not in serialized
    assert "Localo visibility review" not in serialized
    assert "workflow jako" not in serialized
    assert "ocena zwrotu z reklam" not in serialized
    assert "wzrost konwersji" not in serialized
    assert "local ranking " + "up" + "lift" not in serialized
    assert "local_ranking_uplift_claim" not in serialized
    assert "GBP performance verdict" not in serialized


def test_workflow_label_fallbacks_do_not_expose_raw_values() -> None:
    raw_value = "new_raw_workflow_status"

    labels = [
        _workflow_status_label(raw_value),
        _workflow_risk_label(raw_value),
        _workflow_run_status_label(raw_value),
    ]

    assert labels == [
        "status procesu do sprawdzenia",
        "ryzyko procesu do sprawdzenia",
        "status uruchomienia do sprawdzenia",
    ]
    assert all(raw_value not in label for label in labels)


def test_workflow_missing_contract_detail_fallback_explains_complete_process() -> None:
    workflow = Workflow(
        id="workflow_without_missing_contracts",
        label="Proces bez braków",
        description="Proces testowy bez brakujących zakresów danych.",
        steps=[],
    )

    assert workflow.missing_contract_detail_label == "Dane kompletne dla tego procesu"
    assert workflow.missing_contract_summary_label == "Dane kompletne dla tej decyzji"
    assert workflow.missing_contract_detail_label != "brak"


def test_workflow_run_persists_to_local_state_with_redaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "workflow_state.sqlite3"))
    response = client.post(
        "/api/workflows/daily_command/runs",
        json={
            "id": "run_daily_command_contract",
            "input": {
                "connector_ids": ["google_ads"],
                "parameters": {
                    "api_key": "sk-workflowsecretvalue1234567890",  # pragma: allowlist secret
                },
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "run_daily_command_contract"
    assert data["status"] == "queued"
    assert data["input"]["parameters"]["api_key"] == "[REDACTED]"

    detail_response = client.get("/api/workflow-runs/run_daily_command_contract")
    assert detail_response.status_code == 200
    assert detail_response.json()["input"]["parameters"]["api_key"] == "[REDACTED]"

    list_response = client.get("/api/workflow-runs")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == ["run_daily_command_contract"]
