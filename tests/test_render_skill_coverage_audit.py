from __future__ import annotations

import importlib.util
import json
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
                "operator_next_step": "Otwórz powierzchnię review i sprawdź akcję.",
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

    report = audit.build_report(eval_root)

    assert report["pass"] is True
    assert report["passing_skill_count"] == 1
    row = report["rows"][0]
    assert row["skill"] == "wilq-example"
    assert "20260702T020000Z" in row["latest_artifact"]
    assert row["score"] == 5
    assert row["state"] == "ready / review-only"
    assert "ev_connector_google_ads_status" not in row["what_it_proves"]
    assert "1 evidence IDs" in row["what_it_proves"]


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
    assert "`wilq-missing`" in markdown
    assert "missing passing eval" in markdown
    assert "Uruchom deterministic smoke" in markdown
