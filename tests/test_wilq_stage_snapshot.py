from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    module_path = scripts_dir / "wilq_stage_snapshot.py"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location("wilq_stage_snapshot", module_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def test_stage_snapshot_summarizes_live_readiness_without_closing_goal() -> None:
    stage = load_module()

    snapshot = stage.build_stage_snapshot_from_reports(
        dashboard_report={
            "surface_count": 15,
            "demo_ready_count": 13,
            "review_ready_count": 2,
            "blocked_count": 0,
            "pass": True,
        },
        skill_report={
            "skill_count": 13,
            "fresh_passing_skill_count": 13,
            "minimum_score": 9,
            "maximum_score": 9,
            "wilku_ready_skill_count": 0,
            "pass": True,
            "rows": [
                {
                    "skill": "wilq-daily-command",
                    "score": 9,
                    "state": "gotowy do review",
                    "remaining_blocker": "Sprawdź pierwszy priorytet w Command Center.",
                }
            ],
        },
        completion_report={
            "status": "blocked_missing_goal_005_uat_proof",
            "missing_input": "goal_005_uat_result_or_owner_defer",
            "next_uat_input": {
                "first_service_profile_review": {
                    "label": "Sprawdź kartę BDO",
                    "target_card_id": "ekologus_service_bdo_reporting",
                    "required_fields": ["źródła danych", "twierdzenia"],
                    "next_step": "Najpierw sprawdź publiczną kartę BDO.",
                }
            },
        },
        reviewer_scorecard_report={
            "scorecard_count": 3,
            "candidate_for_10_count": 2,
            "fulfilled_candidate_count": 1,
            "open_candidate_count": 1,
            "rerun_required_count": 3,
            "failure_count": 0,
            "rows": [
                {
                    "status": "valid",
                    "skill": "wilq-daily-command",
                    "decision": "candidate_for_10",
                    "can_consider_10": "tak",
                    "rerun_eval_required": "tak",
                    "candidate_fulfilled": True,
                    "next_step": "uruchom rerun eval",
                }
            ],
        },
        private_review_example={
            "decisions": [
                {
                    "action_id": (
                        "service_profile_review_private_proposal_"
                        "ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01"
                    ),
                    "target_card_id": "ekologus_claim_policy_legal_safety",
                    "decision": "approve|needs_changes|stale|reject",
                    "notes": "<krótka decyzja>",
                    "source_trace_clear": "tak|nie",
                    "blocked_claims_reviewed": "tak|nie",
                    "data_classes_confirmed": "tak|nie",
                    "source_block_refs_confirmed": "tak|nie",
                }
            ]
        },
        approval_readiness={
            "status": "blocked",
            "status_label": "wniosek o zatwierdzenie zablokowany",
            "can_request_promotion": False,
            "mutation_allowed": False,
            "production_depth_unlocked": False,
            "first_action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
            "first_action_label": (
                "Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa"
            ),
            "checklist": [
                {
                    "code": "public_service_review",
                    "label": "Publiczne karty usług sprawdzone przez człowieka",
                    "blocking": True,
                    "next_step": "Zacznij od pierwszej publicznej karty usługi.",
                },
                {
                    "code": "promotion_request_packet",
                    "label": "Osobny wniosek o zatwierdzenie jest gotowy do przygotowania",
                    "blocking": True,
                    "next_step": "Najpierw zapisz wynik rozmowy review.",
                },
            ],
        },
        api_base="http://127.0.0.1:8000",
    )

    assert snapshot["current_stage"] == "demo/review-ready, ale nie production-ready"
    assert snapshot["live_proof"]["dashboard"]["demo_ready_count"] == 13
    assert snapshot["live_proof"]["skills"]["score_range"] == "9"
    assert snapshot["live_proof"]["skills"]["wilku_ready_skill_count"] == 0
    assert snapshot["live_proof"]["skills"]["nearest_10_blockers"] == [
        {
            "skill": "wilq-daily-command",
            "score": 9,
            "state": "gotowy do review",
            "what_it_proves": "",
            "next_step": "Sprawdź pierwszy priorytet w Command Center.",
            "next_step_truncated": False,
        }
    ]
    assert snapshot["live_proof"]["skills"]["nearest_10_plan"] == [
        {
            "skill": "wilq-daily-command",
            "state": "gotowy do review",
            "packet_command": (
                "rtk uv run python scripts/skill_tuning_packet.py "
                "--skill wilq-daily-command"
            ),
            "test": (
                "wykonaj wskazany ekran/workflow z odpowiedzi skilla i oceń, czy "
                "marketer w 30 sekund wie, co kliknąć albo sprawdzić."
            ),
            "improvement_target": (
                "zamienić dobry review-only output w Wilku-ready instrukcję: "
                "decyzja, dowód, blokada i najbliższy bezpieczny krok."
            ),
        }
    ]
    assert snapshot["live_proof"]["skills"]["reviewer_scorecards"] == {
        "scorecard_count": 3,
        "candidate_for_10_count": 2,
        "fulfilled_candidate_count": 1,
        "open_candidate_count": 1,
        "rerun_required_count": 3,
        "failure_count": 0,
        "rows": [
            {
                "skill": "wilq-daily-command",
                "decision": "candidate_for_10",
                "can_consider_10": "tak",
                "rerun_eval_required": "tak",
                "candidate_fulfilled": True,
                "next_step": "uruchom rerun eval",
            }
        ],
    }
    assert snapshot["live_proof"]["goal_005"]["closed"] is False
    assert (
        snapshot["live_proof"]["goal_005"]["blocker"]
        == "brakuje realnego wyniku UAT albo jawnego owner deferu"
    )
    assert snapshot["maturity_ranges"][0]["done"] == "75-80%"
    assert snapshot["maturity_ranges"][2]["remaining"] == "55-65%"
    assert snapshot["owner_review"]["first_decision"] == {
        "label": "Sprawdź kartę BDO",
        "target_card_id": "ekologus_service_bdo_reporting",
        "required_fields": ["źródła danych", "twierdzenia"],
        "next_step": "Najpierw sprawdź publiczną kartę BDO.",
    }
    assert any(
        "--review-type public_service_cards" in command
        for command in snapshot["owner_review"]["commands"]
    )
    assert any(
        "--review-type private_source_proposals" in command
        for command in snapshot["owner_review"]["commands"]
    )
    assert snapshot["owner_review"]["first_private_decision"] == {
        "action_id": (
            "service_profile_review_private_proposal_"
            "ekologus_ai_kb021_legal_safety_review_candidate_2026_07_01"
        ),
        "target_card_id": "ekologus_claim_policy_legal_safety",
        "label": "Bezpieczeństwo prawne, poufność i zgody",
        "required_fields": [
            "source_trace_clear",
            "blocked_claims_reviewed",
            "data_classes_confirmed",
            "source_block_refs_confirmed",
        ],
    }
    assert snapshot["owner_review"]["approval_readiness"] == {
        "status": "blocked",
        "status_label": "wniosek o zatwierdzenie zablokowany",
        "can_request_promotion": False,
        "mutation_allowed": False,
        "production_depth_unlocked": False,
        "mutation_label": "zablokowana",
        "production_depth_label": "zablokowane",
        "first_action_id": "service_profile_review_card_ekologus_service_bdo_reporting",
        "first_action_label": (
            "Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa"
        ),
        "blocking_checklist": [
            {
                "code": "public_service_review",
                "label": "Publiczne karty usług sprawdzone przez człowieka",
                "next_step": "Zacznij od pierwszej publicznej karty usługi.",
            },
            {
                "code": "promotion_request_packet",
                "label": "Osobny wniosek o zatwierdzenie jest gotowy do przygotowania",
                "next_step": "Najpierw zapisz wynik rozmowy review.",
            },
        ],
    }


def test_stage_snapshot_markdown_is_wilku_readable_and_actionable() -> None:
    stage = load_module()

    snapshot = stage.build_stage_snapshot_from_reports(
        dashboard_report={
            "surface_count": 15,
            "demo_ready_count": 13,
            "review_ready_count": 2,
            "blocked_count": 0,
            "pass": True,
        },
        skill_report={
            "skill_count": 13,
            "fresh_passing_skill_count": 13,
            "minimum_score": 8,
            "maximum_score": 9,
            "wilku_ready_skill_count": 0,
            "pass": True,
            "rows": [
                {
                    "skill": "wilq-ga4-analyst",
                    "score": 9,
                    "state": "gotowy do review",
                    "remaining_blocker": "Uprość opis problemów (not set)…",
                }
            ],
        },
        completion_report={
            "status": "blocked_missing_goal_005_uat_proof",
            "missing_input": "goal_005_uat_result_or_owner_defer",
            "next_uat_input": {
                "first_service_profile_review": {
                    "label": "Sprawdź kartę BDO",
                    "target_card_id": "ekologus_service_bdo_reporting",
                    "required_fields": ["źródła danych", "twierdzenia"],
                    "next_step": "Najpierw sprawdź publiczną kartę BDO.",
                }
            },
        },
        reviewer_scorecard_report={
            "scorecard_count": 3,
            "candidate_for_10_count": 2,
            "fulfilled_candidate_count": 1,
            "open_candidate_count": 1,
            "rerun_required_count": 3,
            "failure_count": 0,
            "rows": [],
        },
        private_review_example={
            "decisions": [
                {
                    "action_id": "service_profile_review_private_proposal_example",
                    "target_card_id": "ekologus_claim_policy_legal_safety",
                    "decision": "approve|needs_changes|stale|reject",
                    "notes": "<krótka decyzja>",
                    "source_trace_clear": "tak|nie",
                    "blocked_claims_reviewed": "tak|nie",
                    "data_classes_confirmed": "tak|nie",
                }
            ]
        },
        approval_readiness={
            "status": "blocked",
            "status_label": "wniosek o zatwierdzenie zablokowany",
            "can_request_promotion": False,
            "mutation_allowed": False,
            "production_depth_unlocked": False,
            "first_action_label": "Sprawdź kartę usługi: BDO",
            "checklist": [
                {
                    "code": "public_service_review",
                    "label": "Publiczne karty usług sprawdzone przez człowieka",
                    "blocking": True,
                    "next_step": "Zacznij od pierwszej publicznej karty usługi.",
                }
            ],
        },
    )

    markdown = stage.render_markdown(snapshot)

    assert "## Ile zostało" in markdown
    assert "Pokazanie Wilkowi" in markdown
    assert "gotowe około **75-80%**" in markdown
    assert "13/15 ekranów demo-ready" in markdown
    assert "score range 8-9" in markdown
    assert "Reviewer pass: scorecardy 3, kandydaci do 10/10 2" in markdown
    assert "potwierdzeni przez eval 1" in markdown
    assert "otwarci kandydaci 1" in markdown
    assert "rerun eval wymagany 3" in markdown
    assert "Jak podbić skille do 10/10" in markdown
    assert "`wilq-ga4-analyst` (9/10): Uprość opis problemów (not set)…" in markdown
    assert "opis kroku jest ucięty w eval artefakcie" in markdown
    assert "Plan testu najbliższych skillów" in markdown
    assert "odtwórz pełny operator_next_step" in markdown
    assert "ucięty tekst nie wystarcza do oceny 10/10" in markdown
    assert "bez zgadywania brakującego końca zdania" in markdown
    assert "scripts/skill_tuning_packet.py --skill wilq-ga4-analyst" in markdown
    assert "brakuje realnego wyniku UAT albo jawnego owner deferu" in markdown
    assert "Jak ruszyć review wiedzy" in markdown
    assert "Pierwsza publiczna decyzja: Sprawdź kartę BDO" in markdown
    assert "Pierwsza prywatna decyzja ekologus-ai" in markdown
    assert "Bezpieczeństwo prawne, poufność i zgody" in markdown
    assert "Gotowość zatwierdzenia: wniosek o zatwierdzenie zablokowany" in markdown
    assert "mutacja: zablokowana" in markdown
    assert "production-depth: zablokowane" in markdown
    assert "Blokada checklisty: Publiczne karty usług sprawdzone przez człowieka" in markdown
    assert "--review-type public_service_cards" in markdown
    assert "--review-type private_source_proposals" in markdown
    assert "Co pokazać Wilkowi" in markdown
    assert "pełnym BDOS-class systemem codziennego wykonania" in markdown
    assert "production-ready" in markdown
