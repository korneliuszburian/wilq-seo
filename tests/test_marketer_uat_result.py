from __future__ import annotations

import pytest

from scripts.record_marketer_uat_result import (
    build_uat_result_report,
    render_markdown,
)


def test_uat_result_report_turns_failures_and_confusion_into_tasks() -> None:
    payload = {
        "data": "2026-06-25",
        "osoba": "Marketer Ekologus",
        "centrum_pracy": "zaliczone wiem, że mam zacząć od Merchant",
        "merchant": {
            "wynik": "niezaliczone",
            "notatka": "Nie było jasne, że zgłoszenia nie są unikalnymi SKU.",
        },
        "treści": "zaliczone widzę BDO jako odświeżenie albo scalenie",
        "google_ads": (
            "zaliczone rozumiem, że kosztu pozyskania celu ani zwrotu z reklam są zablokowane"
        ),
        "ga4": "niezaliczone (not set) wyglądało jak zła kampania",
        "największy_realny_zysk": "Widok treści daje gotowy brief do sprawdzenia.",
        "największa_niejasność": "Merchant count semantics",
        "nowe_zadania": ["Dodać tooltip przy liczbie zgłoszeń Merchant"],
        "gotowe_bez_developera": "nie",
    }

    report = build_uat_result_report(payload)

    assert report["report_type"] == "ekologus_marketer_uat_result_v1"
    assert report["overall_status"] == "needs_tasks_before_unassisted_demo"
    assert report["ready_without_developer"] == "no"
    assert [item["result"] for item in report["route_results"]] == [
        "pass",
        "fail",
        "pass",
        "pass",
        "fail",
    ]
    assert [item["label"] for item in report["route_results"]] == [
        "Centrum pracy",
        "Merchant",
        "Treści",
        "Google Ads",
        "GA4",
    ]
    tasks = report["task_candidates"]
    assert any(task["source"] == "merchant" for task in tasks)
    assert any(task["source"] == "ga4" for task in tasks)
    assert any(task["source"] == "biggest_confusion" for task in tasks)
    assert any(task["category"] == "marketer_feedback" for task in tasks)
    assert any("Popraw niejasność UAT w widoku Merchant" in task["task"] for task in tasks)
    assert "Nie odblokowuje publikacji ani zapisu zmian" in report["safety_note"]
    serialized = str(report)
    assert "Command Center" not in serialized
    assert "Content Planner" not in serialized
    assert "Ads Doctor" not in serialized


def test_uat_result_report_rejects_placeholders() -> None:
    payload = {
        "data": "<YYYY-MM-DD>",
        "osoba": "<marketer>",
        "centrum_pracy": "<zaliczone|niezaliczone + notatka>",
        "merchant": "zaliczone ok",
        "treści": "zaliczone ok",
        "google_ads": "zaliczone ok",
        "ga4": "zaliczone ok",
        "gotowe_bez_developera": "<tak|nie>",
    }

    with pytest.raises(RuntimeError) as error:
        build_uat_result_report(payload)

    message = str(error.value)
    assert "Brak pola UAT albo placeholder: data" in message
    assert "Brak wyniku UAT dla widoku: centrum_pracy" in message
    assert "gotowe_bez_developera musi mieć wartość tak albo nie" in message


def test_uat_result_markdown_lists_task_candidates() -> None:
    report = {
        "report_type": "ekologus_marketer_uat_result_v1",
        "date": "2026-06-25",
        "person": "Marketer Ekologus",
        "overall_status": "needs_tasks_before_unassisted_demo",
        "ready_without_developer": "no",
        "safety_note": "Ten raport zapisuje feedback UAT.",
        "route_results": [
            {
                "label": "Merchant",
                "result": "fail",
                "note": "Liczba zgłoszeń była niejasna.",
            }
        ],
        "biggest_real_boost": "Widok treści",
        "biggest_confusion": "Merchant count semantics",
        "task_candidates": [
            {
                "category": "demo_ux",
                "source": "merchant",
                "task": "Doprecyzować licznik zgłoszeń Merchant.",
            }
        ],
    }

    markdown = render_markdown(report)

    assert "# Wynik UAT marketera Ekologus" in markdown
    assert "`niezaliczone` Merchant" in markdown
    assert "niejasność demo / Merchant" in markdown
    assert "Doprecyzować licznik zgłoszeń Merchant." in markdown
    assert "`demo_ux`" not in markdown
    assert "Route Results" not in markdown
    assert "Task Candidates" not in markdown
    assert "Feedback" not in markdown


def test_uat_result_report_accepts_polish_packet_template_keys() -> None:
    payload = {
        "data": "2026-06-29",
        "osoba": "Wilku",
        "centrum_pracy": "zaliczone wiem, co zrobić dalej",
        "merchant": {"wynik": "niezaliczone", "niejasność": "Licznik był niejasny."},
        "treści": "zaliczone widzę publiczny URL",
        "google_ads": "zaliczone rozumiem blokady kosztu pozyskania celu",
        "ga4": "zaliczone rozumiem problem pomiaru",
        "największy_realny_zysk": "Treści",
        "największa_niejasność": "Merchant",
        "nowe_zadania": ["Doprecyzować licznik Merchant"],
        "gotowe_bez_developera": "nie",
    }

    report = build_uat_result_report(payload)

    assert report["date"] == "2026-06-29"
    assert report["person"] == "Wilku"
    assert report["ready_without_developer"] == "no"
    assert [item["result"] for item in report["route_results"]] == [
        "pass",
        "fail",
        "pass",
        "pass",
        "pass",
    ]
    assert any(task["source"] == "merchant" for task in report["task_candidates"])


def test_uat_result_report_rejects_stale_english_packet_keys() -> None:
    payload = {
        "date": "2026-06-25",
        "person": "Marketer Ekologus",
        "command_center": "pass wiem, co zrobić dalej",
        "merchant": {"result": "pass", "note": "ok"},
        "content": "pass ok",
        "ads": "pass ok",
        "ga4": "pass ok",
        "ready_without_developer": "yes",
    }

    with pytest.raises(RuntimeError) as error:
        build_uat_result_report(payload)

    message = str(error.value)
    assert "Brak pola UAT albo placeholder: data" in message
    assert "Brak wyniku UAT dla widoku: centrum_pracy" in message


def test_uat_result_report_rejects_stale_english_result_values() -> None:
    payload = {
        "data": "2026-06-25",
        "osoba": "Marketer Ekologus",
        "centrum_pracy": "pass wiem, co zrobić dalej",
        "merchant": {"wynik": "pass", "notatka": "ok"},
        "treści": "zaliczone ok",
        "google_ads": "zaliczone ok",
        "ga4": "zaliczone ok",
        "największy_realny_zysk": "Treści",
        "największa_niejasność": "brak",
        "nowe_zadania": [],
        "gotowe_bez_developera": "yes",
    }

    with pytest.raises(RuntimeError) as error:
        build_uat_result_report(payload)

    message = str(error.value)
    assert "Wynik widoku centrum_pracy musi zaczynać się od zaliczone albo niezaliczone" in message
    assert "Wynik widoku merchant musi zaczynać się od zaliczone albo niezaliczone" in message
    assert "gotowe_bez_developera musi mieć wartość tak albo nie" in message
