#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from skill_tuning_packet import build_packet

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORECARD_DIR = REPO_ROOT / "docs/evals/skill-reviewer-scorecards"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate filled reviewer scorecards for WILQ skill tuning."
    )
    parser.add_argument(
        "--scorecard-dir",
        type=Path,
        default=DEFAULT_SCORECARD_DIR,
        help="Directory with reviewer scorecard JSON files.",
    )
    parser.add_argument("--json", action="store_true", help="Render JSON summary.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when no scorecards are found.",
    )
    args = parser.parse_args()

    report = build_report(args.scorecard_dir, strict=args.strict)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0 if report["pass"] else 1


def build_report(scorecard_dir: Path, *, strict: bool = False) -> dict[str, Any]:
    paths = sorted(scorecard_dir.glob("*.json")) if scorecard_dir.exists() else []
    rows = [_validate_scorecard(path) for path in paths]
    failures = [row for row in rows if row["status"] != "valid"]
    pass_state = not failures and (bool(rows) or not strict)
    return {
        "schema_version": "wilq_skill_reviewer_scorecard_audit_v1",
        "scorecard_dir": str(scorecard_dir),
        "scorecard_count": len(rows),
        "failure_count": len(failures),
        "candidate_for_10_count": sum(
            1 for row in rows if row.get("decision") == "candidate_for_10"
        ),
        "rerun_required_count": sum(
            1 for row in rows if row.get("rerun_eval_required") == "tak"
        ),
        "fulfilled_candidate_count": sum(
            1 for row in rows if row.get("candidate_fulfilled") is True
        ),
        "open_candidate_count": sum(
            1
            for row in rows
            if row.get("decision") == "candidate_for_10"
            and row.get("candidate_fulfilled") is not True
        ),
        "pass": pass_state,
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Skill reviewer scorecard audit",
        "",
        f"- Scorecards: {report['scorecard_count']}",
        f"- Failures: {report['failure_count']}",
        f"- Candidate for 10/10: {report['candidate_for_10_count']}",
        f"- Fulfilled candidates: {report['fulfilled_candidate_count']}",
        f"- Open candidates: {report['open_candidate_count']}",
        f"- Rerun eval required: {report['rerun_required_count']}",
        f"- Pass: {'tak' if report['pass'] else 'nie'}",
        "",
        "## Rows",
        "",
    ]
    for row in report["rows"]:
        lines.append(
            f"- `{row['path']}`: {row['skill']} -> {row.get('decision') or 'brak'} "
            f"({row['status']}, score {row.get('score') or 'brak'})"
        )
        if row.get("error"):
            lines.append(f"  - Error: {row['error']}")
        if row.get("next_step"):
            lines.append(f"  - Następny krok: {row['next_step']}")
    return "\n".join(lines)


def _validate_scorecard(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {"path": str(path), "status": "valid"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("scorecard root must be an object")
        skill = payload.get("skill")
        if not isinstance(skill, str) or not skill.strip():
            raise RuntimeError("scorecard must include non-empty skill")
        packet = build_packet(skill=skill, reviewer_scorecard_path=path)
        scorecard = packet["reviewer_scorecard"]
        _check_decision_consistency(scorecard)
        row.update(
            {
                "skill": skill,
                "score": packet.get("score"),
                "decision": scorecard["decision"],
                "can_consider_10": scorecard["can_consider_10"],
                "rerun_eval_required": scorecard["rerun_eval_required"],
                "criteria_count": len(scorecard["criteria"]),
                "criteria_total": sum(item["score"] for item in scorecard["criteria"]),
                "candidate_fulfilled": _candidate_fulfilled(scorecard, packet),
                "next_step": _next_step(scorecard),
            }
        )
    except Exception as exc:  # noqa: BLE001 - CLI audit should report all bad files.
        row.update({"status": "invalid", "error": str(exc)})
    return row


def _check_decision_consistency(scorecard: dict[str, Any]) -> None:
    decision = scorecard["decision"]
    can_consider_10 = scorecard["can_consider_10"]
    rerun_eval_required = scorecard["rerun_eval_required"]
    if decision == "candidate_for_10" and can_consider_10 != "tak":
        raise RuntimeError("candidate_for_10 requires can_consider_10=tak")
    if decision == "candidate_for_10" and rerun_eval_required != "tak":
        raise RuntimeError("candidate_for_10 requires rerun_eval_required=tak")
    if decision == "popraw" and can_consider_10 == "tak":
        raise RuntimeError("popraw cannot set can_consider_10=tak")


def _next_step(scorecard: dict[str, Any]) -> str:
    decision = scorecard["decision"]
    if decision == "candidate_for_10":
        return "uruchom rerun non-interactive eval i dopiero wtedy rozważ zmianę score"
    if decision == "rerun_eval":
        return "uruchom rerun eval po sprawdzeniu, że output nadal spełnia scorecard"
    return "popraw API/dashboard/skill według follow-upów, potem rerun eval"


def _candidate_fulfilled(scorecard: dict[str, Any], packet: dict[str, Any]) -> bool:
    return (
        scorecard["decision"] == "candidate_for_10"
        and isinstance(packet.get("score"), int)
        and not isinstance(packet.get("score"), bool)
        and int(packet["score"]) >= 10
    )


if __name__ == "__main__":
    raise SystemExit(main())
