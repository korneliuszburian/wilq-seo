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
            "blocked_claims": ["ponowne zatwierdzenie produktu", "odzyskany przychód"],
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
    assert packet["route_order"] == [
        "/command-center",
        "/merchant",
        "/content-planner",
        "/ads-doctor",
        "/ga4",
    ]
    assert [route["key"] for route in packet["route_checks"]] == [
        "command_center",
        "merchant",
        "content",
        "ads",
        "ga4",
    ]
    assert "nie jest dowodem wykonanego UAT" in packet["safety_note"]
    assert "Nie odblokowuje publikacji ani zapisu zmian" in packet["safety_note"]
    assert packet["result_template"]["ready_without_developer"] == "<yes|no>"

    content_snapshot = packet["route_checks"][2]["live_snapshot"]
    assert content_snapshot["current_site_match_count"] == 1
    assert content_snapshot["top_decisions"][0]["source_public_url"] == (
        "https://www.ekologus.pl/bdo/"
    )
    assert content_snapshot["top_decisions"][0]["final_canonical_url"] == (
        "https://www.ekologus.pl/bdo/"
    )


def test_marketer_uat_packet_markdown_has_recording_fields() -> None:
    packet = {
        "packet_type": "ekologus_marketer_uat_packet_v1",
        "generated_at": "2026-06-24T21:30:00Z",
        "api_base": "http://127.0.0.1:8000",
        "time_limit_minutes": 15,
        "primary_next_step": "Najpierw otwórz /merchant.",
        "safety_note": "Ten pakiet nie jest dowodem wykonanego UAT.",
        "route_checks": [
            {
                "label": "Command Center",
                "route": "/command-center",
                "operator_task": "Wskaż jedną decyzję.",
                "pass_condition": "Marketer wie, co zrobić.",
                "fail_condition": "Marketer zgaduje.",
                "live_snapshot": {"daily_decisions": []},
                "record_after_session": {
                    "result": "<pass|fail>",
                    "marketer_next_step": "<what marketer says>",
                    "confusion": "<what was unclear>",
                    "tasks_to_create": ["<task if any>"],
                },
            }
        ],
        "final_questions": ["Czy wiesz, co zrobić jako następny krok?"],
        "result_template": {
            "ready_without_developer": "<yes|no>",
            "new_tasks": ["<task from feedback>"],
        },
    }

    markdown = render_markdown(packet)

    assert "# Ekologus Marketer UAT Packet" in markdown
    assert "Live snapshot" in markdown
    assert "Do uzupełnienia po sesji" in markdown
    assert "Czy wiesz, co zrobić jako następny krok?" in markdown
    assert "ready_without_developer" in markdown
