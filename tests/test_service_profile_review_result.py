from __future__ import annotations

import pytest

from scripts.record_service_profile_review_result import (
    build_review_result_report,
    render_markdown,
)


def test_service_profile_review_result_records_approved_review_without_promotion() -> None:
    payload = {
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "publiczne karty usług",
        "decisions": [
            {
                "action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
                "target_card_id": "ekologus_service_bdo_reporting",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "notes": "Źródło publiczne i blokady claimów są jasne.",
            }
        ],
    }

    report = build_review_result_report(payload, live_context=_live_context())

    assert report["report_type"] == "service_profile_public_card_review_result_v1"
    assert report["overall_status"] == "review_ready_for_promotion_request"
    assert report["approved_decision_count"] == 1
    assert report["blocking_decision_count"] == 0
    assert report["promotion_allowed"] is False
    assert "nie ustawia approved_current" in report["safety_note"]
    assert report["live_provenance"] == {
        "api_base": "http://127.0.0.1:8000",
        "service_profile_read_only": True,
        "production_depth_ready": False,
        "live_public_review_action_count": 2,
        "reviewed_action_count": 1,
        "reviewed_action_ids": [
            "service_profile_review_card_ekologus_service_bdo_reporting"
        ],
        "reviewed_target_card_ids": ["ekologus_service_bdo_reporting"],
    }

    markdown = render_markdown(report)
    assert "# Wynik Service Profile review" in markdown
    assert "Promotion allowed: nie" in markdown
    assert "review gotowy do osobnego promotion request" in markdown


def test_service_profile_review_result_records_blocking_decision_with_follow_up() -> None:
    payload = {
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "publiczne karty usług",
        "decisions": [
            {
                "action_id": "service_profile_review_card_ekologus_service_operat_wodnoprawny",
                "target_card_id": "ekologus_service_operat_wodnoprawny",
                "decision": "needs_changes",
                "source_trace_clear": "nie",
                "blocked_claims_reviewed": "tak",
                "notes": "Potrzebny prostszy opis zakresu pozwolenia wodnoprawnego.",
                "follow_up_beads": ["wilq-seo-next: doprecyzować kartę operatu"],
            }
        ],
        "follow_up_beads": ["wilq-seo-next: przejrzeć źródła wodnoprawne"],
    }

    report = build_review_result_report(payload, live_context=_live_context())

    assert report["overall_status"] == "needs_follow_up_before_promotion_request"
    assert report["blocking_decision_count"] == 1
    assert report["follow_up_tasks"] == ["wilq-seo-next: przejrzeć źródła wodnoprawne"]


def test_service_profile_review_result_requires_follow_up_for_blocking_decision() -> None:
    payload = {
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "publiczne karty usług",
        "decisions": [
            {
                "action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
                "target_card_id": "ekologus_service_bdo_reporting",
                "decision": "stale",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "notes": "Źródło wymaga odświeżenia.",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=_live_context())

    assert "Blokujące decyzje review wymagają follow_up_beads" in str(error.value)


def test_service_profile_review_result_rejects_unknown_live_action() -> None:
    payload = {
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "publiczne karty usług",
        "decisions": [
            {
                "action_id": "service_profile_review_card_unknown",
                "target_card_id": "ekologus_service_bdo_reporting",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "notes": "OK.",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=_live_context())

    assert "action_id nie występuje w live Service Profile" in str(error.value)


def test_service_profile_review_result_rejects_target_mismatch_and_placeholders() -> None:
    payload = {
        "data_review": "<YYYY-MM-DD>",
        "reviewer": "Wilku",
        "scope_label": "publiczne karty usług",
        "decisions": [
            {
                "action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
                "target_card_id": "ekologus_service_operat_wodnoprawny",
                "decision": "approve",
                "source_trace_clear": "yes",
                "blocked_claims_reviewed": "tak",
                "notes": "-",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=_live_context())

    message = str(error.value)
    assert "Brak pola albo placeholder: data review" in message
    assert "target_card_id nie pasuje do live action" in message
    assert "czy ślad źródłowy jest czytelny musi mieć wartość tak albo nie" in message
    assert "brak pola albo placeholder: notatki review" in message


def _live_context() -> dict[str, object]:
    return {
        "api_base": "http://127.0.0.1:8000",
        "service_profile": {
            "read_only": True,
            "coverage_summary": {"ready_for_daily_content": False},
            "service_sections": [
                {"card_id": "ekologus_service_bdo_reporting"},
                {"card_id": "ekologus_service_operat_wodnoprawny"},
            ],
            "review_actions": [
                {
                    "action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
                    "target_card_id": "ekologus_service_bdo_reporting",
                },
                {
                    "action_id": (
                        "service_profile_review_card_"
                        "ekologus_service_operat_wodnoprawny"
                    ),
                    "target_card_id": "ekologus_service_operat_wodnoprawny",
                },
                {
                    "action_id": "service_profile_review_private_proposal_example",
                    "target_card_id": "ekologus_service_eko_opieka_calendar",
                },
            ],
        },
    }
