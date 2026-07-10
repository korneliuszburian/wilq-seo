"""Command Center and marketing brief API contract tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from tests._contract_support.env import clear_ahrefs_env, clear_google_ads_env
from wilq.briefing.ahrefs_diagnostics import _missing_authority_summary
from wilq.briefing.ga4_diagnostics import _ga4_freshness_assessment
from wilq.briefing.marketing_brief import _blocker_summary, build_marketing_brief
from wilq.briefing.merchant_diagnostics import _merchant_freshness_assessment
from wilq.connectors.vendor import VendorReadResult
from wilq.schemas import (
    ActionMode,
    ActionObject,
    ActionRisk,
    ActionStatus,
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


def test_command_center_returns_valid_shape() -> None:
    response = client.get("/api/dashboard/command-center")
    assert response.status_code == 200
    data = response.json()
    assert data["strict_instruction"]
    assert data["connector_summary"]["total"] >= 12
    assert data["sections"] == {}
    assert data["demo_script"] == []
    assert data["action_plan"]
    assert data["action_plan"][0]["evidence_ids"]
    nested_evidence_ids = {
        evidence_id
        for decision in data["daily_decisions"]
        for evidence_id in decision["evidence_ids"]
    }
    nested_action_ids = {
        action_id for decision in data["daily_decisions"] for action_id in decision["action_ids"]
    }
    assert data["evidence_ids"]
    assert data["action_ids"]
    assert set(data["evidence_ids"]) == nested_evidence_ids
    assert set(data["action_ids"]) == nested_action_ids
    assert data["source_connectors"]
    assert data["source_connector_labels"]
    assert data["evidence_summary"]
    assert data["action_summary"]
    assert data["work_orders"]
    assert data["work_orders"][0]["decision_id"]
    assert data["work_orders"][0]["owner_role"]
    assert data["work_orders"][0]["next_safe_step"]
    assert data["work_orders"][0]["close_condition"]
    assert "ActionObject" not in data["work_orders"][0]["summary"]


def test_command_center_work_orders_are_filled_from_daily_decisions() -> None:
    decision = DailyDecision(
        id="decision_review_merchant_feed_issues",
        title="Przejrzyj kolejkę problemów Merchant Center",
        domain="merchant",
        freshness=FreshnessState(state="fresh"),
        freshness_label="świeże dane",
        decision_state="ready",
        decision_state_label="gotowe",
        route="/merchant",
        route_label="Merchant",
        cta_label="Otwórz Merchant",
        status="ready",
        priority=1,
        priority_label="najpierw",
        co_widzimy="Merchant ma potwierdzone problemy pliku produktowego.",
        dlaczego_to_ma_znaczenie="To może blokować widoczność produktów.",
        bezpieczny_next_step="Otwórz Merchant i sprawdź akcję review.",
        why_it_matters="To może blokować widoczność produktów.",
        operator_action="Otwórz Merchant i sprawdź akcję review.",
        source_connectors=["google_merchant_center"],
        source_connector_labels=["Merchant Center"],
        evidence_ids=["ev_refresh_merchant"],
        evidence_summary="1 dowód źródłowy",
        action_ids=["act_review_merchant_feed_issues"],
        action_summary="1 akcja do sprawdzenia",
        blocked_claims=["odzyskany przychód"],
        blocked_claim_labels=["odzyskany przychód"],
        risk=ActionRisk.medium,
    )
    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj Merchant.",
        daily_decisions=[decision],
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )

    assert len(command.work_orders) == 1
    work_order = command.work_orders[0]
    assert work_order.id == "work_order_review_merchant_feed_issues"
    assert work_order.decision_id == decision.id
    assert work_order.status == "review_required"
    assert work_order.status_label == "do sprawdzenia"
    assert work_order.owner_role == "product_feed"
    assert work_order.next_safe_step == decision.bezpieczny_next_step
    assert work_order.close_condition.startswith("Zamknięte po review")
    assert work_order.evidence_ids == ["ev_refresh_merchant"]
    assert work_order.blocked_claim_labels == ["odzyskany przychód"]


def test_command_center_endpoint_uses_daily_runtime_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj decyzje.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    calls = {"command_center": 0}

    def fake_command_center() -> CommandCenterResponse:
        calls["command_center"] += 1
        return command

    monkeypatch.setattr(
        "apps.api.wilq_api.routers.diagnostics.build_daily_command_center",
        fake_command_center,
    )

    response = client.get("/api/dashboard/command-center")

    assert response.status_code == 200
    assert response.json()["primary_next_step"] == "Przejrzyj decyzje."
    assert calls == {"command_center": 1}


def test_daily_command_center_does_not_build_full_action_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    command = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        primary_next_step="Przejrzyj decyzje.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    tactical_queue = TacticalQueueResponse(
        strict_instruction="WILQ pokazuje tylko metryki z danych źródłowych.",
        items=[],
    )

    def fail_list_actions() -> list[ActionObject]:
        raise AssertionError("Command Center first-screen path must not build full actions")

    shared_facts: dict[str, list[MetricFact]] = {"google_merchant_center": []}
    seen: dict[str, Any] = {}

    class FakeMetricStore:
        def list_latest_metric_facts_by_connector_limits(
            self,
            limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["metric_limits"] = limits
            return shared_facts

    def fake_tactical_queue(
        use_cache: bool = True,
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
    ) -> TacticalQueueResponse:
        seen["tactical_facts"] = facts_by_connector
        return tactical_queue

    def fake_command_center_response(
        connectors: list[ConnectorStatus] | None = None,
        tactical_queue: TacticalQueueResponse | None = None,
        actions: list[ActionObject] | None = None,
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
        refresh_runs: list[ConnectorRefreshRun] | None = None,
    ) -> CommandCenterResponse:
        seen["response_facts"] = facts_by_connector
        seen["response_refresh_runs"] = refresh_runs
        return command

    monkeypatch.setattr(daily_runtime, "list_actions", fail_list_actions)
    monkeypatch.setattr(daily_runtime, "list_connector_statuses", lambda: [])
    monkeypatch.setattr(daily_runtime, "metric_store", lambda: FakeMetricStore())
    monkeypatch.setattr(daily_runtime, "build_tactical_queue", fake_tactical_queue)
    monkeypatch.setattr(
        daily_runtime,
        "build_command_center_response",
        fake_command_center_response,
    )

    assert daily_runtime.build_daily_command_center(use_cache=False) == command
    assert seen["tactical_facts"] is shared_facts
    assert seen["response_facts"] is shared_facts
    assert "google_merchant_center" in seen["metric_limits"]


def test_marketing_brief_endpoint_uses_daily_runtime_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = MarketingBrief(
        strict_instruction="Brief z testowego DailyRuntime.",
        connector_summary=ConnectorSummary(total=0, configured=0, missing_credentials=0),
        sections=[],
        evidence_ids=["ev_test_daily_runtime_brief"],
    )
    calls = {"marketing_brief": 0}

    def fake_marketing_brief() -> MarketingBrief:
        calls["marketing_brief"] += 1
        return brief

    monkeypatch.setattr(
        "apps.api.wilq_api.routers.diagnostics.build_daily_marketing_brief",
        fake_marketing_brief,
    )

    response = client.get("/api/marketing/brief")

    assert response.status_code == 200
    assert response.json()["strict_instruction"] == "Brief z testowego DailyRuntime."
    assert response.json()["evidence_ids"] == ["ev_test_daily_runtime_brief"]
    assert calls == {"marketing_brief": 1}


def test_daily_runtime_cache_seconds_default_and_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import daily_runtime

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", raising=False)
    assert daily_runtime._cache_seconds() == 30.0

    monkeypatch.setenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", "7.5")
    assert daily_runtime._cache_seconds() == 7.5

    monkeypatch.setenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", "-1")
    assert daily_runtime._cache_seconds() == 0.0

    monkeypatch.setenv("WILQ_DAILY_RUNTIME_CACHE_SECONDS", "invalid")
    assert daily_runtime._cache_seconds() == 30.0


def test_tactical_queue_uses_short_ttl_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import tactical_queue

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("WILQ_TACTICAL_QUEUE_CACHE_SECONDS", "30")
    tactical_queue.clear_tactical_queue_cache()
    calls = {"build": 0}

    def fake_build(
        facts_by_connector: dict[str, list[MetricFact]] | None = None,
    ) -> TacticalQueueResponse:
        assert facts_by_connector is None
        calls["build"] += 1
        return TacticalQueueResponse(
            strict_instruction=f"cached tactical queue {calls['build']}",
            items=[],
            evidence_ids=[],
            action_ids=[],
        )

    monkeypatch.setattr(tactical_queue, "_build_tactical_queue", fake_build)

    first = tactical_queue.build_tactical_queue()
    second = tactical_queue.build_tactical_queue()
    tactical_queue.clear_tactical_queue_cache()
    third = tactical_queue.build_tactical_queue()

    assert first.strict_instruction == "cached tactical queue 1"
    assert second.strict_instruction == "cached tactical queue 1"
    assert third.strict_instruction == "cached tactical queue 2"
    assert calls == {"build": 2}
    tactical_queue.clear_tactical_queue_cache()


def test_tactical_queue_uses_latest_metric_fact_batch_for_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import tactical_queue

    fact = MetricFact(
        name="clicks",
        value=4,
        period="last_28_days",
        source_connector="google_search_console",
        evidence_id="ev_tactical_latest",
    )
    seen: dict[str, Any] = {}

    class FastMetricStore:
        def list_metric_facts_by_connector(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("Tactical queue must use latest facts without delta windows")

        def list_latest_metric_facts_by_connector(
            self,
            connector_ids: list[str],
            limit_per_connector: int = 100,
        ) -> dict[str, list[MetricFact]]:
            seen["connector_ids"] = connector_ids
            seen["limit_per_connector"] = limit_per_connector
            return {connector_id: [] for connector_id in connector_ids} | {
                "google_search_console": [fact]
            }

        def list_latest_metric_facts_by_connector_limits(
            self,
            connector_limits: dict[str, int],
        ) -> dict[str, list[MetricFact]]:
            seen["connector_limits"] = connector_limits
            return {connector_id: [] for connector_id in connector_limits} | {
                "google_search_console": [fact]
            }

    monkeypatch.setattr(tactical_queue, "metric_store", lambda: FastMetricStore())

    facts = tactical_queue._tactical_metric_facts()

    assert facts == [fact]
    assert "google_search_console" in seen["connector_limits"]
    assert (
        seen["connector_limits"]["wordpress_ekologus"]
        == tactical_queue.WORDPRESS_INVENTORY_FACT_LIMIT
    )


def test_command_center_reuses_batched_localo_facts_before_evidence_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from wilq.briefing import command_center

    run = ConnectorRefreshRun(
        id="refresh_localo_latest",
        connector_id="localo",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        evidence_ids=["ev_refresh_localo_latest"],
        metric_summary={},
        summary="Localo latest facts.",
    )
    fact = MetricFact(
        name="localo_active_place_count",
        value=4,
        period="connector_refresh",
        source_connector="localo",
        evidence_id="ev_refresh_localo_latest",
    )

    class FailingMetricStore:
        def list_metric_facts_by_evidence_ids(self, *_args: object) -> list[MetricFact]:
            raise AssertionError("Command Center must reuse batched Localo facts first")

    monkeypatch.setattr(command_center, "metric_store", lambda: FailingMetricStore())

    assert command_center._localo_metric_facts_for_run(run, [fact]) == [fact]


def test_marketing_brief_aggregates_metric_facts_and_blockers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "brief_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "brief_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))
    clear_google_ads_env(monkeypatch)
    clear_ahrefs_env(monkeypatch)
    monkeypatch.setenv("AHREFS_API_TOKEN", "ahrefs-token-test")

    monkeypatch.setattr(
        "wilq.connectors.refresh.refresh_ahrefs_domain_rating",
        lambda request: VendorReadResult(
            status=ConnectorRefreshStatus.completed,
            summary="Ahrefs domain rating completed through test adapter.",
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"domain_rating": 24.0, "ahrefs_rank": 6433882},
        ),
    )

    refresh_response = client.post(
        "/api/connectors/ahrefs/refresh",
        json={"mode": "vendor_read", "reason": "marketing brief contract test"},
    )
    assert refresh_response.status_code == 200

    response = client.get("/api/marketing/brief")

    assert response.status_code == 200
    brief = response.json()
    assert brief["language"] == "pl-PL"
    assert "metryki" in brief["strict_instruction"].lower()
    sections = {section["id"]: section for section in brief["sections"]}
    metric_items = sections["what_we_know"]["items"]
    assert any(item["source_connectors"] == ["ahrefs"] for item in metric_items)
    ahrefs_item = next(item for item in metric_items if item["source_connectors"] == ["ahrefs"])
    assert ahrefs_item["evidence_ids"] == refresh_response.json()["evidence_ids"][-1:]
    assert ahrefs_item["source_connector_labels"] == ["Ahrefs"]
    assert ahrefs_item["evidence_summary_label"] == "1 dowód źródłowy"
    assert (
        ahrefs_item["action_summary_label"] == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
    assert ahrefs_item["kind"] == "metric"
    assert ahrefs_item["kind_label"] == "fakt z danych"
    assert ahrefs_item["metric_facts"]
    blocker_items = sections["what_blocks_us"]["items"]
    assert any(item["source_connectors"] == ["google_ads"] for item in blocker_items)
    assert all(item["source_connectors"] != ["google_sheets"] for item in blocker_items)
    assert all(item["source_connectors"] != ["linkedin"] for item in blocker_items)
    assert all(item["source_connectors"] != ["facebook"] for item in blocker_items)
    assert all(item["source_connectors"] != ["openai_codex"] for item in blocker_items)
    assert all(
        item["kind"] in {"metric", "blocker", "action", "recommendation"}
        for section in sections.values()
        for item in section["items"]
    )
    for section in sections.values():
        for item in section["items"]:
            assert item["kind_label"]
            assert item["kind_label"] not in {
                "metric",
                "blocker",
                "action",
                "recommendation",
            }
            assert item["priority_label"]
            assert isinstance(item["source_connector_labels"], list)
            assert item["evidence_summary_label"]
            assert item["action_summary_label"]


def test_marketing_brief_does_not_turn_successful_reads_into_blockers() -> None:
    connectors = [
        ConnectorStatus(
            id=connector_id,
            label=label,
            status=ConnectorStatusValue.configured,
            configured=True,
            freshness=FreshnessState(state="fresh"),
            capabilities=ConnectorCapability(read=True),
            health_check="configured",
        )
        for connector_id, label in (
            ("google_search_console", "Google Search Console"),
            ("google_analytics_4", "GA4"),
            ("google_merchant_center", "Merchant Center"),
        )
    ]
    refresh_runs = [
        ConnectorRefreshRun(
            id=f"refresh_{connector.id}_success",
            connector_id=connector.id,
            mode=ConnectorRefreshMode.vendor_read,
            status=ConnectorRefreshStatus.completed,
            completed_at=datetime.now(UTC),
            evidence_ids=[f"ev_refresh_{connector.id}_success"],
            external_call_attempted=True,
            vendor_data_collected=True,
            metric_summary={"row_count": 10, "total_products": 10776},
            summary=f"{connector.label} read completed.",
        )
        for connector in connectors
    ]

    brief = build_marketing_brief(
        connectors=connectors,
        refresh_runs=refresh_runs,
        actions=[],
    )

    blockers = next(section for section in brief.sections if section.id == "what_blocks_us").items
    assert blockers == []
    assert brief.blocker_count == 0


def test_marketing_brief_makes_stale_daily_decisions_refresh_first() -> None:
    stale_decision = DailyDecision(
        id="decision_review_merchant_feed_issues",
        title="Przejrzyj kolejkę problemów Merchant Center",
        domain="merchant",
        freshness=FreshnessState(
            state="stale",
            notes="Świeżość źródeł decyzji: Merchant Center: dane wymagają odświeżenia.",
        ),
        freshness_label="dane wymagają odświeżenia",
        decision_state="stale",
        decision_state_label="do odświeżenia",
        route="/merchant",
        status="ready",
        priority=10,
        metric_tiles={"zgłoszenia": 1289},
        co_widzimy="Merchant Center ma zgłoszenia problemów pliku produktowego.",
        dlaczego_to_ma_znaczenie="WILQ widzi kolejkę problemów do sprawdzenia.",
        bezpieczny_next_step="Otwórz widok Merchant i sprawdź kolejkę problemów.",
        why_it_matters="WILQ widzi kolejkę problemów do sprawdzenia.",
        operator_action="Otwórz widok Merchant i sprawdź kolejkę problemów.",
        source_connectors=["google_merchant_center"],
        source_connector_labels=["Merchant Center"],
        evidence_ids=["ev_refresh_refresh_google_merchant_center_stale"],
        action_ids=["act_review_merchant_feed_issues"],
        blocked_claims=["ponowne zatwierdzenie produktu"],
        risk=ActionRisk.low,
    )
    command_center = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki i dowody.",
        primary_next_step="Najpierw odśwież Merchant.",
        daily_decisions=[stale_decision],
        connector_summary=ConnectorSummary(total=1, configured=1, missing_credentials=0),
        sections={},
        active_actions=[],
        connector_health=[],
        codex_operator_status={},
    )
    action = ActionObject(
        id="act_review_merchant_feed_issues",
        title="Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
        domain=OpportunityDomain.merchant,
        connector="google_merchant_center",
        mode=ActionMode.prepare,
        risk=ActionRisk.low,
        status=ActionStatus.needs_validation,
        evidence_ids=["ev_refresh_refresh_google_merchant_center_stale"],
        human_diagnosis="Merchant Center ma kolejkę do sprawdzenia.",
        recommended_reason="Otwórz widok Merchant i sprawdź kolejkę problemów.",
        payload={"action_type": "merchant_review"},
        validation_status="not_validated",
        created_by="test",
    )

    brief = build_marketing_brief(
        connectors=[],
        refresh_runs=[],
        actions=[action],
        command_center=command_center,
    )
    sections = {section.id: section for section in brief.sections}
    metric_item = sections["what_we_know"].items[0]
    blocker_item = sections["what_blocks_us"].items[0]
    action_item = sections["safe_next_actions"].items[0]
    recommendation_item = sections["recommended_focus"].items[0]

    assert metric_item.kind == "blocker"
    assert metric_item.risk == ActionRisk.medium
    assert metric_item.blocker_reason == "dane wymagają odświeżenia przed rekomendacją"
    assert "refresh-first" in metric_item.summary
    assert "nie aktualna rekomendacja operacyjna" in metric_item.summary
    assert metric_item.next_step.startswith("Najpierw odśwież dane źródłowe: Merchant Center")
    assert "Dopiero po świeżym odczycie" in metric_item.next_step

    assert blocker_item.id == "brief_blocker_decision_review_merchant_feed_issues"
    assert blocker_item.blocker_reason == "dane wymagają odświeżenia przed rekomendacją"
    assert "refresh-first" in blocker_item.summary
    assert blocker_item.action_ids == ["act_review_merchant_feed_issues"]

    assert action_item.kind == "blocker"
    assert action_item.title.startswith("Odśwież dane przed akcją:")
    assert action_item.blocker_reason == "dane wymagają odświeżenia przed rekomendacją"
    assert "refresh-first" in action_item.summary
    assert action_item.next_step.startswith("Najpierw odśwież dane źródłowe: Merchant Center")
    assert "Dopiero po świeżym odczycie" in action_item.next_step
    assert action_item.risk == ActionRisk.medium

    assert recommendation_item.title.startswith("Odśwież dane przed decyzją:")
    assert recommendation_item.blocker_reason == ("dane wymagają odświeżenia przed rekomendacją")
    assert "refresh-first" in recommendation_item.summary
    assert "Najpierw odśwież dane źródłowe" in recommendation_item.next_step
    assert brief.blocker_count == 1


def test_marketing_brief_names_only_stale_sources_in_refresh_first_copy() -> None:
    stale_decision = DailyDecision(
        id="decision_prepare_content_refresh_queue",
        title="Przejrzyj kolejkę SEO z GSC i WordPress",
        domain="content",
        freshness=FreshnessState(
            state="stale",
            notes=(
                "Świeżość źródeł decyzji: Ahrefs: dane wymagają odświeżenia, "
                "Google Search Console: świeże dane, WordPress ekologus.pl: świeże dane, "
                "WordPress sklep.ekologus.pl: dane wymagają odświeżenia."
            ),
        ),
        freshness_label="dane wymagają odświeżenia",
        decision_state="stale",
        decision_state_label="do odświeżenia",
        route="/content-workflow",
        status="ready",
        priority=11,
        co_widzimy="GSC i WordPress tworzą kolejkę SEO.",
        dlaczego_to_ma_znaczenie="Ahrefs ma kolejkę sprawdzenia luk SEO.",
        bezpieczny_next_step="Sprawdź overlap intencji.",
        why_it_matters="Ahrefs ma kolejkę sprawdzenia luk SEO.",
        operator_action="Sprawdź overlap intencji.",
        source_connectors=[
            "ahrefs",
            "google_search_console",
            "wordpress_ekologus",
            "wordpress_sklep",
        ],
        source_connector_labels=[
            "Ahrefs",
            "Google Search Console",
            "WordPress ekologus.pl",
            "WordPress sklep.ekologus.pl",
        ],
        evidence_ids=["ev_refresh_refresh_google_search_console_fresh"],
        action_ids=["act_prepare_content_refresh_queue"],
    )
    command_center = CommandCenterResponse(
        strict_instruction="WILQ pokazuje tylko metryki i dowody.",
        primary_next_step="Najpierw odśwież stale źródła.",
        daily_decisions=[stale_decision],
        connector_summary=ConnectorSummary(total=4, configured=4, missing_credentials=0),
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
    metric_item = next(section for section in brief.sections if section.id == "what_we_know").items[
        0
    ]

    assert "Ahrefs, WordPress sklep.ekologus.pl" in metric_item.summary
    assert "Google Search Console" not in metric_item.summary
    assert "WordPress ekologus.pl" not in metric_item.summary
    assert metric_item.next_step.startswith(
        "Najpierw odśwież dane źródłowe: Ahrefs, WordPress sklep.ekologus.pl."
    )


def test_blocked_refresh_summaries_use_operator_status_labels() -> None:
    blocked_run = ConnectorRefreshRun(
        id="refresh_blocked_operator_status",
        connector_id="google_merchant_center",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.blocked,
        completed_at=datetime.now(UTC),
        evidence_ids=[],
        external_call_attempted=True,
        vendor_data_collected=False,
        summary="Blocked test read.",
    )
    connector = ConnectorStatus(
        id="google_merchant_center",
        label="Merchant Center",
        status=ConnectorStatusValue.configured,
        configured=True,
        freshness=FreshnessState(state="fresh"),
        capabilities=ConnectorCapability(read=True),
        health_check="configured",
    )

    marketing_summary = _blocker_summary(connector, blocked_run, "testowy blocker")
    merchant_freshness = _merchant_freshness_assessment(blocked_run)
    ga4_freshness = _ga4_freshness_assessment(blocked_run, [])
    ahrefs_summary = _missing_authority_summary([], blocked_run)

    summaries = [
        marketing_summary,
        merchant_freshness.summary,
        ga4_freshness.summary,
        ahrefs_summary,
    ]
    assert summaries == [
        "Ostatni odczyt zakończył się statusem odczyt zablokowany. Powód: testowy blocker",
        "Ostatni odczyt Merchant nie zakończył się poprawnie. "
        "Status odczytu: status odczytu do sprawdzenia.",
        "Ostatni odczyt GA4 nie zakończył się pełnym pobraniem metryk. "
        "Status odczytu: odczyt zablokowany.",
        "Ostatni odczyt Ahrefs zakończył się statusem status odczytu do sprawdzenia.",
    ]
    for summary in summaries:
        assert "ConnectorRefreshStatus" not in summary
        assert "status.value" not in summary
        assert " completed" not in summary
        assert " blocked" not in summary


def test_marketing_brief_exposes_metric_backed_prepare_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/marketing/brief")
    assert response.status_code == 200
    brief = response.json()
    for connector_id in (
        "google_merchant_center",
        "google_analytics_4",
        "google_search_console",
    ):
        item = next(
            item
            for section in brief["sections"]
            if section["id"] == "what_we_know"
            for item in section["items"]
            if connector_id in item["source_connectors"]
        )
        assert item["evidence_ids"]
        assert item["summary"]
    action_items = {
        item["action_ids"][0]: item
        for section in brief["sections"]
        if section["id"] == "safe_next_actions"
        for item in section["items"]
        if item["action_ids"]
    }

    for action_id in (
        "act_review_merchant_feed_issues",
        "act_review_ga4_tracking_quality",
        "act_prepare_content_refresh_queue",
    ):
        assert action_id in brief["action_ids"]
        item = action_items[action_id]
        assert item["evidence_ids"]
        assert item["risk"] in {"low", "medium"}
        assert item["summary"]
        assert item["next_step"]
    assert "act_prepare_linkedin_social_drafts" not in brief["action_ids"]
    assert "act_prepare_facebook_social_drafts" not in brief["action_ids"]
    assert "act_prepare_linkedin_social_drafts" not in action_items
    assert "act_prepare_facebook_social_drafts" not in action_items
    serialized = json.dumps(brief)
    assert "feed/product issues" not in serialized


def test_marketing_tactical_queue_uses_dimensioned_metric_facts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/marketing/tactical-queue")

    assert response.status_code == 200
    queue = response.json()
    assert queue["language"] == "pl-PL"
    assert queue["items"]
    intents = {item["intent"] for item in queue["items"]}
    assert "content_refresh" in intents
    assert "landing_page_quality" in intents
    assert "merchant_feed_triage" in intents
    assert queue["evidence_ids"]
    assert queue["action_ids"]
    assert queue["compact_groups"]
    assert len(queue["compact_groups"]) <= len(queue["items"])
    gsc_groups = [
        group
        for group in queue["compact_groups"]
        if "google_search_console" in group["source_connectors"]
    ]
    assert gsc_groups
    assert any("powiązane zapytanie" in group["diagnosis"] for group in gsc_groups)
    assert all("Query:" not in group["diagnosis"] for group in gsc_groups)
    assert all("clicks=" not in group["diagnosis"] for group in gsc_groups)
    assert all("impressions=" not in group["diagnosis"] for group in gsc_groups)
    assert any("kliknięcia:" in group["diagnosis"] for group in gsc_groups)
    assert any("wyświetlenia:" in group["diagnosis"] for group in gsc_groups)
    assert all(group["evidence_ids"] for group in queue["compact_groups"])
    assert all(group["blocked_claims"] for group in queue["compact_groups"])
    assert all(group["priority_label"] for group in queue["compact_groups"])
    assert all(group["source_connector_labels"] for group in queue["compact_groups"])
    assert all(group["evidence_summary_label"] for group in queue["compact_groups"])
    assert all(group["action_summary_label"] for group in queue["compact_groups"])
    assert all(group["blocked_claim_labels"] for group in queue["compact_groups"])
    assert all(" / " not in group["meta"] for group in queue["compact_groups"])
    assert all("Obszar:" in group["meta"] for group in queue["compact_groups"])
    assert all("Zadanie:" in group["meta"] for group in queue["compact_groups"])
    assert all("Priorytet:" in group["meta"] for group in queue["compact_groups"])
    content_items = [item for item in queue["items"] if item["intent"] == "content_refresh"]
    assert any(item["dimensions"]["wordpress_match"] == "found" for item in content_items)
    assert all("clicks=" not in item["diagnosis"] for item in content_items)
    assert all("average_position=" not in item["diagnosis"] for item in content_items)
    assert any("kliknięcia:" in item["diagnosis"] for item in content_items)
    assert any(
        item["dimensions"]["wordpress_match_confidence"] == "exact_url" for item in content_items
    )
    assert any("wordpress_ekologus" in item["source_connectors"] for item in content_items)
    ga4_items = [item for item in queue["items"] if item["intent"] == "landing_page_quality"]
    assert any(item["dimensions"]["wordpress_match"] == "found" for item in ga4_items)
    assert all("wordpress_match_confidence" in item["dimensions"] for item in ga4_items)
    assert all("źródło ruchu:" in item["title"] for item in ga4_items)
    merchant_items = [item for item in queue["items"] if item["intent"] == "merchant_feed_triage"]
    assert any(item["dimensions"].get("issue_type") == "missing_image" for item in merchant_items)
    assert any(
        item["dimensions"].get("affected_attribute") == "image_link" for item in merchant_items
    )
    assert all(" / " not in item["title"] for item in merchant_items)
    ahrefs_items = [item for item in queue["items"] if item["source_connectors"] == ["ahrefs"]]
    assert ahrefs_items
    assert any(
        item["dimensions"].get("keyword") == "audyt środowiskowy"
        and item["dimensions"].get("gap_type") == "content_gap"
        for item in ahrefs_items
    )
    ahrefs_audit_item = next(
        item for item in ahrefs_items if item["dimensions"].get("keyword") == "audyt środowiskowy"
    )
    assert ahrefs_audit_item["dimensions"]["gsc_demand"] == "present"
    assert ahrefs_audit_item["dimensions"]["wordpress_inventory_match"] == "present"
    assert "audyt środowiskowy" in ahrefs_audit_item["dimensions"]["gsc_overlap_terms"]
    assert (
        "https://www.ekologus.pl/audyt-srodowiskowy/"
        in ahrefs_audit_item["dimensions"]["wordpress_overlap_urls"]
    )
    assert "GSC" in ahrefs_audit_item["next_step"]
    assert "WordPress" in ahrefs_audit_item["next_step"]
    assert (
        "Ahrefs wskazuje: luka treści dla tematu audyt środowiskowy."
        in (ahrefs_audit_item["diagnosis"])
    )
    assert "`content_gap`" not in ahrefs_audit_item["diagnosis"]
    assert "competitor_domain=" not in ahrefs_audit_item["diagnosis"]
    assert "source_url=" not in ahrefs_audit_item["diagnosis"]
    assert "referenced_public_url=" not in ahrefs_audit_item["diagnosis"]
    ahrefs_beczka_item = next(
        item for item in ahrefs_items if item["dimensions"].get("keyword") == "beczka"
    )
    assert ahrefs_beczka_item["dimensions"]["gsc_demand"] == "missing"
    assert ahrefs_beczka_item["dimensions"]["wordpress_inventory_match"] == "missing"
    assert ahrefs_beczka_item["dimensions"]["gsc_overlap_terms"] == ""
    assert ahrefs_beczka_item["dimensions"]["wordpress_overlap_urls"] == ""
    assert all(item["domain"] == "content" for item in ahrefs_items)
    assert all("wzrost ruchu" in item["blocked_claims"] for item in ahrefs_items)
    assert all(
        "plan treści bez sprawdzenia GSC i WordPress" in item["blocked_claims"]
        for item in ahrefs_items
    )
    assert all(
        "content brief without" not in " ".join(item["blocked_claims"]) for item in ahrefs_items
    )
    assert all(item["dimensions"].get("competitor_domain") != "cuk.pl" for item in ahrefs_items)
    for item in queue["items"]:
        assert item["domain_label"]
        assert "Content /" not in item["domain_label"]
        assert item["intent_label"]
        assert item["priority_label"]
        assert item["source_connector_labels"]
        assert item["evidence_summary_label"]
        assert item["action_summary_label"]
        assert item["dimension_labels"]
        assert item["dimension_value_labels"]
        assert set(item["dimensions"]) == set(item["dimension_value_labels"])
        assert item["blocked_claim_labels"]
        assert item["dimensions"]
        assert item["evidence_ids"]
        assert item["source_connectors"]
        assert item["metric_facts"]
        assert item["blocked_claims"]
        assert item["next_step"]
    content_wordpress_item = next(
        item
        for item in content_items
        if item["dimensions"].get("wordpress_match_confidence") == "exact_url"
    )
    assert (
        content_wordpress_item["dimension_value_labels"]["wordpress_match_confidence"]
        == "dokładny adres URL"
    )
