from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests._contract_support.action_candidate_seed import seed_action_candidate_metric_facts
from tests._contract_support.api_client import client
from tests._contract_support.assertions import (
    assert_preview_items_are_operator_view_models,
    preview_card_row_values,
)


def test_action_preview_generates_dry_run_audit_without_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "preview_state.sqlite3"))

    preview_response = client.post(
        "/api/actions/act_review_merchant_feed_issues/preview",
        json={"requested_by": "operator_test", "max_items": 3},
    )

    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["status"] in {"preview_ready", "blocked"}
    assert preview["status_label"] in {"podgląd gotowy", "zablokowany"}
    assert preview["dry_run"] is True
    assert preview["mutation_allowed"] is False
    assert preview["audit_event"]["event_type"] == "action_preview_generated"
    assert preview["audit_event"]["event_type_label"] == "Podgląd zmian wygenerowany"
    assert preview["audit_event"]["actor"] == "operator_test"
    assert preview["preview_items_total"] >= len(preview["preview_items"])
    assert len(preview["preview_items"]) <= 3
    assert preview["preview_cards"]
    assert_preview_items_are_operator_view_models(preview["preview_items"])
    assert preview["review_gate"]["apply_allowed"] is False
    assert preview["review_gate"]["status_label"]
    assert len(preview["blocker_labels"]) == len(preview["blockers"])
    assert "warunek techniczny do sprawdzenia" not in preview["blocker_labels"]
    assert "status=" not in preview["audit_event"]["summary"]
    assert "zapis zmian=" not in preview["audit_event"]["summary"]
    assert "zapis zmian pozostaje zablokowany" in preview["audit_event"]["summary"]

    audit_response = client.get("/api/audit/events?action_id=act_review_merchant_feed_issues")
    assert audit_response.status_code == 200
    assert audit_response.json()[0]["event_type"] == "action_preview_generated"


def test_content_action_preview_exposes_review_only_brief_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_action_candidate_metric_facts(tmp_path, monkeypatch)
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "content_preview_state.sqlite3"))
    preview_response = client.post(
        "/api/actions/act_prepare_content_refresh_queue/preview",
        json={"requested_by": "operator_test", "max_items": 4},
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["preview_contract"] == "content_brief_preview_v1"
    assert preview["dry_run"] is True
    assert preview["mutation_allowed"] is False
    assert preview["status"] == "blocked"
    assert preview["preview_items_total"] >= 2
    assert preview["preview_cards"]
    assert_preview_items_are_operator_view_models(preview["preview_items"])
    serialized_preview_items = json.dumps(preview["preview_items"], ensure_ascii=False)
    assert "source_type" not in serialized_preview_items
    assert "preview_contract" not in serialized_preview_items
    assert "apply_allowed" not in serialized_preview_items
    assert any(
        "odśwież istniejącą treść" in preview_card_row_values(card, "Tryb")
        for card in preview["preview_cards"]
    )
    assert any(
        "kontrola prawna" in ", ".join(preview_card_row_values(card, "Blokady publikacji"))
        for card in preview["preview_cards"]
    )
    assert "action_mode_prepare_only" in preview["blockers"]


def test_change_history_preview_hides_vendor_ids_and_field_enums() -> None:
    from wilq.actions.google_ads.change_history import change_history_preview_cards
    from wilq.schemas import ActionPreviewRowViewModel

    cards = change_history_preview_cards(
        {
            "change_history_preview": [
                {
                    "id": "change_history_preview_1783057185097981_0_9",
                    "change_event_id": "1783057185097981~0~9",
                    "change_date_time": "2026-07-03 07:39:45.097981",
                    "change_resource_type": "AD_GROUP_CRITERION",
                    "resource_change_operation": "CREATE",
                    "changed_field_count": "7",
                    "changed_fields": ["adGroup", "criterionId", "keyword.text"],
                    "required_validation_labels": ["sprawdź historię zmian"],
                    "blocked_claim_labels": ["wpływ zmian"],
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                }
            ]
        },
        preview_row=lambda label, value: ActionPreviewRowViewModel(label=label, value=value),
        string_list=lambda value: [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else [],
        action_gate_labels=lambda values: values,
        blocked_claims=lambda values: values,
        apply_state_label=lambda value: "zapis zmian zablokowany",
        system_readiness_label=lambda value: "system zablokowany przed zapisem",
    )

    assert len(cards) == 1
    rows = {row.label: row.value for row in cards[0].rows}
    assert rows["Zdarzenie"] == "zmiana Google Ads do sprawdzenia"
    assert rows["Pola"] == "7 pól zmiany"
    serialized = str(cards[0].model_dump())
    assert "1783057185097981" not in serialized
    assert "AD_GROUP_CRITERION" not in serialized
    assert "adGroup" not in serialized


def test_demand_gen_preview_keeps_readiness_blockers_in_operator_card() -> None:
    from wilq.actions.google_ads.demand_gen_preview import demand_gen_readiness_preview_cards
    from wilq.schemas import ActionPreviewRowViewModel

    cards = demand_gen_readiness_preview_cards(
        {
            "payload_preview": [
                {
                    "campaign_channel_counts": {"DEMAND_GEN": 2},
                    "campaign_rows_evaluated": 4,
                    "demand_gen_campaign_row_count": 2,
                    "demand_gen_ad_group_ad_row_count": 1,
                    "demand_gen_creative_asset_row_count": 0,
                    "demand_gen_landing_quality_row_count": 0,
                    "missing_read_contract_labels": ["brak odczytu kreacji"],
                    "required_validation_labels": ["sprawdź jakość stron wejścia"],
                    "blocked_claim_labels": ["gotowość trybu Demand Gen"],
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                }
            ]
        },
        preview_row=lambda label, value: ActionPreviewRowViewModel(label=label, value=value),
        string_list=lambda value: [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else [],
        channel_label=lambda value: "Demand Gen" if value == "DEMAND_GEN" else value,
        apply_state_label=lambda value: "zapis zmian zablokowany",
        system_readiness_label=lambda value: "system zablokowany przed zapisem",
    )

    assert len(cards) == 1
    rows = {row.label: row.value for row in cards[0].rows}
    assert rows["Kanały kampanii"] == "Demand Gen: 2"
    assert "brak odczytu kreacji" in rows["Braki"]
    assert "gotowość trybu Demand Gen" in rows["Czego nie wolno twierdzić"]
    assert cards[0].apply_state_label == "zapis zmian zablokowany"


def test_search_term_ngram_preview_keeps_metrics_and_safety_rows() -> None:
    from wilq.actions.google_ads.search_term_ngram_preview import search_term_ngram_preview_cards
    from wilq.schemas import ActionPreviewRowViewModel

    cards = search_term_ngram_preview_cards(
        {
            "ngram_preview": [
                {
                    "ngram": "pompa ciepła",
                    "ngram_size": 2,
                    "source_search_term_count": 3,
                    "sample_search_terms": ["pompa ciepła dom", "pompa ciepła cena"],
                    "clicks": 12,
                    "impressions": 240,
                    "cost_micros": 1250000,
                    "conversions": 0,
                    "missing_read_contract_labels": ["brak kontroli intencji"],
                    "required_validation_labels": ["sprawdź 90 dni"],
                    "blocked_claim_labels": ["marnowanie budżetu"],
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                }
            ]
        },
        preview_row=lambda label, value: ActionPreviewRowViewModel(label=label, value=value),
        string_list=lambda value: [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else [],
        plain_metric_value_label=lambda value: str(value if value is not None else "brak danych"),
        micros_money_label=lambda value: f"{value} mikro",
        apply_state_label=lambda value: "zapis zmian zablokowany",
        system_readiness_label=lambda value: "system zablokowany przed zapisem",
    )

    assert len(cards) == 1
    rows = {row.label: row.value for row in cards[0].rows}
    assert rows["Temat"] == "pompa ciepła"
    assert rows["Kliknięcia"] == "12"
    assert "brak kontroli intencji" in rows["Braki"]
    assert "marnowanie budżetu" in rows["Czego nie wolno twierdzić"]
    assert cards[0].apply_state_label == "zapis zmian zablokowany"


def test_ga4_tracking_preview_keeps_landing_source_and_measurement_blockers() -> None:
    from wilq.actions.ga4.tracking_preview import ga4_tracking_quality_preview_cards
    from wilq.schemas import ActionPreviewRowViewModel

    cards = ga4_tracking_quality_preview_cards(
        {
            "payload_preview": [
                {
                    "landing_page_label": "/uslugi",
                    "source_medium_label": "google / cpc",
                    "campaign_name_label": "Ekologus Search",
                    "metric_snapshot": {"sessions": 14},
                    "metric_snapshot_labels": {"sessions": "sesje"},
                    "tracking_dimension_gap_labels": ["brak strony wejścia"],
                    "required_validation_labels": ["sprawdź konfigurację GA4"],
                    "blocked_claim_labels": ["jakość kampanii"],
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                }
            ]
        },
        preview_row=lambda label, value: ActionPreviewRowViewModel(label=label, value=value),
        string_list=lambda value: [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else [],
        metric_snapshot_rows=lambda snapshot, labels: [
            ActionPreviewRowViewModel(label=str(labels[key]), value=str(snapshot[key]))
            for key in snapshot
            if key in labels
        ],
        apply_state_label=lambda value: "zapis zmian zablokowany",
        system_readiness_label=lambda value: "system zablokowany przed zapisem",
    )

    assert len(cards) == 1
    rows = {row.label: row.value for row in cards[0].rows}
    assert rows["Strona wejścia"] == "/uslugi"
    assert rows["Źródło"] == "google / cpc"
    assert rows["sesje"] == "14"
    assert "brak strony wejścia" in rows["Braki wymiarów"]
    assert "jakość kampanii" in rows["Czego nie wolno twierdzić"]
    assert cards[0].apply_state_label == "zapis zmian zablokowany"


def test_local_visibility_preview_keeps_contracts_and_claim_blockers() -> None:
    from wilq.actions.localo.visibility_preview import local_visibility_preview_cards
    from wilq.schemas import ActionPreviewRowViewModel

    cards = local_visibility_preview_cards(
        {
            "payload_preview": [
                {
                    "metric_snapshot": {"localo_reviews_count": 12},
                    "metric_snapshot_labels": {"localo_reviews_count": "liczba opinii"},
                    "allowed_contract_labels": ["agregat opinii"],
                    "missing_read_contract_labels": ["brak lokalnych rankingów"],
                    "required_validation_labels": ["potwierdź odczyt przez człowieka"],
                    "blocked_claim_labels": ["widoczność konkurencji"],
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                }
            ]
        },
        preview_row=lambda label, value: ActionPreviewRowViewModel(label=label, value=value),
        string_list=lambda value: [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else [],
        metric_snapshot_rows=lambda snapshot, labels, keys: [
            ActionPreviewRowViewModel(label=str(labels[key]), value=str(snapshot[key]))
            for key in keys
            if key in snapshot and key in labels
        ],
        apply_state_label=lambda value: "zapis zmian zablokowany",
        system_readiness_label=lambda value: "system zablokowany przed zapisem",
    )

    assert len(cards) == 1
    rows = {row.label: row.value for row in cards[0].rows}
    assert rows["liczba opinii"] == "12"
    assert rows["Dozwolone odczyty"] == "agregat opinii"
    assert "brak lokalnych rankingów" in rows["Braki"]
    assert "widoczność konkurencji" in rows["Czego nie wolno twierdzić"]
    assert cards[0].apply_state_label == "zapis zmian zablokowany"
