from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROUTE_KEYS = ["command_center", "merchant", "content", "ads", "ga4"]
ROUTE_LABELS = {
    "command_center": "Centrum pracy",
    "merchant": "Merchant",
    "content": "Treści",
    "ads": "Google Ads",
    "ga4": "GA4",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and summarize a filled Ekologus marketer UAT result. "
            "This records feedback and task candidates; it does not run UAT."
        )
    )
    parser.add_argument("input", help="Path to a filled UAT result JSON file")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format for the validated UAT result summary.",
    )
    args = parser.parse_args()

    try:
        payload = load_json(Path(args.input))
        report = build_uat_result_report(payload)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"Could not read {path}: {error}") from error
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{path} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return payload


def build_uat_result_report(payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_uat_payload(payload)
    if errors:
        raise RuntimeError("Invalid UAT result:\n- " + "\n- ".join(errors))

    route_results = [
        normalize_route_result(key, payload.get(key)) for key in ROUTE_KEYS
    ]
    failed_routes = [
        result for result in route_results if result["result"] == "fail"
    ]
    task_candidates = build_task_candidates(payload, route_results)
    ready_without_developer = normalize_ready(payload.get("ready_without_developer"))

    return {
        "report_type": "ekologus_marketer_uat_result_v1",
        "date": payload.get("date"),
        "person": payload.get("person"),
        "ready_without_developer": ready_without_developer,
        "overall_status": (
            "ready_for_demo_without_developer"
            if ready_without_developer == "yes" and not failed_routes
            else "needs_tasks_before_unassisted_demo"
        ),
        "route_results": route_results,
        "biggest_real_boost": str(payload.get("biggest_real_boost") or "").strip(),
        "biggest_confusion": str(payload.get("biggest_confusion") or "").strip(),
        "task_candidates": task_candidates,
        "safety_note": (
            "Ten raport zapisuje feedback UAT. Nie odblokowuje publikacji ani "
            "zapisu zmian, automatycznej optymalizacji Ads, naprawy feedu, "
            "obietnic wzrostu Localo, CPA/ROAS ani twierdzeń o przychodach."
        ),
    }


def validate_uat_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["date", "person", "ready_without_developer"]:
        if is_blank_or_placeholder(payload.get(key)):
            errors.append(f"Missing or placeholder field: {key}")
    for key in ROUTE_KEYS:
        if is_blank_or_placeholder(payload.get(key)):
            errors.append(f"Missing or placeholder route result: {key}")
            continue
        route_result = normalize_route_result(key, payload.get(key))
        if route_result["result"] not in {"pass", "fail"}:
            errors.append(f"Route {key} must start with pass or fail")
    if normalize_ready(payload.get("ready_without_developer")) not in {"yes", "no"}:
        errors.append("ready_without_developer must be yes or no")
    return errors


def normalize_route_result(key: str, value: Any) -> dict[str, str]:
    label = ROUTE_LABELS[key]
    if isinstance(value, dict):
        raw_result = str(value.get("result") or "").strip().lower()
        note = str(value.get("note") or value.get("confusion") or "").strip()
    else:
        raw = str(value or "").strip()
        first, _, rest = raw.partition(" ")
        raw_result = first.strip().lower()
        note = rest.strip()
    if raw_result.startswith("pass"):
        result = "pass"
    elif raw_result.startswith("fail"):
        result = "fail"
    else:
        result = "unknown"
    return {
        "key": key,
        "label": label,
        "result": result,
        "note": note,
    }


def build_task_candidates(
    payload: dict[str, Any],
    route_results: list[dict[str, str]],
) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for route in route_results:
        if route["result"] == "fail":
            tasks.append(
                {
                    "category": "demo_ux",
                    "source": route["key"],
                    "task": (
                        f"Popraw niejasność UAT w widoku {route['label']}: "
                        f"{route['note'] or 'brak notatki'}"
                    ),
                }
            )
    biggest_confusion = str(payload.get("biggest_confusion") or "").strip()
    if biggest_confusion:
        tasks.append(
            {
                "category": "demo_ux",
                "source": "biggest_confusion",
                "task": f"Resolve biggest UAT confusion: {biggest_confusion}",
            }
        )
    if normalize_ready(payload.get("ready_without_developer")) == "no":
        tasks.append(
            {
                "category": "demo_readiness",
                "source": "ready_without_developer",
                "task": (
                    "Demo nie jest gotowe bez wsparcia developera; sklasyfikuj "
                    "i popraw blokującą niejasność przed deklaracją gotowości UAT."
                ),
            }
        )
    for task in list_payload(payload.get("new_tasks")):
        if not is_blank_or_placeholder(task):
            tasks.append(
                {
                    "category": "marketer_feedback",
                    "source": "new_tasks",
                    "task": str(task).strip(),
                }
            )
    return tasks


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Wynik UAT marketera Ekologus",
        "",
        f"- Typ: `{report.get('report_type')}`",
        f"- Data: `{report.get('date')}`",
        f"- Osoba: `{report.get('person')}`",
        f"- Status: `{report.get('overall_status')}`",
        f"- Gotowe bez developera: `{report.get('ready_without_developer')}`",
        "",
        report.get("safety_note") or "",
        "",
        "## Wyniki widoków",
        "",
    ]
    for route in list_payload(report.get("route_results")):
        route = mapping(route)
        lines.append(
            f"- `{route.get('result')}` {route.get('label')}: "
            f"{route.get('note') or 'brak notatki'}"
        )
    lines.extend(
        [
            "",
            "## Informacje zwrotne",
            "",
            f"- Największy realny zysk: {report.get('biggest_real_boost') or 'brak'}",
            f"- Największa niejasność: {report.get('biggest_confusion') or 'brak'}",
            "",
            "## Zadania z UAT",
            "",
        ]
    )
    task_candidates = list_payload(report.get("task_candidates"))
    if task_candidates:
        for task in task_candidates:
            task = mapping(task)
            lines.append(
                f"- `{task.get('category')}` z `{task.get('source')}`: "
                f"{task.get('task')}"
            )
    else:
        lines.append("- brak")
    return "\n".join(lines).rstrip() + "\n"


def normalize_ready(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    if lowered in {"yes", "tak"}:
        return "yes"
    if lowered in {"no", "nie"}:
        return "no"
    return lowered


def is_blank_or_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return not value or all(is_blank_or_placeholder(item) for item in value)
    text = str(value).strip()
    return not text or text.startswith("<") or text.endswith(">")


def list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    sys.exit(main())
