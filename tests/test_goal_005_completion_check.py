from __future__ import annotations

import json
from pathlib import Path

from scripts.goal_005_completion_check import (
    blocked_report,
    build_completion_report,
    render_markdown,
    uat_live_provenance_summary,
    validate_owner_defer,
)


def test_goal_005_completion_check_blocks_without_uat_or_defer() -> None:
    report = build_completion_report()

    assert report["status"] == "blocked_missing_goal_005_uat_proof"
    assert report["missing_input"] == "goal_005_uat_result_or_owner_defer"
    assert "ukończony Goal 005" in report["blocked_claims"]
    assert "Service Profile" in report["safe_scope"]


def test_goal_005_completion_check_blocks_uat_result_that_needs_follow_up(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": (
                    "Nie było jasne, czemu pełny UAT nadal jest zablokowany."
                ),
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

    assert report["status"] == "blocked_missing_goal_005_uat_proof"
    assert report["missing_input"] == "goal_005_uat_ready_for_full_content_uat"
    assert any("needs_follow_up_before_full_content_uat" in detail for detail in report["details"])
    assert "realny dowód użyteczności dla Wilka" in report["blocked_claims"]


def test_goal_005_completion_check_blocks_ready_uat_without_plain_review_model(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": [
                    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
                ],
                "pytania_skad_to_wzielo": "Źródła danych były jasne.",
                "miejsca_generyczne_off_brand": "Nie znaleziono krytycznych miejsc.",
                "najwiekszy_brak_produktu": "Brak dalszych blokad dla tego testu.",
                "wilku_rozumie_blokady_pelnego_uat": "tak",
                "service_profile_czytelny": "tak",
                "public_service_review_actions_czytelne": "tak",
                "private_review_actions_czytelne": "tak",
                "private_policy_review_actions_czytelne": "tak",
                "mozna_przejsc_do_pelnego_content_uat": "tak",
                "follow_up_beads": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_completion_report(uat_result=result_path)

    assert report["status"] == "blocked_missing_goal_005_uat_proof"
    assert report["missing_input"] == "goal_005_required_review_artifacts"
    assert any(
        "2026-07-02-wilq-marketing-content-model.md" in detail
        for detail in report["details"]
    )
    assert any("2026-07-02-co-pokazac-wilkowi.md" in detail for detail in report["details"])


def test_goal_005_completion_check_renders_uat_sales_brief_provenance() -> None:
    provenance = uat_live_provenance_summary(
        {
            "selected_work_item_found": True,
            "selected_sales_brief_status": "blocked",
            "selected_sales_brief_blockers": [
                "Brakuje karty usługi",
                "Brakuje karty CTA",
            ],
            "selected_sales_brief_constraint_evidence_ids": [
                "ev_content_service_profile_source_facts"
            ],
            "production_depth_ready": False,
        }
    )

    report = blocked_report(
        "goal_005_uat_ready_for_full_content_uat",
        ["UAT result is valid, but it is not ready for Goal 005 completion."],
        uat_live_provenance=provenance,
    )
    markdown = render_markdown(report)

    assert report["uat_live_provenance"] == provenance
    assert "## Live UAT provenance" in markdown
    assert "Sales Brief status: `blocked`" in markdown
    assert "Sales Brief blocker: Brakuje karty usługi; Brakuje karty CTA" in markdown
    assert "Sales Brief constraint evidence: ev_content_service_profile_source_facts" in markdown
    assert "Production-depth ready: nie" in markdown


def test_goal_005_completion_check_accepts_ready_uat_result(tmp_path: Path) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": [
                    "docs/handoffs/2026-07-02-wilq-marketing-content-model.md",
                    "docs/handoffs/2026-07-02-co-pokazac-wilkowi.md",
                    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
                ],
                "pytania_skad_to_wzielo": "Źródła danych były jasne.",
                "miejsca_generyczne_off_brand": "Nie znaleziono krytycznych miejsc.",
                "najwiekszy_brak_produktu": "Brak dalszych blokad dla tego testu.",
                "wilku_rozumie_blokady_pelnego_uat": "tak",
                "service_profile_czytelny": "tak",
                "public_service_review_actions_czytelne": "tak",
                "private_review_actions_czytelne": "tak",
                "private_policy_review_actions_czytelne": "tak",
                "mozna_przejsc_do_pelnego_content_uat": "tak",
                "follow_up_beads": [],
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
        "docs/handoffs/2026-07-02-wilq-marketing-content-model.md",
        "docs/handoffs/2026-07-02-co-pokazac-wilkowi.md",
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
                    "ukończony Goal 005",
                    "realny dowód użyteczności dla Wilka",
                    "production-depth readiness",
                    "gotowość finalnego draftu albo publikacji",
                ],
                "nastepny_przeglad": "po realnej sesji z Wilkiem",
                "nastepny_input_uat": (
                    "Pokazać Wilkowi live UAT packet, BDO handoff, Eko-Opieka "
                    "handoff i prywatne governance pola review."
                ),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_completion_report(owner_defer=defer_path)

    assert report["status"] == "owner_deferred"
    assert report["proof_type"] == "explicit_goal_005_owner_defer"
    assert "Brak realnej walidacji" in report["residual_risk"]
    assert "live UAT packet" in report["next_uat_input"]
    assert "production-depth readiness" in report["blocked_claims"]
    markdown = render_markdown(report)
    assert "Następny input UAT" in markdown
    assert "prywatne governance pola review" in markdown


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
    assert "brak pola owner defer: nastepny_input_uat" in report["errors"]


def test_goal_005_owner_defer_requires_core_blocked_claims(tmp_path: Path) -> None:
    defer_path = tmp_path / "goal-005-owner-defer.json"
    defer_path.write_text(
        json.dumps(
            {
                "odroczenie_goal_005_uat": True,
                "data": "2026-07-02",
                "osoba": "Kornel",
                "powod": "Wilku nie jest dostępny.",
                "co_mozna_pokazac": "Można pokazać przygotowanie.",
                "ryzyko_rezydualne": "Brak realnej walidacji z Wilkiem.",
                "czego_nie_wolno_twierdzic": ["ukończony UAT"],
                "nastepny_przeglad": "po sesji",
                "nastepny_input_uat": "Pokazać Wilkowi UAT packet.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = validate_owner_defer(defer_path)

    assert report["valid"] is False
    assert any(
        "czego_nie_wolno_twierdzic musi zawierać" in error
        and "production-depth readiness" in error
        and "gotowość finalnego draftu albo publikacji" in error
        for error in report["errors"]
    )
