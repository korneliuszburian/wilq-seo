import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, createWilqQueryClient, createWilqRouter } from "./App";

const connectors = [
  {
    id: "google_ads",
    label: "Google Ads",
    status: "missing_credentials",
    configured: false,
    missing_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    available_credential_sources: [],
    freshness: { state: "missing" },
    supported_actions: []
  }
];

const opportunities = [
  {
    id: "opp_decision_review_ads_campaign_metrics",
    type: "google_ads_review_queue",
    title: "Przejrzyj kolejki Ads do oceny bez apply",
    domain: "google_ads",
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metric_tiles: {
      kampanie: 18,
      zapytania: 50,
      "podgląd budżetu": 18,
      rekomendacje: 4
    },
    metrics: [],
    human_diagnosis:
      "Google Ads ma liczniki do oceny i ActionObjecty review-only. Apply pozostaje zablokowany.",
    recommended_action:
      "Otwórz /ads-doctor i przejrzyj kolejno: podgląd budżetów, podgląd rekomendacji, przegląd wykluczeń i podgląd segmentów.",
    risk: "medium",
    action_ids: [
      "act_prepare_ads_campaign_review_queue",
      "act_prepare_google_ads_recommendation_review_queue"
    ],
    expert_rule_ids: [],
    playbook_ids: ["wilq-ads-doctor"],
    is_fixture: false
  }
];

const actions = [
  {
    id: "act_1",
    title: "Odnow Google Ads OAuth refresh token",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "low",
    status: "needs_validation",
    evidence_ids: ["ev_1"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis: "Google Ads refresh token returns oauth_error=invalid_grant.",
    recommended_reason: "OAuth repair unlocks reads.",
    payload: { action_type: "repair_google_ads_oauth" },
    audit_events: []
  },
  {
    id: "act_review_merchant_feed_issues",
    title: "Przygotuj kolejkę przeglądu feedu Merchant Center",
    domain: "merchant",
    connector: "google_merchant_center",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_merchant_feed"],
    metrics: [
      {
        name: "merchant_disapproved_product_count",
        value: 3,
        period: "connector_refresh",
        source_connector: "google_merchant_center",
        evidence_id: "ev_refresh_merchant_feed",
        unit: null
      }
    ],
    validation_status: "not_validated",
    human_diagnosis: "Merchant Center ma realne metryki produktu/feedu w WILQ API.",
    recommended_reason: "Przygotuj kolejkę problemów feedu z payload preview.",
    payload: {
      action_type: "merchant_feed_issue",
      connector: "google_merchant_center",
      mode: "prepare_only",
      destructive: false
    },
    audit_events: []
  },
  {
    id: "act_review_ga4_tracking_quality",
    title: "Sprawdź jakość pomiaru GA4 przed oceną kampanii",
    domain: "ga4",
    connector: "google_analytics_4",
    mode: "prepare",
    risk: "low",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_ga4"],
    metrics: [
      {
        name: "active_users",
        value: 20,
        period: "connector_refresh",
        source_connector: "google_analytics_4",
        evidence_id: "ev_refresh_ga4",
        unit: null
      }
    ],
    validation_status: "not_validated",
    human_diagnosis: "GA4 zwraca realne metryki ruchu, ale bez dowodu konwersji.",
    recommended_reason: "Przygotuj tracking-gap review.",
    payload: {
      action_type: "ga4_tracking_gap",
      connector: "google_analytics_4",
      mode: "prepare_only",
      destructive: false
    },
    audit_events: []
  },
  {
    id: "act_prepare_content_refresh_queue",
    title: "Przygotuj kolejkę odświeżenia treści ekologus.pl",
    domain: "content",
    connector: "wordpress_ekologus",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_wordpress_inventory", "ev_refresh_gsc"],
    metrics: [
      {
        name: "content_object_count",
        value: 16,
        period: "connector_refresh",
        source_connector: "wordpress_ekologus",
        evidence_id: "ev_refresh_wordpress_inventory",
        unit: null
      },
      {
        name: "clicks",
        value: 12,
        period: "connector_refresh",
        source_connector: "google_search_console",
        evidence_id: "ev_refresh_gsc",
        unit: null
      }
    ],
    validation_status: "not_validated",
    human_diagnosis: "WordPress inventory można zestawić z GSC przed tworzeniem nowych tematów.",
    recommended_reason: "Przygotuj queue refresh/create/merge/block.",
    payload: {
      action_type: "wordpress_content_refresh",
      connector: "wordpress_ekologus",
      mode: "prepare_only",
      destructive: false
    },
    audit_events: []
  },
  {
    id: "act_prepare_negative_keyword_review_queue",
    title: "Przygotuj kolejkę review wykluczeń z search terms",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis:
      "Google Ads ma search-term metric facts do review, ale apply wymaga 90-day safety check.",
    recommended_reason: "Przygotuj review-only queue bez claimów o waste.",
    payload: {
      action_type: "negative_keyword_candidate",
      connector: "google_ads",
      mode: "prepare_only",
      terms: ["odpady cena"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      preview_contract: "negative_keyword_payload_preview_v1",
      api_mutation_ready: false,
      payload_preview: [
        {
          id: "negative_keyword_preview_123_789_odpady_cena",
          search_term: "odpady cena",
          negative_keyword_text: "odpady cena",
          match_type: "EXACT",
          level: "ad_group",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "789",
          ad_group_name: "Odpady",
          reason: "Exact negative keyword review preview zbudowany z evidence.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: ["search_term_clicks", "search_term_90d_clicks"],
          required_validation: [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "human_confirm_before_apply"
          ],
          blocked_claims: ["negative keyword apply", "search-term waste"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      required_validation: [
        "90_day_safety_check",
        "negative_keyword_payload_preview"
      ],
      apply_allowed: false,
      destructive: false
    },
    audit_events: []
  },
  {
    id: "act_prepare_google_ads_recommendation_review_queue",
    title: "Przygotuj review rekomendacji Google Ads",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis:
      "Google Ads ma aktywne recommendation facts, ale apply wymaga review strategii.",
    recommended_reason: "Przejrzyj typ rekomendacji i impact preview bez apply.",
    payload: {
      action_type: "google_ads_recommendation_review",
      connector: "google_ads",
      mode: "prepare_only",
      recommendations: [
        {
          id: "rec-1",
          recommendation_id: "rec-1",
          recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
          recommendation_type: "CAMPAIGN_BUDGET",
          campaign_id: "123",
          campaign_budget_id: "777",
          source_metric_names: ["recommendation_available"],
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          blocked_claims: ["recommendation apply"],
          required_validation: [
            "review_recommendation_type",
            "review_impact_metrics",
            "review_change_history",
            "review_business_goal",
            "recommendation_apply_preview",
            "google_ads_rmf_compliance_review",
            "human_confirm_before_apply"
          ]
        }
      ],
      preview_contract: "recommendation_apply_preview_v1",
      payload_preview: [
        {
          id: "recommendation_apply_preview_rec-1",
          recommendation_id: "rec-1",
          recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
          recommendation_type: "CAMPAIGN_BUDGET",
          campaign_id: "123",
          campaign_budget_id: "777",
          operation_type: "ApplyRecommendationOperation",
          reason: "Review-only recommendation apply operation preview.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: ["recommendation_available"],
          required_validation: [
            "review_recommendation_type",
            "review_impact_metrics",
            "review_change_history",
            "review_business_goal",
            "recommendation_apply_preview",
            "google_ads_rmf_compliance_review",
            "human_confirm_before_apply"
          ],
          blocked_claims: [
            "recommendation apply",
            "automatic recommendation accept",
            "budget apply",
            "campaign mutation",
            "performance uplift"
          ],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      source_metric_names: ["recommendation_available"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      required_validation: [
        "review_recommendation_type",
        "review_impact_metrics",
        "review_change_history",
        "review_business_goal",
        "recommendation_apply_preview",
        "google_ads_rmf_compliance_review",
        "human_confirm_before_apply"
      ],
      blocked_claims: [
        "recommendation apply",
        "automatic recommendation accept",
        "budget apply",
        "campaign mutation",
        "performance uplift"
      ],
      api_mutation_ready: false,
      apply_allowed: false,
      destructive: false
    },
    audit_events: []
  }
];

const evidence = [
  {
    id: "ev_connector_google_ads_status",
    source_connector: "google_ads",
    source_type: "connector_status",
    source_id: "google_ads",
    collected_at: "2026-06-17T10:00:00Z",
    freshness: { state: "missing" },
    summary: "Connector google_ads is missing credential names.",
    raw_ref: null
  },
  {
    id: "ev_refresh_merchant_feed",
    source_connector: "google_merchant_center",
    source_type: "connector_refresh",
    source_id: "refresh_merchant_feed",
    collected_at: "2026-06-17T10:00:00Z",
    freshness: { state: "fresh" },
    summary: "Merchant Center feed diagnostics collected sanitized product issue counters.",
    raw_ref: null
  }
];

const connectorRefreshRuns = [
  {
    id: "refresh_google_ads_test",
    connector_id: "google_ads",
    mode: "status_probe",
    status: "completed",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: "2026-06-17T10:00:01Z",
    evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
    missing_credentials: [],
    checked_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    external_call_attempted: false,
    vendor_data_collected: false,
    metric_summary: {},
    summary: "Connector google_ads status probe completed.",
    errors: [],
    redacted: true
  }
];

const adsDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  connector: {
    ...connectors[0],
    status: "configured",
    configured: true,
    missing_credentials: [],
    available_credential_sources: ["repo_env"],
    freshness: { state: "fresh" }
  },
  latest_refresh: {
    ...connectorRefreshRuns[0],
    mode: "vendor_read",
    status: "completed",
    external_call_attempted: true,
    vendor_data_collected: true,
    summary: "Google Ads vendor read completed through googleAds:searchStream. Rows: 18.",
    errors: [],
    metric_summary: {
      row_count: 18,
      clicks: 107,
      impressions: 2783,
      cost_micros: 164591174,
      conversions: 2.5,
      conversion_value: 450.75
    }
  },
  live_data_available: true,
  campaign_read_contract: {
    id: "ads_campaign_activity_read_contract",
    status: "ready",
    title: "Google Ads: aktywność kampanii",
    summary:
      "WILQ ma 1 wierszy kampanii: kliknięcia=107, wyświetlenia=2783, koszt_micros=164591174, konwersje=2.5, wartość_konwersji=450.75.",
    allowed_metrics: ["clicks", "impressions", "cost_micros", "conversions", "conversion_value"],
    missing_read_contracts: [],
    blocked_claims: ["CPA", "ROAS", "search-term waste", "wasted budget"],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    campaign_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        clicks: 107,
        impressions: 2783,
        cost_micros: 164591174,
        conversions: 2.5,
        conversion_value: 450.75,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [
          {
            name: "clicks",
            value: 107,
            period: "connector_refresh",
            source_connector: "google_ads",
            evidence_id: "ev_refresh_refresh_google_ads_test",
            dimensions: { campaign_id: "123", campaign_name: "Ekologus Search" },
            unit: null
          },
          {
            name: "conversions",
            value: 2.5,
            period: "connector_refresh",
            source_connector: "google_ads",
            evidence_id: "ev_refresh_refresh_google_ads_test",
            dimensions: { campaign_id: "123", campaign_name: "Ekologus Search" },
            unit: null
          }
        ],
        missing_metrics: [],
        blocked_claims: ["CPA", "ROAS", "search-term waste", "wasted budget"]
      }
    ],
    next_step: "Użyj wierszy kampanii do przeglądu aktywności."
  },
  account_currency_read_contract: {
    id: "ads_account_currency_read_contract",
    status: "ready",
    title: "Google Ads: waluta konta",
    summary: "WILQ ma walutę konta Google Ads z evidence: PLN.",
    currency_code: "PLN",
    allowed_metrics: ["account_currency_code"],
    missing_read_contracts: [],
    blocked_claims: ["profitability", "margin verdict", "budget apply"],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    next_step:
      "Pokazuj koszt, CPC i CPA w walucie konta. Nadal nie oceniaj rentowności bez marży, celu biznesowego i walidowanego preview."
  },
  derived_kpi_read_contract: {
    id: "ads_derived_kpi_read_contract",
    status: "ready",
    title: "Google Ads: wyliczone KPI kampanii",
    summary:
      "WILQ może policzyć KPI dla 1 kampanii: CPA dostępne dla 1, ROAS dostępny dla 1. To są obliczenia z bieżących metric facts, nie werdykt opłacalności.",
    allowed_metrics: [
      "ctr",
      "average_cpc_micros",
      "conversion_rate",
      "cost_per_conversion_micros",
      "roas",
      "value_per_conversion"
    ],
    missing_read_contracts: ["profit_margin", "change_history"],
    blocked_claims: [
      "profitability",
      "budget scaling",
      "wasted budget",
      "recommendation apply",
      "incrementality"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    kpi_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        ctr: 0.038448,
        average_cpc_micros: 1538235.271028,
        conversion_rate: 0.023364,
        cost_per_conversion_micros: 65836469.6,
        roas: 2.738589,
        value_per_conversion: 180.3,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        source_metric_names: [
          "clicks",
          "impressions",
          "cost_micros",
          "conversions",
          "conversion_value"
        ],
        missing_metrics: [],
        blocked_claims: [
          "profitability",
          "budget scaling",
          "wasted budget",
          "recommendation apply"
        ]
      }
    ],
    next_step:
      "Użyj KPI do triage kampanii. Przed decyzją budżetową sprawdź walutę konta, marżę, pacing budżetu, historię zmian i rekomendacje."
  },
  budget_pacing_read_contract: {
    id: "ads_budget_pacing_read_contract",
    status: "ready",
    title: "Google Ads: kontekst budżetu kampanii",
    summary:
      "WILQ ma budżetowy kontekst dla 1 kampanii; 1 ma policzalny stosunek kosztu z 7 dni do budżetu dziennego.",
    allowed_metrics: [
      "budget_amount_micros",
      "cost_micros_7d",
      "seven_day_budget_micros",
      "spend_to_budget_ratio_7d",
      "budget_has_recommended_budget",
      "budget_recommended_amount_micros"
    ],
    missing_read_contracts: [
      "shared_budget_distribution",
      "budget_target_or_seasonality",
      "change_history",
      "human_budget_goal"
    ],
    blocked_claims: [
      "budget scaling",
      "budget apply",
      "profitability",
      "wasted budget",
      "recommendation apply"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    budget_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        campaign_status: "ENABLED",
        advertising_channel_type: "SEARCH",
        budget_id: "777",
        budget_name: "Ekologus Search budget",
        budget_period: "DAILY",
        budget_status: "ENABLED",
        budget_amount_micros: 30000000,
        cost_micros_7d: 164591174,
        seven_day_budget_micros: 210000000,
        spend_to_budget_ratio_7d: 0.783768,
        has_recommended_budget: true,
        recommended_budget_amount_micros: 42000000,
        recommended_budget_delta_micros: 12000000,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        payload_preview: {
          id: "budget_apply_preview_123_777",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          campaign_budget_id: "777",
          campaign_budget_name: "Ekologus Search budget",
          operation_type: "CampaignBudgetOperation",
          current_budget_amount_micros: 30000000,
          proposed_budget_amount_micros: 42000000,
          proposed_budget_delta_micros: 12000000,
          reason:
            "Review-only podgląd CampaignBudgetOperation z Google recommended budget.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: [
            "budget_amount_micros",
            "budget_recommended_amount_micros"
          ],
          required_validation: [
            "review_campaign_activity",
            "verify_account_currency",
            "budget_pacing",
            "impression_share",
            "change_history",
            "human_budget_goal",
            "campaign_budget_operation_preview",
            "human_confirm_before_apply"
          ],
          blocked_claims: [
            "budget scaling",
            "budget apply",
            "campaign pause",
            "wasted budget",
            "profitability",
            "CPA verdict",
            "ROAS verdict",
            "recommendation apply"
          ],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        missing_metrics: [],
        blocked_claims: [
          "budget scaling",
          "budget apply",
          "profitability",
          "wasted budget",
          "recommendation apply"
        ]
      }
    ],
    payload_preview: [
      {
        id: "budget_apply_preview_123_777",
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        campaign_budget_id: "777",
        campaign_budget_name: "Ekologus Search budget",
        operation_type: "CampaignBudgetOperation",
        current_budget_amount_micros: 30000000,
        proposed_budget_amount_micros: 42000000,
        proposed_budget_delta_micros: 12000000,
        reason: "Review-only podgląd CampaignBudgetOperation z Google recommended budget.",
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        source_metric_names: [
          "budget_amount_micros",
          "budget_recommended_amount_micros"
        ],
        required_validation: [
          "review_campaign_activity",
          "verify_account_currency",
          "budget_pacing",
          "impression_share",
          "change_history",
          "human_budget_goal",
          "campaign_budget_operation_preview",
          "human_confirm_before_apply"
        ],
        blocked_claims: [
          "budget scaling",
          "budget apply",
          "campaign pause",
          "wasted budget",
          "profitability",
          "CPA verdict",
          "ROAS verdict",
          "recommendation apply"
        ],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ],
    action_ids: ["act_prepare_ads_campaign_review_queue"],
    next_step:
      "Użyj tego jako kontekstu review; nie skaluj budżetu bez historii zmian i walidowanego ActionObject."
  },
  recommendations_read_contract: {
    id: "ads_recommendations_read_contract",
    status: "ready",
    title: "Google Ads: rekomendacje do review",
    summary:
      "WILQ ma 1 aktywnych rekomendacji Google Ads do review. Typy: CAMPAIGN_BUDGET. Impact preview dostępny dla 1; apply payload preview dla 1.",
    allowed_metrics: [
      "recommendation_available",
      "recommendation_campaign_count",
      "recommendation_impact_base_clicks",
      "recommendation_impact_potential_clicks",
      "recommendation_impact_base_cost_micros",
      "recommendation_impact_potential_cost_micros"
    ],
    missing_read_contracts: ["change_history", "human_strategy_review"],
    blocked_claims: [
      "recommendation apply",
      "automatic recommendation accept",
      "budget apply",
      "campaign mutation",
      "performance uplift"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    recommendation_rows: [
      {
        recommendation_id: "rec-1",
        recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
        recommendation_type: "CAMPAIGN_BUDGET",
        dismissed: false,
        campaign_id: "123",
        campaign_budget_id: "777",
        campaign_count: 1,
        impact_available: true,
        base_clicks: 20,
        potential_clicks: 25,
        delta_clicks: 5,
        base_impressions: 200,
        potential_impressions: 260,
        delta_impressions: 60,
        base_cost_micros: 10000000,
        potential_cost_micros: 12000000,
        delta_cost_micros: 2000000,
        base_conversions: null,
        potential_conversions: null,
        delta_conversions: null,
        base_conversion_value: null,
        potential_conversion_value: null,
        delta_conversion_value: null,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        payload_preview: {
          id: "recommendation_apply_preview_rec-1",
          recommendation_id: "rec-1",
          recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
          recommendation_type: "CAMPAIGN_BUDGET",
          campaign_id: "123",
          campaign_budget_id: "777",
          operation_type: "ApplyRecommendationOperation",
          reason: "Review-only recommendation apply operation preview.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: [
            "recommendation_available",
            "recommendation_impact_potential_cost_micros"
          ],
          required_validation: [
            "review_recommendation_type",
            "review_impact_metrics",
            "review_change_history",
            "review_business_goal",
            "recommendation_apply_preview",
            "google_ads_rmf_compliance_review",
            "human_confirm_before_apply"
          ],
          blocked_claims: [
            "recommendation apply",
            "automatic recommendation accept",
            "budget apply",
            "campaign mutation",
            "performance uplift"
          ],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        missing_metrics: [],
        blocked_claims: [
          "recommendation apply",
          "automatic recommendation accept",
          "budget apply",
          "campaign mutation"
        ]
      }
    ],
    payload_preview: [
      {
        id: "recommendation_apply_preview_rec-1",
        recommendation_id: "rec-1",
        recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
        recommendation_type: "CAMPAIGN_BUDGET",
        campaign_id: "123",
        campaign_budget_id: "777",
        operation_type: "ApplyRecommendationOperation",
        reason: "Review-only recommendation apply operation preview.",
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        source_metric_names: [
          "recommendation_available",
          "recommendation_impact_potential_cost_micros"
        ],
        required_validation: [
          "review_recommendation_type",
          "review_impact_metrics",
          "review_change_history",
          "review_business_goal",
          "recommendation_apply_preview",
          "google_ads_rmf_compliance_review",
          "human_confirm_before_apply"
        ],
        blocked_claims: [
          "recommendation apply",
          "automatic recommendation accept",
          "budget apply",
          "campaign mutation",
          "performance uplift"
        ],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ],
    action_ids: ["act_prepare_google_ads_recommendation_review_queue"],
    next_step:
      "Potraktuj rekomendacje Google jako input do review, nie jako gotową strategię."
  },
  impression_share_read_contract: {
    id: "ads_impression_share_read_contract",
    status: "ready",
    title: "Google Ads: udział w wyświetleniach",
    summary: "WILQ ma impression share dla 1 kampanii; budget-lost > 0 w 1, rank-lost > 0 w 1.",
    allowed_metrics: [
      "search_impression_share",
      "search_budget_lost_impression_share",
      "search_rank_lost_impression_share"
    ],
    missing_read_contracts: ["change_history", "human_budget_goal", "budget_apply_preview"],
    blocked_claims: [
      "budget scaling",
      "budget apply",
      "wasted budget",
      "performance uplift",
      "campaign mutation"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    impression_share_rows: [
      {
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        campaign_status: "ENABLED",
        advertising_channel_type: "SEARCH",
        search_impression_share: 0.73,
        search_budget_lost_impression_share: 0.18,
        search_rank_lost_impression_share: 0.09,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        missing_metrics: [],
        blocked_claims: [
          "budget scaling",
          "budget apply",
          "wasted budget",
          "performance uplift"
        ]
      }
    ],
    next_step:
      "Użyj udziału w wyświetleniach jako kontekstu review, nie jako decyzji budżetowej."
  },
  change_history_read_contract: {
    id: "ads_change_history_read_contract",
    status: "ready",
    title: "Google Ads: historia zmian",
    summary:
      "WILQ ma 1 zdarzeń historii zmian Google Ads z ostatnich 14 dni. Typy zasobów: CAMPAIGN; operacje: UPDATE.",
    allowed_metrics: ["change_event_available", "change_event_changed_field_count"],
    missing_read_contracts: [
      "pre_change_performance_window",
      "post_change_performance_window",
      "human_change_impact_review",
      "apply_preview"
    ],
    blocked_claims: [
      "change impact",
      "performance uplift",
      "budget scaling",
      "budget apply",
      "campaign mutation"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    change_history_rows: [
      {
        change_event_id: "change-1",
        change_date_time: "2026-06-18 12:30:00.000000",
        change_resource_id: "123",
        change_resource_type: "CAMPAIGN",
        resource_change_operation: "UPDATE",
        client_type: "GOOGLE_ADS_WEB_CLIENT",
        campaign_id: "123",
        changed_field_count: 2,
        changed_fields: ["campaign.status", "campaign_budget.amount_micros"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        missing_metrics: [],
        blocked_claims: [
          "change impact",
          "performance uplift",
          "budget apply",
          "campaign mutation"
        ]
      }
    ],
    next_step:
      "Użyj historii zmian jako kontekstu audytu, nie jako dowodu wpływu zmiany."
  },
  search_terms_read_contract: {
    id: "ads_search_terms_read_contract",
    status: "ready",
    title: "Google Ads: zapytania użytkowników",
    summary:
      "WILQ ma 1 wierszy zapytań: kliknięcia=12, wyświetlenia=140, koszt_micros=9000000, konwersje=1, wartość_konwersji=120.",
    allowed_metrics: [
      "search_term",
      "campaign",
      "ad_group",
      "status",
      "clicks",
      "impressions",
      "cost_micros",
      "conversions",
      "conversion_value"
    ],
    missing_read_contracts: [
      "90_day_safety_check",
      "negative_keyword_action_validation"
    ],
    blocked_claims: [
      "search-term waste",
      "negative keyword candidates",
      "negative keyword apply",
      "CPA",
      "ROAS"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    search_term_rows: [
      {
        search_term: "bdo rejestracja",
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        ad_group_id: "456",
        ad_group_name: "BDO",
        search_term_status: "ADDED",
        clicks: 12,
        impressions: 140,
        cost_micros: 9000000,
        conversions: 1,
        conversion_value: 120,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [
          {
            name: "search_term_clicks",
            value: 12,
            period: "connector_refresh",
            source_connector: "google_ads",
            evidence_id: "ev_refresh_refresh_google_ads_test",
            dimensions: {
              campaign_id: "123",
              campaign_name: "Ekologus Search",
              ad_group_id: "456",
              ad_group_name: "BDO",
              search_term: "bdo rejestracja",
              search_term_status: "ADDED"
            },
            unit: null
          },
          {
            name: "search_term_conversions",
            value: 1,
            period: "connector_refresh",
            source_connector: "google_ads",
            evidence_id: "ev_refresh_refresh_google_ads_test",
            dimensions: {
              campaign_id: "123",
              campaign_name: "Ekologus Search",
              ad_group_id: "456",
              ad_group_name: "BDO",
              search_term: "bdo rejestracja",
              search_term_status: "ADDED"
            },
            unit: null
          }
        ],
        missing_metrics: [],
        blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"]
      }
    ],
    next_step: "Użyj wierszy zapytań jako przeglądu danych z reklam."
  },
  search_term_safety_read_contract: {
    id: "ads_search_term_safety_read_contract",
    status: "ready",
    title: "Google Ads: 90-dniowy safety read zapytań",
    summary:
      "WILQ ma 90-dniowy read safety dla 1 zapytań: kliknięcia=10, wyświetlenia=120, koszt_micros=8000000, konwersje=0, wartość_konwersji=0.",
    allowed_metrics: [
      "search_term",
      "campaign",
      "ad_group",
      "status",
      "search_term_90d_clicks",
      "search_term_90d_impressions",
      "search_term_90d_cost_micros",
      "search_term_90d_conversions",
      "search_term_90d_conversion_value"
    ],
    missing_read_contracts: [
      "keyword match context",
      "human_intent_review"
    ],
    blocked_claims: [
      "negative keyword apply",
      "search-term waste",
      "conversion loss",
      "CPA",
      "ROAS"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    safety_rows: [
      {
        search_term: "odpady cena",
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        ad_group_id: "789",
        ad_group_name: "Odpady",
        search_term_status: "NONE",
        clicks_90d: 10,
        impressions_90d: 120,
        cost_micros_90d: 8000000,
        conversions_90d: 0,
        conversion_value_90d: 0,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        missing_metrics: [],
        blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"]
      }
    ],
    next_step:
      "Użyj 90-dniowego odczytu jako hamulca bezpieczeństwa przed wykluczeniem."
  },
  keyword_match_context_read_contract: {
    id: "ads_keyword_match_context_read_contract",
    status: "ready",
    title: "Google Ads: kontekst dopasowań keywords",
    summary:
      "WILQ ma read-only kontekst 1 istniejących keywordów z match types: BROAD.",
    allowed_metrics: [
      "keyword_text",
      "keyword_match_type",
      "criterion_status",
      "keyword_negative",
      "campaign",
      "ad_group"
    ],
    missing_read_contracts: ["human_intent_review"],
    blocked_claims: [
      "negative keyword apply",
      "search-term waste",
      "conversion loss",
      "CPA",
      "ROAS"
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    context_rows: [
      {
        keyword_text: "odpady",
        match_type: "BROAD",
        criterion_id: "401",
        criterion_status: "ENABLED",
        negative: false,
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        ad_group_id: "789",
        ad_group_name: "Odpady",
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        blocked_claims: ["negative keyword apply", "search-term waste", "wasted budget"]
      }
    ],
    next_step: "Użyj tego jako kontekstu review, nie jako zgody na apply."
  },
  custom_segments_read_contract: {
    id: "ads_custom_segments_read_contract",
    status: "ready",
    title: "Custom segments z realnych search terms",
    summary: "WILQ ma 1 kandydatów custom segments i 1 source terms z Google Ads evidence.",
    candidates: [
      {
        id: "ads_custom_segment_123",
        name: "Search terms: Ekologus Search",
        intent: "search_term_interest",
        source_terms: ["bdo rejestracja"],
        rejected_terms: [],
        rejection_reasons: [],
        search_term_rows: [
          {
            search_term: "bdo rejestracja",
            campaign_id: "123",
            campaign_name: "Ekologus Search",
            ad_group_id: "456",
            ad_group_name: "BDO",
            search_term_status: "ADDED",
            clicks: 12,
            impressions: 140,
            cost_micros: 9000000,
            conversions: 1,
            conversion_value: 120,
            evidence_ids: ["ev_refresh_refresh_google_ads_test"],
            metric_facts: [],
            missing_metrics: [],
            blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"]
          }
        ],
        source_connectors: ["google_ads"],
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        confidence: "medium",
        validation_status: "pending_validation",
        payload_preview: {
          id: "preview_ads_custom_segment_123",
          custom_segment_name: "Search terms: Ekologus Search",
          member_type: "KEYWORD",
          source_terms: ["bdo rejestracja"],
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          reason: "Review-only custom audience keyword members from search-term evidence.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: ["search_term_clicks", "search_term_impressions"],
          required_validation: [
            "review_source_terms",
            "reject_brand_or_low_intent_terms",
            "keyword_planner_enrichment",
            "forecast_or_audience_size",
            "human_confirm_before_apply"
          ],
          blocked_claims: [
            "audience size",
            "conversion uplift",
            "ROAS",
            "targeting applied",
            "campaign performance"
          ],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        blocked_claims: [
          "audience size",
          "conversion uplift",
          "ROAS",
          "targeting applied",
          "campaign performance"
        ],
        next_step: "Użyj tych terminów jako prepare-only candidate."
      }
    ],
    payload_preview: [
      {
        id: "preview_ads_custom_segment_123",
        custom_segment_name: "Search terms: Ekologus Search",
        member_type: "KEYWORD",
        source_terms: ["bdo rejestracja"],
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        reason: "Review-only custom audience keyword members from search-term evidence.",
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        source_metric_names: ["search_term_clicks", "search_term_impressions"],
        required_validation: [
          "review_source_terms",
          "reject_brand_or_low_intent_terms",
          "keyword_planner_enrichment",
          "forecast_or_audience_size",
          "human_confirm_before_apply"
        ],
        blocked_claims: [
          "audience size",
          "conversion uplift",
          "ROAS",
          "targeting applied",
          "campaign performance"
        ],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    missing_read_contracts: [
      "keyword_planner_enrichment",
      "forecast_or_audience_size"
    ],
    blocked_claims: [
      "audience size",
      "conversion uplift",
      "ROAS",
      "targeting applied",
      "campaign performance"
    ],
    action_ids: ["act_prepare_custom_segments_from_search_terms"],
    next_step: "Przejrzyj source terms i waliduj ActionObject przed apply."
  },
  negative_keywords_read_contract: {
    id: "ads_negative_keywords_read_contract",
    status: "ready",
    title: "Review wykluczeń z search terms",
    summary:
      "WILQ ma 1 terminów do review: mają koszt lub kliknięcia i zero konwersji w bieżącym Google Ads evidence.",
    candidates: [
      {
        id: "ads_negative_keyword_review_123_789_odpady_cena",
        search_term: "odpady cena",
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        ad_group_id: "789",
        ad_group_name: "Odpady",
        clicks: 6,
        impressions: 60,
        cost_micros: 5000000,
        conversions: 0,
        conversion_value: 0,
        clicks_90d: 10,
        impressions_90d: 120,
        cost_micros_90d: 8000000,
        conversions_90d: 0,
        conversion_value_90d: 0,
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        safety_evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        keyword_context_evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        metric_facts: [],
        safety_metric_facts: [],
        keyword_context_rows: [
          {
            keyword_text: "odpady",
            match_type: "BROAD",
            criterion_id: "401",
            criterion_status: "ENABLED",
            negative: false,
            campaign_id: "123",
            campaign_name: "Ekologus Search",
            ad_group_id: "789",
            ad_group_name: "Odpady",
            evidence_ids: ["ev_refresh_refresh_google_ads_test"],
            metric_facts: [],
            blocked_claims: ["negative keyword apply", "search-term waste", "wasted budget"]
          }
        ],
        payload_preview: {
          id: "negative_keyword_preview_123_789_odpady_cena",
          search_term: "odpady cena",
          negative_keyword_text: "odpady cena",
          match_type: "EXACT",
          level: "ad_group",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "789",
          ad_group_name: "Odpady",
          reason: "Exact negative keyword review preview zbudowany z evidence.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: ["search_term_clicks", "search_term_90d_clicks"],
          required_validation: [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "human_confirm_before_apply"
          ],
          blocked_claims: ["negative keyword apply", "search-term waste"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        },
        required_checks: [
          "review_search_term_context",
          "check_existing_keywords_and_match_types",
          "90_day_safety_check",
          "negative_keyword_payload_preview",
          "human_confirm_before_apply"
        ],
        safety_status: "read_ready_needs_human_review",
        validation_status: "pending_validation",
        blocked_claims: ["negative keyword apply", "search-term waste", "CPA", "ROAS"],
        next_step: "Sprawdź intencję i 90-dniową historię przed wykluczeniem."
      }
    ],
    payload_preview: [
      {
        id: "negative_keyword_preview_123_789_odpady_cena",
        search_term: "odpady cena",
        negative_keyword_text: "odpady cena",
        match_type: "EXACT",
        level: "ad_group",
        campaign_id: "123",
        campaign_name: "Ekologus Search",
        ad_group_id: "789",
        ad_group_name: "Odpady",
        reason: "Exact negative keyword review preview zbudowany z evidence.",
        evidence_ids: ["ev_refresh_refresh_google_ads_test"],
        source_metric_names: ["search_term_clicks", "search_term_90d_clicks"],
        required_validation: [
          "review_search_term_context",
          "check_existing_keywords_and_match_types",
          "90_day_safety_check",
          "human_confirm_before_apply"
        ],
        blocked_claims: ["negative keyword apply", "search-term waste"],
        api_mutation_ready: false,
        apply_allowed: false,
        destructive: false
      }
    ],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    missing_read_contracts: [],
    blocked_claims: [
      "negative keyword apply",
      "search-term waste",
      "conversion loss",
      "CPA",
      "ROAS"
    ],
    action_ids: ["act_prepare_negative_keyword_review_queue"],
    next_step: "Przejrzyj kandydatów jako review-only i sprawdź payload preview."
  },
  decision_queue: [
    {
      id: "ads_review_campaign_activity",
      decision_type: "review_campaign_activity",
      status: "ready",
      title: "Przejrzyj aktywność kampanii Google Ads",
      summary:
        "WILQ ma 1 wierszy kampanii: kliknięcia=107, wyświetlenia=2783, koszt_micros=164591174, konwersje=2.5, wartość_konwersji=450.75.",
      rationale:
        "To jest uczciwy pierwszy przegląd kampanii: WILQ widzi kliknięcia, wyświetlenia, koszt, konwersje i wartość konwersji po kampaniach.",
      next_step: "Sprawdź kampanie z największym kosztem i ruchem w tabeli dowodów.",
      priority: 20,
      metric_tiles: {
        kampanie: 1,
        kliknięcia: 107,
        wyświetlenia: 2783,
        koszt: "164.6",
        konwersje: 2.5
      },
      allowed_metrics: ["clicks", "impressions", "cost_micros", "conversions", "conversion_value"],
      missing_read_contracts: [],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [
        {
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          clicks: 107,
          impressions: 2783,
          cost_micros: 164591174,
          conversions: 2.5,
          conversion_value: 450.75,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: ["CPA", "ROAS", "search-term waste", "wasted budget"]
        }
      ],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [],
      custom_segment_candidates: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      knowledge_card_ids: [
        "card_google_ads_search_playbook",
        "card_google_ads_budget_review_playbook"
      ],
      expert_rule_ids: [
        "ads_diagnostics_v1",
        "ads_scaling_candidates_v1",
        "ads_recommendations_v1"
      ],
      blocked_claims: ["CPA", "ROAS", "search-term waste", "wasted budget"],
      risk: "low"
    },
    {
      id: "ads_review_recommendations",
      decision_type: "review_recommendations",
      status: "ready",
      title: "Przejrzyj rekomendacje Google Ads bez apply",
      summary:
        "WILQ ma 1 aktywnych rekomendacji Google Ads do review. Typy: CAMPAIGN_BUDGET. Impact preview dostępny dla 1; apply payload preview dla 1.",
      rationale:
        "Google Ads recommendations są sygnałem do kontroli, nie automatyczną strategią.",
      next_step:
        "Potraktuj rekomendacje Google jako input do review, nie jako gotową strategię.",
      priority: 35,
      metric_tiles: {
        rekomendacje: 1,
        "podgląd wpływu": 1,
        "podgląd akcji": 1
      },
      allowed_metrics: [
        "recommendation_available",
        "recommendation_campaign_count",
        "recommendation_impact_base_clicks",
        "recommendation_impact_potential_clicks",
        "recommendation_impact_base_cost_micros",
        "recommendation_impact_potential_cost_micros"
      ],
      missing_read_contracts: ["change_history", "human_strategy_review"],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [
        {
          recommendation_id: "rec-1",
          recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
          recommendation_type: "CAMPAIGN_BUDGET",
          dismissed: false,
          campaign_id: "123",
          campaign_budget_id: "777",
          campaign_count: 1,
          impact_available: true,
          base_clicks: 20,
          potential_clicks: 25,
          delta_clicks: 5,
          base_impressions: 200,
          potential_impressions: 260,
          delta_impressions: 60,
          base_cost_micros: 10000000,
          potential_cost_micros: 12000000,
          delta_cost_micros: 2000000,
          base_conversions: null,
          potential_conversions: null,
          delta_conversions: null,
          base_conversion_value: null,
          potential_conversion_value: null,
          delta_conversion_value: null,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          payload_preview: {
            id: "recommendation_apply_preview_rec-1",
            recommendation_id: "rec-1",
            recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
            recommendation_type: "CAMPAIGN_BUDGET",
            campaign_id: "123",
            campaign_budget_id: "777",
            operation_type: "ApplyRecommendationOperation",
            reason: "Review-only recommendation apply operation preview.",
            evidence_ids: ["ev_refresh_refresh_google_ads_test"],
            source_metric_names: [
              "recommendation_available",
              "recommendation_impact_potential_cost_micros"
            ],
            required_validation: [
              "review_recommendation_type",
              "review_impact_metrics",
              "review_change_history",
              "review_business_goal",
              "recommendation_apply_preview",
              "google_ads_rmf_compliance_review",
              "human_confirm_before_apply"
            ],
            blocked_claims: [
              "recommendation apply",
              "automatic recommendation accept",
              "budget apply",
              "campaign mutation",
              "performance uplift"
            ],
            api_mutation_ready: false,
            apply_allowed: false,
            destructive: false
          },
          missing_metrics: [],
          blocked_claims: [
            "recommendation apply",
            "automatic recommendation accept",
            "budget apply",
            "campaign mutation"
          ]
        }
      ],
      recommendation_apply_preview: [
        {
          id: "recommendation_apply_preview_rec-1",
          recommendation_id: "rec-1",
          recommendation_resource_name: "customers/1234567890/recommendations/rec-1",
          recommendation_type: "CAMPAIGN_BUDGET",
          campaign_id: "123",
          campaign_budget_id: "777",
          operation_type: "ApplyRecommendationOperation",
          reason: "Review-only recommendation apply operation preview.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: [
            "recommendation_available",
            "recommendation_impact_potential_cost_micros"
          ],
          required_validation: [
            "review_recommendation_type",
            "review_impact_metrics",
            "review_change_history",
            "review_business_goal",
            "recommendation_apply_preview",
            "google_ads_rmf_compliance_review",
            "human_confirm_before_apply"
          ],
          blocked_claims: [
            "recommendation apply",
            "automatic recommendation accept",
            "budget apply",
            "campaign mutation",
            "performance uplift"
          ],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [],
      custom_segment_candidates: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: ["act_prepare_google_ads_recommendation_review_queue"],
      knowledge_card_ids: ["card_google_ads_budget_review_playbook"],
      expert_rule_ids: ["ads_recommendations_v1", "ads_principles_v1"],
      blocked_claims: [
        "recommendation apply",
        "automatic recommendation accept",
        "budget apply",
        "campaign mutation",
        "performance uplift"
      ],
      risk: "medium"
    },
    {
      id: "ads_review_impression_share",
      decision_type: "review_impression_share",
      status: "ready",
      title: "Sprawdź utracony udział w wyświetleniach",
      summary: "WILQ ma impression share dla 1 kampanii; budget-lost > 0 w 1, rank-lost > 0 w 1.",
      rationale:
        "Impression share pokazuje, czy kampania traci ekspozycję przez budżet albo ranking.",
      next_step:
        "Użyj udziału w wyświetleniach jako kontekstu review, nie jako decyzji budżetowej.",
      allowed_metrics: [
        "search_impression_share",
        "search_budget_lost_impression_share",
        "search_rank_lost_impression_share"
      ],
      missing_read_contracts: ["change_history", "human_budget_goal", "budget_apply_preview"],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [
        {
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          campaign_status: "ENABLED",
          advertising_channel_type: "SEARCH",
          search_impression_share: 0.73,
          search_budget_lost_impression_share: 0.18,
          search_rank_lost_impression_share: 0.09,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: [
            "budget scaling",
            "budget apply",
            "wasted budget",
            "performance uplift"
          ]
        }
      ],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [],
      custom_segment_candidates: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      knowledge_card_ids: ["card_google_ads_budget_review_playbook"],
      expert_rule_ids: ["ads_scaling_candidates_v1", "ads_principles_v1"],
      blocked_claims: [
        "budget scaling",
        "budget apply",
        "wasted budget",
        "performance uplift",
        "campaign mutation"
      ],
      risk: "medium"
    },
    {
      id: "ads_review_change_history",
      decision_type: "review_change_history",
      status: "ready",
      title: "Sprawdź historię zmian Google Ads",
      summary:
        "WILQ ma 1 zdarzeń historii zmian Google Ads z ostatnich 14 dni. Typy zasobów: CAMPAIGN; operacje: UPDATE.",
      rationale:
        "Historia zmian mówi, co ostatnio zmieniano w koncie, ale nie dowodzi wpływu na wynik.",
      next_step:
        "Użyj historii zmian jako kontekstu audytu, nie jako dowodu wpływu zmiany.",
      allowed_metrics: ["change_event_available", "change_event_changed_field_count"],
      missing_read_contracts: [
        "pre_change_performance_window",
        "post_change_performance_window",
        "human_change_impact_review",
        "apply_preview"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [],
      change_history_rows: [
        {
          change_event_id: "change-1",
          change_date_time: "2026-06-18 12:30:00.000000",
          change_resource_id: "123",
          change_resource_type: "CAMPAIGN",
          resource_change_operation: "UPDATE",
          client_type: "GOOGLE_ADS_WEB_CLIENT",
          campaign_id: "123",
          changed_field_count: 2,
          changed_fields: ["campaign.status", "campaign_budget.amount_micros"],
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: [
            "change impact",
            "performance uplift",
            "budget apply",
            "campaign mutation"
          ]
        }
      ],
      search_term_rows: [],
      search_term_safety_rows: [],
      custom_segment_candidates: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      knowledge_card_ids: ["card_google_ads_budget_review_playbook"],
      expert_rule_ids: ["ads_diagnostics_v1", "ads_principles_v1"],
      blocked_claims: [
        "change impact",
        "performance uplift",
        "budget apply",
        "campaign mutation"
      ],
      risk: "medium"
    },
    {
      id: "ads_review_search_terms",
      decision_type: "review_search_terms",
      status: "ready",
      title: "Przejrzyj zapytania z reklam bez automatycznych wykluczeń",
      summary:
        "WILQ ma 1 wierszy zapytań: kliknięcia=12, wyświetlenia=140, koszt_micros=9000000, konwersje=1, wartość_konwersji=120.",
      rationale:
        "WILQ widzi zapytania, kampanie, grupy reklam, koszt, kliknięcia i konwersje.",
      next_step: "Przejrzyj zapytania z najwyższym kosztem.",
      allowed_metrics: ["search_term", "campaign", "ad_group", "clicks", "conversions"],
      missing_read_contracts: [
        "keyword match context",
        "negative_keyword_action_validation"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [
        {
          search_term: "bdo rejestracja",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "456",
          ad_group_name: "BDO",
          search_term_status: "ADDED",
          clicks: 12,
          impressions: 140,
          cost_micros: 9000000,
          conversions: 1,
          conversion_value: 120,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"]
        }
      ],
      custom_segment_candidates: [],
      search_term_safety_rows: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"],
      risk: "medium"
    },
    {
      id: "ads_review_search_term_safety",
      decision_type: "review_search_term_safety",
      status: "ready",
      title: "Sprawdź 90-dniową historię zapytań przed wykluczeniami",
      summary:
        "WILQ ma 90-dniowy read safety dla 1 zapytań: kliknięcia=10, wyświetlenia=120, koszt_micros=8000000, konwersje=0, wartość_konwersji=0.",
      rationale:
        "WILQ ma oddzielny 90-dniowy odczyt search terms jako hamulec bezpieczeństwa.",
      next_step:
        "Użyj 90-dniowego odczytu jako hamulca bezpieczeństwa przed wykluczeniem.",
      allowed_metrics: [
        "search_term_90d_clicks",
        "search_term_90d_impressions",
        "search_term_90d_cost_micros",
        "search_term_90d_conversions",
        "search_term_90d_conversion_value"
      ],
      missing_read_contracts: [
        "keyword match context",
        "human_intent_review"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [
        {
          search_term: "odpady cena",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "789",
          ad_group_name: "Odpady",
          search_term_status: "NONE",
          clicks_90d: 10,
          impressions_90d: 120,
          cost_micros_90d: 8000000,
          conversions_90d: 0,
          conversion_value_90d: 0,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"]
        }
      ],
      custom_segment_candidates: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      knowledge_card_ids: [
        "card_google_ads_negative_keywords_playbook",
        "card_google_ads_search_playbook"
      ],
      expert_rule_ids: [
        "ads_negative_keywords_v1",
        "ads_search_terms_v1",
        "ads_principles_v1"
      ],
      blocked_claims: ["negative keyword apply", "search-term waste", "CPA", "ROAS"],
      risk: "medium"
    },
    {
      id: "ads_review_negative_keyword_safety",
      decision_type: "review_negative_keyword_safety",
      status: "ready",
      title: "Przejrzyj kandydatów wykluczeń tylko w trybie safety review",
      summary:
        "WILQ ma 1 terminów do review: mają koszt lub kliknięcia i zero konwersji w bieżącym Google Ads evidence.",
      rationale:
        "To jest sygnał do review, nie dowód waste ani zgoda na automatyczne wykluczenie.",
      next_step: "Przejrzyj kandydatów jako review-only przed payload preview.",
      allowed_metrics: [
        "search_term",
        "search_term_clicks",
        "search_term_cost_micros",
        "search_term_conversions"
      ],
      missing_read_contracts: ["keyword match context"],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [
        {
          search_term: "odpady cena",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "789",
          ad_group_name: "Odpady",
          search_term_status: "NONE",
          clicks_90d: 10,
          impressions_90d: 120,
          cost_micros_90d: 8000000,
          conversions_90d: 0,
          conversion_value_90d: 0,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"]
        }
      ],
      custom_segment_candidates: [],
      negative_keyword_candidates: [
        {
          id: "ads_negative_keyword_review_123_789_odpady_cena",
          search_term: "odpady cena",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "789",
          ad_group_name: "Odpady",
          clicks: 6,
          impressions: 60,
          cost_micros: 5000000,
          conversions: 0,
          conversion_value: 0,
          clicks_90d: 10,
          impressions_90d: 120,
          cost_micros_90d: 8000000,
          conversions_90d: 0,
          conversion_value_90d: 0,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          safety_evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          safety_metric_facts: [],
          payload_preview: {
            id: "negative_keyword_preview_123_789_odpady_cena",
            search_term: "odpady cena",
            negative_keyword_text: "odpady cena",
            match_type: "EXACT",
            level: "ad_group",
            campaign_id: "123",
            campaign_name: "Ekologus Search",
            ad_group_id: "789",
            ad_group_name: "Odpady",
            reason: "Exact negative keyword review preview zbudowany z evidence.",
            evidence_ids: ["ev_refresh_refresh_google_ads_test"],
            source_metric_names: ["search_term_clicks", "search_term_90d_clicks"],
            required_validation: [
              "review_search_term_context",
              "check_existing_keywords_and_match_types",
              "90_day_safety_check",
              "human_confirm_before_apply"
            ],
            blocked_claims: ["negative keyword apply", "search-term waste"],
            api_mutation_ready: false,
            apply_allowed: false,
            destructive: false
          },
          required_checks: [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "negative_keyword_payload_preview",
            "human_confirm_before_apply"
          ],
          safety_status: "read_ready_needs_human_review",
          validation_status: "pending_validation",
          blocked_claims: ["negative keyword apply", "search-term waste", "CPA", "ROAS"],
          next_step: "Sprawdź intencję i 90-dniową historię przed wykluczeniem."
        }
      ],
      negative_keyword_payload_preview: [
        {
          id: "negative_keyword_preview_123_789_odpady_cena",
          search_term: "odpady cena",
          negative_keyword_text: "odpady cena",
          match_type: "EXACT",
          level: "ad_group",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "789",
          ad_group_name: "Odpady",
          reason: "Exact negative keyword review preview zbudowany z evidence.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: ["search_term_clicks", "search_term_90d_clicks"],
          required_validation: [
            "review_search_term_context",
            "check_existing_keywords_and_match_types",
            "90_day_safety_check",
            "human_confirm_before_apply"
          ],
          blocked_claims: ["negative keyword apply", "search-term waste"],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      action_ids: ["act_prepare_negative_keyword_review_queue"],
      blocked_claims: ["negative keyword apply", "search-term waste", "CPA", "ROAS"],
      risk: "medium"
    },
    {
      id: "ads_prepare_custom_segments_from_search_terms",
      decision_type: "prepare_custom_segments",
      status: "ready",
      title: "Przygotuj custom segments z realnych search terms",
      summary: "WILQ ma 1 kandydatów custom segments i 1 source terms z Google Ads evidence.",
      rationale: "WILQ ma source terms z Google Ads evidence, więc może przygotować kandydatów segmentów.",
      next_step: "Przejrzyj source terms i waliduj ActionObject przed apply.",
      allowed_metrics: ["search_term", "search_term_clicks", "search_term_impressions"],
      missing_read_contracts: [
        "keyword_planner_enrichment",
        "forecast_or_audience_size"
      ],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [
        {
          search_term: "bdo rejestracja",
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          ad_group_id: "456",
          ad_group_name: "BDO",
          search_term_status: "ADDED",
          clicks: 12,
          impressions: 140,
          cost_micros: 9000000,
          conversions: 1,
          conversion_value: 120,
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          missing_metrics: [],
          blocked_claims: ["CPA", "ROAS", "negative keyword apply", "wasted budget"]
        }
      ],
      search_term_safety_rows: [],
      custom_segment_candidates: [
        {
          id: "ads_custom_segment_123",
          name: "Search terms: Ekologus Search",
          intent: "search_term_interest",
          source_terms: ["bdo rejestracja"],
          rejected_terms: [],
          rejection_reasons: [],
          search_term_rows: [],
          source_connectors: ["google_ads"],
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          metric_facts: [],
          confidence: "medium",
          validation_status: "pending_validation",
          payload_preview: {
            id: "preview_ads_custom_segment_123",
            custom_segment_name: "Search terms: Ekologus Search",
            member_type: "KEYWORD",
            source_terms: ["bdo rejestracja"],
            campaign_id: "123",
            campaign_name: "Ekologus Search",
            reason: "Review-only custom audience keyword members from search-term evidence.",
            evidence_ids: ["ev_refresh_refresh_google_ads_test"],
            source_metric_names: ["search_term_clicks", "search_term_impressions"],
            required_validation: [
              "review_source_terms",
              "reject_brand_or_low_intent_terms",
              "keyword_planner_enrichment",
              "forecast_or_audience_size",
              "human_confirm_before_apply"
            ],
            blocked_claims: [
              "audience size",
              "conversion uplift",
              "ROAS",
              "targeting applied",
              "campaign performance"
            ],
            api_mutation_ready: false,
            apply_allowed: false,
            destructive: false
          },
          blocked_claims: [
            "audience size",
            "conversion uplift",
            "ROAS",
            "targeting applied",
            "campaign performance"
          ],
          next_step: "Użyj tych terminów jako prepare-only candidate."
        }
      ],
      custom_segment_payload_preview: [
        {
          id: "preview_ads_custom_segment_123",
          custom_segment_name: "Search terms: Ekologus Search",
          member_type: "KEYWORD",
          source_terms: ["bdo rejestracja"],
          campaign_id: "123",
          campaign_name: "Ekologus Search",
          reason: "Review-only custom audience keyword members from search-term evidence.",
          evidence_ids: ["ev_refresh_refresh_google_ads_test"],
          source_metric_names: ["search_term_clicks", "search_term_impressions"],
          required_validation: [
            "review_source_terms",
            "reject_brand_or_low_intent_terms",
            "keyword_planner_enrichment",
            "forecast_or_audience_size",
            "human_confirm_before_apply"
          ],
          blocked_claims: [
            "audience size",
            "conversion uplift",
            "ROAS",
            "targeting applied"
          ],
          api_mutation_ready: false,
          apply_allowed: false,
          destructive: false
        }
      ],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: ["act_prepare_custom_segments_from_search_terms"],
      blocked_claims: ["audience size", "conversion uplift", "ROAS", "targeting applied"],
      risk: "medium"
    },
    {
      id: "ads_block_write_actions_without_actionobject",
      decision_type: "block_write_actions",
      status: "blocked",
      title: "Nie wdrażaj zmian Ads bez osobnego ActionObject",
      summary: "WILQ ma dowody z odczytu Google Ads; ścieżka zapisu nadal nie ma gotowego ActionObject.",
      rationale: "Zmiany budżetów, kampanii, wykluczeń i segmentów wymagają walidacji.",
      next_step: "Rozszerz Ads workflow o prepare-only ActionObject.",
      allowed_metrics: [],
      missing_read_contracts: [],
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [],
      campaign_rows: [],
      derived_kpi_rows: [],
      budget_rows: [],
      recommendation_rows: [],
      impression_share_rows: [],
      change_history_rows: [],
      search_term_rows: [],
      search_term_safety_rows: [],
      custom_segment_candidates: [],
      negative_keyword_candidates: [],
      negative_keyword_payload_preview: [],
      action_ids: [],
      blocked_claims: ["budget apply", "campaign creation", "negative keyword apply"],
      risk: "medium"
    }
  ],
  sections: [
    {
      id: "ads_live_data_status",
      title: "Google Ads: live data dostępne",
      status: "ready",
      summary: "WILQ ma zapisane metric facts z odczytu Google Ads vendor_read.",
      diagnosis: "Ads Doctor może pokazać campaign i search-term metrics, ale nie CPA/ROAS.",
      next_step: "Analizuj tylko widoczne metric facts i evidence IDs.",
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
      metric_facts: [
        {
          name: "clicks",
          value: 107,
          period: "connector_refresh",
          source_connector: "google_ads",
          evidence_id: "ev_refresh_refresh_google_ads_test",
          dimensions: { campaign_id: "123", campaign_name: "Ekologus Search" },
          unit: null
        }
      ],
      action_ids: [],
      blocked_claims: ["CPA", "ROAS", "wasted budget"],
      risk: "medium"
    },
    {
      id: "ads_campaign_overview",
      title: "Aktywność kampanii Google Ads",
      status: "ready",
      summary: "Metric facts: clicks=107, impressions=2783.",
      diagnosis: "Są live campaign rows, ale CPA/ROAS wymagają osobnego read contract.",
      next_step: "Sprawdź kampanie bez claimów CPA/ROAS.",
      source_connectors: ["google_ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      metric_facts: [
        {
          name: "impressions",
          value: 2783,
          period: "connector_refresh",
          source_connector: "google_ads",
          evidence_id: "ev_refresh_refresh_google_ads_test",
          dimensions: { campaign_id: "123", campaign_name: "Ekologus Search" },
          unit: null
        }
      ],
      action_ids: [],
      blocked_claims: ["CPA", "ROAS", "wasted budget"],
      risk: "medium"
    }
  ],
  blocked_handoff: null,
  evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
  action_ids: [
    "act_prepare_google_ads_recommendation_review_queue",
    "act_prepare_custom_segments_from_search_terms",
    "act_prepare_negative_keyword_review_queue"
  ],
  blocker_count: 1
};

const metricFacts = [
  {
    name: "content_object_count",
    value: 16,
    period: "connector_refresh",
    source_connector: "wordpress_ekologus",
    evidence_id: "ev_refresh_wordpress_inventory",
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 14,
    delta: 2,
    delta_percent: 14.2857,
    trend: "up",
    freshness_state: "fresh",
    freshness_label: "odświeżone mniej niż godzinę temu"
  },
  {
    name: "merchant_disapproved_product_count",
    value: 3,
    period: "connector_refresh",
    source_connector: "google_merchant_center",
    evidence_id: "ev_refresh_merchant_feed",
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 4,
    delta: -1,
    delta_percent: -25,
    trend: "down",
    freshness_state: "fresh",
    freshness_label: "odświeżone mniej niż godzinę temu"
  },
  {
    name: "total_products",
    value: 10900,
    period: "connector_refresh",
    source_connector: "google_merchant_center",
    evidence_id: "ev_refresh_merchant_feed",
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 10900,
    delta: 0,
    delta_percent: 0,
    trend: "flat",
    freshness_state: "fresh",
    freshness_label: "odświeżone mniej niż godzinę temu"
  },
  {
    name: "issue_product_count",
    value: 23,
    period: "connector_refresh",
    source_connector: "google_merchant_center",
    evidence_id: "ev_refresh_merchant_feed",
    dimensions: {
      issue_type: "availability_updated",
      affected_attribute: "n:availability"
    },
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 20,
    delta: 3,
    delta_percent: 15,
    trend: "up",
    freshness_state: "fresh",
    freshness_label: "odświeżone mniej niż godzinę temu"
  },
  {
    name: "active_users",
    value: 20,
    period: "connector_refresh",
    source_connector: "google_analytics_4",
    evidence_id: "ev_refresh_ga4",
    dimensions: {
      landing_page: "/oferta/",
      source_medium: "google / cpc",
      campaign_name: "Ekologus Ogólna"
    },
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 10,
    delta: 10,
    delta_percent: 100,
    trend: "up",
    freshness_state: "fresh",
    freshness_label: "odświeżone mniej niż godzinę temu"
  },
  {
    name: "clicks",
    value: 12,
    period: "connector_refresh",
    source_connector: "google_search_console",
    evidence_id: "ev_refresh_gsc",
    unit: null,
    collected_at: "2026-06-17T10:00:00Z",
    previous_value: 12,
    delta: 0,
    delta_percent: 0,
    trend: "flat",
    freshness_state: "fresh",
    freshness_label: "odświeżone mniej niż godzinę temu"
  }
];

const metricStoreStatus = {
  backend: "duckdb",
  enabled: true,
  path_configured: false,
  metric_fact_count: 1,
  connector_count: 1,
  refresh_run_count: 1
};

const marketingBrief = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  connector_summary: { total: 1, configured: 0, missing_credentials: 1 },
  sections: [
    {
      id: "what_we_know",
      title: "Co wiemy z realnych danych",
      description: "Metric facts.",
      items: [
        {
          id: "brief_metric_wordpress",
          title: "WordPress: content_object_count = 16",
          kind: "metric",
          priority: 21,
          source_connectors: ["wordpress_ekologus"],
          evidence_ids: ["ev_refresh_wordpress_inventory"],
          metric_facts: metricFacts,
          action_ids: [],
          summary: "WILQ ma realne metric facts z connectora WordPress.",
          next_step: "Połącz inventory z GSC/GA4.",
          risk: "low",
          blocker_reason: null
        }
      ]
    },
    {
      id: "what_blocks_us",
      title: "Co blokuje decyzje",
      description: "Blockery.",
      items: [
        {
          id: "brief_status_localo_access_ready",
          title: "Localo: MCP access działa, brak jeszcze ranking/GBP facts",
          kind: "metric",
          priority: 90,
          source_connectors: ["localo"],
          evidence_ids: ["ev_refresh_refresh_localo_f1d5b9fed00c"],
          metric_facts: [],
          action_ids: [],
          summary:
            "Localo MCP initialize=200 potwierdza access. Brakuje jeszcze ranking/GBP facts.",
          next_step: "Nie pokazuj lokalnych rekomendacji bez konkretnych ranking/GBP facts.",
          risk: "low",
          blocker_reason: null
        },
        {
          id: "brief_blocker_linkedin",
          title: "LinkedIn: brakuje organizacji i access tokena",
          kind: "blocker",
          priority: 80,
          source_connectors: ["linkedin"],
          evidence_ids: ["ev_connector_linkedin_status"],
          metric_facts: [],
          action_ids: [],
          summary: "LinkedIn publishing evidence is blocked by missing organization access.",
          next_step: "Skonfiguruj LinkedIn credentials przed post candidates.",
          risk: "medium",
          blocker_reason: "missing LinkedIn credentials"
        }
      ]
    },
    {
      id: "safe_next_actions",
      title: "Bezpieczne następne kroki",
      description: "ActionObjects.",
      items: [
        {
          id: "brief_action_act_1",
          title: "Odnow Google Ads OAuth refresh token",
          kind: "action",
          priority: 80,
          source_connectors: ["google_ads"],
          evidence_ids: ["ev_1"],
          metric_facts: [],
          action_ids: ["act_1"],
          summary: "Google Ads jest zablokowany przez OAuth, zanim WILQ oceni spend.",
          next_step: "Zweryfikuj ActionObject i odśwież OAuth.",
          risk: "low",
          blocker_reason: null
        }
      ]
    },
    {
      id: "recommended_focus",
      title: "Rekomendowany fokus",
      description: "Priorytety.",
      items: [
        {
          id: "brief_focus_merchant_feed",
          title: "Merchant Center: zacznij od kolejki problemów feedu",
          kind: "recommendation",
          priority: 87,
          source_connectors: ["google_merchant_center"],
          evidence_ids: ["ev_refresh_merchant_feed"],
          metric_facts: [metricFacts[1]],
          action_ids: ["act_review_merchant_feed_issues"],
          summary:
            "WILQ widzi Merchant metric facts i kieruje operatora do walidacji kolejki problemów feedu.",
          next_step:
            "Otwórz payload preview dla ActionObject przed zmianą danych produktu.",
          risk: "medium",
          blocker_reason: null
        },
        {
          id: "brief_focus_ga4_quality",
          title: "GA4: sprawdź jakość ruchu na landing pages",
          kind: "recommendation",
          priority: 75,
          source_connectors: ["google_analytics_4"],
          evidence_ids: ["ev_refresh_ga4"],
          metric_facts: [metricFacts[4]],
          action_ids: ["act_review_ga4_tracking_quality"],
          summary: "WILQ ma GA4 metric facts i może ocenić jakość ruchu po odświeżeniu.",
          next_step: "Porównaj engagement i konwersje z kampaniami.",
          risk: "low",
          blocker_reason: null
        },
        {
          id: "brief_focus_gsc_content",
          title: "GSC: przełóż widoczność na kolejkę treści",
          kind: "recommendation",
          priority: 74,
          source_connectors: ["google_search_console"],
          evidence_ids: ["ev_refresh_gsc"],
          metric_facts: [metricFacts[5]],
          action_ids: ["act_prepare_content_refresh_queue"],
          summary: "WILQ ma GSC clicks i może zbudować kolejkę content opportunities.",
          next_step: "Połącz query/page evidence z WordPress inventory.",
          risk: "low",
          blocker_reason: null
        }
      ]
    }
  ],
  top_metric_facts: metricFacts,
  evidence_ids: ["ev_refresh_wordpress_inventory"],
  action_ids: [
    "act_1",
    "act_review_merchant_feed_issues",
    "act_review_ga4_tracking_quality",
    "act_prepare_content_refresh_queue"
  ],
  blocker_count: 1,
  recommendation_count: 1
};

const tacticalQueue = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  items: [
    {
      id: "tq_ga4_landing",
      title: "GA4: /oferta/ / google / cpc",
      domain: "ga4",
      intent: "landing_page_quality",
      priority: 25,
      risk: "low",
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      metric_facts: [metricFacts[4]],
      dimensions: {
        landing_page: "/oferta/",
        source_medium: "google / cpc",
        campaign_name: "Ekologus Ogólna"
      },
      diagnosis: "Landing /oferta/ ma active_users=20 i wymaga sprawdzenia jakości ruchu.",
      next_step: "Sprawdź message match, CTA i tracking przed oceną kampanii.",
      blocked_claims: ["conversion rate", "ROAS"],
      action_ids: ["act_review_ga4_tracking_quality"]
    },
    {
      id: "tq_gsc_content",
      title: "GSC: zielony ład -> /europejski-zielony-lad-co-to-takiego/",
      domain: "gsc_seo",
      intent: "content_refresh",
      priority: 26,
      risk: "low",
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_refresh_gsc"],
      metric_facts: [metricFacts[5]],
      dimensions: {
        query: "zielony ład",
        page: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/",
        wordpress_match: "found",
        wordpress_match_confidence: "exact_url",
        wordpress_connector: "wordpress_ekologus",
        wordpress_content_type: "sitemap",
        wordpress_status: "indexed",
        wordpress_content_url: "https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/"
      },
      diagnosis: "Query zielony ład ma GSC evidence i prowadzi do istniejącej strony.",
      next_step: "Przygotuj refresh istniejącej strony i sprawdź duplikaty w WordPress.",
      blocked_claims: ["conversion uplift", "revenue impact"],
      action_ids: ["act_prepare_content_refresh_queue"]
    },
    {
      id: "tq_merchant_issue",
      title: "Merchant: NOT_IMPACTED / availability_updated / PL",
      domain: "merchant",
      intent: "merchant_feed_triage",
      priority: 27,
      risk: "medium",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      metric_facts: [metricFacts[3]],
      dimensions: {
        issue_type: "availability_updated",
        affected_attribute: "n:availability"
      },
      diagnosis: "Merchant issue availability_updated dotyczy atrybutu n:availability.",
      next_step: "Przygotuj kolejkę przeglądu bez zmiany głównego feedu.",
      blocked_claims: ["automatic feed edit", "approval restored"],
      action_ids: ["act_review_merchant_feed_issues"]
    }
  ],
  evidence_ids: ["ev_refresh_ga4", "ev_refresh_gsc", "ev_refresh_merchant_feed"],
  action_ids: [
    "act_review_ga4_tracking_quality",
    "act_prepare_content_refresh_queue",
    "act_review_merchant_feed_issues"
  ]
};

const merchantDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  connector: {
    id: "google_merchant_center",
    label: "Merchant Center",
    status: "configured",
    configured: true,
    missing_credentials: [],
    available_credential_sources: ["repo_env"],
    freshness: { state: "fresh" },
    supported_actions: ["merchant_feed_issue"]
  },
  latest_refresh: {
    id: "refresh_google_merchant_center_test",
    connector_id: "google_merchant_center",
    mode: "vendor_read",
    status: "completed",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: "2026-06-17T10:00:01Z",
    evidence_ids: ["ev_refresh_merchant_feed"],
    missing_credentials: [],
    checked_credentials: ["GOOGLE_MERCHANT_CENTER_ACCOUNT_ID"],
    external_call_attempted: true,
    vendor_data_collected: true,
    metric_summary: { total_products: 10900, item_level_issue_count: 23 },
    summary: "Merchant Center vendor read completed.",
    errors: [],
    redacted: true
  },
  live_data_available: true,
  product_count: 10900,
  issue_count: 23,
  issue_clusters: [
    {
      id: "merchant_issue_pl_not_impacted_availability_updated_n_availability",
      issue_type: "availability_updated",
      severity: "NOT_IMPACTED",
      resolution: "MERCHANT_ACTION",
      affected_attribute: "n:availability",
      country: "PL",
      reporting_context: "SHOPPING_ADS",
      product_count: 23,
      sample_product_ids: [],
      sample_titles: [],
      sample_unavailable_reason:
        "Obecny kontrakt odczytu Merchant zwraca wymiary problemu i liczbę wystąpień problemu w raportach, ale nie zwraca przykładowych ID produktów ani tytułów.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      blocked_claims: ["approval restored", "revenue recovered", "automatic feed edit"],
      action_id: "act_review_merchant_feed_issues",
      risk: "medium",
      next_step:
        "Przejrzyj tę grupę problemu w `act_review_merchant_feed_issues`; najpierw przygotuj podgląd payloadu, bez automatycznej zmiany feedu."
    }
  ],
  decision_queue: [
    {
      id: "merchant_decision_merchant_issue_pl_not_impacted_availability_updated_n_availability",
      decision_type: "review_issue_cluster",
      status: "ready",
      title: "Merchant: sprawdź zmiana dostępności do sprawdzenia / dostępność",
      summary: "23 zgłoszeń problemu NOT_IMPACTED/MERCHANT_ACTION dla PL / SHOPPING_ADS.",
      cluster_id: "merchant_issue_pl_not_impacted_availability_updated_n_availability",
      issue_type: "availability_updated",
      severity: "NOT_IMPACTED",
      resolution: "MERCHANT_ACTION",
      affected_attribute: "n:availability",
      country: "PL",
      reporting_context: "SHOPPING_ADS",
      product_count: 23,
      issue_count: 23,
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      metric_facts: [metricFacts[3]],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["approval restored", "revenue recovered", "automatic feed edit"],
      rationale:
        "To jest klaster problemu Merchant do ręcznego review. Liczba oznacza wystąpienia problemu w raportach, nie gotową zmianę feedu. Obecny odczyt nie zwraca przykładowych ID produktów ani tytułów.",
      next_step:
        "Przejrzyj tę grupę problemu w `act_review_merchant_feed_issues`; najpierw przygotuj podgląd payloadu, bez automatycznej zmiany feedu.",
      risk: "medium"
    }
  ],
  sections: [
    {
      id: "merchant_feed_health",
      title: "Merchant Center: stan produktów i feedu",
      status: "ready",
      summary: "Metryki Merchant: total_products=10900, item_level_issue_count=23.",
      diagnosis: "WILQ ma metryki Merchant z odczytu i może ocenić skalę feedu.",
      next_step: "Przejdź do kolejki problemów i grupuj je po typie.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      metric_facts: [metricFacts[2], metricFacts[3]],
      tactical_items: [],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["approval restored", "revenue recovered"],
      risk: "medium"
    },
    {
      id: "merchant_issue_queue",
      title: "Merchant Center: kolejka problemów feedu",
      status: "ready",
      summary:
        "WILQ ma 1 grupę problemów feedu, 1 taktykę Merchant i 1 metrykę problemu. Liczby w grupach są wystąpieniami problemu w raportach, nie gwarancją unikalnych produktów.",
      diagnosis: "Najbezpieczniejsza praca to przegląd problemów po typie.",
      next_step: "Otwórz ActionObject `act_review_merchant_feed_issues`.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      metric_facts: [metricFacts[3]],
      tactical_items: [tacticalQueue.items[2]],
      action_ids: ["act_review_merchant_feed_issues"],
      blocked_claims: ["automatic feed edit", "primary feed overwrite"],
      risk: "medium"
    }
  ],
  evidence_ids: ["ev_refresh_merchant_feed"],
  action_ids: ["act_review_merchant_feed_issues"],
  blocker_count: 0
};

const contentDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  connectors: [
    {
      id: "google_search_console",
      label: "Google Search Console",
      status: "configured",
      configured: true,
      missing_credentials: [],
      available_credential_sources: ["repo_env"],
      freshness: { state: "fresh" },
      supported_actions: ["content_refresh"]
    },
    {
      id: "wordpress_ekologus",
      label: "WordPress ekologus.pl",
      status: "configured",
      configured: true,
      missing_credentials: [],
      available_credential_sources: ["repo_env"],
      freshness: { state: "fresh" },
      supported_actions: ["content_refresh"]
    }
  ],
  latest_refreshes: [
    {
      id: "refresh_google_search_console_test",
      connector_id: "google_search_console",
      mode: "vendor_read",
      status: "completed",
      started_at: "2026-06-17T10:00:00Z",
      completed_at: "2026-06-17T10:00:01Z",
      evidence_ids: ["ev_refresh_gsc"],
      missing_credentials: [],
      checked_credentials: ["GOOGLE_APPLICATION_CREDENTIALS"],
      external_call_attempted: true,
      vendor_data_collected: true,
      metric_summary: { clicks: 12, impressions: 120 },
      summary: "GSC vendor read completed.",
      errors: [],
      redacted: true
    },
    {
      id: "refresh_wordpress_ekologus_test",
      connector_id: "wordpress_ekologus",
      mode: "vendor_read",
      status: "completed",
      started_at: "2026-06-17T10:00:00Z",
      completed_at: "2026-06-17T10:00:01Z",
      evidence_ids: ["ev_refresh_wordpress_inventory"],
      missing_credentials: [],
      checked_credentials: ["WORDPRESS_EKOLOGUS_URL"],
      external_call_attempted: true,
      vendor_data_collected: true,
      metric_summary: { content_object_count: 16 },
      summary: "WordPress inventory completed.",
      errors: [],
      redacted: true
    }
  ],
  live_data_available: true,
  query_page_count: 1,
  matched_inventory_count: 1,
  decision_queue: [
    {
      id: "content_decision_https_www_ekologus_pl_bdo",
      decision_type: "refresh_or_merge",
      title: 'SEO: odśwież lub scal "bdo" (1 zapytanie)',
      summary:
        'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja refresh/merge, nie nowy artykuł.',
      page: "https://www.ekologus.pl/bdo/",
      normalized_page_path: "/bdo",
      queries: ["bdo"],
      query_count: 1,
      primary_query: "bdo",
      total_clicks: 12,
      total_impressions: 120,
      aggregate_ctr: 0.1,
      best_average_position: 4.5,
      wordpress_match: "found",
      wordpress_match_confidence: "exact_url",
      wordpress_content_url: "https://www.ekologus.pl/bdo/",
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
      metric_facts: [metricFacts[5]],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["lead uplift", "conversion uplift"],
      rationale:
        "WordPress inventory potwierdza istniejący URL, więc WILQ kieruje to do odświeżenia albo scalenia zamiast tworzenia nowej treści.",
      next_step:
        "Przygotuj brief refresh/merge: title, H1/H2, sekcje brakujące wobec zapytania i CTA. Nie obiecuj leadów ani wzrostów pozycji.",
      risk: "low"
    }
  ],
  sections: [
    {
      id: "content_query_page_matrix",
      title: "GSC: query/page matrix",
      status: "ready",
      summary: "WILQ ma 1 GSC tactical items i 1 query/page metric facts.",
      diagnosis: "Query/page matrix pozwala wskazać konkretne strony i zapytania.",
      next_step: "Otwórz najwyższe priorytety i sprawdź intent oraz WordPress match.",
      source_connectors: ["google_search_console"],
      evidence_ids: ["ev_refresh_gsc"],
      metric_facts: [metricFacts[5]],
      tactical_items: [tacticalQueue.items[1]],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["lead uplift", "conversion uplift"],
      risk: "low"
    },
    {
      id: "content_inventory_match",
      title: "WordPress: inventory protection",
      status: "ready",
      summary: "WILQ ma 1 inventory facts, 1 matched queue items i 0 missing matches.",
      diagnosis: "WordPress inventory chroni marketera przed pisaniem drugi raz tego samego.",
      next_step: "Najpierw obsłuż matched refresh/merge; nowe treści twórz po duplicate check.",
      source_connectors: ["wordpress_ekologus"],
      evidence_ids: ["ev_refresh_wordpress_inventory", "ev_refresh_gsc"],
      metric_facts: [metricFacts[0]],
      tactical_items: [tacticalQueue.items[1]],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["new article without inventory check"],
      risk: "low"
    }
  ],
  evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
  action_ids: ["act_prepare_content_refresh_queue"],
  blocker_count: 0
};

const ga4Diagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  connector: {
    id: "google_analytics_4",
    label: "Google Analytics 4",
    status: "configured",
    configured: true,
    missing_credentials: [],
    available_credential_sources: ["repo_env"],
    freshness: { state: "fresh" },
    supported_actions: ["ga4_tracking_gap"]
  },
  latest_refresh: {
    id: "refresh_google_analytics_4_test",
    connector_id: "google_analytics_4",
    mode: "vendor_read",
    status: "completed",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: "2026-06-17T10:00:01Z",
    evidence_ids: ["ev_refresh_ga4"],
    missing_credentials: [],
    checked_credentials: ["GOOGLE_APPLICATION_CREDENTIALS"],
    external_call_attempted: true,
    vendor_data_collected: true,
    metric_summary: { active_users: 20, sessions: 30 },
    summary: "GA4 vendor read completed.",
    errors: [],
    redacted: true
  },
  live_data_available: true,
  landing_group_count: 1,
  low_engagement_count: 1,
  wordpress_match_count: 0,
  decision_queue: [
    {
      id: "ga4_decision_tq_ga4_landing",
      decision_type: "review_landing_mapping",
      title: "Sprawdź mapowanie landing page: /oferta/",
      status: "blocked",
      priority: 31,
      metric_tiles: { aktywni: 20, sesje: 30, engagement: "12.5%" },
      landing_page: "/oferta/",
      source_medium: "google / cpc",
      campaign_name: "Ekologus Ogólna",
      wordpress_match: "missing",
      wordpress_match_confidence: "missing",
      wordpress_content_url: null,
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      metric_facts: [metricFacts[4]],
      action_ids: ["act_review_ga4_tracking_quality"],
      blocked_claims: ["conversion rate", "ROAS", "revenue", "profitability"],
      rationale:
        "GA4 widzi ruch na landingu /oferta/, ale WordPress inventory nie potwierdza dopasowania URL.",
      next_step:
        "Sprawdź mapowanie landing page i dopiero potem oceniaj message match albo jakość ruchu.",
      risk: "medium"
    }
  ],
  sections: [
    {
      id: "ga4_landing_behavior",
      title: "GA4: jakość ruchu z landingów",
      status: "ready",
      summary: "WILQ ma 1 landing/source/campaign groups i 1 GA4 metric facts.",
      diagnosis: "GA4 behavior facts pozwalają wskazać landing pages do kontroli jakości ruchu.",
      next_step: "Najpierw sprawdź grupy z niskim engagement.",
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      metric_facts: [metricFacts[4]],
      tactical_items: [tacticalQueue.items[0]],
      action_ids: ["act_review_ga4_tracking_quality"],
      blocked_claims: ["conversion rate", "ROAS", "revenue"],
      risk: "low"
    },
    {
      id: "ga4_tracking_readiness",
      title: "GA4: gotowość pomiaru konwersji",
      status: "missing",
      summary: "WILQ ma 1 metrykę zachowania i 0 metryk konwersji albo kluczowych zdarzeń.",
      diagnosis: "Aktualne dane wspierają review jakości ruchu, ale nie dowodzą konwersji.",
      next_step: "Waliduj ActionObject i zatrzymaj wnioski o konwersjach bez metryk.",
      source_connectors: ["google_analytics_4"],
      evidence_ids: ["ev_refresh_ga4"],
      metric_facts: [metricFacts[4]],
      tactical_items: [tacticalQueue.items[0]],
      action_ids: ["act_review_ga4_tracking_quality"],
      blocked_claims: ["conversion drop", "funnel diagnosis"],
      risk: "medium"
    }
  ],
  evidence_ids: ["ev_refresh_ga4"],
  action_ids: ["act_review_ga4_tracking_quality"],
  blocker_count: 0
};

const localoDiagnostics = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  connector: {
    id: "localo",
    label: "Localo",
    status: "configured",
    configured: true,
    missing_credentials: [],
    available_credential_sources: ["repo_env"],
    freshness: { state: "fresh" },
    supported_actions: []
  },
  latest_refresh: {
    id: "refresh_localo_access_ready_test",
    connector_id: "localo",
    mode: "vendor_read",
    status: "completed",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: "2026-06-17T10:00:01Z",
    evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
    missing_credentials: [],
    checked_credentials: ["LOCALO_ACCESS_TOKEN"],
    external_call_attempted: true,
    vendor_data_collected: true,
    metric_summary: {
      api: "localo_mcp_oauth_probe",
      mcp_initialize_status: 200,
      authorization_code_supported: 1,
      pkce_s256_supported: 1,
      access_token_present: 1
    },
    summary: "Localo MCP initialize completed with local OAuth access token.",
    errors: [],
    redacted: true
  },
  access_probe: {
    status: "access_ready",
    source_run_id: "refresh_localo_access_ready_test",
    mcp_initialize_status: 200,
    authorization_code_supported: true,
    pkce_s256_supported: true,
    access_token_present: true,
    evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
    summary:
      "Localo MCP initialize zwrócił 200. To potwierdza dostęp WILQ do MCP, ale nie jest jeszcze dowodem rankingów, GBP ani konkurencji."
  },
  live_data_available: false,
  visibility_fact_count: 0,
  decision_queue: [
    {
      id: "localo_access_ready_wait_for_visibility_facts",
      decision_type: "access_ready_wait_for_visibility_facts",
      status: "ready",
      title: "Localo access działa; brakuje ranking/GBP facts",
      summary:
        "MCP initialize=200 potwierdza dostęp. WILQ nie ma jeszcze lokalnych rankingów, GBP, konkurencji ani reviews.",
      rationale:
        "To jest gotowość adaptera, nie diagnoza lokalnej widoczności. Marketer nie powinien traktować tego jako zadania optymalizacyjnego.",
      next_step:
        "Zostaw Localo jako status źródła i dodaj Localo read contract dla rankings/GBP/competitors/reviews.",
      access_status: "access_ready",
      allowed_evidence: ["mcp_initialize", "oauth_metadata", "access_token_presence"],
      missing_read_contracts: [
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
        "local_tasks"
      ],
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [
        "local ranking",
        "GBP performance",
        "competitor visibility",
        "local visibility uplift"
      ],
      risk: "low"
    },
    {
      id: "localo_block_visibility_claims_without_read_contract",
      decision_type: "block_visibility_claims",
      status: "blocked",
      title: "Nie wyciągaj wniosków o lokalnej widoczności bez Localo facts",
      summary:
        "WILQ blokuje claimy o rankingach, GBP, konkurencji, reviews i wzroście widoczności, dopóki Localo read contract nie dostarczy tych facts.",
      rationale:
        "Access/readiness nie jest metryką marketingową. To chroni dashboard i skille przed udawaniem lokalnego SEO insightu.",
      next_step:
        "Najpierw dodaj typed Localo read contract; dopiero potem buduj lokalne ActionObjecty.",
      access_status: "access_ready",
      allowed_evidence: ["mcp_initialize"],
      missing_read_contracts: [
        "local_rankings",
        "gbp_visibility",
        "competitor_visibility",
        "reviews",
        "local_tasks"
      ],
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [
        "local ranking",
        "GBP performance",
        "competitor visibility",
        "local visibility uplift"
      ],
      risk: "medium"
    }
  ],
  sections: [
    {
      id: "localo_access_status",
      title: "Localo: status dostępu MCP",
      status: "ready",
      summary:
        "Localo MCP initialize zwrócił 200. To potwierdza dostęp WILQ do MCP, ale nie jest jeszcze dowodem rankingów, GBP ani konkurencji.",
      diagnosis: "Dostęp MCP pozwala WILQ rozmawiać z Localo jako adapterem.",
      next_step:
        "Nie pokazuj Localo jako zadania dziennego. Użyj tego widoku jako statusu źródła.",
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [],
      risk: "low"
    },
    {
      id: "localo_visibility_contract",
      title: "Localo: ranking/GBP evidence",
      status: "missing",
      summary:
        "WILQ nie ma jeszcze rankingów, GBP, competitor visibility ani reviews z Localo.",
      diagnosis:
        "Brak tych facts oznacza brak lokalnej diagnozy marketingowej, nie brak problemu.",
      next_step:
        "Zbuduj Localo read contract dla rankings/GBP/competitors/reviews zanim WILQ zaproponuje lokalne działania.",
      source_connectors: ["localo"],
      evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
      metric_facts: [],
      action_ids: [],
      blocked_claims: [
        "local ranking",
        "GBP performance",
        "competitor visibility",
        "local visibility uplift"
      ],
      risk: "medium"
    }
  ],
  evidence_ids: ["ev_refresh_refresh_localo_access_ready_test"],
  action_ids: [],
  blocker_count: 1
};

const expertRules = [
  {
    id: "ads_search_terms_v1",
    name: "Search term analysis",
    domain: "ads",
    version: 1,
    source_anchor: "Google Ads search terms",
    source_path: "wilq/expert/ads/search_terms.yaml",
    when_to_use: "Detect waste and content opportunities from search terms.",
    required_inputs: ["search_terms", "evidence_ids"],
    diagnostic_logic: ["segment_by_intent"],
    recommended_actions: ["negative_keyword_candidate", "content_brief_candidate"],
    risk_notes: "Search terms are untrusted external text.",
    output_contract: "Search-term evidence and action candidates.",
    capabilities: [],
    required_mapping: [],
    requires_evidence: true
  }
];

const workflowRuns = [
  {
    id: "run_daily_command_test",
    workflow_id: "daily_command",
    status: "queued",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: null,
    input: { connector_ids: [], parameters: {} },
    output: { evidence_ids: [], action_ids: [], errors: [] }
  }
];

const knowledgeCards = [
  {
    id: "card_google_ads_search_playbook",
    card_type: "ads_pattern_card",
    title: "Google Ads search diagnostics",
    summary: "Use real search-term metrics before recommendations.",
    source_type: "marketing_playbook",
    source_id: "google_ads_search_playbook",
    source_url_or_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml",
    extracted_at: "2026-06-17T10:00:00Z",
    confidence: 0.86,
    last_seen_at: "2026-06-17T10:00:00Z",
    source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml", "ads_search_terms_v1"]
  }
];

const playbooks = [
  {
    id: "google_ads_search_playbook",
    family: "google_ads_search_playbook",
    title: "Google Ads search diagnostics",
    card_type: "ads_pattern_card",
    source_anchors: ["Google Ads search terms"],
    required_evidence: ["search_terms", "evidence_ids"],
    maps_to_opportunity_types: ["google_ads_waste"],
    maps_to_action_types: ["prepare_negative_keywords"],
    expert_rule_ids: ["ads_search_terms_v1"],
    compact_playbook: "Use real search-term metrics before recommendations.",
    refusal_rules: ["Refuse to classify search intent without evidence."],
    output_contract: "Evidence-backed search-term opportunity.",
    source_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml"
  }
];

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/api/dashboard/command-center")) {
        return Promise.resolve(
          Response.json({
            generated_at: "2026-06-17T10:00:00Z",
            strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
            primary_next_step:
              "Najpierw otwórz /merchant i przejrzyj kolejkę problemów feedu.",
            blocker_count: 0,
            tactical_item_count: 3,
            daily_decisions: [
              {
                id: "decision_review_merchant_feed_issues",
                title: "Przejrzyj kolejkę problemów Merchant Center",
                route: "/merchant",
                status: "ready",
                priority: 10,
                metric_tiles: {
                  produkty: 10900,
                  "typy problemów": 15,
                  zgłoszenia: 1887,
                  decyzje: 8,
                  blockery: 0
                },
                co_widzimy:
                  "Merchant Center: produkty=10900, typy problemów=15, zgłoszenia=1887, decyzje=8, blockery=0. Źródła=google_merchant_center, dowody=2 evidence IDs, akcje=1 ActionObject.",
                dlaczego_to_ma_znaczenie:
                  "WILQ widzi 10900 produktów i 1887 zgłoszeń problemów feedu. To wymaga ręcznego review przed zmianami.",
                bezpieczny_next_step:
                  "Otwórz /merchant, sprawdź kolejkę problemów i waliduj ActionObject.",
                skill_id: "wilq-merchant-feed-operator",
                codex_prompt:
                  "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center dla Ekologus.",
                codex_context_endpoint: "/api/codex/context-pack",
                expected_codex_output: "Polski brief przeglądu problemów feedu z evidence IDs.",
                source_connectors: ["google_merchant_center"],
                evidence_ids: [
                  "ev_refresh_merchant_feed",
                  "ev_refresh_merchant_issue_clusters"
                ],
                action_ids: ["act_review_merchant_feed_issues"],
                blocked_claims: ["approval restored", "automatic feed edit"],
                risk: "medium"
              },
              {
                id: "decision_prepare_content_refresh_queue",
                title: "Przejrzyj kolejkę SEO z GSC i WordPress",
                route: "/content-planner",
                status: "ready",
                priority: 12,
                metric_tiles: { "query/page": 1, "WP match": 1, decyzje: 1, wyświetlenia: 120, kliknięcia: 12 },
                co_widzimy:
                  "Content + SEO: query/page=1, WP match=1, decyzje=1, wyświetlenia=120, kliknięcia=12. Źródła=google_search_console, wordpress_ekologus, dowody=2 evidence IDs, akcje=1 ActionObject.",
                dlaczego_to_ma_znaczenie:
                  'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja refresh/merge, nie nowy artykuł. Pełny drilldown query/page i URL jest w /content-planner.',
                bezpieczny_next_step:
                  'Otwórz /content-planner i zacznij od: SEO: odśwież lub scal "bdo" (1 zapytanie).',
                skill_id: "wilq-content-strategist",
                codex_prompt:
                  "Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh.",
                codex_context_endpoint: "/api/codex/context-pack",
                expected_codex_output: "Polska kolejka content decyzji.",
                source_connectors: ["google_search_console", "wordpress_ekologus"],
                evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
                action_ids: ["act_prepare_content_refresh_queue"],
                blocked_claims: ["lead uplift", "ranking guarantee"],
                risk: "low"
              },
              {
                id: "decision_review_ads_campaign_metrics",
                title: "Przejrzyj kampanie Google Ads z live metryk",
                route: "/ads-doctor",
                status: "ready",
                priority: 16,
                metric_tiles: { kampanie: 18, "search terms": 50 },
                co_widzimy:
                  "Google Ads: kampanie=18, search terms=50. Źródła=google_ads, dowody=1 evidence ID, akcje=brak ActionObject.",
                dlaczego_to_ma_znaczenie:
                  "Google Ads OAuth, MCC login i child customer działają.",
                bezpieczny_next_step:
                  "Otwórz /ads-doctor i analizuj tylko metryki widoczne w evidence.",
                source_connectors: ["google_ads"],
                evidence_ids: ["ev_refresh_refresh_google_ads_test"],
                action_ids: [],
                blocked_claims: ["CPA", "ROAS", "search-term waste"],
                risk: "medium"
              }
            ],
            operator_brief: [
              {
                id: "daily_ads_status",
                title: "Ads: live campaign metrics dostępne",
                route: "/ads-doctor",
                status: "ready",
                priority: 30,
                summary: "Google Ads ma live metric facts.",
                next_step: "Otwórz /ads-doctor i przejdź do read-only performance review.",
                source_connectors: ["google_ads"],
                evidence_ids: ["ev_refresh_refresh_google_ads_test"],
                action_ids: [],
                metric_tiles: { kampanie: 18, "search terms": 50, blockery: 1 },
                blocked_claims: ["CPA", "ROAS", "search-term waste"],
                risk: "medium"
              },
              {
                id: "daily_merchant_feed",
                title: "Merchant: kolejka problemów feedu",
                route: "/merchant",
                status: "ready",
                priority: 10,
                summary:
                  "Produkty=10900, typy problemów=15, zgłoszenia=1887, decyzje=8. To jest read-only queue.",
                next_step:
                  "Otwórz /merchant i przejrzyj decyzje feedu przed walidacją ActionObject.",
                source_connectors: ["google_merchant_center"],
                evidence_ids: [
                  "ev_refresh_merchant_feed",
                  "ev_refresh_merchant_issue_clusters"
                ],
                action_ids: ["act_review_merchant_feed_issues"],
                metric_tiles: {
                  produkty: 10900,
                  "typy problemów": 15,
                  zgłoszenia: 1887,
                  decyzje: 8,
                  blockery: 0
                },
                blocked_claims: ["approval restored", "automatic feed edit"],
                risk: "medium"
              },
              {
                id: "daily_content_queue",
                title: "Content: kolejka SEO z GSC i WordPress",
                route: "/content-planner",
                status: "ready",
                priority: 12,
                summary:
                  'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja refresh/merge, nie nowy artykuł.',
                next_step:
                  'Otwórz /content-planner i zacznij od: SEO: odśwież lub scal "bdo" (1 zapytanie).',
                source_connectors: ["google_search_console", "wordpress_ekologus"],
                evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
                action_ids: ["act_prepare_content_refresh_queue"],
                metric_tiles: { "query/page": 1, "WP match": 1, decyzje: 1, wyświetlenia: 120, kliknięcia: 12 },
                blocked_claims: ["lead uplift", "ranking guarantee"],
                risk: "low"
              },
              {
                id: "daily_ga4_landing_quality",
                title: "GA4: pomiar i jakość ruchu do kontroli",
                route: "/ga4",
                status: "blocked",
                priority: 14,
                summary:
                  "GA4 ma 1 grupę landing/source/campaign i 1 decyzję review: pomiar=1, jakość ruchu=0. Status blocked oznacza brak kontraktu na ROAS/revenue/conversion drop/tracking fixed, nie awarię connectora.",
                next_step:
                  "Otwórz /ga4 i przejdź przez kolejkę decyzji. Waliduj `act_review_ga4_tracking_quality`.",
                source_connectors: ["google_analytics_4"],
                evidence_ids: ["ev_refresh_ga4"],
                action_ids: ["act_review_ga4_tracking_quality"],
                metric_tiles: {
                  "grupy ruchu": 1,
                  decyzje: 1,
                  pomiar: 1,
                  "jakość ruchu": 0,
                  "braki kontraktu": 1
                },
                blocked_claims: ["ROAS", "revenue", "conversion drop", "tracking fixed"],
                risk: "medium"
              }
            ],
            demo_script: [
              {
                id: "demo_start_command_center",
                label: "Start: plan dnia WILQ",
                route: "/command-center",
                status: "ready",
                what_it_proves:
                  "WILQ zbiera gotowe źródła, blockery, evidence IDs i ActionObjecty.",
                operator_prompt: "Pokaż dzisiejszy priorytet i akcje do walidacji.",
                source_item_ids: ["daily_ads_status", "daily_merchant_feed"],
                evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_merchant_feed"],
                action_ids: ["act_review_merchant_feed_issues"]
              },
              {
                id: "demo_daily_merchant_feed",
                label: "Merchant Center: dowód feedu produktów",
                route: "/merchant",
                status: "ready",
                what_it_proves:
                  "Merchant Center daje realne product/feed metryki i ActionObject review.",
                operator_prompt: "Otwórz /merchant i przejrzyj kolejkę problemów feedu.",
                source_item_ids: ["daily_merchant_feed"],
                evidence_ids: ["ev_refresh_merchant_feed"],
                action_ids: ["act_review_merchant_feed_issues"]
              }
            ],
            action_plan: [
              {
                id: "plan_review_merchant_feed_issues",
                title: "Przejrzyj kolejkę problemów Merchant Center",
                route: "/merchant",
                status: "ready",
                priority: 10,
                category: "Merchant Center",
                why_it_matters:
                  "WILQ widzi 10900 produktów i 1887 zgłoszeń problemów feedu. To wymaga ręcznego review przed zmianami.",
                operator_action:
                  "Otwórz /merchant, sprawdź kolejkę problemów i waliduj ActionObject.",
                skill_id: "wilq-merchant-feed-operator",
                codex_prompt:
                  "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center dla Ekologus.",
                codex_context_endpoint: "/api/codex/context-pack",
                expected_codex_output: "Polski brief przeglądu problemów feedu z evidence IDs.",
                source_connectors: ["google_merchant_center"],
                evidence_ids: [
                  "ev_refresh_merchant_feed",
                  "ev_refresh_merchant_issue_clusters"
                ],
                action_ids: ["act_review_merchant_feed_issues"],
                blocked_claims: ["approval restored", "automatic feed edit"],
                risk: "medium"
              },
              {
                id: "plan_prepare_content_refresh_queue",
                title: "Przejrzyj kolejkę SEO z GSC i WordPress",
                route: "/content-planner",
                status: "ready",
                priority: 12,
                category: "Content + SEO",
                why_it_matters:
                  'GSC: 120 wyświetleń, 12 kliknięć, CTR 10.00%; główne zapytanie: "bdo". WordPress potwierdza istniejącą stronę, więc to jest decyzja refresh/merge, nie nowy artykuł. Pełny drilldown query/page i URL jest w /content-planner.',
                operator_action:
                  'Otwórz /content-planner i zacznij od: SEO: odśwież lub scal "bdo" (1 zapytanie).',
                skill_id: "wilq-content-strategist",
                codex_prompt:
                  "Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh.",
                codex_context_endpoint: "/api/codex/context-pack",
                expected_codex_output: "Polska kolejka content decyzji.",
                source_connectors: ["google_search_console", "wordpress_ekologus"],
                evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
                action_ids: ["act_prepare_content_refresh_queue"],
                blocked_claims: ["lead uplift", "ranking guarantee"],
                risk: "low"
              },
              {
                id: "plan_review_ads_campaign_metrics",
                title: "Przejrzyj kampanie Google Ads z live metryk",
                route: "/ads-doctor",
                status: "ready",
                priority: 16,
                category: "Google Ads",
                why_it_matters: "Google Ads OAuth, MCC login i child customer działają.",
                operator_action: "Otwórz /ads-doctor i analizuj tylko metryki widoczne w evidence.",
                source_connectors: ["google_ads"],
                evidence_ids: ["ev_refresh_refresh_google_ads_test"],
                action_ids: [],
                blocked_claims: ["CPA", "ROAS", "search-term waste"],
                risk: "medium"
              }
            ],
            connector_summary: { total: 1, configured: 0, missing_credentials: 1 },
            sections: {
              todays_moves: opportunities,
              money_leaks: opportunities,
              traffic_wins: [],
              content_to_rewrite: [],
              content_to_create: [],
              local_visibility_moves: [],
              social_queue: []
            },
            active_actions: actions,
            connector_health: connectors,
            codex_operator_status: {}
          })
        );
      }
      if (url.endsWith("/api/marketing/brief")) {
        return Promise.resolve(Response.json(marketingBrief));
      }
      if (url.endsWith("/api/marketing/tactical-queue")) {
        return Promise.resolve(Response.json(tacticalQueue));
      }
      if (url.endsWith("/api/ads/diagnostics")) {
        return Promise.resolve(Response.json(adsDiagnostics));
      }
      if (url.endsWith("/api/merchant/diagnostics")) {
        return Promise.resolve(Response.json(merchantDiagnostics));
      }
      if (url.endsWith("/api/content/diagnostics")) {
        return Promise.resolve(Response.json(contentDiagnostics));
      }
      if (url.endsWith("/api/ga4/diagnostics")) {
        return Promise.resolve(Response.json(ga4Diagnostics));
      }
      if (url.endsWith("/api/localo/diagnostics")) {
        return Promise.resolve(Response.json(localoDiagnostics));
      }
      if (url.endsWith("/api/connectors")) return Promise.resolve(Response.json(connectors));
      if (url.includes("/api/metrics?")) return Promise.resolve(Response.json(metricFacts));
      if (url.endsWith("/api/metrics/status")) return Promise.resolve(Response.json(metricStoreStatus));
      if (url.endsWith("/api/opportunities")) return Promise.resolve(Response.json(opportunities));
      if (url.endsWith("/api/actions")) return Promise.resolve(Response.json(actions));
      if (url.includes("/api/actions/") && url.endsWith("/validate")) {
        const actionId = url.split("/api/actions/")[1]?.replace("/validate", "") ?? "unknown";
        return Promise.resolve(
          Response.json({
            action_id: actionId,
            valid: true,
            status: "valid",
            errors: [],
            warnings: [],
            checked_at: "2026-06-17T10:00:00Z"
          })
        );
      }
      if (url.endsWith("/api/evidence")) return Promise.resolve(Response.json(evidence));
      if (url.endsWith("/api/connectors/refresh-runs")) {
        return Promise.resolve(Response.json(connectorRefreshRuns));
      }
      if (url.endsWith("/api/expert/rules")) return Promise.resolve(Response.json(expertRules));
      if (url.endsWith("/api/workflows")) {
        return Promise.resolve(
          Response.json([{ id: "daily_command", label: "Daily Command", description: "Runs." }])
        );
      }
      if (url.endsWith("/api/workflow-runs")) return Promise.resolve(Response.json(workflowRuns));
      if (url.endsWith("/api/knowledge/cards")) return Promise.resolve(Response.json(knowledgeCards));
      if (url.endsWith("/api/knowledge/playbooks")) return Promise.resolve(Response.json(playbooks));
      return Promise.resolve(Response.json({}));
    })
  );
}

describe("WILQ dashboard", () => {
  let testQueryClient: QueryClient;

  it("uses short server-state cache defaults without overriding test config", () => {
    const client = createWilqQueryClient({
      defaultOptions: {
        queries: {
          gcTime: Infinity,
          retry: false
        }
      }
    });

    expect(client.getDefaultOptions().queries?.staleTime).toBe(30_000);
    expect(client.getDefaultOptions().queries?.refetchOnWindowFocus).toBe(false);
    expect(client.getDefaultOptions().queries?.gcTime).toBe(Infinity);
    expect(client.getDefaultOptions().queries?.retry).toBe(false);
    client.clear();
  });

  beforeEach(() => {
    mockFetch();
    testQueryClient = createWilqQueryClient({
      defaultOptions: {
        queries: {
          gcTime: Infinity,
          retry: false
        }
      }
    });
  });

  afterEach(() => {
    cleanup();
    testQueryClient.clear();
    vi.unstubAllGlobals();
  });

  function renderApp(path: string) {
    return render(
      <App
        appRouter={createWilqRouter({ initialPath: path, defaultPendingMinMs: 0 })}
        client={testQueryClient}
      />
    );
  }

  it("command center renders", async () => {
    renderApp("/command-center");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Command Center" })).toBeInTheDocument()
    );
    expect(screen.getByText("Dzisiejsze decyzje marketera")).toBeInTheDocument();
    expect(
      screen.getByText("Najpierw otwórz /merchant i przejrzyj kolejkę problemów feedu.")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Decyzje")).toHaveLength(1);
    expect(screen.getAllByRole("link", { name: "act_review_merchant_feed_issues" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Przejrzyj kolejkę problemów Merchant Center")).toBeInTheDocument();
    expect(screen.getAllByText("produkty").length).toBeGreaterThan(0);
    expect(screen.getAllByText("10900").length).toBeGreaterThan(0);
    expect(screen.queryByText(/status=ready/)).not.toBeInTheDocument();
    expect(screen.getAllByText("Prompt do Codex").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Jak Codex może pomóc").length).toBeGreaterThan(0);
    expect(screen.getByText("Skill: wilq-merchant-feed-operator")).toBeInTheDocument();
    expect(screen.getAllByText("Context-pack: /api/codex/context-pack").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/^Dowody/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Dowody: \d+ ID/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/^Przykładowe dowody/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Evidence:/)).not.toBeInTheDocument();
    expect(screen.queryByText("Przykładowe evidence")).not.toBeInTheDocument();
    expect(screen.getAllByText(/ponowne zatwierdzenie produktu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/automatyczna zmiana feedu/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/wzrost leadów/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/gwarancja pozycji/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/waste na zapytaniach/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/approval restored/)).not.toBeInTheDocument();
    expect(screen.queryByText(/automatic feed edit/)).not.toBeInTheDocument();
    expect(screen.queryByText(/lead uplift/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ranking guarantee/)).not.toBeInTheDocument();
    expect(screen.queryByText(/search-term waste/)).not.toBeInTheDocument();
    expect(
      screen.getByText("Oczekiwany wynik: Polski brief przeglądu problemów feedu z evidence IDs.")
    ).toBeInTheDocument();
    expect(screen.getByText("Przejrzyj kolejkę SEO z GSC i WordPress")).toBeInTheDocument();
    expect(screen.getAllByText(/120 wyświetleń/).length).toBeGreaterThan(0);
    expect(screen.getByText("Przejrzyj kampanie Google Ads z live metryk")).toBeInTheDocument();
    expect(screen.getByText("Źródła i ograniczenia")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Otwórz ustawienia" })).toBeInTheDocument();
    expect(screen.queryByText("Plan działań marketera")).not.toBeInTheDocument();
    expect(screen.queryByText("Dzisiejszy panel operatora")).not.toBeInTheDocument();
    expect(screen.queryByText("Blockery i świeżość źródeł")).not.toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS_DEVELOPER_TOKEN/)).not.toBeInTheDocument();
    expect(screen.queryByText("Dzisiejsze konkretne taktyki")).not.toBeInTheDocument();
    expect(screen.queryByText("Realne metric facts zapisane lokalnie")).not.toBeInTheDocument();
    expect(screen.queryByText("GA4: /oferta/ / google / cpc")).not.toBeInTheDocument();
    expect(screen.queryByText("Merchant: NOT_IMPACTED / availability_updated / PL")).not.toBeInTheDocument();
    expect(screen.queryByText("Kontekst")).not.toBeInTheDocument();
    expect(screen.queryByText(/Źródło: google \/ cpc/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Issue: availability_updated/)).not.toBeInTheDocument();
    expect(screen.queryByText("Priorytety dnia")).not.toBeInTheDocument();
    expect(screen.queryByText("Dzisiejszy brief WILQ")).not.toBeInTheDocument();
    expect(screen.queryByText("Budżet i ryzyko wydatków")).not.toBeInTheDocument();
    expect(screen.queryByText("Kandydaci działań API")).not.toBeInTheDocument();
    expect(screen.queryByText(/connector_configured/)).not.toBeInTheDocument();
    expect(screen.queryByText(/No performance metrics have been collected/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Run a read-only/)).not.toBeInTheDocument();
    expect(screen.queryByText("Demo dla marketera")).not.toBeInTheDocument();
    expect(screen.queryByText(/priority \d+/i)).not.toBeInTheDocument();
    expect(screen.queryByText("GA4: (not set) / (not set)")).not.toBeInTheDocument();
    expect(screen.queryByText("Merchant: feed/product issues do przeglądu")).not.toBeInTheDocument();
    expect(screen.queryByText("Content: GSC query/page + WordPress inventory")).not.toBeInTheDocument();
  });

  it("connector status renders", async () => {
    renderApp("/settings");
    await waitFor(() => expect(screen.getByText("Google Ads")).toBeInTheDocument());
    expect(screen.getByText(/GOOGLE_ADS_DEVELOPER_TOKEN/)).toBeInTheDocument();
  });

  it("opportunities route renders", async () => {
    renderApp("/opportunities");
    await waitFor(() =>
      expect(screen.getByText("Przejrzyj kolejki Ads do oceny bez apply")).toBeInTheDocument()
    );
    expect(screen.getByRole("heading", { name: "Szanse i decyzje" })).toBeInTheDocument();
    expect(screen.getByText("Kolejka decyzji z WILQ API")).toBeInTheDocument();
    expect(screen.getAllByText("kampanie").length).toBeGreaterThan(0);
    expect(screen.getAllByText("podgląd budżetu").length).toBeGreaterThan(0);
    expect(screen.getByText("Aktywne")).toBeInTheDocument();
    expect(screen.queryByText("Rejestr kart opportunities")).not.toBeInTheDocument();
    expect(screen.getByText("Dowody użyte przez karty")).toBeInTheDocument();
    expect(screen.queryByText("Evidence użyte przez opportunities")).not.toBeInTheDocument();
  });

  it("actions route starts from ActionObjects instead of registry dumps", async () => {
    renderApp("/actions");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Actions" })).toBeInTheDocument()
    );
    expect(screen.getByText("ActionObjecty do przeglądu")).toBeInTheDocument();
    expect(screen.getByText("Dowody powiązane z akcjami")).toBeInTheDocument();
    expect(screen.getByText("Do walidacji")).toBeInTheDocument();
    expect(screen.getByText("Odnow Google Ads OAuth refresh token")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "OPPORTUNITIES" })).not.toBeInTheDocument();
    expect(screen.queryByText("Connector Refresh Runs")).not.toBeInTheDocument();
  });

  it("action detail route renders", async () => {
    renderApp("/actions/act_1");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Odnow Google Ads OAuth refresh token" })
      ).toBeInTheDocument()
    );
  });

  it("ads doctor route renders live metric-backed diagnostics", async () => {
    renderApp("/ads-doctor");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Ads Doctor" })).toBeInTheDocument()
    );
    expect(
      screen.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w Google Ads" })
    ).toBeInTheDocument();
    expect(screen.getByText("Przejrzyj aktywność kampanii Google Ads")).toBeInTheDocument();
    expect(
      screen.getByText("Przejrzyj zapytania z reklam bez automatycznych wykluczeń")
    ).toBeInTheDocument();
    expect(screen.getByText("Przejrzyj rekomendacje Google Ads bez apply")).toBeInTheDocument();
    expect(screen.getByText("Nie wdrażaj zmian Ads bez osobnego ActionObject")).toBeInTheDocument();
    expect(screen.queryByText("Handoff blockera Ads")).not.toBeInTheDocument();
    expect(screen.queryByText(/handoff blockera OAuth/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dowody i ograniczenia Ads" })).toBeInTheDocument();
    expect(screen.getAllByText("Ekologus Search").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Konwersje").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Wartość konw.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("450,75").length).toBeGreaterThan(0);
    expect(screen.getAllByText("kliknięcia").length).toBeGreaterThan(0);
    expect(screen.getAllByText("wyświetlenia").length).toBeGreaterThan(0);
    expect(screen.getAllByText("koszt").length).toBeGreaterThan(0);
    expect(screen.getAllByText("164.6").length).toBeGreaterThan(0);
    expect(screen.getAllByText("podgląd wpływu").length).toBeGreaterThan(0);
    expect(screen.getByText("Koszt 7 dni")).toBeInTheDocument();
    expect(screen.getByText("7-dniowy budżet")).toBeInTheDocument();
    expect(screen.getByText("78,38%")).toBeInTheDocument();
    expect(screen.getAllByText("CAMPAIGN_BUDGET").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/automatyczne przyjęcie rekomendacji/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Karty wiedzy:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/card_google_ads_budget_review_playbook/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Reguły:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ads_scaling_candidates_v1/).length).toBeGreaterThan(0);
    expect(screen.getByText(/wartość_konwersji=120/)).toBeInTheDocument();
    expect(screen.getAllByText(/Brakujące kontrakty/).length).toBeGreaterThan(0);
    expect(screen.getByText("bdo rejestracja")).toBeInTheDocument();
    expect(screen.getAllByText(/90-dniowa kontrola bezpieczeństwa/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Odnow Google Ads OAuth refresh token")).not.toBeInTheDocument();
    expect(screen.queryByText(/wasted spend/)).not.toBeInTheDocument();
    expect(screen.queryByText("Read contract Ads")).not.toBeInTheDocument();
    expect(screen.queryByText("Search terms read-only")).not.toBeInTheDocument();
    expect(screen.queryByText("Campaign activity read contract")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence")).not.toBeInTheDocument();
    expect(screen.queryByText("configured")).not.toBeInTheDocument();
  });

  it("expert rules render on operating routes", async () => {
    renderApp("/ads-doctor/search-terms");
    await waitFor(() => expect(screen.getByText("Expert Rules")).toBeInTheDocument());
    expect(screen.getByText("Search term analysis")).toBeInTheDocument();
  });

  it("workflow route renders persisted workflow runs", async () => {
    renderApp("/workflows");
    await waitFor(() => expect(screen.getByText("Ostatnie uruchomienia")).toBeInTheDocument());
    expect(screen.getByText("Rejestr workflowów")).toBeInTheDocument();
    expect(screen.getByText("Wyniki workflowów")).toBeInTheDocument();
    expect(screen.getByText("run_daily_command_test")).toBeInTheDocument();
  });

  it("knowledge route renders compiled cards and playbooks", async () => {
    renderApp("/knowledge");
    await waitFor(() => expect(screen.getByText("Knowledge Cards")).toBeInTheDocument());
    expect(screen.getAllByText("Google Ads search diagnostics").length).toBeGreaterThan(0);
    expect(screen.getByText("Machine-Readable Playbooks")).toBeInTheDocument();
  });

  it("merchant route renders dedicated feed diagnostics", async () => {
    renderApp("/merchant");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Merchant Center" })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Dowody i ograniczenia Merchant")).toBeInTheDocument();
    expect(screen.queryByText("Merchant Center: feed/product health")).not.toBeInTheDocument();
    expect(screen.queryByText("Merchant Center: kolejka feed/product issues")).not.toBeInTheDocument();
    expect(screen.getByText("Co marketer ma zrobić teraz z feedem")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczny tryb pracy")).toBeInTheDocument();
    expect(screen.getByText(/WILQ grupuje problemy Merchant po typie/)).toBeInTheDocument();
    expect(
      screen.getByText("Merchant: sprawdź zmiana dostępności do sprawdzenia / dostępność")
    ).toBeInTheDocument();
    expect(screen.getByText("przegląd problemu feedu")).toBeInTheDocument();
    expect(
      screen.getByText(/23 zgłoszeń problemu NOT_IMPACTED\/MERCHANT_ACTION dla PL \/ SHOPPING_ADS/)
    ).toBeInTheDocument();
    expect(screen.getByText("Zgłoszenia")).toBeInTheDocument();
    expect(screen.getByText("zgłoszenia: 23")).toBeInTheDocument();
    expect(screen.getByText("problem: availability_updated")).toBeInTheDocument();
    expect(screen.getByText("atrybut: n:availability")).toBeInTheDocument();
    expect(screen.getByText("kontekst: SHOPPING_ADS")).toBeInTheDocument();
    expect(screen.queryByText("Affected")).not.toBeInTheDocument();
    expect(screen.queryByText("configured")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence")).not.toBeInTheDocument();
    expect(screen.getByText("dostęp skonfigurowany")).toBeInTheDocument();
    expect(screen.getByText("metryki feedu dostępne")).toBeInTheDocument();
    expect(screen.getByText("Dowody")).toBeInTheDocument();
    expect(screen.getByText(/nie zwraca przykładowych ID produktów/)).toBeInTheDocument();
    expect(screen.getByText(/najpierw przygotuj podgląd payloadu/)).toBeInTheDocument();
    expect(screen.getAllByText(/produkt zatwierdzony ponownie/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/automatic feed edit/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Waliduj ActionObject" })).toHaveAttribute(
      "href",
      "/actions/act_review_merchant_feed_issues"
    );
    expect(screen.queryByText("Merchant: NOT_IMPACTED / availability_updated / PL")).not.toBeInTheDocument();
    expect(screen.getAllByText(/total_products: 10900/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ev_refresh_merchant_feed/).length).toBeGreaterThan(0);
    expect(screen.getByText("ActionObjecty do walidacji")).toBeInTheDocument();
    expect(
      screen.getByText("Przygotuj kolejkę przeglądu feedu Merchant Center")
    ).toBeInTheDocument();
    expect(screen.getByText(/Apply zablokowany/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Waliduj" }));
    await waitFor(() => expect(screen.getByText("Wynik:")).toBeInTheDocument());
    expect(screen.getByText("valid")).toBeInTheDocument();
    expect(screen.getByText("Błędy: brak")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "act_review_merchant_feed_issues" })[0]
    ).toHaveAttribute("href", "/actions/act_review_merchant_feed_issues");
    expect(
      screen.getAllByRole("link", { name: "ev_refresh_merchant_feed" })[0]
    ).toHaveAttribute("href", "/evidence/ev_refresh_merchant_feed");
  });

  it("ga4 and gsc routes render workflow-specific brief focus", async () => {
    renderApp("/ga4");
    await waitFor(() => expect(screen.getByRole("heading", { name: /^GA4$/ })).toBeInTheDocument());
    expect(screen.getByText("Status GA4 / Landing Quality")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma sprawdzić teraz w jakości ruchu")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczny tryb analityki")).toBeInTheDocument();
    expect(screen.getByText(/Brak metryk konwersji oznacza/)).toBeInTheDocument();
    expect(screen.getByText("Sprawdź mapowanie landing page: /oferta/")).toBeInTheDocument();
    expect(screen.getByText("aktywni")).toBeInTheDocument();
    expect(screen.getByText("sesje")).toBeInTheDocument();
    expect(screen.getByText("engagement")).toBeInTheDocument();
    expect(screen.getAllByText(/Landing: \/oferta\//).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Źródło: google \/ cpc/).length).toBeGreaterThan(0);
    expect(screen.getByText(/WordPress: brak potwierdzenia/)).toBeInTheDocument();
    expect(screen.getAllByText(/Gotowość pomiaru/).length).toBeGreaterThan(0);
    expect(screen.getByText("Dowody i ograniczenia GA4")).toBeInTheDocument();
    expect(screen.queryByText(/Tracking readiness/)).not.toBeInTheDocument();
    expect(screen.queryByText("GA4: landing/source/campaign behavior")).not.toBeInTheDocument();
    expect(screen.queryByText("GA4: tracking/conversion readiness")).not.toBeInTheDocument();
    expect(
      screen.getByText("Sprawdź jakość pomiaru GA4 przed oceną kampanii")
    ).toBeInTheDocument();
    expect(screen.queryByText("Analytics Safety Gate")).not.toBeInTheDocument();
    expect(screen.getByText("Brama bezpieczeństwa GA4")).toBeInTheDocument();
    expect(screen.getAllByText(/active_users: 20/).length).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("link", { name: "act_review_ga4_tracking_quality" })[0]
    ).toHaveAttribute("href", "/actions/act_review_ga4_tracking_quality");

    cleanup();
    testQueryClient.clear();
    mockFetch();

    renderApp("/seo-gsc");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "SEO / GSC" })).toBeInTheDocument()
    );
    expect(screen.getByText("Status SEO / Content")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma zrobić teraz z treściami")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczny tryb treści")).toBeInTheDocument();
    expect(
      screen.getByText(/WILQ łączy zapytania i URL-e z GSC z inventory WordPress/)
    ).toBeInTheDocument();
    expect(screen.getByText(/SEO: odśwież lub scal "bdo"/)).toBeInTheDocument();
    expect(screen.getByText(/120 wyświetleń/)).toBeInTheDocument();
    expect(screen.getByText(/12 kliknięć/)).toBeInTheDocument();
    expect(screen.getByText(/WordPress: potwierdzony/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Waliduj ActionObject" })).toHaveAttribute(
      "href",
      "/actions/act_prepare_content_refresh_queue"
    );
    expect(screen.getByText("Dowody i ograniczenia Content")).toBeInTheDocument();
    expect(screen.queryByText("GSC: query/page matrix")).not.toBeInTheDocument();
    expect(screen.queryByText("WordPress: inventory protection")).not.toBeInTheDocument();
    expect(screen.queryByText("WordPress match: found")).not.toBeInTheDocument();
    expect(screen.getByText("Brama bezpieczeństwa treści")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "act_prepare_content_refresh_queue" })[0]).toHaveAttribute(
      "href",
      "/actions/act_prepare_content_refresh_queue"
    );
    expect(screen.getAllByText(/clicks: 12/).length).toBeGreaterThan(0);
  });

  it("localo social and content routes render workflow-specific blockers or focus", async () => {
    renderApp("/localo");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Localo" })).toBeInTheDocument()
    );
    expect(screen.getByText("Status Localo / MCP access")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma wiedzieć o Localo")).toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia Localo")).toBeInTheDocument();
    expect(
      screen.getByText("Localo access działa; brakuje ranking/GBP facts")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Nie wyciągaj wniosków o lokalnej widoczności bez Localo facts")
    ).toBeInTheDocument();
    expect(screen.getAllByText("access działa").length).toBeGreaterThan(0);
    expect(screen.getByText("Brama bezpieczeństwa Localo/GBP")).toBeInTheDocument();
    expect(screen.queryByText("Local Visibility Focus")).not.toBeInTheDocument();
    expect(screen.queryByText("Taktyki z WILQ API")).not.toBeInTheDocument();
    expect(screen.queryByText("Metric facts")).not.toBeInTheDocument();
    expect(screen.queryByText("24 Taktyki")).not.toBeInTheDocument();
    expect(screen.queryByText("Dokończ Localo access")).not.toBeInTheDocument();

    cleanup();
    testQueryClient.clear();
    mockFetch();

    renderApp("/social-publisher");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Social Publisher" })).toBeInTheDocument()
    );
    expect(screen.getByText("Social Publishing Focus")).toBeInTheDocument();
    expect(screen.getByText("LinkedIn: brakuje organizacji i access tokena")).toBeInTheDocument();

    cleanup();
    testQueryClient.clear();
    mockFetch();

    renderApp("/content-planner");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Content Planner" })).toBeInTheDocument()
    );
    expect(screen.getByText("Status SEO / Content")).toBeInTheDocument();
    expect(screen.getByText("Dowody i ograniczenia Content")).toBeInTheDocument();
    expect(screen.queryByText("WordPress: inventory protection")).not.toBeInTheDocument();
    expect(
      screen.getByText("Przygotuj kolejkę odświeżenia treści ekologus.pl")
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Waliduj" }));
    await waitFor(() => expect(screen.getByText("Wynik:")).toBeInTheDocument());
    expect(screen.getByText("valid")).toBeInTheDocument();
  });

  it("evidence detail route renders source trace from linked evidence id", async () => {
    renderApp("/evidence/ev_refresh_merchant_feed");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "ev_refresh_merchant_feed" })
      ).toBeInTheDocument()
    );
    expect(
      screen.getByText("Merchant Center feed diagnostics collected sanitized product issue counters.")
    ).toBeInTheDocument();
    expect(screen.getByText("Source connector: google_merchant_center")).toBeInTheDocument();
  });
});
