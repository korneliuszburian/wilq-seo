from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_module():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    module_path = scripts_dir / "audit_skill_reviewer_scorecards.py"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "audit_skill_reviewer_scorecards",
            module_path,
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


def test_reviewer_scorecard_audit_accepts_candidate_for_10(
    tmp_path,
    monkeypatch,
) -> None:
    audit_module = load_module()
    scorecard_dir = tmp_path / "scorecards"
    scorecard_dir.mkdir()
    scorecard_path = scorecard_dir / "ads.json"
    scorecard_path.write_text(
        json.dumps(
            {
                "skill": "wilq-ads-doctor",
                "decision": "candidate_for_10",
                "can_consider_10": "tak",
                "rerun_eval_required": "tak",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit_module, "build_packet", fake_packet)

    report = audit_module.build_report(scorecard_dir, strict=True)
    markdown = audit_module.render_markdown(report)

    assert report["pass"] is True
    assert report["scorecard_count"] == 1
    assert report["candidate_for_10_count"] == 1
    assert report["fulfilled_candidate_count"] == 0
    assert report["open_candidate_count"] == 1
    assert report["rows"][0]["next_step"].startswith("uruchom rerun")
    assert "candidate_for_10" in markdown


def test_reviewer_scorecard_audit_rejects_inconsistent_candidate(
    tmp_path,
    monkeypatch,
) -> None:
    audit_module = load_module()
    scorecard_dir = tmp_path / "scorecards"
    scorecard_dir.mkdir()
    scorecard_path = scorecard_dir / "ads.json"
    scorecard_path.write_text(
        json.dumps(
            {
                "skill": "wilq-ads-doctor",
                "decision": "candidate_for_10",
                "can_consider_10": "nie",
                "rerun_eval_required": "tak",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit_module, "build_packet", fake_packet)

    report = audit_module.build_report(scorecard_dir, strict=True)

    assert report["pass"] is False
    assert report["failure_count"] == 1
    assert "requires can_consider_10=tak" in report["rows"][0]["error"]


def test_reviewer_scorecard_audit_strict_requires_files(tmp_path) -> None:
    audit_module = load_module()

    report = audit_module.build_report(tmp_path / "missing", strict=True)

    assert report["pass"] is False
    assert report["scorecard_count"] == 0


def test_reviewer_scorecard_audit_marks_candidate_fulfilled(
    tmp_path,
    monkeypatch,
) -> None:
    audit_module = load_module()
    scorecard_dir = tmp_path / "scorecards"
    scorecard_dir.mkdir()
    scorecard_path = scorecard_dir / "ads.json"
    scorecard_path.write_text(
        json.dumps(
            {
                "skill": "wilq-ads-doctor",
                "decision": "candidate_for_10",
                "can_consider_10": "tak",
                "rerun_eval_required": "tak",
            }
        ),
        encoding="utf-8",
    )

    def fake_packet_10(*, skill: str, reviewer_scorecard_path: Path):
        packet = fake_packet(skill=skill, reviewer_scorecard_path=reviewer_scorecard_path)
        packet["score"] = 10
        return packet

    monkeypatch.setattr(audit_module, "build_packet", fake_packet_10)

    report = audit_module.build_report(scorecard_dir, strict=True)

    assert report["pass"] is True
    assert report["fulfilled_candidate_count"] == 1
    assert report["open_candidate_count"] == 0
    assert report["rows"][0]["candidate_fulfilled"] is True


def fake_packet(*, skill: str, reviewer_scorecard_path: Path):
    payload = json.loads(reviewer_scorecard_path.read_text(encoding="utf-8"))
    return {
        "skill": skill,
        "score": 9,
        "reviewer_scorecard": {
            "skill": skill,
            "filled": True,
            "reviewer": "test",
            "decision": payload["decision"],
            "can_consider_10": payload["can_consider_10"],
            "rerun_eval_required": payload["rerun_eval_required"],
            "criteria": [
                {"field": "decyzja_w_30_sekund", "question": "q1", "score": 5},
                {"field": "dowody_i_zrodla", "question": "q2", "score": 5},
            ],
            "follow_up_slots": ["rerun eval"],
        },
    }
