from __future__ import annotations

from wilq.security.redaction import redact_mapping


def test_redaction_hides_token_like_values() -> None:
    redacted = redact_mapping(
        {
            "summary": "failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
            "error": "failure with sk-testsecretvalue1234567890",  # pragma: allowlist secret
            "api_key": "sk-testsecretvalue1234567890",  # pragma: allowlist secret
            "safe_env_name": "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID",
        }
    )

    assert redacted["summary"] == "[REDACTED]"
    assert redacted["error"] == "[REDACTED]"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["safe_env_name"] == "GOOGLE_MERCHANT_CENTER_ACCOUNT_ID"


def test_redaction_checks_nested_wordpress_binding_identifier_shapes() -> None:
    secret_like_handoff_id = "sk-" + "x" * 40  # pragma: allowlist secret

    redacted = redact_mapping(
        {
            "details": {
                "wordpress_draft_binding": {
                    "work_item_id": "content_work_item_bdo",
                    "handoff_id": secret_like_handoff_id,
                    "revision_id": "content_revision_bdo_1",
                    "content_digest": "0" * 64,
                    "draft_package_id": "draft_package_content_work_item_bdo",
                    "draft_package_digest": "1" * 64,
                    "approval_decision_id": "content_revision_decision_bdo_1",
                    "final_canonical_url": "https://ekologus.pl/bdo/",
                }
            }
        }
    )

    binding = redacted["details"]["wordpress_draft_binding"]
    assert binding["handoff_id"] == "[REDACTED]"
    assert binding["work_item_id"] == "content_work_item_bdo"
    assert binding["revision_id"] == "content_revision_bdo_1"
    assert binding["content_digest"] == "0" * 64
    assert binding["draft_package_id"] == "draft_package_content_work_item_bdo"
    assert binding["draft_package_digest"] == "1" * 64
    assert binding["approval_decision_id"] == "content_revision_decision_bdo_1"
    assert binding["final_canonical_url"] == "https://ekologus.pl/bdo/"


def test_redaction_preserves_operator_contract_metadata() -> None:
    redacted = redact_mapping(
        {
            "decision_type": "merge_create_after_inventory_check",
            "credential_source": "repo_env",
            "created_by": "system_ads_target_confirmation_seed",
            "knowledge_card_ids": ["card_google_ads_budget_review_playbook"],
            "expert_rule_ids": ["ads_scaling_candidates_v1"],
            "business_policy_ids": ["use_margin_as_context_not_profitability_verdict"],
            "operator_review_gates": ["google_ads_rmf_compliance_review"],
            "human_review_gates": ["review_search_terms_before_budget_decision"],
            "review_gate": {
                "required_checks": [
                    "google_ads_rmf_compliance_review",
                    "reject_brand_or_low_intent_terms",
                ],
                "operator_checklist": ["check_existing_keywords_and_match_types"],
                "apply_blockers": [
                    "payload_apply_allowed_false",
                    "blocked_claim:zapis rekomendacji",
                ],
            },
            "operations": ["custom_segment_candidate"],
            "supported_actions": ["custom_segment_candidate"],
            "required_validation": ["google_ads_rmf_compliance_review"],
            "preview_contract": "custom_segment_change_preview_v1",
            "custom_segment_preview_id": "preview_ads_custom_segment_23848569273",
            "operation_type": "custom_segment_targeting_review",
            "recommended_actions": ["prepare_custom_segment_review"],
        }
    )

    assert redacted["decision_type"] == "merge_create_after_inventory_check"
    assert redacted["credential_source"] == "repo_env"
    assert redacted["created_by"] == "system_ads_target_confirmation_seed"
    assert redacted["knowledge_card_ids"] == ["card_google_ads_budget_review_playbook"]
    assert redacted["expert_rule_ids"] == ["ads_scaling_candidates_v1"]
    assert redacted["business_policy_ids"] == ["use_margin_as_context_not_profitability_verdict"]
    assert redacted["operator_review_gates"] == ["google_ads_rmf_compliance_review"]
    assert redacted["human_review_gates"] == ["review_search_terms_before_budget_decision"]
    assert redacted["review_gate"]["required_checks"] == [
        "google_ads_rmf_compliance_review",
        "reject_brand_or_low_intent_terms",
    ]
    assert redacted["review_gate"]["operator_checklist"] == [
        "check_existing_keywords_and_match_types"
    ]
    assert redacted["review_gate"]["apply_blockers"] == [
        "payload_apply_allowed_false",
        "blocked_claim:zapis rekomendacji",
    ]
    assert redacted["operations"] == ["custom_segment_candidate"]
    assert redacted["supported_actions"] == ["custom_segment_candidate"]
    assert redacted["required_validation"] == ["google_ads_rmf_compliance_review"]
    assert redacted["preview_contract"] == "custom_segment_change_preview_v1"
    assert redacted["custom_segment_preview_id"] == "preview_ads_custom_segment_23848569273"
    assert redacted["operation_type"] == "custom_segment_targeting_review"
    assert redacted["recommended_actions"] == ["prepare_custom_segment_review"]


def test_redaction_preserves_safe_marketing_context_values() -> None:
    redacted = redact_mapping(
        {
            "source_metric_names": ["search_term_clicks"],
            "available_read_contracts": ["ga4_landing_source_campaign_quality"],
            "missing_read_contracts": [
                "demand_gen_landing_quality_by_campaign",
                "demand_gen_campaign_mode_review",
            ],
            "omitted_contracts": [
                "keyword_match_context_read_contract",
                "search_term_safety_read_contract",
            ],
            "blocked_claims": ["rekomendacja uruchomienia Demand Gen"],
            "cluster_id": "merchant_issue_pl_not_impacted_missing_potentially_required_attribute",
            "issue_type": "missing_potentially_required_attribute",
            "affected_attribute": "n:unit_pricing_measure",
            "country": "PL",
            "reporting_context": "SHOPPING_ADS",
            "severity": "NOT_IMPACTED",
            "resolution": "MERCHANT_ACTION",
            "normalized_page_path": "/europejski-zielony-lad-co-to-takiego",
            "wordpress_content_url": (
                "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
            ),
            "allowed_evidence": ["ahrefs_organic_keyword_gap_count"],
            "gap_type": "organic_keyword_gap",
            "source_url": "https://example.pl/poradnik/",
            "referenced_public_url": (
                "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
            ),
            "source_site_host": "www.ekologus.pl",
            "competitor_domain": "example.pl",
            "keyword": "zielony ład obowiązki",
            "gsc_overlap_terms": ["zielony ład"],
            "wordpress_overlap_urls": [
                "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
            ],
        }
    )

    assert redacted["source_metric_names"] == ["search_term_clicks"]
    assert redacted["available_read_contracts"] == ["ga4_landing_source_campaign_quality"]
    assert redacted["missing_read_contracts"] == [
        "demand_gen_landing_quality_by_campaign",
        "demand_gen_campaign_mode_review",
    ]
    assert redacted["omitted_contracts"] == [
        "keyword_match_context_read_contract",
        "search_term_safety_read_contract",
    ]
    assert redacted["blocked_claims"] == ["rekomendacja uruchomienia Demand Gen"]
    assert redacted["cluster_id"] == (
        "merchant_issue_pl_not_impacted_missing_potentially_required_attribute"
    )
    assert redacted["wordpress_content_url"] == (
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    )
    assert redacted["competitor_domain"] == "example.pl"
    assert redacted["keyword"] == "zielony ład obowiązki"
    assert redacted["gsc_overlap_terms"] == ["zielony ład"]
    assert redacted["wordpress_overlap_urls"] == [
        "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
    ]
