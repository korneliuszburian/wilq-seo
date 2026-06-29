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
POLISH_INPUT_FIELDS = {
    "date": "data",
    "person": "osoba",
    "command_center": "centrum_pracy",
    "merchant": "merchant",
    "content": "treści",
    "ads": "google_ads",
    "ga4": "ga4",
    "biggest_real_boost": "największy_realny_zysk",
    "biggest_confusion": "największa_niejasność",
    "new_tasks": "nowe_zadania",
    "ready_without_developer": "gotowe_bez_developera",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sprawdza i podsumowuje wypełniony wynik UAT marketera Ekologus. "
            "Zapisuje feedback i kandydatów zadań; nie uruchamia UAT."
        )
    )
    parser.add_argument("input", help="Ścieżka do wypełnionego pliku JSON z wynikiem UAT")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Format wyjścia dla sprawdzonego podsumowania UAT.",
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
    parsed_payload = parse_polish_uat_payload(payload)
    errors = validate_uat_payload(payload)
    if errors:
        raise RuntimeError("Niepoprawny wynik UAT:\n- " + "\n- ".join(errors))

    route_results = [normalize_route_result(key, parsed_payload.get(key)) for key in ROUTE_KEYS]
    failed_routes = [result for result in route_results if result["result"] == "fail"]
    task_candidates = build_task_candidates(parsed_payload, route_results)
    ready_without_developer = normalize_ready(parsed_payload.get("ready_without_developer"))

    return {
        "report_type": "ekologus_marketer_uat_result_v1",
        "date": parsed_payload.get("date"),
        "person": parsed_payload.get("person"),
        "ready_without_developer": ready_without_developer,
        "overall_status": (
            "ready_for_demo_without_developer"
            if ready_without_developer == "yes" and not failed_routes
            else "needs_tasks_before_unassisted_demo"
        ),
        "route_results": route_results,
        "biggest_real_boost": str(parsed_payload.get("biggest_real_boost") or "").strip(),
        "biggest_confusion": str(parsed_payload.get("biggest_confusion") or "").strip(),
        "task_candidates": task_candidates,
        "safety_note": (
            "Ten raport zapisuje feedback UAT. Nie odblokowuje publikacji ani "
            "zapisu zmian, automatycznej optymalizacji Ads, naprawy feedu, "
            "obietnic wzrostu Localo, CPA/ROAS ani twierdzeń o przychodach."
        ),
    }


def validate_uat_payload(payload: dict[str, Any]) -> list[str]:
    parsed_payload = parse_polish_uat_payload(payload)
    errors: list[str] = []
    for key in ["date", "person", "ready_without_developer"]:
        if is_blank_or_placeholder(parsed_payload.get(key)):
            errors.append(f"Brak pola UAT albo placeholder: {POLISH_INPUT_FIELDS[key]}")
    for key in ROUTE_KEYS:
        if is_blank_or_placeholder(parsed_payload.get(key)):
            errors.append(f"Brak wyniku UAT dla widoku: {POLISH_INPUT_FIELDS[key]}")
            continue
        route_result = normalize_route_result(key, parsed_payload.get(key))
        if route_result["result"] not in {"pass", "fail"}:
            errors.append(
                f"Wynik widoku {POLISH_INPUT_FIELDS[key]} musi zaczynać się "
                "od zaliczone albo niezaliczone"
            )
    if normalize_ready(parsed_payload.get("ready_without_developer")) not in {"yes", "no"}:
        errors.append("gotowe_bez_developera musi mieć wartość tak albo nie")
    return errors


def normalize_route_result(key: str, value: Any) -> dict[str, str]:
    label = ROUTE_LABELS[key]
    if isinstance(value, dict):
        raw_result = str(value.get("wynik") or "").strip().lower()
        note = str(value.get("notatka") or value.get("niejasność") or "").strip()
    else:
        raw = str(value or "").strip()
        first, _, rest = raw.partition(" ")
        raw_result = first.strip().lower()
        note = rest.strip()
    if raw_result.startswith("zaliczone"):
        result = "pass"
    elif raw_result.startswith("niezaliczone"):
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
                "task": f"Wyjaśnij największą niejasność UAT: {biggest_confusion}",
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
        f"- Status: {visible_overall_status(report.get('overall_status'))}",
        f"- Gotowe bez developera: {visible_ready(report.get('ready_without_developer'))}",
        "",
        report.get("safety_note") or "",
        "",
        "## Wyniki widoków",
        "",
    ]
    for route in list_payload(report.get("route_results")):
        route = mapping(route)
        lines.append(
            f"- `{visible_route_result(route.get('result'))}` "
            f"{route.get('label')}: {route.get('note') or 'brak notatki'}"
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
                f"- {visible_task_category(task.get('category'))} / "
                f"{visible_task_source(task.get('source'))}: {task.get('task')}"
            )
    else:
        lines.append("- brak")
    return "\n".join(lines).rstrip() + "\n"


def normalize_ready(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    if lowered == "tak":
        return "yes"
    if lowered == "nie":
        return "no"
    return "unknown"


def visible_route_result(value: Any) -> str:
    if value == "pass":
        return "zaliczone"
    if value == "fail":
        return "niezaliczone"
    return "nieznane"


def visible_ready(value: Any) -> str:
    if value == "yes":
        return "tak"
    if value == "no":
        return "nie"
    return "nieznane"


def visible_overall_status(value: Any) -> str:
    if value == "ready_for_demo_without_developer":
        return "gotowe do demo bez developera"
    if value == "needs_tasks_before_unassisted_demo":
        return "wymaga poprawek przed demo bez developera"
    return "nieznane"


def visible_task_category(value: Any) -> str:
    if value == "demo_ux":
        return "niejasność demo"
    if value == "demo_readiness":
        return "gotowość demo"
    if value == "marketer_feedback":
        return "feedback marketera"
    return "zadanie"


def visible_task_source(value: Any) -> str:
    route_label = ROUTE_LABELS.get(str(value or ""))
    if route_label:
        return route_label
    if value == "biggest_confusion":
        return "największa niejasność"
    if value == "ready_without_developer":
        return "gotowość bez developera"
    if value == "new_tasks":
        return "nowe zadania"
    return "źródło UAT"


def parse_polish_uat_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        canonical: payload.get(polish)
        for canonical, polish in POLISH_INPUT_FIELDS.items()
    }


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
