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


def test_content_uat_result_records_live_packet_provenance_for_selected_item() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "wybrany_work_item": "content_work_item_content_decision_https___www_ekologus_pl",
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "private_review_actions_czytelne": "tak",
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
    assert provenance["service_profile_read_only"] is True
    assert provenance["production_depth_ready"] is False
    assert provenance["private_review_action_count"] == 1
    assert provenance["private_proposal_promotion_ready"] is False

    markdown = render_markdown(report)
    assert "## Live provenance" in markdown
    assert "Wybrany work item znaleziony w live packet: tak" in markdown
    assert "Źródła wybranego itemu: google_search_console, wordpress_ekologus" in markdown


def test_content_uat_result_rejects_work_item_missing_from_live_packet() -> None:
    payload = {
        "data_sesji": "2026-07-02",
        "osoba": "Wilku",
        "czas_do_zrozumienia_statusu": "8 minut",
        "wybrany_work_item": "content_work_item_fake",
        "pytania_skad_to_wzielo": "Źródła danych były jasne.",
        "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
        "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
        "wilku_rozumie_blokady_pelnego_uat": "tak",
        "service_profile_czytelny": "tak",
        "private_review_actions_czytelne": "tak",
        "mozna_przejsc_do_pelnego_content_uat": "nie",
        "follow_up_beads": ["wilq-seo-next: wybrać konkretniejszy temat UAT"],
    }

    with pytest.raises(RuntimeError) as error:
        build_content_uat_result_report(payload, live_context=_live_context())

    assert "Wybrany work item nie występuje w aktualnym live UAT packet" in str(
        error.value
    )


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
                    "recommended_mode": "refresh",
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
            "private_source_proposal_summary": {"promotion_ready": False},
            "review_actions": [
                {
                    "action_id": "service_profile_review_private_proposal_example",
                }
            ],
        },
    }
