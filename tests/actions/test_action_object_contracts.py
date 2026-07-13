"""ActionObject and action-safety API contract tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from apps.api.wilq_api.context_compaction import (
    compact_audit_event_for_daily_context,
    compact_audit_event_for_skill_context,
    compact_refresh_run_for_operator_context,
)
from apps.api.wilq_api.context_daily import (
    compact_evidence_for_operator_context,
    compact_knowledge_card_for_operator_context,
)
from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.ads_review_seed import seed_google_ads_live_review_metric_facts
from tests._contract_support.api_client import client
from tests._contract_support.env import clear_google_ads_env
from wilq.actions.content_refresh import (
    _draft_content_block_label,
    content_contract_label,
)
from wilq.actions.ga4.tracking_quality import (
    _blocked_claim_label as _ga4_tracking_blocked_claim_label,
)
from wilq.actions.ga4.tracking_quality import (
    _operation_type_label as _ga4_tracking_operation_type_label,
)
from wilq.actions.ga4.tracking_quality import (
    _tracking_dimension_gap_label as _ga4_tracking_dimension_gap_label,
)
from wilq.actions.ga4.tracking_quality import (
    _validation_label as _ga4_tracking_validation_label,
)
from wilq.actions.google_ads.business_context import (
    ADS_BUSINESS_CONTEXT_ACTION_ID,
    ADS_STRATEGY_REVIEW_ACTION_ID,
    ADS_TARGET_CONFIRMATION_ACTION_ID,
)
from wilq.actions.google_ads.campaign_triage import _campaign_channel_label
from wilq.actions.google_ads.demand_gen import demand_gen_contract_labels
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.payloads import validate_action_payload
from wilq.actions.service import (
    _ads_recommendation_type_label,
    _operator_audit_summary_text,
    list_actions,
)
from wilq.briefing.ahrefs_diagnostics import (
    _ahrefs_connector_status_label,
    _ahrefs_refresh_status_label,
    _ahrefs_status_label,
)
from wilq.briefing.ga4_diagnostics import (
    _ga4_connector_status_label,
    _ga4_decision_with_marketer_labels,
    _ga4_freshness_label,
    _ga4_optional_label,
    _ga4_read_contract_labels,
    _ga4_refresh_status_label,
    _ga4_risk_label,
    _ga4_section_status_label,
)
from wilq.briefing.localo_diagnostics import (
    _localo_connector_status_label,
    _localo_contract_evidence_kind,
    _localo_decision_status_label,
    _localo_decision_type_label,
    _localo_read_contract_status_label,
    _localo_refresh_status_label,
    _localo_section_status_label,
)
from wilq.briefing.localo_labels import localo_contract_label, localo_metric_fact_label
from wilq.briefing.merchant_diagnostics import (
    _merchant_connector_status_label,
    _merchant_freshness_label,
    _merchant_refresh_status_label,
    _merchant_risk_label,
    _merchant_status_label,
)
from wilq.briefing.merchant_labels import (
    merchant_dimension_label,
    merchant_dimension_value_label,
    merchant_display_label,
    merchant_metric_fact_label,
    merchant_preview_contract_label,
    merchant_reporting_context_label,
    merchant_resolution_label,
    merchant_severity_label,
)
from wilq.briefing.tactical_merchant import build_merchant_feed_items as _merchant_feed_items
from wilq.briefing.tactical_queue import _merchant_dimension_label
from wilq.connectors.vendor import VendorMetricFact
from wilq.content.preflight.marketer_view import content_marketer_blocked_claims
from wilq.operator_labels import (
    blocked_claim_label,
    blocked_claim_labels,
    connector_refresh_status_label,
    impact_comparison_summary_label,
    knowledge_reference_count_label,
    missing_contract_labels,
    opportunity_domain_label,
    source_connector_label,
    source_connector_labels,
)
from wilq.opportunities.engine import _risk_label as _opportunity_risk_label
from wilq.schemas import (
    ActionRisk,
    AuditEvent,
    ConnectorRefreshMode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    Evidence,
    FreshnessState,
    Ga4DecisionItem,
    KnowledgeCard,
    KnowledgeDecisionBinding,
    MetricFact,
    connector_refresh_has_live_data,
    connector_refresh_run_status_label,
)
from wilq.storage.local_state import local_state_store
from wilq.storage.metric_store import metric_store


def test_action_operator_labels_are_specific(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "action_labels.sqlite3"))
    leaks: list[tuple[str, str]] = []

    def walk(action_id: str, value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                item_path = f"{path}.{key}" if path else str(key)
                if (
                    key.endswith("_labels")
                    and isinstance(item, list)
                    and (
                        "warunek techniczny do sprawdzenia" in item
                        or "brak opisu w kontrakcie WILQ" in item
                    )
                ):
                    leaks.append((action_id, item_path))
                walk(action_id, item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(action_id, item, f"{path}[{index}]")

    for action in list_actions():
        walk(action.id, action.model_dump(mode="json"))

    assert leaks == []


def test_impact_comparison_summary_label_handles_legacy_copy_without_string_rewrite() -> None:
    legacy_summary = "Okno przed zmianą: 7 dni. Okno po zmianie: 14 dni."

    assert impact_comparison_summary_label(legacy_summary) == (
        "Porównanie sprzed zmiany: 7 dni. Porównanie po zmianie: 14 dni."
    )
    source = Path("wilq/operator_labels.py").read_text(encoding="utf-8")
    assert '.replace("Okno przed zmianą"' not in source
    assert '.replace("Okno po zmianie"' not in source


def test_operator_label_fallbacks_do_not_expose_raw_connector_ids() -> None:
    unknown_connector = "new_vendor_connector"

    assert source_connector_label(unknown_connector) == "źródło danych do sprawdzenia"
    assert source_connector_labels([unknown_connector]) == ["źródło danych do sprawdzenia"]
    connector_run = ConnectorRefreshRun(
        id="refresh_test",
        connector_id=unknown_connector,
        mode=ConnectorRefreshMode.status_probe,
        status=ConnectorRefreshStatus.completed,
        summary="Testowy odczyt.",
    )
    assert connector_run.connector_label == "źródło danych do sprawdzenia"
    assert connector_refresh_status_label(ConnectorRefreshStatus.completed) == ("odczyt zakończony")
    assert connector_refresh_status_label(ConnectorRefreshStatus.blocked) == ("odczyt zablokowany")
    assert connector_refresh_status_label("new_raw_status") == "status odczytu do sprawdzenia"
    assert (
        knowledge_reference_count_label()
        == "Nie ma użytej wiedzy; decyzja nie ma wsparcia z kart ani reguł"
    )
    assert (
        knowledge_reference_count_label(
            playbook_ids=["content_playbook_v1"],
            expert_rule_ids=["content_rule_v1"],
        )
        == "2 elementy wiedzy użyte w decyzji"
    )

    compact = compact_refresh_run_for_operator_context(
        {
            "id": "refresh_unknown_vendor",
            "connector_id": unknown_connector,
            "status": "new_raw_status",
            "evidence_ids": ["ev_unknown"],
            "missing_credentials": ["UNKNOWN_VENDOR_TOKEN"],
            "metric_summary": {"row_count": 1},
        }
    )

    assert compact["connector_label"] == "źródło danych do sprawdzenia"
    run = ConnectorRefreshRun(
        id="refresh_status_label_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_status_label_test"],
        summary="Testowy odczyt.",
    )
    blocked_run = ConnectorRefreshRun(
        id="refresh_blocked_status_label_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.blocked,
        summary="Testowy odczyt zablokowany.",
    )

    assert run.status_label == "odczyt zakończony"
    assert blocked_run.status_label == "odczyt zablokowany"
    assert compact["status_label"] == "status odczytu do sprawdzenia"
    assert unknown_connector not in compact["summary"]
    assert "new_raw_status" not in compact["summary"]
    assert "1 dowód źródłowy" in compact["summary"]
    assert "1 pole" in compact["summary"]
    assert "dowody 1" not in compact["summary"]
    assert "braki dostępu 1" not in compact["summary"]

    configured_compact = compact_refresh_run_for_operator_context(
        {
            "id": "refresh_configured",
            "connector_id": "google_merchant_center",
            "status": "completed",
            "evidence_ids": ["ev_one", "ev_two"],
            "missing_credentials": [],
        }
    )

    assert "2 dowody źródłowe" in configured_compact["summary"]
    assert "Pola dostępu kompletne w tym sprawdzeniu" in configured_compact["summary"]
    assert "dowody 2" not in configured_compact["summary"]
    assert "braki dostępu 0" not in configured_compact["summary"]


def test_connector_refresh_run_labels_incomplete_metric_persistence() -> None:
    run = ConnectorRefreshRun(
        id="refresh_google_ads_incomplete_metrics",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        vendor_data_collected=True,
        metrics_persisted=False,
        summary="Odczyt Google Ads zakończony, ale metryki nie zostały utrwalone.",
    )

    assert run.status_label == "odczyt niepełny - metryki nieutrwalone"
    assert connector_refresh_has_live_data(run) is False
    assert connector_refresh_run_status_label(run) == "odczyt niepełny - metryki nieutrwalone"

    trusted_run = run.model_copy(update={"metrics_persisted": True})
    assert connector_refresh_has_live_data(trusted_run) is True


def test_operator_label_fallbacks_do_not_humanize_raw_unknown_enums() -> None:
    raw_value = "new_VENDOR_raw_value"

    assert merchant_display_label("n:certification") == "certyfikacja"
    assert merchant_display_label("liczba unikalnych produktów") == ("liczba unikalnych produktów")
    assert merchant_display_label(
        "skalowanie produktu w reklamach produktowych i Performance Max"
    ) == ("skalowanie produktu w reklamach produktowych i Performance Max")
    assert merchant_display_label("opłacalność produktu") == "opłacalność produktu"
    assert (
        merchant_display_label("nadpisanie głównego pliku produktowego")
        == "nadpisanie głównego pliku produktowego"
    )
    assert merchant_display_label("zmiana danych produktu") == "zmiana danych produktu"

    labels = [
        *missing_contract_labels([raw_value]),
        blocked_claim_label(raw_value),
        *blocked_claim_labels([raw_value]),
        *content_marketer_blocked_claims([raw_value]),
        _merchant_dimension_label(raw_value),
        merchant_display_label(raw_value),
        merchant_dimension_label(raw_value),
        merchant_dimension_value_label("unknown_dimension", raw_value),
        merchant_metric_fact_label(raw_value),
        merchant_preview_contract_label(raw_value),
        merchant_reporting_context_label(raw_value),
        merchant_severity_label(raw_value),
        merchant_resolution_label(raw_value),
        content_contract_label(raw_value),
        _draft_content_block_label(raw_value),
        _ads_recommendation_type_label(raw_value),
        _ahrefs_status_label(raw_value),
        _ahrefs_connector_status_label(raw_value),
        _ahrefs_refresh_status_label(raw_value),
        _ga4_optional_label(raw_value, {}),
        _ga4_connector_status_label(raw_value),
        _ga4_refresh_status_label(raw_value),
        _ga4_freshness_label(raw_value),
        _ga4_section_status_label(raw_value),
        _ga4_risk_label(raw_value),
        _localo_decision_status_label(raw_value),
        _localo_section_status_label(raw_value),
        _localo_read_contract_status_label(raw_value),
        _localo_decision_type_label(raw_value),
        _localo_connector_status_label(raw_value),
        _localo_refresh_status_label(raw_value),
        _localo_contract_evidence_kind(raw_value),
        _merchant_connector_status_label(raw_value),
        _merchant_refresh_status_label(raw_value),
        _merchant_freshness_label(raw_value),
        _merchant_status_label(raw_value),
        _merchant_risk_label(raw_value),
        _campaign_channel_label(raw_value),
        _ga4_tracking_operation_type_label(raw_value),
        _ga4_tracking_dimension_gap_label(raw_value),
        _ga4_tracking_validation_label(raw_value),
        _ga4_tracking_blocked_claim_label(raw_value),
        _opportunity_risk_label(raw_value),
        localo_contract_label(raw_value),
        localo_metric_fact_label(raw_value),
        *_ga4_read_contract_labels([raw_value]),
        *demand_gen_contract_labels([raw_value]),
        opportunity_domain_label(raw_value),
    ]

    assert labels == [
        "brakujące dane do sprawdzenia",
        "obietnica do sprawdzenia",
        "obietnica do sprawdzenia",
        "obietnica do sprawdzenia",
        "wymiar Merchant do sprawdzenia",
        "wartość Merchant do sprawdzenia",
        "wymiar Merchant do sprawdzenia",
        "wartość Merchant do sprawdzenia",
        "metryka Merchant do sprawdzenia",
        "typ sprawdzenia do weryfikacji",
        "wartość Merchant do sprawdzenia",
        "wartość Merchant do sprawdzenia",
        "wartość Merchant do sprawdzenia",
        "warunek treści do sprawdzenia",
        "sekcja do sprawdzenia",
        "typ rekomendacji do sprawdzenia",
        "status Ahrefs do sprawdzenia",
        "status źródła do sprawdzenia",
        "status odczytu do sprawdzenia",
        "wartość GA4 do sprawdzenia",
        "status źródła do sprawdzenia",
        "status odczytu do sprawdzenia",
        "świeżość danych do sprawdzenia",
        "status sekcji do sprawdzenia",
        "ryzyko do sprawdzenia",
        "status decyzji do sprawdzenia",
        "status sekcji do sprawdzenia",
        "status danych do sprawdzenia",
        "typ decyzji Localo do sprawdzenia",
        "status źródła do sprawdzenia",
        "status odczytu do sprawdzenia",
        "zakres danych Localo do sprawdzenia",
        "status źródła do sprawdzenia",
        "status odczytu do sprawdzenia",
        "świeżość danych do sprawdzenia",
        "status sekcji do sprawdzenia",
        "ryzyko do sprawdzenia",
        "kanał kampanii do sprawdzenia",
        "typ sprawdzenia GA4 do weryfikacji",
        "wymiar GA4 do sprawdzenia",
        "warunek GA4 do sprawdzenia",
        "wniosek GA4 do sprawdzenia",
        "ryzyko szansy do sprawdzenia",
        "zakres danych Localo do sprawdzenia",
        "metryka Localo do sprawdzenia",
        "zakres danych GA4 do sprawdzenia",
        "warunek Demand Gen do sprawdzenia",
        "obszar do sprawdzenia",
    ]
    assert all(raw_value not in label for label in labels)
    assert all("new VENDOR raw value" not in label for label in labels)

    ga4_decision = Ga4DecisionItem.model_construct(
        id="decision_unknown_ga4_type",
        decision_type=raw_value,
        title="GA4",
        status="ready",
        rationale="Sprawdzenie GA4.",
        next_step="Otwórz GA4.",
    )
    labelled_ga4_decision = _ga4_decision_with_marketer_labels(ga4_decision)
    assert labelled_ga4_decision.decision_type_label == "typ decyzji GA4 do sprawdzenia"
    assert raw_value not in labelled_ga4_decision.decision_type_label

    knowledge_card = KnowledgeCard(
        id="card_unknown_operator_label",
        card_type=raw_value,
        title="Karta wiedzy",
        summary="Karta testowa.",
        source_type=raw_value,
        source_id="source_unknown_operator_label",
        source_url_or_path="docs/source.md",
        confidence=0.5,
    )
    assert knowledge_card.card_type_label == "typ wiedzy do sprawdzenia"
    assert knowledge_card.source_type_label == "źródło wiedzy do sprawdzenia"
    assert raw_value not in knowledge_card.card_type_label
    assert raw_value not in knowledge_card.source_type_label

    knowledge_binding = KnowledgeDecisionBinding(
        id="binding_unknown_route",
        title="Powiązanie wiedzy",
        status="ready",
        route=f"/{raw_value}",
        summary="Sprawdzenie wiedzy.",
        next_step="Otwórz widok.",
        risk=ActionRisk.low,
    )
    assert knowledge_binding.route_label == "widok do sprawdzenia"
    assert raw_value not in knowledge_binding.route_label
    assert (
        knowledge_binding.source_connector_summary_label
        == "Nie ma źródeł danych; nie traktuj tego jako rekomendacji"
    )
    assert (
        knowledge_binding.evidence_summary_label
        == "Nie ma dowodów źródłowych; nie traktuj tego jako rekomendacji"
    )
    assert (
        knowledge_binding.action_summary_label
        == "Nie ma akcji do sprawdzenia; zostaje ręczna ocena"
    )
    assert (
        knowledge_binding.knowledge_summary_label
        == "Nie ma użytej wiedzy; decyzja nie ma wsparcia z kart ani reguł"
    )
    assert (
        knowledge_binding.required_evidence_summary_label
        == "Nie wskazano wymaganych dowodów; nie odblokowuje to publikacji ani zapisu"
    )
    assert knowledge_binding.missing_contract_summary_label == "Dane kompletne dla tej decyzji"
    assert (
        knowledge_binding.missing_contract_detail_label
        == "Nie ma brakujących zakresów danych dla tej decyzji"
    )
    assert knowledge_binding.has_missing_contracts is False
    assert (
        knowledge_binding.blocked_claim_summary_label
        == "WILQ nie zgłosił zakazanych obietnic; nadal sprawdź dowody przed publikacją"
    )
    assert (
        knowledge_binding.blocked_claim_count_summary_label
        == "WILQ nie zgłosił zablokowanych obietnic; nadal sprawdź dowody przed publikacją"
    )
    assert knowledge_binding.has_blocked_claims is False
    assert (
        knowledge_binding.source_lineage_summary_label
        == "Nie ma śladów źródłowych; nie traktuj tego jako sprawdzonej wiedzy"
    )

    knowledge_blocked_claim_binding = KnowledgeDecisionBinding(
        id="binding_unknown_claim",
        title="Powiązanie wiedzy",
        status="blocked",
        route="/knowledge",
        summary="Sprawdzenie zakazanej obietnicy.",
        next_step="Nie używaj obietnicy bez dowodu.",
        risk=ActionRisk.high,
        blocked_claims=[raw_value],
    )
    assert knowledge_blocked_claim_binding.blocked_claim_labels == ["obietnica do sprawdzenia"]
    assert knowledge_blocked_claim_binding.blocked_claim_summary_label == "obietnica do sprawdzenia"
    assert (
        knowledge_blocked_claim_binding.blocked_claim_count_summary_label
        == "1 zablokowana obietnica"
    )
    assert knowledge_blocked_claim_binding.has_blocked_claims is True
    assert raw_value not in knowledge_blocked_claim_binding.blocked_claim_summary_label

    compact_evidence = compact_evidence_for_operator_context(
        Evidence(
            id="ev_unknown_operator_label",
            source_connector=raw_value,
            source_type=raw_value,
            source_id="unknown-source",
            freshness=FreshnessState(state="fresh"),
            summary="Raw vendor evidence summary.",
        )
    )
    assert compact_evidence["summary"] == (
        "Dowód ev_unknown_operator_label: źródło źródło danych do sprawdzenia, "
        "typ dowód źródłowy, świeżość świeże dane. "
        "Decyzję bierz z aktualnych diagnostyk WILQ."
    )
    assert raw_value not in compact_evidence["summary"]

    compact_card = compact_knowledge_card_for_operator_context(knowledge_card)
    assert compact_card["title"] == "Karta wiedzy: typ wiedzy do sprawdzenia"
    assert compact_card["card_type_label"] == "typ wiedzy do sprawdzenia"
    assert compact_card["source_type_label"] == "źródło wiedzy do sprawdzenia"
    assert raw_value not in compact_card["title"]
    assert raw_value not in compact_card["card_type_label"]
    assert raw_value not in compact_card["source_type_label"]

    raw_audit_event = {
        "id": "audit_unknown_operator_label",
        "action_id": "act_unknown_operator_label",
        "event_type": raw_value,
        "actor": "operator_test",
        "created_at": "2026-06-29T12:00:00Z",
    }
    daily_audit = compact_audit_event_for_daily_context(raw_audit_event)
    skill_audit = compact_audit_event_for_skill_context(raw_audit_event)
    assert daily_audit is not None
    assert skill_audit is not None
    assert daily_audit["event_type_label"] == "Zdarzenie audytu"
    assert skill_audit["event_type_label"] == "Zdarzenie audytu"
    assert raw_value not in daily_audit["summary"]
    assert raw_value not in skill_audit["summary"]
    assert daily_audit["summary"] == (
        "Ślad bezpieczeństwa: Zdarzenie audytu. "
        "Szczegóły techniczne są dostępne w szczegółach akcji WILQ."
    )

    merchant_items = _merchant_feed_items(
        facts=[
            MetricFact(
                name="issue_product_count",
                value=3,
                period="test",
                source_connector="google_merchant_center",
                evidence_id="ev_unknown_merchant_issue",
                dimensions={
                    "severity": raw_value,
                    "resolution": raw_value,
                    "issue_type": raw_value,
                    "country": "PL",
                },
            )
        ],
        action_ids={"google_merchant_center": ["act_unknown_merchant_issue"]},
    )
    assert merchant_items
    assert merchant_items[0].dimension_value_labels["severity"] == "wartość do sprawdzenia"
    assert merchant_items[0].dimension_value_labels["resolution"] == "wartość do sprawdzenia"
    assert merchant_items[0].dimension_value_labels["issue_type"] == "wartość do sprawdzenia"
    merchant_item_text = " ".join(
        [
            merchant_items[0].title,
            merchant_items[0].diagnosis,
            merchant_items[0].next_step,
        ]
    )
    assert raw_value not in merchant_item_text
    assert "Merchant do sprawdzenia" in merchant_item_text


def test_content_brief_preview_keeps_dev_site_as_optional_preview_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_target_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_target.duckdb"))
    source_url = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    dev_preview_url = "https://ekologus.dev.proudsite.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_content_public_url_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_gsc_content_public_url_test"],
        metric_summary={"query_page_rows": 1},
        summary="GSC source URL for public content review.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_content_public_url_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_content_public_url_test"],
        metric_summary={"content_object_count": 1},
        summary="Dev preview URL should not become public content inventory.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=8,
                dimensions={"query": "bdo przedsiębiorca", "page": source_url},
            ),
            VendorMetricFact(
                name="impressions",
                value=220,
                dimensions={"query": "bdo przedsiębiorca", "page": source_url},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "sitemap",
                    "content_url": dev_preview_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                    "modified_gmt": "2026-06-20T08:15:00+00:00",
                    "title_or_h1": "BDO - co musi wiedzieć przedsiębiorca?",
                    "canonical_url": dev_preview_url,
                },
            )
        ],
    )

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    diagnostics_response = client.get("/api/content/diagnostics")

    assert action_response.status_code == 200
    assert diagnostics_response.status_code == 200
    action = action_response.json()
    diagnostics = diagnostics_response.json()
    decision = next(item for item in diagnostics["decision_queue"] if item["page"] == source_url)
    assert decision["source_public_url"] == source_url
    assert decision["final_canonical_url"] == source_url
    assert decision["intended_final_url"] == source_url
    assert "ekologus.dev.proudsite.pl" not in decision["final_canonical_url"]
    assert decision["preview_url"] is None
    assert not any(key.startswith("target_site_") for key in decision)
    assert not any(key.startswith("mapping_review_") for key in decision)
    assert not any(key.startswith("transition_candidate") for key in decision)
    assert decision["inventory_gate_status"] == "missing_inventory_match"
    assert decision["inventory_gate_status_label"] == "brak dopasowania w spisie treści"
    assert decision["canonical_gate_status"] == "blocked_until_inventory_review"
    assert decision["canonical_gate_status_label"] == "zablokowane do sprawdzenia spisu"
    assert decision["duplicate_gate_status"] == "create_blocked_until_duplicate_check"
    assert decision["duplicate_gate_status_label"] == (
        "utworzenie zablokowane do kontroli duplikacji"
    )
    assert decision["decision_type_label"]
    assert decision["blocked_claim_labels"]
    assert "adresu kanonicznego" in decision["content_gate_summary"]
    assert "duplik" in decision["content_gate_summary"]
    assert diagnostics["operator_summary"]["current_site_match_count"] == 1
    assert not any(key.startswith("target_site_") for key in diagnostics["operator_summary"])
    preview = next(
        item
        for item in action["payload"]["content_brief_preview"]
        if item["final_canonical_url"] == source_url
    )
    assert preview["source_public_url"] == source_url
    assert preview["final_canonical_url"] == source_url
    assert preview["intended_final_url"] == source_url
    assert preview["preview_url"] is None
    assert not any(key.startswith("target_site_") for key in preview)
    assert not any(key.startswith("mapping_review_") for key in preview)
    assert not any(key.startswith("transition_candidate") for key in preview)


def test_content_diagnostics_ignores_dev_site_alternatives_when_public_url_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "content_target_alternative_state.sqlite3"),
    )
    monkeypatch.setenv(
        "WILQ_METRIC_DB",
        str(tmp_path / "content_target_alternative.duckdb"),
    )
    source_url = "https://www.ekologus.pl/remediacja-czym-jest-na-czym-polega-kiedy-jest-wymagana/"
    dev_same_path_url = (
        "https://ekologus.dev.proudsite.pl/remediacja-czym-jest-na-czym-polega-kiedy-jest-wymagana/"
    )
    alternative_url = (
        "https://ekologus.dev.proudsite.pl/uslugi/ekodokumentacje/"
        "remediacje-monitoring-gruntow-i-wod-podziemnych/"
    )
    normalized_alternative_url = alternative_url.rstrip("/")
    gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_content_dev_ignored_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_gsc_content_dev_ignored_test"],
        metric_summary={"query_page_rows": 1},
        summary="GSC source URL with dev preview alternatives ignored.",
    )
    wordpress_run = ConnectorRefreshRun(
        id="refresh_wordpress_content_dev_ignored_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wordpress_content_dev_ignored_test"],
        metric_summary={"content_object_count": 2},
        summary="WordPress inventory with current URL and one dev preview alternative.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=11,
                dimensions={"query": "remediacja co to", "page": source_url},
            ),
            VendorMetricFact(
                name="impressions",
                value=440,
                dimensions={"query": "remediacja co to", "page": source_url},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "post",
                    "content_url": source_url,
                    "status": "publish",
                    "inventory_source": "wordpress_rest",
                    "modified_gmt": "2024-05-01T08:00:00+00:00",
                    "title_or_h1": "Remediacja - czym jest?",
                    "canonical_url": source_url,
                },
            ),
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "uslugi",
                    "content_url": alternative_url,
                    "status": "indexed",
                    "inventory_source": "public_sitemap",
                    "modified_gmt": "2025-09-05T09:13:12+00:00",
                    "title_or_h1": ("Remediacje, monitoring gruntów i wód podziemnych"),
                    "canonical_url": alternative_url,
                },
            ),
        ],
    )

    diagnostics_response = client.get("/api/content/diagnostics")
    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")

    assert diagnostics_response.status_code == 200
    assert action_response.status_code == 200
    diagnostics = diagnostics_response.json()
    decision = next(item for item in diagnostics["decision_queue"] if item["page"] == source_url)
    assert decision["source_public_url"] == source_url
    assert decision["final_canonical_url"] == source_url
    assert decision["intended_final_url"] == source_url
    assert not any(key.startswith("target_site_") for key in decision)
    assert not any(key.startswith("mapping_review_") for key in decision)
    assert not any(key.startswith("transition_candidate") for key in decision)
    assert normalized_alternative_url not in str(decision)
    assert dev_same_path_url not in str(decision)
    assert not any(key.startswith("target_site_") for key in diagnostics["operator_summary"])

    action = action_response.json()
    preview = next(
        item
        for item in action["payload"]["content_brief_preview"]
        if item["final_canonical_url"] == source_url
    )
    assert preview["source_public_url"] == source_url
    assert preview["final_canonical_url"] == source_url
    assert preview["intended_final_url"] == source_url
    assert not any(key.startswith("target_site_") for key in preview)
    assert not any(key.startswith("mapping_review_") for key in preview)
    assert not any(key.startswith("transition_candidate") for key in preview)
    assert normalized_alternative_url not in str(preview)
    assert dev_same_path_url not in str(preview)
    assert preview["inventory_gate_status"] == "confirmed_current_inventory"
    assert preview["canonical_gate_status"] == "public_canonical_confirmed"
    assert preview["duplicate_gate_status"] == "existing_public_content_requires_refresh_or_merge"
    assert "duplik" in preview["content_gate_summary"]
    assert preview["seo_title_direction"]
    assert preview["meta_description_direction"]
    assert preview["schema_direction"]
    assert preview["publication_readiness_status"] == "blocked_until_review"
    assert "legal_factual_review" in preview["publication_blockers"]
    assert "human_confirm_before_wordpress_write" in preview["publication_blockers"]
    assert preview["legal_review_notes"]
    assert preview["brand_voice_notes"]
    assert preview["wordpress_inventory_match"] == "present"
    assert preview["apply_allowed"] is False
    assert preview["api_mutation_ready"] is False


def test_content_action_preview_keeps_dimensioned_decisions_after_newer_aggregate_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_action_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_action.duckdb"))
    older = datetime(2026, 6, 18, 8, 0, tzinfo=UTC)
    newer = older + timedelta(hours=2)
    page = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/"
    gsc_dimensioned_run = ConnectorRefreshRun(
        id="refresh_gsc_action_dimensioned_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=older,
        completed_at=older,
        evidence_ids=["ev_refresh_gsc_action_dimensioned_test"],
        metric_summary={"query_page_rows": 1},
        summary="Dimensioned GSC facts for action preview regression.",
    )
    wordpress_inventory_run = ConnectorRefreshRun(
        id="refresh_wordpress_action_dimensioned_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=older,
        completed_at=older,
        evidence_ids=["ev_refresh_wordpress_action_dimensioned_test"],
        metric_summary={"content_object_count": 1},
        summary="Dimensioned WordPress inventory for action preview regression.",
    )
    noisy_gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_action_noisy_aggregate_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        started_at=newer,
        completed_at=newer,
        evidence_ids=["ev_refresh_gsc_action_noisy_aggregate_test"],
        metric_summary={"clicks": 2, "impressions": 200},
        summary="Newer non-query/page GSC facts should not erase action previews.",
    )
    metric_store().save_connector_refresh_metrics(
        gsc_dimensioned_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=4,
                dimensions={"query": "bdo co to", "page": page},
            ),
            VendorMetricFact(
                name="impressions",
                value=4429,
                dimensions={"query": "bdo co to", "page": page},
            ),
            VendorMetricFact(
                name="ctr",
                value=0.000903,
                dimensions={"query": "bdo co to", "page": page},
            ),
            VendorMetricFact(
                name="average_position",
                value=9.44,
                dimensions={"query": "bdo co to", "page": page},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        wordpress_inventory_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "pages",
                    "content_url": page,
                    "status": "publish",
                },
            )
        ],
    )
    metric_store().save_connector_refresh_metrics(
        noisy_gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=index,
                dimensions={"date": f"2026-06-{index % 28 + 1:02d}", "row": str(index)},
            )
            for index in range(160)
        ],
    )

    diagnostics_response = client.get("/api/content/diagnostics")
    assert diagnostics_response.status_code == 200
    diagnostics = diagnostics_response.json()
    assert diagnostics["decision_queue"]
    assert diagnostics["decision_queue"][0]["evidence_ids"]

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert action_response.status_code == 200
    action = action_response.json()
    previews = action["payload"].get("content_brief_preview") or []

    assert previews
    assert previews[0]["preview_contract"] == "content_brief_preview_v1"
    assert previews[0]["candidate_id"].startswith("content_brief_gsc_")
    assert previews[0]["evidence_ids"]
    assert previews[0]["intent"]
    assert previews[0]["content_angle"]
    assert previews[0]["audience"]
    assert previews[0]["key_objections"]
    assert previews[0]["h1_direction"]
    assert previews[0]["h2_direction"]
    assert previews[0]["faq_direction"]
    assert previews[0]["cta_direction"]
    assert previews[0]["internal_link_direction"]
    assert previews[0]["source_facts"]
    assert all("target_url=" not in fact for fact in previews[0]["source_facts"])
    assert all("GSC page=" not in fact for fact in previews[0]["source_facts"])
    assert all("queries=" not in fact for fact in previews[0]["source_facts"])
    assert any("Strona z GSC:" in fact for fact in previews[0]["source_facts"])
    assert previews[0]["missing_evidence"]
    assert "gwarancja pozycji" in previews[0]["forbidden_claims"]
    assert previews[0]["apply_allowed"] is False
    assert previews[0]["api_mutation_ready"] is False
    assert "gwarancja pozycji" in previews[0]["blocked_claims"]


def test_content_brief_preview_homepage_candidate_id_is_traceable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    homepage = "https://www.ekologus.pl/"
    homepage_gsc_run = ConnectorRefreshRun(
        id="refresh_gsc_homepage_candidate_id_test",
        connector_id="google_search_console",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_gsc_homepage_candidate_id_test"],
        metric_summary={"query_page_rows": 1},
        summary="Homepage GSC fact for content candidate ID regression.",
    )
    homepage_wordpress_run = ConnectorRefreshRun(
        id="refresh_wp_homepage_candidate_id_test",
        connector_id="wordpress_ekologus",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        evidence_ids=["ev_refresh_wp_homepage_candidate_id_test"],
        metric_summary={"content_object_count": 1},
        summary="Homepage WordPress inventory fact for content candidate ID regression.",
    )
    metric_store().save_connector_refresh_metrics(
        homepage_gsc_run,
        detailed_facts=[
            VendorMetricFact(
                name="clicks",
                value=6,
                dimensions={"query": "ekologus", "page": homepage},
            ),
            VendorMetricFact(
                name="impressions",
                value=80,
                dimensions={"query": "ekologus", "page": homepage},
            ),
            VendorMetricFact(
                name="ctr",
                value=0.075,
                dimensions={"query": "ekologus", "page": homepage},
            ),
            VendorMetricFact(
                name="average_position",
                value=1.01,
                dimensions={"query": "ekologus", "page": homepage},
            ),
        ],
    )
    metric_store().save_connector_refresh_metrics(
        homepage_wordpress_run,
        detailed_facts=[
            VendorMetricFact(
                name="content_object_seen",
                value=1,
                dimensions={
                    "connector_id": "wordpress_ekologus",
                    "content_type": "pages",
                    "content_url": homepage,
                    "status": "publish",
                },
            )
        ],
    )

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")

    assert action_response.status_code == 200
    action = action_response.json()
    previews = action["payload"].get("content_brief_preview") or []
    homepage_preview = next(
        item for item in previews if item.get("final_canonical_url") == homepage
    )
    assert homepage_preview["candidate_id"] == "content_brief_gsc_www_ekologus_pl"
    assert not homepage_preview["candidate_id"].endswith("_")


def test_content_brief_candidate_review_persists_audit_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_review_state.sqlite3"))

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert action_response.status_code == 200
    action = action_response.json()
    candidate = action["payload"]["content_brief_preview"][0]
    candidate_id = candidate["candidate_id"]
    reviewed_url = candidate["final_canonical_url"] or candidate["source_public_url"]

    review_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": f"Wybrano kandydata briefu {candidate_id} do dalszego review.",
            "checked_items": [
                f"candidate:{candidate_id}",
                f"source_type:{candidate['source_type']}",
                f"mode:{candidate['mode']}",
                "url_review_outcome:confirm_final_canonical_url",
                f"reviewed_url:{reviewed_url}",
                "review_notes:operator potwierdzil publiczny URL do dalszego review",
                "draft_readiness_outcome:needs_duplicate_resolution",
                "canonical_review_outcome:canonical_needs_target_confirmation",
                "duplicate_review_outcome:merge_required_before_draft",
                "legal_factual_review_outcome:needs_expert_review",
                "human_review_outcome:prepare_only_review_recorded",
                "draft_readiness_notes:canonical i duplikaty wymagaja dalszego review",
            ],
            "blockers": [
                "payload_apply_allowed_false",
                "wordpress_write_not_requested",
                "blocked_claim:gwarancja pozycji",
            ],
        },
    )

    assert review_response.status_code == 200
    result = review_response.json()
    assert result["status"] == "recorded"
    assert result["audit_event"]["event_type"] == "human_review_approved_for_prepare"
    assert result["review_gate"]["apply_allowed"] is False
    assert result["review_gate"]["last_review_outcome"] == "approved_for_prepare"
    assert "wybrano pozycję do sprawdzenia" in result["audit_event"]["summary"]
    assert "URL finalny: potwierdź finalny URL kanoniczny" in result["audit_event"]["summary"]
    assert "sprawdzony URL zapisany w szczegółach audytu" in result["audit_event"]["summary"]
    for raw_term in (
        f"candidate:{candidate_id}",
        "source_type:gsc_query_page",
        "mode:refresh",
        "payload_apply_allowed_false",
        "wordpress_write_not_requested",
        "blocked_claim:",
    ):
        assert raw_term not in result["audit_event"]["summary"]
    assert "podgląd zmian nie pozwala na zapis" in result["audit_event"]["summary"]
    assert "zapis WordPress nie został zlecony" in result["audit_event"]["summary"]
    assert "nie wolno twierdzić: gwarancja pozycji" in result["audit_event"]["summary"]
    assert result["audit_event"]["details"]["content_url_review"] == {
        "candidate": candidate_id,
        "url_review_outcome": "confirm_final_canonical_url",
        "reviewed_url": reviewed_url,
        "review_notes": "operator potwierdzil publiczny URL do dalszego review",
    }
    assert result["audit_event"]["details"]["content_draft_readiness_review"] == {
        "candidate": candidate_id,
        "draft_readiness_outcome": "needs_duplicate_resolution",
        "canonical_review_outcome": "canonical_needs_target_confirmation",
        "duplicate_review_outcome": "merge_required_before_draft",
        "legal_factual_review_outcome": "needs_expert_review",
        "human_review_outcome": "prepare_only_review_recorded",
        "draft_readiness_notes": "canonical i duplikaty wymagaja dalszego review",
    }
    assert (
        "Ten krok nie zapisuje zmian w zewnętrznych systemach" in result["audit_event"]["summary"]
    )

    audit_response = client.get("/api/audit/events?action_id=act_prepare_content_refresh_queue")
    assert audit_response.status_code == 200
    persisted_audit = audit_response.json()[0]
    assert persisted_audit["event_type"] == "human_review_approved_for_prepare"
    assert "wybrano pozycję do sprawdzenia" in persisted_audit["summary"]
    assert f"candidate:{candidate_id}" not in persisted_audit["summary"]
    assert persisted_audit["details"]["content_url_review"]["reviewed_url"] == (reviewed_url)

    reviewed_action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert reviewed_action_response.status_code == 200
    reviewed_action = reviewed_action_response.json()
    draft_previews = reviewed_action["payload"]["wordpress_draft_payload_preview"]
    assert len(draft_previews) == 1
    draft_preview = draft_previews[0]
    assert draft_preview["preview_contract"] == "wordpress_draft_payload_preview_v1"
    assert draft_preview["source_preview_contract"] == "content_brief_preview_v1"
    assert draft_preview["candidate_id"] == candidate_id
    assert draft_preview["intent"]
    assert draft_preview["post_status"] == "draft"
    assert draft_preview["mutation_allowed"] is False
    assert draft_preview["apply_allowed"] is False
    assert draft_preview["api_mutation_ready"] is False
    assert draft_preview["destructive"] is False
    assert draft_preview["content_url_review_recorded_outcome"] == "confirm_final_canonical_url"
    assert draft_preview["content_url_review_reviewed_url"] == reviewed_url
    assert draft_preview["content_url_review_notes"] == (
        "operator potwierdzil publiczny URL do dalszego review"
    )
    assert not any(
        key.startswith("target_site_")
        or key.startswith("mapping_review_")
        or key.startswith("transition_candidate")
        for key in draft_preview
    )
    assert "current_transition_candidate_url" not in draft_preview
    assert draft_preview["draft_readiness_review_recorded_outcome"] == "needs_duplicate_resolution"
    assert (
        draft_preview["canonical_review_recorded_outcome"] == "canonical_needs_target_confirmation"
    )
    assert draft_preview["duplicate_review_recorded_outcome"] == "merge_required_before_draft"
    assert draft_preview["legal_factual_review_recorded_outcome"] == "needs_expert_review"

    assert draft_preview["human_review_recorded_outcome"] == "prepare_only_review_recorded"
    assert (
        draft_preview["draft_readiness_review_notes"]
        == "canonical i duplikaty wymagaja dalszego review"
    )
    assert draft_preview["draft_generation_status"] == "blocked_pending_canonical_duplicate_review"
    assert "final_canonical_review" in draft_preview["draft_blockers"]
    assert "duplicate_or_cannibalization_check" in draft_preview["draft_blockers"]
    assert "human_confirm_before_wordpress_write" in draft_preview["draft_blockers"]
    assert draft_preview["inventory_gate_status"]
    assert draft_preview["canonical_gate_status"]
    assert draft_preview["duplicate_gate_status"]
    assert draft_preview["content_gate_summary"]
    assert (
        "spis treści: spis potwierdzony na obecnej stronie"
        in draft_preview["content_gate_status_summary"]
    )
    assert (
        "URL kanoniczny: publiczny URL kanoniczny potwierdzony"
        in draft_preview["content_gate_status_summary"]
    )
    assert (
        "duplikaty: istniejąca publiczna treść wymaga odświeżenia albo scalenia"
        in draft_preview["content_gate_status_summary"]
    )
    draft_contract = draft_preview["draft_generation_contract"]
    assert draft_contract["contract_version"] == "content_draft_generation_v1"
    assert draft_contract["language"] == "pl-PL"
    assert draft_contract["status"] == draft_preview["draft_generation_status"]
    assert draft_contract["allowed_output_kind"] in {
        "outline_only_until_checks_complete",
        "reviewable_polish_draft_preview",
    }
    assert "duplicate_or_cannibalization_check" in draft_contract["requires_passed_gates"]
    assert "publish_ready_claim" in draft_contract["forbidden_outputs"]
    readiness_contract = draft_preview["draft_readiness_review_contract"]
    assert readiness_contract["contract_version"] == "content_draft_readiness_review_v1"
    assert readiness_contract["scope"] == "review_only"
    assert "needs_duplicate_resolution" in readiness_contract["allowed_outcomes"]
    assert "canonical_review_outcome" in readiness_contract["required_fields"]
    assert "wordpress_draft_write" in readiness_contract["blocked_outputs"]
    assert draft_preview["wordpress_draft_handoff_status"] == "blocked_until_draft_checks_complete"
    assert (
        "wordpress_draft_write_not_requested" in draft_preview["wordpress_draft_handoff_blockers"]
    )
    wordpress_draft_contract = draft_preview["wordpress_draft_handoff_contract"]
    assert wordpress_draft_contract["contract_version"] == "wordpress_draft_handoff_v1"
    assert wordpress_draft_contract["scope"] == "blocked_preview_only"
    assert wordpress_draft_contract["final_canonical_url"] == draft_preview["final_canonical_url"]
    assert "target_site_url" not in wordpress_draft_contract
    assert wordpress_draft_contract["required_next_action_contract"] == "wordpress_draft_handoff_v1"
    assert "content_draft_readiness_review" in wordpress_draft_contract["requires_passed_gates"]
    assert "wordpress_draft_write" in wordpress_draft_contract["blocked_outputs"]
    measurement_plan = draft_preview["post_publication_measurement_plan"]
    assert measurement_plan["contract_version"] == "post_publication_measurement_plan_v1"
    assert measurement_plan["scope"] == "blocked_preview_only"
    assert measurement_plan["final_canonical_url"] == draft_preview["final_canonical_url"]
    assert "target_site_url" not in measurement_plan
    assert measurement_plan["status"] == "blocked_until_publish_and_followup_data"
    assert "google_search_console" in measurement_plan["required_source_connectors"]
    assert "google_analytics_4" in measurement_plan["required_source_connectors"]
    assert "28d_after_publish" in measurement_plan["followup_windows"]
    assert "followup_window_captured" in measurement_plan["requires_before_claims"]
    assert "ranking_gain_claim" in measurement_plan["blocked_outputs"]
    assert "obietnica wzrostu leadów" in measurement_plan["blocked_outputs"]
    assert draft_preview["draft_payload"]["post_status"] == "draft"
    assert draft_preview["post_status_label"] == "szkic"
    assert draft_preview["draft_payload"]["post_status_label"] == "szkic"
    assert draft_preview["draft_payload"]["post_title"]
    assert "human_confirm_before_wordpress_write" in draft_preview["required_validation"]
    assert "gwarancja pozycji" in draft_preview["blocked_claims"]
    assert draft_preview["evidence_ids"]

    preview_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/preview",
        json={"requested_by": "operator_test", "max_items": 12},
    )
    assert preview_response.status_code == 200
    preview_items = preview_response.json()["preview_items"]
    assert any(
        item.get("preview_contract") == "wordpress_draft_payload_preview_v1"
        and item.get("candidate_id") == candidate_id
        for item in preview_items
    )


def test_actions_api_drops_legacy_content_review_audit_terms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "legacy_content_review.sqlite3"))

    local_state_store().save_audit_event(
        AuditEvent(
            id="audit_legacy_content_url_review",
            action_id="act_prepare_content_refresh_queue",
            event_type="human_review_approved_for_prepare",
            actor="operator_legacy_review",
            summary=(
                "Wynik review: zatwierdzone. Sprawdzone: "
                "mapping_outcome:confirm_alternative_candidate, "
                "selected_target_url:[stored in audit details], "
                "mapping_notes:target wybrany tylko do review staging handoff. "
                "Blokady: payload_apply_allowed_false, wordpress_write_not_requested, "
                "blocked_claim:ranking guarantee. "
                "Sprawdzone: source_type:gsc_query_page, mode:refresh."
            ),
            evidence_ids=["ev_refresh_wordpress_content_contract_test"],
            details={
                "review_outcome": "approved_for_prepare",
                "reviewed_by": "operator_legacy_review",
                "checked_items": [
                    "candidate:content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca",
                    "mapping_outcome:confirm_alternative_candidate",
                    "selected_target_url:https://ekologus.dev.proudsite.pl/bdo/",
                    "mapping_notes:target wybrany tylko do review staging handoff",
                    "draft_readiness_outcome:needs_duplicate_resolution",
                    "source_type:gsc_query_page",
                    "mode:refresh",
                ],
                "blockers": [
                    "payload_apply_allowed_false",
                    "wordpress_write_not_requested",
                    "blocked_claim:ranking guarantee",
                ],
                "target_site_mapping_review": {
                    "candidate": "content_brief_gsc_bdo_co_musi_wiedziec_przedsiebiorca",
                    "mapping_outcome": "confirm_alternative_candidate",
                    "mapping_notes": "target wybrany tylko do review staging handoff",
                    "selected_target_url": "https://ekologus.dev.proudsite.pl/bdo/",
                },
                "content_draft_readiness_review": {
                    "draft_readiness_notes": "staging handoff pozostaje zablokowany",
                },
            },
        )
    )

    response = client.get("/api/actions")

    assert response.status_code == 200
    actions = response.json()
    content_action = next(
        action for action in actions if action["id"] == "act_prepare_content_refresh_queue"
    )
    visible_content_copy = "\n".join(
        [
            content_action["human_diagnosis"],
            content_action["recommended_reason"],
            *[
                item["content_gate_summary"]
                for item in content_action["payload"]["content_brief_preview"]
            ],
            *[
                fact
                for item in content_action["payload"]["content_brief_preview"]
                for fact in item["source_facts"]
            ],
        ]
    )
    for stale_term in (
        "URL/query evidence",
        "GSC query/page",
        "query/page facts",
        "WordPress inventory facts",
        "WordPress inventory",
        "core workflow",
        "clean runtime",
    ):
        assert stale_term not in visible_content_copy
    serialized = json.dumps(content_action["audit_events"], ensure_ascii=False)
    for stale_term in (
        "target_site",
        "mapping_review",
        "mapping_outcome",
        "selected_target_url",
        "staging handoff",
        "ekologus.dev.proudsite.pl",
        "source_type:gsc_query_page",
        "mode:refresh",
    ):
        assert stale_term not in serialized
    legacy_event = next(
        event
        for event in content_action["audit_events"]
        if event["id"] == "audit_legacy_content_url_review"
    )
    assert legacy_event["summary"] == (
        "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
    )
    assert legacy_event["details"]["checked_items"]
    assert "content_draft_readiness_review" not in legacy_event["details"]
    assert "blockers" in legacy_event["details"]
    assert content_action["review_gate"]["last_review_outcome"] is None
    service_source = Path("wilq/actions/service.py").read_text(encoding="utf-8")
    assert "_is_obsolete_content_review_event" not in service_source
    assert '"target", "site", "mapping", "review"' not in service_source


def test_content_refresh_empty_state_uses_operator_source_language(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_empty_state.sqlite3"))
    monkeypatch.setenv("WILQ_METRIC_DB", str(tmp_path / "content_empty_metrics.duckdb"))
    monkeypatch.setenv("WILQ_ACCESS_PACK_PATH", str(tmp_path / "empty_access_pack"))

    response = client.get("/api/actions/act_prepare_content_refresh_queue")

    assert response.status_code == 200
    action = response.json()
    preview = action["payload"]["content_brief_preview"][0]
    visible_copy = "\n".join(
        [
            action["human_diagnosis"],
            action["recommended_reason"],
            preview["content_gate_summary"],
            preview["brief_goal"],
            *preview["source_facts"],
        ]
    )
    for stale_term in (
        "URL/query evidence",
        "GSC query/page",
        "query/page facts",
        "WordPress inventory facts",
        "WordPress inventory",
        "core workflow",
        "clean runtime",
    ):
        assert stale_term not in visible_copy
    assert "dane GSC dla zapytań i stron" in visible_copy
    assert "spis treści WordPress" in visible_copy


def test_content_refresh_review_gates_use_polish_operator_language(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "content_review_gate_language.sqlite3"),
    )

    response = client.get("/api/actions/act_prepare_content_refresh_queue")

    assert response.status_code == 200
    action = response.json()
    review_gate_copy = "\n".join(
        [
            *action["payload"]["operator_review_gates"],
            *action["review_gate"]["operator_checklist"],
            *action["review_gate"]["operator_checklist_labels"],
        ]
    )

    assert "sprawdź intencję zapytania i tematu" in review_gate_copy
    assert "query" + "/topic" not in review_gate_copy


def test_wordpress_handoff_review_gate_avoids_payload_jargon(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "wordpress_handoff_review_gate_language.sqlite3"),
    )

    response = client.get("/api/actions/act_prepare_wordpress_draft_handoff")

    assert response.status_code == 200
    action = response.json()
    review_gate_copy = "\n".join(
        [
            *action["review_gate"]["required_checks"],
            *action["review_gate"]["required_check_labels"],
            *action["review_gate"]["operator_checklist"],
            *action["review_gate"]["operator_checklist_labels"],
        ]
    )

    assert "wordpress_draft_payload_preview" not in review_gate_copy
    assert "payload" not in review_gate_copy
    assert "wordpress_draft_preview_review" in action["review_gate"]["required_checks"]
    assert "podgląd wpisu WordPress" in action["review_gate"]["required_check_labels"]


def test_content_strategist_context_pack_preserves_reviewed_draft_preview(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv(
        "WILQ_STATE_DB",
        str(tmp_path / "content_review_context_state.sqlite3"),
    )

    action_response = client.get("/api/actions/act_prepare_content_refresh_queue")
    assert action_response.status_code == 200
    action = action_response.json()
    candidate = action["payload"]["content_brief_preview"][0]
    candidate_id = candidate["candidate_id"]

    review_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": f"Wybrano propozycję briefu {candidate_id} do context-pack proof.",
            "checked_items": [
                f"candidate:{candidate_id}",
                f"source_type:{candidate['source_type']}",
                f"mode:{candidate['mode']}",
            ],
            "blockers": [
                "payload_apply_allowed_false",
                "wordpress_write_not_requested",
                "blocked_claim:gwarancja pozycji",
            ],
        },
    )
    assert review_response.status_code == 200

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-content-strategist"},
    )

    assert context_response.status_code == 200
    context = context_response.json()
    actions_by_id = {item["id"]: item for item in context["active_action_objects"]}
    content_action = actions_by_id["act_prepare_content_refresh_queue"]
    assert "payload" not in content_action
    assert "action_plan" in content_action
    payload = content_action["action_plan"]

    assert payload["content_plan_items_total"] >= 1
    assert payload["content_plan_items_included"] >= 1
    brief_preview = next(
        item for item in payload["content_plan_items"] if item["candidate_id"] == candidate_id
    )
    assert brief_preview["intent"]
    assert brief_preview["source_type_label"] == "Google Search Console"
    assert brief_preview["mode_label"] == "odśwież istniejącą treść"
    assert brief_preview["publication_readiness_status_label"] == ("zablokowane do sprawdzenia")
    assert "gwarancja pozycji" in brief_preview["blocked_claim_labels"]
    assert brief_preview["content_angle"]
    assert brief_preview["audience"]
    assert brief_preview["h1_direction"]
    assert brief_preview["seo_title_direction"]
    assert brief_preview["meta_description_direction"]
    assert brief_preview["h2_direction"]
    assert brief_preview["faq_direction"]
    assert brief_preview["schema_direction"]
    assert brief_preview["key_objections"]
    assert brief_preview["cta_direction"]
    assert brief_preview["internal_link_direction"]
    assert "publication_readiness_status" not in brief_preview
    assert "publication_blockers" not in brief_preview
    assert "kontrola prawna i faktograficzna" in brief_preview["publication_blocker_labels"]
    assert brief_preview["legal_review_notes"]
    assert brief_preview["brand_voice_notes"]
    assert brief_preview["source_facts"]
    assert all("target_url=" not in fact for fact in brief_preview["source_facts"])
    assert all("GSC page=" not in fact for fact in brief_preview["source_facts"])
    assert all("queries=" not in fact for fact in brief_preview["source_facts"])
    assert any("Strona z GSC:" in fact for fact in brief_preview["source_facts"])
    assert brief_preview["missing_evidence"]
    assert brief_preview["metric_tiles"]["kliknięcia"] > 0
    assert "forbidden_claims" not in brief_preview
    assert brief_preview["source_public_url"]
    assert brief_preview["final_canonical_url"]
    assert brief_preview["intended_final_url"]
    assert "ekologus.dev.proudsite.pl" not in brief_preview["final_canonical_url"]
    assert not [
        key
        for key in brief_preview
        if key.startswith(("target_site_", "mapping_review_", "transition_candidate"))
        or key == "current_transition_candidate_url"
    ]
    assert "required_validation" not in brief_preview
    assert "kontrola duplikacji i kanibalizacji" in brief_preview["required_check_labels"]
    assert "odśwież istniejącą treść" in brief_preview["decision_option_labels"]
    assert payload["wordpress_draft_preview_items_total"] == 1
    assert payload["wordpress_draft_preview_items_included"] == 1
    draft_preview = payload["wordpress_draft_preview_items"][0]
    assert "preview_contract" not in draft_preview
    assert "source_preview_contract" not in draft_preview
    assert draft_preview["candidate_id"] == candidate_id
    assert draft_preview["intent"]
    assert draft_preview["post_status"] == "draft"
    assert draft_preview["operation_type_label"] == ("wersja robocza istniejącej treści")
    assert draft_preview["post_status_label"] == "szkic"
    assert draft_preview["draft_generation_status_label"]
    assert "gwarancja pozycji" in draft_preview["blocked_claim_labels"]
    assert draft_preview["draft_payload"]["post_title"].startswith("Odświeżenie:")
    assert any(
        block.get("section_label") == "intencja"
        for block in draft_preview["draft_payload"]["content_blocks"]
    )
    assert draft_preview["source_public_url"]
    assert draft_preview["final_canonical_url"]
    assert draft_preview["intended_final_url"]
    assert not [
        key
        for key in draft_preview
        if key.startswith(("target_site_", "mapping_review_", "transition_candidate"))
        or key == "current_transition_candidate_url"
    ]
    assert "draft_generation_status" not in draft_preview
    assert "inventory_gate_status" not in draft_preview
    assert "canonical_gate_status" not in draft_preview
    assert "duplicate_gate_status" not in draft_preview
    assert draft_preview["inventory_gate_status_label"]
    assert draft_preview["canonical_gate_status_label"]
    assert draft_preview["duplicate_gate_status_label"]
    assert draft_preview["content_gate_summary"]
    draft_contract = draft_preview["draft_generation_contract"]
    assert draft_contract["contract_version"] == "content_draft_generation_v1"
    assert draft_contract["language"] == "pl-PL"
    assert "status" not in draft_contract
    assert draft_contract["allowed_output_kind"] in {
        "outline_only_until_checks_complete",
        "reviewable_polish_draft_preview",
    }
    assert "duplicate_or_cannibalization_check" in draft_contract["requires_passed_gates"]
    assert "publish_ready_claim" in draft_contract["forbidden_outputs"]
    assert (
        "warunek: kontrola duplikacji i kanibalizacji" in draft_preview["draft_generation_summary"]
    )
    assert "zakaz: obietnica gotowości do publikacji" in draft_preview["draft_generation_summary"]
    assert draft_preview["wordpress_draft_handoff_status"] in {
        "blocked_until_draft_checks_complete",
        "blocked_until_draft_readiness_review",
        "blocked_until_wordpress_draft_handoff_action",
    }
    assert (
        "wordpress_draft_write_not_requested" in draft_preview["wordpress_draft_handoff_blockers"]
    )
    assert (
        "zapis szkicu WordPress nie został zlecony"
        in draft_preview["wordpress_draft_handoff_blocker_labels"]
    )
    assert (
        "blokada: zapis szkicu WordPress nie został zlecony"
        in draft_preview["wordpress_draft_handoff_summary"]
    )
    wordpress_draft_contract = draft_preview["wordpress_draft_handoff_contract"]
    assert wordpress_draft_contract["contract_version"] == "wordpress_draft_handoff_v1"
    assert wordpress_draft_contract["scope"] == "blocked_preview_only"
    assert "wordpress_publish" in wordpress_draft_contract["blocked_outputs"]
    assert (
        "blokuje: publikacja WordPress" in draft_preview["wordpress_draft_handoff_contract_summary"]
    )
    measurement_plan = draft_preview["post_publication_measurement_plan"]
    assert measurement_plan["contract_version"] == "post_publication_measurement_plan_v1"
    assert measurement_plan["scope"] == "blocked_preview_only"
    assert "status" not in measurement_plan
    assert "google_search_console" in measurement_plan["required_source_connectors"]
    assert "google_analytics_4" in measurement_plan["required_source_connectors"]
    assert "content_success_verdict" in measurement_plan["blocked_outputs"]
    assert (
        "blokuje: werdykt skuteczności treści"
        in draft_preview["post_publication_measurement_summary"]
    )
    assert "human_confirm_before_wordpress_write" in draft_preview["draft_blockers"]
    assert (
        "potwierdzenie człowieka przed zapisem WordPress" in draft_preview["draft_blocker_labels"]
    )
    assert (
        "wymaga: wynik decyzji człowieka"
        in draft_preview["draft_readiness_review_contract_summary"]
    )
    assert "required_validation" not in draft_preview
    assert "kontrola duplikacji i kanibalizacji" in draft_preview["required_check_labels"]
    assert draft_preview["apply_status_label"] == "zablokowane do sprawdzenia"
    assert draft_preview["write_status_label"] == "bez zapisu automatycznego"
    assert draft_preview["evidence_ids"]
    assert "blocked_claims" not in draft_preview
    assert "gwarancja pozycji" in draft_preview["blocked_claim_labels"]
    assert content_action["review_gate"]["last_review_outcome"] == "approved_for_prepare"


def test_legacy_raw_audit_summary_is_not_rewritten_with_string_labels() -> None:
    summary = (
        "Blokady: payload_apply_allowed_false, wordpress_write_not_requested, "
        "blocked_claim:ranking guarantee. Sprawdzone: "
        "candidate:content_brief_gsc_bdo, source_type:gsc_query_page."
    )

    cleaned = _operator_audit_summary_text(summary)

    assert cleaned == (
        "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
    )
    assert "payload_apply_allowed_false" not in cleaned
    assert "candidate:" not in cleaned
    assert "blocked_claim:" not in cleaned


def test_operator_audit_summary_hides_raw_audit_identifiers() -> None:
    summary = (
        "Potwierdzenie podglądu zapisane. "
        "Audyt podglądu: audit_act_review_merchant_feed_issues_preview_123abc. "
        "Notatka: Operator potwierdza podgląd. Ten krok nie zapisuje zmian.. "
        "Ten krok nie zapisuje zmian w zewnętrznych systemach."
    )

    cleaned = _operator_audit_summary_text(summary)

    assert "Potwierdzenie podglądu zapisane" in cleaned
    assert "Notatka: Operator potwierdza podgląd" in cleaned
    assert "Audyt podglądu" not in cleaned
    assert "audit_" not in cleaned
    assert ".." not in cleaned
    assert (
        "Ten krok nie zapisuje zmian. Ten krok nie zapisuje zmian w zewnętrznych systemach."
        not in cleaned
    )


def test_action_review_gate_hides_raw_legacy_review_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "raw_review_summary.sqlite3"))

    local_state_store().save_audit_event(
        AuditEvent(
            id="audit_raw_review_summary",
            action_id="act_review_merchant_feed_issues",
            event_type="human_review_approved_for_prepare",
            actor="operator_test",
            summary=(
                "Wynik review: zatwierdzone. Sprawdzone: "
                "candidate:merchant_feed_issue, source_type:merchant_center. "
                "Blockery: payload_apply_allowed_false, blocked_claim:ranking guarantee."
            ),
            evidence_ids=["ev_merchant_issue"],
            details={
                "review_outcome": "approved_for_prepare",
                "reviewed_by": "operator_test",
            },
        )
    )

    response = client.get("/api/actions/act_review_merchant_feed_issues")
    assert response.status_code == 200

    summary = response.json()["review_gate"]["last_review_summary"]

    assert summary == (
        "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
    )
    assert "Wynik review" not in summary
    assert "Blockery" not in summary
    assert "candidate:" not in summary
    assert "source_type:" not in summary
    assert "payload_apply_allowed_false" not in summary
    assert "blocked_claim:" not in summary


def test_action_detail_hides_legacy_apply_audit_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "legacy_apply_audit.sqlite3"))

    local_state_store().save_audit_event(
        AuditEvent(
            id="audit_legacy_apply_summary",
            action_id="act_review_ga4_tracking_quality",
            event_type="apply_confirmation_missing",
            actor="wilq_api",
            summary=(
                "Explicit apply confirmation is required.; "
                "Action must be validated before apply.; "
                "Action mode must be apply before external execution."
            ),
            evidence_ids=["ev_refresh_refresh_google_analytics_4_action_test"],
        )
    )

    response = client.get("/api/actions/act_review_ga4_tracking_quality")
    assert response.status_code == 200

    serialized = json.dumps(response.json(), ensure_ascii=False)
    assert (
        "Historyczny ślad bezpieczeństwa. Nie zapisano zmian w zewnętrznych systemach."
        in serialized
    )
    assert "Zapis zmian zablokowany" in serialized
    assert "Explicit apply confirmation is required" not in serialized
    assert "Action must be validated before apply" not in serialized
    assert "Action mode must be apply before external execution" not in serialized


def test_google_ads_business_context_action_is_review_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert ADS_BUSINESS_CONTEXT_ACTION_ID in actions
    assert "act_configure_google_ads_env" not in actions
    legacy_action_response = client.get("/api/actions/act_configure_google_ads_env")
    assert legacy_action_response.status_code == 404

    action_response = client.get(f"/api/actions/{ADS_BUSINESS_CONTEXT_ACTION_ID}")
    assert action_response.status_code == 200
    action = action_response.json()
    serialized = json.dumps(action)
    assert action["title"] == "Uzupełnij kontekst biznesowy Google Ads"
    assert action["mode"] == "prepare"
    assert action["risk"] == "low"
    assert action["payload"]["action_type"] == "configure_ads_business_context"
    assert action["payload"]["mode"] == "prepare_only"
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False
    assert action["payload"]["missing_read_contracts"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert "WILQ_ADS_PROFIT_MARGIN" in action["payload"]["required_env"]
    assert "WILQ_ADS_TARGET_ROAS" in action["payload"]["alternative_env"]["target_roas_or_cpa"]
    assert (
        "WILQ_ADS_TARGET_CPA_MICROS" in action["payload"]["alternative_env"]["target_roas_or_cpa"]
    )
    assert "GOOGLE_ADS_REFRESH_TOKEN" not in serialized
    assert "client_secret" not in serialized

    validate_response = client.post(f"/api/actions/{ADS_BUSINESS_CONTEXT_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    validation = validate_response.json()
    assert validation["valid"] is True
    assert validation["errors"] == []

    apply_response = client.post(f"/api/actions/{ADS_BUSINESS_CONTEXT_ACTION_ID}/apply")
    assert apply_response.status_code == 409
    apply_detail = apply_response.json()["detail"]
    assert apply_detail["status"] == "blocked"
    assert apply_detail["applied"] is False
    assert apply_detail["audit_event"]["event_type"] == "apply_confirmation_missing"


def test_google_ads_business_context_allows_empty_preliminary_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_ADS_PROFIT_MARGIN", "0.35")
    monkeypatch.setenv("WILQ_ADS_BUSINESS_GOAL", "lead quality review")
    monkeypatch.setenv("WILQ_ADS_BUDGET_GOAL", "protect current monthly budget")
    monkeypatch.setenv("WILQ_ADS_TARGET_ROAS", "")
    monkeypatch.setenv("WILQ_ADS_TARGET_CPA_MICROS", "")

    response = client.get("/api/ads/diagnostics")

    assert response.status_code == 200
    payload = response.json()
    business_context_contract = payload["business_context_read_contract"]
    assert business_context_contract["status"] == "ready"
    assert business_context_contract["status_label"] == "wstępny"
    assert business_context_contract["profit_margin"] == 0.35
    assert business_context_contract["business_goal"] == "lead quality review"
    assert business_context_contract["budget_goal"] == "protect current monthly budget"
    assert business_context_contract["target_roas"] is None
    assert business_context_contract["target_cpa_micros"] is None
    assert business_context_contract["allowed_metrics"] == [
        "profit_margin",
        "business_goal",
        "human_budget_goal",
    ]
    assert business_context_contract["business_policy_ids"] == [
        "use_margin_as_context_not_profitability_verdict",
        "align_campaign_review_to_business_goal",
        "honor_human_budget_goal_before_budget_changes",
        "block_target_verdict_until_roas_or_cpa_confirmed",
        "block_target_verdict_until_strategy_review_approved",
    ]
    assert (
        business_context_contract["target_interpretation"]["interpretation_contract"]
        == "ads_business_target_interpretation_v1"
    )
    assert business_context_contract["target_interpretation"]["status"] == "preliminary"
    assert business_context_contract["target_interpretation"]["status_label"] == "wstępne"
    assert (
        "campaign_review_context"
        in business_context_contract["target_interpretation"]["allowed_uses"]
    )
    assert (
        "kontekst oceny kampanii"
        in business_context_contract["target_interpretation"]["allowed_use_labels"]
    )
    assert (
        "target_kpi_verdict" in business_context_contract["target_interpretation"]["blocked_uses"]
    )
    assert (
        "ocena wskaźników względem celu"
        in business_context_contract["target_interpretation"]["blocked_use_labels"]
    )
    assert business_context_contract["target_interpretation"]["missing_requirements"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert business_context_contract["target_interpretation"]["missing_requirement_labels"] == [
        "docelowy zwrot z reklam albo koszt pozyskania celu",
        "ocena strategii przez człowieka",
    ]
    assert (
        "ocena strategii przez człowieka"
        in business_context_contract["target_interpretation"]["required_validation_labels"]
    )
    assert business_context_contract["target_interpretation"]["action_ids"] == [
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]
    assert business_context_contract["target_interpretation"]["apply_allowed"] is False
    assert business_context_contract["target_interpretation"]["destructive"] is False
    strategy_readiness = business_context_contract["strategy_review_readiness_contract"]
    assert strategy_readiness["id"] == "ads_strategy_review_readiness_contract"
    assert strategy_readiness["status"] == "blocked"
    assert strategy_readiness["status_label"] == "zablokowane"
    assert strategy_readiness["latest_review_status"] == "missing"
    assert strategy_readiness["latest_review_status_label"] == ("ocena strategii niepotwierdzona")
    assert strategy_readiness["latest_review_outcome"] is None
    assert strategy_readiness["apply_allowed"] is False
    assert strategy_readiness["action_ids"] == [ADS_STRATEGY_REVIEW_ACTION_ID]
    assert strategy_readiness["current_context"]["profit_margin"] == 0.35
    assert strategy_readiness["current_context"]["business_goal"] == "lead quality review"
    assert strategy_readiness["current_context"]["budget_goal"] == (
        "protect current monthly budget"
    )
    assert strategy_readiness["current_context"]["target_roas"] is None
    assert strategy_readiness["current_context"]["target_cpa_micros"] is None
    assert strategy_readiness["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert strategy_readiness["missing_read_contract_labels"] == [
        "docelowy zwrot z reklam albo koszt pozyskania celu",
        "ocena strategii przez człowieka",
    ]
    assert "human_strategy_review" in strategy_readiness["required_validation"]
    assert "ocena strategii przez człowieka" in strategy_readiness["required_validation_labels"]
    assert "ocena opłacalności" in strategy_readiness["blocked_claims"]
    assert "ocena opłacalności" in strategy_readiness["blocked_claim_labels"]
    assert business_context_contract["operator_review_gates"] == [
        "human_strategy_review",
        "review_profit_margin_model",
        "review_business_goal",
        "review_human_budget_goal",
        "confirm_target_roas_or_cpa",
    ]
    assert business_context_contract["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert "wstępny lokalny kontekst" in business_context_contract["summary"]
    assert "ocena celu pozostaje zablokowana" in business_context_contract["next_step"]

    business_context_section = next(
        section for section in payload["sections"] if section["id"] == "ads_business_context"
    )
    assert business_context_section["status"] == "ready"
    assert business_context_section["action_ids"] == [
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]

    business_context_decision = next(
        decision
        for decision in payload["decision_queue"]
        if decision["id"] == "ads_review_business_context"
    )
    assert business_context_decision["status"] == "ready"
    assert business_context_decision["start_here_summary"]
    assert business_context_decision["measurement_plan"]
    assert "opłacalnym" in business_context_decision["start_here_summary"]
    assert "okna pomiarowego" in business_context_decision["measurement_plan"]
    assert business_context_decision["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert business_context_decision["metric_tiles"] == {
        "braki": 2,
        "blokady": 6,
        "ustawione pola": 3,
        "warunki sprawdzenia": 5,
        "polityki": 5,
    }
    assert (
        business_context_decision["operator_review_gates"]
        == (business_context_contract["operator_review_gates"])
    )
    assert business_context_decision["action_ids"] == [
        ADS_TARGET_CONFIRMATION_ACTION_ID,
        ADS_STRATEGY_REVIEW_ACTION_ID,
    ]

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert ADS_BUSINESS_CONTEXT_ACTION_ID not in actions
    assert ADS_TARGET_CONFIRMATION_ACTION_ID in actions
    assert ADS_STRATEGY_REVIEW_ACTION_ID in actions

    action_response = client.get(f"/api/actions/{ADS_TARGET_CONFIRMATION_ACTION_ID}")
    assert action_response.status_code == 200
    action = action_response.json()
    assert action["title"] == "Potwierdź docelowy zwrot z reklam albo koszt pozyskania celu dla Ads"
    assert action["mode"] == "prepare"
    assert action["payload"]["action_type"] == "confirm_ads_target_guardrails"
    assert action["payload"]["mode"] == "prepare_only"
    assert action["payload"]["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert action["payload"]["current_context"]["profit_margin"] == 0.35
    assert action["payload"]["current_context"]["business_goal"] == "lead quality review"
    assert action["payload"]["current_context"]["budget_goal"] == "protect current monthly budget"
    assert action["payload"]["current_context"]["target_roas"] is None
    assert action["payload"]["current_context"]["target_cpa_micros"] is None
    assert action["payload"]["target_env_options"]["target_roas_or_cpa"] == [
        "WILQ_ADS_TARGET_ROAS",
        "WILQ_ADS_TARGET_CPA_MICROS",
    ]
    assert action["payload"]["target_env_options"]["target_roas_or_cpa_labels"] == [
        "docelowy zwrot z reklam",
        "docelowy koszt pozyskania celu",
    ]
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False
    assert action["preview_cards"]
    target_preview_card = action["preview_cards"][0]
    assert target_preview_card["kind"] == "google_ads_target_guardrail_review"
    assert target_preview_card["title_label"] == "Cel Ads do potwierdzenia"
    target_preview_rows = {row["label"]: row["value"] for row in target_preview_card["rows"]}
    assert target_preview_rows["Marża"] == "35%"
    assert target_preview_rows["Cel biznesowy"] == "lead quality review"
    assert target_preview_rows["Cel budżetu"] == "protect current monthly budget"
    assert (
        target_preview_rows["Docelowy zwrot z reklam"]
        == "nie ustawiono; WILQ nie ocenia opłacalności Ads"
    )
    assert (
        target_preview_rows["Docelowy koszt pozyskania celu"]
        == "nie ustawiono; WILQ nie ocenia kosztu celu"
    )
    assert target_preview_rows["Ustawione pola"] == "3 pola ustawione lokalnie"
    target_marketer_card_text = str(
        {
            key: target_preview_card[key]
            for key in ("title_label", "subtitle_label", "status_label", "rows")
        }
    )
    assert "confirm_ads_target_guardrails" not in target_marketer_card_text
    assert "target_roas_or_cpa" not in target_marketer_card_text
    assert "WILQ_ADS_TARGET_ROAS" not in target_marketer_card_text
    assert "WILQ_ADS_TARGET_CPA_MICROS" not in target_marketer_card_text

    validate_response = client.post(f"/api/actions/{ADS_TARGET_CONFIRMATION_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    strategy_response = client.get(f"/api/actions/{ADS_STRATEGY_REVIEW_ACTION_ID}")
    assert strategy_response.status_code == 200
    strategy_action = strategy_response.json()
    assert strategy_action["payload"]["action_type"] == "record_ads_strategy_review"
    assert strategy_action["payload"]["apply_allowed"] is False
    assert strategy_action["payload"]["destructive"] is False
    assert strategy_action["preview_cards"]
    strategy_preview_card = strategy_action["preview_cards"][0]
    assert strategy_preview_card["kind"] == "google_ads_strategy_review"
    assert strategy_preview_card["title_label"] == "Ocena strategii Ads do zapisania"
    strategy_preview_rows = {row["label"]: row["value"] for row in strategy_preview_card["rows"]}
    assert strategy_preview_rows["Marża"] == "35%"
    assert strategy_preview_rows["Ostatni przegląd strategii"] == (
        "przegląd strategii nie jest zapisany"
    )
    strategy_marketer_card_text = str(
        {
            key: strategy_preview_card[key]
            for key in ("title_label", "subtitle_label", "status_label", "rows")
        }
    )
    assert "record_ads_strategy_review" not in strategy_marketer_card_text
    assert "human_strategy_review" not in strategy_marketer_card_text
    assert "WILQ_ADS_PROFIT_MARGIN" not in strategy_marketer_card_text
    strategy_validate_response = client.post(
        f"/api/actions/{ADS_STRATEGY_REVIEW_ACTION_ID}/validate"
    )
    assert strategy_validate_response.status_code == 200
    assert strategy_validate_response.json()["valid"] is True


def test_google_ads_target_guardrail_confirmation_persists_local_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_ADS_PROFIT_MARGIN", "0.35")
    monkeypatch.setenv("WILQ_ADS_BUSINESS_GOAL", "lead quality review")
    monkeypatch.setenv("WILQ_ADS_BUDGET_GOAL", "protect current monthly budget")
    monkeypatch.delenv("WILQ_ADS_TARGET_ROAS", raising=False)
    monkeypatch.delenv("WILQ_ADS_TARGET_CPA_MICROS", raising=False)

    before_response = client.get("/api/ads/diagnostics")
    assert before_response.status_code == 200
    before_payload = before_response.json()
    assert before_payload["business_context_read_contract"]["missing_read_contracts"] == [
        "target_roas_or_cpa",
        "human_strategy_review",
    ]
    assert ADS_TARGET_CONFIRMATION_ACTION_ID in before_payload["action_ids"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID in before_payload["action_ids"]

    confirm_response = client.post(
        f"/api/actions/{ADS_TARGET_CONFIRMATION_ACTION_ID}/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Potwierdzam roboczy target zwrotu z reklam 4.2 do sprawdzenia kampanii.",
            "target_roas": 4.2,
        },
    )

    assert confirm_response.status_code == 200
    confirmation = confirm_response.json()
    assert confirmation["confirmed"] is True
    assert confirmation["status"] == "confirmed"
    assert confirmation["blockers"] == []
    assert confirmation["audit_event"]["event_type"] == "ads_target_guardrail_confirmed"
    assert "docelowy zwrot z reklam: 4.2" in confirmation["audit_event"]["summary"]
    assert "target_roas=" not in confirmation["audit_event"]["summary"]
    assert "target_cpa_micros=" not in confirmation["audit_event"]["summary"]
    assert confirmation["review_gate"]["last_confirmation_by"] == "operator_test"
    assert confirmation["review_gate"]["apply_allowed"] is False

    after_response = client.get("/api/ads/diagnostics")
    assert after_response.status_code == 200
    after_payload = after_response.json()
    business_context = after_payload["business_context_read_contract"]
    assert business_context["target_roas"] == 4.2
    assert business_context["target_cpa_micros"] is None
    assert business_context["missing_read_contracts"] == ["human_strategy_review"]
    assert (
        f"local_state:{ADS_TARGET_CONFIRMATION_ACTION_ID}" in business_context["configured_sources"]
    )
    assert business_context["target_interpretation"]["status"] == "preliminary"
    assert "target_roas_review_context" in business_context["target_interpretation"]["allowed_uses"]
    assert "budget_apply" in business_context["target_interpretation"]["blocked_uses"]
    assert ADS_TARGET_CONFIRMATION_ACTION_ID not in after_payload["action_ids"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID in after_payload["action_ids"]

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    action_ids = {action["id"] for action in actions_response.json()}
    assert ADS_TARGET_CONFIRMATION_ACTION_ID not in action_ids
    assert ADS_STRATEGY_REVIEW_ACTION_ID in action_ids

    audit_response = client.get(f"/api/audit/events?action_id={ADS_TARGET_CONFIRMATION_ACTION_ID}")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "ads_target_guardrail_confirmed"
    assert "docelowy zwrot z reklam: 4.2" in audit_response.json()[0]["summary"]
    assert "target_roas=" not in audit_response.json()[0]["summary"]

    strategy_review_response = client.post(
        f"/api/actions/{ADS_STRATEGY_REVIEW_ACTION_ID}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "operator_test",
            "notes": "Strategia Ads zatwierdzona do dalszego sprawdzenia bez zapisu zmian.",
            "checked_items": [
                "review_profit_margin_model",
                "review_business_goal",
                "review_target_fit",
            ],
            "blockers": ["apply nadal zablokowany"],
        },
    )
    assert strategy_review_response.status_code == 200
    strategy_review = strategy_review_response.json()
    assert strategy_review["status"] == "recorded"
    assert strategy_review["audit_event"]["event_type"] == "human_review_approved_for_prepare"

    final_response = client.get("/api/ads/diagnostics")
    assert final_response.status_code == 200
    final_payload = final_response.json()
    final_business_context = final_payload["business_context_read_contract"]
    assert final_business_context["missing_read_contracts"] == []
    assert final_business_context["strategy_review_status"] == "approved_for_prepare"
    assert final_business_context["strategy_reviewed_by"] == "operator_test"
    assert (
        f"local_state:{ADS_STRATEGY_REVIEW_ACTION_ID}"
        in final_business_context["configured_sources"]
    )
    assert final_business_context["target_interpretation"]["status"] == "ready"
    assert "target_roas_review" in final_business_context["target_interpretation"]["allowed_uses"]
    assert ADS_STRATEGY_REVIEW_ACTION_ID not in final_payload["action_ids"]


def test_google_ads_target_guardrail_confirmation_summary_uses_operator_labels(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    clear_google_ads_env(monkeypatch)
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_ADS_PROFIT_MARGIN", "0.35")
    monkeypatch.setenv("WILQ_ADS_BUSINESS_GOAL", "lead quality review")
    monkeypatch.setenv("WILQ_ADS_BUDGET_GOAL", "protect current monthly budget")
    monkeypatch.delenv("WILQ_ADS_TARGET_ROAS", raising=False)
    monkeypatch.delenv("WILQ_ADS_TARGET_CPA_MICROS", raising=False)

    diagnostics_response = client.get("/api/ads/diagnostics")
    assert diagnostics_response.status_code == 200
    assert ADS_TARGET_CONFIRMATION_ACTION_ID in diagnostics_response.json()["action_ids"]

    confirm_response = client.post(
        f"/api/actions/{ADS_TARGET_CONFIRMATION_ACTION_ID}/confirm",
        json={
            "confirmed_by": "operator_test",
            "notes": "Brakuje wybranego celu Ads.",
        },
    )

    assert confirm_response.status_code == 200
    confirmation = confirm_response.json()
    assert confirmation["confirmed"] is False
    assert confirmation["status"] == "blocked"
    assert confirmation["blockers"] == ["target_roas_or_cpa_required"]
    assert confirmation["blocker_labels"] == [
        "podaj docelowy zwrot z reklam albo koszt pozyskania celu"
    ]
    assert "target_roas_or_cpa_required" not in confirmation["audit_event"]["summary"]
    assert "target_roas_or_cpa" not in confirmation["audit_event"]["summary"]
    assert (
        "podaj docelowy zwrot z reklam albo koszt pozyskania celu"
        in confirmation["audit_event"]["summary"]
    )


def test_google_ads_keyword_planner_access_blocker_action_is_review_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_google_ads_live_review_metric_facts(tmp_path, monkeypatch)
    blocked_run = ConnectorRefreshRun(
        id="refresh_google_ads_keyword_planner_blocked",
        connector_id="google_ads",
        mode=ConnectorRefreshMode.vendor_read,
        status=ConnectorRefreshStatus.completed,
        completed_at=datetime.now(UTC) + timedelta(seconds=1),
        evidence_ids=["ev_refresh_refresh_google_ads_keyword_planner_blocked"],
        external_call_attempted=True,
        vendor_data_collected=True,
        metric_summary={
            "campaign_row_count": 1,
            "search_term_row_count": 1,
            "keyword_planner_status": "blocked",
            "keyword_planner_http_status": 403,
            "keyword_planner_blocker": (
                "api_code=403, api_status=PERMISSION_DENIED, "
                "ads_error=authorizationError.DEVELOPER_TOKEN_NOT_APPROVED"
            ),
            "keyword_planner_seed_term_count": 1,
            "keyword_planner_idea_count": 0,
        },
        summary="Google Ads Keyword Planner access blocked seed.",
    )
    local_state_store().save_connector_refresh_run(blocked_run)

    actions_response = client.get("/api/actions")
    assert actions_response.status_code == 200
    actions = {action["id"]: action for action in actions_response.json()}
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID in actions
    action = actions[KEYWORD_PLANNER_ACCESS_ACTION_ID]
    serialized = json.dumps(action)

    assert action["title"] == "Odblokuj Keyword Planner dla Google Ads"
    assert action["mode"] == "prepare"
    assert action["risk"] == "low"
    assert action["payload"]["action_type"] == "configure_google_ads_keyword_planner_access"
    assert action["payload"]["blocked_api"] == "Keyword Planner"
    assert action["payload"]["blocked_reason"] == (
        "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera"
    )
    assert action["payload"]["apply_allowed"] is False
    assert action["payload"]["destructive"] is False
    assert "rozmiar odbiorców" in action["payload"]["blocked_claims"]
    assert action["preview_cards"]
    preview_card = action["preview_cards"][0]
    assert preview_card["kind"] == "google_ads_keyword_planner_access_review"
    assert preview_card["title_label"] == "Dostęp do Keyword Plannera do odblokowania"
    preview_rows = {row["label"]: row["value"] for row in preview_card["rows"]}
    assert preview_rows["Powód"] == (
        "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera"
    )
    assert "api_code=403" not in str(preview_card)
    assert "DEVELOPER_TOKEN_NOT_APPROVED" not in str(preview_card)
    assert "PERMISSION_DENIED" not in serialized
    assert "DEVELOPER_TOKEN_NOT_APPROVED" not in serialized
    assert "GOOGLE_ADS_REFRESH_TOKEN" not in serialized
    assert "client_secret" not in serialized

    context_response = client.post(
        "/api/codex/context-pack",
        json={"skill": "wilq-ads-doctor"},
    )
    assert context_response.status_code == 200
    keyword_planner_context_action = next(
        action
        for action in context_response.json()["active_action_objects"]
        if action["id"] == KEYWORD_PLANNER_ACCESS_ACTION_ID
    )
    context_text = json.dumps(keyword_planner_context_action, ensure_ascii=False)
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID in context_text
    assert "PERMISSION_DENIED" not in context_text
    assert "DEVELOPER_TOKEN_NOT_APPROVED" not in context_text
    assert "developer token" not in context_text
    assert "forecast" not in context_text
    assert "audience size" not in context_text
    assert "Keyword Planner claims" not in context_text
    assert "token deweloperski nie ma zatwierdzonego dostępu do Keyword Plannera" in context_text

    validate_response = client.post(f"/api/actions/{KEYWORD_PLANNER_ACCESS_ACTION_ID}/validate")
    assert validate_response.status_code == 200
    validation = validate_response.json()
    assert validation["valid"] is True
    assert validation["errors"] == []

    diagnostics_response = client.get("/api/ads/diagnostics")
    assert diagnostics_response.status_code == 200
    diagnostics = diagnostics_response.json()
    keyword_planner_contract = diagnostics["keyword_planner_read_contract"]
    assert keyword_planner_contract["status"] == "blocked"
    assert "keyword_planner_enrichment" in keyword_planner_contract["missing_read_contracts"]
    keyword_planner_section = next(
        section for section in diagnostics["sections"] if section["id"] == "ads_keyword_planner"
    )
    assert keyword_planner_section["status"] == "blocked"
    assert keyword_planner_section["action_ids"] == [KEYWORD_PLANNER_ACCESS_ACTION_ID]
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID in diagnostics["action_ids"]
    sections_by_id = {section["id"]: section for section in diagnostics["sections"]}
    assert sections_by_id["ads_live_data_status"]["action_ids"] == []
    assert sections_by_id["ads_campaign_overview"]["action_ids"] == [
        "act_prepare_ads_campaign_review_queue"
    ]
    assert sections_by_id["ads_search_terms"]["action_ids"] == [
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
    ]
    assert (
        KEYWORD_PLANNER_ACCESS_ACTION_ID not in sections_by_id["ads_live_data_status"]["action_ids"]
    )
    assert (
        KEYWORD_PLANNER_ACCESS_ACTION_ID
        not in sections_by_id["ads_campaign_overview"]["action_ids"]
    )
    assert KEYWORD_PLANNER_ACCESS_ACTION_ID not in sections_by_id["ads_search_terms"]["action_ids"]


def test_metric_backed_prepare_actions_are_evidence_grounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)

    response = client.get("/api/actions")
    assert response.status_code == 200
    actions = {action["id"]: action for action in response.json()}

    expected_actions = {
        "act_review_merchant_feed_issues": {
            "connector": "google_merchant_center",
            "action_type": "merchant_feed_issue",
            "metric_names": {"issue_product_count"},
        },
        "act_review_ga4_tracking_quality": {
            "connector": "google_analytics_4",
            "action_type": "ga4_tracking_gap",
            "metric_names": {"active_users", "sessions"},
        },
        "act_prepare_content_refresh_queue": {
            "connector": "wordpress_ekologus",
            "action_type": "wordpress_content_refresh",
            "metric_names": {"content_object_count", "clicks", "domain_rating"},
        },
        "act_prepare_wordpress_draft_handoff": {
            "connector": "wordpress_ekologus",
            "action_type": "wordpress_draft_handoff",
            "metric_names": {"content_object_count", "clicks", "domain_rating"},
        },
        "act_prepare_linkedin_social_drafts": {
            "connector": "linkedin",
            "action_type": "linkedin_post_candidate",
            "metric_names": {"clicks", "impressions", "issue_product_count"},
        },
        "act_prepare_facebook_social_drafts": {
            "connector": "facebook",
            "action_type": "facebook_post_candidate",
            "metric_names": {"clicks", "impressions", "issue_product_count"},
        },
    }

    for action_id, expected in expected_actions.items():
        action = actions[action_id]
        assert action["mode"] == "prepare"
        assert action["status"] == "needs_validation"
        assert action["connector"] == expected["connector"]
        assert action["payload"]["action_type"] == expected["action_type"]
        assert action["payload"]["mode"] == "prepare_only"
        assert action["payload"]["destructive"] is False
        assert action["review_gate"]["status"] == "pending_validation"
        assert action["review_gate"]["confirmation_required"] is True
        assert action["review_gate"]["apply_allowed"] is False
        assert "action_validation_required" in action["review_gate"]["apply_blockers"]
        assert "payload_apply_allowed_false" in action["review_gate"]["apply_blockers"]
        assert "wymagane sprawdzenie w WILQ" in action["review_gate"]["apply_blocker_labels"]
        assert "podgląd zmian nie pozwala na zapis" in action["review_gate"]["apply_blocker_labels"]
        assert action["review_gate"]["apply_blocker_summary_label"]
        assert action["evidence_ids"]
        for preview_key in (
            "payload_preview",
            "budget_payload_preview",
            "content_brief_preview",
            "wordpress_draft_payload_preview",
        ):
            preview_items = action["payload"].get(preview_key)
            if isinstance(preview_items, dict):
                preview_items = [preview_items]
            if not isinstance(preview_items, list):
                continue
            for preview in preview_items:
                if not isinstance(preview, dict) or not preview.get("required_validation"):
                    continue
                assert preview.get("required_validation_labels"), (
                    action_id,
                    preview_key,
                    preview.get("required_validation"),
                )
                assert not any(
                    "_" in label
                    for label in preview["required_validation_labels"]
                    if isinstance(label, str)
                )
                assert (
                    "warunek techniczny do sprawdzenia" not in preview["required_validation_labels"]
                )
                assert "brak opisu w kontrakcie WILQ" not in preview["required_validation_labels"]
        if action_id.startswith("act_prepare_") and "social_drafts" in action_id:
            assert action["domain"] == "social"
            assert action["payload"]["source_inputs"]
            assert "candidate_inputs" not in action["payload"]
            preview_cards = action["preview_cards"]
            assert preview_cards
            assert {card["kind"] for card in preview_cards} == {"social_draft_input_review"}
            preview_text = json.dumps(
                [
                    {
                        "title_label": card["title_label"],
                        "subtitle_label": card["subtitle_label"],
                        "status_label": card["status_label"],
                        "rows": card["rows"],
                    }
                    for card in preview_cards
                ],
                ensure_ascii=False,
            )
            assert "Google Search Console" in preview_text
            assert "Merchant Center" in preview_text
            assert "kliknięcia" in preview_text
            assert "zgłoszenia problemów" in preview_text
            assert "google_search_console" not in preview_text
            assert "google_merchant_center" not in preview_text
            assert "clicks" not in preview_text
            assert "issue_product_count" not in preview_text
            assert (
                "no_publishing_without_connector_credentials"
                in action["payload"]["draft_constraints"]
            )
            assert (
                "require_social_history_duplicate_review" in action["payload"]["draft_constraints"]
            )
            assert "brak powtórzeń historycznych postów" in action["payload"]["blocked_claims"]
            assert {"ev_connector_linkedin_status", "ev_connector_facebook_status"}.issubset(
                set(action["evidence_ids"])
            )
        if action_id == "act_prepare_content_refresh_queue":
            content_payload = action["payload"]
            assert content_payload["preview_contract"] == "content_brief_preview_v1"
            content_cards = action["preview_cards"]
            assert content_cards
            assert "content_brief_review" in {card["kind"] for card in content_cards}
            if content_payload.get("wordpress_draft_payload_preview"):
                assert "wordpress_draft_payload_review" in {card["kind"] for card in content_cards}
            content_card_text = json.dumps(
                [
                    {
                        "title_label": card["title_label"],
                        "subtitle_label": card["subtitle_label"],
                        "status_label": card["status_label"],
                        "rows": card["rows"],
                    }
                    for card in content_cards
                ],
                ensure_ascii=False,
            )
            assert "Plan treści do sprawdzenia" in content_card_text
            if content_payload.get("wordpress_draft_payload_preview"):
                assert "Szkic WordPress do sprawdzenia" in content_card_text
            assert "URL publiczny" in content_card_text
            assert "content_brief_" not in content_card_text
            assert "content_brief_preview_v1" not in content_card_text
            assert "wordpress_draft_payload_preview_v1" not in content_card_text
            assert "target_site" not in content_card_text
            assert "mapping_review" not in content_card_text
            assert content_payload["apply_allowed"] is False
            assert content_payload["api_mutation_ready"] is False
            assert "target_site_mapping_review_contract" not in content_payload
            url_contract = content_payload["content_url_review_contract"]
            assert url_contract["contract"] == "content_url_preflight_review_v1"
            assert url_contract["scope"] == "review_only"
            assert "confirm_final_canonical_url" in url_contract["allowed_outcomes"]
            assert "potwierdź finalny URL kanoniczny" in url_contract["allowed_outcome_labels"]
            assert "docelowy URL publiczny" in url_contract["required_field_labels"]
            assert "wordpress_publish" in url_contract["blocked_outputs"]
            assert "publikacja WordPress" in url_contract["blocked_output_labels"]
            assert "obietnica braku duplikacji" in url_contract["blocked_output_labels"]
            assert "content_url_preflight_review" in content_payload["required_validation"]
            assert "target_site_mapping_review" not in content_payload["required_validation"]
            assert "content_brief_preview" in content_payload
            assert len(content_payload["content_brief_preview"]) >= 2
            gsc_preview = next(
                item
                for item in content_payload["content_brief_preview"]
                if item["source_type"] == "gsc_query_page"
            )
            assert gsc_preview["mode"] == "refresh"
            assert gsc_preview["wordpress_inventory_match"] == "present"
            assert gsc_preview["metric_snapshot"]["clicks"] == 12
            assert gsc_preview["metric_snapshot"]["impressions"] == 120
            assert gsc_preview["apply_allowed"] is False
            assert "gwarancja pozycji" in gsc_preview["blocked_claims"]
            assert "human_confirm_before_wordpress_write" in gsc_preview["required_validation"]
            ahrefs_preview = next(
                item
                for item in content_payload["content_brief_preview"]
                if item["source_type"] == "ahrefs_gap_review"
            )
            serialized_content_preview = json.dumps(
                content_payload["content_brief_preview"],
                ensure_ascii=False,
            )
        if action_id == "act_prepare_wordpress_draft_handoff":
            wordpress_draft_payload = action["payload"]
            assert wordpress_draft_payload["preview_contract"] == (
                "wordpress_draft_handoff_preview_v1"
            )
            handoff_cards = action["preview_cards"]
            assert handoff_cards
            assert {card["kind"] for card in handoff_cards} == {"wordpress_draft_handoff_review"}
            handoff_card_text = json.dumps(
                [
                    {
                        "title_label": card["title_label"],
                        "subtitle_label": card["subtitle_label"],
                        "status_label": card["status_label"],
                        "rows": card["rows"],
                    }
                    for card in handoff_cards
                ],
                ensure_ascii=False,
            )
            assert "Szkic WordPress do sprawdzenia" in handoff_card_text
            assert "URL publiczny" in handoff_card_text
            assert "URL kanoniczny" in handoff_card_text
            assert "Szkic WordPress" in handoff_card_text
            assert "candidate_id" not in handoff_card_text
            assert "content_brief_" not in handoff_card_text
            assert "wordpress_draft_handoff_preview_v1" not in handoff_card_text
            assert "wordpress_draft_handoff_review" not in handoff_card_text
            assert wordpress_draft_payload["depends_on_action_id"] == (
                "act_prepare_content_refresh_queue"
            )
            assert (
                "content_draft_readiness_review_v1"
                in wordpress_draft_payload["required_input_contracts"]
            )
            assert (
                "post_publication_measurement_plan_v1"
                in wordpress_draft_payload["required_input_contracts"]
            )
            assert wordpress_draft_payload["apply_allowed"] is False
            assert wordpress_draft_payload["api_mutation_ready"] is False
            assert (
                "wordpress_draft_preview_review" in wordpress_draft_payload["required_validation"]
            )
            assert (
                "wordpress_draft_payload_preview"
                not in wordpress_draft_payload["required_validation"]
            )
            assert "wordpress_publish" in wordpress_draft_payload["blocked_claims"]
            assert len(wordpress_draft_payload["payload_preview"]) >= 1
            first_wordpress_draft_preview = wordpress_draft_payload["payload_preview"][0]
            assert first_wordpress_draft_preview["preview_contract"] == (
                "wordpress_draft_handoff_preview_v1"
            )
            assert first_wordpress_draft_preview["operation_type"] == (
                "wordpress_draft_handoff_review"
            )
            assert first_wordpress_draft_preview["apply_allowed"] is False
            assert first_wordpress_draft_preview["api_mutation_ready"] is False
            assert first_wordpress_draft_preview["final_canonical_url"]
            assert "selected_target_url" not in first_wordpress_draft_preview
            assert "mapping_review_status" not in first_wordpress_draft_preview
            assert not any(
                key.startswith("target_site_")
                or key.startswith("mapping_review_")
                or key.startswith("transition_candidate")
                for key in first_wordpress_draft_preview
            )
            wordpress_draft_measurement_plan = first_wordpress_draft_preview[
                "post_publication_measurement_plan"
            ]
            assert (
                wordpress_draft_measurement_plan["contract_version"]
                == "post_publication_measurement_plan_v1"
            )
            assert wordpress_draft_measurement_plan["scope"] == "blocked_preview_only"
            assert (
                "wordpress_ekologus"
                in wordpress_draft_measurement_plan["required_source_connectors"]
            )
            assert "obietnica wzrostu leadów" in wordpress_draft_measurement_plan["blocked_outputs"]
            assert first_wordpress_draft_preview["canonical_gate_status_label"]
            assert first_wordpress_draft_preview["duplicate_gate_status_label"]
            assert (
                "stan przekazania do WordPress: zablokowany do przejścia kontroli szkicu"
                in first_wordpress_draft_preview["wordpress_draft_handoff_summary"]
            )
            assert "status:" not in " ".join(
                [
                    *first_wordpress_draft_preview["wordpress_draft_handoff_summary"],
                    *first_wordpress_draft_preview["post_publication_measurement_summary"],
                ]
            )
            assert (
                first_wordpress_draft_preview["required_next_action_label"]
                == "zapis szkicu WordPress"
            )
            assert (
                "potwierdzenie publicznego URL-a"
                in first_wordpress_draft_preview["required_validation_labels"]
            )
            assert "publikacja WordPress" in first_wordpress_draft_preview["blocked_claim_labels"]
            assert "blokuje: obietnica wzrostu pozycji" in (
                " ".join(first_wordpress_draft_preview["post_publication_measurement_summary"])
            )
            assert ahrefs_preview["mode"] == "review"
            assert ahrefs_preview["topic"] == "audyt środowiskowy"
            assert ahrefs_preview["gsc_demand"] == "unknown"
            assert ahrefs_preview["apply_allowed"] is False
            assert "gsc_demand_check" in ahrefs_preview["required_validation"]
            assert ahrefs_preview["evidence_ids"] == ["ev_refresh_refresh_ahrefs_action_test"]
            assert "cuk.pl" not in serialized_content_preview
        metric_names = {str(metric["name"]) for metric in action["metrics"]}
        assert metric_names.issuperset(expected["metric_names"])
        assert "prepare" in json.dumps(action["payload"])
    serialized = json.dumps(response.json(), ensure_ascii=False)
    assert "active_products=12" not in serialized
    assert "disapproved_products=3" not in serialized
    assert "active_users=20" not in serialized
    assert "sessions=30" not in serialized


@pytest.mark.parametrize(
    ("connector_id", "payload"),
    [
        (
            "google_ads",
            {"action_type": "google_ads_recommendation_review", "connector": "google_ads"},
        ),
        ("google_ads", {"action_type": "campaign_change_review", "connector": "google_ads"}),
        (
            "google_ads",
            {"action_type": "negative_keyword_candidate", "connector": "google_ads"},
        ),
        (
            "google_ads",
            {
                "action_type": "custom_segment_candidate",
                "connector": "google_ads",
                "invented_terms": True,
            },
        ),
        (
            "google_ads",
            {
                "action_type": "google_ads_change_history_impact_review",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {
                "action_type": "google_ads_search_term_ngram_review",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {
                "action_type": "google_ads_demand_gen_readiness_review",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {
                "action_type": "configure_google_ads_keyword_planner_access",
                "connector": "google_ads",
            },
        ),
        (
            "google_ads",
            {"action_type": "configure_ads_business_context", "connector": "google_ads"},
        ),
        (
            "google_ads",
            {"action_type": "confirm_ads_target_guardrails", "connector": "google_ads"},
        ),
        (
            "google_ads",
            {"action_type": "record_ads_strategy_review", "connector": "google_ads"},
        ),
        (
            "google_analytics_4",
            {"action_type": "ga4_tracking_gap", "connector": "google_analytics_4"},
        ),
        ("localo", {"action_type": "local_visibility_task", "connector": "localo"}),
    ],
)
def test_action_payload_validation_errors_are_operator_readable(
    connector_id: str,
    payload: dict[str, Any],
) -> None:
    errors = validate_action_payload(connector_id, payload)
    assert errors
    joined = " ".join(errors)
    forbidden_fragments = [
        "payload",
        "requires",
        "must ",
        "connector=",
        "mode=",
        "apply_allowed",
        "api_mutation_ready",
        "destructive=false",
        "payload_preview",
        "evidence IDs",
        "required_validation",
        "source_connectors",
        "missing_read_contracts",
        "not supported",
        "is only valid",
        "non-destructive",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in joined
