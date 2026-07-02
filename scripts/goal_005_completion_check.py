from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.audit_skill_eval_coverage import build_report as build_skill_eval_coverage_report
from scripts.claim_ledger_gate_audit import build_report as build_claim_ledger_gate_report
from scripts.dashboard_usefulness_audit import build_report as build_dashboard_usefulness_report
from scripts.record_goal_005_content_uat_result import (
    build_content_uat_input_example,
    build_content_uat_result_report,
    load_json,
)
from scripts.render_skill_coverage_audit import build_report as build_latest_skill_eval_report
from scripts.source_fact_coverage_audit import build_report as build_source_fact_coverage_report

REQUIRED_DOCS = [
    Path("PLANS.md"),
    Path("docs/PROGRESS.md"),
    Path("docs/CONTEXT.md"),
    Path("docs/goals/archive/005-goal.md"),
    Path("docs/handoffs/2026-07-01-wilku-content-uat-ready.md"),
]

OWNER_DEFER_FIELDS = {
    "flag": "odroczenie_goal_005_uat",
    "date": "data",
    "owner": "osoba",
    "reason": "powod",
    "safe_scope": "co_mozna_pokazac",
    "residual_risk": "ryzyko_rezydualne",
    "blocked_claims": "czego_nie_wolno_twierdzic",
    "next_review": "nastepny_przeglad",
    "next_uat_input": "nastepny_input_uat",
}

REQUIRED_OWNER_DEFER_BLOCKED_CLAIMS = [
    "ukończony Goal 005",
    "realny dowód użyteczności dla Wilka",
    "production-depth readiness",
    "gotowość finalnego draftu albo publikacji",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sprawdza, czy Goal 005 ma wymagany proof UAT albo explicit owner "
            "defer z residual risk. Ten guard nie uruchamia UAT i nie zamyka goalu."
        )
    )
    parser.add_argument("--uat-result", help="Ścieżka do wypełnionego Goal 005 UAT JSON.")
    parser.add_argument("--owner-defer", help="Ścieżka do explicit owner defer JSON.")
    parser.add_argument("--api-base", help="Opcjonalnie waliduje UAT result przeciw live WILQ API.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Format outputu.",
    )
    args = parser.parse_args()

    report = build_completion_report(
        uat_result=Path(args.uat_result) if args.uat_result else None,
        owner_defer=Path(args.owner_defer) if args.owner_defer else None,
        api_base=args.api_base,
    )

    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"complete_with_uat", "owner_deferred"} else 1


def build_completion_report(
    *,
    uat_result: Path | None = None,
    owner_defer: Path | None = None,
    api_base: str | None = None,
) -> dict[str, Any]:
    pre_demo_audits = goal_005_pre_demo_audit_summary(api_base=api_base)
    next_uat_input = goal_005_next_uat_input(api_base=api_base)
    missing_docs = [str(path) for path in REQUIRED_DOCS if not path.exists()]
    if missing_docs:
        return blocked_report(
            "required_goal_005_docs",
            missing_docs,
            next_uat_input=next_uat_input,
            pre_demo_audits=pre_demo_audits,
        )

    if uat_result is not None:
        uat_report = validate_uat_result(uat_result, api_base=api_base)
        if (
            uat_report["valid"]
            and uat_report["overall_status"] == "ready_for_full_content_uat"
            and uat_report.get("missing_recommended_review_artifacts")
        ):
            return blocked_report(
                "goal_005_required_review_artifacts",
                [
                    "UAT result is valid, but it skipped recommended plain-language "
                    "review artifacts.",
                    "Show these artifacts to Wilku before claiming Goal 005 completion:",
                    *[
                        str(artifact)
                        for artifact in uat_report["missing_recommended_review_artifacts"]
                    ],
                ],
                uat_live_provenance=uat_report.get("live_provenance_summary"),
                next_uat_input=next_uat_input,
                pre_demo_audits=pre_demo_audits,
            )
        if (
            uat_report["valid"]
            and uat_report["overall_status"] == "ready_for_full_content_uat"
            and uat_report.get("review_follow_up_suggestions")
        ):
            return blocked_report(
                "goal_005_review_scorecard_follow_up",
                [
                    "UAT result is valid, but Wilku's material scorecard still "
                    "contains follow-up suggestions.",
                    "Resolve these scorecard follow-ups before claiming Goal 005 "
                    "completion:",
                    *review_follow_up_detail_lines(
                        uat_report["review_follow_up_suggestions"]
                    ),
                ],
                uat_live_provenance=uat_report.get("live_provenance_summary"),
                uat_review_follow_up_suggestions=uat_report.get(
                    "review_follow_up_suggestions"
                ),
                next_uat_input=next_uat_input,
                pre_demo_audits=pre_demo_audits,
            )
        if uat_report["valid"] and uat_report["overall_status"] == "ready_for_full_content_uat":
            return {
                "status": "complete_with_uat",
                "proof_type": "real_wilku_content_uat",
                "proof_path": str(uat_result),
                "uat_status": uat_report["overall_status"],
                "selected_work_item": uat_report["selected_work_item"],
                "shown_review_artifacts": uat_report["shown_review_artifacts"],
                "uat_live_provenance": uat_report.get("live_provenance_summary"),
                "pre_demo_audits": pre_demo_audits,
                "safe_scope": (
                    "Goal 005 ma zwalidowany wynik realnego UAT. Domknięcie nadal "
                    "wymaga zgodności z pozostałymi kryteriami goalu i pełnego verify."
                ),
                "blocked_claims": [],
            }
        if uat_report["valid"]:
            return blocked_report(
                "goal_005_uat_ready_for_full_content_uat",
                [
                    "UAT result is valid, but it is not ready for Goal 005 completion.",
                    f"UAT status: {uat_report['overall_status']}",
                    "Use this as follow-up evidence, or provide explicit owner defer.",
                    *review_follow_up_detail_lines(
                        uat_report.get("review_follow_up_suggestions") or []
                    ),
                ],
                uat_live_provenance=uat_report.get("live_provenance_summary"),
                uat_review_follow_up_suggestions=uat_report.get(
                    "review_follow_up_suggestions"
                ),
                next_uat_input=next_uat_input,
                pre_demo_audits=pre_demo_audits,
            )
        return blocked_report(
            "valid_goal_005_uat_result",
            uat_report["errors"],
            next_uat_input=next_uat_input,
            pre_demo_audits=pre_demo_audits,
        )

    if owner_defer is not None:
        defer_report = validate_owner_defer(owner_defer)
        if defer_report["valid"]:
            return {
                "status": "owner_deferred",
                "proof_type": "explicit_goal_005_owner_defer",
                "proof_path": str(owner_defer),
                "owner": defer_report["owner"],
                "date": defer_report["date"],
                "safe_scope": defer_report["safe_scope"],
                "residual_risk": defer_report["residual_risk"],
                "next_review": defer_report["next_review"],
                "next_uat_input": defer_report["next_uat_input"],
                "blocked_claims": defer_report["blocked_claims"],
                "pre_demo_audits": pre_demo_audits,
            }
        return blocked_report(
            "valid_goal_005_owner_defer",
            defer_report["errors"],
            next_uat_input=next_uat_input,
            pre_demo_audits=pre_demo_audits,
        )

    return blocked_report(
        "goal_005_uat_result_or_owner_defer",
        [
            "Provide --uat-result with a validated Goal 005 UAT JSON, or",
            "provide --owner-defer with explicit owner defer and residual risk.",
        ],
        next_uat_input=next_uat_input,
        pre_demo_audits=pre_demo_audits,
    )


def goal_005_pre_demo_audit_summary(api_base: str | None = None) -> dict[str, Any]:
    source_report = build_source_fact_coverage_report()
    claim_report = build_claim_ledger_gate_report()
    eval_report = build_skill_eval_coverage_report()
    latest_eval_report = build_latest_skill_eval_report()
    latest_eval_scores = [
        row["score"] for row in latest_eval_report["rows"] if row.get("score") is not None
    ]
    summary = {
        "source_fact_coverage": {
            "pass": source_report["pass"],
            "knowledge_status": source_report["knowledge_status"],
            "ready_for_daily_content": source_report["ready_for_daily_content"],
            "production_depth_percent": source_report["production_depth_percent"],
            "approved_service_percent": source_report["approved_service_percent"],
            "reviewed_fact_percent": source_report["reviewed_fact_percent"],
            "fact_count": source_report["fact_count"],
            "review_action_count": source_report["review_action_count"],
            "private_review_required_count": source_report[
                "private_review_required_count"
            ],
            "next_review_actions": [
                {
                    "action_id": item["action_id"],
                    "review_scope": item["review_scope"],
                    "target_card_title": item["target_card_title"],
                    "decision_options": item.get("decision_options", []),
                }
                for item in source_report.get("review_action_queue", [])[:5]
            ],
        },
        "claim_ledger_gate": {
            "pass": claim_report["pass"],
            "check_count": claim_report["check_count"],
            "passed_count": claim_report["passed_count"],
            "failed_count": claim_report["failed_count"],
            "publish_ready_locked": claim_report["publish_ready_locked"],
            "structured_generation_blocks": claim_report[
                "structured_generation_blocks"
            ],
        },
        "skill_eval_coverage": {
            "pass": eval_report["pass"],
            "case_count": eval_report["case_count"],
            "skill_dir_count": eval_report["skill_dir_count"],
            "hard_gap_count": eval_report["summary"]["hard_gap_count"],
            "warning_count": eval_report["summary"]["warning_count"],
        },
        "latest_skill_eval_results": {
            "pass": latest_eval_report["pass"],
            "passing_skill_count": latest_eval_report["passing_skill_count"],
            "skill_count": latest_eval_report["skill_count"],
            "minimum_score": min(latest_eval_scores) if latest_eval_scores else None,
            "blocked_correctly_count": sum(
                1
                for row in latest_eval_report["rows"]
                if str(row.get("state", "")).startswith("blocked correctly")
            ),
            "missing_passing_skills": latest_eval_report["missing_passing_skills"],
        },
    }
    if api_base:
        dashboard_report = build_dashboard_usefulness_report(api_base)
        knowledge_surface = next(
            (
                surface
                for surface in dashboard_report["surfaces"]
                if surface["surface_id"] == "knowledge"
            ),
            {},
        )
        summary["dashboard_usefulness"] = {
            "pass": dashboard_report["pass"],
            "surface_count": dashboard_report["surface_count"],
            "demo_ready_count": dashboard_report["demo_ready_count"],
            "review_ready_count": dashboard_report["review_ready_count"],
            "blocked_count": dashboard_report["blocked_count"],
            "production_failure_count": dashboard_report[
                "production_failure_count"
            ],
            "knowledge_record_count": knowledge_surface.get("record_count"),
            "knowledge_lineage_count": knowledge_surface.get("lineage_count"),
        }
    return summary


def goal_005_next_uat_input(api_base: str | None = None) -> dict[str, Any]:
    live_context: dict[str, Any] | None = None
    if api_base:
        try:
            from scripts.record_goal_005_content_uat_result import load_live_uat_context

            live_context = load_live_uat_context(api_base)
        except RuntimeError as error:
            return {
                "available": False,
                "blocked_reason": str(error),
                "selected_work_item": "<work_item_id_z_uat_packet>",
                "review_artifacts": [],
                "print_input_command": (
                    "rtk uv run python scripts/record_goal_005_content_uat_result.py "
                    f"--print-input-example --api-base {api_base}"
                ),
            }
    example = build_content_uat_input_example(live_context=live_context)
    return {
        "available": True,
        "selected_work_item": example["wybrany_work_item"],
        "review_artifacts": example.get("pokazane_materialy_review", []),
        "print_input_command": (
            "rtk uv run python scripts/record_goal_005_content_uat_result.py "
            + "--print-input-example"
            + (f" --api-base {api_base}" if api_base else "")
        ),
        "fillable_input": example,
    }


def validate_uat_result(path: Path, *, api_base: str | None = None) -> dict[str, Any]:
    try:
        payload = load_json(path)
        live_context = None
        if api_base:
            from scripts.record_goal_005_content_uat_result import load_live_uat_context

            live_context = load_live_uat_context(api_base)
        report = build_content_uat_result_report(payload, live_context=live_context)
    except RuntimeError as error:
        return {"valid": False, "errors": str(error).splitlines()}
    return {
        "valid": True,
        "overall_status": report["overall_status"],
        "selected_work_item": report["selected_work_item"],
        "shown_review_artifacts": report["shown_review_artifacts"],
        "missing_recommended_review_artifacts": report[
            "missing_recommended_review_artifacts"
        ],
        "review_follow_up_suggestions": report.get("review_follow_up_suggestions")
        or [],
        "live_provenance_summary": uat_live_provenance_summary(
            report.get("live_provenance")
        ),
    }


def uat_live_provenance_summary(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "selected_work_item_found": value.get("selected_work_item_found"),
        "selected_sales_brief_status": value.get("selected_sales_brief_status"),
        "selected_sales_brief_blocker": value.get("selected_sales_brief_blocker"),
        "selected_sales_brief_blockers": value.get("selected_sales_brief_blockers")
        or [],
        "selected_sales_brief_constraint_evidence_ids": value.get(
            "selected_sales_brief_constraint_evidence_ids"
        )
        or [],
        "production_depth_ready": value.get("production_depth_ready"),
    }


def validate_owner_defer(path: Path) -> dict[str, Any]:
    try:
        payload = load_json(path)
    except RuntimeError as error:
        return {"valid": False, "errors": str(error).splitlines()}

    errors: list[str] = []
    if payload.get(OWNER_DEFER_FIELDS["flag"]) is not True:
        errors.append("owner defer musi ustawić odroczenie_goal_005_uat na true")
    for key in (
        "date",
        "owner",
        "reason",
        "safe_scope",
        "residual_risk",
        "next_review",
        "next_uat_input",
    ):
        field = OWNER_DEFER_FIELDS[key]
        if is_blank(payload.get(field)):
            errors.append(f"brak pola owner defer: {field}")
    raw_blocked_claims = payload.get(OWNER_DEFER_FIELDS["blocked_claims"])
    blocked_claim_list: list[Any] = (
        raw_blocked_claims if isinstance(raw_blocked_claims, list) else []
    )
    if not blocked_claim_list:
        errors.append("czego_nie_wolno_twierdzic musi być niepustą listą")
    elif any(is_blank(item) for item in blocked_claim_list):
        errors.append("czego_nie_wolno_twierdzic nie może zawierać pustych pozycji")
    else:
        normalized_claims = {normalize_text(item) for item in blocked_claim_list}
        missing_required_claims = [
            claim
            for claim in REQUIRED_OWNER_DEFER_BLOCKED_CLAIMS
            if normalize_text(claim) not in normalized_claims
        ]
        if missing_required_claims:
            errors.append(
                "czego_nie_wolno_twierdzic musi zawierać: "
                + ", ".join(missing_required_claims)
            )

    if errors:
        return {"valid": False, "errors": errors}
    return {
        "valid": True,
        "date": str(payload[OWNER_DEFER_FIELDS["date"]]).strip(),
        "owner": str(payload[OWNER_DEFER_FIELDS["owner"]]).strip(),
        "reason": str(payload[OWNER_DEFER_FIELDS["reason"]]).strip(),
        "safe_scope": str(payload[OWNER_DEFER_FIELDS["safe_scope"]]).strip(),
        "residual_risk": str(payload[OWNER_DEFER_FIELDS["residual_risk"]]).strip(),
        "next_review": str(payload[OWNER_DEFER_FIELDS["next_review"]]).strip(),
        "next_uat_input": str(payload[OWNER_DEFER_FIELDS["next_uat_input"]]).strip(),
        "blocked_claims": [str(item).strip() for item in blocked_claim_list],
    }


def blocked_report(
    missing_input: str,
    details: list[str],
    *,
    uat_live_provenance: dict[str, Any] | None = None,
    uat_review_follow_up_suggestions: list[dict[str, Any]] | None = None,
    next_uat_input: dict[str, Any] | None = None,
    pre_demo_audits: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "blocked_missing_goal_005_uat_proof",
        "missing_input": missing_input,
        "details": details,
        "uat_live_provenance": uat_live_provenance,
        "uat_review_follow_up_suggestions": uat_review_follow_up_suggestions or [],
        "next_uat_input": next_uat_input or goal_005_next_uat_input(),
        "pre_demo_audits": pre_demo_audits or goal_005_pre_demo_audit_summary(),
        "safe_scope": (
            "Service Profile, materiały review i UAT packet można pokazać jako "
            "przygotowanie, ale nie jako ukończony dowód użyteczności."
        ),
        "blocked_claims": [
            "ukończony Goal 005",
            "realny dowód użyteczności dla Wilka",
            "production-depth readiness",
            "gotowość finalnego draftu albo publikacji",
        ],
        "unblockers": [
            "Przeprowadź realną sesję Wilku i przekaż wynik przez --uat-result.",
            "Albo zapisz explicit owner defer z residual risk przez --owner-defer.",
            "Przed completion claim uruchom pełne rtk scripts/verify.sh.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Sprawdzenie domknięcia Goal 005",
        "",
        f"- Status: `{report['status']}`",
    ]
    if report["status"] == "blocked_missing_goal_005_uat_proof":
        lines.extend(
            [
                f"- Brakujący dowód: `{report['missing_input']}`",
                f"- Bezpieczny zakres: {report['safe_scope']}",
                "",
                "## Zablokowane obietnice",
            ]
        )
        lines.extend(f"- {item}" for item in report["blocked_claims"])
        if report.get("uat_live_provenance"):
            lines.extend(["", "## Live UAT provenance"])
            lines.extend(render_uat_live_provenance(report["uat_live_provenance"]))
        if report.get("uat_review_follow_up_suggestions"):
            lines.extend(["", "## Follow-up ze scorecardu Wilka"])
            lines.extend(
                render_review_follow_up_suggestions(
                    report["uat_review_follow_up_suggestions"]
                )
            )
        if report.get("next_uat_input"):
            lines.extend(["", "## Następny input UAT"])
            lines.extend(render_next_uat_input(report["next_uat_input"]))
        if report.get("pre_demo_audits"):
            lines.extend(["", "## Pre-demo gates"])
            lines.extend(render_pre_demo_audits(report["pre_demo_audits"]))
        lines.extend(["", "## Co odblokowuje domknięcie"])
        lines.extend(f"- {item}" for item in report["unblockers"])
    else:
        lines.extend(
            [
                f"- Typ dowodu: `{report['proof_type']}`",
                f"- Ścieżka dowodu: `{report['proof_path']}`",
                f"- Bezpieczny zakres: {report['safe_scope']}",
            ]
        )
        if report.get("selected_work_item"):
            lines.append(f"- Wybrany work item: `{report['selected_work_item']}`")
        if report.get("shown_review_artifacts"):
            lines.extend(["", "## Pokazane materiały review"])
            lines.extend(f"- `{item}`" for item in report["shown_review_artifacts"])
        if report.get("uat_live_provenance"):
            lines.extend(["", "## Live UAT provenance"])
            lines.extend(render_uat_live_provenance(report["uat_live_provenance"]))
        if report.get("pre_demo_audits"):
            lines.extend(["", "## Pre-demo gates"])
            lines.extend(render_pre_demo_audits(report["pre_demo_audits"]))
        if report.get("residual_risk"):
            lines.extend(["", "## Ryzyko rezydualne", report["residual_risk"]])
        if report.get("next_uat_input"):
            lines.extend(["", "## Następny input UAT", report["next_uat_input"]])
        if report.get("blocked_claims"):
            lines.extend(["", "## Obietnice nadal zablokowane"])
            lines.extend(f"- {item}" for item in report["blocked_claims"])
    return "\n".join(lines).rstrip() + "\n"


def render_uat_live_provenance(value: dict[str, Any]) -> list[str]:
    blockers = value.get("selected_sales_brief_blockers") or []
    blocker_label = value.get("selected_sales_brief_blocker") or "; ".join(blockers) or "brak"
    evidence_ids = value.get("selected_sales_brief_constraint_evidence_ids") or []
    return [
        "- Wybrany work item znaleziony: "
        + ("tak" if value.get("selected_work_item_found") is True else "nie"),
        f"- Sales Brief status: `{value.get('selected_sales_brief_status') or 'brak'}`",
        f"- Sales Brief blocker: {blocker_label}",
        "- Sales Brief constraint evidence: "
        + (", ".join(evidence_ids) or "brak"),
        "- Production-depth ready: "
        + ("tak" if value.get("production_depth_ready") is True else "nie"),
    ]


def render_review_follow_up_suggestions(value: list[dict[str, Any]]) -> list[str]:
    if not value:
        return ["- Brak follow-upów ze scorecardu."]
    return [f"- {line}" for line in review_follow_up_detail_lines(value)]


def review_follow_up_detail_lines(value: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in value:
        low_scores = [
            f"{score.get('label')} {score.get('score')}/5"
            for score in item.get("low_scores", [])
            if isinstance(score, dict)
        ]
        lines.append(
            f"{item.get('material')}: decyzja `{item.get('decision')}`, "
            f"słabe oceny: {', '.join(low_scores) or 'brak'}, "
            f"poprawka: {item.get('requested_fix')}"
        )
    return lines


def render_next_uat_input(value: dict[str, Any]) -> list[str]:
    artifacts = value.get("review_artifacts") or []
    lines = [
        "- Dostępny: " + ("tak" if value.get("available") is True else "nie"),
        f"- Wybrany work item: `{value.get('selected_work_item') or 'brak'}`",
        f"- Komenda do wygenerowania JSON: `{value.get('print_input_command') or 'brak'}`",
    ]
    if value.get("blocked_reason"):
        lines.append(f"- Blokada pobrania live inputu: {value['blocked_reason']}")
    lines.append(
        "- Materiały review: "
        + (", ".join(f"`{artifact}`" for artifact in artifacts) or "brak")
    )
    return lines


def render_pre_demo_audits(value: dict[str, Any]) -> list[str]:
    source = value.get("source_fact_coverage") or {}
    claim = value.get("claim_ledger_gate") or {}
    eval_coverage = value.get("skill_eval_coverage") or {}
    latest_eval = value.get("latest_skill_eval_results") or {}
    dashboard = value.get("dashboard_usefulness") or {}
    lines = [
        "- Source facts: "
        f"`pass={str(source.get('pass')).lower()}`, "
        f"`knowledge_status={source.get('knowledge_status')}`, "
        f"`production_depth={source.get('production_depth_percent')}%`, "
        f"`ready_for_daily_content={str(source.get('ready_for_daily_content')).lower()}`",
        "- Claim Ledger gate: "
        f"`pass={str(claim.get('pass')).lower()}`, "
        f"`checks={claim.get('passed_count')}/{claim.get('check_count')}`, "
        f"`publish_ready_locked={str(claim.get('publish_ready_locked')).lower()}`",
        "- Skill eval coverage: "
        f"`pass={str(eval_coverage.get('pass')).lower()}`, "
        f"`cases={eval_coverage.get('case_count')}`, "
        f"`skills={eval_coverage.get('skill_dir_count')}`, "
        f"`hard_gaps={eval_coverage.get('hard_gap_count')}`",
        "- Latest skill eval results: "
        f"`pass={str(latest_eval.get('pass')).lower()}`, "
        f"`passing={latest_eval.get('passing_skill_count')}/{latest_eval.get('skill_count')}`, "
        f"`minimum_score={latest_eval.get('minimum_score')}`, "
        f"`blocked_correctly={latest_eval.get('blocked_correctly_count')}`",
    ]
    next_review_actions = source.get("next_review_actions") or []
    if next_review_actions:
        lines.append("- Next Service Profile review actions:")
        for item in next_review_actions[:5]:
            decisions = ", ".join(
                str(decision) for decision in item.get("decision_options", [])
            )
            details = (
                f"`{item.get('review_scope')}` -> "
                f"{item.get('target_card_title') or 'brak targetu'}"
            )
            if decisions:
                details += f" (decyzje: {decisions})"
            lines.append(
                f"  - `{item.get('action_id')}`: {details}"
                if item.get("action_id")
                else f"  - {details}"
            )
    if dashboard:
        lines.append(
            "- Dashboard usefulness: "
            f"`pass={str(dashboard.get('pass')).lower()}`, "
            f"`demo_ready={dashboard.get('demo_ready_count')}`, "
            f"`review_ready={dashboard.get('review_ready_count')}`, "
            f"`blocked={dashboard.get('blocked_count')}`, "
            f"`knowledge_records={dashboard.get('knowledge_record_count')}`, "
            f"`knowledge_lineage={dashboard.get('knowledge_lineage_count')}`"
        )
    return lines


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.startswith("<") or text in {"-", "TODO", "todo"}


def normalize_text(value: object) -> str:
    return str(value).strip().casefold()


if __name__ == "__main__":
    sys.exit(main())
