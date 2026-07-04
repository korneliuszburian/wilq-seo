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
    "werdykt_po_15_minutach": "werdykt po 15 minutach",
    "czas_do_zrozumienia_statusu": "czas do zrozumienia statusu",
    "punkty_niezrozumienia": "punkty niezrozumienia",
    "wybrany_work_item": "wybrane zadanie treściowe",
    "pytania_skad_to_wzielo": 'pytania "skąd to wzięło?"',
    "miejsca_generyczne_off_brand": "miejsca generyczne/off-brand",
    "najwiekszy_brak_produktu": "największy brak produktu",
}

REQUIRED_BOOLEAN_FIELDS = {
    "wilku_rozumie_blokady_pelnego_uat": (
        "czy Wilku rozumie blokady pełnego testu treści"
    ),
    "service_profile_czytelny": "czy Service Profile jest czytelny",
    "public_service_review_actions_czytelne": (
        "czy publiczne decyzje oceny kart usług są czytelne"
    ),
    "private_review_actions_czytelne": (
        "czy prywatne decyzje oceny propozycji są czytelne"
    ),
    "private_policy_review_actions_czytelne": (
        "czy prywatne decyzje oceny polityk są czytelne"
    ),
    "mozna_przejsc_do_pelnego_content_uat": (
        "czy można przejść do pełnego testu treści"
    ),
}
REVIEW_ARTIFACTS_FIELD = "pokazane_materialy_review"
REVIEW_SCORECARD_FIELD = "oceny_materialow_review"
PRIVATE_SOURCE_TRACE_SCORECARD_FIELD = "oceny_prywatnego_sladu_zrodlowego"
WILKU_REVIEW_QUESTIONS_FIELD = "pytania_do_wilka"
WILKU_REVIEW_ANSWERS_FIELD = "odpowiedzi_wilka"
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
SESSION_VERDICT_FIELD = "werdykt_po_15_minutach"
SESSION_VERDICTS = {
    "przejdź do pełnego testu treści",
    "zostań przy review",
    "popraw materiały i wróć",
    "odrzuć ten kierunek",
}
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
SOURCE_SCOPE_LABELS = {
    "service": "usługa",
    "buyer_problem": "problem kupującego",
    "cta": "CTA",
    "claim_policy": "polityka twierdzeń",
    "evidence_requirement": "wymóg dowodowy",
    "metric_signal": "sygnał metryczny",
}
REVIEW_REQUIRED_FIELD_LABELS = {
    "action_id": "którą decyzję zapisujemy",
    "target_card_id": "której karty dotyczy decyzja",
    "decision": "werdykt: zatwierdzić, poprawić, oznaczyć jako nieaktualne albo odrzucić",
    "source_trace_clear": "czy źródło i pochodzenie faktu są jasne",
    "blocked_claims_reviewed": "czy zablokowane twierdzenia zostały sprawdzone",
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
            "Waliduje i renderuje wynik Goal 005 rozmowy z Wilkiem. "
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
            "aktualny input rozmowy co JSON proof."
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
    provenance = live_uat_provenance(
        live_context=live_context,
        selected_work_item=selected_work_item,
    )
    review_questions = wilku_review_questions(provenance)
    return {
        "data_sesji": "<YYYY-MM-DD>",
        "osoba": "Wilku",
        SESSION_VERDICT_FIELD: "popraw materiały i wróć",
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
        WILKU_REVIEW_QUESTIONS_FIELD: review_questions,
        WILKU_REVIEW_ANSWERS_FIELD: [
            {
                "pytanie": question,
                "odpowiedz": "UZUPEŁNIJ: odpowiedź Wilka albo brak odpowiedzi",
                "follow_up": "UZUPEŁNIJ: co poprawić albo brak follow-upu",
            }
            for question in review_questions
        ],
        PRIVATE_SOURCE_TRACE_SCORECARD_FIELD: private_source_trace_scorecard_example(
            provenance
        ),
        "pytania_skad_to_wzielo": (
            'UZUPEŁNIJ: gdzie Wilku zapytał "skąd to wzięło?" albo "brak pytań"'
        ),
        "miejsca_generyczne_off_brand": (
            "UZUPEŁNIJ: co brzmiało generycznie/off-brand albo brak uwag"
        ),
        "najwiekszy_brak_produktu": (
            "UZUPEŁNIJ: największa luka przed pełnym testem treści"
        ),
        "wilku_rozumie_blokady_pelnego_uat": "nie",
        "service_profile_czytelny": "nie",
        "public_service_review_actions_czytelne": "nie",
        "private_review_actions_czytelne": "nie",
        "private_policy_review_actions_czytelne": "nie",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": [
            "<wilq-seo-...: opisz follow-up po sesji, jeżeli pełny test treści jest zablokowany>"
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
        "## Kolejność rozmowy 15 minut",
        "",
        (
            "1. Status: czy Wilku rozumie, czemu pełny test treści jest jeszcze "
            "zablokowany."
        ),
        (
            "2. BDO: sprawdzić pierwszą kartę Service Profile i zdecydować: "
            "zatwierdzić, poprawić, odświeżyć albo odrzucić."
        ),
        (
            "3. Prywatny ślad: sprawdzić, czy `KB_*` i bramki ewaluacji są "
            "wystarczająco czytelne bez surowego prywatnego tekstu."
        ),
        (
            "4. Brief: ocenić, czy sygnał wystarcza tylko do oceny, czy jest "
            "zbyt słaby nawet do rozmowy."
        ),
        (
            "5. Stop/decyzja: zapisać największy brak i nie iść dalej, jeżeli "
            "Wilku pyta `skąd to wzięło?` albo widzi generyczny język."
        ),
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
        *private_source_trace_lines(provenance),
        "## Pytania do Wilka",
        "",
        "- Czy rozumiesz, czemu pełny test treści jest jeszcze zablokowany?",
        "- Czy Service Profile i pierwsza karta BDO są czytelne?",
        *private_review_question_lines(provenance),
        *sales_brief_review_question_lines(provenance),
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
        "## ID do zapisu po rozmowie",
        "",
        f"- Materiał ID: `{selected_work_item}`",
        "- Kolejka content: "
        f"`{provenance.get('queue_status') or 'nie sprawdzono live API'}`",
        "- Status briefu sprzedażowego: "
        f"`{provenance.get('selected_sales_brief_status') or 'brak live proof'}`",
        "- Jakość sygnału briefu: "
        f"{selected_sales_brief_signal_quality_label(provenance)}",
        "- Wiedza gotowa do finalnych treści: "
        f"`{visible_bool(provenance.get('production_depth_ready') is True)}`",
        "- Źródła danych: "
        f"{', '.join(provenance.get('selected_source_connectors') or []) or 'brak live proof'}",
        "- Decyzja Service Profile ID: "
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
        raise RuntimeError(
            "Niepoprawny wynik Goal 005 rozmowy z Wilkiem:\n- "
            + "\n- ".join(errors)
        )

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
    private_source_trace_scorecard = private_source_trace_scorecard_payload(
        payload.get(PRIVATE_SOURCE_TRACE_SCORECARD_FIELD)
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
        "session_verdict": str(payload[SESSION_VERDICT_FIELD]).strip(),
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
        "wilku_review_questions": list_payload(
            payload.get(WILKU_REVIEW_QUESTIONS_FIELD)
        ),
        "wilku_review_answers": wilku_review_answer_payload(
            payload.get(WILKU_REVIEW_ANSWERS_FIELD)
        ),
        "review_scorecard": review_scorecard,
        "review_scorecard_summary": review_scorecard_summary(review_scorecard),
        "private_source_trace_scorecard": private_source_trace_scorecard,
        "private_source_trace_follow_up_suggestions": (
            private_source_trace_follow_up_suggestions(private_source_trace_scorecard)
        ),
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
            "Ten raport zapisuje wynik Goal 005 rozmowy z Wilkiem. Nie promuje private "
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
    session_verdict = str(payload.get(SESSION_VERDICT_FIELD) or "").strip()
    if session_verdict and session_verdict not in SESSION_VERDICTS:
        errors.append(
            "werdykt po 15 minutach musi być jednym z: "
            + ", ".join(sorted(SESSION_VERDICTS))
        )
    if not list_payload(payload.get("follow_up_beads")) and normalize_bool(
        payload.get("mozna_przejsc_do_pelnego_content_uat")
    ) is False:
        errors.append("Gdy pełny test treści jest zablokowany, wpisz follow_up_beads")
    errors.extend(validate_review_artifacts(payload.get(REVIEW_ARTIFACTS_FIELD)))
    errors.extend(
        validate_review_scorecard(
            payload.get(REVIEW_SCORECARD_FIELD),
            shown_review_artifacts=review_artifact_paths(
                payload.get(REVIEW_ARTIFACTS_FIELD)
            ),
        )
    )
    errors.extend(
        validate_private_source_trace_scorecard(
            payload.get(PRIVATE_SOURCE_TRACE_SCORECARD_FIELD)
        )
    )
    if live_context is not None:
        selected_work_item = str(payload.get("wybrany_work_item") or "").strip()
        candidate_ids = live_context_candidate_ids(live_context)
        if selected_work_item and selected_work_item not in candidate_ids:
            errors.append(
                "Wybrane zadanie nie występuje w aktualnym pakiecie rozmowy: "
                f"{selected_work_item}"
            )
        provenance = live_uat_provenance(
            live_context=live_context,
            selected_work_item=selected_work_item,
        )
        if raw_list_payload(
            (provenance or {}).get("private_source_trace_items")
        ) and not raw_list_payload(
            payload.get(PRIVATE_SOURCE_TRACE_SCORECARD_FIELD)
        ):
            errors.append(
                "Gdy WILQ pokazuje prywatny ślad źródłowy, wpisz "
                "oceny_prywatnego_sladu_zrodlowego"
            )
    return errors


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Wynik Goal 005 rozmowy z Wilkiem",
        "",
        f"- Typ: `{report['report_type']}`",
        f"- Data: `{report['date']}`",
        f"- Osoba: `{report['person']}`",
        f"- Werdykt po 15 minutach: {report['session_verdict']}",
        f"- Materiał: `{report['selected_work_item']}`",
        f"- Status: {visible_status(report['overall_status'])}",
        f"- Czas do zrozumienia statusu: {report['time_to_status_understanding']}",
        f"- Punkty niezrozumienia: {report['confusion_points']}",
        "",
        report["safety_note"],
        "",
        "## Ślad danych do rozmowy",
        "",
        render_live_provenance(report.get("live_provenance")),
        "",
        "## Ocena",
        "",
        f"- Rozumie blokady pełnego testu treści: {visible_bool(report['blockers_understood'])}",
        f"- Service Profile czytelny: {visible_bool(report['service_profile_clear'])}",
        "- Publiczne decyzje oceny kart usług czytelne: "
        f"{visible_bool(report['public_service_review_actions_clear'])}",
        "- Prywatne decyzje oceny propozycji czytelne: "
        f"{visible_bool(report['private_review_actions_clear'])}",
        "- Prywatne decyzje oceny polityk czytelne: "
        f"{visible_bool(report['private_policy_review_actions_clear'])}",
        "- Można przejść do pełnego testu treści: "
        f"{visible_bool(report['can_continue_to_full_content_uat'])}",
        "",
        "## Pokazane materiały review",
        "",
        *[f"- `{artifact}`" for artifact in report["shown_review_artifacts"]],
        "",
        *render_wilku_review_questions(report.get("wilku_review_questions")),
        "",
        *render_wilku_review_answers(report.get("wilku_review_answers")),
        "",
        "## Scorecard Wilka",
        "",
        render_review_scorecard_summary(report.get("review_scorecard_summary")),
        "",
        *render_review_scorecard(report.get("review_scorecard")),
        "",
        *render_private_source_trace_scorecard(
            report.get("private_source_trace_scorecard")
        ),
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


def render_wilku_review_questions(value: Any) -> list[str]:
    questions = list_payload(value)
    if not questions:
        return []
    return [
        "## Pytania prowadzące z WILQ",
        "",
        *[f"- {question}" for question in questions],
    ]


def render_wilku_review_answers(value: Any) -> list[str]:
    rows = [row for row in raw_list_payload(value) if isinstance(row, dict)]
    if not rows:
        return []
    lines = ["## Odpowiedzi Wilka na pytania WILQ", ""]
    for row in rows:
        lines.extend(
            [
                f"- {row.get('pytanie')}",
                f"  - odpowiedź: {row.get('odpowiedz')}",
                f"  - follow-up: {row.get('follow_up') or 'brak'}",
            ]
        )
    return lines


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


def render_private_source_trace_scorecard(value: Any) -> list[str]:
    rows = [row for row in raw_list_payload(value) if isinstance(row, dict)]
    if not rows:
        return []
    lines = ["## Ocena prywatnego śladu źródłowego", ""]
    for row in rows:
        source_blocks = ", ".join(raw_string_list(row.get("source_blocks"))) or "brak"
        eval_cases = ", ".join(raw_string_list(row.get("eval_cases"))) or "brak"
        lines.extend(
            [
                f"- {row.get('target')}",
                f"  - zakres: {row.get('scope')}",
                f"  - źródło: {source_blocks}",
                f"  - eval: {eval_cases}",
                f"  - trace czytelny: {visible_bool(row.get('trace_czytelny') is True)}",
                f"  - decyzja: {row.get('decyzja')}",
                f"  - najważniejsza poprawka: {row.get('najwazniejsza_poprawka')}",
            ]
        )
    return lines


def private_source_trace_follow_up_suggestions(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for row in rows:
        decision = str(row.get("decyzja") or "")
        trace_clear = row.get("trace_czytelny") is True
        requested_fix = str(row.get("najwazniejsza_poprawka") or "").strip()
        if decision == "zatwierdź" and trace_clear and requested_fix.lower() == "brak":
            continue
        suggestions.append(
            {
                "target": row.get("target"),
                "scope": row.get("scope"),
                "decision": decision,
                "trace_clear": trace_clear,
                "requested_fix": requested_fix,
                "source_blocks": row.get("source_blocks") or [],
                "eval_cases": row.get("eval_cases") or [],
            }
        )
    return suggestions


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
        "signal_quality_status": (
            signal_quality.get("status") if isinstance(signal_quality, dict) else None
        ),
        "signal_quality_reason": (
            signal_quality.get("reason") if isinstance(signal_quality, dict) else None
        ),
        "signal_quality_safe_next_step": (
            signal_quality.get("safe_next_step")
            if isinstance(signal_quality, dict)
            else None
        ),
        "evidence_id_count": (
            signal_quality.get("evidence_id_count")
            if isinstance(signal_quality, dict)
            else None
        ),
        "source_connector_count": (
            signal_quality.get("source_connector_count")
            if isinstance(signal_quality, dict)
            else None
        ),
        "source_fact_count": (
            signal_quality.get("source_fact_count")
            if isinstance(signal_quality, dict)
            else None
        ),
        "review_required_knowledge_card_count": (
            signal_quality.get("review_required_knowledge_card_count")
            if isinstance(signal_quality, dict)
            else None
        ),
        "measurement_baseline_ready": (
            signal_quality.get("measurement_baseline_ready")
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
    raw_private_review_value = service_profile.get("private_review_value")
    private_review_value: dict[str, Any] = (
        raw_private_review_value if isinstance(raw_private_review_value, dict) else {}
    )
    raw_source_fact_coverage = service_profile.get("source_fact_coverage")
    source_fact_coverage: dict[str, Any] = (
        raw_source_fact_coverage if isinstance(raw_source_fact_coverage, dict) else {}
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
        "selected_sales_brief_signal_quality_status": selected_sales_brief_trace.get(
            "signal_quality_status"
        ),
        "selected_sales_brief_signal_quality_status_label": (
            selected_sales_brief_trace.get("signal_quality_status_label")
        ),
        "selected_sales_brief_signal_quality_reason": selected_sales_brief_trace.get(
            "signal_quality_reason"
        ),
        "selected_sales_brief_signal_quality_safe_next_step": (
            selected_sales_brief_trace.get("signal_quality_safe_next_step")
        ),
        "selected_sales_brief_signal_quality_counts": {
            "evidence_id_count": selected_sales_brief_trace.get("evidence_id_count"),
            "source_connector_count": selected_sales_brief_trace.get(
                "source_connector_count"
            ),
            "source_fact_count": selected_sales_brief_trace.get("source_fact_count"),
            "knowledge_constraint_count": selected_sales_brief_trace.get(
                "knowledge_constraint_count"
            ),
            "review_required_knowledge_card_count": selected_sales_brief_trace.get(
                "review_required_knowledge_card_count"
            ),
            "measurement_baseline_ready": selected_sales_brief_trace.get(
                "measurement_baseline_ready"
            ),
        },
        "selected_sales_brief_constraint_evidence_ids": selected_sales_brief_trace.get(
            "knowledge_constraint_evidence_ids"
        )
        or [],
        "selected_sales_brief_review_questions": sales_brief_review_questions(
            selected_sales_brief_trace
        ),
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
        "private_review_questions": [
            str(question)
            for question in raw_list_payload(private_review_value.get("review_questions"))
            if str(question).strip()
        ],
        "private_source_trace_items": private_source_trace_items_from_queue(
            raw_list_payload(source_fact_coverage.get("private_review_queue"))
        ),
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
        f"zakres: {review_scope_label(scope)}" if scope else None,
        f"karta: `{target}`" if target else None,
        str(next_step) if next_step else None,
    ]
    return " - ".join(part for part in parts if part)


def first_service_profile_review_plain_label(value: dict[str, Any]) -> str:
    label = value.get("first_service_profile_review_label")
    next_step = humanize_review_decision_text(
        value.get("first_service_profile_review_next_step")
    )
    if not any([label, next_step]):
        return "Brak pierwszej decyzji do oceny w aktualnym pakiecie."
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
    return "; ".join(labels) or "brak opcji z aktualnego pakietu"


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
    text = operator_copy_text(str(value))
    replacements = {
        "approve/needs_changes/stale/reject": (
            "zatwierdź, wróć z poprawkami, oznacz jako nieaktualne albo odrzuć"
        ),
        "approve": "zatwierdź",
        "needs_changes": "wróć z poprawkami",
        "stale": "oznacz jako nieaktualne",
        "reject": "odrzuć",
        "zablokowane claimy": "zablokowane twierdzenia",
        "claimy": "twierdzenia",
    }
    for raw, label in replacements.items():
        text = text.replace(raw, label)
    return text


def operator_copy_text(value: str) -> str:
    replacements = {
        "wymaga review": "wymaga oceny",
        "do review": "do oceny",
        "bez review": "bez oceny",
        "decyzję review": "decyzję oceny",
        "materiał do review": "materiał do oceny",
        "review człowieka": "ocenę człowieka",
        "claimy": "twierdzenia",
        "connectory": "źródła danych",
        "source facts": "fakty źródłowe",
        "source fact": "fakt źródłowy",
        "trace gotowy": "ślad gotowy",
        "trace niepełny": "ślad niepełny",
    }
    text = value
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
            "- Wybrany materiał znaleziony w aktualnym pakiecie: "
            f"{visible_bool(value.get('selected_work_item_found') is True)}",
            f"- Tryb wybranego materiału: `{value.get('selected_recommended_mode')}`",
            "- Źródła wybranego materiału: "
            f"{', '.join(value.get('selected_source_connectors') or []) or 'brak'}",
            "- Brief sprzedażowy wybranego materiału: "
            f"`{value.get('selected_sales_brief_status') or 'brak'}`",
            "- Jakość sygnału briefu: "
            f"{selected_sales_brief_signal_quality_label(value)}",
            "- Co blokuje brief sprzedażowy: "
            f"{sales_brief_blocker_label(value)}",
            "- Dowody przy ograniczeniu briefu: "
            f"{sales_brief_evidence_label(value)}",
            "- Service Profile read-only: "
            f"{visible_bool(value.get('service_profile_read_only') is True)}",
            "- Wiedza gotowa do finalnych treści: "
            f"{visible_bool(value.get('production_depth_ready') is True)}",
            "- Pierwszy Service Profile review: "
            f"{first_service_profile_review_label(value)}",
            "- Wymagane pola pierwszego review: "
            f"{first_service_profile_review_required_fields_label(value)}",
            "- Publiczne decyzje oceny kart usług: "
            f"`{value.get('public_service_review_action_count')}`",
            "- Prywatne decyzje oceny propozycji: "
            f"`{value.get('private_review_action_count')}`",
            "- Prywatne decyzje oceny usług: "
            f"`{value.get('private_service_review_action_count')}`",
            "- Prywatne decyzje oceny polityk: "
            f"`{value.get('private_policy_review_action_count')}`",
            "- Private proposal promotion ready: "
            f"{visible_bool(value.get('private_proposal_promotion_ready') is True)}",
            "- Pytania do prywatnych propozycji: "
            f"{private_review_questions_label(value)}",
            "- Prywatny ślad źródłowy do pokazania: "
            f"{private_source_trace_items_label(value)}",
        ]
    )


def private_review_question_lines(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    questions = [
        str(question).strip()
        for question in raw_list_payload(value.get("private_review_questions"))
        if str(question).strip()
    ]
    if not questions:
        return []
    return [
        "- Prywatna wiedza / ekologus-ai:",
        *[f"  - {question}" for question in questions],
    ]


def private_source_trace_lines(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    items = [
        item
        for item in raw_list_payload(value.get("private_source_trace_items"))
        if isinstance(item, dict)
    ]
    if not items:
        return []
    return [
        "## Prywatny ślad źródłowy do pokazania",
        "",
        *[f"- {private_source_trace_item_label(item)}" for item in items[:3]],
        "",
    ]


def wilku_review_questions(value: dict[str, Any] | None) -> list[str]:
    questions = [
        "Czy rozumiesz, czemu pełny test treści jest jeszcze zablokowany?",
        "Czy Service Profile i pierwsza karta BDO są czytelne?",
    ]
    if isinstance(value, dict):
        questions.extend(
            [
                str(question).strip()
                for question in raw_list_payload(value.get("private_review_questions"))
                if str(question).strip()
            ]
        )
        questions.extend(sales_brief_review_questions(value))
    questions.extend(
        [
            'Gdzie pytasz: "skąd WILQ to wziął?"',
            "Co brzmi generycznie albo nie jak Ekologus?",
            "Co trzeba poprawić, zanim puścimy pełny test treści?",
        ]
    )
    seen: set[str] = set()
    unique_questions: list[str] = []
    for question in questions:
        if question in seen:
            continue
        seen.add(question)
        unique_questions.append(question)
    return unique_questions


def wilku_review_answer_payload(value: Any) -> list[dict[str, str]]:
    answers: list[dict[str, str]] = []
    for item in raw_list_payload(value):
        if not isinstance(item, dict):
            continue
        question = str(item.get("pytanie") or "").strip()
        answer = str(item.get("odpowiedz") or "").strip()
        if is_blank_or_placeholder(question) or is_blank_or_placeholder(answer):
            continue
        follow_up = str(item.get("follow_up") or "").strip()
        answers.append(
            {
                "pytanie": question,
                "odpowiedz": answer,
                "follow_up": "" if is_blank_or_placeholder(follow_up) else follow_up,
            }
        )
    return answers


def private_review_questions_label(value: dict[str, Any]) -> str:
    questions = [
        str(question).strip()
        for question in raw_list_payload(value.get("private_review_questions"))
        if str(question).strip()
    ]
    return "; ".join(questions) or "brak"


def private_source_trace_items_label(value: dict[str, Any]) -> str:
    items = [
        item
        for item in raw_list_payload(value.get("private_source_trace_items"))
        if isinstance(item, dict)
    ]
    return "; ".join(private_source_trace_item_label(item) for item in items[:3]) or "brak"


def private_source_trace_items_from_queue(queue: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_item in queue[:5]:
        item = raw_item if isinstance(raw_item, dict) else {}
        target = str(item.get("target_card_title") or "").strip()
        if not target:
            continue
        items.append(
            {
                "target": private_trace_operator_text(target),
                "scope": REVIEW_SCOPE_LABELS.get(
                    str(item.get("scope") or ""),
                    SOURCE_SCOPE_LABELS.get(
                        str(item.get("scope") or ""),
                        str(item.get("scope") or "brak"),
                    ),
                ),
                "source_blocks": [
                    str(value).strip()
                    for value in raw_list_payload(item.get("source_block_refs"))
                    if str(value).strip()
                ],
                "eval_cases": [
                    str(value).strip()
                    for value in raw_list_payload(item.get("eval_case_ids"))
                    if str(value).strip()
                ],
                "retention": private_retention_label(item.get("retention_decision")),
                "redacted": item.get("redacted") is True,
                "trace_ready": item.get("source_trace_ready") is True,
                "safe_next_step": humanize_review_decision_text(
                    private_trace_operator_text(str(item.get("safe_next_step") or ""))
                ),
            }
        )
    return items


def private_retention_label(value: Any) -> str:
    raw = str(value or "")
    return {
        "pending_owner_decision": "decyzja właściciela wymagana",
        "retain_while_source_approved": "utrzymuj tylko dopóki źródło jest zatwierdzone",
        "short_window_only": "krótkie okno retencji",
        "do_not_retain": "nie utrzymuj",
    }.get(raw, raw or "brak")


def private_trace_operator_text(value: str) -> str:
    return (
        value.replace("reviewerowi", "osobie oceniającej")
        .replace("reviewerem", "osobą oceniającą")
        .replace("reviewer", "osoba oceniająca")
        .replace("reviewed source fact", "oceniony fakt źródłowy")
        .replace("reviewed policy fact", "oceniony fakt polityki")
        .replace("reviewed evidence policy", "oceniona polityka dowodowa")
        .replace("reviewed źródeł", "ocenionych źródeł")
        .replace("reviewed source", "ocenione źródło")
        .replace("claim policy", "polityka twierdzeń")
        .replace("Source trace", "Ślad źródłowy")
        .replace("source trace", "ślad źródłowy")
        .replace("evidence pack", "pakiet dowodów")
        .replace("review", "ocena")
        .replace("production-depth", "wiedza do finalnych treści")
        .replace("redacted source fact", "zredagowany fakt źródłowy")
    )


def private_source_trace_item_label(value: dict[str, Any]) -> str:
    source_blocks = ", ".join(raw_string_list(value.get("source_blocks"))) or "brak"
    eval_cases = ", ".join(raw_string_list(value.get("eval_cases"))) or "brak"
    redacted = "zredagowane" if value.get("redacted") is True else "wymaga redakcji"
    trace_ready = "ślad gotowy" if value.get("trace_ready") is True else "ślad niepełny"
    parts = [
        str(value.get("target") or "brak"),
        str(value.get("scope") or "brak"),
        f"źródło: {source_blocks}",
        f"eval: {eval_cases}",
        str(value.get("retention") or "brak"),
        redacted,
        trace_ready,
    ]
    return " / ".join(parts)


def private_source_trace_scorecard_example(
    value: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    return [
        {
            "target": item.get("target"),
            "scope": item.get("scope"),
            "source_blocks": item.get("source_blocks") or [],
            "eval_cases": item.get("eval_cases") or [],
            "trace_czytelny": "nie",
            "decyzja": "popraw",
            "najwazniejsza_poprawka": (
                "UZUPEŁNIJ: czy ślad jest jasny i co poprawić albo wpisz brak"
            ),
        }
        for item in raw_list_payload(value.get("private_source_trace_items"))
        if isinstance(item, dict)
    ]


def private_source_trace_scorecard_payload(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in raw_list_payload(value):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "target": str(item.get("target") or "").strip(),
                "scope": str(item.get("scope") or "").strip(),
                "source_blocks": raw_string_list(item.get("source_blocks")),
                "eval_cases": raw_string_list(item.get("eval_cases")),
                "trace_czytelny": normalize_bool(item.get("trace_czytelny")),
                "decyzja": str(item.get("decyzja") or "").strip(),
                "najwazniejsza_poprawka": str(
                    item.get("najwazniejsza_poprawka") or ""
                ).strip(),
            }
        )
    return rows


def raw_string_list(value: Any) -> list[str]:
    return [
        str(item).strip()
        for item in raw_list_payload(value)
        if str(item).strip()
    ]


def sales_brief_review_question_lines(value: dict[str, Any]) -> list[str]:
    questions = sales_brief_review_questions(value)
    if not questions:
        return []
    return [
        "- Brief sprzedażowy / jakość sygnału:",
        *[f"  - {question}" for question in questions],
    ]


def sales_brief_review_questions(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    explicit_questions = [
        str(question).strip()
        for question in raw_list_payload(
            value.get("selected_sales_brief_review_questions")
        )
        if str(question).strip()
    ]
    if explicit_questions:
        return explicit_questions
    status_label = str(
        value.get("selected_sales_brief_signal_quality_status_label")
        or value.get("signal_quality_status_label")
        or ""
    ).strip()
    status_label = operator_copy_text(status_label)
    if not status_label:
        return []

    questions = [
        (
            "Czy status briefu `"
            + status_label
            + "` mówi jasno, czy można go pokazać tylko do oceny?"
        )
    ]
    reason = str(
        value.get("selected_sales_brief_signal_quality_reason")
        or value.get("signal_quality_reason")
        or ""
    ).strip()
    if reason:
        questions.append(
            "Czy powód jakości sygnału jest zrozumiały: "
            + operator_copy_text(reason)
        )
    safe_next_step = str(
        value.get("selected_sales_brief_signal_quality_safe_next_step")
        or value.get("signal_quality_safe_next_step")
        or ""
    ).strip()
    if safe_next_step:
        questions.append(
            "Czy następny krok briefu jest właściwy: "
            + operator_copy_text(safe_next_step)
        )

    counts = value.get("selected_sales_brief_signal_quality_counts")
    if not isinstance(counts, dict):
        counts = {
            "evidence_id_count": value.get("evidence_id_count"),
            "source_connector_count": value.get("source_connector_count"),
            "source_fact_count": value.get("source_fact_count"),
            "knowledge_constraint_count": value.get("knowledge_constraint_count"),
        }
    evidence_count = counts.get("evidence_id_count")
    connector_count = counts.get("source_connector_count")
    fact_count = counts.get("source_fact_count")
    constraint_count = counts.get("knowledge_constraint_count")
    if any(
        item is not None
        for item in (evidence_count, connector_count, fact_count, constraint_count)
    ):
        questions.append(
            "Czy ta ilość sygnału wystarcza do oceny: "
            f"dowody {evidence_count or 0}, źródła danych {connector_count or 0}, "
            f"fakty źródłowe {fact_count or 0}, ograniczenia {constraint_count or 0}?"
        )
    return questions


def sales_brief_review_questions_label(value: dict[str, Any]) -> str:
    return "; ".join(sales_brief_review_questions(value)) or "brak"


def sales_brief_blocker_label(value: dict[str, Any]) -> str:
    blocker = value.get("selected_sales_brief_blocker")
    if blocker:
        return str(blocker)
    blockers = sales_brief_blocker_labels(value.get("selected_sales_brief_blockers"))
    return "; ".join(blockers) or "brak"


def selected_sales_brief_signal_quality_label(value: dict[str, Any] | None) -> str:
    if not isinstance(value, dict):
        return "brak live proof"
    label = value.get("selected_sales_brief_signal_quality_status_label")
    if not label:
        return "brak live proof"
    label = operator_copy_text(str(label))
    counts = value.get("selected_sales_brief_signal_quality_counts")
    count_labels: list[str] = []
    if isinstance(counts, dict):
        if counts.get("evidence_id_count") is not None:
            count_labels.append(f"dowody: {counts.get('evidence_id_count')}")
        if counts.get("source_connector_count") is not None:
            count_labels.append(
                f"źródła danych: {counts.get('source_connector_count')}"
            )
        if counts.get("source_fact_count") is not None:
            count_labels.append(f"fakty źródłowe: {counts.get('source_fact_count')}")
        if counts.get("knowledge_constraint_count") is not None:
            count_labels.append(
                f"ograniczenia wiedzy: {counts.get('knowledge_constraint_count')}"
            )
    details = f" ({', '.join(count_labels)})" if count_labels else ""
    return f"{label}{details}"


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


def validate_private_source_trace_scorecard(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return [
            "oceny_prywatnego_sladu_zrodlowego musi być listą, gdy jest podane"
        ]
    errors: list[str] = []
    seen_targets: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            errors.append(f"Ocena prywatnego śladu #{index} musi być obiektem")
            continue
        target = str(item.get("target") or "").strip()
        if is_blank_or_placeholder(target):
            errors.append(f"Ocena prywatnego śladu #{index} musi mieć target")
        elif target in seen_targets:
            errors.append(f"Ocena prywatnego śladu powtarza target: {target}")
        seen_targets.add(target)
        if is_blank_or_placeholder(item.get("scope")):
            errors.append(f"Ocena prywatnego śladu {target or index} musi mieć scope")
        if not raw_string_list(item.get("source_blocks")):
            errors.append(
                f"Ocena prywatnego śladu {target or index} musi mieć source_blocks"
            )
        if not raw_string_list(item.get("eval_cases")):
            errors.append(
                f"Ocena prywatnego śladu {target or index} musi mieć eval_cases"
            )
        if normalize_bool(item.get("trace_czytelny")) is None:
            errors.append(
                f"Ocena prywatnego śladu {target or index} musi mieć trace_czytelny: tak albo nie"
            )
        decision = str(item.get("decyzja") or "").strip()
        if decision not in REVIEW_SCORECARD_DECISIONS:
            errors.append(
                f"Ocena prywatnego śladu {target or index} musi mieć decyzję: "
                "zatwierdź, popraw, odrzuć albo odśwież"
            )
        if is_blank_or_placeholder(item.get("najwazniejsza_poprawka")):
            errors.append(
                f"Ocena prywatnego śladu {target or index} musi mieć "
                "najwazniejsza_poprawka albo 'brak'"
            )
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
        return "gotowe do pełnego testu treści"
    return "wymaga follow-up przed pełnym testem treści"


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
