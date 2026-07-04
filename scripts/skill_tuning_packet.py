#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from render_skill_coverage_audit import build_report as build_skill_report

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Render a small tuning packet for the nearest sub-10 WILQ skill "
            "from the latest non-interactive eval artifact."
        )
    )
    parser.add_argument("--skill", help="Skill name. Defaults to first sub-10 skill.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()

    packet = build_packet(skill=args.skill)
    if args.format == "json":
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(packet))
    return 0


def build_packet(*, skill: str | None = None) -> dict[str, Any]:
    report = build_skill_report()
    row = _select_row(report["rows"], skill=skill)
    artifact = row.get("latest_artifact")
    if not artifact:
        raise RuntimeError(f"Skill {row.get('skill') or skill!r} has no latest artifact")
    result_path = REPO_ROOT / str(artifact)
    result = json.loads(result_path.read_text(encoding="utf-8"))
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
