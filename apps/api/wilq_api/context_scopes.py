from __future__ import annotations

from wilq.actions.google_ads.demand_gen import DEMAND_GEN_READINESS_REVIEW_ACTION_ID
from wilq.actions.google_ads.keyword_planner import KEYWORD_PLANNER_ACCESS_ACTION_ID
from wilq.actions.google_ads.search_term_ngrams import SEARCH_TERM_NGRAM_ACTION_ID

SKILL_CONNECTOR_SCOPES: dict[str, set[str]] = {
    "wilq-ads-doctor": {"google_ads"},
    "wilq-ahrefs-gap-finder": {"ahrefs", "google_search_console", "wordpress_ekologus"},
    "wilq-campaign-builder": {
        "google_ads",
        "google_analytics_4",
        "google_search_console",
    },
    "wilq-content-strategist": {
        "google_search_console",
        "google_analytics_4",
        "ahrefs",
        "wordpress_ekologus",
        "wordpress_sklep",
    },
    "wilq-custom-segments": {"google_ads", "google_search_console"},
    "wilq-demand-gen-operator": {
        "google_ads",
        "google_analytics_4",
    },
    "wilq-ga4-analyst": {"google_analytics_4", "wordpress_ekologus"},
    "wilq-gsc-content-doctor": {
        "google_search_console",
        "wordpress_ekologus",
        "wordpress_sklep",
    },
    "wilq-localo-operator": {"localo"},
    "wilq-merchant-feed-operator": {"google_merchant_center"},
    "wilq-social-publisher": {
        "facebook",
        "google_analytics_4",
        "google_merchant_center",
        "google_search_console",
        "linkedin",
        "wordpress_ekologus",
    },
}

SKILL_KEYWORD_SCOPES: dict[str, set[str]] = {
    "wilq-ads-doctor": {
        "ads",
        "budget",
        "google_ads",
        "negative",
        "recommendations",
        "scaling",
        "search",
        "pmax",
    },
    "wilq-ahrefs-gap-finder": {"ahrefs", "gap", "content", "seo"},
    "wilq-campaign-builder": {"ads", "campaign", "pmax", "search", "shopping"},
    "wilq-content-strategist": {"content", "seo", "gsc", "wordpress", "ahrefs"},
    "wilq-custom-segments": {"custom", "segment", "audience", "ads"},
    "wilq-demand-gen-operator": {"demand", "creative", "ga4", "ads"},
    "wilq-ga4-analyst": {"ga4", "analytics", "behavior", "landing"},
    "wilq-gsc-content-doctor": {"gsc", "seo", "content", "wordpress"},
    "wilq-localo-operator": {"localo", "local", "gbp"},
    "wilq-merchant-feed-operator": {"merchant", "feed", "shopping", "product"},
    "wilq-social-publisher": {"social", "linkedin", "facebook", "content"},
}

SKILL_KNOWLEDGE_CARD_IDS: dict[str, list[str]] = {
    "wilq-ads-doctor": [
        "card_google_ads_search_playbook",
        "card_google_ads_budget_review_playbook",
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_custom_segments_playbook",
        "card_goal_001_rules",
    ],
}

SKILL_ACTION_ID_SCOPES: dict[str, set[str]] = {
    "wilq-ads-doctor": {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
        SEARCH_TERM_NGRAM_ACTION_ID,
        "act_prepare_custom_segments_from_search_terms",
        "act_prepare_negative_keyword_review_queue",
        KEYWORD_PLANNER_ACCESS_ACTION_ID,
    },
    "wilq-ahrefs-gap-finder": {"act_prepare_content_refresh_queue"},
    "wilq-campaign-builder": {
        "act_prepare_ads_campaign_review_queue",
        "act_prepare_google_ads_recommendation_review_queue",
    },
    "wilq-content-strategist": {"act_prepare_content_refresh_queue"},
    "wilq-custom-segments": {
        "act_prepare_custom_segments_from_search_terms",
    },
    "wilq-demand-gen-operator": {DEMAND_GEN_READINESS_REVIEW_ACTION_ID},
    "wilq-ga4-analyst": {"act_review_ga4_tracking_quality"},
    "wilq-gsc-content-doctor": {"act_prepare_content_refresh_queue"},
    "wilq-localo-operator": {"act_review_localo_visibility_facts"},
    "wilq-social-publisher": {
        "act_prepare_facebook_social_drafts",
        "act_prepare_linkedin_social_drafts",
    },
}

SKILL_EXPERT_RULE_IDS: dict[str, list[str]] = {
    "wilq-ads-doctor": [
        "ads_diagnostics_v1",
        "ads_principles_v1",
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1",
        "ads_search_terms_v1",
        "ads_negative_keywords_v1",
        "ads_custom_segments_v1",
        "ads_keyword_planner_v1",
    ],
    "wilq-content-strategist": [
        "seo_gsc_opportunities_v1",
        "seo_query_page_matrix_v1",
        "seo_content_decay_v1",
        "seo_cannibalization_v1",
        "content_duplication_rules_v1",
        "content_brief_rules_v1",
    ],
}
