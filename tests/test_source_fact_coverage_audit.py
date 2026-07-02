from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "source_fact_coverage_audit.py"
    spec = importlib.util.spec_from_file_location("source_fact_coverage_audit", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_source_fact_coverage_audit_reports_current_goal_005_backlog() -> None:
    audit = load_module()

    report = audit.build_report()

    assert report["pass"] is True
    assert report["knowledge_status"] == "source_backed_review_required"
    assert report["ready_for_daily_content"] is False
    assert report["production_depth_percent"] == 0
    assert report["reviewed_fact_percent"] == 0
    assert report["fact_count"] >= 12
    assert report["private_proposal_count"] >= 5
    assert report["private_review_required_count"] == report["private_proposal_count"]
    assert report["review_action_count"] >= report["private_proposal_count"]
    assert report["private_review_queue"][0]["risk_tier"] == "high"
    assert all(not item["promotion_allowed"] for item in report["private_review_queue"])
    assert report["blockers"]


def test_source_fact_coverage_markdown_is_wilku_readable() -> None:
    audit = load_module()
    report = {
        "workspace_id": "ekologus",
        "knowledge_status": "source_backed_review_required",
        "ready_for_daily_content": False,
        "production_depth_percent": 0,
        "approved_service_percent": 0,
        "reviewed_fact_percent": 0,
        "fact_count": 12,
        "review_action_count": 13,
        "private_review_required_count": 5,
        "safe_next_step": "Pokaż Wilkowi review-required źródła przed treścią.",
        "private_review_queue": [
            {
                "scope": "claim_policy",
                "target_card_title": "Styl marki",
                "risk_tier": "high",
                "safe_next_step": "Sprawdź zasady claimów z reviewerem.",
            }
        ],
        "blockers": ["Brakuje zatwierdzonych production-depth kart usług Ekologus."],
    }

    markdown = audit.render_markdown(report)

    assert "Production-depth service readiness: 0%" in markdown
    assert "Pokaż Wilkowi review-required źródła przed treścią." in markdown
    assert "| 1 | `claim_policy` | Styl marki | `high` |" in markdown
    assert "Brakuje zatwierdzonych production-depth kart usług Ekologus." in markdown
