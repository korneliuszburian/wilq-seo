from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "render_skill_coverage_audit.py"
    spec = importlib.util.spec_from_file_location("render_skill_coverage_audit", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_result(path: Path, *, skill: str, score: int, blocked: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "skill": skill,
                "language": "pl-PL",
                "api_used": True,
                "source_connectors": ["google_ads"],
                "evidence_ids": ["ev_connector_google_ads_status"],
                "recommendations": [],
                "action_candidates": [
                    {
                        "label_pl": "Sprawdź akcję",
                        "action_id": "act_review_example",
                        "validation_state": "validated",
                    }
                ],
                "blocked": blocked,
                "blocked_reason": "Brak wystarczających danych do rekomendacji."
                if blocked
                else None,
                "operator_next_step": (
                    "Otwórz powierzchnię review i sprawdź akcję, bo "
                    "command_center.primary_next_step wskazało ten priorytet."
                ),
                "operator_usefulness_score": score,
                "eval_rubric": {
                    "hard_gates": {
                        "evidence_requirement_handled": True,
                        "source_connector_requirement_handled": True,
                    }
                },
                "failure_tags": [],
                "decision_quality": {"safe_next_step_present": True},
                "notes": "test",
            }
        ),
        encoding="utf-8",
    )


def test_build_report_flags_truncated_visible_operator_output(
    tmp_path,
    monkeypatch,
) -> None:
    audit = load_module()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "skill": "wilq-truncated",
                    "minimum_operator_usefulness_score": 5,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "CASES_PATH", cases_path)

    eval_root = tmp_path / "evals"
    result_path = eval_root / "20260702T010000Z/wilq-truncated/result.json"
    write_result(result_path, skill="wilq-truncated", score=9, blocked=False)
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["operator_next_step"] = "Otwórz /ads-doctor i przejdź przez kolejkę..."
    result_path.write_text(json.dumps(payload), encoding="utf-8")

    report = audit.build_report(eval_root)
    markdown = audit.render_markdown(report)

    assert report["rows"][0]["truncated_visible_output"] is True
    assert "widoczne pole decyzyjne jest ucięte" in markdown
    assert "pełnym opisem przed oceną 10/10" in markdown


def test_build_report_uses_latest_passing_result(tmp_path, monkeypatch) -> None:
    audit = load_module()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "skill": "wilq-example",
                    "minimum_operator_usefulness_score": 4,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "CASES_PATH", cases_path)

    eval_root = tmp_path / "evals"
    write_result(
        eval_root / "20260702T010000Z/wilq-example/result.json",
        skill="wilq-example",
        score=4,
        blocked=True,
    )
    write_result(
        eval_root / "20260702T020000Z/wilq-example/result.json",
        skill="wilq-example",
        score=5,
        blocked=False,
    )
    write_result(
        eval_root / "20260702T030000Z/wilq-example/result.json",
        skill="wilq-example",
        score=8,
        blocked=False,
    )

    report = audit.build_report(eval_root)

    assert report["pass"] is True
    assert report["passing_skill_count"] == 1
    assert report["minimum_score"] == 8
    assert report["maximum_score"] == 8
    assert report["strong_skill_count"] == 1
    assert report["wilku_ready_skill_count"] == 0
    row = report["rows"][0]
    assert row["skill"] == "wilq-example"
    assert "20260702T030000Z" in row["latest_artifact"]
    assert row["score"] == 8
    assert row["state"] == "gotowy do review"
    assert "ev_connector_google_ads_status" not in row["what_it_proves"]
    assert "1 evidence IDs" in row["what_it_proves"]
    assert "command_center.primary_next_step" not in row["remaining_blocker"]
    assert "priorytet wskazany przez Command Center" in row["remaining_blocker"]
    assert "command_center.primary_next_step" not in row["remaining_blocker_full"]
    assert "priorytet wskazany przez Command Center" in row["remaining_blocker_full"]


def test_render_markdown_marks_missing_passing_eval(tmp_path, monkeypatch) -> None:
    audit = load_module()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "skill": "wilq-missing",
                    "minimum_operator_usefulness_score": 5,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "CASES_PATH", cases_path)

    report = audit.build_report(tmp_path / "evals")
    markdown = audit.render_markdown(report)

    assert report["pass"] is False
    assert report["minimum_score"] is None
    assert report["maximum_score"] is None
    assert report["strong_skill_count"] == 0
    assert report["wilku_ready_skill_count"] == 0
    assert "`wilq-missing`" in markdown
    assert "missing passing eval" in markdown
    assert "Uruchom deterministic smoke" in markdown


def test_render_markdown_uses_operator_labels(tmp_path, monkeypatch) -> None:
    audit = load_module()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "skill": "wilq-example",
                    "minimum_operator_usefulness_score": 5,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "CASES_PATH", cases_path)

    eval_root = tmp_path / "evals"
    write_result(
        eval_root / "20260702T010000Z/wilq-example/result.json",
        skill="wilq-example",
        score=9,
        blocked=False,
    )

    markdown = audit.render_markdown(audit.build_report(eval_root))

    assert "ready / review-only" not in markdown
    assert "blocked correctly / review-only" not in markdown
    assert "command_center.primary_next_step" not in markdown
    assert "gotowy do review" in markdown
    assert "priorytet wskazany przez Command Center" in markdown


def test_build_report_floors_minimum_operator_usefulness_at_five(
    tmp_path,
    monkeypatch,
) -> None:
    audit = load_module()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "skill": "wilq-low-floor",
                    "minimum_operator_usefulness_score": 4,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "CASES_PATH", cases_path)

    eval_root = tmp_path / "evals"
    write_result(
        eval_root / "20260702T010000Z/wilq-low-floor/result.json",
        skill="wilq-low-floor",
        score=4,
        blocked=True,
    )

    report = audit.build_report(eval_root)

    assert report["pass"] is False
    assert report["missing_passing_skills"] == ["wilq-low-floor"]
    assert report["rows"][0]["state"] == "missing passing eval"


def test_build_report_marks_eval_stale_when_skill_changed_after_result(
    tmp_path,
    monkeypatch,
) -> None:
    audit = load_module()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            [
                {
                    "skill": "wilq-stale",
                    "minimum_operator_usefulness_score": 5,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "CASES_PATH", cases_path)

    eval_root = tmp_path / "evals"
    result_path = eval_root / "20260702T010000Z/wilq-stale/result.json"
    write_result(result_path, skill="wilq-stale", score=9, blocked=False)

    skill_path = tmp_path / "skills/wilq-stale/SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("---\nname: wilq-stale\n---\nchanged\n", encoding="utf-8")

    old = 1_700_000_000
    new = old + 60
    os.utime(result_path, (old, old))
    os.utime(skill_path, (new, new))

    report = audit.build_report(eval_root, skill_root=tmp_path / "skills")
    markdown = audit.render_markdown(report)

    assert report["pass"] is False
    assert report["passing_skill_count"] == 1
    assert report["fresh_passing_skill_count"] == 0
    assert report["stale_passing_skills"] == ["wilq-stale"]
    assert report["rows"][0]["state"] == "stale passing eval"
    assert report["rows"][0]["stale"] is True
    assert "passing evals are fresh" in markdown
    assert "rerun smoke and non-interactive Codex eval" in markdown
