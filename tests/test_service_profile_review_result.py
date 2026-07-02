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
        "live_public_promotion_preview_count": 2,
        "reviewed_action_count": 1,
        "reviewed_action_ids": [
            "service_profile_review_card_ekologus_service_bdo_reporting"
        ],
        "reviewed_target_card_ids": ["ekologus_service_bdo_reporting"],
        "reviewed_required_review_fields": {
            "service_profile_review_card_ekologus_service_bdo_reporting": [
                "action_id",
                "target_card_id",
                "decision",
                "source_trace_clear",
                "blocked_claims_reviewed",
                "notes",
            ]
        },
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


def test_service_profile_review_result_records_private_proposal_review_without_promotion() -> None:
    payload = {
        "review_type": "private_source_proposals",
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "prywatne propozycje ekologus-ai",
        "decisions": [
            {
                "action_id": (
                    "service_profile_review_private_proposal_"
                    "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
                ),
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "data_classes_confirmed": "tak",
                "source_block_refs_confirmed": "tak",
                "retention_decision_confirmed": "tak",
                "deletion_path_confirmed": "tak",
                "eval_gates_confirmed": "tak",
                "notes": "Redacted opis wystarcza do przygotowania osobnego promotion request.",
            }
        ],
    }

    report = build_review_result_report(payload, live_context=_live_context())

    assert report["report_type"] == "service_profile_private_proposal_review_result_v1"
    assert report["overall_status"] == "review_ready_for_promotion_request"
    assert report["approved_decision_count"] == 1
    assert report["blocking_decision_count"] == 0
    assert report["promotion_allowed"] is False
    assert "nie zapisuje raw private text" in report["safety_note"]
    assert report["safe_next_step"].startswith("Przygotuj osobny, audytowany private")
    assert report["decisions"][0]["data_classes_confirmed"] is True
    assert report["decisions"][0]["source_block_refs_confirmed"] is True
    assert report["decisions"][0]["retention_decision_confirmed"] is True
    assert report["decisions"][0]["deletion_path_confirmed"] is True
    assert report["decisions"][0]["eval_gates_confirmed"] is True
    assert report["live_provenance"] == {
        "api_base": "http://127.0.0.1:8000",
        "service_profile_read_only": True,
        "production_depth_ready": False,
        "live_private_review_action_count": 1,
        "live_private_promotion_preview_count": 1,
        "reviewed_action_count": 1,
        "reviewed_action_ids": [
            (
                "service_profile_review_private_proposal_"
                "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
            )
        ],
        "reviewed_target_card_ids": ["ekologus_service_eko_opieka_calendar"],
        "reviewed_required_review_fields": {
            (
                "service_profile_review_private_proposal_"
                "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
            ): [
                "action_id",
                "target_card_id",
                "decision",
                "source_trace_clear",
                "blocked_claims_reviewed",
                "notes",
                "data_classes_confirmed",
                "source_block_refs_confirmed",
                "retention_decision_confirmed",
                "deletion_path_confirmed",
                "eval_gates_confirmed",
            ]
        },
        "private_proposal_promotion_ready": False,
    }

    markdown = render_markdown(report)
    assert "service_profile_private_proposal_review_result_v1" in markdown
    assert "Promotion allowed: nie" in markdown
    assert "retention_decision_confirmed: tak" in markdown
    assert "Wymagane pola review z live Service Profile" in markdown
    assert "eval_gates_confirmed" in markdown


def test_service_profile_review_result_follows_new_live_private_required_field() -> None:
    live_context = _live_context()
    review_actions = live_context["service_profile"]["review_actions"]  # type: ignore[index]
    private_action = review_actions[2]
    private_action["review_requirements"] = [
        *private_action["review_requirements"],
        {
            "field": "owner_retention_note_confirmed",
            "label": "czy owner potwierdził notatkę retencji",
            "requirement_type": "boolean",
            "required": True,
        },
    ]
    payload = {
        "review_type": "private_source_proposals",
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "prywatne propozycje ekologus-ai",
        "decisions": [
            {
                "action_id": (
                    "service_profile_review_private_proposal_"
                    "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
                ),
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "data_classes_confirmed": "tak",
                "source_block_refs_confirmed": "tak",
                "retention_decision_confirmed": "tak",
                "deletion_path_confirmed": "tak",
                "eval_gates_confirmed": "tak",
                "notes": "Stary JSON nie zna nowego wymaganego pola z API.",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=live_context)

    message = str(error.value)
    assert "owner_retention_note_confirmed" in message
    assert "musi mieć wartość tak albo nie" in message


def test_service_profile_review_result_requires_private_governance_checks() -> None:
    payload = {
        "review_type": "private_source_proposals",
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "prywatne propozycje ekologus-ai",
        "decisions": [
            {
                "action_id": (
                    "service_profile_review_private_proposal_"
                    "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
                ),
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "data_classes_confirmed": "tak",
                "source_block_refs_confirmed": "tak",
                "retention_decision_confirmed": "nie",
                "deletion_path_confirmed": "tak",
                "notes": "Brakuje eval gates i decyzji retencji.",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=_live_context())

    message = str(error.value)
    assert (
        "czy eval gates blokujące unsafe claimy są wskazane musi mieć wartość tak albo nie"
        in message
    )
    assert "Blokujące decyzje review wymagają follow_up_beads" in message


def test_service_profile_review_result_rejects_public_action_in_private_mode() -> None:
    payload = {
        "review_type": "private_source_proposals",
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "prywatne propozycje ekologus-ai",
        "decisions": [
            {
                "action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
                "target_card_id": "ekologus_service_bdo_reporting",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "notes": "To jest publiczna karta, nie prywatna propozycja.",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=_live_context())

    message = str(error.value)
    assert "action_id nie występuje w live Service Profile" in message
    assert "target_card_id nie występuje w live Service Profile" in message


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


def test_service_profile_review_result_rejects_approve_missing_promotion_preview() -> None:
    live_context = _live_context()
    assert isinstance(live_context["promotion_actions"], dict)
    live_context["promotion_actions"] = {}
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
                "notes": "OK.",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=live_context)

    assert "action_id nie występuje w live promotion preview" in str(error.value)


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
                    "review_requirements": _public_review_requirements(),
                },
                {
                    "action_id": (
                        "service_profile_review_card_"
                        "ekologus_service_operat_wodnoprawny"
                    ),
                    "target_card_id": "ekologus_service_operat_wodnoprawny",
                    "review_requirements": _public_review_requirements(),
                },
                {
                    "action_id": (
                        "service_profile_review_private_proposal_"
                        "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
                    ),
                    "target_card_id": "ekologus_service_eko_opieka_calendar",
                    "review_requirements": _private_review_requirements(),
                },
            ],
            "private_source_proposal_summary": {"promotion_ready": False},
            "private_source_proposals": [
                {
                    "proposal_id": (
                        "private_proposal_"
                        "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
                    ),
                    "target_card_id": "ekologus_service_eko_opieka_calendar",
                }
            ],
        },
        "promotion_actions": {
            "act_prepare_service_profile_knowledge_promotion": {
                "payload": {
                    "payload_preview": [
                        {
                            "review_action_id": (
                                "service_profile_review_card_"
                                "ekologus_service_bdo_reporting"
                            ),
                            "target_card_id": "ekologus_service_bdo_reporting",
                        },
                        {
                            "review_action_id": (
                                "service_profile_review_card_"
                                "ekologus_service_operat_wodnoprawny"
                            ),
                            "target_card_id": "ekologus_service_operat_wodnoprawny",
                        },
                    ]
                }
            },
            "act_prepare_service_profile_private_proposal_promotion": {
                "payload": {
                    "payload_preview": [
                        {
                            "review_action_id": (
                                "service_profile_review_private_proposal_"
                                "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
                            ),
                            "target_card_id": "ekologus_service_eko_opieka_calendar",
                        }
                    ]
                }
            },
        },
    }


def _public_review_requirements() -> list[dict[str, object]]:
    return [
        {"field": "action_id", "requirement_type": "text", "required": True},
        {"field": "target_card_id", "requirement_type": "text", "required": True},
        {"field": "decision", "requirement_type": "text", "required": True},
        {
            "field": "source_trace_clear",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "blocked_claims_reviewed",
            "requirement_type": "boolean",
            "required": True,
        },
        {"field": "notes", "requirement_type": "text", "required": True},
    ]


def _private_review_requirements() -> list[dict[str, object]]:
    return [
        *_public_review_requirements(),
        {
            "field": "data_classes_confirmed",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "source_block_refs_confirmed",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "retention_decision_confirmed",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "deletion_path_confirmed",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "eval_gates_confirmed",
            "requirement_type": "boolean",
            "required": True,
        },
    ]
