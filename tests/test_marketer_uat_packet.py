from __future__ import annotations

from copy import deepcopy

from scripts.export_marketer_uat_packet import (
    build_marketer_uat_packet,
    render_markdown,
)

MARKETER_UAT_SURFACES = {
    "command_center": {
        "generated_at": "2026-06-24T21:30:00Z",
        "strict_instruction": "Nie zmyślaj metryk.",
        "primary_next_step": "Najpierw otwórz /merchant.",
        "blocker_count": 2,
        "tactical_item_count": 24,
        "daily_decisions": [
            {
                "id": "decision_review_merchant_feed_issues",
                "title": "Przejrzyj kolejkę problemów Merchant Center",
                "domain": "merchant",
                "route": "/merchant",
                "status": "ready",
                "priority": 10,
                "metric_tiles": {"produkty": 10776},
            }
        ],
    },
    "merchant": {
        "operator_summary": {
            "reported_issue_occurrences": 1343,
            "decision_queue_count": 5,
        },
        "decision_queue": [
            {
                "id": "merchant_issue_unit_pricing",
                "title": "Review unit pricing measure",
                "status": "review",
                "next_step": "Sprawdź atrybut.",
            },
        ],
        "blocked_claims": [
            "ponowne zatwierdzenie produktu",
            "twierdzenie o odzyskanym przychodzie",
        ],
        "action_ids": ["act_review_merchant_feed_issues"],
    },
    "content": {
        "operator_summary": {
            "confirmed_wordpress_count": 1,
            "missing_wordpress_count": 0,
            "current_site_match_count": 1,
            "decision_type_labels": ["odświeżenie albo scalenie"],
        },
        "decision_queue": [
            {
                "id": "content_decision_ahrefs_gap",
                "title": "Ahrefs: zweryfikuj lukę przed planem treści",
                "decision_type_label": "luki Ahrefs do ręcznej oceny",
                "source_public_url": None,
                "intended_final_url": None,
                "final_canonical_url": None,
                "preview_url": None,
                "next_step": "Najpierw wykonaj ręczny cross-check.",
                "blocked_claims": ["ranking gain"],
            },
            {
                "id": "content_decision_bdo",
                "title": "SEO: odśwież BDO",
                "decision_type": "refresh_or_merge",
                "source_public_url": "https://www.ekologus.pl/bdo/",
                "intended_final_url": "https://www.ekologus.pl/bdo/",
                "final_canonical_url": "https://www.ekologus.pl/bdo/",
                "preview_url": None,
                "next_step": "Przygotuj brief odświeżenia na istniejący URL.",
                "blocked_claims": ["wordpress_publish", "ranking gain"],
            },
        ],
        "blocked_claims": ["wordpress_publish", "ranking gain"],
        "action_ids": ["act_prepare_content_refresh_queue"],
    },
    "content_snapshot": {
        "candidate": {
            "decision_id": "content_decision_bdo",
            "title": "SEO: odśwież BDO (5 sygnałów planistycznych)",
            "recommended_mode_label": "odśwież istniejącą treść",
            "source_public_url": "https://www.ekologus.pl/bdo/",
            "intended_final_url": "https://www.ekologus.pl/bdo/",
            "final_canonical_url": "https://www.ekologus.pl/bdo/",
            "preview_url": None,
            "safe_next_step": "Sprawdź dokładny zakres i pięć sygnałów GSC.",
        },
        "planning_workspace": {
            "proposal": {
                "search_demand": {
                    "status": "available",
                    "gsc_query_rows": [
                        {"term": "bdo", "impressions": 7, "clicks": 2},
                        {"term": "bdo firmy", "impressions": 3, "clicks": 0},
                        {"term": "bdo odpady", "impressions": 2, "clicks": 0},
                        {"term": "bdo rejestr", "impressions": 1, "clicks": 0},
                        {"term": "bdo pomoc", "impressions": 1, "clicks": 0},
                    ],
                }
            }
        },
        "service_profile_context": {"status_label": "Kontekst usługi wymaga review"},
    },
    "ads": {
        "operator_summary": {"campaign_count": 3, "blocked_claim_count": 4},
        "decision_queue": [
            {
                "id": "ads_review_campaigns",
                "title": "Review campaigns",
                "status": "review",
            }
        ],
        "blocked_claims": ["ocena kosztu pozyskania celu", "werdykt zwrotu z reklam"],
        "action_ids": ["act_prepare_ads_campaign_review_queue"],
    },
    "ga4": {
        "operator_summary": {"tracking_gap_count": 2},
        "decision_queue": [
            {
                "id": "ga4_not_set",
                "title": "Review braków w pomiarze",
                "decision_type": "fix_measurement",
            }
        ],
        "blocked_claims": ["naprawiony pomiar", "ocena przychodu"],
        "action_ids": ["act_review_ga4_tracking_quality"],
    },
}


def test_marketer_uat_packet_covers_core_demo_path_without_claiming_uat() -> None:

    packet = build_marketer_uat_packet(MARKETER_UAT_SURFACES)

    assert packet["packet_type"] == "ekologus_marketer_uat_packet_v1"
    assert packet["kolejność_widoków"] == [
        "/command-center",
        "/merchant",
        "/content-workflow",
        "/ads-doctor",
        "/ga4",
    ]
    assert [route["klucz"] for route in packet["widoki"]] == [
        "command_center",
        "merchant",
        "content",
        "ads",
        "ga4",
    ]
    assert [route["etykieta"] for route in packet["widoki"]] == [
        "Centrum pracy",
        "Merchant",
        "Treści",
        "Google Ads",
        "GA4",
    ]
    assert "nie jest dowodem wykonanego UAT" in packet["safety_note"]
    assert "Nie odblokowuje publikacji ani zapisu zmian" in packet["safety_note"]
    assert packet["szablon_wyniku"]["gotowe_bez_developera"] == "<tak|nie>"
    serialized = str(packet)
    assert "Command Center" not in serialized
    assert "Content Planner" not in serialized
    assert "Ads Doctor" not in serialized
    assert "feed write" not in serialized
    assert "approval recovery" not in serialized
    assert "publish-ready" not in serialized
    assert "tracking/attribution" not in serialized
    assert "wasted budget" not in serialized
    assert "budget scaling" not in serialized
    assert "audit contract" not in serialized
    assert "optimizer" not in serialized
    assert "dev preview" not in serialized
    assert "decision_type" not in serialized
    assert "marketer_next_step" not in serialized
    assert "what marketer says" not in serialized
    assert "primary_next_step" not in serialized
    assert "route_checks" not in serialized
    assert "operator_task" not in serialized
    assert "record_after_session" not in serialized
    assert "confirmed_wordpress_count" not in serialized

    content_snapshot = packet["widoki"][2]["podgląd_z_wilq"]
    assert content_snapshot["dopasowania_obecnej_strony"] == 1
    assert content_snapshot["najważniejsze_decyzje"][0]["decyzja"] == (
        "Ahrefs: zweryfikuj lukę przed planem treści"
    )
    assert content_snapshot["najważniejsze_decyzje"][0]["publiczny_url"] is None
    assert content_snapshot["najważniejsze_decyzje"][1]["publiczny_url"] == (
        "https://www.ekologus.pl/bdo/"
    )
    assert content_snapshot["najważniejsze_decyzje"][1]["finalny_kanoniczny_url"] == (
        "https://www.ekologus.pl/bdo/"
    )
    assert content_snapshot["najważniejsze_decyzje"][1]["tryb"] == ("odśwież istniejącą treść")
    assert content_snapshot["najważniejsze_decyzje"][1]["decyzja"] == (
        "SEO: odśwież BDO (5 sygnałów planistycznych)"
    )
    assert content_snapshot["najważniejsze_decyzje"][1]["następny_krok"] == (
        "Sprawdź dokładny zakres i pięć sygnałów GSC."
    )
    assert content_snapshot["sygnały_planistyczne_gsc"] == 5
    assert content_snapshot["wyświetlenia_gsc"] == 14
    assert content_snapshot["kliknięcia_gsc"] == 2
    assert content_snapshot["status_wiedzy"] == "Kontekst usługi wymaga review"


def test_content_packet_keeps_selected_snapshot_when_decision_is_beyond_top_five() -> None:
    surfaces = deepcopy(MARKETER_UAT_SURFACES)
    ahrefs, selected = surfaces["content"]["decision_queue"]
    other_decisions = [
        {
            "id": f"content_decision_other_{index}",
            "title": f"Inna decyzja {index}",
            "decision_type_label": "ręczna ocena",
            "next_step": "Sprawdź ręcznie.",
            "blocked_claims": ["ranking gain"],
        }
        for index in range(5)
    ]
    surfaces["content"]["decision_queue"] = [ahrefs, *other_decisions, selected]

    content = _content_preview(build_marketer_uat_packet(surfaces))
    titles = [item["decyzja"] for item in content["najważniejsze_decyzje"]]

    assert len(titles) == 5
    assert titles[0] == "Ahrefs: zweryfikuj lukę przed planem treści"
    assert titles[-1] == "SEO: odśwież BDO (5 sygnałów planistycznych)"


def test_content_packet_reports_missing_exact_demand_as_blocker_not_zero() -> None:
    surfaces = deepcopy(MARKETER_UAT_SURFACES)
    surfaces["content_snapshot"] = {
        "candidate": MARKETER_UAT_SURFACES["content_snapshot"]["candidate"],
        "planning_workspace": {
            "proposal": {
                "search_demand": {
                    "status": "missing",
                    "gsc_query_rows": [],
                    "safe_next_step": "Odśwież GSC; nie interpretuj braku jako zero.",
                }
            }
        },
    }

    content = _content_preview(build_marketer_uat_packet(surfaces))

    assert content["status_popytu_gsc"] == "Odśwież GSC; nie interpretuj braku jako zero."
    assert content["sygnały_planistyczne_gsc"] is None
    assert content["wyświetlenia_gsc"] is None
    assert content["kliknięcia_gsc"] is None


def _content_preview(packet: dict) -> dict:
    return next(
        route["podgląd_z_wilq"] for route in packet["widoki"] if route["klucz"] == "content"
    )


def test_marketer_uat_packet_markdown_has_recording_fields() -> None:
    packet = {
        "packet_type": "ekologus_marketer_uat_packet_v1",
        "generated_at": "2026-06-24T21:30:00Z",
        "api_base": "http://127.0.0.1:8000",
        "limit_minut": 15,
        "następny_krok": "Najpierw otwórz /merchant.",
        "safety_note": "Ten pakiet nie jest dowodem wykonanego UAT.",
        "widoki": [
            {
                "etykieta": "Centrum pracy",
                "widok": "/command-center",
                "zadanie_marketera": "Wskaż jedną decyzję.",
                "warunek_zaliczenia": "Marketer wie, co zrobić.",
                "warunek_niezaliczenia": "Marketer zgaduje.",
                "podgląd_z_wilq": {"decyzje_dnia": []},
                "do_uzupełnienia_po_sesji": {
                    "wynik": "<zaliczone|niezaliczone>",
                    "następny_krok_marketera": "<co marketer mówi>",
                    "niejasność": "<co było niejasne>",
                    "zadania_do_utworzenia": ["<zadanie, jeśli jest potrzebne>"],
                },
            }
        ],
        "pytania_końcowe": ["Czy wiesz, co zrobić jako następny krok?"],
        "szablon_wyniku": {
            "gotowe_bez_developera": "<tak|nie>",
            "nowe_zadania": ["<zadanie z feedbacku>"],
        },
    }

    markdown = render_markdown(packet)

    assert "# Pakiet UAT dla marketera Ekologus" in markdown
    assert "Podgląd z WILQ" in markdown
    assert "Karta odpowiedzi po sesji" in markdown
    assert "Czy wiesz, co zrobić jako następny krok?" in markdown
    assert "Gotowe bez developera: tak / nie" in markdown
    assert "Co marketer mówi, że zrobi dalej" in markdown
    assert "gotowe_bez_developera" not in markdown
    assert "następny_krok_marketera" not in markdown
    assert "zadania_do_utworzenia" not in markdown
    assert "```json" not in markdown
    assert "feed write" not in markdown
    assert "approval recovery" not in markdown
    assert "publish-ready" not in markdown
    assert "Pass:" not in markdown
    assert "Fail:" not in markdown
    assert "Command Center" not in markdown
    assert "- Route:" not in markdown
    assert "- Pass:" not in markdown
    assert "- Fail:" not in markdown
    assert "feedbacku marketera" not in markdown
    assert "marketer_next_step" not in markdown
    assert "what marketer says" not in markdown
