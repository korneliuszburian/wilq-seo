from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

CONTENT_OPERATOR_SKILL_PATH = Path(".agents/skills/wilq-content-operator/SKILL.md")
CONTENT_OPERATOR_OUTPUT_CONTRACT_PATH = Path(
    ".agents/skills/wilq-content-operator/references/output-contract.md"
)
CONTENT_OPERATOR_SMOKE_PATH = Path(
    ".agents/skills/wilq-content-operator/scripts/smoke_skill_contract.py"
)
CONTENT_OPERATOR_UAT_PATH = Path(
    ".agents/skills/wilq-content-operator/scripts/build_uat_packet.py"
)


def load_uat_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "wilq_content_operator_uat_packet",
        CONTENT_OPERATOR_UAT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wilq_content_operator_skill_is_api_orchestrator_not_writer() -> None:
    skill_doc = CONTENT_OPERATOR_SKILL_PATH.read_text(encoding="utf-8")
    output_contract = CONTENT_OPERATOR_OUTPUT_CONTRACT_PATH.read_text(encoding="utf-8")
    smoke_script = CONTENT_OPERATOR_SMOKE_PATH.read_text(encoding="utf-8")
    uat_script = CONTENT_OPERATOR_UAT_PATH.read_text(encoding="utf-8")

    for endpoint in (
        "GET /api/content/work-items/queue",
        "GET /api/content/work-items/{work_item_id}/snapshot",
        "GET /api/content/work-items/{work_item_id}/enrichment",
        "GET /api/content/knowledge-cards",
        "POST /api/content/work-items/structured-draft-runtime",
        "POST /api/content/work-items/quality-review",
        "POST /api/content/work-items/revision-apply",
        "POST /api/content/work-items/wordpress-draft-execution",
        "POST /api/content/work-items/measurement-outcome",
    ):
        assert endpoint in skill_doc

    for phrase in (
        "nie jako autora tekstu",
        "Nie wywołuj OpenAI SDK bezpośrednio",
        "Nie wywołuj WordPress bezpośrednio",
        "Nie ustawiaj ani nie akceptuj `publish_ready=true`",
        "Brak preflightu oznacza brak pisania",
        "Brak measurement window oznacza brak wniosku o sukcesie albo porażce",
    ):
        assert phrase in skill_doc or phrase in output_contract

    for marker in (
        "/api/content/work-items/queue",
        "/api/content/work-items/{work_item_id}/snapshot",
        "/api/content/work-items/{work_item_id}/enrichment",
        "/api/content/knowledge-cards",
        "/api/content/work-items/wordpress-draft-execution",
        "/api/content/work-items/measurement-outcome",
        "publish_ready",
        "publish_allowed",
        "destructive_update_allowed",
        "external_write_attempted",
        "ekologus.dev.proudsite.pl",
        "measured_success",
    ):
        assert marker in smoke_script

    for marker in (
        "uat_tasks",
        "3-5",
        "/api/content/service-profile",
        "Service Profile",
        "public_service_review_actions",
        "private_review_actions",
        "private_policy_review_actions",
        "public service review actions",
        "private policy review actions",
        "Service Profile nie jest production-depth",
        "publiczne karty usług wymagają review Wilka/ownera",
        "promotion_checklist",
        "warunki przed reviewed source fact",
        "private_proposal_details",
        "szczegóły private proposals",
        "klasy danych",
        "source block refs",
        "retencja",
        "ścieżka usunięcia",
        "eval gates",
        "review_result_recorders",
        "wymagania review",
        "sales_brief_trace",
        "ograniczenia wiedzy z dowodami",
        "zablokowany albo niedostępny",
        "service_profile_public_card_review_result_v1",
        "service_profile_private_proposal_review_result_v1",
        "promotion preview rows",
        "Public service review action nie promuje faktu ani karty wiedzy.",
        "Private proposal review action nie promuje faktu ani karty wiedzy.",
        "Dev URL nie jest canonical",
        "WordPress pozostaje draft-only",
        "/api/content/work-items/queue",
        "/api/content/work-items/{work_item_id}/enrichment",
    ):
        assert marker in uat_script


def test_content_operator_uat_packet_summarizes_review_requirements() -> None:
    uat_script = load_uat_script()

    summary = uat_script.review_requirements_summary(
        {
            "review_requirements": [
                {
                    "field": "action_id",
                    "label": "action ID z live Service Profile",
                    "requirement_type": "text",
                    "required": True,
                },
                {
                    "field": "source_trace_clear",
                    "label": "czy ślad źródłowy jest czytelny",
                    "requirement_type": "boolean",
                    "required": True,
                },
                {
                    "field": "follow_up_beads",
                    "label": "follow-up Beads",
                    "requirement_type": "follow_up",
                    "required": False,
                    "blocking_rule": "Wymagane, gdy decision != approve.",
                },
            ]
        }
    )

    assert "wymagane pola: action_id, source_trace_clear" in summary
    assert "follow_up_beads: Wymagane, gdy decision != approve." in summary


def test_content_operator_uat_packet_separates_public_and_private_review_actions(
    monkeypatch: Any,
) -> None:
    uat_script = load_uat_script()
    review_requirements = [
        {
            "field": "action_id",
            "label": "action ID z live Service Profile",
            "requirement_type": "text",
            "required": True,
        },
        {
            "field": "target_card_id",
            "label": "target card ID zgodny z action_id",
            "requirement_type": "text",
            "required": True,
        },
        {
            "field": "decision",
            "label": "decyzja review",
            "requirement_type": "text",
            "required": True,
        },
        {
            "field": "source_trace_clear",
            "label": "czy ślad źródłowy jest czytelny",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "blocked_claims_reviewed",
            "label": "czy claimy zablokowane zostały sprawdzone",
            "requirement_type": "boolean",
            "required": True,
        },
        {
            "field": "notes",
            "label": "notatki review",
            "requirement_type": "text",
            "required": True,
        },
        {
            "field": "follow_up_beads",
            "label": "follow-up Beads",
            "requirement_type": "follow_up",
            "required": False,
            "blocking_rule": "Wymagane, gdy decision != approve.",
        },
    ]

    def fake_request_json(
        api_base: str,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        timeout: int = 180,
    ) -> dict[str, Any]:
        assert api_base == "http://example.test"
        assert method == "GET"
        if path == "/api/actions/act_prepare_service_profile_knowledge_promotion":
            return {
                "id": "act_prepare_service_profile_knowledge_promotion",
                "validation_status": "valid",
                "payload": {
                    "preview_contract": "service_profile_knowledge_promotion_preview_v1",
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                    "payload_preview": [
                        {
                            "review_action_id": (
                                "service_profile_review_card_"
                                "ekologus_service_bdo_reporting"
                            ),
                            "target_card_id": "ekologus_service_bdo_reporting",
                        }
                    ],
                },
            }
        if path == "/api/actions/act_prepare_service_profile_private_proposal_promotion":
            return {
                "id": "act_prepare_service_profile_private_proposal_promotion",
                "validation_status": "valid",
                "payload": {
                    "preview_contract": "private_source_proposal_promotion_preview_v1",
                    "apply_allowed": False,
                    "api_mutation_ready": False,
                    "payload_preview": [
                        {
                            "review_action_id": (
                                "service_profile_review_private_proposal_"
                                "ekologus_ai_eko_opieka_2026_07_01"
                            ),
                            "target_card_id": (
                                "ekologus_service_environmental_consulting_outsourcing"
                            ),
                        },
                        {
                            "review_action_id": (
                                "service_profile_review_private_proposal_"
                                "ekologus_ai_brand_voice_2026_07_01"
                            ),
                            "target_card_id": "ekologus_claim_policy_brand_voice",
                        },
                        {
                            "review_action_id": (
                                "service_profile_review_private_proposal_"
                                "ekologus_ai_evidence_policy_2026_07_02"
                            ),
                            "target_card_id": "ekologus_evidence_policy_source_trace",
                        },
                    ],
                },
            }
        assert path == "/api/content/service-profile"
        return {
            "read_only": True,
            "coverage_summary": {
                "ready_for_daily_content": False,
                "status_label": "production-depth zablokowane",
                "safe_next_step": "Zatwierdź karty usług.",
                "service_card_count": 2,
                "approved_current_count": 0,
                "source_backed_review_required_count": 2,
            },
            "private_source_proposal_summary": {
                "proposal_count": 3,
                "service_proposal_count": 1,
                "claim_policy_proposal_count": 1,
                "evidence_requirement_proposal_count": 1,
                "review_required_count": 3,
                "approved_count": 0,
                "promotion_ready": False,
                "promotion_blocked_reason": "Wymaga review.",
                "promotion_checklist": ["Zatwierdź źródło."],
                "redacted": True,
            },
            "coverage_gaps": [],
            "review_actions": [
                {
                    "action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
                    "mode": "review_request",
                    "review_scope": "public_service_card",
                    "priority": "medium",
                    "decision_options": ["approve", "needs_changes", "stale", "reject"],
                    "review_requirements": review_requirements,
                    "label": "Sprawdź BDO",
                    "reason": "Źródło publiczne wymaga decyzji właściciela.",
                    "blocked_write_claim": "Ta akcja nie promuje faktu ani karty wiedzy.",
                    "required_human_role": "owner",
                    "target_card_id": "ekologus_service_bdo_reporting",
                },
                {
                    "action_id": (
                        "service_profile_review_private_proposal_"
                        "ekologus_ai_eko_opieka_2026_07_01"
                    ),
                    "mode": "review_request",
                    "review_scope": "private_service_proposal",
                    "priority": "medium",
                    "decision_options": ["approve", "needs_changes", "stale", "reject"],
                    "review_requirements": review_requirements,
                    "label": "Sprawdź prywatną propozycję",
                    "reason": "Prywatne źródło wymaga sanitizacji.",
                    "blocked_write_claim": "Ta akcja nie promuje faktu ani karty wiedzy.",
                    "required_human_role": "owner",
                    "target_card_id": "ekologus_service_environmental_consulting_outsourcing",
                },
                {
                    "action_id": (
                        "service_profile_review_private_proposal_"
                        "ekologus_ai_brand_voice_2026_07_01"
                    ),
                    "mode": "review_request",
                    "review_scope": "private_claim_policy_proposal",
                    "priority": "high",
                    "decision_options": ["approve", "needs_changes", "stale", "reject"],
                    "review_requirements": review_requirements,
                    "label": "Sprawdź prywatną politykę claimów",
                    "reason": "Prywatne źródło claim-policy wymaga decyzji.",
                    "blocked_write_claim": "Ta akcja nie promuje faktu ani karty wiedzy.",
                    "required_human_role": "reviewer",
                    "target_card_id": "ekologus_claim_policy_brand_voice",
                },
                {
                    "action_id": (
                        "service_profile_review_private_proposal_"
                        "ekologus_ai_evidence_policy_2026_07_02"
                    ),
                    "mode": "review_request",
                    "review_scope": "private_evidence_policy_proposal",
                    "priority": "high",
                    "decision_options": ["approve", "needs_changes", "stale", "reject"],
                    "review_requirements": review_requirements,
                    "label": "Sprawdź prywatną politykę evidence",
                    "reason": "Prywatne źródło evidence-policy wymaga decyzji.",
                    "blocked_write_claim": "Ta akcja nie promuje faktu ani karty wiedzy.",
                    "required_human_role": "reviewer",
                    "target_card_id": "ekologus_evidence_policy_source_trace",
                },
            ],
            "review_action_summary": {
                "total_count": 4,
                "public_service_review_count": 1,
                "private_review_count": 3,
                "private_service_review_count": 1,
                "private_policy_review_count": 2,
                "review_request_count": 4,
                "prepare_count": 0,
                "safe_next_step": "API-owned review action summary.",
            },
            "private_source_proposals": [
                {
                    "proposal_id": "private_proposal_service",
                    "source_id": "ekologus_ai_service",
                    "source_type": "reviewed_internal",
                    "privacy_class": "redacted_only",
                    "scope": "service",
                    "target_card_id": "ekologus_service_environmental_consulting_outsourcing",
                    "target_card_title": "Doradztwo",
                    "review_status": "review_required",
                    "support_level": "partial",
                    "risk_tier": "medium",
                    "data_classes": ["service_strategy", "internal_operational"],
                    "source_block_refs": ["KB_SERVICE"],
                    "retention_decision": "pending_owner_decision",
                    "deletion_path": ["Usuń albo odrzuć redacted proposal."],
                    "eval_case_ids": ["goal_005_private_service_review"],
                    "confidence_label": "średnia",
                    "blocked_claims": ["gwarancja"],
                    "safe_next_step": "Review.",
                    "promotion_allowed": False,
                    "redacted": True,
                },
                {
                    "proposal_id": "private_proposal_policy",
                    "source_id": "ekologus_ai_policy",
                    "source_type": "reviewed_internal",
                    "privacy_class": "redacted_only",
                    "scope": "claim_policy",
                    "target_card_id": "ekologus_claim_policy_brand_voice",
                    "target_card_title": "Styl marki",
                    "review_status": "review_required",
                    "support_level": "direct",
                    "risk_tier": "high",
                    "data_classes": ["brand_policy", "legal_or_claim_policy"],
                    "source_block_refs": ["KB_POLICY"],
                    "retention_decision": "pending_owner_decision",
                    "deletion_path": ["Usuń albo odrzuć redacted proposal."],
                    "eval_case_ids": ["goal_005_private_claim_policy_review"],
                    "confidence_label": "wysoka",
                    "blocked_claims": ["gwarancja wyniku"],
                    "safe_next_step": "Review policy.",
                    "promotion_allowed": False,
                    "redacted": True,
                },
                {
                    "proposal_id": "private_proposal_evidence_policy",
                    "source_id": "ekologus_ai_evidence_policy",
                    "source_type": "reviewed_internal",
                    "privacy_class": "redacted_only",
                    "scope": "evidence_requirement",
                    "target_card_id": "ekologus_evidence_policy_source_trace",
                    "target_card_title": "Source trace i evidence pack",
                    "review_status": "review_required",
                    "support_level": "direct",
                    "risk_tier": "medium",
                    "data_classes": ["evidence_policy", "internal_operational"],
                    "source_block_refs": ["KB_EVIDENCE"],
                    "retention_decision": "pending_owner_decision",
                    "deletion_path": ["Usuń albo odrzuć redacted proposal."],
                    "eval_case_ids": ["goal_005_private_evidence_policy_review"],
                    "confidence_label": "wysoka",
                    "blocked_claims": ["claim bez source trace"],
                    "safe_next_step": "Review evidence policy.",
                    "promotion_allowed": False,
                    "redacted": True,
                },
            ],
        }

    monkeypatch.setattr(uat_script, "request_json", fake_request_json)

    summary = uat_script.service_profile_uat_summary("http://example.test")

    assert summary["review_action_summary"] == {
        "total_count": 4,
        "public_service_review_count": 1,
        "private_review_count": 3,
        "private_service_review_count": 1,
        "private_policy_review_count": 2,
        "review_request_count": 4,
        "prepare_count": 0,
        "safe_next_step": "API-owned review action summary.",
    }
    assert summary["public_service_review_actions"][0]["target_card_id"] == (
        "ekologus_service_bdo_reporting"
    )
    assert summary["public_service_review_actions"][0]["review_scope"] == (
        "public_service_card"
    )
    assert summary["public_service_review_actions"][0]["priority"] == "medium"
    assert summary["public_service_review_actions"][0]["decision_options"] == [
        "approve",
        "needs_changes",
        "stale",
        "reject",
    ]
    assert summary["public_service_review_actions"][0]["review_requirements"] == (
        review_requirements
    )
    assert summary["private_review_actions"][0]["target_card_id"] == (
        "ekologus_service_environmental_consulting_outsourcing"
    )
    assert summary["private_service_review_actions"][0]["target_card_id"] == (
        "ekologus_service_environmental_consulting_outsourcing"
    )
    assert summary["private_policy_review_actions"][0]["target_card_id"] == (
        "ekologus_claim_policy_brand_voice"
    )
    assert summary["private_policy_review_actions"][0]["review_scope"] == (
        "private_claim_policy_proposal"
    )
    assert summary["private_policy_review_actions"][0]["priority"] == "high"
    assert summary["private_policy_review_actions"][0]["decision_options"] == [
        "approve",
        "needs_changes",
        "stale",
        "reject",
    ]
    assert summary["private_policy_review_actions"][0]["review_requirements"] == (
        review_requirements
    )
    recorders = summary["review_result_recorders"]
    assert recorders["recorder_script"] == "scripts/record_service_profile_review_result.py"
    assert recorders["public_review"]["review_type"] == "public_service_cards"
    assert recorders["public_review"]["promotion_preview"]["preview_row_count"] == 1
    assert recorders["private_review"]["review_type"] == "private_source_proposals"
    assert recorders["private_review"]["promotion_preview"]["preview_row_count"] == 3
    assert recorders["private_review"]["promotion_preview"]["apply_allowed"] is False
    assert {
        "decisions[].data_classes_confirmed",
        "decisions[].source_block_refs_confirmed",
        "decisions[].retention_decision_confirmed",
        "decisions[].deletion_path_confirmed",
        "decisions[].eval_gates_confirmed",
    } <= set(recorders["private_review"]["minimal_payload_required_fields"])
    assert "Nie promuje source facts" in recorders["safety_note"]
    private_summary = summary["private_source_proposals"]
    assert private_summary["service_proposal_count"] == 1
    assert private_summary["claim_policy_proposal_count"] == 1
    assert private_summary["evidence_requirement_proposal_count"] == 1
    details = summary["private_proposal_details"]
    assert details[0]["data_classes"] == ["service_strategy", "internal_operational"]
    assert details[0]["source_block_refs"] == ["KB_SERVICE"]
    assert details[0]["retention_decision"] == "pending_owner_decision"
    assert details[0]["deletion_path"] == ["Usuń albo odrzuć redacted proposal."]
    assert details[0]["eval_case_ids"] == ["goal_005_private_service_review"]


def test_content_operator_uat_packet_item_includes_sales_brief_constraint_evidence(
    monkeypatch: Any,
) -> None:
    uat_script = load_uat_script()

    def fake_request_json(
        api_base: str,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        timeout: int = 180,
    ) -> dict[str, Any]:
        assert api_base == "http://example.test"
        assert method == "GET"
        assert body is None
        if path == "/api/content/work-items/content_work_item_bdo/enrichment":
            return {
                "enrichment": {
                    "status": "ready",
                    "intent_label": "informacyjno-usługowa",
                    "service_fit": "obsługa środowiskowa Ekologus",
                    "buyer_problem": "Firma chce sprawdzić BDO.",
                    "safe_next_step": "Pokaż ograniczenia wiedzy Wilkowi.",
                },
                "blockers": [],
            }
        if path == "/api/content/work-items/content_work_item_bdo/snapshot":
            return {
                "sales_brief": {
                    "sales_brief_result": {
                        "brief": {
                            "signal_quality": {
                                "status": "review_required",
                                "status_label": "sygnał użyteczny, ale wymaga review",
                            },
                            "knowledge_constraints": [
                                {
                                    "card_id": "ekologus_service_bdo_reporting",
                                    "constraint_type": "evidence_requirement",
                                    "label": "BDO wymaga live evidence",
                                    "reason": "Nie rekomenduj bez dowodu i źródła.",
                                    "evidence_ids": [
                                        "ev_content_service_profile_source_facts"
                                    ],
                                }
                            ],
                        },
                        "blockers": [],
                    }
                }
            }
        raise AssertionError(f"Unexpected path: {path}")

    monkeypatch.setattr(uat_script, "request_json", fake_request_json)

    item = uat_script.packet_item(
        "http://example.test",
        {
            "work_item_id": "content_work_item_bdo",
            "title": "BDO dla firm",
            "topic": "BDO dla firm",
            "recommended_mode": "refresh",
            "recommended_mode_label": "odświeżenie",
            "status_label": "do sprawdzenia",
            "reason": "Temat ma popyt i istniejącą treść.",
            "safe_next_step": "Sprawdź źródła przed briefem.",
            "evidence_ids": ["ev_gsc_bdo"],
            "source_connectors": ["google_search_console"],
            "final_canonical_url": "https://ekologus.pl/bdo/",
            "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
            "preflight_status": "brief_allowed",
            "duplicate_canonical_risk_summary": "brak",
            "measurement_readiness": {"label": "pomiar zaplanowany"},
            "blockers": [],
        },
    )

    trace = item["sales_brief_trace"]
    assert trace["signal_quality"]["status_label"] == (
        "sygnał użyteczny, ale wymaga review"
    )
    assert trace["shown_knowledge_constraints"] == [
        {
            "card_id": "ekologus_service_bdo_reporting",
            "constraint_type": "evidence_requirement",
            "label": "BDO wymaga live evidence",
            "reason": "Nie rekomenduj bez dowodu i źródła.",
            "evidence_ids": ["ev_content_service_profile_source_facts"],
        }
    ]


def test_content_operator_uat_packet_renders_blocked_sales_brief_trace() -> None:
    uat_script = load_uat_script()

    lines = uat_script.sales_brief_trace_markdown_lines(
        {
            "status": "missing",
            "blocker": "snapshot nie zawiera sales_brief",
        }
    )

    assert lines == [
        "- Sales Brief: zablokowany albo niedostępny "
        "(snapshot nie zawiera sales_brief)"
    ]
