#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from audit_skill_reviewer_scorecards import (
    DEFAULT_SCORECARD_DIR,
)
from audit_skill_reviewer_scorecards import (
    build_report as build_scorecard_report,
)
from dashboard_usefulness_audit import build_report as build_dashboard_report
from goal_005_completion_check import build_completion_report
from record_service_profile_review_result import (
    build_input_example,
    load_live_context,
    service_profile_target_label,
)
from render_skill_coverage_audit import build_report as build_skill_report

DEFAULT_API_BASE = "http://127.0.0.1:8000"

MATURITY_RANGES = [
    {
        "area": "Pokazanie Wilkowi",
        "done": "75-80%",
        "remaining": "20-25%",
        "why": (
            "Dashboard i skille mają dowody, decyzje i bezpieczne następne kroki, "
            "ale nadal brakuje realnej sesji Wilku albo świadomego deferu ownera."
        ),
    },
    {
        "area": "Codzienna praca Ekologus",
        "done": "55-65%",
        "remaining": "35-45%",
        "why": (
            "WILQ umie już prowadzić review treści, Ads, GA4, Merchant i wiedzy, "
            "ale brakuje zatwierdzonej wiedzy production-depth, social history "
            "dedupe i pełnej pętli publikacja-pomiar-nauka."
        ),
    },
    {
        "area": "BDOS-class multi-client MOS",
        "done": "35-45%",
        "remaining": "55-65%",
        "why": (
            "Fundament API-first i ActionObject istnieje, ale write execution, "
            "multi-client model, optimizer depth i raportowanie wyników są nadal "
            "na wcześniejszym etapie."
        ),
    },
]

NEXT_WORK = [
    "Zebrać realny 15-minutowy feedback Wilka albo jawny owner defer z ryzykiem.",
    "Doprowadzić wybrane Service Profile/source facts do owner review zamiast review-required.",
    "Dodać reviewed social-history metadata, żeby blokować powtórki LinkedIn/Facebook.",
    "Przejść z review-only do pierwszych bezpiecznych draft/write ActionObjects, bez publikacji.",
    "Po publikacji lub zmianie zasilać measurement loop realnym oknem obserwacji.",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a short WILQ stage snapshot from live API readiness, "
            "skill eval coverage and Goal 005 completion guard."
        )
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()

    snapshot = build_stage_snapshot(api_base=args.api_base)
    if args.format == "json":
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(snapshot))
    return 0


def build_stage_snapshot(*, api_base: str = DEFAULT_API_BASE) -> dict[str, Any]:
    dashboard_report = build_dashboard_report(api_base)
    skill_report = build_skill_report()
    scorecard_report = build_scorecard_report(DEFAULT_SCORECARD_DIR, strict=False)
    completion_report = build_completion_report(api_base=api_base)
    live_context = load_live_context(api_base)
    private_review_example = build_input_example(
        live_context,
        review_type="private_source_proposals",
    )
    return build_stage_snapshot_from_reports(
        dashboard_report=dashboard_report,
        skill_report=skill_report,
        reviewer_scorecard_report=scorecard_report,
        completion_report=completion_report,
        private_review_example=private_review_example,
        approval_readiness=(
            live_context.get("service_profile", {}).get("approval_readiness")
            if isinstance(live_context.get("service_profile"), dict)
            else None
        ),
        api_base=api_base,
    )


def build_stage_snapshot_from_reports(
    *,
    dashboard_report: dict[str, Any],
    skill_report: dict[str, Any],
    completion_report: dict[str, Any],
    reviewer_scorecard_report: dict[str, Any] | None = None,
    private_review_example: dict[str, Any] | None = None,
    approval_readiness: dict[str, Any] | None = None,
    api_base: str = DEFAULT_API_BASE,
) -> dict[str, Any]:
    dashboard_surfaces = int(dashboard_report.get("surface_count") or 0)
    demo_ready = int(dashboard_report.get("demo_ready_count") or 0)
    review_ready = int(dashboard_report.get("review_ready_count") or 0)
    blocked_surfaces = int(dashboard_report.get("blocked_count") or 0)

    skill_count = int(skill_report.get("skill_count") or 0)
    fresh_skills = int(skill_report.get("fresh_passing_skill_count") or 0)
    wilku_ready_skills = int(skill_report.get("wilku_ready_skill_count") or 0)
    min_score = skill_report.get("minimum_score")
    max_score = skill_report.get("maximum_score")
    skill_quality_blockers = _skill_quality_blockers(skill_report)
    reviewer_scorecards = _reviewer_scorecard_summary(reviewer_scorecard_report)

    completion_status = str(completion_report.get("status") or "unknown")
    blocker = _completion_blocker_label(completion_report)
    is_goal_closed = completion_status in {"complete_with_uat", "owner_deferred"}
    owner_review = _owner_review_next_step(
        completion_report,
        private_review_example=private_review_example,
        approval_readiness=approval_readiness,
        api_base=api_base,
    )

    current_stage = (
        "demo/review-ready, ale nie production-ready"
        if not is_goal_closed
        else "Goal 005 ma formalny proof/defer, nadal wymaga verify przed claimem"
    )

    return {
        "schema_version": "wilq_stage_snapshot_v1",
        "api_base": api_base.rstrip("/"),
        "current_stage": current_stage,
        "one_sentence": (
            "WILQ jest już działającym cockpit review dla Ekologus, ale jeszcze "
            "nie pełnym BDOS-class systemem codziennego wykonania."
        ),
        "maturity_ranges": MATURITY_RANGES,
        "live_proof": {
            "dashboard": {
                "surface_count": dashboard_surfaces,
                "demo_ready_count": demo_ready,
                "review_ready_count": review_ready,
                "blocked_count": blocked_surfaces,
                "pass": bool(dashboard_report.get("pass")),
            },
            "skills": {
                "skill_count": skill_count,
                "fresh_passing_skill_count": fresh_skills,
                "score_range": _score_range(min_score, max_score),
                "wilku_ready_skill_count": wilku_ready_skills,
                "nearest_10_blockers": skill_quality_blockers,
                "nearest_10_plan": _skill_to_10_plan(skill_quality_blockers),
                "reviewer_scorecards": reviewer_scorecards,
                "pass": bool(skill_report.get("pass")),
            },
            "goal_005": {
                "status": completion_status,
                "blocker": blocker,
                "closed": is_goal_closed,
            },
        },
        "what_is_real_now": [
            "API-first mózg systemu i dashboard z decyzjami zamiast luźnych promptów.",
            "13 skillów z aktualnym passing evalem, dowodami i polskim next stepem.",
            "Service Profile, source facts i prywatny ekologus-ai trace jako review-required.",
            "ActionObject safety loop: walidacja, preview, review, confirm, audit.",
            "WordPress pozostaje draft-only i bez publikacji bez zgody.",
        ],
        "main_gaps": [
            "Brak realnego Wilku UAT albo jawnego owner deferu dla Goal 005.",
            "Brak approved-current knowledge cards dla production-depth treści.",
            "Brak reviewed social-history inventory dla claimów o braku powtórek.",
            "Write execution jest jeszcze ograniczone i musi iść przez ActionObject.",
            "Measurement loop nie może jeszcze rościć sukcesu bez okna obserwacji.",
        ],
        "next_work": NEXT_WORK,
        "owner_review": owner_review,
        "show_to_wilku": [
            "Pokaż Command Center jako poranny cockpit: co dziś otworzyć i dlaczego.",
            "Pokaż Service Profile: co WILQ wie, co wymaga review i czego nie wolno jeszcze mówić.",
            (
                "Pokaż Content Workflow/Claim Ledger jako dowód, że treść nie "
                "idzie do publikacji bez review."
            ),
            "Zadaj pytanie: czy po 15 minutach Wilku wie, co zrobić dalej bez developera?",
        ],
    }


def render_markdown(snapshot: dict[str, Any]) -> str:
    proof = snapshot["live_proof"]
    dashboard = proof["dashboard"]
    skills = proof["skills"]
    goal = proof["goal_005"]
    lines = [
        "# WILQ stage snapshot",
        "",
        f"- Etap: **{snapshot['current_stage']}**",
        f"- W skrócie: {snapshot['one_sentence']}",
        f"- API: `{snapshot['api_base']}`",
        "",
        "## Ile zostało",
        "",
    ]
    for row in snapshot["maturity_ranges"]:
        lines.append(
            f"- **{row['area']}**: gotowe około **{row['done']}**, "
            f"zostało **{row['remaining']}**. {row['why']}"
        )
    lines.extend(
        [
            "",
            "## Dowód aktualnego stanu",
            "",
            (
                f"- Dashboard: {dashboard['demo_ready_count']}/"
                f"{dashboard['surface_count']} ekranów demo-ready, "
                f"{dashboard['review_ready_count']} review-ready, "
                f"{dashboard['blocked_count']} blocked."
            ),
            (
                f"- Skille: {skills['fresh_passing_skill_count']}/"
                f"{skills['skill_count']} świeżych passing evali, "
                f"score range {skills['score_range']}, "
                f"{skills['wilku_ready_skill_count']} na poziomie 10/10."
            ),
            (
                f"- Goal 005: `{goal['status']}`; blocker: "
                f"{goal['blocker']}."
            ),
            "",
            "## Co jest realne teraz",
            "",
        ]
    )
    if skills.get("reviewer_scorecards", {}).get("scorecard_count"):
        scorecards = skills["reviewer_scorecards"]
        lines.append(
            f"- Reviewer pass: {scorecards['scorecard_count']} scorecardy, "
            f"{scorecards['candidate_for_10_count']} kandydatów do 10/10, "
            f"{scorecards['rerun_required_count']} wymagają rerun eval."
        )
    lines.extend(f"- {item}" for item in snapshot["what_is_real_now"])
    if skills.get("nearest_10_blockers"):
        lines.extend(["", "## Jak podbić skille do 10/10", ""])
        for item in skills["nearest_10_blockers"]:
            lines.append(
                f"- `{item['skill']}` ({item['score']}/10): {item['next_step']}"
            )
            if item.get("next_step_truncated"):
                lines.append(
                    "  - Uwaga: opis kroku jest ucięty w eval artefakcie; "
                    "najpierw odtwórz pełny operator_next_step."
                )
        if skills.get("nearest_10_plan"):
            lines.extend(["", "Plan testu najbliższych skillów:"])
            for item in skills["nearest_10_plan"]:
                lines.append(
                    f"- `{item['skill']}`: {item['test']} "
                    f"Cel poprawy: {item['improvement_target']}"
                )
                if item.get("packet_command"):
                    lines.append(f"  - Packet do testu: `{item['packet_command']}`")
    lines.extend(["", "## Główne braki", ""])
    lines.extend(f"- {item}" for item in snapshot["main_gaps"])
    lines.extend(["", "## Następny ruch", ""])
    lines.extend(f"- {item}" for item in snapshot["next_work"])
    if snapshot.get("owner_review"):
        owner_review = snapshot["owner_review"]
        lines.extend(["", "## Jak ruszyć review wiedzy", ""])
        if owner_review.get("first_decision"):
            decision = owner_review["first_decision"]
            lines.append(
                f"- Pierwsza publiczna decyzja: {decision['label']} "
                f"(`{decision['target_card_id']}`)."
            )
            if decision.get("required_fields"):
                lines.append(
                    "- Pola do sprawdzenia: "
                    + ", ".join(decision["required_fields"])
                    + "."
                )
            if decision.get("next_step"):
                lines.append(f"- Następny krok: {decision['next_step']}")
        if owner_review.get("first_private_decision"):
            private_decision = owner_review["first_private_decision"]
            lines.append(
                f"- Pierwsza prywatna decyzja ekologus-ai: "
                f"{private_decision['label']} (`{private_decision['target_card_id']}`)."
            )
            if private_decision.get("required_fields"):
                lines.append(
                    "- Prywatne pola do sprawdzenia: "
                    + ", ".join(private_decision["required_fields"])
                    + "."
                )
        if owner_review.get("approval_readiness"):
            readiness = owner_review["approval_readiness"]
            lines.append(
                f"- Gotowość zatwierdzenia: {readiness['status_label']} "
                f"(mutacja: {readiness['mutation_label']}, "
                f"production-depth: {readiness['production_depth_label']})."
            )
            if readiness.get("first_action_label"):
                lines.append(
                    f"- Pierwszy krok zatwierdzenia: {readiness['first_action_label']}."
                )
            for item in readiness.get("blocking_checklist") or []:
                lines.append(f"- Blokada checklisty: {item['label']} - {item['next_step']}")
        for command in owner_review.get("commands") or []:
            lines.append(f"- `{command}`")
    lines.extend(["", "## Co pokazać Wilkowi", ""])
    lines.extend(f"- {item}" for item in snapshot["show_to_wilku"])
    return "\n".join(lines)


def _completion_blocker_label(report: dict[str, Any]) -> str:
    if report.get("status") == "blocked_missing_goal_005_uat_proof":
        missing = str(report.get("missing_input") or "").strip()
        if missing == "goal_005_uat_result_or_owner_defer":
            return "brakuje realnego wyniku UAT albo jawnego owner deferu"
        if missing:
            return missing
    if report.get("status") == "owner_deferred":
        return "owner świadomie odroczył UAT i przyjął ryzyko rezydualne"
    if report.get("status") == "complete_with_uat":
        return "realny UAT zapisany; przed claimem nadal wymagany pełny verify"
    return "sprawdź completion guard Goal 005"


def _score_range(min_score: Any, max_score: Any) -> str:
    if min_score is None or max_score is None:
        return "brak"
    if min_score == max_score:
        return str(min_score)
    return f"{min_score}-{max_score}"


def _owner_review_next_step(
    completion_report: dict[str, Any],
    *,
    private_review_example: dict[str, Any] | None,
    approval_readiness: dict[str, Any] | None,
    api_base: str,
) -> dict[str, Any]:
    next_uat_input = completion_report.get("next_uat_input")
    if not isinstance(next_uat_input, dict):
        return {}
    first_review = next_uat_input.get("first_service_profile_review")
    commands = [
        (
            "rtk uv run python scripts/record_service_profile_review_result.py "
            "--print-session-card --review-type public_service_cards "
            f"--api-base {api_base.rstrip('/')}"
        ),
        (
            "rtk uv run python scripts/record_service_profile_review_result.py "
            "--print-session-card --review-type private_source_proposals "
            f"--api-base {api_base.rstrip('/')}"
        ),
    ]
    owner_review: dict[str, Any] = {"commands": commands}
    if isinstance(first_review, dict) and first_review:
        owner_review["first_decision"] = {
            "label": first_review.get("label") or "pierwsza decyzja Service Profile",
            "target_card_id": first_review.get("target_card_id") or "brak",
            "required_fields": first_review.get("required_fields") or [],
            "next_step": first_review.get("next_step") or "",
        }
    first_private = _first_private_review_decision(private_review_example)
    if first_private:
        owner_review["first_private_decision"] = first_private
    readiness = _approval_readiness_summary(approval_readiness)
    if readiness:
        owner_review["approval_readiness"] = readiness
    return owner_review


def _approval_readiness_summary(
    approval_readiness: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(approval_readiness, dict):
        return None
    checklist = [
        item
        for item in approval_readiness.get("checklist") or []
        if isinstance(item, dict)
    ]
    blocking_checklist = [
        {
            "code": str(item.get("code") or "").strip(),
            "label": str(item.get("label") or "").strip(),
            "next_step": str(item.get("next_step") or "").strip(),
        }
        for item in checklist
        if item.get("blocking") is True
    ]
    return {
        "status": str(approval_readiness.get("status") or "blocked").strip(),
        "status_label": str(
            approval_readiness.get("status_label") or "wniosek zablokowany"
        ).strip(),
        "can_request_promotion": bool(
            approval_readiness.get("can_request_promotion")
        ),
        "mutation_allowed": bool(approval_readiness.get("mutation_allowed")),
        "production_depth_unlocked": bool(
            approval_readiness.get("production_depth_unlocked")
        ),
        "mutation_label": (
            "dozwolona" if approval_readiness.get("mutation_allowed") else "zablokowana"
        ),
        "production_depth_label": (
            "odblokowane"
            if approval_readiness.get("production_depth_unlocked")
            else "zablokowane"
        ),
        "first_action_id": approval_readiness.get("first_action_id"),
        "first_action_label": approval_readiness.get("first_action_label"),
        "blocking_checklist": blocking_checklist[:4],
    }


def _first_private_review_decision(
    private_review_example: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(private_review_example, dict):
        return None
    decisions = private_review_example.get("decisions") or []
    if not isinstance(decisions, list) or not decisions:
        return None
    first = decisions[0]
    if not isinstance(first, dict):
        return None
    target_card_id = str(first.get("target_card_id") or "").strip()
    required_fields = [
        key
        for key, value in first.items()
        if key not in {"action_id", "target_card_id", "decision", "notes", "follow_up_beads"}
        and value
    ]
    return {
        "action_id": first.get("action_id") or "",
        "target_card_id": target_card_id or "brak",
        "label": service_profile_target_label(target_card_id) if target_card_id else "brak",
        "required_fields": required_fields,
    }


def _skill_quality_blockers(
    skill_report: dict[str, Any],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    rows = skill_report.get("rows") or []
    blockers: list[dict[str, Any]] = []
    for row in rows:
        score = row.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or score >= 10:
            continue
        raw_next_step = (
            row.get("remaining_blocker_full") or row.get("remaining_blocker") or ""
        )
        blockers.append(
            {
                "skill": row.get("skill"),
                "score": score,
                "state": row.get("state"),
                "what_it_proves": str(row.get("what_it_proves") or "").strip(),
                "next_step": str(raw_next_step).strip(),
                "next_step_truncated": bool(row.get("truncated_visible_output"))
                or _looks_truncated(raw_next_step),
            }
        )
    return blockers[:limit]


def _reviewer_scorecard_summary(
    report: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {
            "scorecard_count": 0,
            "candidate_for_10_count": 0,
            "rerun_required_count": 0,
            "failure_count": 0,
            "rows": [],
        }
    rows = [
        {
            "skill": row.get("skill"),
            "decision": row.get("decision"),
            "can_consider_10": row.get("can_consider_10"),
            "rerun_eval_required": row.get("rerun_eval_required"),
            "next_step": row.get("next_step"),
        }
        for row in report.get("rows") or []
        if isinstance(row, dict) and row.get("status") == "valid"
    ]
    return {
        "scorecard_count": int(report.get("scorecard_count") or 0),
        "candidate_for_10_count": int(report.get("candidate_for_10_count") or 0),
        "rerun_required_count": int(report.get("rerun_required_count") or 0),
        "failure_count": int(report.get("failure_count") or 0),
        "rows": rows,
    }


def _skill_to_10_plan(blockers: list[dict[str, Any]]) -> list[dict[str, str]]:
    plan: list[dict[str, str]] = []
    for item in blockers:
        skill = str(item.get("skill") or "").strip()
        state = str(item.get("state") or "").strip()
        next_step = str(item.get("next_step") or "").strip()
        if not skill:
            continue
        plan.append(
            {
                "skill": skill,
                "state": state,
                "packet_command": (
                    "rtk uv run python scripts/skill_tuning_packet.py "
                    f"--skill {skill}"
                ),
                "test": _skill_test_instruction(skill, state, next_step),
                "improvement_target": _skill_improvement_target(state, next_step),
            }
        )
    return plan


def _skill_test_instruction(skill: str, state: str, next_step: str) -> str:
    if _looks_truncated(next_step):
        return (
            "najpierw odtwórz pełny operator_next_step w eval artefakcie albo "
            "rerun non-interactive eval z pełniejszym next stepem; ucięty tekst "
            "nie wystarcza do oceny 10/10."
        )
    if state == "poprawnie zablokowany do review":
        return (
            "uruchom ten sam marketerowy prompt i sprawdź, czy odpowiedź nie tylko "
            "blokuje claim, ale daje jedną decyzję review, źródła i kolejny krok."
        )
    if state == "stale passing eval":
        return (
            "rerun deterministic smoke i non-interactive Codex eval, bo aktualny "
            "wynik jest starszy niż instrukcje skilla."
        )
    if next_step:
        return (
            "wykonaj wskazany ekran/workflow z odpowiedzi skilla i oceń, czy "
            "marketer w 30 sekund wie, co kliknąć albo sprawdzić."
        )
    return (
        "uruchom realistyczny polski prompt, porównaj odpowiedź z WILQ API i "
        "oceń użyteczność dla operatora w skali 0-10."
    )


def _skill_improvement_target(state: str, next_step: str) -> str:
    if _looks_truncated(next_step):
        return (
            "pełny opis kolejnego kroku ma być wystarczający do wykonania testu "
            "bez zgadywania brakującego końca zdania."
        )
    if state == "poprawnie zablokowany do review":
        return (
            "blokada ma zostać, ale odpowiedź musi lepiej tłumaczyć, co człowiek "
            "może teraz ocenić bez developera."
        )
    if state == "stale passing eval":
        return "odzyskać świeży passing eval zanim uznamy skill za aktualny."
    if next_step:
        return (
            "zamienić dobry review-only output w Wilku-ready instrukcję: decyzja, "
            "dowód, blokada i najbliższy bezpieczny krok."
        )
    return (
        "usunąć ogólnikowość: odpowiedź ma używać konkretnych decyzji, dowodów, "
        "ActionObjectów i polskiego następnego kroku."
    )


def _looks_truncated(value: Any) -> bool:
    text = str(value or "").strip()
    return text.endswith("…") or text.endswith("...")


if __name__ == "__main__":
    raise SystemExit(main())
