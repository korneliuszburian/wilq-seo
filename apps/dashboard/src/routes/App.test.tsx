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
    id: "opp_1",
    type: "google_ads_waste",
    title: "Google Ads diagnostics blocked until credentials are configured",
    domain: "google_ads",
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_1"],
    metrics: [],
    human_diagnosis: "Connector state is missing.",
    recommended_action: "Configure connector.",
    risk: "low",
    action_ids: ["act_1"],
    expert_rule_ids: ["ads_search_terms_v1"],
    playbook_ids: ["google_ads_search_playbook"],
    is_fixture: true
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
    recommended_reason: "Przygotuj feed issue queue z payload preview.",
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
  connector: connectors[0],
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
    title: "Google Ads: campaign activity rows",
    summary:
      "WILQ ma 1 campaign rows: clicks=107, impressions=2783, cost_micros=164591174, conversions=2.5, conversion_value=450.75.",
    allowed_metrics: ["clicks", "impressions", "cost_micros", "conversions", "conversion_value"],
    missing_read_contracts: ["recommendations"],
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
    next_step: "Użyj campaign rows do przeglądu aktywności."
  },
  search_terms_read_contract: {
    id: "ads_search_terms_read_contract",
    status: "ready",
    title: "Google Ads: search terms read-only rows",
    summary:
      "WILQ ma 1 search term rows: clicks=12, impressions=140, cost_micros=9000000, conversions=1, conversion_value=120.",
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
    next_step: "Użyj search term rows jako read-only przeglądu zapytań."
  },
  sections: [
    {
      id: "ads_live_data_status",
      title: "Google Ads: live data dostępne",
      status: "ready",
      summary: "WILQ ma zapisane metric facts z read-only Google Ads vendor_read.",
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
      action_ids: ["act_1"],
    blocked_claims: ["CPA", "ROAS", "wasted budget"],
      risk: "medium"
    },
    {
      id: "ads_campaign_overview",
      title: "Campaign activity read contract",
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
      action_ids: ["act_1"],
      blocked_claims: ["CPA", "ROAS", "wasted budget"],
      risk: "medium"
    }
  ],
  blocked_handoff: {
    id: "ads_oauth_blocked_handoff",
    status: "blocked",
    title: "Google Ads: finalny handoff blockera OAuth",
    summary: "Google Ads OAuth token refresh HTTP 401 (oauth_error=deleted_client).",
    marketer_message:
      "W demo pokaż, że WILQ widzi problem z dostępem i blokuje wszystkie wnioski o spendzie, CPA, ROAS, search terms i negative keywords.",
    repair_steps: [
      "Otwórz /ads-doctor i pokaż redacted OAuth blocker.",
      "Zweryfikuj ActionObject `act_configure_google_ads_env`.",
      "Uzyskaj świeży Google Ads OAuth token z zakresem `adwords`.",
      "Uruchom read-only `google_ads vendor_read`."
    ],
    allowed_demo_claims: [
      "Google Ads jest zablokowany przez OAuth/API access.",
      "WILQ nie zmyśla Ads metryk bez vendor evidence.",
      "Naprawa dostępu ma ActionObject i validation gate."
    ],
    blocked_claims: ["wasted spend", "CPA", "ROAS", "search terms"],
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
    action_ids: ["act_1"]
  },
  evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
  action_ids: ["act_1"],
  blocker_count: 2
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
          title: "Merchant Center: zacznij od feed/product issues",
          kind: "recommendation",
          priority: 87,
          source_connectors: ["google_merchant_center"],
          evidence_ids: ["ev_refresh_merchant_feed"],
          metric_facts: [metricFacts[1]],
          action_ids: ["act_review_merchant_feed_issues"],
          summary: "WILQ widzi Merchant metric facts i kieruje operatora do walidacji feedu.",
          next_step: "Otwórz payload preview dla action candidate przed zmianą feedu.",
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
      next_step: "Przygotuj review queue bez zmiany primary feedu.",
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
        "Obecny Merchant read contract zwraca issue dimensions i liczby produktów, ale nie zwraca sample product IDs ani tytułów.",
      source_connectors: ["google_merchant_center"],
      evidence_ids: ["ev_refresh_merchant_feed"],
      blocked_claims: ["approval restored", "revenue recovered", "automatic feed edit"],
      action_id: "act_review_merchant_feed_issues",
      risk: "medium",
      next_step:
        "Przejrzyj ten issue cluster w `act_review_merchant_feed_issues`; najpierw przygotuj payload preview, bez automatycznej zmiany feedu."
    }
  ],
  sections: [
    {
      id: "merchant_feed_health",
      title: "Merchant Center: feed/product health",
      status: "ready",
      summary: "Metric facts: total_products=10900, issue_product_count=23.",
      diagnosis: "WILQ ma read-only Merchant facts i może ocenić skalę feedu.",
      next_step: "Przejdź do issue queue i grupuj problemy po issue_type.",
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
      title: "Merchant Center: kolejka feed/product issues",
      status: "ready",
      summary: "WILQ ma 1 issue clusters, 1 Merchant tactical items i 1 issue metric facts.",
      diagnosis: "Najbezpieczniejsza praca to review problemów po issue_type.",
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
      title: "Odśwież lub scal istniejącą treść: https://www.ekologus.pl/bdo/",
      page: "https://www.ekologus.pl/bdo/",
      normalized_page_path: "/bdo",
      queries: ["bdo"],
      query_count: 1,
      wordpress_match: "found",
      wordpress_match_confidence: "exact_url",
      wordpress_content_url: "https://www.ekologus.pl/bdo/",
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
      metric_facts: [metricFacts[5]],
      action_ids: ["act_prepare_content_refresh_queue"],
      blocked_claims: ["lead uplift", "conversion uplift"],
      rationale: "WordPress inventory potwierdza istniejącą stronę dla query z GSC.",
      next_step: "Przygotuj refresh/merge brief na podstawie GSC i WordPress inventory.",
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
  sections: [
    {
      id: "ga4_landing_behavior",
      title: "GA4: landing/source/campaign behavior",
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
      title: "GA4: tracking/conversion readiness",
      status: "missing",
      summary: "WILQ ma 1 behavior facts i 0 conversion-like facts.",
      diagnosis: "Aktualne dane wspierają review jakości ruchu, ale nie dowodzą konwersji.",
      next_step: "Waliduj ActionObject i przygotuj tracking-gap checklist bez apply.",
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
              "Najpierw otwórz /merchant i przejrzyj feed/product issues z ActionObject.",
            blocker_count: 2,
            tactical_item_count: 3,
            daily_decisions: [
              {
                id: "decision_review_merchant_feed_issues",
                title: "Przejrzyj produkty z problemami w Merchant Center",
                route: "/merchant",
                status: "ready",
                priority: 10,
                metric_tiles: { produkty: 10900, issues: 23, blockery: 0 },
                co_widzimy:
                  "Merchant Center: produkty=10900, issues=23, blockery=0. Źródła=google_merchant_center, dowody=1 evidence ID, akcje=act_review_merchant_feed_issues.",
                dlaczego_to_ma_znaczenie:
                  "WILQ widzi 10900 produktów i 23 feed/product issues. To wymaga review.",
                bezpieczny_next_step:
                  "Otwórz /merchant, sprawdź issue queue i waliduj ActionObject.",
                skill_id: "wilq-merchant-feed-operator",
                codex_prompt:
                  "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center dla Ekologus.",
                codex_context_endpoint: "/api/codex/context-pack",
                expected_codex_output: "Polski brief feed issue review z evidence IDs.",
                source_connectors: ["google_merchant_center"],
                evidence_ids: ["ev_refresh_merchant_feed"],
                action_ids: ["act_review_merchant_feed_issues"],
                blocked_claims: ["approval restored", "automatic feed edit"],
                risk: "medium"
              },
              {
                id: "decision_prepare_content_refresh_queue",
                title: "Ułóż kolejkę refresh/merge/create dla treści SEO",
                route: "/content-planner",
                status: "ready",
                priority: 12,
                metric_tiles: { "query/page": 1, "WP match": 1 },
                co_widzimy:
                  "Content + SEO: query/page=1, WP match=1. Źródła=google_search_console, wordpress_ekologus, dowody=2 evidence IDs, akcje=act_prepare_content_refresh_queue.",
                dlaczego_to_ma_znaczenie:
                  "WILQ ma query/page kandydatów i dopasowania WordPress.",
                bezpieczny_next_step:
                  "Otwórz /content-planner i wybierz refresh, merge, create albo block.",
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
                title: "Merchant: feed/product issues do przeglądu",
                route: "/merchant",
                status: "ready",
                priority: 10,
                summary: "Produkty=10900, issues=23. To jest read-only queue.",
                next_step: "Otwórz /merchant i waliduj `act_review_merchant_feed_issues`.",
                source_connectors: ["google_merchant_center"],
                evidence_ids: ["ev_refresh_merchant_feed"],
                action_ids: ["act_review_merchant_feed_issues"],
                metric_tiles: { produkty: 10900, issues: 23, blockery: 0 },
                blocked_claims: ["approval restored", "automatic feed edit"],
                risk: "medium"
              },
              {
                id: "daily_content_queue",
                title: "Content: GSC query/page + WordPress inventory",
                route: "/content-planner",
                status: "ready",
                priority: 12,
                summary: "Query/page=1, WordPress match=1.",
                next_step: "Otwórz /content-planner i przygotuj queue refresh/create/merge/block.",
                source_connectors: ["google_search_console", "wordpress_ekologus"],
                evidence_ids: ["ev_refresh_gsc", "ev_refresh_wordpress_inventory"],
                action_ids: ["act_prepare_content_refresh_queue"],
                metric_tiles: { "query/page": 1, "WP match": 1 },
                blocked_claims: ["lead uplift", "ranking guarantee"],
                risk: "low"
              },
              {
                id: "daily_ga4_landing_quality",
                title: "GA4: landing/source/campaign quality review",
                route: "/ga4",
                status: "ready",
                priority: 14,
                summary: "Landing groups=1, low engagement=1, WP match=0.",
                next_step: "Otwórz /ga4 i waliduj `act_review_ga4_tracking_quality`.",
                source_connectors: ["google_analytics_4"],
                evidence_ids: ["ev_refresh_ga4"],
                action_ids: ["act_review_ga4_tracking_quality"],
                metric_tiles: { "landing groups": 1, "low engagement": 1, "WP match": 0 },
                blocked_claims: ["ROAS", "revenue", "conversion drop"],
                risk: "low"
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
                operator_prompt: "Otwórz /merchant i waliduj feed/product issues.",
                source_item_ids: ["daily_merchant_feed"],
                evidence_ids: ["ev_refresh_merchant_feed"],
                action_ids: ["act_review_merchant_feed_issues"]
              }
            ],
            action_plan: [
              {
                id: "plan_review_merchant_feed_issues",
                title: "Przejrzyj produkty z problemami w Merchant Center",
                route: "/merchant",
                status: "ready",
                priority: 10,
                category: "Merchant Center",
                why_it_matters:
                  "WILQ widzi 10900 produktów i 23 feed/product issues. To wymaga review.",
                operator_action: "Otwórz /merchant, sprawdź issue queue i waliduj ActionObject.",
                skill_id: "wilq-merchant-feed-operator",
                codex_prompt:
                  "Użyj skilla wilq-merchant-feed-operator. Przejrzyj Merchant Center dla Ekologus.",
                codex_context_endpoint: "/api/codex/context-pack",
                expected_codex_output: "Polski brief feed issue review z evidence IDs.",
                source_connectors: ["google_merchant_center"],
                evidence_ids: ["ev_refresh_merchant_feed"],
                action_ids: ["act_review_merchant_feed_issues"],
                blocked_claims: ["approval restored", "automatic feed edit"],
                risk: "medium"
              },
              {
                id: "plan_prepare_content_refresh_queue",
                title: "Ułóż kolejkę refresh/merge/create dla treści SEO",
                route: "/content-planner",
                status: "ready",
                priority: 12,
                category: "Content + SEO",
                why_it_matters: "WILQ ma query/page kandydatów i dopasowania WordPress.",
                operator_action: "Otwórz /content-planner i wybierz refresh, merge, create albo block.",
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
      screen.getByText("Najpierw otwórz /merchant i przejrzyj feed/product issues z ActionObject.")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Decyzje")).toHaveLength(1);
    expect(screen.getAllByRole("link", { name: "act_review_merchant_feed_issues" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Przejrzyj produkty z problemami w Merchant Center")).toBeInTheDocument();
    expect(screen.getAllByText("produkty").length).toBeGreaterThan(0);
    expect(screen.getAllByText("10900").length).toBeGreaterThan(0);
    expect(screen.queryByText(/status=ready/)).not.toBeInTheDocument();
    expect(screen.getAllByText("Prompt do Codex").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Jak Codex może pomóc").length).toBeGreaterThan(0);
    expect(screen.getByText("Skill: wilq-merchant-feed-operator")).toBeInTheDocument();
    expect(screen.getAllByText("Context-pack: /api/codex/context-pack").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Oczekiwany wynik: Polski brief feed issue review z evidence IDs.")
    ).toBeInTheDocument();
    expect(screen.getByText("Ułóż kolejkę refresh/merge/create dla treści SEO")).toBeInTheDocument();
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
      expect(screen.getByText("Google Ads diagnostics blocked until credentials are configured")).toBeInTheDocument()
    );
    expect(screen.getByText("Kolejka decyzji")).toBeInTheDocument();
    expect(screen.getByText("Evidence użyte przez opportunities")).toBeInTheDocument();
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
    expect(screen.getByText("Google Ads: live data dostępne")).toBeInTheDocument();
    expect(screen.getByText(/clicks: \d+/)).toBeInTheDocument();
    expect(screen.getAllByText(/campaign_id=123/).length).toBeGreaterThan(0);
    expect(screen.getByText("Co wolno pokazać w demo")).toBeInTheDocument();
    expect(
      screen.getByText("WILQ nie zmyśla Ads metryk bez vendor evidence.")
    ).toBeInTheDocument();
    expect(screen.getByText("Google Ads: campaign activity rows")).toBeInTheDocument();
    expect(screen.getByText("Read contract Ads")).toBeInTheDocument();
    expect(screen.getAllByText("Ekologus Search").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Konwersje").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Wartość konw.").length).toBeGreaterThan(0);
    expect(screen.getAllByText("450.75").length).toBeGreaterThan(0);
    expect(screen.getAllByText("120").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Brakujące read contracts/).length).toBeGreaterThan(0);
    expect(screen.getByText("Google Ads: search terms read-only rows")).toBeInTheDocument();
    expect(screen.getByText("Search terms read-only")).toBeInTheDocument();
    expect(screen.getByText("bdo rejestracja")).toBeInTheDocument();
    expect(screen.getByText(/90_day_safety_check/)).toBeInTheDocument();
    expect(screen.getByText("Campaign activity read contract")).toBeInTheDocument();
    expect(screen.getAllByText("Odnow Google Ads OAuth refresh token").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "act_1" })[0]).toHaveAttribute(
      "href",
      "/actions/act_1"
    );
    expect(screen.getAllByText(/wasted spend/).length).toBeGreaterThan(0);
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
    expect(screen.getByText("Merchant Center: feed/product health")).toBeInTheDocument();
    expect(screen.getByText("Merchant Center: kolejka feed/product issues")).toBeInTheDocument();
    expect(screen.getByText("Co marketer ma zrobić teraz z feedem")).toBeInTheDocument();
    expect(screen.getByText("Bezpieczny tryb pracy")).toBeInTheDocument();
    expect(screen.getByText(/WILQ grupuje problemy Merchant po issue type/)).toBeInTheDocument();
    expect(screen.getByText("availability_updated / n:availability")).toBeInTheDocument();
    expect(screen.getByText(/Dotyczy 23 produktów w kraju PL \/ SHOPPING_ADS/)).toBeInTheDocument();
    expect(screen.getByText(/nie zwraca sample product IDs/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Waliduj ActionObject" })).toHaveAttribute(
      "href",
      "/actions/act_review_merchant_feed_issues"
    );
    expect(screen.getAllByText("Merchant: NOT_IMPACTED / availability_updated / PL").length).toBe(1);
    expect(screen.getAllByText(/total_products: 10900/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ev_refresh_merchant_feed/).length).toBeGreaterThan(0);
    expect(screen.getByText("ActionObject focus")).toBeInTheDocument();
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
    expect(screen.getByText(/Brak conversion-like facts oznacza/)).toBeInTheDocument();
    expect(screen.getAllByText(/Landing: \/oferta\//).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Źródło: google \/ cpc/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Tracking readiness/)).toBeInTheDocument();
    expect(screen.getByText("GA4: landing/source/campaign behavior")).toBeInTheDocument();
    expect(screen.getByText("GA4: tracking/conversion readiness")).toBeInTheDocument();
    expect(
      screen.getByText("Sprawdź jakość pomiaru GA4 przed oceną kampanii")
    ).toBeInTheDocument();
    expect(screen.getAllByText("GA4: /oferta/ / google / cpc").length).toBeGreaterThan(0);
    expect(screen.getByText("Analytics Safety Gate")).toBeInTheDocument();
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
    expect(screen.getByText("Bezpieczny tryb content")).toBeInTheDocument();
    expect(screen.getByText(/WILQ łączy GSC query\/page z WordPress inventory/)).toBeInTheDocument();
    expect(screen.getByText(/Query: zielony ład/)).toBeInTheDocument();
    expect(
      screen.getAllByText(/WordPress match: found/).length
    ).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Waliduj ActionObject" })).toHaveAttribute(
      "href",
      "/actions/act_prepare_content_refresh_queue"
    );
    expect(screen.getByText("GSC: query/page matrix")).toBeInTheDocument();
    expect(screen.getByText("WordPress: inventory protection")).toBeInTheDocument();
    expect(
      screen.getAllByText("GSC: zielony ład -> /europejski-zielony-lad-co-to-takiego/").length
    ).toBeGreaterThan(0);
    expect(screen.getByText("Content Safety Gate")).toBeInTheDocument();
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
    expect(screen.getByText("Local Visibility Focus")).toBeInTheDocument();
    expect(
      screen.getByText("Localo: MCP access działa, brak jeszcze ranking/GBP facts")
    ).toBeInTheDocument();

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
    expect(screen.getByText("WordPress: inventory protection")).toBeInTheDocument();
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
