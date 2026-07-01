#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "docs/evals/cases/wilq-skill-eval-cases.json"
SCHEMA_PATH = REPO_ROOT / "docs/evals/schemas/wilq-skill-eval-result.schema.json"
SKILLS_PATH = REPO_ROOT / ".agents/skills"

REQUIRED_RESULT_FIELDS = {
    "skill",
    "language",
    "api_used",
    "source_connectors",
    "evidence_ids",
    "recommendations",
    "action_candidates",
    "blocked",
    "operator_next_step",
    "operator_usefulness_score",
    "decision_quality",
    "notes",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _skill_dirs() -> list[str]:
    if not SKILLS_PATH.exists():
        return []
    return sorted(
        path.name
        for path in SKILLS_PATH.iterdir()
        if path.is_dir() and path.name.startswith("wilq-")
    )


def _case_gaps(case: dict[str, Any]) -> tuple[list[str], list[str]]:
    gaps: list[str] = []
    warnings: list[str] = []

    if not case.get("skill"):
        gaps.append("missing_skill")
    if not (case.get("task_pl") or case.get("messy_task_pl")):
        gaps.append("missing_realistic_polish_task")
    if not case.get("expected_connectors"):
        gaps.append("missing_expected_connectors")
    if not (case.get("expected_terms_pl") or case.get("surface_path")):
        gaps.append("missing_route_or_workflow_oracle")

    has_action_oracle = any(
        case.get(field)
        for field in (
            "expected_action_ids",
            "expected_no_action_ids",
            "forbidden_action_ids",
        )
    )
    has_blocker_oracle = bool(case.get("expected_blocked")) or bool(
        case.get("blocked_claim_terms")
    )
    if not (has_action_oracle or has_blocker_oracle):
        warnings.append("missing_action_or_blocker_oracle")

    if case.get("expected_blocked") is True and not case.get("blocked_claim_terms"):
        warnings.append("blocked_case_without_blocked_claim_terms")
    if case.get("expected_action_ids") and not case.get("expected_validated_action_ids"):
        warnings.append("actions_expected_without_validation_oracle")

    return gaps, warnings


def build_report() -> dict[str, Any]:
    cases = _load_json(CASES_PATH)
    schema = _load_json(SCHEMA_PATH)
    skill_dirs = _skill_dirs()
    case_skills = sorted(case.get("skill") for case in cases if case.get("skill"))

    schema_required = set(schema.get("required", []))
    missing_schema_fields = sorted(REQUIRED_RESULT_FIELDS - schema_required)

    case_reports = []
    total_gaps = 0
    total_warnings = 0
    for case in cases:
        gaps, warnings = _case_gaps(case)
        total_gaps += len(gaps)
        total_warnings += len(warnings)
        case_reports.append(
            {
                "skill": case.get("skill"),
                "gaps": gaps,
                "warnings": warnings,
            }
        )

    missing_skill_cases = sorted(set(skill_dirs) - set(case_skills))
    unknown_case_skills = sorted(set(case_skills) - set(skill_dirs))
    hard_gaps = bool(total_gaps or missing_schema_fields or unknown_case_skills)

    return {
        "schema_version": "wilq_skill_eval_coverage_v1",
        "case_count": len(cases),
        "skill_dir_count": len(skill_dirs),
        "skills_with_cases": case_skills,
        "skill_dirs": skill_dirs,
        "missing_skill_cases": missing_skill_cases,
        "unknown_case_skills": unknown_case_skills,
        "missing_required_schema_fields": missing_schema_fields,
        "case_reports": case_reports,
        "summary": {
            "hard_gap_count": total_gaps
            + len(missing_schema_fields)
            + len(unknown_case_skills),
            "warning_count": total_warnings + len(missing_skill_cases),
            "openai_alignment": [
                "production_like_polish_inputs",
                "structured_output_schema",
                "deterministic_evidence_and_connector_grades",
                "blocked_claim_grades",
                "freshness_handling",
                "operator_usefulness_threshold",
            ],
        },
        "pass": not hard_gaps,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit non-zero on hard gaps")
    args = parser.parse_args()

    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and not report["pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
