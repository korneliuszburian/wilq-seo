#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from dashboard_usefulness_audit import build_report as build_dashboard_report
from goal_005_completion_check import build_completion_report
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
    completion_report = build_completion_report(api_base=api_base)
    return build_stage_snapshot_from_reports(
        dashboard_report=dashboard_report,
        skill_report=skill_report,
        completion_report=completion_report,
        api_base=api_base,
    )


def build_stage_snapshot_from_reports(
    *,
    dashboard_report: dict[str, Any],
    skill_report: dict[str, Any],
    completion_report: dict[str, Any],
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

    completion_status = str(completion_report.get("status") or "unknown")
    blocker = _completion_blocker_label(completion_report)
    is_goal_closed = completion_status in {"complete_with_uat", "owner_deferred"}
    owner_review = _owner_review_next_step(completion_report, api_base=api_base)

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
    lines.extend(f"- {item}" for item in snapshot["what_is_real_now"])
    if skills.get("nearest_10_blockers"):
        lines.extend(["", "## Dlaczego skille nie są jeszcze 10/10", ""])
        for item in skills["nearest_10_blockers"]:
            lines.append(
                f"- `{item['skill']}` ({item['score']}/10): {item['next_step']}"
            )
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
                f"- Pierwsza decyzja: {decision['label']} "
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
    if not isinstance(first_review, dict) or not first_review:
        return {"commands": commands}
    return {
        "first_decision": {
            "label": first_review.get("label") or "pierwsza decyzja Service Profile",
            "target_card_id": first_review.get("target_card_id") or "brak",
            "required_fields": first_review.get("required_fields") or [],
            "next_step": first_review.get("next_step") or "",
        },
        "commands": commands,
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
        blockers.append(
            {
                "skill": row.get("skill"),
                "score": score,
                "state": row.get("state"),
                "next_step": str(row.get("remaining_blocker") or "").strip(),
            }
        )
    return blockers[:limit]


if __name__ == "__main__":
    raise SystemExit(main())
