#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "docs/evals/cases/wilq-skill-eval-cases.json"
DEFAULT_EVAL_ROOT = REPO_ROOT / ".local-lab/evals/codex-skill"
DEFAULT_SKILL_ROOT = REPO_ROOT / ".agents/skills"
MINIMUM_OPERATOR_USEFULNESS_SCORE = 5
SKILL_SOURCE_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".sh"}
SKIP_SOURCE_PARTS = {"__pycache__"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _cases() -> list[dict[str, Any]]:
    cases = _load_json(CASES_PATH)
    if not isinstance(cases, list):
        raise ValueError("skill eval cases must be a list")
    return cases


def _result_paths(eval_root: Path, skill: str) -> list[Path]:
    if not eval_root.exists():
        return []
    return sorted(eval_root.glob(f"*/{skill}/result.json"))


def _hard_gates_pass(result: dict[str, Any]) -> bool:
    hard_gates = ((result.get("eval_rubric") or {}).get("hard_gates") or {})
    return bool(hard_gates) and all(value is True for value in hard_gates.values())


def _is_passing_result(result: dict[str, Any], minimum_score: int) -> bool:
    return (
        result.get("api_used") is True
        and result.get("language") == "pl-PL"
        and int(result.get("operator_usefulness_score") or 0) >= minimum_score
        and not result.get("failure_tags")
        and _hard_gates_pass(result)
    )


def _load_latest_passing_result(
    eval_root: Path, skill: str, minimum_score: int
) -> tuple[Path | None, dict[str, Any] | None]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for path in _result_paths(eval_root, skill):
        try:
            result = _load_json(path)
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict) and _is_passing_result(result, minimum_score):
            candidates.append((path, result))
    if not candidates:
        return None, None
    return candidates[-1]


def _skill_source_paths(skill_root: Path, skill: str) -> list[Path]:
    skill_dir = skill_root / skill
    if not skill_dir.exists():
        return []
    return sorted(
        path
        for path in skill_dir.rglob("*")
        if path.is_file()
        and path.suffix in SKILL_SOURCE_SUFFIXES
        and not any(part in SKIP_SOURCE_PARTS for part in path.parts)
    )


def _latest_skill_source_mtime(skill_root: Path, skill: str) -> float | None:
    mtimes = [path.stat().st_mtime for path in _skill_source_paths(skill_root, skill)]
    return max(mtimes) if mtimes else None


def _is_stale_result(path: Path, skill_root: Path, skill: str) -> bool:
    latest_source_mtime = _latest_skill_source_mtime(skill_root, skill)
    if latest_source_mtime is None:
        return False
    return latest_source_mtime > path.stat().st_mtime


def _status_label(result: dict[str, Any]) -> str:
    actions = result.get("action_candidates") or []
    if result.get("blocked") is True:
        return "blocked correctly / review-only"
    if actions:
        return "ready / review-only"
    return "ready / read-only"


def _short_text(value: Any, *, max_len: int = 130) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _what_it_proves(result: dict[str, Any]) -> str:
    connectors = ", ".join(result.get("source_connectors") or [])
    evidence_count = len(result.get("evidence_ids") or [])
    actions = [
        action.get("action_id")
        for action in (result.get("action_candidates") or [])
        if action.get("action_id")
    ]
    parts = [f"{evidence_count} evidence IDs"]
    if connectors:
        parts.append(f"connectors: {connectors}")
    if actions:
        parts.append("actions: " + ", ".join(actions[:4]))
    return _short_text("; ".join(parts), max_len=180)


def _remaining_blocker(result: dict[str, Any]) -> str:
    if result.get("blocked"):
        return _short_text(result.get("blocked_reason"), max_len=180)
    return _short_text(result.get("operator_next_step"), max_len=180)


def build_report(
    eval_root: Path = DEFAULT_EVAL_ROOT,
    *,
    skill_root: Path = DEFAULT_SKILL_ROOT,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    stale: list[str] = []
    for case in _cases():
        skill = str(case["skill"])
        minimum_score = max(
            int(
                case.get(
                    "minimum_operator_usefulness_score",
                    MINIMUM_OPERATOR_USEFULNESS_SCORE,
                )
            ),
            MINIMUM_OPERATOR_USEFULNESS_SCORE,
        )
        path, result = _load_latest_passing_result(eval_root, skill, minimum_score)
        if result is None or path is None:
            missing.append(skill)
            rows.append(
                {
                    "skill": skill,
                    "latest_artifact": None,
                    "score": None,
                    "state": "missing passing eval",
                    "what_it_proves": "Brak aktualnego passing result.json dla tego skilla.",
                    "remaining_blocker": (
                        "Uruchom deterministic smoke i scripts/codex_skill_eval.sh."
                    ),
                }
            )
            continue
        result_is_stale = _is_stale_result(path, skill_root, skill)
        if result_is_stale:
            stale.append(skill)
        artifact = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
        rows.append(
            {
                "skill": skill,
                "latest_artifact": artifact,
                "score": int(result.get("operator_usefulness_score") or 0),
                "state": "stale passing eval" if result_is_stale else _status_label(result),
                "what_it_proves": _what_it_proves(result),
                "remaining_blocker": (
                    "Skill instructions or references changed after this eval; "
                    "rerun smoke and non-interactive Codex eval."
                    if result_is_stale
                    else _remaining_blocker(result)
                ),
                "stale": result_is_stale,
            }
        )
    scores = [
        int(row["score"])
        for row in rows
        if isinstance(row.get("score"), int) and not isinstance(row.get("score"), bool)
    ]
    return {
        "schema_version": "wilq_latest_skill_coverage_audit_v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "eval_root": str(eval_root.relative_to(REPO_ROOT))
        if eval_root.is_relative_to(REPO_ROOT)
        else str(eval_root),
        "skill_root": str(skill_root.relative_to(REPO_ROOT))
        if skill_root.is_relative_to(REPO_ROOT)
        else str(skill_root),
        "skill_count": len(rows),
        "passing_skill_count": len(rows) - len(missing),
        "fresh_passing_skill_count": len(rows) - len(missing) - len(stale),
        "minimum_score": min(scores) if scores else None,
        "maximum_score": max(scores) if scores else None,
        "strong_skill_count": sum(1 for score in scores if score >= 7),
        "wilku_ready_skill_count": sum(1 for score in scores if score >= 10),
        "missing_passing_skills": missing,
        "stale_passing_skills": stale,
        "rows": rows,
        "pass": not missing and not stale,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# WILQ Skill Coverage Audit",
        "",
        f"Generated: `{report['generated_at']}`.",
        "",
        "Cel: krótka mapa recovery dla WILQ skills po aktualnych evalach. "
        "Pełne przebiegi zostają w `docs/evals/skill-eval-ledger.md`; tutaj "
        "trzymamy tylko najnowszy passing artifact i decyzję produktową.",
        "",
        "## Coverage Table",
        "",
        (
            "| Skill | Latest artifact | Score | State | What it proves | "
            "Remaining blocker / next step |"
        ),
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for row in report["rows"]:
        artifact = row["latest_artifact"] or "missing"
        score = "" if row["score"] is None else str(row["score"])
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['skill']}`",
                    f"`{artifact}`",
                    score,
                    _md_cell(row["state"]),
                    _md_cell(row["what_it_proves"]),
                    _md_cell(row["remaining_blocker"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Product Readout",
            "",
            (
                f"- {report['passing_skill_count']}/{report['skill_count']} "
                "WILQ skills have a latest passing non-interactive eval."
            ),
            (
                f"- {report['fresh_passing_skill_count']}/{report['skill_count']} "
                "passing evals are fresh against current skill instructions."
            ),
            (
                f"- Score range: `{report.get('minimum_score')}`-"
                f"`{report.get('maximum_score')}`; "
                f"`{report.get('strong_skill_count')}` skills are already "
                "`7+/10`, and "
                f"`{report.get('wilku_ready_skill_count')}` are `10/10`."
            ),
            (
                "- Passing means: Polish operator output, WILQ API usage, "
                "source connectors, evidence IDs, blocked-claim handling and "
                "all hard gates true."
            ),
            (
                "- `blocked correctly / review-only` is a useful state when "
                "WILQ has evidence for the blocker but not enough proof for an "
                "action or claim."
            ),
            (
                "- If this file drifts, regenerate it with `rtk uv run python "
                "scripts/render_skill_coverage_audit.py --write "
                "docs/evals/skill-coverage-audit.md`."
            ),
            "",
            "## Guardrail",
            "",
            "Do not fix future skill failures by adding edge-case prose to references. "
            "If an eval lacks a useful decision, first check whether WILQ API exposes "
            "a typed field for that decision. If not, add or fix the typed "
            "API/dashboard contract, then make the skill consume it.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, default=DEFAULT_EVAL_ROOT)
    parser.add_argument("--skill-root", type=Path, default=DEFAULT_SKILL_ROOT)
    parser.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    parser.add_argument("--write", type=Path, help="write rendered markdown to this path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any skill lacks a passing eval",
    )
    args = parser.parse_args()

    report = build_report(args.eval_root, skill_root=args.skill_root)
    if args.json:
        output = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        output = render_markdown(report)

    if args.write:
        args.write.write_text(output, encoding="utf-8")
        if not output.endswith("\n"):
            args.write.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    if args.strict and not report["pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
