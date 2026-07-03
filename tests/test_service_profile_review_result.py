from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.record_service_profile_review_result import (
    PRIVATE_DECISION_BOOLEAN_FIELDS,
    build_input_example,
    build_promotion_readiness_report,
    build_review_result_report,
    render_markdown,
)
from wilq.content.knowledge.service_profile import content_service_profile_response


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


def test_private_recorder_fields_match_service_profile_review_requirements() -> None:
    profile = content_service_profile_response()
    private_actions = [
        action
        for action in profile.review_actions
        if action.review_scope
        in {
            "private_service_proposal",
            "private_claim_policy_proposal",
            "private_evidence_policy_proposal",
        }
    ]

    assert private_actions
    recorder_fields = set(PRIVATE_DECISION_BOOLEAN_FIELDS)
    for action in private_actions:
        private_required_fields = {
            requirement.field
            for requirement in action.review_requirements
            if requirement.required and requirement.field in recorder_fields
        }
        assert private_required_fields == recorder_fields


def test_service_profile_review_input_example_uses_live_private_requirements() -> None:
    example = build_input_example(
        _live_context(),
        review_type="private_source_proposals",
    )

    assert example["review_type"] == "private_source_proposals"
    assert example["scope_label"] == "prywatne propozycje ekologus-ai"
    assert example["reviewer"] == "<imię reviewera>"
    assert "promotion nadal wymaga osobnego" in example["_instruction"]
    assert len(example["decisions"]) == 1

    decision = example["decisions"][0]
    assert decision["action_id"] == "renamed_private_eko_opieka_review"
    assert decision["target_card_id"] == "ekologus_service_eko_opieka_calendar"
    assert decision["decision"] == "approve|needs_changes|stale|reject"
    assert decision["source_trace_clear"] == "tak|nie"
    assert decision["blocked_claims_reviewed"] == "tak|nie"
    for field in PRIVATE_DECISION_BOOLEAN_FIELDS:
        assert decision[field] == "tak|nie"


def test_service_profile_review_input_example_pins_first_public_review_item() -> None:
    live_context = _live_context()
    profile = live_context["service_profile"]  # type: ignore[index]
    profile["review_action_summary"] = {  # type: ignore[index]
        "first_review_action_id": "service_profile_review_card_ekologus_service_bdo_reporting"
    }
    review_actions = profile["review_actions"]  # type: ignore[index]
    review_actions[:] = [review_actions[1], review_actions[0], review_actions[2]]

    example = build_input_example(
        live_context,
        review_type="public_service_cards",
    )

    decisions = example["decisions"]
    assert decisions[0]["action_id"] == (
        "service_profile_review_card_ekologus_service_bdo_reporting"
    )
    assert decisions[1]["action_id"] == "renamed_public_operat_review"


def test_service_profile_review_input_example_orders_private_policy_before_service() -> None:
    live_context = _live_context()
    profile = live_context["service_profile"]  # type: ignore[index]
    review_actions = profile["review_actions"]  # type: ignore[index]
    review_actions.append(
        {
            "action_id": "renamed_private_legal_policy_review",
            "target_card_id": "ekologus_claim_policy_legal_safety",
            "review_scope": "private_claim_policy_proposal",
            "priority": "high",
            "review_requirements": _private_review_requirements(),
        }
    )
    review_actions.append(
        {
            "action_id": "renamed_private_brand_policy_review",
            "target_card_id": "ekologus_claim_policy_brand_voice",
            "review_scope": "private_claim_policy_proposal",
            "priority": "high",
            "review_requirements": _private_review_requirements(),
        }
    )
    review_actions[2]["priority"] = "medium"

    example = build_input_example(
        live_context,
        review_type="private_source_proposals",
    )

    decisions = example["decisions"]
    assert decisions[0]["action_id"] == "renamed_private_legal_policy_review"
    assert decisions[1]["action_id"] == "renamed_private_brand_policy_review"
    assert decisions[2]["action_id"] == "renamed_private_eko_opieka_review"


def test_service_profile_review_input_example_tracks_new_live_required_field() -> None:
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

    example = build_input_example(
        live_context,
        review_type="private_source_proposals",
    )

    assert (
        example["decisions"][0]["owner_retention_note_confirmed"]  # type: ignore[index]
        == "tak|nie"
    )


def test_service_profile_review_result_records_blocking_decision_with_follow_up() -> None:
    payload = {
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "publiczne karty usług",
        "decisions": [
            {
                "action_id": "renamed_public_operat_review",
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
                "action_id": "renamed_private_eko_opieka_review",
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "data_classes_confirmed": "tak",
                "source_block_refs_confirmed": "tak",
                "freshness_status_confirmed": "tak",
                "audience_scope_confirmed": "tak",
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
    assert report["decisions"][0]["freshness_status_confirmed"] is True
    assert report["decisions"][0]["audience_scope_confirmed"] is True
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
        "reviewed_action_ids": ["renamed_private_eko_opieka_review"],
        "reviewed_target_card_ids": ["ekologus_service_eko_opieka_calendar"],
        "reviewed_required_review_fields": {
            "renamed_private_eko_opieka_review": [
                "action_id",
                "target_card_id",
                "decision",
                "source_trace_clear",
                "blocked_claims_reviewed",
                "notes",
                "data_classes_confirmed",
                "source_block_refs_confirmed",
                "freshness_status_confirmed",
                "audience_scope_confirmed",
                "retention_decision_confirmed",
                "deletion_path_confirmed",
                "eval_gates_confirmed",
            ]
        },
        "private_proposal_promotion_ready": False,
        "reviewed_private_proposal_provenance": {
            "ekologus_service_eko_opieka_calendar": {
                "proposal_id": (
                    "private_proposal_"
                    "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01"
                ),
                "source_id": "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
                "freshness_status": "current",
                "audience": "company_wide",
                "retention_decision": "pending_owner_decision",
                "risk_tier": "medium",
                "support_level": "partial",
                "promotion_allowed": False,
                "redacted": True,
            }
        },
    }

    markdown = render_markdown(report)
    assert "service_profile_private_proposal_review_result_v1" in markdown
    assert "Promotion allowed: nie" in markdown
    assert "retention_decision_confirmed: tak" in markdown
    assert "freshness_status_confirmed: tak" in markdown
    assert "audience_scope_confirmed: tak" in markdown
    assert "Wymagane pola review z live Service Profile" in markdown
    assert "eval_gates_confirmed" in markdown
    assert "Private proposal provenance z live Service Profile" in markdown
    assert "freshness=current" in markdown
    assert "audience=company_wide" in markdown


def test_service_profile_promotion_readiness_blocks_private_without_evidence() -> None:
    payload = _private_eko_opieka_approved_payload()

    report = build_promotion_readiness_report(payload, live_context=_live_context())

    assert report["report_type"] == "service_profile_promotion_readiness_v1"
    assert report["review_ready"] is True
    assert report["promotion_request_ready"] is False
    assert report["promotion_allowed"] is False
    assert report["mutation_allowed"] is False
    assert report["production_depth_unlocked"] is False
    assert report["raw_private_text_included"] is False
    assert "missing_evidence_ids" in report["promotion_blockers"]
    assert "private_retention_not_usable" in report["promotion_blockers"]
    preview = report["promotion_request_preview"][0]
    assert preview["source_connectors"] == ["ekologus_ai_private_source_catalog"]
    assert preview["blocked_claims"]
    assert preview["promotion_ready"] is False
    assert "nie edytuje source_facts.json" in report["safety_note"].lower()


def test_service_profile_promotion_readiness_prepares_complete_private_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _private_eko_opieka_approved_payload()
    live_context = _live_context()
    proposal = live_context["service_profile"]["private_source_proposals"][0]  # type: ignore[index]
    proposal["retention_decision"] = "retain_while_source_approved"
    monkeypatch.setattr(
        "scripts.record_service_profile_review_result.source_fact_by_id",
        lambda: {
            "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01": SimpleNamespace(
                evidence_ids=["ev_private_reviewed_eko_opieka"],
                source_connectors=["ekologus_ai_private_source_catalog"],
                freshness_date="2026-07-01",
                confidence=0.82,
            )
        },
    )

    report = build_promotion_readiness_report(payload, live_context=live_context)

    assert report["review_ready"] is True
    assert report["promotion_request_ready"] is True
    assert report["promotion_allowed"] is False
    assert report["mutation_allowed"] is False
    assert report["production_depth_unlocked"] is False
    assert report["promotion_blockers"] == []
    preview = report["promotion_request_preview"][0]
    assert preview["promotion_ready"] is True
    assert preview["evidence_ids"] == ["ev_private_reviewed_eko_opieka"]
    assert preview["retention_decision"] == "retain_while_source_approved"


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
                "action_id": "renamed_private_eko_opieka_review",
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "data_classes_confirmed": "tak",
                "source_block_refs_confirmed": "tak",
                "freshness_status_confirmed": "tak",
                "audience_scope_confirmed": "tak",
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
                "action_id": "renamed_private_eko_opieka_review",
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "data_classes_confirmed": "tak",
                "source_block_refs_confirmed": "tak",
                "retention_decision_confirmed": "nie",
                "deletion_path_confirmed": "tak",
                "notes": "Brakuje eval gates, świeżości, audience i decyzji retencji.",
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
    assert (
        "czy aktualność prywatnego źródła została potwierdzona musi mieć wartość tak albo nie"
        in message
    )
    assert (
        "czy zakres dostępu/audience prywatnego źródła jest poprawny musi mieć wartość tak albo nie"
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
    assert (
        "action_id service_profile_review_card_ekologus_service_bdo_reporting "
        "należy do review_type public_service_cards"
    ) in message
    assert "Użyj --review-type public_service_cards" in message
    assert "target_card_id nie występuje w live Service Profile" in message


def test_service_profile_review_result_explains_private_action_in_public_mode() -> None:
    payload = {
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "publiczne karty usług",
        "decisions": [
            {
                "action_id": "renamed_private_eko_opieka_review",
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "notes": "To jest prywatna propozycja, nie publiczna karta.",
            }
        ],
    }

    with pytest.raises(RuntimeError) as error:
        build_review_result_report(payload, live_context=_live_context())

    message = str(error.value)
    assert (
        "action_id renamed_private_eko_opieka_review należy do review_type "
        "private_source_proposals"
    ) in message
    assert "Użyj --review-type private_source_proposals" in message
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
                    "review_scope": "public_service_card",
                    "review_requirements": _public_review_requirements(),
                },
                {
                    "action_id": "renamed_public_operat_review",
                    "target_card_id": "ekologus_service_operat_wodnoprawny",
                    "review_scope": "public_service_card",
                    "review_requirements": _public_review_requirements(),
                },
                {
                    "action_id": "renamed_private_eko_opieka_review",
                    "target_card_id": "ekologus_service_eko_opieka_calendar",
                    "review_scope": "private_service_proposal",
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
                    "source_id": "ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01",
                    "target_card_id": "ekologus_service_eko_opieka_calendar",
                    "freshness_status": "current",
                    "audience": "company_wide",
                    "retention_decision": "pending_owner_decision",
                    "risk_tier": "medium",
                    "support_level": "partial",
                    "data_classes": ["service_strategy", "internal_operational"],
                    "source_block_refs": ["KB_001_EKO_OPIEKA"],
                    "deletion_path": [
                        "Usuń albo odrzuć redacted proposal w Service Profile review."
                    ],
                    "eval_case_ids": [
                        "goal_005_private_service_review",
                        "goal_005_service_profile_uat",
                    ],
                    "blocked_claims": [
                        "obiecanie klientowi pełnej zgodności bez audytu i review"
                    ],
                    "promotion_allowed": False,
                    "redacted": True,
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
                            "review_action_id": "renamed_private_eko_opieka_review",
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


def _private_eko_opieka_approved_payload() -> dict[str, object]:
    return {
        "review_type": "private_source_proposals",
        "data_review": "2026-07-02",
        "reviewer": "Wilku",
        "scope_label": "prywatne propozycje ekologus-ai",
        "decisions": [
            {
                "action_id": "renamed_private_eko_opieka_review",
                "target_card_id": "ekologus_service_eko_opieka_calendar",
                "decision": "approve",
                "source_trace_clear": "tak",
                "blocked_claims_reviewed": "tak",
                "data_classes_confirmed": "tak",
                "source_block_refs_confirmed": "tak",
                "freshness_status_confirmed": "tak",
                "audience_scope_confirmed": "tak",
                "retention_decision_confirmed": "tak",
                "deletion_path_confirmed": "tak",
                "eval_gates_confirmed": "tak",
                "notes": "Redacted opis wystarcza do przygotowania readiness preview.",
            }
        ],
    }


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
            "field": "freshness_status_confirmed",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "audience_scope_confirmed",
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
