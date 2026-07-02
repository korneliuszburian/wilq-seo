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
        "/content-planner",
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
                "errors": [],
            }
        ],
    }

    markdown = audit.render_markdown(report)

    assert "| Centrum pracy | `production` | `demo_ready` | 9 | 1 | 1 |" in markdown
    assert "Najpierw sprawdź kolejkę działań." in markdown
