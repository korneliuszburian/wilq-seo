from __future__ import annotations

import json
from pathlib import Path

from scripts.goal_005_completion_check import (
    blocked_report,
    build_completion_report,
    build_owner_defer_example,
    goal_005_next_uat_input,
    goal_005_pre_demo_audit_summary,
    render_markdown,
    render_next_uat_input,
    uat_live_provenance_summary,
    validate_owner_defer,
)

FULL_REVIEW_ARTIFACTS = [
    "docs/handoffs/2026-07-03-wilku-service-profile-review-now.md",
    "docs/handoffs/2026-07-02-wilq-marketing-content-model.md",
    "docs/handoffs/2026-07-02-co-pokazac-wilkowi.md",
    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md",
    "docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md",
    "docs/handoffs/2026-07-02-wilku-social-history-blocker.md",
]


def test_goal_005_completion_check_blocks_without_uat_or_defer() -> None:
    report = build_completion_report()

    assert report["status"] == "blocked_missing_goal_005_uat_proof"
    assert report["missing_input"] == "goal_005_uat_result_or_owner_defer"
    assert "ukończony Goal 005" in report["blocked_claims"]
    assert "Service Profile" in report["safe_scope"]
    assert report["pre_demo_audits"]["source_fact_coverage"]["knowledge_status"] == (
        "source_backed_review_required"
    )
    assert report["pre_demo_audits"]["source_fact_coverage"][
        "production_depth_percent"
    ] == 0
    assert report["pre_demo_audits"]["claim_ledger_gate"]["publish_ready_locked"] is True
    assert report["pre_demo_audits"]["skill_eval_coverage"]["hard_gap_count"] == 0
    assert report["next_uat_input"]["available"] is True
    assert report["next_uat_input"]["selected_work_item"] == "<work_item_id_z_uat_packet>"
    first_review = report["next_uat_input"]["first_service_profile_review"]
    assert first_review["action_id"]
    assert first_review["label"]
    assert first_review["scope"] == "public_service_card"
    assert "source_trace_clear" in first_review["required_fields"]
    assert report["next_uat_input"]["private_review_questions"]
    assert report["next_uat_input"]["private_source_trace_items"]
    assert report["next_uat_input"]["private_source_trace_items"][0]["source_blocks"]
    assert report["next_uat_input"]["private_source_trace_items"][0]["eval_cases"]
    assert report["next_uat_input"]["private_source_trace_items"][0]["trace_ready"] is True
    private_trace_text = json.dumps(
        report["next_uat_input"]["private_source_trace_items"],
        ensure_ascii=False,
    )
    assert "ocenaerowi" not in private_trace_text
    assert "ocenaed" not in private_trace_text
    assert "nie odblokowuj wiedza" not in private_trace_text
    assert "osobie oceniającej" in private_trace_text
    assert any(
        "CTA" in question
        for question in report["next_uat_input"]["private_review_questions"]
    )
    markdown = render_markdown(report)
    assert "Werdykt: materiały można pokazać Wilkowi do oceny" in markdown
    assert "Status techniczny: `blocked_missing_goal_005_uat_proof`" in markdown
    assert "Pytania o prywatną wiedzę" in markdown
    assert "Prywatny ślad źródłowy do pokazania" in markdown
    assert "ślad gotowy" in markdown
    assert "Czy proponowane CTA brzmi jak realny następny krok Ekologus" in markdown
    assert "--print-owner-defer-example --api-base http://127.0.0.1:8000" in markdown


def test_wilku_service_profile_handoff_includes_private_source_trace() -> None:
    handoff = Path(
        "docs/handoffs/2026-07-03-wilku-service-profile-review-now.md"
    ).read_text(encoding="utf-8")

    assert "Prywatny ślad źródłowy do pokazania bez raw private text" in handoff
    assert "KB_021_BEZPIECZENSTWO_PRAWNE" in handoff
    assert "KB_014_STYL_MARKI" in handoff
    assert "goal_005_private_claim_policy_review" in handoff
    assert "goal_006_claim_ledger_gate" in handoff
    assert "goal_005_private_evidence_policy_review" in handoff
    assert "decyzja właściciela wymagana" in handoff
    assert "zredagowane, ślad gotowy, bez promocji do finalnych treści" in handoff


def test_goal_005_pre_demo_audit_summary_tracks_current_gates() -> None:
    summary = goal_005_pre_demo_audit_summary()

    assert summary["source_fact_coverage"]["pass"] is True
    assert summary["source_fact_coverage"]["ready_for_daily_content"] is False
    assert summary["source_fact_coverage"]["private_review_required_count"] >= 5
    assert summary["source_fact_coverage"]["next_review_actions"]
    assert summary["source_fact_coverage"]["next_review_actions"][0]["action_id"]
    assert summary["claim_ledger_gate"]["pass"] is True
    assert summary["claim_ledger_gate"]["passed_count"] == summary["claim_ledger_gate"][
        "check_count"
    ]
    assert "missing_claim_ledger" in summary["claim_ledger_gate"][
        "structured_generation_blocks"
    ]
    assert summary["skill_eval_coverage"]["pass"] is True
    assert summary["skill_eval_coverage"]["case_count"] == summary["skill_eval_coverage"][
        "skill_dir_count"
    ]
    assert summary["latest_skill_eval_results"]["pass"] is True
    assert summary["latest_skill_eval_results"]["passing_skill_count"] == summary[
        "latest_skill_eval_results"
    ]["skill_count"]
    assert summary["latest_skill_eval_results"]["minimum_score"] >= 5
    assert summary["latest_skill_eval_results"]["maximum_score"] >= summary[
        "latest_skill_eval_results"
    ]["minimum_score"]
    assert summary["latest_skill_eval_results"]["strong_skill_count"] >= 1
    assert summary["latest_skill_eval_results"]["wilku_ready_skill_count"] >= 0


def test_goal_005_next_uat_input_prefers_live_actionable_candidate(monkeypatch) -> None:
    from scripts import record_goal_005_content_uat_result

    def fake_live_context(api_base: str) -> dict[str, object]:
        assert api_base == "http://127.0.0.1:8000"
        return {
            "queue": {
                "candidates": [
                    {
                        "work_item_id": (
                            "content_work_item_content_decision_ahrefs_gap_records_review"
                        ),
                        "recommended_mode": "block",
                        "source_connectors": ["ahrefs"],
                    },
                    {
                        "work_item_id": (
                            "content_work_item_content_decision_https___www_ekologus_pl"
                        ),
                        "recommended_mode": "refresh",
                        "final_canonical_url": "https://www.ekologus.pl/",
                        "source_public_url": "https://www.ekologus.pl/",
                        "preflight_status": "plan_allowed",
                        "source_connectors": [
                            "google_search_console",
                            "wordpress_ekologus",
                        ],
                    },
                ]
            },
            "sales_brief_traces": {
                "content_work_item_content_decision_https___www_ekologus_pl": {
                    "status": "ready",
                    "signal_quality_status": "review_required",
                    "signal_quality_status_label": "sygnał użyteczny, ale wymaga oceny",
                    "signal_quality_reason": (
                        "Są dowody i źródła, ale część wiedzy wymaga review."
                    ),
                    "signal_quality_safe_next_step": (
                        "Pokaż brief Wilkowi i zapisz decyzję review."
                    ),
                    "evidence_id_count": 2,
                    "source_connector_count": 2,
                    "source_fact_count": 2,
                    "knowledge_constraint_count": 18,
                }
            },
            "service_profile": {
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
                "source_fact_coverage": {
                    "private_review_queue": [
                        {
                            "target_card_title": "Eko-Opieka i Eko Kalendarz",
                            "scope": "service",
                            "source_block_refs": ["KB_001_EKO_OPIEKA"],
                            "eval_case_ids": ["goal_005_private_service_review"],
                            "retention_decision": "pending_owner_decision",
                            "redacted": True,
                            "source_trace_ready": True,
                            "safe_next_step": (
                                "Pokaż Wilkowi zwykły handoff i zdecyduj o review."
                            ),
                        }
                    ]
                }
            },
        }

    monkeypatch.setattr(
        record_goal_005_content_uat_result,
        "load_live_uat_context",
        fake_live_context,
    )

    next_input = goal_005_next_uat_input(api_base="http://127.0.0.1:8000")

    assert next_input["available"] is True
    assert next_input["selected_work_item"] == (
        "content_work_item_content_decision_https___www_ekologus_pl"
    )
    assert next_input["selected_sales_brief_signal_quality_status_label"] == (
        "sygnał użyteczny, ale wymaga oceny"
    )
    assert next_input["fillable_input"]["wybrany_work_item"] == (
        "content_work_item_content_decision_https___www_ekologus_pl"
    )
    assert next_input["first_service_profile_review"] == {
        "action_id": "renamed_public_service_bdo_review",
        "label": "Sprawdź kartę BDO",
        "scope": "public_service_card",
        "priority": "medium",
        "target_card_id": "ekologus_service_bdo_reporting",
        "gap_id": None,
        "required_fields": ["action_id", "source_trace_clear"],
        "safe_next_step": "Najpierw sprawdź publiczną kartę BDO.",
    }
    rendered = "\n".join(render_next_uat_input(next_input))
    assert "Pierwsza decyzja w Service Profile" in rendered
    public_part = rendered.split("ID do zapisu po rozmowie")[0]
    assert "renamed_public_service_bdo_review" not in public_part
    assert "ekologus_service_bdo_reporting" not in public_part
    assert "Najpierw sprawdź publiczną kartę BDO." in rendered
    assert "Co trzeba ocenić: którą decyzję zapisujemy" in rendered
    assert "czy źródło i pochodzenie faktu są jasne" in rendered
    assert "Jakość sygnału briefu: sygnał użyteczny, ale wymaga oceny" in rendered
    assert "ograniczenia wiedzy: 18" in rendered
    assert "Pytania o brief sprzedażowy" in rendered
    assert "Prywatny ślad źródłowy do pokazania" in rendered
    assert "Eko-Opieka i Eko Kalendarz / usługa / źródło: KB_001_EKO_OPIEKA" in rendered
    assert "bramka: goal_005_private_service_review" in rendered
    private_trace_section = rendered.split(
        "Prywatny ślad źródłowy do pokazania", 1
    )[1].split("Jakość sygnału briefu", 1)[0]
    assert "eval:" not in private_trace_section
    assert "decyzja właściciela wymagana" in rendered
    assert "zredagowane / ślad gotowy" in rendered
    assert (
        "Czy status briefu `sygnał użyteczny, ale wymaga oceny` mówi jasno"
        in rendered
    )
    assert "Czy następny krok briefu jest właściwy" in rendered
    assert "decyzja `renamed_public_service_bdo_review`" in rendered
    assert "karta `ekologus_service_bdo_reporting`" in rendered
    assert "approve/needs_changes/stale/reject" not in rendered
    assert "Service Profile - co pokazać teraz" in rendered
    assert "--api-base http://127.0.0.1:8000" in next_input["print_input_command"]
    assert "--print-session-card --api-base http://127.0.0.1:8000" in next_input[
        "session_card_command"
    ]
    assert "Komenda do karty rozmowy" in rendered
    assert "--print-session-card" in rendered


def test_goal_005_pre_demo_audit_summary_can_include_dashboard_usefulness(
    monkeypatch,
) -> None:
    from scripts import goal_005_completion_check

    def fake_dashboard_report(api_base: str) -> dict[str, object]:
        assert api_base == "http://127.0.0.1:8000"
        return {
            "pass": True,
            "surface_count": 13,
            "demo_ready_count": 12,
            "review_ready_count": 1,
            "blocked_count": 0,
            "production_failure_count": 0,
            "surfaces": [
                {
                    "surface_id": "knowledge",
                    "record_count": 15,
                    "lineage_count": 49,
                }
            ],
        }

    monkeypatch.setattr(
        goal_005_completion_check,
        "build_dashboard_usefulness_report",
        fake_dashboard_report,
    )

    summary = goal_005_pre_demo_audit_summary(api_base="http://127.0.0.1:8000")

    assert summary["dashboard_usefulness"] == {
        "pass": True,
        "surface_count": 13,
        "demo_ready_count": 12,
        "review_ready_count": 1,
        "blocked_count": 0,
        "production_failure_count": 0,
        "knowledge_record_count": 15,
        "knowledge_lineage_count": 49,
    }

    markdown = render_markdown(
        blocked_report(
            "goal_005_uat_result_or_owner_defer",
            ["Brakuje UAT."],
            pre_demo_audits=summary,
        )
    )

    assert "Dashboard:" in markdown
    assert "rekordy wiedzy: 15" in markdown
    assert "ślady źródłowe: 49" in markdown


def test_goal_005_completion_check_blocks_uat_result_that_needs_follow_up(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "werdykt_po_15_minutach": "przejdź do pełnego testu treści",
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
                "oceny_materialow_review": _scorecard(
                    ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"]
                ),
                "pytania_skad_to_wzielo": "Źródła danych były jasne.",
                "miejsca_generyczne_off_brand": "Za szeroki temat strony głównej.",
                "najwiekszy_brak_produktu": "Brak zatwierdzonych kart usług.",
                "odpowiedzi_wilka": [
                    {
                        "pytanie": "Czy Service Profile i pierwsza karta BDO są czytelne?",
                        "odpowiedz": "Tak, ale opis claimów nadal jest za techniczny.",
                        "follow_up": "Uprościć opis zablokowanych claimów.",
                    }
                ],
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
    assert report["uat_review_follow_up_suggestions"][0]["decision"] == "popraw"
    assert report["uat_wilku_review_answers"] == [
        {
            "pytanie": "Czy Service Profile i pierwsza karta BDO są czytelne?",
            "odpowiedz": "Tak, ale opis claimów nadal jest za techniczny.",
            "follow_up": "Uprościć opis zablokowanych claimów.",
        }
    ]
    assert any("dopasowanie CTA 3/5" in detail for detail in report["details"])
    assert "realny dowód użyteczności dla Wilka" in report["blocked_claims"]

    markdown = render_markdown(report)
    assert "## Follow-up ze scorecardu Wilka" in markdown
    assert "## Odpowiedzi Wilka na pytania WILQ" in markdown
    assert "Tak, ale opis claimów nadal jest za techniczny" in markdown
    assert "dopasowanie CTA 3/5" in markdown


def test_goal_005_completion_check_blocks_ready_uat_without_plain_review_model(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "werdykt_po_15_minutach": "przejdź do pełnego testu treści",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": [
                    "docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"
                ],
                "oceny_materialow_review": _scorecard(
                    ["docs/handoffs/2026-07-02-wilku-bdo-uat-review.md"]
                ),
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
    assert any(
        "2026-07-02-wilku-ekologus-ai-policy-review.md" in detail
        for detail in report["details"]
    )
    assert any(
        "2026-07-02-wilku-social-history-blocker.md" in detail
        for detail in report["details"]
    )


def test_goal_005_completion_check_blocks_ready_uat_with_scorecard_follow_up(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "werdykt_po_15_minutach": "przejdź do pełnego testu treści",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": FULL_REVIEW_ARTIFACTS,
                "oceny_materialow_review": _scorecard(
                    FULL_REVIEW_ARTIFACTS,
                    decision="zatwierdź",
                    cta_score=3,
                ),
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
    assert report["missing_input"] == "goal_005_review_scorecard_follow_up"
    assert report["uat_review_follow_up_suggestions"]
    assert any("dopasowanie CTA 3/5" in detail for detail in report["details"])
    assert "## Follow-up ze scorecardu Wilka" in render_markdown(report)


def test_goal_005_completion_check_blocks_live_uat_without_private_trace_scorecard(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts import goal_005_completion_check, record_goal_005_content_uat_result

    def fake_pre_demo_audits(api_base: str | None = None) -> dict[str, object]:
        assert api_base in {None, "http://127.0.0.1:8000"}
        return {}

    def fake_next_uat_input(api_base: str | None = None) -> dict[str, object]:
        assert api_base == "http://127.0.0.1:8000"
        return {"available": True}

    def fake_live_context(api_base: str) -> dict[str, object]:
        assert api_base == "http://127.0.0.1:8000"
        return {
            "api_base": api_base,
            "queue": {
                "queue_status": "ready",
                "candidate_count": 1,
                "actionable_candidate_count": 1,
                "candidates": [
                    {
                        "work_item_id": (
                            "content_work_item_content_decision_https___www_ekologus_pl"
                        ),
                        "title": "SEO: odśwież lub scal \"ekologus\"",
                        "recommended_mode": "refresh",
                        "final_canonical_url": "https://www.ekologus.pl/",
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
                "review_action_summary": {},
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
                                "goal_005_private_claim_policy_review"
                            ],
                            "retention_decision": "pending_owner_decision",
                            "redacted": True,
                            "source_trace_ready": True,
                        }
                    ]
                },
                "review_actions": [],
            },
            "sales_brief_traces": {
                "content_work_item_content_decision_https___www_ekologus_pl": {
                    "status": "ready",
                    "signal_quality_status": "ready",
                    "evidence_id_count": 2,
                    "source_connector_count": 2,
                    "source_fact_count": 2,
                    "knowledge_constraint_count": 1,
                }
            },
        }

    monkeypatch.setattr(
        goal_005_completion_check,
        "goal_005_pre_demo_audit_summary",
        fake_pre_demo_audits,
    )
    monkeypatch.setattr(
        goal_005_completion_check,
        "goal_005_next_uat_input",
        fake_next_uat_input,
    )
    monkeypatch.setattr(
        record_goal_005_content_uat_result,
        "load_live_uat_context",
        fake_live_context,
    )

    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "werdykt_po_15_minutach": "przejdź do pełnego testu treści",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": FULL_REVIEW_ARTIFACTS,
                "oceny_materialow_review": _scorecard(
                    FULL_REVIEW_ARTIFACTS,
                    decision="zatwierdź",
                    cta_score=5,
                ),
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

    report = build_completion_report(
        uat_result=result_path,
        api_base="http://127.0.0.1:8000",
    )

    assert report["status"] == "blocked_missing_goal_005_uat_proof"
    assert report["missing_input"] == "valid_goal_005_uat_result"
    assert any(
        "oceny_prywatnego_sladu_zrodlowego" in detail
        for detail in report["details"]
    )


def test_goal_005_completion_check_blocks_ready_uat_with_private_trace_follow_up(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts import goal_005_completion_check, record_goal_005_content_uat_result

    def fake_pre_demo_audits(api_base: str | None = None) -> dict[str, object]:
        assert api_base in {None, "http://127.0.0.1:8000"}
        return {}

    def fake_next_uat_input(api_base: str | None = None) -> dict[str, object]:
        assert api_base == "http://127.0.0.1:8000"
        return {"available": True}

    monkeypatch.setattr(
        goal_005_completion_check,
        "goal_005_pre_demo_audit_summary",
        fake_pre_demo_audits,
    )
    monkeypatch.setattr(
        goal_005_completion_check,
        "goal_005_next_uat_input",
        fake_next_uat_input,
    )
    monkeypatch.setattr(
        record_goal_005_content_uat_result,
        "load_live_uat_context",
        _live_context_with_private_trace,
    )

    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "werdykt_po_15_minutach": "przejdź do pełnego testu treści",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": FULL_REVIEW_ARTIFACTS,
                "oceny_materialow_review": _scorecard(
                    FULL_REVIEW_ARTIFACTS,
                    decision="zatwierdź",
                    cta_score=5,
                ),
                "oceny_prywatnego_sladu_zrodlowego": _private_trace_scorecard(
                    decision="popraw",
                    trace_clear="nie",
                    requested_fix="Dopisać prostszy opis źródła dla Wilka.",
                ),
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

    report = build_completion_report(
        uat_result=result_path,
        api_base="http://127.0.0.1:8000",
    )

    assert report["status"] == "blocked_missing_goal_005_uat_proof"
    assert report["missing_input"] == "goal_005_private_trace_scorecard_follow_up"
    assert report["uat_private_source_trace_follow_up_suggestions"] == [
        {
            "target": "Bezpieczeństwo prawne, poufność i zgody",
            "scope": "polityka twierdzeń",
            "decision": "popraw",
            "trace_clear": False,
            "requested_fix": "Dopisać prostszy opis źródła dla Wilka.",
            "source_blocks": ["KB_021_BEZPIECZENSTWO_PRAWNE"],
            "eval_cases": ["goal_005_private_claim_policy_review"],
        }
    ]
    assert any("ślad czytelny: nie" in detail for detail in report["details"])
    assert any(
        "bramka: goal_005_private_claim_policy_review" in detail
        for detail in report["details"]
    )
    markdown = render_markdown(report)
    assert "## Follow-up prywatnego śladu źródłowego" in markdown
    assert "Dopisać prostszy opis źródła dla Wilka." in markdown


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
    assert "## Ślad danych do rozmowy" in markdown
    assert "## Bramki przed pokazaniem" in markdown
    assert "wiedza do finalnych treści: 0%" in markdown
    assert "publikacja/finalny draft: zablokowane zgodnie z zasadami" in markdown
    assert "Najnowsze wyniki umiejętności" in markdown
    assert "Następne decyzje w Service Profile" in markdown
    assert "-> Bezpieczeństwo prawne, poufność i zgody" in markdown
    assert "Ślad źródłowy i pakiet dowodów" in markdown
    assert "decyzje: zatwierdź, wróć z poprawkami" in markdown
    pre_demo_section = markdown.split("## Bramki przed pokazaniem")[1].split(
        "## Co odblokowuje"
    )[0]
    assert "service_profile_review_" not in pre_demo_section
    assert "Następny materiał do rozmowy" in markdown
    assert "Komenda do wzoru wyniku rozmowy" in markdown
    assert "Status briefu sprzedażowego: `blocked`" in markdown
    assert "Jakość sygnału briefu" in markdown
    assert (
        "Co blokuje brief sprzedażowy: Brakuje karty usługi; Brakuje karty CTA"
        in markdown
    )
    assert "Dowody przy ograniczeniu briefu: ev_content_service_profile_source_facts" in markdown
    assert "Wiedza gotowa do finalnych treści: nie" in markdown


def test_goal_005_completion_check_accepts_ready_uat_result(tmp_path: Path) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "werdykt_po_15_minutach": "przejdź do pełnego testu treści",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": FULL_REVIEW_ARTIFACTS,
                "oceny_materialow_review": _scorecard(
                    FULL_REVIEW_ARTIFACTS,
                    decision="zatwierdź",
                    cta_score=4,
                ),
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
    assert report["shown_review_artifacts"] == FULL_REVIEW_ARTIFACTS

    markdown = render_markdown(report)
    assert "# Sprawdzenie domknięcia Goal 005" in markdown
    assert "Pokazane materiały review" in markdown


def test_goal_005_completion_check_blocks_ready_uat_without_ready_session_verdict(
    tmp_path: Path,
) -> None:
    result_path = tmp_path / "goal-005-uat-result.json"
    result_path.write_text(
        json.dumps(
            {
                "data_sesji": "2026-07-02",
                "osoba": "Wilku",
                "werdykt_po_15_minutach": "zostań przy review",
                "czas_do_zrozumienia_statusu": "8 minut",
                "punkty_niezrozumienia": "Brak krytycznych punktów niezrozumienia.",
                "wybrany_work_item": (
                    "content_work_item_content_decision_https___www_ekologus_pl"
                ),
                "pokazane_materialy_review": FULL_REVIEW_ARTIFACTS,
                "oceny_materialow_review": _scorecard(
                    FULL_REVIEW_ARTIFACTS,
                    decision="zatwierdź",
                    cta_score=4,
                ),
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
    assert report["missing_input"] == "goal_005_session_verdict_not_ready"
    assert any("zostań przy review" in detail for detail in report["details"])
    assert any(
        "przejdź do pełnego testu treści" in detail for detail in report["details"]
    )
    assert "realny dowód użyteczności dla Wilka" in report["blocked_claims"]


def _scorecard(
    artifacts: list[str],
    *,
    decision: str = "popraw",
    cta_score: int = 3,
) -> list[dict[str, object]]:
    return [
        {
            "material": artifact,
            "decyzja": decision,
            "czytelnosc_1_5": 4,
            "uzytecznosc_1_5": 5,
            "glos_ekologus_1_5": 4,
            "zaufanie_do_blokad_1_5": 4,
            "dopasowanie_cta_1_5": cta_score,
            "najwazniejsza_poprawka": "Doprecyzować język i kolejny krok.",
        }
        for artifact in artifacts
    ]


def _private_trace_scorecard(
    *,
    decision: str = "zatwierdź",
    trace_clear: str = "tak",
    requested_fix: str = "brak",
) -> list[dict[str, object]]:
    return [
        {
            "target": "Bezpieczeństwo prawne, poufność i zgody",
            "scope": "polityka twierdzeń",
            "source_blocks": ["KB_021_BEZPIECZENSTWO_PRAWNE"],
            "eval_cases": ["goal_005_private_claim_policy_review"],
            "trace_czytelny": trace_clear,
            "decyzja": decision,
            "najwazniejsza_poprawka": requested_fix,
        }
    ]


def _live_context_with_private_trace(api_base: str) -> dict[str, object]:
    assert api_base == "http://127.0.0.1:8000"
    return {
        "api_base": api_base,
        "queue": {
            "queue_status": "ready",
            "candidate_count": 1,
            "actionable_candidate_count": 1,
            "candidates": [
                {
                    "work_item_id": (
                        "content_work_item_content_decision_https___www_ekologus_pl"
                    ),
                    "title": "SEO: odśwież lub scal \"ekologus\"",
                    "recommended_mode": "refresh",
                    "final_canonical_url": "https://www.ekologus.pl/",
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
            "review_action_summary": {},
            "private_source_proposal_summary": {"promotion_ready": False},
            "source_fact_coverage": {
                "private_review_queue": [
                    {
                        "target_card_title": "Bezpieczeństwo prawne, poufność i zgody",
                        "scope": "claim_policy",
                        "source_block_refs": ["KB_021_BEZPIECZENSTWO_PRAWNE"],
                        "eval_case_ids": ["goal_005_private_claim_policy_review"],
                        "retention_decision": "pending_owner_decision",
                        "redacted": True,
                        "source_trace_ready": True,
                    }
                ]
            },
            "review_actions": [],
        },
        "sales_brief_traces": {
            "content_work_item_content_decision_https___www_ekologus_pl": {
                "status": "ready",
                "signal_quality_status": "ready",
                "evidence_id_count": 2,
                "source_connector_count": 2,
                "source_fact_count": 2,
                "knowledge_constraint_count": 1,
            }
        },
    }


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
                    "Brak realnej walidacji, czy Wilku rozumie blokady, "
                    "prywatny ślad źródłowy ekologus-ai i źródła."
                ),
                "czego_nie_wolno_twierdzic": [
                    "ukończony Goal 005",
                    "realny dowód użyteczności dla Wilka",
                    "zatwierdzona wiedza do finalnych treści",
                    "gotowość finalnego draftu albo publikacji",
                ],
                "nastepny_przeglad": "po realnej sesji z Wilkiem",
                "nastepny_input_uat": (
                    "Pokazać Wilkowi kartę rozmowy, BDO handoff, Eko-Opieka "
                    "handoff i prywatne pola zarządzania wiedzą do oceny."
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
    assert "ekologus-ai" in report["residual_risk"]
    assert "kartę rozmowy" in report["next_uat_input"]
    assert "zatwierdzona wiedza do finalnych treści" in report["blocked_claims"]
    markdown = render_markdown(report)
    assert "Następny materiał do rozmowy" in markdown
    assert "prywatne pola zarządzania wiedzą do oceny" in markdown


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


def test_goal_005_owner_defer_requires_private_source_residual_risk(
    tmp_path: Path,
) -> None:
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
                "czego_nie_wolno_twierdzic": [
                    "ukończony Goal 005",
                    "realny dowód użyteczności dla Wilka",
                    "zatwierdzona wiedza do finalnych treści",
                    "gotowość finalnego draftu albo publikacji",
                ],
                "nastepny_przeglad": "po sesji",
                "nastepny_input_uat": "Pokazać Wilkowi UAT packet.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = validate_owner_defer(defer_path)

    assert report["valid"] is False
    assert (
        "ryzyko_rezydualne musi nazwać ryzyko prywatnych źródeł, "
        "ekologus-ai albo śladu źródłowego"
    ) in report["errors"]


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
                "ryzyko_rezydualne": (
                    "Brak realnej walidacji prywatnego śladu źródłowego."
                ),
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
        and "zatwierdzona wiedza do finalnych treści" in error
        and "gotowość finalnego draftu albo publikacji" in error
        for error in report["errors"]
    )


def test_owner_defer_example_contains_required_claims_but_needs_owner_input(
    tmp_path: Path,
) -> None:
    example = build_owner_defer_example(api_base=None)

    assert example["odroczenie_goal_005_uat"] is True
    assert example["data"] == "<YYYY-MM-DD>"
    assert "UZUPEŁNIJ" in example["powod"]
    assert "ukończony Goal 005" in example["czego_nie_wolno_twierdzic"]
    assert "zatwierdzona wiedza do finalnych treści" in example[
        "czego_nie_wolno_twierdzic"
    ]
    assert "Uruchomić kartę rozmowy:" in example["nastepny_input_uat"]
    assert "--print-session-card" in example["nastepny_input_uat"]

    defer_path = tmp_path / "owner-defer-example.json"
    defer_path.write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")

    report = validate_owner_defer(defer_path)

    assert report["valid"] is False
    assert "brak pola owner defer: data" in report["errors"]
    assert "brak pola owner defer: powod" in report["errors"]
