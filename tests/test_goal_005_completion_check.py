from __future__ import annotations

import json
from pathlib import Path

from scripts.goal_005_completion_check import (
    build_completion_report,
    render_markdown,
    validate_owner_defer,
)


def test_goal_005_completion_check_blocks_without_uat_or_defer() -> None:
    report = build_completion_report()

    assert report["status"] == "blocked_missing_goal_005_uat_proof"
    assert report["missing_input"] == "goal_005_uat_result_or_owner_defer"
    assert "ukończony Goal 005" in report["blocked_claims"]
    assert "Service Profile" in report["safe_scope"]


def test_goal_005_completion_check_accepts_uat_result(tmp_path: Path) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "czas_do_zrozumienia_statusu": "8 minut",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": [
                    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
                ],
                "pytania_skad_to_wzielo": "Źródła danych były jasne.",
                "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
                "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
                "wilku_rozumie_blokady_pelnego_uat": "tak",
                "service_profile_czytelny": "tak",
                "public_service_review_actions_czytelne": "tak",
                "private_review_actions_czytelne": "tak",
                "private_policy_review_actions_czytelne": "tak",
                "mozna_przejsc_do_pelnego_content_uat": "nie",
                "follow_up_beads": ["wilq-seo-next: realny follow-up po sesji"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_completion_report(uat_result=result_path)

    assert report["status"] == "complete_with_uat"
    assert report["proof_type"] == "real_wilku_content_uat"
    assert report["selected_work_item"] == (
        "content_work_item_content_decision_https___www_ekologus_pl"
    )
    assert report["shown_review_artifacts"] == [
        "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
    ]

    markdown = render_markdown(report)
    assert "# Sprawdzenie domknięcia Goal 005" in markdown
    assert "Pokazane materiały review" in markdown


def test_goal_005_completion_check_accepts_owner_defer(tmp_path: Path) -> None:
    defer_path = tmp_path / "goal-005-owner-defer.json"
    defer_path.write_text(
        json.dumps(
            {
                "odroczenie_goal_005_uat": True,
                "data": "2026-07-02",
                "osoba": "Kornel",
                "powod": "Wilku nie jest dostępny na sesję tej nocy.",
                "co_mozna_pokazac": "Można pokazać review handoffs i Service Profile.",
                "ryzyko_rezydualne": (
                    "Brak realnej walidacji, czy Wilku rozumie blokady i źródła."
                ),
                "czego_nie_wolno_twierdzic": [
                    "ukończony UAT",
                    "production-depth readiness",
                ],
                "nastepny_przeglad": "po realnej sesji z Wilkiem",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_completion_report(owner_defer=defer_path)

    assert report["status"] == "owner_deferred"
    assert report["proof_type"] == "explicit_goal_005_owner_defer"
    assert "Brak realnej walidacji" in report["residual_risk"]
    assert "production-depth readiness" in report["blocked_claims"]


def test_goal_005_owner_defer_requires_residual_risk(tmp_path: Path) -> None:
    defer_path = tmp_path / "goal-005-owner-defer.json"
    defer_path.write_text(
        json.dumps(
            {
                "odroczenie_goal_005_uat": True,
                "data": "2026-07-02",
                "osoba": "Kornel",
                "powod": "Wilku nie jest dostępny.",
                "co_mozna_pokazac": "Można pokazać przygotowanie.",
                "czego_nie_wolno_twierdzic": ["ukończony UAT"],
                "nastepny_przeglad": "po sesji",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = validate_owner_defer(defer_path)

    assert report["valid"] is False
    assert "brak pola owner defer: ryzyko_rezydualne" in report["errors"]
