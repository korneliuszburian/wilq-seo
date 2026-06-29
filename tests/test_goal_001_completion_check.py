from __future__ import annotations

from pathlib import Path

from scripts.goal_001_completion_check import (
    build_completion_report,
    validate_owner_defer,
)


def test_goal_completion_check_blocks_without_uat_or_defer() -> None:
    report = build_completion_report()

    assert report["status"] == "blocked_missing_uat_proof"
    assert report["missing_input"] == "real_marketer_uat_result_or_owner_defer"
    assert "domknięcie Goal 001" in report["blocked_claims"]
    assert "zakończony dowód użyteczności" in report["safe_scope"]


def test_goal_completion_check_accepts_real_uat_result(tmp_path: Path) -> None:
    result_path = tmp_path / "marketer-uat-result.json"
    result_path.write_text(
        """
        {
          "data": "2026-06-29",
          "osoba": "Wilku",
          "centrum_pracy": "zaliczone wiem, co zrobić dalej",
          "merchant": "zaliczone rozumiem kolejkę problemów",
          "treści": "zaliczone widzę, co zachować albo odświeżyć",
          "google_ads": "zaliczone rozumiem blokady optymalizacji",
          "ga4": "zaliczone rozumiem różnicę między pomiarem i jakością",
          "największy_realny_zysk": "Treści pokazują następny krok.",
          "największa_niejasność": "brak",
          "nowe_zadania": [],
          "gotowe_bez_developera": "tak"
        }
        """,
        encoding="utf-8",
    )

    report = build_completion_report(uat_result=result_path)

    assert report["status"] == "complete_with_uat"
    assert report["proof_type"] == "real_marketer_uat"
    assert report["ready_without_developer"] == "yes"


def test_goal_completion_check_accepts_polish_owner_defer(tmp_path: Path) -> None:
    defer_path = tmp_path / "owner-defer.json"
    defer_path.write_text(
        """
        {
          "odroczenie_realnego_uat": true,
          "data": "2026-06-29",
          "osoba": "Owner",
          "powód": "Wilku nie jest dostępny dzisiaj.",
          "co_można_pokazać": "Zweryfikowany cockpit i pakiet UAT.",
          "zablokowane_obietnice": [
            "gotowość bez developera",
            "potwierdzona użyteczność marketera"
          ]
        }
        """,
        encoding="utf-8",
    )

    report = build_completion_report(owner_defer=defer_path)

    assert report["status"] == "owner_deferred"
    assert report["owner"] == "Owner"
    assert report["safe_scope"] == "Zweryfikowany cockpit i pakiet UAT."
    assert "gotowość bez developera" in report["blocked_claims"]


def test_owner_defer_requires_explicit_blocked_claims(tmp_path: Path) -> None:
    defer_path = tmp_path / "owner-defer.json"
    defer_path.write_text(
        """
        {
          "odroczenie_realnego_uat": true,
          "data": "2026-06-29",
          "osoba": "Owner",
          "powód": "Wilku nie jest dostępny dzisiaj.",
          "co_można_pokazać": "Zweryfikowany cockpit i pakiet UAT.",
          "zablokowane_obietnice": []
        }
        """,
        encoding="utf-8",
    )

    report = validate_owner_defer(defer_path)

    assert report["valid"] is False
    assert "zablokowane_obietnice musi być niepustą listą" in report["errors"]


def test_owner_defer_rejects_stale_alias_fields(tmp_path: Path) -> None:
    defer_path = tmp_path / "owner-defer.json"
    defer_path.write_text(
        """
        {
          "defer_uat": true,
          "date": "2026-06-29",
          "owner": "Owner",
          "reason": "No marketer today.",
          "safe_to_show": "Cleanup proof only.",
          "blocked_claims": [
            "gotowość bez developera"
          ]
        }
        """,
        encoding="utf-8",
    )

    report = validate_owner_defer(defer_path)

    assert report["valid"] is False
    assert "defer ownera musi ustawić odroczenie_realnego_uat na true" in report["errors"]
    assert "brak pola defer ownera: data" in report["errors"]
