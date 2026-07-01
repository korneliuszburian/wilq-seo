from __future__ import annotations

import pytest

from scripts.record_goal_005_content_uat_result import (
    build_content_uat_result_report,
    render_markdown,
)


def test_content_uat_result_records_follow_up_when_full_uat_blocked() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pytania_skad_to_wzielo": "Chce widzieć publiczny URL obok evidence ID.",
        "miejsca_generyczne_off_brand": "CTA było za szerokie dla usług środowiskowych.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonej karty dla Eko-Opieki.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "private_review_actions_czytelne": "nie",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-xyz: doprecyzować private review action copy"],
    }

    report = build_content_uat_result_report(payload)

    assert report["report_type"] == "goal_005_content_uat_result_v1"
    assert report["selected_work_item"] == payload["wybrany_work_item"]
    assert report["overall_status"] == "needs_follow_up_before_full_content_uat"
    assert report["missing_follow_up_task"] is False
    assert report["follow_up_tasks"] == [
        "wilq-seo-xyz: doprecyzować private review action copy"
    ]
    assert "Nie promuje private proposals" in report["safety_note"]
    assert "nie odblokowuje publikacji" in report["safety_note"]


def test_content_uat_result_rejects_placeholders_and_invalid_booleans() -> None:
    payload = {
        "data_sesji": "<YYYY-MM-DD>",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "-",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pytania_skad_to_wzielo": "TODO",
        "miejsca_generyczne_off_brand": "brak",
        "najwiekszy_brak_produktu": "brak",
        "wilku_rozumie_blokady_pelnego_uat": "yes",
        "service_profile_czytelny": "tak",
        "private_review_actions_czytelne": "nie",
        "mozna_przejsc_do_pelnego_content_uat": "maybe",
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    message = str(error.value)
    assert "Brak pola albo placeholder: data sesji" in message
    assert "Brak pola albo placeholder: czas do zrozumienia statusu" in message
    assert 'Brak pola albo placeholder: pytania "skąd to wzięło?"' in message
    assert "czy Wilku rozumie blokady pełnego UAT musi mieć wartość tak albo nie" in message
    assert "czy można przejść do pełnego content UAT musi mieć wartość tak albo nie" in message


def test_content_uat_result_requires_follow_up_when_blocked() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "12 minut",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pytania_skad_to_wzielo": "Wystarczy, ale chce linki publiczne.",
        "miejsca_generyczne_off_brand": "Nagłówki brzmią jak zwykłe SEO.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonej usługi BDO.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "private_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": [],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload)

    assert "Gdy pełny content UAT jest zablokowany, wpisz follow_up_beads" in str(
        error.value
    )


def test_content_uat_result_ready_only_when_all_gates_are_yes() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "6 minut",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pytania_skad_to_wzielo": "Evidence IDs i source connectors wystarczają.",
        "miejsca_generyczne_off_brand": "Brak.",
        "najwiekszy_brak_produktu": "Brak.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "private_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "tak",
    }

    report = build_content_uat_result_report(payload)

    assert report["overall_status"] == "ready_for_full_content_uat"
    assert report["missing_follow_up_task"] is False

    markdown = render_markdown(report)
    assert "# Wynik Goal 005 content UAT" in markdown
    assert "Status: gotowe do pełnego content UAT" in markdown
    assert "Pytania \"skąd to wzięło?\"" in markdown
    assert "Generyczne/off-brand" in markdown
    assert "Największy brak produktu" in markdown
    assert "brak" in markdown
