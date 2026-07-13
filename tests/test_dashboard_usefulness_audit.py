from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "dashboard_usefulness_audit.py"
    spec = importlib.util.spec_from_file_location("dashboard_usefulness_audit", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_diagnostic_surface_scores_demo_ready_when_it_has_decisions_and_proof() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "ga4",
        "/ga4",
        "GA4",
        "diagnostic",
        "production",
        "/api/ga4/diagnostics",
        requires_evidence=True,
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
    )
    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "language": "pl-PL",
                "evidence_ids": ["ev_ga4"],
                "source_connectors": ["google_analytics_4"],
                "action_ids": ["act_review_ga4_tracking_quality"],
                "blocked_claims": ["zwrot z reklam"],
                "decision_queue": [
                    {
                        "decision_type": "review_landing_quality",
                        "next_step": "Sprawdź dopasowanie strony wejścia do kampanii.",
                    }
                ],
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "demo_ready"
    assert result["usefulness_score"] == 10
    assert result["sample_evidence_ids"] == ["ev_ga4"]
    assert result["sample_action_ids"] == ["act_review_ga4_tracking_quality"]


def test_production_surface_blocks_when_proof_or_next_step_is_missing() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "content",
        "/content-workflow",
        "Treści",
        "diagnostic",
        "production",
        "/api/content/diagnostics",
        requires_evidence=True,
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
    )
    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "language": "pl-PL",
                "decision_queue": [{"decision_type": "refresh_or_merge"}],
                "action_ids": ["act_prepare_content_refresh_queue"],
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "blocked"
    assert "missing evidence_ids" in result["errors"]
    assert "missing source_connectors" in result["errors"]
    assert "missing safe next step/operator action" in result["errors"]


def test_experimental_surface_caps_at_review_ready_even_with_full_proof() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "demand_gen",
        "/ads-doctor/demand-gen",
        "Demand Gen",
        "diagnostic",
        "experimental",
        "/api/demand-gen/diagnostics",
        requires_evidence=True,
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
        requires_polish_contract=True,
    )
    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "language": "pl-PL",
                "evidence_ids": ["ev_ads"],
                "source_connectors": ["google_ads"],
                "action_ids": ["act_review"],
                "blocked_claims": ["skuteczność kampanii"],
                "decision_queue": [{"next_step": "Przejrzyj jakość materiałów."}],
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "review_ready"
    assert result["usefulness_score"] == 10


def test_social_surface_detects_operator_next_step_and_draft_action_ids() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "social_publisher",
        "/social-publisher",
        "Publikacje social",
        "workflow",
        "experimental",
        "/api/codex/context-pack",
        method="POST",
        request_json={"skill": "wilq-social-publisher"},
        payload_key="social_draft_context",
        requires_evidence=True,
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
    )

    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "social_draft_context": {
                    "source_connectors": ["google_search_console", "wordpress_ekologus"],
                    "evidence_ids": ["ev_social"],
                    "draft_action_ids": ["act_prepare_linkedin_social_drafts"],
                    "blocked_claims": ["brak powtórzeń historycznych postów"],
                    "operator_next_step": (
                        "Zbierz metadata-only historię LinkedIn/Facebook przed claimem "
                        "o braku powtórek."
                    ),
                }
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "review_ready"
    assert result["sample_action_ids"] == ["act_prepare_linkedin_social_drafts"]
    assert result["sample_next_steps"] == [
        "Zbierz metadata-only historię LinkedIn/Facebook przed claimem o braku powtórek."
    ]


def test_surface_specs_include_content_workflow_and_social_publisher() -> None:
    audit = load_module()
    specs_by_id = {surface.surface_id: surface for surface in audit.SURFACES}

    assert specs_by_id["content_workflow"].path == "/content-workflow"
    assert specs_by_id["content_workflow"].endpoint == "/api/content/work-items/snapshot"
    assert specs_by_id["content_workflow"].auxiliary_endpoints == (
        "/api/content/wordpress/authoring-profile",
    )
    assert specs_by_id["social_publisher"].path == "/social-publisher"
    assert specs_by_id["social_publisher"].method == "POST"
    assert specs_by_id["social_publisher"].request_json == {"skill": "wilq-social-publisher"}
    assert specs_by_id["social_publisher"].payload_key == "social_draft_context"


def test_content_workflow_requires_safe_wordpress_authoring_profile() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "content_workflow",
        "/content-workflow",
        "Workflow treści",
        "workflow",
        "production",
        "/api/content/work-items/snapshot",
        auxiliary_endpoints=("/api/content/wordpress/authoring-profile",),
        requires_evidence=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
    )

    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "evidence_ids": ["ev_content"],
                "source_connectors": ["google_search_console"],
                "safe_next_step": "Przejdź przez Claim Ledger i review człowieka.",
                "preflight": {
                    "preflight_verdict": {
                        "blockers": [{"code": "missing_claim_ledger"}]
                    }
                },
            },
            "auxiliary_payloads": {
                "/api/content/wordpress/authoring-profile": safe_authoring_profile()
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "demo_ready"
    assert result["auxiliary_checks"] == [
        {
            "id": "wordpress_authoring_profile",
            "endpoint": "/api/content/wordpress/authoring-profile",
            "status": "ready",
            "summary": "REST=configured, WP-CLI=configured, ACF layouts=1, writes blocked=True",
            "errors": [],
        }
    ]


def test_content_workflow_blocks_when_wordpress_authoring_writes_are_not_safe() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "content_workflow",
        "/content-workflow",
        "Workflow treści",
        "workflow",
        "production",
        "/api/content/work-items/snapshot",
        auxiliary_endpoints=("/api/content/wordpress/authoring-profile",),
        requires_evidence=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
    )
    profile = safe_authoring_profile()
    profile["write_boundary"]["publish_allowed"] = True

    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "evidence_ids": ["ev_content"],
                "source_connectors": ["google_search_console"],
                "safe_next_step": "Przejdź przez Claim Ledger i review człowieka.",
                "preflight": {
                    "preflight_verdict": {
                        "blockers": [{"code": "missing_claim_ledger"}]
                    }
                },
            },
            "auxiliary_payloads": {
                "/api/content/wordpress/authoring-profile": profile
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "blocked"
    assert "wordpress authoring write boundary not false: publish_allowed" in result["errors"]
    assert result["auxiliary_checks"][0]["status"] == "blocked"


def test_blocker_lists_satisfy_blocker_requirement() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "content_workflow",
        "/content-workflow",
        "Workflow treści",
        "workflow",
        "production",
        "/api/content/work-items/snapshot",
        requires_evidence=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
    )

    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "evidence_ids": ["ev_content"],
                "source_connectors": ["google_search_console"],
                "preflight": {
                    "preflight_verdict": {
                        "blockers": [
                            {
                                "code": "missing_claim_ledger",
                                "next_step": "Sprawdź i zatwierdź ryzykowne twierdzenia.",
                            }
                        ]
                    }
                },
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "demo_ready"


def test_action_ids_are_detected_from_singular_review_action_fields() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "service_profile",
        "/service-profile",
        "Service Profile",
        "knowledge",
        "production",
        "/api/content/service-profile",
        requires_evidence=True,
        requires_source_connector=False,
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
    )
    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "evidence_ids": ["ev_content_service_profile_source_facts"],
                "blocked_claims": ["production-depth bez review"],
                "coverage_summary": {
                    "safe_next_step": "Pokaż propozycje Wilkowi przed promocją wiedzy."
                },
                "source_fact_coverage": {
                    "private_review_queue": [
                        {
                            "proposal_id": "private_proposal_abc",
                            "source_id": "ekologus_ai_abc",
                            "data_classes": ["service_strategy"],
                            "source_block_refs": ["KB_001_EKO_OPIEKA"],
                            "retention_decision": "pending_owner_decision",
                            "deletion_path": ["Usuń zredagowaną propozycję."],
                            "eval_case_ids": ["goal_005_private_service_review"],
                            "source_locator_label": "ekologus-ai reviewed handoff",
                            "owner_role": "Wilku",
                            "redacted": True,
                            "source_trace_ready": True,
                        }
                    ]
                },
                "review_actions": [
                    {
                        "action_id": "service_profile_review_private_proposal_abc",
                        "safe_next_step": "Zapisz wynik review po decyzji człowieka.",
                    }
                ],
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "demo_ready"
    assert result["sample_action_ids"] == ["service_profile_review_private_proposal_abc"]
    assert result["private_source_trace"]["ready"] is True
    assert result["private_source_trace"]["trace_ready_count"] == 1


def test_service_profile_blocks_when_private_source_trace_is_missing() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "service_profile",
        "/service-profile",
        "Service Profile",
        "knowledge",
        "production",
        "/api/content/service-profile",
        requires_evidence=True,
        requires_source_connector=False,
        requires_action=True,
        requires_decision=True,
        requires_private_source_trace=True,
        requires_blocker_or_blocked_claim=True,
    )

    result = audit.evaluate_surface(
        spec,
        {
            "payload": {
                "evidence_ids": ["ev_content_service_profile_source_facts"],
                "blocked_claims": ["production-depth bez review"],
                "coverage_summary": {
                    "safe_next_step": "Pokaż propozycje Wilkowi przed promocją wiedzy."
                },
                "source_fact_coverage": {
                    "private_review_queue": [
                        {
                            "proposal_id": "private_proposal_abc",
                            "source_id": "ekologus_ai_abc",
                            "source_block_refs": ["KB_001_EKO_OPIEKA"],
                            "eval_case_ids": ["goal_005_private_service_review"],
                        }
                    ]
                },
                "review_actions": [
                    {
                        "action_id": "service_profile_review_private_proposal_abc",
                        "safe_next_step": "Zapisz wynik review po decyzji człowieka.",
                    }
                ],
            },
            "errors": [],
        },
    )

    assert result["readiness"] == "blocked"
    assert result["private_source_trace"]["ready"] is False
    assert result["private_source_trace"]["trace_ready_count"] == 0
    assert result["errors"] == [
        (
            "private source review item 1 missing trace fields: data_classes, "
            "retention_decision, source_locator_label, owner_role, redacted, "
            "source_trace_ready"
        )
    ]


def test_reference_surface_can_explain_safe_operator_use_without_decision_queue() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "actions",
        "/actions",
        "Akcje",
        "registry",
        "production",
        "/api/actions",
        requires_evidence=False,
        requires_source_connector=False,
        reference_next_step=(
            "Użyj po wybraniu konkretnej akcji z Centrum pracy; to rejestr, "
            "nie kolejka startowa."
        ),
    )

    result = audit.evaluate_surface(
        spec,
        {
            "payload": [
                {
                    "action_id": "act_prepare_content_refresh_queue",
                    "evidence_ids": ["ev_content"],
                }
            ],
            "errors": [],
        },
    )

    assert result["readiness"] == "demo_ready"
    assert result["safe_next_step_count"] == 0
    assert result["sample_next_steps"] == [
        "Użyj po wybraniu konkretnej akcji z Centrum pracy; to rejestr, "
        "nie kolejka startowa."
    ]


def test_knowledge_surface_requires_nonempty_records() -> None:
    audit = load_module()
    spec = audit.SurfaceSpec(
        "knowledge",
        "/knowledge",
        "Baza wiedzy",
        "knowledge",
        "production",
        "/api/knowledge/cards",
        requires_evidence=False,
        requires_source_connector=False,
        requires_records=True,
        requires_lineage=True,
    )

    empty = audit.evaluate_surface(spec, {"payload": [], "errors": []})

    assert empty["readiness"] == "blocked"
    assert empty["record_count"] == 0
    assert "missing records" in empty["errors"]
    assert "missing source lineage" in empty["errors"]

    missing_lineage = audit.evaluate_surface(
        spec,
        {
            "payload": [
                {
                    "id": "card_goal_001_rules",
                    "title": "Bez zmyślonych metryk",
                }
            ],
            "errors": [],
        },
    )

    assert missing_lineage["readiness"] == "blocked"
    assert missing_lineage["record_count"] == 1
    assert missing_lineage["lineage_count"] == 0
    assert "missing source lineage" in missing_lineage["errors"]

    ready = audit.evaluate_surface(
        spec,
        {
            "payload": [
                {
                    "id": "card_goal_001_rules",
                    "title": "Bez zmyślonych metryk",
                    "source_lineage": ["docs/goals/001-goal.md"],
                }
            ],
            "errors": [],
        },
    )

    assert ready["readiness"] == "demo_ready"
    assert ready["record_count"] == 1
    assert ready["lineage_count"] == 1


def test_markdown_report_shows_surface_progress_without_raw_json_dump() -> None:
    audit = load_module()
    report = {
        "api_base": "http://127.0.0.1:8000",
        "surface_count": 1,
        "demo_ready_count": 1,
        "review_ready_count": 0,
        "blocked_count": 0,
        "pass": True,
        "surfaces": [
            {
                "label": "Centrum pracy",
                "path": "/command-center",
                "status": "production",
                "readiness": "demo_ready",
                "usefulness_score": 9,
                "record_count": 1,
                "lineage_count": 1,
                "evidence_count": 2,
                "action_count": 1,
                "decision_count": 3,
                "sample_next_steps": ["Najpierw sprawdź kolejkę działań."],
                "auxiliary_checks": [
                    {
                        "id": "wordpress_authoring_profile",
                        "status": "ready",
                        "summary": (
                            "REST=configured, WP-CLI=configured, "
                            "ACF layouts=21, writes blocked=True"
                        ),
                    }
                ],
                "errors": [],
            }
        ],
    }

    markdown = audit.render_markdown(report)

    assert "| Centrum pracy | `production` | `demo_ready` | 9 | 1 | 1 |" in markdown
    assert "Najpierw sprawdź kolejkę działań." in markdown
    assert "## Kontrole pomocnicze" in markdown
    assert "ACF layouts=21, writes blocked=True" in markdown


def safe_authoring_profile() -> dict[str, object]:
    return {
        "profile_version": "wordpress_authoring_profile_v1",
        "rest_api": {"status": "configured"},
        "wp_cli": {"status": "configured"},
        "acf": {
            "layouts_discovered": True,
            "layouts": [{"name": "podstrona"}],
        },
        "dev_content": {
            "status": "available",
            "page_count": 1,
            "pages": [
                {
                    "title": "BDO dla firm",
                    "section_count": 1,
                    "sections": [{"layout_name": "baner_startowy"}],
                }
            ],
            "blockers": [],
        },
        "blockers": [],
        "write_boundary": {
            "direct_vendor_write_allowed": False,
            "live_write_enabled": False,
            "publish_allowed": False,
            "destructive_update_allowed": False,
            "external_write_attempted": False,
        },
    }


def _readiness_fixture_payload(**extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "evidence_ids": ["ev_fixture"],
        "source_connectors": ["fixture"],
        "action_ids": ["act_fixture"],
        "decision_queue": [{"next_step": "Sprawdź fixture."}],
        "blocked_claims": ["nie obiecuj wyniku"],
        "next_step": "Sprawdź fixture.",
    }
    payload.update(extra)
    return payload


def _readiness_fixture_spec(module: object) -> object:
    return module.SurfaceSpec(
        "fixture",
        "/fixture",
        "Fixture",
        "diagnostic",
        "production",
        "/api/fixture",
        requires_action=True,
        requires_decision=True,
        requires_blocker_or_blocked_claim=True,
    )


def test_semantic_api_blocker_overrides_structural_demo_score() -> None:
    audit = load_module()
    result = audit.evaluate_surface(
        _readiness_fixture_spec(audit),
        {"payload": _readiness_fixture_payload(status="blocked"), "errors": []},
    )

    assert result["usefulness_score"] == 10
    assert result["semantic_readiness"] == "blocked"
    assert result["readiness"] == "blocked"


def test_review_required_production_depth_is_not_demo_ready() -> None:
    audit = load_module()
    result = audit.evaluate_surface(
        _readiness_fixture_spec(audit),
        {
            "payload": _readiness_fixture_payload(
                production_depth_readiness={
                    "status": "source_backed_review_required",
                    "ready_for_daily_content": False,
                }
            ),
            "errors": [],
        },
    )

    assert result["semantic_readiness"] == "review_ready"
    assert result["readiness"] == "review_ready"


def test_ready_surface_remains_demo_ready() -> None:
    audit = load_module()
    result = audit.evaluate_surface(
        _readiness_fixture_spec(audit),
        {"payload": _readiness_fixture_payload(status="ready"), "errors": []},
    )

    assert result["semantic_readiness"] is None
    assert result["readiness"] == "demo_ready"
