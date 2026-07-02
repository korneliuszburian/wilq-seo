from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.record_goal_005_content_uat_result import (
    build_content_uat_result_report,
    load_json,
)

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
}


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
    missing_docs = [str(path) for path in REQUIRED_DOCS if not path.exists()]
    if missing_docs:
        return blocked_report("required_goal_005_docs", missing_docs)

    if uat_result is not None:
        uat_report = validate_uat_result(uat_result, api_base=api_base)
        if uat_report["valid"]:
            return {
                "status": "complete_with_uat",
                "proof_type": "real_wilku_content_uat",
                "proof_path": str(uat_result),
                "uat_status": uat_report["overall_status"],
                "selected_work_item": uat_report["selected_work_item"],
                "shown_review_artifacts": uat_report["shown_review_artifacts"],
                "safe_scope": (
                    "Goal 005 ma zwalidowany wynik realnego UAT. Domknięcie nadal "
                    "wymaga zgodności pozostałych kryteriów goalu i pełnego verify."
                ),
                "blocked_claims": [],
            }
        return blocked_report("valid_goal_005_uat_result", uat_report["errors"])

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
                "blocked_claims": defer_report["blocked_claims"],
            }
        return blocked_report("valid_goal_005_owner_defer", defer_report["errors"])

    return blocked_report(
        "goal_005_uat_result_or_owner_defer",
        [
            "Provide --uat-result with a validated Goal 005 UAT JSON, or",
            "provide --owner-defer with explicit owner defer and residual risk.",
        ],
    )


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
    }


def validate_owner_defer(path: Path) -> dict[str, Any]:
    try:
        payload = load_json(path)
    except RuntimeError as error:
        return {"valid": False, "errors": str(error).splitlines()}

    errors: list[str] = []
    if payload.get(OWNER_DEFER_FIELDS["flag"]) is not True:
        errors.append("owner defer musi ustawić odroczenie_goal_005_uat na true")
    for key in ("date", "owner", "reason", "safe_scope", "residual_risk", "next_review"):
        field = OWNER_DEFER_FIELDS[key]
        if is_blank(payload.get(field)):
            errors.append(f"brak pola owner defer: {field}")
    blocked_claims = payload.get(OWNER_DEFER_FIELDS["blocked_claims"])
    if not isinstance(blocked_claims, list) or not blocked_claims:
        errors.append("czego_nie_wolno_twierdzic musi być niepustą listą")
    elif any(is_blank(item) for item in blocked_claims):
        errors.append("czego_nie_wolno_twierdzic nie może zawierać pustych pozycji")

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
        "blocked_claims": [str(item).strip() for item in blocked_claims],
    }


def blocked_report(missing_input: str, details: list[str]) -> dict[str, Any]:
    return {
        "status": "blocked_missing_goal_005_uat_proof",
        "missing_input": missing_input,
        "details": details,
        "safe_scope": (
            "Service Profile, review handoffs and UAT packet can be shown as "
            "preparation, not as a completed usefulness proof."
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
        if report.get("residual_risk"):
            lines.extend(["", "## Ryzyko rezydualne", report["residual_risk"]])
        if report.get("blocked_claims"):
            lines.extend(["", "## Obietnice nadal zablokowane"])
            lines.extend(f"- {item}" for item in report["blocked_claims"])
    return "\n".join(lines).rstrip() + "\n"


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.startswith("<") or text in {"-", "TODO", "todo"}


if __name__ == "__main__":
    sys.exit(main())
