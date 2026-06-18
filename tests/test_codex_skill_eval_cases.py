from __future__ import annotations

import json
from pathlib import Path

CASES_PATH = Path("docs/evals/cases/wilq-skill-eval-cases.json")
HARNESS_PATH = Path("scripts/codex_skill_eval.sh")


def test_route_specific_codex_eval_cases_define_surface_markers() -> None:
    cases = {case["skill"]: case for case in json.loads(CASES_PATH.read_text(encoding="utf-8"))}

    expected = {
        "wilq-ads-doctor": {
            "surface_path": "/ads-doctor",
            "terms": {"Ads Doctor", "OAuth", "spend"},
            "action_ids": {"act_configure_google_ads_env"},
        },
        "wilq-ga4-analyst": {
            "surface_path": "/ga4",
            "terms": {"GA4", "active_users"},
            "action_ids": {"act_review_ga4_tracking_quality"},
        },
        "wilq-gsc-content-doctor": {
            "surface_path": "/seo-gsc",
            "terms": {"SEO / GSC", "GSC", "treści"},
            "action_ids": set(),
        },
        "wilq-merchant-feed-operator": {
            "surface_path": "/merchant",
            "terms": {"Merchant Center", "feed", "product"},
            "action_ids": {"act_review_merchant_feed_issues"},
        },
        "wilq-content-strategist": {
            "surface_path": "/content-planner",
            "terms": {"Content Planner", "WordPress", "GSC"},
            "action_ids": {"act_prepare_content_refresh_queue"},
        },
        "wilq-localo-operator": {
            "surface_path": "/localo",
            "terms": {"Localo", "LOCALO_ACCESS_TOKEN", "blocker"},
            "action_ids": set(),
        },
    }

    for skill, contract in expected.items():
        case = cases[skill]
        assert case["surface_path"] == contract["surface_path"]
        expected_terms = set(str(term) for term in case["expected_terms_pl"])
        expected_action_ids = set(
            str(action_id) for action_id in case.get("expected_action_ids", [])
        )
        assert expected_terms.issuperset(contract["terms"])
        assert expected_action_ids.issuperset(contract["action_ids"])
        assert case["expected_connectors"]

    content_case = cases["wilq-content-strategist"]
    assert "wordpress_sklep" in content_case["expected_connectors"]
    assert "wordpress_sklep" not in content_case["required_source_connectors"]
    assert set(content_case["required_source_connectors"]) <= set(
        content_case["expected_connectors"]
    )


def test_codex_skill_eval_harness_validates_route_markers() -> None:
    harness = HARNESS_PATH.read_text(encoding="utf-8")

    for required in (
        "surface_path marker missing",
        "expected route term missing",
        "expected connector missing",
        "expected action_id missing",
        "required_source_connectors",
    ):
        assert required in harness


def test_route_specific_skill_smokes_expose_marketing_brief_items() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    route_skills = [case["skill"] for case in cases if case.get("surface_path")]

    for skill in route_skills:
        skill_root = Path(".agents/skills") / skill
        skill_doc = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        smoke_script = (skill_root / "scripts" / "smoke_skill_contract.py").read_text(
            encoding="utf-8"
        )

        assert "GET /api/marketing/brief" in skill_doc
        assert 'brief = request_json(args.api_base, "GET", "/api/marketing/brief")' in smoke_script
        assert '"brief_items": brief_items' in smoke_script
