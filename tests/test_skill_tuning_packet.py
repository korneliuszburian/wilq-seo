from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    module_path = scripts_dir / "skill_tuning_packet.py"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location("skill_tuning_packet", module_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def test_skill_tuning_packet_preserves_full_next_step(tmp_path, monkeypatch) -> None:
    packet_module = load_module()
    result_path = tmp_path / "evals/20260704T010000Z/wilq-ads-doctor/result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "skill": "wilq-ads-doctor",
                "operator_next_step": (
                    "Wejdź w /ads-doctor, zacznij od kampanii i budżetów, "
                    "potem przejdź przez rekomendacje, wyszukiwane hasła, "
                    "wykluczenia i segmenty bez zapisu zmian."
                ),
                "decision_quality": {
                    "notes_pl": "Output jest użyteczny, ale wymaga reviewer pass na ekranie.",
                },
                "evidence_ids": ["ev_connector_google_ads_status"],
                "source_connectors": ["google_ads"],
                "recommendations": [
                    {
                        "label_pl": "Priorytet 1: sprawdź kampanie i budżety.",
                        "confidence": "high",
                        "blocked_reason": None,
                        "evidence_ids": ["ev_connector_google_ads_status"],
                        "source_connectors": ["google_ads"],
                    }
                ],
                "action_candidates": [
                    {
                        "label_pl": "Przygotuj kolejkę przeglądu kampanii",
                        "action_id": "act_prepare_ads_campaign_review_queue",
                        "validation_state": "validated",
                        "blocked_reason": None,
                    }
                ],
                "blocked": False,
                "blocked_reason": None,
                "eval_rubric": {
                    "score_reason_pl": "Bardzo mocny wynik review-only.",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(packet_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        packet_module,
        "build_skill_report",
        lambda: {
            "rows": [
                {
                    "skill": "wilq-ads-doctor",
                    "score": 9,
                    "state": "gotowy do review",
                    "latest_artifact": str(result_path.relative_to(tmp_path)),
                    "remaining_blocker_full": "pełny next step",
                }
            ]
        },
    )

    packet = packet_module.build_packet()
    markdown = packet_module.render_markdown(packet)

    assert packet["skill"] == "wilq-ads-doctor"
    assert packet["score"] == 9
    assert packet["can_claim_10_now"] is False
    assert packet["operator_next_step"].endswith("bez zapisu zmian.")
    assert packet["evidence_count"] == 1
    assert packet["source_connectors"] == ["google_ads"]
    assert packet["actions"][0]["action_id"] == "act_prepare_ads_campaign_review_queue"
    assert packet["reviewer_scorecard"]["skill"] == "wilq-ads-doctor"
    assert packet["reviewer_scorecard"]["decision"] == "popraw|rerun_eval|candidate_for_10"
    assert packet["reviewer_scorecard"]["can_consider_10"] == "nie"
    assert packet["reviewer_scorecard"]["rerun_eval_required"] == "tak"
    assert len(packet["reviewer_scorecard"]["criteria"]) == 5
    assert "Test 30 sekund" in markdown
    assert "Formularz oceny reviewer pass" in markdown
    assert "decyzja_w_30_sekund" in markdown
    assert "czy rerun non-interactive eval jest potrzebny" in markdown
    assert "Czy marketer po pierwszym akapicie wie" in markdown
    assert "bez zapisu zmian." in markdown


def test_skill_tuning_packet_supports_explicit_skill(tmp_path, monkeypatch) -> None:
    packet_module = load_module()
    result_path = tmp_path / "evals/20260704T010000Z/wilq-gsc-content-doctor/result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "skill": "wilq-gsc-content-doctor",
                "operator_next_step": "Otwórz /content-planner i zacznij od mapy decyzji.",
                "decision_quality": {"notes_pl": ""},
                "evidence_ids": [],
                "source_connectors": [],
                "recommendations": [],
                "action_candidates": [],
                "blocked": False,
                "blocked_reason": None,
                "eval_rubric": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(packet_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        packet_module,
        "build_skill_report",
        lambda: {
            "rows": [
                {
                    "skill": "wilq-ads-doctor",
                    "score": 10,
                    "state": "gotowy do review",
                    "latest_artifact": "missing.json",
                },
                {
                    "skill": "wilq-gsc-content-doctor",
                    "score": 9,
                    "state": "gotowy do review",
                    "latest_artifact": str(result_path.relative_to(tmp_path)),
                },
            ]
        },
    )

    packet = packet_module.build_packet(skill="wilq-gsc-content-doctor")

    assert packet["skill"] == "wilq-gsc-content-doctor"
    assert packet["operator_next_step"] == "Otwórz /content-planner i zacznij od mapy decyzji."


def test_skill_tuning_packet_renders_filled_reviewer_scorecard(
    tmp_path,
    monkeypatch,
) -> None:
    packet_module = load_module()
    result_path = _write_eval_result(tmp_path, "wilq-ads-doctor")
    scorecard_path = tmp_path / "reviewer-pass.json"
    scorecard_path.write_text(
        json.dumps(
            {
                "skill": "wilq-ads-doctor",
                "reviewer": "SEO reviewer",
                "decision": "candidate_for_10",
                "can_consider_10": "tak",
                "rerun_eval_required": "tak",
                "criteria": [
                    {
                        "field": "decyzja_w_30_sekund",
                        "question": "Czy decyzja jest jasna?",
                        "score": 5,
                    },
                    {
                        "field": "dowody_i_zrodla",
                        "question": "Czy dowody są wystarczające?",
                        "score": 5,
                    },
                ],
                "follow_up_slots": ["rerun eval po zmianie skilla"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(packet_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        packet_module,
        "build_skill_report",
        lambda: {
            "rows": [
                {
                    "skill": "wilq-ads-doctor",
                    "score": 9,
                    "state": "gotowy do review",
                    "latest_artifact": str(result_path.relative_to(tmp_path)),
                }
            ]
        },
    )

    packet = packet_module.build_packet(reviewer_scorecard_path=scorecard_path)
    markdown = packet_module.render_markdown(packet)

    assert packet["reviewer_scorecard"]["filled"] is True
    assert packet["reviewer_scorecard"]["decision"] == "candidate_for_10"
    assert packet["reviewer_scorecard"]["criteria"][0]["score"] == 5
    assert "Wynik reviewer pass" in markdown
    assert "candidate_for_10" in markdown
    assert "rerun eval po zmianie skilla" in markdown


def test_skill_tuning_packet_rejects_scorecard_for_wrong_skill(
    tmp_path,
    monkeypatch,
) -> None:
    packet_module = load_module()
    result_path = _write_eval_result(tmp_path, "wilq-ads-doctor")
    scorecard_path = tmp_path / "reviewer-pass.json"
    scorecard_path.write_text(
        json.dumps(
            {
                "skill": "wilq-gsc-content-doctor",
                "reviewer": "SEO reviewer",
                "decision": "candidate_for_10",
                "can_consider_10": "tak",
                "rerun_eval_required": "tak",
                "criteria": [
                    {
                        "field": "decyzja_w_30_sekund",
                        "question": "Czy decyzja jest jasna?",
                        "score": 5,
                    }
                ],
                "follow_up_slots": ["rerun eval"],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(packet_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        packet_module,
        "build_skill_report",
        lambda: {
            "rows": [
                {
                    "skill": "wilq-ads-doctor",
                    "score": 9,
                    "state": "gotowy do review",
                    "latest_artifact": str(result_path.relative_to(tmp_path)),
                }
            ]
        },
    )

    try:
        packet_module.build_packet(reviewer_scorecard_path=scorecard_path)
    except RuntimeError as error:
        assert "skill mismatch" in str(error)
    else:
        raise AssertionError("Expected scorecard skill mismatch to fail")


def _write_eval_result(tmp_path: Path, skill: str) -> Path:
    result_path = tmp_path / f"evals/20260704T010000Z/{skill}/result.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(
        json.dumps(
            {
                "skill": skill,
                "operator_next_step": "Otwórz ekran i sprawdź decyzję.",
                "decision_quality": {"notes_pl": "Wymaga reviewer pass."},
                "evidence_ids": ["ev_connector_google_ads_status"],
                "source_connectors": ["google_ads"],
                "recommendations": [],
                "action_candidates": [],
                "blocked": False,
                "blocked_reason": None,
                "eval_rubric": {},
            }
        ),
        encoding="utf-8",
    )
    return result_path
