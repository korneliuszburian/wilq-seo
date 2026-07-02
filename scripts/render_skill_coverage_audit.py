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


def build_report(eval_root: Path = DEFAULT_EVAL_ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for case in _cases():
        skill = str(case["skill"])
        minimum_score = int(case.get("minimum_operator_usefulness_score", 4))
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
        artifact = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
        rows.append(
            {
                "skill": skill,
                "latest_artifact": artifact,
                "score": int(result.get("operator_usefulness_score") or 0),
                "state": _status_label(result),
                "what_it_proves": _what_it_proves(result),
                "remaining_blocker": _remaining_blocker(result),
            }
        )
    return {
        "schema_version": "wilq_latest_skill_coverage_audit_v1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "eval_root": str(eval_root.relative_to(REPO_ROOT))
        if eval_root.is_relative_to(REPO_ROOT)
        else str(eval_root),
        "skill_count": len(rows),
        "passing_skill_count": len(rows) - len(missing),
        "missing_passing_skills": missing,
        "rows": rows,
        "pass": not missing,
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
    parser.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    parser.add_argument("--write", type=Path, help="write rendered markdown to this path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any skill lacks a passing eval",
    )
    args = parser.parse_args()

    report = build_report(args.eval_root)
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
