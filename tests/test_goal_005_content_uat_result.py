from __future__ import annotations

import pytest

from scripts.record_goal_005_content_uat_result import (
    RECOMMENDED_REVIEW_ARTIFACTS,
    REQUIRED_BOOLEAN_FIELDS,
    REQUIRED_TEXT_FIELDS,
    build_content_uat_input_example,
    build_content_uat_result_report,
    render_content_uat_session_card,
    render_markdown,
    sales_brief_blocker_label,
    sales_brief_trace_from_snapshot,
    select_uat_candidate_id,
)


def test_content_uat_result_records_follow_up_when_full_uat_blocked() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "punkty_niezrozumienia": "Nie było jasne, które karty są tylko review-required.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "oceny_materialow_review": _scorecard(
            ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
            decision="popraw",
        ),
        "pytania_skad_to_wzielo": "Chce widzieć publiczny URL obok evidence ID.",
        "miejsca_generyczne_off_brand": "CTA było za szerokie dla usług środowiskowych.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonej karty dla Eko-Opieki.",
        "pytania_do_wilka": [
            "Czy Service Profile i pierwsza karta BDO są czytelne?",
            "Czy status briefu `sygnał użyteczny, ale wymaga review` mówi jasno?",
        ],
        "odpowiedzi_wilka": [
            {
                "pytanie": "Czy Service Profile i pierwsza karta BDO są czytelne?",
                "odpowiedz": "Tak, ale trzeba uprościć opis zablokowanych claimów.",
                "follow_up": "Przepisać blocker claimów z języka technicznego.",
            },
            {
                "pytanie": "Czy status briefu `sygnał użyteczny, ale wymaga review` mówi jasno?",
                "odpowiedz": "Tak, jasne że to tylko review.",
                "follow_up": "brak",
            },
            {
                "pytanie": "Czy placeholder nie powinien wejść do proof?",
                "odpowiedz": "UZUPEŁNIJ: odpowiedź Wilka albo brak odpowiedzi",
                "follow_up": "UZUPEŁNIJ: co poprawić albo brak follow-upu",
            },
        ],
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "nie",
        "private_policy_review_actions_czytelne": "nie",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-xyz: doprecyzować opis prywatnej decyzji do oceny"],
    }

    report = build_content_uat_result_report(payload)

    assert report["report_type"] == "goal_005_content_uat_result_v1"
    assert report["selected_work_item"] == payload["wybrany_work_item"]
    assert report["confusion_points"] == payload["punkty_niezrozumienia"]
    assert report["overall_status"] == "needs_follow_up_before_full_content_uat"
    assert report["missing_follow_up_task"] is False
    assert report["follow_up_tasks"] == [
        "wilq-seo-xyz: doprecyzować opis prywatnej decyzji do oceny"
    ]
    assert report["shown_review_artifacts"] == [
        "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
    ]
    assert report["wilku_review_questions"] == [
        "Czy Service Profile i pierwsza karta BDO są czytelne?",
        "Czy status briefu `sygnał użyteczny, ale wymaga review` mówi jasno?",
    ]
    assert report["wilku_review_answers"] == [
        {
            "pytanie": "Czy Service Profile i pierwsza karta BDO są czytelne?",
            "odpowiedz": "Tak, ale trzeba uprościć opis zablokowanych claimów.",
            "follow_up": "Przepisać blocker claimów z języka technicznego.",
        },
        {
            "pytanie": "Czy status briefu `sygnał użyteczny, ale wymaga review` mówi jasno?",
            "odpowiedz": "Tak, jasne że to tylko review.",
            "follow_up": "brak",
        },
    ]
    assert report["review_scorecard_summary"] == {
        "artifact_count": 1,
        "average_clarity": 4.0,
        "average_usefulness": 5.0,
        "decision_counts": {"popraw": 1},
    }
    assert report["review_follow_up_suggestions"] == [
        {
            "material": "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md",
            "nazwa_materialu": "BDO i sprawozdawczość - próbka rozmowy",
            "decision": "popraw",
            "low_scores": [
                {
                    "field": "dopasowanie_cta_1_5",
                    "label": "dopasowanie CTA",
                    "score": 3,
                }
            ],
            "requested_fix": "Doprecyzować język i kolejny krok.",
        }
    ]
    assert report["missing_recommended_review_artifacts"] == [
        artifact
        for artifact in RECOMMENDED_REVIEW_ARTIFACTS
        if artifact != "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
    ]
    assert "Nie promuje private proposals" in report["safety_note"]
    assert "nie odblokowuje publikacji" in report["safety_note"]

    markdown = render_markdown(report)
    assert "## Pytania prowadzące z WILQ" in markdown
    assert "## Odpowiedzi Wilka na pytania WILQ" in markdown
    assert "Czy Service Profile i pierwsza karta BDO są czytelne?" in markdown
    assert "Tak, ale trzeba uprościć opis zablokowanych claimów." in markdown
    assert "## Ostrzeżenia materiałów review" in markdown
    assert "## Scorecard Wilka" in markdown
    assert "## Sugestie follow-up z ocen" in markdown
    assert "decyzja: popraw" in markdown
    assert "dopasowanie CTA 3/5" in markdown
    assert "2026-07-02-wilq-marketing-content-model.md" in markdown
    assert "2026-07-03-wilku-service-profile-review-now.md" in markdown
    assert "2026-07-02-co-pokazac-wilkowi.md" in markdown
    assert "2026-07-02-wilku-ekologus-ai-policy-review.md" in markdown
    assert "2026-07-02-wilku-social-history-blocker.md" in markdown


def test_content_uat_input_example_uses_live_candidate_and_review_artifacts() -> None:
    example = build_content_uat_input_example(live_context=_live_context())

    assert example["wybrany_work_item"] == (
        "content_work_item_content_decision_https___www_ekologus_pl"
    )
    for key in REQUIRED_TEXT_FIELDS:
        assert key in example
    for key in REQUIRED_BOOLEAN_FIELDS:
        assert example[key] in {"tak", "nie"}
    assert example["pokazane_materialy_review"] == RECOMMENDED_REVIEW_ARTIFACTS
    assert [row["material"] for row in example["oceny_materialow_review"]] == (
        RECOMMENDED_REVIEW_ARTIFACTS
    )
    assert example["oceny_materialow_review"][0]["nazwa_materialu"] == (
        "Service Profile - co pokazać teraz"
    )
    assert example["pytania_do_wilka"]
    assert [row["pytanie"] for row in example["odpowiedzi_wilka"]] == example[
        "pytania_do_wilka"
    ]
    assert example["odpowiedzi_wilka"][0]["odpowiedz"].startswith("UZUPEŁNIJ:")
    assert "Czy Service Profile i pierwsza karta BDO są czytelne?" in example[
        "pytania_do_wilka"
    ]
    assert any(
        "Czy status briefu `sygnał użyteczny, ale wymaga review` mówi jasno"
        in question
        for question in example["pytania_do_wilka"]
    )
    assert any(
        "Czy proponowane CTA brzmi jak realny następny krok Ekologus"
        in question
        for question in example["pytania_do_wilka"]
    )
    assert example["follow_up_beads"] == [
        "<wilq-seo-...: opisz follow-up po sesji, jeżeli pełny test treści jest zablokowany>"
    ]


def test_content_uat_session_card_is_plain_wilku_handoff() -> None:
    card = render_content_uat_session_card(live_context=_live_context())

    assert "# Goal 005 - karta rozmowy z Wilkiem" in card
    assert (
        "content_work_item_content_decision_https___www_ekologus_pl"
        in card
    )
    assert "Temat rozmowy: SEO: odśwież lub scal \"ekologus\"" in card
    assert "URL / miejsce w serwisie: https://www.ekologus.pl/" in card
    assert "Decyzja contentowa WILQ: odśwież istniejącą treść" in card
    status_section = card.split("## Pierwsza decyzja w Service Profile")[0]
    assert "content_work_item_content_decision_https___www_ekologus_pl" not in (
        status_section
    )
    assert "google_search_console" not in status_section
    assert "production-depth" not in status_section
    assert "Zatwierdzona wiedza do finalnych treści: nie" in status_section
    assert "## ID do zapisu po rozmowie" in card
    assert "Materiał ID: `content_work_item_content_decision_https___www_ekologus_pl`" in card
    public_section = card.split("## ID do zapisu po rozmowie")[0]
    assert "renamed_public_service_bdo_review" not in public_section
    assert "ekologus_service_bdo_reporting" not in public_section
    assert "renamed_public_service_bdo_review" in card
    assert "ekologus_service_bdo_reporting" in card
    assert "Sprawdź kartę BDO" in card
    assert "Możliwe decyzje: zatwierdź do dalszego użycia" in card
    assert "wróć z poprawkami" in card
    assert "Co trzeba ocenić: którą decyzję zapisujemy" in card
    assert "czy źródło i pochodzenie faktu są jasne" in card
    assert "approve/needs_changes/stale/reject" not in card
    assert "Najpierw sprawdź publiczną kartę BDO." in card
    assert "Decyzja Service Profile ID" in card
    assert "Jakość sygnału briefu: sygnał użyteczny, ale wymaga review" in card
    assert "dowody: 2" in card
    assert "Brief sprzedażowy / jakość sygnału:" in card
    assert (
        "Czy status briefu `sygnał użyteczny, ale wymaga review` mówi jasno"
        in card
    )
    assert "Czy powód jakości sygnału jest zrozumiały" in card
    assert "Czy następny krok briefu jest właściwy" in card
    assert "Czy Service Profile i pierwsza karta BDO są czytelne?" in card
    assert "## Prywatny ślad źródłowy do pokazania" in card
    assert "Bezpieczeństwo prawne, poufność i zgody" in card
    assert "źródło: KB_021_BEZPIECZENSTWO_PRAWNE" in card
    assert (
        "eval: goal_005_private_claim_policy_review, goal_006_claim_ledger_gate"
        in card
    )
    assert "decyzja właściciela wymagana" in card
    assert "zredagowane" in card
    assert "trace gotowy" in card
    assert "Prywatna wiedza / ekologus-ai:" in card
    assert (
        "Czy proponowane CTA brzmi jak realny następny krok Ekologus, a nie obietnica wyniku?"
        in card
    )
    assert "docs/handoffs/2026-07-03-wilku-service-profile-review-now.md" in card
    assert "Service Profile - co pokazać teraz" in card
    assert "BDO i sprawozdawczość - próbka rozmowy" in card
    assert "Historia social - co blokuje ponowne użycie tematu" in card
    assert "--print-input-example --api-base http://127.0.0.1:8000" in card
    assert "scripts/record_goal_005_content_uat_result.py <plik.json>" in card
    assert "production-depth" not in card
    assert "content UAT" not in public_section
    assert "JSON proof" not in public_section


def test_content_uat_candidate_selection_prefers_actionable_work_item() -> None:
    live_context = _live_context_with_blocked_and_actionable_candidates()

    selected_work_item = select_uat_candidate_id(live_context)
    example = build_content_uat_input_example(live_context=live_context)

    assert selected_work_item == (
        "content_work_item_content_decision_https___www_ekologus_pl"
    )
    assert example["wybrany_work_item"] == selected_work_item


def test_content_uat_input_example_is_not_a_completed_uat_result() -> None:
    example = build_content_uat_input_example(live_context=_live_context())

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(example, live_context=_live_context())

    message = str(error.value)
    assert "Brak pola albo placeholder: data sesji" in message
    assert "Brak pola albo placeholder: czas do zrozumienia statusu" in message
    assert "Brak pola albo placeholder: największy brak produktu" in message
    assert "Gdy pełny test treści jest zablokowany, wpisz follow_up_beads" in message


def test_content_uat_result_records_live_packet_provenance_for_selected_item() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "punkty_niezrozumienia": "Nie było jasne, czemu BDO nie jest aktualnym zadaniem.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "oceny_materialow_review": _scorecard(
            ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"]
        ),
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: wybrać konkretniejszy temat UAT"],
    }
    live_context = _live_context()

    report = build_content_uat_result_report(payload, live_context=live_context)

    provenance = report["live_provenance"]
    assert provenance["api_base"] == "http://127.0.0.1:8000"
    assert provenance["queue_status"] == "blocked"
    assert provenance["selected_work_item_found"] is True
    assert provenance["selected_recommended_mode"] == "refresh"
    assert provenance["selected_source_connectors"] == [
        "google_search_console",
        "wordpress_ekologus",
    ]
    assert provenance["selected_sales_brief_status"] == "ready"
    assert provenance["selected_sales_brief_blocker"] is None
    assert provenance["selected_sales_brief_constraint_count"] == 1
    assert provenance["selected_sales_brief_constraint_evidence_ids"] == [
        "ev_content_service_profile_source_facts"
    ]
    assert provenance["selected_sales_brief_review_questions"]
    assert (
        "Czy status briefu `sygnał użyteczny, ale wymaga review` mówi jasno"
        in provenance["selected_sales_brief_review_questions"][0]
    )
    assert provenance["service_profile_read_only"] is True
    assert provenance["production_depth_ready"] is False
    assert provenance["first_service_profile_review_action_id"] == (
        "renamed_public_service_bdo_review"
    )
    assert provenance["first_service_profile_review_label"] == "Sprawdź kartę BDO"
    assert provenance["first_service_profile_review_scope"] == "public_service_card"
    assert provenance["first_service_profile_review_target_card_id"] == (
        "ekologus_service_bdo_reporting"
    )
    assert provenance["first_service_profile_review_required_fields"] == [
        "action_id",
        "source_trace_clear",
    ]
    assert provenance["public_service_review_action_count"] == 1
    assert provenance["private_review_action_count"] == 1
    assert provenance["private_service_review_action_count"] == 1
    assert provenance["private_policy_review_action_count"] == 0
    assert provenance["private_proposal_promotion_ready"] is False
    assert provenance["private_source_trace_items"] == [
        {
            "target": "Bezpieczeństwo prawne, poufność i zgody",
            "scope": "polityka twierdzeń",
            "source_blocks": ["KB_021_BEZPIECZENSTWO_PRAWNE"],
            "eval_cases": [
                "goal_005_private_claim_policy_review",
                "goal_006_claim_ledger_gate",
            ],
            "retention": "decyzja właściciela wymagana",
            "redacted": True,
            "trace_ready": True,
            "safe_next_step": "Pokaż Wilkowi ślad źródłowy bez raw private text.",
        }
    ]

    markdown = render_markdown(report)
    assert "## Ślad danych do rozmowy" in markdown
    assert "Wybrany materiał znaleziony w aktualnym pakiecie: tak" in markdown
    assert "Źródła wybranego materiału: google_search_console, wordpress_ekologus" in markdown
    assert "Brief sprzedażowy wybranego materiału: `ready`" in markdown
    assert "Co blokuje brief sprzedażowy: brak" in markdown
    assert (
        "Dowody przy ograniczeniu briefu: ev_content_service_profile_source_facts"
        in markdown
    )
    assert "Publiczne decyzje oceny kart usług: `1`" in markdown
    assert (
        "Prywatny ślad źródłowy do pokazania: "
        "Bezpieczeństwo prawne, poufność i zgody"
        in markdown
    )
    assert "Pierwszy Service Profile review" in markdown
    assert "renamed_public_service_bdo_review" in markdown
    assert "Wymagane pola pierwszego review: action_id, source_trace_clear" in markdown
    assert "Prywatne decyzje oceny usług: `1`" in markdown
    assert "Prywatne decyzje oceny polityk: `0`" in markdown
    assert "## Pokazane materiały review" in markdown
    assert "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md" in markdown


def test_content_uat_result_has_no_warning_when_plain_show_guide_was_shown() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "7 minut",
        "punkty_niezrozumienia": "Prosty przewodnik pomógł odczytać techniczne handoffy.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": RECOMMENDED_REVIEW_ARTIFACTS,
        "oceny_materialow_review": _scorecard(RECOMMENDED_REVIEW_ARTIFACTS),
        "pytania_skad_to_wzielo": "Źródła były czytelne.",
        "miejsca_generyczne_off_brand": "Brak nowych uwag.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonej karty usługi.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: zatwierdzić albo poprawić kartę usługi"],
    }

    report = build_content_uat_result_report(payload)

    assert report["missing_recommended_review_artifacts"] == []
    assert "## Ostrzeżenia materiałów review" not in render_markdown(report)


def test_content_uat_result_preserves_blocked_sales_brief_reason() -> None:
    trace = sales_brief_trace_from_snapshot(
        {
            "sales_brief": {
                "sales_brief_result": {
                    "brief": None,
                    "blockers": [
                        {
                            "code": "missing_required_knowledge_card",
                            "label": "Brakuje wymaganej karty wiedzy",
                        }
                    ],
                }
            }
        }
    )

    assert trace["status"] == "blocked"
    assert trace["blockers"] == [
        {
            "code": "missing_required_knowledge_card",
            "label": "Brakuje wymaganej karty wiedzy",
        }
    ]
    assert (
        sales_brief_blocker_label({"selected_sales_brief_blockers": trace["blockers"]})
        == "Brakuje wymaganej karty wiedzy"
    )


def test_content_uat_result_rejects_work_item_missing_from_live_packet() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "punkty_niezrozumienia": "Nie wiadomo, czemu ten item jest poza kolejką.",
        "wybrany_work_item": "content_work_item_fake",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: wybrać konkretniejszy temat UAT"],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload, live_context=_live_context())

    assert "Wybrane zadanie nie występuje w aktualnym pakiecie rozmowy" in str(
        error.value
    )


def test_content_uat_result_rejects_placeholders_and_invalid_booleans() -> None:
    payload = {
        "data_sesji": "<YYYY-MM-DD>",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "-",
        "punkty_niezrozumienia": "TODO",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "pytania_skad_to_wzielo": "TODO",
        "miejsca_generyczne_off_brand": "brak",
        "najwiekszy_brak_produktu": "brak",
        "wilku_rozumie_blokady_pelnego_uat": "yes",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "nie",
        "private_policy_review_actions_czytelne": "nie",
        "mozna_przejsc_do_pelnego_content_uat": "maybe",
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    message = str(error.value)
    assert "Brak pola albo placeholder: data sesji" in message
    assert "Brak pola albo placeholder: czas do zrozumienia statusu" in message
    assert "Brak pola albo placeholder: punkty niezrozumienia" in message
    assert 'Brak pola albo placeholder: pytania "skąd to wzięło?"' in message
    assert (
        "czy Wilku rozumie blokady pełnego testu treści musi mieć wartość tak albo nie"
        in message
    )
    assert "czy można przejść do pełnego testu treści musi mieć wartość tak albo nie" in message


def test_content_uat_result_requires_existing_review_artifact() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "punkty_niezrozumienia": "Brak widocznego materiału review blokuje interpretację.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/brak-takiego-materialu.md"],
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: wybrać konkretniejszy temat UAT"],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    assert "Materiał review nie istnieje" in str(error.value)


def test_content_uat_result_requires_review_artifact_list() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "punkty_niezrozumienia": "Nie wiadomo, które materiały pokazano.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: wybrać konkretniejszy temat UAT"],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    assert "Brak pokazanych materiałów review" in str(error.value)


def test_content_uat_result_requires_public_service_review_feedback() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "10 minut",
        "punkty_niezrozumienia": "Brak oceny publicznych akcji review.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: ocenić publiczne karty usług"],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    assert (
        "czy publiczne decyzje oceny kart usług są czytelne musi mieć wartość tak albo nie"
        in str(error.value)
    )


def test_content_uat_result_requires_follow_up_when_blocked() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "12 minut",
        "punkty_niezrozumienia": "Nie wiadomo, co trzeba poprawić przed pełnym UAT.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "pytania_skad_to_wzielo": "Wystarczy, ale chce linki publiczne.",
        "miejsca_generyczne_off_brand": "Nagłówki brzmią jak zwykłe SEO.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonej usługi BDO.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": [],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    assert "Gdy pełny test treści jest zablokowany, wpisz follow_up_beads" in str(
        error.value
    )


def test_content_uat_result_ready_only_when_all_gates_are_yes() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "6 minut",
        "punkty_niezrozumienia": "Brak nowych punktów niezrozumienia po review.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "oceny_materialow_review": _scorecard(
            ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
            decision="zatwierdź",
        ),
        "pytania_skad_to_wzielo": "Evidence IDs i source connectors wystarczają.",
        "miejsca_generyczne_off_brand": "Brak.",
        "najwiekszy_brak_produktu": "Brak.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "tak",
    }

    report = build_content_uat_result_report(payload)

    assert report["overall_status"] == "ready_for_full_content_uat"
    assert report["missing_follow_up_task"] is False

    markdown = render_markdown(report)
    assert "# Wynik Goal 005 rozmowy z Wilkiem" in markdown
    assert "Status: gotowe do pełnego testu treści" in markdown
    assert "Punkty niezrozumienia" in markdown
    assert "Pytania \"skąd to wzięło?\"" in markdown
    assert "Generyczne/off-brand" in markdown
    assert "Największy brak produktu" in markdown
    assert "brak" in markdown


def test_content_uat_result_has_no_scorecard_follow_up_for_strong_approved_material() -> None:
    artifact = "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "5 minut",
        "punkty_niezrozumienia": "Brak.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": [artifact],
        "oceny_materialow_review": [
            {
                "material": artifact,
                "decyzja": "zatwierdź",
                "czytelnosc_1_5": 5,
                "uzytecznosc_1_5": 5,
                "glos_ekologus_1_5": 4,
                "zaufanie_do_blokad_1_5": 4,
                "dopasowanie_cta_1_5": 4,
                "najwazniejsza_poprawka": "brak",
            }
        ],
        "pytania_skad_to_wzielo": "Brak pytań.",
        "miejsca_generyczne_off_brand": "Brak.",
        "najwiekszy_brak_produktu": "Brak.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "tak",
    }

    report = build_content_uat_result_report(payload)

    assert report["review_follow_up_suggestions"] == []
    assert "Brak automatycznych sugestii ze scorecardu" in render_markdown(report)


def test_content_uat_result_requires_scorecard_for_shown_artifacts() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "punkty_niezrozumienia": "Brak oceny materiału review.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Brak.",
        "najwiekszy_brak_produktu": "Brak.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: dodać scorecard do wyniku UAT"],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    assert "Brak scorecardu materiałów review" in str(error.value)


def test_content_uat_result_rejects_invalid_scorecard_values() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "punkty_niezrozumienia": "Skala ocen była niejasna.",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pokazane_materialy_review": ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"],
        "oceny_materialow_review": [
            {
                "material": "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md",
                "decyzja": "może",
                "czytelnosc_1_5": 6,
                "uzytecznosc_1_5": 4,
                "glos_ekologus_1_5": 4,
                "zaufanie_do_blokad_1_5": 4,
                "dopasowanie_cta_1_5": 4,
                "najwazniejsza_poprawka": "UZUPEŁNIJ",
            }
        ],
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Brak.",
        "najwiekszy_brak_produktu": "Brak.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "public_service_review_actions_czytelne": "tak",
        "private_review_actions_czytelne": "tak",
        "private_policy_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: doprecyzować skalę scorecardu"],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    message = str(error.value)
    assert "musi mieć decyzję: zatwierdź, popraw, odrzuć albo odśwież" in message
    assert "musi mieć czytelność 1-5" in message
    assert "musi mieć najwazniejsza_poprawka" in message


def _scorecard(artifacts: list[str], *, decision: str = "popraw") -> list[dict[str, object]]:
    return [
        {
            "material": artifact,
            "decyzja": decision,
            "czytelnosc_1_5": 4,
            "uzytecznosc_1_5": 5,
            "glos_ekologus_1_5": 4,
            "zaufanie_do_blokad_1_5": 4,
            "dopasowanie_cta_1_5": 3,
            "najwazniejsza_poprawka": "Doprecyzować język i kolejny krok.",
        }
        for artifact in artifacts
    ]


def _live_context() -> dict[str, object]:
    return {
        "api_base": "http://127.0.0.1:8000",
        "queue": {
            "queue_status": "blocked",
            "candidate_count": 1,
            "actionable_candidate_count": 1,
            "candidates": [
                {
                    "work_item_id": "content_work_item_content_decision_https___www_ekologus_pl",
                    "title": "SEO: odśwież lub scal \"ekologus\"",
                    "topic": "ekologus",
                    "recommended_mode": "refresh",
                    "recommended_mode_label": "odśwież istniejącą treść",
                    "final_canonical_url": "https://www.ekologus.pl/",
                    "reason": "GSC pokazuje wyświetlenia bez kliknięć.",
                    "safe_next_step": "Przygotuj plan odświeżenia strony.",
                    "evidence_ids": ["ev_gsc", "ev_wp"],
                    "source_connectors": [
                        "google_search_console",
                        "wordpress_ekologus",
                    ],
                }
            ],
        },
        "service_profile": {
            "read_only": True,
            "coverage_summary": {"ready_for_daily_content": False},
            "review_action_summary": {
                "first_review_action_id": "renamed_public_service_bdo_review",
                "first_review_action_label": "Sprawdź kartę BDO",
                "first_review_action_scope": "public_service_card",
                "first_review_action_priority": "medium",
                "first_review_action_target_card_id": "ekologus_service_bdo_reporting",
                "first_review_required_fields": [
                    "action_id",
                    "source_trace_clear",
                ],
                "first_review_safe_next_step": (
                    "Najpierw sprawdź publiczną kartę BDO."
                ),
            },
            "private_source_proposal_summary": {"promotion_ready": False},
            "source_fact_coverage": {
                "private_review_queue": [
                    {
                        "target_card_title": (
                            "Bezpieczeństwo prawne, poufność i zgody"
                        ),
                        "scope": "claim_policy",
                        "source_block_refs": ["KB_021_BEZPIECZENSTWO_PRAWNE"],
                        "eval_case_ids": [
                            "goal_005_private_claim_policy_review",
                            "goal_006_claim_ledger_gate",
                        ],
                        "retention_decision": "pending_owner_decision",
                        "redacted": True,
                        "source_trace_ready": True,
                        "safe_next_step": (
                            "Pokaż Wilkowi source trace bez raw private text."
                        ),
                    }
                ]
            },
            "private_review_value": {
                "review_questions": [
                    (
                        "Czy proponowane CTA brzmi jak realny następny krok "
                        "Ekologus, a nie obietnica wyniku?"
                    ),
                    (
                        "Czy opisany problem kupującego faktycznie pasuje do "
                        "rozmów z klientami Ekologus?"
                    ),
                ]
            },
            "private_source_proposals": [
                {
                    "target_card_id": "ekologus_service_eko_opieka_calendar",
                    "scope": "service",
                }
            ],
            "review_actions": [
                {
                    "action_id": "renamed_public_service_bdo_review",
                    "review_scope": "public_service_card",
                    "decision_options": [
                        "approve",
                        "needs_changes",
                        "stale",
                        "reject",
                    ],
                },
                {
                    "action_id": "renamed_private_service_review",
                    "review_scope": "private_service_proposal",
                    "target_card_id": "ekologus_service_eko_opieka_calendar",
                }
            ],
        },
        "sales_brief_traces": {
            "content_work_item_content_decision_https___www_ekologus_pl": {
                "status": "ready",
                "signal_quality_status": "review_required",
                "signal_quality_status_label": "sygnał użyteczny, ale wymaga review",
                "signal_quality_reason": (
                    "Są dowody i źródła, ale część wiedzy wymaga review."
                ),
                "signal_quality_safe_next_step": (
                    "Pokaż brief Wilkowi i zapisz decyzję review."
                ),
                "evidence_id_count": 2,
                "source_connector_count": 2,
                "source_fact_count": 2,
                "knowledge_constraint_count": 1,
                "review_required_knowledge_card_count": 1,
                "measurement_baseline_ready": True,
                "knowledge_constraint_evidence_ids": [
                    "ev_content_service_profile_source_facts"
                ],
            }
        },
    }


def _live_context_with_blocked_and_actionable_candidates() -> dict[str, object]:
    live_context = _live_context()
    live_context["queue"] = {
        "queue_status": "blocked",
        "candidate_count": 3,
        "actionable_candidate_count": 1,
        "candidates": [
            {
                "work_item_id": "content_work_item_content_decision_ga4_tracking_gap_review",
                "recommended_mode": "block",
                "evidence_ids": ["ev_ga4"],
                "source_connectors": ["google_analytics_4"],
            },
            {
                "work_item_id": "content_work_item_content_decision_ahrefs_gap_records_review",
                "recommended_mode": "block",
                "evidence_ids": ["ev_ahrefs"],
                "source_connectors": ["ahrefs"],
            },
            {
                "work_item_id": "content_work_item_content_decision_https___www_ekologus_pl",
                "recommended_mode": "refresh",
                "final_canonical_url": "https://www.ekologus.pl/",
                "source_public_url": "https://www.ekologus.pl/",
                "preflight_status": "plan_allowed",
                "evidence_ids": ["ev_gsc", "ev_wp"],
                "source_connectors": [
                    "google_search_console",
                    "wordpress_ekologus",
                ],
            },
        ],
    }
    live_context["sales_brief_traces"] = {
        "content_work_item_content_decision_ga4_tracking_gap_review": {
            "status": "blocked",
        },
        "content_work_item_content_decision_ahrefs_gap_records_review": {
            "status": "blocked",
        },
        "content_work_item_content_decision_https___www_ekologus_pl": {
            "status": "ready",
            "knowledge_constraint_count": 1,
            "knowledge_constraint_evidence_ids": [
                "ev_content_service_profile_source_facts"
            ],
        },
    }
    return live_context
