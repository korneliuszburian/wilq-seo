from __future__ import annotations

from wilq.schemas import (
    AdsChangeHistoryRow,
    AdsChangeImpactReadinessRow,
    AdsKeywordMatchContextRow,
    AdsNegativeKeywordCandidate,
    AdsNegativeKeywordPayloadPreview,
    AdsSearchTermCampaignReviewRow,
    AdsSearchTermMetricRow,
    AdsSearchTermReviewRow,
    AdsSearchTermSafetyRow,
)


def test_ads_label_fallbacks_do_not_expose_raw_vendor_values() -> None:
    from wilq.briefing.ads_diagnostics import (
        _ads_allowed_metric_labels,
        _ads_campaign_status_label,
        _ads_change_resource_type_label,
        _ads_changed_field_labels,
        _ads_channel_type_label,
        _ads_client_type_label,
        _ads_google_operation_label,
        _ads_keyword_criterion_status_label,
        _ads_keyword_match_type_label,
        _ads_missing_read_contract_labels,
        _ads_recommendation_type_label,
        _ads_resource_change_operation_label,
        _ads_review_gate_labels,
        _custom_segment_rejection_reason_label,
    )

    raw_values = {
        _custom_segment_rejection_reason_label("competitor_term_detected"),
        *_ads_review_gate_labels(["new_ads_gate"]),
        _ads_campaign_status_label("APP_CAMPAIGN"),
        _ads_channel_type_label("DISCOVERY"),
        _ads_google_operation_label("ApplyExperimentalOperation"),
        _ads_recommendation_type_label("PERFORMANCE_GOAL"),
        _ads_change_resource_type_label("CUSTOM_CONVERSION_GOAL"),
        _ads_resource_change_operation_label("SET_PRIMARY"),
        _ads_client_type_label("THIRD_PARTY_TOOL"),
        *_ads_changed_field_labels(["campaign.network_settings.target_search_network"]),
        *_ads_allowed_metric_labels(["current_campaign_cost_micros_30d"]),
        _ads_keyword_match_type_label("EXACTISH"),
        _ads_keyword_criterion_status_label("ELIGIBLE_LIMITED"),
        *_ads_missing_read_contract_labels(["pre_change_performance_window_v2"]),
    }
    joined = " ".join(sorted(raw_values))

    for forbidden in (
        "competitor_term_detected",
        "new_ads_gate",
        "APP_CAMPAIGN",
        "DISCOVERY",
        "ApplyExperimentalOperation",
        "PERFORMANCE_GOAL",
        "CUSTOM_CONVERSION_GOAL",
        "SET_PRIMARY",
        "THIRD_PARTY_TOOL",
        "network_settings",
        "current_campaign_cost_micros_30d",
        "EXACTISH",
        "ELIGIBLE_LIMITED",
        "pre_change_performance_window_v2",
    ):
        assert forbidden not in joined
    assert _ads_campaign_status_label(None) == "status kampanii niepotwierdzony"
    assert _ads_channel_type_label(None) == "typ kampanii niepotwierdzony"
    assert _ads_keyword_criterion_status_label(None) == "status słowa niepotwierdzony"
    assert _ads_change_resource_type_label(None) == "typ zasobu zmiany niepotwierdzony"
    assert _ads_resource_change_operation_label(None) == "operacja zmiany niepotwierdzona"
    assert _ads_client_type_label(None) == "źródło zmiany niepotwierdzone"


def test_ads_entity_display_labels_do_not_expose_raw_ids() -> None:
    raw_campaign_id = "customers/123/campaigns/987654321"
    raw_ad_group_id = "customers/123/adGroups/123456789"
    rows = [
        AdsSearchTermMetricRow(
            search_term="bdo cena",
            campaign_id=raw_campaign_id,
            ad_group_id=raw_ad_group_id,
        ),
        AdsSearchTermSafetyRow(
            search_term="bdo cena",
            campaign_id=raw_campaign_id,
            ad_group_id=raw_ad_group_id,
        ),
        AdsSearchTermReviewRow(
            search_term="bdo cena",
            campaign_id=raw_campaign_id,
            ad_group_id=raw_ad_group_id,
        ),
        AdsKeywordMatchContextRow(
            keyword_text="bdo",
            match_type="EXACT",
            campaign_id=raw_campaign_id,
            ad_group_id=raw_ad_group_id,
        ),
        AdsNegativeKeywordPayloadPreview(
            id="preview",
            search_term="bdo cena",
            negative_keyword_text="bdo cena",
            match_type="EXACT",
            level="ad_group",
            campaign_id=raw_campaign_id,
            ad_group_id=raw_ad_group_id,
            reason="Sprawdzenie wykluczenia.",
        ),
        AdsNegativeKeywordCandidate(
            id="candidate",
            search_term="bdo cena",
            review_reason="Sprawdzenie wykluczenia.",
            campaign_id=raw_campaign_id,
            ad_group_id=raw_ad_group_id,
            next_step="Sprawdź intencję.",
        ),
    ]
    campaign_review = AdsSearchTermCampaignReviewRow(campaign_id=raw_campaign_id)
    change_history = AdsChangeHistoryRow(
        change_resource_id="customers/123/campaigns/987654321",
        change_resource_type_label="kampania",
        campaign_id=raw_campaign_id,
    )
    change_impact = AdsChangeImpactReadinessRow(
        change_event_id="customers/123/changeEvents/111",
        campaign_id=raw_campaign_id,
    )
    labels = [label for row in rows for label in (row.campaign_label, row.ad_group_label)]
    labels.extend(
        [
            campaign_review.campaign_label,
            change_history.change_resource_label,
            change_history.campaign_label,
            change_impact.change_event_label,
            change_impact.campaign_label,
        ]
    )
    assert "kampania do sprawdzenia w szczegółach technicznych" in labels
    assert "grupa reklam do sprawdzenia w szczegółach technicznych" in labels
    assert all(raw_campaign_id not in label for label in labels)
    assert all(raw_ad_group_id not in label for label in labels)
    assert all("987654321" not in label for label in labels)
    assert all("changeEvents" not in label for label in labels)


def test_ads_helper_label_fallbacks_do_not_expose_raw_vendor_values() -> None:
    from wilq.briefing.ads_change_history import (
        _change_resource_type_label,
        _resource_change_operation_label,
    )
    from wilq.briefing.ads_recommendations import (
        _missing_metric_labels,
        _recommendation_type_label,
    )

    joined = " ".join(
        [
            _recommendation_type_label("PERFORMANCE_GOAL"),
            _missing_metric_labels(["recommendation_impact_quality_score_v2"]),
            _change_resource_type_label("CUSTOM_CONVERSION_GOAL"),
            _resource_change_operation_label("SET_PRIMARY"),
        ]
    )

    for forbidden in (
        "PERFORMANCE_GOAL",
        "recommendation_impact_quality_score_v2",
        "CUSTOM_CONVERSION_GOAL",
        "SET_PRIMARY",
        "quality score",
        "custom conversion",
    ):
        assert forbidden not in joined
    assert _change_resource_type_label(None) == "typ zasobu zmiany niepotwierdzony"
    assert _resource_change_operation_label(None) == "operacja zmiany niepotwierdzona"
