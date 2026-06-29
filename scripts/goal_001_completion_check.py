from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.record_marketer_uat_result import build_uat_result_report, load_json


REQUIRED_DOCS = [
    Path("PLAN.md"),
    Path("PLANS.md"),
    Path("docs/PROGRESS.md"),
    Path("docs/CONTEXT.md"),
    Path("docs/goals/001-goal.md"),
    Path("docs/handoffs/2026-06-29-marketer-uat-ready.md"),
]

OWNER_DEFER_ALIASES = {
    "defer_real_marketer_uat": [
        "defer_real_marketer_uat",
        "defer_uat",
        "odroczenie_realnego_uat",
    ],
    "date": ["date", "data"],
    "owner": ["owner", "osoba", "kto"],
    "reason": ["reason", "powód", "dlaczego"],
    "safe_to_show": ["safe_to_show", "co_można_pokazać", "bezpieczny_zakres"],
    "blocked_claims": [
        "blocked_claims",
        "zablokowane_obietnice",
        "zablokowane_claimy",
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check whether Goal 001 has the required marketer UAT proof or "
            "an explicit owner defer note. This guard does not run UAT."
        )
    )
    parser.add_argument("--uat-result", help="Path to a filled real marketer UAT result JSON.")
    parser.add_argument("--owner-defer", help="Path to an explicit owner defer JSON note.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format.",
    )
    args = parser.parse_args()

    report = build_completion_report(
        uat_result=Path(args.uat_result) if args.uat_result else None,
        owner_defer=Path(args.owner_defer) if args.owner_defer else None,
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
) -> dict[str, Any]:
    missing_docs = [str(path) for path in REQUIRED_DOCS if not path.exists()]
    if missing_docs:
        return blocked_report(
            missing_input="required_goal_docs",
            details=missing_docs,
        )

    if uat_result is not None:
        uat_report = validate_uat_result(uat_result)
        if uat_report["valid"]:
            return {
                "status": "complete_with_uat",
                "proof_type": "real_marketer_uat",
                "proof_path": str(uat_result),
                "uat_status": uat_report["overall_status"],
                "ready_without_developer": uat_report["ready_without_developer"],
                "blocked_claims": [],
                "safe_scope": (
                    "Dowód UAT istnieje; domknięcie celu nadal wymaga, żeby "
                    "pozostałe warunki z Goal 001 były prawdziwe."
                ),
            }
        return blocked_report(
            missing_input="valid_real_marketer_uat_result",
            details=uat_report["errors"],
        )

    if owner_defer is not None:
        defer_report = validate_owner_defer(owner_defer)
        if defer_report["valid"]:
            return {
                "status": "owner_deferred",
                "proof_type": "explicit_owner_defer",
                "proof_path": str(owner_defer),
                "owner": defer_report["owner"],
                "date": defer_report["date"],
                "safe_scope": defer_report["safe_to_show"],
                "blocked_claims": defer_report["blocked_claims"],
            }
        return blocked_report(
            missing_input="valid_owner_defer_note",
            details=defer_report["errors"],
        )

    return blocked_report(
        missing_input="real_marketer_uat_result_or_owner_defer",
        details=[
            "Provide --uat-result with a filled marketer UAT JSON, or",
            "provide --owner-defer with an explicit owner defer JSON.",
        ],
    )


def validate_uat_result(path: Path) -> dict[str, Any]:
    try:
        report = build_uat_result_report(load_json(path))
    except RuntimeError as error:
        return {"valid": False, "errors": str(error).splitlines()}
    return {
        "valid": True,
        "overall_status": report["overall_status"],
        "ready_without_developer": report["ready_without_developer"],
    }


def validate_owner_defer(path: Path) -> dict[str, Any]:
    try:
        payload = load_json(path)
    except RuntimeError as error:
        return {"valid": False, "errors": str(error).splitlines()}

    normalized = normalize_defer_payload(payload)
    errors: list[str] = []
    if normalized.get("defer_real_marketer_uat") is not True:
        errors.append("owner defer must set defer_real_marketer_uat to true")
    for key in ["date", "owner", "reason", "safe_to_show"]:
        if is_blank(normalized.get(key)):
            errors.append(f"missing owner defer field: {key}")
    blocked_claims = normalized.get("blocked_claims")
    if not isinstance(blocked_claims, list) or not blocked_claims:
        errors.append("blocked_claims must be a non-empty list")
    elif any(is_blank(item) for item in blocked_claims):
        errors.append("blocked_claims must not contain blank items")

    if errors:
        return {"valid": False, "errors": errors}
    return {
        "valid": True,
        "date": str(normalized["date"]).strip(),
        "owner": str(normalized["owner"]).strip(),
        "reason": str(normalized["reason"]).strip(),
        "safe_to_show": str(normalized["safe_to_show"]).strip(),
        "blocked_claims": [str(item).strip() for item in blocked_claims],
    }


def normalize_defer_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for canonical, aliases in OWNER_DEFER_ALIASES.items():
        for alias in aliases:
            if alias in payload:
                normalized[canonical] = payload[alias]
                break
    return normalized


def blocked_report(*, missing_input: str, details: list[str]) -> dict[str, Any]:
    return {
        "status": "blocked_missing_uat_proof",
        "missing_input": missing_input,
        "details": details,
        "safe_scope": (
            "Zweryfikowany cockpit i gotowy pakiet UAT można pokazać jako "
            "przygotowanie techniczne, nie jako zakończony dowód użyteczności."
        ),
        "blocked_claims": [
            "realny dowód użyteczności dla marketera",
            "gotowość demo bez developera",
            "domknięcie Goal 001",
        ],
        "unblockers": [
            (
                "Przeprowadź 15-minutową sesję z marketerem i przekaż "
                "wypełniony JSON przez --uat-result."
            ),
            (
                "Albo zapisz jawny JSON defer ownera i przekaż go przez "
                "--owner-defer."
            ),
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Sprawdzenie domknięcia Goal 001",
        "",
        f"- Status: `{report['status']}`",
    ]
    if report["status"] == "blocked_missing_uat_proof":
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
        if report.get("blocked_claims"):
            lines.extend(["", "## Obietnice nadal zablokowane przez defer"])
            lines.extend(f"- {item}" for item in report["blocked_claims"])
    return "\n".join(lines).rstrip() + "\n"


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.startswith("<") or text.endswith(">")


if __name__ == "__main__":
    sys.exit(main())
