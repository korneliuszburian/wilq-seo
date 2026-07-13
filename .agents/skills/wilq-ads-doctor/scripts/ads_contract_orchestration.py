from __future__ import annotations

from typing import Any

from ads_change_history_assertions import validate_change_history_contract
from ads_change_impact_assertions import validate_change_impact_contract
from ads_custom_segments_assertions import validate_custom_segments_contract
from ads_impression_share_assertions import validate_impression_share_contract
from ads_keyword_match_assertions import validate_keyword_match_context_contract
from ads_keyword_planner_assertions import validate_keyword_planner_contract
from ads_negative_keyword_assertions import validate_negative_keyword_contract
from ads_recommendation_assertions import validate_recommendations_contract
from ads_search_term_ngram_assertions import validate_search_term_ngram_contract
from ads_search_term_review_assertions import validate_search_term_review_contract
from ads_search_term_safety_assertions import validate_search_term_safety_contract


def validate_ads_contracts(
    ads_diagnostics: dict[str, Any],
    pack: dict[str, Any],
) -> dict[str, Any]:
    """Validate Ads subcontracts and return the compact values used by the report."""
    recommendations = validate_recommendations_contract(ads_diagnostics, pack)
    impression_share = validate_impression_share_contract(ads_diagnostics, pack)
    change_history = validate_change_history_contract(ads_diagnostics, pack)
    change_impact = validate_change_impact_contract(ads_diagnostics, pack, change_history)
    search_term_review = validate_search_term_review_contract(ads_diagnostics, pack)
    search_term_safety = validate_search_term_safety_contract(ads_diagnostics, pack)
    keyword_match = validate_keyword_match_context_contract(ads_diagnostics, pack)
    keyword_planner = validate_keyword_planner_contract(ads_diagnostics, pack)
    custom_segments = validate_custom_segments_contract(ads_diagnostics, pack, keyword_planner)
    validate_search_term_ngram_contract(ads_diagnostics)
    negative_keywords = validate_negative_keyword_contract(ads_diagnostics)
    custom_segment_idea_count = sum(
        len(candidate.get("keyword_planner_ideas") or [])
        for candidate in custom_segments.get("candidates") or []
    )
    return {
        "recommendations": recommendations,
        "impression_share": impression_share,
        "change_history": change_history,
        "change_impact": change_impact,
        "search_term_review": search_term_review,
        "search_term_safety": search_term_safety,
        "keyword_match": keyword_match,
        "keyword_planner": keyword_planner,
        "custom_segments": custom_segments,
        "custom_segment_idea_count": custom_segment_idea_count,
        "negative_keywords": negative_keywords,
    }
