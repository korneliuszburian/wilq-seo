from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_TEXT_FIELDS = {
    "data_sesji": "data sesji",
    "osoba": "osoba",
    "czas_do_zrozumienia_statusu": "czas do zrozumienia statusu",
    "wybrany_work_item": "wybrany work item",
    "pytania_skad_to_wzielo": 'pytania "skąd to wzięło?"',
    "miejsca_generyczne_off_brand": "miejsca generyczne/off-brand",
    "najwiekszy_brak_produktu": "największy brak produktu",
}

REQUIRED_BOOLEAN_FIELDS = {
    "wilku_rozumie_blokady_pelnego_uat": "czy Wilku rozumie blokady pełnego UAT",
    "service_profile_czytelny": "czy Service Profile jest czytelny",
    "private_review_actions_czytelne": "czy private review actions są czytelne",
    "mozna_przejsc_do_pelnego_content_uat": "czy można przejść do pełnego content UAT",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Waliduje i renderuje wynik Goal 005 Wilku content UAT. "
            "Nie uruchamia UAT i nie zamyka goalu."
        )
    )
    parser.add_argument("input", help="Ścieżka do wypełnionego JSON z wynikiem UAT")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()

    try:
        payload = load_json(Path(args.input))
        report = build_content_uat_result_report(payload)
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


def build_content_uat_result_report(payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_content_uat_payload(payload)
    if errors:
        raise RuntimeError("Niepoprawny wynik Goal 005 content UAT:\n- " + "\n- ".join(errors))

    can_continue = normalize_bool(payload["mozna_przejsc_do_pelnego_content_uat"])
    blockers_understood = normalize_bool(payload["wilku_rozumie_blokady_pelnego_uat"])
    service_profile_clear = normalize_bool(payload["service_profile_czytelny"])
    private_actions_clear = normalize_bool(payload["private_review_actions_czytelne"])
    follow_up_tasks = list_payload(payload.get("follow_up_beads"))
    missing_follow_up = not can_continue and not follow_up_tasks

    ready_for_full_content_uat = (
        can_continue
        and blockers_understood
        and service_profile_clear
        and private_actions_clear
    )

    return {
        "report_type": "goal_005_content_uat_result_v1",
        "date": str(payload["data_sesji"]).strip(),
        "person": str(payload["osoba"]).strip(),
        "selected_work_item": str(payload["wybrany_work_item"]).strip(),
        "time_to_status_understanding": str(
            payload["czas_do_zrozumienia_statusu"]
        ).strip(),
        "blockers_understood": blockers_understood,
        "service_profile_clear": service_profile_clear,
        "private_review_actions_clear": private_actions_clear,
        "source_trace_questions": str(payload["pytania_skad_to_wzielo"]).strip(),
        "generic_or_off_brand_findings": str(
            payload["miejsca_generyczne_off_brand"]
        ).strip(),
        "largest_product_gap": str(payload["najwiekszy_brak_produktu"]).strip(),
        "can_continue_to_full_content_uat": can_continue,
        "follow_up_tasks": follow_up_tasks,
        "overall_status": (
            "ready_for_full_content_uat"
            if ready_for_full_content_uat
            else "needs_follow_up_before_full_content_uat"
        ),
        "missing_follow_up_task": missing_follow_up,
        "safety_note": (
            "Ten raport zapisuje wynik Goal 005 content UAT. Nie promuje private "
            "proposals do source facts, nie zatwierdza knowledge cards i nie "
            "odblokowuje publikacji, WordPress write ani success claims."
        ),
    }


def validate_content_uat_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, label in REQUIRED_TEXT_FIELDS.items():
        if is_blank_or_placeholder(payload.get(key)):
            errors.append(f"Brak pola albo placeholder: {label}")
    for key, label in REQUIRED_BOOLEAN_FIELDS.items():
        if normalize_bool(payload.get(key)) is None:
            errors.append(f"{label} musi mieć wartość tak albo nie")
    if not list_payload(payload.get("follow_up_beads")) and normalize_bool(
        payload.get("mozna_przejsc_do_pelnego_content_uat")
    ) is False:
        errors.append("Gdy pełny content UAT jest zablokowany, wpisz follow_up_beads")
    return errors


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Wynik Goal 005 content UAT",
        "",
        f"- Typ: `{report['report_type']}`",
        f"- Data: `{report['date']}`",
        f"- Osoba: `{report['person']}`",
        f"- Work item: `{report['selected_work_item']}`",
        f"- Status: {visible_status(report['overall_status'])}",
        f"- Czas do zrozumienia statusu: {report['time_to_status_understanding']}",
        "",
        report["safety_note"],
        "",
        "## Ocena",
        "",
        f"- Rozumie blokady pełnego UAT: {visible_bool(report['blockers_understood'])}",
        f"- Service Profile czytelny: {visible_bool(report['service_profile_clear'])}",
        "- Private review actions czytelne: "
        f"{visible_bool(report['private_review_actions_clear'])}",
        "- Można przejść do pełnego content UAT: "
        f"{visible_bool(report['can_continue_to_full_content_uat'])}",
        "",
        "## Źródła i jakość",
        "",
        f"- Pytania \"skąd to wzięło?\": {report['source_trace_questions']}",
        f"- Generyczne/off-brand: {report['generic_or_off_brand_findings']}",
        f"- Największy brak produktu: {report['largest_product_gap']}",
        "",
        "## Follow-up",
        "",
    ]
    for task in report["follow_up_tasks"] or ["brak"]:
        lines.append(f"- {task}")
    return "\n".join(lines).rstrip() + "\n"


def normalize_bool(value: Any) -> bool | None:
    lowered = str(value or "").strip().lower()
    if lowered == "tak":
        return True
    if lowered == "nie":
        return False
    return None


def visible_bool(value: Any) -> str:
    return "tak" if value is True else "nie"


def visible_status(value: Any) -> str:
    if value == "ready_for_full_content_uat":
        return "gotowe do pełnego content UAT"
    return "wymaga follow-up przed pełnym content UAT"


def list_payload(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if not is_blank_or_placeholder(item)]
    if is_blank_or_placeholder(value):
        return []
    return [str(value).strip()]


def is_blank_or_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return not text or text.startswith("<") or text in {"-", "TODO", "todo"}


if __name__ == "__main__":
    raise SystemExit(main())
