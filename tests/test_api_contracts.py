from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._contract_support.ads_review_seed import (
    seed_google_ads_live_review_metric_facts,
)
from tests._contract_support.api_client import client
from tests._contract_support.assertions import assert_operator_context_strings_clean
from tests._contract_support.env import clear_localo_env
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID
from wilq.briefing.marketing_brief import build_marketing_brief
from wilq.connectors.vendor import VendorMetricFact
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
    CommandCenterBriefItem,
    CommandCenterResponse,
    ConnectorCapability,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    ConnectorStatus,
    ConnectorStatusValue,
    ConnectorSummary,
    DailyDecision,
    FreshnessState,
    MarketingBrief,
    MetricFact,
    OpportunityDomain,
    TacticalQueueResponse,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store


def save_localo_visibility_metric_facts() -> None:
    localo_run = ConnectorRefreshRun(
        id="refresh_localo_opportunity_seed",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_refresh_localo_opportunity_seed"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "api": "localo_mcp_oauth_probe",
            "mcp_initialize_status": 200,
            "authorization_code_supported": 1,
            "pkce_s256_supported": 1,
            "access_token_present": 1,
            "localo_active_place_count": 4,
            "localo_tracked_keyword_count": 23,
            "localo_avg_visibility_current": 52.8261,
            "localo_reviews_count": 793,
        },
        summary="Odczyt danych Localo zakończony agregatami.",
    )
    local_state_store().save_connector_refresh_run(localo_run)
    metric_store().save_connector_refresh_metrics(
        localo_run,
        detailed_facts=[
            VendorMetricFact(
                "localo_active_place_count",
                4,
                {"contract": "place_inventory", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_tracked_keyword_count",
                23,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_avg_visibility_current",
                52.8261,
                {"contract": "local_rankings", "scope": "active_places"},
                period="localo_mcp_read",
            ),
            VendorMetricFact(
                "localo_reviews_count",
                793,
                {"contract": "reviews", "scope": "active_places"},
                period="localo_mcp_read",
            ),
        ],
    )


def test_opportunities_are_derived_from_evidence_and_rule_mappings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_localo_env(monkeypatch)
    monkeypatch.setenv("LOCALO_API_TOKEN", "localo-token-test")
    monkeypatch.setenv("LOCALO_ORGANIZATION_ID", "localo-org-test")
    monkeypatch.setenv("LOCALO_ACCESS_TOKEN", "localo-access-test")
    save_localo_visibility_metric_facts()

    response = client.get("/api/opportunities")
    assert response.status_code == 200
    opportunities = response.json()
    opportunity_ids = {item["id"] for item in opportunities}
    assert opportunity_ids == {
        "opp_decision_review_merchant_feed_issues",
        "opp_decision_prepare_content_refresh_queue",
        "opp_decision_review_ga4_landing_quality",
        "opp_decision_review_ads_campaign_metrics",
        "opp_decision_review_localo_visibility_facts",
    }
    google_ads = next(
        item for item in opportunities if item["id"] == "opp_decision_review_ads_campaign_metrics"
    )
    assert google_ads["type"] == "google_ads_review_queue"
    assert google_ads["domain"] == "google_ads"
    assert google_ads["domain_label"] == "Google Ads"
    assert google_ads["source_connector_labels"] == ["Google Ads"]
    assert "dowod" in google_ads["evidence_summary_label"]
    assert google_ads["action_summary_label"] == "4 akcje do sprawdzenia"
    assert google_ads["knowledge_summary_label"] == "1 element wiedzy użyty w decyzji"
    assert google_ads["metric_tiles"]["kampanie"] >= 1
    assert google_ads["action_ids"] == [
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
    ]
    assert google_ads["is_fixture"] is False
    localo = next(
        item
        for item in opportunities
        if item["id"] == "opp_decision_review_localo_visibility_facts"
    )
    assert localo["type"] == "localo_visibility_drop"
    assert localo["domain"] == "localo"
    assert localo["action_ids"] == ["act_review_localo_visibility_facts"]
    assert localo["is_fixture"] is False
    content = next(
        item for item in opportunities if item["id"] == "opp_decision_prepare_content_refresh_queue"
    )
    assert content["type"] == "content_brief_candidate"
    assert content["domain"] == "gsc_seo"
    assert content["action_ids"] == ["act_prepare_content_refresh_queue"]
    assert content["is_fixture"] is False
    serialized = json.dumps(opportunities, ensure_ascii=False)
    visible_opportunity_text = " ".join(
        " ".join(
            [
                item["title"],
                item["human_diagnosis"],
                item["recommended_action"],
            ]
        )
        for item in opportunities
    )
    assert "opp_connector_" not in serialized
    assert "connector_configured" not in serialized
    assert "Run a read-only" not in serialized
    for stale_label in (
        "credentiali",
        "credentiale",
        "vendor_read",
        "fresh evidence",
        "query/page",
        "content-gap evidence",
        "inventory treści",
        "read-only refresh",
        "refreshu connectora",
        "rejestr reguł i playbooków",
        "playbooków",
    ):
        assert stale_label not in visible_opportunity_text


def test_marketing_brief_dedupes_command_center_blockers() -> None:
    blocked_decision = DailyDecision(
        id="decision_review_ga4_landing_quality",
        title="GA4: pomiar i jakość ruchu do kontroli",
        route="/ga4",
        status="blocked",
        priority=14,
        co_widzimy="GA4 ma problemy pomiaru.",
        dlaczego_to_ma_znaczenie="Brak kontraktu na zwrot z reklam i przychody.",
        bezpieczny_next_step="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        why_it_matters="Brak kontraktu na zwrot z reklam i przychody.",
        operator_action="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        source_connectors=["google_analytics_4"],
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        action_ids=["act_review_ga4_tracking_quality"],
        blocked_claims=["zwrot z reklam", "przychód"],
        risk=ActionRisk.low,
    )
    operator_brief_item = CommandCenterBriefItem(
        id="daily_ga4_landing_quality",
        title="GA4: pomiar i jakość ruchu do kontroli",
        route="/ga4",
        status="blocked",
        priority=14,
        summary="GA4 ma problemy pomiaru.",
        next_step="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        source_connectors=["google_analytics_4"],
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        action_ids=["act_review_ga4_tracking_quality"],
        blocked_claims=["zwrot z reklam", "przychód"],
        risk=ActionRisk.low,
    )
    command_center = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Otwórz /ga4.",
        blocker_count=1,
        daily_decisions=[blocked_decision],
        operator_brief=[operator_brief_item],
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )

    brief = build_marketing_brief(
        connectors=[],
        refresh_runs=[],
        actions=[],
        command_center=command_center,
    )

    blockers = next(section for section in brief.sections if section.id == "what_blocks_us").items
    assert len(blockers) == 1
    assert blockers[0].title == "GA4: pomiar i jakość ruchu do kontroli"


def test_marketing_brief_daily_context_limits_safe_actions_to_daily_decisions() -> None:
    daily_decision = DailyDecision(
        id="decision_review_ga4_landing_quality",
        title="GA4: pomiar i jakość ruchu do kontroli",
        route="/ga4",
        status="blocked",
        priority=14,
        co_widzimy="GA4 ma problemy pomiaru.",
        dlaczego_to_ma_znaczenie="Brak kontraktu na zwrot z reklam i przychody.",
        bezpieczny_next_step="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        why_it_matters="Brak kontraktu na zwrot z reklam i przychody.",
        operator_action="Otwórz /ga4 i sprawdź w WILQ review GA4.",
        source_connectors=["google_analytics_4"],
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        action_ids=["act_review_ga4_tracking_quality"],
        blocked_claims=["zwrot z reklam", "przychód"],
        risk=ActionRisk.low,
    )
    command_center = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Otwórz /ga4.",
        blocker_count=1,
        daily_decisions=[daily_decision],
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    daily_action = ActionObject(
        id="act_review_ga4_tracking_quality",
        title="Sprawdź jakość pomiaru GA4 przed oceną kampanii",
        domain=OpportunityDomain.ga4,
        connector="google_analytics_4",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_refresh_refresh_google_analytics_4_test"],
        human_diagnosis="GA4 wymaga sprawdzenia.",
        recommended_reason="Sprawdź pomiar GA4.",
        payload={"action_type": "ga4_review"},
        validation_status="not_validated",
        created_by="test",
    )
    noisy_action = ActionObject(
        id="act_review_demand_gen_readiness",
        title="Przygotuj sprawdzenie gotowości Demand Gen",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_refresh_refresh_google_ads_test"],
        human_diagnosis="Demand Gen nie należy do daily decision.",
        recommended_reason="Nie promuj w daily brief.",
        payload={"action_type": "demand_gen_review"},
        validation_status="not_validated",
        created_by="test",
    )

    brief = build_marketing_brief(
        connectors=[],
        refresh_runs=[],
        actions=[daily_action, noisy_action],
        command_center=command_center,
    )

    action_items = next(
        section for section in brief.sections if section.id == "safe_next_actions"
    ).items
    action_ids = [item.action_ids[0] for item in action_items]
    assert action_ids == ["act_review_ga4_tracking_quality"]


def test_codex_context_pack_embeds_marketing_brief_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "context_pack.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "context_pack.duckdb"))
    brief_response = client.get("/api/marketing/brief")
    assert brief_response.status_code == 200
    brief = brief_response.json()

    context_response = client.post("/api/codex/context-pack", json={"skill": "wilq-daily-command"})
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert_operator_context_strings_clean(context_payload)
    context_brief = context_payload["marketing_brief"]

    assert context_payload["context_scope"]["mode"] == "daily"
    assert context_payload["context_scope"]["skill"] == "wilq-daily-command"
    assert context_payload["context_scope"]["full_context_available"] is True
    assert context_payload["context_pack_compaction"]["mode"] == "daily_default"
    assert context_payload["context_pack_compaction"]["full_context_available"] is True
    assert context_payload["context_pack_compaction"]["command_center_daily_decisions_only"] is True
    assert context_payload["context_pack_compaction"]["expert_capabilities_compacted"] is True
    assert context_payload["context_pack_compaction"]["action_review_gates_compacted"] is True
    assert (
        context_payload["context_pack_compaction"]["full_marketing_brief_endpoint"]
        == "/api/marketing/brief"
    )
    assert context_payload["context_pack_compaction"]["evidence_summaries_limit"] == 32
    assert "command_center" in context_payload
    assert "tactical_queue" not in context_payload
    assert "ads_diagnostics" not in context_payload
    assert "merchant_diagnostics" not in context_payload
    assert len(context_payload["evidence_summaries"]) <= 32
    assert context_brief["language"] == "pl-PL"
    assert context_brief["language"] == brief["language"]
    assert context_brief["blocker_count"] == brief["blocker_count"]
    assert context_brief["recommendation_count"] == brief["recommendation_count"]
    assert context_brief["evidence_ids"] == brief["evidence_ids"]
    assert context_brief["action_ids"] == brief["action_ids"]
    assert [section["id"] for section in context_brief["sections"]] == [
        section["id"] for section in brief["sections"]
    ]
    assert len(context_brief["top_metric_facts"]) <= 8
    assert "connector_health" not in context_payload["command_center"]
    assert context_payload["command_center"]["daily_decisions"]
    assert "operator_brief" not in context_payload["command_center"]
    assert "action_plan" not in context_payload["command_center"]
    assert "demo_script" not in context_payload["command_center"]
    for connector in context_payload["connector_status"]:
        assert connector["status_label"]
        assert connector["status_label"] != connector["status"]
        assert connector["freshness"]["label"]
        assert connector["freshness"]["label"] != connector["freshness"]["state"]
        assert "status configured" not in connector["summary"]
        assert connector["status"] not in connector["summary"]
    for action in context_payload["active_action_objects"]:
        assert "metrics" not in action
        assert "payload" not in action
        assert action["api_endpoint_template"] == "/api/actions/{action_id}"
    for section in context_brief["sections"]:
        for item in section["items"]:
            assert item["metric_fact_count"] >= len(item["metric_facts"])
            assert len(item["metric_facts"]) <= 3
    serialized_operator_context = json.dumps(
        {
            "connector_status": context_payload["connector_status"],
            "connector_refresh_runs": context_payload["connector_refresh_runs"],
            "active_action_objects": context_payload["active_action_objects"],
            "expert_rule_summaries": context_payload["expert_rule_summaries"],
        },
        ensure_ascii=False,
    )
    for forbidden_term in (
        "target_site",
        "mapping_review",
        "content_url_review_contract",
        "confirm_final_canonical_url",
        "Strona z GSC: publiczny URL w polu",
        "vendor_read",
        "Read-only",
        "read-only",
        "review-only",
        "ActionObject",
    ):
        assert forbidden_term not in serialized_operator_context


def test_daily_runtime_reuses_preloaded_daily_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    connector = ConnectorStatus(
        id="google_merchant_center",
        label="Merchant Center",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="fresh"),
        capabilities=ConnectorCapability(read=True),
        health_check="configured",
    )
    action = ActionObject(
        id="act_review_merchant_feed_issues",
        title="Przejrzyj problemy pliku produktowego",
        domain=OpportunityDomain.merchant,
        connector="google_merchant_center",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_merchant"],
        human_diagnosis="Merchant wymaga sprawdzenia.",
        recommended_reason="Przygotuj sprawdzenie.",
        payload={},
        validation_status="not_validated",
        created_by="wilq",
    )
    refresh_run = ConnectorRefreshRun(
        id="refresh_merchant",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_merchant"],
        summary="Merchant read.",
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        items=[],
    )
    metric_fact = MetricFact(
        name="issue_product_count",
        value=3,
        period="connector_refresh",
        source_connector="google_merchant_center",
        evidence_id="ev_merchant",
    )
    facts_by_connector = {"google_merchant_center": [metric_fact]}

    class FakeMetricStore:
        def list_latest_metric_facts_by_connector_limits(
            self,
            limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["metric_fact_limits"] = limits
            return facts_by_connector

    monkeypatch.setattr(daily_runtime, "metric_store", lambda: FakeMetricStore())
    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj Merchant.",
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[connector],
        codex_operator_status={},
    )
    brief = MarketingBrief(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections=[],
    )
    seen: dict[str, object] = {}

    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [connector])
    monkeypatch.setattr(daily_runtime, "list_actions_cached", lambda: [action])
    monkeypatch.setattr(daily_runtime, "list_connector_refresh_runs", lambda: [refresh_run])
    monkeypatch.setattr(
        daily_runtime,
        "build_tactical_queue",
        lambda facts_by_connector=None: tactical_queue,
    )

    def command_builder(
        connectors: list[ConnectorStatus] | None = None,
        tactical_queue: TacticalQueueResponse | None = None,
        actions: list[ActionObject] | None = None,
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
        refresh_runs: list[ConnectorRefreshRun] | None = None,
    ) -> CommandCenterResponse:
        seen["command_connectors"] = connectors
        seen["command_tactical_queue"] = tactical_queue
        seen["command_actions"] = actions
        seen["command_facts_by_connector"] = facts_by_connector
        seen["command_refresh_runs"] = refresh_runs
        return command

    def brief_builder(
        connectors: list[ConnectorStatus] | None = None,
        refresh_runs: list[ConnectorRefreshRun] | None = None,
        actions: list[ActionObject] | None = None,
        command_center: CommandCenterResponse | None = None,
        metric_facts_by_connector: dict[str, list[MetricFact]] | None = None,
    ) -> MarketingBrief:
        seen["brief_connectors"] = connectors
        seen["brief_refresh_runs"] = refresh_runs
        seen["brief_actions"] = actions
        seen["brief_command_center"] = command_center
        seen["brief_metric_facts_by_connector"] = metric_facts_by_connector
        return brief

    monkeypatch.setattr(daily_runtime, "build_command_center_response", command_builder)
    monkeypatch.setattr(daily_runtime, "build_marketing_brief", brief_builder)

    runtime = daily_runtime.build_daily_runtime()

    assert runtime.connectors == [connector]
    assert runtime.actions == [action]
    assert runtime.refresh_runs == [refresh_run]
    assert runtime.core_actions == [action]
    assert runtime.command_center == command
    assert runtime.marketing_brief == brief
    assert seen["command_connectors"] == [connector]
    assert seen["command_tactical_queue"] == tactical_queue
    assert seen["command_actions"] == [action]
    assert seen["command_facts_by_connector"] == facts_by_connector
    assert seen["command_refresh_runs"] == [refresh_run]
    assert seen["brief_connectors"] == [connector]
    assert seen["brief_refresh_runs"] == [refresh_run]
    assert seen["brief_actions"] == [action]
    assert seen["brief_command_center"] == command
    assert seen["brief_metric_facts_by_connector"] == facts_by_connector


def test_daily_command_center_does_not_build_marketing_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj Centrum pracy.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    base = daily_runtime.DailyRuntimeBase(
        connectors=[],
        actions=[],
        refresh_runs=[],
        tactical_queue=TacticalQueueResponse(
            strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
            items=[],
        ),
    )

    monkeypatch.setattr(daily_runtime, "build_daily_runtime_base", lambda use_cache=True: base)

    def build_command_center_response(
        connectors=None,
        tactical_queue=None,
        actions=None,
        facts_by_connector=None,
        refresh_runs=None,
    ) -> CommandCenterResponse:
        return command

    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        build_command_center_response,
    )

    def fail_marketing_brief(*args: object, **kwargs: object) -> MarketingBrief:
        raise AssertionError("Command Center endpoint must not build Marketing Brief")

    monkeypatch.setattr(daily_runtime, "build_marketing_brief", fail_marketing_brief)

    assert daily_runtime.build_daily_command_center(use_cache=False) == command


def test_command_center_uses_preloaded_refresh_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import command_center

    connector = ConnectorStatus(
        id="google_ads",
        label="Google Ads",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="fresh"),
        capabilities=ConnectorCapability(read=True),
        health_check="configured",
    )
    refresh_run = ConnectorRefreshRun(
        id="refresh_google_ads_live",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_google_ads_live"],
        vendor_data_collected=True,
        metric_summary={"row_count": 1},
        summary="Google Ads live read.",
    )
    metric_fact = MetricFact(
        name="clicks",
        value=4,
        period="connector_refresh",
        source_connector="google_ads",
        evidence_id="ev_refresh_google_ads_live",
    )

    class FailingLocalState:
        def list_connector_refresh_runs(self, connector_id: str | None = None) -> list[object]:
            raise AssertionError("Command Center must use preloaded refresh runs")

    monkeypatch.setattr(command_center, "local_state_store", lambda: FailingLocalState())

    response = command_center.build_command_center_response(
        connectors=[connector],
        tactical_queue=TacticalQueueResponse(
            strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
            items=[],
        ),
        actions=[],
        facts_by_connector={"google_ads": [metric_fact]},
        refresh_runs=[refresh_run],
    )

    ads_item = next(item for item in response.operator_brief if item.id == "daily_ads_status")
    assert ads_item.status == "ready"
    assert "ev_refresh_google_ads_live" in ads_item.evidence_ids


def test_command_center_brief_uses_lightweight_daily_item_builders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import command_center
    from wilq.briefing import tactical_queue as tactical_queue_module

    action = ActionObject(
        id="act_prepare_ads_campaign_review_queue",
        title="Przygotuj kolejkę przeglądu kampanii Google Ads",
        domain=OpportunityDomain.google_ads,
        connector="google_ads",
        mode=ActionMode.prepare,
        risk=ActionRisk.medium,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_ads"],
        human_diagnosis="Ads wymaga sprawdzenia.",
        recommended_reason="Przygotuj sprawdzenie.",
        payload={},
        validation_status="not_validated",
        created_by="wilq",
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        items=[],
    )
    seen: dict[str, object] = {}

    def ads_item_builder(
        facts: list[object],
        actions: list[ActionObject],
        **_kwargs: object,
    ) -> CommandCenterBriefItem:
        seen["ads_metric_facts"] = facts
        seen["actions"] = actions
        return CommandCenterBriefItem(
            id="daily_ads_status",
            title="Ads: aktualne metryki kampanii dostępne",
            route="/ads-doctor",
            status="ready",
            priority=30,
            summary="Google Ads ma aktualne metryki źródłowe.",
            next_step="Otwórz /ads-doctor.",
            source_connectors=["google_ads"],
            evidence_ids=["ev_ads"],
            action_ids=[action.id],
        )

    def merchant_item_builder(
        tactical_items: list[object],
        actions: list[ActionObject],
        metric_facts: list[object],
        **_kwargs: object,
    ) -> CommandCenterBriefItem:
        seen["merchant_tactical_items"] = tactical_items
        seen["merchant_actions"] = actions
        seen["merchant_metric_facts"] = metric_facts
        return CommandCenterBriefItem(
            id="daily_merchant_feed",
            title="Merchant",
            route="/merchant",
            status="ready",
            priority=10,
            summary="Merchant.",
            next_step="Otwórz /merchant.",
        )

    def content_item_builder(
        queue: TacticalQueueResponse,
        ahrefs_facts: list[object],
        actions: list[ActionObject],
        **_kwargs: object,
    ) -> CommandCenterBriefItem:
        seen["content_tactical_queue"] = queue
        seen["content_ahrefs_facts"] = ahrefs_facts
        seen["content_actions"] = actions
        return CommandCenterBriefItem(
            id="daily_content_queue",
            title="Content",
            route="/content-workflow",
            status="ready",
            priority=12,
            summary="Content.",
            next_step="Otwórz /content-workflow.",
        )

    def ga4_item_builder(
        tactical_items: list[object],
        actions: list[ActionObject],
        metric_facts: list[object],
    ) -> CommandCenterBriefItem:
        seen["ga4_tactical_items"] = tactical_items
        seen["ga4_actions"] = actions
        seen["ga4_metric_facts"] = metric_facts
        return CommandCenterBriefItem(
            id="daily_ga4_landing_quality",
            title="GA4",
            route="/ga4",
            status="blocked",
            priority=14,
            summary="GA4.",
            next_step="Otwórz /ga4.",
        )

    monkeypatch.setattr(command_center, "_ads_item_from_facts", ads_item_builder)
    monkeypatch.setattr(
        command_center,
        "_ads_business_context_item_from_facts",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(command_center, "_merchant_item_from_tactical", merchant_item_builder)
    monkeypatch.setattr(command_center, "_content_item_from_tactical", content_item_builder)
    monkeypatch.setattr(command_center, "_ga4_item_from_tactical", ga4_item_builder)

    class EmptyMetricStore:
        def list_metric_facts(self, *_args: object) -> list[object]:
            raise AssertionError("Command Center must use batched metric fact reads")

        def list_metric_facts_by_connector(
            self,
            *_args: object,
            **_kwargs: object,
        ) -> dict[str, list[object]]:
            raise AssertionError("Command Center must use latest facts without delta windows")

        def list_latest_metric_facts_by_connector(
            self,
            *_args: object,
            **_kwargs: object,
        ) -> object:
            raise AssertionError("Command Center must use connector-specific limits")

        def list_latest_metric_facts_by_connector_limits(
            self,
            connector_limits: dict[str, int],
        ) -> dict[str, list[object]]:
            seen["metric_connector_limits"] = connector_limits
            return {connector_id: [] for connector_id in connector_limits}

    monkeypatch.setattr(command_center, "metric_store", lambda: EmptyMetricStore())
    monkeypatch.setattr(command_center, "get_connector_status", lambda _connector_id: None)

    command_center.build_command_center_brief(
        tactical_queue=tactical_queue,
        actions=[action],
    )

    assert seen["actions"] == [action]
    assert seen["ads_metric_facts"] == []
    assert seen["merchant_tactical_items"] == tactical_queue.items
    assert seen["merchant_actions"] == [action]
    assert seen["merchant_metric_facts"] == []
    assert seen["content_tactical_queue"] == tactical_queue
    assert seen["content_ahrefs_facts"] == []
    assert seen["content_actions"] == [action]
    assert seen["ga4_tactical_items"] == tactical_queue.items
    assert seen["ga4_actions"] == [action]
    assert seen["ga4_metric_facts"] == []
    assert seen["metric_connector_limits"] == {
        "google_ads": command_center.GOOGLE_ADS_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "google_merchant_center": command_center.MERCHANT_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "google_analytics_4": command_center.GA4_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "ahrefs": command_center.AHREFS_COMMAND_CENTER_METRIC_FACT_LIMIT,
        "localo": 120,
        "google_search_console": tactical_queue_module.GSC_QUERY_PAGE_FACT_LIMIT,
        "wordpress_ekologus": tactical_queue_module.WORDPRESS_INVENTORY_FACT_LIMIT,
        "wordpress_sklep": tactical_queue_module.WORDPRESS_INVENTORY_FACT_LIMIT,
    }


def test_codex_context_pack_full_context_keeps_diagnostic_surfaces(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "context_pack_full.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "context_pack_full.duckdb"))
    ads_response = client.get("/api/ads/diagnostics")
    assert ads_response.status_code == 200
    ads_diagnostics = ads_response.json()
    merchant_response = client.get("/api/merchant/diagnostics")
    assert merchant_response.status_code == 200
    merchant_diagnostics = merchant_response.json()

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-daily-command", "full_context": True},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()

    assert "context_scope" not in context_payload
    assert context_payload["tactical_queue"]["language"] == "pl-PL"
    assert "items" in context_payload["tactical_queue"]
    assert context_payload["ads_diagnostics"]["language"] == "pl-PL"
    assert (
        context_payload["ads_diagnostics"]["live_data_available"]
        == ads_diagnostics["live_data_available"]
    )
    assert context_payload["ads_diagnostics"]["evidence_ids"] == ads_diagnostics["evidence_ids"]
    assert context_payload["ads_diagnostics"]["action_ids"] == ads_diagnostics["action_ids"]
    assert context_payload["merchant_diagnostics"]["language"] == "pl-PL"
    assert (
        context_payload["merchant_diagnostics"]["live_data_available"]
        == merchant_diagnostics["live_data_available"]
    )
    assert (
        context_payload["merchant_diagnostics"]["evidence_ids"]
        == merchant_diagnostics["evidence_ids"]
    )
    assert (
        context_payload["merchant_diagnostics"]["action_ids"] == merchant_diagnostics["action_ids"]
    )


def test_codex_context_pack_scopes_ads_doctor_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    ads_response = client.get("/api/ads/diagnostics")
    assert ads_response.status_code == 200
    ads_diagnostics = ads_response.json()

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )

    assert response.status_code == 200
    data = response.json()
    ads_context = data["ads_diagnostics"]
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-ads-doctor"
    referenced_knowledge_card_ids = {
        card_id
        for decision in ads_context["decision_queue"]
        for card_id in decision.get("knowledge_card_ids", [])
    }
    referenced_expert_rule_ids = {
        rule_id
        for decision in ads_context["decision_queue"]
        for rule_id in decision.get("expert_rule_ids", [])
    }
    context_knowledge_card_ids = {card["id"] for card in data["knowledge_card_summaries"]}
    context_expert_rule_ids = {rule["id"] for rule in data["expert_rule_summaries"]}
    assert referenced_knowledge_card_ids
    assert referenced_expert_rule_ids
    assert referenced_knowledge_card_ids.issubset(context_knowledge_card_ids)
    assert referenced_expert_rule_ids.issubset(context_expert_rule_ids)
    assert "ads_diagnostics" in data
    assert "content_diagnostics" not in data
    assert "command_center" not in data
    assert ads_context["evidence_ids"] == ads_diagnostics["evidence_ids"]
    assert ads_context["action_ids"] == ads_diagnostics["action_ids"]
    assert ads_context["context_pack_compaction"]["metric_facts_removed"] is True
    assert ads_context["context_pack_compaction"]["sections_omitted"] is True
    assert ads_context["context_pack_compaction"]["sections_total"] >= 0
    assert ads_context["context_pack_compaction"]["decision_row_payloads_omitted"] is True
    assert ads_context["context_pack_compaction"]["empty_decision_row_lists_omitted"] is True
    assert ads_context["context_pack_compaction"]["full_endpoint"] == "/api/ads/diagnostics"
    assert "sections" not in ads_context
    triage_contract = ads_context["campaign_triage_read_contract"]
    assert triage_contract["status"] == "ready"
    assert triage_contract["triage_rows"]
    assert len(triage_contract["triage_rows"]) <= 4
    assert triage_contract["triage_rows"][0]["action_ids"] == [
        "act_prepare_ads_campaign_review_queue"
    ]
    assert "zmarnowany budżet" in triage_contract["blocked_claims"]
    assert ads_context["context_pack_compaction"]["campaign_triage_rows_included"] == len(
        triage_contract["triage_rows"]
    )
    optimizer_contract = ads_context["optimizer_readiness_contract"]
    assert optimizer_contract["status"] == "review_ready"
    assert optimizer_contract["mode"] == "review_only"
    assert optimizer_contract["apply_allowed"] is False
    assert "campaign_review_queue" in [item["id"] for item in optimizer_contract["readiness_items"]]
    assert "zapis zmian kampanii" in optimizer_contract["blocked_claims"]
    assert ads_context["change_impact_readiness_contract"]["status"] == "blocked"
    assert "wpływ zmian" in ads_context["change_impact_readiness_contract"]["blocked_claims"]
    if ads_context["change_history_read_contract"]["change_history_rows"]:
        assert ads_context["change_impact_readiness_contract"]["readiness_rows"]
        assert (
            "current_campaign_snapshot"
            not in ads_context["change_impact_readiness_contract"]["missing_read_contracts"]
        )
    custom_segment_candidate = ads_context["custom_segments_read_contract"]["candidates"][0]
    assert "source_quality" in custom_segment_candidate
    assert "rejection_reasons" not in custom_segment_candidate
    assert (
        ads_context["context_pack_compaction"][
            "custom_segment_candidate_search_term_rows_compacted"
        ]
        is True
    )
    assert custom_segment_candidate["search_term_rows_included"] == len(
        custom_segment_candidate["search_term_rows"]
    )
    assert custom_segment_candidate["search_term_rows_total"] >= len(
        custom_segment_candidate["search_term_rows"]
    )
    for row in custom_segment_candidate["search_term_rows"]:
        assert set(row) == {
            "search_term",
            "clicks",
            "cost_micros",
            "conversions",
            "evidence_ids",
            "missing_metrics",
        }
    assert len(json.dumps(data, ensure_ascii=False).encode()) < 200_000
    target_interpretation = ads_context["business_context_read_contract"]["target_interpretation"]
    assert target_interpretation["interpretation_contract"] == (
        "ads_business_target_interpretation_v1"
    )
    strategy_readiness = ads_context["business_context_read_contract"][
        "strategy_review_readiness_contract"
    ]
    assert strategy_readiness["id"] == "ads_strategy_review_readiness_contract"
    assert strategy_readiness["apply_allowed"] is False
    assert "human_strategy_review" in strategy_readiness["required_validation"]
    assert "ocena opłacalności" in strategy_readiness["blocked_claims"]
    assert "[REDACTED]" not in json.dumps(target_interpretation, ensure_ascii=False)
    assert len(data["connector_refresh_runs"]) <= 3
    for action in data["active_action_objects"]:
        action_plan = action.get("action_plan") or {}
        for rows_key in (
            "campaign_candidates",
            "budget_preview_items",
            "recommendations",
            "terms",
            "source_terms",
            "preview_items",
            "keyword_match_context",
        ):
            rows = action_plan.get(rows_key)
            if isinstance(rows, list):
                if rows_key == "campaign_candidates" and action["id"] == (
                    "act_prepare_ads_campaign_review_queue"
                ):
                    assert 0 < len(rows) <= 3
                    assert action_plan[f"{rows_key}_included"] == len(rows)
                elif rows_key == "preview_items" and action["id"] == (
                    "act_prepare_custom_segments_from_search_terms"
                ):
                    assert len(rows) == 1
                    assert "safety_contract" not in rows[0]["safety_review"]
                    assert rows[0]["safety_review"]["apply_status_label"] == (
                        "zablokowane do sprawdzenia"
                    )
                    assert rows[0]["safety_review"]["required_check_labels"]
                    assert action_plan[f"{rows_key}_included"] == 1
                else:
                    assert rows == []
                    assert action_plan[f"{rows_key}_included"] == 0
                assert action_plan[f"{rows_key}_total"] >= 0
    serialized_actions = json.dumps(data["active_action_objects"], ensure_ascii=False)
    assert "dimension_value_labels" not in serialized_actions
    assert "wartość wymiaru do sprawdzenia" not in serialized_actions
    assert "ENABLED" not in serialized_actions
    assert "PERFORMANCE_MAX" not in serialized_actions
    actions_by_id = {action["id"]: action for action in data["active_action_objects"]}
    assert "act_review_demand_gen_readiness" not in actions_by_id
    campaign_review_action = actions_by_id["act_prepare_ads_campaign_review_queue"]
    campaign_candidate = campaign_review_action["action_plan"]["campaign_candidates"][0]
    full_action_response = client.get("/api/actions/act_prepare_ads_campaign_review_queue")
    assert full_action_response.status_code == 200
    full_campaign_candidate = full_action_response.json()["payload"]["campaign_candidates"][0]
    assert campaign_candidate["campaign_name"] == full_campaign_candidate["campaign_name"]
    assert campaign_candidate["review_priority"] == full_campaign_candidate["review_priority"]
    assert campaign_candidate["review_score"] == full_campaign_candidate["review_score"]
    assert "Kolejność oceny kampanii" in campaign_candidate["review_reason"]
    assert campaign_candidate["review_reason"] == full_campaign_candidate["review_reason"]
    assert (
        campaign_candidate["human_review_gate_labels"]
        == (full_campaign_candidate["human_review_gate_labels"])
    )
    assert (
        campaign_candidate["target_context"]["target_status_label"]
        == (full_campaign_candidate["target_context"]["target_status_label"])
    )
    assert "target_cpa_micros" not in campaign_candidate["target_context"]
    assert "cost_per_conversion_micros" not in campaign_candidate["target_context"]
    assert "sprawdź cel kampanii" in campaign_candidate["human_review_gate_labels"]
    assert campaign_candidate["apply_status_label"] == "zablokowane do sprawdzenia"
    assert len(ads_context["search_terms_read_contract"]["search_term_rows"]) <= 8
    assert len(ads_context["search_term_ngram_read_contract"]["ngram_rows"]) <= 8
    assert len(ads_context["search_term_safety_read_contract"]["safety_rows"]) <= 8
    assert len(ads_context["keyword_match_context_read_contract"]["context_rows"]) <= 8
    assert len(ads_context["budget_pacing_read_contract"]["payload_preview"]) <= 4
    budget_preview = ads_context["budget_pacing_read_contract"]["payload_preview"][0]
    assert budget_preview["safety_review"]["safety_contract"] == ("campaign_budget_apply_safety_v1")
    assert budget_preview["safety_review"]["apply_allowed"] is False
    assert len(ads_context["recommendations_read_contract"]["payload_preview"]) <= 8
    assert (
        ads_context["context_pack_compaction"]["recommendation_row_payload_previews_omitted"]
        is True
    )
    for recommendation_row in ads_context["recommendations_read_contract"]["recommendation_rows"]:
        assert "payload_preview" not in recommendation_row
        assert recommendation_row["payload_preview_total"] >= 0
        assert recommendation_row["payload_preview_included"] == 0
    assert len(ads_context["negative_keywords_read_contract"]["payload_preview"]) <= 8
    assert (
        ads_context["context_pack_compaction"]["negative_keyword_candidate_context_rows_compacted"]
        is True
    )
    assert ads_context["context_pack_compaction"]["budget_payload_preview_included"] <= 4
    for candidate in ads_context["negative_keywords_read_contract"]["candidates"]:
        assert len(candidate["keyword_context_rows"]) <= 2
        assert candidate["keyword_context_rows_included"] == len(candidate["keyword_context_rows"])
        assert candidate["keyword_context_rows_total"] >= len(candidate["keyword_context_rows"])
        for row in candidate["keyword_context_rows"]:
            assert set(row) == {
                "keyword_text",
                "match_type",
                "criterion_status",
                "negative",
                "evidence_ids",
            }
    for decision in ads_context["decision_queue"]:
        assert "budget_apply_preview" not in decision
        assert len(decision.get("recommendation_apply_preview", [])) <= 4
        assert len(decision.get("search_term_safety_rows", [])) <= 4
        assert len(decision.get("keyword_match_context_rows", [])) <= 4
        assert len(decision.get("negative_keyword_payload_preview", [])) <= 4
        assert decision.get("omitted_empty_row_lists_count", 0) > 0
        for candidate in decision.get("negative_keyword_candidates", []):
            assert len(candidate["keyword_context_rows"]) <= 4
    assert ads_context["context_pack_compaction"]["keyword_match_context_rows_included"] <= 8
    assert ads_context["context_pack_compaction"]["search_term_safety_rows_included"] <= 8
    assert ads_context["context_pack_compaction"]["recommendation_apply_preview_included"] <= 8
    assert '"metric_facts":' not in json.dumps(ads_context)
    assert "safety_metric_facts" not in json.dumps(ads_context)
    ngram_context_action = next(
        action
        for action in data["active_action_objects"]
        if action["id"] == SEARCH_TERM_NGRAM_ACTION_ID
    )
    assert ngram_context_action["action_plan"]["search_term_theme_preview_items_included"] <= 4
    ngram_context_text = json.dumps(ngram_context_action, ensure_ascii=False)
    assert "N-gram review" not in ngram_context_text
    assert "search-term evidence" not in ngram_context_text
    assert "negative keyword queue" not in ngram_context_text
    assert "Przegląd tematów zapytań" in ngram_context_text
    assert "kolejką sprawdzenia wykluczeń" in ngram_context_text


def test_codex_context_pack_scopes_custom_segments_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-custom-segments"},
    )

    assert response.status_code == 200
    data = response.json()
    ads_context = data["ads_diagnostics"]
    assert data["context_scope"]["mode"] == "skill"
    assert data["context_scope"]["skill"] == "wilq-custom-segments"
    assert "content_diagnostics" not in data
    assert "command_center" not in data
    assert [action["id"] for action in data["active_action_objects"]] == [
        "act_prepare_custom_segments_from_search_terms"
    ]
    assert data["top_opportunities"] == []
    assert ads_context["action_ids"] == ["act_prepare_custom_segments_from_search_terms"]
    assert [decision["id"] for decision in ads_context["decision_queue"]] == [
        "ads_prepare_custom_segments_from_search_terms"
    ]
    assert ads_context["custom_segments_read_contract"]["payload_preview"]
    context_safety_review = ads_context["custom_segments_read_contract"]["payload_preview"][0][
        "safety_review"
    ]
    assert context_safety_review["safety_contract"] == "custom_segment_apply_safety_v1"
    assert context_safety_review["status"] == "blocked"
    assert context_safety_review["apply_allowed"] is False
    assert context_safety_review["api_mutation_ready"] is False
    assert context_safety_review["audit_required"] is True
    assert "forecast_or_audience_size" in context_safety_review["missing_requirements"]
    assert "google_ads_mutation_audit" in context_safety_review["missing_requirements"]
    action_safety_review = data["active_action_objects"][0]["action_plan"]["preview_items"][0][
        "safety_review"
    ]
    assert "safety_contract" not in action_safety_review
    assert action_safety_review["apply_status_label"] == "zablokowane do sprawdzenia"
    assert ads_context["custom_segments_read_contract"]["audience_forecast_read_contract"][
        "forecast_rows"
    ]
    assert (
        "custom_segment_change_preview"
        not in ads_context["custom_segments_read_contract"]["missing_read_contracts"]
    )
    assert "recommendations_read_contract" not in ads_context
    assert "negative_keywords_read_contract" not in ads_context
    assert "budget_pacing_read_contract" not in ads_context
    assert "campaign_read_contract" not in ads_context
    assert "search_terms_read_contract" in ads_context
    assert ads_context["context_pack_compaction"]["purpose"] == "custom_segments_context"
    assert ads_context["context_pack_compaction"]["custom_segment_payload_preview_included"] <= 8
    for action in data["active_action_objects"]:
        assert action["metrics_included"] <= 3
        assert action["metrics_total"] >= action["metrics_included"]
        action_plan = action.get("action_plan") or {}
        rows = action_plan.get("preview_items")
        if isinstance(rows, list):
            if action["id"] == "act_prepare_custom_segments_from_search_terms":
                assert len(rows) == 1
                assert "safety_contract" not in rows[0]["safety_review"]
                assert rows[0]["safety_review"]["apply_status_label"] == (
                    "zablokowane do sprawdzenia"
                )
                assert action_plan["preview_items_included"] == 1
            else:
                assert rows == []
                assert action_plan["preview_items_included"] == 0
            assert action_plan["preview_items_total"] >= 0
