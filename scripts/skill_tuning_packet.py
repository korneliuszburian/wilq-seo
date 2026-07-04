#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from render_skill_coverage_audit import build_report as build_skill_report

REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEWER_DECISIONS = {"popraw", "rerun_eval", "candidate_for_10"}
YES_NO_VALUES = {"tak", "nie"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a small tuning packet for the nearest sub-10 WILQ skill "
            "from the latest non-interactive eval artifact."
        )
    )
    parser.add_argument("--skill", help="Skill name. Defaults to first sub-10 skill.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--reviewer-scorecard",
        type=Path,
        help="Optional filled reviewer scorecard JSON for this skill.",
    )
    args = parser.parse_args()

    packet = build_packet(
        skill=args.skill,
        reviewer_scorecard_path=args.reviewer_scorecard,
    )
    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(packet))
    return 0


def build_packet(
    *,
    skill: str | None = None,
    reviewer_scorecard_path: Path | None = None,
) -> dict[str, Any]:
    report = build_skill_report()
    row = _select_row(report["rows"], skill=skill)
    artifact = row.get("latest_artifact")
    if not artifact:
        raise RuntimeError(f"Skill {row.get('skill') or skill!r} has no latest artifact")
    result_path = REPO_ROOT / str(artifact)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    reviewer_scorecard = (
        _load_reviewer_scorecard(reviewer_scorecard_path, skill=row["skill"])
        if reviewer_scorecard_path
        else _reviewer_scorecard(row["skill"])
    )
    return {
        "schema_version": "wilq_skill_tuning_packet_v1",
        "skill": row["skill"],
        "score": row.get("score"),
        "state": row.get("state"),
        "latest_artifact": str(artifact),
        "operator_next_step": result.get("operator_next_step") or "",
        "decision_quality": result.get("decision_quality") or {},
        "evidence_count": len(result.get("evidence_ids") or []),
        "source_connectors": result.get("source_connectors") or [],
        "recommendations": _recommendation_summaries(result),
        "actions": _action_summaries(result),
        "blocked": bool(result.get("blocked")),
        "blocked_reason": result.get("blocked_reason"),
        "score_reason": (result.get("eval_rubric") or {}).get("score_reason_pl") or "",
        "can_claim_10_now": False,
        "why_not_10_yet": (
            "Aktualny artefakt ma score poniżej 10. Nie podbijaj wyniku ręcznie: "
            "wykonaj test użyteczności albo rerun eval po realnej poprawie outputu."
        ),
        "thirty_second_test": _thirty_second_test(row["skill"], result),
        "reviewer_scorecard": reviewer_scorecard,
        "next_tuning_action": _next_tuning_action(row["skill"], result),
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        f"# Skill tuning packet: {packet['skill']}",
        "",
        f"- Score: {packet['score']}/10",
        f"- Stan: {packet['state']}",
        f"- Artefakt: `{packet['latest_artifact']}`",
        f"- Dowody: {packet['evidence_count']}; źródła danych: "
        + ", ".join(packet["source_connectors"]),
        f"- Czy wolno uznać 10/10 teraz: {'tak' if packet['can_claim_10_now'] else 'nie'}",
        f"- Dlaczego nie 10/10: {packet['why_not_10_yet']}",
        "",
        "## Następny krok operatora",
        "",
        packet["operator_next_step"],
        "",
        "## Test 30 sekund",
        "",
    ]
    lines.extend(f"- {item}" for item in packet["thirty_second_test"])
    scorecard = packet.get("reviewer_scorecard") or {}
    if scorecard:
        heading = (
            "Wynik reviewer pass"
            if scorecard.get("filled")
            else "Formularz oceny reviewer pass"
        )
        lines.extend(["", f"## {heading}", ""])
        lines.append(f"- Reviewer: {scorecard['reviewer']}")
        lines.append(f"- Decyzja: {scorecard['decision']}")
        lines.append(f"- Czy można rozważyć 10/10: {scorecard['can_consider_10']}")
        lines.append(f"- Czy trzeba rerun eval: {scorecard['rerun_eval_required']}")
        lines.append("- Kryteria 1-5:")
        for item in scorecard["criteria"]:
            lines.append(f"  - {item['field']}: {item['question']} -> {item['score']}")
        lines.append("- Follow-upy:")
        lines.extend(f"  - {item}" for item in scorecard["follow_up_slots"])
    lines.extend(["", "## Co sprawdzić w outputcie", ""])
    for item in packet["recommendations"][:5]:
        lines.append(f"- Rekomendacja: {item['label_pl']}")
        if item.get("blocked_reason"):
            lines.append(f"  - Blokada: {item['blocked_reason']}")
    if packet["actions"]:
        lines.extend(["", "## Akcje do sprawdzenia", ""])
        lines.extend(
            f"- {item['action_id'] or 'brak action_id'}: {item['label_pl']} "
            f"({item['validation_state']})"
            for item in packet["actions"]
        )
    lines.extend(["", "## Następne strojenie", "", packet["next_tuning_action"]])
    return "\n".join(lines)


def _select_row(rows: list[dict[str, Any]], *, skill: str | None) -> dict[str, Any]:
    candidates = [
        row
        for row in rows
        if isinstance(row.get("score"), int)
        and not isinstance(row.get("score"), bool)
        and int(row["score"]) < 10
    ]
    if skill:
        for row in rows:
            if row.get("skill") == skill:
                return row
        raise RuntimeError(f"Unknown skill: {skill}")
    if not candidates:
        raise RuntimeError("No sub-10 skills found")
    return candidates[0]


def _recommendation_summaries(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label_pl": str(item.get("label_pl") or "").strip(),
            "confidence": item.get("confidence"),
            "blocked_reason": item.get("blocked_reason"),
            "evidence_count": len(item.get("evidence_ids") or []),
            "source_connectors": item.get("source_connectors") or [],
        }
        for item in result.get("recommendations", [])
        if isinstance(item, dict)
    ]


def _action_summaries(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label_pl": str(item.get("label_pl") or "").strip(),
            "action_id": item.get("action_id"),
            "validation_state": item.get("validation_state"),
            "blocked_reason": item.get("blocked_reason"),
        }
        for item in result.get("action_candidates", [])
        if isinstance(item, dict)
    ]


def _thirty_second_test(skill: str, result: dict[str, Any]) -> list[str]:
    action_count = len(
        [
            item
            for item in result.get("action_candidates", [])
            if isinstance(item, dict) and item.get("action_id")
        ]
    )
    return [
        "Czy marketer po pierwszym akapicie wie, który ekran albo workflow otworzyć?",
        "Czy odpowiedź mówi, dlaczego ten krok jest pierwszy właśnie teraz?",
        "Czy decyzja ma dowody WILQ i źródła danych bez czytania raw payloadu?",
        (
            "Czy blokady są praktyczne: mówią czego nie wolno twierdzić albo "
            "zapisać, a nie tylko wymieniają techniczne braki?"
        ),
        (
            f"Czy {skill} wskazuje realne akcje do sprawdzenia "
            f"({action_count}) bez obiecywania zapisu zmian?"
        ),
    ]


def _reviewer_scorecard(skill: str) -> dict[str, Any]:
    criteria = [
        (
            "decyzja_w_30_sekund",
            "Czy marketer wie w 30 sekund, co otworzyć i co sprawdzić najpierw?",
        ),
        (
            "dowody_i_zrodla",
            "Czy dowody WILQ i źródła danych wystarczają bez czytania raw JSON?",
        ),
        (
            "blokady_praktyczne",
            "Czy blokady mówią jasno czego nie wolno twierdzić ani zapisać?",
        ),
        (
            "ekologus_specific",
            "Czy output brzmi jak praca dla Ekologus, a nie ogólna porada marketingowa?",
        ),
        (
            "oszczednosc_czasu",
            "Czy wynik oszczędza czas względem ręcznego czytania dashboardu?",
        ),
    ]
    return {
        "skill": skill,
        "filled": False,
        "reviewer": "UZUPEŁNIJ: kto ocenia",
        "decision": "popraw|rerun_eval|candidate_for_10",
        "can_consider_10": "nie",
        "rerun_eval_required": "tak",
        "criteria": [
            {"field": field, "question": question, "score": "UZUPEŁNIJ 1-5"}
            for field, question in criteria
        ],
        "follow_up_slots": [
            "co było niejasne: UZUPEŁNIJ albo brak",
            "co trzeba poprawić w API/dashboard/skill: UZUPEŁNIJ albo brak",
            "czy rerun non-interactive eval jest potrzebny: tak/nie + dlaczego",
        ],
    }


def _load_reviewer_scorecard(path: Path, *, skill: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Reviewer scorecard file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Reviewer scorecard is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Reviewer scorecard root must be an object")
    if payload.get("skill") != skill:
        raise RuntimeError(
            "Reviewer scorecard skill mismatch: "
            f"expected {skill!r}, got {payload.get('skill')!r}"
        )
    decision = _required_string(payload, "decision")
    if decision not in REVIEWER_DECISIONS:
        raise RuntimeError(
            "Reviewer scorecard decision must be one of: "
            + ", ".join(sorted(REVIEWER_DECISIONS))
        )
    can_consider_10 = _required_string(payload, "can_consider_10")
    rerun_eval_required = _required_string(payload, "rerun_eval_required")
    if can_consider_10 not in YES_NO_VALUES:
        raise RuntimeError("Reviewer scorecard can_consider_10 must be `tak` or `nie`")
    if rerun_eval_required not in YES_NO_VALUES:
        raise RuntimeError(
            "Reviewer scorecard rerun_eval_required must be `tak` or `nie`"
        )
    criteria = payload.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise RuntimeError("Reviewer scorecard criteria must be a non-empty list")
    normalized_criteria = [_normalize_criterion(item) for item in criteria]
    follow_ups = payload.get("follow_up_slots") or []
    if not isinstance(follow_ups, list) or not all(
        isinstance(item, str) and item.strip() for item in follow_ups
    ):
        raise RuntimeError("Reviewer scorecard follow_up_slots must be a list of text")
    return {
        "skill": skill,
        "filled": True,
        "reviewer": _required_string(payload, "reviewer"),
        "decision": decision,
        "can_consider_10": can_consider_10,
        "rerun_eval_required": rerun_eval_required,
        "criteria": normalized_criteria,
        "follow_up_slots": [item.strip() for item in follow_ups],
        "notes": str(payload.get("notes") or "").strip(),
    }


def _normalize_criterion(item: object) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise RuntimeError("Reviewer scorecard criteria items must be objects")
    field = _required_string(item, "field")
    question = _required_string(item, "question")
    score = item.get("score")
    if not isinstance(score, int) or isinstance(score, bool) or score < 1 or score > 5:
        raise RuntimeError(
            f"Reviewer scorecard criterion {field!r} score must be an integer 1-5"
        )
    return {"field": field, "question": question, "score": score}


def _required_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Reviewer scorecard field {field!r} must be non-empty text")
    return value.strip()


def _next_tuning_action(skill: str, result: dict[str, Any]) -> str:
    quality = result.get("decision_quality") or {}
    notes = str(quality.get("notes_pl") or "").strip()
    if notes:
        return (
            f"Zrób reviewer pass dla `{skill}`: porównaj notatkę jakości "
            f"({notes}) z realnym ekranem i sprawdź, czy output oszczędza "
            "czas względem ręcznego czytania dashboardu."
        )
    return (
        f"Zrób reviewer pass dla `{skill}` na realnym ekranie i zapisz, "
        "co blokuje score 10/10."
    )


if __name__ == "__main__":
    raise SystemExit(main())
