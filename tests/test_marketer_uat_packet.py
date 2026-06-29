from __future__ import annotations

from scripts.export_marketer_uat_packet import (
    build_marketer_uat_packet,
    render_markdown,
)


def test_marketer_uat_packet_covers_core_demo_path_without_claiming_uat() -> None:
    surfaces = {
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
                }
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
                    "id": "content_decision_bdo",
                    "title": "SEO: odśwież BDO",
                    "decision_type": "refresh_or_merge",
                    "source_public_url": "https://www.ekologus.pl/bdo/",
                    "intended_final_url": "https://www.ekologus.pl/bdo/",
                    "final_canonical_url": "https://www.ekologus.pl/bdo/",
                    "preview_url": None,
                    "next_step": "Przygotuj brief odświeżenia na istniejący URL.",
                    "blocked_claims": ["wordpress_publish", "ranking gain"],
                }
            ],
            "blocked_claims": ["wordpress_publish", "ranking gain"],
            "action_ids": ["act_prepare_content_refresh_queue"],
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

    packet = build_marketer_uat_packet(surfaces)

    assert packet["packet_type"] == "ekologus_marketer_uat_packet_v1"
    assert packet["kolejność_widoków"] == [
        "/command-center",
        "/merchant",
        "/content-planner",
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
    assert content_snapshot["najważniejsze_decyzje"][0]["publiczny_url"] == (
        "https://www.ekologus.pl/bdo/"
    )
    assert content_snapshot["najważniejsze_decyzje"][0]["finalny_kanoniczny_url"] == (
        "https://www.ekologus.pl/bdo/"
    )
    assert content_snapshot["najważniejsze_decyzje"][0]["tryb"] == (
        "odświeżenie albo scalenie"
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
    assert "Do uzupełnienia po sesji" in markdown
    assert "Czy wiesz, co zrobić jako następny krok?" in markdown
    assert "gotowe_bez_developera" in markdown
    assert "następny_krok_marketera" in markdown
    assert "Command Center" not in markdown
    assert "- Route:" not in markdown
    assert "- Pass:" not in markdown
    assert "- Fail:" not in markdown
    assert "feedbacku marketera" not in markdown
    assert "marketer_next_step" not in markdown
    assert "what marketer says" not in markdown
