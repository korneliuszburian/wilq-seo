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
                "ads_review_budget_context",
                "budget_pacing_read_contract",
                "card_google_ads_budget_review_playbook",
                "ads_scaling_candidates_v1",
                "ads_recommendations_v1",
                "recommendations_read_contract",
                "ads_review_recommendations",
                "review_priority",
                "review_score",
                "review_reason",
                "review rekomendacji",
                "impression_share_read_contract",
                "ads_review_impression_share",
                "change_history_read_contract",
                "ads_review_change_history",
                "search_term_safety_read_contract",
                "search_term_90d",
                "keyword_match_context_read_contract",
                "keyword_match_context",
                "custom_segments_read_contract",
                "custom segments",
                "keyword_planner_read_contract",
                "keyword_planner_enrichment",
                "forecast_or_audience_size",
                "negative_keyword_payload_preview",
                "recommendation apply",
                "search terms",
                "negative_keywords_read_contract",
                "CPA",
                "ROAS",
                "blocked claims",
            },
            "action_ids": {
                "act_prepare_ads_campaign_review_queue",
                "act_prepare_google_ads_recommendation_review_queue",
                "act_prepare_custom_segments_from_search_terms",
                "act_prepare_negative_keyword_review_queue",
            },
            "validated_action_ids": {
                "act_prepare_ads_campaign_review_queue",
                "act_prepare_google_ads_recommendation_review_queue",
                "act_prepare_custom_segments_from_search_terms",
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
            "validated_action_ids": {"act_review_ga4_tracking_quality"},
        },
        "wilq-gsc-content-doctor": {
            "surface_path": "/seo-gsc",
            "terms": {
                "SEO / GSC",
                "GSC",
                "treści",
                "content_diagnostics",
                "query/page",
                "decision_queue",
                "merge_create_after_inventory_check",
                "inventory_check_before_create",
                "gsc_content_doctor_context",
            },
            "action_ids": {"act_prepare_content_refresh_queue"},
            "validated_action_ids": {"act_prepare_content_refresh_queue"},
            "forbidden_connectors": {"ahrefs"},
        },
        "wilq-ahrefs-gap-finder": {
            "surface_path": "/ahrefs",
            "terms": {
                "Ahrefs",
                "ahrefs_diagnostics",
                "decision_queue",
                "ahrefs_review_authority_context",
                "ahrefs_review_gap_records",
                "missing_read_contracts",
                "ahrefs_content_gap_records",
                "ahrefs_backlink_gap_records",
                "ahrefs_organic_keywords_by_url",
                "ahrefs_competitor_pages",
                "ahrefs_top_pages_by_competitor",
                "domain_rating",
                "ahrefs_rank",
                "top pages",
                "organic keywords",
                "content gap",
                "backlink gap",
                "gap_read_contract",
                "stale",
                "review-only",
                "Zablokowane claims",
            },
            "action_ids": set(),
        },
        "wilq-merchant-feed-operator": {
            "surface_path": "/merchant",
            "terms": {
                "Merchant Center",
                "feed",
                "product",
                "merchant_diagnostics",
                "freshness_assessment",
                "decision_queue",
                "unknowns",
                "product_sample_readiness",
                "sample_product_ids",
                "issue",
                "act_review_merchant_feed_issues",
                "merchant_feed_issue_review_preview_v1",
                "review-only",
            },
            "action_ids": {"act_review_merchant_feed_issues"},
            "validated_action_ids": {"act_review_merchant_feed_issues"},
        },
        "wilq-content-strategist": {
            "surface_path": "/content-planner",
            "terms": {
                "Content Planner",
                "WordPress",
                "google_search_console",
                "content_diagnostics",
                "decision_queue",
                "inventory",
                "inventory_check_before_create",
                "merge_create_after_inventory_check",
                "review_ahrefs_gap_records",
                "bdo co to",
                "zielony ład",
            },
            "action_ids": {"act_prepare_content_refresh_queue"},
            "validated_action_ids": {"act_prepare_content_refresh_queue"},
        },
        "wilq-custom-segments": {
            "surface_path": "/ads-doctor",
            "terms": {
                "Ads Doctor",
                "custom segments",
                "ads_diagnostics",
                "custom_segments_read_contract",
                "audience_forecast_read_contract",
                "custom_segment_payload_preview",
                "forecast_or_audience_size",
                "missing_forecast",
                "review_priority",
                "review_score",
                "review_reason",
                "review segmentu",
                "source_terms",
                "blocked claims",
                "audience size",
                "ROAS",
            },
            "action_ids": {"act_prepare_custom_segments_from_search_terms"},
            "validated_action_ids": {"act_prepare_custom_segments_from_search_terms"},
        },
        "wilq-demand-gen-operator": {
            "surface_path": "/ads-doctor/demand-gen",
            "terms": {
                "Demand Gen",
                "demand_gen_readiness",
                "demand_gen_campaign_rows",
                "demand_gen_ad_group_ad_rows",
                "demand_gen_creative_asset_rows",
                "demand_gen_landing_quality_by_campaign",
                "demand_gen_migration_constraints",
                "demand_gen_readiness_review_action_object",
                "blocked claims",
            },
            "action_ids": {"act_review_demand_gen_readiness"},
            "validated_action_ids": {"act_review_demand_gen_readiness"},
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
            "action_ids": {"act_review_localo_visibility_facts"},
            "validated_action_ids": {"act_review_localo_visibility_facts"},
        },
        "wilq-social-publisher": {
            "surface_path": "/social-publisher",
            "terms": {
                "social_draft_context",
                "publish_allowed",
                "missing_publish_permissions",
                "candidate_inputs",
                "review-only",
                "LinkedIn",
                "Facebook",
                "blocked claims",
            },
            "action_ids": {
                "act_prepare_linkedin_social_drafts",
                "act_prepare_facebook_social_drafts",
            },
            "validated_action_ids": {
                "act_prepare_linkedin_social_drafts",
                "act_prepare_facebook_social_drafts",
            },
        },
    }

    for skill, contract in expected.items():
        case = cases[skill]
        assert case["surface_path"] == contract["surface_path"]
        expected_terms = set(str(term) for term in case["expected_terms_pl"])
        expected_action_ids = set(
            str(action_id) for action_id in case.get("expected_action_ids", [])
        )
        expected_validated_action_ids = set(
            str(action_id) for action_id in case.get("expected_validated_action_ids", [])
        )
        assert expected_terms.issuperset(contract["terms"])
        assert expected_action_ids.issuperset(contract["action_ids"])
        assert expected_validated_action_ids.issuperset(
            contract.get("validated_action_ids", set())
        )
        assert set(case.get("forbidden_connectors", [])).issuperset(
            contract.get("forbidden_connectors", set())
        )
        assert case["expected_connectors"]

    ads_case = cases["wilq-ads-doctor"]
    assert set(ads_case["expected_knowledge_card_ids"]) == {
        "card_google_ads_budget_review_playbook"
    }
    assert set(ads_case["expected_expert_rule_ids"]) == {
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1",
        "ads_principles_v1",
    }

    content_case = cases["wilq-content-strategist"]
    assert "wordpress_sklep" in content_case["expected_connectors"]
    assert "wordpress_sklep" not in content_case["required_source_connectors"]
    assert "freshness" in content_case["expected_terms_pl"]
    assert "stale" in content_case["expected_terms_pl"]
    assert set(content_case["required_source_connectors"]) <= set(
        content_case["expected_connectors"]
    )

    demand_gen_case = cases["wilq-demand-gen-operator"]
    assert demand_gen_case["expected_connectors"] == ["google_ads", "google_analytics_4"]
    assert "act_review_demand_gen_readiness" in demand_gen_case["expected_action_ids"]
    assert "act_review_demand_gen_readiness" in demand_gen_case[
        "expected_validated_action_ids"
    ]
    assert "google_merchant_center" not in demand_gen_case["expected_connectors"]
    assert demand_gen_case["expected_blocked"] is True
    assert "Demand Gen launch recommendation" in demand_gen_case["blocked_claim_terms"]
    assert "Demand Gen migration ready" in demand_gen_case["blocked_claim_terms"]
    assert "performance uplift" in demand_gen_case["blocked_claim_terms"]
    custom_segments_case = cases["wilq-custom-segments"]
    assert "audience size" in custom_segments_case["blocked_claim_terms"]
    assert "targeting applied" in custom_segments_case["blocked_claim_terms"]
    daily_case = cases["wilq-daily-command"]
    assert "localo" in daily_case["expected_connectors"]
    assert "localo" not in daily_case["required_source_connectors"]
    assert set(daily_case["required_source_connectors"]) <= set(
        daily_case["expected_connectors"]
    )
    assert set(daily_case["expected_validated_action_ids"]) == {
        "act_review_merchant_feed_issues",
        "act_prepare_content_refresh_queue",
        "act_review_ga4_tracking_quality",
    }
    ahrefs_case = cases["wilq-ahrefs-gap-finder"]
    assert ahrefs_case["expected_blocked"] is False
    assert ahrefs_case["expected_no_action_ids"] is True
    assert "content gap" not in ahrefs_case["blocked_claim_terms"]
    assert "backlink gap" not in ahrefs_case["blocked_claim_terms"]
    assert "ranking opportunity" not in ahrefs_case["blocked_claim_terms"]
    assert "traffic uplift" in ahrefs_case["blocked_claim_terms"]
    assert "competitor gap" not in ahrefs_case["blocked_claim_terms"]
    assert "act_prepare_content_refresh_queue" in ahrefs_case["forbidden_action_ids"]


def test_codex_skill_eval_harness_validates_route_markers() -> None:
    harness = HARNESS_PATH.read_text(encoding="utf-8")

    for required in (
        "surface_path marker missing",
        "expected route term missing",
        "expected connector missing",
        "expected action_id missing",
        "expected knowledge_card_id missing",
        "expected expert_rule_id missing",
        "required_source_connectors",
        "blocked must be",
        "expected no action_ids",
        "forbidden action_id present",
        "expected validated action_id",
        "blocked claim terms must stay out of recommendations",
        "uses blocked claim term without blocked_reason",
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
    ads_validation_call = (
        'request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert ads_validation_call in ads_smoke_script
    assert '"action_validations": action_validations' in ads_smoke_script

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
    assert '"action_validations": action_validations' in custom_segments_smoke_script

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
    assert "freshness_assessment" in merchant_smoke_script
    assert "decision_queue" in merchant_smoke_script
    assert "unknowns" in merchant_smoke_script
    assert "sample_product_ids" in merchant_smoke_script
    assert "Merchant diagnostics with samples must expose sample product IDs" in (
        merchant_smoke_script
    )
    assert "context_pack_action_status" in merchant_smoke_script
    assert "context_pack_validation_status" in merchant_smoke_script
    merchant_validation_call = (
        'request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert merchant_validation_call in merchant_smoke_script
    assert '"action_validations": action_validations' in merchant_smoke_script

    ga4_skill_doc = Path(".agents/skills/wilq-ga4-analyst/SKILL.md").read_text(
        encoding="utf-8"
    )
    ga4_smoke_script = Path(
        ".agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    assert "GET /api/ga4/diagnostics" in ga4_skill_doc
    assert 'request_json(args.api_base, "GET", "/api/ga4/diagnostics")' in ga4_smoke_script
    assert '"ga4_diagnostics": {' in ga4_smoke_script
    ga4_validation_call = (
        'request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert ga4_validation_call in ga4_smoke_script
    assert '"action_validations": action_validations' in ga4_smoke_script
    assert "decision_queue" in ga4_smoke_script
    assert "Live GA4 diagnostics must expose decision_queue" in ga4_smoke_script
    assert '"decision_samples": _decision_samples(decision_queue)' in ga4_smoke_script
    assert "metric_facts" in ga4_smoke_script
    assert "active_users" in ga4_smoke_script

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
        if skill in {"wilq-gsc-content-doctor", "wilq-content-strategist"}:
            content_validation_call = (
                'request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")'
            )
            assert content_validation_call in content_smoke_script
            assert '"action_validations": action_validations' in content_smoke_script

    ahrefs_skill_doc = Path(".agents/skills/wilq-ahrefs-gap-finder/SKILL.md").read_text(
        encoding="utf-8"
    )
    ahrefs_smoke_script = Path(
        ".agents/skills/wilq-ahrefs-gap-finder/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    assert "GET /api/ahrefs/diagnostics" in ahrefs_skill_doc
    assert (
        'request_json(args.api_base, "POST", "/api/codex/context-pack"'
        in ahrefs_smoke_script
    )
    assert "ahrefs_diagnostics" in ahrefs_smoke_script
    assert "ahrefs_review_gap_records" in ahrefs_smoke_script
    assert "Context pack ahrefs_diagnostics must be an object" in ahrefs_smoke_script

    demand_gen_smoke_script = Path(
        ".agents/skills/wilq-demand-gen-operator/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    demand_gen_validation_call = (
        'request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert demand_gen_validation_call in demand_gen_smoke_script
    assert '"action_validations": action_validations' in demand_gen_smoke_script

    localo_smoke_script = Path(
        ".agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    localo_validation_call = (
        'request_json(args.api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert localo_validation_call in localo_smoke_script
    assert '"action_validations": action_validations' in localo_smoke_script

    daily_smoke_script = Path(
        ".agents/skills/wilq-daily-command/scripts/smoke_context_pack.py"
    ).read_text(encoding="utf-8")
    daily_validation_call = (
        'request_json(api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert daily_validation_call in daily_smoke_script
    assert '"action_validations": action_validations' in daily_smoke_script

    cases_by_skill = {case["skill"]: case for case in cases}
    social_case = cases_by_skill["wilq-social-publisher"]
    assert social_case["expected_blocked"] is False
    assert set(social_case["expected_validated_action_ids"]) == {
        "act_prepare_linkedin_social_drafts",
        "act_prepare_facebook_social_drafts",
    }
    assert "post published" in social_case["blocked_claim_terms"]
    assert "social performance uplift" in social_case["blocked_claim_terms"]
    social_smoke_script = Path(
        ".agents/skills/wilq-social-publisher/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    social_validation_call = (
        'request_json(api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert social_validation_call in social_smoke_script
    assert '"action_validations": action_validations' in social_smoke_script

    campaign_case = cases_by_skill["wilq-campaign-builder"]
    assert set(campaign_case["expected_validated_action_ids"]) == {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
    }
    assert "content_landing_context" in campaign_case["expected_terms_pl"]
    assert "query_page_candidates" in campaign_case["expected_terms_pl"]
    assert "campaign performance" in campaign_case["blocked_claim_terms"]
    campaign_smoke_script = Path(
        ".agents/skills/wilq-campaign-builder/scripts/smoke_skill_contract.py"
    ).read_text(encoding="utf-8")
    campaign_validation_call = (
        'request_json(api_base, "POST", f"/api/actions/{quoted_action}/validate")'
    )
    assert campaign_validation_call in campaign_smoke_script
    assert '"action_validations": action_validations' in campaign_smoke_script
    assert '"content_landing_context": {' in campaign_smoke_script
    assert '"query_page_candidates": landing_candidates[:4]' in campaign_smoke_script
