from __future__ import annotations

import pytest

from scripts.record_marketer_uat_result import (
    build_uat_result_report,
    render_markdown,
)


def test_uat_result_report_turns_failures_and_confusion_into_tasks() -> None:
    payload = {
        "date": "2026-06-25",
        "person": "Marketer Ekologus",
        "command_center": "pass wiem, że mam zacząć od Merchant",
        "merchant": {
            "result": "fail",
            "note": "Nie było jasne, że zgłoszenia nie są unikalnymi SKU.",
        },
        "content": "pass widzę BDO jako odświeżenie albo scalenie",
        "ads": "pass rozumiem, że kosztu pozyskania celu ani zwrotu z reklam są zablokowane",
        "ga4": "fail (not set) wyglądało jak zła kampania",
        "biggest_real_boost": "Widok treści daje gotowy brief do review.",
        "biggest_confusion": "Merchant count semantics",
        "new_tasks": ["Dodać tooltip przy liczbie zgłoszeń Merchant"],
        "ready_without_developer": "no",
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
    tasks = report["task_candidates"]
    assert any(task["source"] == "merchant" for task in tasks)
    assert any(task["source"] == "ga4" for task in tasks)
    assert any(task["source"] == "biggest_confusion" for task in tasks)
    assert any(task["category"] == "marketer_feedback" for task in tasks)
    assert "Nie odblokowuje publikacji ani zapisu zmian" in report["safety_note"]


def test_uat_result_report_rejects_placeholders() -> None:
    payload = {
        "date": "<YYYY-MM-DD>",
        "person": "<marketer>",
        "command_center": "<pass|fail + note>",
        "merchant": "pass ok",
        "content": "pass ok",
        "ads": "pass ok",
        "ga4": "pass ok",
        "ready_without_developer": "<yes|no>",
    }

    with pytest.raises(RuntimeError) as error:
        build_uat_result_report(payload)

    message = str(error.value)
    assert "Missing or placeholder field: date" in message
    assert "Missing or placeholder route result: command_center" in message
    assert "ready_without_developer must be yes or no" in message


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
                "task": "Fix Merchant count copy.",
            }
        ],
    }

    markdown = render_markdown(report)

    assert "# Ekologus Marketer UAT Result" in markdown
    assert "`fail` Merchant" in markdown
    assert "`demo_ux` from `merchant`" in markdown
    assert "Fix Merchant count copy." in markdown
