"""ActionObject and action-safety API contract tests."""

from __future__ import annotations

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
from tests._contract_support.api_client import client
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
from wilq.actions.google_ads.campaign_triage import _campaign_channel_label
from wilq.actions.google_ads.demand_gen import demand_gen_contract_labels
from wilq.actions.service import (
    _ads_recommendation_type_label,
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








