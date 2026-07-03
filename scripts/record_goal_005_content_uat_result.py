from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REQUIRED_TEXT_FIELDS = {
    "data_sesji": "data sesji",
    "osoba": "osoba",
    "czas_do_zrozumienia_statusu": "czas do zrozumienia statusu",
    "punkty_niezrozumienia": "punkty niezrozumienia",
    "wybrany_work_item": "wybrany work item",
    "pytania_skad_to_wzielo": 'pytania "skąd to wzięło?"',
    "miejsca_generyczne_off_brand": "miejsca generyczne/off-brand",
    "najwiekszy_brak_produktu": "największy brak produktu",
}

REQUIRED_BOOLEAN_FIELDS = {
    "wilku_rozumie_blokady_pelnego_uat": "czy Wilku rozumie blokady pełnego UAT",
    "service_profile_czytelny": "czy Service Profile jest czytelny",
    "public_service_review_actions_czytelne": (
        "czy public service review actions są czytelne"
    ),
    "private_review_actions_czytelne": "czy private review actions są czytelne",
    "private_policy_review_actions_czytelne": (
        "czy private policy review actions są czytelne"
    ),
    "mozna_przejsc_do_pelnego_content_uat": "czy można przejść do pełnego content UAT",
}
REVIEW_ARTIFACTS_FIELD = "pokazane_materialy_review"
REVIEW_SCORECARD_FIELD = "oceny_materialow_review"
REVIEW_ARTIFACTS_ROOT = Path("docs/handoffs")
RECOMMENDED_REVIEW_ARTIFACTS = [
    "docs/handoffs/2026-07-03-wilku-service-profile-review-now.md",
    "docs/handoffs/2026-07-02-wilq-marketing-content-model.md",
    "docs/handoffs/2026-07-02-co-pokazac-wilkowi.md",
    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md",
    "docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md",
    "docs/handoffs/2026-07-02-wilku-social-history-blocker.md",
]
REVIEW_ARTIFACT_LABELS = {
    "docs/handoffs/2026-07-03-wilku-service-profile-review-now.md": (
        "Service Profile - co pokazać teraz"
    ),
    "docs/handoffs/2026-07-02-wilq-marketing-content-model.md": (
        "WILQ pod marketing i treści"
    ),
    "docs/handoffs/2026-07-02-co-pokazac-wilkowi.md": "Co pokazać Wilkowi",
    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md": (
        "BDO i sprawozdawczość - próbka rozmowy"
    ),
    "docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md": (
        "Ekologus-ai - polityki do oceny"
    ),
    "docs/handoffs/2026-07-02-wilku-social-history-blocker.md": (
        "Historia social - co blokuje ponowne użycie tematu"
    ),
}
REVIEW_SCORECARD_DECISIONS = {"zatwierdź", "popraw", "odrzuć", "odśwież"}
REVIEW_SCORECARD_SCORE_FIELDS = {
    "czytelnosc_1_5": "czytelność",
    "uzytecznosc_1_5": "użyteczność",
    "glos_ekologus_1_5": "głos Ekologus",
    "zaufanie_do_blokad_1_5": "zaufanie do blokad",
    "dopasowanie_cta_1_5": "dopasowanie CTA",
}
PUBLIC_SERVICE_REVIEW_SCOPES = {"public_service_card"}
PRIVATE_SOURCE_REVIEW_SCOPES = {
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
}
PRIVATE_SERVICE_REVIEW_SCOPES = {"private_service_proposal"}
PRIVATE_POLICY_REVIEW_SCOPES = {
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
}
REVIEW_SCOPE_LABELS = {
    "public_service_card": "publiczna karta usługi",
    "private_claim_policy_proposal": "prywatna propozycja polityki twierdzeń",
    "private_evidence_policy_proposal": "prywatna propozycja wymagań dowodowych",
    "private_service_proposal": "prywatna propozycja usługi",
}
REVIEW_REQUIRED_FIELD_LABELS = {
    "action_id": "którą decyzję zapisujemy",
    "target_card_id": "której karty dotyczy decyzja",
    "decision": "werdykt: zatwierdzić, poprawić, oznaczyć jako nieaktualne albo odrzucić",
    "source_trace_clear": "czy źródło i pochodzenie faktu są jasne",
    "blocked_claims_reviewed": "czy zablokowane claimy zostały sprawdzone",
    "notes": "krótka notatka co poprawić albo dlaczego zaakceptować",
}
REVIEW_DECISION_OPTION_LABELS = {
    "approve": "zatwierdź do dalszego użycia",
    "needs_changes": "wróć z poprawkami",
    "stale": "oznacz jako nieaktualne",
    "reject": "odrzuć",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Waliduje i renderuje wynik Goal 005 Wilku content UAT. "
            "Nie uruchamia UAT i nie zamyka goalu."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Ścieżka do wypełnionego JSON z wynikiem UAT",
    )
    parser.add_argument(
        "--print-input-example",
        action="store_true",
        help=(
            "Wypisuje fillable JSON do zapisania przed rozmową z Wilkiem. "
            "To nie jest wynik UAT i celowo zawiera placeholdery."
        ),
    )
    parser.add_argument(
        "--print-session-card",
        action="store_true",
        help=(
            "Wypisuje krótką kartę rozmowy dla Wilka, opartą na tym samym "
            "live UAT input co JSON proof."
        ),
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--api-base",
        help=(
            "Opcjonalnie sprawdza wynik przeciw aktualnej kolejce i Service Profile "
            "z WILQ API."
        ),
    )
    args = parser.parse_args()

    try:
        live_context = load_live_uat_context(args.api_base) if args.api_base else None
        if args.print_session_card:
            print(render_content_uat_session_card(live_context=live_context))
            return 0
        if args.print_input_example:
            print(
                json.dumps(
                    build_content_uat_input_example(live_context=live_context),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if not args.input:
            parser.error(
                "podaj ścieżkę input albo użyj --print-input-example, żeby wygenerować wzór"
            )
        payload = load_json(Path(args.input))
        report = build_content_uat_result_report(payload, live_context=live_context)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0


def build_content_uat_input_example(
    *,
    live_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_work_item = "<work_item_id_z_uat_packet>"
    if live_context is not None:
        selected_work_item = select_uat_candidate_id(live_context) or selected_work_item
    return {
        "data_sesji": "<YYYY-MM-DD>",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "UZUPEŁNIJ: np. 8 minut",
        "punkty_niezrozumienia": (
            "UZUPEŁNIJ: co było niejasne w statusie, blokadach albo kolejce"
        ),
        "wybrany_work_item": selected_work_item,
        REVIEW_ARTIFACTS_FIELD: RECOMMENDED_REVIEW_ARTIFACTS,
        REVIEW_SCORECARD_FIELD: [
            {
                "material": artifact,
                "nazwa_materialu": review_artifact_title(artifact),
                "decyzja": "popraw",
                "czytelnosc_1_5": 3,
                "uzytecznosc_1_5": 3,
                "glos_ekologus_1_5": 3,
                "zaufanie_do_blokad_1_5": 3,
                "dopasowanie_cta_1_5": 3,
                "najwazniejsza_poprawka": (
                    "UZUPEŁNIJ: co poprawić w tym materiale albo wpisz brak"
                ),
            }
            for artifact in RECOMMENDED_REVIEW_ARTIFACTS
        ],
        "pytania_skad_to_wzielo": (
            'UZUPEŁNIJ: gdzie Wilku zapytał "skąd to wzięło?" albo "brak pytań"'
        ),
        "miejsca_generyczne_off_brand": (
            "UZUPEŁNIJ: co brzmiało generycznie/off-brand albo brak uwag"
        ),
        "najwiekszy_brak_produktu": (
            "UZUPEŁNIJ: największa luka przed pełnym content UAT"
        ),
        "wilku_rozumie_blokady_pelnego_uat": "nie",
        "service_profile_czytelny": "nie",
        "public_service_review_actions_czytelne": "nie",
        "private_review_actions_czytelne": "nie",
        "private_policy_review_actions_czytelne": "nie",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": [
            "<wilq-seo-...: opisz follow-up po sesji, jeżeli pełny UAT jest zablokowany>"
        ],
    }


def render_content_uat_session_card(
    *,
    live_context: dict[str, Any] | None = None,
) -> str:
    example = build_content_uat_input_example(live_context=live_context)
    selected_work_item = str(example["wybrany_work_item"])
    provenance = live_uat_provenance(
        live_context=live_context,
        selected_work_item=selected_work_item,
    )
    artifacts = example.get(REVIEW_ARTIFACTS_FIELD) or []
    first_review = first_service_profile_review_plain_label(provenance)
    required_fields = first_service_profile_review_required_fields_plain_label(
        provenance
    )
    decision_options = first_service_profile_review_decision_options_label(provenance)
    command = (
        "rtk uv run python scripts/record_goal_005_content_uat_result.py "
        "--print-input-example"
        + (
            f" --api-base {live_context.get('api_base')}"
            if isinstance(live_context, dict) and live_context.get("api_base")
            else ""
        )
    )
    lines = [
        "# Goal 005 - karta rozmowy z Wilkiem",
        "",
        "## Decyzja na sesję",
        "",
        (
            "Sprawdzamy, czy obecny Service Profile, materiały do oceny i pierwszy "
            "kandydat treści są wystarczająco czytelne, żeby przejść do "
            "pełnego testu treści. To nie zatwierdza publikacji ani wiedzy do "
            "finalnych treści."
        ),
        "",
        "## Aktualny status WILQ",
        "",
        "- Temat rozmowy: "
        f"{selected_content_candidate_title(provenance)}",
        "- URL / miejsce w serwisie: "
        f"{selected_content_candidate_url(provenance)}",
        "- Decyzja contentowa WILQ: "
        f"{selected_content_candidate_mode(provenance)}",
        "- Dlaczego ten temat: "
        f"{selected_content_candidate_reason(provenance)}",
        "- Bezpieczny następny krok: "
        f"{selected_content_candidate_next_step(provenance)}",
        "- Zatwierdzona wiedza do finalnych treści: "
        f"{visible_bool(provenance.get('production_depth_ready') is True)}",
        "",
        "## Pierwsza decyzja w Service Profile",
        "",
        f"- {first_review}",
        f"- Możliwe decyzje: {decision_options}",
        f"- Co trzeba ocenić: {required_fields}",
        "",
        "## Co pokazać",
        "",
        *[f"- {review_artifact_label(artifact)}" for artifact in artifacts],
        "",
        "## Pytania do Wilka",
        "",
        "- Czy rozumiesz, czemu pełny test treści jest jeszcze zablokowany?",
        "- Czy Service Profile i pierwsza karta BDO są czytelne?",
        "- Gdzie pytasz: skąd WILQ to wziął?",
        "- Co brzmi generycznie albo nie jak Ekologus?",
        "- Co trzeba poprawić, zanim puścimy pełny test treści?",
        "",
        "## Jak zapisać dowód",
        "",
        f"1. Wygeneruj wzór wyniku rozmowy: `{command}`",
        "2. Uzupełnij pola po rozmowie.",
        (
            "3. Sprawdź wynik komendą: `rtk uv run python "
            "scripts/record_goal_005_content_uat_result.py <plik.json> "
            + (
                f"--api-base {live_context.get('api_base')}`"
                if isinstance(live_context, dict) and live_context.get("api_base")
                else "`"
            )
        ),
        "",
        "## Dane techniczne do zapisu dowodu",
        "",
        f"- Work item ID: `{selected_work_item}`",
        "- Kolejka content: "
        f"`{provenance.get('queue_status') or 'nie sprawdzono live API'}`",
        "- Sales Brief status: "
        f"`{provenance.get('selected_sales_brief_status') or 'brak live proof'}`",
        "- Service Profile production-depth: "
        f"`{visible_bool(provenance.get('production_depth_ready') is True)}`",
        "- Źródła danych: "
        f"{', '.join(provenance.get('selected_source_connectors') or []) or 'brak live proof'}",
        "- Service Profile review JSON: "
        f"{first_service_profile_review_label(provenance)}",
    ]
    return "\n".join(lines).rstrip() + "\n"


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


def build_content_uat_result_report(
    payload: dict[str, Any],
    *,
    live_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    errors = validate_content_uat_payload(payload, live_context=live_context)
    if errors:
        raise RuntimeError("Niepoprawny wynik Goal 005 content UAT:\n- " + "\n- ".join(errors))

    can_continue = normalize_bool(payload["mozna_przejsc_do_pelnego_content_uat"])
    blockers_understood = normalize_bool(payload["wilku_rozumie_blokady_pelnego_uat"])
    service_profile_clear = normalize_bool(payload["service_profile_czytelny"])
    public_actions_clear = normalize_bool(
        payload["public_service_review_actions_czytelne"]
    )
    private_actions_clear = normalize_bool(payload["private_review_actions_czytelne"])
    private_policy_actions_clear = normalize_bool(
        payload["private_policy_review_actions_czytelne"]
    )
    follow_up_tasks = list_payload(payload.get("follow_up_beads"))
    shown_review_artifacts = review_artifact_paths(payload.get(REVIEW_ARTIFACTS_FIELD))
    review_scorecard = review_scorecard_payload(
        payload.get(REVIEW_SCORECARD_FIELD),
        shown_review_artifacts=shown_review_artifacts,
    )
    missing_recommended_review_artifacts = recommended_review_artifact_gaps(
        shown_review_artifacts
    )
    missing_follow_up = not can_continue and not follow_up_tasks
    selected_work_item = str(payload["wybrany_work_item"]).strip()
    live_provenance = live_uat_provenance(
        live_context=live_context,
        selected_work_item=selected_work_item,
    )

    ready_for_full_content_uat = (
        can_continue
        and blockers_understood
        and service_profile_clear
        and public_actions_clear
        and private_actions_clear
        and private_policy_actions_clear
    )

    return {
        "report_type": "goal_005_content_uat_result_v1",
        "date": str(payload["data_sesji"]).strip(),
        "person": str(payload["osoba"]).strip(),
        "selected_work_item": selected_work_item,
        "time_to_status_understanding": str(
            payload["czas_do_zrozumienia_statusu"]
        ).strip(),
        "confusion_points": str(payload["punkty_niezrozumienia"]).strip(),
        "blockers_understood": blockers_understood,
        "service_profile_clear": service_profile_clear,
        "public_service_review_actions_clear": public_actions_clear,
        "private_review_actions_clear": private_actions_clear,
        "private_policy_review_actions_clear": private_policy_actions_clear,
        "source_trace_questions": str(payload["pytania_skad_to_wzielo"]).strip(),
        "generic_or_off_brand_findings": str(
            payload["miejsca_generyczne_off_brand"]
        ).strip(),
        "largest_product_gap": str(payload["najwiekszy_brak_produktu"]).strip(),
        "can_continue_to_full_content_uat": can_continue,
        "shown_review_artifacts": shown_review_artifacts,
        "review_scorecard": review_scorecard,
        "review_scorecard_summary": review_scorecard_summary(review_scorecard),
        "review_follow_up_suggestions": review_follow_up_suggestions(review_scorecard),
        "missing_recommended_review_artifacts": missing_recommended_review_artifacts,
        "follow_up_tasks": follow_up_tasks,
        "live_provenance": live_provenance,
        "overall_status": (
            "ready_for_full_content_uat"
            if ready_for_full_content_uat
            else "needs_follow_up_before_full_content_uat"
        ),
        "missing_follow_up_task": missing_follow_up,
        "safety_note": (
            "Ten raport zapisuje wynik Goal 005 content UAT. Nie promuje private "
            "proposals do source facts, nie zatwierdza publicznych service cards "
            "i nie odblokowuje publikacji, WordPress write ani success claims."
        ),
    }


def validate_content_uat_payload(
    payload: dict[str, Any],
    *,
    live_context: dict[str, Any] | None = None,
) -> list[str]:
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
    errors.extend(validate_review_artifacts(payload.get(REVIEW_ARTIFACTS_FIELD)))
    errors.extend(
        validate_review_scorecard(
            payload.get(REVIEW_SCORECARD_FIELD),
            shown_review_artifacts=review_artifact_paths(
                payload.get(REVIEW_ARTIFACTS_FIELD)
            ),
        )
    )
    if live_context is not None:
        selected_work_item = str(payload.get("wybrany_work_item") or "").strip()
        candidate_ids = live_context_candidate_ids(live_context)
        if selected_work_item and selected_work_item not in candidate_ids:
            errors.append(
                "Wybrany work item nie występuje w aktualnym live UAT packet: "
                f"{selected_work_item}"
            )
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
        f"- Punkty niezrozumienia: {report['confusion_points']}",
        "",
        report["safety_note"],
        "",
        "## Live provenance",
        "",
        render_live_provenance(report.get("live_provenance")),
        "",
        "## Ocena",
        "",
        f"- Rozumie blokady pełnego UAT: {visible_bool(report['blockers_understood'])}",
        f"- Service Profile czytelny: {visible_bool(report['service_profile_clear'])}",
        "- Public service review actions czytelne: "
        f"{visible_bool(report['public_service_review_actions_clear'])}",
        "- Private review actions czytelne: "
        f"{visible_bool(report['private_review_actions_clear'])}",
        "- Private policy review actions czytelne: "
        f"{visible_bool(report['private_policy_review_actions_clear'])}",
        "- Można przejść do pełnego content UAT: "
        f"{visible_bool(report['can_continue_to_full_content_uat'])}",
        "",
        "## Pokazane materiały review",
        "",
        *[f"- `{artifact}`" for artifact in report["shown_review_artifacts"]],
        "",
        "## Scorecard Wilka",
        "",
        render_review_scorecard_summary(report.get("review_scorecard_summary")),
        "",
        *render_review_scorecard(report.get("review_scorecard")),
        "",
        "## Sugestie follow-up z ocen",
        "",
        *render_review_follow_up_suggestions(
            report.get("review_follow_up_suggestions")
        ),
        "",
        *render_missing_recommended_review_artifacts(report),
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


def render_review_scorecard_summary(value: Any) -> str:
    if not isinstance(value, dict):
        return "- Brak scorecardu materiałów review."
    decisions = value.get("decision_counts")
    decision_label = ", ".join(
        f"{decision}: {count}"
        for decision, count in sorted((decisions or {}).items())
    )
    return "\n".join(
        [
            f"- Materiały ocenione: `{value.get('artifact_count')}`",
            f"- Średnia czytelność: `{value.get('average_clarity')}`/5",
            f"- Średnia użyteczność: `{value.get('average_usefulness')}`/5",
            f"- Decyzje: {decision_label or 'brak'}",
        ]
    )


def render_review_scorecard(value: Any) -> list[str]:
    rows = [row for row in raw_list_payload(value) if isinstance(row, dict)]
    if not rows:
        return ["- Brak ocen materiałów review."]
    lines: list[str] = []
    for row in rows:
        label = row.get("nazwa_materialu") or review_artifact_title(row.get("material"))
        lines.extend(
            [
                f"- {label}",
                f"  - proof: `{row.get('material')}`",
                f"  - decyzja: {row.get('decyzja')}",
                "  - oceny: "
                f"czytelność {row.get('czytelnosc_1_5')}/5, "
                f"użyteczność {row.get('uzytecznosc_1_5')}/5, "
                f"głos Ekologus {row.get('glos_ekologus_1_5')}/5, "
                f"zaufanie do blokad {row.get('zaufanie_do_blokad_1_5')}/5, "
                f"CTA {row.get('dopasowanie_cta_1_5')}/5",
                f"  - najważniejsza poprawka: {row.get('najwazniejsza_poprawka')}",
            ]
        )
    return lines


def render_review_follow_up_suggestions(value: Any) -> list[str]:
    rows = [row for row in raw_list_payload(value) if isinstance(row, dict)]
    if not rows:
        return ["- Brak automatycznych sugestii ze scorecardu."]
    lines: list[str] = []
    for row in rows:
        label = row.get("nazwa_materialu") or review_artifact_title(row.get("material"))
        low_scores = [
            f"{item.get('label')} {item.get('score')}/5"
            for item in raw_list_payload(row.get("low_scores"))
            if isinstance(item, dict)
        ]
        lines.append(
            "- "
            f"{label}: decyzja `{row.get('decision')}`; "
            f"słabe oceny: {', '.join(low_scores) or 'brak'}; "
            f"poprawka: {row.get('requested_fix')}"
        )
    return lines


def render_missing_recommended_review_artifacts(report: dict[str, Any]) -> list[str]:
    missing = report.get("missing_recommended_review_artifacts") or []
    if not missing:
        return []
    return [
        "## Ostrzeżenia materiałów review",
        "",
        *[
            f"- Nie pokazano rekomendowanego prostego przewodnika: `{artifact}`"
            for artifact in missing
        ],
        "",
    ]


def load_live_uat_context(api_base: str) -> dict[str, Any]:
    health = request_json(api_base, "GET", "/api/health")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise RuntimeError(f"WILQ API health is not ok at {api_base}")
    queue = request_json(api_base, "GET", "/api/content/work-items/queue")
    service_profile = request_json(api_base, "GET", "/api/content/service-profile")
    if not isinstance(queue, dict):
        raise RuntimeError("Live content work-item queue must be an object")
    if not isinstance(service_profile, dict):
        raise RuntimeError("Live Service Profile must be an object")
    return {
        "api_base": api_base.rstrip("/"),
        "queue": queue,
        "service_profile": service_profile,
        "sales_brief_traces": load_sales_brief_traces(api_base, queue),
    }


def load_sales_brief_traces(api_base: str, queue: dict[str, Any]) -> dict[str, Any]:
    traces: dict[str, Any] = {}
    for candidate in raw_list_payload(queue.get("candidates")):
        if not isinstance(candidate, dict):
            continue
        work_item_id = str(candidate.get("work_item_id") or "").strip()
        if not work_item_id:
            continue
        try:
            snapshot = request_json(
                api_base,
                "GET",
                f"/api/content/work-items/{work_item_id}/snapshot",
                timeout=120,
            )
        except RuntimeError as error:
            traces[work_item_id] = {
                "status": "unavailable",
                "blocker": str(error),
            }
            continue
        traces[work_item_id] = sales_brief_trace_from_snapshot(snapshot)
    return traces


def sales_brief_trace_from_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"status": "missing", "blocker": "snapshot nie jest obiektem"}
    sales_brief_stage = snapshot.get("sales_brief")
    if not isinstance(sales_brief_stage, dict):
        return {"status": "missing", "blocker": "snapshot nie zawiera sales_brief"}
    result = sales_brief_stage.get("sales_brief_result")
    if not isinstance(result, dict):
        return {
            "status": "missing",
            "blocker": "snapshot nie zawiera sales_brief_result",
        }
    brief = result.get("brief")
    blockers = result.get("blockers")
    if not isinstance(brief, dict):
        return {
            "status": "blocked",
            "blockers": blockers if isinstance(blockers, list) else [],
        }
    signal_quality = brief.get("signal_quality")
    constraints = [
        constraint
        for constraint in raw_list_payload(brief.get("knowledge_constraints"))
        if isinstance(constraint, dict)
    ]
    evidence_ids = sorted(
        {
            str(evidence_id)
            for constraint in constraints
            for evidence_id in raw_list_payload(constraint.get("evidence_ids"))
            if evidence_id
        }
    )
    return {
        "status": "ready",
        "signal_quality_status_label": (
            signal_quality.get("status_label")
            if isinstance(signal_quality, dict)
            else None
        ),
        "knowledge_constraint_count": len(constraints),
        "knowledge_constraint_evidence_ids": evidence_ids,
    }


def request_json(api_base: str, method: str, path: str, *, timeout: int = 60) -> Any:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}{path}",
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"HTTP {error.code} from {path}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach WILQ API at {api_base}: {error.reason}") from error


def live_context_candidate_ids(live_context: dict[str, Any]) -> set[str]:
    queue = live_context.get("queue")
    if not isinstance(queue, dict):
        return set()
    return {
        str(candidate.get("work_item_id") or "").strip()
        for candidate in raw_list_payload(queue.get("candidates"))
        if isinstance(candidate, dict) and candidate.get("work_item_id")
    }


def select_uat_candidate_id(live_context: dict[str, Any]) -> str | None:
    queue = live_context.get("queue")
    if not isinstance(queue, dict):
        return None
    candidates = [
        candidate
        for candidate in raw_list_payload(queue.get("candidates"))
        if isinstance(candidate, dict) and candidate.get("work_item_id")
    ]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            -uat_candidate_score(candidate, live_context),
            str(candidate.get("work_item_id") or ""),
        ),
    )
    return str(ranked[0].get("work_item_id") or "").strip() or None


def uat_candidate_score(candidate: dict[str, Any], live_context: dict[str, Any]) -> int:
    score = 0
    mode = str(candidate.get("recommended_mode") or "").strip()
    if mode in {"refresh", "merge", "refresh_or_merge"}:
        score += 50
    elif mode == "block":
        score -= 20
    if candidate.get("final_canonical_url") or candidate.get("intended_final_url"):
        score += 20
    if candidate.get("source_public_url"):
        score += 10
    if candidate.get("preflight_status") in {"plan_allowed", "ready"}:
        score += 10
    if candidate.get("source_connectors"):
        score += 5
    traces = live_context.get("sales_brief_traces")
    if isinstance(traces, dict):
        trace = traces.get(str(candidate.get("work_item_id") or ""))
        if isinstance(trace, dict):
            if trace.get("status") == "ready":
                score += 20
            elif trace.get("status") == "blocked":
                score += 5
    return score


def live_uat_provenance(
    *,
    live_context: dict[str, Any] | None,
    selected_work_item: str,
) -> dict[str, Any] | None:
    if live_context is None:
        return None
    raw_queue = live_context.get("queue")
    queue: dict[str, Any] = raw_queue if isinstance(raw_queue, dict) else {}
    raw_service_profile = live_context.get("service_profile")
    service_profile: dict[str, Any] = (
        raw_service_profile if isinstance(raw_service_profile, dict) else {}
    )
    candidates = [
        candidate
        for candidate in raw_list_payload(queue.get("candidates"))
        if isinstance(candidate, dict)
    ]
    selected = next(
        (
            candidate
            for candidate in candidates
            if str(candidate.get("work_item_id") or "") == selected_work_item
        ),
        {},
    )
    raw_coverage = service_profile.get("coverage_summary")
    coverage: dict[str, Any] = raw_coverage if isinstance(raw_coverage, dict) else {}
    raw_review_summary = service_profile.get("review_action_summary")
    review_summary: dict[str, Any] = (
        raw_review_summary if isinstance(raw_review_summary, dict) else {}
    )
    raw_private_summary = service_profile.get("private_source_proposal_summary")
    private_summary: dict[str, Any] = (
        raw_private_summary if isinstance(raw_private_summary, dict) else {}
    )
    raw_sales_brief_traces = live_context.get("sales_brief_traces")
    sales_brief_traces: dict[str, Any] = (
        raw_sales_brief_traces if isinstance(raw_sales_brief_traces, dict) else {}
    )
    raw_selected_sales_brief_trace = sales_brief_traces.get(selected_work_item)
    selected_sales_brief_trace: dict[str, Any] = (
        raw_selected_sales_brief_trace
        if isinstance(raw_selected_sales_brief_trace, dict)
        else {}
    )
    review_actions = [
        action
        for action in raw_list_payload(service_profile.get("review_actions"))
        if isinstance(action, dict)
    ]
    first_review_action_id = review_summary.get("first_review_action_id")
    first_review_action = next(
        (
            action
            for action in review_actions
            if action.get("action_id") == first_review_action_id
        ),
        {},
    )
    return {
        "api_base": live_context.get("api_base"),
        "queue_status": queue.get("queue_status"),
        "candidate_count": queue.get("candidate_count"),
        "actionable_candidate_count": queue.get("actionable_candidate_count"),
        "selected_work_item_found": bool(selected),
        "selected_title": selected.get("title"),
        "selected_topic": selected.get("topic"),
        "selected_url": selected.get("final_canonical_url")
        or selected.get("intended_final_url")
        or selected.get("source_public_url"),
        "selected_recommended_mode": selected.get("recommended_mode"),
        "selected_recommended_mode_label": selected.get("recommended_mode_label"),
        "selected_reason": selected.get("reason"),
        "selected_safe_next_step": selected.get("safe_next_step"),
        "selected_evidence_ids": selected.get("evidence_ids") or [],
        "selected_source_connectors": selected.get("source_connectors") or [],
        "selected_sales_brief_status": selected_sales_brief_trace.get("status"),
        "selected_sales_brief_blocker": selected_sales_brief_trace.get("blocker"),
        "selected_sales_brief_blockers": sales_brief_blocker_labels(
            selected_sales_brief_trace.get("blockers")
        ),
        "selected_sales_brief_constraint_count": selected_sales_brief_trace.get(
            "knowledge_constraint_count"
        ),
        "selected_sales_brief_constraint_evidence_ids": selected_sales_brief_trace.get(
            "knowledge_constraint_evidence_ids"
        )
        or [],
        "service_profile_read_only": service_profile.get("read_only"),
        "production_depth_ready": coverage.get("ready_for_daily_content"),
        "first_service_profile_review_action_id": first_review_action_id,
        "first_service_profile_review_label": review_summary.get(
            "first_review_action_label"
        ),
        "first_service_profile_review_scope": review_summary.get(
            "first_review_action_scope"
        ),
        "first_service_profile_review_target_card_id": review_summary.get(
            "first_review_action_target_card_id"
        ),
        "first_service_profile_review_required_fields": review_summary.get(
            "first_review_required_fields"
        )
        or [],
        "first_service_profile_review_next_step": review_summary.get(
            "first_review_safe_next_step"
        ),
        "first_service_profile_review_decision_options": first_review_action.get(
            "decision_options"
        )
        or [],
        "public_service_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PUBLIC_SERVICE_REVIEW_SCOPES
            ]
        ),
        "private_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PRIVATE_SOURCE_REVIEW_SCOPES
            ]
        ),
        "private_service_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PRIVATE_SERVICE_REVIEW_SCOPES
            ]
        ),
        "private_policy_review_action_count": len(
            [
                action
                for action in review_actions
                if review_scope(action) in PRIVATE_POLICY_REVIEW_SCOPES
            ]
        ),
        "private_proposal_promotion_ready": private_summary.get("promotion_ready"),
    }


def review_scope(action: dict[str, Any]) -> str:
    return str(action.get("review_scope") or "").strip()


def first_service_profile_review_label(value: dict[str, Any]) -> str:
    action_id = value.get("first_service_profile_review_action_id")
    label = value.get("first_service_profile_review_label")
    scope = value.get("first_service_profile_review_scope")
    target = value.get("first_service_profile_review_target_card_id")
    next_step = humanize_review_decision_text(
        value.get("first_service_profile_review_next_step")
    )
    if not any([action_id, label, scope, target, next_step]):
        return "brak"
    parts = [
        f"`{action_id}`" if action_id else None,
        str(label) if label else None,
        f"scope {review_scope_label(scope)}" if scope else None,
        f"target `{target}`" if target else None,
        str(next_step) if next_step else None,
    ]
    return " - ".join(part for part in parts if part)


def first_service_profile_review_plain_label(value: dict[str, Any]) -> str:
    label = value.get("first_service_profile_review_label")
    next_step = humanize_review_decision_text(
        value.get("first_service_profile_review_next_step")
    )
    if not any([label, next_step]):
        return "Brak pierwszej decyzji review w live packet."
    parts = [
        str(label) if label else None,
        str(next_step) if next_step else None,
    ]
    return " - ".join(part for part in parts if part)


def review_scope_label(value: Any) -> str:
    raw = str(value)
    return REVIEW_SCOPE_LABELS.get(raw, raw.replace("_", " "))


def first_service_profile_review_required_fields_label(value: dict[str, Any]) -> str:
    return ", ".join(value.get("first_service_profile_review_required_fields") or []) or "brak"


def first_service_profile_review_required_fields_plain_label(
    value: dict[str, Any],
) -> str:
    fields = value.get("first_service_profile_review_required_fields") or []
    labels = [REVIEW_REQUIRED_FIELD_LABELS.get(str(field), str(field)) for field in fields]
    return "; ".join(labels) or "brak"


def first_service_profile_review_decision_options_label(value: dict[str, Any]) -> str:
    options = value.get("first_service_profile_review_decision_options") or []
    labels = [REVIEW_DECISION_OPTION_LABELS.get(str(option), str(option)) for option in options]
    return "; ".join(labels) or "brak opcji z live packet"


def selected_content_candidate_title(value: dict[str, Any]) -> str:
    return str(value.get("selected_title") or value.get("selected_topic") or "brak live tytułu")


def selected_content_candidate_url(value: dict[str, Any]) -> str:
    return str(value.get("selected_url") or "brak live URL")


def selected_content_candidate_mode(value: dict[str, Any]) -> str:
    return str(
        value.get("selected_recommended_mode_label")
        or value.get("selected_recommended_mode")
        or "brak live decyzji"
    )


def selected_content_candidate_reason(value: dict[str, Any]) -> str:
    return str(value.get("selected_reason") or "brak live uzasadnienia")


def selected_content_candidate_next_step(value: dict[str, Any]) -> str:
    return str(value.get("selected_safe_next_step") or "brak live następnego kroku")


def review_artifact_label(artifact: Any) -> str:
    path = str(artifact)
    label = review_artifact_title(path)
    if label:
        return f"{label} (`{path}`)"
    return f"`{path}`"


def review_artifact_title(artifact: Any) -> str:
    return REVIEW_ARTIFACT_LABELS.get(str(artifact), "")


def humanize_review_decision_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    replacements = {
        "approve/needs_changes/stale/reject": (
            "zatwierdź, wróć z poprawkami, oznacz jako nieaktualne albo odrzuć"
        ),
        "approve": "zatwierdź",
        "needs_changes": "wróć z poprawkami",
        "stale": "oznacz jako nieaktualne",
        "reject": "odrzuć",
    }
    for raw, label in replacements.items():
        text = text.replace(raw, label)
    return text


def render_live_provenance(value: Any) -> str:
    if not isinstance(value, dict):
        return "- Nie sprawdzono live WILQ API dla tego wyniku."
    return "\n".join(
        [
            f"- API: `{value.get('api_base')}`",
            "- Kolejka: "
            f"`{value.get('queue_status')}`, kandydaci: `{value.get('candidate_count')}`",
            "- Wybrany work item znaleziony w live packet: "
            f"{visible_bool(value.get('selected_work_item_found') is True)}",
            f"- Tryb wybranego itemu: `{value.get('selected_recommended_mode')}`",
            "- Źródła wybranego itemu: "
            f"{', '.join(value.get('selected_source_connectors') or []) or 'brak'}",
            "- Sales Brief wybranego itemu: "
            f"`{value.get('selected_sales_brief_status') or 'brak'}`",
            "- Sales Brief blocker: "
            f"{sales_brief_blocker_label(value)}",
            "- Sales Brief constraint evidence: "
            f"{sales_brief_evidence_label(value)}",
            "- Service Profile read-only: "
            f"{visible_bool(value.get('service_profile_read_only') is True)}",
            "- Production-depth ready: "
            f"{visible_bool(value.get('production_depth_ready') is True)}",
            "- Pierwszy Service Profile review: "
            f"{first_service_profile_review_label(value)}",
            "- Wymagane pola pierwszego review: "
            f"{first_service_profile_review_required_fields_label(value)}",
            "- Public service review actions: "
            f"`{value.get('public_service_review_action_count')}`",
            "- Private review actions: "
            f"`{value.get('private_review_action_count')}`",
            "- Private service review actions: "
            f"`{value.get('private_service_review_action_count')}`",
            "- Private policy review actions: "
            f"`{value.get('private_policy_review_action_count')}`",
            "- Private proposal promotion ready: "
            f"{visible_bool(value.get('private_proposal_promotion_ready') is True)}",
        ]
    )


def sales_brief_blocker_label(value: dict[str, Any]) -> str:
    blocker = value.get("selected_sales_brief_blocker")
    if blocker:
        return str(blocker)
    blockers = sales_brief_blocker_labels(value.get("selected_sales_brief_blockers"))
    return "; ".join(blockers) or "brak"


def sales_brief_evidence_label(value: dict[str, Any]) -> str:
    evidence_ids = value.get("selected_sales_brief_constraint_evidence_ids") or []
    return ", ".join(evidence_ids) or "brak"


def sales_brief_blocker_labels(value: Any) -> list[str]:
    labels: list[str] = []
    for item in raw_list_payload(value):
        if isinstance(item, dict):
            labels.append(str(item.get("label") or item.get("reason") or item.get("code")))
        elif item:
            labels.append(str(item))
    return [label for label in labels if label and label != "None"]


def review_scorecard_payload(
    value: Any,
    *,
    shown_review_artifacts: list[str],
) -> list[dict[str, Any]]:
    artifacts = set(shown_review_artifacts)
    rows: list[dict[str, Any]] = []
    for item in raw_list_payload(value):
        if not isinstance(item, dict):
            continue
        material = str(item.get("material") or "").strip()
        if material not in artifacts:
            continue
        row: dict[str, Any] = {
            "material": material,
            "nazwa_materialu": review_artifact_title(material),
            "decyzja": str(item.get("decyzja") or "").strip(),
            "najwazniejsza_poprawka": str(
                item.get("najwazniejsza_poprawka") or ""
            ).strip(),
        }
        for field in REVIEW_SCORECARD_SCORE_FIELDS:
            row[field] = int(item.get(field) or 0)
        rows.append(row)
    return rows


def review_scorecard_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "artifact_count": 0,
            "average_clarity": None,
            "average_usefulness": None,
            "decision_counts": {},
        }
    decision_counts: dict[str, int] = {}
    for row in rows:
        decision = str(row.get("decyzja") or "")
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    return {
        "artifact_count": len(rows),
        "average_clarity": round(
            sum(int(row["czytelnosc_1_5"]) for row in rows) / len(rows),
            1,
        ),
        "average_usefulness": round(
            sum(int(row["uzytecznosc_1_5"]) for row in rows) / len(rows),
            1,
        ),
        "decision_counts": decision_counts,
    }


def review_follow_up_suggestions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for row in rows:
        decision = str(row.get("decyzja") or "")
        low_scores = [
            {
                "field": field,
                "label": label,
                "score": int(row[field]),
            }
            for field, label in REVIEW_SCORECARD_SCORE_FIELDS.items()
            if int(row.get(field) or 0) <= 3
        ]
        requested_fix = str(row.get("najwazniejsza_poprawka") or "").strip()
        if decision == "zatwierdź" and not low_scores:
            continue
        suggestions.append(
            {
                "material": row.get("material"),
                "nazwa_materialu": row.get("nazwa_materialu"),
                "decision": decision,
                "low_scores": low_scores,
                "requested_fix": requested_fix,
            }
        )
    return suggestions


def validate_review_scorecard(
    value: Any,
    *,
    shown_review_artifacts: list[str],
) -> list[str]:
    if not shown_review_artifacts:
        return []
    if not isinstance(value, list):
        return [
            "Brak scorecardu materiałów review w polu oceny_materialow_review"
        ]
    errors: list[str] = []
    rows_by_material: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            errors.append(f"Scorecard #{index} musi być obiektem")
            continue
        material = str(item.get("material") or "").strip()
        if material not in shown_review_artifacts:
            errors.append(
                "Scorecard wskazuje materiał spoza pokazane_materialy_review: "
                f"{material or '<brak>'}"
            )
            continue
        if material in rows_by_material:
            errors.append(f"Scorecard powtarza materiał review: {material}")
        rows_by_material[material] = item
        decision = str(item.get("decyzja") or "").strip()
        if decision not in REVIEW_SCORECARD_DECISIONS:
            errors.append(
                "Scorecard dla materiału "
                f"{material} musi mieć decyzję: zatwierdź, popraw, odrzuć albo odśwież"
            )
        for field, label in REVIEW_SCORECARD_SCORE_FIELDS.items():
            score = item.get(field)
            if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
                errors.append(
                    f"Scorecard dla materiału {material} musi mieć {label} 1-5"
                )
        if is_blank_or_placeholder(item.get("najwazniejsza_poprawka")):
            errors.append(
                "Scorecard dla materiału "
                f"{material} musi mieć najwazniejsza_poprawka albo 'brak'"
            )
    missing = [
        artifact
        for artifact in shown_review_artifacts
        if artifact not in rows_by_material
    ]
    for artifact in missing:
        errors.append(f"Brak scorecardu dla materiału review: {artifact}")
    return errors


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


def review_artifact_paths(value: Any) -> list[str]:
    return list_payload(value)


def validate_review_artifacts(value: Any) -> list[str]:
    artifacts = review_artifact_paths(value)
    if not artifacts:
        return ["Brak pokazanych materiałów review w polu pokazane_materialy_review"]
    errors: list[str] = []
    for artifact in artifacts:
        path = Path(artifact)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"Materiał review musi być ścieżką repo-relative: {artifact}")
            continue
        if REVIEW_ARTIFACTS_ROOT not in [path, *path.parents]:
            errors.append(f"Materiał review musi pochodzić z docs/handoffs: {artifact}")
            continue
        if not path.is_file():
            errors.append(f"Materiał review nie istnieje: {artifact}")
    return errors


def recommended_review_artifact_gaps(shown_review_artifacts: list[str]) -> list[str]:
    shown = set(shown_review_artifacts)
    return [
        artifact
        for artifact in RECOMMENDED_REVIEW_ARTIFACTS
        if artifact not in shown
    ]


def raw_list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def is_blank_or_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    lowered = text.lower()
    return (
        not text
        or text.startswith("<")
        or text in {"-", "TODO", "todo"}
        or lowered.startswith("todo:")
        or lowered in {"uzupełnij", "uzupelnij"}
        or lowered.startswith("uzupełnij:")
        or lowered.startswith("uzupelnij:")
    )


if __name__ == "__main__":
    raise SystemExit(main())
