from __future__ import annotations

CUSTOM_SEGMENT_PIPELINE = (
    "pull_real_search_terms",
    "cluster_and_clean_terms",
    "reject_low_intent_or_brand_risk_terms",
    "enrich_with_keyword_planner",
    "build_candidate_segment",
    "validate_segment_payload",
    "create_action_object",
    "apply_where_supported",
    "log_evidence_and_action_history",
)
