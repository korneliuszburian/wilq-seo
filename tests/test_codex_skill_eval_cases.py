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
            "terms": {
                "Ads Doctor",
                "google_ads",
                "ads_diagnostics",
                "live_data_available",
                "campaign",
                "search terms",
                "negative_keywords_read_contract",
                "CPA",
                "ROAS",
                "blocked claims",
            },
            "action_ids": {
                "act_prepare_ads_campaign_review_queue",
                "act_prepare_negative_keyword_review_queue",
            },
        },
        "wilq-ga4-analyst": {
            "surface_path": "/ga4",
            "terms": {
                "GA4",
                "active_users",
                "ga4_diagnostics",
                "decision_queue",
                "fix_measurement",
                "review_landing_mapping",
                "review_traffic_quality",
                "landing/source/campaign",
            },
            "action_ids": {"act_review_ga4_tracking_quality"},
        },
        "wilq-gsc-content-doctor": {
            "surface_path": "/seo-gsc",
            "terms": {"SEO / GSC", "GSC", "treści", "content_diagnostics", "query/page"},
            "action_ids": {"act_prepare_content_refresh_queue"},
        },
        "wilq-merchant-feed-operator": {
            "surface_path": "/merchant",
            "terms": {
                "Merchant Center",
                "feed",
                "product",
                "merchant_diagnostics",
                "issue",
                "act_review_merchant_feed_issues",
            },
            "action_ids": {"act_review_merchant_feed_issues"},
        },
        "wilq-content-strategist": {
            "surface_path": "/content-planner",
            "terms": {"Content Planner", "WordPress", "GSC", "content_diagnostics", "inventory"},
            "action_ids": {"act_prepare_content_refresh_queue"},
        },
        "wilq-custom-segments": {
            "surface_path": "/ads-doctor",
            "terms": {
                "Ads Doctor",
                "custom segments",
                "ads_diagnostics",
                "custom_segments_read_contract",
                "source_terms",
                "blocked claims",
                "audience size",
                "ROAS",
            },
            "action_ids": {"act_prepare_custom_segments_from_search_terms"},
        },
        "wilq-localo-operator": {
            "surface_path": "/localo",
            "terms": {
                "Localo",
                "mcp_initialize_status",
                "ranking",
                "GBP",
                "local visibility",
                "blocked claims",
            },
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

    ads_skill_doc = Path(".agents/skills/wilq-ads-doctor/SKILL.md").read_text(
        encoding="utf-8"
    )
    ads_smoke_script = Path(
        ".agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    assert "GET /api/ads/diagnostics" in ads_skill_doc
    assert 'request_json(args.api_base, "GET", "/api/ads/diagnostics")' in ads_smoke_script
    assert '"ads_diagnostics": {' in ads_smoke_script
    assert "blocked_handoff" in ads_skill_doc
    assert "Live Ads diagnostics must not expose OAuth blocked_handoff" in ads_smoke_script
    assert "Blocked Ads diagnostics must expose blocked_handoff" in ads_smoke_script

    custom_segments_skill_doc = Path(
        ".agents/skills/wilq-custom-segments/SKILL.md"
    ).read_text(encoding="utf-8")
    custom_segments_smoke_script = Path(
        ".agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    assert "GET /api/ads/diagnostics" in custom_segments_skill_doc
    assert (
        'request_json(args.api_base, "GET", "/api/ads/diagnostics")'
        in custom_segments_smoke_script
    )
    assert '"ads_diagnostics": {' in custom_segments_smoke_script
    assert "custom_segments_read_contract" in custom_segments_smoke_script
    assert "act_prepare_custom_segments_from_search_terms" in custom_segments_smoke_script

    merchant_skill_doc = Path(
        ".agents/skills/wilq-merchant-feed-operator/SKILL.md"
    ).read_text(encoding="utf-8")
    merchant_smoke_script = Path(
        ".agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    assert "GET /api/merchant/diagnostics" in merchant_skill_doc
    assert (
        'request_json(args.api_base, "GET", "/api/merchant/diagnostics")'
        in merchant_smoke_script
    )
    assert '"merchant_diagnostics": {' in merchant_smoke_script

    ga4_skill_doc = Path(".agents/skills/wilq-ga4-analyst/SKILL.md").read_text(
        encoding="utf-8"
    )
    ga4_smoke_script = Path(
        ".agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    assert "GET /api/ga4/diagnostics" in ga4_skill_doc
    assert 'request_json(args.api_base, "GET", "/api/ga4/diagnostics")' in ga4_smoke_script
    assert '"ga4_diagnostics": {' in ga4_smoke_script
    assert "decision_queue" in ga4_smoke_script
    assert "Live GA4 diagnostics must expose decision_queue" in ga4_smoke_script

    for skill in ("wilq-gsc-content-doctor", "wilq-content-strategist"):
        content_skill_doc = (Path(".agents/skills") / skill / "SKILL.md").read_text(
            encoding="utf-8"
        )
        content_smoke_script = (
            Path(".agents/skills") / skill / "scripts" / "smoke_skill_contract.py"
        ).read_text(encoding="utf-8")
        assert "GET /api/content/diagnostics" in content_skill_doc
        assert (
            'request_json(args.api_base, "GET", "/api/content/diagnostics")'
            in content_smoke_script
        )
        assert '"content_diagnostics": {' in content_smoke_script
